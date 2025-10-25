#!/usr/bin/env python3
"""
Download historical daily data from Coinbase for all symbols that have 
historically been ranked in the top 200 by market cap.

This script:
1. Reads historical market cap snapshots (both yearly and monthly)
2. Identifies all symbols that have EVER been ranked ≤200
3. Downloads daily OHLCV data from Coinbase for those symbols since 2020
"""

import ccxt
from datetime import datetime, timedelta
import pandas as pd
import time
from typing import List, Dict, Set
import os

def get_top200_symbols_from_snapshots() -> Set[str]:
    """
    Extract symbols that have ever been ranked in the top 200 from historical market cap snapshots.
    Combines data from both yearly snapshots and monthly snapshots for comprehensive coverage.
    
    Returns:
        Set of unique coin symbols that have ever been in top 200
    """
    print("="*80)
    print("EXTRACTING TOP 200 SYMBOLS FROM HISTORICAL DATA")
    print("="*80)
    
    top200_symbols = set()
    
    # Process historical snapshots (yearly)
    historical_file = 'data/raw/coinmarketcap_historical_all_snapshots.csv'
    if os.path.exists(historical_file):
        print(f"\nReading yearly snapshots from {historical_file}...")
        df_historical = pd.read_csv(historical_file)
        
        # Filter for rank <= 200
        df_top200 = df_historical[df_historical['Rank'] <= 200]
        symbols_historical = set(df_top200['Symbol'].unique())
        top200_symbols.update(symbols_historical)
        
        print(f"  Found {len(symbols_historical)} unique symbols in top 200 from yearly snapshots")
        print(f"  Date range: {df_historical['snapshot_date'].min()} to {df_historical['snapshot_date'].max()}")
        print(f"  Total snapshots: {df_historical['snapshot_date'].nunique()}")
    
    # Process monthly snapshots
    monthly_file = 'data/raw/coinmarketcap_monthly_all_snapshots.csv'
    if os.path.exists(monthly_file):
        print(f"\nReading monthly snapshots from {monthly_file}...")
        df_monthly = pd.read_csv(monthly_file)
        
        # Filter for rank <= 200
        df_top200 = df_monthly[df_monthly['Rank'] <= 200]
        symbols_monthly = set(df_top200['Symbol'].unique())
        
        # Add to overall set
        new_symbols = symbols_monthly - top200_symbols
        top200_symbols.update(symbols_monthly)
        
        print(f"  Found {len(symbols_monthly)} unique symbols in top 200 from monthly snapshots")
        print(f"  Added {len(new_symbols)} new symbols not in yearly data")
        print(f"  Date range: {df_monthly['snapshot_date'].min()} to {df_monthly['snapshot_date'].max()}")
        print(f"  Total snapshots: {df_monthly['snapshot_date'].nunique()}")
    
    print(f"\n{'='*80}")
    print(f"TOTAL UNIQUE SYMBOLS EVER IN TOP 200: {len(top200_symbols)}")
    print(f"{'='*80}")
    
    # Show some examples
    sorted_symbols = sorted(list(top200_symbols))
    print(f"\nSample symbols (first 30): {sorted_symbols[:30]}")
    if len(sorted_symbols) > 30:
        print(f"... and {len(sorted_symbols) - 30} more")
    
    return top200_symbols


