#!/usr/bin/env python3
"""
Cryptocurrency Basket Divergence Signal Generation
Phase 3 of Pairs Trading Research Specification

This script generates mean-reversion trading signals based on coin divergence
from sector/category basket performance.

Usage:
    python3 signals/calc_basket_divergence_signals.py \
        --categories "Meme Coins,DeFi Blue Chips,Dino Coins" \
        --lookback 60 \
        --threshold 1.5 \
        --basket-weight market_cap

Author: Research Team
Date: 2025-10-26
"""

import os
import sys
import argparse
import warnings
from datetime import datetime
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

# Default parameters (aligned with Phase 2 recommendations)
DEFAULT_LOOKBACK_WINDOW = 60  # days for z-score calculation
DEFAULT_SIGNAL_THRESHOLD = 1.5  # |z-score| threshold for entry
DEFAULT_BASKET_WEIGHT = 'equal_weight'  # 'equal_weight' or 'market_cap'
DEFAULT_MIN_BASKET_SIZE = 5  # minimum coins with valid data

# Filter thresholds
MIN_VOLUME_USD = 5_000_000  # $5M 30-day average volume
MIN_MARKET_CAP_USD = 50_000_000  # $50M market cap
MAX_VOLATILITY_ANNUAL = 1.50  # 150% annualized volatility
MIN_CORRELATION = 0.3  # minimum correlation with basket
MIN_DATA_DAYS = 90  # minimum days of continuous data

# Tier 1 categories (from Phase 2)
TIER_1_CATEGORIES = [
    'Meme Coins',
    'DeFi Blue Chips',
    'Dino Coins',
]

# Data paths
DATA_DIR = 'data/raw'
PRICE_DATA_FILE = os.path.join(DATA_DIR, 'combined_coinbase_coinmarketcap_daily.csv')
CATEGORY_MAPPING_FILE = os.path.join(DATA_DIR, 'category_mappings_validated.csv')

# Output paths
SIGNALS_DIR = 'signals'
OUTPUT_FULL = os.path.join(SIGNALS_DIR, 'basket_divergence_signals_full.csv')
OUTPUT_CURRENT = os.path.join(SIGNALS_DIR, 'basket_divergence_signals_current.csv')
OUTPUT_BY_CATEGORY = os.path.join(SIGNALS_DIR, 'basket_divergence_signals_by_category.csv')

# ============================================================================
# DATA LOADING
# ============================================================================

def load_price_data(filepath: str) -> pd.DataFrame:
    """Load and prepare price data."""
    print(f"Loading price data from {filepath}...")
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    
    # Use 'base' column for symbol matching (e.g., 'BTC' instead of 'BTC/USD')
    if 'base' not in df.columns:
        raise ValueError("Price data must have 'base' column for symbol matching")
    
    df = df.sort_values(['base', 'date'])
    
    # Calculate returns (grouped by base symbol)
    df['return'] = df.groupby('base')['close'].pct_change()
    df['log_return'] = np.log(df['close'] / df.groupby('base')['close'].shift(1))
    
    # Handle inf/nan
    df['return'] = df['return'].replace([np.inf, -np.inf], np.nan)
    df['log_return'] = df['log_return'].replace([np.inf, -np.inf], np.nan)
    
    print(f"Loaded {len(df)} rows for {df['base'].nunique()} base symbols")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    
    return df


def load_category_mappings(filepath: str) -> pd.DataFrame:
    """Load category mappings."""
    print(f"Loading category mappings from {filepath}...")
    df = pd.read_csv(filepath)
    
    print(f"Loaded {len(df)} mappings for {df['symbol'].nunique()} symbols")
    print(f"Categories: {df['category'].nunique()}")
    
    return df


# ============================================================================
# BASKET RETURN CALCULATION
# ============================================================================

