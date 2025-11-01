#!/usr/bin/env python3
"""
Backtest for Hurst Exponent Factor Strategy

This script backtests a Hurst exponent factor strategy that:
1. Calculates rolling Hurst exponent for all cryptocurrencies
2. Ranks cryptocurrencies by Hurst values (mean-reverting vs trending)
3. Creates long/short portfolios based on Hurst rankings:
   - Long Mean-Reverting: Long low Hurst (H < 0.5), Short high Hurst (H > 0.5)
   - Long Trending: Long high Hurst (H > 0.5), Short low Hurst (H < 0.5)
4. Uses equal-weight or risk parity weighting within each bucket
5. Rebalances periodically (weekly by default)
6. Tracks portfolio performance over time

Hurst hypothesis: Tests whether mean-reverting coins (low H) outperform 
trending coins (high H) or vice versa.
"""

import pandas as pd
import numpy as np
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


def calculate_hurst_rs(returns, min_points=20):
    """
    Calculate Hurst exponent using R/S (Rescaled Range) method.
    
    The Hurst exponent measures long-term memory in time series:
    - H < 0.5: Mean-reverting (anti-persistent)
    - H = 0.5: Random walk (no memory)
    - H > 0.5: Trending (persistent)
    
    Args:
        returns (np.array): Array of log returns
        min_points (int): Minimum points required for calculation
        
    Returns:
        float: Hurst exponent estimate (or np.nan if insufficient data)
    """
    # Remove NaN values
    returns = returns[~np.isnan(returns)]
    
    if len(returns) < min_points:
        return np.nan
    
    # Use geometric spacing for lags
    n = len(returns)
    max_lag = n // 2
    
    if max_lag < 4:
        return np.nan
    
    # Create lag array with geometric spacing
    lags = np.unique(np.logspace(0.5, np.log10(max_lag), min(20, max_lag)).astype(int))
    lags = lags[lags >= 2]
    
    if len(lags) < 3:
        return np.nan
    
    # Calculate R/S for each lag
    rs_values = []
    valid_lags = []
    
    for lag in lags:
        # Split returns into chunks of size 'lag'
        n_chunks = len(returns) // lag
        
        if n_chunks < 1:
            continue
        
        rs_list = []
        for i in range(n_chunks):
            chunk = returns[i*lag:(i+1)*lag]
            
            if len(chunk) < lag:
                continue
            
            # Calculate mean
            mean = np.mean(chunk)
            
            # Calculate cumulative deviations from mean
            deviations = chunk - mean
            cumdev = np.cumsum(deviations)
            
            # Calculate range R
            R = np.max(cumdev) - np.min(cumdev)
            
            # Calculate standard deviation S
            S = np.std(chunk, ddof=1)
            
            # Calculate R/S for this chunk (avoid division by zero)
            if S > 1e-10 and R > 0:
                rs_list.append(R / S)
        
        if len(rs_list) > 0:
            rs_values.append(np.mean(rs_list))
            valid_lags.append(lag)
    
    # Need at least 3 points to fit a line
    if len(rs_values) < 3:
        return np.nan
    
    # Fit log(R/S) vs log(lag) to get Hurst exponent
    # H is the slope of this relationship
    try:
        log_lags = np.log(valid_lags)
        log_rs = np.log(rs_values)
        
        # Filter out any inf or nan values
        mask = np.isfinite(log_lags) & np.isfinite(log_rs)
        if np.sum(mask) < 3:
            return np.nan
        
        log_lags = log_lags[mask]
        log_rs = log_rs[mask]
        
        # Linear regression: log(R/S) = H * log(lag) + const
        hurst = np.polyfit(log_lags, log_rs, 1)[0]
        
        # Bound Hurst between 0 and 1 (theoretical bounds)
        if hurst < 0 or hurst > 1:
            return np.nan
        
        return hurst
        
    except (np.linalg.LinAlgError, ValueError):
        return np.nan


