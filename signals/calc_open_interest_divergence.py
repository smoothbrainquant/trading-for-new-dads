from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd


@dataclass
class OIDivergenceConfig:
    lookback: int = 30
    mode: str = "trend"  # "trend" or "divergence"
    top_n: int = 10
    bottom_n: int = 10


def _zscore(series: pd.Series, window: int) -> pd.Series:
    rolling = series.rolling(window=window, min_periods=window)
    mean = rolling.mean()
    std = rolling.std(ddof=0)
    with np.errstate(divide='ignore', invalid='ignore'):
        z = (series - mean) / std
    return z.replace([np.inf, -np.inf], np.nan)


def prepare_price_data(price_df: pd.DataFrame) -> pd.DataFrame:
    """Normalize price data schema to ['date','symbol','close']."""
    df = price_df.copy()
    if 'date' not in df.columns:
        raise ValueError("price_df must contain 'date' column")
    if 'close' not in df.columns:
        raise ValueError("price_df must contain 'close' column")
    if 'symbol' in df.columns:
        sym_col = 'symbol'
    elif 'base_symbol' in df.columns:
        sym_col = 'base_symbol'
    elif 'base' in df.columns:
        sym_col = 'base'
    else:
        raise ValueError("price_df must contain one of: 'symbol', 'base_symbol', 'base'")

    out = df[['date', sym_col, 'close']].rename(columns={sym_col: 'symbol'})
    out['date'] = pd.to_datetime(out['date'])
    out = out.sort_values(['symbol', 'date']).reset_index(drop=True)
    return out


def prepare_oi_data(oi_df: pd.DataFrame) -> pd.DataFrame:
    """Normalize OI data schema to ['date','symbol','oi_close']."""
    df = oi_df.copy()
    if 'date' not in df.columns:
        raise ValueError("oi_df must contain 'date' column")
    # select oi column
    oi_col = None
    for c in ['oi_close', 'oi', 'open_interest', 'oi_usd']:
        if c in df.columns:
            oi_col = c
            break
    if oi_col is None:
        raise ValueError("oi_df must contain one of ['oi_close','oi','open_interest','oi_usd']")

    # select symbol column
    sym_col = None
    for c in ['coin_symbol', 'base_symbol', 'symbol', 'base']:
        if c in df.columns:
            sym_col = c
            break
    if sym_col is None:
        raise ValueError("oi_df must contain a symbol column: coin_symbol/base_symbol/symbol/base")

    out = df[['date', sym_col, oi_col]].rename(columns={sym_col: 'symbol', oi_col: 'oi_close'})
    out['date'] = pd.to_datetime(out['date'])
    out = out.sort_values(['symbol', 'date']).reset_index(drop=True)
    return out


essential_cols = ['date','symbol','ret','d_oi','z_ret','z_doi','score_trend','score_divergence']

def compute_oi_divergence_scores(
    oi_df: pd.DataFrame,
    price_df: pd.DataFrame,
    lookback: int = 30,
) -> pd.DataFrame:
    """Compute OI trend and divergence scores per symbol/day.

    Returns columns essential_cols.
    """
    prices = prepare_price_data(price_df)
    oi = prepare_oi_data(oi_df)

    # Check for date/symbol overlap before merge
    if prices.empty or oi.empty:
        print("    ⚠️  Empty price or OI data, cannot compute scores")
        return pd.DataFrame(columns=essential_cols)
    
    # Validate date overlap
    price_dates = set(prices['date'].dt.date)
    oi_dates = set(oi['date'].dt.date)
    overlap_dates = price_dates & oi_dates
    
    if not overlap_dates:
        print(f"    ⚠️  No date overlap for OI divergence merge:")
        print(f"       Price dates: {min(price_dates)} to {max(price_dates)} ({len(price_dates)} days)")
        print(f"       OI dates: {min(oi_dates)} to {max(oi_dates)} ({len(oi_dates)} days)")
        return pd.DataFrame(columns=essential_cols)
    
    # Validate symbol overlap
    price_symbols = set(prices['symbol'].unique())
    oi_symbols = set(oi['symbol'].unique())
    overlap_symbols = price_symbols & oi_symbols
    
    if not overlap_symbols:
        print(f"    ⚠️  No symbol overlap for OI divergence merge:")
        print(f"       Price symbols: {list(price_symbols)[:10]} (showing first 10)")
        print(f"       OI symbols: {list(oi_symbols)[:10]} (showing first 10)")
        return pd.DataFrame(columns=essential_cols)

    df = pd.merge(prices, oi, on=['date', 'symbol'], how='inner')
    if df.empty:
        print(f"    ⚠️  Merge produced empty dataframe despite overlap:")
        print(f"       Date overlap: {len(overlap_dates)} days")
        print(f"       Symbol overlap: {len(overlap_symbols)} symbols")
        return pd.DataFrame(columns=essential_cols)

    df['ret'] = df.groupby('symbol')['close'].transform(lambda x: np.log(x) - np.log(x.shift(1)))
    df['d_oi'] = df.groupby('symbol')['oi_close'].transform(lambda x: np.log(x) - np.log(x.shift(1)))

    df['z_ret'] = (
        df.groupby('symbol')['ret']
        .transform(lambda s: _zscore(s, window=lookback))
    )
    df['z_doi'] = (
        df.groupby('symbol')['d_oi']
        .transform(lambda s: _zscore(s, window=lookback))
    )

    df['score_trend'] = df['z_doi'] * np.sign(df['ret'].fillna(0.0))
    df['score_divergence'] = -df['score_trend']

    return df[essential_cols]


