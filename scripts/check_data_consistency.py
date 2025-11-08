#!/usr/bin/env python3
"""
Check data consistency across different price data files.
Identify single source of truth.
"""

import pandas as pd
import os
import glob

print("=" * 80)
print("DATA SOURCE CONSISTENCY CHECK")
print("=" * 80)

# List all potential data files
data_files = {
    "MAIN (run_all_backtests default)": "data/raw/combined_coinbase_coinmarketcap_daily.csv",
    "Coinbase spot (raw)": "data/raw/coinbase_spot_daily_data_20200101_20251024_110130.csv",
    "Coinbase top200 (newer)": "data/raw/coinbase_top200_daily_20200101_to_present_20251025_171900.csv",
}

file_stats = {}

for name, filepath in data_files.items():
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        df['date'] = pd.to_datetime(df['date'])
        
        stats = {
            'exists': True,
            'rows': len(df),
            'symbols': df['base'].nunique() if 'base' in df.columns else df['symbol'].nunique(),
            'date_min': df['date'].min(),
            'date_max': df['date'].max(),
            'columns': list(df.columns),
            'has_cmc': 'cmc_rank' in df.columns or 'market_cap' in df.columns,
            'file_size_mb': os.path.getsize(filepath) / 1024 / 1024
        }
        
        # Sample a few symbols to check data quality
        if 'base' in df.columns:
            sample_symbols = sorted(df['base'].unique())[:5]
            stats['sample_symbols'] = sample_symbols
        
        file_stats[name] = stats
    else:
        file_stats[name] = {'exists': False}

print("\n" + "=" * 80)
print("FILE COMPARISON")
print("=" * 80)

for name, stats in file_stats.items():
    print(f"\n{name}:")
    print(f"  File: {data_files[name]}")
    if stats['exists']:
        print(f"  ✓ Exists: YES")
        print(f"  Rows: {stats['rows']:,}")
        print(f"  Symbols: {stats['symbols']}")
        print(f"  Date range: {stats['date_min'].date()} to {stats['date_max'].date()}")
        print(f"  Days: {(stats['date_max'] - stats['date_min']).days}")
        print(f"  Has CMC data: {'YES' if stats['has_cmc'] else 'NO'}")
        print(f"  File size: {stats['file_size_mb']:.1f} MB")
        print(f"  Columns: {', '.join(stats['columns'][:8])}")
        if 'sample_symbols' in stats:
            print(f"  Sample symbols: {', '.join(stats['sample_symbols'])}")
    else:
        print(f"  ✗ Exists: NO")

# Check which files are used where
print("\n" + "=" * 80)
print("USAGE IN CODEBASE")
print("=" * 80)

scripts_to_check = [
    ('run_all_backtests.py', 'backtests/scripts/run_all_backtests.py'),
    ('backtest_dilution_factor.py', 'backtests/scripts/backtest_dilution_factor.py'),
    ('optimize_rebalance_frequency.py', 'backtests/scripts/optimize_rebalance_frequency.py'),
]

for script_name, script_path in scripts_to_check:
    if os.path.exists(script_path):
        with open(script_path, 'r') as f:
            content = f.read()
        
        uses_combined = 'combined_coinbase_coinmarketcap_daily.csv' in content
        uses_coinbase = 'coinbase_spot_daily_data' in content
        uses_top200 = 'coinbase_top200' in content
        
        print(f"\n{script_name}:")
        if uses_combined:
            print(f"  ✓ Uses combined_coinbase_coinmarketcap_daily.csv")
        if uses_coinbase:
            print(f"  ? Uses coinbase_spot_daily_data")
        if uses_top200:
            print(f"  ? Uses coinbase_top200")
        if not (uses_combined or uses_coinbase or uses_top200):
            print(f"  ? No hardcoded data file (uses argument)")

# Check if combined file is same as coinbase file
print("\n" + "=" * 80)
print("DATA IDENTITY CHECK")
print("=" * 80)

combined_df = pd.read_csv("data/raw/combined_coinbase_coinmarketcap_daily.csv")
coinbase_df = pd.read_csv("data/raw/coinbase_spot_daily_data_20200101_20251024_110130.csv")