def calculate_basket_returns(
    price_df: pd.DataFrame,
    category_df: pd.DataFrame,
    category: str,
    weight_method: str = 'equal_weight',
    exclude_symbol: str = None
) -> pd.DataFrame:
    """
    Calculate basket returns for a category.
    
    Parameters:
    -----------
    price_df : pd.DataFrame
        Price data with returns
    category_df : pd.DataFrame
        Category mappings
    category : str
        Category name
    weight_method : str
        'equal_weight' or 'market_cap'
    exclude_symbol : str, optional
        Symbol to exclude from basket (for leave-one-out calculation)
    
    Returns:
    --------
    pd.DataFrame with columns: date, basket_return
    """
    # Get symbols in this category
    symbols = category_df[category_df['category'] == category]['symbol'].unique()
    
    # Exclude symbol if specified
    if exclude_symbol:
        symbols = [s for s in symbols if s != exclude_symbol]
    
    # Filter price data (using 'base' column for matching)
    basket_df = price_df[price_df['base'].isin(symbols)].copy()
    
    if len(basket_df) == 0:
        return pd.DataFrame()
    
    # Calculate basket returns by date
    if weight_method == 'equal_weight':
        # Equal-weight basket
        basket_returns = basket_df.groupby('date')['log_return'].mean().reset_index()
        basket_returns.columns = ['date', 'basket_return']
        
    elif weight_method == 'market_cap':
        # Market-cap-weighted basket
        # Calculate weights
        basket_df['weight'] = basket_df.groupby('date')['market_cap'].transform(
            lambda x: x / x.sum()
        )
        basket_df['weighted_return'] = basket_df['weight'] * basket_df['log_return']
        
        basket_returns = basket_df.groupby('date')['weighted_return'].sum().reset_index()
        basket_returns.columns = ['date', 'basket_return']
        
    else:
        raise ValueError(f"Unknown weight method: {weight_method}")
    
    return basket_returns


# ============================================================================
# DIVERGENCE CALCULATION
# ============================================================================