def get_coinbase_spot_markets() -> Dict[str, str]:
    """
    Get all available spot markets on Coinbase.
    
    Returns:
        Dictionary mapping base currency to full symbol (e.g., {'BTC': 'BTC/USD'})
    """
    print("\n" + "="*80)
    print("FETCHING COINBASE MARKETS")
    print("="*80)
    print("\nConnecting to Coinbase...")
    
    exchange = ccxt.coinbase({
        'enableRateLimit': True,
    })
    
    try:
        # Load all markets
        markets = exchange.load_markets()
        print(f"  Loaded {len(markets)} total markets")
        
        # Filter for spot markets with USD or USDT quote
        spot_markets = {}
        spot_count = 0
        
        for symbol, market in markets.items():
            # Coinbase markets are spot by default, but check anyway
            is_spot = market.get('spot', False) or market.get('type') == 'spot'
            
            # Note: Many Coinbase markets have active=False in CCXT but still work
            # So we don't filter by active status
            if is_spot:
                spot_count += 1
                base = market.get('base')
                quote = market.get('quote')
                
                # Prefer USD, then USDT, then USDC
                if quote in ['USD', 'USDT', 'USDC']:
                    # If we already have this base, prefer USD over USDT over USDC
                    current_symbol = spot_markets.get(base, '')
                    if base not in spot_markets:
                        spot_markets[base] = symbol
                    elif quote == 'USD' and '/USD' not in current_symbol:
                        spot_markets[base] = symbol
                    elif quote == 'USDT' and '/USD' not in current_symbol and '/USDT' not in current_symbol:
                        spot_markets[base] = symbol
        
        print(f"  Found {spot_count} spot markets")
        print(f"✓ Mapped {len(spot_markets)} unique base currencies")
        
        return spot_markets
        
    except Exception as e:
        print(f"✗ Error fetching Coinbase markets: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}


def fetch_daily_data_for_symbol(exchange: ccxt.Exchange, symbol: str, start_date: datetime) -> pd.DataFrame:
    """
    Fetch all available daily OHLCV data for a single symbol since start_date.
    Fetches in chunks to handle Coinbase's data limits.
    
    Args:
        exchange: CCXT exchange instance
        symbol: Trading pair symbol (e.g., 'BTC/USD')
        start_date: Preferred start date
    
    Returns:
        DataFrame with OHLCV data
    """
    try:
        print(f"  Fetching data for {symbol}...", end=' ', flush=True)
        
        all_ohlcv = []
        now = datetime.now()
        
        # Fetch data in 300-day chunks
        chunk_days = 300
        
        # Try different start dates if preferred date doesn't work
        start_dates_to_try = [
            start_date,
            datetime(2021, 1, 1),
            datetime(2022, 1, 1),
            datetime(2023, 1, 1),
            datetime(2024, 1, 1),
        ]
        
        # Try to fetch data starting from each date
        for start_dt in start_dates_to_try:
            if start_dt >= now:
                continue
                
            current_date = start_dt
            temp_ohlcv = []
            
            while current_date < now:
                since = int(current_date.timestamp() * 1000)
                
                try:
                    ohlcv = exchange.fetch_ohlcv(
                        symbol=symbol,
                        timeframe='1d',
                        since=since,
                        limit=chunk_days
                    )
                    
                    if not ohlcv:
                        break
                    
                    temp_ohlcv.extend(ohlcv)
                    
                    # Get the last timestamp
                    last_timestamp = ohlcv[-1][0]
                    last_date = datetime.fromtimestamp(last_timestamp / 1000)
                    
                    # If we got less data than requested, we've reached the end
                    if len(ohlcv) < chunk_days:
                        break
                    
                    # Move forward
                    current_date = last_date + timedelta(days=1)
                    time.sleep(0.1)
                    
                except Exception as e:
                    if 'INVALID_ARGUMENT' in str(e) or 'UNAVAILABLE' in str(e):
                        # Try next start date
                        break
                    else:
                        break
            
            # If we got data, use it
            if temp_ohlcv:
                all_ohlcv = temp_ohlcv
                break
        
        # If still no data, try without any start date (fetch most recent)
        if not all_ohlcv:
            try:
                ohlcv = exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe='1d',
                    limit=1000  # Get last 1000 days
                )
                if ohlcv:
                    all_ohlcv = ohlcv
            except:
                pass
        
        if not all_ohlcv:
            print(f"✗ No data available")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(
            all_ohlcv,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        
        # Convert timestamp to date
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.date
        df['symbol'] = symbol
        
        # Get base currency from symbol
        base = symbol.split('/')[0]
        df['base'] = base
        
        # Select and reorder columns
        df = df[['date', 'symbol', 'base', 'open', 'high', 'low', 'close', 'volume']]
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['date', 'symbol'], keep='first')
        df = df.sort_values('date').reset_index(drop=True)
        
        print(f"✓ {len(df)} days (from {df['date'].min()} to {df['date'].max()})")
        
        return df
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return pd.DataFrame()


