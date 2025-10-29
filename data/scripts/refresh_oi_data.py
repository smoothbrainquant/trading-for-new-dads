#!/usr/bin/env python3
"""
Automatic OI Data Refresh Module

This module handles automatic refresh of Open Interest data when it becomes stale.
Triggered automatically by the trading system when:
- OI data is 1+ days behind current date
- OI data file is >8 hours old

Integrates with the existing fetch_all_open_interest_since_2020_all_perps.py script.
"""
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from glob import glob

import pandas as pd

# Add workspace root to path for imports
WORKSPACE_ROOT = Path(__file__).parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from data.scripts.coinalyze_client import CoinalyzeClient


def get_oi_data_status() -> Dict:
    """
    Check OI data freshness with comprehensive status.

    Returns dict with:
    - status: 'missing', 'current', 'stale_content', 'stale_file', 'error'
    - latest_date: Latest date in data (if available)
    - file_age_hours: Age of file in hours
    - days_behind: Days behind current date
    - needs_refresh: Boolean indicating if refresh is needed
    - file_path: Path to OI data file
    """
    try:
        # Find OI data file
        oi_data_dir = WORKSPACE_ROOT / "data" / "raw"
        pattern = str(oi_data_dir / "historical_open_interest_all_perps_since2020_*.csv")
        oi_files = sorted(glob(pattern), reverse=True)

        if not oi_files:
            return {"status": "missing", "needs_refresh": True, "reason": "No OI data file found"}

        oi_file = Path(oi_files[0])

        # Check file modification time
        file_mtime = datetime.fromtimestamp(oi_file.stat().st_mtime)
        file_age_hours = (datetime.now() - file_mtime).total_seconds() / 3600

        # Read data and check content date
        df = pd.read_csv(oi_file, usecols=["date"], nrows=100000)
        df["date"] = pd.to_datetime(df["date"])
        max_date = df["date"].max()
        today = pd.Timestamp(datetime.now().date())
        days_behind = (today - max_date).days

        # Determine if refresh is needed
        needs_refresh = False
        status = "current"
        reason = None

        if days_behind >= 1:
            needs_refresh = True
            status = "stale_content"
            reason = f"Data is {days_behind} day(s) behind current date"
        elif file_age_hours > 8:
            needs_refresh = True
            status = "stale_file"
            reason = f"File is {file_age_hours:.1f} hours old (>8 hour threshold)"

        return {
            "status": status,
            "latest_date": max_date.date(),
            "file_age_hours": file_age_hours,
            "days_behind": days_behind,
            "needs_refresh": needs_refresh,
            "reason": reason,
            "file_path": str(oi_file),
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "needs_refresh": False,
            "reason": f"Error checking OI data: {e}",
        }


def resolve_output_dir() -> Path:
    """Find appropriate output directory for OI data."""
    for c in [Path("data/raw"), WORKSPACE_ROOT / "data" / "raw", Path(".")]:
        if c.exists() and c.is_dir():
            return c
    return Path(".")


def get_all_perp_symbols(client: CoinalyzeClient) -> Dict[str, str]:
    """
    Return map base_symbol -> preferred Coinalyze perp symbol.

    Prioritize exchanges by A (Binance), 6 (Bybit), 3 (OKX), 0 (BitMEX), 2 (Deribit).
    Only select quote in {USDT, USD, USDC}.
    """
    print("  Loading perpetual markets universe from Coinalyze...")
    futures = client.get_future_markets()
    if not futures:
        return {}

    preferred_exchanges = ["A", "6", "3", "0", "2"]
    by_base: Dict[str, List[Dict]] = {}
    for f in futures:
        if not f.get("is_perpetual"):
            continue
        base = f.get("base_asset")
        quote = f.get("quote_asset")
        exch = f.get("exchange")
        if not base or quote not in {"USDT", "USD", "USDC"}:
            continue
        by_base.setdefault(base, []).append(f)

    best: Dict[str, str] = {}
    for base, items in by_base.items():
        items_sorted = sorted(
            items,
            key=lambda x: (
                preferred_exchanges.index(x.get("exchange"))
                if x.get("exchange") in preferred_exchanges
                else 999
            ),
        )
        best[base] = items_sorted[0]["symbol"]

    print(f"  Found {len(best)} perpetual bases")
    return best


