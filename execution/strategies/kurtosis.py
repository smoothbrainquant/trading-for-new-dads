"""
Kurtosis Factor Strategy

This strategy trades based on the tail-fatness of return distributions:
- Momentum variant: Long high kurtosis (fat tails/volatile), Short low kurtosis (stable)
- Mean reversion variant: Long low kurtosis (stable), Short high kurtosis (volatile)

Kurtosis measures the "tailedness" of a distribution. High kurtosis indicates
more extreme price movements (fat tails), while low kurtosis indicates more
stable, normal-like returns.
"""

from typing import Dict
import pandas as pd
import numpy as np
from scipy import stats

from .utils import calculate_rolling_30d_volatility, calc_weights


def calculate_kurtosis(
    historical_data: Dict[str, pd.DataFrame], window: int = 30
) -> Dict[str, float]:
    """
    Calculate rolling kurtosis of daily returns for each symbol.

    Args:
        historical_data: Dictionary mapping symbols to their historical DataFrames
        window: Rolling window for kurtosis calculation (default: 30 days)

    Returns:
        Dictionary mapping symbols to their current kurtosis values
    """
    kurtosis_values = {}

    for symbol, df in historical_data.items():
        if df is None or df.empty or len(df) < window + 1:
            continue

        # Calculate daily returns
        df = df.copy().sort_values("timestamp" if "timestamp" in df.columns else "date")
        if "close" in df.columns:
            returns = df["close"].pct_change().dropna()
        else:
            continue

        # Need at least window days of returns
        if len(returns) < window:
            continue

        # Get last window days of returns
        recent_returns = returns.tail(window)

        # Calculate excess kurtosis (Fisher=True: normal distribution = 0)
        try:
            kurt_value = stats.kurtosis(recent_returns.dropna(), fisher=True, nan_policy="omit")
            if not np.isnan(kurt_value) and not np.isinf(kurt_value):
                kurtosis_values[symbol] = kurt_value
        except:
            continue

    return kurtosis_values


