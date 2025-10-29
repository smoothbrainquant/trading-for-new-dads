#!/usr/bin/env python3
"""
Compare CMC/Coinbase symbols with funding rate data to find missing symbols,
then download funding rate history for missing symbols.
"""
import pandas as pd
import os
from datetime import datetime, timedelta
from coinalyze_client import CoinalyzeClient
import time
import logging
from typing import Set, Dict, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_cmc_coinbase_symbols() -> Set[str]:
    """
    Get all unique symbols from CMC and Coinbase data.

    Returns:
        Set of unique symbols
    """
    print("=" * 80)
    print("EXTRACTING SYMBOLS FROM CMC AND COINBASE DATA")
    print("=" * 80)

    all_symbols = set()

    # Get workspace root
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    # 1. Read CMC historical snapshots
    cmc_historical = os.path.join(
        workspace_root, "data/raw/coinmarketcap_historical_all_snapshots.csv"
    )
    if os.path.exists(cmc_historical):
        print(f"\nReading {cmc_historical}...")
        df = pd.read_csv(cmc_historical)
        symbols = set(df["Symbol"].unique())
        all_symbols.update(symbols)
        print(f"  Found {len(symbols)} unique symbols")
        print(f"  Date range: {df['snapshot_date'].min()} to {df['snapshot_date'].max()}")
    else:
        print(f"  ✗ File not found: {cmc_historical}")

    # 2. Read CMC monthly snapshots
    cmc_monthly = os.path.join(workspace_root, "data/raw/coinmarketcap_monthly_all_snapshots.csv")
    if os.path.exists(cmc_monthly):
        print(f"\nReading {cmc_monthly}...")
        df = pd.read_csv(cmc_monthly)
        symbols = set(df["Symbol"].unique())
        new_symbols = symbols - all_symbols
        all_symbols.update(symbols)
        print(f"  Found {len(symbols)} unique symbols")
        print(f"  Added {len(new_symbols)} new symbols")
    else:
        print(f"  ✗ File not found: {cmc_monthly}")

    # 3. Read Coinbase combined data
    coinbase_combined = os.path.join(
        workspace_root, "data/raw/combined_coinbase_coinmarketcap_daily.csv"
    )
    if os.path.exists(coinbase_combined):
        print(f"\nReading {coinbase_combined}...")
        df = pd.read_csv(coinbase_combined)
        if "base" in df.columns:
            symbols = set(df["base"].unique())
            new_symbols = symbols - all_symbols
            all_symbols.update(symbols)
            print(f"  Found {len(symbols)} unique symbols")
            print(f"  Added {len(new_symbols)} new symbols")
    else:
        print(f"  ✗ File not found: {coinbase_combined}")

    # 4. Read Coinbase spot daily data
    coinbase_spot = os.path.join(
        workspace_root, "data/raw/coinbase_spot_daily_data_20200101_20251024_110130.csv"
    )
    if os.path.exists(coinbase_spot):
        print(f"\nReading {coinbase_spot}...")
        df = pd.read_csv(coinbase_spot)
        if "base" in df.columns:
            symbols = set(df["base"].unique())
            new_symbols = symbols - all_symbols
            all_symbols.update(symbols)
            print(f"  Found {len(symbols)} unique symbols")
            print(f"  Added {len(new_symbols)} new symbols")
    else:
        print(f"  ✗ File not found: {coinbase_spot}")

    print(f"\n{'='*80}")
    print(f"TOTAL UNIQUE CMC/COINBASE SYMBOLS: {len(all_symbols)}")
    print(f"{'='*80}")

    return all_symbols


