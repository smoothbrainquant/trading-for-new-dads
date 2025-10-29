#!/usr/bin/env python3
"""
Fetch ALL Historical Open Interest (OI) - Maximum Available Daily Data
- Uses Coinalyze API daily OI history (unlimited retention per docs)
- For top 50 coins by latest CoinMarketCap snapshot
- Saves detailed CSV, availability CSV, and summary CSV
"""
import os
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd

from coinalyze_client import CoinalyzeClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_cmc_file() -> str:
    candidates = [
        "data/raw/coinmarketcap_historical_all_snapshots.csv",
        "/workspace/data/raw/coinmarketcap_historical_all_snapshots.csv",
        "coinmarketcap_historical_all_snapshots.csv",
    ]
    for path in candidates:
        if Path(path).exists():
            return path
    raise FileNotFoundError(
        "coinmarketcap_historical_all_snapshots.csv not found in expected locations"
    )


def get_top_50_coins() -> List[Dict]:
    cmc_path = find_cmc_file()
    logger.info(f"Loading CoinMarketCap data from {cmc_path}...")

    df = pd.read_csv(cmc_path)
    latest_date = df["snapshot_date"].max()
    logger.info(f"Latest snapshot: {latest_date}")

    latest = df[df["snapshot_date"] == latest_date].copy()
    latest = latest.sort_values("Rank").head(50)
    logger.info(f"Found {len(latest)} coins in top 50")

    return latest[["Rank", "Name", "Symbol", "Market Cap"]].to_dict("records")


def find_perpetual_symbols(client: CoinalyzeClient, coin_symbols: List[str]) -> Dict[str, str]:
    futures = client.get_future_markets()
    if not futures:
        logger.error("Failed to fetch futures markets")
        return {}

    preferred_exchanges = ["A", "6", "3", "0", "2"]
    symbol_map: Dict[str, str] = {}

    for coin_symbol in coin_symbols:
        matches = [
            f
            for f in futures
            if (
                f.get("base_asset") == coin_symbol
                and f.get("is_perpetual")
                and f.get("quote_asset") in ["USDT", "USD", "USDC"]
            )
        ]
        if matches:
            matches_sorted = sorted(
                matches,
                key=lambda x: (
                    preferred_exchanges.index(x.get("exchange"))
                    if x.get("exchange") in preferred_exchanges
                    else 999
                ),
            )
            symbol_map[coin_symbol] = matches_sorted[0]["symbol"]
            logger.info(f"  {coin_symbol} -> {symbol_map[coin_symbol]}")
        else:
            logger.warning(f"  {coin_symbol} -> No perpetual found")

    return symbol_map


def fetch_max_history_for_symbol(
    client: CoinalyzeClient,
    symbol: str,
    start_year: int = 2019,
) -> List[Dict]:
    from datetime import datetime as _dt

    start_ts = int(_dt(start_year, 1, 1).timestamp())
    end_ts = int(_dt.now().timestamp())

    logger.info(
        f"  Fetching {symbol} from {_dt.fromtimestamp(start_ts).date()} to {_dt.fromtimestamp(end_ts).date()}"
    )

    rows: List[Dict] = []

    try:
        result = client.get_open_interest_history(
            symbols=symbol,
            interval="daily",
            from_ts=start_ts,
            to_ts=end_ts,
            convert_to_usd=True,
        )
        if result and len(result) > 0:
            history = result[0].get("history", [])
            if history:
                logger.info(f"  ✓ {symbol}: {len(history)} days of data")
                for point in history:
                    rows.append(
                        {
                            "symbol": symbol,
                            "timestamp": point["t"],
                            "date": _dt.fromtimestamp(point["t"]).strftime("%Y-%m-%d"),
                            "oi_open": point.get("o"),
                            "oi_high": point.get("h"),
                            "oi_low": point.get("l"),
                            "oi_close": point.get("c"),
                        }
                    )
            else:
                logger.warning(f"  ⚠ {symbol}: No data returned")
        else:
            logger.warning(f"  ⚠ {symbol}: Failed to fetch data")
    except Exception as e:
        logger.error(f"  ✗ {symbol}: Error - {e}")

    return rows


