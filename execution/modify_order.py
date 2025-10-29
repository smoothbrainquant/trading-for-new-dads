import ccxt
import os
import argparse
from pprint import pprint


def modify_order(order_id, symbol, new_price=None, new_amount=None):
    """
    Modify an existing order on Hyperliquid exchange with new price and/or new amount.

    Args:
        order_id: The ID of the order to modify
        symbol: Trading pair (e.g., 'BTC/USDC:USDC', 'ETH/USDC:USDC')
        new_price: New price for the order (optional, keeps existing if not provided)
        new_amount: New notional amount in USD/USDC (optional, keeps existing if not provided)

    Requires environment variables:
        HL_API: Hyperliquid API key (wallet address)
        HL_SECRET: Hyperliquid secret key

    Returns:
        Dictionary containing modified order response
    """
    # Get API credentials from environment variables
    api_key = os.getenv("HL_API")
    secret_key = os.getenv("HL_SECRET")

    if not api_key or not secret_key:
        raise ValueError("Missing required environment variables: HL_API and/or HL_SECRET")

    # Validate inputs
    if not order_id:
        raise ValueError("Order ID is required")

    if not symbol:
        raise ValueError("Symbol is required")

    if new_price is None and new_amount is None:
        raise ValueError("At least one of new_price or new_amount must be provided")

    if new_price is not None and new_price <= 0:
        raise ValueError("New price must be positive")

    if new_amount is not None and new_amount <= 0:
        raise ValueError("New amount must be positive")

    # Initialize Hyperliquid exchange with authentication
    exchange = ccxt.hyperliquid(
        {
            "privateKey": secret_key,
            "walletAddress": api_key,
            "enableRateLimit": True,
        }
    )

    try:
        # First, fetch the existing order to get current details
        print(f"\nFetching existing order {order_id}...")
        existing_order = exchange.fetch_order(order_id, symbol)

        print(f"\nCurrent order details:")
        print(f"  Order ID: {existing_order.get('id', 'N/A')}")
        print(f"  Symbol: {existing_order.get('symbol', 'N/A')}")
        print(f"  Type: {(existing_order.get('type') or 'N/A').upper()}")
        print(f"  Side: {(existing_order.get('side') or 'N/A').upper()}")
        print(f"  Amount: {existing_order.get('amount', 0):.6f}")
        print(f"  Price: ${existing_order.get('price', 0):,.2f}")
        print(f"  Status: {(existing_order.get('status') or 'N/A').upper()}")

        # Get order details
        order_type = existing_order.get("type", "limit")
        order_side = existing_order.get("side", "buy")
        current_price = existing_order.get("price")
        current_amount = existing_order.get("amount")

        # Check if order can be modified
        order_status = existing_order.get("status", "").lower()
        if order_status not in ["open", "pending"]:
            raise ValueError(f"Order cannot be modified. Current status: {order_status.upper()}")

        # Determine final price and amount
        # If new_price is provided, use it; otherwise keep current price
        final_price = new_price if new_price is not None else current_price

        # If new_amount (notional) is provided, calculate the quantity based on final_price
        # Otherwise keep current amount
        if new_amount is not None:
            final_quantity = new_amount / final_price
        else:
            final_quantity = current_amount

        print(f"\nModifying order to:")
        print(
            f"  New Price: ${final_price:,.2f}"
            + (" (modified)" if new_price is not None else " (unchanged)")
        )
        print(
            f"  New Quantity: {final_quantity:.6f}"
            + (" (modified)" if new_amount is not None else " (unchanged)")
        )
        if new_amount is not None:
            print(f"  New Notional: ${new_amount:,.2f}")
        else:
            print(f"  Notional: ${(final_quantity * final_price):,.2f}")

        # Confirm before modifying order
        print(f"\n{'='*60}")
        print("MODIFYING ORDER...")
        print(f"{'='*60}\n")

        # Modify the order using edit_order
        modified_order = exchange.edit_order(
            id=order_id,
            symbol=symbol,
            type=order_type,
            side=order_side,
            amount=final_quantity,
            price=final_price,
        )

        print("✓ Order modified successfully!")
        print(f"\n{'='*60}")
        print("MODIFIED ORDER SUMMARY")
        print(f"{'='*60}")
        print(f"Order ID: {modified_order.get('id', 'N/A')}")
        print(f"Symbol: {modified_order.get('symbol', 'N/A')}")
        print(f"Type: {(modified_order.get('type') or 'N/A').upper()}")
        print(f"Side: {(modified_order.get('side') or 'N/A').upper()}")

        # Handle potentially None values
        amount = modified_order.get("amount")
        price = modified_order.get("price")
        status = modified_order.get("status")

        if amount is not None:
            print(f"Amount: {amount:.6f}")
        else:
            print(f"Amount: N/A")

        if price is not None:
            print(f"Price: ${price:,.2f}")
        else:
            print(f"Price: N/A")

        if status is not None:
            print(f"Status: {status.upper()}")
        else:
            print(f"Status: N/A")

        if modified_order.get("filled"):
            print(f"Filled: {modified_order.get('filled', 0):.6f}")
        if modified_order.get("remaining"):
            print(f"Remaining: {modified_order.get('remaining', 0):.6f}")
        if modified_order.get("cost"):
            print(f"Cost: ${modified_order.get('cost', 0):,.2f}")
        if modified_order.get("average"):
            print(f"Average Price: ${modified_order.get('average', 0):,.2f}")

        print(f"{'='*60}\n")

        return modified_order

    except Exception as e:
        print(f"\n✗ Error modifying order: {str(e)}")
        raise


def main():
    """
    Command-line interface for modifying orders.
    """
    parser = argparse.ArgumentParser(
        description="Modify an existing order on Hyperliquid exchange",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Modify order price to $65000
  python3 modify_order.py --order-id 12345 --symbol BTC/USDC:USDC --price 65000
  
  # Modify order amount to $200 notional
  python3 modify_order.py --order-id 12345 --symbol BTC/USDC:USDC --amount 200
  
  # Modify both price and amount
  python3 modify_order.py --order-id 12345 --symbol ETH/USDC:USDC --price 3500 --amount 100

Environment Variables Required:
  HL_API: Your Hyperliquid API key (wallet address)
  HL_SECRET: Your Hyperliquid secret key
        """,
    )

    parser.add_argument("--order-id", "-o", required=True, help="ID of the order to modify")
    parser.add_argument(
        "--symbol",
        "-s",
        required=True,
        help="Trading pair symbol (e.g., BTC/USDC:USDC, ETH/USDC:USDC)",
    )
    parser.add_argument("--price", "-p", type=float, default=None, help="New price for the order")
    parser.add_argument(
        "--amount", "-a", type=float, default=None, help="New notional amount in USD/USDC"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Show full order details")

    args = parser.parse_args()

    try:
        # Modify the order
        order = modify_order(
            order_id=args.order_id, symbol=args.symbol, new_price=args.price, new_amount=args.amount
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
    main()
