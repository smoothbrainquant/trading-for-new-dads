#!/usr/bin/env python3
"""
Visualize Turnover Factor Construction Comparison
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load results
equity = pd.read_csv('backtests/results/turnover_construction_equity_curves.csv')
equity['date'] = pd.to_datetime(equity['date'])

comparison = pd.read_csv('backtests/results/turnover_construction_comparison.csv')

# Create visualization
fig, axes = plt.subplots(2, 2, figsize=(16, 10))
fig.suptitle('Turnover Factor: Top/Bottom 10 vs Deciles Comparison', fontsize=16, fontweight='bold')

# Plot 1: Equity Curves
ax = axes[0, 0]
for method in equity['method'].unique():
    method_data = equity[equity['method'] == method]
    ax.plot(method_data['date'], method_data['portfolio_value'], 
            label=method, linewidth=2, alpha=0.8)

ax.set_xlabel('Date', fontsize=11)
ax.set_ylabel('Portfolio Value ($)', fontsize=11)
ax.set_title('Equity Curves Comparison', fontsize=12, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
ax.axhline(y=10000, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='Initial Capital')

# Plot 2: Drawdown
ax = axes[0, 1]
for method in equity['method'].unique():
    method_data = equity[equity['method'] == method].copy()
    method_data['cum_max'] = method_data['portfolio_value'].cummax()
    method_data['drawdown'] = (method_data['portfolio_value'] - method_data['cum_max']) / method_data['cum_max']
    ax.plot(method_data['date'], method_data['drawdown'] * 100, 
            label=method, linewidth=2, alpha=0.8)

ax.set_xlabel('Date', fontsize=11)
ax.set_ylabel('Drawdown (%)', fontsize=11)
ax.set_title('Drawdown Over Time', fontsize=12, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
ax.axhline(y=0, color='black', linestyle='-', linewidth=1)

# Plot 3: Performance Metrics Comparison
ax = axes[1, 0]
metrics = ['annualized_return', 'sharpe_ratio', 'max_drawdown', 'win_rate']
metric_labels = ['Ann. Return', 'Sharpe', 'Max DD', 'Win Rate']
x_pos = np.arange(len(metrics))
width = 0.35

method1_vals = [
    comparison.iloc[0]['annualized_return'] * 100,
    comparison.iloc[0]['sharpe_ratio'],
    comparison.iloc[0]['max_drawdown'] * 100,
    comparison.iloc[0]['win_rate'] * 100,
]
method2_vals = [
    comparison.iloc[1]['annualized_return'] * 100,
    comparison.iloc[1]['sharpe_ratio'],
    comparison.iloc[1]['max_drawdown'] * 100,
    comparison.iloc[1]['win_rate'] * 100,
]

bars1 = ax.bar(x_pos - width/2, method1_vals, width, label='Top/Bottom 10', alpha=0.8)
bars2 = ax.bar(x_pos + width/2, method2_vals, width, label='Top/Bottom Deciles', alpha=0.8)

ax.set_xlabel('Metric', fontsize=11)
ax.set_ylabel('Value', fontsize=11)
ax.set_title('Performance Metrics Comparison', fontsize=12, fontweight='bold')
ax.set_xticks(x_pos)
ax.set_xticklabels(metric_labels, fontsize=10)
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3, axis='y')
ax.axhline(y=0, color='black', linestyle='-', linewidth=1)

# Add value labels on bars
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}',
                ha='center', va='bottom' if height > 0 else 'top',
                fontsize=8)

# Plot 4: Rolling Returns Comparison
ax = axes[1, 1]
window = 90  # 90-day rolling window

for method in equity['method'].unique():
    method_data = equity[equity['method'] == method].copy()
    method_data = method_data.sort_values('date')
    method_data['returns'] = method_data['portfolio_value'].pct_change()
    method_data['rolling_return'] = method_data['returns'].rolling(window).sum() * 100
    ax.plot(method_data['date'], method_data['rolling_return'], 
            label=f'{method} (90d)', linewidth=2, alpha=0.8)

ax.set_xlabel('Date', fontsize=11)
ax.set_ylabel('Rolling Return (%)', fontsize=11)
ax.set_title('90-Day Rolling Returns', fontsize=12, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
ax.axhline(y=0, color='black', linestyle='-', linewidth=1)

plt.tight_layout()
plt.savefig('backtests/results/turnover_construction_comparison.png', dpi=300, bbox_inches='tight')
print("\n✓ Visualization saved to: backtests/results/turnover_construction_comparison.png")

# Print summary table
print("\n" + "=" * 80)
print("SUMMARY TABLE")
print("=" * 80)
print("\nKey Findings:")
print(f"  • Top/Bottom 10 achieves Sharpe {comparison.iloc[0]['sharpe_ratio']:.3f}")
print(f"  • Top/Bottom Deciles achieves Sharpe {comparison.iloc[1]['sharpe_ratio']:.3f}")
print(f"  • Performance difference: {(comparison.iloc[0]['sharpe_ratio'] - comparison.iloc[1]['sharpe_ratio']):.3f} Sharpe")
print(f"\n  • Top/Bottom 10 final value: ${comparison.iloc[0]['final_value']:,.2f}")
print(f"  • Top/Bottom Deciles final value: ${comparison.iloc[1]['final_value']:,.2f}")
print(f"  • Difference: ${comparison.iloc[0]['final_value'] - comparison.iloc[1]['final_value']:,.2f}")
print(f"\n  • Top/Bottom 10 max drawdown: {comparison.iloc[0]['max_drawdown']*100:.2f}%")
print(f"  • Top/Bottom Deciles max drawdown: {comparison.iloc[1]['max_drawdown']*100:.2f}%")
print("\n" + "=" * 80)

print("\n📊 Visualization complete!")
