#!/usr/bin/env python3
"""
Combine Coinbase spot daily data with CoinMarketCap historical data
to get market cap and rank information for each coin/day.
"""

import pandas as pd
from datetime import datetime

# Read the most recent Coinbase spot daily data
print("Reading Coinbase spot daily data...")
coinbase_file = "coinbase_spot_daily_data_20200101_20251024_110130.csv"
coinbase_df = pd.read_csv(coinbase_file)

# Read CoinMarketCap historical data
print("Reading CoinMarketCap historical data...")
cmc_file = "coinmarketcap_historical_all_snapshots.csv"
cmc_df = pd.read_csv(cmc_file)

print(f"Coinbase data shape: {coinbase_df.shape}")
print(f"CoinMarketCap data shape: {cmc_df.shape}")

# Convert date formats to match
# Coinbase: YYYY-MM-DD
# CoinMarketCap: YYYYMMDD (snapshot_date)
print("\nConverting date formats...")
coinbase_df['date'] = pd.to_datetime(coinbase_df['date'])
cmc_df['snapshot_date'] = pd.to_datetime(cmc_df['snapshot_date'], format='%Y%m%d')

# Rename columns for clarity before merge
cmc_df = cmc_df.rename(columns={
    'Symbol': 'base',
    'snapshot_date': 'date',
    'Rank': 'cmc_rank',
    'Market Cap': 'market_cap',
    'Name': 'coin_name',
    'Price': 'cmc_price',
    'Circulating Supply': 'circulating_supply',
    'Volume (24h)': 'cmc_volume_24h',
    '% 1h': 'pct_1h',
    '% 24h': 'pct_24h',
    '% 7d': 'pct_7d'
})

# Select relevant columns from CoinMarketCap
cmc_columns = ['date', 'base', 'cmc_rank', 'market_cap', 'coin_name', 
               'cmc_price', 'circulating_supply', 'cmc_volume_24h',
               'pct_1h', 'pct_24h', 'pct_7d']
cmc_df_subset = cmc_df[cmc_columns]

print("\nMerging datasets...")
# Create a more complete join by using the most recent CMC data for each date
# Strategy: Merge exact matches first, then forward-fill within each coin

cmc_dates = sorted(cmc_df_subset['date'].unique())
print(f"CMC snapshot dates: {[d.strftime('%Y-%m-%d') for d in cmc_dates]}")

# Step 1: Do a left join to get exact matches
print("Step 1: Merging exact date matches...")
combined_df = coinbase_df.merge(
    cmc_df_subset,
    on=['date', 'base'],
    how='left'
)

# Step 2: For each coin, forward-fill the CMC data from snapshots
print("Step 2: Forward-filling CMC data from snapshots...")

# Get all unique coins
coins = combined_df['base'].unique()
print(f"Processing forward-fill for {len(coins)} coins...")

result_dfs = []
for coin in coins:
    coin_data = combined_df[combined_df['base'] == coin].sort_values('date')
    
    # For this coin, get CMC data at snapshot dates
    coin_cmc = cmc_df_subset[cmc_df_subset['base'] == coin].sort_values('date')
    
    if len(coin_cmc) > 0:
        # For each date, fill with the most recent prior snapshot
        for idx, row in coin_data.iterrows():
            if pd.isna(row['market_cap']):
                # Find the most recent CMC snapshot <= this date
                prior_snapshots = coin_cmc[coin_cmc['date'] <= row['date']]
                if len(prior_snapshots) > 0:
                    latest_snapshot = prior_snapshots.iloc[-1]
                    coin_data.loc[idx, 'cmc_rank'] = latest_snapshot['cmc_rank']
                    coin_data.loc[idx, 'market_cap'] = latest_snapshot['market_cap']
                    coin_data.loc[idx, 'coin_name'] = latest_snapshot['coin_name']
                    coin_data.loc[idx, 'cmc_price'] = latest_snapshot['cmc_price']
                    coin_data.loc[idx, 'circulating_supply'] = latest_snapshot['circulating_supply']
                    coin_data.loc[idx, 'cmc_volume_24h'] = latest_snapshot['cmc_volume_24h']
                    coin_data.loc[idx, 'pct_1h'] = latest_snapshot['pct_1h']
                    coin_data.loc[idx, 'pct_24h'] = latest_snapshot['pct_24h']
                    coin_data.loc[idx, 'pct_7d'] = latest_snapshot['pct_7d']
    
    result_dfs.append(coin_data)

combined_df = pd.concat(result_dfs, ignore_index=True).sort_values(['date', 'base']).reset_index(drop=True)

print(f"Combined data shape: {combined_df.shape}")
print(f"\nRows with market cap data: {combined_df['market_cap'].notna().sum()}")
print(f"Rows without market cap data: {combined_df['market_cap'].isna().sum()}")

# Show some statistics
print("\n" + "="*60)
print("COMBINED DATA SAMPLE:")
print("="*60)
print(combined_df.head(10).to_string())

print("\n" + "="*60)
print("DATA SUMMARY:")
print("="*60)
print(f"Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
print(f"Number of unique coins: {combined_df['base'].nunique()}")
print(f"Total records: {len(combined_df)}")
print(f"Records with CMC data: {combined_df['market_cap'].notna().sum()}")

# Show coins with and without CMC data
coins_with_cmc = combined_df[combined_df['market_cap'].notna()]['base'].unique()
coins_without_cmc = combined_df[combined_df['market_cap'].isna()]['base'].unique()
print(f"\nCoins with CMC data: {len(coins_with_cmc)}")
print(f"Coins without CMC data: {len(coins_without_cmc)}")

if len(coins_without_cmc) > 0:
    print(f"\nSample of coins without CMC data: {sorted(coins_without_cmc)[:10]}")

# Save combined data
output_file = "combined_coinbase_coinmarketcap_daily.csv"
print(f"\nSaving combined data to {output_file}...")
combined_df.to_csv(output_file, index=False)

print(f"\n✓ Successfully saved combined data to {output_file}")
print("\nColumns in output file:")
for i, col in enumerate(combined_df.columns, 1):
    print(f"  {i}. {col}")
