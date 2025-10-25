import ccxt
import pandas as pd
from datetime import datetime
from pprint import pprint

def fetch_binance_funding_rates(symbols=None, exchange_id='binance'):
    """
    Fetch current funding rates from Binance for perpetual futures.
    
    Args:
        symbols: List of trading pairs (e.g., ['BTC/USDT:USDT', 'ETH/USDT:USDT'])
                 If None, fetches all available funding rates
        exchange_id: Exchange to use ('binance' or 'binanceus')
    
    Returns:
        DataFrame with columns: symbol, funding_rate, funding_time, next_funding_time
    
    Note:
        - Binance may be geo-restricted in some locations
        - Use exchange_id='binanceus' if you're in the US
        - Funding occurs every 8 hours (00:00, 08:00, 16:00 UTC)
        - Positive funding rate = longs pay shorts
        - Negative funding rate = shorts pay longs
    """
    # Initialize Binance exchange
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',  # Use futures market
        }
    })
    
    try:
        if symbols:
            # Fetch funding rates for specific symbols
            funding_data = []
            for symbol in symbols:
                try:
                    print(f"Fetching funding rate for {symbol}...")
                    funding_rate = exchange.fetch_funding_rate(symbol)
                    funding_data.append(funding_rate)
                except Exception as e:
                    print(f"Error fetching funding rate for {symbol}: {str(e)}")
        else:
            # Fetch all funding rates
            print("Fetching all funding rates from Binance...")
            funding_rates = exchange.fetch_funding_rates()
            funding_data = list(funding_rates.values())
        
        # Convert to DataFrame
        if funding_data:
            df_data = []
            for item in funding_data:
                df_data.append({
                    'symbol': item.get('symbol'),
                    'funding_rate': item.get('fundingRate'),
                    'funding_rate_pct': item.get('fundingRate', 0) * 100,  # Convert to percentage
                    'funding_timestamp': item.get('fundingTimestamp'),
                    'funding_time': pd.to_datetime(item.get('fundingTimestamp'), unit='ms') if item.get('fundingTimestamp') else None,
                    'next_funding_time': pd.to_datetime(item.get('nextFundingTime'), unit='ms') if item.get('nextFundingTime') else None,
                    'mark_price': item.get('markPrice'),
                    'index_price': item.get('indexPrice'),
                })
            
            df = pd.DataFrame(df_data)
            df = df.sort_values('funding_rate', ascending=False).reset_index(drop=True)
            return df
        else:
            return pd.DataFrame(columns=['symbol', 'funding_rate', 'funding_rate_pct', 
                                        'funding_timestamp', 'funding_time', 'next_funding_time', 
                                        'mark_price', 'index_price'])
            
    except Exception as e:
        print(f"Error fetching funding rates: {str(e)}")
        raise


