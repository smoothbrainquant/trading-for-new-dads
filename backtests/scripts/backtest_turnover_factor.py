#!/usr/bin/env python3
"""
Backtest Turnover Factor

Factor: Turnover = 24h Volume / Market Cap
Hypothesis: Tokens with optimal turnover (liquid but not overly speculative) outperform

Uses historical data:
- CoinMarketCap monthly snapshots (market cap, volume)
- Coinbase daily prices (for returns)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from pathlib import Path


def load_historical_marketcap_data() -> pd.DataFrame:
    """Load historical market cap and volume snapshots"""
    filepath = "/workspace/data/raw/coinmarketcap_historical_all_snapshots.csv"
    
    print(f"Loading: {filepath}")
    df = pd.read_csv(filepath)
    
    # Clean and process
    df['snapshot_date'] = pd.to_datetime(df['snapshot_date'], format='%Y%m%d')
    df['Market Cap'] = pd.to_numeric(df['Market Cap'], errors='coerce')
    df['Volume (24h)'] = pd.to_numeric(df['Volume (24h)'], errors='coerce')
    
    # Calculate turnover
    df['turnover_pct'] = (df['Volume (24h)'] / df['Market Cap'] * 100).replace([np.inf, -np.inf], np.nan)
    
    # Keep relevant columns
    df = df[['Symbol', 'snapshot_date', 'Market Cap', 'Volume (24h)', 'turnover_pct']].copy()
    df.columns = ['symbol', 'date', 'market_cap', 'volume_24h', 'turnover_pct']
    
    print(f"Loaded {len(df)} snapshots from {df['date'].min()} to {df['date'].max()}")
    print(f"Unique tokens: {df['symbol'].nunique()}")
    
    return df


def load_historical_prices() -> pd.DataFrame:
    """Load historical price data"""
    filepath = "/workspace/data/raw/coinbase_top200_daily_20200101_to_present_20251025_171900.csv"
    
    print(f"Loading: {filepath}")
    df = pd.read_csv(filepath)
    
    df['date'] = pd.to_datetime(df['date'])
    
    # Extract base symbol
    df['symbol'] = df['base'] if 'base' in df.columns else df['symbol']
    
    # Keep relevant columns
    df = df[['date', 'symbol', 'close']].copy()
    
    print(f"Loaded {len(df)} price records from {df['date'].min()} to {df['date'].max()}")
    print(f"Unique tokens: {df['symbol'].nunique()}")
    
    return df


def calculate_forward_returns(prices_df: pd.DataFrame, periods: int = 30) -> pd.DataFrame:
    """Calculate forward returns"""
    prices_df = prices_df.sort_values(['symbol', 'date'])
    
    # Calculate forward return
    prices_df['forward_return'] = prices_df.groupby('symbol')['close'].pct_change(periods).shift(-periods)
    
    return prices_df


def merge_factors_and_returns(factors_df: pd.DataFrame, returns_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge factor signals with forward returns
    
    Strategy: Use monthly CMC snapshots to generate signals, then calculate
    next month's returns from daily price data
    """
    # For each monthly snapshot, find the closest future price data
    merged_data = []
    
    for _, factor_row in factors_df.iterrows():
        symbol = factor_row['symbol']
        snapshot_date = factor_row['date']
        
        # Get price at snapshot date (or closest after)
        symbol_prices = returns_df[
            (returns_df['symbol'] == symbol) & 
            (returns_df['date'] >= snapshot_date)
        ].sort_values('date')
        
        if len(symbol_prices) == 0:
            continue
        
        # Get first price after snapshot
        start_price_row = symbol_prices.iloc[0]
        
        # Get price 30 days later
        end_date = snapshot_date + timedelta(days=30)
        end_prices = returns_df[
            (returns_df['symbol'] == symbol) & 
            (returns_df['date'] >= end_date)
        ].sort_values('date')
        
        if len(end_prices) == 0:
            continue
        
        end_price_row = end_prices.iloc[0]
        
        # Calculate return
        forward_return = (end_price_row['close'] - start_price_row['close']) / start_price_row['close']
        
        merged_data.append({
            'symbol': symbol,
            'date': snapshot_date,
            'turnover_pct': factor_row['turnover_pct'],
            'market_cap': factor_row['market_cap'],
            'volume_24h': factor_row['volume_24h'],
            'forward_return': forward_return,
            'start_date': start_price_row['date'],
            'end_date': end_price_row['date'],
        })
    
    merged_df = pd.DataFrame(merged_data)
    print(f"\nMerged {len(merged_df)} factor-return pairs")
    
    return merged_df


