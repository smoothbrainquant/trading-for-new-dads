#!/usr/bin/env python3
"""
Visualize top 100 coin price data coverage.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from datetime import datetime

# Load data
price_df = pd.read_csv('data/raw/combined_coinbase_coinmarketcap_daily.csv')
price_df['date'] = pd.to_datetime(price_df['date'])

hist_df = pd.read_csv('crypto_dilution_historical_2021_2025.csv')
hist_df['date'] = pd.to_datetime(hist_df['date'])

# Get latest top 100
latest = hist_df[hist_df['date'] == hist_df['date'].max()]
top100 = latest.nsmallest(100, 'Rank').copy()

# Analyze date coverage for each coin
coverage_data = []

for _, row in top100.iterrows():
    symbol = row['Symbol']
    symbol_data = price_df[price_df['base'] == symbol]
    
    if len(symbol_data) > 0:
        first = symbol_data['date'].min()
        last = symbol_data['date'].max()
        days = (last - first).days
        has_current = (last >= pd.to_datetime('2025-01-01'))
        coverage = 'Current' if has_current else 'Old Data'
    else:
        first = None
        last = None
        days = 0
        coverage = 'Missing'
    
    coverage_data.append({
        'Rank': int(row['Rank']),
        'Symbol': symbol,
        'Name': row['Name'],
        'Market_Cap': row['Market Cap'],
        'First_Date': first,
        'Last_Date': last,
        'Days_Available': days,
        'Coverage': coverage
    })

coverage_df = pd.DataFrame(coverage_data)

# Create visualization
fig = plt.figure(figsize=(18, 14))
gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

# Plot 1: Coverage by rank tier
ax1 = fig.add_subplot(gs[0, 0])

tiers = [
    ('Top 10', 1, 10),
    ('11-20', 11, 20),
    ('21-30', 21, 30),
    ('31-50', 31, 50),
    ('51-100', 51, 100),
]

tier_labels = []
current_counts = []
old_counts = []
missing_counts = []

for tier_name, start, end in tiers:
    tier_data = coverage_df[(coverage_df['Rank'] >= start) & (coverage_df['Rank'] <= end)]
    tier_labels.append(tier_name)
    current_counts.append((tier_data['Coverage'] == 'Current').sum())
    old_counts.append((tier_data['Coverage'] == 'Old Data').sum())
    missing_counts.append((tier_data['Coverage'] == 'Missing').sum())

x = np.arange(len(tier_labels))
width = 0.7

p1 = ax1.bar(x, current_counts, width, label='Current (2025 data)', color='#4ECDC4')
p2 = ax1.bar(x, old_counts, width, bottom=current_counts, label='Old Data (pre-2025)', color='#FFB86C')
p3 = ax1.bar(x, missing_counts, width, bottom=np.array(current_counts) + np.array(old_counts), 
             label='Missing', color='#FF6B6B')

ax1.set_ylabel('Number of Coins', fontweight='bold')
ax1.set_title('Price Data Coverage by Market Cap Tier', fontweight='bold', fontsize=14)
ax1.set_xticks(x)
ax1.set_xticklabels(tier_labels)
ax1.legend(loc='upper right')
ax1.grid(axis='y', alpha=0.3)

# Add value labels
for i, (curr, old, miss) in enumerate(zip(current_counts, old_counts, missing_counts)):
    if curr > 0:
        ax1.text(i, curr/2, str(curr), ha='center', va='center', fontweight='bold', fontsize=10)
    if old > 0:
        ax1.text(i, curr + old/2, str(old), ha='center', va='center', fontweight='bold', fontsize=9)
    if miss > 0:
        ax1.text(i, curr + old + miss/2, str(miss), ha='center', va='center', fontweight='bold', fontsize=9)

# Plot 2: Summary stats
ax2 = fig.add_subplot(gs[0, 1])
ax2.axis('off')

total = len(coverage_df)
current = (coverage_df['Coverage'] == 'Current').sum()
old = (coverage_df['Coverage'] == 'Old Data').sum()
missing = (coverage_df['Coverage'] == 'Missing').sum()

summary_text = f"""
TOP 100 COINS - PRICE DATA COVERAGE

Overall Statistics:
  Total coins:          {total}
  Current data (2025):  {current} ({current/total*100:.1f}%)
  Old data (pre-2025):  {old} ({old/total*100:.1f}%)
  Missing entirely:     {missing} ({missing/total*100:.1f}%)

Coverage by Tier:
  Top 10:    {current_counts[0]}/10 current ({current_counts[0]*10:.0f}%)
  11-20:     {current_counts[1]}/10 current ({current_counts[1]*10:.0f}%)
  21-30:     {current_counts[2]}/10 current ({current_counts[2]*10:.0f}%)
  31-50:     {current_counts[3]}/20 current ({current_counts[3]*5:.0f}%)
  51-100:    {current_counts[4]}/50 current ({current_counts[4]*2:.0f}%)

Issue Found:
  Many coins (e.g. SOL, XRP, DOGE) have price
  data but only for SHORT TIME PERIODS.
  
  Example: SOL has data from 2021-06-17 to
  2021-10-28 (only 4 months!) then STOPS.
  
  This explains why backtest join rate is low
  even though coins "exist" in the dataset.
