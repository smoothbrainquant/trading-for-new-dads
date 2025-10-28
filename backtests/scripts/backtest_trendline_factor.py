#!/usr/bin/env python3
"""
Backtest for Trendline Factor Strategy

This script backtests a trendline factor strategy that:
1. Calculates rolling linear regression on closing prices
2. Extracts slope (trend direction/magnitude) and R² (trend quality)
3. Ranks cryptocurrencies by trendline score (slope × R²)
4. Creates long/short portfolios based on trendline rankings:
   - Long Uptrends, Short Downtrends: Long strong uptrends (high slope × R²), Short strong downtrends
   - Slope-Only: Pure momentum, ignore R²
   - R²-Filtered: Only trade clean trends (high R²)
5. Uses equal-weight or risk parity weighting within each bucket
6. Rebalances periodically (weekly by default)
7. Tracks portfolio performance over time

Trendline hypothesis: Tests whether coins with strong, clean trends (high slope × high R²)
outperform coins with weak or noisy trends.
"""

import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../signals'))


def load_data(filepath):
    """
    Load historical OHLCV data from CSV file.
    
    Args:
        filepath (str): Path to CSV file with OHLCV data
        
    Returns:
        pd.DataFrame: DataFrame with date, symbol, close, volume, market_cap
    """
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Keep only relevant columns
    required_cols = ['date', 'symbol', 'close']
    optional_cols = ['volume', 'market_cap', 'open', 'high', 'low']
    
    cols_to_keep = required_cols.copy()
    for col in optional_cols:
        if col in df.columns:
            cols_to_keep.append(col)
    
    df = df[cols_to_keep]
    return df


def calculate_rolling_trendline(data, window=30):
    """
    Calculate rolling linear regression on closing prices.
    
    Extracts:
    - Slope: Trend direction and magnitude (price change per day)
    - R²: Trend quality/cleanness (0 to 1)
    - p-value: Statistical significance of slope
    
    Args:
        data (pd.DataFrame): DataFrame with date, symbol, close columns
        window (int): Rolling window size for trendline calculation
        
    Returns:
        pd.DataFrame: DataFrame with slope, r_squared, p_value columns
    """
    df = data.copy()
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Calculate daily returns for volatility calculation
    df['daily_return'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    def fit_trendline(prices):
        """Fit linear regression to price window"""
        n = len(prices)
        
        # Remove NaN values
        valid_mask = ~np.isnan(prices.values)
        
        # Require at least 70% data availability
        min_periods = int(window * 0.7)
        if valid_mask.sum() < min_periods:
            return pd.Series({
                'slope': np.nan,
                'intercept': np.nan,
                'r_squared': np.nan,
                'p_value': np.nan,
                'std_err': np.nan
            })
        
        valid_prices = prices.values[valid_mask]
        valid_x = np.arange(len(valid_prices))
        
        try:
            # Fit linear regression using scipy
            slope, intercept, r_value, p_value, std_err = stats.linregress(valid_x, valid_prices)
            r_squared = r_value ** 2
            
            return pd.Series({
                'slope': slope,
                'intercept': intercept,
                'r_squared': r_squared,
                'p_value': p_value,
                'std_err': std_err
            })
        except Exception as e:
            return pd.Series({
                'slope': np.nan,
                'intercept': np.nan,
                'r_squared': np.nan,
                'p_value': np.nan,
                'std_err': np.nan
            })
    
    # Calculate rolling trendline metrics for each coin
    def calculate_for_group(group):
        """Calculate trendline metrics for a single coin"""
        trendline_results = []
        
        for i in range(len(group)):
            if i < window - 1:
                trendline_results.append({
                    'slope': np.nan,
                    'intercept': np.nan,
                    'r_squared': np.nan,
                    'p_value': np.nan,
                    'std_err': np.nan
                })
            else:
                # Get window of prices
                price_window = group['close'].iloc[i-window+1:i+1]
                result = fit_trendline(price_window)
                trendline_results.append(result.to_dict())
        
        return pd.DataFrame(trendline_results)
    
    # Apply to each symbol
    trendline_df = df.groupby('symbol', group_keys=False).apply(
        calculate_for_group
    ).reset_index(drop=True)
    
    # Merge back with original data
    for col in ['slope', 'intercept', 'r_squared', 'p_value', 'std_err']:
        df[col] = trendline_df[col].values
    
    return df


def calculate_normalized_slope(df):
    """
    Normalize slope by price level to make slopes comparable across coins.
    
    Returns annualized percentage slope.
    
    Args:
        df (pd.DataFrame): DataFrame with slope and close columns
        
    Returns:
        pd.DataFrame: DataFrame with norm_slope column added
    """
    df = df.copy()
    
    # Convert daily slope to percentage per day
    # slope is in price units per day, divide by price level to get percentage
    df['pct_slope_daily'] = (df['slope'] / df['close']) * 100
    
    # Annualize (multiply by 365)
    df['norm_slope'] = df['pct_slope_daily'] * 365
    
    # Cap extreme values
    df['norm_slope'] = df['norm_slope'].clip(-500, 500)
    
    return df


def calculate_trendline_score(df, method='multiplicative', r2_threshold=0.0):
    """
    Calculate composite trendline score from slope and R².
    
    Args:
        df (pd.DataFrame): DataFrame with norm_slope and r_squared columns
        method (str): Scoring method:
            - 'multiplicative': slope × R² (default)
            - 'slope_only': Just normalized slope
            - 'r2_only': Just R²
            - 'filtered': Slope if R² > threshold, else 0
        r2_threshold (float): Minimum R² for filtered method
        
    Returns:
        pd.DataFrame: DataFrame with trendline_score column added
    """
    df = df.copy()
    
    if method == 'multiplicative':
        # Slope × R² (prioritizes both strength and quality)
        df['trendline_score'] = df['norm_slope'] * df['r_squared']
        
    elif method == 'slope_only':
        # Pure momentum, ignore R²
        df['trendline_score'] = df['norm_slope']
        
    elif method == 'r2_only':
        # Pure quality, ignore direction
        df['trendline_score'] = df['r_squared']
        
    elif method == 'filtered':
        # Only use slope if R² is high enough (conservative)
        df['trendline_score'] = np.where(
            df['r_squared'] >= r2_threshold,
            df['norm_slope'],
            0.0
        )
        
    else:
        raise ValueError(f"Unknown method: {method}")
    
    return df


def calculate_volatility(data, window=30):
    """
    Calculate rolling volatility (annualized).
    
    Args:
        data (pd.DataFrame): DataFrame with daily_return column
        window (int): Rolling window size
        
    Returns:
        pd.DataFrame: DataFrame with volatility column
    """
    df = data.copy()
    
    # Calculate annualized volatility
    df['volatility'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=window, min_periods=int(window*0.7)).std() * np.sqrt(365)
    )
    
    return df


