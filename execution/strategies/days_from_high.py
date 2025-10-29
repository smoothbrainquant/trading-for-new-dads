from typing import Dict

import pandas as pd

from .utils import calculate_days_from_200d_high, calculate_rolling_30d_volatility, calc_weights


def strategy_days_from_high(
    historical_data: Dict[str, pd.DataFrame], notional: float, max_days: int = 20
) -> Dict[str, float]:
    days_from_high = calculate_days_from_200d_high(historical_data)
    selected_symbols = [s for s, d in days_from_high.items() if d <= max_days]
    if not selected_symbols:
        print("  No symbols selected for days_from_high.")
        return {}

    volatilities = calculate_rolling_30d_volatility(historical_data, selected_symbols)
    if not volatilities:
        print("  No volatilities computed for days_from_high.")
        return {}

    weights = calc_weights(volatilities)
    if not weights:
        print("  No weights computed for days_from_high.")
        return {}

    target_positions = {symbol: weight * notional for symbol, weight in weights.items()}
    print(
        f"  Allocated ${notional:,.2f} to days_from_high (LONG-only) across {len(target_positions)} symbols"
    )
    return target_positions