def select_portfolio_on_date(
    scores_df: pd.DataFrame,
    as_of_date: pd.Timestamp,
    mode: str = 'trend',
    top_n: int = 10,
    bottom_n: int = 10,
) -> Tuple[List[str], List[str]]:
    if scores_df.empty:
        return [], []
    df = scores_df.copy()
    df = df[df['date'] == pd.to_datetime(as_of_date)]
    if df.empty:
        return [], []

    col = 'score_trend' if mode == 'trend' else 'score_divergence'
    df = df[['symbol', col]].dropna()
    if df.empty:
        return [], []

    df_sorted = df.sort_values(col, ascending=False)
    longs = df_sorted.head(max(0, int(top_n)))['symbol'].tolist()
    shorts = df_sorted.tail(max(0, int(bottom_n)))['symbol'].tolist()
    return longs, shorts


def build_equal_or_risk_parity_weights(
    price_df: pd.DataFrame,
    long_symbols: List[str],
    short_symbols: List[str],
    notional: float,
    volatility_window: int = 30,
    use_risk_parity: bool = True,
) -> Dict[str, float]:
    result: Dict[str, float] = {}
    longs = list(dict.fromkeys(long_symbols))
    shorts = list(dict.fromkeys(short_symbols))

    if not longs and not shorts:
        return result

    prices = prepare_price_data(price_df)
    if use_risk_parity and (longs or shorts):
        prices = prices.copy()
        prices['ret'] = prices.groupby('symbol')['close'].transform(lambda x: np.log(x) - np.log(x.shift(1)))
        vol = (
            prices.groupby('symbol')['ret']
            .transform(lambda s: s.rolling(window=volatility_window, min_periods=volatility_window).std() * np.sqrt(365))
        )
        prices['vol'] = vol
        latest = prices.sort_values('date').groupby('symbol', as_index=False).tail(1)
        vol_map = dict(zip(latest['symbol'], latest['vol']))
    else:
        vol_map = {}

    alloc_long = notional * 0.5 if longs and shorts else (notional if longs else 0.0)
    alloc_short = notional * 0.5 if longs and shorts else (notional if shorts else 0.0)

    def _alloc(symbols: List[str], alloc: float, sign: float) -> None:
        if not symbols or alloc <= 0:
            return
        if use_risk_parity:
            vols = {s: vol_map.get(s) for s in symbols}
            vols = {s: v for s, v in vols.items() if v is not None and v > 0}
            if vols:
                inv = {s: 1.0 / v for s, v in vols.items()}
                total = sum(inv.values())
                if total > 0:
                    for s, val in inv.items():
                        result[s] = result.get(s, 0.0) + sign * alloc * (val / total)
                    return
        # fallback equal weight
        w = alloc / len(symbols)
        for s in symbols:
            result[s] = result.get(s, 0.0) + sign * w

    _alloc(longs, alloc_long, +1.0)
    _alloc(shorts, alloc_short, -1.0)
    return result
