#!/usr/bin/env python3
"""
Fetch Crypto Dilution Metrics for Top 50 Coins

This script fetches supply data for the top 50 cryptocurrencies and calculates
dilution metrics by comparing current circulating supply vs total/maximum supply.

Metrics calculated:
- Current circulating supply
- Total supply (if available)
- Maximum supply (if available)
- Circulating % = (circulating / max_supply) * 100
- Potential dilution % = ((max_supply - circulating) / circulating) * 100
- Locked tokens = max_supply - circulating
"""

import requests
import pandas as pd
import os
from datetime import datetime


def fetch_crypto_supply_data(api_key=None, limit=50, convert="USD"):
    """
    Fetch cryptocurrency supply data from CoinMarketCap to calculate dilution.

    Args:
        api_key (str): CoinMarketCap API key. If None, tries to read from CMC_API env var
        limit (int): Number of cryptocurrencies to fetch (default 50)
        convert (str): Currency for conversion (default USD)

    Returns:
        pd.DataFrame: DataFrame with supply and dilution metrics
    """
    # Get API key from environment if not provided
    if api_key is None:
        api_key = os.environ.get("CMC_API")
        if not api_key:
            print("WARNING: No CoinMarketCap API key found.")
            print("Please set CMC_API environment variable.")
            print("Using mock data instead...")
            return generate_mock_dilution_data(limit)

    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"

    parameters = {
        "start": "1",
        "limit": str(limit),
        "convert": convert,
        "sort": "market_cap",
        "sort_dir": "desc",
    }

    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": api_key,
    }

    try:
        print(f"Fetching top {limit} cryptocurrencies from CoinMarketCap...")
        response = requests.get(url, headers=headers, params=parameters)
        response.raise_for_status()

        data = response.json()

        if "data" not in data:
            print(f"ERROR: Unexpected API response structure")
            return generate_mock_dilution_data(limit)

        # Parse the data
        coins_data = []
        for coin in data["data"]:
            quote = coin["quote"][convert]
            
            # Get supply data
            circulating_supply = coin.get("circulating_supply", None)
            total_supply = coin.get("total_supply", None)
            max_supply = coin.get("max_supply", None)
            
            # Calculate dilution metrics
            # Use max_supply if available, otherwise use total_supply
            effective_max_supply = max_supply if max_supply is not None else total_supply
            
            circulating_pct = None
            potential_dilution_pct = None
            locked_tokens = None
            
            if circulating_supply and effective_max_supply and effective_max_supply > 0:
                circulating_pct = (circulating_supply / effective_max_supply) * 100
                if circulating_supply > 0:
                    potential_dilution_pct = ((effective_max_supply - circulating_supply) / circulating_supply) * 100
                locked_tokens = effective_max_supply - circulating_supply
            
            coins_data.append(
                {
                    "rank": coin["cmc_rank"],
                    "symbol": coin["symbol"],
                    "name": coin["name"],
                    "price": quote["price"],
                    "market_cap": quote["market_cap"],
                    "circulating_supply": circulating_supply,
                    "total_supply": total_supply,
                    "max_supply": max_supply,
                    "effective_max_supply": effective_max_supply,
                    "circulating_pct": circulating_pct,
                    "potential_dilution_pct": potential_dilution_pct,
                    "locked_tokens": locked_tokens,
                    "volume_24h": quote["volume_24h"],
                    "market_cap_dominance": quote.get("market_cap_dominance", None),
                    "timestamp": datetime.now().isoformat(),
                }
            )

        df = pd.DataFrame(coins_data)
        print(f"Successfully fetched {len(df)} cryptocurrencies")
        return df

    except requests.exceptions.RequestException as e:
        print(f"ERROR fetching from CoinMarketCap: {e}")
        print("Using mock data instead...")
        return generate_mock_dilution_data(limit)


