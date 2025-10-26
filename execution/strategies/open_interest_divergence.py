from __future__ import annotations

from typing import Dict, List, Tuple
from datetime import datetime, timedelta

import pandas as pd

from .utils import get_base_symbol


def _parse_trading_symbol(symbol: str) -> Tuple[str, str]:
    if not isinstance(symbol, str) or '/' not in symbol:
        return symbol, ''
    base, rhs = symbol.split('/', 1)
    quote = rhs.split(':', 1)[0] if ':' in rhs else rhs
    return base, quote


def _build_coinalyze_symbol(base: str, quote: str, exchange_code: str) -> str:
    """
    Build Coinalyze symbol. Format varies by exchange:
    - Hyperliquid (H): {BASE}.H  (e.g., BTC.H)
    - Binance (A): {BASE}{QUOTE}_PERP.A (e.g., BTCUSDT_PERP.A)
    """
    if exchange_code == 'H':
        return f"{base}.{exchange_code}"
    else:
        return f"{base}{quote}_PERP.{exchange_code}"


def _prepare_price_df(historical_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: List[pd.DataFrame] = []
    for sym, df in historical_data.items():
        d = df.copy()
        if 'symbol' not in d.columns:
            d['symbol'] = sym
        d['base_symbol'] = d['symbol'].astype(str).apply(get_base_symbol)
        rows.append(d[['date', 'close', 'symbol', 'base_symbol']])
    if not rows:
        return pd.DataFrame(columns=['date', 'close', 'symbol', 'base_symbol'])
    out = pd.concat(rows, ignore_index=True)
    out['date'] = pd.to_datetime(out['date'])
    out = out.sort_values(['base_symbol', 'date']).reset_index(drop=True)
    return out


def _fetch_oi_history_for_universe(
    universe_symbols: List[str],
    exchange_code: str = 'H',
    days: int = 200,
) -> pd.DataFrame:
    """Fetch daily OI USD history for given trading symbols' bases.

    Returns columns: ['coin_symbol','coinalyze_symbol','date','oi_close']
    """
    try:
        from data.scripts.coinalyze_client import CoinalyzeClient  # type: ignore
    except Exception:
        return pd.DataFrame()

    client = CoinalyzeClient()

    # Map base -> coinalyze symbol (choose quote from trading symbol or default USDC)
    base_to_csym: Dict[str, str] = {}
    for tsym in universe_symbols:
        base, quote = _parse_trading_symbol(tsym)
        if not base:
            continue
        if not quote:
            quote = 'USDC'
        c_sym = _build_coinalyze_symbol(base, quote, exchange_code)
        base_to_csym.setdefault(base, c_sym)

    if not base_to_csym:
        return pd.DataFrame()

    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=days)).timestamp())

    rows: List[dict] = []
    # Coinalyze allows up to 20 symbols per request
    items = list(base_to_csym.items())
    chunk = 20
    for i in range(0, len(items), chunk):
        batch = items[i:i+chunk]
        symbols_param = ','.join(cs for _, cs in batch)
        try:
            data = client.get_open_interest_history(
                symbols=symbols_param,
                interval='daily',
                from_ts=start_ts,
                to_ts=end_ts,
                convert_to_usd=True,
            )
        except Exception:
            data = None
        if not data:
            continue
        # Reverse map coinalyze_symbol -> base
        csym_to_base = {cs: b for b, cs in batch}
        for item in data:
            csym = item.get('symbol')
            hist = item.get('history', [])
            base = csym_to_base.get(csym)
            if not base:
                continue
            for pt in hist:
                rows.append({
                    'coin_symbol': base,
                    'coinalyze_symbol': csym,
                    'date': datetime.fromtimestamp(pt['t']).strftime('%Y-%m-%d'),
                    'oi_close': pt.get('c'),
                })
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['coin_symbol', 'date']).reset_index(drop=True)
    return df[['coin_symbol', 'coinalyze_symbol', 'date', 'oi_close']]


def strategy_oi_divergence(
    historical_data: Dict[str, pd.DataFrame],
    notional: float,
    mode: str = 'trend',  # or 'divergence'
    lookback: int = 30,
    top_n: int = 10,
    bottom_n: int = 10,
    exchange_code: str = 'H',  # Hyperliquid by default
) -> Dict[str, float]:
    """Open Interest divergence/trend strategy using recent OI history from Coinalyze.

    - Builds OI z-score vs price returns over a rolling window
    - Selects top/bottom by score
    - Allocates risk-parity within each side using recent price volatility
    """
    if not historical_data:
        return {}

    # Build price dataframe and universe mappings
    price_df = _prepare_price_df(historical_data)
    if price_df.empty:
        return {}

    # Universe trading symbols and mapping base -> trading symbol
    universe_symbols = list(historical_data.keys())
    base_to_trading: Dict[str, str] = {}
    for tsym in universe_symbols:
        base = get_base_symbol(tsym)
        base_to_trading[base] = tsym

    # Fetch OI history for last ~200 days
    oi_df = _fetch_oi_history_for_universe(universe_symbols, exchange_code=exchange_code, days=max(lookback * 4, 120))
    if oi_df is None or oi_df.empty:
        print("  ⚠️  OI DIVERGENCE STRATEGY: No OI data available from Coinalyze!")
        print(f"       Check: 1) COINALYZE_API key is set, 2) symbols exist on exchange {exchange_code}")
        print(f"       This strategy requires {max(lookback * 4, 120)} days of OI history")
        return {}

    # Compute scores
    from signals.calc_open_interest_divergence import (
        compute_oi_divergence_scores,
        build_equal_or_risk_parity_weights,
    )

    scores = compute_oi_divergence_scores(oi_df, price_df, lookback=lookback)
    if scores.empty:
        return {}

    # Pick on latest date present across both
    latest_date = min(price_df['date'].max(), oi_df['date'].max())
    day_scores = scores[scores['date'] == latest_date]
    if day_scores.empty:
        # fallback to last available in scores
        latest_date = scores['date'].max()
        day_scores = scores[scores['date'] == latest_date]
    col = 'score_trend' if mode == 'trend' else 'score_divergence'
    day_scores = day_scores[['symbol', col]].dropna()
    if day_scores.empty:
        return {}

    sel = day_scores.sort_values(col, ascending=False)
    long_bases = sel.head(max(0, int(top_n)))['symbol'].tolist()
    short_bases = sel.tail(max(0, int(bottom_n)))['symbol'].tolist()

    # Build risk-parity weights on base-level price data
    weights_base = build_equal_or_risk_parity_weights(
        price_df=price_df.rename(columns={'base_symbol': 'symbol'})[['date','symbol','close']],
        long_symbols=long_bases,
        short_symbols=short_bases,
        notional=notional,
        volatility_window=30,
        use_risk_parity=True,
    )

    # Map base -> trading symbols used by execution
    weights_trading: Dict[str, float] = {}
    for base, w in weights_base.items():
        tsym = base_to_trading.get(base)
        if tsym:
            weights_trading[tsym] = weights_trading.get(tsym, 0.0) + w

    return weights_trading
