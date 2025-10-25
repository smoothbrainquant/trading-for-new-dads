#!/usr/bin/env python3
"""
Compare CMC snapshots with Coinbase daily data to find missing symbols,
then download historical data for any missing symbols from 2020 to current.
"""

import ccxt
from datetime import datetime, timedelta
import pandas as pd
import time
from typing import Set, Dict, List
import os


def get_cmc_symbols() -> Set[str]:
    """
    Get all unique symbols from CMC historical snapshots (yearly + monthly).
    
    Returns:
        Set of unique symbols from CMC data
    """
    print("="*80)
    print("EXTRACTING SYMBOLS FROM CMC SNAPSHOTS")
    print("="*80)
    
    all_symbols = set()
    
    # Read historical snapshots (yearly)
    historical_file = 'data/raw/coinmarketcap_historical_all_snapshots.csv'
    if os.path.exists(historical_file):
        print(f"\nReading {historical_file}...")
        df_historical = pd.read_csv(historical_file)
        symbols_hist = set(df_historical['Symbol'].unique())
        all_symbols.update(symbols_hist)
        print(f"  Found {len(symbols_hist)} unique symbols in yearly snapshots")
        print(f"  Date range: {df_historical['snapshot_date'].min()} to {df_historical['snapshot_date'].max()}")
    else:
        print(f"  ✗ File not found: {historical_file}")
    
    # Read monthly snapshots
    monthly_file = 'data/raw/coinmarketcap_monthly_all_snapshots.csv'
    if os.path.exists(monthly_file):
        print(f"\nReading {monthly_file}...")
        df_monthly = pd.read_csv(monthly_file)
        symbols_monthly = set(df_monthly['Symbol'].unique())
        
        new_symbols = symbols_monthly - all_symbols
        all_symbols.update(symbols_monthly)
        
        print(f"  Found {len(symbols_monthly)} unique symbols in monthly snapshots")
        print(f"  Added {len(new_symbols)} new symbols not in yearly data")
        print(f"  Date range: {df_monthly['snapshot_date'].min()} to {df_monthly['snapshot_date'].max()}")
    else:
        print(f"  ✗ File not found: {monthly_file}")
    
    print(f"\n{'='*80}")
    print(f"TOTAL UNIQUE CMC SYMBOLS: {len(all_symbols)}")
    print(f"{'='*80}")
    
    return all_symbols


def get_coinbase_symbols() -> Set[str]:
    """
    Get all unique symbols that exist in Coinbase daily data.
    
    Returns:
        Set of unique base symbols from Coinbase data
    """
    print("\n" + "="*80)
    print("EXTRACTING SYMBOLS FROM COINBASE DAILY DATA")
    print("="*80)
    
    all_symbols = set()
    
    # Look for the most recent coinbase file
    coinbase_files = [
        'data/raw/coinbase_top200_daily_20200101_to_present_20251025_171900.csv',
        'data/raw/coinbase_top200_daily_20200101_to_present_20251025_171425.csv',
        'data/raw/coinbase_spot_daily_data_20200101_20251024_110130.csv',
    ]
    
    for file_path in coinbase_files:
        if os.path.exists(file_path):
            print(f"\nReading {file_path}...")
            df = pd.read_csv(file_path)
            
            # Get base symbols
            if 'base' in df.columns:
                symbols = set(df['base'].unique())
            elif 'symbol' in df.columns:
                # Extract base from symbol (e.g., 'BTC/USD' -> 'BTC')
                symbols = set(df['symbol'].str.split('/').str[0].unique())
            else:
                print(f"  ✗ Cannot find 'base' or 'symbol' column")
                continue
            
            all_symbols.update(symbols)
            print(f"  Found {len(symbols)} unique symbols")
            print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
            print(f"  Total rows: {len(df):,}")
            break
    
    print(f"\n{'='*80}")
    print(f"TOTAL UNIQUE COINBASE SYMBOLS: {len(all_symbols)}")
    print(f"{'='*80}")
    
    return all_symbols


