#!/usr/bin/env python3
"""
Backtest for Carry Factor Strategy using Funding Rates

This script backtests a carry factor strategy that:
1. Uses historical funding rates from perpetual futures
2. Ranks cryptocurrencies by funding rates
3. Creates long/short portfolios:
   - Long position: Coins with lowest (most negative) funding rates -> we receive payments
   - Short position: Coins with highest (most positive) funding rates -> we collect payments
4. Uses risk parity weighting based on price volatility
5. Rebalances periodically (daily, weekly, or monthly)
6. Tracks portfolio performance over time

Carry factor hypothesis: Funding rates mean-revert, and extreme funding rates
provide opportunities to earn carry while benefiting from reversion.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
from calc_vola import calculate_rolling_30d_volatility
from calc_weights import calculate_weights


def calculate_rolling_volatility_custom(data, window=30):
    """
    Calculate rolling volatility with custom window size.
    
    Args:
        data (pd.DataFrame): DataFrame with date, symbol, close columns
        window (int): Window size for volatility calculation
        
    Returns:
        pd.DataFrame: DataFrame with volatility_30d column
    """
    df = data.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Calculate daily log returns
    df['daily_return'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Calculate rolling volatility (annualized)
    df['volatility_30d'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=window, min_periods=window).std() * np.sqrt(365)
    )
    
    return df[['date', 'symbol', 'close', 'daily_return', 'volatility_30d']]


def load_price_data(filepath):
    """
    Load historical OHLCV price data from CSV file.
    
    Args:
        filepath (str): Path to CSV file with OHLCV data
        
    Returns:
        pd.DataFrame: DataFrame with date, symbol, open, high, low, close, volume
    """
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Normalize symbol format (e.g., 'BTC/USD' -> 'BTC')
    if 'base' in df.columns:
        df['base_symbol'] = df['base']
    elif '/' in df['symbol'].iloc[0]:
        df['base_symbol'] = df['symbol'].apply(lambda x: x.split('/')[0])
    else:
        df['base_symbol'] = df['symbol']
    
    return df


def load_funding_rates(filepath):
    """
    Load historical funding rates data from CSV file.
    
    Args:
        filepath (str): Path to funding rates CSV file
        
    Returns:
        pd.DataFrame: DataFrame with date, coin_symbol, funding_rate_pct
    """
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['coin_symbol', 'date']).reset_index(drop=True)
    
    # Keep only necessary columns
    df = df[['date', 'coin_symbol', 'funding_rate_pct', 'rank', 'coin_name']]
    
    return df


def rank_by_funding_rate(funding_df, date, top_n=10, bottom_n=10):
    """
    Rank coins by funding rate on a specific date.
    
    Args:
        funding_df (pd.DataFrame): Funding rates data
        date (pd.Timestamp): Date to rank on
        top_n (int): Number of top (highest funding rate) coins to select
        bottom_n (int): Number of bottom (lowest funding rate) coins to select
        
    Returns:
        dict: Dictionary with 'long' (lowest funding) and 'short' (highest funding) lists
    """
    # Get funding rates for this specific date
    date_data = funding_df[funding_df['date'] == date].copy()
    
    if date_data.empty:
        return {'long': [], 'short': []}
    
    # Remove any NaN funding rates
    date_data = date_data.dropna(subset=['funding_rate_pct'])
    
    if len(date_data) < (top_n + bottom_n):
        # Not enough coins, scale down
        available = len(date_data)
        top_n = min(top_n, available // 2)
        bottom_n = min(bottom_n, available // 2)
    
    # Sort by funding rate
    date_data = date_data.sort_values('funding_rate_pct')
    
    # Long: coins with LOWEST funding rates (most negative) -> we receive funding
    long_symbols = date_data.head(bottom_n)['coin_symbol'].tolist()
    
    # Short: coins with HIGHEST funding rates (most positive) -> we receive funding
    short_symbols = date_data.tail(top_n)['coin_symbol'].tolist()
    
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
        symbol_return = returns_df[returns_df['base_symbol'] == symbol]['daily_return'].values
        if len(symbol_return) > 0 and not np.isnan(symbol_return[0]):
            portfolio_return += weight * symbol_return[0]
    
    return portfolio_return


def backtest(
    price_data,
    funding_data,
    top_n=10,
    bottom_n=10,
    volatility_window=30,
    rebalance_days=7,
    start_date=None,
    end_date=None,
    initial_capital=10000,
    leverage=1.0,
    long_allocation=0.5,
    short_allocation=0.5
):
    """
    Run backtest for the carry factor strategy.
    
    Args:
        price_data (pd.DataFrame): Historical OHLCV data
        funding_data (pd.DataFrame): Historical funding rates data
        top_n (int): Number of highest funding rate coins to short
        bottom_n (int): Number of lowest funding rate coins to long
        volatility_window (int): Window for volatility calculation
        rebalance_days (int): Rebalance every N days
        start_date (str): Start date for backtest (format: 'YYYY-MM-DD')
        end_date (str): End date for backtest (format: 'YYYY-MM-DD')
        initial_capital (float): Initial portfolio capital
        leverage (float): Leverage multiplier (default 1.0 for no leverage)
        long_allocation (float): Allocation to long side (default 0.5 = 50%)
        short_allocation (float): Allocation to short side (default 0.5 = 50%)
        
    Returns:
        dict: Dictionary containing backtest results
    """
    # Filter data by date range if specified
    if start_date:
        price_data = price_data[price_data['date'] >= pd.to_datetime(start_date)]
        funding_data = funding_data[funding_data['date'] >= pd.to_datetime(start_date)]
    if end_date:
        price_data = price_data[price_data['date'] <= pd.to_datetime(end_date)]
        funding_data = funding_data[funding_data['date'] <= pd.to_datetime(end_date)]
    
    # Get all available dates from both datasets
    price_dates = set(price_data['date'].unique())
    funding_dates = set(funding_data['date'].unique())
    common_dates = sorted(list(price_dates.intersection(funding_dates)))
    
    if len(common_dates) < volatility_window + 10:
        raise ValueError(f"Insufficient overlapping data. Need at least {volatility_window + 10} days, have {len(common_dates)}")
    
    print(f"\nData Overlap:")
    print(f"  Price data: {len(price_dates)} dates")
    print(f"  Funding data: {len(funding_dates)} dates")
    print(f"  Common dates: {len(common_dates)} dates")
    print(f"  Date range: {common_dates[0].date()} to {common_dates[-1].date()}")
    
    # Start backtest after minimum required period
    backtest_start_idx = volatility_window
    backtest_dates = common_dates[backtest_start_idx::rebalance_days]
    
    if len(backtest_dates) == 0:
        backtest_dates = [common_dates[-1]]
    
    print(f"\nBacktest Configuration:")
    print(f"  Period: {backtest_dates[0].date()} to {backtest_dates[-1].date()}")
    print(f"  Trading days: {len(backtest_dates)}")
    print(f"  Rebalance frequency: Every {rebalance_days} days")
    print(f"  Long positions: {bottom_n} coins (lowest funding rates)")
    print(f"  Short positions: {top_n} coins (highest funding rates)")
    print(f"  Volatility window: {volatility_window}d")
    print(f"  Initial capital: ${initial_capital:,.2f}")
    print(f"  Leverage: {leverage}x")
    print(f"  Long allocation: {long_allocation:.1%}")
    print(f"  Short allocation: {short_allocation:.1%}")
    print("=" * 80)
    
    # Initialize tracking variables
    portfolio_values = []
    trades_history = []
    current_weights = {}
    current_capital = initial_capital
    last_rebalance_date = None
    
    # Calculate daily returns for all price data
    data_with_returns = price_data.copy()
    data_with_returns['daily_return'] = data_with_returns.groupby('base_symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Track daily for portfolio value
    daily_tracking_dates = common_dates[backtest_start_idx:]
    
    for date_idx, current_date in enumerate(daily_tracking_dates):
        # Check if it's a rebalancing day
        is_rebalance_day = (
            last_rebalance_date is None or 
            current_date in backtest_dates or
            (current_date - last_rebalance_date).days >= rebalance_days
        )
        
        if is_rebalance_day:
            # Rank coins by funding rate on this date
            selected = rank_by_funding_rate(
                funding_data, 
                current_date, 
                top_n=top_n, 
                bottom_n=bottom_n
            )
            
            long_symbols = selected['long']
            short_symbols = selected['short']
            
            # Get historical price data up to current date for volatility calculation
            historical_data = price_data[price_data['date'] <= current_date].copy()
            
            # Filter to only symbols in our selection
            all_active_symbols = long_symbols + short_symbols
            active_data = historical_data[historical_data['base_symbol'].isin(all_active_symbols)]
            
            new_weights = {}
            
            if len(all_active_symbols) > 0:
                try:
                    # Calculate volatility for active symbols
                    volatility_df = calculate_rolling_volatility_custom(active_data, window=volatility_window)
                    latest_volatility = volatility_df[volatility_df['date'] == current_date]
                    
                    # Separate volatilities for longs and shorts
                    long_volatilities = {}
                    short_volatilities = {}
                    
                    for _, row in latest_volatility.iterrows():
                        if not pd.isna(row['volatility_30d']) and row['volatility_30d'] > 0:
                            base_sym = row['symbol'].split('/')[0] if '/' in row['symbol'] else row['symbol']
                            if base_sym in long_symbols:
                                long_volatilities[base_sym] = row['volatility_30d']
                            elif base_sym in short_symbols:
                                short_volatilities[base_sym] = row['volatility_30d']
                    
                    # Calculate risk parity weights separately for longs and shorts
                    long_weights = calculate_weights(long_volatilities) if long_volatilities else {}
                    short_weights = calculate_weights(short_volatilities) if short_volatilities else {}
                    
                    # Apply leverage and allocation
                    for symbol, weight in long_weights.items():
                        new_weights[symbol] = weight * long_allocation * leverage
                    
                    for symbol, weight in short_weights.items():
                        new_weights[symbol] = -weight * short_allocation * leverage
                    
                except Exception as e:
                    print(f"Error calculating volatility/weights on {current_date}: {e}")
                    new_weights = current_weights.copy()
            
            # Record trades when weights change
            if new_weights != current_weights:
                all_symbols = set(new_weights.keys()) | set(current_weights.keys())
                for symbol in all_symbols:
                    old_weight = current_weights.get(symbol, 0)
                    new_weight = new_weights.get(symbol, 0)
                    if abs(new_weight - old_weight) > 0.0001:
                        # Get funding rate for this symbol
                        fr = funding_data[
                            (funding_data['date'] == current_date) & 
                            (funding_data['coin_symbol'] == symbol)
                        ]['funding_rate_pct'].values
                        funding_rate = fr[0] if len(fr) > 0 else np.nan
                        
                        trades_history.append({
                            'date': current_date,
                            'symbol': symbol,
                            'old_weight': old_weight,
                            'new_weight': new_weight,
                            'weight_change': new_weight - old_weight,
                            'funding_rate_pct': funding_rate,
                            'position_type': 'long' if new_weight > 0 else 'short' if new_weight < 0 else 'close'
                        })
            
            current_weights = new_weights.copy()
            last_rebalance_date = current_date
        
        # Calculate daily portfolio return based on current weights
        # Use NEXT day's returns to avoid lookahead bias (weights from day T applied to returns from day T+1)
        if current_weights and date_idx < len(daily_tracking_dates) - 1:
            next_date = daily_tracking_dates[date_idx + 1]
            next_returns = data_with_returns[data_with_returns['date'] == next_date]
            portfolio_return = calculate_portfolio_returns(current_weights, next_returns)
            current_capital = current_capital * np.exp(portfolio_return)
        
        # Record portfolio value daily
        long_exposure = sum(w for w in current_weights.values() if w > 0)
        short_exposure = abs(sum(w for w in current_weights.values() if w < 0))
        net_exposure = sum(current_weights.values())
        
        # Calculate expected daily funding income (approximate)
        expected_funding_daily = 0.0
        for symbol, weight in current_weights.items():
            fr = funding_data[
                (funding_data['date'] == current_date) & 
                (funding_data['coin_symbol'] == symbol)
            ]['funding_rate_pct'].values
            if len(fr) > 0:
                # Funding rate is typically 8-hour, so daily = 3x
                # Negative weight (short) on positive FR = positive income
                # Positive weight (long) on negative FR = positive income
                expected_funding_daily += -weight * fr[0] / 100 * 3  # 3 funding periods per day
        
        portfolio_values.append({
            'date': current_date,
            'portfolio_value': current_capital,
            'num_long_positions': len([w for w in current_weights.values() if w > 0]),
            'num_short_positions': len([w for w in current_weights.values() if w < 0]),
            'long_exposure': long_exposure,
            'short_exposure': short_exposure,
            'net_exposure': net_exposure,
            'gross_exposure': long_exposure + short_exposure,
            'expected_funding_daily': expected_funding_daily
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
    
    # Add funding rate statistics to metrics
    if not trades_df.empty:
        long_trades = trades_df[(trades_df['position_type'] == 'long') & (trades_df['new_weight'] > 0)]
        short_trades = trades_df[(trades_df['position_type'] == 'short') & (trades_df['new_weight'] < 0)]
        
        metrics['avg_long_funding_rate'] = long_trades['funding_rate_pct'].mean() if len(long_trades) > 0 else 0
        metrics['avg_short_funding_rate'] = short_trades['funding_rate_pct'].mean() if len(short_trades) > 0 else 0
        metrics['total_expected_funding_income'] = portfolio_df['expected_funding_daily'].sum()
    
    return {
        'portfolio_values': portfolio_df,
        'trades': trades_df,
        'metrics': metrics,
        'strategy_info': {
            'top_n': top_n,
            'bottom_n': bottom_n,
            'rebalance_days': rebalance_days
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
    
    # Maximum drawdown
    cumulative_returns = (1 + portfolio_df['daily_return'].fillna(0)).cumprod()
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max
    max_drawdown = drawdown.min()
    
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
        'max_drawdown': max_drawdown,
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
    print("CARRY FACTOR BACKTEST RESULTS")
    print("=" * 80)
    
    print(f"\nStrategy Information:")
    print(f"  Long positions: {strategy_info['bottom_n']} coins with lowest funding rates")
    print(f"  Short positions: {strategy_info['top_n']} coins with highest funding rates")
    print(f"  Rebalance frequency: Every {strategy_info['rebalance_days']} days")
    
    print(f"\nPortfolio Performance:")
    print(f"  Initial Capital:        ${metrics['initial_capital']:>15,.2f}")
    print(f"  Final Value:            ${metrics['final_value']:>15,.2f}")
    print(f"  Total Return:           {metrics['total_return']:>15.2%}")
    print(f"  Annualized Return:      {metrics['annualized_return']:>15.2%}")
    
    print(f"\nRisk Metrics:")
    print(f"  Annualized Volatility:  {metrics['annualized_volatility']:>15.2%}")
    print(f"  Sharpe Ratio:           {metrics['sharpe_ratio']:>15.2f}")
    print(f"  Maximum Drawdown:       {metrics['max_drawdown']:>15.2%}")
    
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
    
    if 'avg_long_funding_rate' in metrics:
        print(f"\nFunding Rate Statistics:")
        print(f"  Avg Long FR:            {metrics['avg_long_funding_rate']:>15.4f}%")
        print(f"  Avg Short FR:           {metrics['avg_short_funding_rate']:>15.4f}%")
        print(f"  Total Expected Income:  ${metrics['total_expected_funding_income']:>15,.2f}")
    
    if not results['trades'].empty:
        print(f"  Total Rebalances:       {len(results['trades']):>15,.0f}")
    
    print("\n" + "=" * 80)
    
    # Show portfolio value over time (sample)
    portfolio_df = results['portfolio_values']
    print("\nPortfolio Value Sample (first 10 days):")
    display_cols = ['date', 'portfolio_value', 'num_long_positions', 'num_short_positions', 
                    'long_exposure', 'short_exposure', 'net_exposure']
    print(portfolio_df[display_cols].head(10).to_string(index=False))
    
    print("\nPortfolio Value Sample (last 10 days):")
    print(portfolio_df[display_cols].tail(10).to_string(index=False))


def save_results(results, output_prefix='backtest_carry_factor'):
    """
    Save backtest results to CSV files.
    
    Args:
        results (dict): Dictionary containing backtest results
        output_prefix (str): Prefix for output filenames
    """
    # Save portfolio values
    portfolio_file = f"{output_prefix}_portfolio_values.csv"
    results['portfolio_values'].to_csv(portfolio_file, index=False)
    print(f"\nPortfolio values saved to: {portfolio_file}")
    
    # Save trades
    if not results['trades'].empty:
        trades_file = f"{output_prefix}_trades.csv"
        results['trades'].to_csv(trades_file, index=False)
        print(f"Trades history saved to: {trades_file}")
    
    # Save metrics
    metrics_file = f"{output_prefix}_metrics.csv"
    metrics_df = pd.DataFrame([results['metrics']])
    metrics_df.to_csv(metrics_file, index=False)
    print(f"Performance metrics saved to: {metrics_file}")
    
    # Save strategy info
    strategy_file = f"{output_prefix}_strategy_info.csv"
    strategy_df = pd.DataFrame([results['strategy_info']])
    strategy_df.to_csv(strategy_file, index=False)
    print(f"Strategy info saved to: {strategy_file}")


def main():
    """Main execution function for backtest."""
    parser = argparse.ArgumentParser(
        description='Backtest Carry Factor Trading Strategy using Funding Rates',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--price-data',
        type=str,
        default='combined_coinbase_coinmarketcap_daily.csv',
        help='Path to historical OHLCV price data CSV file'
    )
    parser.add_argument(
        '--funding-data',
        type=str,
        default='historical_funding_rates_top100_ALL_HISTORY_20251028_002456.csv',
        help='Path to historical funding rates CSV file (top 100 coins, 2020-present)'
    )
    parser.add_argument(
        '--top-n',
        type=int,
        default=10,
        help='Number of highest funding rate coins to short'
    )
    parser.add_argument(
        '--bottom-n',
        type=int,
        default=10,
        help='Number of lowest funding rate coins to long'
    )
    parser.add_argument(
        '--volatility-window',
        type=int,
        default=30,
        help='Volatility calculation window in days'
    )
    parser.add_argument(
        '--rebalance-days',
        type=int,
        default=7,
        help='Rebalance every N days'
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
        default='backtest_carry_factor',
        help='Prefix for output CSV files'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("CARRY FACTOR BACKTEST")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Price data file: {args.price_data}")
    print(f"  Funding data file: {args.funding_data}")
    print(f"  Long positions (lowest FR): {args.bottom_n} coins")
    print(f"  Short positions (highest FR): {args.top_n} coins")
    print(f"  Volatility window: {args.volatility_window}d")
    print(f"  Rebalance frequency: Every {args.rebalance_days} days")
    print(f"  Initial capital: ${args.initial_capital:,.2f}")
    print(f"  Leverage: {args.leverage}x")
    print(f"  Long allocation: {args.long_allocation:.1%}")
    print(f"  Short allocation: {args.short_allocation:.1%}")
    print(f"  Start date: {args.start_date or 'First available'}")
    print(f"  End date: {args.end_date or 'Last available'}")
    print("=" * 80)
    
    # Load price data
    print("\nLoading price data...")
    price_data = load_price_data(args.price_data)
    print(f"Loaded {len(price_data)} rows for {price_data['base_symbol'].nunique()} symbols")
    print(f"Date range: {price_data['date'].min().date()} to {price_data['date'].max().date()}")
    
    # Load funding rates data
    print("\nLoading funding rates data...")
    funding_data = load_funding_rates(args.funding_data)
    print(f"Loaded {len(funding_data)} rows for {funding_data['coin_symbol'].nunique()} symbols")
    print(f"Date range: {funding_data['date'].min().date()} to {funding_data['date'].max().date()}")
    
    # Run backtest
    print("\nRunning backtest...")
    results = backtest(
        price_data=price_data,
        funding_data=funding_data,
        top_n=args.top_n,
        bottom_n=args.bottom_n,
        volatility_window=args.volatility_window,
        rebalance_days=args.rebalance_days,
        initial_capital=args.initial_capital,
        leverage=args.leverage,
        long_allocation=args.long_allocation,
        short_allocation=args.short_allocation,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    # Print results
    print_results(results)
    
    # Save results
    save_results(results, output_prefix=args.output_prefix)
    
    print("\n" + "=" * 80)
    print("BACKTEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
