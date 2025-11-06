"""
Calculate Daily Market Cap from Price and Circulating Supply

This script calculates daily market cap as:
    daily_market_cap = daily_close_price × circulating_supply

Instead of using monthly snapshots, we:
1. Take circulating supply from monthly snapshots
2. Forward-fill circulating supply between snapshots
3. Calculate daily market cap using daily prices
"""

import pandas as pd
import numpy as np
import sys
import os

def calculate_daily_market_cap(price_data, marketcap_snapshots):
    """
    Calculate daily market cap from price and circulating supply.
    
    Args:
        price_data: DataFrame with columns ['date', 'symbol', 'close']
        marketcap_snapshots: DataFrame with columns ['date', 'Symbol', 'Circulating Supply']
    
    Returns:
        DataFrame with columns ['date', 'symbol', 'market_cap']
    """
    print("="*100)
    print("CALCULATING DAILY MARKET CAP")
    print("="*100)
    
    # Prepare price data
    price_df = price_data.copy()
    price_df['date'] = pd.to_datetime(price_df['date'])
    
    # Extract base symbol (remove trading pair)
    if 'base' not in price_df.columns:
        price_df['base'] = price_df['symbol'].apply(
            lambda x: x.split('/')[0] if '/' in str(x) else x
        )
    
    print(f"\n1. Price Data:")
    print(f"   Rows: {len(price_df):,}")
    print(f"   Symbols: {price_df['base'].nunique()}")
    print(f"   Date range: {price_df['date'].min().date()} to {price_df['date'].max().date()}")
    
    # Prepare market cap snapshots
    mcap_df = marketcap_snapshots.copy()
    
    # Handle snapshot_date column
    if 'snapshot_date' in mcap_df.columns:
        mcap_df['date'] = pd.to_datetime(mcap_df['snapshot_date'], format='%Y%m%d')
        mcap_df = mcap_df.drop(columns=['snapshot_date'])
    elif 'date' in mcap_df.columns:
        mcap_df['date'] = pd.to_datetime(mcap_df['date'])
    
    # Normalize column names
    if 'Symbol' in mcap_df.columns:
        mcap_df['symbol'] = mcap_df['Symbol']
    
    # Keep only necessary columns
    mcap_df = mcap_df[['date', 'symbol', 'Circulating Supply']].copy()
    mcap_df.columns = ['date', 'symbol', 'circulating_supply']
    
    print(f"\n2. Market Cap Snapshots:")
    print(f"   Rows: {len(mcap_df):,}")
    print(f"   Snapshots: {mcap_df['date'].nunique()}")
    print(f"   Symbols: {mcap_df['symbol'].nunique()}")
    print(f"   Date range: {mcap_df['date'].min().date()} to {mcap_df['date'].max().date()}")
    
    # Get all dates from price data
    all_dates = sorted(price_df['date'].unique())
    
    print(f"\n3. Expanding Circulating Supply to Daily Frequency:")
    print(f"   Target: {len(all_dates)} daily observations")
    
    # For each symbol, create daily circulating supply by forward-filling
    daily_supply_list = []
    
    symbols_with_supply = mcap_df['symbol'].unique()
    print(f"   Processing {len(symbols_with_supply)} symbols with supply data...")
    
    for i, symbol in enumerate(symbols_with_supply):
        if (i + 1) % 50 == 0:
            print(f"   Progress: {i+1}/{len(symbols_with_supply)} symbols processed")
        
        # Get supply snapshots for this symbol
        symbol_supply = mcap_df[mcap_df['symbol'] == symbol][['date', 'circulating_supply']].copy()
        symbol_supply = symbol_supply.sort_values('date')
        
        # Create daily index for this symbol
        daily_df = pd.DataFrame({'date': all_dates})
        
        # Merge and forward-fill
        daily_df = daily_df.merge(symbol_supply, on='date', how='left')
        daily_df['circulating_supply'] = daily_df['circulating_supply'].fillna(method='ffill')
        
        # Add symbol
        daily_df['symbol'] = symbol
        
        # Keep only rows with valid supply
        daily_df = daily_df.dropna(subset=['circulating_supply'])
        
        daily_supply_list.append(daily_df)
    
    # Combine all symbols
    daily_supply_df = pd.concat(daily_supply_list, ignore_index=True)
    
    print(f"   ✓ Created {len(daily_supply_df):,} daily supply observations")
    
    # Merge with price data to calculate market cap
    print(f"\n4. Merging Price and Supply:")
    
    # Merge on base symbol
    merged = price_df.merge(
        daily_supply_df[['date', 'symbol', 'circulating_supply']],
        left_on=['date', 'base'],
        right_on=['date', 'symbol'],
        how='left',
        suffixes=('', '_supply')
    )
    
    print(f"   Before merge: {len(price_df):,} rows")
    print(f"   After merge: {len(merged):,} rows")
    print(f"   Rows with supply: {merged['circulating_supply'].notna().sum():,}")
    
    # Calculate daily market cap
    print(f"\n5. Calculating Market Cap:")
    merged['market_cap'] = merged['close'] * merged['circulating_supply']
    
    # Remove rows without market cap
    valid_mcap = merged['market_cap'].notna()
    print(f"   Valid market cap rows: {valid_mcap.sum():,}")
    
    # Prepare output
    result = merged[valid_mcap][['date', 'symbol', 'market_cap']].copy()
    
    print(f"\n6. Final Daily Market Cap Data:")
    print(f"   Rows: {len(result):,}")
    print(f"   Symbols: {result['symbol'].nunique()}")
    print(f"   Date range: {result['date'].min().date()} to {result['date'].max().date()}")
    print(f"   Daily observations: {result['date'].nunique()}")
    
    # Summary statistics
    avg_symbols_per_day = result.groupby('date').size().mean()
    print(f"   Avg symbols per day: {avg_symbols_per_day:.0f}")
    
    print("\n" + "="*100)
    print("✓ DAILY MARKET CAP CALCULATION COMPLETE")
    print("="*100)
    
    return result


def main():
    """Test the daily market cap calculation."""
    # Load data
    print("\nLoading data...")
    price_file = "data/raw/combined_coinbase_coinmarketcap_daily.csv"
    mcap_file = "data/raw/coinmarketcap_monthly_all_snapshots.csv"
    
    price_df = pd.read_csv(price_file)
    mcap_df = pd.read_csv(mcap_file)
    
    # Calculate daily market cap
    daily_mcap = calculate_daily_market_cap(price_df, mcap_df)
    
    # Save to file
    output_file = "data/raw/daily_calculated_market_cap.csv"
    daily_mcap.to_csv(output_file, index=False)
    print(f"\n✓ Saved to: {output_file}")
    
    # Show sample
    print("\nSample (first 10 rows):")
    print(daily_mcap.head(10))
    
    print("\nSample (last 10 rows):")
    print(daily_mcap.tail(10))


if __name__ == "__main__":
    main()