def calculate_rolling_hurst(data, window=90, min_periods=60):
    """
    Calculate rolling Hurst exponent for each cryptocurrency.
    
    Args:
        data (pd.DataFrame): DataFrame with date, symbol, close columns
        window (int): Rolling window size for Hurst calculation
        min_periods (int): Minimum periods required (default 70% of window)
        
    Returns:
        pd.DataFrame: DataFrame with hurst column added
    """
    df = data.copy()
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Calculate daily log returns for all coins
    df['daily_return'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Calculate rolling Hurst exponent
    def rolling_hurst_series(returns_series):
        """Calculate rolling Hurst for a single coin's returns"""
        hurst_values = []
        
        for i in range(len(returns_series)):
            if i < min_periods:
                hurst_values.append(np.nan)
            else:
                # Get window of returns
                start_idx = max(0, i - window + 1)
                window_returns = returns_series.iloc[start_idx:i+1].values
                
                # Calculate Hurst
                hurst = calculate_hurst_rs(window_returns, min_points=min_periods)
                hurst_values.append(hurst)
        
        return pd.Series(hurst_values, index=returns_series.index)
    
    print("  Calculating rolling Hurst exponents (this may take a while)...")
    df['hurst'] = df.groupby('symbol', group_keys=False)['daily_return'].apply(
        rolling_hurst_series
    )
    
    # Calculate additional statistics for analysis
    df['returns_mean_90d'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=window, min_periods=min_periods).mean()
    )
    
    df['returns_std_90d'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=window, min_periods=min_periods).std()
    )
    
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


def filter_universe(data, min_volume=5_000_000, min_market_cap=50_000_000):
    """
    Filter cryptocurrency universe by liquidity and market cap.
    
    Args:
        data (pd.DataFrame): DataFrame with volume and market_cap columns
        min_volume (float): Minimum 30-day average daily volume
        min_market_cap (float): Minimum market cap
        
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
    
    return df


def rank_by_hurst(data, date, num_quintiles=5):
    """
    Rank cryptocurrencies by Hurst exponent on a specific date.
    
    Args:
        data (pd.DataFrame): DataFrame with hurst column
        date (pd.Timestamp): Date to rank on
        num_quintiles (int): Number of quintiles
        
    Returns:
        pd.DataFrame: DataFrame with quintile and rank information
    """
    # Get data for this specific date
    date_data = data[data['date'] == date].copy()
    
    if date_data.empty:
        return pd.DataFrame()
    
    # Remove NaN Hurst values and invalid values
    date_data = date_data.dropna(subset=['hurst'])
    date_data = date_data[(date_data['hurst'] >= 0) & (date_data['hurst'] <= 1)]
    
    if len(date_data) < num_quintiles:
        return pd.DataFrame()
    
    # Rank by Hurst (ascending: low to high)
    date_data['hurst_rank'] = date_data['hurst'].rank(method='first', ascending=True)
    date_data['percentile'] = date_data['hurst_rank'] / len(date_data) * 100
    
    # Assign quintiles (1 = lowest Hurst, num_quintiles = highest Hurst)
    try:
        date_data['quintile'] = pd.qcut(
            date_data['hurst'],
            q=num_quintiles,
            labels=range(1, num_quintiles + 1),
            duplicates='drop'
        )
    except ValueError:
        # If qcut fails, use rank-based approach
        date_data['quintile'] = pd.cut(
            date_data['hurst_rank'],
            bins=num_quintiles,
            labels=range(1, num_quintiles + 1)
        )
    
    return date_data


def select_symbols_by_hurst(data, date, strategy='long_mean_reverting', 
                            num_quintiles=5, long_percentile=20, short_percentile=80):
    """
    Select symbols based on Hurst exponent factor strategy.
    
    Args:
        data (pd.DataFrame): Data with hurst column
        date (pd.Timestamp): Date to select on
        strategy (str): Strategy type:
            - 'long_mean_reverting': Long low Hurst (mean-reverting), short high Hurst (trending)
            - 'long_trending': Long high Hurst (trending), short low Hurst (mean-reverting)
            - 'long_low_hurst': Long low Hurst only
            - 'long_high_hurst': Long high Hurst only
        num_quintiles (int): Number of quintiles
        long_percentile (int): Percentile threshold for long positions
        short_percentile (int): Percentile threshold for short positions
        
    Returns:
        dict: Dictionary with 'long' and 'short' DataFrames
    """
    # Rank by Hurst
    ranked_df = rank_by_hurst(data, date, num_quintiles)
    
    if ranked_df.empty:
        return {'long': pd.DataFrame(), 'short': pd.DataFrame()}
    
    if strategy == 'long_mean_reverting':
        # Long lowest Hurst (mean-reverting), short highest Hurst (trending)
        long_df = ranked_df[ranked_df['percentile'] <= long_percentile]
        short_df = ranked_df[ranked_df['percentile'] >= short_percentile]
        
    elif strategy == 'long_trending':
        # Long highest Hurst (trending), short lowest Hurst (mean-reverting)
        long_df = ranked_df[ranked_df['percentile'] >= short_percentile]
        short_df = ranked_df[ranked_df['percentile'] <= long_percentile]
        
    elif strategy == 'long_low_hurst':
        # Long only low Hurst
        long_df = ranked_df[ranked_df['percentile'] <= long_percentile]
        short_df = pd.DataFrame()
        
    elif strategy == 'long_high_hurst':
        # Long only high Hurst
        long_df = ranked_df[ranked_df['percentile'] >= short_percentile]
        short_df = pd.DataFrame()
        
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
    
    return {'long': long_df, 'short': short_df}


def calculate_position_weights(positions_df, weighting_method='equal_weight', total_allocation=0.5):
    """
    Calculate position weights for a bucket of positions.
    
    Args:
        positions_df (pd.DataFrame): DataFrame with positions and volatility
        weighting_method (str): Weighting method ('equal_weight' or 'risk_parity')
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
    
    else:
        raise ValueError(f"Unknown weighting method: {weighting_method}")
    
    return df


