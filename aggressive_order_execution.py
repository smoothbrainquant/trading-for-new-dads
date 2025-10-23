"""
Aggressive Order Execution with Tick-Based Best Bid/Ask Tracking

For a collection of orders {symbol: size}:
1. Send limit orders at best bid/ask
2. Continuously monitor (tick-based) the market:
   - Poll bid/ask prices every tick_interval seconds
   - If best bid/ask changes, immediately move orders to new best bid/ask
   - Check if orders are filled
3. Continue until orders are filled, max_time is reached, or max_ticks exceeded
4. Finally, if still unfilled after max time, cross the spread with limit orders
   - Buy orders: moved to ASK price (crosses spread)
   - Sell orders: moved to BID price (crosses spread)

This strategy ensures orders stay at the best bid/ask to maximize fill probability
while still getting good prices (better than market orders).
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


def get_all_open_orders(exchange):
    """
    Fetch all open orders from the exchange.
    
    Args:
        exchange: ccxt exchange instance
        
    Returns:
        list: List of open orders
    """
    try:
        open_orders = exchange.fetch_open_orders()
        return open_orders
    except Exception as e:
        print(f"  Warning: Could not fetch open orders: {e}")
        return []


def cancel_all_open_orders(exchange, dry_run=True):
    """
    Cancel all existing open orders.
    
    Args:
        exchange: ccxt exchange instance
        dry_run: If True, only print what would be canceled
        
    Returns:
        int: Number of orders canceled
    """
    try:
        open_orders = get_all_open_orders(exchange)
        
        if not open_orders:
            print("  No existing open orders to cancel")
            return 0
        
        print(f"  Found {len(open_orders)} existing open order(s):")
        for order in open_orders:
            symbol = order.get('symbol', 'N/A')
            side = order.get('side', 'N/A').upper()
            price = order.get('price', 0)
            amount = order.get('amount', 0)
            order_id = order.get('id', 'N/A')
            print(f"    {symbol}: {side} @ ${price:.4f}, Amount: {amount:.6f}, ID: {order_id}")
        
        if dry_run:
            print(f"  [DRY RUN] Would cancel {len(open_orders)} order(s)")
            return len(open_orders)
        
        # Cancel all orders
        canceled = 0
        for order in open_orders:
            try:
                symbol = order.get('symbol')
                order_id = order.get('id')
                exchange.cancel_order(order_id, symbol)
                canceled += 1
                print(f"    ✓ Canceled {symbol} order {order_id}")
            except Exception as e:
                print(f"    ✗ Failed to cancel order {order_id}: {e}")
        
        return canceled
        
    except Exception as e:
        print(f"  Warning: Error canceling orders: {e}")
        return 0


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


def move_order_to_best_bid_ask(exchange, symbol: str, order_info: dict, 
                               bid_ask_dict: dict) -> Optional[dict]:
    """
    Move an order to the current best bid/ask price.
    
    For buy orders: move to current best bid
    For sell orders: move to current best ask
    
    Args:
        exchange: ccxt exchange instance
        symbol: Trading symbol
        order_info: Current order information
        bid_ask_dict: Dictionary with current bid/ask prices
        
    Returns:
        Modified order info or None if error or no change needed
    """
    try:
        side = order_info['side']
        current_price = order_info['price']
        bid = bid_ask_dict[symbol]['bid']
        ask = bid_ask_dict[symbol]['ask']
        
        # Determine target price based on side
        if side == 'buy':
            target_price = bid
            target_name = 'BID'
        else:  # sell
            target_price = ask
            target_name = 'ASK'
        
        # Don't modify if already at target price (within 0.01%)
        if current_price:
            price_diff_pct = abs((target_price - current_price) / current_price * 100)
            if price_diff_pct < 0.01:
                return None  # No change needed
        
        print(f"  {symbol}: Moving {side.upper()} order from ${current_price:.4f} to ${target_price:.4f} (best {target_name})")
        
        # Modify the order to new best bid/ask
        modified_order = modify_order(
            order_id=order_info['id'],
            symbol=symbol,
            new_price=target_price,
            new_amount=None  # Keep same amount
        )
        
        return {
            'id': modified_order.get('id'),
            'filled': modified_order.get('filled', 0),
            'remaining': modified_order.get('remaining', 0),
            'status': modified_order.get('status'),
            'price': target_price,
            'side': side,
            'amount': modified_order.get('amount')
        }
        
    except Exception as e:
        print(f"  {symbol}: Error moving order to best bid/ask: {e}")
        return None


def cross_spread_with_market_order(exchange, symbol: str, order_info: dict, 
                                   bid_ask_dict: dict) -> Optional[dict]:
    """
    Cross the spread by placing a MARKET order for immediate fill.
    Market orders guarantee execution but may have price slippage.
    
    Args:
        exchange: ccxt exchange instance
        symbol: Trading symbol
        order_info: Current order information
        bid_ask_dict: Dictionary with current bid/ask prices (for display only)
        
    Returns:
        New order info or None if error
    """
    try:
        side = order_info['side']
        remaining = order_info.get('remaining', 0)
        
        if remaining <= 0:
            print(f"  {symbol}: No remaining amount to fill")
            return None
        
        old_price = order_info.get('price', 0)
        
        # Get current bid/ask for display purposes
        if symbol in bid_ask_dict:
            bid = bid_ask_dict[symbol]['bid']
            ask = bid_ask_dict[symbol]['ask']
            expected_price = ask if side == 'buy' else bid
            remaining_notional = remaining * expected_price
            print(f"  {symbol}: Crossing spread with MARKET {side.upper()} order")
            print(f"           Expected price: ~${expected_price:.4f} (was ${old_price:.4f})")
            print(f"           Remaining: {remaining:.6f} (~${remaining_notional:.2f})")
        else:
            print(f"  {symbol}: Crossing spread with MARKET {side.upper()} order")
            print(f"           Remaining: {remaining:.6f}")
        
        # Cancel the existing limit order first
        try:
            exchange.cancel_order(order_info['id'], symbol)
            print(f"  {symbol}: ✓ Cancelled limit order {order_info['id']}")
        except Exception as e:
            print(f"  {symbol}: Warning - could not cancel order: {e}")
        
        # Place MARKET order for immediate fill
        new_order = exchange.create_order(
            symbol=symbol,
            type='market',
            side=side,
            amount=remaining
        )
        
        fill_price = new_order.get('average') or new_order.get('price', 0)
        print(f"  {symbol}: ✓ MARKET order FILLED at ~${fill_price:.4f} - ID: {new_order.get('id')}")
        
        return new_order
        
    except Exception as e:
        print(f"  {symbol}: Error placing market order: {e}")
        return None


def aggressive_execute_orders(
    trades: Dict[str, float],
    tick_interval: float = 2.0,
    max_time: int = 60,
    cross_spread_after: bool = True,
    dry_run: bool = True,
    **kwargs  # Accept but ignore legacy parameters
):
    """
    Aggressively execute orders using tick-based best bid/ask tracking.
    
    Strategy:
    1. Send limit orders at best bid/ask
    2. Continuously monitor market (tick-based):
       - Poll bid/ask every tick_interval seconds
       - If best bid/ask changes, immediately move orders to new best bid/ask
       - Check if orders are filled
    3. Continue until orders filled, max_time reached, or all trades complete
    4. Optionally cross spread with limit orders for remaining unfilled
       - Buy orders: moved to ASK price (crosses spread, fills immediately)
       - Sell orders: moved to BID price (crosses spread, fills immediately)
    
    Args:
        trades: Dictionary mapping symbol to notional amount
                Positive = buy, Negative = sell
                Example: {'BTC/USDC:USDC': 100, 'ETH/USDC:USDC': -50}
        tick_interval: Seconds between bid/ask polls (default: 2.0)
        max_time: Maximum seconds to run before crossing spread (default: 60)
        cross_spread_after: If True, cross spread for remaining orders after max_time (default: True)
        dry_run: If True, only prints actions without executing
        
    Returns:
        dict: Summary of execution results
    """
    print("=" * 80)
    print("AGGRESSIVE ORDER EXECUTION - TICK-BASED BID/ASK TRACKING")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE TRADING'}")
    print(f"Tick interval: {tick_interval}s")
    print(f"Max time: {max_time}s")
    print(f"Cross spread after max time: {cross_spread_after}")
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
    
    # STEP 1: Get initial bid/ask prices
    print(f"\n[1/4] Fetching initial bid/ask prices for {len(symbols)} symbols...")
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
    
    print("✓ Initial bid/ask prices fetched")
    
    # STEP 2: Send initial limit orders at best bid/ask
    print(f"\n[2/4] Sending initial limit orders at best bid/ask...")
    print("-" * 80)
    
    order_ids = {}  # Track order IDs for each symbol
    order_info_dict = {}  # Track full order info
    
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
            order_info_dict[symbol] = {
                'id': f"DRY_RUN_{symbol}",
                'side': side,
                'price': price,
                'amount': abs_amount / price,
                'status': 'open'
            }
        else:
            try:
                order = ccxt_make_order(
                    symbol=symbol,
                    notional_amount=abs_amount,
                    side=side,
                    order_type='limit',
                    price=price
                )
                order_id = order.get('id')
                order_ids[symbol] = order_id
                order_info_dict[symbol] = {
                    'id': order_id,
                    'side': side,
                    'price': price,
                    'amount': order.get('amount', abs_amount / price),
                    'filled': order.get('filled', 0),
                    'remaining': order.get('remaining', order.get('amount', 0)),
                    'status': order.get('status', 'open')
                }
                print(f"  Status:      ✓ Order placed - ID: {order_id}")
            except Exception as e:
                print(f"  Status:      ✗ Error: {e}")
    
    if not order_ids:
        print("\n✗ No orders were placed")
        return {'success': False, 'error': 'No orders placed'}
    
    print(f"\n✓ Placed {len(order_ids)} initial orders")
    
    # STEP 3: Tick-based monitoring loop
    print(f"\n[3/4] Starting tick-based monitoring (polling every {tick_interval}s for max {max_time}s)...")
    print("-" * 80)
    
    start_time = time.time()
    tick_count = 0
    filled_symbols = set()
    unfilled_symbols = set(order_ids.keys())
    
    while True:
        elapsed_time = time.time() - start_time
        
        # Check if max time exceeded
        if elapsed_time >= max_time:
            print(f"\n⏱ Max time ({max_time}s) reached")
            break
        
        # Check if all orders filled
        if not unfilled_symbols:
            print(f"\n✓ All orders filled!")
            break
        
        # Wait for next tick
        if tick_count > 0:
            time.sleep(tick_interval)
        
        tick_count += 1
        print(f"\n--- Tick {tick_count} (elapsed: {elapsed_time:.1f}s) ---")
        
        if not dry_run:
            # Fetch current bid/ask for unfilled symbols
            try:
                current_bid_ask = get_bid_ask(list(unfilled_symbols))
                if current_bid_ask is not None and not current_bid_ask.empty:
                    for _, row in current_bid_ask.iterrows():
                        bid_ask_dict[row['symbol']] = {
                            'bid': row['bid'],
                            'ask': row['ask'],
                            'spread': row['spread'],
                            'spread_pct': row['spread_pct']
                        }
            except Exception as e:
                print(f"  Warning: Could not fetch bid/ask: {e}")
            
            # Check order fills and move orders to best bid/ask if needed
            order_status = check_order_fills(exchange, {s: order_ids[s] for s in unfilled_symbols})
            
            for symbol in list(unfilled_symbols):
                if symbol not in order_status:
                    continue
                
                status = order_status[symbol]
                
                # Check for errors
                if 'error' in status:
                    print(f"  {symbol}: Error checking order - {status['error']}")
                    continue
                
                # Check if filled
                if status.get('status') in ['closed', 'filled']:
                    filled_symbols.add(symbol)
                    unfilled_symbols.discard(symbol)
                    print(f"  {symbol}: ✓ FILLED")
                    continue
                
                # Check partial fills
                filled_amt = status.get('filled', 0)
                total_amt = status.get('amount', 0)
                if filled_amt > 0:
                    print(f"  {symbol}: Partially filled - {filled_amt:.6f} / {total_amt:.6f}")
                
                # Move order to current best bid/ask if it changed
                if symbol in bid_ask_dict:
                    new_order_info = move_order_to_best_bid_ask(
                        exchange, symbol, status, bid_ask_dict
                    )
                    
                    if new_order_info:
                        # Order was moved, update tracking
                        order_ids[symbol] = new_order_info['id']
                        order_info_dict[symbol] = new_order_info
                    else:
                        # No move needed, already at best bid/ask
                        print(f"  {symbol}: Already at best bid/ask")
        else:
            print(f"  [DRY RUN] Would monitor {len(unfilled_symbols)} orders")
            # Simulate some fills in dry run
            if tick_count > 2 and unfilled_symbols:
                filled = list(unfilled_symbols)[0]
                filled_symbols.add(filled)
                unfilled_symbols.discard(filled)
                print(f"  {filled}: ✓ FILLED (simulated)")
    
    # STEP 4: Cross spread for remaining unfilled orders (optional)
    print(f"\n[4/4] Handling remaining unfilled orders...")
    print("-" * 80)
    
    if unfilled_symbols:
        if cross_spread_after:
            print(f"\nRemaining unfilled orders: {len(unfilled_symbols)}")
            print("Crossing spread with market orders...")
            
            if not dry_run:
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
                
                # Check final status and cross spread
                final_status = check_order_fills(exchange, {s: order_ids[s] for s in unfilled_symbols})
                
                for symbol in unfilled_symbols:
                    if symbol not in final_status or 'error' in final_status[symbol]:
                        continue
                    
                    status = final_status[symbol]
                    remaining = status.get('remaining', 0)
                    
                    if remaining > 0:
                        print(f"\n{symbol}: Crossing spread for {remaining:.6f} remaining")
                        
                        cross_order = cross_spread_with_limit_order(
                            exchange, symbol, status, bid_ask_dict
                        )
                        
                        if cross_order:
                            filled_symbols.add(symbol)
                    else:
                        print(f"\n{symbol}: ✓ Order filled")
                        filled_symbols.add(symbol)
            else:
                print(f"[DRY RUN] Would cross spread for {len(unfilled_symbols)} unfilled orders:")
                for symbol in unfilled_symbols:
                    side = order_info_dict[symbol]['side']
                    if symbol in bid_ask_dict:
                        cross_price = bid_ask_dict[symbol]['ask'] if side == 'buy' else bid_ask_dict[symbol]['bid']
                        print(f"  {symbol}: Would place limit order at ${cross_price:.4f} (crosses spread)")
                    else:
                        print(f"  {symbol}: Would cross spread")
        else:
            print(f"\n{len(unfilled_symbols)} orders still open (cross_spread_after=False)")
            for symbol in unfilled_symbols:
                print(f"  → {symbol}: Limit order remains open")
    else:
        print("✓ All orders filled during tick-based monitoring")
    
    # Summary
    remaining = unfilled_symbols - filled_symbols
    
    print("\n" + "=" * 80)
    print("EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Total trades:        {len(trades)}")
    print(f"Orders placed:       {len(order_ids)}")
    print(f"Filled:              {len(filled_symbols)}")
    print(f"Still open:          {len(remaining)}")
    print(f"Ticks executed:      {tick_count}")
    print(f"Total time:          {time.time() - start_time:.1f}s")
    
    if filled_symbols:
        print(f"\nFilled symbols:")
        for symbol in sorted(filled_symbols):
            print(f"  ✓ {symbol}")
    
    if remaining:
        print(f"\nRemaining open orders:")
        for symbol in sorted(remaining):
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
        'remaining': len(remaining),
        'ticks': tick_count,
        'elapsed_time': time.time() - start_time
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
  
  # Live: Buy $200 SOL with faster tick interval
  python3 aggressive_order_execution.py --trades "SOL/USDC:USDC:200" --live --tick-interval 1.0
  
  # Multiple trades with longer monitoring period
  python3 aggressive_order_execution.py --trades \\
    "BTC/USDC:USDC:100" \\
    "ETH/USDC:USDC:-50" \\
    "SOL/USDC:USDC:75" \\
    --live --max-time 120 --tick-interval 2.0
  
  # Keep limit orders open without crossing spread
  python3 aggressive_order_execution.py --trades "BTC/USDC:USDC:100" --live --no-cross-spread

Strategy (Tick-Based Best Bid/Ask Tracking):
  1. Sends limit orders at best bid (buy) or ask (sell)
  2. Continuously monitors market every tick-interval seconds:
     - Polls current bid/ask prices
     - If best bid/ask changed, moves orders to new best bid/ask
     - Checks if orders are filled
  3. Continues until orders filled or max-time reached
  4. Optionally crosses spread with limit orders for remaining unfilled
     - Buy orders: moved to ASK (crosses spread)
     - Sell orders: moved to BID (crosses spread)
  
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
        '--tick-interval',
        type=float,
        default=2.0,
        help='Seconds between bid/ask polls (default: 2.0)'
    )
    parser.add_argument(
        '--max-time',
        type=int,
        default=60,
        help='Maximum seconds to run before crossing spread (default: 60)'
    )
    parser.add_argument(
        '--no-cross-spread',
        action='store_true',
        help='Do not cross spread after max time (keep limit orders open)'
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
            tick_interval=args.tick_interval,
            max_time=args.max_time,
            cross_spread_after=not args.no_cross_spread,
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
