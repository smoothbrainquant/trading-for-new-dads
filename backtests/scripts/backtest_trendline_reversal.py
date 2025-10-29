#!/usr/bin/env python3
"""
Backtest for Trendline Reversal Strategy

This script backtests a trendline reversal strategy that:
1. Calculates rolling linear regression on closing prices (trendline)
2. Detects REVERSALS when trendlines are broken:
   - LONG: Downtrend broken to upside (price breaks above downtrend)
   - SHORT: Uptrend broken to downside (price breaks below uptrend)
3. Only trades when the trendline is clean and strong (high R²)
4. Uses next-day returns to avoid lookahead bias

Hypothesis: Strong trendline breaks signal trend reversals and mean reversion.
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
    """Load historical OHLCV data from CSV file."""
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
    - Slope: Trend direction and magnitude
    - R²: Trend quality/cleanness
    - Predicted price: Where trendline says price should be
    - Distance: How far actual price is from trendline
    """
    df = data.copy()
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Calculate daily returns
    df['daily_return'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    def fit_trendline(prices, current_idx):
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
                'predicted_price': np.nan
            })
        
        valid_prices = prices.values[valid_mask]
        valid_x = np.arange(len(valid_prices))
        
        try:
            # Fit linear regression
            slope, intercept, r_value, p_value, std_err = stats.linregress(valid_x, valid_prices)
            r_squared = r_value ** 2
            
            # Predict price at current index (end of window)
            predicted_price = slope * (len(valid_prices) - 1) + intercept
            
            return pd.Series({
                'slope': slope,
                'intercept': intercept,
                'r_squared': r_squared,
                'p_value': p_value,
                'predicted_price': predicted_price
            })
        except Exception as e:
            return pd.Series({
                'slope': np.nan,
                'intercept': np.nan,
                'r_squared': np.nan,
                'p_value': np.nan,
                'predicted_price': np.nan
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
                    'predicted_price': np.nan
                })
            else:
                # Get window of prices
                price_window = group['close'].iloc[i-window+1:i+1]
                result = fit_trendline(price_window, i)
                trendline_results.append(result.to_dict())
        
        return pd.DataFrame(trendline_results)
    
    # Apply to each symbol
    trendline_df = df.groupby('symbol', group_keys=False).apply(
        calculate_for_group, include_groups=False
    ).reset_index(drop=True)
    
    # Merge back with original data
    for col in ['slope', 'intercept', 'r_squared', 'p_value', 'predicted_price']:
        df[col] = trendline_df[col].values
    
    return df


def calculate_reversal_metrics(df, window=30):
    """
    Calculate reversal metrics: distance from trendline normalized by volatility.
    """
    df = df.copy()
    
    # Calculate distance from trendline (percentage)
    df['distance_from_trendline'] = (df['close'] - df['predicted_price']) / df['predicted_price'] * 100
    
    # Calculate rolling volatility (annualized)
    df['volatility'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=window, min_periods=int(window*0.7)).std() * np.sqrt(365)
    )
    
    # Normalize distance by volatility (Z-score)
    df['distance_rolling_mean'] = df.groupby('symbol')['distance_from_trendline'].transform(
        lambda x: x.rolling(window=window, min_periods=int(window*0.7)).mean()
    )
    df['distance_rolling_std'] = df.groupby('symbol')['distance_from_trendline'].transform(
        lambda x: x.rolling(window=window, min_periods=int(window*0.7)).std()
    )
    
    # Z-score: how extreme is the current distance
    df['reversal_z_score'] = (
        (df['distance_from_trendline'] - df['distance_rolling_mean']) / 
        df['distance_rolling_std']
    )
    
    # Replace inf/nan with 0
    df['reversal_z_score'] = df['reversal_z_score'].replace([np.inf, -np.inf], np.nan).fillna(0)
    
    # Normalized slope (percentage per year)
    df['norm_slope'] = (df['slope'] / df['close']) * 100 * 365
    df['norm_slope'] = df['norm_slope'].clip(-500, 500)
    
    return df


