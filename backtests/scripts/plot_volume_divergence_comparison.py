#!/usr/bin/env python3
"""
Plot comparison of Volume Divergence Factor strategies
"""

import pandas as pd
import matplotlib.pyplot as plt
import os

# Set style
plt.style.use('seaborn-v0_8-darkgrid')

# Load portfolio values for all strategies
results_dir = os.path.join(os.path.dirname(__file__), '..', 'results')

confirmation = pd.read_csv(os.path.join(results_dir, 'backtest_volume_divergence_portfolio_values.csv'))
momentum = pd.read_csv(os.path.join(results_dir, 'backtest_volume_momentum_portfolio_values.csv'))
contrarian = pd.read_csv(os.path.join(results_dir, 'backtest_contrarian_divergence_portfolio_values.csv'))

# Convert dates
confirmation['date'] = pd.to_datetime(confirmation['date'])
momentum['date'] = pd.to_datetime(momentum['date'])
contrarian['date'] = pd.to_datetime(contrarian['date'])

# Create figure with subplots
fig, axes = plt.subplots(2, 1, figsize=(14, 10))

# Plot 1: Equity Curves
ax1 = axes[0]
ax1.plot(confirmation['date'], confirmation['portfolio_value'], 
         label='Confirmation Premium', linewidth=2, alpha=0.8)
ax1.plot(momentum['date'], momentum['portfolio_value'], 
         label='Volume Momentum', linewidth=2, alpha=0.8)
ax1.plot(contrarian['date'], contrarian['portfolio_value'], 
         label='Contrarian Divergence (BEST)', linewidth=2.5, alpha=0.9, color='green')
ax1.axhline(y=10000, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='Initial Capital')

ax1.set_title('Volume Divergence Factor: Strategy Comparison', fontsize=16, fontweight='bold')
ax1.set_xlabel('Date', fontsize=12)
ax1.set_ylabel('Portfolio Value ($)', fontsize=12)
ax1.legend(fontsize=10, loc='upper left')
ax1.grid(True, alpha=0.3)

# Add annotations for final values
final_conf = confirmation['portfolio_value'].iloc[-1]
final_mom = momentum['portfolio_value'].iloc[-1]
final_cont = contrarian['portfolio_value'].iloc[-1]

ax1.text(0.02, 0.98, 
         f'Final Values:\n'
         f'Contrarian: ${final_cont:,.0f} (+53.4%)\n'
         f'Momentum: ${final_mom:,.0f} (+35.8%)\n'
         f'Confirmation: ${final_conf:,.0f} (-34.8%)',
         transform=ax1.transAxes,
         fontsize=10,
         verticalalignment='top',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# Plot 2: Drawdown Comparison
ax2 = axes[1]

# Calculate drawdowns
confirmation['drawdown'] = (confirmation['portfolio_value'] / confirmation['portfolio_value'].cummax() - 1) * 100
momentum['drawdown'] = (momentum['portfolio_value'] / momentum['portfolio_value'].cummax() - 1) * 100
contrarian['drawdown'] = (contrarian['portfolio_value'] / contrarian['portfolio_value'].cummax() - 1) * 100

ax2.fill_between(confirmation['date'], confirmation['drawdown'], 0, 
                  alpha=0.3, label='Confirmation Premium')
ax2.fill_between(momentum['date'], momentum['drawdown'], 0, 
                  alpha=0.3, label='Volume Momentum')
ax2.fill_between(contrarian['date'], contrarian['drawdown'], 0, 
                  alpha=0.5, color='green', label='Contrarian Divergence')

ax2.set_title('Drawdown Comparison', fontsize=14, fontweight='bold')
ax2.set_xlabel('Date', fontsize=12)
ax2.set_ylabel('Drawdown (%)', fontsize=12)
ax2.legend(fontsize=10, loc='lower right')
ax2.grid(True, alpha=0.3)

# Add max drawdown annotations
max_dd_conf = confirmation['drawdown'].min()
max_dd_mom = momentum['drawdown'].min()
max_dd_cont = contrarian['drawdown'].min()

ax2.text(0.02, 0.02,
         f'Max Drawdowns:\n'
         f'Contrarian: {max_dd_cont:.1f}%\n'
         f'Momentum: {max_dd_mom:.1f}%\n'
         f'Confirmation: {max_dd_conf:.1f}%',
         transform=ax2.transAxes,
         fontsize=10,
         verticalalignment='bottom',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()

# Save plot
output_file = os.path.join(results_dir, 'volume_divergence_strategy_comparison.png')
plt.savefig(output_file, dpi=300, bbox_inches='tight')
print(f"Saved comparison plot to: {output_file}")

plt.close()

# Create summary statistics table
summary_data = {
    'Strategy': ['Contrarian Divergence', 'Volume Momentum', 'Confirmation Premium'],
    'Total Return (%)': [53.41, 35.79, -34.82],
    'Ann. Return (%)': [9.46, 6.68, -8.64],
    'Ann. Vol (%)': [54.87, 52.70, 55.03],
    'Sharpe Ratio': [0.172, 0.127, -0.157],
    'Max DD (%)': [-61.06, -62.83, -71.02],
    'Win Rate (%)': [50.43, 48.64, 49.51]
}

summary_df = pd.DataFrame(summary_data)
print("\n" + "="*80)
print("VOLUME DIVERGENCE FACTOR - STRATEGY COMPARISON")
print("="*80)
print(summary_df.to_string(index=False))
print("="*80)
print("\n🏆 BEST STRATEGY: Contrarian Divergence")
print("   - Fade weak moves, bet on reversals")
print("   - Long divergences, Short confirmations")
print("   - +53.41% total return, 9.46% annualized")
print("="*80)
