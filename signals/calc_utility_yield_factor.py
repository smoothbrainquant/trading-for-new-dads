#!/usr/bin/env python3
"""
Calculate Utility Yield Factor Signals

This module generates factor signals based on DefiLlama data:
- Utility Yield = Daily fees / TVL (annualized)
- On-chain Yield = Staking/lending APYs
- Total Yield = Utility + On-chain yield

Theory:
High utility yield indicates protocols generating significant revenue relative
to their TVL, which may correlate with token value accrual. Combined with
on-chain yields, this provides a comprehensive view of crypto asset productivity.

Signal Generation:
- Long tokens with high total yield (top quintile)
- Short tokens with low total yield (bottom quintile) - or neutral
- Rebalance monthly/quarterly
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Optional


def load_defillama_factors(date: str = None) -> pd.DataFrame:
    """
    Load DefiLlama factor data
    
    Args:
        date: Date string in YYYYMMDD format, defaults to latest
        
    Returns:
        DataFrame with factor data
    """
    if date is None:
        # Find latest file
        data_dir = Path("/workspace/data/raw")
        files = list(data_dir.glob("defillama_factors_*.csv"))
        if not files:
            raise FileNotFoundError("No DefiLlama factor files found")
        latest = max(files, key=lambda x: x.stem.split('_')[-1])
        filepath = latest
    else:
        filepath = Path(f"/workspace/data/raw/defillama_factors_{date}.csv")
    
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    print(f"Loading: {filepath}")
    df = pd.read_csv(filepath)
    
    # Handle infinite values (protocols with 0 TVL but fees)
    df['utility_yield_pct'] = df['utility_yield_pct'].replace([np.inf, -np.inf], np.nan)
    df['total_yield_pct'] = df['total_yield_pct'].replace([np.inf, -np.inf], np.nan)
    
    return df


def calculate_factor_scores(df: pd.DataFrame, method: str = 'total_yield') -> pd.DataFrame:
    """
    Calculate factor scores for each token
    
    Args:
        df: DataFrame with factor data
        method: Scoring method - 'total_yield', 'utility_yield', 'onchain_yield'
        
    Returns:
        DataFrame with factor scores
    """
    df = df.copy()
    
    if method == 'total_yield':
        df['factor_score'] = df['total_yield_pct']
    elif method == 'utility_yield':
        df['factor_score'] = df['utility_yield_pct']
    elif method == 'onchain_yield':
        df['factor_score'] = df['weighted_apy']
    else:
        raise ValueError(f"Unknown method: {method}")
    
    # Remove tokens with missing scores
    df = df[df['factor_score'].notna()].copy()
    
    # Rank tokens (higher yield = higher rank)
    df['factor_rank'] = df['factor_score'].rank(ascending=False, method='average')
    df['factor_percentile'] = df['factor_rank'] / len(df) * 100
    
    return df


def generate_signals(
    df: pd.DataFrame,
    long_threshold: float = 80,  # Top 20%
    short_threshold: float = 20,  # Bottom 20%
    min_tvl: float = 1_000_000,  # Minimum $1M TVL
) -> pd.DataFrame:
    """
    Generate long/short signals based on factor scores
    
    Args:
        df: DataFrame with factor scores
        long_threshold: Percentile threshold for long signals (e.g., 80 = top 20%)
        short_threshold: Percentile threshold for short signals (e.g., 20 = bottom 20%)
        min_tvl: Minimum TVL to include in signals
        
    Returns:
        DataFrame with signals
    """
    df = df.copy()
    
    # Filter by TVL
    df['total_tvl_all'] = df['tvl'].fillna(0) + df['total_tvl'].fillna(0)
    df = df[df['total_tvl_all'] >= min_tvl].copy()
    
    # Recalculate percentiles after filtering
    df['factor_percentile'] = df['factor_score'].rank(ascending=False, pct=True) * 100
    
    # Generate signals
    df['signal'] = 'neutral'
    df.loc[df['factor_percentile'] >= long_threshold, 'signal'] = 'long'
    df.loc[df['factor_percentile'] <= short_threshold, 'signal'] = 'short'
    
    # Add weights (equal weight within each bucket)
    long_count = (df['signal'] == 'long').sum()
    short_count = (df['signal'] == 'short').sum()
    
    df['weight'] = 0.0
    if long_count > 0:
        df.loc[df['signal'] == 'long', 'weight'] = 1.0 / long_count
    if short_count > 0:
        df.loc[df['signal'] == 'short', 'weight'] = -1.0 / short_count
    
    return df


def main():
    """Generate utility yield factor signals"""
    print("=" * 60)
    print("Utility Yield Factor Signal Generation")
    print("=" * 60)
    print()
    
    # Load data
    try:
        df = load_defillama_factors()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nPlease run: python3 data/scripts/fetch_defillama_data.py")
        print("Then run: python3 data/scripts/map_defillama_to_universe.py")
        return
    
    print(f"Loaded data for {len(df)} tokens\n")
    
    # Calculate factor scores using different methods
    methods = {
        'total_yield': 'Total Yield (Utility + On-chain)',
        'utility_yield': 'Utility Yield Only',
        'onchain_yield': 'On-chain Yield Only',
    }
    
    all_signals = {}
    
    for method, description in methods.items():
        print(f"\n{description}")
        print("-" * 60)
        
        # Calculate scores
        df_scored = calculate_factor_scores(df, method=method)
        print(f"Tokens with valid scores: {len(df_scored)}")
        
        # Generate signals
        df_signals = generate_signals(
            df_scored,
            long_threshold=80,  # Top 20%
            short_threshold=20,  # Bottom 20%
            min_tvl=1_000_000,
        )
        
        # Summary
        long_tokens = df_signals[df_signals['signal'] == 'long']
        short_tokens = df_signals[df_signals['signal'] == 'short']
        neutral_tokens = df_signals[df_signals['signal'] == 'neutral']
        
        print(f"  Long: {len(long_tokens)} tokens")
        print(f"  Short: {len(short_tokens)} tokens")
        print(f"  Neutral: {len(neutral_tokens)} tokens")
        
        if len(long_tokens) > 0:
            print(f"\n  Top 5 Long signals:")
            top_5 = long_tokens.nlargest(5, 'factor_score')[
                ['symbol', 'factor_score', 'utility_yield_pct', 'weighted_apy', 'total_tvl_all']
            ]
            for _, row in top_5.iterrows():
                print(f"    {row['symbol']:6s}: {row['factor_score']:6.2f}% "
                      f"(Util: {row['utility_yield_pct']:5.2f}%, "
                      f"Yield: {row['weighted_apy']:5.2f}%) "
                      f"TVL: ${row['total_tvl_all']:,.0f}")
        
        all_signals[method] = df_signals
    
    # Save signals
    date = datetime.now().strftime("%Y%m%d")
    output_dir = Path("/workspace/signals")
    
    for method, df_signals in all_signals.items():
        # Full signals
        filepath = output_dir / f"utility_yield_{method}_signals_full.csv"
        df_signals.to_csv(filepath, index=False)
        print(f"\n✓ Saved: {filepath}")
        
        # Current signals only (long/short)
        current = df_signals[df_signals['signal'] != 'neutral'].copy()
        filepath = output_dir / f"utility_yield_{method}_signals_current.csv"
        current.to_csv(filepath, index=False)
        print(f"✓ Saved: {filepath}")
    
    # Create combined signal (average across methods)
    print("\n" + "=" * 60)
    print("Combined Signal (Equal Weight Average)")
    print("=" * 60)
    
    combined = pd.DataFrame()
    for method, df_sig in all_signals.items():
        if combined.empty:
            combined = df_sig[['symbol']].copy()
        method_score = df_sig.set_index('symbol')['factor_score']
        combined = combined.merge(
            method_score.to_frame(name=f'score_{method}'),
            left_on='symbol',
            right_index=True,
            how='outer'
        )
    
    # Average scores
    score_cols = [c for c in combined.columns if c.startswith('score_')]
    combined['combined_score'] = combined[score_cols].mean(axis=1)
    combined['combined_rank'] = combined['combined_score'].rank(ascending=False, pct=True) * 100
    
    # Generate signals
    combined['signal'] = 'neutral'
    combined.loc[combined['combined_rank'] >= 80, 'signal'] = 'long'
    combined.loc[combined['combined_rank'] <= 20, 'signal'] = 'short'
    
    long_tokens = combined[combined['signal'] == 'long']
    short_tokens = combined[combined['signal'] == 'short']
    
    print(f"\nCombined signals:")
    print(f"  Long: {len(long_tokens)} tokens")
    print(f"  Short: {len(short_tokens)} tokens")
    
    if len(long_tokens) > 0:
        print(f"\n  Long tokens:")
        for symbol in sorted(long_tokens['symbol'].values):
            print(f"    {symbol}")
    
    # Save combined
    filepath = output_dir / f"utility_yield_combined_signals.csv"
    combined.to_csv(filepath, index=False)
    print(f"\n✓ Saved: {filepath}")
    
    print("\n" + "=" * 60)
    print("✅ Signal generation complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Backtest these signals with historical price data")
    print("  2. Combine with other factors (momentum, value, etc.)")
    print("  3. Implement in portfolio construction")


if __name__ == "__main__":
    main()