def detect_reversal_signals(data, 
                            reversal_threshold=1.5,
                            min_r2=0.5,
                            min_slope_magnitude=50,
                            max_pvalue=0.05):
    """
    Detect REVERSAL signals when trendlines are broken in opposite direction.
    
    LONG Signal: Clean downtrend broken to upside (price breaks above downtrend)
    SHORT Signal: Clean uptrend broken to downside (price breaks below uptrend)
    
    Args:
        data (pd.DataFrame): DataFrame with trendline and reversal metrics
        reversal_threshold (float): Minimum Z-score for reversal (e.g., 1.5 = 1.5 std devs)
        min_r2 (float): Minimum R² for clean trendline
        min_slope_magnitude (float): Minimum absolute slope (% per year) to consider strong trend
        max_pvalue (float): Maximum p-value for significant trendline
        
    Returns:
        pd.DataFrame: DataFrame with signal column (-1, 0, 1)
    """
    df = data.copy()
    
    # Initialize signal
    df['signal'] = 0
    
    # Filter for clean trendlines with strong slopes
    clean_mask = (
        (df['r_squared'] >= min_r2) &
        (df['p_value'] <= max_pvalue) &
        (df['norm_slope'].abs() >= min_slope_magnitude) &  # Strong trend required
        (~df['reversal_z_score'].isna())
    )
    
    # LONG: Downtrend broken to upside
    # - Strong downtrend (negative slope)
    # - Price breaks ABOVE the downtrend line (positive distance, positive Z-score)
    long_reversal_mask = (
        clean_mask &
        (df['norm_slope'] < 0) &  # Downtrend
        (df['reversal_z_score'] > reversal_threshold) &  # Strong upward break
        (df['distance_from_trendline'] > 0)  # Above trendline
    )
    df.loc[long_reversal_mask, 'signal'] = 1
    
    # SHORT: Uptrend broken to downside
    # - Strong uptrend (positive slope)
    # - Price breaks BELOW the uptrend line (negative distance, negative Z-score)
    short_reversal_mask = (
        clean_mask &
        (df['norm_slope'] > 0) &  # Uptrend
        (df['reversal_z_score'] < -reversal_threshold) &  # Strong downward break
        (df['distance_from_trendline'] < 0)  # Below trendline
    )
    df.loc[short_reversal_mask, 'signal'] = -1
    
    # Create signal strength score (for ranking)
    df['signal_strength'] = df['reversal_z_score'].abs() * df['r_squared'] * (df['norm_slope'].abs() / 100)
    
    return df


def filter_universe(data, min_volume=5_000_000, min_market_cap=50_000_000):
    """Filter cryptocurrency universe by liquidity and market cap."""
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


def select_top_signals(data, date, max_positions=10, side='both'):
    """Select top reversal signals for a given date."""
    # Get data for this date
    date_data = data[data['date'] == date].copy()
    
    if date_data.empty:
        return {'long': pd.DataFrame(), 'short': pd.DataFrame()}
    
    # Select long signals (downtrend reversals)
    long_df = pd.DataFrame()
    if side in ['long', 'both']:
        long_signals = date_data[date_data['signal'] == 1].copy()
        if not long_signals.empty:
            # Rank by signal strength
            long_signals = long_signals.sort_values('signal_strength', ascending=False)
            long_df = long_signals.head(max_positions)
    
    # Select short signals (uptrend reversals)
    short_df = pd.DataFrame()
    if side in ['short', 'both']:
        short_signals = date_data[date_data['signal'] == -1].copy()
        if not short_signals.empty:
            # Rank by signal strength
            short_signals = short_signals.sort_values('signal_strength', ascending=False)
            short_df = short_signals.head(max_positions)
    
    return {'long': long_df, 'short': short_df}


