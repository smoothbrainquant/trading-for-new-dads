#!/usr/bin/env python3
"""
Dilution Factor Strategy Backtest - Bug Comparison

This script runs BOTH versions (buggy and fixed) side-by-side to demonstrate
the impact of the portfolio construction bug.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os
import sys

# Import functions from the original backtest
sys.path.append('/workspace/backtests/scripts')


def load_historical_price_data():
    """Load historical price data."""
    possible_paths = [
        'data/raw/combined_coinbase_coinmarketcap_daily.csv',
        '/workspace/data/raw/combined_coinbase_coinmarketcap_daily.csv',
    ]
    
    df = None
    for path in possible_paths:
        if os.path.exists(path):
            print(f"Loading price data from: {path}")
            df = pd.read_csv(path)
            break
    
    if df is None:
        raise FileNotFoundError("Could not find price data file")
    
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['date'] >= '2021-01-01'].copy()
    df = df.sort_values(['base', 'date'])
    df['return'] = df.groupby('base')['close'].pct_change()
    df['return_next'] = df.groupby('base')['return'].shift(-1)
    
    print(f"Loaded price data: {len(df)} records, {df['base'].nunique()} coins")
    
    return df


def load_historical_dilution_snapshots():
    """Load historical dilution snapshots."""
    hist_file = 'crypto_dilution_historical_2021_2025.csv'
    if not os.path.exists(hist_file):
        hist_file = '/workspace/crypto_dilution_historical_2021_2025.csv'
    
    df = pd.read_csv(hist_file)
    df['date'] = pd.to_datetime(df['date'])
    
    print(f"Loaded historical dilution: {len(df)} records, {df['Symbol'].nunique()} coins")
    
    return df


def calculate_rolling_dilution_signal(historical_dilution_df, lookback_months=12):
    """Calculate rolling dilution velocity for each coin."""
    signals = []
    rebalance_dates = sorted(historical_dilution_df['date'].unique())
    
    for rebal_date in rebalance_dates:
        lookback_start = rebal_date - pd.DateOffset(months=lookback_months)
        window_data = historical_dilution_df[
            (historical_dilution_df['date'] >= lookback_start) &
            (historical_dilution_df['date'] <= rebal_date)
        ].copy()
        
        for symbol in window_data['Symbol'].unique():
            coin_data = window_data[window_data['Symbol'] == symbol].sort_values('date')
            
            if len(coin_data) < 2:
                continue
            
            first = coin_data.iloc[0]
            last = coin_data.iloc[-1]
            
            days_elapsed = (last['date'] - first['date']).days
            if days_elapsed == 0:
                continue
            
            years_elapsed = days_elapsed / 365.25
            circ_pct_change = last['circulating_pct'] - first['circulating_pct']
            dilution_velocity = circ_pct_change / years_elapsed if years_elapsed > 0 else 0
            
            signals.append({
                'date': rebal_date,
                'symbol': symbol,
                'dilution_velocity': dilution_velocity,
                'market_cap': last['Market Cap'],
                'rank': last['Rank'],
                'price': last['Price'],
                'circulating_pct': last['circulating_pct']
            })
    
    return pd.DataFrame(signals)


def calculate_volatility(price_df, symbol, end_date, lookback_days=90):
    """Calculate historical volatility."""
    lookback_start = end_date - pd.DateOffset(days=lookback_days)
    
    coin_data = price_df[
        (price_df['base'] == symbol) &
        (price_df['date'] >= lookback_start) &
        (price_df['date'] <= end_date)
    ].copy()
    
    if len(coin_data) < 20:
        return np.nan
    
    returns = coin_data['return'].dropna()
    volatility = returns.std() * np.sqrt(365)
    
    return volatility


def construct_portfolio_BUGGY(signals, price_df, rebal_date, top_n=10):
    """BUGGY VERSION: Select first, filter later."""
    valid_signals = signals[signals['dilution_velocity'].notna()].copy()
    valid_signals = valid_signals.nsmallest(150, 'rank')
    
    if len(valid_signals) < top_n * 2:
        return {}
    
    # BUGGY: Sort and select BEFORE checking price data
    valid_signals = valid_signals.sort_values('dilution_velocity')
    long_candidates = valid_signals.head(top_n).copy()
    short_candidates = valid_signals.tail(top_n).copy()
    
    # Now calculate volatility - many will fail
    long_candidates['volatility'] = long_candidates['symbol'].apply(
        lambda s: calculate_volatility(price_df, s, rebal_date)
    )
    short_candidates['volatility'] = short_candidates['symbol'].apply(
        lambda s: calculate_volatility(price_df, s, rebal_date)
    )
    
    # Remove positions without volatility data
    long_candidates = long_candidates[long_candidates['volatility'].notna()]
    short_candidates = short_candidates[short_candidates['volatility'].notna()]
    
    if len(long_candidates) == 0 or len(short_candidates) == 0:
        return {}
    
    # Risk parity weighting
    long_candidates['inv_vol'] = 1.0 / long_candidates['volatility']
    short_candidates['inv_vol'] = 1.0 / short_candidates['volatility']
    
    long_total = long_candidates['inv_vol'].sum()
    short_total = short_candidates['inv_vol'].sum()
    
    long_candidates['weight'] = long_candidates['inv_vol'] / long_total
    short_candidates['weight'] = -short_candidates['inv_vol'] / short_total
    
    portfolio = {}
    for _, row in long_candidates.iterrows():
        portfolio[row['symbol']] = {
            'weight': row['weight'],
            'side': 'long',
            'dilution_velocity': row['dilution_velocity'],
            'volatility': row['volatility']
        }
    
    for _, row in short_candidates.iterrows():
        portfolio[row['symbol']] = {
            'weight': row['weight'],
            'side': 'short',
            'dilution_velocity': row['dilution_velocity'],
            'volatility': row['volatility']
        }
    
    return portfolio


def construct_portfolio_FIXED(signals, price_df, rebal_date, top_n=10):
    """FIXED VERSION: Filter by price data availability FIRST."""
    valid_signals = signals[signals['dilution_velocity'].notna()].copy()
    valid_signals = valid_signals.nsmallest(150, 'rank')
    
    if len(valid_signals) < top_n * 2:
        return {}
    
    # FIXED: Filter to coins with price data FIRST
    available_coins = price_df['base'].unique()
    valid_signals = valid_signals[valid_signals['symbol'].isin(available_coins)]
    
    # Pre-calculate volatility for all candidates
    valid_signals['volatility'] = valid_signals['symbol'].apply(
        lambda s: calculate_volatility(price_df, s, rebal_date)
    )
    
    # Keep only coins with valid volatility
    valid_signals = valid_signals[valid_signals['volatility'].notna()]
    
    if len(valid_signals) < 4:
        return {}
    
    # Adjust position count if needed
    adjusted_top_n = min(top_n, len(valid_signals) // 2)
    
    # NOW select top/bottom from valid universe
    valid_signals = valid_signals.sort_values('dilution_velocity')
    long_candidates = valid_signals.head(adjusted_top_n).copy()
    short_candidates = valid_signals.tail(adjusted_top_n).copy()
    
    if len(long_candidates) == 0 or len(short_candidates) == 0:
        return {}
    
    # Risk parity weighting
    long_candidates['inv_vol'] = 1.0 / long_candidates['volatility']
    short_candidates['inv_vol'] = 1.0 / short_candidates['volatility']
    
    long_total = long_candidates['inv_vol'].sum()
    short_total = short_candidates['inv_vol'].sum()
    
    long_candidates['weight'] = long_candidates['inv_vol'] / long_total
    short_candidates['weight'] = -short_candidates['inv_vol'] / short_total
    
    portfolio = {}
    for _, row in long_candidates.iterrows():
        portfolio[row['symbol']] = {
            'weight': row['weight'],
            'side': 'long',
            'dilution_velocity': row['dilution_velocity'],
            'volatility': row['volatility']
        }
    
    for _, row in short_candidates.iterrows():
        portfolio[row['symbol']] = {
            'weight': row['weight'],
            'side': 'short',
            'dilution_velocity': row['dilution_velocity'],
            'volatility': row['volatility']
        }
    
    return portfolio


def backtest_strategy(signals_df, price_df, construct_func, version_name, top_n=10):
    """Run backtest with specified portfolio construction function."""
    print(f"\n{'='*80}")
    print(f"Running backtest: {version_name}")
    print(f"{'='*80}")
    
    rebalance_dates = sorted(signals_df['date'].unique())
    portfolio_history = []
    current_portfolio = {}
    portfolio_value = 1.0
    
    for i, rebal_date in enumerate(rebalance_dates):
        if i % 10 == 0:
            print(f"Progress: {i+1}/{len(rebalance_dates)}")
        
        date_signals = signals_df[signals_df['date'] == rebal_date].copy()
        new_portfolio = construct_func(date_signals, price_df, rebal_date, top_n=top_n)
        
        if len(new_portfolio) == 0:
            continue
        
        # Calculate returns until next rebalance
        if i < len(rebalance_dates) - 1:
            next_rebal = rebalance_dates[i + 1]
        else:
            next_rebal = price_df['date'].max()
        
        holding_period = price_df[
            (price_df['date'] > rebal_date) &
            (price_df['date'] <= next_rebal)
        ].copy()
        
        for date in sorted(holding_period['date'].unique()):
            daily_returns = holding_period[holding_period['date'] == date]
            
            portfolio_return = 0.0
            valid_positions = 0
            
            for symbol, position in new_portfolio.items():
                symbol_return = daily_returns[daily_returns['base'] == symbol]['return'].values
                
                if len(symbol_return) > 0 and not np.isnan(symbol_return[0]):
                    portfolio_return += position['weight'] * symbol_return[0]
                    valid_positions += 1
            
            if valid_positions > 0:
                portfolio_value *= (1 + portfolio_return)
                
                portfolio_history.append({
                    'date': date,
                    'portfolio_value': portfolio_value,
                    'return': portfolio_return,
                    'n_positions': len(new_portfolio),
                    'n_long': sum(1 for p in new_portfolio.values() if p['side'] == 'long'),
                    'n_short': sum(1 for p in new_portfolio.values() if p['side'] == 'short')
                })
        
        current_portfolio = new_portfolio
    
    return pd.DataFrame(portfolio_history)


def calculate_metrics(portfolio_df):
    """Calculate performance metrics."""
    if len(portfolio_df) == 0:
        return {}
    
    total_return = (portfolio_df['portfolio_value'].iloc[-1] / portfolio_df['portfolio_value'].iloc[0] - 1) * 100
    
    days = (portfolio_df['date'].max() - portfolio_df['date'].min()).days
    years = days / 365.25
    annualized_return = ((portfolio_df['portfolio_value'].iloc[-1] / portfolio_df['portfolio_value'].iloc[0]) ** (1/years) - 1) * 100
    
    daily_returns = portfolio_df['return'].dropna()
    volatility = daily_returns.std() * np.sqrt(365) * 100
    sharpe = annualized_return / volatility if volatility > 0 else 0
    
    cumulative = portfolio_df['portfolio_value']
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max * 100
    max_drawdown = drawdown.min()
    
    win_rate = (daily_returns > 0).sum() / len(daily_returns) * 100
    
    return {
        'total_return_pct': total_return,
        'annualized_return_pct': annualized_return,
        'volatility_pct': volatility,
        'sharpe_ratio': sharpe,
        'max_drawdown_pct': max_drawdown,
        'win_rate_pct': win_rate,
        'n_days': len(portfolio_df),
        'avg_positions': portfolio_df['n_positions'].mean(),
        'median_positions': portfolio_df['n_positions'].median()
    }


def create_comparison_chart(buggy_df, fixed_df):
    """Create side-by-side comparison chart."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Plot 1: Portfolio values
    ax1 = axes[0, 0]
    ax1.plot(buggy_df['date'], buggy_df['portfolio_value'], 
            linewidth=2, color='red', label='Buggy (1-4 positions)', alpha=0.7)
    ax1.plot(fixed_df['date'], fixed_df['portfolio_value'], 
            linewidth=2, color='green', label='Fixed (10-16 positions)', alpha=0.7)
    ax1.set_ylabel('Portfolio Value ($)', fontsize=12)
    ax1.set_title('Portfolio Value: Buggy vs Fixed', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.set_yscale('log')
    
    # Plot 2: Position counts
    ax2 = axes[0, 1]
    ax2.plot(buggy_df['date'], buggy_df['n_positions'], 
            linewidth=1, color='red', label='Buggy', alpha=0.7)
    ax2.plot(fixed_df['date'], fixed_df['n_positions'], 
            linewidth=1, color='green', label='Fixed', alpha=0.7)
    ax2.set_ylabel('Number of Positions', fontsize=12)
    ax2.set_title('Portfolio Diversification', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=20, color='blue', linestyle='--', linewidth=1, alpha=0.5, label='Target (20)')
    
    # Plot 3: Daily returns distribution
    ax3 = axes[1, 0]
    ax3.hist(buggy_df['return'] * 100, bins=50, alpha=0.5, color='red', label='Buggy')
    ax3.hist(fixed_df['return'] * 100, bins=50, alpha=0.5, color='green', label='Fixed')
    ax3.set_xlabel('Daily Return (%)', fontsize=12)
    ax3.set_ylabel('Frequency', fontsize=12)
    ax3.set_title('Daily Returns Distribution', fontsize=14, fontweight='bold')
    ax3.legend(fontsize=11)
    ax3.grid(True, alpha=0.3)
    ax3.set_xlim(-25, 65)
    
    # Plot 4: Cumulative returns
    ax4 = axes[1, 1]
    buggy_cumret = (buggy_df['portfolio_value'] / buggy_df['portfolio_value'].iloc[0] - 1) * 100
    fixed_cumret = (fixed_df['portfolio_value'] / fixed_df['portfolio_value'].iloc[0] - 1) * 100
    ax4.plot(buggy_df['date'], buggy_cumret, 
            linewidth=2, color='red', label='Buggy', alpha=0.7)
    ax4.plot(fixed_df['date'], fixed_cumret, 
            linewidth=2, color='green', label='Fixed', alpha=0.7)
    ax4.set_ylabel('Cumulative Return (%)', fontsize=12)
    ax4.set_xlabel('Date', fontsize=12)
    ax4.set_title('Cumulative Returns', fontsize=14, fontweight='bold')
    ax4.legend(fontsize=11)
    ax4.grid(True, alpha=0.3)
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('dilution_factor_bug_vs_fixed_comparison.png', dpi=300, bbox_inches='tight')
    print("? Saved: dilution_factor_bug_vs_fixed_comparison.png")
    plt.close()


def main():
    """Main execution."""
    print("="*80)
    print("DILUTION FACTOR: BUGGY VS FIXED COMPARISON")
    print("="*80)
    
    # Load data
    price_df = load_historical_price_data()
    dilution_df = load_historical_dilution_snapshots()
    
    print("\nCalculating dilution signals...")
    signals_df = calculate_rolling_dilution_signal(dilution_df)
    
    # Run buggy version
    buggy_df = backtest_strategy(signals_df, price_df, construct_portfolio_BUGGY, "BUGGY")
    buggy_metrics = calculate_metrics(buggy_df)
    
    # Run fixed version  
    fixed_df = backtest_strategy(signals_df, price_df, construct_portfolio_FIXED, "FIXED")
    fixed_metrics = calculate_metrics(fixed_df)
    
    # Print comparison
    print("\n" + "="*80)
    print("RESULTS COMPARISON")
    print("="*80)
    
    metrics_names = [
        ('Total Return (%)', 'total_return_pct'),
        ('Annualized Return (%)', 'annualized_return_pct'),
        ('Volatility (%)', 'volatility_pct'),
        ('Sharpe Ratio', 'sharpe_ratio'),
        ('Max Drawdown (%)', 'max_drawdown_pct'),
        ('Win Rate (%)', 'win_rate_pct'),
        ('Avg Positions', 'avg_positions'),
        ('Median Positions', 'median_positions')
    ]
    
    print(f"\n{'Metric':<25} {'Buggy':>15} {'Fixed':>15} {'Difference':>15}")
    print("-" * 70)
    
    for name, key in metrics_names:
        buggy_val = buggy_metrics[key]
        fixed_val = fixed_metrics[key]
        diff = fixed_val - buggy_val
        print(f"{name:<25} {buggy_val:>15.2f} {fixed_val:>15.2f} {diff:>15.2f}")
    
    # Create visualization
    print("\nGenerating comparison charts...")
    create_comparison_chart(buggy_df, fixed_df)
    
    # Save results
    comparison = pd.DataFrame({
        'Metric': [name for name, _ in metrics_names],
        'Buggy': [buggy_metrics[key] for _, key in metrics_names],
        'Fixed': [fixed_metrics[key] for _, key in metrics_names],
        'Difference': [fixed_metrics[key] - buggy_metrics[key] for _, key in metrics_names]
    })
    comparison.to_csv('dilution_factor_bug_fix_comparison.csv', index=False)
    print("? Saved: dilution_factor_bug_fix_comparison.csv")
    
    print("\n" + "="*80)
    print("COMPARISON COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
