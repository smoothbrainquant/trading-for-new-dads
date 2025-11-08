#!/usr/bin/env python3
"""
Analyze coverage of top 100 coins by market cap.
Check which coins we have price data for.
"""

import pandas as pd
import numpy as np

# Load latest dilution data to get market cap rankings
hist_df = pd.read_csv('crypto_dilution_historical_2021_2025.csv')
hist_df['date'] = pd.to_datetime(hist_df['date'])

# Get most recent snapshot
latest_date = hist_df['date'].max()
latest_snapshot = hist_df[hist_df['date'] == latest_date].copy()

# Sort by rank (1 = highest market cap)
latest_snapshot = latest_snapshot.sort_values('Rank')

# Get top 100
top100 = latest_snapshot.head(100).copy()

print("=" * 80)
print(f"TOP 100 COINS BY MARKET CAP (as of {latest_date.date()})")
print("=" * 80)

# Load price data
price_df = pd.read_csv('data/raw/combined_coinbase_coinmarketcap_daily.csv')
price_symbols = set(price_df['base'].unique())

print(f"\nPrice data coverage: {len(price_symbols)} symbols")

# Check coverage
top100['has_price_data'] = top100['Symbol'].isin(price_symbols)

# Summary stats
n_with_price = top100['has_price_data'].sum()
n_without_price = (~top100['has_price_data']).sum()

print(f"\nTop 100 Coverage:")
print(f"  With price data:    {n_with_price} ({n_with_price/100*100:.1f}%)")
print(f"  Without price data: {n_without_price} ({n_without_price/100*100:.1f}%)")

# Show top 20
print("\n" + "=" * 80)
print("TOP 20 COINS")
print("=" * 80)
print(f"{'Rank':<6} {'Symbol':<10} {'Name':<25} {'Market Cap':<15} {'Price Data'}")
print("-" * 80)

for _, row in top100.head(20).iterrows():
    status = "? YES" if row['has_price_data'] else "? NO"
    market_cap_str = f"${row['Market Cap']/1e9:.2f}B"
    print(f"{int(row['Rank']):<6} {row['Symbol']:<10} {row['Name'][:24]:<25} {market_cap_str:<15} {status}")

# Show missing coins in top 100
missing = top100[~top100['has_price_data']].copy()
if len(missing) > 0:
    print("\n" + "=" * 80)
    print(f"MISSING FROM PRICE DATA (Top 100): {len(missing)} coins")
    print("=" * 80)
    print(f"{'Rank':<6} {'Symbol':<10} {'Name':<30} {'Market Cap':<15}")
    print("-" * 80)
    
    for _, row in missing.head(30).iterrows():
        market_cap_str = f"${row['Market Cap']/1e9:.2f}B"
        print(f"{int(row['Rank']):<6} {row['Symbol']:<10} {row['Name'][:29]:<30} {market_cap_str:<15}")

# Breakdown by rank tiers
print("\n" + "=" * 80)
print("COVERAGE BY RANK TIER")
print("=" * 80)

tiers = [
    ("Top 10", 1, 10),
    ("11-20", 11, 20),
    ("21-30", 21, 30),
    ("31-50", 31, 50),
    ("51-100", 51, 100),
]

for tier_name, start, end in tiers:
    tier_data = top100[(top100['Rank'] >= start) & (top100['Rank'] <= end)]
    n_total = len(tier_data)
    n_with = tier_data['has_price_data'].sum()
    pct = n_with / n_total * 100 if n_total > 0 else 0
    print(f"{tier_name:<12} {n_with:>2}/{n_total:<2} ({pct:>5.1f}%)")

# Save detailed report
output_df = top100[['Rank', 'Symbol', 'Name', 'Market Cap', 'Price', 'has_price_data']].copy()
output_df['Market Cap ($B)'] = output_df['Market Cap'] / 1e9
output_df = output_df.drop('Market Cap', axis=1)
output_df['Price Data'] = output_df['has_price_data'].map({True: 'YES', False: 'NO'})
output_df = output_df.drop('has_price_data', axis=1)

output_df.to_csv('top100_price_data_coverage.csv', index=False)
print(f"\n? Saved detailed report to: top100_price_data_coverage.csv")

# Check what's in price data but NOT in top 100
price_only = price_symbols - set(top100['Symbol'])
print("\n" + "=" * 80)
print(f"COINS IN PRICE DATA BUT NOT TOP 100: {len(price_only)}")
print("=" * 80)
print(f"These are coins ranked >100 or not in dilution dataset")
print(f"Examples: {sorted(list(price_only))[:20]}")

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