def calculate_position_weights(positions_df, weighting_method='equal_weight', total_allocation=0.5):
    """Calculate position weights."""
    df = positions_df.copy()
    
    if df.empty:
        return df
    
    if weighting_method == 'equal_weight':
        df['weight'] = total_allocation / len(df)
        
    elif weighting_method == 'signal_weighted':
        # Weight by signal strength
        if 'signal_strength' in df.columns:
            df['weight'] = (df['signal_strength'] / df['signal_strength'].sum()) * total_allocation
        else:
            df['weight'] = total_allocation / len(df)
            
    elif weighting_method == 'risk_parity':
        # Weight inversely by volatility
        if 'volatility' in df.columns and not df['volatility'].isna().all():
            df['inv_vol'] = 1 / df['volatility'].fillna(df['volatility'].median())
            df['weight'] = (df['inv_vol'] / df['inv_vol'].sum()) * total_allocation
        else:
            df['weight'] = total_allocation / len(df)
    
    else:
        raise ValueError(f"Unknown weighting method: {weighting_method}")
    
    return df


def run_backtest(data,
                trendline_window=30,
                volatility_window=30,
                reversal_threshold=1.5,
                min_r2=0.5,
                min_slope_magnitude=50,
                max_pvalue=0.05,
                rebalance_days=1,
                max_positions=10,
                holding_period=5,
                weighting_method='equal_weight',
                initial_capital=10000,
                leverage=1.0,
                long_allocation=0.5,
                short_allocation=0.5,
                min_volume=5_000_000,
                min_market_cap=50_000_000,
                start_date=None,
                end_date=None):
    """Run the trendline reversal backtest."""
    print("=" * 80)
    print("TRENDLINE REVERSAL BACKTEST")
    print("=" * 80)
    print(f"\nTrendline Window: {trendline_window} days")
    print(f"Reversal Threshold: {reversal_threshold} σ")
    print(f"Min R²: {min_r2}")
    print(f"Min Slope Magnitude: {min_slope_magnitude}% per year")
    print(f"Max P-value: {max_pvalue}")
    print(f"Rebalance Frequency: {rebalance_days} days")
    print(f"Max Positions: {max_positions} per side")
    print(f"Holding Period: {holding_period} days")
    print(f"Weighting Method: {weighting_method}")
    
    # Step 1: Calculate trendline metrics
    print("\n" + "-" * 80)
    print("Step 1: Calculating rolling trendline...")
    trendline_data = calculate_rolling_trendline(data, window=trendline_window)
    
    # Step 2: Calculate reversal metrics
    print("\n" + "-" * 80)
    print("Step 2: Calculating reversal metrics...")
    trendline_data = calculate_reversal_metrics(trendline_data, window=volatility_window)
    
    # Step 3: Detect reversal signals
    print("\n" + "-" * 80)
    print("Step 3: Detecting reversal signals...")
    trendline_data = detect_reversal_signals(
        trendline_data,
        reversal_threshold=reversal_threshold,
        min_r2=min_r2,
        min_slope_magnitude=min_slope_magnitude,
        max_pvalue=max_pvalue
    )
    
    long_signals = (trendline_data['signal'] == 1).sum()
    short_signals = (trendline_data['signal'] == -1).sum()
    print(f"  Long signals (downtrend reversals): {long_signals}")
    print(f"  Short signals (uptrend reversals): {short_signals}")
    print(f"  Total reversal signals: {long_signals + short_signals}")
    
    # Step 4: Filter universe
    print("\n" + "-" * 80)
    print("Step 4: Filtering universe...")
    print(f"  Coins before filtering: {trendline_data['symbol'].nunique()}")
    trendline_data = filter_universe(
        trendline_data,
        min_volume=min_volume,
        min_market_cap=min_market_cap
    )
    print(f"  Coins after filtering: {trendline_data['symbol'].nunique()}")
    
    # Step 5: Filter by date range
    if start_date:
        trendline_data = trendline_data[trendline_data['date'] >= pd.to_datetime(start_date)]
    if end_date:
        trendline_data = trendline_data[trendline_data['date'] <= pd.to_datetime(end_date)]
    
    # Step 6: Run backtest
    print("\n" + "-" * 80)
    print("Step 5: Running backtest...")
    
    # Get trading dates
    trading_dates = sorted(trendline_data['date'].unique())
    
    if len(trading_dates) < trendline_window + rebalance_days:
        raise ValueError(f"Insufficient data. Need at least {trendline_window + rebalance_days} days.")
    
    # Start after warmup
    start_idx = max(trendline_window, volatility_window)
    trading_dates = trading_dates[start_idx:]
    
    print(f"  Trading period: {trading_dates[0].date()} to {trading_dates[-1].date()}")
    print(f"  Total trading days: {len(trading_dates)}")
    
    # Initialize portfolio
    portfolio_values = []
    trades = []
    current_positions = {}  # {symbol: {'weight': weight, 'entry_date': date, 'signal': 'LONG'/'SHORT'}}
    portfolio_value = initial_capital * leverage
    
    # Rebalancing loop
    rebalance_dates = trading_dates[::rebalance_days]
    print(f"  Number of rebalance checks: {len(rebalance_dates)}")
    
    for date_idx, current_date in enumerate(trading_dates):
        # Check for new signals on rebalance dates
        if current_date in rebalance_dates:
            # Get new reversal signals
            selected = select_top_signals(
                trendline_data,
                current_date,
                max_positions=max_positions,
                side='both'
            )
            
            # Calculate weights
            long_positions = calculate_position_weights(
                selected['long'], weighting_method, long_allocation
            )
            short_positions = calculate_position_weights(
                selected['short'], weighting_method, short_allocation
            )
            
            # Add new positions
            for _, row in long_positions.iterrows():
                if row['symbol'] not in current_positions:
                    current_positions[row['symbol']] = {
                        'weight': row['weight'],
                        'entry_date': current_date,
                        'signal': 'LONG',
                        'entry_data': row.to_dict()
                    }
                    
                    trades.append({
                        'date': current_date,
                        'symbol': row['symbol'],
                        'signal': 'LONG',
                        'action': 'OPEN',
                        'weight': row['weight'],
                        'price': row['close'],
                        'slope': row['slope'],
                        'norm_slope': row['norm_slope'],
                        'r_squared': row['r_squared'],
                        'distance_from_trendline': row['distance_from_trendline'],
                        'reversal_z_score': row['reversal_z_score'],
                        'signal_strength': row['signal_strength'],
                        'volatility': row.get('volatility', np.nan),
                        'reversal_type': 'downtrend_broken_up'
                    })
            
            for _, row in short_positions.iterrows():
                if row['symbol'] not in current_positions:
                    current_positions[row['symbol']] = {
                        'weight': -row['weight'],
                        'entry_date': current_date,
                        'signal': 'SHORT',
                        'entry_data': row.to_dict()
                    }
                    
                    trades.append({
                        'date': current_date,
                        'symbol': row['symbol'],
                        'signal': 'SHORT',
                        'action': 'OPEN',
                        'weight': -row['weight'],
                        'price': row['close'],
                        'slope': row['slope'],
                        'norm_slope': row['norm_slope'],
                        'r_squared': row['r_squared'],
                        'distance_from_trendline': row['distance_from_trendline'],
                        'reversal_z_score': row['reversal_z_score'],
                        'signal_strength': row['signal_strength'],
                        'volatility': row.get('volatility', np.nan),
                        'reversal_type': 'uptrend_broken_down'
                    })
        
        # Close positions after holding period
        positions_to_close = []
        for symbol, pos_info in current_positions.items():
            days_held = (current_date - pos_info['entry_date']).days
            if days_held >= holding_period:
                positions_to_close.append(symbol)
                
                # Record close
                symbol_data = trendline_data[
                    (trendline_data['date'] == current_date) &
                    (trendline_data['symbol'] == symbol)
                ]
                
                if not symbol_data.empty:
                    trades.append({
                        'date': current_date,
                        'symbol': symbol,
                        'signal': pos_info['signal'],
                        'action': 'CLOSE',
                        'weight': 0,
                        'price': symbol_data.iloc[0]['close'],
                        'days_held': days_held
                    })
        
        for symbol in positions_to_close:
            del current_positions[symbol]
        
        # Calculate daily P&L using next day's returns
        if date_idx < len(trading_dates) - 1:
            next_date = trading_dates[date_idx + 1]
            next_day_data = trendline_data[trendline_data['date'] == next_date]
            
            daily_pnl = 0
            for symbol, pos_info in current_positions.items():
                symbol_data = next_day_data[next_day_data['symbol'] == symbol]
                if not symbol_data.empty:
                    daily_return = symbol_data.iloc[0]['daily_return']
                    if not np.isnan(daily_return):
                        daily_pnl += pos_info['weight'] * daily_return
            
            portfolio_value = portfolio_value * (1 + daily_pnl)
        
        # Calculate exposures
        long_exposure = sum([p['weight'] for p in current_positions.values() if p['weight'] > 0])
        short_exposure = sum([p['weight'] for p in current_positions.values() if p['weight'] < 0])
        
        # Record portfolio value
        portfolio_values.append({
            'date': current_date,
            'portfolio_value': portfolio_value,
            'num_positions': len(current_positions),
            'num_longs': sum([1 for p in current_positions.values() if p['weight'] > 0]),
            'num_shorts': sum([1 for p in current_positions.values() if p['weight'] < 0]),
            'long_exposure': long_exposure * portfolio_value,
            'short_exposure': short_exposure * portfolio_value,
            'net_exposure': (long_exposure + short_exposure) * portfolio_value,
            'gross_exposure': (long_exposure + abs(short_exposure)) * portfolio_value
        })
    
    # Convert to DataFrames
    portfolio_df = pd.DataFrame(portfolio_values)
    trades_df = pd.DataFrame(trades)
    
    # Calculate metrics
    print("\n" + "-" * 80)
    print("Step 6: Calculating performance metrics...")
    metrics = calculate_metrics(portfolio_df, trades_df, initial_capital, leverage)
    
    # Strategy info
    strategy_info = {
        'trendline_window': trendline_window,
        'reversal_threshold': reversal_threshold,
        'min_r2': min_r2,
        'min_slope_magnitude': min_slope_magnitude,
        'max_pvalue': max_pvalue,
        'rebalance_days': rebalance_days,
        'max_positions': max_positions,
        'holding_period': holding_period,
        'weighting_method': weighting_method,
        'initial_capital': initial_capital,
        'leverage': leverage,
        'long_allocation': long_allocation,
        'short_allocation': short_allocation
    }
    
    return {
        'portfolio_values': portfolio_df,
        'trades': trades_df,
        'metrics': metrics,
        'strategy_info': strategy_info
    }