def get_funding_rate_symbols() -> Set[str]:
    """
    Get all unique symbols from funding rate data.

    Returns:
        Set of unique base symbols (e.g., 'BTC', 'ETH')
    """
    print("\n" + "=" * 80)
    print("EXTRACTING SYMBOLS FROM FUNDING RATE DATA")
    print("=" * 80)

    # Get workspace root
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    all_symbols = set()

    # Look for funding rate files
    funding_files = [
        os.path.join(
            workspace_root, "data/raw/historical_funding_rates_top100_20251025_124832.csv"
        ),
        os.path.join(
            workspace_root,
            "data/raw/historical_funding_rates_top50_ALL_HISTORY_20251025_123832.csv",
        ),
    ]

    for file_path in funding_files:
        if os.path.exists(file_path):
            print(f"\nReading {file_path}...")
            df = pd.read_csv(file_path)

            # Extract base symbol from coin_symbol column
            if "coin_symbol" in df.columns:
                symbols = set(df["coin_symbol"].unique())
                symbols.discard("")  # Remove empty strings
                all_symbols.update(symbols)
                print(f"  Found {len(symbols)} unique symbols")

                # Show sample
                if "date" in df.columns:
                    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
            else:
                print(f"  ✗ Cannot find 'coin_symbol' column")

    print(f"\n{'='*80}")
    print(f"TOTAL UNIQUE FUNDING RATE SYMBOLS: {len(all_symbols)}")
    print(f"{'='*80}")

    return all_symbols


def compare_symbols(cmc_coinbase_symbols: Set[str], funding_symbols: Set[str]) -> tuple:
    """
    Compare CMC/Coinbase symbols with funding rate symbols.

    Returns:
        Tuple of (missing_symbols, present_symbols)
    """
    print("\n" + "=" * 80)
    print("COMPARING SYMBOLS")
    print("=" * 80)

    missing_symbols = cmc_coinbase_symbols - funding_symbols
    present_symbols = cmc_coinbase_symbols & funding_symbols

    print(f"\n  CMC/Coinbase Symbols:     {len(cmc_coinbase_symbols):,}")
    print(f"  Funding Rate Symbols:     {len(funding_symbols):,}")
    print(f"  Present in both:          {len(present_symbols):,}")
    print(f"  Missing in Funding Rates: {len(missing_symbols):,}")

    if missing_symbols:
        print(f"\n{'='*80}")
        print(f"MISSING SYMBOLS (in CMC/Coinbase but not in Funding Rate data)")
        print(f"{'='*80}")
        sorted_missing = sorted(list(missing_symbols))

        # Print in columns
        cols = 8
        for i in range(0, len(sorted_missing), cols):
            row = sorted_missing[i : i + cols]
            print("  " + "  ".join(f"{s:8s}" for s in row))

    return missing_symbols, present_symbols


def find_perpetual_symbols(client: CoinalyzeClient, coin_symbols: List[str]) -> Dict[str, str]:
    """
    Map coin symbols to Coinalyze perpetual symbols.

    Args:
        client: CoinalyzeClient instance
        coin_symbols: List of coin symbols (e.g., ['BTC', 'ETH'])

    Returns:
        Dictionary mapping coin symbol to Coinalyze symbol
    """
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
            # Sort by preferred exchanges
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


