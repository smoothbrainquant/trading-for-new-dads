#!/usr/bin/env python3
"""
Backtest for Autocorrelation Factor Strategy

This script backtests an autocorrelation factor strategy that:
1. Calculates rolling autocorrelation (lag-1) of returns for all cryptocurrencies
2. Ranks cryptocurrencies by autocorrelation
3. Creates long/short portfolios based on autocorrelation quintiles:
   - Momentum: Long high positive autocorr, short negative autocorr
   - Contrarian: Long negative autocorr, short high positive autocorr
4. Uses equal-weight or risk parity weighting within each quintile
5. Rebalances periodically (daily, weekly, or monthly)
6. Tracks portfolio performance over time

Autocorrelation factor hypothesis: Coins with positive autocorrelation exhibit momentum
(trending behavior), while coins with negative autocorrelation exhibit mean reversion.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import sys
import os

# Add parent directory to path to import calc_vola and calc_weights
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'signals'))
from calc_vola import calculate_rolling_30d_volatility
from calc_weights import calculate_weights


def calculate_rolling_autocorr(data, lag=1, window=30):
    """
    Calculate rolling autocorrelation of returns.
    
    Args:
        data (pd.DataFrame): DataFrame with date, symbol, close columns
        lag (int): Lag for autocorrelation (default: 1)
        window (int): Window size for autocorrelation calculation (default: 30)
        
    Returns:
        pd.DataFrame: DataFrame with autocorrelation column
    """
    df = data.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Calculate daily log returns
    df['daily_return'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Calculate rolling autocorrelation
    def autocorr_func(x):
        """Calculate autocorrelation with given lag."""
        if len(x) < lag + 2:
            return np.nan
        try:
            # Use pandas autocorr method
            return pd.Series(x).autocorr(lag=lag)
        except:
            return np.nan
    
    df[f'autocorr_lag{lag}_{window}d'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=window, min_periods=max(window-5, int(window*0.8))).apply(autocorr_func)
    )
    
    return df[['date', 'symbol', 'close', 'daily_return', f'autocorr_lag{lag}_{window}d']]


def calculate_rolling_volatility_custom(data, window=30):
    """
    Calculate rolling volatility for risk parity weighting.
    
    Args:
        data (pd.DataFrame): DataFrame with date, symbol, close columns
        window (int): Window size for volatility calculation
        
    Returns:
        pd.DataFrame: DataFrame with volatility column
    """
    df = data.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Calculate daily log returns
    df['daily_return'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Calculate rolling volatility (annualized)
    df[f'volatility_{window}d'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=window, min_periods=window).std() * np.sqrt(365)
    )
    
    return df[['date', 'symbol', 'close', 'daily_return', f'volatility_{window}d']]


def load_data(filepath):
    """
    Load historical OHLCV data from CSV file.
    
    Args:
        filepath (str): Path to CSV file with OHLCV data
        
    Returns:
        pd.DataFrame: DataFrame with date, symbol, open, high, low, close, volume
    """
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    return df


def assign_autocorr_quintiles(autocorr_df, date, num_quintiles=5, autocorr_column='autocorr_lag1_30d'):
    """
    Assign cryptocurrencies to autocorrelation quintiles on a specific date.
    
    Args:
        autocorr_df (pd.DataFrame): Autocorrelation data with date, symbol, and autocorr columns
        date (pd.Timestamp): Date to rank on
        num_quintiles (int): Number of quintiles (default 5)
        autocorr_column (str): Name of autocorrelation column
        
    Returns:
        pd.DataFrame: DataFrame with quintile assignments
    """
    # Get data for this specific date
    date_data = autocorr_df[autocorr_df['date'] == date].copy()
    
    if date_data.empty:
        return pd.DataFrame()
    
    # Remove any NaN autocorrelations
    date_data = date_data.dropna(subset=[autocorr_column])
    
    if len(date_data) < num_quintiles:
        return pd.DataFrame()
    
    # Sort by autocorrelation (ascending: negative to positive)
    date_data = date_data.sort_values(autocorr_column)
    
    # Assign quintiles (1 = most negative autocorr, num_quintiles = most positive autocorr)
    try:
        date_data['quintile'] = pd.qcut(
            date_data[autocorr_column],
            q=num_quintiles,
            labels=range(1, num_quintiles + 1),
            duplicates='drop'
        )
    except ValueError:
        # If qcut fails due to duplicate bin edges, use rank-based approach
        date_data['quintile'] = pd.cut(
            date_data[autocorr_column].rank(method='first'),
            bins=num_quintiles,
            labels=range(1, num_quintiles + 1)
        )
    
    return date_data


def select_symbols_by_autocorr(autocorr_df, date, strategy='momentum', num_quintiles=5, autocorr_column='autocorr_lag1_30d'):
    """
    Select symbols based on autocorrelation factor strategy.
    
    Args:
        autocorr_df (pd.DataFrame): Autocorrelation data
        date (pd.Timestamp): Date to select on
        strategy (str): Strategy type:
            - 'momentum': Long high positive autocorr (quintile 5), short negative autocorr (quintile 1)
            - 'contrarian': Long negative autocorr (quintile 1), short high positive autocorr (quintile 5)
            - 'long_only_momentum': Long high positive autocorr only
            - 'long_only_contrarian': Long negative autocorr only
        num_quintiles (int): Number of quintiles
        autocorr_column (str): Name of autocorrelation column
        
    Returns:
        dict: Dictionary with 'long' and 'short' lists of symbols
    """
    # Assign quintiles
    ranked_df = assign_autocorr_quintiles(autocorr_df, date, num_quintiles, autocorr_column)
    
    if ranked_df.empty:
        return {'long': [], 'short': []}
    
    if strategy == 'momentum':
        # Long high positive autocorr (quintile 5), short negative autocorr (quintile 1)
        long_symbols = ranked_df[ranked_df['quintile'] == num_quintiles]['symbol'].tolist()
        short_symbols = ranked_df[ranked_df['quintile'] == 1]['symbol'].tolist()
        
    elif strategy == 'contrarian':
        # Long negative autocorr (quintile 1), short high positive autocorr (quintile 5)
        long_symbols = ranked_df[ranked_df['quintile'] == 1]['symbol'].tolist()
        short_symbols = ranked_df[ranked_df['quintile'] == num_quintiles]['symbol'].tolist()
        
    elif strategy == 'long_only_momentum':
        # Long high positive autocorr only
        long_symbols = ranked_df[ranked_df['quintile'] == num_quintiles]['symbol'].tolist()
        short_symbols = []
        
    elif strategy == 'long_only_contrarian':
        # Long negative autocorr only
        long_symbols = ranked_df[ranked_df['quintile'] == 1]['symbol'].tolist()
        short_symbols = []
        
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
    
    return {'long': long_symbols, 'short': short_symbols}


def calculate_portfolio_returns(weights, returns_df):
    """
    Calculate portfolio returns based on weights and individual asset returns.
    Handles both positive (long) and negative (short) weights.
    
    Args:
        weights (dict): Dictionary mapping symbols to portfolio weights (can be negative for shorts)
        returns_df (pd.DataFrame): DataFrame with symbol and daily_return columns
        
    Returns:
        float: Portfolio return for the period
    """
    if not weights or returns_df.empty:
        return 0.0
    
    portfolio_return = 0.0
    for symbol, weight in weights.items():
        symbol_return = returns_df[returns_df['symbol'] == symbol]['daily_return'].values
        if len(symbol_return) > 0 and not np.isnan(symbol_return[0]):
            portfolio_return += weight * symbol_return[0]
    
    return portfolio_return


def backtest(
    price_data,
    strategy='momentum',
    num_quintiles=5,
    autocorr_window=30,
    autocorr_lag=1,
    volatility_window=30,
    rebalance_days=7,
    start_date=None,
    end_date=None,
    initial_capital=10000,
    leverage=1.0,
    long_allocation=0.5,
    short_allocation=0.5,
    weighting_method='risk_parity',
    min_volume=5000000
):
    """
    Run backtest for the autocorrelation factor strategy.
    
    Args:
        price_data (pd.DataFrame): Historical OHLCV data
        strategy (str): Autocorrelation factor strategy type
        num_quintiles (int): Number of autocorrelation buckets for ranking
        autocorr_window (int): Window for autocorrelation calculation
        autocorr_lag (int): Lag for autocorrelation (default: 1)
        volatility_window (int): Window for volatility calculation (for risk parity)
        rebalance_days (int): Rebalance every N days
        start_date (str): Start date for backtest (format: 'YYYY-MM-DD')
        end_date (str): End date for backtest (format: 'YYYY-MM-DD')
        initial_capital (float): Initial portfolio capital
        leverage (float): Leverage multiplier (default 1.0 for no leverage)
        long_allocation (float): Allocation to long side (default 0.5 = 50%)
        short_allocation (float): Allocation to short side (default 0.5 = 50%)
        weighting_method (str): 'equal' or 'risk_parity'
        min_volume (float): Minimum daily volume filter (USD)
        
    Returns:
        dict: Dictionary containing backtest results
    """
    # Filter data by date range if specified
    if start_date:
        price_data = price_data[price_data['date'] >= pd.to_datetime(start_date)]
    if end_date:
        price_data = price_data[price_data['date'] <= pd.to_datetime(end_date)]
    
    print(f"\nCalculating {autocorr_window}-day rolling autocorrelation (lag {autocorr_lag})...")
    # Calculate autocorrelation for all data
    autocorr_df = calculate_rolling_autocorr(price_data, lag=autocorr_lag, window=autocorr_window)
    autocorr_column = f'autocorr_lag{autocorr_lag}_{autocorr_window}d'
    
    # Calculate volatility for risk parity weighting
    if weighting_method == 'risk_parity':
        print(f"Calculating {volatility_window}-day rolling volatility for risk parity...")
        vol_df = calculate_rolling_volatility_custom(price_data, window=volatility_window)
        vol_column = f'volatility_{volatility_window}d'
        # Merge volatility into autocorr_df
        autocorr_df = autocorr_df.merge(
            vol_df[['date', 'symbol', vol_column]],
            on=['date', 'symbol'],
            how='left'
        )
    
    # Get unique dates for rebalancing
    all_dates = sorted(autocorr_df['date'].unique())
    
    # Need enough data for autocorrelation calculation
    min_required_days = autocorr_window + 10
    
    if len(all_dates) < min_required_days:
        raise ValueError(f"Insufficient data. Need at least {min_required_days} days, have {len(all_dates)}")
    
    # Start backtest after minimum required period
    backtest_start_idx = autocorr_window
    backtest_dates = all_dates[backtest_start_idx::rebalance_days]  # Rebalance every N days
    
    if len(backtest_dates) == 0:
        backtest_dates = [all_dates[-1]]
    
    print(f"\nBacktest Configuration:")
    print(f"  Strategy: {strategy}")
    print(f"  Period: {backtest_dates[0].date()} to {backtest_dates[-1].date()}")
    print(f"  Trading days: {len(all_dates[backtest_start_idx:])}")
    print(f"  Rebalance frequency: Every {rebalance_days} days ({len(backtest_dates)} rebalances)")
    print(f"  Autocorrelation window: {autocorr_window}d, lag: {autocorr_lag}")
    print(f"  Num quintiles: {num_quintiles}")
    print(f"  Initial capital: ${initial_capital:,.2f}")
    print(f"  Leverage: {leverage}x")
    print(f"  Long allocation: {long_allocation:.1%}")
    print(f"  Short allocation: {short_allocation:.1%}")
    print(f"  Weighting method: {weighting_method}")
    print("=" * 80)
    
    # Initialize tracking variables
    portfolio_values = []
    trades_history = []
    current_weights = {}
    current_capital = initial_capital
    last_rebalance_date = None
    
    # Calculate daily returns for all data
    data_with_returns = price_data.copy()
    data_with_returns['daily_return'] = data_with_returns.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Track daily (not just rebalance days) for portfolio value
    daily_tracking_dates = all_dates[backtest_start_idx:]
    
    for date_idx, current_date in enumerate(daily_tracking_dates):
        # Check if it's a rebalancing day
        is_rebalance_day = (
            last_rebalance_date is None or 
            current_date in backtest_dates or
            (current_date - last_rebalance_date).days >= rebalance_days
        )
        
        if is_rebalance_day:
            # Get autocorrelation data up to current date (no lookahead bias)
            historical_autocorr = autocorr_df[autocorr_df['date'] <= current_date]
            
            # Select symbols based on autocorrelation strategy
            selected = select_symbols_by_autocorr(
                historical_autocorr,
                current_date,
                strategy=strategy,
                num_quintiles=num_quintiles,
                autocorr_column=autocorr_column
            )
            
            long_symbols = selected['long']
            short_symbols = selected['short']
            
            new_weights = {}
            
            if len(long_symbols) + len(short_symbols) > 0:
                try:
                    if weighting_method == 'equal':
                        # Equal weight within each side
                        if long_symbols:
                            long_weight = long_allocation * leverage / len(long_symbols)
                            for symbol in long_symbols:
                                new_weights[symbol] = long_weight
                        
                        if short_symbols:
                            short_weight = short_allocation * leverage / len(short_symbols)
                            for symbol in short_symbols:
                                new_weights[symbol] = -short_weight
                    
                    elif weighting_method == 'risk_parity':
                        # Risk parity weighting based on volatility
                        # Get current volatilities
                        current_data = historical_autocorr[historical_autocorr['date'] == current_date]
                        
                        # Separate volatilities for longs and shorts
                        long_volatilities = {}
                        short_volatilities = {}
                        
                        for _, row in current_data.iterrows():
                            if not pd.isna(row.get(vol_column, np.nan)) and row.get(vol_column, 0) > 0:
                                if row['symbol'] in long_symbols:
                                    long_volatilities[row['symbol']] = row[vol_column]
                                elif row['symbol'] in short_symbols:
                                    short_volatilities[row['symbol']] = row[vol_column]
                        
                        # Calculate risk parity weights separately for longs and shorts
                        long_weights = calculate_weights(long_volatilities) if long_volatilities else {}
                        short_weights = calculate_weights(short_volatilities) if short_volatilities else {}
                        
                        # Apply leverage and allocation
                        for symbol, weight in long_weights.items():
                            new_weights[symbol] = weight * long_allocation * leverage
                        
                        for symbol, weight in short_weights.items():
                            new_weights[symbol] = -weight * short_allocation * leverage
                    
                except Exception as e:
                    print(f"Error calculating weights on {current_date}: {e}")
                    new_weights = current_weights.copy()
            
            # Record trades when weights change
            if new_weights != current_weights:
                all_symbols = set(new_weights.keys()) | set(current_weights.keys())
                for symbol in all_symbols:
                    old_weight = current_weights.get(symbol, 0)
                    new_weight = new_weights.get(symbol, 0)
                    if abs(new_weight - old_weight) > 0.0001:
                        # Get autocorrelation for this symbol
                        autocorr_data = historical_autocorr[
                            (historical_autocorr['date'] == current_date) & 
                            (historical_autocorr['symbol'] == symbol)
                        ]
                        autocorr_val = autocorr_data[autocorr_column].values[0] if len(autocorr_data) > 0 else np.nan
                        
                        trades_history.append({
                            'date': current_date,
                            'symbol': symbol,
                            'old_weight': old_weight,
                            'new_weight': new_weight,
                            'weight_change': new_weight - old_weight,
                            autocorr_column: autocorr_val,
                            'position_type': 'long' if new_weight > 0 else 'short' if new_weight < 0 else 'close'
                        })
            
            current_weights = new_weights.copy()
            last_rebalance_date = current_date
        
        # Calculate daily portfolio return based on current weights
        # IMPORTANT: Use NEXT day's returns to avoid lookahead bias
        if current_weights and date_idx < len(daily_tracking_dates) - 1:
            next_date = daily_tracking_dates[date_idx + 1]
            next_returns = data_with_returns[data_with_returns['date'] == next_date]
            portfolio_return = calculate_portfolio_returns(current_weights, next_returns)
            current_capital = current_capital * np.exp(portfolio_return)
        
        # Record portfolio value daily
        long_exposure = sum(w for w in current_weights.values() if w > 0)
        short_exposure = abs(sum(w for w in current_weights.values() if w < 0))
        net_exposure = sum(current_weights.values())
        
        portfolio_values.append({
            'date': current_date,
            'portfolio_value': current_capital,
            'num_long_positions': len([w for w in current_weights.values() if w > 0]),
            'num_short_positions': len([w for w in current_weights.values() if w < 0]),
            'long_exposure': long_exposure,
            'short_exposure': short_exposure,
            'net_exposure': net_exposure,
            'gross_exposure': long_exposure + short_exposure
        })
        
        # Progress update
        if (date_idx + 1) % 50 == 0 or date_idx == len(daily_tracking_dates) - 1:
            print(f"Progress: {date_idx+1}/{len(daily_tracking_dates)} days | "
                  f"Date: {current_date.date()} | "
                  f"Value: ${current_capital:,.2f} | "
                  f"Long: {len([w for w in current_weights.values() if w > 0])} | "
                  f"Short: {len([w for w in current_weights.values() if w < 0])}")
    
    # Convert to DataFrames
    portfolio_df = pd.DataFrame(portfolio_values)
    trades_df = pd.DataFrame(trades_history)
    
    # Calculate performance metrics
    metrics = calculate_performance_metrics(portfolio_df, initial_capital)
    
    return {
        'portfolio_values': portfolio_df,
        'trades': trades_df,
        'metrics': metrics,
        'strategy_info': {
            'strategy': strategy,
            'autocorr_window': autocorr_window,
            'autocorr_lag': autocorr_lag,
            'num_quintiles': num_quintiles,
            'rebalance_days': rebalance_days,
            'weighting_method': weighting_method
        }
    }


def calculate_performance_metrics(portfolio_df, initial_capital):
    """
    Calculate performance metrics for the backtest.
    
    Args:
        portfolio_df (pd.DataFrame): DataFrame with portfolio values over time
        initial_capital (float): Initial portfolio capital
        
    Returns:
        dict: Dictionary of performance metrics
    """
    # Calculate returns
    portfolio_df['daily_return'] = portfolio_df['portfolio_value'].pct_change()
    portfolio_df['log_return'] = np.log(portfolio_df['portfolio_value'] / portfolio_df['portfolio_value'].shift(1))
    
    # Total return
    final_value = portfolio_df['portfolio_value'].iloc[-1]
    total_return = (final_value - initial_capital) / initial_capital
    
    # Annualized return (assuming 365 trading days per year)
    num_days = len(portfolio_df)
    years = num_days / 365.25
    annualized_return = (final_value / initial_capital) ** (1 / years) - 1 if years > 0 else 0
    
    # Volatility (annualized)
    daily_returns = portfolio_df['log_return'].dropna()
    daily_vol = daily_returns.std()
    annualized_vol = daily_vol * np.sqrt(365)
    
    # Sharpe ratio (assuming 0% risk-free rate)
    sharpe_ratio = annualized_return / annualized_vol if annualized_vol > 0 else 0
    
    # Sortino ratio (downside volatility only)
    downside_returns = daily_returns[daily_returns < 0]
    downside_vol = downside_returns.std() * np.sqrt(365) if len(downside_returns) > 0 else annualized_vol
    sortino_ratio = annualized_return / downside_vol if downside_vol > 0 else 0
    
    # Maximum drawdown
    cumulative_returns = (1 + portfolio_df['daily_return'].fillna(0)).cumprod()
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # Calmar ratio
    calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
    
    # Win rate (percentage of positive days)
    positive_days = (daily_returns > 0).sum()
    total_trading_days = len(daily_returns)
    win_rate = positive_days / total_trading_days if total_trading_days > 0 else 0
    
    # Average positions
    avg_long_positions = portfolio_df['num_long_positions'].mean()
    avg_short_positions = portfolio_df['num_short_positions'].mean()
    avg_total_positions = avg_long_positions + avg_short_positions
    
    # Average exposures
    avg_long_exposure = portfolio_df['long_exposure'].mean()
    avg_short_exposure = portfolio_df['short_exposure'].mean()
    avg_net_exposure = portfolio_df['net_exposure'].mean()
    avg_gross_exposure = portfolio_df['gross_exposure'].mean()
    
    metrics = {
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'annualized_return': annualized_return,
        'annualized_volatility': annualized_vol,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'max_drawdown': max_drawdown,
        'calmar_ratio': calmar_ratio,
        'win_rate': win_rate,
        'num_days': num_days,
        'avg_long_positions': avg_long_positions,
        'avg_short_positions': avg_short_positions,
        'avg_total_positions': avg_total_positions,
        'avg_long_exposure': avg_long_exposure,
        'avg_short_exposure': avg_short_exposure,
        'avg_net_exposure': avg_net_exposure,
        'avg_gross_exposure': avg_gross_exposure
    }
    
    return metrics


def print_results(results):
    """
    Print backtest results in a formatted manner.
    
    Args:
        results (dict): Dictionary containing backtest results
    """
    metrics = results['metrics']
    strategy_info = results['strategy_info']
    
    print("\n" + "=" * 80)
    print("AUTOCORRELATION FACTOR BACKTEST RESULTS")
    print("=" * 80)
    
    print(f"\nStrategy Information:")
    print(f"  Strategy: {strategy_info['strategy']}")
    print(f"  Autocorrelation window: {strategy_info['autocorr_window']} days")
    print(f"  Autocorrelation lag: {strategy_info['autocorr_lag']}")
    print(f"  Num quintiles: {strategy_info['num_quintiles']}")
    print(f"  Rebalance frequency: Every {strategy_info['rebalance_days']} days")
    print(f"  Weighting method: {strategy_info['weighting_method']}")
    
    print(f"\nPortfolio Performance:")
    print(f"  Initial Capital:        ${metrics['initial_capital']:>15,.2f}")
    print(f"  Final Value:            ${metrics['final_value']:>15,.2f}")
    print(f"  Total Return:           {metrics['total_return']:>15.2%}")
    print(f"  Annualized Return:      {metrics['annualized_return']:>15.2%}")
    
    print(f"\nRisk Metrics:")
    print(f"  Annualized Volatility:  {metrics['annualized_volatility']:>15.2%}")
    print(f"  Sharpe Ratio:           {metrics['sharpe_ratio']:>15.2f}")
    print(f"  Sortino Ratio:          {metrics['sortino_ratio']:>15.2f}")
    print(f"  Maximum Drawdown:       {metrics['max_drawdown']:>15.2%}")
    print(f"  Calmar Ratio:           {metrics['calmar_ratio']:>15.2f}")
    
    print(f"\nTrading Statistics:")
    print(f"  Win Rate:               {metrics['win_rate']:>15.2%}")
    print(f"  Trading Days:           {metrics['num_days']:>15,.0f}")
    print(f"  Avg Long Positions:     {metrics['avg_long_positions']:>15.1f}")
    print(f"  Avg Short Positions:    {metrics['avg_short_positions']:>15.1f}")
    print(f"  Avg Total Positions:    {metrics['avg_total_positions']:>15.1f}")
    
    print(f"\nExposure Statistics:")
    print(f"  Avg Long Exposure:      {metrics['avg_long_exposure']:>15.2%}")
    print(f"  Avg Short Exposure:     {metrics['avg_short_exposure']:>15.2%}")
    print(f"  Avg Net Exposure:       {metrics['avg_net_exposure']:>15.2%}")
    print(f"  Avg Gross Exposure:     {metrics['avg_gross_exposure']:>15.2%}")
    
    if not results['trades'].empty:
        print(f"  Total Trades:           {len(results['trades']):>15,.0f}")
    
    print("\n" + "=" * 80)
    
    # Show portfolio value over time (sample)
    portfolio_df = results['portfolio_values']
    print("\nPortfolio Value Sample (first 10 days):")
    display_cols = ['date', 'portfolio_value', 'num_long_positions', 'num_short_positions', 
                    'long_exposure', 'short_exposure', 'net_exposure']
    print(portfolio_df[display_cols].head(10).to_string(index=False))
    
    print("\nPortfolio Value Sample (last 10 days):")
    print(portfolio_df[display_cols].tail(10).to_string(index=False))


def save_results(results, output_prefix='backtest_autocorr_factor', output_dir='backtests/results'):
    """
    Save backtest results to CSV files.
    
    Args:
        results (dict): Dictionary containing backtest results
        output_prefix (str): Prefix for output filenames
        output_dir (str): Directory to save results
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Save portfolio values
    portfolio_file = os.path.join(output_dir, f"{output_prefix}_portfolio_values.csv")
    results['portfolio_values'].to_csv(portfolio_file, index=False)
    print(f"\nPortfolio values saved to: {portfolio_file}")
    
    # Save trades
    if not results['trades'].empty:
        trades_file = os.path.join(output_dir, f"{output_prefix}_trades.csv")
        results['trades'].to_csv(trades_file, index=False)
        print(f"Trades history saved to: {trades_file}")
    
    # Save metrics
    metrics_file = os.path.join(output_dir, f"{output_prefix}_metrics.csv")
    metrics_df = pd.DataFrame([results['metrics']])
    metrics_df.to_csv(metrics_file, index=False)
    print(f"Performance metrics saved to: {metrics_file}")
    
    # Save strategy info
    strategy_file = os.path.join(output_dir, f"{output_prefix}_strategy_info.csv")
    strategy_df = pd.DataFrame([results['strategy_info']])
    strategy_df.to_csv(strategy_file, index=False)
    print(f"Strategy info saved to: {strategy_file}")


