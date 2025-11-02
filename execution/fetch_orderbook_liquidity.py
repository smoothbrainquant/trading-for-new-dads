"""
Fetch Top of Book Liquidity from CCXT

This script demonstrates how to fetch order book liquidity data from exchanges
using CCXT. It shows both top-of-book (best bid/ask) and deeper order book levels.

Top of book liquidity includes:
- Best bid price and size
- Best ask price and size
- Bid-ask spread
- Liquidity at top levels
"""

import ccxt
import pandas as pd
from datetime import datetime
from typing import List, Optional, Dict


def fetch_orderbook_liquidity(
    symbols: Optional[List[str]] = None,
    exchange_name: str = "hyperliquid",
    depth: int = 5
) -> pd.DataFrame:
    """
    Fetch order book liquidity for given symbols.
    
    Args:
        symbols: List of trading pairs (e.g., ['BTC/USDC:USDC', 'ETH/USDC:USDC'])
                If None, fetches for top active markets
        exchange_name: Name of the exchange (default: hyperliquid)
        depth: Number of order book levels to fetch (default: 5)
    
    Returns:
        DataFrame with liquidity metrics for each symbol
    """
    # Initialize exchange
    if exchange_name == "hyperliquid":
        exchange = ccxt.hyperliquid({"enableRateLimit": True})
    else:
        exchange_class = getattr(ccxt, exchange_name)
        exchange = exchange_class({"enableRateLimit": True})
    
    # Load markets
    markets = exchange.load_markets()
    
    # If no symbols provided, get top active perpetual markets
    if symbols is None:
        symbols = [
            symbol for symbol, market in markets.items()
            if market.get("active") and market.get("type") == "swap"
        ][:10]  # Limit to top 10 for demo
        print(f"No symbols provided, using top {len(symbols)} active markets")
    
    liquidity_data = []
    
    print(f"\n{'='*100}")
    print(f"FETCHING ORDER BOOK LIQUIDITY - TOP {depth} LEVELS")
    print(f"{'='*100}\n")
    
    for symbol in symbols:
        try:
            # Fetch order book with specified depth
            orderbook = exchange.fetch_order_book(symbol, limit=depth)
            
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                print(f"{symbol:20s} | No order book data available")
                continue
            
            # Extract top of book (best bid/ask)
            best_bid_price = bids[0][0]
            best_bid_size = bids[0][1]
            best_ask_price = asks[0][0]
            best_ask_size = asks[0][1]
            
            # Calculate liquidity metrics
            spread = best_ask_price - best_bid_price
            spread_pct = (spread / best_bid_price * 100) if best_bid_price > 0 else 0
            mid_price = (best_bid_price + best_ask_price) / 2
            
            # Calculate total liquidity at top N levels
            total_bid_liquidity = sum(price * size for price, size in bids)
            total_ask_liquidity = sum(price * size for price, size in asks)
            total_bid_size = sum(size for _, size in bids)
            total_ask_size = sum(size for _, size in asks)
            
            # Average price weighted by size for top N levels
            avg_bid_price = total_bid_liquidity / total_bid_size if total_bid_size > 0 else 0
            avg_ask_price = total_ask_liquidity / total_ask_size if total_ask_size > 0 else 0
            
            liquidity_data.append({
                'symbol': symbol,
                'timestamp': datetime.fromtimestamp(orderbook['timestamp'] / 1000) if orderbook.get('timestamp') else datetime.now(),
                
                # Top of book
                'best_bid_price': best_bid_price,
                'best_bid_size': best_bid_size,
                'best_ask_price': best_ask_price,
                'best_ask_size': best_ask_size,
                
                # Spread metrics
                'mid_price': mid_price,
                'spread': spread,
                'spread_pct': spread_pct,
                
                # Aggregate liquidity (top N levels)
                'total_bid_liquidity_usd': total_bid_liquidity,
                'total_ask_liquidity_usd': total_ask_liquidity,
                'total_bid_size': total_bid_size,
                'total_ask_size': total_ask_size,
                'avg_bid_price': avg_bid_price,
                'avg_ask_price': avg_ask_price,
                
                # Depth levels captured
                'depth_levels': min(len(bids), len(asks)),
            })
            
            # Print summary
            print(f"{symbol:20s} | Mid: ${mid_price:>12,.2f} | "
                  f"Bid: ${best_bid_price:>12,.2f} ({best_bid_size:>8,.3f}) | "
                  f"Ask: ${best_ask_price:>12,.2f} ({best_ask_size:>8,.3f}) | "
                  f"Spread: {spread_pct:.4f}%")
            print(f"{' '*20} | Total Bid Liq: ${total_bid_liquidity:>12,.2f} | "
                  f"Total Ask Liq: ${total_ask_liquidity:>12,.2f}")
            
        except Exception as e:
            print(f"{symbol:20s} | Error: {str(e)}")
            continue
    
    # Create DataFrame
    if liquidity_data:
        df = pd.DataFrame(liquidity_data)
        return df
    else:
        return pd.DataFrame()