def fetch_all_open_interest_max_history(
    client: CoinalyzeClient,
    symbols: List[str],
    start_year: int = 2019,
    max_retries: int = 3,
) -> pd.DataFrame:
    logger.info(f"\n{'='*80}")
    logger.info("FETCHING MAXIMUM AVAILABLE DAILY OI HISTORY (USD)")
    logger.info(f"{'='*80}")
    logger.info(f"Start date: {start_year}-01-01")
    logger.info(f"End date: {datetime.now().date()}")
    logger.info(f"Total symbols: {len(symbols)}")
    logger.info(f"{'='*80}\n")

    all_rows: List[Dict] = []
    wait_time = 3

    for idx, symbol in enumerate(symbols, 1):
        logger.info(f"\n[{idx}/{len(symbols)}] Processing {symbol}")
        success = False
        retry_count = 0
        while not success and retry_count < max_retries:
            try:
                data = fetch_max_history_for_symbol(client, symbol, start_year)
                if data:
                    all_rows.extend(data)
                    success = True
                else:
                    retry_count += 1
                    if retry_count < max_retries:
                        wait = 10 * retry_count
                        logger.warning(
                            f"  Retrying in {wait}s (attempt {retry_count+1}/{max_retries})..."
                        )
                        time.sleep(wait)
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    wait = 10 * retry_count
                    logger.warning(f"  Error: {e}, retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    logger.error(f"  Failed after {max_retries} attempts")
        if idx < len(symbols):
            logger.info(f"  Waiting {wait_time}s before next symbol...")
            time.sleep(wait_time)

    return pd.DataFrame(all_rows)


def resolve_output_dir() -> Path:
    for c in [Path("data/raw"), Path("/workspace/data/raw"), Path(".")]:
        if c.exists() and c.is_dir():
            return c
    return Path(".")


def main():
    print("=" * 80)
    print("FETCH ALL HISTORICAL OPEN INTEREST (OI) - MAXIMUM DAILY DATA")
    print("=" * 80)
    print("\nThis fetches ALL daily OI (USD) from 2019 to present for top 50 coins")
    print("Daily interval data is retained indefinitely by Coinalyze")
    print("=" * 80 + "\n")

    if not os.environ.get("COINALYZE_API"):
        logger.error("COINALYZE_API environment variable not set")
        return

    client = CoinalyzeClient()

    top_50 = get_top_50_coins()
    print("\nTop 50 Coins:")
    print("-" * 80)
    for coin in top_50[:10]:
        print(f"  {coin['Rank']:>2}. {coin['Name']:<30} ({coin['Symbol']})")
    if len(top_50) > 10:
        print(f"  ... and {len(top_50) - 10} more")

    coin_symbols = [coin["Symbol"] for coin in top_50]
    symbol_map = find_perpetual_symbols(client, coin_symbols)

    print(f"\n{len(symbol_map)}/{len(coin_symbols)} coins have perpetual contracts available")
    if not symbol_map:
        logger.error("No symbols found to fetch")
        return

    print("\n" + "=" * 80)
    print("Starting to fetch maximum daily OI history...")
    print("This may take several minutes depending on API rate limits")
    print("=" * 80 + "\n")

    start_time = time.time()

    coinalyze_symbols = list(symbol_map.values())
    oi_df = fetch_all_open_interest_max_history(
        client,
        coinalyze_symbols,
        start_year=2019,
    )

    elapsed = time.time() - start_time

    if oi_df.empty:
        logger.error("No open interest data retrieved")
        return

    reverse_map = {v: k for k, v in symbol_map.items()}
    coin_info_map = {coin["Symbol"]: coin for coin in top_50}

    oi_df["coin_symbol"] = oi_df["symbol"].apply(lambda x: reverse_map.get(x, ""))
    oi_df["coin_name"] = oi_df["coin_symbol"].apply(
        lambda x: coin_info_map.get(x, {}).get("Name", "")
    )
    oi_df["rank"] = oi_df["coin_symbol"].apply(lambda x: coin_info_map.get(x, {}).get("Rank", 999))

    oi_df = (
        oi_df[
            [
                "rank",
                "coin_name",
                "coin_symbol",
                "symbol",
                "date",
                "timestamp",
                "oi_open",
                "oi_high",
                "oi_low",
                "oi_close",
            ]
        ]
        .sort_values(["rank", "date"])
        .reset_index(drop=True)
    )

    out_dir = resolve_output_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    detailed_file = out_dir / f"historical_open_interest_top50_ALL_HISTORY_{ts}.csv"
    oi_df.to_csv(detailed_file, index=False)

    # Availability
    availability = oi_df.groupby(["rank", "coin_name", "coin_symbol"]).agg(
        {"date": ["count", "min", "max"]}
    )
    availability.columns = ["Days", "First Date", "Last Date"]
    availability = availability.reset_index()
    availability["Years"] = (
        (
            pd.to_datetime(availability["Last Date"]) - pd.to_datetime(availability["First Date"])
        ).dt.days
        / 365.25
    ).round(2)

    availability_file = out_dir / f"open_interest_data_availability_{ts}.csv"
    availability.to_csv(availability_file, index=False)

    # Summary
    summary = (
        oi_df.groupby(["rank", "coin_name", "coin_symbol"])
        .agg({"oi_close": ["count", "mean", "std", "min", "max"]})
        .round(4)
    )
    summary.columns = ["_".join(col).strip() for col in summary.columns.values]
    summary = summary.reset_index()
    summary = summary.rename(
        columns={
            "oi_close_count": "Data Points",
            "oi_close_mean": "Avg OI USD",
            "oi_close_std": "Std OI USD",
            "oi_close_min": "Min OI USD",
            "oi_close_max": "Max OI USD",
        }
    )

    summary_file = out_dir / f"historical_open_interest_top50_ALL_HISTORY_summary_{ts}.csv"
    summary.to_csv(summary_file, index=False)

    print("\n" + "=" * 80)
    print("RESULTS - COMPLETE HISTORICAL OI DATA")
    print("=" * 80)
    print(f"Execution time: {elapsed/60:.1f} minutes")
    print(f"Total data points: {len(oi_df):,}")
    print(f"Unique coins: {oi_df['coin_symbol'].nunique()}")
    print(f"Date range: {oi_df['date'].min()} to {oi_df['date'].max()}")
    print(f"\nDetailed CSV: {detailed_file}")
    print(f"Availability CSV: {availability_file}")
    print(f"Summary CSV:  {summary_file}")
    print("\n" + "=" * 80)
    print("✅ COMPLETE - ALL AVAILABLE DAILY OI DATA FETCHED!")
    print("=" * 80)


if __name__ == "__main__":
    main()