def filter_universe(data, min_volume=5_000_000, min_market_cap=50_000_000, 
                    min_r2=0.0, max_pvalue=1.0):
    """
    Filter cryptocurrency universe by liquidity, market cap, and trendline quality.
    
    Args:
        data (pd.DataFrame): DataFrame with volume, market_cap, r_squared, p_value columns
        min_volume (float): Minimum 30-day average daily volume
        min_market_cap (float): Minimum market cap
        min_r2 (float): Minimum R² threshold
        max_pvalue (float): Maximum p-value threshold
        
    Returns:
        pd.DataFrame: Filtered data
    """
    df = data.copy()
    
    # Calculate 30-day rolling average volume
    if 'volume' in df.columns:
        df['volume_30d_avg'] = df.groupby('symbol')['volume'].transform(
            lambda x: x.rolling(window=30, min_periods=20).mean()
        )
        df = df[df['volume_30d_avg'] >= min_volume]
    
    # Filter by market cap
    if 'market_cap' in df.columns:
        df = df[df['market_cap'] >= min_market_cap]
    
    # Filter by R² (optional)
    if min_r2 > 0:
        df = df[df['r_squared'] >= min_r2]
    
    # Filter by p-value (optional)
    if max_pvalue < 1.0:
        df = df[df['p_value'] <= max_pvalue]
    
    return df


def rank_by_trendline(data, date, num_quintiles=5):
    """
    Rank cryptocurrencies by trendline score on a specific date.
    
    Args:
        data (pd.DataFrame): DataFrame with trendline_score column
        date (pd.Timestamp): Date to rank on
        num_quintiles (int): Number of quintiles
        
    Returns:
        pd.DataFrame: DataFrame with quintile and rank information
    """
    # Get data for this specific date
    date_data = data[data['date'] == date].copy()
    
    if date_data.empty:
        return pd.DataFrame()
    
    # Remove NaN trendline scores
    date_data = date_data.dropna(subset=['trendline_score'])
    
    if len(date_data) < num_quintiles:
        return pd.DataFrame()
    
    # Rank by trendline score (ascending: low to high)
    # Low rank = negative score (downtrends)
    # High rank = positive score (uptrends)
    date_data['trendline_rank'] = date_data['trendline_score'].rank(method='first', ascending=True)
    date_data['percentile'] = date_data['trendline_rank'] / len(date_data) * 100
    
    # Assign quintiles
    try:
        date_data['quintile'] = pd.qcut(
            date_data['trendline_score'],
            q=num_quintiles,
            labels=range(1, num_quintiles + 1),
            duplicates='drop'
        )
    except ValueError:
        # If qcut fails, use rank-based approach
        date_data['quintile'] = pd.cut(
            date_data['trendline_rank'],
            bins=num_quintiles,
            labels=range(1, num_quintiles + 1)
        )
    
    return date_data