def fetch_binance_funding_history(symbol, limit=100):
    """
    Fetch historical funding rates for a specific symbol.
    
    Args:
        symbol: Trading pair (e.g., 'BTC/USDT:USDT')
        limit: Number of historical records to fetch (default 100)
    
    Returns:
        DataFrame with historical funding rates
    """
    exchange = ccxt.binance({
        'enableRateLimit': True,
        'options': {
            'defaultType': 'future',
        }
    })
    
    try:
        print(f"\nFetching funding rate history for {symbol}...")
        history = exchange.fetch_funding_rate_history(symbol, limit=limit)
        
        if history:
            df = pd.DataFrame(history)
            df['funding_time'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['funding_rate_pct'] = df['fundingRate'] * 100
            df = df.sort_values('timestamp', ascending=False).reset_index(drop=True)
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        print(f"Error fetching funding history for {symbol}: {str(e)}")
        raise


def print_funding_summary(df, top_n=20):
    """
    Print a formatted summary of funding rates.
    
    Args:
        df: DataFrame with funding rate data
        top_n: Number of top positive and negative rates to display
    """
    print("\n" + "=" * 100)
    print("BINANCE PERPETUAL FUTURES FUNDING RATES")
    print("=" * 100)
    
    if df.empty:
        print("\nNo funding rate data available.")
        return
    
    print(f"\nTotal symbols: {len(df)}")
    print(f"Data fetched at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if 'next_funding_time' in df.columns and not df['next_funding_time'].isna().all():
        next_funding = df['next_funding_time'].iloc[0]
        print(f"Next funding time: {next_funding}")
    
    # Summary statistics
    print(f"\nFunding Rate Statistics:")
    print(f"  Mean:   {df['funding_rate_pct'].mean():.4f}%")
    print(f"  Median: {df['funding_rate_pct'].median():.4f}%")
    print(f"  Min:    {df['funding_rate_pct'].min():.4f}%")
    print(f"  Max:    {df['funding_rate_pct'].max():.4f}%")
    
    # Top positive funding rates (long pays short)
    print(f"\n{'-' * 100}")
    print(f"TOP {top_n} HIGHEST FUNDING RATES (Long pays Short - expensive to be long)")
    print(f"{'-' * 100}")
    print(f"{'Symbol':<20} {'Funding Rate':<15} {'Annual Rate':<15} {'Mark Price':<15}")
    print(f"{'-' * 100}")
    
    top_positive = df.nlargest(top_n, 'funding_rate_pct')
    for _, row in top_positive.iterrows():
        symbol = row['symbol']
        funding_pct = row['funding_rate_pct']
        # Funding occurs every 8 hours on Binance (3 times per day)
        annual_rate = funding_pct * 3 * 365
        mark_price = row.get('mark_price', 'N/A')
        mark_price_str = f"${mark_price:,.2f}" if isinstance(mark_price, (int, float)) else str(mark_price)
        print(f"{symbol:<20} {funding_pct:>13.4f}%  {annual_rate:>13.2f}%  {mark_price_str:<15}")
    
    # Top negative funding rates (short pays long)
    print(f"\n{'-' * 100}")
    print(f"TOP {top_n} LOWEST FUNDING RATES (Short pays Long - expensive to be short)")
    print(f"{'-' * 100}")
    print(f"{'Symbol':<20} {'Funding Rate':<15} {'Annual Rate':<15} {'Mark Price':<15}")
    print(f"{'-' * 100}")
    
    top_negative = df.nsmallest(top_n, 'funding_rate_pct')
    for _, row in top_negative.iterrows():
        symbol = row['symbol']
        funding_pct = row['funding_rate_pct']
        annual_rate = funding_pct * 3 * 365
        mark_price = row.get('mark_price', 'N/A')
        mark_price_str = f"${mark_price:,.2f}" if isinstance(mark_price, (int, float)) else str(mark_price)
        print(f"{symbol:<20} {funding_pct:>13.4f}%  {annual_rate:>13.2f}%  {mark_price_str:<15}")
    
    print("=" * 100)


if __name__ == "__main__":
    print("Fetching Binance funding rates...")
    print("=" * 100)
    
    try:
        # Option 1: Fetch all funding rates
        # Note: Use exchange_id='binanceus' if you're in the US
        df_all = fetch_binance_funding_rates(exchange_id='binance')
        print_funding_summary(df_all, top_n=20)
        
        # Save to CSV
        output_file = 'binance_funding_rates.csv'
        df_all.to_csv(output_file, index=False)
        print(f"\n✓ Funding rates saved to {output_file}")
        
        # Option 2: Fetch specific symbols (uncomment to use)
        # specific_symbols = ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']
        # df_specific = fetch_binance_funding_rates(symbols=specific_symbols)
        # print("\nSpecific symbols:")
        # print(df_specific[['symbol', 'funding_rate_pct', 'mark_price']])
        
        # Option 3: Fetch funding rate history for a specific symbol (uncomment to use)
        # df_history = fetch_binance_funding_history('BTC/USDT:USDT', limit=50)
        # if not df_history.empty:
        #     print("\n\nBTC/USDT Funding Rate History (Last 50):")
        #     print(df_history[['funding_time', 'fundingRate', 'funding_rate_pct']].head(20))
        #     
        #     # Calculate average funding rate
        #     avg_funding = df_history['funding_rate_pct'].mean()
        #     print(f"\nAverage funding rate (last 50): {avg_funding:.4f}%")
        #     print(f"Annualized (assuming 3x per day): {avg_funding * 3 * 365:.2f}%")
        
    except ccxt.ExchangeNotAvailable as e:
        print("\n" + "!" * 100)
        print("ERROR: Binance API is not available from this location (geo-restricted)")
        print("!" * 100)
        print("\nPossible solutions:")
        print("  1. Use a VPN to access from a supported location")
        print("  2. Use exchange_id='binanceus' if you're in the US")
        print("  3. Use an alternative exchange (e.g., Bybit, OKX)")
        print(f"\nError details: {str(e)}")
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        raise