def display_liquidity_summary(df: pd.DataFrame):
    """Display summary statistics for order book liquidity."""
    if df is None or df.empty:
        print("\nNo liquidity data to display.")
        return
    
    print(f"\n{'='*100}")
    print("ORDER BOOK LIQUIDITY SUMMARY")
    print(f"{'='*100}")
    print(f"Total Instruments: {len(df)}")
    
    print(f"\nSpread Statistics:")
    print(f"  Average Spread %: {df['spread_pct'].mean():.4f}%")
    print(f"  Median Spread %:  {df['spread_pct'].median():.4f}%")
    print(f"  Min Spread %:     {df['spread_pct'].min():.4f}%")
    print(f"  Max Spread %:     {df['spread_pct'].max():.4f}%")
    
    print(f"\nBid Liquidity (USD):")
    print(f"  Average: ${df['total_bid_liquidity_usd'].mean():,.2f}")
    print(f"  Median:  ${df['total_bid_liquidity_usd'].median():,.2f}")
    print(f"  Min:     ${df['total_bid_liquidity_usd'].min():,.2f}")
    print(f"  Max:     ${df['total_bid_liquidity_usd'].max():,.2f}")
    
    print(f"\nAsk Liquidity (USD):")
    print(f"  Average: ${df['total_ask_liquidity_usd'].mean():,.2f}")
    print(f"  Median:  ${df['total_ask_liquidity_usd'].median():,.2f}")
    print(f"  Min:     ${df['total_ask_liquidity_usd'].min():,.2f}")
    print(f"  Max:     ${df['total_ask_liquidity_usd'].max():,.2f}")
    
    # Show instruments by liquidity
    print(f"\nTop 5 Most Liquid (by total bid+ask):")
    df['total_liquidity'] = df['total_bid_liquidity_usd'] + df['total_ask_liquidity_usd']
    top_liquid = df.nlargest(5, 'total_liquidity')[
        ['symbol', 'mid_price', 'spread_pct', 'total_bid_liquidity_usd', 
         'total_ask_liquidity_usd', 'total_liquidity']
    ]
    print(top_liquid.to_string(index=False))
    
    print(f"\nTop 5 Least Liquid (by total bid+ask):")
    least_liquid = df.nsmallest(5, 'total_liquidity')[
        ['symbol', 'mid_price', 'spread_pct', 'total_bid_liquidity_usd', 
         'total_ask_liquidity_usd', 'total_liquidity']
    ]
    print(least_liquid.to_string(index=False))
    
    print(f"{'='*100}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Fetch order book liquidity from CCXT exchanges",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        help="List of symbols to fetch (e.g., BTC/USDC:USDC ETH/USDC:USDC)"
    )
    parser.add_argument(
        "--exchange",
        type=str,
        default="hyperliquid",
        help="Exchange name (hyperliquid, binance, etc.)"
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=5,
        help="Number of order book levels to fetch"
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="Save results to CSV file"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch for top 10 active markets"
    )
    
    args = parser.parse_args()
    
    print(f"{'='*100}")
    print(f"CCXT ORDER BOOK LIQUIDITY FETCHER")
    print(f"Exchange: {args.exchange.upper()}")
    print(f"{'='*100}")
    
    # Determine symbols to fetch
    if args.all:
        symbols = None
    elif args.symbols:
        symbols = args.symbols
    else:
        # Default to major cryptocurrencies
        symbols = [
            "BTC/USDC:USDC",
            "ETH/USDC:USDC",
            "SOL/USDC:USDC",
        ]
        print(f"\nUsing default symbols: {', '.join(symbols)}")
    
    # Fetch liquidity data
    df = fetch_orderbook_liquidity(
        symbols=symbols,
        exchange_name=args.exchange,
        depth=args.depth
    )
    
    # Display summary
    display_liquidity_summary(df)
    
    # Save to CSV if requested
    if args.csv and not df.empty:
        df.to_csv(args.csv, index=False)
        print(f"Liquidity data saved to {args.csv}")
    
    print("Done!")