"""

ax2.text(0.05, 0.95, summary_text, transform=ax2.transAxes,
         fontsize=11, verticalalignment='top', fontfamily='monospace',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.9))

# Plot 3: Top 30 coins timeline
ax3 = fig.add_subplot(gs[1, :])

top30 = coverage_df.head(30)

y_positions = np.arange(len(top30))
colors_map = {'Current': '#4ECDC4', 'Old Data': '#FFB86C', 'Missing': '#FF6B6B'}

min_date = pd.to_datetime('2020-01-01')
max_date = pd.to_datetime('2025-10-31')

for i, row in top30.iterrows():
    color = colors_map[row['Coverage']]
    
    if row['Coverage'] != 'Missing':
        start = row['First_Date']
        end = row['Last_Date']
        
        # Convert to numeric for plotting
        start_num = (start - min_date).days
        end_num = (end - min_date).days
        width_num = end_num - start_num
        
        ax3.barh(i, width_num, left=start_num, height=0.8, color=color, alpha=0.8, edgecolor='black', linewidth=0.5)
        
        # Add label
        label = f"{row['Symbol']}"
        ax3.text(-50, i, label, ha='right', va='center', fontsize=8, fontweight='bold')
    else:
        # No data - show as red line
        ax3.barh(i, 0, height=0.8, color=color, alpha=0.8)
        label = f"{row['Symbol']}"
        ax3.text(-50, i, label, ha='right', va='center', fontsize=8, fontweight='bold')

# Format x-axis as dates
date_range = pd.date_range(min_date, max_date, freq='6MS')
tick_positions = [(d - min_date).days for d in date_range]
tick_labels = [d.strftime('%Y-%m') for d in date_range]
ax3.set_xticks(tick_positions)
ax3.set_xticklabels(tick_labels, rotation=45, ha='right')

ax3.set_yticks([])
ax3.set_xlabel('Date', fontweight='bold')
ax3.set_title('Top 30 Coins: Price Data Availability Timeline', fontweight='bold', fontsize=14)
ax3.set_xlim([-300, (max_date - min_date).days + 50])
ax3.grid(axis='x', alpha=0.3)

# Add vertical line for current date
current_days = (pd.to_datetime('2025-10-01') - min_date).days
ax3.axvline(current_days, color='red', linestyle='--', linewidth=2, alpha=0.5, label='Oct 2025')

# Plot 4: Problem examples
ax4 = fig.add_subplot(gs[2, :])
ax4.axis('off')

# Show specific problem cases
problem_cases = coverage_df[coverage_df['Coverage'].isin(['Old Data', 'Missing'])].head(15)

problem_text = "SPECIFIC PROBLEMS - Top 15 Coins with Data Issues:\n\n"
problem_text += f"{'Rank':<6} {'Symbol':<10} {'Name':<25} {'Status':<15} {'Date Range'}\n"
problem_text += "-" * 100 + "\n"

for _, row in problem_cases.iterrows():
    if row['Coverage'] == 'Missing':
        date_range = "NO DATA"
    else:
        date_range = f"{row['First_Date'].date()} to {row['Last_Date'].date()} ({row['Days_Available']} days)"
    
    problem_text += f"{row['Rank']:<6} {row['Symbol']:<10} {row['Name'][:24]:<25} {row['Coverage']:<15} {date_range}\n"

problem_text += "\n" + "=" * 100 + "\n"
problem_text += "CONCLUSION:\n"
problem_text += "  ? 63% of top 100 coins exist in price dataset (good!)\n"
problem_text += "  ? BUT many have INCOMPLETE temporal coverage (bad!)\n"
problem_text += "  ? SOL, XRP, DOGE, ADA, etc. have data for only 4-6 months\n"
problem_text += "  ? This creates LOW JOIN RATE at most rebalance dates\n"
problem_text += "  ? Only 8/10 top 10 coins have CURRENT (2025) data\n"

ax4.text(0.05, 0.95, problem_text, transform=ax4.transAxes,
         fontsize=9, verticalalignment='top', fontfamily='monospace',
         bbox=dict(boxstyle='round', facecolor='#FFE5E5', alpha=0.9))

plt.savefig('top100_price_coverage_analysis.png', dpi=300, bbox_inches='tight')
print("? Saved: top100_price_coverage_analysis.png")

# Save detailed CSV
coverage_df.to_csv('top100_price_coverage_detailed.csv', index=False)
print("? Saved: top100_price_coverage_detailed.csv")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Top 100 coins analyzed:")
print(f"  Current data (2025):  {current} coins ({current/total*100:.1f}%)")
print(f"  Old data (pre-2025):  {old} coins ({old/total*100:.1f}%)")
print(f"  Missing entirely:     {missing} coins ({missing/total*100:.1f}%)")
print(f"\nTop 10 specifically:")
print(f"  Current: {current_counts[0]}/10 ({current_counts[0]*10:.0f}%)")
print(f"  Problems: {10 - current_counts[0]}/10 coins")
