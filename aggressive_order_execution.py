"""
Aggressive Order Execution with Notional Limit and Price Ladder

For a collection of orders {symbol: notional_amount}:
1. Calculate position size based on notional / (last + spread * 2) to ensure sufficient budget
2. Send initial limit orders at best bid (buy) or ask (sell)
3. Continuously monitor (tick-based) and walk price ladder:
   - Poll prices every tick_interval seconds
   - For buys: gradually increase price from bid towards max_price (last + spread * 2)
   - For sells: gradually decrease price from ask towards min_price (last - spread * 2)
   - Walk 20% of remaining distance to max/min price each tick
   - Check if orders are filled
4. Continue until orders are filled or max_time is reached
5. Optionally cross spread with limit orders for remaining unfilled
   - Buy orders: moved to ASK price (crosses spread)
   - Sell orders: moved to BID price (crosses spread)
   - NO MARKET ORDERS - all orders remain as limit orders

This strategy ensures we have enough notional to fill at higher prices while
progressively moving towards max acceptable price (NOT taking market orders).
"""

import argparse
import os
import time
import ccxt
from typing import Dict, List, Optional
from get_bid_ask import get_bid_ask
from ccxt_make_order import ccxt_make_order
from modify_order import modify_order
import pandas as pd


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


def get_prices_with_last(symbols):
    """
    Fetch bid/ask/last prices for symbols.
    
    Args:
        symbols: List of trading symbols
        
    Returns:
        DataFrame with columns: symbol, bid, ask, last, spread, spread_pct, max_price
    """
    exchange = ccxt.hyperliquid({
        'enableRateLimit': True,
    })
    
    price_data = []
    for symbol in symbols:
        try:
            ticker = exchange.fetch_ticker(symbol)
            bid = ticker.get('bid')
            ask = ticker.get('ask')
            last = ticker.get('last')
            
            if bid and ask and last:
                spread = ask - bid
                spread_pct = (spread / bid * 100) if bid > 0 else 0
                # Calculate max acceptable price: last + (spread * 2)
                max_price = last + (spread * 2)
                
                price_data.append({
                    'symbol': symbol,
                    'bid': bid,
                    'ask': ask,
                    'last': last,
                    'spread': spread,
                    'spread_pct': spread_pct,
                    'max_price': max_price
                })
        except Exception as e:
            print(f"  Warning: Could not fetch prices for {symbol}: {e}")
    
    return pd.DataFrame(price_data) if price_data else None


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
                               price_dict: dict) -> Optional[dict]:
    """
    Move an order to the current best bid/ask price.
    
    For buy orders: move to current best bid
    For sell orders: move to current best ask
    
    Args:
        exchange: ccxt exchange instance
        symbol: Trading symbol
        order_info: Current order information
        price_dict: Dictionary with current bid/ask prices
        
    Returns:
        Modified order info or None if error or no change needed
    """
    try:
        side = order_info['side']
        current_price = order_info['price']
        bid = price_dict[symbol]['bid']
        ask = price_dict[symbol]['ask']
        
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


