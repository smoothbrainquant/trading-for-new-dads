from typing import Dict, List

import pandas as pd

from .utils import calculate_rolling_30d_volatility, calc_weights, get_base_symbol


def strategy_carry(
    historical_data: Dict[str, pd.DataFrame],
    universe_symbols: List[str],
    notional: float,
    exchange_id: str = "binance",
    top_n: int = 10,
    bottom_n: int = 10,
) -> Dict[str, float]:
    try:
        from execution.get_carry import fetch_binance_funding_rates
    except Exception as e:
        print(f"  Carry handler unavailable (import error): {e}")
        return {}

    # Try to fetch funding rates; gracefully fallback if exchange is restricted
    try:
        df_rates = fetch_binance_funding_rates(symbols=None, exchange_id=exchange_id)
    except Exception as e:
        print(f"  Error fetching funding rates from {exchange_id}: {e}")
        # Fallback to binanceus if primary is restricted
        if exchange_id == "binance":
            try:
                print("  Trying fallback exchange_id='binanceus' ...")
                df_rates = fetch_binance_funding_rates(symbols=None, exchange_id="binanceus")
            except Exception as e2:
                print(f"  Carry unavailable from both binance and binanceus: {e2}")
                return {}
        else:
            return {}
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

    # Select bottom N (most negative) for LONG carry and top N (most positive) for SHORT carry
    df_sorted_asc = df_rates.sort_values('funding_rate', ascending=True)
    df_sorted_desc = df_rates.sort_values('funding_rate', ascending=False)

    selected_long_bases = df_sorted_asc.head(max(0, int(bottom_n)))['base'].tolist()
    selected_short_bases = df_sorted_desc.head(max(0, int(top_n)))['base'].tolist()

    long_symbols = [universe_bases[b] for b in selected_long_bases if b in universe_bases]
    short_symbols = [universe_bases[b] for b in selected_short_bases if b in universe_bases]

    target_positions: Dict[str, float] = {}

    if long_symbols:
        vola_long = calculate_rolling_30d_volatility(historical_data, long_symbols)
        w_long = calc_weights(vola_long) if vola_long else {}
        for symbol, w in w_long.items():
            target_positions[symbol] = target_positions.get(symbol, 0.0) + w * notional
        print(f"  Allocated ${notional:,.2f} to carry LONGS across {len(w_long)} symbols (bottom {bottom_n} FR)")
    else:
        print("  No carry LONG candidates (negative funding).")

    if short_symbols:
        vola_short = calculate_rolling_30d_volatility(historical_data, short_symbols)
        w_short = calc_weights(vola_short) if vola_short else {}
        for symbol, w in w_short.items():
            target_positions[symbol] = target_positions.get(symbol, 0.0) - w * notional
        print(f"  Allocated ${notional:,.2f} to carry SHORTS across {len(w_short)} symbols (top {top_n} FR)")
    else:
        print("  No carry SHORT candidates (positive funding).")

    return target_positions
