#!/usr/bin/env python3
"""
Fetch CoinMarketCap Tags and Metadata

This script fetches comprehensive metadata for all coins in our universe,
including tags, VC portfolios, social links, and other alternative data.

Output files:
- cmc_coin_metadata_full.csv: Complete metadata for each coin
- cmc_coin_tags.csv: Coin-to-tag mapping (long format)
- cmc_tag_coins.csv: Tag-to-coin mapping with counts
- cmc_vc_portfolios.csv: VC portfolio exposures
- cmc_tag_categories.csv: Tag categories (DeFi, Layer1, Meme, etc.)
"""

import requests
import pandas as pd
import os
import json
import time
from datetime import datetime


def get_universe_symbols():
    """Get list of all symbols we track from combined data."""
    print("Loading universe from combined data...")
    
    try:
        df = pd.read_csv("data/raw/combined_coinbase_coinmarketcap_daily.csv")
        symbols = sorted(df['base'].unique().tolist())
        print(f"Found {len(symbols)} unique symbols in universe")
        return symbols
    except FileNotFoundError:
        print("ERROR: Could not find combined data file")
        print("Using fallback top 100 symbols...")
        # Fallback to common symbols
        return [
            'BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'AVAX', 'DOGE', 'DOT', 'MATIC',
            'LTC', 'LINK', 'UNI', 'ATOM', 'ARB', 'OP', 'APT', 'SUI', 'INJ', 'TIA',
            'SEI', 'STX', 'FET', 'NEAR', 'GRT', 'RUNE', 'AAVE', 'MKR', 'SNX', 'CRV',
            'COMP', 'YFI', 'SUSHI', 'BAL', '1INCH', 'ENJ', 'SAND', 'MANA', 'AXS', 'IMX',
            'BLUR', 'LDO', 'RPL', 'FXS', 'CVX', 'DYDX', 'GMX', 'GNS', 'PERP', 'JOE',
            'ALGO', 'VET', 'FIL', 'ICP', 'HBAR', 'XLM', 'ETC', 'BCH', 'LDO', 'APE'
        ]