def main():
    """Main execution function for backtest."""
    parser = argparse.ArgumentParser(
        description='Backtest Autocorrelation Factor Trading Strategy',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--price-data',
        type=str,
        default='data/raw/combined_coinbase_coinmarketcap_daily.csv',
        help='Path to historical OHLCV price data CSV file'
    )
    parser.add_argument(
        '--strategy',
        type=str,
        default='momentum',
        choices=['momentum', 'contrarian', 'long_only_momentum', 'long_only_contrarian'],
        help='Autocorrelation factor strategy type'
    )
    parser.add_argument(
        '--num-quintiles',
        type=int,
        default=5,
        help='Number of autocorrelation quintiles for ranking'
    )
    parser.add_argument(
        '--autocorr-window',
        type=int,
        default=30,
        help='Autocorrelation calculation window in days'
    )
    parser.add_argument(
        '--autocorr-lag',
        type=int,
        default=1,
        help='Lag for autocorrelation calculation'
    )
    parser.add_argument(
        '--volatility-window',
        type=int,
        default=30,
        help='Volatility calculation window in days (for risk parity)'
    )
    parser.add_argument(
        '--rebalance-days',
        type=int,
        default=7,
        help='Rebalance every N days'
    )
    parser.add_argument(
        '--weighting-method',
        type=str,
        default='risk_parity',
        choices=['equal', 'risk_parity'],
        help='Portfolio weighting method'
    )
    parser.add_argument(
        '--initial-capital',
        type=float,
        default=10000,
        help='Initial portfolio capital in USD'
    )
    parser.add_argument(
        '--leverage',
        type=float,
        default=1.0,
        help='Leverage multiplier (1.0 = no leverage)'
    )
    parser.add_argument(
        '--long-allocation',
        type=float,
        default=0.5,
        help='Allocation to long side (0.5 = 50%%)'
    )
    parser.add_argument(
        '--short-allocation',
        type=float,
        default=0.5,
        help='Allocation to short side (0.5 = 50%%)'
    )
    parser.add_argument(
        '--min-volume',
        type=float,
        default=5000000,
        help='Minimum daily volume filter (USD)'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        default=None,
        help='Start date for backtest (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        default=None,
        help='End date for backtest (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--output-prefix',
        type=str,
        default='backtest_autocorr_factor',
        help='Prefix for output CSV files'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='backtests/results',
        help='Directory to save output files'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("AUTOCORRELATION FACTOR BACKTEST")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Price data file: {args.price_data}")
    print(f"  Strategy: {args.strategy}")
    print(f"  Num quintiles: {args.num_quintiles}")
    print(f"  Autocorrelation window: {args.autocorr_window}d, lag: {args.autocorr_lag}")
    print(f"  Volatility window: {args.volatility_window}d")
    print(f"  Rebalance frequency: Every {args.rebalance_days} days")
    print(f"  Weighting method: {args.weighting_method}")
    print(f"  Initial capital: ${args.initial_capital:,.2f}")
    print(f"  Leverage: {args.leverage}x")
    print(f"  Long allocation: {args.long_allocation:.1%}")
    print(f"  Short allocation: {args.short_allocation:.1%}")
    print(f"  Start date: {args.start_date or 'First available'}")
    print(f"  End date: {args.end_date or 'Last available'}")
    print("=" * 80)
    
    # Load price data
    print("\nLoading price data...")
    price_data = load_data(args.price_data)
    print(f"Loaded {len(price_data)} rows for {price_data['symbol'].nunique()} symbols")
    print(f"Date range: {price_data['date'].min().date()} to {price_data['date'].max().date()}")
    
    # Run backtest
    print("\nRunning backtest...")
    results = backtest(
        price_data=price_data,
        strategy=args.strategy,
        num_quintiles=args.num_quintiles,
        autocorr_window=args.autocorr_window,
        autocorr_lag=args.autocorr_lag,
        volatility_window=args.volatility_window,
        rebalance_days=args.rebalance_days,
        initial_capital=args.initial_capital,
        leverage=args.leverage,
        long_allocation=args.long_allocation,
        short_allocation=args.short_allocation,
        weighting_method=args.weighting_method,
        min_volume=args.min_volume,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    # Print results
    print_results(results)
    
    # Save results
    save_results(results, output_prefix=args.output_prefix, output_dir=args.output_dir)
    
    print("\n" + "=" * 80)
    print("BACKTEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
