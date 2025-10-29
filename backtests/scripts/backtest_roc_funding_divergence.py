#!/usr/bin/env python3
"""
Backtest for RoC vs Funding DIVERGENCE Strategy

This script tests a divergence-based approach:
- Calculate RoC-Funding spread for all coins
- Identify EXTREME divergences (z-score > threshold)
- Only trade when divergence is significant
- Test both mean reversion and momentum continuation

Key difference from factor approach:
- Factor: Rank all coins, long top quintile, short bottom quintile
- Divergence: Only trade individual coins with extreme spreads

Hypotheses to test:
1. Mean Reversion: Extreme divergences correct
   - Very positive spread (RoC >> Funding) → SHORT (overbought)
   - Very negative spread (RoC << Funding) → LONG (oversold)

2. Momentum Continuation: Extreme divergences signal strength
   - Very positive spread (RoC >> Funding) → LONG (strong momentum)
   - Very negative spread (RoC << Funding) → SHORT (weak with high costs)

3. Asymmetric: Only trade one side
   - Only short extreme positive spreads (funding too low)
   - Only long extreme negative spreads (funding too high)
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
    """Load historical OHLCV price data from CSV file."""
    print(f"Loading price data from {filepath}...")
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    required_cols = ['date', 'symbol', 'close']
    optional_cols = ['volume', 'market_cap', 'open', 'high', 'low', 'base']
    
    cols_to_keep = required_cols.copy()
    for col in optional_cols:
        if col in df.columns:
            cols_to_keep.append(col)
    
    df = df[cols_to_keep]
    
    if 'base' in df.columns:
        df['base_symbol'] = df['base']
    else:
        df['base_symbol'] = df['symbol'].str.split('/').str[0]
    
    print(f"  Loaded {len(df)} rows for {df['symbol'].nunique()} symbols")
    return df


def load_funding_data(filepath):
    """Load historical funding rates from CSV file."""
    print(f"Loading funding data from {filepath}...")
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['coin_symbol', 'date']).reset_index(drop=True)
    
    required_cols = ['date', 'coin_symbol', 'funding_rate_pct']
    
    if not all(col in df.columns for col in required_cols):
        if 'funding_rate' in df.columns:
            df['funding_rate_pct'] = df['funding_rate'] * 100
    
    df = df[required_cols]
    print(f"  Loaded {len(df)} rows for {df['coin_symbol'].nunique()} symbols")
    return df


def merge_price_and_funding(price_df, funding_df):
    """Merge price and funding data on date and symbol."""
    print("Merging price and funding data...")
    
    merged = price_df.merge(
        funding_df,
        left_on=['date', 'base_symbol'],
        right_on=['date', 'coin_symbol'],
        how='left'
    )
    
    total_rows = len(merged)
    rows_with_funding = merged['funding_rate_pct'].notna().sum()
    pct_with_funding = rows_with_funding / total_rows * 100
    
    print(f"  Merged data: {total_rows} rows")
    print(f"  Rows with funding data: {rows_with_funding} ({pct_with_funding:.1f}%)")
    print(f"  Symbols with funding: {merged[merged['funding_rate_pct'].notna()]['base_symbol'].nunique()}")
    
    return merged


def calculate_roc(data, window=30):
    """Calculate rolling Rate of Change (RoC)."""
    df = data.copy()
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    df['roc_pct'] = df.groupby('symbol')['close'].transform(
        lambda x: (x / x.shift(window) - 1) * 100
    )
    
    return df


def calculate_cumulative_funding(data, window=30):
    """Calculate cumulative funding rate over rolling window."""
    df = data.copy()
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    df['cum_funding_pct'] = df.groupby('symbol')['funding_rate_pct'].transform(
        lambda x: x.rolling(window=window, min_periods=int(window*0.7)).sum()
    )
    
    return df


def calculate_roc_funding_spread(data, window=30):
    """Calculate RoC minus cumulative funding spread."""
    print(f"Calculating RoC-Funding spread with {window}-day window...")
    
    df = calculate_roc(data, window)
    df = calculate_cumulative_funding(df, window)
    df['spread_pct'] = df['roc_pct'] - df['cum_funding_pct']
    
    valid_spreads = df['spread_pct'].dropna()
    if len(valid_spreads) > 0:
        print(f"  Spread statistics:")
        print(f"    Mean: {valid_spreads.mean():.2f}%")
        print(f"    Median: {valid_spreads.median():.2f}%")
        print(f"    Std: {valid_spreads.std():.2f}%")
        print(f"    Min: {valid_spreads.min():.2f}%")
        print(f"    Max: {valid_spreads.max():.2f}%")
    
    return df


def calculate_spread_zscore(data, zscore_window=90):
    """
    Calculate z-score of spread for divergence detection.
    
    Z-score = (spread - rolling_mean) / rolling_std
    
    Extreme z-scores indicate divergence:
    - z > +2: RoC much higher than funding (unusual)
    - z < -2: RoC much lower than funding (unusual)
    """
    df = data.copy()
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Calculate rolling mean and std of spread
    df['spread_mean'] = df.groupby('symbol')['spread_pct'].transform(
        lambda x: x.rolling(window=zscore_window, min_periods=int(zscore_window*0.7)).mean()
    )
    
    df['spread_std'] = df.groupby('symbol')['spread_pct'].transform(
        lambda x: x.rolling(window=zscore_window, min_periods=int(zscore_window*0.7)).std()
    )
    
    # Calculate z-score
    df['spread_zscore'] = (df['spread_pct'] - df['spread_mean']) / df['spread_std']
    
    # Replace inf with NaN
    df['spread_zscore'] = df['spread_zscore'].replace([np.inf, -np.inf], np.nan)
    
    return df


def calculate_volatility(data, window=30):
    """Calculate rolling volatility (annualized)."""
    df = data.copy()
    
    df['daily_return'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    df['volatility'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=window, min_periods=int(window*0.7)).std() * np.sqrt(365)
    )
    
    return df


def filter_universe(data, min_volume=5_000_000, min_market_cap=50_000_000):
    """Filter cryptocurrency universe by liquidity and market cap."""
    df = data.copy()
    initial_symbols = df['symbol'].nunique()
    
    if 'volume' in df.columns:
        df['volume_30d_avg'] = df.groupby('symbol')['volume'].transform(
            lambda x: x.rolling(window=30, min_periods=20).mean()
        )
        df = df[df['volume_30d_avg'] >= min_volume]
    
    if 'market_cap' in df.columns:
        df = df[df['market_cap'] >= min_market_cap]
    
    # Must have funding and spread data
    df = df[df['funding_rate_pct'].notna()]
    df = df[df['spread_pct'].notna()]
    
    final_symbols = df['symbol'].nunique()
    print(f"  Universe filtered: {initial_symbols} → {final_symbols} symbols")
    
    return df


def generate_divergence_signals(data, date, strategy='mean_reversion',
                                zscore_threshold=2.0, min_spread_abs=20.0):
    """
    Generate trading signals based on extreme divergences.
    
    Args:
        data: DataFrame with spread_zscore column
        date: Date to generate signals for
        strategy: 'mean_reversion', 'momentum_continuation', 'short_expensive_longs', 'long_cheap_shorts'
        zscore_threshold: Absolute z-score threshold for extreme (e.g., 2.0 = 2 std devs)
        min_spread_abs: Minimum absolute spread to trade (filter noise)
        
    Returns:
        DataFrame with signals
    """
    date_data = data[data['date'] == date].copy()
    
    if date_data.empty:
        return pd.DataFrame()
    
    # Remove NaN z-scores
    date_data = date_data.dropna(subset=['spread_zscore', 'spread_pct'])
    
    if len(date_data) == 0:
        return pd.DataFrame()
    
    # Initialize signal column
    date_data['signal'] = 0
    
    # Filter for extreme divergences (high absolute z-score)
    date_data['is_extreme'] = np.abs(date_data['spread_zscore']) >= zscore_threshold
    
    # Additional filter: spread magnitude must be significant
    date_data['spread_significant'] = np.abs(date_data['spread_pct']) >= min_spread_abs
    
    # Combine filters
    date_data['tradeable'] = date_data['is_extreme'] & date_data['spread_significant']
    
    if strategy == 'mean_reversion':
        # MEAN REVERSION: Fade extreme divergences
        # Very positive spread (z > threshold) → SHORT (expect correction down)
        # Very negative spread (z < -threshold) → LONG (expect correction up)
        date_data.loc[
            date_data['tradeable'] & (date_data['spread_zscore'] > zscore_threshold),
            'signal'
        ] = -1  # Short extreme positive spreads
        
        date_data.loc[
            date_data['tradeable'] & (date_data['spread_zscore'] < -zscore_threshold),
            'signal'
        ] = 1  # Long extreme negative spreads
    
    elif strategy == 'momentum_continuation':
        # MOMENTUM CONTINUATION: Follow extreme divergences
        # Very positive spread (z > threshold) → LONG (strong momentum)
        # Very negative spread (z < -threshold) → SHORT (weak momentum)
        date_data.loc[
            date_data['tradeable'] & (date_data['spread_zscore'] > zscore_threshold),
            'signal'
        ] = 1  # Long extreme positive spreads
        
        date_data.loc[
            date_data['tradeable'] & (date_data['spread_zscore'] < -zscore_threshold),
            'signal'
        ] = -1  # Short extreme negative spreads
    
    elif strategy == 'short_expensive_longs':
        # ASYMMETRIC: Only short when funding is too low relative to momentum
        # Very positive spread (RoC >> Funding) → SHORT
        # Logic: Price went up a lot but funding still low = longs not priced in yet
        date_data.loc[
            date_data['tradeable'] & (date_data['spread_zscore'] > zscore_threshold),
            'signal'
        ] = -1  # Short only
    
    elif strategy == 'long_cheap_shorts':
        # ASYMMETRIC: Only long when funding is too high relative to momentum
        # Very negative spread (RoC << Funding) → LONG
        # Logic: Funding high but price not moving = shorts will cover / longs will reduce
        date_data.loc[
            date_data['tradeable'] & (date_data['spread_zscore'] < -zscore_threshold),
            'signal'
        ] = 1  # Long only
    
    return date_data


def calculate_position_weights(signals_data, weighting_method='equal_weight',
                               allocation=1.0):
    """
    Calculate position weights for divergence trades.
    
    Args:
        signals_data: DataFrame with signals
        weighting_method: 'equal_weight', 'zscore_weighted', 'risk_parity'
        allocation: Total allocation (0-1)
    """
    df = signals_data.copy()
    df['weight'] = 0.0
    
    longs = df[df['signal'] == 1].copy()
    shorts = df[df['signal'] == -1].copy()
    
    num_longs = len(longs)
    num_shorts = len(shorts)
    
    if weighting_method == 'equal_weight':
        # Equal weight across all positions
        total_positions = num_longs + num_shorts
        if total_positions > 0:
            weight_per_position = allocation / total_positions
            df.loc[df['signal'] == 1, 'weight'] = weight_per_position
            df.loc[df['signal'] == -1, 'weight'] = -weight_per_position
    
    elif weighting_method == 'zscore_weighted':
        # Weight by absolute z-score (stronger signal = higher weight)
        total_zscore = df[df['signal'] != 0]['spread_zscore'].abs().sum()
        
        if total_zscore > 0:
            df.loc[df['signal'] == 1, 'weight'] = (
                df.loc[df['signal'] == 1, 'spread_zscore'].abs() / total_zscore * allocation
            )
            df.loc[df['signal'] == -1, 'weight'] = (
                -df.loc[df['signal'] == -1, 'spread_zscore'].abs() / total_zscore * allocation
            )
    
    elif weighting_method == 'risk_parity':
        # Weight by inverse volatility
        if num_longs > 0 and 'volatility' in longs.columns:
            longs_inv_vol = 1 / longs['volatility'].replace(0, np.nan)
            longs_inv_vol = longs_inv_vol.fillna(0)
            
            if longs_inv_vol.sum() > 0:
                longs_weights = (longs_inv_vol / longs_inv_vol.sum()) * (allocation * num_longs / (num_longs + num_shorts))
                df.loc[df['signal'] == 1, 'weight'] = longs_weights.values
        
        if num_shorts > 0 and 'volatility' in shorts.columns:
            shorts_inv_vol = 1 / shorts['volatility'].replace(0, np.nan)
            shorts_inv_vol = shorts_inv_vol.fillna(0)
            
            if shorts_inv_vol.sum() > 0:
                shorts_weights = (shorts_inv_vol / shorts_inv_vol.sum()) * (allocation * num_shorts / (num_longs + num_shorts))
                df.loc[df['signal'] == -1, 'weight'] = -shorts_weights.values
    
    return df


def run_divergence_backtest(data, strategy='mean_reversion', window=30,
                            zscore_window=90, zscore_threshold=2.0,
                            min_spread_abs=20.0, rebalance_days=7,
                            weighting_method='equal_weight', allocation=1.0,
                            initial_capital=10000, leverage=1.0,
                            holding_period=None,
                            start_date=None, end_date=None):
    """
    Run backtest for divergence-based strategy.
    
    Args:
        holding_period: Days to hold position (None = until next rebalance)
    """
    print(f"\n{'='*70}")
    print(f"DIVERGENCE BACKTEST: {strategy.upper()}")
    print(f"{'='*70}")
    print(f"Window: {window} days")
    print(f"Z-score window: {zscore_window} days")
    print(f"Z-score threshold: {zscore_threshold}")
    print(f"Min spread: {min_spread_abs}%")
    print(f"Rebalance: Every {rebalance_days} days")
    print(f"Weighting: {weighting_method}")
    print(f"Allocation: {allocation:.0%}")
    
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
    
    # Need at least window + zscore_window days for first signal
    min_days = max(window, zscore_window)
    rebalance_dates = [d for d in all_dates[min_days::rebalance_days]]
    
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
        # Generate divergence signals
        signals = generate_divergence_signals(
            data, rebal_date, strategy,
            zscore_threshold, min_spread_abs
        )
        
        if signals.empty or (signals['signal'] == 0).all():
            # No extreme divergences - hold cash or existing positions
            if i < len(rebalance_dates) - 1:
                next_rebal_date = rebalance_dates[i + 1]
            else:
                next_rebal_date = all_dates[-1]
            
            # Still track portfolio value
            period_data = data[
                (data['date'] > rebal_date) &
                (data['date'] <= next_rebal_date)
            ].copy()
            
            for date in period_data['date'].unique():
                daily_value = initial_capital
                
                for symbol, pos in current_positions.items():
                    symbol_data = period_data[
                        (period_data['symbol'] == symbol) &
                        (period_data['date'] == date)
                    ]
                    
                    if not symbol_data.empty:
                        current_price = symbol_data.iloc[0]['close']
                        entry_price = pos['entry_price']
                        position_return = (current_price / entry_price - 1)
                        position_pnl = pos['position_size'] * position_return
                        daily_value += position_pnl
                
                portfolio_values.append({
                    'date': date,
                    'portfolio_value': daily_value,
                    'cash': cash,
                    'num_positions': len(current_positions),
                    'num_longs': sum(1 for p in current_positions.values() if p['signal'] == 1),
                    'num_shorts': sum(1 for p in current_positions.values() if p['signal'] == -1)
                })
            
            if portfolio_values:
                portfolio_value = portfolio_values[-1]['portfolio_value']
            
            continue
        
        # Calculate position weights
        weighted = calculate_position_weights(
            signals, weighting_method, allocation
        )
        
        # Get next rebalance date
        if i < len(rebalance_dates) - 1:
            next_rebal_date = rebalance_dates[i + 1]
        else:
            next_rebal_date = all_dates[-1]
        
        # Calculate returns between rebalance dates
        period_data = data[
            (data['date'] > rebal_date) &
            (data['date'] <= next_rebal_date)
        ].copy()
        
        if period_data.empty:
            continue
        
        # Create new positions
        new_positions = {}
        
        for _, row in weighted[weighted['weight'] != 0].iterrows():
            symbol = row['symbol']
            weight = row['weight']
            entry_price = row['close']
            position_size = portfolio_value * weight
            
            new_positions[symbol] = {
                'weight': weight,
                'entry_price': entry_price,
                'position_size': position_size,
                'signal': row['signal'],
                'entry_zscore': row['spread_zscore'],
                'entry_spread': row['spread_pct']
            }
            
            # Record trade
            all_trades.append({
                'date': rebal_date,
                'symbol': symbol,
                'signal': 'LONG' if row['signal'] == 1 else 'SHORT',
                'roc_pct': row['roc_pct'],
                'cum_funding_pct': row['cum_funding_pct'],
                'spread_pct': row['spread_pct'],
                'spread_zscore': row['spread_zscore'],
                'spread_mean': row['spread_mean'],
                'spread_std': row['spread_std'],
                'weight': weight,
                'position_size': position_size,
                'volatility': row.get('volatility', np.nan)
            })
        
        # Calculate daily portfolio values
        for date in period_data['date'].unique():
            daily_value = initial_capital
            
            for symbol, pos in new_positions.items():
                symbol_data = period_data[
                    (period_data['symbol'] == symbol) &
                    (period_data['date'] == date)
                ]
                
                if not symbol_data.empty:
                    current_price = symbol_data.iloc[0]['close']
                    entry_price = pos['entry_price']
                    position_return = (current_price / entry_price - 1)
                    position_pnl = pos['position_size'] * position_return
                    daily_value += position_pnl
            
            num_longs = sum(1 for p in new_positions.values() if p['signal'] == 1)
            num_shorts = sum(1 for p in new_positions.values() if p['signal'] == -1)
            
            portfolio_values.append({
                'date': date,
                'portfolio_value': daily_value,
                'cash': cash,
                'num_positions': len(new_positions),
                'num_longs': num_longs,
                'num_shorts': num_shorts
            })
        
        # Update portfolio value
        if portfolio_values:
            portfolio_value = portfolio_values[-1]['portfolio_value']
        
        current_positions = new_positions
    
    # Convert to DataFrames
    df_portfolio = pd.DataFrame(portfolio_values)
    df_trades = pd.DataFrame(all_trades)
    
    # Calculate metrics
    metrics = calculate_performance_metrics(
        df_portfolio, df_trades, initial_capital,
        strategy, window, zscore_threshold
    )
    
    return {
        'portfolio_values': df_portfolio,
        'trades': df_trades,
        'metrics': metrics
    }


def calculate_performance_metrics(portfolio_df, trades_df, initial_capital,
                                  strategy, window, zscore_threshold):
    """Calculate performance metrics."""
    if portfolio_df.empty:
        return {}
    
    portfolio_df = portfolio_df.sort_values('date').reset_index(drop=True)
    portfolio_df['daily_return'] = portfolio_df['portfolio_value'].pct_change()
    
    final_value = portfolio_df['portfolio_value'].iloc[-1]
    total_return = (final_value - initial_capital) / initial_capital
    
    num_days = len(portfolio_df)
    num_years = num_days / 365
    
    annualized_return = (final_value / initial_capital) ** (1 / num_years) - 1 if num_years > 0 else 0
    
    daily_returns = portfolio_df['daily_return'].dropna()
    annualized_volatility = daily_returns.std() * np.sqrt(365)
    
    sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility > 0 else 0
    
    downside_returns = daily_returns[daily_returns < 0]
    downside_volatility = downside_returns.std() * np.sqrt(365) if len(downside_returns) > 0 else 0
    sortino_ratio = annualized_return / downside_volatility if downside_volatility > 0 else 0
    
    cumulative = (1 + daily_returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()
    
    calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
    
    win_rate = (daily_returns > 0).sum() / len(daily_returns) if len(daily_returns) > 0 else 0
    
    # Trade statistics
    num_trades = len(trades_df)
    num_long_trades = len(trades_df[trades_df['signal'] == 'LONG'])
    num_short_trades = len(trades_df[trades_df['signal'] == 'SHORT'])
    
    # Average z-scores
    avg_zscore_long = trades_df[trades_df['signal'] == 'LONG']['spread_zscore'].mean() if num_long_trades > 0 else 0
    avg_zscore_short = trades_df[trades_df['signal'] == 'SHORT']['spread_zscore'].mean() if num_short_trades > 0 else 0
    
    # Average spreads
    avg_spread_long = trades_df[trades_df['signal'] == 'LONG']['spread_pct'].mean() if num_long_trades > 0 else 0
    avg_spread_short = trades_df[trades_df['signal'] == 'SHORT']['spread_pct'].mean() if num_short_trades > 0 else 0
    
    # Average positions per day
    avg_positions = portfolio_df['num_positions'].mean()
    avg_long_positions = portfolio_df['num_longs'].mean()
    avg_short_positions = portfolio_df['num_shorts'].mean()
    
    # Percent of days with positions
    pct_days_invested = (portfolio_df['num_positions'] > 0).sum() / len(portfolio_df) * 100
    
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
        'num_trades': num_trades,
        'num_long_trades': num_long_trades,
        'num_short_trades': num_short_trades,
        'avg_positions': avg_positions,
        'avg_long_positions': avg_long_positions,
        'avg_short_positions': avg_short_positions,
        'avg_zscore_long': avg_zscore_long,
        'avg_zscore_short': avg_zscore_short,
        'avg_spread_long': avg_spread_long,
        'avg_spread_short': avg_spread_short,
        'pct_days_invested': pct_days_invested,
        'trading_days': num_days,
        'strategy': strategy,
        'window': window,
        'zscore_threshold': zscore_threshold
    }
    
    return metrics


def save_results(results, output_prefix):
    """Save backtest results to CSV files."""
    output_dir = os.path.join(os.path.dirname(__file__), '../results')
    os.makedirs(output_dir, exist_ok=True)
    
    portfolio_file = os.path.join(output_dir, f'{output_prefix}_portfolio_values.csv')
    results['portfolio_values'].to_csv(portfolio_file, index=False)
    print(f"\n✓ Saved portfolio values to {portfolio_file}")
    
    trades_file = os.path.join(output_dir, f'{output_prefix}_trades.csv')
    results['trades'].to_csv(trades_file, index=False)
    print(f"✓ Saved trades to {trades_file}")
    
    metrics_file = os.path.join(output_dir, f'{output_prefix}_metrics.csv')
    metrics_df = pd.DataFrame([results['metrics']])
    metrics_df.to_csv(metrics_file, index=False)
    print(f"✓ Saved metrics to {metrics_file}")


def print_results(results):
    """Print backtest results summary."""
    metrics = results['metrics']
    
    print(f"\n{'='*70}")
    print("DIVERGENCE BACKTEST RESULTS")
    print(f"{'='*70}")
    
    print(f"\nStrategy: {metrics['strategy']}")
    print(f"Window: {metrics['window']} days")
    print(f"Z-score Threshold: {metrics['zscore_threshold']}")
    
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
    print(f"Total Trades:         {metrics['num_trades']:>7.0f}")
    print(f"Long Trades:          {metrics['num_long_trades']:>7.0f}")
    print(f"Short Trades:         {metrics['num_short_trades']:>7.0f}")
    print(f"Avg Positions/Day:    {metrics['avg_positions']:>7.1f}")
    print(f"% Days Invested:      {metrics['pct_days_invested']:>7.1f}%")
    
    print(f"\n{'='*70}")
    print("DIVERGENCE STATISTICS")
    print(f"{'='*70}")
    print(f"Avg Z-score Long:     {metrics['avg_zscore_long']:>7.2f}")
    print(f"Avg Z-score Short:    {metrics['avg_zscore_short']:>7.2f}")
    print(f"Avg Spread Long:      {metrics['avg_spread_long']:>7.2f}%")
    print(f"Avg Spread Short:     {metrics['avg_spread_short']:>7.2f}%")
    
    print(f"\n{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Backtest RoC vs Funding DIVERGENCE Strategy'
    )
    
    parser.add_argument('--price-data', type=str,
                       default='data/raw/combined_coinbase_coinmarketcap_daily.csv')
    parser.add_argument('--funding-data', type=str,
                       default='data/raw/historical_funding_rates_top100_ALL_HISTORY_20251028_002456.csv')
    
    parser.add_argument('--strategy', type=str,
                       default='mean_reversion',
                       choices=['mean_reversion', 'momentum_continuation',
                               'short_expensive_longs', 'long_cheap_shorts'])
    parser.add_argument('--window', type=int, default=30)
    parser.add_argument('--zscore-window', type=int, default=90)
    parser.add_argument('--zscore-threshold', type=float, default=2.0)
    parser.add_argument('--min-spread-abs', type=float, default=20.0)
    parser.add_argument('--rebalance-days', type=int, default=7)
    parser.add_argument('--weighting-method', type=str, default='equal_weight',
                       choices=['equal_weight', 'zscore_weighted', 'risk_parity'])
    parser.add_argument('--allocation', type=float, default=1.0)
    
    parser.add_argument('--min-volume', type=float, default=5_000_000)
    parser.add_argument('--min-market-cap', type=float, default=50_000_000)
    parser.add_argument('--initial-capital', type=float, default=10000)
    parser.add_argument('--leverage', type=float, default=1.0)
    parser.add_argument('--start-date', type=str, default='2021-01-01')
    parser.add_argument('--end-date', type=str, default=None)
    parser.add_argument('--output-prefix', type=str,
                       default='backtest_roc_funding_divergence')
    
    args = parser.parse_args()
    
    try:
        price_data = load_price_data(args.price_data)
        funding_data = load_funding_data(args.funding_data)
        merged_data = merge_price_and_funding(price_data, funding_data)
        
        spread_data = calculate_roc_funding_spread(merged_data, args.window)
        spread_data = calculate_spread_zscore(spread_data, args.zscore_window)
        spread_data = calculate_volatility(spread_data, window=30)
        
        filtered_data = filter_universe(
            spread_data,
            min_volume=args.min_volume,
            min_market_cap=args.min_market_cap
        )
        
        results = run_divergence_backtest(
            filtered_data,
            strategy=args.strategy,
            window=args.window,
            zscore_window=args.zscore_window,
            zscore_threshold=args.zscore_threshold,
            min_spread_abs=args.min_spread_abs,
            rebalance_days=args.rebalance_days,
            weighting_method=args.weighting_method,
            allocation=args.allocation,
            initial_capital=args.initial_capital,
            leverage=args.leverage,
            start_date=args.start_date,
            end_date=args.end_date
        )
        
        if results:
            print_results(results)
            save_results(results, args.output_prefix)
            print("✓ Divergence backtest completed successfully!")
        else:
            print("ERROR: Backtest failed")
            sys.exit(1)
            
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
