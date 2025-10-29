"""
Tick.py - Move all open orders to best bid/ask prices

This script fetches all open orders and adjusts their prices to best bid/ask:
- Buy orders -> moved to best bid
- Sell orders -> moved to best ask
"""

import ccxt
import os
import argparse
from typing import Dict, List


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

    # Check if price change is needed (0.01% tolerance)
    if current_price and target_price:
        price_diff_pct = abs((current_price - target_price) / target_price * 100)
        if price_diff_pct < 0.01:
            return {"status": "skip", "message": f"Already at {price_type} (within 0.01%)"}

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


def tick_orders(dry_run: bool = True, verbose: bool = False):
    """
    Main function to tick all open orders to best bid/ask prices.

    Args:
        dry_run: If True, only simulate changes without executing
        verbose: If True, show detailed information

    Returns:
        dict: Summary of the operation
    """
    print("=" * 80)
    print("TICK ORDERS TO BEST BID/ASK")
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

        # Step 3: Move orders to best bid/ask
        print("\n[3/3] Processing orders...")
        print("-" * 80)

        modified_count = 0
        skipped_count = 0
        error_count = 0

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
            print("To execute live modifications, run with --live flag")
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
  # Dry run: Show what changes would be made (default)
  python3 tick.py
  
  # Live: Actually modify the orders
  python3 tick.py --live
  
  # Live with verbose output
  python3 tick.py --live --verbose

How it works:
  - Fetches all open orders from Hyperliquid
  - Gets current best bid/ask prices for each symbol
  - Moves BUY orders to best BID price
  - Moves SELL orders to best ASK price
  - Skips orders already at the target price
  
Environment Variables Required:
  HL_API: Your Hyperliquid API key (wallet address)
  HL_SECRET: Your Hyperliquid secret key

Safety:
  - Default mode is DRY RUN (no actual changes)
  - Use --live flag to execute real order modifications
  - Orders within 0.01% of target price are skipped
        """,
    )

    parser.add_argument(
        "--live", action="store_true", help="Execute live order modifications (default is dry-run)"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show verbose output with detailed information"
    )

    args = parser.parse_args()

    # Determine mode
    dry_run = not args.live

    # Check for API credentials
    if not dry_run:
        api_key = os.getenv("HL_API")
        secret_key = os.getenv("HL_SECRET")

        if not api_key or not secret_key:
            print("\n✗ Error: Missing API credentials for live trading")
            print("\nPlease set the following environment variables:")
            print("  export HL_API='your_api_key'")
            print("  export HL_SECRET='your_secret_key'")
            print("\nOr run in dry-run mode (without --live flag)")
            exit(1)

    try:
        # Execute tick operation
        result = tick_orders(dry_run=dry_run, verbose=args.verbose)

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
