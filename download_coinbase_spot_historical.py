import ccxt
from datetime import datetime, timedelta
import pandas as pd
import time
from typing import List, Dict

def get_unique_symbols_from_snapshots(filename: str = 'coinmarketcap_historical_all_snapshots.csv') -> List[str]:
    """
    Extract unique coin symbols from the historical market cap snapshots.
    
    Args:
        filename: Path to the CSV file containing historical snapshots
    
    Returns:
        List of unique coin symbols
    """
    print(f"Reading symbols from {filename}...")
    df = pd.read_csv(filename)
    
    # Get unique symbols
    unique_symbols = sorted(df['Symbol'].unique())
    print(f"Found {len(unique_symbols)} unique symbols in historical data")
    
    return unique_symbols

def get_coinbase_spot_markets() -> Dict[str, str]:
    """
    Get all available spot markets on Coinbase.
    
    Returns:
        Dictionary mapping base currency to full symbol (e.g., {'BTC': 'BTC/USD'})
    """
    print("\nConnecting to Coinbase...")
    exchange = ccxt.coinbase({
        'enableRateLimit': True,
    })
    
    try:
        # Load all markets
        markets = exchange.load_markets()
        
        # Filter for spot markets (type = 'spot') with USD or USDT quote
        spot_markets = {}
        
        for symbol, market in markets.items():
            if market.get('type') == 'spot' and market.get('active', True):
                base = market.get('base')
                quote = market.get('quote')
                
                # Prefer USD, then USDT, then USDC
                if quote in ['USD', 'USDT', 'USDC']:
                    # If we already have this base, prefer USD over USDT over USDC
                    if base not in spot_markets or (
                        quote == 'USD' or 
                        (quote == 'USDT' and '/USD' not in spot_markets.get(base, '')) or
                        (quote == 'USDC' and '/USD' not in spot_markets.get(base, '') and '/USDT' not in spot_markets.get(base, ''))
                    ):
                        spot_markets[base] = symbol
        
        print(f"Found {len(spot_markets)} spot markets on Coinbase")
        
        return spot_markets
        
    except Exception as e:
        print(f"Error fetching Coinbase markets: {str(e)}")
        return {}

def fetch_daily_data_for_symbol(exchange: ccxt.Exchange, symbol: str, start_date: datetime) -> pd.DataFrame:
    """
    Fetch daily OHLCV data for a single symbol from a start date to present.
    Fetches in chunks to handle Coinbase's 300-day limit.
    
    Args:
        exchange: CCXT exchange instance
        symbol: Trading pair symbol (e.g., 'BTC/USD')
        start_date: Start date for historical data
    
    Returns:
        DataFrame with OHLCV data
    """
    try:
        print(f"  Fetching data for {symbol}...", end=' ', flush=True)
        
        all_ohlcv = []
        current_date = start_date
        now = datetime.now()
        
        # Fetch data in 250-day chunks (to stay under the limit)
        chunk_days = 250
        
        while current_date < now:
            # Convert current date to timestamp
            since = int(current_date.timestamp() * 1000)
            
            try:
                ohlcv = exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe='1d',
                    since=since,
                    limit=chunk_days
                )
                
                if not ohlcv:
                    # No more data available
                    break
                
                all_ohlcv.extend(ohlcv)
                
                # Move to the next chunk
                # Get the last timestamp and add 1 day
                last_timestamp = ohlcv[-1][0]
                last_date = datetime.fromtimestamp(last_timestamp / 1000)
                
                # If we got less data than requested, we've reached the end
                if len(ohlcv) < chunk_days:
                    break
                
                # Move forward by the chunk size
                current_date = last_date + timedelta(days=1)
                
                # Add a small delay to respect rate limits
                time.sleep(0.1)
                
            except Exception as e:
                # If we hit an error mid-fetch, break and use what we have
                if 'INVALID_ARGUMENT' in str(e):
                    # This symbol doesn't exist on Coinbase
                    break
                else:
                    # Try to continue with what we have
                    break
        
        if not all_ohlcv:
            print(f"No data available")
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
        
        # Remove duplicates (in case of overlapping data)
        df = df.drop_duplicates(subset=['date', 'symbol'], keep='first')
        
        # Filter to only include data from start_date onwards
        df = df[df['date'] >= start_date.date()]
        
        print(f"✓ Got {len(df)} days of data (from {df['date'].min()} to {df['date'].max()})")
        
        return df
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return pd.DataFrame()