def generate_mock_dilution_data(limit=50):
    """
    Generate mock dilution data for testing when API key is not available.

    Args:
        limit (int): Number of cryptocurrencies to generate

    Returns:
        pd.DataFrame: Mock dilution data
    """
    import numpy as np

    # Top cryptocurrencies with realistic dilution scenarios
    mock_data = [
        # BTC - Fixed supply, ~93% circulated
        {"symbol": "BTC", "name": "Bitcoin", "circ": 19_500_000, "max": 21_000_000},
        # ETH - No max supply
        {"symbol": "ETH", "name": "Ethereum", "circ": 120_000_000, "max": None},
        # BNB - Deflationary, burning supply
        {"symbol": "BNB", "name": "BNB", "circ": 150_000_000, "max": 200_000_000},
        # SOL - High initial circulation
        {"symbol": "SOL", "name": "Solana", "circ": 420_000_000, "max": 580_000_000},
        # XRP - Heavy vesting schedule
        {"symbol": "XRP", "name": "XRP", "circ": 53_000_000_000, "max": 100_000_000_000},
        # ADA - Moderate circulation
        {"symbol": "ADA", "name": "Cardano", "circ": 35_000_000_000, "max": 45_000_000_000},
        # AVAX - Medium term unlock
        {"symbol": "AVAX", "name": "Avalanche", "circ": 350_000_000, "max": 720_000_000},
        # DOGE - No max supply
        {"symbol": "DOGE", "name": "Dogecoin", "circ": 142_000_000_000, "max": None},
        # DOT - Inflationary
        {"symbol": "DOT", "name": "Polkadot", "circ": 1_290_000_000, "max": None},
        # MATIC - Low circulation
        {"symbol": "MATIC", "name": "Polygon", "circ": 9_300_000_000, "max": 10_000_000_000},
    ]

    coins_data = []
    base_market_cap = 1_000_000_000_000  # $1T for #1

    for i in range(limit):
        rank = i + 1
        
        # Use realistic data for top 10, generate for rest
        if i < len(mock_data):
            symbol = mock_data[i]["symbol"]
            name = mock_data[i]["name"]
            circ = mock_data[i]["circ"]
            max_supply = mock_data[i]["max"]
            total_supply = max_supply
        else:
            symbol = f"COIN{i+1}"
            name = f"Coin {i+1}"
            circ = np.random.uniform(50_000_000, 500_000_000)
            # 70% of coins have max supply, 30% are inflationary
            if np.random.random() < 0.7:
                max_supply = circ * np.random.uniform(1.2, 5.0)
                total_supply = max_supply
            else:
                max_supply = None
                total_supply = circ * np.random.uniform(1.0, 1.5)
        
        # Calculate market cap and price
        market_cap = base_market_cap / (rank ** 1.5)
        market_cap *= np.random.uniform(0.8, 1.2)
        price = market_cap / circ if circ > 0 else 0
        
        # Calculate dilution metrics
        effective_max_supply = max_supply if max_supply is not None else total_supply
        
        circulating_pct = None
        potential_dilution_pct = None
        locked_tokens = None
        
        if circ and effective_max_supply and effective_max_supply > 0:
            circulating_pct = (circ / effective_max_supply) * 100
            if circ > 0:
                potential_dilution_pct = ((effective_max_supply - circ) / circ) * 100
            locked_tokens = effective_max_supply - circ
        
        coins_data.append(
            {
                "rank": rank,
                "symbol": symbol,
                "name": name,
                "price": price,
                "market_cap": market_cap,
                "circulating_supply": circ,
                "total_supply": total_supply,
                "max_supply": max_supply,
                "effective_max_supply": effective_max_supply,
                "circulating_pct": circulating_pct,
                "potential_dilution_pct": potential_dilution_pct,
                "locked_tokens": locked_tokens,
                "volume_24h": market_cap * np.random.uniform(0.05, 0.3),
                "market_cap_dominance": (market_cap / base_market_cap) * 100,
                "timestamp": datetime.now().isoformat(),
            }
        )

    df = pd.DataFrame(coins_data)
    print(f"Generated mock dilution data for {len(df)} cryptocurrencies")
    return df