def download_top200_historical_data(start_date: str = '2020-01-01') -> pd.DataFrame:
    """
    Main function to download historical daily data from Coinbase for top 200 symbols.
    
    Args:
        start_date: Start date in 'YYYY-MM-DD' format
    
    Returns:
        DataFrame with all downloaded data
    """
    # Step 1: Get symbols that have ever been in top 200
    top200_symbols = get_top200_symbols_from_snapshots()
    
    # Step 2: Get available Coinbase spot markets
    coinbase_markets = get_coinbase_spot_markets()
    
    # Step 3: Match symbols
    print("\n" + "="*80)
    print("MATCHING SYMBOLS WITH COINBASE MARKETS")
    print("="*80)
    
    matched_symbols = []
    not_found = []
    
    for symbol in sorted(top200_symbols):
        if symbol in coinbase_markets:
            matched_symbols.append((symbol, coinbase_markets[symbol]))
        else:
            not_found.append(symbol)
    
    print(f"\n✓ Found {len(matched_symbols)} matching symbols on Coinbase")
    print(f"✗ Not found on Coinbase: {len(not_found)} symbols")
    
    # Show matched symbols
    print(f"\nMatched symbols (first 20):")
    for i, (base, full_symbol) in enumerate(matched_symbols[:20], 1):
        print(f"  {i:2d}. {base:8s} -> {full_symbol}")
    if len(matched_symbols) > 20:
        print(f"  ... and {len(matched_symbols) - 20} more")
    
    # Step 4: Download data for all matched symbols
    print(f"\n{'='*80}")
    print(f"DOWNLOADING DAILY DATA FROM {start_date} TO PRESENT")
    print(f"{'='*80}\n")
    
    exchange = ccxt.coinbase({
        'enableRateLimit': True,
    })
    
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    
    all_data = []
    successful = 0
    failed = 0
    
    for i, (base, full_symbol) in enumerate(matched_symbols, 1):
        print(f"[{i}/{len(matched_symbols)}]", end=' ')
        
        # Fetch all available data for this symbol
        df = fetch_daily_data_for_symbol(exchange, full_symbol, start_dt)
        
        if not df.empty:
            all_data.append(df)
            successful += 1
        else:
            failed += 1
        
        # Add delay between requests to respect rate limits
        if i < len(matched_symbols):
            time.sleep(exchange.rateLimit / 1000)
    
    # Step 5: Combine all data and save
    print(f"\n{'='*80}")
    print(f"DOWNLOAD SUMMARY")
    print(f"{'='*80}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(matched_symbols)}")
    print(f"{'='*80}\n")
    
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df = combined_df.sort_values(['date', 'symbol']).reset_index(drop=True)
        
        print(f"Combined data shape: {combined_df.shape}")
        print(f"Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
        print(f"Unique symbols: {combined_df['base'].nunique()}")
        
        # Save to CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f'data/raw/coinbase_top200_daily_{start_date.replace("-", "")}_to_present_{timestamp}.csv'
        
        combined_df.to_csv(output_filename, index=False)
        print(f"\n✓ Data saved to {output_filename}")
        
        # Print summary by symbol
        print(f"\n{'='*80}")
        print(f"DATA SUMMARY BY SYMBOL")
        print(f"{'='*80}\n")
        
        summary = combined_df.groupby('base').agg({
            'date': ['min', 'max', 'count']
        }).reset_index()
        summary.columns = ['Symbol', 'First Date', 'Last Date', 'Days']
        summary = summary.sort_values('Symbol')
        
        print(summary.to_string(index=False))
        
        # Save summary
        summary_filename = f'data/raw/coinbase_top200_summary_{timestamp}.csv'
        summary.to_csv(summary_filename, index=False)
        print(f"\n✓ Summary saved to {summary_filename}")
        
        return combined_df
    else:
        print("✗ No data was downloaded.")
        return pd.DataFrame()


if __name__ == "__main__":
    # Download all available data from 2020-01-01 to present
    # for symbols that have ever been in top 200 by market cap
    df = download_top200_historical_data(start_date='2020-01-01')
    
    if not df.empty:
        print(f"\n{'='*80}")
        print(f"SAMPLE OF DOWNLOADED DATA")
        print(f"{'='*80}\n")
        print(df.head(30).to_string(index=False))
        print(f"\n... {len(df)} total rows")
