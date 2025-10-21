import ccxt
import pandas as pd
from datetime import datetime


def get_bid_ask(symbols=None):
    """
    Fetch bid/ask prices for a list of instruments from Hyperliquid.
    
    Args:
        symbols (list): List of trading pairs to fetch bid/ask for.
                       If None, fetches for all active markets.
                       Example: ['BTC/USDC:USDC', 'ETH/USDC:USDC', 'SOL/USDC:USDC']
    
    Returns:
        DataFrame with columns: symbol, bid, ask, spread, spread_pct, timestamp
    """
    # Initialize Hyperliquid exchange
    exchange = ccxt.hyperliquid({
        'enableRateLimit': True,
    })
    
    # If no symbols provided, get all active markets
    if symbols is None:
        print("No symbols provided, fetching all active markets...")
        markets = exchange.load_markets()
        symbols = [symbol for symbol, market in markets.items() 
                  if market.get('active') and market.get('type') == 'swap']
        print(f"Found {len(symbols)} active perpetual markets")
    
    bid_ask_data = []
    
    print(f"\nFetching bid/ask for {len(symbols)} instruments...")
    print("=" * 80)
    
    for symbol in symbols:
        try:
            # Fetch ticker data which includes bid/ask
            ticker = exchange.fetch_ticker(symbol)
            
            bid = ticker.get('bid')
            ask = ticker.get('ask')
            
            if bid is not None and ask is not None:
                spread = ask - bid
                spread_pct = (spread / bid * 100) if bid > 0 else 0
                
                bid_ask_data.append({
                    'symbol': symbol,
                    'bid': bid,
                    'ask': ask,
                    'spread': spread,
                    'spread_pct': spread_pct,
                    'timestamp': datetime.fromtimestamp(ticker['timestamp'] / 1000) if ticker.get('timestamp') else datetime.now()
                })
                
                print(f"{symbol:20s} | Bid: ${bid:>12,.8f} | Ask: ${ask:>12,.8f} | Spread: ${spread:>8.8f} ({spread_pct:.4f}%)")
            else:
                print(f"{symbol:20s} | No bid/ask data available")
                
        except Exception as e:
            print(f"{symbol:20s} | Error: {str(e)}")
    
    # Create DataFrame
    if bid_ask_data:
        df = pd.DataFrame(bid_ask_data)
        df = df.sort_values('symbol').reset_index(drop=True)
        return df
    else:
        # Return empty DataFrame with correct schema
        return pd.DataFrame(columns=['symbol', 'bid', 'ask', 'spread', 'spread_pct', 'timestamp'])


def display_bid_ask_summary(df):
    """
    Display summary statistics for bid/ask data.
    
    Args:
        df: DataFrame containing bid/ask information
    """
    if df is None or df.empty:
        print("\nNo bid/ask data to display.")
        return
    
    print("\n" + "=" * 80)
    print("BID/ASK SUMMARY")
    print("=" * 80)
    print(f"Total Instruments: {len(df)}")
    print(f"\nSpread Statistics:")
    print(f"  Average Spread: ${df['spread'].mean():.4f}")
    print(f"  Median Spread:  ${df['spread'].median():.4f}")
    print(f"  Min Spread:     ${df['spread'].min():.4f}")
    print(f"  Max Spread:     ${df['spread'].max():.4f}")
    print(f"\nSpread % Statistics:")
    print(f"  Average Spread %: {df['spread_pct'].mean():.4f}%")
    print(f"  Median Spread %:  {df['spread_pct'].median():.4f}%")
    print(f"  Min Spread %:     {df['spread_pct'].min():.4f}%")
    print(f"  Max Spread %:     {df['spread_pct'].max():.4f}%")
    
    # Show top 5 widest spreads
    print(f"\nTop 5 Widest Spreads:")
    top_spreads = df.nlargest(5, 'spread_pct')[['symbol', 'bid', 'ask', 'spread', 'spread_pct']]
    print(top_spreads.to_string(index=False))
    
    # Show top 5 tightest spreads
    print(f"\nTop 5 Tightest Spreads:")
    tight_spreads = df.nsmallest(5, 'spread_pct')[['symbol', 'bid', 'ask', 'spread', 'spread_pct']]
    print(tight_spreads.to_string(index=False))
    
    print("=" * 80)


if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Fetch bid/ask prices for crypto instruments from Hyperliquid',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--symbols',
        nargs='+',
        help='List of symbols to fetch (e.g., BTC/USDC:USDC ETH/USDC:USDC)'
    )
    parser.add_argument(
        '--csv',
        type=str,
        help='Save results to CSV file'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Fetch bid/ask for all active markets'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("HYPERLIQUID BID/ASK FETCHER")
    print("=" * 80)
    
    # Determine which symbols to fetch
    if args.all:
        symbols = None  # Will fetch all active markets
    elif args.symbols:
        symbols = args.symbols
    else:
        # Default to major cryptocurrencies
        symbols = [
            'BTC/USDC:USDC',
            'ETH/USDC:USDC',
            'SOL/USDC:USDC',
            'ARB/USDC:USDC',
            'AVAX/USDC:USDC'
        ]
        print(f"\nNo symbols specified, using defaults: {', '.join(symbols)}")
    
    # Fetch bid/ask data
    df = get_bid_ask(symbols)
    
    # Display summary
    display_bid_ask_summary(df)
    
    # Save to CSV if requested
    if args.csv and df is not None and not df.empty:
        df.to_csv(args.csv, index=False)
        print(f"\nBid/ask data saved to {args.csv}")
    
    print("\nDone!")
