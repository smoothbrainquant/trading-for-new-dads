#!/usr/bin/env python3
"""
Fetch Cryptocurrency Categories from CoinMarketCap

This script fetches category data from CoinMarketCap API including:
1. List of all categories with metadata
2. Coin membership for each category
3. Category performance statistics

References:
- CMC API Docs: https://coinmarketcap.com/api/documentation/v1/
- Categories endpoint: /v1/cryptocurrency/categories
- Category detail: /v1/cryptocurrency/category
"""

import requests
import pandas as pd
import json
import os
import time
from datetime import datetime


def fetch_category_list(api_key=None, limit=100):
    """
    Fetch list of cryptocurrency categories from CoinMarketCap.
    
    Args:
        api_key (str): CoinMarketCap API key. If None, reads from CMC_API env var
        limit (int): Number of categories to fetch
        
    Returns:
        pd.DataFrame: DataFrame with category data
    """
    if api_key is None:
        api_key = os.environ.get('CMC_API')
        if not api_key:
            print("WARNING: No CoinMarketCap API key found.")
            print("Set CMC_API environment variable to fetch real data.")
            print("Returning empty DataFrame...")
            return pd.DataFrame()
    
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/categories'
    
    parameters = {
        'start': '1',
        'limit': str(limit),
    }
    
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': api_key,
    }
    
    try:
        print(f"Fetching categories from CoinMarketCap API...")
        response = requests.get(url, headers=headers, params=parameters)
        response.raise_for_status()
        
        data = response.json()
        
        if 'data' not in data:
            print(f"ERROR: Unexpected API response structure")
            print(f"Response: {json.dumps(data, indent=2)}")
            return pd.DataFrame()
        
        # Parse the category data
        categories = []
        for cat in data['data']:
            categories.append({
                'category_id': cat.get('id'),
                'category_name': cat.get('name'),
                'title': cat.get('title'),
                'description': cat.get('description'),
                'num_tokens': cat.get('num_tokens'),
                'avg_price_change': cat.get('avg_price_change'),
                'market_cap': cat.get('market_cap'),
                'market_cap_change': cat.get('market_cap_change'),
                'volume': cat.get('volume'),
                'volume_change': cat.get('volume_change'),
                'last_updated': cat.get('last_updated'),
                'timestamp': datetime.now().isoformat()
            })
        
        df = pd.DataFrame(categories)
        print(f"Successfully fetched {len(df)} categories")
        return df
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR fetching categories from CoinMarketCap: {e}")
        return pd.DataFrame()


def fetch_category_coins(category_id, api_key=None, limit=100):
    """
    Fetch coins in a specific category.
    
    Args:
        category_id (str): Category ID from CMC
        api_key (str): CoinMarketCap API key
        limit (int): Number of coins to fetch per category
        
    Returns:
        pd.DataFrame: DataFrame with coin data for this category
    """
    if api_key is None:
        api_key = os.environ.get('CMC_API')
        if not api_key:
            return pd.DataFrame()
    
    # Note: This endpoint may not exist or may require different authentication
    # This is a placeholder - adjust based on actual CMC API capabilities
    url = f'https://pro-api.coinmarketcap.com/v1/cryptocurrency/category'
    
    parameters = {
        'id': category_id,
        'start': '1',
        'limit': str(limit),
    }
    
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': api_key,
    }
    
    try:
        response = requests.get(url, headers=headers, params=parameters)
        response.raise_for_status()
        
        data = response.json()
        
        # Parse response - structure depends on actual API response
        # This is a placeholder
        coins = []
        if 'data' in data and 'coins' in data['data']:
            for coin in data['data']['coins']:
                coins.append({
                    'category_id': category_id,
                    'symbol': coin.get('symbol'),
                    'name': coin.get('name'),
                    'cmc_rank': coin.get('cmc_rank'),
                    'market_cap': coin.get('market_cap'),
                    'price': coin.get('price'),
                    'volume_24h': coin.get('volume_24h'),
                })
        
        return pd.DataFrame(coins)
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR fetching coins for category {category_id}: {e}")
        return pd.DataFrame()


def fetch_all_category_memberships(categories_df, api_key=None, delay=1.0):
    """
    Fetch coin memberships for all categories.
    
    Args:
        categories_df (pd.DataFrame): DataFrame with category_id column
        api_key (str): CoinMarketCap API key
        delay (float): Delay between API calls to respect rate limits
        
    Returns:
        pd.DataFrame: Combined DataFrame with all category memberships
    """
    if len(categories_df) == 0:
        print("No categories to fetch memberships for")
        return pd.DataFrame()
    
    all_coins = []
    
    for idx, row in categories_df.iterrows():
        category_id = row['category_id']
        category_name = row['category_name']
        
        print(f"Fetching coins for category: {category_name} ({idx+1}/{len(categories_df)})")
        
        coins_df = fetch_category_coins(category_id, api_key=api_key)
        
        if len(coins_df) > 0:
            coins_df['category_name'] = category_name
            all_coins.append(coins_df)
        
        # Respect rate limits
        time.sleep(delay)
    
    if len(all_coins) == 0:
        print("No coin data fetched")
        return pd.DataFrame()
    
    combined = pd.concat(all_coins, ignore_index=True)
    print(f"\nTotal coin-category pairs: {len(combined)}")
    return combined