def select_symbols_by_trendline(data, date, strategy='long_uptrend_short_downtrend',
                                num_quintiles=5, long_percentile=80, short_percentile=20):
    """
    Select symbols based on trendline factor strategy.
    
    Args:
        data (pd.DataFrame): Data with trendline_score column
        date (pd.Timestamp): Date to select on
        strategy (str): Strategy type:
            - 'long_uptrend_short_downtrend': Long high scores, short low scores (default)
            - 'long_only_uptrends': Long high scores only
            - 'slope_only_momentum': Use slope only (ignore R²)
            - 'r2_only_quality': Rank by R² only
        num_quintiles (int): Number of quintiles
        long_percentile (int): Percentile threshold for long positions
        short_percentile (int): Percentile threshold for short positions
        
    Returns:
        dict: Dictionary with 'long' and 'short' DataFrames
    """
    # Rank by trendline score
    ranked_df = rank_by_trendline(data, date, num_quintiles)
    
    if ranked_df.empty:
        return {'long': pd.DataFrame(), 'short': pd.DataFrame()}
    
    if strategy == 'long_uptrend_short_downtrend':
        # Long highest scores (strong uptrends), short lowest scores (strong downtrends)
        long_df = ranked_df[ranked_df['percentile'] >= long_percentile]
        short_df = ranked_df[ranked_df['percentile'] <= short_percentile]
        
    elif strategy == 'long_only_uptrends':
        # Long only high scores
        long_df = ranked_df[ranked_df['percentile'] >= long_percentile]
        short_df = pd.DataFrame()
        
    elif strategy == 'slope_only_momentum':
        # Same as default (score already set to slope_only in preprocessing)
        long_df = ranked_df[ranked_df['percentile'] >= long_percentile]
        short_df = ranked_df[ranked_df['percentile'] <= short_percentile]
        
    elif strategy == 'r2_only_quality':
        # Same as default (score already set to r2_only in preprocessing)
        long_df = ranked_df[ranked_df['percentile'] >= long_percentile]
        short_df = ranked_df[ranked_df['percentile'] <= short_percentile]
        
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
    
    return {'long': long_df, 'short': short_df}


def calculate_position_weights(positions_df, weighting_method='equal_weight', total_allocation=0.5):
    """
    Calculate position weights for a bucket of positions.
    
    Args:
        positions_df (pd.DataFrame): DataFrame with positions
        weighting_method (str): Weighting method:
            - 'equal_weight': Equal allocation
            - 'risk_parity': Inverse volatility weighting
            - 'score_weighted': Weight by absolute trendline score
            - 'r2_weighted': Weight by R²
        total_allocation (float): Total allocation to this bucket (e.g., 0.5 = 50%)
        
    Returns:
        pd.DataFrame: DataFrame with weights column added
    """
    df = positions_df.copy()
    
    if df.empty:
        return df
    
    if weighting_method == 'equal_weight':
        # Equal weight across all positions
        df['weight'] = total_allocation / len(df)
        
    elif weighting_method == 'risk_parity':
        # Weight inversely proportional to volatility
        if 'volatility' not in df.columns or df['volatility'].isna().all():
            # Fall back to equal weight if no volatility data
            df['weight'] = total_allocation / len(df)
        else:
            # Handle missing volatility
            df['volatility_clean'] = df['volatility'].fillna(df['volatility'].median())
            
            # Inverse volatility weights
            df['inv_vol'] = 1 / df['volatility_clean']
            df['weight'] = (df['inv_vol'] / df['inv_vol'].sum()) * total_allocation
            
    elif weighting_method == 'score_weighted':
        # Weight proportional to absolute trendline score
        if 'trendline_score' not in df.columns or df['trendline_score'].isna().all():
            df['weight'] = total_allocation / len(df)
        else:
            abs_score = df['trendline_score'].abs()
            df['weight'] = (abs_score / abs_score.sum()) * total_allocation
            
    elif weighting_method == 'r2_weighted':
        # Weight proportional to R²
        if 'r_squared' not in df.columns or df['r_squared'].isna().all():
            df['weight'] = total_allocation / len(df)
        else:
            df['weight'] = (df['r_squared'] / df['r_squared'].sum()) * total_allocation
    
    else:
        raise ValueError(f"Unknown weighting method: {weighting_method}")
    
    return df


