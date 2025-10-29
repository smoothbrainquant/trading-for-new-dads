#!/usr/bin/env python3
"""
Fetch Historical Funding Rates for Top 50 Coins (Improved)
Uses Coinalyze API + CoinMarketCap data with better rate limit handling
"""
import pandas as pd
import os
from datetime import datetime, timedelta
from coinalyze_client import CoinalyzeClient
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_top_50_coins():
    """Load top 50 coins from latest CoinMarketCap snapshot"""
    logger.info("Loading CoinMarketCap data...")

    df = pd.read_csv("coinmarketcap_historical_all_snapshots.csv")
    latest_date = df["snapshot_date"].max()
    logger.info(f"Latest snapshot: {latest_date}")

    latest = df[df["snapshot_date"] == latest_date].copy()
    latest = latest.sort_values("Rank").head(50)

    logger.info(f"Found {len(latest)} coins in top 50")

    return latest[["Rank", "Name", "Symbol", "Market Cap"]].to_dict("records")


def find_perpetual_symbols(client, coin_symbols):
    """Map coin symbols to Coinalyze perpetual symbols"""
    logger.info("Fetching available perpetual markets from Coinalyze...")

    futures = client.get_future_markets()
    if not futures:
        logger.error("Failed to fetch futures markets")
        return {}

    logger.info(f"Found {len(futures)} perpetual markets")

    symbol_map = {}
    preferred_exchanges = ["A", "6", "3", "0", "2"]  # Binance, Bybit, OKX, BitMEX, Deribit

    for coin_symbol in coin_symbols:
        matches = []

        for future in futures:
            if (
                future["base_asset"] == coin_symbol
                and future["is_perpetual"]
                and future["quote_asset"] in ["USDT", "USD", "USDC"]
            ):
                matches.append(future)

        if matches:
            matches_sorted = sorted(
                matches,
                key=lambda x: (
                    preferred_exchanges.index(x["exchange"])
                    if x["exchange"] in preferred_exchanges
                    else 999
                ),
            )

            best_match = matches_sorted[0]["symbol"]
            symbol_map[coin_symbol] = best_match
            logger.info(f"  {coin_symbol} -> {best_match}")
        else:
            logger.warning(f"  {coin_symbol} -> No perpetual found")

    return symbol_map


