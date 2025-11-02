#!/usr/bin/env python3
"""
Investigate why join rate is low despite good coverage.
"""

import pandas as pd
import numpy as np

# Load data
hist_df = pd.read_csv('crypto_dilution_historical_2021_2025.csv')
hist_df['date'] = pd.to_datetime(hist_df['date'])

price_df = pd.read_csv('data/raw/combined_coinbase_coinmarketcap_daily.csv')
price_df['date'] = pd.to_datetime(price_df['date'])

print("=" * 80)
print("INVESTIGATING JOIN RATE DISCREPANCY")
print("=" * 80)

# Get price symbols
price_symbols = set(price_df['base'].unique())
print(f"\nPrice data symbols: {len(price_symbols)}")
print(f"Date range: {price_df['date'].min().date()} to {price_df['date'].max().date()}")

# Get dilution symbols
dilution_symbols = set(hist_df['Symbol'].unique())
print(f"\nDilution data symbols: {len(dilution_symbols)}")
print(f"Date range: {hist_df['date'].min().date()} to {hist_df['date'].max().date()}")

# Check example rebalance date
test_date = pd.to_datetime('2025-10-01')

print(f"\n" + "=" * 80)
print(f"EXAMPLE: {test_date.date()} Rebalance")
print("=" * 80)

# Get dilution signals for this date
date_signals = hist_df[hist_df['date'] == test_date].copy()
top150 = date_signals.nsmallest(150, 'Rank')

print(f"\nDilution signals (top 150): {len(top150)}")

# Check which have price data available AT THAT DATE
# This is the key - need to check if price data exists around that date
price_window = price_df[
    (price_df['date'] >= test_date - pd.Timedelta(days=100)) &
    (price_df['date'] <= test_date)
]
available_at_date = set(price_window['base'].unique())

print(f"Price symbols available around {test_date.date()}: {len(available_at_date)}")

# Check overlap
top150['has_price_overall'] = top150['Symbol'].isin(price_symbols)
top150['has_price_at_date'] = top150['Symbol'].isin(available_at_date)

n_overall = top150['has_price_overall'].sum()
n_at_date = top150['has_price_at_date'].sum()

print(f"\nTop 150 coins:")
print(f"  With price data (overall):  {n_overall} ({n_overall/150*100:.1f}%)")
print(f"  With price data (at date):  {n_at_date} ({n_at_date/150*100:.1f}%)")

# Show what's missing at date but available overall
missing_at_date = top150[top150['has_price_overall'] & ~top150['has_price_at_date']]

if len(missing_at_date) > 0:
    print(f"\n" + "-" * 80)
    print(f"Coins in price data but NOT available around {test_date.date()}: {len(missing_at_date)}")
    print("-" * 80)
    
    for _, row in missing_at_date.head(20).iterrows():
        symbol = row['Symbol']
        # Check when this symbol first appears in price data
        symbol_data = price_df[price_df['base'] == symbol]
        if len(symbol_data) > 0:
            first_date = symbol_data['date'].min()
            last_date = symbol_data['date'].max()
            print(f"  {symbol:<10} Rank {int(row['Rank']):<4} - Price data: {first_date.date()} to {last_date.date()}")

# Check the opposite - what's available at date but not in top 150
print("\n" + "=" * 80)
print("CHECKING ACTUAL JOIN IN BACKTEST")
print("=" * 80)

# Simulate the backtest join logic
sys.path.insert(0, 'backtests/scripts')
from optimize_rebalance_frequency import calculate_rolling_dilution_signal, calculate_volatility

signals_df = calculate_rolling_dilution_signal(hist_df, lookback_months=12)

# Get signals for test date
date_signals = signals_df[signals_df['date'] == test_date].copy()
date_signals = date_signals.nsmallest(150, 'rank')

print(f"\nRolling dilution signals for {test_date.date()}: {len(date_signals)}")

# Check which coins can actually be used (have sufficient price history for volatility)
valid_count = 0
invalid_count = 0
invalid_reasons = []

for symbol in date_signals['symbol'].head(30):  # Check first 30
    # Check if in price data
    if symbol not in price_symbols:
        invalid_count += 1
        invalid_reasons.append((symbol, "Not in price data"))
        continue
    
    # Check if has sufficient history for volatility calculation
    vol = calculate_volatility(price_df, symbol, test_date, lookback_days=90)
    if pd.isna(vol):
        invalid_count += 1
        invalid_reasons.append((symbol, "Insufficient price history"))
    else:
        valid_count += 1

print(f"\nFirst 30 signals:")
print(f"  Valid for trading:   {valid_count}")
print(f"  Invalid for trading: {invalid_count}")

if len(invalid_reasons) > 0:
    print(f"\nInvalid reasons:")
    for symbol, reason in invalid_reasons[:10]:
        print(f"  {symbol:<10} {reason}")

print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"""
Overall Coverage (Static):
  - Top 100 coins: 63% have price data (good!)
  - Top 150 coins: ~60% have price data (good!)

But Backtest Join Rate is Low Because:
  1. Temporal mismatch - coin not listed yet at that date
  2. Insufficient price history - need 90 days for volatility
  3. Data quality issues - missing dates/gaps

The 21.8% join rate is REAL for backtest purposes, even though
we have 63% of coins in the dataset overall.
""")

print("\n" + "=" * 80)

import sys
sys.exit(0)