def run_backtest(data, strategy='long_uptrend_short_downtrend', trendline_window=30,
                score_method='multiplicative', r2_threshold=0.0, pvalue_threshold=1.0,
                volatility_window=30, rebalance_days=7, num_quintiles=5,
                long_percentile=80, short_percentile=20,
                weighting_method='equal_weight', initial_capital=10000,
                leverage=1.0, long_allocation=0.5, short_allocation=0.5,
                min_volume=5_000_000, min_market_cap=50_000_000,
                start_date=None, end_date=None):
    """
    Run the trendline factor backtest.
    
    Args:
        data (pd.DataFrame): Historical OHLCV data
        strategy (str): Strategy type
        trendline_window (int): Trendline calculation window
        score_method (str): Trendline scoring method
        r2_threshold (float): Minimum R² for filtering
        pvalue_threshold (float): Maximum p-value for filtering
        volatility_window (int): Volatility calculation window for risk parity
        rebalance_days (int): Rebalance frequency in days
        num_quintiles (int): Number of quintiles
        long_percentile (int): Percentile threshold for longs
        short_percentile (int): Percentile threshold for shorts
        weighting_method (str): Position weighting method
        initial_capital (float): Starting capital
        leverage (float): Leverage multiplier
        long_allocation (float): Allocation to long side
        short_allocation (float): Allocation to short side
        min_volume (float): Minimum volume filter
        min_market_cap (float): Minimum market cap filter
        start_date (str): Backtest start date
        end_date (str): Backtest end date
        
    Returns:
        dict: Dictionary with portfolio_values, trades, metrics, and strategy_info
    """
    print("=" * 80)
    print("TRENDLINE FACTOR BACKTEST")
    print("=" * 80)
    print(f"\nStrategy: {strategy}")
    print(f"Trendline Window: {trendline_window} days")
    print(f"Score Method: {score_method}")
    print(f"R² Threshold: {r2_threshold}")
    print(f"P-Value Threshold: {pvalue_threshold}")
    print(f"Volatility Window: {volatility_window} days")
    print(f"Rebalance Frequency: {rebalance_days} days")
    print(f"Weighting Method: {weighting_method}")
    print(f"Long Allocation: {long_allocation*100:.1f}%")
    print(f"Short Allocation: {short_allocation*100:.1f}%")
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print(f"Leverage: {leverage}x")
    print(f"Min Volume: ${min_volume:,.0f}")
    print(f"Min Market Cap: ${min_market_cap:,.0f}")
    
    # Step 1: Calculate trendline metrics
    print("\n" + "-" * 80)
    print("Step 1: Calculating rolling trendline (linear regression)...")
    trendline_data = calculate_rolling_trendline(data, window=trendline_window)
    print(f"  Total data points with trendline: {trendline_data['slope'].notna().sum()}")
    print(f"  Slope range: [{trendline_data['slope'].min():.4f}, {trendline_data['slope'].max():.4f}]")
    print(f"  R² range: [{trendline_data['r_squared'].min():.4f}, {trendline_data['r_squared'].max():.4f}]")
    print(f"  R² mean: {trendline_data['r_squared'].mean():.4f}")
    print(f"  R² median: {trendline_data['r_squared'].median():.4f}")
    
    # Step 2: Normalize slope
    print("\n" + "-" * 80)
    print("Step 2: Normalizing slope by price level...")
    trendline_data = calculate_normalized_slope(trendline_data)
    print(f"  Normalized slope range: [{trendline_data['norm_slope'].min():.2f}%, {trendline_data['norm_slope'].max():.2f}%]")
    print(f"  Normalized slope mean: {trendline_data['norm_slope'].mean():.2f}%")
    
    # Step 3: Calculate trendline score
    print("\n" + "-" * 80)
    print("Step 3: Calculating trendline score...")
    trendline_data = calculate_trendline_score(trendline_data, method=score_method, r2_threshold=r2_threshold)
    print(f"  Trendline score range: [{trendline_data['trendline_score'].min():.2f}, {trendline_data['trendline_score'].max():.2f}]")
    print(f"  Trendline score mean: {trendline_data['trendline_score'].mean():.2f}")
    
    # Step 4: Calculate volatility (for risk parity weighting)
    print("\n" + "-" * 80)
    print("Step 4: Calculating volatility...")
    trendline_data = calculate_volatility(trendline_data, window=volatility_window)
    
    # Step 5: Filter universe
    print("\n" + "-" * 80)
    print("Step 5: Filtering universe...")
    print(f"  Coins before filtering: {trendline_data['symbol'].nunique()}")
    trendline_data = filter_universe(
        trendline_data, 
        min_volume=min_volume, 
        min_market_cap=min_market_cap,
        min_r2=r2_threshold if score_method == 'filtered' else 0.0,
        max_pvalue=pvalue_threshold
    )
    print(f"  Coins after filtering: {trendline_data['symbol'].nunique()}")
    
    # Step 6: Filter by date range
    if start_date:
        trendline_data = trendline_data[trendline_data['date'] >= pd.to_datetime(start_date)]
    if end_date:
        trendline_data = trendline_data[trendline_data['date'] <= pd.to_datetime(end_date)]
    
    # Step 7: Run backtest
    print("\n" + "-" * 80)
    print("Step 6: Running backtest...")
    
    # Get trading dates
    trading_dates = sorted(trendline_data['date'].unique())
    
    if len(trading_dates) < trendline_window + rebalance_days:
        raise ValueError(f"Insufficient data. Need at least {trendline_window + rebalance_days} days.")
    
    # Start after warmup period
    start_idx = trendline_window
    trading_dates = trading_dates[start_idx:]
    
    print(f"  Trading period: {trading_dates[0].date()} to {trading_dates[-1].date()}")
    print(f"  Total trading days: {len(trading_dates)}")
    
    # Initialize portfolio tracking
    portfolio_values = []
    trades = []
    current_positions = {}  # {symbol: weight}
    portfolio_value = initial_capital * leverage
    cash = 0  # Market neutral, fully invested
    
    # Rebalancing loop
    rebalance_dates = trading_dates[::rebalance_days]
    print(f"  Number of rebalances: {len(rebalance_dates)}")
    
    for date_idx, current_date in enumerate(trading_dates):
        # Check if rebalance day
        if current_date in rebalance_dates:
            # Select positions based on trendline score
            selected = select_symbols_by_trendline(
                trendline_data, current_date, strategy=strategy,
                num_quintiles=num_quintiles,
                long_percentile=long_percentile,
                short_percentile=short_percentile
            )
            
            # Calculate weights
            long_positions = calculate_position_weights(
                selected['long'], weighting_method, long_allocation
            )
            short_positions = calculate_position_weights(
                selected['short'], weighting_method, short_allocation
            )
            
            # Record trades
            for _, row in long_positions.iterrows():
                trades.append({
                    'date': current_date,
                    'symbol': row['symbol'],
                    'signal': 'LONG',
                    'slope': row.get('slope', np.nan),
                    'norm_slope': row.get('norm_slope', np.nan),
                    'r_squared': row.get('r_squared', np.nan),
                    'trendline_score': row.get('trendline_score', np.nan),
                    'trendline_rank': row.get('trendline_rank', np.nan),
                    'percentile': row.get('percentile', np.nan),
                    'weight': row['weight'],
                    'price': row.get('close', np.nan),
                    'volatility': row.get('volatility', np.nan),
                    'market_cap': row.get('market_cap', np.nan),
                    'volume_30d_avg': row.get('volume_30d_avg', np.nan),
                    'p_value': row.get('p_value', np.nan)
                })
            
            for _, row in short_positions.iterrows():
                trades.append({
                    'date': current_date,
                    'symbol': row['symbol'],
                    'signal': 'SHORT',
                    'slope': row.get('slope', np.nan),
                    'norm_slope': row.get('norm_slope', np.nan),
                    'r_squared': row.get('r_squared', np.nan),
                    'trendline_score': row.get('trendline_score', np.nan),
                    'trendline_rank': row.get('trendline_rank', np.nan),
                    'percentile': row.get('percentile', np.nan),
                    'weight': -row['weight'],  # Negative for short
                    'price': row.get('close', np.nan),
                    'volatility': row.get('volatility', np.nan),
                    'market_cap': row.get('market_cap', np.nan),
                    'volume_30d_avg': row.get('volume_30d_avg', np.nan),
                    'p_value': row.get('p_value', np.nan)
                })
            
            # Update current positions
            current_positions = {}
            for _, row in long_positions.iterrows():
                current_positions[row['symbol']] = row['weight']
            for _, row in short_positions.iterrows():
                current_positions[row['symbol']] = -row['weight']
        
        # Calculate daily P&L using next day's returns (avoid lookahead bias)
        if date_idx < len(trading_dates) - 1:
            next_date = trading_dates[date_idx + 1]
            
            # Get returns for next day
            next_day_data = trendline_data[trendline_data['date'] == next_date]
            
            daily_pnl = 0
            for symbol, weight in current_positions.items():
                symbol_data = next_day_data[next_day_data['symbol'] == symbol]
                if not symbol_data.empty:
                    daily_return = symbol_data.iloc[0]['daily_return']
                    if not np.isnan(daily_return):
                        daily_pnl += weight * daily_return
            
            # Update portfolio value
            portfolio_value = portfolio_value * (1 + daily_pnl)
        
        # Calculate exposures
        long_exposure = sum([w for w in current_positions.values() if w > 0])
        short_exposure = sum([w for w in current_positions.values() if w < 0])
        net_exposure = long_exposure + short_exposure
        gross_exposure = long_exposure + abs(short_exposure)
        
        # Calculate average trendline metrics for portfolio
        avg_score_long = 0
        avg_score_short = 0
        avg_r2_long = 0
        avg_r2_short = 0
        num_longs = 0
        num_shorts = 0
        
        for symbol, weight in current_positions.items():
            symbol_data = trendline_data[(trendline_data['date'] == current_date) & 
                                        (trendline_data['symbol'] == symbol)]
            if not symbol_data.empty:
                score = symbol_data.iloc[0].get('trendline_score', np.nan)
                r2 = symbol_data.iloc[0].get('r_squared', np.nan)
                
                if weight > 0:  # Long
                    if not np.isnan(score):
                        avg_score_long += score
                    if not np.isnan(r2):
                        avg_r2_long += r2
                    num_longs += 1
                else:  # Short
                    if not np.isnan(score):
                        avg_score_short += score
                    if not np.isnan(r2):
                        avg_r2_short += r2
                    num_shorts += 1
        
        # Calculate averages
        avg_score_long = avg_score_long / num_longs if num_longs > 0 else np.nan
        avg_score_short = avg_score_short / num_shorts if num_shorts > 0 else np.nan
        avg_r2_long = avg_r2_long / num_longs if num_longs > 0 else np.nan
        avg_r2_short = avg_r2_short / num_shorts if num_shorts > 0 else np.nan
        
        # Record portfolio value
        portfolio_values.append({
            'date': current_date,
            'portfolio_value': portfolio_value,
            'cash': cash,
            'long_exposure': long_exposure * portfolio_value,
            'short_exposure': short_exposure * portfolio_value,
            'net_exposure': net_exposure * portfolio_value,
            'gross_exposure': gross_exposure * portfolio_value,
            'num_longs': num_longs,
            'num_shorts': num_shorts,
            'avg_trendline_score_long': avg_score_long,
            'avg_trendline_score_short': avg_score_short,
            'avg_r2_long': avg_r2_long,
            'avg_r2_short': avg_r2_short
        })
    
    # Convert to DataFrames
    portfolio_df = pd.DataFrame(portfolio_values)
    trades_df = pd.DataFrame(trades)
    
    # Calculate metrics
    print("\n" + "-" * 80)
    print("Step 7: Calculating performance metrics...")
    metrics = calculate_metrics(portfolio_df, initial_capital, leverage)
    
    # Calculate strategy info
    strategy_info = {
        'strategy': strategy,
        'trendline_window': trendline_window,
        'score_method': score_method,
        'r2_threshold': r2_threshold,
        'pvalue_threshold': pvalue_threshold,
        'volatility_window': volatility_window,
        'rebalance_days': rebalance_days,
        'num_quintiles': num_quintiles,
        'long_percentile': long_percentile,
        'short_percentile': short_percentile,
        'weighting_method': weighting_method,
        'initial_capital': initial_capital,
        'leverage': leverage,
        'long_allocation': long_allocation,
        'short_allocation': short_allocation,
        'avg_trendline_score_long': trades_df[trades_df['signal'] == 'LONG']['trendline_score'].mean() if not trades_df.empty else np.nan,
        'avg_trendline_score_short': trades_df[trades_df['signal'] == 'SHORT']['trendline_score'].mean() if not trades_df.empty else np.nan,
        'avg_r2_long': trades_df[trades_df['signal'] == 'LONG']['r_squared'].mean() if not trades_df.empty else np.nan,
        'avg_r2_short': trades_df[trades_df['signal'] == 'SHORT']['r_squared'].mean() if not trades_df.empty else np.nan,
        'long_symbols': ','.join(sorted(trades_df[trades_df['signal'] == 'LONG']['symbol'].unique())) if not trades_df.empty else '',
        'short_symbols': ','.join(sorted(trades_df[trades_df['signal'] == 'SHORT']['symbol'].unique())) if not trades_df.empty else ''
    }
    
    return {
        'portfolio_values': portfolio_df,
        'trades': trades_df,
        'metrics': metrics,
        'strategy_info': strategy_info
    }