def calculate_metrics(portfolio_df, trades_df, initial_capital, leverage):
    """Calculate performance metrics."""
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
    
    # Sharpe ratio
    sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility > 0 else 0
    
    # Sortino ratio
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
    
    # Trade statistics
    num_trades = len(trades_df[trades_df['action'] == 'OPEN']) if not trades_df.empty else 0
    open_trades = trades_df[trades_df['action'] == 'OPEN'] if not trades_df.empty else pd.DataFrame()
    
    num_long_trades = len(open_trades[open_trades['signal'] == 'LONG']) if not open_trades.empty else 0
    num_short_trades = len(open_trades[open_trades['signal'] == 'SHORT']) if not open_trades.empty else 0
    
    # Average signal metrics
    avg_r2 = open_trades['r_squared'].mean() if not open_trades.empty else np.nan
    avg_reversal_z = open_trades['reversal_z_score'].mean() if not open_trades.empty else np.nan
    avg_signal_strength = open_trades['signal_strength'].mean() if not open_trades.empty else np.nan
    avg_slope_magnitude = open_trades['norm_slope'].abs().mean() if not open_trades.empty else np.nan
    
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
        'num_trades': num_trades,
        'num_long_trades': num_long_trades,
        'num_short_trades': num_short_trades,
        'avg_positions': portfolio_df['num_positions'].mean(),
        'avg_long_positions': portfolio_df['num_longs'].mean(),
        'avg_short_positions': portfolio_df['num_shorts'].mean(),
        'avg_r2': avg_r2,
        'avg_reversal_z_score': avg_reversal_z,
        'avg_signal_strength': avg_signal_strength,
        'avg_slope_magnitude': avg_slope_magnitude
    }
    
    return metrics


