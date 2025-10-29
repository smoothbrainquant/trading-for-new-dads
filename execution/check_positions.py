"""
Position checking and validation module.
Provides utilities to check and analyze current trading positions.
"""

from ccxt_get_positions import ccxt_get_positions


def check_positions():
    """
    Check current positions and return structured information.

    Returns:
        dict: Dictionary containing position summary and details
    """
    positions = ccxt_get_positions()

    # Filter for non-zero positions
    active_positions = [pos for pos in positions if pos.get("contracts", 0) != 0]

    # Calculate summary statistics
    total_unrealized_pnl = sum(pos.get("unrealizedPnl", 0) for pos in active_positions)

    result = {
        "total_positions": len(active_positions),
        "total_unrealized_pnl": total_unrealized_pnl,
        "positions": active_positions,
        "symbols": [pos.get("symbol") for pos in active_positions],
    }

    return result


def get_position_weights(positions_data):
    """
    Calculate current position weights based on notional values.

    Args:
        positions_data (dict): Position data from check_positions()

    Returns:
        dict: Dictionary mapping symbols to their portfolio weights
    """
    positions = positions_data.get("positions", [])

    if not positions:
        return {}

    # Calculate notional value for each position
    notional_values = {}
    total_notional = 0

    for pos in positions:
        symbol = pos.get("symbol")
        contracts = abs(pos.get("contracts", 0))
        mark_price = pos.get("markPrice", 0)

        notional = contracts * mark_price
        notional_values[symbol] = notional
        total_notional += notional

    # Calculate weights
    weights = {}
    if total_notional > 0:
        for symbol, notional in notional_values.items():
            weights[symbol] = notional / total_notional

    return weights


if __name__ == "__main__":
    print("Checking positions...")
    print("=" * 60)

    try:
        positions_data = check_positions()
        print(f"\nTotal active positions: {positions_data['total_positions']}")
        print(f"Total unrealized PnL: ${positions_data['total_unrealized_pnl']:.2f}")
        print(f"\nActive symbols: {', '.join(positions_data['symbols'])}")

        if positions_data["positions"]:
            print("\nPosition details:")
            for pos in positions_data["positions"]:
                print(f"\n  {pos.get('symbol')}:")
                print(f"    Side: {pos.get('side')}")
                print(f"    Contracts: {pos.get('contracts')}")
                print(f"    Entry Price: ${pos.get('entryPrice', 0):.2f}")
                print(f"    Mark Price: ${pos.get('markPrice', 0):.2f}")
                print(f"    Unrealized PnL: ${pos.get('unrealizedPnl', 0):.2f}")

            print("\nPosition weights:")
            weights = get_position_weights(positions_data)
            for symbol, weight in weights.items():
                print(f"  {symbol}: {weight*100:.2f}%")
    except Exception as e:
        print(f"Error: {str(e)}")
