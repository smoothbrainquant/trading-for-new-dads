"""
Send limit orders based on bid/ask prices.

For a list of trades {symbol: amount}, this script:
1. Gets bid/ask prices for each symbol
2. Submits limit orders:
   - Buy orders (positive amount) at the BID price
   - Sell orders (negative amount) at the ASK/OFFER price
"""

import argparse
import os
from typing import Dict
from get_bid_ask import get_bid_ask
from ccxt_make_order import ccxt_make_order


def send_limit_orders(trades: Dict[str, float], dry_run: bool = True):
    """
    Send limit orders based on bid/ask prices.
    
    For buy orders (positive amount): places limit order at the bid price
    For sell orders (negative amount): places limit order at the ask/offer price
    
    Args:
        trades: Dictionary mapping symbol to notional amount
                - Positive amount = buy at bid
                - Negative amount = sell at ask
                Example: {
                    'BTC/USDC:USDC': 100,    # Buy $100 at bid
                    'ETH/USDC:USDC': -50     # Sell $50 at ask
                }
        dry_run: If True, only prints orders without executing (default: True)
        
    Returns:
        list: List of order results (empty if dry_run=True)
    """
    if not trades:
        print("\nNo trades to execute.")
        return []
    
    # Extract symbols from trades
    symbols = list(trades.keys())
    
    print("=" * 80)
    print("LIMIT ORDER SUBMISSION BASED ON BID/ASK")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE TRADING'}")
    print(f"Total trades: {len(trades)}")
    print("=" * 80)
    
    # Step 1: Get bid/ask prices for all symbols
    print(f"\n[1/2] Fetching bid/ask prices for {len(symbols)} symbols...")
    print("-" * 80)
    
    bid_ask_df = get_bid_ask(symbols)
    
    if bid_ask_df is None or bid_ask_df.empty:
        print("\n✗ Error: Could not fetch bid/ask prices")
        return []
    
    # Convert DataFrame to dictionary for easy lookup
    bid_ask_dict = {}
    for _, row in bid_ask_df.iterrows():
        bid_ask_dict[row['symbol']] = {
            'bid': row['bid'],
            'ask': row['ask'],
            'spread': row['spread'],
            'spread_pct': row['spread_pct']
        }
    
    # Step 2: Place limit orders
    print(f"\n[2/2] Placing limit orders...")
    print("-" * 80)
    
    orders = []
    
    for symbol, notional_amount in trades.items():
        # Skip if amount is zero
        if notional_amount == 0:
            print(f"\n{symbol}: SKIP (amount is zero)")
            continue
        
        # Check if we have bid/ask data for this symbol
        if symbol not in bid_ask_dict:
            print(f"\n{symbol}: ERROR - No bid/ask data available")
            continue
        
        bid = bid_ask_dict[symbol]['bid']
        ask = bid_ask_dict[symbol]['ask']
        spread = bid_ask_dict[symbol]['spread']
        spread_pct = bid_ask_dict[symbol]['spread_pct']
        
        # Determine side and price
        if notional_amount > 0:
            # Buy order - place at BID price
            side = 'buy'
            price = bid
            abs_amount = notional_amount
            price_type = "BID"
        else:
            # Sell order - place at ASK price
            side = 'sell'
            price = ask
            abs_amount = abs(notional_amount)
            price_type = "ASK"
        
        print(f"\n{symbol}:")
        print(f"  Side:           {side.upper()}")
        print(f"  Notional:       ${abs_amount:,.2f}")
        print(f"  Bid:            ${bid:,.2f}")
        print(f"  Ask:            ${ask:,.2f}")
        print(f"  Spread:         ${spread:.4f} ({spread_pct:.4f}%)")
        print(f"  Order Price:    ${price:,.2f} ({price_type})")
        print(f"  Order Quantity: {abs_amount / price:.6f}")
        
        if dry_run:
            print(f"  Status:         [DRY RUN] Would place {side.upper()} limit order at ${price:,.2f}")
        else:
            try:
                # Place limit order
                order = ccxt_make_order(
                    symbol=symbol,
                    notional_amount=abs_amount,
                    side=side,
                    order_type='limit',
                    price=price
                )
                orders.append(order)
                print(f"  Status:         ✓ Limit order placed successfully")
                print(f"  Order ID:       {order.get('id', 'N/A')}")
            except Exception as e:
                print(f"  Status:         ✗ Error: {str(e)}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    buy_count = sum(1 for amount in trades.values() if amount > 0)
    sell_count = sum(1 for amount in trades.values() if amount < 0)
    buy_total = sum(amount for amount in trades.values() if amount > 0)
    sell_total = sum(abs(amount) for amount in trades.values() if amount < 0)
    
    print(f"Buy orders:  {buy_count} (total: ${buy_total:,.2f})")
    print(f"Sell orders: {sell_count} (total: ${sell_total:,.2f})")
    
    if dry_run:
        print("\n" + "=" * 80)
        print("NOTE: Running in DRY RUN mode. No actual orders were placed.")
        print("To execute live orders, run with --live flag")
        print("=" * 80)
    else:
        print(f"\nOrders executed: {len(orders)}")
    
    return orders


def parse_trades_from_args(trade_args):
    """
    Parse trades from command line arguments.
    
    Args:
        trade_args: List of strings in format "SYMBOL:AMOUNT"
                   Example: ["BTC/USDC:USDC:100", "ETH/USDC:USDC:-50"]
    
    Returns:
        dict: Dictionary mapping symbols to amounts
    """
    trades = {}
    
    for trade_str in trade_args:
        try:
            # Split by last colon to handle symbol format with colons
            parts = trade_str.rsplit(':', 1)
            if len(parts) != 2:
                print(f"Warning: Invalid trade format '{trade_str}'. Expected SYMBOL:AMOUNT")
                continue
            
            symbol = parts[0]
            amount = float(parts[1])
            trades[symbol] = amount
            
        except ValueError as e:
            print(f"Warning: Could not parse amount in '{trade_str}': {e}")
            continue
    
    return trades


def main():
    """
    Command-line interface for sending limit orders based on bid/ask.
    """
    parser = argparse.ArgumentParser(
        description='Send limit orders based on bid/ask prices',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run: Buy $100 BTC at bid, sell $50 ETH at ask
  python3 send_limit_orders.py --trades "BTC/USDC:USDC:100" "ETH/USDC:USDC:-50"
  
  # Live: Buy $200 SOL at bid
  python3 send_limit_orders.py --trades "SOL/USDC:USDC:200" --live
  
  # Multiple trades (dry run)
  python3 send_limit_orders.py --trades \\
    "BTC/USDC:USDC:100" \\
    "ETH/USDC:USDC:-50" \\
    "SOL/USDC:USDC:75" \\
    "ARB/USDC:USDC:-25"

Trade Format:
  SYMBOL:AMOUNT
  - Positive amount = BUY at bid price
  - Negative amount = SELL at ask price
  
Environment Variables Required (for live trading):
  HL_API: Your Hyperliquid API key (wallet address)
  HL_SECRET: Your Hyperliquid secret key
        """
    )
    
    parser.add_argument(
        '--trades',
        nargs='+',
        required=True,
        help='List of trades in format SYMBOL:AMOUNT (e.g., "BTC/USDC:USDC:100" for buy, "ETH/USDC:USDC:-50" for sell)'
    )
    parser.add_argument(
        '--live',
        action='store_true',
        help='Execute live orders (default is dry-run mode)'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Show verbose output'
    )
    
    args = parser.parse_args()
    
    # Parse trades
    trades = parse_trades_from_args(args.trades)
    
    if not trades:
        print("\n✗ Error: No valid trades provided")
        parser.print_help()
        exit(1)
    
    # Check for API credentials if live mode
    if not args.live:
        dry_run = True
    else:
        api_key = os.getenv('HL_API')
        secret_key = os.getenv('HL_SECRET')
        
        if not api_key or not secret_key:
            print("\n✗ Error: Missing API credentials for live trading")
            print("\nPlease set the following environment variables:")
            print("  export HL_API='your_api_key'")
            print("  export HL_SECRET='your_secret_key'")
            print("\nOr run in dry-run mode (without --live flag)")
            exit(1)
        
        dry_run = False
    
    try:
        # Send limit orders
        orders = send_limit_orders(trades, dry_run=dry_run)
        
        # Print full details if verbose
        if args.verbose and orders:
            print("\nFull Order Details:")
            from pprint import pprint
            for order in orders:
                pprint(order)
                print()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
