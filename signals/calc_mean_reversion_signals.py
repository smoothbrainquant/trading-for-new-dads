"""
Mean Reversion Signal Calculation Module
Constructs a contrarian long signal based on negative N-day return z-scores
(optionally gated by high absolute volume z-scores).

Default configuration follows research findings:
- Period: 2-day returns
- Return threshold: z < -1.5 (extreme negative move)
- Volume threshold: |z| > 1.0 (high/abnormal volume)
- Long-only (do not short positive spikes)

Outputs a row-wise signal and a simple same-day "position" indicator
that is LONG on signal and FLAT otherwise (no persistence model).
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Union, Tuple, Dict, List


def _ensure_dataframe(data_source: Union[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Normalize input to a pandas DataFrame with required columns.
    """
    if isinstance(data_source, str):
        df = pd.read_csv(data_source)
    elif isinstance(data_source, pd.DataFrame):
        df = data_source.copy()
    else:
        raise TypeError("data_source must be either a file path (str) or a pandas DataFrame")

    # Parse date and sort
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    return df


def _calculate_period_changes(df: pd.DataFrame, period: int) -> pd.DataFrame:
    """
    Add N-day price and volume percent changes by symbol.
    """
    result = df.copy()
    result[f'return_{period}d'] = result.groupby('symbol')['close'].transform(
        lambda x: x.pct_change(periods=period)
    )
    result[f'volume_change_{period}d'] = result.groupby('symbol')['volume'].transform(
        lambda x: x.pct_change(periods=period)
    )
    return result


essential_cols_cache: Dict[Tuple[int, int], List[str]] = {}


def _calculate_zscores(df: pd.DataFrame, period: int, zscore_lookback: int) -> pd.DataFrame:
    """
    Compute rolling mean/std z-scores for period returns and volume changes with shift(1)
    to avoid lookahead. Returns a copy with z-score columns added.
    """
    result = df.copy()

    r_col = f'return_{period}d'
    v_col = f'volume_change_{period}d'

    # Rolling stats for returns
    result[f'{r_col}_mean'] = result.groupby('symbol')[r_col].transform(
        lambda x: x.rolling(window=zscore_lookback, min_periods=zscore_lookback).mean().shift(1)
    )
    result[f'{r_col}_std'] = result.groupby('symbol')[r_col].transform(
        lambda x: x.rolling(window=zscore_lookback, min_periods=zscore_lookback).std().shift(1)
    )

    # Rolling stats for volume
    result[f'{v_col}_mean'] = result.groupby('symbol')[v_col].transform(
        lambda x: x.rolling(window=zscore_lookback, min_periods=zscore_lookback).mean().shift(1)
    )
    result[f'{v_col}_std'] = result.groupby('symbol')[v_col].transform(
        lambda x: x.rolling(window=zscore_lookback, min_periods=zscore_lookback).std().shift(1)
    )

    # Z-scores
    result[f'return_zscore_{period}d'] = (
        (result[r_col] - result[f'{r_col}_mean']) / result[f'{r_col}_std']
    )
    result[f'volume_zscore_{period}d'] = (
        (result[v_col] - result[f'{v_col}_mean']) / result[f'{v_col}_std']
    )

    # Sanitize infinities
    result = result.replace([np.inf, -np.inf], np.nan)
    return result


