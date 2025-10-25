"""
Move all existing limit orders to best bid/ask prices.

For buy orders: moves to best bid price
For sell orders: moves to best ask price
"""

import ccxt
import os
import argparse
from typing import List, Dict
from get_bid_ask import get_bid_ask
from modify_order import modify_order


def get_all_open_orders():
    """
    Fetch all open orders from Hyperliquid exchange.
    
    Returns:
        list: List of open orders
    """
    # Get API credentials from environment variables
    api_key = os.getenv('HL_API')
    secret_key = os.getenv('HL_SECRET')
    
    if not api_key or not secret_key:
        raise ValueError("Missing required environment variables: HL_API and/or HL_SECRET")
    
    # Initialize Hyperliquid exchange with authentication
    exchange = ccxt.hyperliquid({
        'privateKey': secret_key,
        'walletAddress': api_key,
        'enableRateLimit': True,
    })
    
    try:
        # Fetch all open orders (no symbol specified = all symbols)
        print("\nFetching all open orders...")
        open_orders = exchange.fetch_open_orders()
        
        return open_orders
        
    except Exception as e:
        print(f"\n✗ Error fetching open orders: {str(e)}")
        raise


def move_orders_to_best_prices(dry_run: bool = True, verbose: bool = False):
    """
    Move all existing limit orders to best bid/ask prices.
    
    Buy orders are moved to the best bid price.
    Sell orders are moved to the best ask price.
    
    Args:
        dry_run: If True, only prints changes without executing (default: True)
        verbose: If True, shows detailed order information
        
    Returns:
        dict: Summary of orders processed and modified
    """
    print("=" * 80)
    print("MOVE LIMIT ORDERS TO BEST BID/ASK")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE TRADING'}")
    print("=" * 80)
    
    # Step 1: Fetch all open orders
    print(f"\n[1/3] Fetching all open orders...")
    print("-" * 80)
    
    try:
        open_orders = get_all_open_orders()
    except Exception as e:
        print(f"\n✗ Failed to fetch orders: {e}")
        return {'success': False, 'error': str(e)}
    
    if not open_orders:
        print("\nNo open orders found.")
        return {'success': True, 'total_orders': 0, 'modified_orders': 0}
    
    print(f"\nFound {len(open_orders)} open order(s)")
    
    # Display current orders
    print("\nCurrent open orders:")
    for i, order in enumerate(open_orders, 1):
        print(f"  {i}. {order.get('symbol', 'N/A'):20s} | "
              f"{(order.get('side') or 'N/A').upper():4s} | "
              f"Price: ${order.get('price', 0):>12,.2f} | "
              f"Amount: {order.get('amount', 0):>12.6f} | "
              f"ID: {order.get('id', 'N/A')}")
    
    # Step 2: Get bid/ask prices for all symbols in the orders
    print(f"\n[2/3] Fetching bid/ask prices...")
    print("-" * 80)
    
    # Extract unique symbols from orders
    symbols = list(set(order['symbol'] for order in open_orders if order.get('symbol')))
    
    try:
        bid_ask_df = get_bid_ask(symbols)
    except Exception as e:
        print(f"\n✗ Failed to fetch bid/ask prices: {e}")
        return {'success': False, 'error': str(e)}
    
    if bid_ask_df is None or bid_ask_df.empty:
        print("\n✗ Error: Could not fetch bid/ask prices")
        return {'success': False, 'error': 'No bid/ask data available'}
    
    # Convert DataFrame to dictionary for easy lookup
    bid_ask_dict = {}
    for _, row in bid_ask_df.iterrows():
        bid_ask_dict[row['symbol']] = {
            'bid': row['bid'],
            'ask': row['ask'],
            'spread': row['spread'],
            'spread_pct': row['spread_pct']
        }
    
    # Step 3: Modify orders to best bid/ask
    print(f"\n[3/3] Moving orders to best bid/ask prices...")
    print("-" * 80)
    
    modified_count = 0
    skipped_count = 0
    error_count = 0
    
    for order in open_orders:
        order_id = order.get('id')
        symbol = order.get('symbol')
        side = order.get('side', '').lower()
        current_price = order.get('price')
        amount = order.get('amount')
        
        print(f"\n{symbol} (Order ID: {order_id}):")
        print(f"  Side:          {side.upper()}")
        print(f"  Current Price: ${current_price:,.8f}")
        print(f"  Amount:        {amount:.6f}")
        
        # Check if we have bid/ask data for this symbol
        if symbol not in bid_ask_dict:
            print(f"  Status:        ✗ SKIP - No bid/ask data available")
            skipped_count += 1
            continue
        
        bid = bid_ask_dict[symbol]['bid']
        ask = bid_ask_dict[symbol]['ask']
        spread = bid_ask_dict[symbol]['spread']
        spread_pct = bid_ask_dict[symbol]['spread_pct']
        
        print(f"  Current Bid:   ${bid:,.8f}")
        print(f"  Current Ask:   ${ask:,.8f}")
        print(f"  Spread:        ${spread:.8f} ({spread_pct:.4f}%)")
        
        # Determine target price based on side
        if side == 'buy':
            target_price = bid
            price_type = "BID"
        elif side == 'sell':
            target_price = ask
            price_type = "ASK"
        else:
            print(f"  Status:        ✗ SKIP - Unknown side '{side}'")
            skipped_count += 1
            continue
        
        print(f"  Target Price:  ${target_price:,.8f} ({price_type})")
        
        # Check if price needs to be modified (use 0.1% tolerance)
        price_diff_pct = abs((current_price - target_price) / target_price * 100) if target_price > 0 else 0
        if price_diff_pct < 0.1:  # 0.1% tolerance
            print(f"  Status:        → SKIP - Already at {price_type} price (within 0.1%)")
            skipped_count += 1
            continue
        
        # Calculate price change
        price_change = target_price - current_price
        price_change_pct = (price_change / current_price * 100) if current_price > 0 else 0
        
        print(f"  Price Change:  ${price_change:+,.2f} ({price_change_pct:+.2f}%)")
        
        if dry_run:
            print(f"  Status:        [DRY RUN] Would modify to ${target_price:,.2f}")
            modified_count += 1
        else:
            try:
                # Modify the order to the new price
                modified_order = modify_order(
                    order_id=order_id,
                    symbol=symbol,
                    new_price=target_price,
                    new_amount=None  # Keep same amount
                )
                print(f"  Status:        ✓ Modified to ${target_price:,.2f}")
                modified_count += 1
                
                if verbose:
                    print(f"  New Order ID:  {modified_order.get('id', 'N/A')}")
                
            except Exception as e:
                print(f"  Status:        ✗ Error: {str(e)}")
                error_count += 1
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total orders:    {len(open_orders)}")
    print(f"Modified:        {modified_count}")
    print(f"Skipped:         {skipped_count}")
    print(f"Errors:          {error_count}")
    
    if dry_run:
        print("\n" + "=" * 80)
        print("NOTE: Running in DRY RUN mode. No actual modifications were made.")
        print("To execute live modifications, run with --live flag")
        print("=" * 80)
    
    return {
        'success': True,
        'total_orders': len(open_orders),
        'modified_orders': modified_count,
        'skipped_orders': skipped_count,
        'error_orders': error_count
    }


def main():
    """
    Command-line interface for moving limit orders to best bid/ask.
    """
    parser = argparse.ArgumentParser(
        description='Move all existing limit orders to best bid/ask prices',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run: Show what changes would be made
  python3 move_limits.py
  
  # Live: Actually modify the orders
  python3 move_limits.py --live
  
  # Live with verbose output
  python3 move_limits.py --live --verbose

How it works:
  - Buy orders are moved to the best BID price
  - Sell orders are moved to the best ASK price
  - Orders already at the target price are skipped
  
Environment Variables Required (for live trading):
  HL_API: Your Hyperliquid API key (wallet address)
  HL_SECRET: Your Hyperliquid secret key
        """
    )
    
    parser.add_argument(
        '--live',
        action='store_true',
        help='Execute live order modifications (default is dry-run mode)'
    )
    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        help='Show verbose output with detailed order information'
    )
    
    args = parser.parse_args()
    
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
        # Move orders to best bid/ask
        result = move_orders_to_best_prices(dry_run=dry_run, verbose=args.verbose)
        
        if not result.get('success'):
            print(f"\n✗ Operation failed: {result.get('error', 'Unknown error')}")
            exit(1)
        
        print("\n✓ Operation completed successfully!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        if args.verbose:
            traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
