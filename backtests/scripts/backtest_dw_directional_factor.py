#!/usr/bin/env python3
"""
Backtest for Durbin-Watson + Directional Factor Strategy (Enhanced)

This script backtests an ENHANCED DW strategy that combines:
1. Durbin-Watson statistic (autocorrelation measure)
2. Recent directional momentum (5-day % change)

Based on analysis showing that DW + Direction provides 4.48% better spread than pure DW.

Strategy Logic:
- LONG candidates:
  * Low-Mid DW + Flat (trend pause before resumption)
  * Low DW + Down (oversold momentum bounce)
  * Mid DW + Up (neutral + momentum continuation)

- SHORT candidates:
  * Low DW + Flat (momentum exhaustion) 
  * Mid + Flat (dead money)
  * Mid-High + Up (mean reversion overextended)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../signals'))


def load_data(filepath):
    """Load historical OHLCV data from CSV file."""
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    required_cols = ['date', 'symbol', 'close']
    optional_cols = ['volume', 'market_cap', 'open', 'high', 'low']
    
    cols_to_keep = required_cols.copy()
    for col in optional_cols:
        if col in df.columns:
            cols_to_keep.append(col)
    
    df = df[cols_to_keep]
    return df


def calculate_durbin_watson(returns, window=30):
    """Calculate Durbin-Watson statistic."""
    if len(returns) < 2:
        return np.nan
    
    clean_returns = returns.dropna()
    if len(clean_returns) < window * 0.7:
        return np.nan
    
    numerator = np.sum(np.diff(clean_returns)**2)
    denominator = np.sum(clean_returns**2)
    
    if denominator == 0 or np.isnan(denominator):
        return np.nan
    
    dw = numerator / denominator
    if dw < 0 or dw > 4.5:
        return np.nan
        
    return dw


def calculate_signals(data, dw_window=30, direction_window=5, 
                     min_volume=5_000_000, min_market_cap=50_000_000):
    """
    Calculate DW + directional signals for all coins.
    """
    df = data.copy()
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Calculate daily log returns
    df['daily_return'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Calculate rolling DW
    df['dw'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=dw_window, min_periods=int(dw_window*0.7)).apply(
            calculate_durbin_watson, raw=False, kwargs={'window': dw_window}
        )
    )
    
    # Calculate directional momentum (% change over direction_window)
    df['pct_chg'] = df.groupby('symbol')['close'].transform(
        lambda x: (x / x.shift(direction_window) - 1)
    )
    
    # Calculate volatility for risk parity weighting
    df['volatility'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=30, min_periods=int(30*0.7)).std() * np.sqrt(365)
    )
    
    # Apply filters
    df['volume_30d_avg'] = df.groupby('symbol')['volume'].transform(
        lambda x: x.rolling(window=30, min_periods=20).mean()
    )
    
    df = df[
        (df['volume_30d_avg'] >= min_volume) & 
        (df['market_cap'] >= min_market_cap)
    ]
    
    # Remove extreme DW values
    df = df[(df['dw'] >= 0.5) & (df['dw'] <= 3.5)]
    
    return df


def classify_dw_bucket(dw_value):
    """Classify DW into buckets based on analysis."""
    if pd.isna(dw_value):
        return None
    elif dw_value < 1.65:
        return 'Low DW'  # Momentum
    elif dw_value < 1.88:
        return 'Low-Mid'  # Slight momentum
    elif dw_value < 2.12:
        return 'Mid'  # Neutral
    elif dw_value < 2.35:
        return 'Mid-High'  # Slight mean reversion
    else:
        return 'High DW'  # Mean reversion


def classify_direction(pct_chg, flat_threshold=0.03):
    """
    Classify direction into Up/Flat/Down.
    flat_threshold: +/- 3% is considered flat
    """
    if pd.isna(pct_chg):
        return None
    elif pct_chg < -flat_threshold:
        return 'Down'
    elif pct_chg > flat_threshold:
        return 'Up'
    else:
        return 'Flat'


def generate_signals(df, date):
    """
    Generate long/short signals based on DW + direction combinations.
    """
    date_data = df[df['date'] == date].copy()
    
    if date_data.empty:
        return {'long': pd.DataFrame(), 'short': pd.DataFrame()}
    
    # Remove NaN values
    date_data = date_data.dropna(subset=['dw', 'pct_chg'])
    
    # Classify each coin
    date_data['dw_bucket'] = date_data['dw'].apply(classify_dw_bucket)
    date_data['direction'] = date_data['pct_chg'].apply(classify_direction)
    
    # Remove any that couldn't be classified
    date_data = date_data.dropna(subset=['dw_bucket', 'direction'])
    
    # Define LONG criteria (based on analysis)
    long_criteria = [
        ('Low-Mid', 'Flat'),   # Best: +2.71% forward
        ('Low DW', 'Down'),    # +1.77% forward, Sharpe 1.94
        ('Mid', 'Up'),         # +1.95% forward, Sharpe 1.31
    ]
    
    # Define SHORT criteria (based on analysis)
    short_criteria = [
        ('Low DW', 'Flat'),    # Worst: -1.29% forward, Sharpe -1.78
        ('Mid', 'Flat'),       # -1.04% forward
        ('Mid-High', 'Up'),    # -0.85% forward
    ]
    
    # Select longs
    long_mask = pd.Series([False] * len(date_data), index=date_data.index)
    for dw_b, dir_b in long_criteria:
        long_mask |= (date_data['dw_bucket'] == dw_b) & (date_data['direction'] == dir_b)
    
    # Select shorts
    short_mask = pd.Series([False] * len(date_data), index=date_data.index)
    for dw_b, dir_b in short_criteria:
        short_mask |= (date_data['dw_bucket'] == dw_b) & (date_data['direction'] == dir_b)
    
    long_df = date_data[long_mask]
    short_df = date_data[short_mask]
    
    return {'long': long_df, 'short': short_df}


def calculate_position_weights(positions_df, weighting_method='equal_weight', total_allocation=0.5):
    """Calculate position weights for a bucket of positions."""
    df = positions_df.copy()
    
    if df.empty:
        return df
    
    if weighting_method == 'equal_weight':
        df['weight'] = total_allocation / len(df)
        
    elif weighting_method == 'risk_parity':
        if 'volatility' not in df.columns or df['volatility'].isna().all():
            df['weight'] = total_allocation / len(df)
        else:
            df['volatility_clean'] = df['volatility'].fillna(df['volatility'].median())
            df['inv_vol'] = 1 / df['volatility_clean']
            df['weight'] = (df['inv_vol'] / df['inv_vol'].sum()) * total_allocation
    
    else:
        raise ValueError(f"Unknown weighting method: {weighting_method}")
    
    return df


def run_backtest(data, dw_window=30, direction_window=5, rebalance_days=7,
                weighting_method='equal_weight', initial_capital=10000,
                leverage=1.0, long_allocation=0.5, short_allocation=0.5,
                min_volume=5_000_000, min_market_cap=50_000_000,
                start_date=None, end_date=None):
    """
    Run the enhanced DW + directional backtest.
    """
    print("=" * 80)
    print("DURBIN-WATSON + DIRECTIONAL FACTOR BACKTEST (ENHANCED)")
    print("=" * 80)
    print(f"\nStrategy: DW + {direction_window}d Direction")
    print(f"DW Window: {dw_window} days")
    print(f"Direction Window: {direction_window} days")
    print(f"Rebalance Frequency: {rebalance_days} days")
    print(f"Weighting Method: {weighting_method}")
    print(f"Long Allocation: {long_allocation*100:.1f}%")
    print(f"Short Allocation: {short_allocation*100:.1f}%")
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print(f"Leverage: {leverage}x")
    
    # Calculate signals
    print("\n" + "-" * 80)
    print("Step 1: Calculating DW + directional signals...")
    signal_data = calculate_signals(
        data, dw_window=dw_window, direction_window=direction_window,
        min_volume=min_volume, min_market_cap=min_market_cap
    )
    print(f"  Valid data points: {len(signal_data):,}")
    
    # Filter by date range
    if start_date:
        signal_data = signal_data[signal_data['date'] >= pd.to_datetime(start_date)]
    if end_date:
        signal_data = signal_data[signal_data['date'] <= pd.to_datetime(end_date)]
    
    # Run backtest
    print("\n" + "-" * 80)
    print("Step 2: Running backtest...")
    
    trading_dates = sorted(signal_data['date'].unique())
    if len(trading_dates) < dw_window + rebalance_days:
        raise ValueError(f"Insufficient data. Need at least {dw_window + rebalance_days} days.")
    
    start_idx = dw_window
    trading_dates = trading_dates[start_idx:]
    
    print(f"  Trading period: {trading_dates[0].date()} to {trading_dates[-1].date()}")
    print(f"  Total trading days: {len(trading_dates)}")
    
    # Initialize portfolio tracking
    portfolio_values = []
    trades = []
    current_positions = {}
    portfolio_value = initial_capital * leverage
    cash = 0
    
    rebalance_dates = trading_dates[::rebalance_days]
    print(f"  Number of rebalances: {len(rebalance_dates)}")
    
    for date_idx, current_date in enumerate(trading_dates):
        if current_date in rebalance_dates:
            # Generate signals
            selected = generate_signals(signal_data, current_date)
            
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
                    'dw': row['dw'],
                    'dw_bucket': row.get('dw_bucket', ''),
                    'pct_chg': row['pct_chg'] * 100,
                    'direction': row.get('direction', ''),
                    'weight': row['weight'],
                    'volatility': row.get('volatility', np.nan),
                })
            
            for _, row in short_positions.iterrows():
                trades.append({
                    'date': current_date,
                    'symbol': row['symbol'],
                    'signal': 'SHORT',
                    'dw': row['dw'],
                    'dw_bucket': row.get('dw_bucket', ''),
                    'pct_chg': row['pct_chg'] * 100,
                    'direction': row.get('direction', ''),
                    'weight': -row['weight'],
                    'volatility': row.get('volatility', np.nan),
                })
            
            # Update current positions
            current_positions = {}
            for _, row in long_positions.iterrows():
                current_positions[row['symbol']] = row['weight']
            for _, row in short_positions.iterrows():
                current_positions[row['symbol']] = -row['weight']
        
        # Calculate daily P&L using next day's returns
        if date_idx < len(trading_dates) - 1:
            next_date = trading_dates[date_idx + 1]
            next_day_data = signal_data[signal_data['date'] == next_date]
            
            daily_pnl = 0
            for symbol, weight in current_positions.items():
                symbol_data = next_day_data[next_day_data['symbol'] == symbol]
                if not symbol_data.empty:
                    daily_return = symbol_data.iloc[0]['daily_return']
                    if not np.isnan(daily_return):
                        daily_pnl += weight * daily_return
            
            portfolio_value = portfolio_value * (1 + daily_pnl)
        
        # Calculate exposures
        long_exposure = sum([w for w in current_positions.values() if w > 0])
        short_exposure = sum([w for w in current_positions.values() if w < 0])
        net_exposure = long_exposure + short_exposure
        gross_exposure = long_exposure + abs(short_exposure)
        
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
        })
    
    # Convert to DataFrames
    portfolio_df = pd.DataFrame(portfolio_values)
    trades_df = pd.DataFrame(trades)
    
    # Calculate metrics
    print("\n" + "-" * 80)
    print("Step 3: Calculating performance metrics...")
    metrics = calculate_metrics(portfolio_df, initial_capital, leverage)
    
    # Calculate strategy info
    strategy_info = {
        'strategy': 'dw_directional',
        'dw_window': dw_window,
        'direction_window': direction_window,
        'rebalance_days': rebalance_days,
        'weighting_method': weighting_method,
        'initial_capital': initial_capital,
        'leverage': leverage,
        'long_allocation': long_allocation,
        'short_allocation': short_allocation,
        'avg_long_positions': metrics.get('avg_long_positions', 0),
        'avg_short_positions': metrics.get('avg_short_positions', 0),
    }
    
    return {
        'portfolio_values': portfolio_df,
        'trades': trades_df,
        'metrics': metrics,
        'strategy_info': strategy_info
    }


def calculate_metrics(portfolio_df, initial_capital, leverage):
    """Calculate performance metrics from portfolio values."""
    if portfolio_df.empty:
        return {}
    
    portfolio_df['daily_return'] = portfolio_df['portfolio_value'].pct_change()
    
    final_value = portfolio_df['portfolio_value'].iloc[-1]
    initial_value = initial_capital * leverage
    total_return = (final_value - initial_value) / initial_value
    
    num_days = len(portfolio_df)
    annualized_return = (1 + total_return) ** (365 / num_days) - 1
    
    annualized_volatility = portfolio_df['daily_return'].std() * np.sqrt(365)
    sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility > 0 else 0
    
    downside_returns = portfolio_df['daily_return'][portfolio_df['daily_return'] < 0]
    downside_volatility = downside_returns.std() * np.sqrt(365) if len(downside_returns) > 0 else 0
    sortino_ratio = annualized_return / downside_volatility if downside_volatility > 0 else 0
    
    cumulative_returns = (1 + portfolio_df['daily_return']).cumprod()
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max
    max_drawdown = drawdown.min()
    
    calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
    win_rate = (portfolio_df['daily_return'] > 0).sum() / len(portfolio_df)
    
    avg_long_exposure = portfolio_df['long_exposure'].mean()
    avg_short_exposure = portfolio_df['short_exposure'].mean()
    avg_net_exposure = portfolio_df['net_exposure'].mean()
    avg_gross_exposure = portfolio_df['gross_exposure'].mean()
    
    avg_long_positions = portfolio_df['num_longs'].mean()
    avg_short_positions = portfolio_df['num_shorts'].mean()
    
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
    }
    
    return metrics


def print_results(results):
    """Print backtest results in a formatted way."""
    metrics = results['metrics']
    strategy_info = results['strategy_info']
    
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)
    
    print("\nStrategy Configuration:")
    print(f"  Strategy:               {strategy_info['strategy']}")
    print(f"  DW Window:              {strategy_info['dw_window']} days")
    print(f"  Direction Window:       {strategy_info['direction_window']} days")
    print(f"  Rebalance Frequency:    {strategy_info['rebalance_days']} days")
    print(f"  Weighting Method:       {strategy_info['weighting_method']}")
    
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
    
    print("\n" + "=" * 80)


def save_results(results, output_prefix):
    """Save backtest results to CSV files."""
    output_dir = os.path.dirname(output_prefix) or '.'
    os.makedirs(output_dir, exist_ok=True)
    
    portfolio_file = f"{output_prefix}_portfolio_values.csv"
    results['portfolio_values'].to_csv(portfolio_file, index=False)
    print(f"\n✓ Saved portfolio values to: {portfolio_file}")
    
    trades_file = f"{output_prefix}_trades.csv"
    results['trades'].to_csv(trades_file, index=False)
    print(f"✓ Saved trades to: {trades_file}")
    
    metrics_file = f"{output_prefix}_metrics.csv"
    metrics_df = pd.DataFrame([results['metrics']]).T
    metrics_df.columns = ['value']
    metrics_df.to_csv(metrics_file)
    print(f"✓ Saved metrics to: {metrics_file}")
    
    strategy_file = f"{output_prefix}_strategy_info.csv"
    strategy_df = pd.DataFrame([results['strategy_info']])
    strategy_df.to_csv(strategy_file, index=False)
    print(f"✓ Saved strategy info to: {strategy_file}")


def main():
    """Main function to run enhanced DW + directional backtest."""
    parser = argparse.ArgumentParser(description='Backtest DW + Directional factor strategy')
    
    parser.add_argument('--price-data', type=str,
                       default='data/raw/combined_coinbase_coinmarketcap_daily.csv',
                       help='Path to historical OHLCV CSV file')
    
    parser.add_argument('--dw-window', type=int, default=30,
                       help='DW calculation window in days')
    parser.add_argument('--direction-window', type=int, default=5,
                       help='Direction calculation window in days')
    parser.add_argument('--rebalance-days', type=int, default=7,
                       help='Rebalance frequency in days')
    parser.add_argument('--weighting-method', type=str, default='equal_weight',
                       choices=['equal_weight', 'risk_parity'],
                       help='Position weighting method')
    
    parser.add_argument('--initial-capital', type=float, default=10000,
                       help='Initial capital in USD')
    parser.add_argument('--leverage', type=float, default=1.0,
                       help='Leverage multiplier')
    parser.add_argument('--long-allocation', type=float, default=0.5,
                       help='Allocation to long side (0-1)')
    parser.add_argument('--short-allocation', type=float, default=0.5,
                       help='Allocation to short side (0-1)')
    
    parser.add_argument('--min-volume', type=float, default=5_000_000,
                       help='Minimum 30-day average volume in USD')
    parser.add_argument('--min-market-cap', type=float, default=50_000_000,
                       help='Minimum market cap in USD')
    
    parser.add_argument('--start-date', type=str, default=None,
                       help='Backtest start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default=None,
                       help='Backtest end date (YYYY-MM-DD)')
    
    parser.add_argument('--output-prefix', type=str,
                       default='backtests/results/backtest_dw_directional',
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
        dw_window=args.dw_window,
        direction_window=args.direction_window,
        rebalance_days=args.rebalance_days,
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
