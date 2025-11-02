#!/usr/bin/env python3
"""
Optimize Rebalancing Frequency for Dilution Factor Strategy

Tests different rebalancing frequencies:
- Weekly (7 days)
- Biweekly (14 days)
- Monthly (30 days)
- Bimonthly (60 days)
- Quarterly (90 days)

Evaluates:
- Gross returns
- Net returns (after transaction costs)
- Sharpe ratio
- Turnover
- Max drawdown
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import sys
import os

# Import functions from the main backtest script
sys.path.append('/workspace/backtests/scripts')


def load_data():
    """Load price and dilution data."""
    # Load price data
    price_file = '/workspace/data/raw/combined_coinbase_coinmarketcap_daily.csv'
    price_df = pd.read_csv(price_file)
    price_df['date'] = pd.to_datetime(price_df['date'])
    price_df = price_df[price_df['date'] >= '2021-01-01'].copy()
    price_df = price_df.sort_values(['base', 'date'])
    price_df['return'] = price_df.groupby('base')['close'].pct_change()
    
    # Load historical dilution
    hist_file = '/workspace/crypto_dilution_historical_2021_2025.csv'
    hist_df = pd.read_csv(hist_file)
    hist_df['date'] = pd.to_datetime(hist_df['date'])
    
    return price_df, hist_df


def calculate_rolling_dilution_signal(historical_dilution_df, lookback_months=12):
    """Calculate rolling dilution velocity."""
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


def construct_risk_parity_portfolio(signals, price_df, rebal_date, top_n=10):
    """Construct risk parity weighted long/short portfolio."""
    valid_signals = signals[signals['dilution_velocity'].notna()].copy()
    valid_signals = valid_signals.nsmallest(150, 'rank')
    
    if len(valid_signals) < top_n * 2:
        return {}
    
    valid_signals = valid_signals.sort_values('dilution_velocity')
    long_candidates = valid_signals.head(top_n).copy()
    short_candidates = valid_signals.tail(top_n).copy()
    
    long_candidates['volatility'] = long_candidates['symbol'].apply(
        lambda s: calculate_volatility(price_df, s, rebal_date)
    )
    short_candidates['volatility'] = short_candidates['symbol'].apply(
        lambda s: calculate_volatility(price_df, s, rebal_date)
    )
    
    long_candidates = long_candidates[long_candidates['volatility'].notna()]
    short_candidates = short_candidates[short_candidates['volatility'].notna()]
    
    if len(long_candidates) == 0 or len(short_candidates) == 0:
        return {}
    
    long_candidates['inv_vol'] = 1.0 / long_candidates['volatility']
    short_candidates['inv_vol'] = 1.0 / short_candidates['volatility']
    
    long_total_inv_vol = long_candidates['inv_vol'].sum()
    short_total_inv_vol = short_candidates['inv_vol'].sum()
    
    long_candidates['weight'] = long_candidates['inv_vol'] / long_total_inv_vol
    short_candidates['weight'] = -short_candidates['inv_vol'] / short_total_inv_vol
    
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


def backtest_with_frequency(signals_df, price_df, rebalance_days, top_n=10, transaction_cost=0.001):
    """
    Backtest with specific rebalancing frequency.
    
    Args:
        signals_df: Dilution signals
        price_df: Price data
        rebalance_days: Days between rebalances
        top_n: Number of long/short positions
        transaction_cost: Transaction cost per trade (0.1% = 0.001)
    """
    # Create rebalance dates based on frequency
    start_date = price_df['date'].min()
    end_date = price_df['date'].max()
    
    rebalance_dates = []
    current_date = start_date
    while current_date <= end_date:
        # Find nearest signal date
        nearest_signal = signals_df[signals_df['date'] >= current_date]['date'].min()
        if pd.notna(nearest_signal):
            rebalance_dates.append(nearest_signal)
        current_date += pd.Timedelta(days=rebalance_days)
    
    rebalance_dates = sorted(list(set(rebalance_dates)))
    
    portfolio_history = []
    current_portfolio = {}
    portfolio_value = 1.0
    total_turnover = 0.0
    n_rebalances = 0
    
    for i, rebal_date in enumerate(rebalance_dates):
        date_signals = signals_df[signals_df['date'] == rebal_date].copy()
        new_portfolio = construct_risk_parity_portfolio(date_signals, price_df, rebal_date, top_n=top_n)
        
        if len(new_portfolio) == 0:
            continue
        
        # Calculate turnover
        turnover = 0.0
        all_symbols = set(list(current_portfolio.keys()) + list(new_portfolio.keys()))
        for symbol in all_symbols:
            old_weight = current_portfolio.get(symbol, {}).get('weight', 0)
            new_weight = new_portfolio.get(symbol, {}).get('weight', 0)
            turnover += abs(new_weight - old_weight)
        
        # Apply transaction costs
        transaction_cost_impact = turnover * transaction_cost
        portfolio_value *= (1 - transaction_cost_impact)
        total_turnover += turnover
        n_rebalances += 1
        
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
                    'return': portfolio_return
                })
        
        current_portfolio = new_portfolio
    
    portfolio_df = pd.DataFrame(portfolio_history)
    
    # Calculate metrics
    if len(portfolio_df) > 0:
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
        
        avg_turnover = total_turnover / n_rebalances if n_rebalances > 0 else 0
        
        metrics = {
            'rebalance_days': rebalance_days,
            'total_return_pct': total_return,
            'annualized_return_pct': annualized_return,
            'volatility_pct': volatility,
            'sharpe_ratio': sharpe,
            'max_drawdown_pct': max_drawdown,
            'avg_turnover': avg_turnover,
            'n_rebalances': n_rebalances,
            'total_turnover': total_turnover,
            'transaction_costs_pct': (total_turnover * transaction_cost) * 100
        }
    else:
        metrics = {}
    
    return portfolio_df, metrics


def test_all_frequencies(signals_df, price_df):
    """Test multiple rebalancing frequencies."""
    frequencies = [
        (7, 'Weekly'),
        (14, 'Biweekly'),
        (21, '3-Week'),
        (30, 'Monthly'),
        (45, '6-Week'),
        (60, 'Bimonthly'),
        (90, 'Quarterly')
    ]
    
    results = []
    
    for days, label in frequencies:
        print(f"\nTesting {label} rebalancing ({days} days)...")
        portfolio_df, metrics = backtest_with_frequency(
            signals_df, price_df, days, top_n=10, transaction_cost=0.001
        )
        
        if len(metrics) > 0:
            metrics['label'] = label
            results.append(metrics)
            
            print(f"  Return: {metrics['total_return_pct']:.1f}%")
            print(f"  Sharpe: {metrics['sharpe_ratio']:.2f}")
            print(f"  Rebalances: {metrics['n_rebalances']}")
            print(f"  Avg Turnover: {metrics['avg_turnover']:.2f}")
    
    return pd.DataFrame(results)


def plot_optimization_results(results_df):
    """Plot optimization results."""
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    
    # Sort by rebalance days for plotting
    results_df = results_df.sort_values('rebalance_days')
    
    # Plot 1: Total Return
    ax1 = axes[0, 0]
    ax1.bar(results_df['label'], results_df['total_return_pct'], color='blue', alpha=0.7)
    ax1.set_ylabel('Total Return (%)', fontsize=11)
    ax1.set_title('Total Return by Rebalancing Frequency', fontsize=12, fontweight='bold')
    ax1.tick_params(axis='x', rotation=45)
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Plot 2: Sharpe Ratio
    ax2 = axes[0, 1]
    colors = ['green' if x > 1 else 'orange' if x > 0.5 else 'red' for x in results_df['sharpe_ratio']]
    ax2.bar(results_df['label'], results_df['sharpe_ratio'], color=colors, alpha=0.7)
    ax2.axhline(y=1.0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    ax2.set_ylabel('Sharpe Ratio', fontsize=11)
    ax2.set_title('Risk-Adjusted Returns', fontsize=12, fontweight='bold')
    ax2.tick_params(axis='x', rotation=45)
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Plot 3: Max Drawdown
    ax3 = axes[0, 2]
    ax3.bar(results_df['label'], results_df['max_drawdown_pct'], color='red', alpha=0.7)
    ax3.set_ylabel('Max Drawdown (%)', fontsize=11)
    ax3.set_title('Maximum Drawdown', fontsize=12, fontweight='bold')
    ax3.tick_params(axis='x', rotation=45)
    ax3.grid(True, alpha=0.3, axis='y')
    
    # Plot 4: Turnover
    ax4 = axes[1, 0]
    ax4.bar(results_df['label'], results_df['avg_turnover'], color='purple', alpha=0.7)
    ax4.set_ylabel('Avg Turnover per Rebalance', fontsize=11)
    ax4.set_title('Portfolio Turnover', fontsize=12, fontweight='bold')
    ax4.tick_params(axis='x', rotation=45)
    ax4.grid(True, alpha=0.3, axis='y')
    
    # Plot 5: Transaction Costs
    ax5 = axes[1, 1]
    ax5.bar(results_df['label'], results_df['transaction_costs_pct'], color='orange', alpha=0.7)
    ax5.set_ylabel('Transaction Costs (%)', fontsize=11)
    ax5.set_title('Total Transaction Costs', fontsize=12, fontweight='bold')
    ax5.tick_params(axis='x', rotation=45)
    ax5.grid(True, alpha=0.3, axis='y')
    
    # Plot 6: Return vs Turnover Efficiency
    ax6 = axes[1, 2]
    ax6.scatter(results_df['avg_turnover'], results_df['total_return_pct'], 
               s=results_df['sharpe_ratio']*100, alpha=0.6, c=results_df['rebalance_days'], cmap='viridis')
    for _, row in results_df.iterrows():
        ax6.annotate(row['label'], (row['avg_turnover'], row['total_return_pct']), 
                    fontsize=8, alpha=0.8)
    ax6.set_xlabel('Avg Turnover', fontsize=11)
    ax6.set_ylabel('Total Return (%)', fontsize=11)
    ax6.set_title('Return vs Turnover Efficiency', fontsize=12, fontweight='bold')
    ax6.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('rebalancing_frequency_optimization.png', dpi=300, bbox_inches='tight')
    print(f"\n? Saved: rebalancing_frequency_optimization.png")
    plt.close()


def main():
    """Main execution."""
    print("=" * 80)
    print("REBALANCING FREQUENCY OPTIMIZATION")
    print("=" * 80)
    print("\nTesting frequencies: Weekly, Biweekly, Monthly, Bimonthly, Quarterly")
    print("Transaction cost: 0.1% per trade (0.05% each side)")
    
    # Load data
    print("\n" + "-" * 80)
    print("Loading data...")
    price_df, hist_df = load_data()
    
    # Calculate signals
    print("Calculating dilution signals...")
    signals_df = calculate_rolling_dilution_signal(hist_df, lookback_months=12)
    
    # Test all frequencies
    print("\n" + "-" * 80)
    print("TESTING REBALANCING FREQUENCIES")
    print("-" * 80)
    
    results_df = test_all_frequencies(signals_df, price_df)
    
    # Print summary
    print("\n" + "=" * 80)
    print("OPTIMIZATION RESULTS SUMMARY")
    print("=" * 80)
    
    # Sort by Sharpe ratio
    results_sorted = results_df.sort_values('sharpe_ratio', ascending=False)
    
    print("\n?? RANKED BY SHARPE RATIO:")
    print("-" * 80)
    for i, row in results_sorted.iterrows():
        print(f"{row['label']:12s}: Sharpe={row['sharpe_ratio']:.2f}, "
              f"Return={row['total_return_pct']:7.1f}%, "
              f"Turnover={row['avg_turnover']:.2f}, "
              f"Rebalances={row['n_rebalances']:3.0f}")
    
    # Best by different metrics
    print("\n?? BEST BY METRIC:")
    print("-" * 80)
    best_return = results_df.loc[results_df['total_return_pct'].idxmax()]
    print(f"Highest Return:    {best_return['label']} ({best_return['total_return_pct']:.1f}%)")
    
    best_sharpe = results_df.loc[results_df['sharpe_ratio'].idxmax()]
    print(f"Best Sharpe:       {best_sharpe['label']} ({best_sharpe['sharpe_ratio']:.2f})")
    
    best_dd = results_df.loc[results_df['max_drawdown_pct'].idxmax()]
    print(f"Lowest Drawdown:   {best_dd['label']} ({best_dd['max_drawdown_pct']:.1f}%)")
    
    lowest_turnover = results_df.loc[results_df['avg_turnover'].idxmin()]
    print(f"Lowest Turnover:   {lowest_turnover['label']} ({lowest_turnover['avg_turnover']:.2f})")
    
    # Recommendation
    print("\n?? RECOMMENDATION:")
    print("-" * 80)
    print(f"Optimal Frequency: {best_sharpe['label']}")
    print(f"  - Best risk-adjusted returns (Sharpe: {best_sharpe['sharpe_ratio']:.2f})")
    print(f"  - Return: {best_sharpe['total_return_pct']:.1f}%")
    print(f"  - Manageable turnover: {best_sharpe['avg_turnover']:.2f}")
    print(f"  - Rebalances: {best_sharpe['n_rebalances']:.0f} over ~4.7 years")
    
    # Plot results
    print("\n" + "-" * 80)
    print("Generating visualizations...")
    plot_optimization_results(results_df)
    
    # Save results
    results_df.to_csv('rebalancing_frequency_optimization.csv', index=False)
    print("? Saved: rebalancing_frequency_optimization.csv")
    
    print("\n" + "=" * 80)
    print("OPTIMIZATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
