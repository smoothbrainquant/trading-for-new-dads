import ccxt
import pandas as pd

def ccxt_get_hyperliquid_perpetual_futures():
    """
    Fetch all perpetual futures markets from Hyperliquid exchange.
    
    Returns:
        DataFrame containing perpetual futures market information
    """
    # Initialize Hyperliquid exchange
    exchange = ccxt.hyperliquid({
        'enableRateLimit': True,
    })
    
    try:
        print("Loading Hyperliquid markets...")
        
        # Fetch all markets
        markets = exchange.load_markets()
        
        # Filter for perpetual futures (type = 'swap')
        perpetual_futures = []
        
        for symbol, market in markets.items():
            if market.get('type') == 'swap' or market.get('swap') == True:
                perpetual_futures.append({
                    'symbol': symbol,
                    'id': market.get('id'),
                    'base': market.get('base'),
                    'quote': market.get('quote'),
                    'settle': market.get('settle'),
                    'contract': market.get('contract'),
                    'linear': market.get('linear'),
                    'inverse': market.get('inverse'),
                    'active': market.get('active'),
                    'contractSize': market.get('contractSize'),
                    'type': market.get('type'),
                })
        
        # Create DataFrame
        df = pd.DataFrame(perpetual_futures)
        
        # Sort by symbol
        if not df.empty:
            df = df.sort_values('symbol').reset_index(drop=True)
        
        return df
        
    except Exception as e:
        print(f"Error fetching markets: {str(e)}")
        return None

def display_markets(df):
    """
    Display the perpetual futures markets in a formatted way.
    
    Args:
        df: DataFrame containing market information
    """
    if df is None or df.empty:
        print("No perpetual futures found.")
        return
    
    print(f"\n{'='*80}")
    print(f"Found {len(df)} perpetual futures markets on Hyperliquid")
    print(f"{'='*80}\n")
    
    # Display main columns
    display_cols = ['symbol', 'base', 'quote', 'settle', 'active', 'linear']
    print(df[display_cols].to_string(index=False))
    
    print(f"\n{'='*80}")
    print(f"\nSummary:")
    print(f"  Total Markets: {len(df)}")
    print(f"  Active Markets: {df['active'].sum() if 'active' in df.columns else 'N/A'}")
    print(f"  Linear Contracts: {df['linear'].sum() if 'linear' in df.columns else 'N/A'}")
    print(f"  Inverse Contracts: {df['inverse'].sum() if 'inverse' in df.columns else 'N/A'}")
    
    # List of base currencies
    if 'base' in df.columns:
        unique_bases = df['base'].unique()
        print(f"\n  Base Currencies ({len(unique_bases)}): {', '.join(sorted(unique_bases)[:10])}")
        if len(unique_bases) > 10:
            print(f"    ... and {len(unique_bases) - 10} more")
    
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    print("Fetching perpetual futures markets from Hyperliquid...")
    
    # Get all perpetual futures
    markets_df = ccxt_get_hyperliquid_perpetual_futures()
    
    # Select top 10 instruments
    if markets_df is not None and not markets_df.empty:
        print(f"\nTotal markets found: {len(markets_df)}")
        print("Selecting top 10 instruments (sorted alphabetically)...")
        markets_df = markets_df.head(10)
    
    # Display results
    display_markets(markets_df)
    
    # Optionally, save to CSV
    if markets_df is not None and not markets_df.empty:
        csv_filename = 'hyperliquid_perpetual_futures.csv'
        markets_df.to_csv(csv_filename, index=False)
        print(f"Market data saved to {csv_filename}")
