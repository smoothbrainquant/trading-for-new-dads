"""
Fetch Historical CoinMarketCap Snapshots by extracting embedded JSON

This script downloads historical snapshot data from CoinMarketCap's historical pages
by extracting the embedded JSON data and saves them to CSV files.
"""

import requests
import pandas as pd
import json
import re
import time
from datetime import datetime


def fetch_historical_snapshot(date_str):
    """
    Fetch historical cryptocurrency data from CoinMarketCap snapshot page.

    Args:
        date_str (str): Date string in format YYYYMMDD (e.g., '20200105')

    Returns:
        pd.DataFrame: DataFrame with historical crypto data
    """
    url = f"https://coinmarketcap.com/historical/{date_str}/"

    print(f"\nFetching data from: {url}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()

        html_content = response.text

        # Extract JSON data from __NEXT_DATA__ script tag
        match = re.search(
            r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html_content, re.DOTALL
        )

        if not match:
            print(f"ERROR: Could not find __NEXT_DATA__ in page")
            return None

        json_str = match.group(1)
        data = json.loads(json_str)

        # Navigate through the JSON structure to find the crypto data
        # Structure: props -> initialState (JSON string) -> cryptocurrency -> listingHistorical -> data
        try:
            # initialState is a JSON-encoded string, need to parse it
            initial_state_str = data["props"]["initialState"]
            initial_state = json.loads(initial_state_str)
            crypto_list = initial_state["cryptocurrency"]["listingHistorical"]["data"]
        except (KeyError, json.JSONDecodeError) as e:
            print(f"ERROR: Could not find crypto data in JSON structure: {e}")
            print(f"Available keys: {data.keys()}")
            if "props" in data:
                print(f"Props keys: {data['props'].keys()}")
            return None

        if not crypto_list:
            print(f"ERROR: No crypto data found")
            return None

        # Extract relevant fields from each cryptocurrency
        rows = []
        for crypto in crypto_list:
            # Get USD quote data
            usd_quote = crypto.get("quote", {}).get("USD", {})

            row = {
                "Rank": crypto.get("rank", crypto.get("cmcRank", "")),
                "Name": crypto.get("name", ""),
                "Symbol": crypto.get("symbol", ""),
                "Market Cap": usd_quote.get("marketCap", usd_quote.get("market_cap", 0)),
                "Price": usd_quote.get("price", 0),
                "Circulating Supply": crypto.get(
                    "circulatingSupply", crypto.get("circulating_supply", 0)
                ),
                "Volume (24h)": usd_quote.get("volume24h", usd_quote.get("volume_24h", 0)),
                "% 1h": usd_quote.get("percentChange1h", usd_quote.get("percent_change_1h", 0)),
                "% 24h": usd_quote.get("percentChange24h", usd_quote.get("percent_change_24h", 0)),
                "% 7d": usd_quote.get("percentChange7d", usd_quote.get("percent_change_7d", 0)),
                "snapshot_date": date_str,
            }
            rows.append(row)

        df = pd.DataFrame(rows)

        print(f"Successfully fetched {len(df)} cryptocurrencies from {date_str}")

        return df

    except requests.exceptions.RequestException as e:
        print(f"ERROR fetching data: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"ERROR parsing JSON: {e}")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback

        traceback.print_exc()
        return None


def save_snapshot_to_csv(df, date_str, output_dir="."):
    """
    Save snapshot data to CSV file.

    Args:
        df (pd.DataFrame): Snapshot data
        date_str (str): Date string for filename
        output_dir (str): Output directory
    """
    if df is None or df.empty:
        print(f"No data to save for {date_str}")
        return

    filepath = f"{output_dir}/coinmarketcap_historical_{date_str}.csv"
    df.to_csv(filepath, index=False)
    print(f"Saved to: {filepath}")
    print(f"  Rows: {len(df)}")
    print(f"  Columns: {', '.join(df.columns.tolist())}")
    print(f"  Top 5 by Market Cap:")
    for idx, row in df.head(5).iterrows():
        print(f"    {row['Rank']}. {row['Name']} ({row['Symbol']}) - ${row['Market Cap']:,.0f}")


def main():
    """Main execution function."""
    print("=" * 80)
    print("COINMARKETCAP HISTORICAL SNAPSHOTS DOWNLOAD (JSON Extraction)")
    print("=" * 80)

    # Historical snapshot dates to fetch
    snapshot_dates = [
        "20200105",  # Jan 5, 2020
        "20210103",  # Jan 3, 2021
        "20220102",  # Jan 2, 2022
        "20230101",  # Jan 1, 2023
        "20240107",  # Jan 7, 2024
        "20250105",  # Jan 5, 2025
    ]

    all_snapshots = []

    for date_str in snapshot_dates:
        # Fetch data
        df = fetch_historical_snapshot(date_str)

        if df is not None:
            # Save individual snapshot
            save_snapshot_to_csv(df, date_str)
            all_snapshots.append(df)

        # Be polite to the server - wait between requests
        time.sleep(2)

    # Combine all snapshots into one file
    if all_snapshots:
        print("\n" + "=" * 80)
        print("COMBINING ALL SNAPSHOTS")
        print("=" * 80)

        combined_df = pd.concat(all_snapshots, ignore_index=True)
        combined_filepath = "coinmarketcap_historical_all_snapshots.csv"
        combined_df.to_csv(combined_filepath, index=False)
        print(f"\nCombined data saved to: {combined_filepath}")
        print(f"  Total rows: {len(combined_df)}")
        print(f"  Snapshots: {len(all_snapshots)}")

        # Print summary by date
        print("\nSummary by snapshot date:")
        for date_str in snapshot_dates:
            count = len(combined_df[combined_df["snapshot_date"] == date_str])
            avg_mcap = combined_df[combined_df["snapshot_date"] == date_str]["Market Cap"].mean()
            print(f"  {date_str}: {count} cryptocurrencies, Avg Market Cap: ${avg_mcap:,.0f}")

    print("\n" + "=" * 80)
    print("DOWNLOAD COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
