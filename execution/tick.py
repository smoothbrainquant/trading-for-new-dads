"""
Tick.py - Move all open orders to best bid/ask prices

This script fetches all open orders and adjusts their prices to best bid/ask:
- Buy orders -> moved to best bid
- Sell orders -> moved to best ask

Modes:
- 'best': Move all orders to best bid/ask (default)
- 'proximity': For pairs of orders, move furthest order halfway between closer order and best bid/ask
"""

import ccxt
import os
import argparse
from typing import Dict, List, Tuple, Optional


def get_exchange():
    """Initialize and return authenticated Hyperliquid exchange instance."""
    api_key = os.getenv("HL_API")
    secret_key = os.getenv("HL_SECRET")

    if not api_key or not secret_key:
        raise ValueError("Missing required environment variables: HL_API and/or HL_SECRET")

    return ccxt.hyperliquid(
        {
            "privateKey": secret_key,
            "walletAddress": api_key,
            "enableRateLimit": True,
        }
    )


def fetch_all_open_orders(exchange):
    """
    Fetch all open orders from the exchange.

    Returns:
        list: List of open order dictionaries
    """
    print("\n[1/3] Fetching all open orders...")
    print("-" * 80)

    try:
        orders = exchange.fetch_open_orders()
        print(f"✓ Found {len(orders)} open order(s)")
        return orders
    except Exception as e:
        print(f"✗ Error fetching open orders: {e}")
        raise


def fetch_bid_ask_prices(exchange, symbols: List[str]) -> Dict[str, Dict[str, float]]:
    """
    Fetch current bid/ask prices for given symbols.

    Args:
        exchange: CCXT exchange instance
        symbols: List of trading pair symbols

    Returns:
        dict: Dictionary mapping symbol to {'bid': float, 'ask': float}
    """
    print("\n[2/3] Fetching current bid/ask prices...")
    print("-" * 80)

    bid_ask_dict = {}

    for symbol in symbols:
        try:
            ticker = exchange.fetch_ticker(symbol)
            bid = ticker.get("bid")
            ask = ticker.get("ask")

            if bid is not None and ask is not None:
                bid_ask_dict[symbol] = {
                    "bid": bid,
                    "ask": ask,
                    "spread": ask - bid,
                    "spread_pct": ((ask - bid) / bid * 100) if bid > 0 else 0,
                }
                print(f"  {symbol:20s} | Bid: ${bid:>12,.8f} | Ask: ${ask:>12,.8f}")
            else:
                print(f"  {symbol:20s} | ✗ No bid/ask data available")

        except Exception as e:
            print(f"  {symbol:20s} | ✗ Error: {e}")

    print(f"✓ Fetched bid/ask for {len(bid_ask_dict)}/{len(symbols)} symbols")
    return bid_ask_dict


def move_order_to_target_price(
    exchange, 
    order: dict, 
    target_price: float,
    price_type: str,
    dry_run: bool = True
) -> dict:
    """
    Move a single order to a specific target price.

    Args:
        exchange: CCXT exchange instance
        order: Order dictionary
        target_price: The target price to move the order to
        price_type: Description of the price (e.g., "BID", "ASK", "MIDPOINT")
        dry_run: If True, only simulate the change

    Returns:
        dict: Result with 'status', 'message', and optionally 'modified_order'
    """
    order_id = order.get("id")
    symbol = order.get("symbol")
    side = order.get("side", "").lower()
    current_price = order.get("price")
    amount = order.get("amount")

    # Check if price change is needed (0.01% tolerance)
    if current_price and target_price:
        price_diff_pct = abs((current_price - target_price) / target_price * 100)
        if price_diff_pct < 0.01:
            return {"status": "skip", "message": f"Already at target (within 0.01%)"}

    # Calculate price change
    price_change = target_price - current_price if current_price else 0
    price_change_pct = (
        (price_change / current_price * 100) if current_price and current_price > 0 else 0
    )

    if dry_run:
        return {
            "status": "dry_run",
            "message": f"Would move to {price_type} ${target_price:,.8f} ({price_change_pct:+.2f}%)",
            "target_price": target_price,
            "price_change": price_change,
            "price_change_pct": price_change_pct,
        }

    # Actually modify the order
    try:
        modified_order = exchange.edit_order(
            id=order_id,
            symbol=symbol,
            type=order.get("type", "limit"),
            side=side,
            amount=amount,
            price=target_price,
        )

        return {
            "status": "success",
            "message": f"Moved to {price_type} ${target_price:,.8f} ({price_change_pct:+.2f}%)",
            "target_price": target_price,
            "price_change": price_change,
            "price_change_pct": price_change_pct,
            "modified_order": modified_order,
        }

    except Exception as e:
        return {"status": "error", "message": f"Error: {str(e)}"}


