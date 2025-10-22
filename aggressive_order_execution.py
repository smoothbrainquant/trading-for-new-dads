"""
Aggressive Order Execution with Spread Crossing Strategy

For a collection of orders {symbol: size}:
1. First send limit orders at best bid/ask
2. Wait 10 seconds
3. Check if orders are filled
4. Iterate through unfilled orders, moving them incrementally towards crossing
5. Finally, if still on best bid/ask with no fills, complete by crossing the spread

This strategy balances between getting better prices (limit orders) and ensuring fills (market orders).
"""

import argparse
import os
import time
import ccxt
from typing import Dict, List, Optional
from get_bid_ask import get_bid_ask
from ccxt_make_order import ccxt_make_order
from modify_order import modify_order


def get_exchange():
    """
    Initialize and return Hyperliquid exchange instance.
    
    Returns:
        ccxt.Exchange: Configured Hyperliquid exchange
    """
    api_key = os.getenv('HL_API')
    secret_key = os.getenv('HL_SECRET')
    
    if not api_key or not secret_key:
        raise ValueError("Missing required environment variables: HL_API and/or HL_SECRET")
    
    return ccxt.hyperliquid({
        'privateKey': secret_key,
        'walletAddress': api_key,
        'enableRateLimit': True,
    })


def check_order_fills(exchange, order_ids: Dict[str, str]) -> Dict[str, dict]:
    """
    Check fill status of multiple orders.
    
    Args:
        exchange: ccxt exchange instance
        order_ids: Dictionary mapping symbol to order_id
        
    Returns:
        Dict mapping symbol to order info (with filled/remaining amounts)
    """
    order_status = {}
    
    for symbol, order_id in order_ids.items():
        try:
            order = exchange.fetch_order(order_id, symbol)
            filled = order.get('filled', 0)
            remaining = order.get('remaining', 0)
            status = order.get('status', 'unknown')
            
            order_status[symbol] = {
                'id': order_id,
                'filled': filled,
                'remaining': remaining,
                'status': status,
                'price': order.get('price'),
                'side': order.get('side'),
                'amount': order.get('amount')
            }
            
        except Exception as e:
            print(f"  Warning: Could not fetch order {order_id} for {symbol}: {e}")
            order_status[symbol] = {
                'id': order_id,
                'error': str(e)
            }
    
    return order_status


def move_order_incrementally(exchange, symbol: str, order_info: dict, 
                             bid_ask_dict: dict, increment_ticks: int = 5) -> Optional[dict]:
    """
    Move an order to the best bid/ask price.
    
    For buy orders: move to current best bid
    For sell orders: move to current best ask
    
    Args:
        exchange: ccxt exchange instance
        symbol: Trading symbol
        order_info: Current order information
        bid_ask_dict: Dictionary with current bid/ask prices
        increment_ticks: Unused (kept for API compatibility)
        
    Returns:
        Modified order info or None if error
    """
    try:
        side = order_info['side']
        current_price = order_info['price']
        bid = bid_ask_dict[symbol]['bid']
        ask = bid_ask_dict[symbol]['ask']
        
        # Always move to best bid/ask
        if side == 'buy':
            # Move buy order to best bid
            new_price = bid
            target = 'BID'
        else:  # sell
            # Move sell order to best ask
            new_price = ask
            target = 'ASK'
        
        # Don't modify if already at target price
        price_diff = abs(new_price - current_price)
        if price_diff < 0.000001:  # Essentially zero difference
            print(f"  {symbol}: Already at best {target}, skipping")
            return order_info
        
        print(f"  {symbol}: Moving {side.upper()} order from ${current_price:.6f} to ${new_price:.6f} (BEST {target})")
        
        # Modify the order
        modified_order = modify_order(
            order_id=order_info['id'],
            symbol=symbol,
            new_price=new_price,
            new_amount=None  # Keep same amount
        )
        
        return {
            'id': modified_order.get('id'),
            'filled': modified_order.get('filled', 0),
            'remaining': modified_order.get('remaining', 0),
            'status': modified_order.get('status'),
            'price': new_price,
            'side': side,
            'amount': modified_order.get('amount')
        }
        
    except Exception as e:
        print(f"  {symbol}: Error moving order: {e}")
        return None


