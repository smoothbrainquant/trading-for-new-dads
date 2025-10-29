import ccxt
import os
import argparse
from pprint import pprint


def ccxt_make_order(symbol, notional_amount, side, order_type, price=None):
    """
    Place a market or limit order on Hyperliquid exchange.

    Args:
        symbol: Trading pair (e.g., 'BTC/USDC:USDC', 'ETH/USDC:USDC')
        notional_amount: Total USD/USDC amount to trade (e.g., 100 for $100)
        side: 'buy' or 'sell'
        order_type: 'market' or 'limit'
        price: Price for limit orders (required for limit, ignored for market)

    Requires environment variables:
        HL_API: Hyperliquid API key (wallet address)
        HL_SECRET: Hyperliquid secret key

    Returns:
        Dictionary containing order response
    """
    # Get API credentials from environment variables
    api_key = os.getenv("HL_API")
    secret_key = os.getenv("HL_SECRET")

    if not api_key or not secret_key:
        raise ValueError("Missing required environment variables: HL_API and/or HL_SECRET")

    # Validate inputs
    side = side.lower()
    if side not in ["buy", "sell"]:
        raise ValueError("Side must be 'buy' or 'sell'")

    order_type = order_type.lower()
    if order_type not in ["market", "limit"]:
        raise ValueError("Order type must be 'market' or 'limit'")

    if order_type == "limit" and price is None:
        raise ValueError("Price is required for limit orders")

    if notional_amount <= 0:
        raise ValueError("Notional amount must be positive")

    # Initialize Hyperliquid exchange with authentication
    exchange = ccxt.hyperliquid(
        {
            "privateKey": secret_key,
            "walletAddress": api_key,
            "enableRateLimit": True,
        }
    )

    try:
        # Fetch current market price and ticker to calculate amount
        ticker = exchange.fetch_ticker(symbol)
        current_price = ticker["last"]

        print(f"\nCurrent {symbol} price: ${current_price:,.2f}")

        # For limit orders, use the specified price, for market use current price
        effective_price = price if order_type == "limit" else current_price

        # Calculate the amount (quantity) based on notional amount
        # amount = notional_amount / price
        amount = notional_amount / effective_price

        print(f"Order details:")
        print(f"  Symbol: {symbol}")
        print(f"  Side: {side.upper()}")
        print(f"  Type: {order_type.upper()}")
        print(f"  Notional Amount: ${notional_amount:,.2f}")
        print(
            f"  Price: ${effective_price:,.2f}"
            + (" (specified)" if order_type == "limit" else " (market)")
        )
        print(f"  Quantity: {amount:.6f}")
        print(f"  Total Value: ${notional_amount:,.2f}")

        # Confirm before placing order
        print(f"\n{'='*60}")
        print("PLACING ORDER...")
        print(f"{'='*60}\n")

        # Place the order
        if order_type == "market":
            # Hyperliquid requires price for market orders (for slippage calculation)
            # Use create_order with type='market' and pass the price
            order = exchange.create_order(
                symbol=symbol, type="market", side=side, amount=amount, price=current_price
            )
        else:  # limit order
            order = exchange.create_limit_order(
                symbol=symbol, side=side, amount=amount, price=price
            )

        print("✓ Order placed successfully!")
        print(f"\n{'='*60}")
        print("ORDER SUMMARY")
        print(f"{'='*60}")
        print(f"Order ID: {order.get('id', 'N/A')}")
        print(f"Symbol: {order.get('symbol') or symbol or 'N/A'}")
        print(f"Type: {(order.get('type') or order_type or 'N/A').upper()}")
        print(f"Side: {(order.get('side') or side or 'N/A').upper()}")
        print(f"Amount: {order.get('amount', 0):.6f}")
        if order.get("price"):
            print(f"Price: ${order.get('price'):,.2f}")
        else:
            print(f"Price: MARKET")
        print(f"Status: {(order.get('status') or 'N/A').upper()}")

        if order.get("filled"):
            print(f"Filled: {order.get('filled', 0):.6f}")
        if order.get("remaining"):
            print(f"Remaining: {order.get('remaining', 0):.6f}")
        if order.get("cost"):
            print(f"Cost: ${order.get('cost', 0):,.2f}")
        if order.get("average"):
            print(f"Average Price: ${order.get('average', 0):,.2f}")

        print(f"{'='*60}\n")

        return order

    except Exception as e:
        print(f"\n✗ Error placing order: {str(e)}")
        raise


def ccxt_main():
    """
    Command-line interface for placing orders.
    """
    parser = argparse.ArgumentParser(
        description="Place market or limit orders on Hyperliquid exchange",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Market order to buy $100 worth of BTC
  python make_order.py --symbol BTC/USDC:USDC --notional 100 --side buy --type market
  
  # Limit order to sell $50 worth of ETH at $3000
  python make_order.py --symbol ETH/USDC:USDC --notional 50 --side sell --type limit --price 3000
  
  # Market order to buy $200 worth of SOL
  python make_order.py --symbol SOL/USDC:USDC --notional 200 --side buy --type market

Environment Variables Required:
  HL_API: Your Hyperliquid API key (wallet address)
  HL_SECRET: Your Hyperliquid secret key
        """,
    )

    parser.add_argument(
        "--symbol",
        "-s",
        required=True,
        help="Trading pair symbol (e.g., BTC/USDC:USDC, ETH/USDC:USDC)",
    )
    parser.add_argument(
        "--notional", "-n", type=float, required=True, help="Notional amount in USD/USDC to trade"
    )
    parser.add_argument(
        "--side", "-d", required=True, choices=["buy", "sell"], help="Order side: buy or sell"
    )
    parser.add_argument(
        "--type",
        "-t",
        required=True,
        choices=["market", "limit"],
        help="Order type: market or limit",
    )
    parser.add_argument(
        "--price",
        "-p",
        type=float,
        default=None,
        help="Price for limit orders (required for limit orders)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Show full order details")

    args = parser.parse_args()

    try:
        # Place the order
        order = ccxt_make_order(
            symbol=args.symbol,
            notional_amount=args.notional,
            side=args.side,
            order_type=args.type,
            price=args.price,
        )

        # Print full details if verbose
        if args.verbose:
            print("\nFull Order Details:")
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
    ccxt_main()
