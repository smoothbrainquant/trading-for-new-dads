import ccxt
import os
from pprint import pprint

def get_hyperliquid_balance():
    """
    Fetch account balance from Hyperliquid exchange.
    Fetches both perp (swap) and spot account balances.
    
    Requires environment variables:
        HL_API: Hyperliquid API key (wallet address)
        HL_SECRET: Hyperliquid secret key
    
    Returns:
        Dictionary containing both perp and spot account balance information
    """
    # Get API credentials from environment variables
    api_key = os.getenv('HL_API')
    secret_key = os.getenv('HL_SECRET')
    
    if not api_key or not secret_key:
        raise ValueError("Missing required environment variables: HL_API and/or HL_SECRET")
    
    # Initialize Hyperliquid exchange with authentication
    exchange = ccxt.hyperliquid({
        'apiKey': api_key,
        'secret': secret_key,
        'enableRateLimit': True,
        'walletAddress': api_key,  # Use the API key as wallet address
    })
    
    try:
        # Fetch perp (swap) account balance - includes marginSummary
        perp_balance = exchange.fetch_balance({'user': api_key, 'type': 'swap'})
        
        # Fetch spot account balance
        spot_balance = exchange.fetch_balance({'user': api_key, 'type': 'spot'})
        
        return {
            'perp': perp_balance,
            'spot': spot_balance
        }
        
    except Exception as e:
        print(f"Error fetching balance: {str(e)}")
        raise

def print_balance_summary(balances):
    """
    Print a formatted summary of the account balance.
    
    Args:
        balances: Dictionary with 'perp' and 'spot' balance data
    """
    print("\n" + "=" * 80)
    print("HYPERLIQUID ACCOUNT BALANCE")
    print("=" * 80)
    
    # Print perp account balance
    perp_balance = balances.get('perp', {})
    print("\n" + "-" * 80)
    print("PERP ACCOUNT (Perpetuals Trading)")
    print("-" * 80)
    
    # Extract margin summary from perp info
    perp_info = perp_balance.get('info', {})
    margin_summary = perp_info.get('marginSummary', {})
    cross_margin_summary = perp_info.get('crossMarginSummary', {})
    withdrawable = perp_info.get('withdrawable', 0)
    
    if margin_summary:
        print("\nMargin Summary:")
        print(f"  Account Value:      ${float(margin_summary.get('accountValue', 0)):,.2f}")
        print(f"  Total Margin Used:  ${float(margin_summary.get('totalMarginUsed', 0)):,.2f}")
        print(f"  Total Raw USD:      ${float(margin_summary.get('totalRawUsd', 0)):,.2f}")
        print(f"  Total Position:     ${float(margin_summary.get('totalNtlPos', 0)):,.2f}")
        print(f"  Withdrawable:       ${float(withdrawable):,.2f}")
    
    if cross_margin_summary and cross_margin_summary != margin_summary:
        print("\nCross Margin Summary:")
        print(f"  Account Value:      ${float(cross_margin_summary.get('accountValue', 0)):,.2f}")
        print(f"  Total Margin Used:  ${float(cross_margin_summary.get('totalMarginUsed', 0)):,.2f}")
    
    # Print perp asset positions if any
    asset_positions = perp_info.get('assetPositions', [])
    if asset_positions:
        print("\nActive Positions:")
        for asset_pos in asset_positions:
            position = asset_pos.get('position', {})
            coin = position.get('coin', 'Unknown')
            szi = position.get('szi', 0)
            entry_px = position.get('entryPx', 0)
            position_value = position.get('positionValue', 0)
            unrealized_pnl = position.get('unrealizedPnl', 0)
            leverage_info = position.get('leverage', {})
            leverage_val = leverage_info.get('value', 0) if isinstance(leverage_info, dict) else leverage_info
            
            print(f"  {coin}:")
            print(f"    Size: {szi}")
            print(f"    Entry Price: ${entry_px}")
            print(f"    Position Value: ${float(position_value):,.2f}")
            print(f"    Unrealized PnL: ${float(unrealized_pnl):,.2f}")
            print(f"    Leverage: {leverage_val}x")
    
    # Standard CCXT balance fields for perp
    if 'total' in perp_balance:
        print("\nPerp Balances (CCXT Format):")
        for currency, amount in perp_balance['total'].items():
            if amount and amount > 0:
                used = perp_balance.get('used', {}).get(currency, 0)
                free = perp_balance.get('free', {}).get(currency, 0)
                print(f"  {currency}:")
                print(f"    Total: ${amount:,.2f}")
                if used:
                    print(f"    Used:  ${used:,.2f}")
                if free:
                    print(f"    Free:  ${free:,.2f}")
    
    # Print spot account balance
    spot_balance = balances.get('spot', {})
    print("\n" + "-" * 80)
    print("SPOT ACCOUNT (Spot Trading)")
    print("-" * 80)
    
    # Print spot balances
    has_spot_balance = False
    if 'total' in spot_balance:
        for currency, amount in spot_balance['total'].items():
            if amount and amount > 0:
                if not has_spot_balance:
                    print("\nSpot Balances:")
                    has_spot_balance = True
                used = spot_balance.get('used', {}).get(currency, 0)
                free = spot_balance.get('free', {}).get(currency, 0)
                print(f"  {currency}:")
                print(f"    Total: {amount:,.6f}")
                if used:
                    print(f"    Used:  {used:,.6f}")
                if free:
                    print(f"    Free:  {free:,.6f}")
    
    if not has_spot_balance:
        print("\nNo spot balances found.")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    try:
        print("Fetching Hyperliquid account balance (Perp + Spot)...")
        
        # Fetch balance
        balances = get_hyperliquid_balance()
        
        # Print formatted summary
        print_balance_summary(balances)
        
        # Optionally print full balance details
        print("\nFull Balance Details:")
        print("\n--- PERP BALANCE ---")
        pprint(balances['perp'])
        print("\n--- SPOT BALANCE ---")
        pprint(balances['spot'])
        
    except ValueError as e:
        print(f"\nConfiguration Error: {e}")
        print("\nPlease set the following environment variables:")
        print("  export HL_API='your_api_key'")
        print("  export HL_SECRET='your_secret_key'")
    except Exception as e:
        print(f"\nError: {e}")