def cross_spread_with_market_order(exchange, symbol: str, order_info: dict, 
                                   notional_amount: float) -> Optional[dict]:
    """
    Cross the spread by placing a market order for the remaining amount.
    
    Args:
        exchange: ccxt exchange instance
        symbol: Trading symbol
        order_info: Current order information
        notional_amount: Original notional amount to trade
        
    Returns:
        Market order info or None if error
    """
    try:
        side = order_info['side']
        remaining = order_info.get('remaining', 0)
        
        if remaining <= 0:
            print(f"  {symbol}: No remaining amount to fill")
            return None
        
        # Calculate remaining notional based on current price
        price = order_info.get('price', 0)
        remaining_notional = remaining * price
        
        print(f"  {symbol}: Crossing spread with MARKET {side.upper()} order")
        print(f"           Remaining: {remaining:.6f} (~${remaining_notional:.2f})")
        
        # Cancel the existing limit order first
        try:
            exchange.cancel_order(order_info['id'], symbol)
            print(f"  {symbol}: Cancelled limit order {order_info['id']}")
        except Exception as e:
            print(f"  {symbol}: Warning - could not cancel order: {e}")
        
        # Place market order for remaining amount
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker['last']
        
        market_order = exchange.create_order(
            symbol=symbol,
            type='market',
            side=side,
            amount=remaining,
            price=current_price
        )
        
        print(f"  {symbol}: ✓ Market order placed - ID: {market_order.get('id')}")
        
        return market_order
        
    except Exception as e:
        print(f"  {symbol}: Error placing market order: {e}")
        return None