def print_results(results):
    """Print backtest results."""
    metrics = results['metrics']
    strategy_info = results['strategy_info']
    
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)
    
    print("\nStrategy Configuration:")
    print(f"  Trendline Window:       {strategy_info['trendline_window']} days")
    print(f"  Reversal Threshold:     {strategy_info['reversal_threshold']} σ")
    print(f"  Min R²:                 {strategy_info['min_r2']}")
    print(f"  Min Slope Magnitude:    {strategy_info['min_slope_magnitude']}% per year")
    print(f"  Holding Period:         {strategy_info['holding_period']} days")
    print(f"  Max Positions:          {strategy_info['max_positions']} per side")
    
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
    print(f"  Total Trades:           {metrics['num_trades']:>14.0f}")
    print(f"  Long Trades:            {metrics['num_long_trades']:>14.0f} (downtrend reversals)")
    print(f"  Short Trades:           {metrics['num_short_trades']:>14.0f} (uptrend reversals)")
    print(f"  Avg Positions:          {metrics['avg_positions']:>14.1f}")
    
    print("\nSignal Quality:")
    print(f"  Avg R²:                 {metrics['avg_r2']:>14.4f}")
    print(f"  Avg Reversal Z-score:   {metrics['avg_reversal_z_score']:>14.2f}")
    print(f"  Avg Slope Magnitude:    {metrics['avg_slope_magnitude']:>14.1f}%")
    print(f"  Avg Signal Strength:    {metrics['avg_signal_strength']:>14.2f}")
    
    print("\n" + "=" * 80)