def compare_symbols(cmc_symbols: Set[str], coinbase_symbols: Set[str]) -> tuple:
    """
    Compare CMC symbols with Coinbase symbols to find missing ones.
    
    Returns:
        Tuple of (missing_symbols, present_symbols)
    """
    print("\n" + "="*80)
    print("COMPARING SYMBOLS")
    print("="*80)
    
    missing_symbols = cmc_symbols - coinbase_symbols
    present_symbols = cmc_symbols & coinbase_symbols
    
    print(f"\n  CMC Symbols:        {len(cmc_symbols):,}")
    print(f"  Coinbase Symbols:   {len(coinbase_symbols):,}")
    print(f"  Present in both:    {len(present_symbols):,}")
    print(f"  Missing in Coinbase:{len(missing_symbols):,}")
    
    if missing_symbols:
        print(f"\n{'='*80}")
        print(f"MISSING SYMBOLS (in CMC but not in Coinbase data)")
        print(f"{'='*80}")
        sorted_missing = sorted(list(missing_symbols))
        
        # Print in columns
        cols = 6
        for i in range(0, len(sorted_missing), cols):
            row = sorted_missing[i:i+cols]
            print("  " + "  ".join(f"{s:8s}" for s in row))
    
    return missing_symbols, present_symbols


def get_coinbase_markets() -> Dict[str, str]:
    """
    Get all available spot markets on Coinbase.
    
    Returns:
        Dictionary mapping base currency to full symbol (e.g., {'BTC': 'BTC/USD'})
    """
    print("\n" + "="*80)
    print("FETCHING COINBASE MARKETS")
    print("="*80)
    
    exchange = ccxt.coinbase({
        'enableRateLimit': True,
    })
    
    try:
        markets = exchange.load_markets()
        print(f"  Loaded {len(markets)} total markets")
        
        spot_markets = {}
        
        for symbol, market in markets.items():
            is_spot = market.get('spot', False) or market.get('type') == 'spot'
            
            if is_spot:
                base = market.get('base')
                quote = market.get('quote')
                
                # Prefer USD, then USDT, then USDC
                if quote in ['USD', 'USDT', 'USDC']:
                    current_symbol = spot_markets.get(base, '')
                    if base not in spot_markets:
                        spot_markets[base] = symbol
                    elif quote == 'USD' and '/USD' not in current_symbol:
                        spot_markets[base] = symbol
                    elif quote == 'USDT' and '/USD' not in current_symbol and '/USDT' not in current_symbol:
                        spot_markets[base] = symbol
        
        print(f"✓ Mapped {len(spot_markets)} unique base currencies")
        return spot_markets
        
    except Exception as e:
        print(f"✗ Error fetching Coinbase markets: {str(e)}")
        return {}


def fetch_daily_data_for_symbol(exchange: ccxt.Exchange, symbol: str, start_date: datetime) -> pd.DataFrame:
    """
    Fetch all available daily OHLCV data for a single symbol since start_date.
    """
    try:
        print(f"  Fetching {symbol}...", end=' ', flush=True)
        
        all_ohlcv = []
        now = datetime.now()
        chunk_days = 300
        
        # Try different start dates if preferred date doesn't work
        start_dates_to_try = [
            start_date,
            datetime(2021, 1, 1),
            datetime(2022, 1, 1),
            datetime(2023, 1, 1),
            datetime(2024, 1, 1),
        ]
        
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
                    
                    last_timestamp = ohlcv[-1][0]
                    last_date = datetime.fromtimestamp(last_timestamp / 1000)
                    
                    if len(ohlcv) < chunk_days:
                        break
                    
                    current_date = last_date + timedelta(days=1)
                    time.sleep(0.1)
                    
                except Exception as e:
                    if 'INVALID_ARGUMENT' in str(e) or 'UNAVAILABLE' in str(e):
                        break
                    else:
                        break
            
            if temp_ohlcv:
                all_ohlcv = temp_ohlcv
                break
        
        # If still no data, try without any start date
        if not all_ohlcv:
            try:
                ohlcv = exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe='1d',
                    limit=1000
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
        
        df['date'] = pd.to_datetime(df['timestamp'], unit='ms').dt.date
        df['symbol'] = symbol
        df['base'] = symbol.split('/')[0]
        
        df = df[['date', 'symbol', 'base', 'open', 'high', 'low', 'close', 'volume']]
        df = df.drop_duplicates(subset=['date', 'symbol'], keep='first')
        df = df.sort_values('date').reset_index(drop=True)
        
        print(f"✓ {len(df)} days ({df['date'].min()} to {df['date'].max()})")
        return df
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return pd.DataFrame()


