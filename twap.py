import ccxt
import os
import argparse
import time
from pprint import pprint
from datetime import datetime

def ccxt_twap_order(symbol, notional_amount, side, duration_minutes, num_slices, order_type='market', price=None, dry_run=False):
    """
    Execute a TWAP (Time-Weighted Average Price) order on Hyperliquid exchange.
    
    Splits a large order into smaller slices and executes them at regular intervals
    to minimize market impact and achieve a better average execution price.
    
    Args:
        symbol: Trading pair (e.g., 'BTC/USDC:USDC', 'ETH/USDC:USDC')
        notional_amount: Total USD/USDC amount to trade (e.g., 1000 for $1000)
        side: 'buy' or 'sell'
        duration_minutes: Total time period to execute all slices (in minutes)
        num_slices: Number of order slices to split the total order into
        order_type: 'market' or 'limit' (default: 'market')
        price: Price for limit orders (required for limit, ignored for market)
        dry_run: If True, simulates orders without actual execution (default: False)
    
    Requires environment variables:
        HL_API: Hyperliquid API key (wallet address)
        HL_SECRET: Hyperliquid secret key
    
    Returns:
        List of dictionaries containing order responses for each slice
    """
    # Get API credentials from environment variables
    api_key = os.getenv('HL_API')
    secret_key = os.getenv('HL_SECRET')
    
    if not api_key or not secret_key:
        raise ValueError("Missing required environment variables: HL_API and/or HL_SECRET")
    
    # Validate inputs
    side = side.lower()
    if side not in ['buy', 'sell']:
        raise ValueError("Side must be 'buy' or 'sell'")
    
    order_type = order_type.lower()
    if order_type not in ['market', 'limit']:
        raise ValueError("Order type must be 'market' or 'limit'")
    
    if order_type == 'limit' and price is None:
        raise ValueError("Price is required for limit orders")
    
    if notional_amount <= 0:
        raise ValueError("Notional amount must be positive")
    
    if duration_minutes <= 0:
        raise ValueError("Duration must be positive")
    
    if num_slices <= 0:
        raise ValueError("Number of slices must be positive")
    
    # Calculate slice parameters
    slice_notional = notional_amount / num_slices
    interval_seconds = (duration_minutes * 60) / num_slices
    
    # Initialize Hyperliquid exchange with authentication
    exchange = ccxt.hyperliquid({
        'privateKey': secret_key,
        'walletAddress': api_key,
        'enableRateLimit': True,
    })
    
    print(f"\n{'='*80}")
    print(f"TWAP ORDER EXECUTION {'(DRY RUN)' if dry_run else '(LIVE)'}")
    print(f"{'='*80}")
    print(f"Symbol: {symbol}")
    print(f"Side: {side.upper()}")
    print(f"Total Notional: ${notional_amount:,.2f}")
    print(f"Number of Slices: {num_slices}")
    print(f"Slice Size: ${slice_notional:,.2f}")
    print(f"Duration: {duration_minutes} minutes")
    print(f"Interval: {interval_seconds:.1f} seconds between slices")
    print(f"Order Type: {order_type.upper()}")
    if order_type == 'limit':
        print(f"Limit Price: ${price:,.2f}")
    print(f"{'='*80}\n")
    
    # Store all order results
    orders = []
    total_filled_notional = 0
    total_filled_amount = 0
    weighted_avg_price = 0
    
    try:
        # Fetch initial market price
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        print(f"Starting {symbol} price: ${current_price:,.2f}\n")
        
        # Execute each slice
        for slice_num in range(1, num_slices + 1):
            start_time = time.time()
            
            print(f"{'='*80}")
            print(f"SLICE {slice_num}/{num_slices}")
            print(f"{'='*80}")
            print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Fetch current market price for this slice
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # For limit orders, use the specified price, for market use current price
            effective_price = price if order_type == 'limit' else current_price
            
            # Calculate the amount (quantity) for this slice
            amount = slice_notional / effective_price
            
            print(f"Current Price: ${current_price:,.2f}")
            print(f"Slice Notional: ${slice_notional:,.2f}")
            print(f"Slice Quantity: {amount:.6f}")
            
            if dry_run:
                print(f"\n[DRY RUN] Would place {side.upper()} order:")
                print(f"  Symbol: {symbol}")
                print(f"  Type: {order_type.upper()}")
                print(f"  Amount: {amount:.6f}")
                print(f"  Price: ${effective_price:,.2f}")
                print(f"  Notional: ${slice_notional:,.2f}")
                
                # Simulate order response
                order = {
                    'id': f'dry-run-{slice_num}',
                    'symbol': symbol,
                    'type': order_type,
                    'side': side,
                    'amount': amount,
                    'price': effective_price,
                    'cost': slice_notional,
                    'filled': amount,
                    'status': 'closed',
                    'timestamp': int(time.time() * 1000),
                    'dry_run': True
                }
            else:
                # Place the actual order
                print(f"\nPlacing {order_type.upper()} {side.upper()} order...")
                
                if order_type == 'market':
                    order = exchange.create_order(
                        symbol=symbol,
                        type='market',
                        side=side,
                        amount=amount,
                        price=current_price
                    )
                else:  # limit order
                    order = exchange.create_limit_order(
                        symbol=symbol,
                        side=side,
                        amount=amount,
                        price=price
                    )
                
                print("✓ Order placed successfully!")
            
            # Record order details
            orders.append(order)
            
            # Update statistics
            filled_amount = order.get('filled', amount)
            filled_price = order.get('average', effective_price)
            filled_notional = filled_amount * filled_price
            
            total_filled_amount += filled_amount
            total_filled_notional += filled_notional
            
            print(f"\nSlice Results:")
            print(f"  Order ID: {order.get('id', 'N/A')}")
            print(f"  Status: {(order.get('status') or 'N/A').upper()}")
            print(f"  Filled: {filled_amount:.6f}")
            print(f"  Avg Price: ${filled_price:,.2f}")
            print(f"  Cost: ${filled_notional:,.2f}")
            
            # Calculate running TWAP
            if total_filled_amount > 0:
                weighted_avg_price = total_filled_notional / total_filled_amount
                print(f"\nRunning Statistics:")
                print(f"  Total Filled: {total_filled_amount:.6f}")
                print(f"  Total Cost: ${total_filled_notional:,.2f}")
                print(f"  TWAP: ${weighted_avg_price:,.2f}")
            
            # Wait before next slice (except for the last one)
            if slice_num < num_slices:
                elapsed = time.time() - start_time
                wait_time = max(0, interval_seconds - elapsed)
                
                if wait_time > 0:
                    print(f"\nWaiting {wait_time:.1f} seconds until next slice...")
                    time.sleep(wait_time)
            
            print()
        
        # Final summary
        print(f"{'='*80}")
        print("TWAP EXECUTION COMPLETE")
        print(f"{'='*80}")
        print(f"Total Slices Executed: {len(orders)}")
        print(f"Total Filled Amount: {total_filled_amount:.6f}")
        print(f"Total Filled Notional: ${total_filled_notional:,.2f}")
        if total_filled_amount > 0:
            print(f"Time-Weighted Average Price: ${weighted_avg_price:,.2f}")
        print(f"{'='*80}\n")
        
        return orders
        
    except Exception as e:
        print(f"\n✗ Error during TWAP execution: {str(e)}")
        print(f"Executed {len(orders)} out of {num_slices} slices before error")
        raise