def fetch_funding_rate_history_with_retry(client, symbols, days=90, max_retries=3):
    """
    Fetch historical funding rates with retry logic for rate limits

    Args:
        client: CoinalyzeClient instance
        symbols: List of Coinalyze symbols
        days: Number of days of history to fetch
        max_retries: Maximum number of retries for rate-limited requests
    """
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=days)).timestamp())

    logger.info(
        f"\nFetching funding rates from {datetime.fromtimestamp(start_ts)} to {datetime.fromtimestamp(end_ts)}"
    )
    logger.info(f"Time range: {days} days")

    all_data = []

    # Process in batches of 3 to avoid rate limits (more conservative)
    batch_size = 3
    batch_wait_time = 5  # Increased wait time between batches

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i : i + batch_size]
        batch_str = ",".join(batch)

        logger.info(
            f"\nProcessing batch {i//batch_size + 1}/{(len(symbols)-1)//batch_size + 1}: {batch}"
        )

        # Retry logic
        success = False
        retry_count = 0

        while not success and retry_count < max_retries:
            try:
                result = client.get_funding_rate_history(
                    symbols=batch_str, interval="daily", from_ts=start_ts, to_ts=end_ts
                )

                if result:
                    for item in result:
                        symbol = item["symbol"]
                        history = item.get("history", [])

                        logger.info(f"  ✓ {symbol}: {len(history)} data points")

                        for point in history:
                            all_data.append(
                                {
                                    "symbol": symbol,
                                    "timestamp": point["t"],
                                    "date": datetime.fromtimestamp(point["t"]).strftime("%Y-%m-%d"),
                                    "funding_rate": point["c"],
                                    "funding_rate_pct": point["c"] * 100,
                                    "fr_open": point.get("o"),
                                    "fr_high": point.get("h"),
                                    "fr_low": point.get("l"),
                                }
                            )
                    success = True
                else:
                    # Failed but not a rate limit issue
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = 10 * retry_count
                        logger.warning(
                            f"  ⚠ Failed to fetch batch, retrying in {wait_time}s (attempt {retry_count+1}/{max_retries})..."
                        )
                        time.sleep(wait_time)
                    else:
                        logger.error(f"  ✗ Failed to fetch batch after {max_retries} attempts")

            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 10 * retry_count
                    logger.warning(
                        f"  ⚠ Error: {e}, retrying in {wait_time}s (attempt {retry_count+1}/{max_retries})..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"  ✗ Error after {max_retries} attempts: {e}")

        # Wait between batches to respect rate limits
        if i + batch_size < len(symbols):
            logger.info(f"  Waiting {batch_wait_time}s before next batch...")
            time.sleep(batch_wait_time)

    return pd.DataFrame(all_data)


def main():
    print("=" * 80)
    print("FETCH HISTORICAL FUNDING RATES - TOP 50 COINS (IMPROVED)")
    print("=" * 80)

    # Check for API key
    if not os.environ.get("COINALYZE_API"):
        logger.error("COINALYZE_API environment variable not set")
        return

    # Initialize client
    client = CoinalyzeClient()

    # Step 1: Get top 50 coins
    top_50 = get_top_50_coins()

    print("\nTop 50 Coins:")
    print("-" * 80)
    for coin in top_50[:10]:
        print(f"  {coin['Rank']:>2}. {coin['Name']:<30} ({coin['Symbol']})")
    print(f"  ... and {len(top_50) - 10} more")

    # Step 2: Map to Coinalyze symbols
    coin_symbols = [coin["Symbol"] for coin in top_50]
    symbol_map = find_perpetual_symbols(client, coin_symbols)

    print(f"\n{len(symbol_map)}/{len(coin_symbols)} coins have perpetual contracts available")

    if not symbol_map:
        logger.error("No symbols found to fetch")
        return

    # Step 3: Fetch historical funding rates with improved retry logic
    coinalyze_symbols = list(symbol_map.values())
    funding_df = fetch_funding_rate_history_with_retry(client, coinalyze_symbols, days=90)

    if funding_df.empty:
        logger.error("No funding rate data retrieved")
        return

    # Step 4: Add coin info to results
    reverse_map = {v: k for k, v in symbol_map.items()}
    coin_info_map = {coin["Symbol"]: coin for coin in top_50}

    funding_df["coin_symbol"] = funding_df["symbol"].apply(lambda x: reverse_map.get(x, ""))
    funding_df["coin_name"] = funding_df["coin_symbol"].apply(
        lambda x: coin_info_map[x]["Name"] if x in coin_info_map else ""
    )
    funding_df["rank"] = funding_df["coin_symbol"].apply(
        lambda x: coin_info_map[x]["Rank"] if x in coin_info_map else 999
    )

    # Reorder columns
    funding_df = funding_df[
        [
            "rank",
            "coin_name",
            "coin_symbol",
            "symbol",
            "date",
            "timestamp",
            "funding_rate",
            "funding_rate_pct",
            "fr_open",
            "fr_high",
            "fr_low",
        ]
    ].sort_values(["rank", "date"])

    # Step 5: Save to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"historical_funding_rates_top50_{timestamp}.csv"

    funding_df.to_csv(output_file, index=False)

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Total data points: {len(funding_df)}")
    print(f"Unique coins: {funding_df['coin_symbol'].nunique()}")
    print(f"Date range: {funding_df['date'].min()} to {funding_df['date'].max()}")
    print(f"\nOutput saved to: {output_file}")

    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS (All Coins)")
    print("=" * 80)

    summary = (
        funding_df.groupby(["rank", "coin_name", "coin_symbol"])
        .agg({"funding_rate_pct": ["count", "mean", "std", "min", "max"]})
        .round(4)
    )

    summary.columns = ["_".join(col).strip() for col in summary.columns.values]
    summary = summary.reset_index()
    summary.columns = [
        "Rank",
        "Coin",
        "Symbol",
        "Data Points",
        "Avg FR %",
        "Std FR %",
        "Min FR %",
        "Max FR %",
    ]

    print(summary.to_string(index=False))

    # Save summary
    summary_file = f"historical_funding_rates_top50_summary_{timestamp}.csv"
    summary.to_csv(summary_file, index=False)
    print(f"\nSummary saved to: {summary_file}")

    # Create a detailed analysis
    print("\n" + "=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)

    # Find highest/lowest average funding rates
    top_fr = summary.nlargest(5, "Avg FR %")[["Rank", "Coin", "Avg FR %"]]
    bottom_fr = summary.nsmallest(5, "Avg FR %")[["Rank", "Coin", "Avg FR %"]]

    print("\nTop 5 Highest Average Funding Rates:")
    print(top_fr.to_string(index=False))

    print("\nTop 5 Lowest Average Funding Rates:")
    print(bottom_fr.to_string(index=False))

    # Find most volatile funding rates
    top_vol = summary.nlargest(5, "Std FR %")[["Rank", "Coin", "Std FR %"]]
    print("\nTop 5 Most Volatile Funding Rates:")
    print(top_vol.to_string(index=False))

    print("\n" + "=" * 80)
    print("✅ COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    main()