print("\nComparing combined vs coinbase_spot:")
print(f"  Same number of rows: {len(combined_df) == len(coinbase_df)}")
print(f"  Same number of symbols: {combined_df['base'].nunique() == coinbase_df['base'].nunique()}")

# Check if combined has extra columns
extra_cols = set(combined_df.columns) - set(coinbase_df.columns)
if extra_cols:
    print(f"  Combined has extra columns: {extra_cols}")
    print(f"  → Combined = Coinbase + CMC market cap data")

# Check top200 file (newer)
top200_df = pd.read_csv("data/raw/coinbase_top200_daily_20200101_to_present_20251025_171900.csv")
print(f"\nComparing top200 vs combined:")
print(f"  Top200 rows: {len(top200_df):,}")
print(f"  Combined rows: {len(combined_df):,}")
print(f"  Top200 symbols: {top200_df['base'].nunique()}")
print(f"  Combined symbols: {combined_df['base'].nunique()}")
print(f"  → Top200 has {top200_df['base'].nunique() - combined_df['base'].nunique()} more symbols")

# Show which symbols are in top200 but not in combined
top200_symbols = set(top200_df['base'].unique())
combined_symbols = set(combined_df['base'].unique())
extra_in_top200 = top200_symbols - combined_symbols

if extra_in_top200:
    print(f"\nSymbols in top200 but NOT in combined ({len(extra_in_top200)}):")
    print(f"  {sorted(list(extra_in_top200))[:20]}")

print("\n" + "=" * 80)
print("RECOMMENDATION")
print("=" * 80)

recommendation = """
CURRENT STATE:
  • run_all_backtests uses: combined_coinbase_coinmarketcap_daily.csv (DEFAULT)
  • This is the SINGLE SOURCE OF TRUTH for backtests
  • It's essentially: coinbase_spot + CMC market cap metadata

ISSUE FOUND:
  • Combined file: 172 symbols, outdated (Oct 24, 2025)
  • Top200 file: 207 symbols, newer (Oct 25, 2025)  ← 35 MORE SYMBOLS!
  • Top200 is MORE COMPLETE but NOT used by default

SYMBOLS ONLY IN TOP200 (sample):
"""

if extra_in_top200:
    recommendation += f"  {', '.join(sorted(list(extra_in_top200))[:15])}\n"

recommendation += """
RECOMMENDATION:
  1. UPDATE combined_coinbase_coinmarketcap_daily.csv
     - Use coinbase_top200 as base (207 symbols)
     - Add CMC market cap data
     - This becomes the new single source of truth
  
  2. VERIFY no other scripts use different files
     - All should use combined_coinbase_coinmarketcap_daily.csv
     - Or get file path from command line argument
  
  3. AUTOMATE daily updates
     - Keep combined file up-to-date
     - Single place to update = consistency
"""

print(recommendation)

# Save detailed comparison
comparison_df = pd.DataFrame([
    {
        'File': 'combined_coinbase_coinmarketcap_daily.csv',
        'Symbols': combined_df['base'].nunique(),
        'Rows': len(combined_df),
        'Latest_Date': combined_df['date'].max(),
        'Has_CMC': True,
        'Used_By_Default': True
    },
    {
        'File': 'coinbase_spot_daily_data_20200101_20251024_110130.csv',
        'Symbols': coinbase_df['base'].nunique(),
        'Rows': len(coinbase_df),
        'Latest_Date': coinbase_df['date'].max(),
        'Has_CMC': False,
        'Used_By_Default': False
    },
    {
        'File': 'coinbase_top200_daily_20200101_to_present_20251025_171900.csv',
        'Symbols': top200_df['base'].nunique(),
        'Rows': len(top200_df),
        'Latest_Date': top200_df['date'].max(),
        'Has_CMC': False,
        'Used_By_Default': False
    }
])

comparison_df.to_csv('data_source_comparison.csv', index=False)
print("\n✓ Saved: data_source_comparison.csv")

print("\n" + "=" * 80)