def main():
    """
    Command-line interface for TWAP order execution.
    """
    parser = argparse.ArgumentParser(
        description='Execute TWAP (Time-Weighted Average Price) orders on Hyperliquid exchange',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # TWAP order to buy $1000 worth of BTC over 10 minutes in 5 slices
  python3 twap.py --symbol BTC/USDC:USDC --notional 1000 --side buy --duration 10 --slices 5
  
  # TWAP order to sell $500 worth of ETH over 30 minutes in 10 slices
  python3 twap.py --symbol ETH/USDC:USDC --notional 500 --side sell --duration 30 --slices 10
  
  # Dry run TWAP order (no actual execution)
  python3 twap.py --symbol SOL/USDC:USDC --notional 200 --side buy --duration 5 --slices 3 --dry-run
  
  # TWAP limit order with specific price
  python3 twap.py --symbol BTC/USDC:USDC --notional 1000 --side buy --duration 15 --slices 6 --type limit --price 50000

Environment Variables Required:
  HL_API: Your Hyperliquid API key (wallet address)
  HL_SECRET: Your Hyperliquid secret key
        """
    )
    
    parser.add_argument('--symbol', '-s', required=True, 
                        help='Trading pair symbol (e.g., BTC/USDC:USDC, ETH/USDC:USDC)')
    parser.add_argument('--notional', '-n', type=float, required=True,
                        help='Total notional amount in USD/USDC to trade')
    parser.add_argument('--side', '-d', required=True, choices=['buy', 'sell'],
                        help='Order side: buy or sell')
    parser.add_argument('--duration', '-u', type=float, required=True,
                        help='Duration in minutes to execute all slices')
    parser.add_argument('--slices', '-l', type=int, required=True,
                        help='Number of slices to split the order into')
    parser.add_argument('--type', '-t', default='market', choices=['market', 'limit'],
                        help='Order type: market or limit (default: market)')
    parser.add_argument('--price', '-p', type=float, default=None,
                        help='Price for limit orders (required for limit orders)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Simulate orders without actual execution')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show full order details for each slice')
    
    args = parser.parse_args()
    
    try:
        # Execute TWAP order
        orders = ccxt_twap_order(
            symbol=args.symbol,
            notional_amount=args.notional,
            side=args.side,
            duration_minutes=args.duration,
            num_slices=args.slices,
            order_type=args.type,
            price=args.price,
            dry_run=args.dry_run
        )
        
        # Print full details if verbose
        if args.verbose:
            print("\nDetailed Order Information:")
            print("="*80)
            for i, order in enumerate(orders, 1):
                print(f"\nSlice {i}:")
                pprint(order)
        
    except ValueError as e:
        print(f"\n✗ Configuration Error: {e}")
        if "environment variables" in str(e):
            print("\nPlease set the following environment variables:")
            print("  export HL_API='your_api_key'")
            print("  export HL_SECRET='your_secret_key'")
        parser.print_help()
        exit(1)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        exit(1)


if __name__ == "__main__":
    main()
