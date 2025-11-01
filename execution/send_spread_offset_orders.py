"""
Send limit orders at a configurable offset from best bid/ask.

For a list of trades {symbol: amount}, this script:
1. Gets bid/ask prices for each symbol
2. Calculates the spread (ask - bid)
3. Submits limit orders with spread-based offset:
   - Buy orders (positive amount): bid - (spread * spread_multiplier)
   - Sell orders (negative amount): ask + (spread * spread_multiplier)
4. Rounds prices to the nearest tick size using market precision info

The spread_multiplier parameter allows users to adjust how far from the best price
to place orders. For example:
  - spread_multiplier=1.0 means 1x the spread away from best bid/ask
  - spread_multiplier=0.5 means 0.5x the spread away
  - spread_multiplier=2.0 means 2x the spread away
"""

import argparse
import os
from typing import Dict
import ccxt
from get_bid_ask import get_bid_ask
from ccxt_make_order import ccxt_make_order


def get_exchange():
    """
    Initialize and return Hyperliquid exchange instance.

    Returns:
        ccxt.Exchange: Configured Hyperliquid exchange
    """
    api_key = os.getenv("HL_API")
    secret_key = os.getenv("HL_SECRET")

    if not api_key or not secret_key:
        # Return public exchange (read-only) if no credentials
        return ccxt.hyperliquid({"enableRateLimit": True})

    return ccxt.hyperliquid(
        {
            "privateKey": secret_key,
            "walletAddress": api_key,
            "enableRateLimit": True,
        }
    )


def round_price_to_tick_size(exchange, symbol: str, price: float) -> float:
    """
    Round a price to the nearest valid tick size for the given symbol.

    Args:
        exchange: CCXT exchange instance
        symbol: Trading symbol
        price: The price to round

    Returns:
        float: Price rounded to nearest tick size
    """
    try:
        # Load market info if not already loaded
        if not exchange.markets:
            exchange.load_markets()

        # Use CCXT's decimal_to_precision method to round to tick size
        market = exchange.market(symbol)
        
        # Get price precision from market info
        # CCXT provides this through the precision field
        precision = market.get("precision", {})
        price_precision = precision.get("price")
        
        if price_precision is not None:
            # Use CCXT's built-in rounding
            rounded_price = exchange.price_to_precision(symbol, price)
            return float(rounded_price)
        else:
            # Fallback: round to 8 decimals
            return round(price, 8)
    except Exception as e:
        print(f"  Warning: Could not round price for {symbol}: {e}")
        # Fallback to original price
        return price


