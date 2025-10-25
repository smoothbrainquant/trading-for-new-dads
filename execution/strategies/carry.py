from typing import Dict, List

import pandas as pd

from .utils import calculate_rolling_30d_volatility, calc_weights, get_base_symbol


def strategy_carry(historical_data: Dict[str, pd.DataFrame], universe_symbols: List[str], notional: float, exchange_id: str = "binance") -> Dict[str, float]:
    try:
        from execution.get_carry import fetch_binance_funding_rates
    except Exception as e:
        print(f"  Carry handler unavailable (import error): {e}")
        return {}

    df_rates = fetch_binance_funding_rates(symbols=None, exchange_id=exchange_id)
    if df_rates is None or df_rates.empty:
        print("  No funding rate data available for carry.")
        return {}

    universe_bases = {get_base_symbol(s): s for s in universe_symbols}
    df_rates = df_rates.copy()
    df_rates['base'] = df_rates['symbol'].astype(str).str.split('/').str[0]
    df_rates = df_rates[df_rates['base'].isin(universe_bases.keys())]
    if df_rates.empty:
        print("  No funding symbols matched our universe for carry.")
        return {}

    df_rates = df_rates.dropna(subset=['funding_rate'])
    long_bases = df_rates[df_rates['funding_rate'] < 0]['base'].unique().tolist()
    short_bases = df_rates[df_rates['funding_rate'] > 0]['base'].unique().tolist()

    long_symbols = [universe_bases[b] for b in long_bases if b in universe_bases]
    short_symbols = [universe_bases[b] for b in short_bases if b in universe_bases]

    target_positions: Dict[str, float] = {}

    if long_symbols:
        vola_long = calculate_rolling_30d_volatility(historical_data, long_symbols)
        w_long = calc_weights(vola_long) if vola_long else {}
        for symbol, w in w_long.items():
            target_positions[symbol] = target_positions.get(symbol, 0.0) + w * notional
        print(f"  Allocated ${notional:,.2f} to carry LONGS across {len(w_long)} symbols")
    else:
        print("  No carry LONG candidates (negative funding).")

    if short_symbols:
        vola_short = calculate_rolling_30d_volatility(historical_data, short_symbols)
        w_short = calc_weights(vola_short) if vola_short else {}
        for symbol, w in w_short.items():
            target_positions[symbol] = target_positions.get(symbol, 0.0) - w * notional
        print(f"  Allocated ${notional:,.2f} to carry SHORTS across {len(w_short)} symbols")
    else:
        print("  No carry SHORT candidates (positive funding).")

    return target_positions
