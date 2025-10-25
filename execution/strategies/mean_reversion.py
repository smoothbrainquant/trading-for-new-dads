from typing import Dict

import pandas as pd

from .utils import calculate_rolling_30d_volatility, calc_weights


def strategy_mean_reversion(historical_data: Dict[str, pd.DataFrame], notional: float, quantile: float = 0.2) -> Dict[str, float]:
    latest_returns = []
    for symbol, df in historical_data.items():
        s = df.sort_values('date').copy()
        if 'close' not in s.columns:
            continue
        s['ret'] = s['close'].pct_change()
        last_ret = s['ret'].iloc[-1] if len(s) > 1 else None
        if last_ret is not None and pd.notna(last_ret):
            latest_returns.append((symbol, float(last_ret)))

    if not latest_returns:
        print("  No returns computed for mean_reversion.")
        return {}

    sr = pd.Series({sym: r for sym, r in latest_returns})
    low_thresh = sr.quantile(quantile)
    high_thresh = sr.quantile(1 - quantile)
    long_symbols = sr[sr <= low_thresh].index.tolist()
    short_symbols = sr[sr >= high_thresh].index.tolist()

    target_positions: Dict[str, float] = {}
    if long_symbols:
        vola_long = calculate_rolling_30d_volatility(historical_data, long_symbols)
        w_long = calc_weights(vola_long) if vola_long else {}
        for symbol, w in w_long.items():
            target_positions[symbol] = target_positions.get(symbol, 0.0) + w * notional
        print(f"  Allocated ${notional:,.2f} to mean_reversion LONGS across {len(w_long)} symbols")
    else:
        print("  No mean_reversion LONG candidates.")

    if short_symbols:
        vola_short = calculate_rolling_30d_volatility(historical_data, short_symbols)
        w_short = calc_weights(vola_short) if vola_short else {}
        for symbol, w in w_short.items():
            target_positions[symbol] = target_positions.get(symbol, 0.0) - w * notional
        print(f"  Allocated ${notional:,.2f} to mean_reversion SHORTS across {len(w_short)} symbols")
    else:
        print("  No mean_reversion SHORT candidates.")

    return target_positions