def download_missing_symbols(missing_symbols: Set[str], start_date: str = '2020-01-01') -> pd.DataFrame:
    """
    Download historical data for missing symbols from Coinbase.
    
    Args:
        missing_symbols: Set of symbol names that are missing
        start_date: Start date in 'YYYY-MM-DD' format
        
    Returns:
        DataFrame with downloaded data
    """
    if not missing_symbols:
        print("\n✓ No missing symbols to download!")
        return pd.DataFrame()
    
    # Get available Coinbase markets
    coinbase_markets = get_coinbase_markets()
    
    # Match missing symbols with Coinbase markets
    print("\n" + "="*80)
    print("MATCHING MISSING SYMBOLS WITH COINBASE MARKETS")
    print("="*80)
    
    matched = []
    not_found = []
    
    for symbol in sorted(missing_symbols):
        if symbol in coinbase_markets:
            matched.append((symbol, coinbase_markets[symbol]))
        else:
            not_found.append(symbol)
    
    print(f"\n✓ Found {len(matched)} missing symbols available on Coinbase")
    print(f"✗ {len(not_found)} symbols not available on Coinbase")
    
    if matched:
        print(f"\nSymbols to download:")
        for i, (base, full_symbol) in enumerate(matched, 1):
            print(f"  {i:2d}. {base:8s} -> {full_symbol}")
    
    if not_found:
        print(f"\nSymbols not available on Coinbase:")
        cols = 6
        for i in range(0, len(not_found), cols):
            row = not_found[i:i+cols]
            print("  " + "  ".join(f"{s:8s}" for s in row))
    
    if not matched:
        print("\n✓ No additional symbols to download from Coinbase")
        return pd.DataFrame()
    
    # Download data
    print(f"\n{'='*80}")
    print(f"DOWNLOADING MISSING SYMBOLS FROM {start_date} TO PRESENT")
    print(f"{'='*80}\n")
    
    exchange = ccxt.coinbase({
        'enableRateLimit': True,
    })
    
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    
    all_data = []
    successful = 0
    failed = 0
    
    for i, (base, full_symbol) in enumerate(matched, 1):
        print(f"[{i}/{len(matched)}]", end=' ')
        
        df = fetch_daily_data_for_symbol(exchange, full_symbol, start_dt)
        
        if not df.empty:
            all_data.append(df)
            successful += 1
        else:
            failed += 1
        
        if i < len(matched):
            time.sleep(exchange.rateLimit / 1000)
    
    # Combine and save
    print(f"\n{'='*80}")
    print(f"DOWNLOAD SUMMARY")
    print(f"{'='*80}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(matched)}")
    print(f"{'='*80}\n")
    
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df = combined_df.sort_values(['date', 'symbol']).reset_index(drop=True)
        
        print(f"Combined data shape: {combined_df.shape}")
        print(f"Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
        print(f"Unique symbols: {combined_df['base'].nunique()}")
        
        # Save to CSV
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f'data/raw/coinbase_missing_symbols_{start_date.replace("-", "")}_to_present_{timestamp}.csv'
        
        combined_df.to_csv(output_filename, index=False)
        print(f"\n✓ Data saved to {output_filename}")
        
        # Print summary
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
        summary_filename = f'data/raw/coinbase_missing_symbols_summary_{timestamp}.csv'
        summary.to_csv(summary_filename, index=False)
        print(f"\n✓ Summary saved to {summary_filename}")
        
        return combined_df
    else:
        print("✗ No data was downloaded.")
        return pd.DataFrame()


def main():
    """Main function to compare and download missing symbols."""
    
    print("\n" + "="*80)
    print("COMPARE CMC SNAPSHOTS WITH COINBASE DATA")
    print("="*80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Step 1: Get all symbols from CMC snapshots
    cmc_symbols = get_cmc_symbols()
    
    # Step 2: Get all symbols from Coinbase daily data
    coinbase_symbols = get_coinbase_symbols()
    
    # Step 3: Compare and identify missing symbols
    missing_symbols, present_symbols = compare_symbols(cmc_symbols, coinbase_symbols)
    
    # Step 4: Download missing symbols if any
    if missing_symbols:
        df = download_missing_symbols(missing_symbols, start_date='2020-01-01')
        
        if not df.empty:
            print(f"\n{'='*80}")
            print(f"SAMPLE OF DOWNLOADED DATA")
            print(f"{'='*80}\n")
            print(df.head(30).to_string(index=False))
            print(f"\n... {len(df)} total rows")
    
    print(f"\n{'='*80}")
    print(f"COMPLETE!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
