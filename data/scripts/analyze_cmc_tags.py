#!/usr/bin/env python3
"""
Analyze CoinMarketCap Tag Data

Quick analysis of the scraped tag data to find interesting patterns
and trading opportunities.
"""

import pandas as pd
import glob
import os


def find_latest_file(pattern):
    """Find the most recent file matching pattern."""
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getctime)


def main():
    print("="*80)
    print("COINMARKETCAP TAG DATA ANALYSIS")
    print("="*80)
    
    # Load the latest files
    tag_file = find_latest_file("data/raw/cmc_coin_tags_*.csv")
    summary_file = find_latest_file("data/raw/cmc_tag_summary_*.csv")
    categories_file = find_latest_file("data/raw/cmc_tag_categories_*.csv")
    vc_file = find_latest_file("data/raw/cmc_vc_portfolios_*.csv")
    metadata_file = find_latest_file("data/raw/cmc_coin_metadata_full_*.csv")
    
    if not all([tag_file, summary_file, categories_file, vc_file, metadata_file]):
        print("ERROR: Could not find all required files")
        return
    
    print(f"\nLoading data files...")
    tags_df = pd.read_csv(tag_file)
    summary_df = pd.read_csv(summary_file)
    categories_df = pd.read_csv(categories_file)
    vc_df = pd.read_csv(vc_file)
    metadata_df = pd.read_csv(metadata_file)
    
    print(f"? Loaded {len(metadata_df)} coins with {len(tags_df)} tag relationships")
    
    # Analysis 1: Most popular tags by category
    print("\n" + "="*80)
    print("MOST POPULAR TAGS BY GROUP")
    print("="*80)
    
    for group in ['INDUSTRY', 'PLATFORM', 'CATEGORY', 'ALGORITHM']:
        group_tags = summary_df[summary_df['tag_group'] == group].head(5)
        if len(group_tags) > 0:
            print(f"\n?? {group}:")
            for _, row in group_tags.iterrows():
                print(f"   {row['num_coins']:3d} coins: {row['tag_name']}")
    
    # Analysis 2: VC Portfolio Concentration
    print("\n" + "="*80)
    print("VC PORTFOLIO ANALYSIS")
    print("="*80)
    
    # Get VC columns (exclude symbol and total)
    vc_cols = [col for col in vc_df.columns if col not in ['symbol', 'total_vc_portfolios']]
    
    print(f"\n?? Top 10 VCs by Portfolio Size:")
    vc_counts = {}
    for col in vc_cols:
        count = vc_df[col].sum()
        vc_counts[col] = count
    
    vc_sorted = sorted(vc_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    for vc, count in vc_sorted:
        print(f"   {count:2d} coins: {vc}")
    
    print(f"\n?? Coins with Most VC Backing:")
    top_vc_coins = vc_df.nlargest(10, 'total_vc_portfolios')[['symbol', 'total_vc_portfolios']]
    for _, row in top_vc_coins.iterrows():
        print(f"   {row['symbol']:8s} - {row['total_vc_portfolios']} VCs")
    
    # Analysis 3: Category Concentrations
    print("\n" + "="*80)
    print("SECTOR/CATEGORY BREAKDOWN")
    print("="*80)
    
    category_cols = [col for col in categories_df.columns if col.startswith('is_')]
    category_counts = {col.replace('is_', '').upper(): categories_df[col].sum() 
                      for col in category_cols}
    category_sorted = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    
    print(f"\n?? Coins per Category:")
    for category, count in category_sorted:
        pct = 100 * count / len(categories_df)
        bar = '?' * int(pct / 2)
        print(f"   {category:15s} {count:3d} ({pct:5.1f}%) {bar}")
    
    # Analysis 4: Multi-category coins
    print("\n" + "="*80)
    print("MULTI-CATEGORY COINS")
    print("="*80)
    
    categories_df['num_categories'] = categories_df[category_cols].sum(axis=1)
    
    print(f"\n?? Coins in Multiple Categories:")
    multi_cat = categories_df.nlargest(10, 'num_categories')[['symbol', 'num_categories']]
    for _, row in multi_cat.iterrows():
        coin_cats = []
        for col in category_cols:
            if categories_df[categories_df['symbol'] == row['symbol']][col].values[0]:
                coin_cats.append(col.replace('is_', '').upper())
        print(f"   {row['symbol']:8s} - {row['num_categories']} categories: {', '.join(coin_cats)}")
    
    # Analysis 5: Interesting tag combinations
    print("\n" + "="*80)
    print("INTERESTING TAG COMBINATIONS")
    print("="*80)
    
    print(f"\n?? AI + DeFi Coins:")
    ai_defi = categories_df[(categories_df['is_ai'] == 1) & (categories_df['is_defi'] == 1)]
    print(f"   {', '.join(ai_defi['symbol'].tolist()) if len(ai_defi) > 0 else 'None found'}")
    
    print(f"\n?? Gaming + DeFi Coins:")
    gaming_defi = categories_df[(categories_df['is_gaming'] == 1) & (categories_df['is_defi'] == 1)]
    print(f"   {', '.join(gaming_defi['symbol'].tolist()) if len(gaming_defi) > 0 else 'None found'}")
    
    print(f"\n? Layer1 + DeFi Coins:")
    l1_defi = categories_df[(categories_df['is_layer1'] == 1) & (categories_df['is_defi'] == 1)]
    print(f"   {', '.join(l1_defi['symbol'].tolist()[:15])}")
    if len(l1_defi) > 15:
        print(f"   ... and {len(l1_defi) - 15} more")
    
    print(f"\n?? Meme Coins:")
    meme = categories_df[categories_df['is_meme'] == 1]
    print(f"   {', '.join(meme['symbol'].tolist())}")
    
    # Analysis 6: Coins by platform
    print("\n" + "="*80)
    print("TOKEN PLATFORM ANALYSIS")
    print("="*80)
    
    # Count coins vs tokens
    coins_vs_tokens = metadata_df['category'].value_counts()
    print(f"\n?? Coins vs Tokens:")
    for cat, count in coins_vs_tokens.items():
        print(f"   {cat:10s}: {count}")
    
    # Most common platforms for tokens
    tokens_df = metadata_df[metadata_df['category'] == 'token']
    if len(tokens_df) > 0:
        platform_counts = tokens_df['platform_name'].value_counts().head(10)
        print(f"\n???  Most Common Token Platforms:")
        for platform, count in platform_counts.items():
            if pd.notna(platform):
                print(f"   {count:2d} tokens: {platform}")
    
    # Analysis 7: Tags that might predict performance
    print("\n" + "="*80)
    print("POTENTIAL TRADING STRATEGIES")
    print("="*80)
    
    print(f"\n?? Strategy Ideas Based on Tags:")
    
    print(f"\n1. ?? VC-Backed Premium:")
    print(f"   - Trade coins with 5+ VC backers")
    print(f"   - Hypothesis: Strong VC backing = better fundamentals")
    high_vc = vc_df[vc_df['total_vc_portfolios'] >= 5]['symbol'].tolist()
    print(f"   - Universe: {len(high_vc)} coins")
    print(f"   - Examples: {', '.join(high_vc[:10])}")
    
    print(f"\n2. ?? Sector Rotation:")
    print(f"   - Rotate between DeFi, AI, Gaming, Layer1 based on momentum")
    print(f"   - DeFi: {len(categories_df[categories_df['is_defi'] == 1])} coins")
    print(f"   - AI: {len(categories_df[categories_df['is_ai'] == 1])} coins")
    print(f"   - Gaming: {len(categories_df[categories_df['is_gaming'] == 1])} coins")
    print(f"   - Layer1: {len(categories_df[categories_df['is_layer1'] == 1])} coins")
    
    print(f"\n3. ?? Ecosystem Plays:")
    eth_eco = tags_df[tags_df['tag'] == 'ethereum-ecosystem']['symbol'].nunique()
    sol_eco = tags_df[tags_df['tag'] == 'solana-ecosystem']['symbol'].nunique()
    arb_eco = tags_df[tags_df['tag'] == 'arbitrum-ecosystem']['symbol'].nunique()
    print(f"   - Trade ecosystem baskets when L1 pumps")
    print(f"   - Ethereum ecosystem: {eth_eco} coins")
    print(f"   - Solana ecosystem: {sol_eco} coins")
    print(f"   - Arbitrum ecosystem: {arb_eco} coins")
    
    print(f"\n4. ?? Narrative Trading:")
    print(f"   - Identify emerging narratives via tag creation dates")
    print(f"   - Current narratives: AI, Gaming, DePIN, RWA")
    
    print(f"\n5. ?? Meme Coin Momentum:")
    meme_count = len(categories_df[categories_df['is_meme'] == 1])
    print(f"   - High beta, momentum-driven")
    print(f"   - Universe: {meme_count} meme coins")
    print(f"   - Strategy: Short-term momentum with tight stops")
    
    # Save strategy universes
    print("\n" + "="*80)
    print("SAVING STRATEGY UNIVERSES")
    print("="*80)
    
    output_dir = "data/raw"
    
    # VC-backed premium
    vc_premium_df = vc_df[vc_df['total_vc_portfolios'] >= 5][['symbol', 'total_vc_portfolios']]
    vc_premium_df.to_csv(f"{output_dir}/strategy_vc_backed_premium.csv", index=False)
    print(f"\n? Saved: strategy_vc_backed_premium.csv ({len(vc_premium_df)} coins)")
    
    # Sector universes
    for sector in ['defi', 'ai', 'gaming', 'layer1', 'layer2', 'meme']:
        sector_coins = categories_df[categories_df[f'is_{sector}'] == 1]['symbol']
        sector_coins.to_csv(f"{output_dir}/strategy_{sector}_universe.csv", index=False, header=['symbol'])
        print(f"? Saved: strategy_{sector}_universe.csv ({len(sector_coins)} coins)")
    
    # Ecosystem baskets
    for ecosystem in ['ethereum-ecosystem', 'solana-ecosystem', 'arbitrum-ecosystem', 'bnb-chain-ecosystem']:
        eco_coins = tags_df[tags_df['tag'] == ecosystem]['symbol'].unique()
        pd.DataFrame({'symbol': eco_coins}).to_csv(
            f"{output_dir}/strategy_{ecosystem.replace('-', '_')}.csv", 
            index=False
        )
        print(f"? Saved: strategy_{ecosystem.replace('-', '_')}.csv ({len(eco_coins)} coins)")
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE!")
    print("="*80)
    print("\n?? Next Steps:")
    print("   1. Use strategy universe CSVs for backtesting")
    print("   2. Combine tag data with price/volume data")
    print("   3. Build sector rotation models")
    print("   4. Track tag performance over time")
    print()


if __name__ == "__main__":
    main()