def generate_factor_signals(
    df: pd.DataFrame,
    long_percentile: float = 80,
    short_percentile: float = 20,
    min_market_cap: float = 100_000_000  # $100M minimum
) -> pd.DataFrame:
    """Generate long/short signals based on turnover factor"""
    
    results = []
    
    # Process each date separately
    for date in df['date'].unique():
        date_data = df[df['date'] == date].copy()
        
        # Filter by market cap
        date_data = date_data[date_data['market_cap'] >= min_market_cap]
        
        if len(date_data) < 10:  # Need enough tokens
            continue
        
        # Remove extreme outliers and missing data
        date_data = date_data[date_data['turnover_pct'].notna()]
        date_data = date_data[
            (date_data['turnover_pct'] > 0) & 
            (date_data['turnover_pct'] < 100)  # Exclude extreme speculation
        ]
        
        if len(date_data) < 10:
            continue
        
        # Calculate percentiles
        date_data['percentile'] = date_data['turnover_pct'].rank(pct=True) * 100
        
        # Generate signals
        date_data['signal'] = 'neutral'
        date_data.loc[date_data['percentile'] >= long_percentile, 'signal'] = 'long'
        date_data.loc[date_data['percentile'] <= short_percentile, 'signal'] = 'short'
        
        results.append(date_data)
    
    if not results:
        return pd.DataFrame()
    
    signals_df = pd.concat(results, ignore_index=True)
    
    print(f"\nGenerated signals for {signals_df['date'].nunique()} dates")
    print(f"  Long signals: {(signals_df['signal'] == 'long').sum()}")
    print(f"  Short signals: {(signals_df['signal'] == 'short').sum()}")
    print(f"  Neutral: {(signals_df['signal'] == 'neutral').sum()}")
    
    return signals_df


def backtest_strategy(signals_df: pd.DataFrame) -> pd.DataFrame:
    """
    Backtest the turnover factor strategy
    
    Returns:
        DataFrame with portfolio returns by date
    """
    portfolio_returns = []
    
    for date in sorted(signals_df['date'].unique()):
        date_signals = signals_df[signals_df['date'] == date]
        
        # Long portfolio (equal weight)
        longs = date_signals[date_signals['signal'] == 'long']
        long_return = longs['forward_return'].mean() if len(longs) > 0 else 0
        
        # Short portfolio (equal weight)
        shorts = date_signals[date_signals['signal'] == 'short']
        short_return = shorts['forward_return'].mean() if len(shorts) > 0 else 0
        
        # Long-short portfolio
        ls_return = long_return - short_return
        
        # Benchmark (all tokens equal weight)
        benchmark_return = date_signals['forward_return'].mean()
        
        portfolio_returns.append({
            'date': date,
            'long_return': long_return,
            'short_return': short_return,
            'ls_return': ls_return,
            'benchmark_return': benchmark_return,
            'num_longs': len(longs),
            'num_shorts': len(shorts),
        })
    
    returns_df = pd.DataFrame(portfolio_returns)
    returns_df = returns_df.sort_values('date')
    
    # Calculate cumulative returns
    returns_df['cum_long'] = (1 + returns_df['long_return']).cumprod()
    returns_df['cum_short'] = (1 + returns_df['short_return']).cumprod()
    returns_df['cum_ls'] = (1 + returns_df['ls_return']).cumprod()
    returns_df['cum_benchmark'] = (1 + returns_df['benchmark_return']).cumprod()
    
    return returns_df