def calculate_zscore_divergence(
    coin_returns: pd.Series,
    basket_returns: pd.Series,
    window: int = 60
) -> pd.Series:
    """
    Calculate z-score of coin's relative performance vs basket.
    
    relative_perf = coin_return - basket_return
    z_score = (relative_perf - mean(relative_perf, window)) / std(relative_perf, window)
    """
    # Calculate relative performance
    relative_perf = coin_returns - basket_returns
    
    # Calculate rolling z-score
    rolling_mean = relative_perf.rolling(window=window, min_periods=window//2).mean()
    rolling_std = relative_perf.rolling(window=window, min_periods=window//2).std()
    
    z_score = (relative_perf - rolling_mean) / rolling_std
    
    return z_score


def calculate_percentile_rank(
    coin_returns: pd.Series,
    all_returns_df: pd.DataFrame,
    window: int = 20
) -> pd.Series:
    """
    Calculate percentile rank of coin's cumulative return within basket.
    
    Parameters:
    -----------
    coin_returns : pd.Series
        Returns for the coin
    all_returns_df : pd.DataFrame
        DataFrame with returns for all coins in basket (wide format)
    window : int
        Lookback window for cumulative returns
    
    Returns:
    --------
    pd.Series with percentile ranks (0-100)
    """
    # Calculate cumulative returns over window
    cum_returns = (1 + all_returns_df).rolling(window=window, min_periods=1).apply(
        lambda x: np.prod(x) - 1, raw=True
    )
    
    # Calculate percentile rank for each date
    percentiles = cum_returns.rank(axis=1, pct=True) * 100
    
    return percentiles[coin_returns.name] if coin_returns.name in percentiles.columns else pd.Series(np.nan, index=coin_returns.index)


def calculate_correlation_with_basket(
    coin_returns: pd.Series,
    basket_returns: pd.Series,
    window: int = 60
) -> float:
    """Calculate rolling correlation between coin and basket."""
    # Align series
    aligned = pd.DataFrame({
        'coin': coin_returns,
        'basket': basket_returns
    }).dropna()
    
    if len(aligned) < window:
        return np.nan
    
    # Calculate correlation over available data
    correlation = aligned['coin'].corr(aligned['basket'])
    
    return correlation


# ============================================================================
# FILTERS
# ============================================================================

def apply_liquidity_filter(
    price_df: pd.DataFrame,
    min_volume: float = MIN_VOLUME_USD,
    window: int = 30
) -> pd.DataFrame:
    """Filter by minimum volume."""
    price_df['volume_30d'] = price_df.groupby('base')['volume'].transform(
        lambda x: x.rolling(window=window, min_periods=window//2).mean()
    )
    
    # Volume is already in USD
    filtered = price_df[price_df['volume_30d'] >= min_volume].copy()
    
    return filtered


def apply_market_cap_filter(
    price_df: pd.DataFrame,
    min_market_cap: float = MIN_MARKET_CAP_USD
) -> pd.DataFrame:
    """Filter by minimum market cap."""
    filtered = price_df[price_df['market_cap'] >= min_market_cap].copy()
    
    return filtered


def apply_volatility_filter(
    price_df: pd.DataFrame,
    max_vol: float = MAX_VOLATILITY_ANNUAL,
    window: int = 30
) -> pd.DataFrame:
    """Filter by maximum volatility."""
    # Calculate rolling volatility (annualized)
    price_df['volatility_30d'] = price_df.groupby('base')['log_return'].transform(
        lambda x: x.rolling(window=window, min_periods=window//2).std() * np.sqrt(252)
    )
    
    filtered = price_df[price_df['volatility_30d'] <= max_vol].copy()
    
    return filtered


def apply_data_quality_filter(
    price_df: pd.DataFrame,
    min_days: int = MIN_DATA_DAYS
) -> pd.DataFrame:
    """Filter symbols with insufficient data."""
    symbol_counts = price_df.groupby('base').size()
    valid_symbols = symbol_counts[symbol_counts >= min_days].index
    
    filtered = price_df[price_df['base'].isin(valid_symbols)].copy()
    
    return filtered


# ============================================================================
# SIGNAL GENERATION
# ============================================================================

def generate_signals_for_category(
    price_df: pd.DataFrame,
    category_df: pd.DataFrame,
    category: str,
    lookback_window: int = 60,
    signal_threshold: float = 1.5,
    basket_weight: str = 'equal_weight',
    min_basket_size: int = 5,
    min_correlation: float = MIN_CORRELATION
) -> pd.DataFrame:
    """
    Generate divergence signals for a category.
    
    Returns:
    --------
    pd.DataFrame with columns: date, symbol, category, signal, z_score, 
                               percentile_rank, basket_corr, basket_return_20d,
                               coin_return_20d, divergence, market_cap, volume_30d_avg
    """
    print(f"\nProcessing category: {category}")
    
    # Get symbols in this category
    symbols = category_df[category_df['category'] == category]['symbol'].unique()
    print(f"  Symbols in category: {len(symbols)}")
    
    # Filter to symbols in category (using 'base' column)
    cat_price_df = price_df[price_df['base'].isin(symbols)].copy()
    
    if len(cat_price_df) == 0:
        print(f"  No data found for category {category}")
        return pd.DataFrame()
    
    # Check basket size
    symbols_with_data = cat_price_df['base'].nunique()
    if symbols_with_data < min_basket_size:
        print(f"  Skipping: only {symbols_with_data} symbols with data (min {min_basket_size})")
        return pd.DataFrame()
    
    print(f"  Symbols with data: {symbols_with_data}")
    
    # Generate signals for each symbol
    all_signals = []
    
    for symbol in cat_price_df['base'].unique():
        # Get coin data
        coin_df = cat_price_df[cat_price_df['base'] == symbol].copy()
        
        # Calculate basket returns (excluding this coin)
        basket_returns_df = calculate_basket_returns(
            price_df=cat_price_df,
            category_df=category_df,
            category=category,
            weight_method=basket_weight,
            exclude_symbol=symbol
        )
        
        if len(basket_returns_df) == 0:
            continue
        
        # Merge coin and basket returns
        merged = coin_df[['date', 'base', 'log_return', 'market_cap', 'volume_30d', 'volatility_30d']].merge(
            basket_returns_df,
            on='date',
            how='inner'
        )
        merged['symbol'] = symbol  # Keep base symbol for clarity
        
        if len(merged) < lookback_window:
            continue
        
        # Calculate z-score divergence
        merged['z_score'] = calculate_zscore_divergence(
            coin_returns=merged['log_return'],
            basket_returns=merged['basket_return'],
            window=lookback_window
        )
        
        # Calculate 20-day cumulative returns for divergence
        merged['coin_return_20d'] = (1 + merged['log_return']).rolling(20, min_periods=1).apply(
            lambda x: np.prod(x) - 1, raw=True
        )
        merged['basket_return_20d'] = (1 + merged['basket_return']).rolling(20, min_periods=1).apply(
            lambda x: np.prod(x) - 1, raw=True
        )
        merged['divergence'] = merged['coin_return_20d'] - merged['basket_return_20d']
        
        # Calculate correlation with basket
        basket_corr = calculate_correlation_with_basket(
            coin_returns=merged['log_return'],
            basket_returns=merged['basket_return'],
            window=lookback_window
        )
        merged['basket_corr'] = basket_corr
        
        # Calculate percentile rank within basket
        # Create wide format for percentile calculation
        basket_wide = cat_price_df.pivot_table(
            index='date',
            columns='base',
            values='log_return'
        )
        
        # Get coin percentile
        if symbol in basket_wide.columns:
            cum_returns = (1 + basket_wide).rolling(20, min_periods=1).apply(
                lambda x: np.prod(x) - 1, raw=True
            )
            percentile_ranks = cum_returns.rank(axis=1, pct=True) * 100
            percentile_series = percentile_ranks[symbol].reset_index()
            percentile_series.columns = ['date', 'percentile_rank']
            merged = merged.merge(percentile_series, on='date', how='left')
        else:
            merged['percentile_rank'] = np.nan
        
        # Generate signals based on thresholds
        merged['signal'] = 'NONE'
        
        # Long signal: underperformer
        long_condition = (
            (merged['z_score'] < -signal_threshold) &
            (merged['percentile_rank'] < 25) &
            (merged['basket_corr'] > min_correlation)
        )
        merged.loc[long_condition, 'signal'] = 'LONG'
        
        # Short signal: outperformer
        short_condition = (
            (merged['z_score'] > signal_threshold) &
            (merged['percentile_rank'] > 75) &
            (merged['basket_corr'] > min_correlation)
        )
        merged.loc[short_condition, 'signal'] = 'SHORT'
        
        # Add category
        merged['category'] = category
        
        # Select final columns
        signal_df = merged[[
            'date', 'symbol', 'category', 'signal', 'z_score', 'percentile_rank',
            'basket_corr', 'basket_return_20d', 'coin_return_20d', 'divergence',
            'market_cap', 'volume_30d', 'volatility_30d'
        ]].copy()
        
        all_signals.append(signal_df)
    
    if len(all_signals) == 0:
        return pd.DataFrame()
    
    # Combine all signals
    category_signals = pd.concat(all_signals, ignore_index=True)
    
    # Count signals
    n_long = (category_signals['signal'] == 'LONG').sum()
    n_short = (category_signals['signal'] == 'SHORT').sum()
    n_total = len(category_signals)
    
    print(f"  Signals generated: {n_long} LONG, {n_short} SHORT (out of {n_total} observations)")
    
    return category_signals


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Generate basket divergence signals for pairs trading',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--categories',
        type=str,
        default=','.join(TIER_1_CATEGORIES),
        help='Comma-separated list of categories to analyze'
    )
    parser.add_argument(
        '--lookback',
        type=int,
        default=DEFAULT_LOOKBACK_WINDOW,
        help='Lookback window for z-score calculation'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=DEFAULT_SIGNAL_THRESHOLD,
        help='Z-score threshold for signal generation'
    )
    parser.add_argument(
        '--basket-weight',
        type=str,
        default=DEFAULT_BASKET_WEIGHT,
        choices=['equal_weight', 'market_cap'],
        help='Basket weighting method'
    )
    parser.add_argument(
        '--min-basket-size',
        type=int,
        default=DEFAULT_MIN_BASKET_SIZE,
        help='Minimum basket size (number of coins)'
    )
    parser.add_argument(
        '--all-categories',
        action='store_true',
        help='Process all categories (ignore --categories)'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Basket Divergence Signal Generation - Phase 3")
    print("=" * 80)
    print(f"Timestamp: {datetime.now()}")
    print(f"\nParameters:")
    print(f"  Lookback window: {args.lookback} days")
    print(f"  Signal threshold: {args.threshold}")
    print(f"  Basket weighting: {args.basket_weight}")
    print(f"  Min basket size: {args.min_basket_size}")
    print(f"\nFilters:")
    print(f"  Min volume (30d avg): ${MIN_VOLUME_USD:,.0f}")
    print(f"  Min market cap: ${MIN_MARKET_CAP_USD:,.0f}")
    print(f"  Max volatility: {MAX_VOLATILITY_ANNUAL:.0%}")
    print(f"  Min correlation: {MIN_CORRELATION}")
    print(f"  Min data days: {MIN_DATA_DAYS}")
    
    # Load data
    price_df = load_price_data(PRICE_DATA_FILE)
    category_df = load_category_mappings(CATEGORY_MAPPING_FILE)
    
    # Apply filters
    print("\n" + "=" * 80)
    print("Applying Filters")
    print("=" * 80)
    
    print(f"Initial symbols: {price_df['base'].nunique()}")
    
    price_df = apply_data_quality_filter(price_df, min_days=MIN_DATA_DAYS)
    print(f"After data quality filter: {price_df['base'].nunique()} symbols")
    
    price_df = apply_liquidity_filter(price_df, min_volume=MIN_VOLUME_USD)
    print(f"After liquidity filter: {price_df['base'].nunique()} symbols")
    
    price_df = apply_market_cap_filter(price_df, min_market_cap=MIN_MARKET_CAP_USD)
    print(f"After market cap filter: {price_df['base'].nunique()} symbols")
    
    price_df = apply_volatility_filter(price_df, max_vol=MAX_VOLATILITY_ANNUAL)
    print(f"After volatility filter: {price_df['base'].nunique()} symbols")
    
    # Determine categories to process
    if args.all_categories:
        categories = sorted(category_df['category'].unique())
        print(f"\nProcessing ALL categories: {len(categories)}")
    else:
        categories = [c.strip() for c in args.categories.split(',')]
        print(f"\nProcessing specified categories: {categories}")
    
    # Generate signals for each category
    print("\n" + "=" * 80)
    print("Signal Generation")
    print("=" * 80)
    
    all_signals = []
    
    for category in categories:
        try:
            signals = generate_signals_for_category(
                price_df=price_df,
                category_df=category_df,
                category=category,
                lookback_window=args.lookback,
                signal_threshold=args.threshold,
                basket_weight=args.basket_weight,
                min_basket_size=args.min_basket_size,
                min_correlation=MIN_CORRELATION
            )
            
            if len(signals) > 0:
                all_signals.append(signals)
        
        except Exception as e:
            print(f"  Error processing {category}: {e}")
            continue
    
    if len(all_signals) == 0:
        print("\nNo signals generated!")
        return
    
    # Combine all signals
    all_signals_df = pd.concat(all_signals, ignore_index=True)
    all_signals_df = all_signals_df.sort_values(['date', 'category', 'symbol'])
    
    # Save outputs
    print("\n" + "=" * 80)
    print("Saving Outputs")
    print("=" * 80)
    
    # Full signals
    all_signals_df.to_csv(OUTPUT_FULL, index=False)
    print(f"Full signals saved: {OUTPUT_FULL}")
    print(f"  Total rows: {len(all_signals_df):,}")
    print(f"  Date range: {all_signals_df['date'].min()} to {all_signals_df['date'].max()}")
    
    # Current signals (most recent date)
    latest_date = all_signals_df['date'].max()
    current_signals = all_signals_df[all_signals_df['date'] == latest_date].copy()
    current_signals.to_csv(OUTPUT_CURRENT, index=False)
    print(f"\nCurrent signals saved: {OUTPUT_CURRENT}")
    print(f"  Date: {latest_date}")
    print(f"  Signals: {len(current_signals)}")
    
    # Signals by category
    category_summary = all_signals_df.groupby(['category', 'signal']).size().reset_index(name='count')
    category_summary = category_summary.pivot(index='category', columns='signal', values='count').fillna(0)
    category_summary = category_summary.astype(int)
    category_summary.to_csv(OUTPUT_BY_CATEGORY)
    print(f"\nCategory summary saved: {OUTPUT_BY_CATEGORY}")
    print(f"\nSignal counts by category:")
    print(category_summary)
    
    # Overall statistics
    print("\n" + "=" * 80)
    print("Summary Statistics")
    print("=" * 80)
    
    signal_counts = all_signals_df['signal'].value_counts()
    print(f"\nOverall signal counts:")
    print(signal_counts)
    
    active_signals = all_signals_df[all_signals_df['signal'].isin(['LONG', 'SHORT'])]
    if len(active_signals) > 0:
        print(f"\nActive signals statistics:")
        print(f"  Total active signals: {len(active_signals):,}")
        print(f"  Symbols with signals: {active_signals['symbol'].nunique()}")
        print(f"  Categories with signals: {active_signals['category'].nunique()}")
        print(f"\nZ-score statistics:")
        print(active_signals['z_score'].describe())
        print(f"\nPercentile rank statistics:")
        print(active_signals['percentile_rank'].describe())
    
    print("\n" + "=" * 80)
    print("Phase 3 Signal Generation Complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()
