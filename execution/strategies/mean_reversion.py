from typing import Dict, List, Optional

import pandas as pd
import numpy as np

from .utils import calculate_rolling_30d_volatility, calc_weights


def _compute_latest_return_and_volume_zscores(
    historical_data: Dict[str, pd.DataFrame],
    lookback_window: int,
    period_days: int = 2,
) -> pd.DataFrame:
    """Compute latest return and volume z-scores per symbol using a rolling window.

    Z-score is computed as (r_t - mean_{t-1}) / std_{t-1} where r_t is the
    N-day percentage return and mean/std are rolling over the past lookback_window
    days, shifted by one day to avoid lookahead bias.
    
    Args:
        historical_data: Dict mapping symbol to DataFrame with OHLCV data
        lookback_window: Window for calculating rolling mean/std (e.g., 30 days)
        period_days: Period for calculating returns (e.g., 2 for 2-day returns)
        
    Returns:
        DataFrame with columns: symbol, return_zscore, volume_zscore
    """
    frames: List[pd.DataFrame] = []
    for symbol, df in historical_data.items():
        if df is None or df.empty or 'close' not in df.columns or 'volume' not in df.columns:
            continue
        s = df[['date', 'close', 'volume']].copy()
        s['symbol'] = symbol
        frames.append(s)

    if not frames:
        return pd.DataFrame(columns=['symbol', 'return_zscore', 'volume_zscore'])

    df_all = pd.concat(frames, ignore_index=True)
    df_all['date'] = pd.to_datetime(df_all['date'])
    df_all = df_all.sort_values(['symbol', 'date']).reset_index(drop=True)

    # Calculate N-day percentage returns (e.g., 2-day returns)
    df_all['return_nd'] = df_all.groupby('symbol')['close'].transform(
        lambda x: x.pct_change(periods=period_days)
    )
    
    # Calculate N-day volume change
    df_all['volume_change_nd'] = df_all.groupby('symbol')['volume'].transform(
        lambda x: x.pct_change(periods=period_days)
    )

    # Rolling mean/std for returns (shifted to avoid look-ahead bias)
    df_all['ret_mean'] = (
        df_all.groupby('symbol')['return_nd']
        .transform(lambda x: x.rolling(lookback_window, min_periods=lookback_window).mean().shift(1))
    )
    df_all['ret_std'] = (
        df_all.groupby('symbol')['return_nd']
        .transform(lambda x: x.rolling(lookback_window, min_periods=lookback_window).std().shift(1))
    )
    
    # Rolling mean/std for volume (shifted to avoid look-ahead bias)
    df_all['vol_mean'] = (
        df_all.groupby('symbol')['volume_change_nd']
        .transform(lambda x: x.rolling(lookback_window, min_periods=lookback_window).mean().shift(1))
    )
    df_all['vol_std'] = (
        df_all.groupby('symbol')['volume_change_nd']
        .transform(lambda x: x.rolling(lookback_window, min_periods=lookback_window).std().shift(1))
    )

    # Calculate z-scores
    df_all['return_zscore'] = (df_all['return_nd'] - df_all['ret_mean']) / df_all['ret_std']
    df_all['volume_zscore'] = (df_all['volume_change_nd'] - df_all['vol_mean']) / df_all['vol_std']
    
    # Replace inf with NaN
    df_all = df_all.replace([np.inf, -np.inf], np.nan)

    # Get latest row for each symbol
    latest = df_all.sort_values('date').groupby('symbol').tail(1)
    latest = latest[['symbol', 'return_zscore', 'volume_zscore']].dropna(subset=['return_zscore'])
    return latest.reset_index(drop=True)


def strategy_mean_reversion(
    historical_data: Dict[str, pd.DataFrame],
    notional: float,
    zscore_threshold: float = 1.5,
    volume_threshold: float = 1.0,
    lookback_window: int = 30,
    period_days: int = 2,
    limit: int = 100,
    long_only: bool = True,
) -> Dict[str, float]:
    """Mean reversion strategy: buy extreme dips with high volume.
    
    Based on backtest findings (see DIRECTIONAL_MEAN_REVERSION_SUMMARY.md):
    - Optimal: 2-day lookback, z-score < -1.5, high volume (z > 1.0)
    - Long-only: Shorting rallies does NOT work (loses money)
    - High volume is critical: 2.1x better returns than low volume
    - Expected: 1.25% next-day return, 3.14 Sharpe, 59.2% win rate
    
    Strategy:
    - Fetch current market caps (limit=100 by default) from CoinMarketCap
    - Compute N-day return z-scores and volume z-scores (no lookahead bias)
    - LONG candidates: return_zscore <= -zscore_threshold AND volume_zscore >= volume_threshold
    - Weight by inverse 30d volatility
    
    Args:
        historical_data: Dict mapping symbol to DataFrame with OHLCV data
        notional: Total notional amount to allocate
        zscore_threshold: Z-score threshold for returns (absolute value, typically 1.5)
        volume_threshold: Z-score threshold for volume (absolute value, typically 1.0)
        lookback_window: Window for calculating z-score statistics (default 30 days)
        period_days: Period for calculating returns (default 2 for 2-day returns)
        limit: Number of symbols to fetch from CoinMarketCap (default 100)
        long_only: If True, only take long positions (default True per backtest)
        
    Returns:
        Dict mapping symbol to target position notional (positive = long)
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

    # Get tradable symbols (all symbols with market cap data)
    tradable_symbols = df_mc['trading_symbol'].tolist()

    # Compute latest z-scores (both return and volume)
    latest_z = _compute_latest_return_and_volume_zscores(
        historical_data, lookback_window, period_days
    )
    if latest_z.empty:
        print("  Unable to compute return/volume z-scores (insufficient data).")
        return {}

    # Create lookup dicts
    return_z_map = dict(zip(latest_z['symbol'], latest_z['return_zscore']))
    volume_z_map = dict(zip(latest_z['symbol'], latest_z['volume_zscore']))

    # Select LONG candidates: extreme negative move + high volume
    # Per backtest: return_zscore < -1.5 AND volume_zscore > 1.0 (absolute value)
    long_candidates = [
        s for s in tradable_symbols
        if (return_z_map.get(s, float('nan')) <= -abs(zscore_threshold) and
            abs(volume_z_map.get(s, float('nan'))) >= volume_threshold)
    ]

    if not long_candidates:
        print(f"  No mean reversion LONG candidates (return z < -{zscore_threshold:.1f}, |volume z| >= {volume_threshold:.1f})")
        return {}

    # Calculate volatility-based weights
    vola_long = calculate_rolling_30d_volatility(historical_data, long_candidates)
    w_long = calc_weights(vola_long) if vola_long else {}
    
    if not w_long:
        print("  Unable to calculate volatility weights for candidates.")
        return {}

    # Allocate notional
    target_positions: Dict[str, float] = {}
    for symbol, w in w_long.items():
        target_positions[symbol] = w * notional

    print(f"  MeanRev LONGS: {len(long_candidates)} selected ({period_days}d return z <= -{zscore_threshold:.1f}, high volume)")
    print(f"    Expected: ~1.25% next-day return, 3.14 Sharpe (per backtest)")

    return target_positions