def run_backtest(data, strategy='long_mean_reverting', hurst_window=90, 
                volatility_window=30, rebalance_days=7, num_quintiles=5,
                long_percentile=20, short_percentile=80,
                weighting_method='equal_weight', initial_capital=10000,
                leverage=1.0, long_allocation=0.5, short_allocation=0.5,
                min_volume=5_000_000, min_market_cap=50_000_000,
                start_date=None, end_date=None):
    """
    Run the Hurst exponent factor backtest.
    
    Args:
        data (pd.DataFrame): Historical OHLCV data
        strategy (str): Strategy type
        hurst_window (int): Hurst calculation window
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
    print("HURST EXPONENT FACTOR BACKTEST")
    print("=" * 80)
    print(f"\nStrategy: {strategy}")
    print(f"Hurst Window: {hurst_window} days")
    print(f"Volatility Window: {volatility_window} days")
    print(f"Rebalance Frequency: {rebalance_days} days")
    print(f"Weighting Method: {weighting_method}")
    print(f"Long Allocation: {long_allocation*100:.1f}%")
    print(f"Short Allocation: {short_allocation*100:.1f}%")
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print(f"Leverage: {leverage}x")
    print(f"Min Volume: ${min_volume:,.0f}")
    print(f"Min Market Cap: ${min_market_cap:,.0f}")
    
    # Step 1: Calculate Hurst exponent
    print("\n" + "-" * 80)
    print("Step 1: Calculating rolling Hurst exponents...")
    min_periods = int(hurst_window * 0.7)
    hurst_data = calculate_rolling_hurst(data, window=hurst_window, min_periods=min_periods)
    print(f"  Total data points with Hurst: {hurst_data['hurst'].notna().sum()}")
    
    valid_hurst = hurst_data[(hurst_data['hurst'] >= 0) & (hurst_data['hurst'] <= 1)]
    if len(valid_hurst) > 0:
        print(f"  Hurst range: [{valid_hurst['hurst'].min():.3f}, {valid_hurst['hurst'].max():.3f}]")
        print(f"  Hurst mean: {valid_hurst['hurst'].mean():.3f}")
        print(f"  Hurst median: {valid_hurst['hurst'].median():.3f}")
    
    # Step 2: Calculate volatility (for risk parity weighting)
    print("\n" + "-" * 80)
    print("Step 2: Calculating volatility...")
    hurst_data = calculate_volatility(hurst_data, window=volatility_window)
    
    # Step 3: Filter universe
    print("\n" + "-" * 80)
    print("Step 3: Filtering universe...")
    print(f"  Coins before filtering: {hurst_data['symbol'].nunique()}")
    hurst_data = filter_universe(hurst_data, min_volume=min_volume, min_market_cap=min_market_cap)
    print(f"  Coins after filtering: {hurst_data['symbol'].nunique()}")
    
    # Step 4: Filter by date range
    if start_date:
        hurst_data = hurst_data[hurst_data['date'] >= pd.to_datetime(start_date)]
    if end_date:
        hurst_data = hurst_data[hurst_data['date'] <= pd.to_datetime(end_date)]
    
    # Step 5: Run backtest
    print("\n" + "-" * 80)
    print("Step 4: Running backtest...")
    
    # Get trading dates
    trading_dates = sorted(hurst_data['date'].unique())
    
    if len(trading_dates) < hurst_window + rebalance_days:
        raise ValueError(f"Insufficient data. Need at least {hurst_window + rebalance_days} days.")
    
    # Start after warmup period
    start_idx = hurst_window
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
            # Select positions based on Hurst
            selected = select_symbols_by_hurst(
                hurst_data, current_date, strategy=strategy,
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
                    'hurst': row['hurst'],
                    'hurst_rank': row.get('hurst_rank', np.nan),
                    'percentile': row.get('percentile', np.nan),
                    'weight': row['weight'],
                    'volatility': row.get('volatility', np.nan),
                    'market_cap': row.get('market_cap', np.nan),
                    'volume_30d_avg': row.get('volume_30d_avg', np.nan)
                })
            
            for _, row in short_positions.iterrows():
                trades.append({
                    'date': current_date,
                    'symbol': row['symbol'],
                    'signal': 'SHORT',
                    'hurst': row['hurst'],
                    'hurst_rank': row.get('hurst_rank', np.nan),
                    'percentile': row.get('percentile', np.nan),
                    'weight': -row['weight'],  # Negative for short
                    'volatility': row.get('volatility', np.nan),
                    'market_cap': row.get('market_cap', np.nan),
                    'volume_30d_avg': row.get('volume_30d_avg', np.nan)
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
            next_day_data = hurst_data[hurst_data['date'] == next_date]
            
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
        
        # Calculate average Hurst of portfolio
        avg_hurst_long = 0
        avg_hurst_short = 0
        num_longs = 0
        num_shorts = 0
        
        for symbol, weight in current_positions.items():
            symbol_hurst_data = hurst_data[(hurst_data['date'] == current_date) & 
                                          (hurst_data['symbol'] == symbol)]
            if not symbol_hurst_data.empty:
                hurst_val = symbol_hurst_data.iloc[0]['hurst']
                if not np.isnan(hurst_val):
                    if weight > 0:
                        avg_hurst_long += hurst_val
                        num_longs += 1
                    else:
                        avg_hurst_short += hurst_val
                        num_shorts += 1
        
        if num_longs > 0:
            avg_hurst_long /= num_longs
        if num_shorts > 0:
            avg_hurst_short /= num_shorts
        
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
            'avg_hurst_long': avg_hurst_long,
            'avg_hurst_short': avg_hurst_short
        })
    
    # Convert to DataFrames
    portfolio_df = pd.DataFrame(portfolio_values)
    trades_df = pd.DataFrame(trades)
    
    # Calculate metrics
    print("\n" + "-" * 80)
    print("Step 5: Calculating performance metrics...")
    metrics = calculate_metrics(portfolio_df, initial_capital, leverage)
    
    # Calculate strategy info
    strategy_info = {
        'strategy': strategy,
        'hurst_window': hurst_window,
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
        'avg_long_hurst': trades_df[trades_df['signal'] == 'LONG']['hurst'].mean() if not trades_df.empty else np.nan,
        'avg_short_hurst': trades_df[trades_df['signal'] == 'SHORT']['hurst'].mean() if not trades_df.empty else np.nan,
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
    
    # Average Hurst
    avg_hurst_long = portfolio_df['avg_hurst_long'].mean()
    avg_hurst_short = portfolio_df['avg_hurst_short'].mean()
    
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
        'avg_hurst_long': avg_hurst_long,
        'avg_hurst_short': avg_hurst_short,
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
    print(f"  Hurst Window:           {strategy_info['hurst_window']} days")
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
    
    print("\nHurst Analysis:")
    print(f"  Avg Long Hurst:         {strategy_info['avg_long_hurst']:>14.3f}")
    print(f"  Avg Short Hurst:        {strategy_info['avg_short_hurst']:>14.3f}")
    print(f"  Hurst Spread:           {strategy_info['avg_short_hurst'] - strategy_info['avg_long_hurst']:>14.3f}")
    
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
    """Main function to run Hurst exponent factor backtest."""
    parser = argparse.ArgumentParser(description='Backtest Hurst exponent factor strategy')
    
    # Data parameters
    parser.add_argument('--price-data', type=str,
                       default='data/raw/combined_coinbase_coinmarketcap_daily.csv',
                       help='Path to historical OHLCV CSV file')
    
    # Strategy parameters
    parser.add_argument('--strategy', type=str, default='long_mean_reverting',
                       choices=['long_mean_reverting', 'long_trending',
                               'long_low_hurst', 'long_high_hurst'],
                       help='Strategy variant')
    
    # Hurst calculation parameters
    parser.add_argument('--hurst-window', type=int, default=90,
                       help='Hurst calculation window in days')
    parser.add_argument('--volatility-window', type=int, default=30,
                       help='Volatility calculation window in days')
    
    # Portfolio construction parameters
    parser.add_argument('--rebalance-days', type=int, default=7,
                       help='Rebalance frequency in days')
    parser.add_argument('--num-quintiles', type=int, default=5,
                       help='Number of Hurst quintiles')
    parser.add_argument('--long-percentile', type=int, default=20,
                       help='Percentile threshold for long positions')
    parser.add_argument('--short-percentile', type=int, default=80,
                       help='Percentile threshold for short positions')
    parser.add_argument('--weighting-method', type=str, default='equal_weight',
                       choices=['equal_weight', 'risk_parity'],
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
                       default='backtests/results/backtest_hurst_factor',
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
        hurst_window=args.hurst_window,
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
