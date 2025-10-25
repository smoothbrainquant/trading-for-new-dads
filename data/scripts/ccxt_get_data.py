import ccxt
from datetime import datetime, timedelta
import pandas as pd

def ccxt_fetch_hyperliquid_daily_data(symbols=['BTC/USDC:USDC', 'ETH/USDC:USDC', 'SOL/USDC:USDC'], days=5):
    """
    Fetch daily OHLCV data from Hyperliquid for specified symbols.
    
    Args:
        symbols: List of trading pairs to fetch
        days: Number of days of historical data to retrieve
    
    Returns:
        DataFrame with columns: date, symbol, open, high, low, close, volume
    """
    # Initialize Hyperliquid exchange
    exchange = ccxt.hyperliquid({
        'enableRateLimit': True,
    })
    
    # Calculate timestamp for 'days' ago
    since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
    
    all_data = []
    
    for symbol in symbols:
        try:
            print(f"\nFetching data for {symbol}...")
            
            # Fetch OHLCV data (timeframe='1d' for daily)
            ohlcv = exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe='1d',
                since=since,
                limit=days
            )
            
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
            
            print(f"\n{symbol} - Last {len(df)} days:")
            print(df.to_string(index=False))
            print(f"\nSummary for {symbol}:")
            print(f"  Price Range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
            print(f"  Average Volume: {df['volume'].mean():.2f}")
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {str(e)}")
    
    # Combine all data into a single DataFrame
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df = combined_df.sort_values(['date', 'symbol']).reset_index(drop=True)
        return combined_df
    else:
        # Return empty DataFrame with correct schema if no data was fetched
        return pd.DataFrame(columns=['date', 'symbol', 'open', 'high', 'low', 'close', 'volume'])

if __name__ == "__main__":
    print("Fetching daily data from Hyperliquid...")
    print("=" * 60)
    
    # Fetch data for BTC, ETH, and SOL
    df = ccxt_fetch_hyperliquid_daily_data(
        symbols=['BTC/USDC:USDC', 'ETH/USDC:USDC', 'SOL/USDC:USDC'],
        days=5
    )
    
    print("\n" + "=" * 60)
    print("Data fetch complete!")
    print(f"\nCombined DataFrame shape: {df.shape}")
    print("\nFirst few rows:")
    print(df.head(10))