def aggressive_execute_orders(
    trades: Dict[str, float],
    wait_time: int = 10,
    max_iterations: int = 3,
    increment_ticks: int = 5,
    dry_run: bool = True
):
    """
    Aggressively execute a collection of orders with spread crossing.
    
    Strategy:
    1. Send limit orders at best bid/ask
    2. Wait specified time
    3. Check fills and move unfilled orders to best bid/ask
    4. Repeat moving process
    5. Finally cross spread with market orders for any remaining
    
    Args:
        trades: Dictionary mapping symbol to notional amount
                Positive = buy, Negative = sell
                Example: {'BTC/USDC:USDC': 100, 'ETH/USDC:USDC': -50}
        wait_time: Seconds to wait after initial orders (default: 10)
        max_iterations: Maximum iterations to move orders (default: 3)
        increment_ticks: Unused (kept for API compatibility)
        dry_run: If True, only prints actions without executing
        
    Returns:
        dict: Summary of execution results
    """
    print("=" * 80)
    print("AGGRESSIVE ORDER EXECUTION WITH SPREAD CROSSING")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE TRADING'}")
    print(f"Wait time: {wait_time}s")
    print(f"Max iterations: {max_iterations}")
    print(f"Strategy: Always move unfilled orders to best bid/ask")
    print("=" * 80)
    
    if not trades:
        print("\nNo trades to execute.")
        return {'success': False, 'error': 'No trades provided'}
    
    # Initialize exchange (only needed for live trading)
    exchange = None
    if not dry_run:
        try:
            exchange = get_exchange()
        except Exception as e:
            print(f"\n✗ Failed to initialize exchange: {e}")
            return {'success': False, 'error': str(e)}
    
    symbols = list(trades.keys())
    
    # STEP 1: Get current bid/ask prices
    print(f"\n[1/5] Fetching bid/ask prices for {len(symbols)} symbols...")
    print("-" * 80)
    
    try:
        bid_ask_df = get_bid_ask(symbols)
    except Exception as e:
        print(f"\n✗ Failed to fetch bid/ask prices: {e}")
        return {'success': False, 'error': str(e)}
    
    if bid_ask_df is None or bid_ask_df.empty:
        print("\n✗ Error: Could not fetch bid/ask prices")
        return {'success': False, 'error': 'No bid/ask data'}
    
    # Convert to dict for easy lookup
    bid_ask_dict = {}
    for _, row in bid_ask_df.iterrows():
        bid_ask_dict[row['symbol']] = {
            'bid': row['bid'],
            'ask': row['ask'],
            'spread': row['spread'],
            'spread_pct': row['spread_pct']
        }
    
    # STEP 2: Send initial limit orders
    print(f"\n[2/5] Sending initial limit orders at best bid/ask...")
    print("-" * 80)
    
    order_ids = {}  # Track order IDs for each symbol
    
    for symbol, notional_amount in trades.items():
        if notional_amount == 0:
            print(f"{symbol}: SKIP (amount is zero)")
            continue
        
        if symbol not in bid_ask_dict:
            print(f"{symbol}: ERROR - No bid/ask data")
            continue
        
        bid = bid_ask_dict[symbol]['bid']
        ask = bid_ask_dict[symbol]['ask']
        side = 'buy' if notional_amount > 0 else 'sell'
        price = bid if side == 'buy' else ask
        abs_amount = abs(notional_amount)
        
        print(f"\n{symbol}:")
        print(f"  Side:        {side.upper()}")
        print(f"  Notional:    ${abs_amount:,.2f}")
        print(f"  Bid:         ${bid:,.4f}")
        print(f"  Ask:         ${ask:,.4f}")
        print(f"  Order Price: ${price:,.4f}")
        
        if dry_run:
            print(f"  Status:      [DRY RUN] Would place {side.upper()} limit order")
            order_ids[symbol] = f"DRY_RUN_{symbol}"
        else:
            try:
                order = ccxt_make_order(
                    symbol=symbol,
                    notional_amount=abs_amount,
                    side=side,
                    order_type='limit',
                    price=price
                )
                order_ids[symbol] = order.get('id')
                print(f"  Status:      ✓ Order placed - ID: {order_ids[symbol]}")
            except Exception as e:
                print(f"  Status:      ✗ Error: {e}")
    
    if not order_ids:
        print("\n✗ No orders were placed")
        return {'success': False, 'error': 'No orders placed'}
    
    # STEP 3: Wait
    print(f"\n[3/5] Waiting {wait_time} seconds for fills...")
    print("-" * 80)
    
    if not dry_run:
        time.sleep(wait_time)
    else:
        print(f"[DRY RUN] Simulating {wait_time}s wait")
    
    print("✓ Wait complete")
    
    # STEP 4: Iterate and move orders to best bid/ask
    print(f"\n[4/5] Checking fills and moving unfilled orders to best bid/ask...")
    print("-" * 80)
    
    filled_symbols = set()
    unfilled_symbols = set(order_ids.keys())
    
    for iteration in range(max_iterations):
        print(f"\nIteration {iteration + 1}/{max_iterations}:")
        print("-" * 40)
        
        if not dry_run:
            # Check order status
            order_status = check_order_fills(exchange, order_ids)
            
            # Identify filled vs unfilled
            for symbol, status in order_status.items():
                if 'error' in status:
                    continue
                
                if status.get('status') in ['closed', 'filled']:
                    filled_symbols.add(symbol)
                    unfilled_symbols.discard(symbol)
                    print(f"  {symbol}: ✓ FILLED")
                elif status.get('remaining', 0) > 0:
                    # Move order to best bid/ask
                    print(f"  {symbol}: Partially filled - {status.get('filled', 0):.6f} / {status.get('amount', 0):.6f}")
                    
                    # Update bid/ask for current iteration
                    current_bid_ask = get_bid_ask([symbol])
                    if current_bid_ask is not None and not current_bid_ask.empty:
                        for _, row in current_bid_ask.iterrows():
                            bid_ask_dict[row['symbol']] = {
                                'bid': row['bid'],
                                'ask': row['ask'],
                                'spread': row['spread'],
                                'spread_pct': row['spread_pct']
                            }
                    
                    new_order_info = move_order_incrementally(
                        exchange, symbol, status, bid_ask_dict, increment_ticks
                    )
                    
                    if new_order_info and new_order_info.get('id'):
                        order_ids[symbol] = new_order_info['id']
        else:
            print("[DRY RUN] Would check fills and move unfilled orders")
            unfilled_symbols = set(list(order_ids.keys())[:len(order_ids)//2])  # Simulate some fills
        
        # Wait a bit between iterations
        if iteration < max_iterations - 1:
            wait_between = 5
            print(f"\nWaiting {wait_between}s before next iteration...")
            if not dry_run:
                time.sleep(wait_between)
    
    # STEP 5: Cross spread for remaining unfilled orders
    print(f"\n[5/5] Crossing spread for remaining unfilled orders...")
    print("-" * 80)
    
    if not dry_run and unfilled_symbols:
        # Refresh bid/ask one more time
        try:
            final_bid_ask = get_bid_ask(list(unfilled_symbols))
            if final_bid_ask is not None and not final_bid_ask.empty:
                for _, row in final_bid_ask.iterrows():
                    bid_ask_dict[row['symbol']] = {
                        'bid': row['bid'],
                        'ask': row['ask'],
                        'spread': row['spread'],
                        'spread_pct': row['spread_pct']
                    }
        except Exception as e:
            print(f"Warning: Could not refresh bid/ask: {e}")
        
        # Check final status and cross spread if needed
        final_status = check_order_fills(exchange, {s: order_ids[s] for s in unfilled_symbols})
        
        for symbol in unfilled_symbols:
            if symbol not in final_status or 'error' in final_status[symbol]:
                continue
            
            status = final_status[symbol]
            
            remaining = status.get('remaining', 0)
            side = status.get('side')
            
            # After all iterations, if still unfilled, cross the spread with market order
            if remaining > 0:
                print(f"\n{symbol}: Still unfilled with {remaining:.6f} remaining after {max_iterations} iterations")
                print(f"          Crossing spread with market order...")
                
                market_order = cross_spread_with_market_order(
                    exchange, symbol, status, trades[symbol]
                )
                
                if market_order:
                    filled_symbols.add(symbol)
            else:
                print(f"\n{symbol}: ✓ Order filled during iterations")
                filled_symbols.add(symbol)
    elif dry_run and unfilled_symbols:
        print(f"[DRY RUN] Would cross spread for {len(unfilled_symbols)} unfilled orders:")
        for symbol in unfilled_symbols:
            print(f"  {symbol}: Would place market order")
    else:
        print("✓ All orders filled, no need to cross spread")
    
    # Summary
    print("\n" + "=" * 80)
    print("EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Total trades:        {len(trades)}")
    print(f"Orders placed:       {len(order_ids)}")
    print(f"Filled:              {len(filled_symbols)}")
    print(f"Still open:          {len(unfilled_symbols - filled_symbols)}")
    
    if filled_symbols:
        print(f"\nFilled symbols:")
        for symbol in filled_symbols:
            print(f"  ✓ {symbol}")
    
    remaining = unfilled_symbols - filled_symbols
    if remaining:
        print(f"\nRemaining open orders:")
        for symbol in remaining:
            print(f"  → {symbol}")
    
    if dry_run:
        print("\n" + "=" * 80)
        print("NOTE: Running in DRY RUN mode. No actual orders were placed.")
        print("To execute live orders, run with --live flag")
        print("=" * 80)
    
    return {
        'success': True,
        'total_trades': len(trades),
        'orders_placed': len(order_ids),
        'filled': len(filled_symbols),
        'remaining': len(unfilled_symbols - filled_symbols)
    }


def parse_trades_from_args(trade_args):
    """
    Parse trades from command line arguments.
    
    Args:
        trade_args: List of strings in format "SYMBOL:AMOUNT"
        
    Returns:
        dict: Dictionary mapping symbols to amounts
    """
    trades = {}
    
    for trade_str in trade_args:
        try:
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
    Command-line interface for aggressive order execution.
    """
    parser = argparse.ArgumentParser(
        description='Aggressively execute orders with spread crossing',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run: Buy $100 BTC, sell $50 ETH
  python3 aggressive_order_execution.py --trades "BTC/USDC:USDC:100" "ETH/USDC:USDC:-50"
  
  # Live: Buy $200 SOL with custom parameters
  python3 aggressive_order_execution.py --trades "SOL/USDC:USDC:200" --live --wait 15 --iterations 5
  
  # Multiple trades with faster execution
  python3 aggressive_order_execution.py --trades \\
    "BTC/USDC:USDC:100" \\
    "ETH/USDC:USDC:-50" \\
    "SOL/USDC:USDC:75" \\
    --live --wait 10 --iterations 3

Strategy:
  1. Sends limit orders at best bid (buy) or ask (sell)
  2. Waits specified time for fills
  3. Moves unfilled orders to best bid/ask (refreshed each iteration)
  4. Finally crosses spread with market orders if needed
  
Trade Format:
  SYMBOL:AMOUNT
  - Positive amount = BUY
  - Negative amount = SELL
  
Environment Variables Required (for live trading):
  HL_API: Your Hyperliquid API key (wallet address)
  HL_SECRET: Your Hyperliquid secret key
        """
    )
    
    parser.add_argument(
        '--trades',
        nargs='+',
        required=True,
        help='List of trades in format SYMBOL:AMOUNT'
    )
    parser.add_argument(
        '--live',
        action='store_true',
        help='Execute live orders (default is dry-run mode)'
    )
    parser.add_argument(
        '--wait',
        type=int,
        default=10,
        help='Seconds to wait after initial orders (default: 10)'
    )
    parser.add_argument(
        '--iterations',
        type=int,
        default=3,
        help='Maximum iterations to move orders (default: 3)'
    )
    parser.add_argument(
        '--increment',
        type=int,
        default=5,
        help='[DEPRECATED] Unused - orders always move to best bid/ask'
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
        # Execute orders
        result = aggressive_execute_orders(
            trades=trades,
            wait_time=args.wait,
            max_iterations=args.iterations,
            increment_ticks=args.increment,
            dry_run=dry_run
        )
        
        if not result.get('success'):
            print(f"\n✗ Execution failed: {result.get('error', 'Unknown error')}")
            exit(1)
        
        print("\n✓ Execution completed!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