def download_coinbase_historical_data(
    start_date: str = '2020-01-01',
    output_filename: str = None
) -> pd.DataFrame:
    """
    Main function to download historical daily data from Coinbase spot markets.
    
    Args:
        start_date: Start date in 'YYYY-MM-DD' format
        output_filename: Output CSV filename (auto-generated if None)
    
    Returns:
        DataFrame with all downloaded data
    """
    print("="*80)
    print("COINBASE SPOT HISTORICAL DATA DOWNLOADER")
    print("="*80)
    
    # Step 1: Get unique symbols from historical snapshots
    snapshot_symbols = get_unique_symbols_from_snapshots()
    
    # Step 2: Get available Coinbase spot markets
    coinbase_markets = get_coinbase_spot_markets()
    
    # Step 3: Match symbols
    print("\nMatching symbols with Coinbase markets...")
    matched_symbols = []
    for symbol in snapshot_symbols:
        if symbol in coinbase_markets:
            matched_symbols.append((symbol, coinbase_markets[symbol]))
    
    print(f"\nFound {len(matched_symbols)} matching symbols on Coinbase:")
    for base, full_symbol in matched_symbols[:10]:
        print(f"  {base} -> {full_symbol}")
    if len(matched_symbols) > 10:
        print(f"  ... and {len(matched_symbols) - 10} more")
    
    # Step 4: Download data for all matched symbols
    print(f"\n{'='*80}")
    print(f"Downloading daily data from {start_date} to present...")
    print(f"{'='*80}\n")
    
    exchange = ccxt.coinbase({
        'enableRateLimit': True,
    })
    
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    now = datetime.now()
    
    all_data = []
    successful = 0
    failed = 0
    
    for i, (base, full_symbol) in enumerate(matched_symbols, 1):
        print(f"[{i}/{len(matched_symbols)}]", end=' ')
        
        # First try from start_date
        df = fetch_daily_data_for_symbol(exchange, full_symbol, start_dt)
        
        # If we got partial data (less than expected), try fetching recent data separately
        if not df.empty:
            days_fetched = len(df)
            expected_days = (now - start_dt).days
            
            # If we got significantly less data than expected, try fetching recent data
            if days_fetched < expected_days * 0.5:  # Less than 50% of expected
                print(f"\n    Attempting to fetch recent data...", end=' ')
                
                # Try fetching last 2 years of data
                recent_start = now - timedelta(days=730)
                df_recent = fetch_daily_data_for_symbol(exchange, full_symbol, recent_start)
                
                if not df_recent.empty:
                    # Combine with existing data, removing duplicates
                    df = pd.concat([df, df_recent], ignore_index=True)
                    df = df.drop_duplicates(subset=['date', 'symbol'], keep='first')
                    df = df.sort_values('date').reset_index(drop=True)
                    print(f"✓ Combined to {len(df)} total days")
        
        if not df.empty:
            all_data.append(df)
            successful += 1
        else:
            failed += 1
        
        # Add delay between requests to respect rate limits
        if i < len(matched_symbols):
            time.sleep(exchange.rateLimit / 1000)
    
    # Step 5: Combine all data
    print(f"\n{'='*80}")
    print(f"Download Summary:")
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
        if output_filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_filename = f'coinbase_spot_daily_data_{start_date.replace("-", "")}_{timestamp}.csv'
        
        combined_df.to_csv(output_filename, index=False)
        print(f"\n✓ Data saved to {output_filename}")
        
        return combined_df
    else:
        print("No data was downloaded.")
        return pd.DataFrame()

if __name__ == "__main__":
    # Download all available data from 2020-01-01 to present
    df = download_coinbase_historical_data(
        start_date='2020-01-01'
    )
    
    # Display sample of the data
    if not df.empty:
        print("\n" + "="*80)
        print("Sample of downloaded data:")
        print("="*80)
        print(df.head(20).to_string(index=False))
        
        print("\n" + "="*80)
        print("Data by symbol:")
        print("="*80)
        summary = df.groupby('base').agg({
            'date': ['min', 'max', 'count']
        }).reset_index()
        summary.columns = ['Symbol', 'First Date', 'Last Date', 'Days']
        print(summary.to_string(index=False))