def calculate_metrics(portfolio_df, initial_capital, leverage):
    """
    Calculate performance metrics from portfolio values.
    
    Args:
        portfolio_df (pd.DataFrame): Portfolio values over time
        initial_capital (float): Starting capital
        leverage (float): Leverage multiplier
        
    Returns:
        dict: Dictionary of performance metrics
    """
    if portfolio_df.empty:
        return {}
    
    # Calculate returns
    portfolio_df['daily_return'] = portfolio_df['portfolio_value'].pct_change()
    
    # Total return
    final_value = portfolio_df['portfolio_value'].iloc[-1]
    initial_value = initial_capital * leverage
    total_return = (final_value - initial_value) / initial_value
    
    # Annualized return
    num_days = len(portfolio_df)
    annualized_return = (1 + total_return) ** (365 / num_days) - 1
    
    # Volatility
    annualized_volatility = portfolio_df['daily_return'].std() * np.sqrt(365)
    
    # Sharpe ratio (assuming 0% risk-free rate)
    sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility > 0 else 0
    
    # Sortino ratio (downside deviation)
    downside_returns = portfolio_df['daily_return'][portfolio_df['daily_return'] < 0]
    downside_volatility = downside_returns.std() * np.sqrt(365) if len(downside_returns) > 0 else 0
    sortino_ratio = annualized_return / downside_volatility if downside_volatility > 0 else 0
    
    # Maximum drawdown
    cumulative_returns = (1 + portfolio_df['daily_return']).cumprod()
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # Calmar ratio
    calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
    
    # Win rate
    win_rate = (portfolio_df['daily_return'] > 0).sum() / len(portfolio_df)
    
    # Average exposures
    avg_long_exposure = portfolio_df['long_exposure'].mean()
    avg_short_exposure = portfolio_df['short_exposure'].mean()
    avg_net_exposure = portfolio_df['net_exposure'].mean()
    avg_gross_exposure = portfolio_df['gross_exposure'].mean()
    
    # Average positions
    avg_long_positions = portfolio_df['num_longs'].mean()
    avg_short_positions = portfolio_df['num_shorts'].mean()
    
    # Average trendline metrics
    avg_score_long = portfolio_df['avg_trendline_score_long'].mean()
    avg_score_short = portfolio_df['avg_trendline_score_short'].mean()
    avg_r2_long = portfolio_df['avg_r2_long'].mean()
    avg_r2_short = portfolio_df['avg_r2_short'].mean()
    
    metrics = {
        'initial_capital': initial_capital,
        'leverage': leverage,
        'final_value': final_value,
        'total_return': total_return,
        'annualized_return': annualized_return,
        'annualized_volatility': annualized_volatility,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'max_drawdown': max_drawdown,
        'calmar_ratio': calmar_ratio,
        'win_rate': win_rate,
        'trading_days': num_days,
        'avg_long_exposure': avg_long_exposure,
        'avg_short_exposure': avg_short_exposure,
        'avg_net_exposure': avg_net_exposure,
        'avg_gross_exposure': avg_gross_exposure,
        'avg_long_positions': avg_long_positions,
        'avg_short_positions': avg_short_positions,
        'avg_trendline_score_long': avg_score_long,
        'avg_trendline_score_short': avg_score_short,
        'avg_r2_long': avg_r2_long,
        'avg_r2_short': avg_r2_short,
    }
    
    return metrics