def move_order_to_best_price(
    exchange, order: dict, bid_ask_dict: Dict[str, Dict[str, float]], dry_run: bool = True
) -> dict:
    """
    Move a single order to best bid/ask price.

    Args:
        exchange: CCXT exchange instance
        order: Order dictionary
        bid_ask_dict: Dictionary of bid/ask prices by symbol
        dry_run: If True, only simulate the change

    Returns:
        dict: Result with 'status', 'message', and optionally 'modified_order'
    """
    order_id = order.get("id")
    symbol = order.get("symbol")
    side = order.get("side", "").lower()
    current_price = order.get("price")
    amount = order.get("amount")

    # Check if we have bid/ask data
    if symbol not in bid_ask_dict:
        return {"status": "skip", "message": "No bid/ask data available"}

    bid = bid_ask_dict[symbol]["bid"]
    ask = bid_ask_dict[symbol]["ask"]

    # Determine target price based on order side
    if side == "buy":
        target_price = bid
        price_type = "BID"
    elif side == "sell":
        target_price = ask
        price_type = "ASK"
    else:
        return {"status": "skip", "message": f"Unknown side: {side}"}

    # Use the generic move function
    return move_order_to_target_price(exchange, order, target_price, price_type, dry_run)


def process_proximity_mode(
    orders: List[dict],
    bid_ask_dict: Dict[str, Dict[str, float]]
) -> Dict[str, List[Tuple[dict, Optional[float], str]]]:
    """
    Group orders and calculate target prices for proximity mode.
    
    For each symbol-side pair with 2 orders:
    - Move furthest order 1/2 way between closer order and best bid/ask
    - If closer order is at best bid/ask, move furthest 1/2 way between itself and best bid/ask
    
    Args:
        orders: List of order dictionaries
        bid_ask_dict: Dictionary of bid/ask prices by symbol
        
    Returns:
        dict: Mapping of order_id to (order, target_price, description)
    """
    from collections import defaultdict
    
    # Group orders by (symbol, side)
    grouped = defaultdict(list)
    for order in orders:
        symbol = order.get("symbol")
        side = order.get("side", "").lower()
        if symbol and side:
            grouped[(symbol, side)].append(order)
    
    # Calculate targets for each group
    order_targets = {}
    
    for (symbol, side), group_orders in grouped.items():
        if len(group_orders) != 2:
            # Not exactly 2 orders, skip proximity mode for this group
            for order in group_orders:
                order_targets[order.get("id")] = (order, None, "Not 2 orders in group")
            continue
            
        if symbol not in bid_ask_dict:
            for order in group_orders:
                order_targets[order.get("id")] = (order, None, "No bid/ask data")
            continue
        
        # Get best bid/ask
        best_price = bid_ask_dict[symbol]["bid"] if side == "buy" else bid_ask_dict[symbol]["ask"]
        price_type = "BID" if side == "buy" else "ASK"
        
        # Sort orders by distance from best price
        # For buy orders, closer = higher price (closer to bid)
        # For sell orders, closer = lower price (closer to ask)
        if side == "buy":
            sorted_orders = sorted(group_orders, key=lambda o: o.get("price", 0), reverse=True)
        else:  # sell
            sorted_orders = sorted(group_orders, key=lambda o: o.get("price", float('inf')))
        
        closer_order = sorted_orders[0]
        furthest_order = sorted_orders[1]
        
        closer_price = closer_order.get("price")
        furthest_price = furthest_order.get("price")
        
        # Check if closer order is already at best bid/ask (within 0.01% tolerance)
        closer_at_best = False
        if closer_price and best_price:
            price_diff_pct = abs((closer_price - best_price) / best_price * 100)
            if price_diff_pct < 0.01:
                closer_at_best = True
        
        # Calculate target for furthest order
        if closer_at_best:
            # Move furthest order 1/2 way between itself and best bid/ask
            target_price = (furthest_price + best_price) / 2
            description = f"MIDPOINT (between self @ ${furthest_price:,.8f} and {price_type} @ ${best_price:,.8f})"
        else:
            # Move furthest order 1/2 way between closer order and best bid/ask
            target_price = (closer_price + best_price) / 2
            description = f"MIDPOINT (between closer @ ${closer_price:,.8f} and {price_type} @ ${best_price:,.8f})"
        
        # Set targets
        order_targets[closer_order.get("id")] = (closer_order, None, "Closer order - no change")
        order_targets[furthest_order.get("id")] = (furthest_order, target_price, description)
    
    return order_targets


