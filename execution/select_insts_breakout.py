"""
Instrument Selection Based on Breakout Signals
Selects instruments based on 50d high/low breakout signals with 70d exit levels.
"""

import pandas as pd
from calc_breakout_signals import get_current_signals, get_active_signals


def select_instruments_by_breakout_signals(data_source):
    """
    Select instruments based on breakout signals.

    Returns instruments that have active LONG or SHORT positions based on:
    - LONG: Close above 50-day high
    - SHORT: Close below 50-day low
    - EXIT LONG: Close below 70-day low
    - EXIT SHORT: Close above 70-day high

    Parameters:
    -----------
    data_source : str or pd.DataFrame
        Either a path to a CSV file or a pandas DataFrame
        Expected columns: date, symbol, open, high, low, close, volume

    Returns:
    --------
    dict with keys:
        'longs': DataFrame of symbols with LONG positions
        'shorts': DataFrame of symbols with SHORT positions
        'all_signals': DataFrame with current signals for all symbols
    """
    # Get current signals for all instruments
    current_signals = get_current_signals(data_source)

    # Filter for LONG positions
    longs_df = current_signals[current_signals["position"] == "LONG"].copy()
    longs_df = longs_df.sort_values("symbol").reset_index(drop=True)

    # Filter for SHORT positions
    shorts_df = current_signals[current_signals["position"] == "SHORT"].copy()
    shorts_df = shorts_df.sort_values("symbol").reset_index(drop=True)

    return {"longs": longs_df, "shorts": shorts_df, "all_signals": current_signals}


def get_target_positions_from_signals(data_source):
    """
    Get target positions (with direction) based on breakout signals.

    Returns a dictionary mapping symbols to their target direction:
    - 1 for LONG positions
    - -1 for SHORT positions
    - 0 for FLAT/no position

    Parameters:
    -----------
    data_source : str or pd.DataFrame
        Either a path to a CSV file or a pandas DataFrame

    Returns:
    --------
    dict: Dictionary mapping symbols to target direction (1=long, -1=short, 0=flat)
    """
    signals = get_current_signals(data_source)

    target_positions = {}

    for _, row in signals.iterrows():
        symbol = row["symbol"]
        position = row["position"]

        if position == "LONG":
            target_positions[symbol] = 1
        elif position == "SHORT":
            target_positions[symbol] = -1
        else:
            target_positions[symbol] = 0

    return target_positions


if __name__ == "__main__":
    # Default data source
    csv_file = "top10_markets_100d_daily_data.csv"

    print("Selecting instruments based on breakout signals")
    print("=" * 80)
    print("Signal Rules:")
    print("  LONG: Close above 50-day high")
    print("  EXIT LONG: Close below 70-day low")
    print("  SHORT: Close below 50-day low")
    print("  EXIT SHORT: Close above 70-day high")
    print("=" * 80)

    # Get instruments with breakout signals
    selected = select_instruments_by_breakout_signals(csv_file)

    print(f"\n\nLONG positions ({len(selected['longs'])}):")
    print("-" * 80)
    if not selected["longs"].empty:
        print(
            selected["longs"][
                ["symbol", "close", "rolling_50d_high", "rolling_70d_low", "position"]
            ].to_string(index=False)
        )
    else:
        print("No LONG positions")

    print(f"\n\nSHORT positions ({len(selected['shorts'])}):")
    print("-" * 80)
    if not selected["shorts"].empty:
        print(
            selected["shorts"][
                ["symbol", "close", "rolling_50d_low", "rolling_70d_high", "position"]
            ].to_string(index=False)
        )
    else:
        print("No SHORT positions")

    print("\n\nTarget positions:")
    print("-" * 80)
    target_positions = get_target_positions_from_signals(csv_file)
    for symbol, direction in target_positions.items():
        if direction != 0:
            direction_str = "LONG" if direction == 1 else "SHORT"
            print(f"  {symbol}: {direction_str}")

    # Save results to CSV
    longs_output = "selected_longs_breakout.csv"
    shorts_output = "selected_shorts_breakout.csv"

    if not selected["longs"].empty:
        selected["longs"].to_csv(longs_output, index=False)
        print(f"\n\nLONG positions saved to: {longs_output}")

    if not selected["shorts"].empty:
        selected["shorts"].to_csv(shorts_output, index=False)
        print(f"SHORT positions saved to: {shorts_output}")
