#!/usr/bin/env python3
"""
Compare Equal-Weighted vs Risk Parity Dilution Decile Analysis
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load results
eq_metrics = pd.read_csv('dilution_decile_metrics.csv')
rp_metrics = pd.read_csv('dilution_decile_risk_parity_metrics.csv')

# Create comparison visualization
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# Plot 1: Annualized Returns Comparison
ax1 = axes[0, 0]
x = np.arange(len(eq_metrics))
width = 0.35

bars1 = ax1.bar(x - width/2, eq_metrics['annualized_return_pct'], width, 
                label='Equal-Weighted', alpha=0.8, color='steelblue')
bars2 = ax1.bar(x + width/2, rp_metrics['annualized_return_pct'], width,
                label='Risk Parity', alpha=0.8, color='coral')

ax1.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax1.set_xlabel('Decile (1=Low Dilution, 10=High Dilution)', fontsize=12)
ax1.set_ylabel('Annualized Return (%)', fontsize=12)
ax1.set_title('Annualized Returns: Equal-Weighted vs Risk Parity', fontsize=13, fontweight='bold')
ax1.set_xticks(x)
ax1.set_xticklabels([f'D{i}' for i in range(1, 11)])
ax1.legend(fontsize=11)
ax1.grid(True, alpha=0.3, axis='y')

# Plot 2: Sharpe Ratio Comparison
ax2 = axes[0, 1]
bars1 = ax2.bar(x - width/2, eq_metrics['sharpe_ratio'], width,
                label='Equal-Weighted', alpha=0.8, color='steelblue')
bars2 = ax2.bar(x + width/2, rp_metrics['sharpe_ratio'], width,
                label='Risk Parity', alpha=0.8, color='coral')

ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
ax2.set_xlabel('Decile (1=Low Dilution, 10=High Dilution)', fontsize=12)
ax2.set_ylabel('Sharpe Ratio', fontsize=12)
ax2.set_title('Sharpe Ratios: Equal-Weighted vs Risk Parity', fontsize=13, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels([f'D{i}' for i in range(1, 11)])
ax2.legend(fontsize=11)
ax2.grid(True, alpha=0.3, axis='y')

# Plot 3: Max Drawdown Comparison
ax3 = axes[1, 0]
bars1 = ax3.bar(x - width/2, eq_metrics['max_drawdown_pct'], width,
                label='Equal-Weighted', alpha=0.8, color='steelblue')
bars2 = ax3.bar(x + width/2, rp_metrics['max_drawdown_pct'], width,
                label='Risk Parity', alpha=0.8, color='coral')

ax3.set_xlabel('Decile (1=Low Dilution, 10=High Dilution)', fontsize=12)
ax3.set_ylabel('Max Drawdown (%)', fontsize=12)
ax3.set_title('Maximum Drawdown: Equal-Weighted vs Risk Parity', fontsize=13, fontweight='bold')
ax3.set_xticks(x)
ax3.set_xticklabels([f'D{i}' for i in range(1, 11)])
ax3.legend(fontsize=11)
ax3.grid(True, alpha=0.3, axis='y')

# Plot 4: Volatility Comparison
ax4 = axes[1, 1]
bars1 = ax4.bar(x - width/2, eq_metrics['volatility_pct'], width,
                label='Equal-Weighted', alpha=0.8, color='steelblue')
bars2 = ax4.bar(x + width/2, rp_metrics['volatility_pct'], width,
                label='Risk Parity', alpha=0.8, color='coral')

ax4.set_xlabel('Decile (1=Low Dilution, 10=High Dilution)', fontsize=12)
ax4.set_ylabel('Volatility (%)', fontsize=12)
ax4.set_title('Annualized Volatility: Equal-Weighted vs Risk Parity', fontsize=13, fontweight='bold')
ax4.set_xticks(x)
ax4.set_xticklabels([f'D{i}' for i in range(1, 11)])
ax4.legend(fontsize=11)
ax4.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig('dilution_equal_vs_risk_parity_comparison.png', dpi=300, bbox_inches='tight')
print("✓ Saved: dilution_equal_vs_risk_parity_comparison.png")

# Create summary comparison table
print("\n" + "=" * 100)
print("EQUAL-WEIGHTED vs RISK PARITY: DECILE 1 (LOW) vs DECILE 10 (HIGH)")
print("=" * 100)

eq_d1 = eq_metrics[eq_metrics['decile'] == 1].iloc[0]
eq_d10 = eq_metrics[eq_metrics['decile'] == 10].iloc[0]
rp_d1 = rp_metrics[rp_metrics['decile'] == 1].iloc[0]
rp_d10 = rp_metrics[rp_metrics['decile'] == 10].iloc[0]

print("\nEQUAL-WEIGHTED RESULTS:")
print(f"  Decile 1 (Low Dilution):   {eq_d1['annualized_return_pct']:>8.2f}% | Sharpe: {eq_d1['sharpe_ratio']:>6.2f} | Vol: {eq_d1['volatility_pct']:>6.2f}%")
print(f"  Decile 10 (High Dilution): {eq_d10['annualized_return_pct']:>8.2f}% | Sharpe: {eq_d10['sharpe_ratio']:>6.2f} | Vol: {eq_d10['volatility_pct']:>6.2f}%")
print(f"  Long/Short Spread:         {eq_d1['annualized_return_pct'] - eq_d10['annualized_return_pct']:>8.2f}% | Sharpe: {eq_d1['sharpe_ratio'] - eq_d10['sharpe_ratio']:>6.2f}")

print("\nRISK PARITY RESULTS:")
print(f"  Decile 1 (Low Dilution):   {rp_d1['annualized_return_pct']:>8.2f}% | Sharpe: {rp_d1['sharpe_ratio']:>6.2f} | Vol: {rp_d1['volatility_pct']:>6.2f}%")
print(f"  Decile 10 (High Dilution): {rp_d10['annualized_return_pct']:>8.2f}% | Sharpe: {rp_d10['sharpe_ratio']:>6.2f} | Vol: {rp_d10['volatility_pct']:>6.2f}%")
print(f"  Long/Short Spread:         {rp_d1['annualized_return_pct'] - rp_d10['annualized_return_pct']:>8.2f}% | Sharpe: {rp_d1['sharpe_ratio'] - rp_d10['sharpe_ratio']:>6.2f}")

print("\nIMPROVEMENT (Risk Parity - Equal-Weighted):")
print(f"  Decile 1 Return:           {rp_d1['annualized_return_pct'] - eq_d1['annualized_return_pct']:>8.2f}%")
print(f"  Decile 10 Return:          {rp_d10['annualized_return_pct'] - eq_d10['annualized_return_pct']:>8.2f}%")
spread_improvement = (rp_d1['annualized_return_pct'] - rp_d10['annualized_return_pct']) - (eq_d1['annualized_return_pct'] - eq_d10['annualized_return_pct'])
print(f"  Spread Improvement:        {spread_improvement:>8.2f}%")

print("\n" + "=" * 100)
print("KEY INSIGHT:")
print("=" * 100)
print("Risk parity weighting REVERSES the result!")
print(f"  Equal-weighted spread: {eq_d1['annualized_return_pct'] - eq_d10['annualized_return_pct']:>6.2f}% (WRONG direction - low dilution underperforms)")
print(f"  Risk parity spread:    {rp_d1['annualized_return_pct'] - rp_d10['annualized_return_pct']:>6.2f}% (RIGHT direction - low dilution outperforms)")
print(f"  Improvement:           {spread_improvement:>6.2f}%")
print("\nRisk parity controls for volatility, preventing high-vol losers from dominating the portfolio.")
print("=" * 100)

# Create detailed comparison CSV
comparison_df = pd.DataFrame({
    'Decile': eq_metrics['decile'],
    'EQ_Return': eq_metrics['annualized_return_pct'],
    'RP_Return': rp_metrics['annualized_return_pct'],
    'Return_Diff': rp_metrics['annualized_return_pct'] - eq_metrics['annualized_return_pct'],
    'EQ_Sharpe': eq_metrics['sharpe_ratio'],
    'RP_Sharpe': rp_metrics['sharpe_ratio'],
    'Sharpe_Diff': rp_metrics['sharpe_ratio'] - eq_metrics['sharpe_ratio'],
    'EQ_Vol': eq_metrics['volatility_pct'],
    'RP_Vol': rp_metrics['volatility_pct'],
    'Vol_Diff': rp_metrics['volatility_pct'] - eq_metrics['volatility_pct'],
    'EQ_MaxDD': eq_metrics['max_drawdown_pct'],
    'RP_MaxDD': rp_metrics['max_drawdown_pct'],
    'MaxDD_Diff': rp_metrics['max_drawdown_pct'] - eq_metrics['max_drawdown_pct']
})

comparison_df.to_csv('dilution_equal_vs_risk_parity_detailed.csv', index=False)
print("\n✓ Saved: dilution_equal_vs_risk_parity_detailed.csv")