def cross_spread_with_limit_order(exchange, symbol: str, order_info: dict, 
                                  price_dict: dict) -> Optional[dict]:
    """
    Cross the spread by placing a limit order on the opposite side.
    For buy orders: place limit at ASK (crosses spread)
    For sell orders: place limit at BID (crosses spread)
    
    Args:
        exchange: ccxt exchange instance
        symbol: Trading symbol
        order_info: Current order information
        price_dict: Dictionary with current bid/ask prices
        
    Returns:
        New order info or None if error
    """
    try:
        side = order_info['side']
        remaining = order_info.get('remaining', 0)
        
        if remaining <= 0:
            print(f"  {symbol}: No remaining amount to fill")
            return None
        
        # Get current bid/ask
        if symbol not in price_dict:
            print(f"  {symbol}: Error - No price data available")
            return None
        
        bid = price_dict[symbol]['bid']
        ask = price_dict[symbol]['ask']
        
        # Cross the spread: buy at ask, sell at bid
        if side == 'buy':
            cross_price = ask
            price_type = "ASK"
        else:
            cross_price = bid
            price_type = "BID"
        
        old_price = order_info.get('price', 0)
        remaining_notional = remaining * cross_price
        
        print(f"  {symbol}: Crossing spread with LIMIT {side.upper()} order")
        print(f"           Moving from ${old_price:.4f} to ${cross_price:.4f} ({price_type})")
        print(f"           Remaining: {remaining:.6f} (~${remaining_notional:.2f})")
        
        # Cancel the existing limit order first
        try:
            exchange.cancel_order(order_info['id'], symbol)
            print(f"  {symbol}: Cancelled limit order {order_info['id']}")
        except Exception as e:
            print(f"  {symbol}: Warning - could not cancel order: {e}")
        
        # Place limit order at the opposite side of spread (crosses spread)
        new_order = exchange.create_order(
            symbol=symbol,
            type='limit',
            side=side,
            amount=remaining,
            price=cross_price
        )
        
        print(f"  {symbol}: ✓ Limit order placed at ${cross_price:.4f} (crosses spread) - ID: {new_order.get('id')}")
        
        return new_order
        
    except Exception as e:
        print(f"  {symbol}: Error placing limit order: {e}")
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
    Aggressively execute orders using notional limit and price ladder strategy.
    
    Strategy:
    1. Calculate position size: notional / (last + spread * 2) to ensure sufficient budget
    2. Send limit orders at best bid (buy) or ask (sell)
    3. Continuously monitor market and walk price ladder (tick-based):
       - Poll prices every tick_interval seconds
       - For buys: walk up from bid towards max_price (last + spread * 2)
       - For sells: walk down from ask towards min_price (last - spread * 2)
       - Move 20% of remaining distance to max/min each tick
       - Check if orders are filled
    4. Continue until orders filled or max_time reached
    5. Optionally cross spread with limit orders for remaining unfilled
       - Buy orders: moved to ASK price (crosses spread)
       - Sell orders: moved to BID price (crosses spread)
       - NO MARKET ORDERS - all orders remain as limit orders
    
    Args:
        trades: Dictionary mapping symbol to notional amount
                Positive = buy, Negative = sell
                Example: {'BTC/USDC:USDC': 100, 'ETH/USDC:USDC': -50}
        tick_interval: Seconds between price polls (default: 2.0)
        max_time: Maximum seconds to run before crossing spread (default: 60)
        cross_spread_after: If True, cross spread for remaining orders after max_time (default: True)
        dry_run: If True, only prints actions without executing
        
    Returns:
        dict: Summary of execution results
    """
    print("=" * 80)
    print("AGGRESSIVE ORDER EXECUTION - NOTIONAL LIMIT WITH PRICE LADDER")
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
    
    # STEP 1: Get initial bid/ask/last prices
    print(f"\n[1/5] Fetching initial bid/ask/last prices for {len(symbols)} symbols...")
    print("-" * 80)
    
    try:
        price_df = get_prices_with_last(symbols)
    except Exception as e:
        print(f"\n✗ Failed to fetch prices: {e}")
        return {'success': False, 'error': str(e)}
    
    if price_df is None or price_df.empty:
        print("\n✗ Error: Could not fetch prices")
        return {'success': False, 'error': 'No price data'}
    
    # Convert to dict for easy lookup
    price_dict = {}
    for _, row in price_df.iterrows():
        price_dict[row['symbol']] = {
            'bid': row['bid'],
            'ask': row['ask'],
            'last': row['last'],
            'spread': row['spread'],
            'spread_pct': row['spread_pct'],
            'max_price': row['max_price']
        }
    
    print("✓ Initial prices fetched with last and max_price calculated")
    
    # STEP 2: Calculate position sizes and send initial limit orders
    print(f"\n[2/5] Calculating position sizes and placing initial limit orders...")
    print("-" * 80)
    
    order_ids = {}  # Track order IDs for each symbol
    order_info_dict = {}  # Track full order info
    
    for symbol, notional_amount in trades.items():
        if notional_amount == 0:
            print(f"{symbol}: SKIP (amount is zero)")
            continue
        
        if symbol not in price_dict:
            print(f"{symbol}: ERROR - No price data")
            continue
        
        prices = price_dict[symbol]
        bid = prices['bid']
        ask = prices['ask']
        last = prices['last']
        spread = prices['spread']
        max_price = prices['max_price']
        
        side = 'buy' if notional_amount > 0 else 'sell'
        abs_notional = abs(notional_amount)
        
        # Calculate position size using max_price to ensure we have enough notional
        # For buys: max_price is last + spread*2
        # For sells: use min_price which is last - spread*2
        if side == 'buy':
            position_size = abs_notional / max_price
            initial_price = bid
            min_price = bid
        else:
            min_price = last - (spread * 2)
            position_size = abs_notional / min_price
            initial_price = ask
            # For sells, we walk down so max becomes the starting point
            max_price_for_sell = ask
            min_price_for_sell = min_price
        
        print(f"\n{symbol}:")
        print(f"  Side:          {side.upper()}")
        print(f"  Notional:      ${abs_notional:,.2f}")
        print(f"  Last Price:    ${last:,.4f}")
        print(f"  Spread:        ${spread:,.6f}")
        if side == 'buy':
            print(f"  Max Price:     ${max_price:,.4f} (last + spread*2)")
        else:
            print(f"  Min Price:     ${min_price_for_sell:,.4f} (last - spread*2)")
        print(f"  Position Size: {position_size:.6f}")
        print(f"  Initial Price: ${initial_price:,.4f} (best {side})")
        
        if dry_run:
            print(f"  Status:        [DRY RUN] Would place {side.upper()} limit order")
            order_ids[symbol] = f"DRY_RUN_{symbol}"
            order_info_dict[symbol] = {
                'id': f"DRY_RUN_{symbol}",
                'side': side,
                'price': initial_price,
                'amount': position_size,
                'target_amount': position_size,
                'max_price': max_price if side == 'buy' else max_price_for_sell,
                'min_price': min_price if side == 'buy' else min_price_for_sell,
                'status': 'open'
            }
        else:
            try:
                # Place order with calculated position size at initial price
                order = exchange.create_order(
                    symbol=symbol,
                    type='limit',
                    side=side,
                    amount=position_size,
                    price=initial_price
                )
                order_id = order.get('id')
                order_ids[symbol] = order_id
                order_info_dict[symbol] = {
                    'id': order_id,
                    'side': side,
                    'price': initial_price,
                    'amount': position_size,
                    'target_amount': position_size,
                    'max_price': max_price if side == 'buy' else max_price_for_sell,
                    'min_price': min_price if side == 'buy' else min_price_for_sell,
                    'filled': order.get('filled', 0),
                    'remaining': order.get('remaining', position_size),
                    'status': order.get('status', 'open')
                }
                print(f"  Status:        ✓ Order placed - ID: {order_id}")
            except Exception as e:
                print(f"  Status:        ✗ Error: {e}")
    
    if not order_ids:
        print("\n✗ No orders were placed")
        return {'success': False, 'error': 'No orders placed'}
    
    print(f"\n✓ Placed {len(order_ids)} initial orders")
    
    # STEP 3: Tick-based monitoring loop with price ladder
    print(f"\n[3/5] Starting price ladder execution (polling every {tick_interval}s for max {max_time}s)...")
    print(f"      Orders will walk price ladder towards max acceptable price...")
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
            # Fetch current prices for unfilled symbols
            try:
                current_prices = get_prices_with_last(list(unfilled_symbols))
                if current_prices is not None and not current_prices.empty:
                    for _, row in current_prices.iterrows():
                        price_dict[row['symbol']] = {
                            'bid': row['bid'],
                            'ask': row['ask'],
                            'last': row['last'],
                            'spread': row['spread'],
                            'spread_pct': row['spread_pct'],
                            'max_price': row['max_price']
                        }
            except Exception as e:
                print(f"  Warning: Could not fetch prices: {e}")
            
            # Check order fills and walk up price ladder if needed
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
                
                # Walk up price ladder towards max_price (for buys) or down (for sells)
                if symbol in price_dict and symbol in order_info_dict:
                    current_order_price = status.get('price')
                    side = status.get('side')
                    max_acceptable = order_info_dict[symbol].get('max_price')
                    min_acceptable = order_info_dict[symbol].get('min_price')
                    
                    if side == 'buy':
                        # For buys, walk up from bid towards max_price
                        # Increase price by 20% of remaining distance to max_price
                        if current_order_price and current_order_price < max_acceptable:
                            price_increment = (max_acceptable - current_order_price) * 0.2
                            new_price = min(current_order_price + price_increment, max_acceptable)
                            
                            # Only move if significantly different (more than 0.1%)
                            if (new_price - current_order_price) / current_order_price > 0.001:
                                print(f"  {symbol}: Walking up price ladder ${current_order_price:.4f} → ${new_price:.4f} (max: ${max_acceptable:.4f})")
                                try:
                                    modified_order = modify_order(
                                        order_id=status['id'],
                                        symbol=symbol,
                                        new_price=new_price,
                                        new_amount=None
                                    )
                                    if modified_order:
                                        order_ids[symbol] = modified_order.get('id')
                                        order_info_dict[symbol]['price'] = new_price
                                        print(f"  {symbol}: ✓ Price updated")
                                except Exception as e:
                                    print(f"  {symbol}: Error modifying order: {e}")
                            else:
                                print(f"  {symbol}: At max price ${current_order_price:.4f}")
                        elif current_order_price and current_order_price >= max_acceptable:
                            print(f"  {symbol}: Already at max price ${current_order_price:.4f}")
                    else:
                        # For sells, walk down from ask towards min_price
                        if current_order_price and current_order_price > min_acceptable:
                            price_decrement = (current_order_price - min_acceptable) * 0.2
                            new_price = max(current_order_price - price_decrement, min_acceptable)
                            
                            if (current_order_price - new_price) / current_order_price > 0.001:
                                print(f"  {symbol}: Walking down price ladder ${current_order_price:.4f} → ${new_price:.4f} (min: ${min_acceptable:.4f})")
                                try:
                                    modified_order = modify_order(
                                        order_id=status['id'],
                                        symbol=symbol,
                                        new_price=new_price,
                                        new_amount=None
                                    )
                                    if modified_order:
                                        order_ids[symbol] = modified_order.get('id')
                                        order_info_dict[symbol]['price'] = new_price
                                        print(f"  {symbol}: ✓ Price updated")
                                except Exception as e:
                                    print(f"  {symbol}: Error modifying order: {e}")
                            else:
                                print(f"  {symbol}: At min price ${current_order_price:.4f}")
                        elif current_order_price and current_order_price <= min_acceptable:
                            print(f"  {symbol}: Already at min price ${current_order_price:.4f}")
        else:
            print(f"  [DRY RUN] Would monitor {len(unfilled_symbols)} orders")
            # Simulate some fills in dry run
            if tick_count > 2 and unfilled_symbols:
                filled = list(unfilled_symbols)[0]
                filled_symbols.add(filled)
                unfilled_symbols.discard(filled)
                print(f"  {filled}: ✓ FILLED (simulated)")
    
    # STEP 4: Handle remaining unfilled orders
    print(f"\n[4/5] Handling remaining unfilled orders...")
    print("-" * 80)
    
    crossed_spread_symbols = set()  # Track which symbols we crossed spread for
    
    if unfilled_symbols:
        if cross_spread_after:
            print(f"\nRemaining unfilled orders: {len(unfilled_symbols)}")
            print("Crossing spread with limit orders...")
            
            if not dry_run:
                # Refresh prices one more time
                try:
                    final_prices = get_prices_with_last(list(unfilled_symbols))
                    if final_prices is not None and not final_prices.empty:
                        for _, row in final_prices.iterrows():
                            price_dict[row['symbol']] = {
                                'bid': row['bid'],
                                'ask': row['ask'],
                                'last': row['last'],
                                'spread': row['spread'],
                                'spread_pct': row['spread_pct'],
                                'max_price': row['max_price']
                            }
                except Exception as e:
                    print(f"Warning: Could not refresh prices: {e}")
                
                # Check final status and cross spread
                final_status = check_order_fills(exchange, {s: order_ids[s] for s in unfilled_symbols})
                
                for symbol in list(unfilled_symbols):
                    if symbol not in final_status or 'error' in final_status[symbol]:
                        continue
                    
                    status = final_status[symbol]
                    remaining = status.get('remaining', 0)
                    
                    if remaining > 0:
                        print(f"\n{symbol}: Crossing spread for {remaining:.6f} remaining")
                        
                        cross_order = cross_spread_with_limit_order(
                            exchange, symbol, status, price_dict
                        )
                        
                        if cross_order:
                            crossed_spread_symbols.add(symbol)
                            # Update order tracking with new crossed-spread order
                            order_ids[symbol] = cross_order.get('id')
                            order_info_dict[symbol].update({
                                'id': cross_order.get('id'),
                                'price': cross_order.get('price'),
                                'amount': cross_order.get('amount'),
                                'filled': cross_order.get('filled', 0),
                                'remaining': cross_order.get('remaining', cross_order.get('amount', 0))
                            })
                    else:
                        print(f"\n{symbol}: ✓ Order filled")
                        filled_symbols.add(symbol)
                        unfilled_symbols.discard(symbol)
                
                # STEP 4b: Monitor crossed-spread orders for a short period
                if crossed_spread_symbols:
                    print(f"\n[4b] Monitoring crossed-spread orders for 15 seconds...")
                    print("-" * 80)
                    
                    cross_spread_start = time.time()
                    cross_spread_max_time = 15  # 15 seconds to wait for fills
                    cross_tick = 0
                    
                    while True:
                        cross_elapsed = time.time() - cross_spread_start
                        
                        if cross_elapsed >= cross_spread_max_time:
                            print(f"\n⏱ Crossed-spread monitoring time ({cross_spread_max_time}s) reached")
                            break
                        
                        if not crossed_spread_symbols:
                            print(f"\n✓ All crossed-spread orders filled!")
                            break
                        
                        if cross_tick > 0:
                            time.sleep(2)  # Poll every 2 seconds
                        
                        cross_tick += 1
                        print(f"\n--- Cross-spread tick {cross_tick} (elapsed: {cross_elapsed:.1f}s) ---")
                        
                        # Check if crossed-spread orders filled
                        cross_status = check_order_fills(exchange, {s: order_ids[s] for s in crossed_spread_symbols})
                        
                        for symbol in list(crossed_spread_symbols):
                            if symbol not in cross_status:
                                continue
                            
                            status = cross_status[symbol]
                            
                            if 'error' in status:
                                print(f"  {symbol}: Error - {status['error']}")
                                continue
                            
                            if status.get('status') in ['closed', 'filled']:
                                filled_symbols.add(symbol)
                                unfilled_symbols.discard(symbol)
                                crossed_spread_symbols.discard(symbol)
                                print(f"  {symbol}: ✓ FILLED")
                            else:
                                filled_amt = status.get('filled', 0)
                                total_amt = status.get('amount', 0)
                                if filled_amt > 0:
                                    print(f"  {symbol}: Partially filled - {filled_amt:.6f} / {total_amt:.6f}")
                                else:
                                    print(f"  {symbol}: Still open...")
                    
                    # STEP 4c: Check final status (NO MARKET ORDERS - keep limit orders open)
                    if crossed_spread_symbols:
                        print(f"\n[4c] Final check for {len(crossed_spread_symbols)} remaining symbols...")
                        print("      (Limit orders will remain open - no market orders)")
                        print("-" * 80)
                        
                        # Check final status one more time
                        final_cross_status = check_order_fills(exchange, {s: order_ids[s] for s in crossed_spread_symbols})
                        
                        for symbol in crossed_spread_symbols:
                            if symbol not in final_cross_status or 'error' in final_cross_status[symbol]:
                                continue
                            
                            status = final_cross_status[symbol]
                            remaining = status.get('remaining', 0)
                            
                            if remaining > 0:
                                print(f"\n{symbol}: Still {remaining:.6f} remaining - limit order stays open")
                            else:
                                print(f"\n{symbol}: ✓ Order filled")
                                filled_symbols.add(symbol)
                                unfilled_symbols.discard(symbol)
                                crossed_spread_symbols.discard(symbol)
            else:
                print(f"[DRY RUN] Would cross spread for {len(unfilled_symbols)} unfilled orders:")
                for symbol in unfilled_symbols:
                    side = order_info_dict[symbol]['side']
                    if symbol in price_dict:
                        cross_price = price_dict[symbol]['ask'] if side == 'buy' else price_dict[symbol]['bid']
                        print(f"  {symbol}: Would place limit order at ${cross_price:.4f} (crosses spread)")
                    else:
                        print(f"  {symbol}: Would cross spread")
                print(f"\n[DRY RUN] Would then monitor for 15s (NO MARKET ORDERS - keep limit orders)")
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
  
  # Multiple trades with longer monitoring period
  python3 aggressive_order_execution.py --trades \\
    "BTC/USDC:USDC:100" \\
    "ETH/USDC:USDC:-50" \\
    "SOL/USDC:USDC:75" \\
    --live --max-time 120 --tick-interval 2.0
  
  # Keep limit orders open without crossing spread
  python3 aggressive_order_execution.py --trades "BTC/USDC:USDC:100" --live --no-cross-spread

Strategy (Notional Limit with Price Ladder):
  1. Calculates position size: notional / (last + spread * 2)
  2. Sends limit orders at best bid (buy) or ask (sell)
  3. Continuously monitors market and walks price ladder every tick-interval seconds:
     - For buys: walks up from bid towards max_price (last + spread * 2)
     - For sells: walks down from ask towards min_price (last - spread * 2)
     - Moves 20% of remaining distance to max/min each tick
     - Checks if orders are filled
  4. Continues until orders filled or max-time reached
  5. Optionally crosses spread with limit orders for remaining unfilled
     - Buy orders: moved to ASK (crosses spread)
     - Sell orders: moved to BID (crosses spread)
     - NO MARKET ORDERS - all remain as limit orders
  
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