def calculate_mean_reversion_signals(
    data_source: Union[str, pd.DataFrame],
    period: int = 2,
    zscore_lookback: int = 30,
    return_threshold: float = -1.5,
    volume_threshold: float = 1.0,
    require_high_volume: bool = True,
) -> pd.DataFrame:
    """
    Calculate mean reversion signals (long-on-dips) for each symbol.

    Parameters:
    - data_source: CSV path or DataFrame with columns [date, symbol, open, high, low, close, volume]
    - period: N-day percent change period for return/volume features
    - zscore_lookback: lookback window for z-score stats (shifted by 1)
    - return_threshold: negative z-score threshold for extreme down moves (e.g., -1.5)
    - volume_threshold: absolute volume z-score threshold (e.g., 1.0)
    - require_high_volume: if True, require |volume_z| > volume_threshold; else ignore volume filter

    Returns:
    - DataFrame with columns: date, symbol, close, return/volume changes, z-scores, signal, position
    """
    df = _ensure_dataframe(data_source)

    # Compute features
    df = _calculate_period_changes(df, period)
    df = _calculate_zscores(df, period, zscore_lookback)

    rzs = f'return_zscore_{period}d'
    vzs = f'volume_zscore_{period}d'

    # Initialize outputs
    df['signal'] = 'NEUTRAL'
    df['position'] = 'FLAT'

    # Long-on-dips condition
    long_cond = df[rzs] < return_threshold
    if require_high_volume:
        long_cond = long_cond & (df[vzs].abs() > volume_threshold)

    df.loc[long_cond, 'signal'] = 'LONG'
    df.loc[long_cond, 'position'] = 'LONG'

    # Select useful columns
    base_cols = ['date', 'symbol', 'close']
    feat_cols = [
        f'return_{period}d',
        f'volume_change_{period}d',
        f'return_zscore_{period}d',
        f'volume_zscore_{period}d',
    ]
    out_cols = base_cols + [c for c in feat_cols if c in df.columns] + ['signal', 'position']

    return df[out_cols]


def get_current_mean_reversion_signals(
    data_source: Union[str, pd.DataFrame],
    period: int = 2,
    zscore_lookback: int = 30,
    return_threshold: float = -1.5,
    volume_threshold: float = 1.0,
    require_high_volume: bool = True,
) -> pd.DataFrame:
    """
    Get the most recent mean reversion signals for each symbol (one row per symbol).
    """
    full_results = calculate_mean_reversion_signals(
        data_source=data_source,
        period=period,
        zscore_lookback=zscore_lookback,
        return_threshold=return_threshold,
        volume_threshold=volume_threshold,
        require_high_volume=require_high_volume,
    )
    latest = full_results.sort_values('date').groupby('symbol').tail(1).reset_index(drop=True)
    return latest


def get_active_mean_reversion_longs(
    data_source: Union[str, pd.DataFrame],
    period: int = 2,
    zscore_lookback: int = 30,
    return_threshold: float = -1.5,
    volume_threshold: float = 1.0,
    require_high_volume: bool = True,
) -> Dict[str, List[str]]:
    """
    Convenience helper: return active LONGs and the latest signals DataFrame.
    """
    current = get_current_mean_reversion_signals(
        data_source=data_source,
        period=period,
        zscore_lookback=zscore_lookback,
        return_threshold=return_threshold,
        volume_threshold=volume_threshold,
        require_high_volume=require_high_volume,
    )
    longs = current[current['position'] == 'LONG']['symbol'].tolist()
    return {'longs': longs, 'signals_df': current}


if __name__ == "__main__":
    # Simple CLI demo (expects CSV path in working directory)
    csv_file = "top10_markets_100d_daily_data.csv"

    print("Calculating Mean Reversion Signals (2d, long-on-dips)")
    print("=" * 80)

    results = calculate_mean_reversion_signals(
        csv_file,
        period=2,
        zscore_lookback=30,
        return_threshold=-1.5,
        volume_threshold=1.0,
        require_high_volume=True,
    )

    print("\nSample results (last 20 rows):")
    print(results.tail(20))

    current = get_current_mean_reversion_signals(csv_file)
    print("\n" + "=" * 80)
    print("Current mean reversion signals (per symbol):")
    print("=" * 80)
    print(current.to_string(index=False))

    active = get_active_mean_reversion_longs(csv_file)
    print(f"\nActive LONGs ({len(active['longs'])}):")
    for sym in active['longs']:
        print(f"  {sym}")
