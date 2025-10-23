"""
Fetch 750 days of daily OHLCV data for top 10 markets from Hyperliquid.
This data will be used for the mean reversion backtest.
"""

import ccxt
from datetime import datetime, timedelta
import pandas as pd
import time

def fetch_750d_data():
    """
    Fetch 750 days of daily data for top 10 crypto perpetual futures.
    """
    # Top 10 markets based on the current data file
    symbols = [
        'BTC/USDC:USDC',
        'ETH/USDC:USDC', 
        'SOL/USDC:USDC',
        'DOGE/USDC:USDC',
        'XRP/USDC:USDC',
        'HYPE/USDC',
        'HYPE/USDC:USDC',
        'UBTC/USDC',
        'ASTER/USDC:USDC',
        'XPL/USDC:USDC'
    ]
    
    days = 750
    
    # Initialize Hyperliquid exchange
    exchange = ccxt.hyperliquid({
        'enableRateLimit': True,
    })
    
    # Calculate timestamp for 750 days ago
    since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
    
    all_data = []
    
    for i, symbol in enumerate(symbols):
        try:
            print(f"\n[{i+1}/{len(symbols)}] Fetching data for {symbol}...")
            
            # Fetch OHLCV data (timeframe='1d' for daily)
            ohlcv = exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe='1d',
                since=since,
                limit=1000  # Max limit to get as much data as possible
            )
            
            if not ohlcv:
                print(f"  WARNING: No data returned for {symbol}")
                continue
            
            # Convert to DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # Convert timestamp to readable date and add symbol column
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['symbol'] = symbol
            df = df[['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
            
            all_data.append(df)
            
            print(f"  ✓ Fetched {len(df)} days of data")
            print(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")
            print(f"  Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
            
            # Rate limiting - small delay between requests
            time.sleep(0.5)
            
        except Exception as e:
            print(f"  ✗ Error fetching data for {symbol}: {str(e)}")
            continue
    
    # Combine all data into a single DataFrame
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df = combined_df.sort_values(['date', 'symbol']).reset_index(drop=True)
        
        # Save to CSV
        output_file = 'top10_markets_750d_daily_data.csv'
        combined_df.to_csv(output_file, index=False)
        
        print("\n" + "=" * 80)
        print("DATA FETCH COMPLETE")
        print("=" * 80)
        print(f"\nTotal records: {len(combined_df):,}")
        print(f"Unique symbols: {combined_df['symbol'].nunique()}")
        print(f"Date range: {combined_df['date'].min().date()} to {combined_df['date'].max().date()}")
        print(f"Saved to: {output_file}")
        print("\nData summary by symbol:")
        print(combined_df.groupby('symbol').agg({
            'date': ['min', 'max', 'count']
        }).to_string())
        
        return combined_df
    else:
        print("\n✗ ERROR: No data was fetched successfully")
        return pd.DataFrame(columns=['date', 'symbol', 'open', 'high', 'low', 'close', 'volume'])


if __name__ == "__main__":
    print("=" * 80)
    print("FETCHING 750 DAYS OF DAILY DATA FROM HYPERLIQUID")
    print("=" * 80)
    print("\nThis will fetch historical data for the top 10 crypto markets.")
    print("Estimated time: 1-2 minutes\n")
    
    df = fetch_750d_data()
    
    if not df.empty:
        print("\n✓ Success! Data ready for mean reversion backtest.")
    else:
        print("\n✗ Failed to fetch data. Please check the error messages above.")