def tick_orders(dry_run: bool = True, verbose: bool = False, mode: str = "best"):
    """
    Main function to tick all open orders to best bid/ask prices.

    Args:
        dry_run: If True, only simulate changes without executing
        verbose: If True, show detailed information
        mode: 'best' (move to best bid/ask) or 'proximity' (adjust based on order proximity)

    Returns:
        dict: Summary of the operation
    """
    mode_display = "PROXIMITY MODE" if mode == "proximity" else "BEST BID/ASK MODE"
    print("=" * 80)
    print(f"TICK ORDERS - {mode_display}")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE TRADING'}")
    print("=" * 80)

    try:
        # Initialize exchange
        exchange = get_exchange()

        # Step 1: Fetch all open orders
        orders = fetch_all_open_orders(exchange)

        if not orders:
            print("\n✓ No open orders found. Nothing to do.")
            return {"success": True, "total_orders": 0, "modified": 0, "skipped": 0, "errors": 0}

        # Display current orders
        print("\nCurrent open orders:")
        for i, order in enumerate(orders, 1):
            print(
                f"  {i}. {order.get('symbol', 'N/A'):20s} | "
                f"{(order.get('side') or 'N/A').upper():4s} | "
                f"Price: ${order.get('price', 0):>14,.8f} | "
                f"Amount: {order.get('amount', 0):>10.6f} | "
                f"ID: {order.get('id', 'N/A')}"
            )

        # Step 2: Fetch bid/ask prices
        symbols = list(set(order["symbol"] for order in orders if order.get("symbol")))
        bid_ask_dict = fetch_bid_ask_prices(exchange, symbols)

        if not bid_ask_dict:
            print("\n✗ Error: Could not fetch any bid/ask prices")
            return {"success": False, "error": "No bid/ask data available"}

        # Step 3: Move orders based on mode
        print("\n[3/3] Processing orders...")
        print("-" * 80)

        modified_count = 0
        skipped_count = 0
        error_count = 0

        if mode == "proximity":
            # Proximity mode: calculate targets for order pairs
            order_targets = process_proximity_mode(orders, bid_ask_dict)
            
            for i, order in enumerate(orders, 1):
                order_id = order.get("id")
                symbol = order.get("symbol")
                side = order.get("side", "").lower()
                current_price = order.get("price")
                amount = order.get("amount")

                print(f"\n[{i}/{len(orders)}] {symbol} (ID: {order_id})")
                print(f"  Side:          {side.upper()}")
                print(
                    f"  Current Price: ${current_price:,.8f}"
                    if current_price
                    else "  Current Price: N/A"
                )
                print(f"  Amount:        {amount:.6f}" if amount else "  Amount: N/A")

                # Get target from proximity calculation
                if order_id in order_targets:
                    _, target_price, description = order_targets[order_id]
                    
                    if target_price is None:
                        print(f"  Result:        → SKIP - {description}")
                        skipped_count += 1
                    else:
                        # Move order to calculated target
                        result = move_order_to_target_price(
                            exchange, order, target_price, description, dry_run
                        )
                        
                        if result["status"] == "success":
                            print(f"  Result:        ✓ {result['message']}")
                            modified_count += 1
                            if verbose and "modified_order" in result:
                                print(f"  New Order ID:  {result['modified_order'].get('id', 'N/A')}")

                        elif result["status"] == "dry_run":
                            print(f"  Result:        [DRY RUN] {result['message']}")
                            modified_count += 1

                        elif result["status"] == "skip":
                            print(f"  Result:        → SKIP - {result['message']}")
                            skipped_count += 1

                        elif result["status"] == "error":
                            print(f"  Result:        ✗ {result['message']}")
                            error_count += 1
                else:
                    print(f"  Result:        → SKIP - Order not in targets")
                    skipped_count += 1
        
        else:  # mode == "best"
            # Best bid/ask mode: move all orders to best prices
            for i, order in enumerate(orders, 1):
                order_id = order.get("id")
                symbol = order.get("symbol")
                side = order.get("side", "").lower()
                current_price = order.get("price")
                amount = order.get("amount")

                print(f"\n[{i}/{len(orders)}] {symbol} (ID: {order_id})")
                print(f"  Side:          {side.upper()}")
                print(
                    f"  Current Price: ${current_price:,.8f}"
                    if current_price
                    else "  Current Price: N/A"
                )
                print(f"  Amount:        {amount:.6f}" if amount else "  Amount: N/A")

                # Move order
                result = move_order_to_best_price(exchange, order, bid_ask_dict, dry_run)

                if result["status"] == "success":
                    print(f"  Result:        ✓ {result['message']}")
                    modified_count += 1
                    if verbose and "modified_order" in result:
                        print(f"  New Order ID:  {result['modified_order'].get('id', 'N/A')}")

                elif result["status"] == "dry_run":
                    print(f"  Result:        [DRY RUN] {result['message']}")
                    modified_count += 1

                elif result["status"] == "skip":
                    print(f"  Result:        → SKIP - {result['message']}")
                    skipped_count += 1

                elif result["status"] == "error":
                    print(f"  Result:        ✗ {result['message']}")
                    error_count += 1

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total orders:    {len(orders)}")
        print(f"Modified:        {modified_count}")
        print(f"Skipped:         {skipped_count}")
        print(f"Errors:          {error_count}")

        if dry_run:
            print("\n" + "=" * 80)
            print("⚠ NOTE: Running in DRY RUN mode. No actual changes were made.")
            print("To execute live modifications, run without --dry-run flag")
            print("=" * 80)

        return {
            "success": True,
            "total_orders": len(orders),
            "modified": modified_count,
            "skipped": skipped_count,
            "errors": error_count,
        }

    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        if verbose:
            import traceback

            traceback.print_exc()
        return {"success": False, "error": str(e)}