def fetch_funding_rate_history_with_retry(
    client: CoinalyzeClient, symbols: List[str], days: int = 365, max_retries: int = 3
) -> pd.DataFrame:
    """
    Fetch historical funding rates with retry logic for rate limits.

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

    # Process in batches of 3 to avoid rate limits
    batch_size = 3
    batch_wait_time = 5

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


def download_missing_funding_rates(missing_symbols: Set[str], days: int = 365) -> pd.DataFrame:
    """
    Download funding rate history for missing symbols.

    Args:
        missing_symbols: Set of coin symbols missing from funding rate data
        days: Number of days of history to fetch

    Returns:
        DataFrame with downloaded funding rate data
    """
    if not missing_symbols:
        print("\n✓ No missing symbols to download!")
        return pd.DataFrame()

    # Check for API key
    if not os.environ.get("COINALYZE_API"):
        logger.error("COINALYZE_API environment variable not set")
        print("\n✗ Please set COINALYZE_API environment variable to download funding rates")
        return pd.DataFrame()

    # Initialize client
    print("\n" + "=" * 80)
    print("INITIALIZING COINALYZE CLIENT")
    print("=" * 80)
    client = CoinalyzeClient()

    # Map symbols to perpetual contracts
    print("\n" + "=" * 80)
    print("MAPPING SYMBOLS TO PERPETUAL CONTRACTS")
    print("=" * 80)

    sorted_missing = sorted(list(missing_symbols))
    symbol_map = find_perpetual_symbols(client, sorted_missing)

    if not symbol_map:
        print("\n✗ No perpetual contracts found for missing symbols")
        return pd.DataFrame()

    print(f"\n✓ Found {len(symbol_map)}/{len(missing_symbols)} symbols with perpetual contracts")

    # Fetch funding rate history
    print("\n" + "=" * 80)
    print(f"DOWNLOADING FUNDING RATES FOR {len(symbol_map)} SYMBOLS")
    print(f"Fetching {days} days of history")
    print("=" * 80)

    coinalyze_symbols = list(symbol_map.values())
    funding_df = fetch_funding_rate_history_with_retry(client, coinalyze_symbols, days=days)

    if funding_df.empty:
        logger.error("No funding rate data retrieved")
        return pd.DataFrame()

    # Add coin symbol information
    reverse_map = {v: k for k, v in symbol_map.items()}
    funding_df["coin_symbol"] = funding_df["symbol"].apply(lambda x: reverse_map.get(x, ""))

    # Reorder columns
    funding_df = funding_df[
        [
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
    ].sort_values(["coin_symbol", "date"])

    # Save to CSV
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    output_file = os.path.join(
        workspace_root, f"data/raw/funding_rates_missing_symbols_{timestamp}.csv"
    )

    funding_df.to_csv(output_file, index=False)

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Total data points: {len(funding_df):,}")
    print(f"Unique symbols: {funding_df['coin_symbol'].nunique()}")
    print(f"Date range: {funding_df['date'].min()} to {funding_df['date'].max()}")
    print(f"\nOutput saved to: {output_file}")

    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)

    summary = (
        funding_df.groupby(["coin_symbol", "symbol"])
        .agg({"funding_rate_pct": ["count", "mean", "std", "min", "max"], "date": ["min", "max"]})
        .round(4)
    )

    summary.columns = ["_".join(col).strip() for col in summary.columns.values]
    summary = summary.reset_index()
    summary.columns = [
        "Coin Symbol",
        "Coinalyze Symbol",
        "Data Points",
        "Avg FR %",
        "Std FR %",
        "Min FR %",
        "Max FR %",
        "First Date",
        "Last Date",
    ]

    print(summary.to_string(index=False))

    # Save summary
    summary_file = os.path.join(
        workspace_root, f"data/raw/funding_rates_missing_symbols_summary_{timestamp}.csv"
    )
    summary.to_csv(summary_file, index=False)
    print(f"\nSummary saved to: {summary_file}")

    return funding_df


def main():
    """Main function to find and download missing funding rate symbols."""

    print("\n" + "=" * 80)
    print("FIND AND DOWNLOAD MISSING FUNDING RATE SYMBOLS")
    print("=" * 80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Step 1: Get all symbols from CMC and Coinbase data
    cmc_coinbase_symbols = get_cmc_coinbase_symbols()

    # Step 2: Get all symbols from funding rate data
    funding_symbols = get_funding_rate_symbols()

    # Step 3: Compare and identify missing symbols
    missing_symbols, present_symbols = compare_symbols(cmc_coinbase_symbols, funding_symbols)

    # Step 4: Download funding rates for missing symbols
    if missing_symbols:
        print(f"\n{'='*80}")
        print(f"PROCEEDING WITH DOWNLOAD")
        print(f"{'='*80}")
        print(
            f"Will attempt to download funding rate history for {len(missing_symbols)} missing symbols"
        )

        df = download_missing_funding_rates(missing_symbols, days=365)

        if not df.empty:
            print(f"\n{'='*80}")
            print(f"SAMPLE OF DOWNLOADED DATA")
            print(f"{'='*80}\n")
            print(df.head(20).to_string(index=False))
            print(f"\n... {len(df):,} total rows")
    else:
        print("\n✓ All CMC/Coinbase symbols already have funding rate data!")

    print(f"\n{'='*80}")
    print(f"COMPLETE!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
