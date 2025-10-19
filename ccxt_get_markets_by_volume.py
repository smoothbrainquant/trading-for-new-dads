import ccxt
import pandas as pd

def ccxt_get_markets_by_volume():
    """
    Fetch all markets from Hyperliquid exchange with 24h notional volume.
    Filters out stablecoins and spot markets from the results.
    
    Returns:
        DataFrame containing markets sorted by 24h notional volume (highest first)
    """
    # List of stablecoins to filter out
    STABLECOINS = {
        'USDT', 'USDC', 'DAI', 'BUSD', 'USDD', 'TUSD', 'FRAX', 'LUSD',
        'UST', 'GUSD', 'USDP', 'PYUSD', 'FDUSD', 'USDE', 'CUSD', 'SUSD',
        'MIM', 'USDN', 'FEI', 'TRIBE', 'RAI', 'OUSD', 'USDX', 'USDJ',
        'USTC', 'HUSD', 'EURS', 'EURT', 'EUROC', 'AGEUR', 'CEUR', 'JEUR'
    }
    
    # Initialize Hyperliquid exchange
    exchange = ccxt.hyperliquid({
        'enableRateLimit': True,
    })
    
    try:
        print("Loading Hyperliquid markets...")
        
        # Fetch all markets
        markets = exchange.load_markets()
        
        print(f"Found {len(markets)} markets. Fetching tickers with volume data...")
        
        # Fetch all tickers (contains volume information)
        tickers = exchange.fetch_tickers()
        
        # Prepare market data with volume
        market_data = []
        
        for symbol, ticker in tickers.items():
            if symbol in markets:
                market = markets[symbol]
                
                # Calculate notional volume (volume * last price)
                volume = ticker.get('quoteVolume', 0) or 0  # This is already notional volume
                base_volume = ticker.get('baseVolume', 0) or 0
                last_price = ticker.get('last', 0) or 0
                
                # If quoteVolume is not available, calculate from baseVolume
                if volume == 0 and base_volume > 0 and last_price > 0:
                    volume = base_volume * last_price
                
                market_data.append({
                    'symbol': symbol,
                    'type': market.get('type'),
                    'base': market.get('base'),
                    'quote': market.get('quote'),
                    'last_price': last_price,
                    'base_volume_24h': base_volume,
                    'notional_volume_24h': volume,
                    'bid': ticker.get('bid', 0),
                    'ask': ticker.get('ask', 0),
                    'high_24h': ticker.get('high', 0),
                    'low_24h': ticker.get('low', 0),
                    'change_24h': ticker.get('change', 0),
                    'percentage_24h': ticker.get('percentage', 0),
                    'active': market.get('active'),
                })
        
        # Create DataFrame
        df = pd.DataFrame(market_data)
        
        # Filter out stablecoins
        if not df.empty:
            initial_count = len(df)
            df = df[~df['base'].isin(STABLECOINS)].copy()
            filtered_count = initial_count - len(df)
            if filtered_count > 0:
                print(f"Filtered out {filtered_count} stablecoin markets")
        
        # Filter out spot markets
        if not df.empty:
            initial_count = len(df)
            df = df[df['type'] != 'spot'].copy()
            filtered_count = initial_count - len(df)
            if filtered_count > 0:
                print(f"Filtered out {filtered_count} spot markets")
        
        # Sort by notional volume (highest first)
        if not df.empty:
            df = df.sort_values('notional_volume_24h', ascending=False).reset_index(drop=True)
        
        return df
        
    except Exception as e:
        print(f"Error fetching markets: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def display_markets_by_volume(df, top_n=50):
    """
    Display the markets sorted by 24h notional volume.
    
    Args:
        df: DataFrame containing market information with volume
        top_n: Number of top markets to display (default: 50)
    """
    if df is None or df.empty:
        print("No markets found.")
        return
    
    print(f"\n{'='*120}")
    print(f"Hyperliquid Markets Ranked by 24h Notional Volume")
    print(f"{'='*120}\n")
    
    # Display top N markets
    display_df = df.head(top_n).copy()
    
    # Format the numbers for better readability
    display_df['notional_volume_24h_formatted'] = display_df['notional_volume_24h'].apply(
        lambda x: f"${x:,.0f}" if x >= 1000 else f"${x:.2f}"
    )
    display_df['base_volume_24h_formatted'] = display_df['base_volume_24h'].apply(
        lambda x: f"{x:,.2f}" if x > 0 else "0"
    )
    display_df['last_price_formatted'] = display_df['last_price'].apply(
        lambda x: f"${x:,.4f}" if x < 10 else f"${x:,.2f}"
    )
    display_df['percentage_24h_formatted'] = display_df['percentage_24h'].apply(
        lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A"
    )
    
    # Select columns to display
    display_cols = {
        'symbol': 'Symbol',
        'type': 'Type',
        'last_price_formatted': 'Last Price',
        'base_volume_24h_formatted': 'Base Volume (24h)',
        'notional_volume_24h_formatted': 'Notional Volume (24h)',
        'percentage_24h_formatted': 'Change (24h)'
    }
    
    output_df = display_df[list(display_cols.keys())].copy()
    output_df.columns = list(display_cols.values())
    
    print(output_df.to_string(index=True))
    
    print(f"\n{'='*120}")
    print(f"\nSummary:")
    print(f"  Total Markets: {len(df)}")
    print(f"  Active Markets: {df['active'].sum() if 'active' in df.columns else 'N/A'}")
    
    # Total volume statistics
    total_volume = df['notional_volume_24h'].sum()
    print(f"\n  Total 24h Notional Volume (All Markets): ${total_volume:,.0f}")
    
    top_10_volume = df.head(10)['notional_volume_24h'].sum()
    top_10_percentage = (top_10_volume / total_volume * 100) if total_volume > 0 else 0
    print(f"  Top 10 Markets Volume: ${top_10_volume:,.0f} ({top_10_percentage:.1f}% of total)")
    
    # Market type breakdown
    if 'type' in df.columns:
        type_counts = df['type'].value_counts()
        print(f"\n  Market Types:")
        for market_type, count in type_counts.items():
            print(f"    {market_type}: {count}")
    
    print(f"\n{'='*120}\n")

def save_to_csv(df, filename='hyperliquid_markets_by_volume.csv'):
    """
    Save the markets data to a CSV file.
    
    Args:
        df: DataFrame containing market information
        filename: Name of the CSV file to save
    """
    if df is not None and not df.empty:
        df.to_csv(filename, index=False)
        print(f"Market data saved to {filename}")
        return True
    return False

if __name__ == "__main__":
    print("Fetching Hyperliquid markets with 24h notional volume...")
    print("This may take a moment...\n")
    
    # Get all markets with volume data
    markets_df = ccxt_get_markets_by_volume()
    
    # Display results
    if markets_df is not None and not markets_df.empty:
        # Show top 50 by default
        display_markets_by_volume(markets_df, top_n=50)
        
        # Save to CSV
        save_to_csv(markets_df)
        
        # Show some interesting statistics
        print("\nTop 5 Markets by 24h Notional Volume:")
        for idx, row in markets_df.head(5).iterrows():
            print(f"  {idx+1}. {row['symbol']}: ${row['notional_volume_24h']:,.0f}")
    else:
        print("Failed to fetch market data.")
