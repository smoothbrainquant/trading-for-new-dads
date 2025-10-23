"""
Fetch Market Cap Data from CoinMarketCap

This script fetches current market cap data for cryptocurrencies from CoinMarketCap API.
Market cap is used for size factor analysis where smaller cap coins may exhibit
different return characteristics compared to large cap coins.
"""

import requests
import pandas as pd
import json
import os
from datetime import datetime


def fetch_coinmarketcap_data(api_key=None, limit=100, convert='USD'):
    """
    Fetch cryptocurrency market cap data from CoinMarketCap.
    
    Args:
        api_key (str): CoinMarketCap API key. If None, tries to read from CMC_API_KEY env var
        limit (int): Number of cryptocurrencies to fetch (max 5000)
        convert (str): Currency for conversion (default USD)
        
    Returns:
        pd.DataFrame: DataFrame with symbol, name, market_cap, price, volume_24h, etc.
    """
    # Get API key from environment if not provided
    if api_key is None:
        api_key = os.environ.get('CMC_API_KEY')
        if not api_key:
            print("WARNING: No CoinMarketCap API key found.")
            print("Please set CMC_API_KEY environment variable or use demo mode.")
            print("Using demo/mock data instead...")
            return fetch_mock_marketcap_data(limit)
    
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
    
    parameters = {
        'start': '1',
        'limit': str(limit),
        'convert': convert,
        'sort': 'market_cap',
        'sort_dir': 'desc'
    }
    
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': api_key,
    }
    
    try:
        print(f"Fetching top {limit} cryptocurrencies from CoinMarketCap...")
        response = requests.get(url, headers=headers, params=parameters)
        response.raise_for_status()
        
        data = response.json()
        
        if 'data' not in data:
            print(f"ERROR: Unexpected API response structure")
            return fetch_mock_marketcap_data(limit)
        
        # Parse the data
        coins_data = []
        for coin in data['data']:
            quote = coin['quote'][convert]
            coins_data.append({
                'symbol': coin['symbol'],
                'name': coin['name'],
                'cmc_rank': coin['cmc_rank'],
                'market_cap': quote['market_cap'],
                'price': quote['price'],
                'volume_24h': quote['volume_24h'],
                'percent_change_24h': quote['percent_change_24h'],
                'percent_change_7d': quote['percent_change_7d'],
                'market_cap_dominance': quote['market_cap_dominance'],
                'timestamp': datetime.now().isoformat()
            })
        
        df = pd.DataFrame(coins_data)
        print(f"Successfully fetched {len(df)} cryptocurrencies")
        return df
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR fetching from CoinMarketCap: {e}")
        print("Using mock data instead...")
        return fetch_mock_marketcap_data(limit)


def fetch_mock_marketcap_data(limit=100):
    """
    Generate mock market cap data for testing when API key is not available.
    This uses approximate values based on typical crypto market structure.
    
    Args:
        limit (int): Number of cryptocurrencies to generate
        
    Returns:
        pd.DataFrame: Mock market cap data
    """
    import numpy as np
    
    # Common crypto symbols (top cryptocurrencies)
    common_symbols = [
        'BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'AVAX', 'DOGE', 'DOT', 'MATIC',
        'LTC', 'LINK', 'UNI', 'ATOM', 'ARB', 'OP', 'APT', 'SUI', 'INJ', 'TIA',
        'SEI', 'STX', 'FET', 'NEAR', 'GRT', 'RUNE', 'AAVE', 'MKR', 'SNX', 'CRV',
        'COMP', 'YFI', 'SUSHI', 'BAL', '1INCH', 'ENJ', 'SAND', 'MANA', 'AXS', 'IMX',
        'BLUR', 'LDO', 'RPL', 'FXS', 'CVX', 'DYDX', 'GMX', 'GNS', 'PERP', 'JOE'
    ]
    
    coins_data = []
    
    # Generate market caps following power law distribution (Zipf's law)
    # Large caps dominate, then exponential decline
    base_market_cap = 1_000_000_000_000  # $1T for #1 (BTC-like)
    
    for i in range(min(limit, len(common_symbols) * 2)):
        rank = i + 1
        
        # Power law for market cap
        market_cap = base_market_cap / (rank ** 1.5)
        
        # Add some randomness
        market_cap *= np.random.uniform(0.8, 1.2)
        
        # Price and volume correlated with market cap
        price = market_cap / np.random.uniform(100_000_000, 1_000_000_000)
        volume_24h = market_cap * np.random.uniform(0.05, 0.3)
        
        symbol = common_symbols[i] if i < len(common_symbols) else f"COIN{i+1}"
        
        coins_data.append({
            'symbol': symbol,
            'name': f"{symbol} Token",
            'cmc_rank': rank,
            'market_cap': market_cap,
            'price': price,
            'volume_24h': volume_24h,
            'percent_change_24h': np.random.uniform(-10, 10),
            'percent_change_7d': np.random.uniform(-20, 20),
            'market_cap_dominance': (market_cap / base_market_cap) * 100,
            'timestamp': datetime.now().isoformat()
        })
    
    df = pd.DataFrame(coins_data)
    print(f"Generated mock data for {len(df)} cryptocurrencies")
    return df


def save_marketcap_data(df, filepath='crypto_marketcap.csv'):
    """
    Save market cap data to CSV file.
    
    Args:
        df (pd.DataFrame): Market cap data
        filepath (str): Output file path
    """
    df.to_csv(filepath, index=False)
    print(f"\nMarket cap data saved to: {filepath}")
    
    # Print summary statistics
    print("\nMarket Cap Summary:")
    print(f"  Total cryptos: {len(df)}")
    print(f"  Total market cap: ${df['market_cap'].sum():,.0f}")
    print(f"  Largest market cap: {df.iloc[0]['symbol']} - ${df.iloc[0]['market_cap']:,.0f}")
    print(f"  Smallest market cap: {df.iloc[-1]['symbol']} - ${df.iloc[-1]['market_cap']:,.0f}")
    print(f"  Median market cap: ${df['market_cap'].median():,.0f}")


def map_symbols_to_trading_pairs(marketcap_df, trading_suffix='/USDC:USDC'):
    """
    Map CoinMarketCap symbols to trading pair format used in CCXT.
    
    Args:
        marketcap_df (pd.DataFrame): Market cap data with 'symbol' column
        trading_suffix (str): Suffix to add for trading pairs (default for Hyperliquid)
        
    Returns:
        pd.DataFrame: Market cap data with additional 'trading_symbol' column
    """
    df = marketcap_df.copy()
    df['trading_symbol'] = df['symbol'] + trading_suffix
    return df


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fetch Market Cap Data from CoinMarketCap',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='CoinMarketCap API key (or set CMC_API_KEY env var)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Number of cryptocurrencies to fetch'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='crypto_marketcap.csv',
        help='Output CSV file path'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("COINMARKETCAP DATA FETCH")
    print("=" * 80)
    
    # Fetch data
    df = fetch_coinmarketcap_data(api_key=args.api_key, limit=args.limit)
    
    # Add trading symbol mapping
    df = map_symbols_to_trading_pairs(df)
    
    # Display sample
    print("\nSample Data (first 10 rows):")
    display_cols = ['cmc_rank', 'symbol', 'name', 'market_cap', 'price', 'volume_24h']
    print(df[display_cols].head(10).to_string(index=False))
    
    # Save to file
    save_marketcap_data(df, args.output)
    
    print("\n" + "=" * 80)
    print("DATA FETCH COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
