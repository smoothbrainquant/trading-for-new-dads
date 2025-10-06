import ccxt
import os

def ccxt_get_positions():
    """
    Fetch account positions from Hyperliquid using API credentials.
    
    Returns:
        List of position dictionaries containing position details
    """
    # Get API credentials from environment variables
    api_key = os.getenv('HL_API')
    api_secret = os.getenv('HL_SECRET')
    
    if not api_key or not api_secret:
        raise ValueError("HL_API and HL_SECRET environment variables must be set")
    
    # Initialize Hyperliquid exchange with authentication
    exchange = ccxt.hyperliquid({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
    })
    
    try:
        # Fetch account positions
        positions = exchange.fetch_positions()
        return positions
    except Exception as e:
        print(f"Error fetching positions: {str(e)}")
        raise

if __name__ == "__main__":
    print("Fetching Hyperliquid positions...")
    print("=" * 60)
    
    try:
        positions = ccxt_get_positions()
        print(f"\nFound {len(positions)} positions:")
        for pos in positions:
            if pos.get('contracts', 0) != 0:  # Only show non-zero positions
                print(f"\nSymbol: {pos.get('symbol')}")
                print(f"  Side: {pos.get('side')}")
                print(f"  Contracts: {pos.get('contracts')}")
                print(f"  Entry Price: {pos.get('entryPrice')}")
                print(f"  Mark Price: {pos.get('markPrice')}")
                print(f"  Unrealized PnL: {pos.get('unrealizedPnl')}")
    except Exception as e:
        print(f"Failed to fetch positions: {str(e)}")