def print_results(results):
    """
    Print backtest results in a formatted way.
    
    Args:
        results (dict): Backtest results dictionary
    """
    metrics = results['metrics']
    strategy_info = results['strategy_info']
    
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)
    
    print("\nStrategy Configuration:")
    print(f"  Strategy:               {strategy_info['strategy']}")
    print(f"  Trendline Window:       {strategy_info['trendline_window']} days")
    print(f"  Score Method:           {strategy_info['score_method']}")
    print(f"  R² Threshold:           {strategy_info['r2_threshold']}")
    print(f"  Rebalance Frequency:    {strategy_info['rebalance_days']} days")
    print(f"  Weighting Method:       {strategy_info['weighting_method']}")
    print(f"  Long Allocation:        {strategy_info['long_allocation']*100:.1f}%")
    print(f"  Short Allocation:       {strategy_info['short_allocation']*100:.1f}%")
    
    print("\nPortfolio Performance:")
    print(f"  Initial Capital:        $ {metrics['initial_capital']:>12,.2f}")
    print(f"  Final Value:            $ {metrics['final_value']:>12,.2f}")
    print(f"  Total Return:           {metrics['total_return']:>14.2%}")
    print(f"  Annualized Return:      {metrics['annualized_return']:>14.2%}")
    
    print("\nRisk Metrics:")
    print(f"  Annualized Volatility:  {metrics['annualized_volatility']:>14.2%}")
    print(f"  Sharpe Ratio:           {metrics['sharpe_ratio']:>14.2f}")
    print(f"  Sortino Ratio:          {metrics['sortino_ratio']:>14.2f}")
    print(f"  Maximum Drawdown:       {metrics['max_drawdown']:>14.2%}")
    print(f"  Calmar Ratio:           {metrics['calmar_ratio']:>14.2f}")
    
    print("\nTrading Statistics:")
    print(f"  Win Rate:               {metrics['win_rate']:>14.2%}")
    print(f"  Trading Days:           {metrics['trading_days']:>14.0f}")
    print(f"  Avg Long Positions:     {metrics['avg_long_positions']:>14.1f}")
    print(f"  Avg Short Positions:    {metrics['avg_short_positions']:>14.1f}")
    
    print("\nExposure Metrics:")
    print(f"  Avg Long Exposure:      $ {metrics['avg_long_exposure']:>12,.2f}")
    print(f"  Avg Short Exposure:     $ {metrics['avg_short_exposure']:>12,.2f}")
    print(f"  Avg Net Exposure:       $ {metrics['avg_net_exposure']:>12,.2f}")
    print(f"  Avg Gross Exposure:     $ {metrics['avg_gross_exposure']:>12,.2f}")
    
    print("\nTrendline Analysis:")
    print(f"  Avg Long Score:         {strategy_info['avg_trendline_score_long']:>14.2f}")
    print(f"  Avg Short Score:        {strategy_info['avg_trendline_score_short']:>14.2f}")
    print(f"  Avg Long R²:            {strategy_info['avg_r2_long']:>14.4f}")
    print(f"  Avg Short R²:           {strategy_info['avg_r2_short']:>14.4f}")
    
    print("\n" + "=" * 80)


