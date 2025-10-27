#!/usr/bin/env python3
"""
Backtest for Beta Factor Strategy

This script backtests a beta factor strategy that:
1. Calculates rolling beta to BTC for all cryptocurrencies
2. Ranks cryptocurrencies by beta values (systematic risk)
3. Creates long/short portfolios based on beta rankings:
   - Betting Against Beta (BAB): Long low beta (defensive), Short high beta (aggressive)
   - Traditional Risk Premium: Long high beta, Short low beta
4. Uses equal-weight or risk parity weighting within each bucket
5. Rebalances periodically (weekly by default)
6. Tracks portfolio performance over time

Beta hypothesis: Tests whether low beta coins outperform high beta coins on 
risk-adjusted basis (BAB anomaly) or vice versa (traditional CAPM).
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


def calculate_rolling_beta(data, btc_data, window=90):
    """
    Calculate rolling beta to BTC for each cryptocurrency.
    
    Beta = Cov(R_coin, R_btc) / Var(R_btc)
    
    Args:
        data (pd.DataFrame): DataFrame with date, symbol, close columns
        btc_data (pd.DataFrame): DataFrame with date, close for BTC
        window (int): Rolling window size for beta calculation
        
    Returns:
        pd.DataFrame: DataFrame with beta and supporting columns
    """
    df = data.copy()
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Calculate daily log returns for all coins
    df['daily_return'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Get BTC returns and merge
    btc_returns = btc_data.copy()
    btc_returns['btc_return'] = np.log(btc_returns['close'] / btc_returns['close'].shift(1))
    btc_returns = btc_returns[['date', 'btc_return']].dropna()
    
    # Merge BTC returns with coin data
    df = df.merge(btc_returns, on='date', how='left')
    
    # Calculate rolling beta using covariance method
    def calculate_beta(group):
        """Calculate rolling beta for a group (one coin)"""
        # Use rolling window to calculate covariance and variance
        rolling_cov = group['daily_return'].rolling(window=window, min_periods=int(window*0.7)).cov(
            group['btc_return']
        )
        rolling_var = group['btc_return'].rolling(window=window, min_periods=int(window*0.7)).var()
        
        # Beta = Covariance / Variance
        beta = rolling_cov / rolling_var
        
        # Replace inf and extreme values
        beta = beta.replace([np.inf, -np.inf], np.nan)
        beta = beta.clip(-5, 10)  # Cap extreme betas
        
        return beta
    
    df['beta'] = df.groupby('symbol', group_keys=False).apply(calculate_beta).values
    
    # Calculate additional statistics for analysis
    df['returns_mean_90d'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=window, min_periods=int(window*0.7)).mean()
    )
    
    df['returns_std_90d'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=window, min_periods=int(window*0.7)).std()
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


def rank_by_beta(data, date, num_quintiles=5):
    """
    Rank cryptocurrencies by beta on a specific date.
    
    Args:
        data (pd.DataFrame): DataFrame with beta column
        date (pd.Timestamp): Date to rank on
        num_quintiles (int): Number of quintiles
        
    Returns:
        pd.DataFrame: DataFrame with quintile and rank information
    """
    # Get data for this specific date
    date_data = data[data['date'] == date].copy()
    
    if date_data.empty:
        return pd.DataFrame()
    
    # Remove NaN betas
    date_data = date_data.dropna(subset=['beta'])
    
    if len(date_data) < num_quintiles:
        return pd.DataFrame()
    
    # Rank by beta (ascending: low to high)
    date_data['beta_rank'] = date_data['beta'].rank(method='first', ascending=True)
    date_data['percentile'] = date_data['beta_rank'] / len(date_data) * 100
    
    # Assign quintiles (1 = lowest beta, num_quintiles = highest beta)
    try:
        date_data['quintile'] = pd.qcut(
            date_data['beta'],
            q=num_quintiles,
            labels=range(1, num_quintiles + 1),
            duplicates='drop'
        )
    except ValueError:
        # If qcut fails, use rank-based approach
        date_data['quintile'] = pd.cut(
            date_data['beta_rank'],
            bins=num_quintiles,
            labels=range(1, num_quintiles + 1)
        )
    
    return date_data


def select_symbols_by_beta(data, date, strategy='betting_against_beta', 
                          num_quintiles=5, long_percentile=20, short_percentile=80):
    """
    Select symbols based on beta factor strategy.
    
    Args:
        data (pd.DataFrame): Data with beta column
        date (pd.Timestamp): Date to select on
        strategy (str): Strategy type:
            - 'betting_against_beta': Long low beta, short high beta (BAB)
            - 'traditional_risk_premium': Long high beta, short low beta
            - 'long_low_beta': Long low beta only
            - 'long_high_beta': Long high beta only
        num_quintiles (int): Number of quintiles
        long_percentile (int): Percentile threshold for long positions
        short_percentile (int): Percentile threshold for short positions
        
    Returns:
        dict: Dictionary with 'long' and 'short' DataFrames
    """
    # Rank by beta
    ranked_df = rank_by_beta(data, date, num_quintiles)
    
    if ranked_df.empty:
        return {'long': pd.DataFrame(), 'short': pd.DataFrame()}
    
    if strategy == 'betting_against_beta':
        # Long lowest beta (defensive), short highest beta (aggressive)
        long_df = ranked_df[ranked_df['percentile'] <= long_percentile]
        short_df = ranked_df[ranked_df['percentile'] >= short_percentile]
        
    elif strategy == 'traditional_risk_premium':
        # Long highest beta (aggressive), short lowest beta (defensive)
        long_df = ranked_df[ranked_df['percentile'] >= short_percentile]
        short_df = ranked_df[ranked_df['percentile'] <= long_percentile]
        
    elif strategy == 'long_low_beta':
        # Long only low beta
        long_df = ranked_df[ranked_df['percentile'] <= long_percentile]
        short_df = pd.DataFrame()
        
    elif strategy == 'long_high_beta':
        # Long only high beta
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
    
    elif weighting_method == 'beta_weighted':
        # Weight inversely proportional to absolute beta
        if 'beta' not in df.columns or df['beta'].isna().all():
            df['weight'] = total_allocation / len(df)
        else:
            df['beta_clean'] = df['beta'].fillna(df['beta'].median())
            df['inv_beta'] = 1 / df['beta_clean'].abs().clip(lower=0.1)
            df['weight'] = (df['inv_beta'] / df['inv_beta'].sum()) * total_allocation
    
    else:
        raise ValueError(f"Unknown weighting method: {weighting_method}")
    
    return df


def run_backtest(data, strategy='betting_against_beta', beta_window=90, 
                volatility_window=30, rebalance_days=7, num_quintiles=5,
                long_percentile=20, short_percentile=80,
                weighting_method='equal_weight', initial_capital=10000,
                leverage=1.0, long_allocation=0.5, short_allocation=0.5,
                min_volume=5_000_000, min_market_cap=50_000_000,
                start_date=None, end_date=None):
    """
    Run the beta factor backtest.
    
    Args:
        data (pd.DataFrame): Historical OHLCV data
        strategy (str): Strategy type
        beta_window (int): Beta calculation window
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
    print("BETA FACTOR BACKTEST")
    print("=" * 80)
    print(f"\nStrategy: {strategy}")
    print(f"Beta Window: {beta_window} days")
    print(f"Volatility Window: {volatility_window} days")
    print(f"Rebalance Frequency: {rebalance_days} days")
    print(f"Weighting Method: {weighting_method}")
    print(f"Long Allocation: {long_allocation*100:.1f}%")
    print(f"Short Allocation: {short_allocation*100:.1f}%")
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print(f"Leverage: {leverage}x")
    print(f"Min Volume: ${min_volume:,.0f}")
    print(f"Min Market Cap: ${min_market_cap:,.0f}")
    
    # Step 1: Extract BTC data (benchmark)
    print("\n" + "-" * 80)
    print("Step 1: Extracting BTC data...")
    # Try both 'BTC' and 'BTC/USD' as symbols
    btc_data = data[data['symbol'].isin(['BTC', 'BTC/USD'])][['date', 'close']].copy()
    if btc_data.empty:
        raise ValueError("BTC data not found in dataset. Beta calculation requires BTC or BTC/USD.")
    print(f"  BTC data points: {len(btc_data)}")
    
    # Step 2: Calculate beta
    print("\n" + "-" * 80)
    print("Step 2: Calculating rolling beta...")
    beta_data = calculate_rolling_beta(data, btc_data, window=beta_window)
    print(f"  Total data points with beta: {beta_data['beta'].notna().sum()}")
    print(f"  Beta range: [{beta_data['beta'].min():.2f}, {beta_data['beta'].max():.2f}]")
    print(f"  Beta mean: {beta_data['beta'].mean():.2f}")
    print(f"  Beta median: {beta_data['beta'].median():.2f}")
    
    # Step 3: Calculate volatility (for risk parity weighting)
    print("\n" + "-" * 80)
    print("Step 3: Calculating volatility...")
    beta_data = calculate_volatility(beta_data, window=volatility_window)
    
    # Step 4: Filter universe
    print("\n" + "-" * 80)
    print("Step 4: Filtering universe...")
    print(f"  Coins before filtering: {beta_data['symbol'].nunique()}")
    beta_data = filter_universe(beta_data, min_volume=min_volume, min_market_cap=min_market_cap)
    print(f"  Coins after filtering: {beta_data['symbol'].nunique()}")
    
    # Step 5: Filter by date range
    if start_date:
        beta_data = beta_data[beta_data['date'] >= pd.to_datetime(start_date)]
    if end_date:
        beta_data = beta_data[beta_data['date'] <= pd.to_datetime(end_date)]
    
    # Step 6: Run backtest
    print("\n" + "-" * 80)
    print("Step 5: Running backtest...")
    
    # Get trading dates
    trading_dates = sorted(beta_data['date'].unique())
    
    if len(trading_dates) < beta_window + rebalance_days:
        raise ValueError(f"Insufficient data. Need at least {beta_window + rebalance_days} days.")
    
    # Start after warmup period
    start_idx = beta_window
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
            # Select positions based on beta
            selected = select_symbols_by_beta(
                beta_data, current_date, strategy=strategy,
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
                    'beta': row['beta'],
                    'beta_rank': row.get('beta_rank', np.nan),
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
                    'beta': row['beta'],
                    'beta_rank': row.get('beta_rank', np.nan),
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
            next_day_data = beta_data[beta_data['date'] == next_date]
            
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
        
        # Calculate portfolio beta
        portfolio_beta = 0
        for symbol, weight in current_positions.items():
            symbol_beta_data = beta_data[(beta_data['date'] == current_date) & 
                                        (beta_data['symbol'] == symbol)]
            if not symbol_beta_data.empty:
                beta_val = symbol_beta_data.iloc[0]['beta']
                if not np.isnan(beta_val):
                    portfolio_beta += weight * beta_val
        
        # Record portfolio value
        portfolio_values.append({
            'date': current_date,
            'portfolio_value': portfolio_value,
            'cash': cash,
            'long_exposure': long_exposure * portfolio_value,
            'short_exposure': short_exposure * portfolio_value,
            'net_exposure': net_exposure * portfolio_value,
            'gross_exposure': gross_exposure * portfolio_value,
            'num_longs': sum([1 for w in current_positions.values() if w > 0]),
            'num_shorts': sum([1 for w in current_positions.values() if w < 0]),
            'portfolio_beta': portfolio_beta
        })
    
    # Convert to DataFrames
    portfolio_df = pd.DataFrame(portfolio_values)
    trades_df = pd.DataFrame(trades)
    
    # Calculate metrics
    print("\n" + "-" * 80)
    print("Step 6: Calculating performance metrics...")
    metrics = calculate_metrics(portfolio_df, initial_capital, leverage)
    
    # Calculate strategy info
    strategy_info = {
        'strategy': strategy,
        'beta_window': beta_window,
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
        'avg_long_beta': trades_df[trades_df['signal'] == 'LONG']['beta'].mean() if not trades_df.empty else np.nan,
        'avg_short_beta': trades_df[trades_df['signal'] == 'SHORT']['beta'].mean() if not trades_df.empty else np.nan,
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
    
    # Portfolio beta
    avg_portfolio_beta = portfolio_df['portfolio_beta'].mean()
    
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
        'avg_portfolio_beta': avg_portfolio_beta,
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
    print(f"  Beta Window:            {strategy_info['beta_window']} days")
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
    print(f"  Avg Portfolio Beta:     {metrics['avg_portfolio_beta']:>14.2f}")
    
    print("\nExposure Metrics:")
    print(f"  Avg Long Exposure:      $ {metrics['avg_long_exposure']:>12,.2f}")
    print(f"  Avg Short Exposure:     $ {metrics['avg_short_exposure']:>12,.2f}")
    print(f"  Avg Net Exposure:       $ {metrics['avg_net_exposure']:>12,.2f}")
    print(f"  Avg Gross Exposure:     $ {metrics['avg_gross_exposure']:>12,.2f}")
    
    print("\nBeta Analysis:")
    print(f"  Avg Long Beta:          {strategy_info['avg_long_beta']:>14.2f}")
    print(f"  Avg Short Beta:         {strategy_info['avg_short_beta']:>14.2f}")
    
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
    """Main function to run beta factor backtest."""
    parser = argparse.ArgumentParser(description='Backtest beta factor strategy')
    
    # Data parameters
    parser.add_argument('--price-data', type=str,
                       default='data/raw/combined_coinbase_coinmarketcap_daily.csv',
                       help='Path to historical OHLCV CSV file')
    
    # Strategy parameters
    parser.add_argument('--strategy', type=str, default='betting_against_beta',
                       choices=['betting_against_beta', 'traditional_risk_premium',
                               'long_low_beta', 'long_high_beta'],
                       help='Strategy variant')
    
    # Beta calculation parameters
    parser.add_argument('--beta-window', type=int, default=90,
                       help='Beta calculation window in days')
    parser.add_argument('--volatility-window', type=int, default=30,
                       help='Volatility calculation window in days')
    
    # Portfolio construction parameters
    parser.add_argument('--rebalance-days', type=int, default=7,
                       help='Rebalance frequency in days')
    parser.add_argument('--num-quintiles', type=int, default=5,
                       help='Number of beta quintiles')
    parser.add_argument('--long-percentile', type=int, default=20,
                       help='Percentile threshold for long positions')
    parser.add_argument('--short-percentile', type=int, default=80,
                       help='Percentile threshold for short positions')
    parser.add_argument('--weighting-method', type=str, default='equal_weight',
                       choices=['equal_weight', 'risk_parity', 'beta_weighted'],
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
                       default='backtests/results/backtest_beta_factor',
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
        beta_window=args.beta_window,
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