def save_results(results, output_prefix):
    """Save backtest results to CSV files."""
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
    """Main function."""
    parser = argparse.ArgumentParser(description='Backtest trendline reversal strategy')
    
    # Data parameters
    parser.add_argument('--price-data', type=str,
                       default='data/raw/combined_coinbase_coinmarketcap_daily.csv',
                       help='Path to historical OHLCV CSV file')
    
    # Trendline parameters
    parser.add_argument('--trendline-window', type=int, default=30,
                       help='Trendline calculation window in days')
    parser.add_argument('--volatility-window', type=int, default=30,
                       help='Volatility window for reversal normalization')
    parser.add_argument('--reversal-threshold', type=float, default=1.5,
                       help='Z-score threshold for reversal signal')
    parser.add_argument('--min-r2', type=float, default=0.5,
                       help='Minimum R² for clean trendline')
    parser.add_argument('--min-slope-magnitude', type=float, default=50,
                       help='Minimum absolute slope (pct per year) for strong trend')
    parser.add_argument('--max-pvalue', type=float, default=0.05,
                       help='Maximum p-value for significant trendline')
    
    # Portfolio parameters
    parser.add_argument('--rebalance-days', type=int, default=1,
                       help='How often to check for new signals')
    parser.add_argument('--max-positions', type=int, default=10,
                       help='Maximum positions per side')
    parser.add_argument('--holding-period', type=int, default=5,
                       help='Days to hold each signal')
    parser.add_argument('--weighting-method', type=str, default='equal_weight',
                       choices=['equal_weight', 'signal_weighted', 'risk_parity'],
                       help='Position weighting method')
    
    # Capital and leverage
    parser.add_argument('--initial-capital', type=float, default=10000,
                       help='Initial capital in USD')
    parser.add_argument('--leverage', type=float, default=1.0,
                       help='Leverage multiplier')
    parser.add_argument('--long-allocation', type=float, default=0.5,
                       help='Allocation to long side')
    parser.add_argument('--short-allocation', type=float, default=0.5,
                       help='Allocation to short side')
    
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
                       default='backtests/results/backtest_trendline_reversal',
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
        trendline_window=args.trendline_window,
        volatility_window=args.volatility_window,
        reversal_threshold=args.reversal_threshold,
        min_r2=args.min_r2,
        min_slope_magnitude=args.min_slope_magnitude,
        max_pvalue=args.max_pvalue,
        rebalance_days=args.rebalance_days,
        max_positions=args.max_positions,
        holding_period=args.holding_period,
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