def strategy_kurtosis(
    historical_data: Dict[str, pd.DataFrame],
    notional: float,
    strategy: str = "momentum",
    kurtosis_window: int = 30,
    long_percentile: float = 20,
    short_percentile: float = 80,
    max_positions: int = 10,
) -> Dict[str, float]:
    """
    Kurtosis factor strategy for live trading.

    Args:
        historical_data: Dictionary mapping symbols to their historical DataFrames
        notional: Total notional value to allocate
        strategy: Strategy type - 'momentum' or 'mean_reversion' (default: 'momentum')
        kurtosis_window: Window for kurtosis calculation in days (default: 30)
        long_percentile: Percentile threshold for long positions (default: 20)
        short_percentile: Percentile threshold for short positions (default: 80)
        max_positions: Maximum positions per side (default: 10)

    Returns:
        Dictionary mapping symbols to target notional values (positive = long, negative = short)
    """
    print(f"  Strategy: Kurtosis {strategy.title()}")
    print(f"  Kurtosis window: {kurtosis_window}d")
    print(f"  Long percentile: {long_percentile}%")
    print(f"  Short percentile: {short_percentile}%")
    print(f"  Max positions per side: {max_positions}")

    # Calculate kurtosis for all symbols
    print(f"  Calculating kurtosis for {len(historical_data)} symbols...")
    kurtosis_values = calculate_kurtosis(historical_data, window=kurtosis_window)

    if not kurtosis_values:
        print(f"  ⚠️  No kurtosis values calculated (insufficient data)")
        return {}

    print(f"  Calculated kurtosis for {len(kurtosis_values)} symbols")

    # Convert to DataFrame for ranking
    df_kurt = pd.DataFrame(list(kurtosis_values.items()), columns=["symbol", "kurtosis"])
    df_kurt["kurtosis_rank"] = df_kurt["kurtosis"].rank(method="average")
    df_kurt["kurtosis_percentile"] = df_kurt["kurtosis_rank"] / len(df_kurt) * 100

    # Select symbols based on strategy
    if strategy == "momentum":
        # Long: High kurtosis (volatile coins)
        long_symbols = df_kurt[df_kurt["kurtosis_percentile"] >= short_percentile][
            "symbol"
        ].tolist()
        # Short: Low kurtosis (stable coins)
        short_symbols = df_kurt[df_kurt["kurtosis_percentile"] <= long_percentile][
            "symbol"
        ].tolist()
    elif strategy == "mean_reversion":
        # Long: Low kurtosis (stable coins)
        long_symbols = df_kurt[df_kurt["kurtosis_percentile"] <= long_percentile][
            "symbol"
        ].tolist()
        # Short: High kurtosis (volatile coins)
        short_symbols = df_kurt[df_kurt["kurtosis_percentile"] >= short_percentile][
            "symbol"
        ].tolist()
    else:
        print(f"  ⚠️  Unknown strategy: {strategy}")
        return {}

    # Limit number of positions
    if len(long_symbols) > max_positions:
        if strategy == "momentum":
            # Take highest kurtosis for momentum
            long_symbols = (
                df_kurt[df_kurt["symbol"].isin(long_symbols)]
                .nlargest(max_positions, "kurtosis")["symbol"]
                .tolist()
            )
        else:
            # Take lowest kurtosis for mean reversion
            long_symbols = (
                df_kurt[df_kurt["symbol"].isin(long_symbols)]
                .nsmallest(max_positions, "kurtosis")["symbol"]
                .tolist()
            )

    if len(short_symbols) > max_positions:
        if strategy == "momentum":
            # Take lowest kurtosis for momentum shorts
            short_symbols = (
                df_kurt[df_kurt["symbol"].isin(short_symbols)]
                .nsmallest(max_positions, "kurtosis")["symbol"]
                .tolist()
            )
        else:
            # Take highest kurtosis for mean reversion shorts
            short_symbols = (
                df_kurt[df_kurt["symbol"].isin(short_symbols)]
                .nlargest(max_positions, "kurtosis")["symbol"]
                .tolist()
            )

    print(f"  Selected {len(long_symbols)} long positions, {len(short_symbols)} short positions")

    if not long_symbols and not short_symbols:
        print(f"  ⚠️  No positions selected")
        return {}

    # Calculate volatilities for risk parity weighting
    all_selected = long_symbols + short_symbols
    volatilities = calculate_rolling_30d_volatility(historical_data, all_selected)

    if not volatilities:
        print(f"  ⚠️  Could not calculate volatilities for weighting")
        return {}

    # Calculate weights using inverse volatility (risk parity)
    long_vols = {sym: vol for sym, vol in volatilities.items() if sym in long_symbols}
    short_vols = {sym: vol for sym, vol in volatilities.items() if sym in short_symbols}

    long_weights = calc_weights(long_vols) if long_vols else {}
    short_weights = calc_weights(short_vols) if short_vols else {}

    # Allocate capital: 50% long, 50% short
    long_allocation = notional * 0.5
    short_allocation = notional * 0.5

    # Build target positions
    target_positions = {}

    for symbol, weight in long_weights.items():
        target_positions[symbol] = weight * long_allocation

    for symbol, weight in short_weights.items():
        target_positions[symbol] = -1 * weight * short_allocation

    # Print top positions
    if target_positions:
        print(f"\n  Top positions:")
        sorted_positions = sorted(target_positions.items(), key=lambda x: abs(x[1]), reverse=True)
        for i, (symbol, notional_val) in enumerate(sorted_positions[:10], 1):
            side = "LONG" if notional_val > 0 else "SHORT"
            kurt_val = kurtosis_values.get(symbol, 0)
            print(
                f"    {i:2d}. {symbol:20s}: {side:5s} ${abs(notional_val):>10,.2f} (kurtosis: {kurt_val:>6.2f})"
            )

    total_long = sum(v for v in target_positions.values() if v > 0)
    total_short = abs(sum(v for v in target_positions.values() if v < 0))
    print(f"\n  Total long:  ${total_long:,.2f}")
    print(f"  Total short: ${total_short:,.2f}")
    print(f"  Total allocated: ${total_long + total_short:,.2f} / ${notional:,.2f}")

    return target_positions