def save_results(results, output_prefix):
    """
    Save backtest results to CSV files.
    
    Args:
        results (dict): Backtest results dictionary
        output_prefix (str): Prefix for output files
    """
    output_dir = os.path.dirname(output_prefix) or '.'
    os.makedirs(output_dir, exist_ok=True)
    
    # Save portfolio values
    portfolio_file = f"{output_prefix}_portfolio_values.csv"
    results['portfolio_values'].to_csv(portfolio_file, index=False)
    print(f"\n✓ Saved portfolio values to: {portfolio_file}")
    
    # Save trades
    trades_file = f"{output_prefix}_trades.csv"
    results['trades'].to_csv(trades_file, index=False)
    print(f"✓ Saved trades to: {trades_file}")
    
    # Save metrics
    metrics_file = f"{output_prefix}_metrics.csv"
    metrics_df = pd.DataFrame([results['metrics']]).T
    metrics_df.columns = ['value']
    metrics_df.to_csv(metrics_file)
    print(f"✓ Saved metrics to: {metrics_file}")
    
    # Save strategy info
    strategy_file = f"{output_prefix}_strategy_info.csv"
    strategy_df = pd.DataFrame([results['strategy_info']])
    strategy_df.to_csv(strategy_file, index=False)
    print(f"✓ Saved strategy info to: {strategy_file}")


