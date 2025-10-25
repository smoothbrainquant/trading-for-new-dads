"""
Aggressive Order Execution with Notional Limit and Price Walking

For a collection of orders {symbol: notional_amount}:
1. Calculate shares based on: notional / (last_price + spread * max_price_factor)
   - This ensures we can afford the shares even at max acceptable price
2. Send limit orders at best bid (buy) or ask (sell)
3. Continuously monitor (tick-based) the market:
   - Poll bid/ask prices every tick_interval seconds
   - Keep orders at best bid/ask to maximize fill probability
   - Check if orders are filled
4. After max_time, walk price to max acceptable price:
   - Buy orders: walk up to (last + spread * max_price_factor)
   - Sell orders: walk down to (last - spread * max_price_factor)
5. Never use market orders - only limit orders up to max acceptable price

This strategy ensures:
- We never exceed our notional budget
- We start with the best possible price (best bid/ask)
- We gradually walk to max acceptable price if not filled
- We NEVER use market orders that could slip beyond our budget
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


def walk_to_max_price(exchange, symbol: str, order_info: dict, 
                     bid_ask_dict: dict) -> Optional[dict]:
    """
    Walk order price to max acceptable price.
    
    Args:
        exchange: ccxt exchange instance
        symbol: Trading symbol
        order_info: Current order information (includes max_price)
        bid_ask_dict: Dictionary with current bid/ask prices
        
    Returns:
        New order info or None if error
    """
    try:
        side = order_info['side']
        remaining = order_info.get('remaining', 0)
        max_price = order_info.get('max_price')
        
        if remaining <= 0:
            print(f"  {symbol}: No remaining amount to fill")
            return None
        
        if not max_price:
            print(f"  {symbol}: Error - no max_price set")
            return None
        
        old_price = order_info.get('price', 0)
        remaining_notional = remaining * max_price
        
        print(f"  {symbol}: Walking to max acceptable price")
        print(f"           Moving from ${old_price:.4f} to ${max_price:.4f}")
        print(f"           Remaining: {remaining:.6f} (~${remaining_notional:.2f})")
        
        # Modify order to max acceptable price
        try:
            modified_order = modify_order(
                order_id=order_info['id'],
                symbol=symbol,
                new_price=max_price,
                new_amount=None  # Keep same amount
            )
            
            print(f"  {symbol}: ✓ Order moved to max price ${max_price:.4f} - ID: {modified_order.get('id')}")
            
            return {
                'id': modified_order.get('id'),
                'filled': modified_order.get('filled', 0),
                'remaining': modified_order.get('remaining', 0),
                'status': modified_order.get('status'),
                'price': max_price,
                'side': side,
                'amount': modified_order.get('amount'),
                'max_price': max_price
            }
            
        except Exception as e:
            print(f"  {symbol}: Error modifying order: {e}")
            return None
        
    except Exception as e:
        print(f"  {symbol}: Error walking to max price: {e}")
        return None


def aggressive_execute_orders(
    trades: Dict[str, float],
    tick_interval: float = 2.0,
    max_time: int = 60,
    cross_spread_after: bool = True,
    dry_run: bool = True,
    max_price_factor: float = 2.0,  # Max acceptable price = last + spread * this factor
    **kwargs  # Accept but ignore legacy parameters
):
    """
    Aggressively execute orders using notional limit with calculated shares.
    
    Strategy:
    1. Calculate shares based on: notional / (last_price + spread * max_price_factor)
    2. Send limit orders at best bid (buy) or ask (sell)
    3. Continuously monitor market (tick-based):
       - Poll bid/ask every tick_interval seconds
       - If not filled, walk price towards max acceptable price
       - Check if orders are filled
    4. Continue until orders filled, max_time reached, or max acceptable price reached
    5. Never use market orders - only limit orders up to max acceptable price
    
    Args:
        trades: Dictionary mapping symbol to notional amount
                Positive = buy, Negative = sell
                Example: {'BTC/USDC:USDC': 100, 'ETH/USDC:USDC': -50}
        tick_interval: Seconds between bid/ask polls (default: 2.0)
        max_time: Maximum seconds to run before reaching max price (default: 60)
        cross_spread_after: If True, walk price to max acceptable for remaining orders (default: True)
        max_price_factor: Factor for calculating max acceptable price (default: 2.0)
        dry_run: If True, only prints actions without executing
        
    Returns:
        dict: Summary of execution results
    """
    print("=" * 80)
    print("AGGRESSIVE ORDER EXECUTION - NOTIONAL LIMIT WITH PRICE WALKING")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE TRADING'}")
    print(f"Tick interval: {tick_interval}s")
    print(f"Max time: {max_time}s")
    print(f"Max price factor: {max_price_factor}x spread")
    print(f"Walk to max price after max time: {cross_spread_after}")
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
    
    # Convert to dict for easy lookup and calculate last price
    bid_ask_dict = {}
    for _, row in bid_ask_df.iterrows():
        bid = row['bid']
        ask = row['ask']
        last = (bid + ask) / 2  # Use mid price as last
        spread = row['spread']
        
        bid_ask_dict[row['symbol']] = {
            'bid': bid,
            'ask': ask,
            'last': last,
            'spread': spread,
            'spread_pct': row['spread_pct']
        }
    
    print("✓ Initial bid/ask prices fetched")
    
    # STEP 2: Calculate shares and send initial limit orders
    print(f"\n[2/4] Calculating shares and sending initial limit orders...")
    print("-" * 80)
    
    order_ids = {}  # Track order IDs for each symbol
    order_info_dict = {}  # Track full order info
    max_prices = {}  # Track max acceptable prices
    
    for symbol, notional_amount in trades.items():
        if notional_amount == 0:
            print(f"{symbol}: SKIP (amount is zero)")
            continue
        
        if symbol not in bid_ask_dict:
            print(f"{symbol}: ERROR - No bid/ask data")
            continue
        
        bid = bid_ask_dict[symbol]['bid']
        ask = bid_ask_dict[symbol]['ask']
        last = bid_ask_dict[symbol]['last']
        spread = bid_ask_dict[symbol]['spread']
        
        side = 'buy' if notional_amount > 0 else 'sell'
        abs_notional = abs(notional_amount)
        
        # Calculate max acceptable price
        if side == 'buy':
            max_price = last + (spread * max_price_factor)
            initial_price = bid
        else:
            max_price = last - (spread * max_price_factor)
            initial_price = ask
        
        # Calculate shares based on max acceptable price
        shares = abs_notional / max_price
        
        # Store max price for later use
        max_prices[symbol] = max_price
        
        print(f"\n{symbol}:")
        print(f"  Side:           {side.upper()}")
        print(f"  Notional:       ${abs_notional:,.2f}")
        print(f"  Last (mid):     ${last:,.4f}")
        print(f"  Spread:         ${spread:,.4f}")
        print(f"  Max price:      ${max_price:,.4f} (last + spread * {max_price_factor})")
        print(f"  Shares:         {shares:.6f} (notional / max_price)")
        print(f"  Initial price:  ${initial_price:,.4f} ({'BID' if side == 'buy' else 'ASK'})")
        
        if dry_run:
            print(f"  Status:         [DRY RUN] Would place {side.upper()} limit order")
            order_ids[symbol] = f"DRY_RUN_{symbol}"
            order_info_dict[symbol] = {
                'id': f"DRY_RUN_{symbol}",
                'side': side,
                'price': initial_price,
                'amount': shares,
                'status': 'open',
                'max_price': max_price
            }
        else:
            try:
                order = exchange.create_order(
                    symbol=symbol,
                    type='limit',
                    side=side,
                    amount=shares,
                    price=initial_price
                )
                order_id = order.get('id')
                order_ids[symbol] = order_id
                order_info_dict[symbol] = {
                    'id': order_id,
                    'side': side,
                    'price': initial_price,
                    'amount': shares,
                    'filled': order.get('filled', 0),
                    'remaining': order.get('remaining', shares),
                    'status': order.get('status', 'open'),
                    'max_price': max_price
                }
                print(f"  Status:         ✓ Order placed - ID: {order_id}")
            except Exception as e:
                print(f"  Status:         ✗ Error: {e}")
    
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
                        bid = row['bid']
                        ask = row['ask']
                        last = (bid + ask) / 2
                        bid_ask_dict[row['symbol']] = {
                            'bid': bid,
                            'ask': ask,
                            'last': last,
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
                
                # Keep order at best bid/ask, don't walk yet
                if symbol in bid_ask_dict:
                    # Just report status, don't move during monitoring phase
                    current_price = status.get('price', 0)
                    side = status.get('side')
                    bid = bid_ask_dict[symbol]['bid']
                    ask = bid_ask_dict[symbol]['ask']
                    target = bid if side == 'buy' else ask
                    
                    # Move to best bid/ask if it changed significantly
                    if current_price:
                        price_diff_pct = abs((target - current_price) / current_price * 100)
                        if price_diff_pct > 0.01:
                            print(f"  {symbol}: Moving to best {'BID' if side == 'buy' else 'ASK'} ${target:.4f}")
                            try:
                                modified_order = modify_order(
                                    order_id=status['id'],
                                    symbol=symbol,
                                    new_price=target,
                                    new_amount=None
                                )
                                order_ids[symbol] = modified_order.get('id')
                                order_info_dict[symbol].update({
                                    'id': modified_order.get('id'),
                                    'price': target
                                })
                            except Exception as e:
                                print(f"  {symbol}: Error moving to best bid/ask: {e}")
                        else:
                            print(f"  {symbol}: At best {'BID' if side == 'buy' else 'ASK'}")
        else:
            print(f"  [DRY RUN] Would monitor {len(unfilled_symbols)} orders")
            # Simulate some fills in dry run
            if tick_count > 2 and unfilled_symbols:
                filled = list(unfilled_symbols)[0]
                filled_symbols.add(filled)
                unfilled_symbols.discard(filled)
                print(f"  {filled}: ✓ FILLED (simulated)")
    
    # STEP 4: Walk to max price for remaining unfilled orders (optional)
    print(f"\n[4/4] Handling remaining unfilled orders...")
    print("-" * 80)
    
    walked_symbols = set()  # Track which symbols we walked to max price
    
    if unfilled_symbols:
        if cross_spread_after:
            print(f"\nRemaining unfilled orders: {len(unfilled_symbols)}")
            print("Walking to max acceptable price...")
            
            if not dry_run:
                # Refresh bid/ask one more time
                try:
                    final_bid_ask = get_bid_ask(list(unfilled_symbols))
                    if final_bid_ask is not None and not final_bid_ask.empty:
                        for _, row in final_bid_ask.iterrows():
                            last = (row['bid'] + row['ask']) / 2
                            bid_ask_dict[row['symbol']] = {
                                'bid': row['bid'],
                                'ask': row['ask'],
                                'last': last,
                                'spread': row['spread'],
                                'spread_pct': row['spread_pct']
                            }
                except Exception as e:
                    print(f"Warning: Could not refresh bid/ask: {e}")
                
                # Check final status and walk to max price
                final_status = check_order_fills(exchange, {s: order_ids[s] for s in unfilled_symbols})
                
                for symbol in list(unfilled_symbols):
                    if symbol not in final_status or 'error' in final_status[symbol]:
                        continue
                    
                    status = final_status[symbol]
                    # Add max_price to status from our tracking
                    status['max_price'] = order_info_dict[symbol].get('max_price')
                    remaining = status.get('remaining', 0)
                    
                    if remaining > 0:
                        print(f"\n{symbol}: Walking to max price for {remaining:.6f} remaining")
                        
                        walked_order = walk_to_max_price(
                            exchange, symbol, status, bid_ask_dict
                        )
                        
                        if walked_order:
                            walked_symbols.add(symbol)
                            # Update order tracking
                            order_ids[symbol] = walked_order.get('id')
                            order_info_dict[symbol].update(walked_order)
                    else:
                        print(f"\n{symbol}: ✓ Order filled")
                        filled_symbols.add(symbol)
                        unfilled_symbols.discard(symbol)
                
                # STEP 4b: Monitor walked orders for a short period
                if walked_symbols:
                    print(f"\n[4b] Monitoring max-price orders for 30 seconds...")
                    print("-" * 80)
                    
                    walk_start = time.time()
                    walk_max_time = 30  # 30 seconds to wait for fills at max price
                    walk_tick = 0
                    
                    while True:
                        walk_elapsed = time.time() - walk_start
                        
                        if walk_elapsed >= walk_max_time:
                            print(f"\n⏱ Max-price monitoring time ({walk_max_time}s) reached")
                            break
                        
                        if not walked_symbols:
                            print(f"\n✓ All max-price orders filled!")
                            break
                        
                        if walk_tick > 0:
                            time.sleep(2)  # Poll every 2 seconds
                        
                        walk_tick += 1
                        print(f"\n--- Max-price tick {walk_tick} (elapsed: {walk_elapsed:.1f}s) ---")
                        
                        # Check if orders filled
                        walk_status = check_order_fills(exchange, {s: order_ids[s] for s in walked_symbols})
                        
                        for symbol in list(walked_symbols):
                            if symbol not in walk_status:
                                continue
                            
                            status = walk_status[symbol]
                            
                            if 'error' in status:
                                print(f"  {symbol}: Error - {status['error']}")
                                continue
                            
                            if status.get('status') in ['closed', 'filled']:
                                filled_symbols.add(symbol)
                                unfilled_symbols.discard(symbol)
                                walked_symbols.discard(symbol)
                                print(f"  {symbol}: ✓ FILLED")
                            else:
                                filled_amt = status.get('filled', 0)
                                total_amt = status.get('amount', 0)
                                if filled_amt > 0:
                                    print(f"  {symbol}: Partially filled - {filled_amt:.6f} / {total_amt:.6f}")
                                else:
                                    print(f"  {symbol}: Still open at max price...")
                    
                    # Final status check
                    if walked_symbols:
                        print(f"\n⚠ {len(walked_symbols)} orders remain unfilled at max acceptable price")
                        for symbol in walked_symbols:
                            max_price = order_info_dict[symbol].get('max_price')
                            print(f"  → {symbol}: Limit order at ${max_price:.4f} (max acceptable)")
            else:
                print(f"[DRY RUN] Would walk to max price for {len(unfilled_symbols)} unfilled orders:")
                for symbol in unfilled_symbols:
                    max_price = order_info_dict[symbol].get('max_price')
                    print(f"  {symbol}: Would walk to ${max_price:.4f} (max acceptable price)")
                print(f"\n[DRY RUN] Would then monitor for 30s at max price")
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
        print(f"\n⚠ WARNING: {len(remaining)} orders still open (not filled):")
        for symbol in sorted(remaining):
            print(f"  → {symbol}")
        print("\nThese orders may need manual intervention to cancel or fill.")
    
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
  
  # Multiple trades with longer monitoring period and custom max price factor
  python3 aggressive_order_execution.py --trades \\
    "BTC/USDC:USDC:100" \\
    "ETH/USDC:USDC:-50" \\
    "SOL/USDC:USDC:75" \\
    --live --max-time 120 --tick-interval 2.0 --max-price-factor 2.5
  
  # Keep limit orders open without walking to max price
  python3 aggressive_order_execution.py --trades "BTC/USDC:USDC:100" --live --no-cross-spread

Strategy (Notional Limit with Price Walking):
  1. Calculates shares: notional / (last_price + spread * max_price_factor)
  2. Sends limit orders at best bid (buy) or ask (sell)
  3. Continuously monitors market every tick-interval seconds:
     - Polls current bid/ask prices
     - Keeps orders at best bid/ask
     - Checks if orders are filled
  4. After max-time, walks price to max acceptable price
     - Max acceptable = last + spread * max_price_factor (for buys)
     - Max acceptable = last - spread * max_price_factor (for sells)
  5. NEVER uses market orders - only limit orders up to max acceptable price
  
Trade Format:
  SYMBOL:AMOUNT
  - Positive amount = BUY (notional in USD)
  - Negative amount = SELL (notional in USD)
  
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
        help='Do not walk to max price after max time (keep limit orders at best bid/ask)'
    )
    parser.add_argument(
        '--max-price-factor',
        type=float,
        default=2.0,
        help='Factor for max acceptable price (default: 2.0x spread from last)'
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
            max_price_factor=args.max_price_factor,
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
