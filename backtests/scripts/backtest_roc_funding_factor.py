#!/usr/bin/env python3
"""
Backtest for RoC vs Funding Factor Strategy

This script backtests a strategy that compares Rate of Change (RoC) vs cumulative
funding rates over matched time periods:
1. Calculates rolling RoC (price momentum) for all cryptocurrencies
2. Calculates cumulative funding rates over the same period
3. Creates RoC-Funding spread as the signal
4. Ranks cryptocurrencies by spread:
   - High spread (RoC >> Funding) = Momentum underpriced → LONG
   - Low spread (RoC << Funding) = Funding overload → SHORT
5. Uses equal-weight or risk parity weighting within each bucket
6. Rebalances periodically (weekly by default)
7. Tracks portfolio performance over time

Hypothesis: RoC should outpace funding in efficient markets. Extreme deviations
signal trading opportunities.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../signals'))


def load_price_data(filepath):
    """
    Load historical OHLCV price data from CSV file.
    
    Args:
        filepath (str): Path to CSV file with OHLCV data
        
    Returns:
        pd.DataFrame: DataFrame with date, symbol, close, volume, market_cap
    """
    print(f"Loading price data from {filepath}...")
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Keep only relevant columns
    required_cols = ['date', 'symbol', 'close']
    optional_cols = ['volume', 'market_cap', 'open', 'high', 'low', 'base']
    
    cols_to_keep = required_cols.copy()
    for col in optional_cols:
        if col in df.columns:
            cols_to_keep.append(col)
    
    df = df[cols_to_keep]
    
    # Use base as symbol if available (cleaner symbol names)
    if 'base' in df.columns:
        df['base_symbol'] = df['base']
    else:
        # Extract base from symbol (e.g., BTC/USD -> BTC)
        df['base_symbol'] = df['symbol'].str.split('/').str[0]
    
    print(f"  Loaded {len(df)} rows for {df['symbol'].nunique()} symbols")
    return df


def load_funding_data(filepath):
    """
    Load historical funding rates from CSV file.
    
    Args:
        filepath (str): Path to CSV file with funding rate data
        
    Returns:
        pd.DataFrame: DataFrame with date, coin_symbol, funding_rate_pct
    """
    print(f"Loading funding data from {filepath}...")
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['coin_symbol', 'date']).reset_index(drop=True)
    
    # Keep only relevant columns
    required_cols = ['date', 'coin_symbol', 'funding_rate_pct']
    
    # Check for required columns
    if not all(col in df.columns for col in required_cols):
        print(f"  Warning: Missing required columns. Available: {df.columns.tolist()}")
        # Try alternative column names
        if 'funding_rate' in df.columns:
            df['funding_rate_pct'] = df['funding_rate'] * 100
    
    df = df[required_cols]
    
    print(f"  Loaded {len(df)} rows for {df['coin_symbol'].nunique()} symbols")
    return df


def merge_price_and_funding(price_df, funding_df):
    """
    Merge price and funding data on date and symbol.
    
    Args:
        price_df (pd.DataFrame): Price data
        funding_df (pd.DataFrame): Funding data
        
    Returns:
        pd.DataFrame: Merged data
    """
    print("Merging price and funding data...")
    
    # Merge on date and symbol
    merged = price_df.merge(
        funding_df,
        left_on=['date', 'base_symbol'],
        right_on=['date', 'coin_symbol'],
        how='left'
    )
    
    # Report merge statistics
    total_rows = len(merged)
    rows_with_funding = merged['funding_rate_pct'].notna().sum()
    pct_with_funding = rows_with_funding / total_rows * 100
    
    print(f"  Merged data: {total_rows} rows")
    print(f"  Rows with funding data: {rows_with_funding} ({pct_with_funding:.1f}%)")
    print(f"  Symbols with funding: {merged[merged['funding_rate_pct'].notna()]['base_symbol'].nunique()}")
    
    return merged


def calculate_roc(data, window=30):
    """
    Calculate rolling Rate of Change (RoC).
    
    RoC = (Price_t - Price_t-N) / Price_t-N = Price_t / Price_t-N - 1
    
    Args:
        data (pd.DataFrame): DataFrame with date, symbol, close columns
        window (int): Lookback period in days
        
    Returns:
        pd.DataFrame: DataFrame with roc_pct column
    """
    df = data.copy()
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Calculate RoC as percentage return over window
    df['roc_pct'] = df.groupby('symbol')['close'].transform(
        lambda x: (x / x.shift(window) - 1) * 100
    )
    
    return df


def calculate_cumulative_funding(data, window=30):
    """
    Calculate cumulative funding rate over rolling window.
    
    Cumulative Funding = Sum of funding rates over window
    
    Args:
        data (pd.DataFrame): DataFrame with funding_rate_pct column
        window (int): Lookback period in days
        
    Returns:
        pd.DataFrame: DataFrame with cum_funding_pct column
    """
    df = data.copy()
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Calculate cumulative funding as rolling sum
    df['cum_funding_pct'] = df.groupby('symbol')['funding_rate_pct'].transform(
        lambda x: x.rolling(window=window, min_periods=int(window*0.7)).sum()
    )
    
    return df


def calculate_roc_funding_spread(data, window=30):
    """
    Calculate RoC minus cumulative funding spread.
    
    Spread = RoC - Cumulative Funding
    
    Args:
        data (pd.DataFrame): DataFrame with price and funding data
        window (int): Lookback period in days
        
    Returns:
        pd.DataFrame: DataFrame with spread_pct column
    """
    print(f"Calculating RoC-Funding spread with {window}-day window...")
    
    # Calculate RoC
    df = calculate_roc(data, window)
    
    # Calculate cumulative funding
    df = calculate_cumulative_funding(df, window)
    
    # Calculate spread
    df['spread_pct'] = df['roc_pct'] - df['cum_funding_pct']
    
    # Report statistics
    valid_spreads = df['spread_pct'].dropna()
    if len(valid_spreads) > 0:
        print(f"  Spread statistics:")
        print(f"    Mean: {valid_spreads.mean():.2f}%")
        print(f"    Median: {valid_spreads.median():.2f}%")
        print(f"    Std: {valid_spreads.std():.2f}%")
        print(f"    Min: {valid_spreads.min():.2f}%")
        print(f"    Max: {valid_spreads.max():.2f}%")
    
    return df


def calculate_volatility(data, window=30):
    """
    Calculate rolling volatility (annualized).
    
    Args:
        data (pd.DataFrame): DataFrame with close column
        window (int): Rolling window size
        
    Returns:
        pd.DataFrame: DataFrame with volatility column
    """
    df = data.copy()
    
    # Calculate daily returns
    df['daily_return'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Calculate annualized volatility
    df['volatility'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=window, min_periods=int(window*0.7)).std() * np.sqrt(365)
    )
    
    return df


def filter_universe(data, min_volume=5_000_000, min_market_cap=50_000_000, min_data_coverage=0.9):
    """
    Filter cryptocurrency universe by liquidity, market cap, and data quality.
    
    Args:
        data (pd.DataFrame): DataFrame with volume, market_cap, and data columns
        min_volume (float): Minimum 30-day average daily volume
        min_market_cap (float): Minimum market cap
        min_data_coverage (float): Minimum data availability (0-1)
        
    Returns:
        pd.DataFrame: Filtered data
    """
    df = data.copy()
    initial_symbols = df['symbol'].nunique()
    
    # Calculate 30-day rolling average volume
    if 'volume' in df.columns:
        df['volume_30d_avg'] = df.groupby('symbol')['volume'].transform(
            lambda x: x.rolling(window=30, min_periods=20).mean()
        )
        df = df[df['volume_30d_avg'] >= min_volume]
    
    # Filter by market cap
    if 'market_cap' in df.columns:
        df = df[df['market_cap'] >= min_market_cap]
    
    # Filter by data quality (must have funding data)
    df = df[df['funding_rate_pct'].notna()]
    df = df[df['spread_pct'].notna()]
    
    final_symbols = df['symbol'].nunique()
    print(f"  Universe filtered: {initial_symbols} → {final_symbols} symbols")
    
    return df


def rank_by_spread(data, date, num_quintiles=5):
    """
    Rank cryptocurrencies by RoC-Funding spread on a specific date.
    
    Args:
        data (pd.DataFrame): DataFrame with spread_pct column
        date (pd.Timestamp): Date to rank on
        num_quintiles (int): Number of quintiles
        
    Returns:
        pd.DataFrame: DataFrame with quintile and rank information
    """
    # Get data for this specific date
    date_data = data[data['date'] == date].copy()
    
    if date_data.empty:
        return pd.DataFrame()
    
    # Remove NaN spreads
    date_data = date_data.dropna(subset=['spread_pct'])
    
    if len(date_data) < num_quintiles:
        return pd.DataFrame()
    
    # Rank by spread (ascending: low to high)
    date_data['spread_rank'] = date_data['spread_pct'].rank(method='first', ascending=True)
    date_data['percentile'] = date_data['spread_rank'] / len(date_data) * 100
    
    # Assign quintiles (1 = lowest spread, num_quintiles = highest spread)
    try:
        date_data['quintile'] = pd.qcut(
            date_data['spread_pct'],
            q=num_quintiles,
            labels=range(1, num_quintiles + 1),
            duplicates='drop'
        )
        date_data['quintile'] = date_data['quintile'].astype(int)
    except ValueError:
        # If can't create quintiles, use percentile-based assignment
        date_data['quintile'] = pd.cut(
            date_data['percentile'],
            bins=[0, 20, 40, 60, 80, 100],
            labels=[1, 2, 3, 4, 5],
            include_lowest=True
        ).astype(int)
    
    return date_data


def generate_signals(ranked_data, strategy='long_high_short_low_spread',
                     long_percentile=80, short_percentile=20):
    """
    Generate long/short signals based on spread rankings.
    
    Args:
        ranked_data (pd.DataFrame): DataFrame with spread rankings
        strategy (str): Strategy variant
        long_percentile (float): Percentile threshold for long (top X%)
        short_percentile (float): Percentile threshold for short (bottom X%)
        
    Returns:
        pd.DataFrame: DataFrame with signal column
    """
    df = ranked_data.copy()
    df['signal'] = 0  # Default: no position
    
    if strategy == 'long_high_short_low_spread':
        # Long high spread (RoC >> Funding), Short low spread (RoC << Funding)
        df.loc[df['percentile'] >= long_percentile, 'signal'] = 1  # Long
        df.loc[df['percentile'] <= short_percentile, 'signal'] = -1  # Short
        
    elif strategy == 'long_high_spread':
        # Long high spread only
        df.loc[df['percentile'] >= long_percentile, 'signal'] = 1  # Long
        
    elif strategy == 'short_low_spread':
        # Short low spread only
        df.loc[df['percentile'] <= short_percentile, 'signal'] = -1  # Short
        
    elif strategy == 'long_low_short_high_spread':
        # Contrarian: Long low spread, Short high spread
        df.loc[df['percentile'] <= short_percentile, 'signal'] = 1  # Long
        df.loc[df['percentile'] >= long_percentile, 'signal'] = -1  # Short
    
    return df


def calculate_portfolio_weights(signals_data, weighting_method='equal_weight',
                                long_allocation=0.5, short_allocation=0.5):
    """
    Calculate portfolio weights based on signals and weighting method.
    
    Args:
        signals_data (pd.DataFrame): DataFrame with signals
        weighting_method (str): Weighting method ('equal_weight', 'spread_weighted', 'risk_parity')
        long_allocation (float): Allocation to long side (0-1)
        short_allocation (float): Allocation to short side (0-1)
        
    Returns:
        pd.DataFrame: DataFrame with weight column
    """
    df = signals_data.copy()
    df['weight'] = 0.0
    
    # Separate longs and shorts
    longs = df[df['signal'] == 1].copy()
    shorts = df[df['signal'] == -1].copy()
    
    num_longs = len(longs)
    num_shorts = len(shorts)
    
    if weighting_method == 'equal_weight':
        # Equal weight allocation
        if num_longs > 0:
            df.loc[df['signal'] == 1, 'weight'] = long_allocation / num_longs
        if num_shorts > 0:
            df.loc[df['signal'] == -1, 'weight'] = -short_allocation / num_shorts
            
    elif weighting_method == 'spread_weighted':
        # Weight by absolute spread magnitude
        if num_longs > 0:
            longs_abs_spread = longs['spread_pct'].abs()
            longs_weights = (longs_abs_spread / longs_abs_spread.sum()) * long_allocation
            df.loc[df['signal'] == 1, 'weight'] = longs_weights.values
        
        if num_shorts > 0:
            shorts_abs_spread = shorts['spread_pct'].abs()
            shorts_weights = (shorts_abs_spread / shorts_abs_spread.sum()) * short_allocation
            df.loc[df['signal'] == -1, 'weight'] = -shorts_weights.values
            
    elif weighting_method == 'risk_parity':
        # Weight by inverse volatility
        if num_longs > 0 and 'volatility' in longs.columns:
            longs_inv_vol = 1 / longs['volatility'].replace(0, np.nan)
            longs_inv_vol = longs_inv_vol.fillna(0)
            if longs_inv_vol.sum() > 0:
                longs_weights = (longs_inv_vol / longs_inv_vol.sum()) * long_allocation
                df.loc[df['signal'] == 1, 'weight'] = longs_weights.values
        
        if num_shorts > 0 and 'volatility' in shorts.columns:
            shorts_inv_vol = 1 / shorts['volatility'].replace(0, np.nan)
            shorts_inv_vol = shorts_inv_vol.fillna(0)
            if shorts_inv_vol.sum() > 0:
                shorts_weights = (shorts_inv_vol / shorts_inv_vol.sum()) * short_allocation
                df.loc[df['signal'] == -1, 'weight'] = -shorts_weights.values
    
    return df


def run_backtest(data, strategy='long_high_short_low_spread', window=30,
                rebalance_days=7, num_quintiles=5, long_percentile=80,
                short_percentile=20, weighting_method='equal_weight',
                long_allocation=0.5, short_allocation=0.5,
                initial_capital=10000, leverage=1.0,
                start_date=None, end_date=None):
    """
    Run backtest for RoC-Funding factor strategy.
    
    Args:
        data (pd.DataFrame): Prepared data with all necessary columns
        strategy (str): Strategy variant
        window (int): Window for RoC and funding calculation
        rebalance_days (int): Rebalance frequency in days
        ... (other parameters)
        
    Returns:
        dict: Dictionary containing portfolio values, trades, and metrics
    """
    print(f"\n{'='*70}")
    print(f"RUNNING BACKTEST: {strategy.upper()}")
    print(f"{'='*70}")
    print(f"Window: {window} days")
    print(f"Rebalance: Every {rebalance_days} days")
    print(f"Weighting: {weighting_method}")
    print(f"Allocation: {long_allocation:.0%} long, {short_allocation:.0%} short")
    
    # Filter by date range
    if start_date:
        data = data[data['date'] >= pd.to_datetime(start_date)]
    if end_date:
        data = data[data['date'] <= pd.to_datetime(end_date)]
    
    if data.empty:
        print("ERROR: No data after date filtering")
        return None
    
    # Get unique dates for rebalancing
    all_dates = sorted(data['date'].unique())
    
    # Need at least window days for first signal
    rebalance_dates = [d for d in all_dates[window::rebalance_days]]
    
    print(f"\nBacktest period: {all_dates[0].date()} to {all_dates[-1].date()}")
    print(f"Total days: {len(all_dates)}")
    print(f"Rebalance dates: {len(rebalance_dates)}")
    
    # Initialize tracking
    portfolio_values = []
    all_trades = []
    current_positions = {}
    portfolio_value = initial_capital * leverage
    cash = 0
    
    # Run backtest
    for i, rebal_date in enumerate(rebalance_dates):
        # Rank and generate signals
        ranked = rank_by_spread(data, rebal_date, num_quintiles)
        
        if ranked.empty:
            continue
        
        signals = generate_signals(ranked, strategy, long_percentile, short_percentile)
        weighted = calculate_portfolio_weights(
            signals, weighting_method, long_allocation, short_allocation
        )
        
        # Get next rebalance date for return calculation
        if i < len(rebalance_dates) - 1:
            next_rebal_date = rebalance_dates[i + 1]
        else:
            # Use last available date
            next_rebal_date = all_dates[-1]
        
        # Calculate returns between rebalance dates
        period_data = data[
            (data['date'] > rebal_date) &
            (data['date'] <= next_rebal_date)
        ].copy()
        
        if period_data.empty:
            continue
        
        # Calculate position returns
        new_positions = {}
        position_values = {}
        
        for _, row in weighted[weighted['weight'] != 0].iterrows():
            symbol = row['symbol']
            weight = row['weight']
            
            # Get entry price
            entry_price = row['close']
            
            # Calculate position size
            position_size = portfolio_value * weight
            
            # Store position
            new_positions[symbol] = {
                'weight': weight,
                'entry_price': entry_price,
                'position_size': position_size,
                'signal': row['signal']
            }
            
            # Record trade
            all_trades.append({
                'date': rebal_date,
                'symbol': symbol,
                'signal': 'LONG' if row['signal'] == 1 else 'SHORT',
                'roc_pct': row['roc_pct'],
                'cum_funding_pct': row['cum_funding_pct'],
                'spread_pct': row['spread_pct'],
                'spread_rank': row['spread_rank'],
                'percentile': row['percentile'],
                'weight': weight,
                'position_size': position_size,
                'volatility': row.get('volatility', np.nan)
            })
        
        # Calculate daily portfolio values for this period
        for date in period_data['date'].unique():
            daily_value = initial_capital  # Start from initial capital
            
            for symbol, pos in new_positions.items():
                # Get price on this date
                symbol_data = period_data[
                    (period_data['symbol'] == symbol) &
                    (period_data['date'] == date)
                ]
                
                if not symbol_data.empty:
                    current_price = symbol_data.iloc[0]['close']
                    entry_price = pos['entry_price']
                    
                    # Calculate return
                    position_return = (current_price / entry_price - 1)
                    
                    # Apply to position value
                    position_pnl = pos['position_size'] * position_return
                    daily_value += position_pnl
            
            # Calculate exposures
            long_exposure = sum(
                abs(p['position_size']) for p in new_positions.values()
                if p['signal'] == 1
            )
            short_exposure = sum(
                abs(p['position_size']) for p in new_positions.values()
                if p['signal'] == -1
            )
            
            num_longs = sum(1 for p in new_positions.values() if p['signal'] == 1)
            num_shorts = sum(1 for p in new_positions.values() if p['signal'] == -1)
            
            # Calculate average spreads
            avg_spread_long = np.mean([
                t['spread_pct'] for t in all_trades[-len(new_positions):]
                if t['signal'] == 'LONG'
            ]) if num_longs > 0 else 0
            
            avg_spread_short = np.mean([
                t['spread_pct'] for t in all_trades[-len(new_positions):]
                if t['signal'] == 'SHORT'
            ]) if num_shorts > 0 else 0
            
            portfolio_values.append({
                'date': date,
                'portfolio_value': daily_value,
                'cash': cash,
                'long_exposure': long_exposure,
                'short_exposure': short_exposure,
                'net_exposure': long_exposure - short_exposure,
                'gross_exposure': long_exposure + short_exposure,
                'num_longs': num_longs,
                'num_shorts': num_shorts,
                'avg_spread_long': avg_spread_long,
                'avg_spread_short': avg_spread_short
            })
        
        # Update portfolio value for next rebalance
        if portfolio_values:
            portfolio_value = portfolio_values[-1]['portfolio_value']
        
        current_positions = new_positions
    
    # Convert to DataFrames
    df_portfolio = pd.DataFrame(portfolio_values)
    df_trades = pd.DataFrame(all_trades)
    
    # Calculate performance metrics
    metrics = calculate_performance_metrics(
        df_portfolio, initial_capital, strategy, window,
        rebalance_days, weighting_method
    )
    
    return {
        'portfolio_values': df_portfolio,
        'trades': df_trades,
        'metrics': metrics
    }


def calculate_performance_metrics(portfolio_df, initial_capital, strategy,
                                  window, rebalance_days, weighting_method):
    """
    Calculate performance metrics from portfolio values.
    
    Args:
        portfolio_df (pd.DataFrame): DataFrame with portfolio values over time
        initial_capital (float): Initial capital
        strategy (str): Strategy name
        window (int): RoC/funding window
        rebalance_days (int): Rebalance frequency
        weighting_method (str): Weighting method
        
    Returns:
        dict: Dictionary of performance metrics
    """
    if portfolio_df.empty:
        return {}
    
    # Calculate returns
    portfolio_df = portfolio_df.sort_values('date').reset_index(drop=True)
    portfolio_df['daily_return'] = portfolio_df['portfolio_value'].pct_change()
    
    # Basic metrics
    final_value = portfolio_df['portfolio_value'].iloc[-1]
    total_return = (final_value - initial_capital) / initial_capital
    
    # Time metrics
    num_days = len(portfolio_df)
    num_years = num_days / 365
    
    # Annualized return
    if num_years > 0:
        annualized_return = (final_value / initial_capital) ** (1 / num_years) - 1
    else:
        annualized_return = 0
    
    # Risk metrics
    daily_returns = portfolio_df['daily_return'].dropna()
    annualized_volatility = daily_returns.std() * np.sqrt(365)
    
    # Sharpe ratio (assuming 0% risk-free rate)
    sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility > 0 else 0
    
    # Sortino ratio (downside deviation)
    downside_returns = daily_returns[daily_returns < 0]
    downside_volatility = downside_returns.std() * np.sqrt(365) if len(downside_returns) > 0 else 0
    sortino_ratio = annualized_return / downside_volatility if downside_volatility > 0 else 0
    
    # Maximum drawdown
    cumulative = (1 + daily_returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # Calmar ratio
    calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
    
    # Win rate
    win_rate = (daily_returns > 0).sum() / len(daily_returns) if len(daily_returns) > 0 else 0
    
    # Average positions
    avg_long_positions = portfolio_df['num_longs'].mean()
    avg_short_positions = portfolio_df['num_shorts'].mean()
    
    # Average spreads
    avg_spread_long = portfolio_df['avg_spread_long'].mean()
    avg_spread_short = portfolio_df['avg_spread_short'].mean()
    
    # Total rebalances
    total_rebalances = num_days // rebalance_days
    
    metrics = {
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'annualized_return': annualized_return,
        'annualized_volatility': annualized_volatility,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'max_drawdown': max_drawdown,
        'calmar_ratio': calmar_ratio,
        'win_rate': win_rate,
        'avg_long_positions': avg_long_positions,
        'avg_short_positions': avg_short_positions,
        'avg_spread_long': avg_spread_long,
        'avg_spread_short': avg_spread_short,
        'total_rebalances': total_rebalances,
        'trading_days': num_days,
        'strategy': strategy,
        'window': window,
        'rebalance_days': rebalance_days,
        'weighting_method': weighting_method
    }
    
    return metrics


def save_results(results, output_prefix):
    """
    Save backtest results to CSV files.
    
    Args:
        results (dict): Dictionary with portfolio_values, trades, metrics
        output_prefix (str): Prefix for output files
    """
    output_dir = os.path.join(os.path.dirname(__file__), '../results')
    os.makedirs(output_dir, exist_ok=True)
    
    # Save portfolio values
    portfolio_file = os.path.join(output_dir, f'{output_prefix}_portfolio_values.csv')
    results['portfolio_values'].to_csv(portfolio_file, index=False)
    print(f"\n✓ Saved portfolio values to {portfolio_file}")
    
    # Save trades
    trades_file = os.path.join(output_dir, f'{output_prefix}_trades.csv')
    results['trades'].to_csv(trades_file, index=False)
    print(f"✓ Saved trades to {trades_file}")
    
    # Save metrics
    metrics_file = os.path.join(output_dir, f'{output_prefix}_metrics.csv')
    metrics_df = pd.DataFrame([results['metrics']])
    metrics_df.to_csv(metrics_file, index=False)
    print(f"✓ Saved metrics to {metrics_file}")


def print_results(results):
    """
    Print backtest results summary.
    
    Args:
        results (dict): Dictionary with metrics
    """
    metrics = results['metrics']
    
    print(f"\n{'='*70}")
    print("BACKTEST RESULTS SUMMARY")
    print(f"{'='*70}")
    
    print(f"\nStrategy: {metrics['strategy']}")
    print(f"Window: {metrics['window']} days")
    print(f"Rebalance: Every {metrics['rebalance_days']} days")
    print(f"Weighting: {metrics['weighting_method']}")
    
    print(f"\n{'='*70}")
    print("RETURNS")
    print(f"{'='*70}")
    print(f"Initial Capital:      ${metrics['initial_capital']:,.2f}")
    print(f"Final Value:          ${metrics['final_value']:,.2f}")
    print(f"Total Return:         {metrics['total_return']:>7.2%}")
    print(f"Annualized Return:    {metrics['annualized_return']:>7.2%}")
    
    print(f"\n{'='*70}")
    print("RISK METRICS")
    print(f"{'='*70}")
    print(f"Annualized Vol:       {metrics['annualized_volatility']:>7.2%}")
    print(f"Sharpe Ratio:         {metrics['sharpe_ratio']:>7.2f}")
    print(f"Sortino Ratio:        {metrics['sortino_ratio']:>7.2f}")
    print(f"Maximum Drawdown:     {metrics['max_drawdown']:>7.2%}")
    print(f"Calmar Ratio:         {metrics['calmar_ratio']:>7.2f}")
    
    print(f"\n{'='*70}")
    print("TRADING STATISTICS")
    print(f"{'='*70}")
    print(f"Win Rate:             {metrics['win_rate']:>7.2%}")
    print(f"Avg Long Positions:   {metrics['avg_long_positions']:>7.1f}")
    print(f"Avg Short Positions:  {metrics['avg_short_positions']:>7.1f}")
    print(f"Avg Spread Long:      {metrics['avg_spread_long']:>7.2f}%")
    print(f"Avg Spread Short:     {metrics['avg_spread_short']:>7.2f}%")
    print(f"Total Rebalances:     {metrics['total_rebalances']:>7.0f}")
    print(f"Trading Days:         {metrics['trading_days']:>7.0f}")
    
    print(f"\n{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Backtest RoC vs Funding Factor Strategy'
    )
    
    # Data files
    parser.add_argument('--price-data', type=str,
                       default='data/raw/combined_coinbase_coinmarketcap_daily.csv',
                       help='Path to price data CSV')
    parser.add_argument('--funding-data', type=str,
                       default='data/raw/historical_funding_rates_top100_ALL_HISTORY_20251028_002456.csv',
                       help='Path to funding data CSV')
    
    # Strategy parameters
    parser.add_argument('--strategy', type=str,
                       default='long_high_short_low_spread',
                       choices=['long_high_short_low_spread', 'long_high_spread',
                               'short_low_spread', 'long_low_short_high_spread'],
                       help='Strategy variant')
    parser.add_argument('--window', type=int, default=30,
                       help='Window for RoC and funding calculation (days)')
    parser.add_argument('--rebalance-days', type=int, default=7,
                       help='Rebalance frequency (days)')
    parser.add_argument('--num-quintiles', type=int, default=5,
                       help='Number of quintiles')
    parser.add_argument('--long-percentile', type=float, default=80,
                       help='Percentile threshold for long (0-100)')
    parser.add_argument('--short-percentile', type=float, default=20,
                       help='Percentile threshold for short (0-100)')
    
    # Weighting
    parser.add_argument('--weighting-method', type=str, default='equal_weight',
                       choices=['equal_weight', 'spread_weighted', 'risk_parity'],
                       help='Portfolio weighting method')
    parser.add_argument('--long-allocation', type=float, default=0.5,
                       help='Allocation to long side (0-1)')
    parser.add_argument('--short-allocation', type=float, default=0.5,
                       help='Allocation to short side (0-1)')
    
    # Filters
    parser.add_argument('--min-volume', type=float, default=5_000_000,
                       help='Minimum 30d avg volume ($)')
    parser.add_argument('--min-market-cap', type=float, default=50_000_000,
                       help='Minimum market cap ($)')
    parser.add_argument('--min-data-coverage', type=float, default=0.9,
                       help='Minimum data availability (0-1)')
    
    # Portfolio
    parser.add_argument('--initial-capital', type=float, default=10000,
                       help='Initial capital (USD)')
    parser.add_argument('--leverage', type=float, default=1.0,
                       help='Leverage multiplier')
    
    # Date range
    parser.add_argument('--start-date', type=str, default='2021-01-01',
                       help='Backtest start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default=None,
                       help='Backtest end date (YYYY-MM-DD)')
    
    # Output
    parser.add_argument('--output-prefix', type=str,
                       default='backtest_roc_funding_factor',
                       help='Output file prefix')
    
    args = parser.parse_args()
    
    try:
        # Load data
        price_data = load_price_data(args.price_data)
        funding_data = load_funding_data(args.funding_data)
        
        # Merge data
        merged_data = merge_price_and_funding(price_data, funding_data)
        
        # Calculate spread
        spread_data = calculate_roc_funding_spread(merged_data, args.window)
        
        # Calculate volatility (for risk parity)
        spread_data = calculate_volatility(spread_data, window=30)
        
        # Filter universe
        filtered_data = filter_universe(
            spread_data,
            min_volume=args.min_volume,
            min_market_cap=args.min_market_cap,
            min_data_coverage=args.min_data_coverage
        )
        
        # Run backtest
        results = run_backtest(
            filtered_data,
            strategy=args.strategy,
            window=args.window,
            rebalance_days=args.rebalance_days,
            num_quintiles=args.num_quintiles,
            long_percentile=args.long_percentile,
            short_percentile=args.short_percentile,
            weighting_method=args.weighting_method,
            long_allocation=args.long_allocation,
            short_allocation=args.short_allocation,
            initial_capital=args.initial_capital,
            leverage=args.leverage,
            start_date=args.start_date,
            end_date=args.end_date
        )
        
        if results:
            # Print results
            print_results(results)
            
            # Save results
            save_results(results, args.output_prefix)
            
            print("✓ Backtest completed successfully!")
        else:
            print("ERROR: Backtest failed to produce results")
            sys.exit(1)
            
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
