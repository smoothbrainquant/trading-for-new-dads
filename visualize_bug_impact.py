#!/usr/bin/env python3
"""
Visualize the impact of the portfolio construction bug.
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Plot 1: Data Coverage
ax1 = axes[0, 0]
categories = ['Dilution\nData', 'Price\nData', 'Common\n(Join)']
values = [565, 172, 170]
colors = ['#FF6B6B', '#4ECDC4', '#95E1D3']
bars = ax1.bar(categories, values, color=colors, edgecolor='black', linewidth=2)
ax1.set_ylabel('Number of Coins', fontsize=12, fontweight='bold')
ax1.set_title('Data Coverage: Only 30% Overlap', fontsize=14, fontweight='bold')
ax1.set_ylim([0, 600])

for bar, val in zip(bars, values):
    height = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2., height + 10,
             f'{val}', ha='center', va='bottom', fontsize=14, fontweight='bold')

# Add percentage label for common
ax1.text(2, 170 + 30, '30.1%\nof dilution', ha='center', va='bottom', 
         fontsize=10, style='italic', color='darkgreen')

# Plot 2: Portfolio Composition Bug
ax2 = axes[0, 1]

intended = [10, 10]  # 10 long, 10 short
buggy = [2.5, 2.5]   # 2-3 long, 2-3 short (avg)
fixed = [7, 7]       # 7 long, 7 short (avg)

x = np.arange(2)
width = 0.25

bars1 = ax2.bar(x - width, intended, width, label='Intended', color='#95E1D3', edgecolor='black')
bars2 = ax2.bar(x, buggy, width, label='Buggy Code', color='#FF6B6B', edgecolor='black')
bars3 = ax2.bar(x + width, fixed, width, label='Bug Fixed', color='#4ECDC4', edgecolor='black')

ax2.set_ylabel('Number of Positions', fontsize=12, fontweight='bold')
ax2.set_title('Portfolio Composition: Bug Causes Concentration', fontsize=14, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(['Long\nPositions', 'Short\nPositions'])
ax2.legend(fontsize=10)
ax2.set_ylim([0, 12])

# Add value labels
for bars in [bars1, bars2, bars3]:
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.2,
                f'{int(height)}', ha='center', va='bottom', fontsize=10, fontweight='bold')

# Plot 3: Performance Impact
ax3 = axes[1, 0]

versions = ['Original\nBug', 'Outlier\nFiltered\n(Bug)', 'My Analysis\nNo Clip\n(Bug)', 
            'My Analysis\n1-99% Clip\n(Bug)', 'Bug\nFixed\n(REAL)']
returns = [2641, 624, 1809, 387, -28]
colors_perf = ['#FF6B6B', '#FF8787', '#FFA07A', '#FFB6A3', '#4ECDC4']

bars = ax3.barh(versions, returns, color=colors_perf, edgecolor='black', linewidth=2)
ax3.set_xlabel('Total Return (%)', fontsize=12, fontweight='bold')
ax3.set_title('All Positive Returns are Artifacts of the Bug', fontsize=14, fontweight='bold')
ax3.axvline(x=0, color='black', linestyle='-', linewidth=1)
ax3.grid(axis='x', alpha=0.3)

# Add value labels
for bar, val in zip(bars, returns):
    if val > 0:
        x_pos = val + 100
        ha = 'left'
    else:
        x_pos = val - 10
        ha = 'right'
    ax3.text(x_pos, bar.get_y() + bar.get_height()/2., f'{val:+.0f}%',
             ha=ha, va='center', fontsize=11, fontweight='bold')

# Add annotations
ax3.text(1500, 4.5, '❌ Buggy\n(Concentrated)', ha='center', va='center',
         fontsize=10, bbox=dict(boxstyle='round', facecolor='#FFB6A3', alpha=0.7))
ax3.text(-100, 0.5, '✅ Real\n(Diversified)', ha='center', va='center',
         fontsize=10, bbox=dict(boxstyle='round', facecolor='#4ECDC4', alpha=0.7))

# Plot 4: Key Metrics Comparison
ax4 = axes[1, 1]
ax4.axis('off')

metrics_text = """
DILUTION FACTOR BACKTEST - SUMMARY

Data Joining Issue:
  • 565 coins in dilution data
  • 172 coins in price data  
  • 170 common (30.1% overlap)
  • Only 21.8% of top 150 coins available

Portfolio Bug Impact:
  • Intended: 20 positions (10 long + 10 short)
  • Buggy: 5 positions (accidental concentration)
  • Fixed: 14 positions (proper diversification)

Performance Impact:
  • Buggy code: +1,809% to +2,641% (FAKE)
  • Fixed code: -27.8% (REAL)
  • Difference: Portfolio construction bug
  
Clipping Analysis:
  • 1-99% clipping reduces returns (buggy code)
  • But analysis is INVALID (based on bug)
  • Need to rerun with fixed code

CONCLUSION:
✅ Data joining analysis is valid (21.8% coverage)
❌ Strategy loses money when properly implemented
❌ All positive backtests were artifacts of bug
⛔ DO NOT TRADE THIS STRATEGY
"""

ax4.text(0.05, 0.95, metrics_text, transform=ax4.transAxes,
         fontsize=11, verticalalignment='top', fontfamily='monospace',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

plt.tight_layout()
plt.savefig('/workspace/dilution_bug_impact_summary.png', dpi=300, bbox_inches='tight')
print("✓ Saved: dilution_bug_impact_summary.png")
plt.close()

print("\n" + "="*80)
print("VISUALIZATION COMPLETE")
print("="*80)
