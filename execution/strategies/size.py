from typing import Dict, List

import pandas as pd

from .utils import calculate_rolling_30d_volatility, calc_weights


def strategy_size(historical_data: Dict[str, pd.DataFrame], universe_symbols: List[str], notional: float, top_n: int = 10, bottom_n: int = 10) -> Dict[str, float]:
    try:
        from data.scripts.ccxt_get_markets_by_volume import ccxt_get_markets_by_volume
    except Exception as e:
        print(f"  Size handler unavailable (market data error): {e}")
        return {}

    df_markets = ccxt_get_markets_by_volume()
    if df_markets is None or df_markets.empty:
        print("  No market volume data for size factor.")
        return {}

    df = df_markets.copy()
    df = df[df['symbol'].isin(universe_symbols)]
    if df.empty:
        print("  Market volume data did not match our universe for size factor.")
        return {}

    df = df.sort_values('notional_volume_24h', ascending=False)
    long_symbols = df.head(max(0, int(top_n)))['symbol'].tolist()
    short_symbols = df.tail(max(0, int(bottom_n)))['symbol'].tolist()

    target_positions: Dict[str, float] = {}
    if long_symbols:
        vola_long = calculate_rolling_30d_volatility(historical_data, long_symbols)
        w_long = calc_weights(vola_long) if vola_long else {}
        for symbol, w in w_long.items():
            target_positions[symbol] = target_positions.get(symbol, 0.0) + w * notional
        print(f"  Allocated ${notional:,.2f} to size LONGS across {len(w_long)} symbols")
    else:
        print("  No size LONG candidates.")

    if short_symbols:
        vola_short = calculate_rolling_30d_volatility(historical_data, short_symbols)
        w_short = calc_weights(vola_short) if vola_short else {}
        for symbol, w in w_short.items():
            target_positions[symbol] = target_positions.get(symbol, 0.0) - w * notional
        print(f"  Allocated ${notional:,.2f} to size SHORTS across {len(w_short)} symbols")
    else:
        print("  No size SHORT candidates.")

    return target_positions