def plot_backtest_results(returns_df: pd.DataFrame, output_path: str):
    """Plot backtest results"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # Cumulative returns
    ax = axes[0, 0]
    ax.plot(returns_df['date'], returns_df['cum_long'], label='Long (High Turnover)', linewidth=2)
    ax.plot(returns_df['date'], returns_df['cum_short'], label='Short (Low Turnover)', linewidth=2)
    ax.plot(returns_df['date'], returns_df['cum_ls'], label='Long-Short', linewidth=2, color='green')
    ax.plot(returns_df['date'], returns_df['cum_benchmark'], label='Benchmark (Equal Weight)', linewidth=1, linestyle='--', color='gray')
    ax.set_xlabel('Date')
    ax.set_ylabel('Cumulative Return')
    ax.set_title('Turnover Factor: Cumulative Returns')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Monthly returns distribution
    ax = axes[0, 1]
    ax.hist(returns_df['ls_return'] * 100, bins=30, alpha=0.7, edgecolor='black')
    ax.axvline(returns_df['ls_return'].mean() * 100, color='red', linestyle='--', linewidth=2, label=f'Mean: {returns_df["ls_return"].mean()*100:.2f}%')
    ax.set_xlabel('Monthly Return (%)')
    ax.set_ylabel('Frequency')
    ax.set_title('Long-Short Return Distribution')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Rolling Sharpe ratio (12-month)
    ax = axes[1, 0]
    rolling_sharpe = returns_df['ls_return'].rolling(12).mean() / returns_df['ls_return'].rolling(12).std() * np.sqrt(12)
    ax.plot(returns_df['date'], rolling_sharpe, linewidth=2)
    ax.axhline(0, color='black', linestyle='-', linewidth=0.5)
    ax.axhline(1, color='green', linestyle='--', linewidth=1, alpha=0.5, label='Sharpe=1')
    ax.set_xlabel('Date')
    ax.set_ylabel('Rolling 12M Sharpe Ratio')
    ax.set_title('Strategy Risk-Adjusted Performance')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Number of positions over time
    ax = axes[1, 1]
    ax.plot(returns_df['date'], returns_df['num_longs'], label='Long Positions', linewidth=2)
    ax.plot(returns_df['date'], returns_df['num_shorts'], label='Short Positions', linewidth=2)
    ax.set_xlabel('Date')
    ax.set_ylabel('Number of Positions')
    ax.set_title('Portfolio Composition Over Time')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n✓ Saved plot: {output_path}")


def print_performance_metrics(returns_df: pd.DataFrame):
    """Print performance statistics"""
    print("\n" + "=" * 80)
    print("BACKTEST PERFORMANCE METRICS")
    print("=" * 80)
    
    strategies = {
        'Long Portfolio': 'long_return',
        'Short Portfolio': 'short_return',
        'Long-Short': 'ls_return',
        'Benchmark': 'benchmark_return',
    }
    
    for name, col in strategies.items():
        returns = returns_df[col]
        cum_return = returns_df[f"cum_{col.replace('_return', '')}"].iloc[-1] - 1
        
        print(f"\n{name}:")
        print(f"  Total Return: {cum_return*100:6.2f}%")
        print(f"  Ann. Return: {(((1 + cum_return) ** (12/len(returns))) - 1)*100:6.2f}%")
        print(f"  Ann. Vol: {returns.std() * np.sqrt(12)*100:6.2f}%")
        print(f"  Sharpe Ratio: {returns.mean() / returns.std() * np.sqrt(12):6.2f}")
        print(f"  Max Drawdown: {((returns_df[f"cum_{col.replace('_return', '')}"] / returns_df[f"cum_{col.replace('_return', '')}"].cummax()) - 1).min()*100:6.2f}%")
        print(f"  Win Rate: {(returns > 0).mean()*100:6.2f}%")
    
    print("\n" + "=" * 80)


def main():
    """Run turnover factor backtest"""
    print("=" * 80)
    print("Turnover Factor Backtest")
    print("=" * 80)
    print()
    
    # Load data
    print("Step 1: Loading data...")
    marketcap_df = load_historical_marketcap_data()
    prices_df = load_historical_prices()
    
    # Merge factors with returns
    print("\nStep 2: Merging factors with forward returns...")
    merged_df = merge_factors_and_returns(marketcap_df, prices_df)
    
    if merged_df.empty:
        print("Error: No merged data available")
        return
    
    # Generate signals
    print("\nStep 3: Generating factor signals...")
    signals_df = generate_factor_signals(merged_df)
    
    if signals_df.empty:
        print("Error: No signals generated")
        return
    
    # Backtest
    print("\nStep 4: Running backtest...")
    returns_df = backtest_strategy(signals_df)
    
    # Save results
    output_dir = Path("/workspace/backtests/results")
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    returns_df.to_csv(output_dir / f"turnover_factor_backtest_{date_str}.csv", index=False)
    print(f"\n✓ Saved results: turnover_factor_backtest_{date_str}.csv")
    
    # Performance metrics
    print_performance_metrics(returns_df)
    
    # Plot
    plot_backtest_results(returns_df, str(output_dir / f"turnover_factor_backtest_{date_str}.png"))
    
    print("\n" + "=" * 80)
    print("✅ Backtest complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
