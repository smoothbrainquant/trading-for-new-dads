import ccxt
from datetime import datetime, timedelta
import pandas as pd

def fetch_hyperliquid_daily_data(symbols=['BTC/USDC:USDC', 'ETH/USDC:USDC', 'SOL/USDC:USDC'], days=5):
    """
    Fetch daily OHLCV data from Hyperliquid for specified symbols.
    
    Args:
        symbols: List of trading pairs to fetch
        days: Number of days of historical data to retrieve
    
    Returns:
        Dictionary with symbol as key and DataFrame as value
    """
    # Initialize Hyperliquid exchange
    exchange = ccxt.hyperliquid({
        'enableRateLimit': True,
    })
    
    # Calculate timestamp for 'days' ago
    since = exchange.parse8601((datetime.now() - timedelta(days=days)).isoformat())
    
    results = {}
    
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
            
            # Convert to DataFrame for better readability
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # Convert timestamp to readable date
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
            
            results[symbol] = df
            
            print(f"\n{symbol} - Last {len(df)} days:")
            print(df.to_string(index=False))
            print(f"\nSummary for {symbol}:")
            print(f"  Price Range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
            print(f"  Average Volume: {df['volume'].mean():.2f}")
            
        except Exception as e:
            print(f"Error fetching data for {symbol}: {str(e)}")
            results[symbol] = None
    
    return results

if __name__ == "__main__":
    print("Fetching daily data from Hyperliquid...")
    print("=" * 60)
    
    # Fetch data for BTC, ETH, and SOL
    data = fetch_hyperliquid_daily_data(
        symbols=['BTC/USDC:USDC', 'ETH/USDC:USDC', 'SOL/USDC:USDC'],
        days=5
    )
    
    print("\n" + "=" * 60)
    print("Data fetch complete!")