def save_category_data(categories_df, memberships_df, output_dir='data/raw'):
    """
    Save category data to CSV files.
    
    Args:
        categories_df (pd.DataFrame): Category list with metadata
        memberships_df (pd.DataFrame): Category memberships
        output_dir (str): Output directory
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if len(categories_df) > 0:
        categories_file = f'{output_dir}/cmc_categories_{timestamp}.csv'
        categories_df.to_csv(categories_file, index=False)
        print(f"\nCategories saved to: {categories_file}")
        print(f"  Total categories: {len(categories_df)}")
    
    if len(memberships_df) > 0:
        memberships_file = f'{output_dir}/cmc_category_members_{timestamp}.csv'
        memberships_df.to_csv(memberships_file, index=False)
        print(f"\nCategory memberships saved to: {memberships_file}")
        print(f"  Total coin-category pairs: {len(memberships_df)}")
        print(f"  Unique coins: {memberships_df['symbol'].nunique()}")
        print(f"  Unique categories: {memberships_df['category_name'].nunique()}")


def analyze_coverage(memberships_df, available_symbols):
    """
    Analyze coverage of CMC categories vs. available data.
    
    Args:
        memberships_df (pd.DataFrame): Category memberships from CMC
        available_symbols (list): List of symbols we have price data for
    """
    if len(memberships_df) == 0:
        print("\nNo membership data to analyze")
        return
    
    cmc_symbols = set(memberships_df['symbol'].unique())
    available_set = set(available_symbols)
    
    overlap = cmc_symbols & available_set
    cmc_only = cmc_symbols - available_set
    available_only = available_set - cmc_symbols
    
    print("\n" + "="*80)
    print("COVERAGE ANALYSIS")
    print("="*80)
    print(f"CMC categories cover: {len(cmc_symbols)} unique symbols")
    print(f"We have price data for: {len(available_set)} symbols")
    print(f"Overlap: {len(overlap)} symbols ({100*len(overlap)/len(available_set):.1f}% of our data)")
    print(f"CMC only (no price data): {len(cmc_only)} symbols")
    print(f"Price data only (no CMC category): {len(available_only)} symbols")
    
    if len(available_only) > 0:
        print(f"\nSample of symbols without CMC categories: {sorted(list(available_only))[:20]}")


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fetch Cryptocurrency Categories from CoinMarketCap',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='CoinMarketCap API key (or set CMC_API env var)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Number of categories to fetch'
    )
    parser.add_argument(
        '--fetch-members',
        action='store_true',
        help='Also fetch coin memberships for each category (slower)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/raw',
        help='Output directory for CSV files'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("COINMARKETCAP CATEGORY FETCH")
    print("=" * 80)
    
    # Fetch category list
    categories_df = fetch_category_list(api_key=args.api_key, limit=args.limit)
    
    if len(categories_df) > 0:
        print("\nCategory Summary:")
        print(categories_df[['category_name', 'num_tokens', 'market_cap', 'volume']].head(20).to_string(index=False))
    
    # Optionally fetch memberships
    memberships_df = pd.DataFrame()
    if args.fetch_members and len(categories_df) > 0:
        print("\n" + "="*80)
        print("FETCHING CATEGORY MEMBERSHIPS")
        print("="*80)
        print("NOTE: This will make multiple API calls and may take time...")
        memberships_df = fetch_all_category_memberships(categories_df, api_key=args.api_key)
    
    # Save results
    if len(categories_df) > 0 or len(memberships_df) > 0:
        save_category_data(categories_df, memberships_df, output_dir=args.output_dir)
    
    # Analyze coverage vs. our available data
    if len(memberships_df) > 0:
        # Load our available symbols
        try:
            price_df = pd.read_csv('data/raw/combined_coinbase_coinmarketcap_daily.csv')
            available_symbols = price_df['base'].unique().tolist()
            analyze_coverage(memberships_df, available_symbols)
        except Exception as e:
            print(f"Could not load price data for coverage analysis: {e}")
    
    print("\n" + "=" * 80)
    print("FETCH COMPLETE")
    print("=" * 80)
    print("\nNOTE: If no data was fetched, make sure:")
    print("  1. CMC_API environment variable is set")
    print("  2. API key has sufficient credits")
    print("  3. Category endpoints are available on your API plan")


if __name__ == "__main__":
    main()
