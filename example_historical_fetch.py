#!/usr/bin/env python3
"""
Example: Fetch Historical Top 100 Coins Quarterly

This script demonstrates how to use the fetch_historical_top100_quarterly function
to get quarterly snapshots of the top 100 cryptocurrencies by market cap from 2020 onwards.

Requirements:
- CoinMarketCap API key with access to historical data (paid plan required)
- Set CMC_API environment variable or pass API key directly

Usage:
    # Set API key
    export CMC_API="your-api-key-here"
    
    # Run the script
    python3 example_historical_fetch.py
"""

from fetch_coinmarketcap_data import fetch_historical_top100_quarterly
import pandas as pd

def main():
    print("=" * 80)
    print("FETCHING HISTORICAL TOP 100 COINS QUARTERLY FROM 2020")
    print("=" * 80)
    print()
    
    # Fetch historical data
    # Note: This requires a paid CoinMarketCap API plan
    df = fetch_historical_top100_quarterly(
        api_key=None,  # Will read from CMC_API environment variable
        start_year=2020,
        limit=100,
        delay_seconds=1.5  # Be respectful of API rate limits
    )
    
    if df is None:
        print("\n❌ Failed to fetch data. Check your API key and plan.")
        return
    
    # Save to CSV
    output_file = 'historical_top100_quarterly_2020.csv'
    df.to_csv(output_file, index=False)
    print(f"\n✓ Data saved to: {output_file}")
    
    # Analysis examples
    print("\n" + "=" * 80)
    print("ANALYSIS EXAMPLES")
    print("=" * 80)
    
    # 1. Coins that appeared in ALL quarters
    coin_quarters = df.groupby('symbol')['quarter'].nunique()
    total_quarters = df['quarter'].nunique()
    always_top100 = coin_quarters[coin_quarters == total_quarters].index.tolist()
    
    print(f"\n1. Coins in top 100 for ALL {total_quarters} quarters:")
    print(f"   {len(always_top100)} coins: {', '.join(sorted(always_top100)[:20])}")
    if len(always_top100) > 20:
        print(f"   ... and {len(always_top100) - 20} more")
    
    # 2. New entrants by quarter
    print("\n2. New coins entering top 100 by quarter:")
    seen_symbols = set()
    for quarter in sorted(df['quarter'].unique()):
        quarter_symbols = set(df[df['quarter'] == quarter]['symbol'])
        new_coins = quarter_symbols - seen_symbols
        if new_coins:
            print(f"   {quarter}: {len(new_coins)} new - {', '.join(sorted(list(new_coins))[:5])}")
        seen_symbols.update(quarter_symbols)
    
    # 3. Market cap concentration
    print("\n3. Market cap concentration (Top 10 dominance):")
    for quarter in sorted(df['quarter'].unique())[-4:]:  # Last 4 quarters
        quarter_data = df[df['quarter'] == quarter].nsmallest(10, 'cmc_rank')
        top10_pct = quarter_data['market_cap_dominance'].sum()
        print(f"   {quarter}: {top10_pct:.1f}%")
    
    # 4. Most volatile rankings
    print("\n4. Coins with most volatile rankings (std dev of rank):")
    rank_volatility = df.groupby('symbol')['cmc_rank'].agg(['std', 'min', 'max', 'count'])
    rank_volatility = rank_volatility[rank_volatility['count'] >= 5]  # At least 5 quarters
    rank_volatility = rank_volatility.nlargest(10, 'std')
    print(rank_volatility.to_string())
    
    # 5. Latest quarter summary
    latest_quarter = df['quarter'].max()
    latest_data = df[df['quarter'] == latest_quarter]
    print(f"\n5. Latest quarter ({latest_quarter}) summary:")
    print(f"   Total market cap: ${latest_data['market_cap'].sum():,.0f}")
    print(f"   Top 5 coins: {', '.join(latest_data.nsmallest(5, 'cmc_rank')['symbol'].tolist())}")
    print(f"   Median market cap: ${latest_data['market_cap'].median():,.0f}")
    
    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
