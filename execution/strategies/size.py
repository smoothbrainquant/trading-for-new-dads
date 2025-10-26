from typing import Dict, List

import pandas as pd

from .utils import calculate_rolling_30d_volatility, calc_weights


def strategy_size(
    historical_data: Dict[str, pd.DataFrame],
    universe_symbols: List[str],
    notional: float,
    top_n: int = 10,
    bottom_n: int = 10,
    limit: int = 100,
) -> Dict[str, float]:
    """Size factor via market capitalization (CoinMarketCap).

    - Fetch current market caps for top `limit` coins from CMC (uses mock if no API key)
    - LONG bottom `bottom_n` (smallest caps)
    - SHORT top `top_n` (largest caps)
    - Intersect with tradable `universe_symbols`
    - Weight by inverse 30d volatility
    """
    try:
        from data.scripts.fetch_coinmarketcap_data import (
            fetch_coinmarketcap_data,
            map_symbols_to_trading_pairs,
        )
    except Exception as e:
        print(f"  Size handler unavailable (CMC import error): {e}")
        return {}

    try:
        df_mc = fetch_coinmarketcap_data(limit=limit)
    except Exception as e:
        print(f"  Error fetching market caps from CMC: {e}")
        return {}

    if df_mc is None or df_mc.empty:
        print("  No market cap data available for size factor.")
        return {}

    # Ensure required columns and map to trading symbols used in our data/exchange
    df_mc = df_mc.dropna(subset=["market_cap", "symbol"]).copy()
    df_mc = map_symbols_to_trading_pairs(df_mc, trading_suffix="/USDC:USDC")

    # Keep only assets that exist in our tradable universe
    df_mc = df_mc[df_mc["trading_symbol"].isin(universe_symbols)]
    if df_mc.empty:
        print("  CMC symbols did not match our tradable universe for size factor.")
        return {}

    # Sort by market cap (desc). Top = large caps; Bottom = small caps
    df_sorted = df_mc.sort_values("market_cap", ascending=False)
    top_large = df_sorted.head(max(0, int(top_n)))
    bottom_small = df_sorted.tail(max(0, int(bottom_n)))

    short_symbols = top_large["trading_symbol"].tolist()  # short large caps
    long_symbols = bottom_small["trading_symbol"].tolist()  # long small caps

    target_positions: Dict[str, float] = {}

    if long_symbols:
        vola_long = calculate_rolling_30d_volatility(historical_data, long_symbols)
        w_long = calc_weights(vola_long) if vola_long else {}
        for symbol, w in w_long.items():
            target_positions[symbol] = target_positions.get(symbol, 0.0) + w * notional
        print(
            f"  Allocated ${notional:,.2f} to SIZE LONGS (bottom {bottom_n} market caps) across {len(w_long)} symbols"
        )
    else:
        print("  No SIZE LONG candidates (small caps).")

    if short_symbols:
        vola_short = calculate_rolling_30d_volatility(historical_data, short_symbols)
        w_short = calc_weights(vola_short) if vola_short else {}
        for symbol, w in w_short.items():
            target_positions[symbol] = target_positions.get(symbol, 0.0) - w * notional
        print(
            f"  Allocated ${notional:,.2f} to SIZE SHORTS (top {top_n} market caps) across {len(w_short)} symbols"
        )
    else:
        print("  No SIZE SHORT candidates (large caps).")

    return target_positions
