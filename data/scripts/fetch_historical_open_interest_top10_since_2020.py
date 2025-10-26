#!/usr/bin/env python3
"""
Fetch Historical Open Interest (OI) for Top N Coins since 2020
- Uses CoinMarketCap snapshots to select latest top N coins (default 50)
- Maps to Coinalyze perpetual futures symbols
- Fetches DAILY OI (USD) from 2020-01-01 to present
- Saves detailed CSV and summary CSV to data/raw

Requires env var: COINALYZE_API
"""
import os
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd

from coinalyze_client import CoinalyzeClient


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_cmc_file() -> str:
    """Locate the CoinMarketCap historical snapshots CSV file."""
    candidates = [
        'data/raw/coinmarketcap_historical_all_snapshots.csv',
        '/workspace/data/raw/coinmarketcap_historical_all_snapshots.csv',
        'coinmarketcap_historical_all_snapshots.csv',
    ]
    for path in candidates:
        if Path(path).exists():
            return path
    raise FileNotFoundError(
        "coinmarketcap_historical_all_snapshots.csv not found in expected locations"
    )


def get_top_n_coins(n: int = 100) -> List[Dict]:
    """Load top N coins by latest CoinMarketCap snapshot."""
    cmc_path = find_cmc_file()
    logger.info(f"Loading CoinMarketCap data from {cmc_path}...")

    df = pd.read_csv(cmc_path)
    latest_date = df['snapshot_date'].max()
    logger.info(f"Latest snapshot: {latest_date}")

    latest = df[df['snapshot_date'] == latest_date].copy()
    latest = latest.sort_values('Rank').head(n)

    logger.info(f"Found {len(latest)} coins in top {n}")
    return latest[['Rank', 'Name', 'Symbol', 'Market Cap']].to_dict('records')


def find_perpetual_symbols(client: CoinalyzeClient, coin_symbols: List[str]) -> Dict[str, str]:
    """
    Map coin symbols (e.g., BTC) to Coinalyze perpetual symbols (e.g., BTCUSDT_PERP.A)
    Prioritizes: Binance (A), Bybit (6), OKX (3), BitMEX (0), Deribit (2)
    Only USDT/USD/USDC quotes considered.
    """
    logger.info("Fetching available perpetual markets from Coinalyze...")

    futures = client.get_future_markets()
    if not futures:
        logger.error("Failed to fetch futures markets")
        return {}

    logger.info(f"Found {len(futures)} future markets")

    preferred_exchanges = ['A', '6', '3', '0', '2']
    symbol_map: Dict[str, str] = {}

    for coin_symbol in coin_symbols:
        matches = [
            f for f in futures
            if (
                f.get('base_asset') == coin_symbol
                and f.get('is_perpetual')
                and f.get('quote_asset') in ['USDT', 'USD', 'USDC']
            )
        ]

        if matches:
            matches_sorted = sorted(
                matches,
                key=lambda x: (
                    preferred_exchanges.index(x.get('exchange'))
                    if x.get('exchange') in preferred_exchanges else 999
                )
            )
            best_symbol = matches_sorted[0]['symbol']
            symbol_map[coin_symbol] = best_symbol
            logger.info(f"  {coin_symbol} -> {best_symbol}")
        else:
            logger.warning(f"  {coin_symbol} -> No perpetual found")

    return symbol_map


def fetch_oi_history_range(
    client: CoinalyzeClient,
    symbols: List[str],
    start_ts: int,
    end_ts: int,
    interval: str = 'daily',
    convert_to_usd: bool = True,
) -> pd.DataFrame:
    """
    Fetch historical OI (USD) for given symbols between start_ts and end_ts.

    Returns dataframe with columns:
    - symbol, timestamp, date, oi_open, oi_high, oi_low, oi_close
    """
    logger.info(
        f"\nFetching OI from {datetime.fromtimestamp(start_ts)} to {datetime.fromtimestamp(end_ts)}"
    )
    logger.info(f"Interval: {interval}")

    all_rows: List[Dict] = []
    batch_size = 5  # conservative vs API max 20

    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i + batch_size]
        batch_str = ','.join(batch)
        logger.info(
            f"\nProcessing batch {i // batch_size + 1}/{(len(symbols)-1) // batch_size + 1}: {batch}"
        )
        try:
            result = client.get_open_interest_history(
                symbols=batch_str,
                interval=interval,
                from_ts=start_ts,
                to_ts=end_ts,
                convert_to_usd=convert_to_usd,
            )
            if result:
                for item in result:
                    sym = item.get('symbol')
                    history = item.get('history', [])
                    logger.info(f"  {sym}: {len(history)} data points")
                    for point in history:
                        all_rows.append({
                            'symbol': sym,
                            'timestamp': point['t'],
                            'date': datetime.fromtimestamp(point['t']).strftime('%Y-%m-%d'),
                            'oi_open': point.get('o'),
                            'oi_high': point.get('h'),
                            'oi_low': point.get('l'),
                            'oi_close': point.get('c'),
                        })
            else:
                logger.warning("  Failed to fetch data for batch")
        except Exception as e:
            logger.error(f"  Error fetching batch: {e}")
        time.sleep(2)  # rate-limit between batches

    return pd.DataFrame(all_rows)


