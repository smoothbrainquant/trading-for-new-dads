from typing import Dict, List, Optional

import pandas as pd

from .utils import calculate_rolling_30d_volatility, calc_weights


def _compute_latest_return_zscores(
    historical_data: Dict[str, pd.DataFrame],
    lookback_window: int,
) -> pd.DataFrame:
    """Compute latest return z-scores per symbol using a rolling window.

    Z-score is computed as (r_t - mean_{t-1}) / std_{t-1} where r_t is today's
    percentage return and mean/std are rolling over the past lookback_window
    days, shifted by one day to avoid lookahead bias.
    """
    frames: List[pd.DataFrame] = []
    for symbol, df in historical_data.items():
        if df is None or df.empty or 'close' not in df.columns:
            continue
        s = df[['date', 'close']].copy()
        s['symbol'] = symbol
        frames.append(s)

    if not frames:
        return pd.DataFrame(columns=['symbol', 'zscore'])

    df_all = pd.concat(frames, ignore_index=True)
    df_all['date'] = pd.to_datetime(df_all['date'])
    df_all = df_all.sort_values(['symbol', 'date']).reset_index(drop=True)

    # Daily percentage returns
    df_all['pct_change'] = df_all.groupby('symbol')['close'].pct_change()

    # Rolling mean/std shifted by one day
    df_all['ret_mean'] = (
        df_all.groupby('symbol')['pct_change']
        .transform(lambda x: x.rolling(lookback_window, min_periods=lookback_window).mean().shift(1))
    )
    df_all['ret_std'] = (
        df_all.groupby('symbol')['pct_change']
        .transform(lambda x: x.rolling(lookback_window, min_periods=lookback_window).std().shift(1))
    )

    # Z-score for the latest row of each symbol
    df_all['zscore'] = (df_all['pct_change'] - df_all['ret_mean']) / df_all['ret_std']

    latest = df_all.sort_values('date').groupby('symbol').tail(1)
    latest = latest[['symbol', 'zscore']].dropna(subset=['zscore'])
    return latest.reset_index(drop=True)


def strategy_mean_reversion(
    historical_data: Dict[str, pd.DataFrame],
    notional: float,
    zscore_threshold: float = 2.0,
    lookback_window: int = 30,
    limit: int = 100,
    large_n: Optional[int] = None,
    small_n: Optional[int] = None,
) -> Dict[str, float]:
    """Mean reversion: long dips in large caps, short rips in small caps.

    - Fetch current market caps (limit=100 by default) from CoinMarketCap
    - Define LARGE group (top by market cap) and SMALL group (bottom by market cap)
    - Compute latest return Z-scores (rolling window with lookahead-safe shift)
    - LONG candidates: LARGE group with zscore <= -zscore_threshold
    - SHORT candidates: SMALL group with zscore >= +zscore_threshold
    - Allocate notional 50/50 to long/short if both sides present; else 100% to the available side
    - Within each side, weight by inverse 30d volatility
    """
    try:
        from data.scripts.fetch_coinmarketcap_data import (
            fetch_coinmarketcap_data,
            map_symbols_to_trading_pairs,
        )
    except Exception as e:
        print(f"  Mean reversion CMC import error: {e}")
        return {}

    # Fetch and map market caps
    try:
        df_mc = fetch_coinmarketcap_data(limit=limit)
    except Exception as e:
        print(f"  Error fetching market caps from CMC: {e}")
        return {}

    if df_mc is None or df_mc.empty:
        print("  No market cap data available for mean reversion.")
        return {}

    df_mc = df_mc.dropna(subset=['market_cap', 'symbol']).copy()
    df_mc = map_symbols_to_trading_pairs(df_mc, trading_suffix='/USDC:USDC')

    tradable = set(historical_data.keys())
    df_mc = df_mc[df_mc['trading_symbol'].isin(tradable)]
    if df_mc.empty:
        print("  CMC symbols did not match our tradable universe.")
        return {}

    # Rank by market cap
    df_sorted = df_mc.sort_values('market_cap', ascending=False).reset_index(drop=True)
    total = len(df_sorted)
    if total == 0:
        print("  No symbols after market cap filtering.")
        return {}

    if large_n is None or small_n is None:
        # Default split: top half as large, bottom half as small
        split = total // 2
        large_symbols = df_sorted.iloc[:split]['trading_symbol'].tolist()
        small_symbols = df_sorted.iloc[split:]['trading_symbol'].tolist()
    else:
        large_symbols = df_sorted.head(max(0, int(large_n)))['trading_symbol'].tolist()
        small_symbols = df_sorted.tail(max(0, int(small_n)))['trading_symbol'].tolist()

    # Compute latest z-scores
    latest_z = _compute_latest_return_zscores(historical_data, lookback_window)
    if latest_z.empty:
        print("  Unable to compute return z-scores (insufficient data).")
        return {}

    z_map = dict(zip(latest_z['symbol'], latest_z['zscore']))

    # Select candidates
    long_candidates = [s for s in large_symbols if z_map.get(s, float('nan')) <= -abs(zscore_threshold)]
    short_candidates = [s for s in small_symbols if z_map.get(s, float('nan')) >= abs(zscore_threshold)]

    # Determine side allocations
    has_long = len(long_candidates) > 0
    has_short = len(short_candidates) > 0
    if not has_long and not has_short:
        print("  No mean reversion candidates at the specified z-score threshold.")
        return {}

    notional_long = notional_short = 0.0
    if has_long and has_short:
        notional_long = notional * 0.5
        notional_short = notional * 0.5
    elif has_long:
        notional_long = notional
    else:
        notional_short = notional

    target_positions: Dict[str, float] = {}

    if has_long:
        vola_long = calculate_rolling_30d_volatility(historical_data, long_candidates)
        w_long = calc_weights(vola_long) if vola_long else {}
        for symbol, w in w_long.items():
            target_positions[symbol] = target_positions.get(symbol, 0.0) + w * notional_long
        print(
            f"  MeanRev LONGS: {len(long_candidates)} selected (large caps dips <= -{zscore_threshold:.1f}σ)"
        )
    else:
        print("  No mean reversion LONG candidates (large caps dips).")

    if has_short:
        vola_short = calculate_rolling_30d_volatility(historical_data, short_candidates)
        w_short = calc_weights(vola_short) if vola_short else {}
        for symbol, w in w_short.items():
            target_positions[symbol] = target_positions.get(symbol, 0.0) - w * notional_short
        print(
            f"  MeanRev SHORTS: {len(short_candidates)} selected (small caps rips >= +{zscore_threshold:.1f}σ)"
        )
    else:
        print("  No mean reversion SHORT candidates (small caps rips).")

    return target_positions
