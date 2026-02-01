#!/usr/bin/env python3
"""
Backtest relative illiquidity strategies on top 50 coins:
1. Long/Short by absolute notional volume (dollar_volume)
   - Long: Low volume (more illiquid)
   - Short: High volume (more liquid)
2. Long/Short by RVOL
   - Long: Low RVOL
   - Short: High RVOL
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def identify_top_coins(df, top_n=50):
    """Identify top N coins by average dollar volume."""
    avg_volume = df.groupby('symbol')['dollar_volume'].mean().sort_values(ascending=False)
    top_coins = avg_volume.head(top_n).index.tolist()
    print(f"\nTop {top_n} coins by average dollar volume:")
    for i, (coin, vol) in enumerate(avg_volume.head(top_n).items(), 1):
        print(f"{i}. {coin}: ${vol:,.0f}")
    return top_coins

def backtest_strategy(df, strategy_name, signal_column, long_pct=0.2, short_pct=0.2, 
                      initial_capital=100000, rebalance_days=7):
    """
    Backtest a long/short strategy using next day's returns.
    
    Logic:
    - Day T: Observe signals (dollar_volume, RVOL)
    - Day T+1: Enter positions at open, calculate returns from open to close
    
    Parameters:
    - long_pct: percentile for long positions (low values = more illiquid/low RVOL)
    - short_pct: percentile for short positions (high values = more liquid/high RVOL)
    """
    print(f"\n{'='*80}")
    print(f"Backtesting: {strategy_name}")
    print(f"Signal column: {signal_column}")
    print(f"Long: Bottom {int(long_pct*100)}% | Short: Top {int(short_pct*100)}%")
    print(f"Rebalance frequency: Every {rebalance_days} days")
    print(f"{'='*80}")
    
    # Create a dataframe with next day's return pre-calculated
    df_sorted = df.sort_values(['symbol', 'date'])
    df_sorted['next_day_return'] = df_sorted.groupby('symbol')['close'].pct_change()
    
    # Get unique dates
    dates = sorted(df_sorted['date'].unique())
    
    # Initialize portfolio tracking
    portfolio_values = []
    trades = []
    
    capital = initial_capital
    current_positions = None
    days_since_rebalance = 0
    
    for i, date in enumerate(dates):
        # Get data for this date
        day_data = df_sorted[df_sorted['date'] == date].copy()
        
        # Skip if insufficient data
        if len(day_data) < 10 or day_data[signal_column].isna().all():
            continue
        
        # Rebalancing logic: use today's signals to determine positions for tomorrow
        if current_positions is None or days_since_rebalance >= rebalance_days:
            # Remove NaN values
            valid_data = day_data[day_data[signal_column].notna()].copy()
            
            if len(valid_data) < 10:
                continue
            
            # Calculate percentiles based on today's signals
            long_threshold = valid_data[signal_column].quantile(long_pct)
            short_threshold = valid_data[signal_column].quantile(1 - short_pct)
            
            # Select long and short positions for tomorrow
            long_positions = valid_data[valid_data[signal_column] <= long_threshold]['symbol'].tolist()
            short_positions = valid_data[valid_data[signal_column] >= short_threshold]['symbol'].tolist()
            
            # Calculate position sizes (equal weight within long and short baskets)
            n_long = len(long_positions)
            n_short = len(short_positions)
            
            if n_long > 0 and n_short > 0:
                long_weight = 0.5 / n_long  # 50% of capital in longs
                short_weight = 0.5 / n_short  # 50% of capital in shorts
                
                trades.append({
                    'signal_date': date,
                    'n_long': n_long,
                    'n_short': n_short,
                    'long_positions': ','.join(long_positions[:5]) + ('...' if n_long > 5 else ''),
                    'short_positions': ','.join(short_positions[:5]) + ('...' if n_short > 5 else ''),
                    'long_threshold': long_threshold,
                    'short_threshold': short_threshold
                })
                
                current_positions = {
                    'long': long_positions,
                    'short': short_positions,
                    'long_weight': long_weight,
                    'short_weight': short_weight
                }
                days_since_rebalance = 0
        
        # Calculate returns using NEXT day's return (already calculated as pct_change of close)
        if current_positions is not None:
            day_return = 0
            
            # Long positions
            for symbol in current_positions['long']:
                symbol_data = day_data[day_data['symbol'] == symbol]
                if not symbol_data.empty and not pd.isna(symbol_data['next_day_return'].values[0]):
                    daily_ret = symbol_data['next_day_return'].values[0]
                    day_return += current_positions['long_weight'] * daily_ret
            
            # Short positions (negative returns)
            for symbol in current_positions['short']:
                symbol_data = day_data[day_data['symbol'] == symbol]
                if not symbol_data.empty and not pd.isna(symbol_data['next_day_return'].values[0]):
                    daily_ret = symbol_data['next_day_return'].values[0]
                    day_return -= current_positions['short_weight'] * daily_ret
            
            capital *= (1 + day_return)
            days_since_rebalance += 1
        
        portfolio_values.append({
            'date': date,
            'portfolio_value': capital
        })
    
    # Convert to DataFrames
    portfolio_df = pd.DataFrame(portfolio_values)
    trades_df = pd.DataFrame(trades)
    
    # Calculate metrics
    portfolio_df['returns'] = portfolio_df['portfolio_value'].pct_change()
    
    total_return = (capital - initial_capital) / initial_capital
    
    # Annualized metrics
    n_days = (portfolio_df['date'].max() - portfolio_df['date'].min()).days
    n_years = n_days / 365.25
    annualized_return = (1 + total_return) ** (1 / n_years) - 1 if n_years > 0 else 0
    
    daily_std = portfolio_df['returns'].std()
    annualized_vol = daily_std * np.sqrt(252)
    sharpe_ratio = annualized_return / annualized_vol if annualized_vol > 0 else 0
    
    # Max drawdown
    portfolio_df['cummax'] = portfolio_df['portfolio_value'].cummax()
    portfolio_df['drawdown'] = (portfolio_df['portfolio_value'] - portfolio_df['cummax']) / portfolio_df['cummax']
    max_drawdown = portfolio_df['drawdown'].min()
    
    # Win rate
    win_rate = (portfolio_df['returns'] > 0).sum() / len(portfolio_df['returns']) if len(portfolio_df['returns']) > 0 else 0
    
    # Print results
    print(f"\nPerformance Metrics:")
    print(f"  Initial Capital: ${initial_capital:,.0f}")
    print(f"  Final Capital: ${capital:,.0f}")
    print(f"  Total Return: {total_return*100:.2f}%")
    print(f"  Annualized Return: {annualized_return*100:.2f}%")
    print(f"  Annualized Volatility: {annualized_vol*100:.2f}%")
    print(f"  Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"  Max Drawdown: {max_drawdown*100:.2f}%")
    print(f"  Win Rate: {win_rate*100:.2f}%")
    print(f"  Number of Rebalances: {len(trades_df)}")
    
    return {
        'strategy': strategy_name,
        'initial_capital': initial_capital,
        'final_capital': capital,
        'total_return': total_return,
        'annualized_return': annualized_return,
        'annualized_vol': annualized_vol,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'n_rebalances': len(trades_df),
        'portfolio_df': portfolio_df,
        'trades_df': trades_df
    }

def main():
    # Load data
    print("Loading data...")
    df = pd.read_csv('coinbase_spot_daily_data_with_metrics.csv')
    df['date'] = pd.to_datetime(df['date'])
    
    print(f"Loaded {len(df)} rows with {df['symbol'].nunique()} symbols")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    
    # Identify top 50 coins
    top_coins = identify_top_coins(df, top_n=50)
    
    # Filter to top 50 coins
    df_top = df[df['symbol'].isin(top_coins)].copy()
    
    print(f"\nFiltered to {len(df_top)} rows with {df_top['symbol'].nunique()} symbols")
    
    # Remove rows with missing data for key columns
    df_clean = df_top[df_top['dollar_volume'].notna() & 
                      df_top['rvol'].notna() & 
                      df_top['close'].notna()].copy()
    
    print(f"After removing NaN: {len(df_clean)} rows")
    
    # Strategy 1: Long/Short by Dollar Volume (low volume = more illiquid = long)
    result1 = backtest_strategy(
        df_clean,
        strategy_name="Long Low Volume / Short High Volume",
        signal_column='dollar_volume',
        long_pct=0.2,  # Long bottom 20% (most illiquid)
        short_pct=0.2,  # Short top 20% (most liquid)
        rebalance_days=7  # Weekly rebalancing
    )
    
    # Strategy 2: Long/Short by RVOL (low RVOL = less active = long)
    result2 = backtest_strategy(
        df_clean,
        strategy_name="Long Low RVOL / Short High RVOL",
        signal_column='rvol',
        long_pct=0.2,  # Long bottom 20% (lowest relative volume)
        short_pct=0.2,  # Short top 20% (highest relative volume)
        rebalance_days=7  # Weekly rebalancing
    )
    
    # Save results
    print("\n" + "="*80)
    print("Saving results...")
    
    # Summary metrics
    summary_data = []
    for result in [result1, result2]:
        summary_data.append({
            'strategy': result['strategy'],
            'initial_capital': result['initial_capital'],
            'final_capital': result['final_capital'],
            'total_return_pct': result['total_return'] * 100,
            'annualized_return_pct': result['annualized_return'] * 100,
            'annualized_vol_pct': result['annualized_vol'] * 100,
            'sharpe_ratio': result['sharpe_ratio'],
            'max_drawdown_pct': result['max_drawdown'] * 100,
            'win_rate_pct': result['win_rate'] * 100,
            'n_rebalances': result['n_rebalances']
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv('backtest_illiquidity_metrics.csv', index=False)
    print("Saved: backtest_illiquidity_metrics.csv")
    
    # Portfolio values
    result1['portfolio_df']['strategy'] = result1['strategy']
    result2['portfolio_df']['strategy'] = result2['strategy']
    combined_portfolio = pd.concat([result1['portfolio_df'], result2['portfolio_df']])
    combined_portfolio.to_csv('backtest_illiquidity_portfolio_values.csv', index=False)
    print("Saved: backtest_illiquidity_portfolio_values.csv")
    
    # Trades
    result1['trades_df']['strategy'] = result1['strategy']
    result2['trades_df']['strategy'] = result2['strategy']
    combined_trades = pd.concat([result1['trades_df'], result2['trades_df']])
    combined_trades.to_csv('backtest_illiquidity_trades.csv', index=False)
    print("Saved: backtest_illiquidity_trades.csv")
    
    print("\n" + "="*80)
    print("BACKTEST COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
