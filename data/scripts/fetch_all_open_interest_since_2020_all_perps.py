#!/usr/bin/env python3
"""
Fetch Historical Open Interest (OI) since 2020 for all perpetual bases
- Uses Coinalyze API daily OI history (unlimited retention per docs)
- Universe: All futures markets marked is_perpetual across major USD/USDT/USDC quotes
- Saves detailed CSV to data/raw

Requires env: COINALYZE_API
"""
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import pandas as pd

from data.scripts.coinalyze_client import CoinalyzeClient


def resolve_output_dir() -> Path:
    for c in [Path('data/raw'), Path('/workspace/data/raw'), Path('.')]:
        if c.exists() and c.is_dir():
            return c
    return Path('.')


def get_all_perp_symbols(client: CoinalyzeClient) -> Dict[str, str]:
    """Return map base_symbol -> preferred Coinalyze perp symbol.

    Prioritize exchanges by A (Binance), 6 (Bybit), 3 (OKX), 0 (BitMEX), 2 (Deribit).
    Only select quote in {USDT, USD, USDC}.
    """
    futures = client.get_future_markets()
    if not futures:
        return {}

    preferred_exchanges = ['A', '6', '3', '0', '2']
    by_base: Dict[str, List[Dict]] = {}
    for f in futures:
        if not f.get('is_perpetual'):
            continue
        base = f.get('base_asset')
        quote = f.get('quote_asset')
        exch = f.get('exchange')
        if not base or quote not in {'USDT','USD','USDC'}:
            continue
        by_base.setdefault(base, []).append(f)

    best: Dict[str, str] = {}
    for base, items in by_base.items():
        items_sorted = sorted(
            items,
            key=lambda x: (preferred_exchanges.index(x.get('exchange')) if x.get('exchange') in preferred_exchanges else 999)
        )
        best[base] = items_sorted[0]['symbol']
    return best


def fetch_oi_daily_history_batch(client: CoinalyzeClient, symbols: List[str], start_year: int = 2020) -> List[Dict]:
    """Fetch daily OI history for up to 20 coinalyze symbols in one call."""
    from datetime import datetime as _dt

    if not symbols:
        return []

    start_ts = int(_dt(start_year, 1, 1).timestamp())
    end_ts = int(_dt.now().timestamp())

    try:
        res = client.get_open_interest_history(
            symbols=','.join(symbols),
            interval='daily',
            from_ts=start_ts,
            to_ts=end_ts,
            convert_to_usd=True,
        )
        rows: List[Dict] = []
        if res:
            for item in res:
                sym = item.get('symbol')
                history = item.get('history', [])
                for pt in history:
                    rows.append({
                        'symbol': sym,
                        'timestamp': pt['t'],
                        'date': _dt.fromtimestamp(pt['t']).strftime('%Y-%m-%d'),
                        'oi_open': pt.get('o'),
                        'oi_high': pt.get('h'),
                        'oi_low': pt.get('l'),
                        'oi_close': pt.get('c'),
                    })
        return rows
    except Exception:
        return []


def main():
    print("="*80)
    print("FETCH OI SINCE 2020 - ALL PERPETUAL BASES")
    print("="*80)

    if not os.environ.get('COINALYZE_API'):
        print("ERROR: COINALYZE_API env var not set")
        return

    client = CoinalyzeClient()

    # Universe
    print("Loading perpetual markets universe...")
    base_to_symbol = get_all_perp_symbols(client)
    print(f"Bases with perps: {len(base_to_symbol)}")

    all_rows: List[Dict] = []
    items = sorted(base_to_symbol.items())
    batch_size = 20  # Coinalyze allows up to 20 per request
    for i in range(0, len(items), batch_size):
        batch = items[i:i+batch_size]
        csymbols = [cs for _, cs in batch]
        rev = {cs: base for base, cs in batch}
        print(f"Batch {i//batch_size + 1}/{(len(items)-1)//batch_size + 1}: {len(csymbols)} symbols")
        rows = fetch_oi_daily_history_batch(client, csymbols, start_year=2020)
        if rows:
            for r in rows:
                # map coinalyze symbol back to base
                r['coin_symbol'] = rev.get(r['symbol'], '')
            all_rows.extend(rows)

    if not all_rows:
        print("No data fetched.")
        return

    df = pd.DataFrame(all_rows)
    df = df[['coin_symbol','symbol','date','timestamp','oi_open','oi_high','oi_low','oi_close']]
    df = df.sort_values(['coin_symbol','date']).reset_index(drop=True)

    out_dir = resolve_output_dir()
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_path = out_dir / f"historical_open_interest_all_perps_since2020_{ts}.csv"
    df.to_csv(out_path, index=False)

    print("\nSaved:", out_path)
    print("Date range:", df['date'].min(), '→', df['date'].max())
    print("Unique bases:", df['coin_symbol'].nunique())
    print("Total rows:", len(df))


if __name__ == '__main__':
    main()