def main():
    """Command-line interface for tick.py"""
    parser = argparse.ArgumentParser(
        description="Move all open orders to best bid/ask prices",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Live: Actually modify the orders (default, best mode)
  python3 tick.py
  
  # Dry run: Show what changes would be made
  python3 tick.py --dry-run
  
  # Live with verbose output
  python3 tick.py --verbose
  
  # Proximity mode: Adjust order pairs based on proximity
  python3 tick.py --mode proximity
  
  # Proximity mode dry run
  python3 tick.py --mode proximity --dry-run

How it works:
  
  Best Mode (--mode best, default):
    - Fetches all open orders from Hyperliquid
    - Gets current best bid/ask prices for each symbol
    - Moves BUY orders to best BID price
    - Moves SELL orders to best ASK price
    - Skips orders already at the target price
  
  Proximity Mode (--mode proximity):
    - Groups orders by symbol and side (buy/sell)
    - For groups with exactly 2 orders:
      * Identifies closer and furthest orders from best bid/ask
      * Moves furthest order 1/2 way between closer order and best bid/ask
      * If closer order is at best bid/ask: moves furthest 1/2 way between itself and best bid/ask
      * Keeps closer order unchanged (preserves queue position)
    - Groups without exactly 2 orders are skipped
  
Environment Variables Required:
  HL_API: Your Hyperliquid API key (wallet address)
  HL_SECRET: Your Hyperliquid secret key

Safety:
  - Default mode is LIVE TRADING (executes real orders)
  - Use --dry-run flag to simulate without executing
  - Orders within 0.01% of target price are skipped
        """,
    )

    parser.add_argument(
        "--dry-run", action="store_true", help="Simulate changes without executing (default is live)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show verbose output with detailed information"
    )
    parser.add_argument(
        "--mode",
        choices=["best", "proximity"],
        default="best",
        help="Order adjustment mode: 'best' (move to best bid/ask) or 'proximity' (adjust based on order proximity)"
    )

    args = parser.parse_args()

    # Determine mode
    dry_run = args.dry_run

    # Check for API credentials
    if not dry_run:
        api_key = os.getenv("HL_API")
        secret_key = os.getenv("HL_SECRET")

        if not api_key or not secret_key:
            print("\n✗ Error: Missing API credentials for live trading")
            print("\nPlease set the following environment variables:")
            print("  export HL_API='your_api_key'")
            print("  export HL_SECRET='your_secret_key'")
            print("\nOr run in dry-run mode (with --dry-run flag)")
            exit(1)

    try:
        # Execute tick operation
        result = tick_orders(dry_run=dry_run, verbose=args.verbose, mode=args.mode)

        if not result.get("success"):
            print(f"\n✗ Operation failed: {result.get('error', 'Unknown error')}")
            exit(1)

        print("\n✓ Operation completed successfully!")
        exit(0)

    except KeyboardInterrupt:
        print("\n\n⚠ Operation cancelled by user")
        exit(130)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