def print_dilution_summary(df):
    """
    Print summary statistics about dilution metrics.

    Args:
        df (pd.DataFrame): Dilution data
    """
    print("\n" + "=" * 80)
    print("DILUTION METRICS SUMMARY")
    print("=" * 80)
    
    # Overall stats
    print(f"\nTotal coins analyzed: {len(df)}")
    
    # Coins with max supply vs infinite
    has_max_supply = df["max_supply"].notna().sum()
    no_max_supply = df["max_supply"].isna().sum()
    print(f"\nCoins with max supply: {has_max_supply} ({has_max_supply/len(df)*100:.1f}%)")
    print(f"Coins with infinite/unclear supply: {no_max_supply} ({no_max_supply/len(df)*100:.1f}%)")
    
    # Circulation statistics (for coins with max supply)
    df_with_max = df[df["max_supply"].notna()].copy()
    if len(df_with_max) > 0:
        print(f"\n--- For coins with defined max supply ({len(df_with_max)} coins) ---")
        print(f"Average circulating %: {df_with_max['circulating_pct'].mean():.2f}%")
        print(f"Median circulating %: {df_with_max['circulating_pct'].median():.2f}%")
        print(f"Min circulating %: {df_with_max['circulating_pct'].min():.2f}% ({df_with_max.loc[df_with_max['circulating_pct'].idxmin(), 'symbol']})")
        print(f"Max circulating %: {df_with_max['circulating_pct'].max():.2f}% ({df_with_max.loc[df_with_max['circulating_pct'].idxmax(), 'symbol']})")
        
        print(f"\nAverage potential dilution: {df_with_max['potential_dilution_pct'].mean():.2f}%")
        print(f"Median potential dilution: {df_with_max['potential_dilution_pct'].median():.2f}%")
        print(f"Max potential dilution: {df_with_max['potential_dilution_pct'].max():.2f}% ({df_with_max.loc[df_with_max['potential_dilution_pct'].idxmax(), 'symbol']})")
    
    # High dilution risk coins (>50% locked)
    high_dilution = df[df["circulating_pct"] < 50].copy()
    if len(high_dilution) > 0:
        print(f"\n--- High Dilution Risk (>50% tokens locked) ---")
        print(f"Number of coins: {len(high_dilution)}")
        print("Top 5 by dilution risk:")
        top_dilution = high_dilution.nsmallest(5, "circulating_pct")[["rank", "symbol", "name", "circulating_pct", "potential_dilution_pct"]]
        print(top_dilution.to_string(index=False))
    
    # Low dilution risk coins (>90% circulated)
    low_dilution = df[df["circulating_pct"] > 90].copy()
    if len(low_dilution) > 0:
        print(f"\n--- Low Dilution Risk (>90% tokens circulated) ---")
        print(f"Number of coins: {len(low_dilution)}")
        sample_low = low_dilution.nsmallest(5, "rank")[["rank", "symbol", "name", "circulating_pct"]]
        print(sample_low.to_string(index=False))


def save_dilution_data(df, filepath="crypto_dilution_top50.csv"):
    """
    Save dilution data to CSV file.

    Args:
        df (pd.DataFrame): Dilution data
        filepath (str): Output file path
    """
    # Sort by rank
    df = df.sort_values("rank").reset_index(drop=True)
    
    # Save to CSV
    df.to_csv(filepath, index=False)
    print(f"\n" + "=" * 80)
    print(f"Dilution data saved to: {filepath}")
    print("=" * 80)
    
    # Print top 10 for preview
    print("\nTop 10 coins by market cap:")
    display_cols = ["rank", "symbol", "name", "circulating_pct", "potential_dilution_pct", "locked_tokens"]
    print(df[display_cols].head(10).to_string(index=False))


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch Crypto Dilution Metrics for Top 50 Coins",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--api-key", 
        type=str, 
        default=None, 
        help="CoinMarketCap API key (or set CMC_API env var)"
    )
    parser.add_argument(
        "--limit", 
        type=int, 
        default=50, 
        help="Number of cryptocurrencies to fetch (default 50)"
    )
    parser.add_argument(
        "--output", 
        type=str, 
        default="crypto_dilution_top50.csv", 
        help="Output CSV file path"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("CRYPTO DILUTION ANALYSIS - TOP 50 COINS")
    print("=" * 80)
    print(f"\nAnalyzing dilution for top {args.limit} cryptocurrencies...")
    print("Dilution = (Locked Tokens / Circulating Supply) * 100")
    print("Circulating % = (Circulating / Max Supply) * 100")
    print()

    # Fetch data
    df = fetch_crypto_supply_data(api_key=args.api_key, limit=args.limit)

    # Print summary
    print_dilution_summary(df)

    # Save to file
    save_dilution_data(df, args.output)

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print("\nColumns in output file:")
    for col in df.columns:
        print(f"  - {col}")


if __name__ == "__main__":
    main()
