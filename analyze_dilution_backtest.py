#!/usr/bin/env python3
"""
Analyze Dilution Factor Backtest Data Joining
- Check how dilution signals join with price data
- Identify any missing data or join issues
- Show results with 1-99% percentile clipping

?? WARNING: THIS SCRIPT CONTAINS A PORTFOLIO CONSTRUCTION BUG

This script reproduces a known bug that causes accidental portfolio concentration,
leading to artificially inflated returns. The bug has been fixed in:
  /workspace/backtests/scripts/backtest_dilution_factor.py

DO NOT USE THIS SCRIPT FOR ACTUAL BACKTESTING.

The data joining analysis is valid, but the performance results are NOT.
See /workspace/DILUTION_BACKTEST_FINAL_SUMMARY.md for details.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os
import sys

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backtests", "scripts"))

from optimize_rebalance_frequency import (
    calculate_rolling_dilution_signal,
    construct_risk_parity_portfolio,
    calculate_volatility,
)


def load_data():
    """Load price and dilution data."""
    print("=" * 80)
    print("LOADING DATA")
    print("=" * 80)
    
    # Load price data
    price_file = 'data/raw/combined_coinbase_coinmarketcap_daily.csv'
    price_df = pd.read_csv(price_file)
    price_df['date'] = pd.to_datetime(price_df['date'])
    
    # Calculate returns
    price_df = price_df.sort_values(['symbol', 'date']).reset_index(drop=True)
    price_df['return'] = price_df.groupby('symbol')['close'].pct_change()
    
    print(f"? Price data: {len(price_df)} records, {price_df['symbol'].nunique()} symbols")
    print(f"  Date range: {price_df['date'].min().date()} to {price_df['date'].max().date()}")
    print(f"  Symbols (first 10): {sorted(price_df['base'].unique())[:10]}")
    
    # Load dilution data
    hist_file = 'crypto_dilution_historical_2021_2025.csv'
    hist_df = pd.read_csv(hist_file)
    hist_df['date'] = pd.to_datetime(hist_df['date'])
    
    print(f"\n? Dilution data: {len(hist_df)} records, {hist_df['Symbol'].nunique()} symbols")
    print(f"  Date range: {hist_df['date'].min().date()} to {hist_df['date'].max().date()}")
    print(f"  Symbols (first 10): {sorted(hist_df['Symbol'].unique())[:10]}")
    
    return price_df, hist_df


def analyze_symbol_overlap(price_df, hist_df):
    """Analyze symbol overlap between price and dilution data."""
    print("\n" + "=" * 80)
    print("ANALYZING SYMBOL OVERLAP")
    print("=" * 80)
    
    # Get unique symbols
    price_symbols = set(price_df['base'].unique())
    dilution_symbols = set(hist_df['Symbol'].unique())
    
    # Calculate overlap
    common_symbols = price_symbols & dilution_symbols
    price_only = price_symbols - dilution_symbols
    dilution_only = dilution_symbols - price_symbols
    
    print(f"\nSymbol counts:")
    print(f"  Price data:         {len(price_symbols)} unique symbols")
    print(f"  Dilution data:      {len(dilution_symbols)} unique symbols")
    print(f"  Common symbols:     {len(common_symbols)} ({len(common_symbols)/len(dilution_symbols)*100:.1f}% of dilution)")
    print(f"  Price only:         {len(price_only)}")
    print(f"  Dilution only:      {len(dilution_only)}")
    
    if len(dilution_only) > 0:
        print(f"\n? WARNING: {len(dilution_only)} symbols in dilution data have NO price data:")
        print(f"  Examples: {list(dilution_only)[:20]}")
    
    if len(price_only) > 0:
        print(f"\n? INFO: {len(price_only)} symbols have price data but no dilution data (OK)")
        print(f"  Examples: {list(price_only)[:10]}")
    
    return common_symbols, dilution_only


def analyze_data_joining_per_rebalance(price_df, signals_df):
    """Analyze how many symbols successfully join at each rebalance date."""
    print("\n" + "=" * 80)
    print("ANALYZING DATA JOINING AT EACH REBALANCE")
    print("=" * 80)
    
    rebalance_dates = sorted(signals_df['date'].unique())
    
    join_stats = []
    
    for i, rebal_date in enumerate(rebalance_dates):
        # Get signals for this date
        date_signals = signals_df[signals_df['date'] == rebal_date].copy()
        
        # Filter to top 150 by rank
        date_signals = date_signals.nsmallest(150, 'rank')
        
        # Get available price data symbols around this date
        price_window = price_df[
            (price_df['date'] >= rebal_date - pd.Timedelta(days=100)) &
            (price_df['date'] <= rebal_date)
        ]
        available_symbols = set(price_window['base'].unique())
        
        # Check which signals have price data
        signals_with_price = date_signals[date_signals['symbol'].isin(available_symbols)]
        signals_without_price = date_signals[~date_signals['symbol'].isin(available_symbols)]
        
        join_rate = len(signals_with_price) / len(date_signals) * 100 if len(date_signals) > 0 else 0
        
        join_stats.append({
            'date': rebal_date,
            'n_signals': len(date_signals),
            'n_with_price': len(signals_with_price),
            'n_without_price': len(signals_without_price),
            'join_rate_pct': join_rate
        })
        
        if i < 3 or i >= len(rebalance_dates) - 3:  # Show first and last 3
            print(f"\n{rebal_date.date()}:")
            print(f"  Dilution signals (top 150): {len(date_signals)}")
            print(f"  With price data:             {len(signals_with_price)} ({join_rate:.1f}%)")
            print(f"  Without price data:          {len(signals_without_price)}")
            if len(signals_without_price) > 0:
                missing = signals_without_price['symbol'].tolist()[:5]
                print(f"  Missing symbols: {missing}")
    
    join_df = pd.DataFrame(join_stats)
    
    print(f"\n" + "-" * 80)
    print(f"SUMMARY STATISTICS:")
    print(f"  Average join rate: {join_df['join_rate_pct'].mean():.1f}%")
    print(f"  Min join rate:     {join_df['join_rate_pct'].min():.1f}%")
    print(f"  Max join rate:     {join_df['join_rate_pct'].max():.1f}%")
    
    return join_df


def run_backtest_with_clipping(price_df, signals_df, top_n=10, transaction_cost=0.001, 
                                initial_capital=10000, clip_percentiles=(1, 99)):
    """
    Run dilution backtest with return clipping.
    
    Args:
        price_df: Price data with returns
        signals_df: Dilution signals
        top_n: Number of positions per side
        transaction_cost: Transaction cost per trade
        initial_capital: Initial capital
        clip_percentiles: Tuple of (lower, upper) percentiles for clipping
        
    Returns:
        Portfolio dataframe with results
    """
    print("\n" + "=" * 80)
    print(f"RUNNING BACKTEST WITH {clip_percentiles[0]}-{clip_percentiles[1]}% PERCENTILE CLIPPING")
    print("=" * 80)
    
    # Calculate clipping thresholds from all returns
    all_returns = price_df['return'].dropna()
    lower_threshold = np.percentile(all_returns, clip_percentiles[0])
    upper_threshold = np.percentile(all_returns, clip_percentiles[1])
    
    print(f"\nReturn clipping thresholds:")
    print(f"  Lower ({clip_percentiles[0]}%): {lower_threshold:.4f} ({lower_threshold*100:.2f}%)")
    print(f"  Upper ({clip_percentiles[1]}%): {upper_threshold:.4f} ({upper_threshold*100:.2f}%)")
    
    # Clip returns
    price_df_clipped = price_df.copy()
    price_df_clipped['return_original'] = price_df_clipped['return']
    price_df_clipped['return'] = price_df_clipped['return'].clip(lower_threshold, upper_threshold)
    
    n_clipped = (
        (price_df_clipped['return_original'] < lower_threshold) | 
        (price_df_clipped['return_original'] > upper_threshold)
    ).sum()
    print(f"  Clipped {n_clipped} returns ({n_clipped/len(all_returns)*100:.2f}% of all returns)")
    
    # Get rebalance dates
    rebalance_dates = sorted(signals_df['date'].unique())
    
    portfolio_history = []
    current_portfolio = {}
    portfolio_value = initial_capital
    
    print(f"\nRunning backtest ({len(rebalance_dates)} rebalance dates)...")
    
    for i, rebal_date in enumerate(rebalance_dates):
        if (i + 1) % 5 == 0:
            print(f"  Progress: {i+1}/{len(rebalance_dates)}")
        
        # Get signals for this date
        date_signals = signals_df[signals_df['date'] == rebal_date].copy()
        
        # Construct portfolio
        new_portfolio = construct_risk_parity_portfolio(
            date_signals, price_df_clipped, rebal_date, top_n=top_n
        )
        
        if len(new_portfolio) == 0:
            continue
        
        # Calculate turnover
        turnover = 0.0
        all_symbols = set(list(current_portfolio.keys()) + list(new_portfolio.keys()))
        for symbol in all_symbols:
            old_weight = current_portfolio.get(symbol, {}).get('weight', 0)
            new_weight = new_portfolio.get(symbol, {}).get('weight', 0)
            turnover += abs(new_weight - old_weight)
        
        transaction_cost_impact = turnover * transaction_cost
        portfolio_value *= (1 - transaction_cost_impact)
        
        # Calculate returns until next rebalance
        if i < len(rebalance_dates) - 1:
            next_rebal = rebalance_dates[i + 1]
        else:
            next_rebal = price_df_clipped['date'].max()
        
        holding_period = price_df_clipped[
            (price_df_clipped['date'] > rebal_date) &
            (price_df_clipped['date'] <= next_rebal)
        ].copy()
        
        for date in sorted(holding_period['date'].unique()):
            daily_returns = holding_period[holding_period['date'] == date]
            portfolio_return = 0.0
            valid_positions = 0
            
            # Calculate daily return for each position
            for symbol, position in new_portfolio.items():
                base_symbol = symbol
                symbol_data = daily_returns[daily_returns['base'] == base_symbol]
                
                if len(symbol_data) == 0:
                    continue
                
                if 'return' in symbol_data.columns:
                    symbol_return = symbol_data['return'].values[0]
                else:
                    continue
                
                if not np.isnan(symbol_return):
                    portfolio_return += position['weight'] * symbol_return
                    valid_positions += 1
            
            if valid_positions > 0:
                portfolio_value *= (1 + portfolio_return)
                portfolio_history.append({
                    'date': date,
                    'portfolio_value': portfolio_value,
                    'return': portfolio_return,
                    'n_positions': len(new_portfolio),
                    'valid_positions': valid_positions
                })
        
        current_portfolio = new_portfolio
    
    portfolio_df = pd.DataFrame(portfolio_history)
    
    print(f"\n? Backtest complete: {len(portfolio_df)} days")
    
    return portfolio_df


def calculate_metrics(portfolio_df, initial_capital=10000):
    """Calculate performance metrics."""
    if len(portfolio_df) == 0:
        return {}
    
    portfolio_df = portfolio_df.copy()
    portfolio_df['daily_return'] = portfolio_df['portfolio_value'].pct_change()
    
    final_value = portfolio_df['portfolio_value'].iloc[-1]
    total_return = (final_value - initial_capital) / initial_capital
    
    days = len(portfolio_df)
    years = days / 365.25
    annualized_return = (final_value / initial_capital) ** (1 / years) - 1 if years > 0 else 0
    
    daily_returns = portfolio_df['daily_return'].dropna()
    volatility = daily_returns.std() * np.sqrt(365)
    sharpe = annualized_return / volatility if volatility > 0 else 0
    
    # Max drawdown
    cumulative = portfolio_df['portfolio_value']
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # Win rate
    win_rate = (daily_returns > 0).sum() / len(daily_returns) if len(daily_returns) > 0 else 0
    
    # Sortino ratio
    downside_returns = daily_returns[daily_returns < 0]
    downside_vol = downside_returns.std() * np.sqrt(365) if len(downside_returns) > 0 else 0
    sortino = annualized_return / downside_vol if downside_vol > 0 else 0
    
    return {
        'total_return': total_return,
        'annualized_return': annualized_return,
        'volatility': volatility,
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'n_days': days,
        'final_value': final_value
    }


def plot_comparison(portfolio_noclip, portfolio_clipped, metrics_noclip, metrics_clipped):
    """Plot comparison of results."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    
    # Plot 1: Portfolio value comparison
    ax1 = axes[0, 0]
    ax1.plot(portfolio_noclip['date'], portfolio_noclip['portfolio_value'], 
             label='No Clipping', linewidth=2, alpha=0.7)
    ax1.plot(portfolio_clipped['date'], portfolio_clipped['portfolio_value'], 
             label='1-99% Clipped', linewidth=2, alpha=0.7)
    ax1.set_ylabel('Portfolio Value ($)')
    ax1.set_title('Portfolio Value: No Clipping vs 1-99% Clipped', fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Drawdown comparison
    ax2 = axes[0, 1]
    
    cumulative_noclip = portfolio_noclip['portfolio_value']
    running_max_noclip = cumulative_noclip.expanding().max()
    drawdown_noclip = (cumulative_noclip - running_max_noclip) / running_max_noclip * 100
    
    cumulative_clipped = portfolio_clipped['portfolio_value']
    running_max_clipped = cumulative_clipped.expanding().max()
    drawdown_clipped = (cumulative_clipped - running_max_clipped) / running_max_clipped * 100
    
    ax2.plot(portfolio_noclip['date'], drawdown_noclip, 
             label='No Clipping', linewidth=1, alpha=0.7)
    ax2.plot(portfolio_clipped['date'], drawdown_clipped, 
             label='1-99% Clipped', linewidth=1, alpha=0.7)
    ax2.set_ylabel('Drawdown (%)')
    ax2.set_title('Drawdown Comparison', fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Rolling returns comparison
    ax3 = axes[1, 0]
    
    portfolio_noclip['rolling_30d'] = portfolio_noclip['return'].rolling(30).sum() * 100
    portfolio_clipped['rolling_30d'] = portfolio_clipped['return'].rolling(30).sum() * 100
    
    ax3.plot(portfolio_noclip['date'], portfolio_noclip['rolling_30d'], 
             label='No Clipping', linewidth=1.5, alpha=0.7)
    ax3.plot(portfolio_clipped['date'], portfolio_clipped['rolling_30d'], 
             label='1-99% Clipped', linewidth=1.5, alpha=0.7)
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.3)
    ax3.set_ylabel('30-Day Rolling Return (%)')
    ax3.set_xlabel('Date')
    ax3.set_title('30-Day Rolling Returns', fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # Plot 4: Metrics comparison table
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    metrics_data = [
        ['Metric', 'No Clipping', '1-99% Clipped', 'Difference'],
        ['Total Return', f"{metrics_noclip['total_return']:.2%}", 
         f"{metrics_clipped['total_return']:.2%}",
         f"{metrics_clipped['total_return'] - metrics_noclip['total_return']:.2%}"],
        ['Annualized Return', f"{metrics_noclip['annualized_return']:.2%}", 
         f"{metrics_clipped['annualized_return']:.2%}",
         f"{metrics_clipped['annualized_return'] - metrics_noclip['annualized_return']:.2%}"],
        ['Volatility', f"{metrics_noclip['volatility']:.2%}", 
         f"{metrics_clipped['volatility']:.2%}",
         f"{metrics_clipped['volatility'] - metrics_noclip['volatility']:.2%}"],
        ['Sharpe Ratio', f"{metrics_noclip['sharpe_ratio']:.3f}", 
         f"{metrics_clipped['sharpe_ratio']:.3f}",
         f"{metrics_clipped['sharpe_ratio'] - metrics_noclip['sharpe_ratio']:.3f}"],
        ['Max Drawdown', f"{metrics_noclip['max_drawdown']:.2%}", 
         f"{metrics_clipped['max_drawdown']:.2%}",
         f"{metrics_clipped['max_drawdown'] - metrics_noclip['max_drawdown']:.2%}"],
        ['Win Rate', f"{metrics_noclip['win_rate']:.2%}", 
         f"{metrics_clipped['win_rate']:.2%}",
         f"{metrics_clipped['win_rate'] - metrics_noclip['win_rate']:.2%}"],
    ]
    
    table = ax4.table(cellText=metrics_data, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.5)
    
    # Style header row
    for i in range(4):
        table[(0, i)].set_facecolor('#40466e')
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    ax4.set_title('Performance Metrics Comparison', fontweight='bold', pad=20)
    
    plt.tight_layout()
    plt.savefig('dilution_backtest_clipping_comparison.png', dpi=300, bbox_inches='tight')
    print("\n? Saved: dilution_backtest_clipping_comparison.png")
    plt.close()


def main():
    """Main execution."""
    print("=" * 80)
    print("DILUTION FACTOR BACKTEST - DATA JOINING ANALYSIS")
    print("=" * 80)
    print()
    
    # Load data
    price_df, hist_df = load_data()
    
    # Analyze symbol overlap
    common_symbols, dilution_only = analyze_symbol_overlap(price_df, hist_df)
    
    # Calculate rolling signals
    print("\n" + "=" * 80)
    print("CALCULATING ROLLING DILUTION SIGNALS")
    print("=" * 80)
    signals_df = calculate_rolling_dilution_signal(hist_df, lookback_months=12)
    
    # Analyze data joining per rebalance
    join_df = analyze_data_joining_per_rebalance(price_df, signals_df)
    
    # Run backtest without clipping
    print("\n" + "=" * 80)
    print("RUNNING BACKTEST WITHOUT CLIPPING (BASELINE)")
    print("=" * 80)
    portfolio_noclip = run_backtest_with_clipping(
        price_df, signals_df, top_n=10, clip_percentiles=(0, 100)
    )
    metrics_noclip = calculate_metrics(portfolio_noclip)
    
    # Run backtest with 1-99% clipping
    portfolio_clipped = run_backtest_with_clipping(
        price_df, signals_df, top_n=10, clip_percentiles=(1, 99)
    )
    metrics_clipped = calculate_metrics(portfolio_clipped)
    
    # Print results
    print("\n" + "=" * 80)
    print("RESULTS COMPARISON")
    print("=" * 80)
    
    print("\nNO CLIPPING:")
    print(f"  Total Return:       {metrics_noclip['total_return']:>8.2%}")
    print(f"  Annualized Return:  {metrics_noclip['annualized_return']:>8.2%}")
    print(f"  Volatility:         {metrics_noclip['volatility']:>8.2%}")
    print(f"  Sharpe Ratio:       {metrics_noclip['sharpe_ratio']:>8.3f}")
    print(f"  Sortino Ratio:      {metrics_noclip['sortino_ratio']:>8.3f}")
    print(f"  Max Drawdown:       {metrics_noclip['max_drawdown']:>8.2%}")
    print(f"  Win Rate:           {metrics_noclip['win_rate']:>8.2%}")
    
    print("\n1-99% PERCENTILE CLIPPING:")
    print(f"  Total Return:       {metrics_clipped['total_return']:>8.2%}")
    print(f"  Annualized Return:  {metrics_clipped['annualized_return']:>8.2%}")
    print(f"  Volatility:         {metrics_clipped['volatility']:>8.2%}")
    print(f"  Sharpe Ratio:       {metrics_clipped['sharpe_ratio']:>8.3f}")
    print(f"  Sortino Ratio:      {metrics_clipped['sortino_ratio']:>8.3f}")
    print(f"  Max Drawdown:       {metrics_clipped['max_drawdown']:>8.2%}")
    print(f"  Win Rate:           {metrics_clipped['win_rate']:>8.2%}")
    
    print("\nDIFFERENCE (Clipped - No Clip):")
    print(f"  Total Return:       {metrics_clipped['total_return'] - metrics_noclip['total_return']:>8.2%}")
    print(f"  Annualized Return:  {metrics_clipped['annualized_return'] - metrics_noclip['annualized_return']:>8.2%}")
    print(f"  Volatility:         {metrics_clipped['volatility'] - metrics_noclip['volatility']:>8.2%}")
    print(f"  Sharpe Ratio:       {metrics_clipped['sharpe_ratio'] - metrics_noclip['sharpe_ratio']:>8.3f}")
    print(f"  Max Drawdown:       {metrics_clipped['max_drawdown'] - metrics_noclip['max_drawdown']:>8.2%}")
    
    # Plot comparison
    plot_comparison(portfolio_noclip, portfolio_clipped, metrics_noclip, metrics_clipped)
    
    # Save results
    portfolio_clipped.to_csv('dilution_backtest_clipped_portfolio.csv', index=False)
    join_df.to_csv('dilution_backtest_join_analysis.csv', index=False)
    
    print("\n? Saved: dilution_backtest_clipped_portfolio.csv")
    print("? Saved: dilution_backtest_join_analysis.csv")
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
