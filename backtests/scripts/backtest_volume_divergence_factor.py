#!/usr/bin/env python3
"""
Backtest for Volume Divergence Factor Strategy

This script backtests a volume divergence strategy that:
1. Calculates volume-price divergence metrics for all cryptocurrencies
2. Ranks cryptocurrencies by divergence characteristics
3. Creates long/short portfolios based on volume-price relationships:
   - Long position: Coins with strong confirmation (price and volume agree)
   - Short position: Coins with divergence (price and volume disagree)
4. Uses equal-weight or volume-weighted portfolio construction
5. Rebalances periodically
6. Tracks portfolio performance over time

Volume divergence hypothesis: Moves confirmed by volume continue; divergent moves reverse.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import sys
import os

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'signals'))


def calculate_volume_divergence_metrics(data, lookback_window=30, vmi_short=10, vmi_long=30):
    """
    Calculate volume divergence metrics.
    
    Args:
        data (pd.DataFrame): DataFrame with date, symbol, close, volume columns
        lookback_window (int): Window for correlation and momentum calculations
        vmi_short (int): Short window for VMI calculation
        vmi_long (int): Long window for VMI calculation
        
    Returns:
        pd.DataFrame: DataFrame with volume divergence metrics
    """
    df = data.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    print(f"Calculating volume divergence metrics...")
    print(f"  Lookback window: {lookback_window} days")
    print(f"  VMI windows: {vmi_short}d / {vmi_long}d")
    
    # Calculate price changes (log returns)
    df['price_change'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Calculate volume changes (log changes)
    df['volume_change'] = df.groupby('symbol')['volume'].transform(
        lambda x: np.log(x.replace(0, np.nan) / x.shift(1).replace(0, np.nan))
    )
    
    # Calculate price momentum (N-day return)
    df['price_momentum'] = df.groupby('symbol')['close'].transform(
        lambda x: (x - x.shift(lookback_window)) / x.shift(lookback_window)
    )
    
    # Calculate volume moving averages
    df['volume_ma_short'] = df.groupby('symbol')['volume'].transform(
        lambda x: x.rolling(vmi_short, min_periods=vmi_short).mean()
    )
    df['volume_ma_long'] = df.groupby('symbol')['volume'].transform(
        lambda x: x.rolling(vmi_long, min_periods=vmi_long).mean()
    )
    
    # Volume Momentum Indicator (VMI)
    df['vmi'] = (df['volume_ma_short'] - df['volume_ma_long']) / df['volume_ma_long']
    
    # Price-Volume Correlation (PVC) - rolling correlation
    def rolling_corr(group):
        price_ch = group['price_change']
        volume_ch = group['volume_change']
        
        # Use rolling window to calculate correlation
        result = []
        for i in range(len(group)):
            if i < lookback_window - 1:
                result.append(np.nan)
            else:
                window_price = price_ch.iloc[i - lookback_window + 1:i + 1]
                window_volume = volume_ch.iloc[i - lookback_window + 1:i + 1]
                
                # Remove NaN values
                valid_mask = ~(window_price.isna() | window_volume.isna())
                window_price_clean = window_price[valid_mask]
                window_volume_clean = window_volume[valid_mask]
                
                if len(window_price_clean) >= lookback_window * 0.8:  # Need at least 80% valid data
                    corr = window_price_clean.corr(window_volume_clean)
                    result.append(corr)
                else:
                    result.append(np.nan)
        
        return pd.Series(result, index=group.index)
    
    print("  Calculating price-volume correlation...")
    df['pvc'] = df.groupby('symbol').apply(rolling_corr).reset_index(level=0, drop=True)
    
    # Divergence Score - combines price momentum and volume momentum
    # Positive when price and volume agree (confirmation)
    # Negative when price and volume disagree (divergence)
    price_sign = np.sign(df['price_momentum'])
    volume_sign = np.sign(df['vmi'])
    
    df['divergence_score'] = (
        price_sign * volume_sign * 
        np.abs(df['price_momentum']) * 
        (1 + np.abs(df['vmi']))
    )
    
    # Replace infinities with NaN
    df = df.replace([np.inf, -np.inf], np.nan)
    
    return df


def load_data(filepath):
    """Load historical OHLCV data from CSV file."""
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    return df


def select_symbols_by_divergence(
    divergence_df,
    date,
    strategy='confirmation_premium',
    metric='divergence_score',
    num_quintiles=5
):
    """
    Select cryptocurrencies for long/short portfolios based on volume divergence.
    
    Args:
        divergence_df (pd.DataFrame): Divergence data
        date (pd.Timestamp): Date to rank on
        strategy (str): Strategy type
        metric (str): Metric to rank on ('divergence_score', 'pvc', 'vmi')
        num_quintiles (int): Number of quintiles
        
    Returns:
        dict: {'long': [symbols], 'short': [symbols]}
    """
    # Get data for this specific date
    date_data = divergence_df[divergence_df['date'] == date].copy()
    
    if date_data.empty:
        return {'long': [], 'short': []}
    
    # Remove any NaN values in the metric
    date_data = date_data.dropna(subset=[metric])
    
    # Filter by volume (minimum $5M average volume)
    if 'volume_ma_long' in date_data.columns:
        date_data = date_data[date_data['volume_ma_long'] > 5000000]
    
    if len(date_data) < num_quintiles:
        return {'long': [], 'short': []}
    
    # Rank by metric
    date_data['rank'] = date_data[metric].rank(ascending=False, method='first')
    date_data['percentile'] = date_data['rank'] / len(date_data) * 100
    
    # Calculate quintile size
    quintile_size = len(date_data) // num_quintiles
    
    long_symbols = []
    short_symbols = []
    
    if strategy == 'confirmation_premium':
        # Long: High divergence score (confirmation)
        # Short: Low divergence score (divergence)
        long_symbols = date_data.nsmallest(quintile_size, 'rank')['symbol'].tolist()
        short_symbols = date_data.nlargest(quintile_size, 'rank')['symbol'].tolist()
    
    elif strategy == 'volume_momentum':
        # Long: High VMI (expanding volume)
        # Short: Low VMI (contracting volume)
        if metric != 'vmi':
            print(f"Warning: volume_momentum strategy should use vmi metric, got {metric}")
        long_symbols = date_data.nsmallest(quintile_size, 'rank')['symbol'].tolist()
        short_symbols = date_data.nlargest(quintile_size, 'rank')['symbol'].tolist()
    
    elif strategy == 'contrarian_divergence':
        # Long: Low divergence score (divergence - bet on reversal)
        # Short: High divergence score (confirmation - bet on reversal)
        long_symbols = date_data.nlargest(quintile_size, 'rank')['symbol'].tolist()
        short_symbols = date_data.nsmallest(quintile_size, 'rank')['symbol'].tolist()
    
    elif strategy == 'high_correlation':
        # Long only: High PVC (strong confirmation)
        if metric != 'pvc':
            print(f"Warning: high_correlation strategy should use pvc metric, got {metric}")
        long_symbols = date_data.nsmallest(quintile_size, 'rank')['symbol'].tolist()
        short_symbols = []
    
    return {'long': long_symbols, 'short': short_symbols}


def run_backtest(
    price_data,
    strategy='confirmation_premium',
    metric='divergence_score',
    lookback_window=30,
    vmi_short=10,
    vmi_long=30,
    num_quintiles=5,
    rebalance_days=7,
    start_date=None,
    end_date=None,
    initial_capital=10000,
    leverage=1.0,
    long_allocation=0.5,
    short_allocation=0.5,
    weighting_method='equal'
):
    """
    Run backtest for the volume divergence factor strategy.
    
    Args:
        price_data (pd.DataFrame): Historical OHLCV data
        strategy (str): Strategy type
        metric (str): Primary metric to rank on
        lookback_window (int): Window for correlation and momentum
        vmi_short (int): Short window for VMI
        vmi_long (int): Long window for VMI
        num_quintiles (int): Number of quintiles for ranking
        rebalance_days (int): Rebalance every N days
        start_date (str): Start date for backtest
        end_date (str): End date for backtest
        initial_capital (float): Initial portfolio capital
        leverage (float): Leverage multiplier
        long_allocation (float): Allocation to long side
        short_allocation (float): Allocation to short side
        weighting_method (str): 'equal' or 'volume_weighted'
        
    Returns:
        dict: Dictionary containing backtest results
    """
    # Filter data by date range if specified
    if start_date:
        price_data = price_data[price_data['date'] >= pd.to_datetime(start_date)]
    if end_date:
        price_data = price_data[price_data['date'] <= pd.to_datetime(end_date)]
    
    # Calculate volume divergence metrics
    divergence_df = calculate_volume_divergence_metrics(
        price_data,
        lookback_window=lookback_window,
        vmi_short=vmi_short,
        vmi_long=vmi_long
    )
    
    # Get unique dates for rebalancing
    all_dates = sorted(divergence_df['date'].unique())
    
    # Need enough data for calculations
    min_required_days = max(lookback_window, vmi_long) + 10
    
    if len(all_dates) < min_required_days:
        raise ValueError(f"Insufficient data. Need at least {min_required_days} days, have {len(all_dates)}")
    
    # Start backtest after minimum required period
    backtest_start_idx = max(lookback_window, vmi_long)
    backtest_dates = all_dates[backtest_start_idx::rebalance_days]  # Rebalance every N days
    
    if len(backtest_dates) == 0:
        backtest_dates = [all_dates[-1]]
    
    print(f"\nBacktest Configuration:")
    print(f"  Strategy: {strategy}")
    print(f"  Metric: {metric}")
    print(f"  Period: {backtest_dates[0].date()} to {backtest_dates[-1].date()}")
    print(f"  Trading days: {len(all_dates[backtest_start_idx:])}")
    print(f"  Rebalance frequency: Every {rebalance_days} days ({len(backtest_dates)} rebalances)")
    print(f"  Lookback window: {lookback_window}d")
    print(f"  VMI windows: {vmi_short}d / {vmi_long}d")
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
    
    # Calculate daily returns
    data_with_returns = price_data.copy()
    data_with_returns['daily_return'] = data_with_returns.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Track daily portfolio value
    daily_tracking_dates = all_dates[backtest_start_idx:]
    
    for date_idx, current_date in enumerate(daily_tracking_dates):
        # Check if it's a rebalancing day
        is_rebalance_day = (
            last_rebalance_date is None or 
            current_date in backtest_dates or
            (current_date - last_rebalance_date).days >= rebalance_days
        )
        
        if is_rebalance_day:
            # Get divergence data up to current date
            historical_divergence = divergence_df[divergence_df['date'] <= current_date]
            
            # Select symbols based on volume divergence strategy
            selected = select_symbols_by_divergence(
                historical_divergence,
                current_date,
                strategy=strategy,
                metric=metric,
                num_quintiles=num_quintiles
            )
            
            long_symbols = selected['long']
            short_symbols = selected['short']
            
            new_weights = {}
            
            if len(long_symbols) + len(short_symbols) > 0:
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
                
                elif weighting_method == 'volume_weighted':
                    # Weight by volume
                    current_div_data = historical_divergence[historical_divergence['date'] == current_date]
                    
                    # Get volumes for longs and shorts
                    long_volumes = {}
                    short_volumes = {}
                    
                    for _, row in current_div_data.iterrows():
                        if not pd.isna(row['volume_ma_long']) and row['volume_ma_long'] > 0:
                            if row['symbol'] in long_symbols:
                                long_volumes[row['symbol']] = row['volume_ma_long']
                            elif row['symbol'] in short_symbols:
                                short_volumes[row['symbol']] = row['volume_ma_long']
                    
                    # Calculate volume-weighted allocations
                    if long_volumes:
                        total_long_volume = sum(long_volumes.values())
                        for symbol, volume in long_volumes.items():
                            new_weights[symbol] = (volume / total_long_volume) * long_allocation * leverage
                    
                    if short_volumes:
                        total_short_volume = sum(short_volumes.values())
                        for symbol, volume in short_volumes.items():
                            new_weights[symbol] = -(volume / total_short_volume) * short_allocation * leverage
                
                # Record trades
                for symbol, new_weight in new_weights.items():
                    old_weight = current_weights.get(symbol, 0)
                    if abs(new_weight - old_weight) > 0.001:
                        # Get divergence metrics for this symbol
                        symbol_data = historical_divergence[
                            (historical_divergence['date'] == current_date) &
                            (historical_divergence['symbol'] == symbol)
                        ]
                        
                        if not symbol_data.empty:
                            trades_history.append({
                                'date': current_date,
                                'symbol': symbol,
                                'old_weight': old_weight,
                                'new_weight': new_weight,
                                'weight_change': new_weight - old_weight,
                                'divergence_score': symbol_data.iloc[0].get('divergence_score', np.nan),
                                'pvc': symbol_data.iloc[0].get('pvc', np.nan),
                                'vmi': symbol_data.iloc[0].get('vmi', np.nan),
                                'price_momentum': symbol_data.iloc[0].get('price_momentum', np.nan),
                                'position_type': 'long' if new_weight > 0 else 'short'
                            })
                
                # Exit positions not in new portfolio
                for symbol in list(current_weights.keys()):
                    if symbol not in new_weights:
                        trades_history.append({
                            'date': current_date,
                            'symbol': symbol,
                            'old_weight': current_weights[symbol],
                            'new_weight': 0,
                            'weight_change': -current_weights[symbol],
                            'divergence_score': np.nan,
                            'pvc': np.nan,
                            'vmi': np.nan,
                            'price_momentum': np.nan,
                            'position_type': 'exit'
                        })
                
                current_weights = new_weights
                last_rebalance_date = current_date
        
        # Calculate portfolio return for this day using NEXT day's returns (no lookahead)
        if date_idx < len(daily_tracking_dates) - 1:
            next_date = daily_tracking_dates[date_idx + 1]
            
            # Get next day's returns for all symbols in portfolio
            next_day_returns = data_with_returns[data_with_returns['date'] == next_date]
            
            portfolio_return = 0
            for symbol, weight in current_weights.items():
                symbol_return = next_day_returns[next_day_returns['symbol'] == symbol]['daily_return']
                if not symbol_return.empty and not pd.isna(symbol_return.iloc[0]):
                    portfolio_return += weight * symbol_return.iloc[0]
            
            # Update capital
            current_capital = current_capital * np.exp(portfolio_return)
        
        # Record portfolio state
        long_exposure = sum([w for w in current_weights.values() if w > 0])
        short_exposure = sum([abs(w) for w in current_weights.values() if w < 0])
        
        # Calculate average divergence metrics for long and short positions
        current_div_data = divergence_df[divergence_df['date'] == current_date]
        
        avg_div_long = np.nan
        avg_div_short = np.nan
        if not current_div_data.empty:
            long_syms = [s for s, w in current_weights.items() if w > 0]
            short_syms = [s for s, w in current_weights.items() if w < 0]
            
            if long_syms:
                long_data = current_div_data[current_div_data['symbol'].isin(long_syms)]
                avg_div_long = long_data['divergence_score'].mean()
            
            if short_syms:
                short_data = current_div_data[current_div_data['symbol'].isin(short_syms)]
                avg_div_short = short_data['divergence_score'].mean()
        
        portfolio_values.append({
            'date': current_date,
            'portfolio_value': current_capital,
            'num_long_positions': len([w for w in current_weights.values() if w > 0]),
            'num_short_positions': len([w for w in current_weights.values() if w < 0]),
            'long_exposure': long_exposure,
            'short_exposure': short_exposure,
            'net_exposure': long_exposure - short_exposure,
            'gross_exposure': long_exposure + short_exposure,
            'avg_divergence_long': avg_div_long,
            'avg_divergence_short': avg_div_short
        })
        
        if (date_idx + 1) % 50 == 0:
            print(f"  Progress: {date_idx + 1}/{len(daily_tracking_dates)} days | "
                  f"Portfolio value: ${current_capital:,.2f} | "
                  f"Positions: {len(current_weights)}")
    
    # Create result DataFrames
    portfolio_df = pd.DataFrame(portfolio_values)
    trades_df = pd.DataFrame(trades_history)
    
    # Calculate performance metrics
    portfolio_df['daily_return'] = portfolio_df['portfolio_value'].pct_change()
    
    total_return = (current_capital - initial_capital) / initial_capital
    days = len(portfolio_df)
    annualized_return = (1 + total_return) ** (365 / days) - 1
    annualized_volatility = portfolio_df['daily_return'].std() * np.sqrt(365)
    sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility > 0 else 0
    
    # Calculate drawdown
    portfolio_df['cumulative_max'] = portfolio_df['portfolio_value'].cummax()
    portfolio_df['drawdown'] = (portfolio_df['portfolio_value'] - portfolio_df['cumulative_max']) / portfolio_df['cumulative_max']
    max_drawdown = portfolio_df['drawdown'].min()
    
    # Sortino ratio (downside volatility)
    downside_returns = portfolio_df['daily_return'][portfolio_df['daily_return'] < 0]
    downside_volatility = downside_returns.std() * np.sqrt(365) if len(downside_returns) > 0 else 0
    sortino_ratio = annualized_return / downside_volatility if downside_volatility > 0 else 0
    
    # Calmar ratio
    calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
    
    # Win rate
    win_rate = len(portfolio_df[portfolio_df['daily_return'] > 0]) / len(portfolio_df[portfolio_df['daily_return'].notna()])
    
    metrics = {
        'initial_capital': initial_capital,
        'final_value': current_capital,
        'total_return': total_return,
        'annualized_return': annualized_return,
        'annualized_volatility': annualized_volatility,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'max_drawdown': max_drawdown,
        'calmar_ratio': calmar_ratio,
        'win_rate': win_rate,
        'total_days': days,
        'num_rebalances': len(backtest_dates),
        'avg_long_positions': portfolio_df['num_long_positions'].mean(),
        'avg_short_positions': portfolio_df['num_short_positions'].mean(),
        'avg_divergence_long': portfolio_df['avg_divergence_long'].mean(),
        'avg_divergence_short': portfolio_df['avg_divergence_short'].mean()
    }
    
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)
    print(f"Initial Capital:        ${metrics['initial_capital']:,.2f}")
    print(f"Final Value:            ${metrics['final_value']:,.2f}")
    print(f"Total Return:           {metrics['total_return']:.2%}")
    print(f"Annualized Return:      {metrics['annualized_return']:.2%}")
    print(f"Annualized Volatility:  {metrics['annualized_volatility']:.2%}")
    print(f"Sharpe Ratio:           {metrics['sharpe_ratio']:.3f}")
    print(f"Sortino Ratio:          {metrics['sortino_ratio']:.3f}")
    print(f"Maximum Drawdown:       {metrics['max_drawdown']:.2%}")
    print(f"Calmar Ratio:           {metrics['calmar_ratio']:.3f}")
    print(f"Win Rate:               {metrics['win_rate']:.2%}")
    print(f"Total Days:             {metrics['total_days']}")
    print(f"Number of Rebalances:   {metrics['num_rebalances']}")
    print(f"Avg Long Positions:     {metrics['avg_long_positions']:.1f}")
    print(f"Avg Short Positions:    {metrics['avg_short_positions']:.1f}")
    print(f"Avg Divergence (Long):  {metrics['avg_divergence_long']:.3f}")
    print(f"Avg Divergence (Short): {metrics['avg_divergence_short']:.3f}")
    print("=" * 80)
    
    return {
        'portfolio_values': portfolio_df,
        'trades': trades_df,
        'metrics': metrics,
        'divergence_data': divergence_df
    }


def save_results(results, output_prefix='backtest_volume_divergence'):
    """Save backtest results to CSV files."""
    output_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
    os.makedirs(output_dir, exist_ok=True)
    
    # Save portfolio values
    portfolio_file = os.path.join(output_dir, f'{output_prefix}_portfolio_values.csv')
    results['portfolio_values'].to_csv(portfolio_file, index=False)
    print(f"\nSaved portfolio values to: {portfolio_file}")
    
    # Save trades
    trades_file = os.path.join(output_dir, f'{output_prefix}_trades.csv')
    results['trades'].to_csv(trades_file, index=False)
    print(f"Saved trades to: {trades_file}")
    
    # Save metrics
    metrics_file = os.path.join(output_dir, f'{output_prefix}_metrics.csv')
    metrics_df = pd.DataFrame([results['metrics']])
    metrics_df.to_csv(metrics_file, index=False)
    print(f"Saved metrics to: {metrics_file}")
    
    print(f"\nAll results saved to: {output_dir}/")


def main():
    parser = argparse.ArgumentParser(description='Backtest Volume Divergence Factor Strategy')
    
    parser.add_argument('--price-data', type=str, 
                        default='data/raw/combined_coinbase_coinmarketcap_daily.csv',
                        help='Path to historical OHLCV CSV file')
    parser.add_argument('--strategy', type=str, default='confirmation_premium',
                        choices=['confirmation_premium', 'volume_momentum', 'contrarian_divergence', 'high_correlation'],
                        help='Volume divergence strategy variant')
    parser.add_argument('--metric', type=str, default='divergence_score',
                        choices=['divergence_score', 'pvc', 'vmi'],
                        help='Primary metric to rank on')
    parser.add_argument('--lookback-window', type=int, default=30,
                        help='Lookback window for correlation and momentum (days)')
    parser.add_argument('--vmi-short-window', type=int, default=10,
                        help='Short window for VMI calculation (days)')
    parser.add_argument('--vmi-long-window', type=int, default=30,
                        help='Long window for VMI calculation (days)')
    parser.add_argument('--num-quintiles', type=int, default=5,
                        help='Number of quintiles for ranking')
    parser.add_argument('--rebalance-days', type=int, default=7,
                        help='Rebalance frequency (days)')
    parser.add_argument('--weighting-method', type=str, default='equal',
                        choices=['equal', 'volume_weighted'],
                        help='Portfolio weighting method')
    parser.add_argument('--initial-capital', type=float, default=10000,
                        help='Initial portfolio capital (USD)')
    parser.add_argument('--leverage', type=float, default=1.0,
                        help='Leverage multiplier')
    parser.add_argument('--long-allocation', type=float, default=0.5,
                        help='Allocation to long side (0-1)')
    parser.add_argument('--short-allocation', type=float, default=0.5,
                        help='Allocation to short side (0-1)')
    parser.add_argument('--start-date', type=str, default=None,
                        help='Backtest start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default=None,
                        help='Backtest end date (YYYY-MM-DD)')
    parser.add_argument('--output-prefix', type=str, default='backtest_volume_divergence',
                        help='Prefix for output files')
    
    args = parser.parse_args()
    
    print("\n" + "=" * 80)
    print("VOLUME DIVERGENCE FACTOR BACKTEST")
    print("=" * 80)
    
    # Load data
    print(f"\nLoading data from: {args.price_data}")
    price_data = load_data(args.price_data)
    print(f"Loaded {len(price_data)} rows, {price_data['symbol'].nunique()} unique symbols")
    print(f"Date range: {price_data['date'].min().date()} to {price_data['date'].max().date()}")
    
    # Run backtest
    results = run_backtest(
        price_data,
        strategy=args.strategy,
        metric=args.metric,
        lookback_window=args.lookback_window,
        vmi_short=args.vmi_short_window,
        vmi_long=args.vmi_long_window,
        num_quintiles=args.num_quintiles,
        rebalance_days=args.rebalance_days,
        start_date=args.start_date,
        end_date=args.end_date,
        initial_capital=args.initial_capital,
        leverage=args.leverage,
        long_allocation=args.long_allocation,
        short_allocation=args.short_allocation,
        weighting_method=args.weighting_method
    )
    
    # Save results
    save_results(results, output_prefix=args.output_prefix)
    
    print("\n" + "=" * 80)
    print("BACKTEST COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