def fetch_coin_metadata(symbols, api_key=None, batch_size=100):
    """
    Fetch metadata for list of symbols.
    
    CMC allows up to 500 symbols per request, but we'll use batches of 100
    to stay within rate limits and avoid timeouts.
    """
    if api_key is None:
        api_key = os.environ.get("CMC_API")
        if not api_key:
            print("ERROR: No CMC_API key found in environment")
            return None
    
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/info"
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": api_key,
    }
    
    all_metadata = {}
    total_batches = (len(symbols) + batch_size - 1) // batch_size
    
    print(f"\nFetching metadata for {len(symbols)} symbols in {total_batches} batches...")
    
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        batch_num = i // batch_size + 1
        
        print(f"\nBatch {batch_num}/{total_batches}: Fetching {len(batch)} symbols...")
        print(f"  Symbols: {', '.join(batch[:5])}{'...' if len(batch) > 5 else ''}")
        
        params = {"symbol": ",".join(batch)}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data:
                    # Handle both v1 (dict) and v2 (list) response formats
                    for symbol, info in data['data'].items():
                        if isinstance(info, list):
                            # v2 format returns list, take first (main coin)
                            info = info[0]
                        all_metadata[symbol] = info
                    print(f"  ? Success: {len(data['data'])} coins fetched")
                else:
                    print(f"  ??  Warning: No data in response")
            else:
                print(f"  ? Error: HTTP {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"     {error_data.get('status', {}).get('error_message', 'Unknown error')}")
                except:
                    pass
        
        except requests.exceptions.Timeout:
            print(f"  ??  Timeout for batch {batch_num}")
        except Exception as e:
            print(f"  ? Exception: {e}")
        
        # Rate limiting: Sleep between batches
        if i + batch_size < len(symbols):
            time.sleep(1.0)  # 1 second between batches
    
    print(f"\n? Total metadata fetched: {len(all_metadata)} coins")
    return all_metadata


def parse_metadata_to_dataframe(metadata_dict):
    """Parse metadata dict into structured DataFrame."""
    rows = []
    
    for symbol, info in metadata_dict.items():
        row = {
            'symbol': symbol,
            'cmc_id': info.get('id'),
            'name': info.get('name'),
            'slug': info.get('slug'),
            'category': info.get('category'),  # coin vs token
            'description': info.get('description', '')[:500],  # Truncate long descriptions
            'logo': info.get('logo'),
            'date_added': info.get('date_added'),
            'date_launched': info.get('date_launched'),
            'is_hidden': info.get('is_hidden'),
            'infinite_supply': info.get('infinite_supply'),
            
            # Social media
            'subreddit': info.get('subreddit'),
            'twitter_username': info.get('twitter_username'),
            
            # URLs
            'website': ','.join(info.get('urls', {}).get('website', [])),
            'twitter': ','.join(info.get('urls', {}).get('twitter', [])),
            'reddit': ','.join(info.get('urls', {}).get('reddit', [])),
            'github': ','.join(info.get('urls', {}).get('source_code', [])),
            'whitepaper': ','.join(info.get('urls', {}).get('technical_doc', [])),
            
            # Platform (for tokens)
            'platform_name': info.get('platform', {}).get('name') if info.get('platform') else None,
            'platform_symbol': info.get('platform', {}).get('symbol') if info.get('platform') else None,
            
            # Tags (comma-separated for this table)
            'tags': ','.join(info.get('tags', [])) if info.get('tags') else '',
            'tag_names': ','.join(info.get('tag-names', [])) if info.get('tag-names') else '',
            'num_tags': len(info.get('tags', [])),
            
            # Timestamp
            'fetched_at': datetime.now().isoformat(),
        }
        rows.append(row)
    
    return pd.DataFrame(rows)


def create_tag_mapping(metadata_dict):
    """Create coin-to-tag mapping in long format."""
    rows = []
    
    for symbol, info in metadata_dict.items():
        tags = info.get('tags', [])
        tag_names = info.get('tag-names', [])
        tag_groups = info.get('tag-groups', [])
        
        # Ensure all lists are same length
        max_len = max(len(tags), len(tag_names), len(tag_groups))
        tags = tags + [''] * (max_len - len(tags))
        tag_names = tag_names + [''] * (max_len - len(tag_names))
        tag_groups = tag_groups + [''] * (max_len - len(tag_groups))
        
        for i, tag in enumerate(tags):
            if tag:  # Skip empty tags
                rows.append({
                    'symbol': symbol,
                    'tag': tag,
                    'tag_name': tag_names[i] if i < len(tag_names) else '',
                    'tag_group': tag_groups[i] if i < len(tag_groups) else '',
                })
    
    return pd.DataFrame(rows)


def create_tag_summary(tag_mapping_df):
    """Create summary of tags with coin counts."""
    summary = tag_mapping_df.groupby(['tag', 'tag_name', 'tag_group']).agg({
        'symbol': ['count', lambda x: ','.join(sorted(x)[:10])]  # First 10 coins
    }).reset_index()
    
    summary.columns = ['tag', 'tag_name', 'tag_group', 'num_coins', 'sample_coins']
    summary = summary.sort_values('num_coins', ascending=False)
    
    return summary


def extract_vc_portfolios(tag_mapping_df):
    """Extract VC portfolio exposures."""
    vc_tags = tag_mapping_df[tag_mapping_df['tag'].str.contains('portfolio', case=False, na=False)]
    
    # Pivot to wide format
    vc_pivot = vc_tags.pivot_table(
        index='symbol',
        columns='tag_name',
        aggfunc='size',
        fill_value=0
    )
    
    # Convert to boolean
    vc_pivot = (vc_pivot > 0).astype(int)
    
    # Add total VC count
    vc_pivot['total_vc_portfolios'] = vc_pivot.sum(axis=1)
    
    return vc_pivot.reset_index()


def categorize_tags(tag_mapping_df):
    """Categorize tags into meaningful groups."""
    categories = {
        'Layer1': ['layer-1', 'bitcoin-ecosystem', 'ethereum-ecosystem', 'solana-ecosystem', 
                   'bnb-chain-ecosystem', 'avalanche-ecosystem', 'polygon-ecosystem'],
        'Layer2': ['layer-2', 'arbitrum-ecosystem', 'optimism-ecosystem', 'zksync-ecosystem',
                   'base-ecosystem', 'polygon-zkevm-ecosystem'],
        'DeFi': ['defi', 'dex', 'lending', 'yield-farming', 'staking', 'liquid-staking',
                'amm', 'yield-aggregator', 'decentralized-exchange'],
        'Meme': ['memes', 'meme', 'dog-themed', 'cat-themed', 'frog-themed'],
        'AI': ['ai', 'artificial-intelligence', 'ai-big-data', 'ai-memes', 'artificial-intelligence-ai'],
        'Gaming': ['gaming', 'play-to-earn', 'metaverse', 'nft', 'collectibles'],
        'Infrastructure': ['oracles', 'storage', 'privacy', 'interoperability', 'cross-chain'],
        'RWA': ['real-world-assets', 'tokenized-gold', 'tokenized-real-estate'],
        'Stablecoin': ['stablecoin', 'stablecoin-protocol', 'algorithmic-stablecoin'],
        'Exchange': ['exchange-based-tokens', 'centralized-exchange', 'dex'],
    }
    
    rows = []
    for symbol in tag_mapping_df['symbol'].unique():
        symbol_tags = tag_mapping_df[tag_mapping_df['symbol'] == symbol]['tag'].tolist()
        
        row = {'symbol': symbol}
        for category, category_tags in categories.items():
            # Check if any of the category tags are in symbol's tags
            has_category = any(tag in symbol_tags for tag in category_tags)
            row[f'is_{category.lower()}'] = int(has_category)
        
        rows.append(row)
    
    return pd.DataFrame(rows)


def main():
    """Main execution."""
    print("="*80)
    print("COINMARKETCAP TAG & METADATA SCRAPER")
    print("="*80)
    
    # Get symbols
    symbols = get_universe_symbols()
    
    if not symbols:
        print("ERROR: No symbols to fetch")
        return
    
    # Fetch metadata
    metadata = fetch_coin_metadata(symbols, batch_size=100)
    
    if not metadata:
        print("ERROR: No metadata fetched")
        return
    
    print("\n" + "="*80)
    print("PARSING AND SAVING DATA")
    print("="*80)
    
    # Create DataFrames
    print("\n1. Creating full metadata table...")
    metadata_df = parse_metadata_to_dataframe(metadata)
    print(f"   ? {len(metadata_df)} coins with metadata")
    
    print("\n2. Creating tag mapping...")
    tag_mapping_df = create_tag_mapping(metadata)
    print(f"   ? {len(tag_mapping_df)} coin-tag pairs")
    print(f"   ? {tag_mapping_df['tag'].nunique()} unique tags")
    
    print("\n3. Creating tag summary...")
    tag_summary_df = create_tag_summary(tag_mapping_df)
    print(f"   ? {len(tag_summary_df)} tags summarized")
    
    print("\n4. Extracting VC portfolios...")
    vc_df = extract_vc_portfolios(tag_mapping_df)
    print(f"   ? {len(vc_df)} coins with VC portfolio data")
    print(f"   ? {vc_df.shape[1]-2} unique VC portfolios")
    
    print("\n5. Categorizing tags...")
    categories_df = categorize_tags(tag_mapping_df)
    print(f"   ? {len(categories_df)} coins categorized")
    
    # Save to files
    output_dir = "data/raw"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("\n" + "="*80)
    print("SAVING FILES")
    print("="*80)
    
    files_saved = []
    
    # 1. Full metadata
    file1 = f"{output_dir}/cmc_coin_metadata_full_{timestamp}.csv"
    metadata_df.to_csv(file1, index=False)
    print(f"\n? Saved: {file1}")
    print(f"   Columns: {', '.join(metadata_df.columns.tolist()[:5])}...")
    files_saved.append(file1)
    
    # 2. Tag mapping (long format)
    file2 = f"{output_dir}/cmc_coin_tags_{timestamp}.csv"
    tag_mapping_df.to_csv(file2, index=False)
    print(f"\n? Saved: {file2}")
    print(f"   Format: symbol, tag, tag_name, tag_group")
    files_saved.append(file2)
    
    # 3. Tag summary
    file3 = f"{output_dir}/cmc_tag_summary_{timestamp}.csv"
    tag_summary_df.to_csv(file3, index=False)
    print(f"\n? Saved: {file3}")
    files_saved.append(file3)
    
    # 4. VC portfolios
    file4 = f"{output_dir}/cmc_vc_portfolios_{timestamp}.csv"
    vc_df.to_csv(file4, index=False)
    print(f"\n? Saved: {file4}")
    files_saved.append(file4)
    
    # 5. Tag categories
    file5 = f"{output_dir}/cmc_tag_categories_{timestamp}.csv"
    categories_df.to_csv(file5, index=False)
    print(f"\n? Saved: {file5}")
    files_saved.append(file5)
    
    # 6. Save raw JSON for future reference
    file6 = f"{output_dir}/cmc_metadata_raw_{timestamp}.json"
    with open(file6, 'w') as f:
        json.dump(metadata, f, indent=2, default=str)
    print(f"\n? Saved: {file6}")
    files_saved.append(file6)
    
    # Print summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS")
    print("="*80)
    
    print(f"\n?? Coins Processed: {len(metadata_df)}")
    print(f"?? Total Tags: {tag_mapping_df['tag'].nunique()}")
    print(f"?? Total Coin-Tag Pairs: {len(tag_mapping_df)}")
    print(f"?? Avg Tags per Coin: {len(tag_mapping_df) / len(metadata_df):.1f}")
    
    print("\n?? Top 10 Most Common Tags:")
    top_tags = tag_summary_df.head(10)[['tag_name', 'num_coins']]
    for idx, row in top_tags.iterrows():
        print(f"   {row['num_coins']:3d} coins: {row['tag_name']}")
    
    print("\n?? VC Portfolio Coverage:")
    if len(vc_df) > 0:
        coins_with_vc = (vc_df['total_vc_portfolios'] > 0).sum()
        print(f"   {coins_with_vc}/{len(vc_df)} coins ({100*coins_with_vc/len(vc_df):.1f}%) have VC backing")
        print(f"   Max VCs for single coin: {vc_df['total_vc_portfolios'].max()}")
        print(f"   Avg VCs per coin: {vc_df['total_vc_portfolios'].mean():.1f}")
    
    print("\n?? Category Distribution:")
    for col in categories_df.columns:
        if col.startswith('is_'):
            category = col.replace('is_', '').title()
            count = categories_df[col].sum()
            pct = 100 * count / len(categories_df)
            print(f"   {count:3d} coins ({pct:5.1f}%): {category}")
    
    print("\n" + "="*80)
    print("COMPLETE!")
    print("="*80)
    print(f"\n?? Files saved in: {output_dir}/")
    print("\n?? Next steps:")
    print("   1. Review tag categories for trading strategies")
    print("   2. Analyze VC portfolio concentrations")
    print("   3. Build sector rotation backtests")
    print("   4. Combine with price data for alpha research")
    print()


if __name__ == "__main__":
    main()