def resolve_output_dir() -> Path:
    """Return preferred output directory (data/raw if exists else current)."""
    candidates = [Path('data/raw'), Path('/workspace/data/raw'), Path('.')]
    for c in candidates:
        try:
            if c.exists() and c.is_dir():
                return c
        except Exception:
            continue
    return Path('.')


def main():
    print("=" * 80)
    print("FETCH HISTORICAL OPEN INTEREST (OI) - TOP 100 COINS SINCE 2020")
    print("=" * 80)

    if not os.environ.get('COINALYZE_API'):
        logger.error("COINALYZE_API environment variable not set")
        return

    client = CoinalyzeClient()

    # Step 1: Top N coins by latest snapshot
    top_n = 100
    top_10 = get_top_n_coins(top_n)
    print(f"\nTop {top_n} Coins:")
    print("-" * 80)
    for coin in top_10:
        print(f"  {coin['Rank']:>2}. {coin['Name']:<30} ({coin['Symbol']})")

    # Step 2: Map to Coinalyze perpetual symbols
    coin_symbols = [coin['Symbol'] for coin in top_10]
    symbol_map = find_perpetual_symbols(client, coin_symbols)

    print(f"\n{len(symbol_map)}/{len(coin_symbols)} coins have perpetual contracts available")
    if not symbol_map:
        logger.error("No symbols found to fetch")
        return

    # Step 3: Fetch OI history from 2020-01-01 to present (daily, USD)
    coinalyze_symbols = list(symbol_map.values())
    start_ts = int(datetime(2020, 1, 1).timestamp())
    end_ts = int(datetime.now().timestamp())
    oi_df = fetch_oi_history_range(
        client,
        coinalyze_symbols,
        start_ts=start_ts,
        end_ts=end_ts,
        interval='daily',
        convert_to_usd=True,
    )

    if oi_df.empty:
        logger.error("No open interest data retrieved")
        return

    # Step 4: Add coin info
    reverse_map = {v: k for k, v in symbol_map.items()}
    coin_info_map = {coin['Symbol']: coin for coin in top_10}

    oi_df['coin_symbol'] = oi_df['symbol'].apply(lambda x: reverse_map.get(x, ''))
    oi_df['coin_name'] = oi_df['coin_symbol'].apply(lambda x: coin_info_map.get(x, {}).get('Name', ''))
    oi_df['rank'] = oi_df['coin_symbol'].apply(lambda x: coin_info_map.get(x, {}).get('Rank', 999))

    # Reorder columns
    oi_df = oi_df[[
        'rank', 'coin_name', 'coin_symbol', 'symbol',
        'date', 'timestamp', 'oi_open', 'oi_high', 'oi_low', 'oi_close'
    ]].sort_values(['rank', 'date']).reset_index(drop=True)

    # Step 5: Save outputs
    out_dir = resolve_output_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    detailed_file = out_dir / f'historical_open_interest_top{top_n}_since2020_{timestamp}.csv'
    oi_df.to_csv(detailed_file, index=False)

    # Summary by coin
    summary = (
        oi_df.groupby(['rank', 'coin_name', 'coin_symbol'])
        .agg({
            'oi_close': ['count', 'mean', 'std', 'min', 'max']
        })
        .round(4)
    )
    summary.columns = ['_'.join(col).strip() for col in summary.columns.values]
    summary = summary.reset_index()
    summary = summary.rename(columns={
        'oi_close_count': 'Data Points',
        'oi_close_mean': 'Avg OI USD',
        'oi_close_std': 'Std OI USD',
        'oi_close_min': 'Min OI USD',
        'oi_close_max': 'Max OI USD',
    })

    summary_file = out_dir / f'historical_open_interest_top{top_n}_since2020_summary_{timestamp}.csv'
    summary.to_csv(summary_file, index=False)

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Total data points: {len(oi_df):,}")
    print(f"Unique coins: {oi_df['coin_symbol'].nunique()}")
    print(f"Date range: {oi_df['date'].min()} to {oi_df['date'].max()}")
    print(f"\nDetailed CSV: {detailed_file}")
    print(f"Summary CSV:  {summary_file}")
    print("\n" + "=" * 80)
    print("✅ COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    main()
