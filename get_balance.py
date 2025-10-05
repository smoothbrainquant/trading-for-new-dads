import ccxt
import os
from pprint import pprint

def get_hyperliquid_balance():
    """
    Fetch account balance from Hyperliquid exchange.
    
    Requires environment variables:
        HL_API: Hyperliquid API key
        HL_SECRET: Hyperliquid secret key
    
    Returns:
        Dictionary containing account balance information
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
    })
    
    try:
        # Fetch account balance
        balance = exchange.fetch_balance()
        
        return balance
        
    except Exception as e:
        print(f"Error fetching balance: {str(e)}")
        raise

def print_balance_summary(balance):
    """
    Print a formatted summary of the account balance.
    
    Args:
        balance: Balance dictionary returned from fetch_balance()
    """
    print("\n" + "=" * 60)
    print("HYPERLIQUID ACCOUNT BALANCE")
    print("=" * 60)
    
    # Print total balances
    if 'total' in balance:
        print("\nTotal Balances:")
        for currency, amount in balance['total'].items():
            if amount > 0:
                print(f"  {currency}: {amount}")
    
    # Print free (available) balances
    if 'free' in balance:
        print("\nAvailable Balances:")
        for currency, amount in balance['free'].items():
            if amount > 0:
                print(f"  {currency}: {amount}")
    
    # Print used (locked) balances
    if 'used' in balance:
        print("\nLocked Balances:")
        for currency, amount in balance['used'].items():
            if amount > 0:
                print(f"  {currency}: {amount}")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    try:
        print("Fetching Hyperliquid account balance...")
        
        # Fetch balance
        balance = get_hyperliquid_balance()
        
        # Print formatted summary
        print_balance_summary(balance)
        
        # Optionally print full balance details
        print("\nFull Balance Details:")
        pprint(balance)
        
    except ValueError as e:
        print(f"\nConfiguration Error: {e}")
        print("\nPlease set the following environment variables:")
        print("  export HL_API='your_api_key'")
        print("  export HL_SECRET='your_secret_key'")
    except Exception as e:
        print(f"\nError: {e}")