def send_spread_offset_orders(
    trades: Dict[str, float], spread_multiplier: float = 1.0, dry_run: bool = False
):
    """
    Send limit orders at a configurable offset from best bid/ask based on spread.

    For buy orders (positive amount): places limit order at bid - (spread * spread_multiplier)
    For sell orders (negative amount): places limit order at ask + (spread * spread_multiplier)

    Prices are automatically rounded to the nearest valid tick size for each market.

    Args:
        trades: Dictionary mapping symbol to notional amount
                - Positive amount = buy at bid - (spread * multiplier)
                - Negative amount = sell at ask + (spread * multiplier)
                Example: {
                    'BTC/USDC:USDC': 100,    # Buy $100 offset from bid
                    'ETH/USDC:USDC': -50     # Sell $50 offset from ask
                }
        spread_multiplier: Multiplier for spread offset (default: 1.0)
                          - 1.0 = place order 1x spread away from best bid/ask
                          - 0.5 = place order 0.5x spread away
                          - 2.0 = place order 2x spread away
        dry_run: If True, only prints orders without executing (default: False)

    Returns:
        list: List of order results (empty if dry_run=True)
    """
    if not trades:
        print("\nNo trades to execute.")
        return []

    # Validate spread_multiplier
    if spread_multiplier < 0:
        raise ValueError("spread_multiplier must be non-negative")

    # Extract symbols from trades
    symbols = list(trades.keys())

    print("=" * 80)
    print("LIMIT ORDER SUBMISSION WITH SPREAD OFFSET")
    print("=" * 80)
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE TRADING'}")
    print(f"Spread multiplier: {spread_multiplier}x")
    print(f"Total trades: {len(trades)}")
    print("=" * 80)

    # Initialize exchange for tick size rounding
    try:
        exchange = get_exchange()
    except Exception as e:
        print(f"\n? Error initializing exchange: {e}")
        return []

    # Step 1: Get bid/ask prices for all symbols
    print(f"\n[1/2] Fetching bid/ask prices for {len(symbols)} symbols...")
    print("-" * 80)

    bid_ask_df = get_bid_ask(symbols)

    if bid_ask_df is None or bid_ask_df.empty:
        print("\n? Error: Could not fetch bid/ask prices")
        return []

    # Convert DataFrame to dictionary for easy lookup
    bid_ask_dict = {}
    for _, row in bid_ask_df.iterrows():
        bid_ask_dict[row["symbol"]] = {
            "bid": row["bid"],
            "ask": row["ask"],
            "spread": row["spread"],
            "spread_pct": row["spread_pct"],
        }

    # Step 2: Place limit orders with spread offset
    print(f"\n[2/2] Placing limit orders with {spread_multiplier}x spread offset...")
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

        bid = bid_ask_dict[symbol]["bid"]
        ask = bid_ask_dict[symbol]["ask"]
        spread = bid_ask_dict[symbol]["spread"]
        spread_pct = bid_ask_dict[symbol]["spread_pct"]

        # Calculate spread offset
        spread_offset = spread * spread_multiplier

        # Determine side and calculate offset price
        if notional_amount > 0:
            # Buy order - place at BID - (spread * multiplier)
            side = "buy"
            raw_price = bid - spread_offset
            abs_amount = notional_amount
            price_description = f"BID - {spread_multiplier}x spread"
        else:
            # Sell order - place at ASK + (spread * multiplier)
            side = "sell"
            raw_price = ask + spread_offset
            abs_amount = abs(notional_amount)
            price_description = f"ASK + {spread_multiplier}x spread"

        # Ensure price is positive
        if raw_price <= 0:
            print(f"\n{symbol}: ERROR - Calculated price is negative or zero")
            print(f"  Side:           {side.upper()}")
            print(f"  Bid:            ${bid:,.4f}")
            print(f"  Ask:            ${ask:,.4f}")
            print(f"  Spread:         ${spread:.4f}")
            print(f"  Offset:         ${spread_offset:.4f}")
            print(f"  Raw Price:      ${raw_price:.4f}")
            print(f"  ERROR: Price must be positive. Try reducing spread_multiplier.")
            continue

        # Round price to valid tick size
        price = round_price_to_tick_size(exchange, symbol, raw_price)

        print(f"\n{symbol}:")
        print(f"  Side:           {side.upper()}")
        print(f"  Notional:       ${abs_amount:,.2f}")
        print(f"  Bid:            ${bid:,.4f}")
        print(f"  Ask:            ${ask:,.4f}")
        print(f"  Spread:         ${spread:.4f} ({spread_pct:.4f}%)")
        print(f"  Spread Offset:  ${spread_offset:.4f} ({spread_multiplier}x)")
        print(f"  Raw Price:      ${raw_price:.8f}")
        print(f"  Order Price:    ${price:.8f} ({price_description}, rounded to tick)")
        print(f"  Order Quantity: {abs_amount / price:.6f}")

        if dry_run:
            print(
                f"  Status:         [DRY RUN] Would place {side.upper()} limit order at ${price:.4f}"
            )
        else:
            try:
                # Place limit order
                order = ccxt_make_order(
                    symbol=symbol,
                    notional_amount=abs_amount,
                    side=side,
                    order_type="limit",
                    price=price,
                )
                orders.append(order)
                print(f"  Status:         ? Limit order placed successfully")
                print(f"  Order ID:       {order.get('id', 'N/A')}")
            except Exception as e:
                print(f"  Status:         ? Error: {str(e)}")

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
    print(f"Spread multiplier: {spread_multiplier}x")

    if dry_run:
        print("\n" + "=" * 80)
        print("NOTE: Running in DRY RUN mode. No actual orders were placed.")
        print("To execute live orders, run without --dry-run flag")
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
            parts = trade_str.rsplit(":", 1)
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
    Command-line interface for sending limit orders with spread offset.
    """
    parser = argparse.ArgumentParser(
        description="Send limit orders at configurable offset from bid/ask based on spread",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Live: Buy $100 BTC at bid - 1x spread, sell $50 ETH at ask + 1x spread
  python3 send_spread_offset_orders.py --trades "BTC/USDC:USDC:100" "ETH/USDC:USDC:-50"
  
  # Live: Buy $200 SOL at bid - 0.5x spread (closer to best bid)
  python3 send_spread_offset_orders.py --trades "SOL/USDC:USDC:200" --spread-multiplier 0.5
  
  # Multiple trades with 2x spread offset (farther from best prices)
  python3 send_spread_offset_orders.py --trades \\
    "BTC/USDC:USDC:100" \\
    "ETH/USDC:USDC:-50" \\
    "SOL/USDC:USDC:75" \\
    "ARB/USDC:USDC:-25" \\
    --spread-multiplier 2.0
  
  # Dry run mode (test without executing)
  python3 send_spread_offset_orders.py --trades "BTC/USDC:USDC:1000" --spread-multiplier 0.25 --dry-run

Order Placement Logic:
  - Buy orders (positive amount): bid - (spread ? spread_multiplier)
  - Sell orders (negative amount): ask + (spread ? spread_multiplier)
  - All prices are rounded to the nearest valid tick size
  
Spread Multiplier:
  - 1.0 (default): Place order 1x the spread away from best bid/ask
  - 0.5: Place order 0.5x the spread away (closer to best price)
  - 2.0: Place order 2x the spread away (farther from best price)
  - 0.0: Place order exactly at best bid/ask (same as send_limit_orders.py)

Trade Format:
  SYMBOL:AMOUNT
  - Positive amount = BUY at bid - (spread ? multiplier)
  - Negative amount = SELL at ask + (spread ? multiplier)
  
Environment Variables Required (for live trading):
  HL_API: Your Hyperliquid API key (wallet address)
  HL_SECRET: Your Hyperliquid secret key
        """,
    )

    parser.add_argument(
        "--trades",
        nargs="+",
        required=True,
        help='List of trades in format SYMBOL:AMOUNT (e.g., "BTC/USDC:USDC:100" for buy, "ETH/USDC:USDC:-50" for sell)',
    )
    parser.add_argument(
        "--spread-multiplier",
        "-m",
        type=float,
        default=1.0,
        help="Multiplier for spread offset (default: 1.0). "
        "1.0 = 1x spread away, 0.5 = 0.5x spread away, etc.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Dry run mode - show orders without executing (default is live trading)"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Show verbose output")

    args = parser.parse_args()

    # Parse trades
    trades = parse_trades_from_args(args.trades)

    if not trades:
        print("\n? Error: No valid trades provided")
        parser.print_help()
        exit(1)

    # Validate spread multiplier
    if args.spread_multiplier < 0:
        print("\n? Error: spread_multiplier must be non-negative")
        exit(1)

    # Check for API credentials if live mode
    if args.dry_run:
        dry_run = True
    else:
        api_key = os.getenv("HL_API")
        secret_key = os.getenv("HL_SECRET")

        if not api_key or not secret_key:
            print("\n? Error: Missing API credentials for live trading")
            print("\nPlease set the following environment variables:")
            print("  export HL_API='your_api_key'")
            print("  export HL_SECRET='your_secret_key'")
            print("\nOr run in dry-run mode (with --dry-run flag)")
            exit(1)

        dry_run = False

    try:
        # Send limit orders with spread offset
        orders = send_spread_offset_orders(
            trades, spread_multiplier=args.spread_multiplier, dry_run=dry_run
        )

        # Print full details if verbose
        if args.verbose and orders:
            print("\nFull Order Details:")
            from pprint import pprint

            for order in orders:
                pprint(order)
                print()

    except Exception as e:
        print(f"\n? Error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        exit(1)


if __name__ == "__main__":
    main()