def fetch_oi_daily_history(
    client: CoinalyzeClient, symbol: str, start_year: int = 2020
) -> List[Dict]:
    """Fetch daily OI history for a single symbol since start_year."""
    start_ts = int(datetime(start_year, 1, 1).timestamp())
    end_ts = int(datetime.now().timestamp())

    try:
        res = client.get_open_interest_history(
            symbols=symbol,
            interval="daily",
            from_ts=start_ts,
            to_ts=end_ts,
            convert_to_usd=True,
        )
        rows: List[Dict] = []
        if res and len(res) > 0:
            hist = res[0].get("history", [])
            for pt in hist:
                rows.append(
                    {
                        "symbol": symbol,
                        "timestamp": pt["t"],
                        "date": datetime.fromtimestamp(pt["t"]).strftime("%Y-%m-%d"),
                        "oi_open": pt.get("o"),
                        "oi_high": pt.get("h"),
                        "oi_low": pt.get("l"),
                        "oi_close": pt.get("c"),
                    }
                )
        return rows
    except Exception as e:
        print(f"  ⚠️  Error fetching {symbol}: {e}")
        return []


def download_fresh_oi_data(start_year: int = 2020) -> Optional[Path]:
    """
    Download fresh OI data from Coinalyze and save to data/raw.

    Returns:
        Path to saved file, or None if download failed
    """
    print("\n" + "=" * 80)
    print("DOWNLOADING FRESH OI DATA")
    print("=" * 80)

    # Check for API key
    if not os.environ.get("COINALYZE_API"):
        print("❌ ERROR: COINALYZE_API environment variable not set")
        print("   Cannot download OI data without API credentials")
        return None

    try:
        client = CoinalyzeClient()

        # Get universe of perpetual symbols
        base_to_symbol = get_all_perp_symbols(client)
        if not base_to_symbol:
            print("❌ ERROR: Could not load perpetual markets universe")
            return None

        # Fetch OI history for all symbols
        all_rows: List[Dict] = []
        wait_s = 1.5  # Rate limiting: 40 calls/min = 1.5s per call
        total_symbols = len(base_to_symbol)

        print(f"\n  Fetching OI data for {total_symbols} symbols (rate limited to 40/min)")
        estimated_time = (total_symbols * wait_s) / 60
        print(f"  Estimated time: {estimated_time:.1f} minutes")
        print("")

        start_time = time.time()
        for i, (base, c_sym) in enumerate(sorted(base_to_symbol.items()), 1):
            # Progress indicator
            if i % 10 == 0 or i == 1:
                elapsed = (time.time() - start_time) / 60
                remaining = ((total_symbols - i) * wait_s) / 60
                print(
                    f"  [{i:4d}/{total_symbols}] {base:8s}: {c_sym:25s} | Elapsed: {elapsed:.1f}m | Remaining: {remaining:.1f}m"
                )

            rows = fetch_oi_daily_history(client, c_sym, start_year=start_year)
            if rows:
                for r in rows:
                    r["coin_symbol"] = base
                all_rows.extend(rows)

            time.sleep(wait_s)

        if not all_rows:
            print("❌ ERROR: No OI data fetched")
            return None

        # Build DataFrame
        df = pd.DataFrame(all_rows)
        df = df[
            [
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
        df = df.sort_values(["coin_symbol", "date"]).reset_index(drop=True)

        # Save to file with timestamp
        out_dir = resolve_output_dir()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"historical_open_interest_all_perps_since2020_{ts}.csv"
        df.to_csv(out_path, index=False)

        # Print summary
        print("\n" + "=" * 80)
        print("✓ OI DATA DOWNLOAD COMPLETE")
        print("=" * 80)
        print(f"  File: {out_path}")
        print(f"  Date range: {df['date'].min()} → {df['date'].max()}")
        print(f"  Unique bases: {df['coin_symbol'].nunique()}")
        print(f"  Total rows: {len(df):,}")
        print(f"  File size: {out_path.stat().st_size / 1024 / 1024:.1f} MB")
        elapsed_total = (time.time() - start_time) / 60
        print(f"  Time taken: {elapsed_total:.1f} minutes")
        print("=" * 80)

        return out_path

    except Exception as e:
        print(f"\n❌ ERROR during OI data download: {e}")
        import traceback

        traceback.print_exc()
        return None


def check_and_refresh_oi_data(force: bool = False, start_year: int = 2020) -> Dict:
    """
    Check OI data freshness and automatically refresh if needed.

    This is the main entry point for automatic OI data management.

    Args:
        force: If True, force download regardless of freshness
        start_year: Start year for historical data (default 2020)

    Returns:
        dict with keys:
        - refreshed: Boolean indicating if data was refreshed
        - status: Current status after check/refresh
        - file_path: Path to OI data file
    """
    print("\n" + "=" * 80)
    print("OI DATA FRESHNESS CHECK")
    print("=" * 80)

    # Check current status
    status = get_oi_data_status()

    print(f"\nStatus: {status.get('status', 'unknown')}")
    if "latest_date" in status:
        print(f"Latest data date: {status['latest_date']}")
    if "file_age_hours" in status:
        print(f"File age: {status['file_age_hours']:.1f} hours")
    if "days_behind" in status:
        print(f"Days behind: {status['days_behind']}")
    if status.get("reason"):
        print(f"Reason: {status['reason']}")

    # Determine if refresh is needed
    needs_refresh = force or status.get("needs_refresh", False)

    if not needs_refresh:
        print("\n✓ OI data is fresh - no refresh needed")
        return {
            "refreshed": False,
            "status": status.get("status"),
            "file_path": status.get("file_path"),
        }

    # Refresh is needed
    if force:
        print("\n🔄 FORCED REFRESH requested")
    else:
        print(f"\n🔄 AUTOMATIC REFRESH triggered: {status.get('reason')}")

    print("\nStarting OI data download...")
    new_file = download_fresh_oi_data(start_year=start_year)

    if new_file:
        print("\n✓ OI data successfully refreshed")
        return {"refreshed": True, "status": "current", "file_path": str(new_file)}
    else:
        print("\n❌ OI data refresh FAILED")
        print("   Trading will use existing data (if available)")
        return {
            "refreshed": False,
            "status": "refresh_failed",
            "file_path": status.get("file_path"),
        }


def main():
    """CLI entry point for manual OI data refresh."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Check and refresh OI data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--force", action="store_true", help="Force download even if data is fresh")
    parser.add_argument(
        "--check-only", action="store_true", help="Only check status, do not download"
    )
    parser.add_argument(
        "--start-year", type=int, default=2020, help="Start year for historical data"
    )
    args = parser.parse_args()

    if args.check_only:
        # Just check status
        status = get_oi_data_status()
        print("\n" + "=" * 80)
        print("OI DATA STATUS")
        print("=" * 80)
        print(f"Status: {status.get('status')}")
        if "latest_date" in status:
            print(f"Latest data date: {status['latest_date']}")
        if "file_age_hours" in status:
            print(f"File age: {status['file_age_hours']:.1f} hours")
        if "days_behind" in status:
            print(f"Days behind: {status['days_behind']}")
        if status.get("file_path"):
            print(f"File: {status['file_path']}")
        print(f"Needs refresh: {status.get('needs_refresh', False)}")
        if status.get("reason"):
            print(f"Reason: {status['reason']}")
    else:
        # Check and refresh if needed
        result = check_and_refresh_oi_data(force=args.force, start_year=args.start_year)

        if result["refreshed"]:
            print("\n✓ SUCCESS: OI data is now fresh")
        elif result["status"] == "current":
            print("\n✓ SUCCESS: OI data was already fresh")
        else:
            print("\n❌ FAILED: Could not refresh OI data")
            sys.exit(1)


if __name__ == "__main__":
    main()
