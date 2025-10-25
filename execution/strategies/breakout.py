from typing import Dict

import pandas as pd

from .utils import calculate_breakout_signals_from_data, calculate_rolling_30d_volatility, calc_weights


def strategy_breakout(historical_data: Dict[str, pd.DataFrame], notional: float) -> Dict[str, float]:
    signals = calculate_breakout_signals_from_data(historical_data)
    longs = [s for s, d in signals.items() if d == 1]
    shorts = [s for s, d in signals.items() if d == -1]

    target_positions: Dict[str, float] = {}

    if longs:
        vola_long = calculate_rolling_30d_volatility(historical_data, longs)
        w_long = calc_weights(vola_long) if vola_long else {}
        for symbol, w in w_long.items():
            target_positions[symbol] = target_positions.get(symbol, 0.0) + w * notional
        print(f"  Allocated ${notional:,.2f} to breakout LONGS across {len(w_long)} symbols")
    else:
        print("  No breakout LONG signals.")

    if shorts:
        vola_short = calculate_rolling_30d_volatility(historical_data, shorts)
        w_short = calc_weights(vola_short) if vola_short else {}
        for symbol, w in w_short.items():
            target_positions[symbol] = target_positions.get(symbol, 0.0) - w * notional
        print(f"  Allocated ${notional:,.2f} to breakout SHORTS across {len(w_short)} symbols")
    else:
        print("  No breakout SHORT signals.")

    return target_positions