def main():
    """Main function to run trendline factor backtest."""
    parser = argparse.ArgumentParser(description='Backtest trendline factor strategy')
    
    # Data parameters
    parser.add_argument('--price-data', type=str,
                       default='data/raw/combined_coinbase_coinmarketcap_daily.csv',
                       help='Path to historical OHLCV CSV file')
    
    # Strategy parameters
    parser.add_argument('--strategy', type=str, default='long_uptrend_short_downtrend',
                       choices=['long_uptrend_short_downtrend', 'long_only_uptrends',
                               'slope_only_momentum', 'r2_only_quality'],
                       help='Strategy variant')
    
    # Trendline calculation parameters
    parser.add_argument('--trendline-window', type=int, default=30,
                       help='Trendline calculation window in days')
    parser.add_argument('--score-method', type=str, default='multiplicative',
                       choices=['multiplicative', 'slope_only', 'r2_only', 'filtered'],
                       help='Trendline scoring method')
    parser.add_argument('--r2-threshold', type=float, default=0.0,
                       help='Minimum R² for filtering (0.0 = no filter)')
    parser.add_argument('--pvalue-threshold', type=float, default=1.0,
                       help='Maximum p-value for filtering (1.0 = no filter)')
    parser.add_argument('--volatility-window', type=int, default=30,
                       help='Volatility calculation window in days')
    
    # Portfolio construction parameters
    parser.add_argument('--rebalance-days', type=int, default=7,
                       help='Rebalance frequency in days')
    parser.add_argument('--num-quintiles', type=int, default=5,
                       help='Number of trendline quintiles')
    parser.add_argument('--long-percentile', type=int, default=80,
                       help='Percentile threshold for long positions')
    parser.add_argument('--short-percentile', type=int, default=20,
                       help='Percentile threshold for short positions')
    parser.add_argument('--weighting-method', type=str, default='equal_weight',
                       choices=['equal_weight', 'risk_parity', 'score_weighted', 'r2_weighted'],
                       help='Position weighting method')
    
    # Capital and leverage
    parser.add_argument('--initial-capital', type=float, default=10000,
                       help='Initial capital in USD')
    parser.add_argument('--leverage', type=float, default=1.0,
                       help='Leverage multiplier')
    parser.add_argument('--long-allocation', type=float, default=0.5,
                       help='Allocation to long side (0-1)')
    parser.add_argument('--short-allocation', type=float, default=0.5,
                       help='Allocation to short side (0-1)')
    
    # Universe filters
    parser.add_argument('--min-volume', type=float, default=5_000_000,
                       help='Minimum 30-day average volume in USD')
    parser.add_argument('--min-market-cap', type=float, default=50_000_000,
                       help='Minimum market cap in USD')
    
    # Date range
    parser.add_argument('--start-date', type=str, default=None,
                       help='Backtest start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default=None,
                       help='Backtest end date (YYYY-MM-DD)')
    
    # Output
    parser.add_argument('--output-prefix', type=str,
                       default='backtests/results/backtest_trendline_factor',
                       help='Prefix for output files')
    
    args = parser.parse_args()
    
    # Load data
    print(f"\nLoading data from: {args.price_data}")
    data = load_data(args.price_data)
    print(f"Loaded {len(data)} data points for {data['symbol'].nunique()} symbols")
    print(f"Date range: {data['date'].min().date()} to {data['date'].max().date()}")
    
    # Run backtest
    results = run_backtest(
        data=data,
        strategy=args.strategy,
        trendline_window=args.trendline_window,
        score_method=args.score_method,
        r2_threshold=args.r2_threshold,
        pvalue_threshold=args.pvalue_threshold,
        volatility_window=args.volatility_window,
        rebalance_days=args.rebalance_days,
        num_quintiles=args.num_quintiles,
        long_percentile=args.long_percentile,
        short_percentile=args.short_percentile,
        weighting_method=args.weighting_method,
        initial_capital=args.initial_capital,
        leverage=args.leverage,
        long_allocation=args.long_allocation,
        short_allocation=args.short_allocation,
        min_volume=args.min_volume,
        min_market_cap=args.min_market_cap,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    # Print results
    print_results(results)
    
    # Save results
    save_results(results, args.output_prefix)
    
    print("\n" + "=" * 80)
    print("BACKTEST COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
