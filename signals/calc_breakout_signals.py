"""
Breakout Signal Calculation Module
Calculates trend-following signals based on 50d high/low breakouts and 70d exit levels.

Signal Rules:
- LONG: Close above 50-day high → Go long
- EXIT LONG: Close below 70-day low → Exit long
- SHORT: Close below 50-day low → Go short
- EXIT SHORT: Close above 70-day high → Exit short
"""

import pandas as pd
import numpy as np
from datetime import datetime


def calculate_breakout_signals(data_source):
    """
    Calculate breakout signals for each symbol in the dataset.

    This function identifies trend-following signals based on price breakouts:
    - Entry signals use 50-day highs/lows
    - Exit signals use 70-day lows/highs

    Parameters:
    -----------
    data_source : str or pd.DataFrame
        Either a path to a CSV file or a pandas DataFrame
        Expected columns: date, symbol, open, high, low, close, volume

    Returns:
    --------
    pd.DataFrame
        DataFrame with columns:
        - date, symbol, close
        - rolling_50d_high: 50-day rolling high
        - rolling_50d_low: 50-day rolling low
        - rolling_70d_high: 70-day rolling high
        - rolling_70d_low: 70-day rolling low
        - signal: 'LONG', 'SHORT', 'EXIT_LONG', 'EXIT_SHORT', or 'NEUTRAL'
    """
    # Read the data - handle both CSV path and DataFrame
    if isinstance(data_source, str):
        df = pd.read_csv(data_source)
    elif isinstance(data_source, pd.DataFrame):
        df = data_source.copy()
    else:
        raise TypeError("data_source must be either a file path (str) or a pandas DataFrame")

    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"])

    # Sort by symbol and date to ensure proper ordering
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

    # Group by symbol and calculate for each
    results = []

    for symbol, group in df.groupby("symbol"):
        # Calculate rolling highs and lows
        group["rolling_50d_high"] = group["high"].rolling(window=50, min_periods=1).max()
        group["rolling_50d_low"] = group["low"].rolling(window=50, min_periods=1).min()
        group["rolling_70d_high"] = group["high"].rolling(window=70, min_periods=1).max()
        group["rolling_70d_low"] = group["low"].rolling(window=70, min_periods=1).min()

        # Initialize signal column
        group["signal"] = "NEUTRAL"
        group["position"] = "FLAT"  # Track current position state

        # Calculate signals based on close price breakouts
        current_position = "FLAT"

        for idx in range(len(group)):
            close = group.iloc[idx]["close"]
            high_50d = group.iloc[idx]["rolling_50d_high"]
            low_50d = group.iloc[idx]["rolling_50d_low"]
            high_70d = group.iloc[idx]["rolling_70d_high"]
            low_70d = group.iloc[idx]["rolling_70d_low"]

            # Store previous close for comparison
            if idx > 0:
                prev_close = group.iloc[idx - 1]["close"]
                prev_high_50d = group.iloc[idx - 1]["rolling_50d_high"]
                prev_low_50d = group.iloc[idx - 1]["rolling_50d_low"]
                prev_high_70d = group.iloc[idx - 1]["rolling_70d_high"]
                prev_low_70d = group.iloc[idx - 1]["rolling_70d_low"]
            else:
                prev_close = close
                prev_high_50d = high_50d
                prev_low_50d = low_50d
                prev_high_70d = high_70d
                prev_low_70d = low_70d

            # Entry and exit logic based on current position
            if current_position == "FLAT":
                # Check for LONG entry: close crosses above 50d high
                if close > prev_high_50d:
                    group.iloc[idx, group.columns.get_loc("signal")] = "LONG"
                    current_position = "LONG"
                # Check for SHORT entry: close crosses below 50d low
                elif close < prev_low_50d:
                    group.iloc[idx, group.columns.get_loc("signal")] = "SHORT"
                    current_position = "SHORT"
                else:
                    group.iloc[idx, group.columns.get_loc("signal")] = "NEUTRAL"

            elif current_position == "LONG":
                # Check for LONG exit: close crosses below 70d low
                if close < prev_low_70d:
                    group.iloc[idx, group.columns.get_loc("signal")] = "EXIT_LONG"
                    current_position = "FLAT"
                else:
                    group.iloc[idx, group.columns.get_loc("signal")] = "HOLD_LONG"

            elif current_position == "SHORT":
                # Check for SHORT exit: close crosses above 70d high
                if close > prev_high_70d:
                    group.iloc[idx, group.columns.get_loc("signal")] = "EXIT_SHORT"
                    current_position = "FLAT"
                else:
                    group.iloc[idx, group.columns.get_loc("signal")] = "HOLD_SHORT"

            # Store current position state
            group.iloc[idx, group.columns.get_loc("position")] = current_position

        results.append(group)

    # Combine all symbols
    result_df = pd.concat(results, ignore_index=True)

    # Select relevant columns
    output_df = result_df[
        [
            "date",
            "symbol",
            "close",
            "rolling_50d_high",
            "rolling_50d_low",
            "rolling_70d_high",
            "rolling_70d_low",
            "signal",
            "position",
        ]
    ]

    return output_df


def get_current_signals(data_source):
    """
    Get the most recent breakout signals for each symbol.

    Parameters:
    -----------
    data_source : str or pd.DataFrame
        Either a path to a CSV file or a pandas DataFrame
        Expected columns: date, symbol, open, high, low, close, volume

    Returns:
    --------
    pd.DataFrame
        DataFrame with the latest date's signals for each symbol
    """
    full_results = calculate_breakout_signals(data_source)

    # Get the most recent date for each symbol
    latest_data = full_results.sort_values("date").groupby("symbol").tail(1).reset_index(drop=True)

    return latest_data


def get_active_signals(data_source):
    """
    Get symbols with active LONG or SHORT signals (current position).

    Parameters:
    -----------
    data_source : str or pd.DataFrame
        Either a path to a CSV file or a pandas DataFrame

    Returns:
    --------
    dict with keys:
        'longs': list of symbols with LONG positions
        'shorts': list of symbols with SHORT positions
        'signals_df': DataFrame with current signals for all symbols
    """
    current_signals = get_current_signals(data_source)

    # Filter for active positions
    longs = current_signals[current_signals["position"] == "LONG"]["symbol"].tolist()
    shorts = current_signals[current_signals["position"] == "SHORT"]["symbol"].tolist()

    return {"longs": longs, "shorts": shorts, "signals_df": current_signals}


if __name__ == "__main__":
    # Example usage with CSV file
    csv_file = "top10_markets_100d_daily_data.csv"

    print("Calculating Breakout Signals")
    print("=" * 80)
    print("Signal Rules:")
    print("  LONG: Close above 50-day high")
    print("  EXIT LONG: Close below 70-day low")
    print("  SHORT: Close below 50-day low")
    print("  EXIT SHORT: Close above 70-day high")
    print("=" * 80)

    # Calculate breakout signals for all dates
    print("\nCalculating breakout signals...")
    full_results = calculate_breakout_signals(csv_file)

    # Display sample results
    print("\nSample results (last 20 rows):")
    print(full_results.tail(20))

    # Get current signals for each symbol
    print("\n" + "=" * 80)
    print("Current signals for each symbol:")
    print("=" * 80)
    current_signals = get_current_signals(csv_file)
    print(current_signals.to_string(index=False))

    # Get active signals
    print("\n" + "=" * 80)
    print("Active positions:")
    print("=" * 80)
    active = get_active_signals(csv_file)
    print(f"\nLONG positions ({len(active['longs'])}):")
    for symbol in active["longs"]:
        print(f"  {symbol}")

    print(f"\nSHORT positions ({len(active['shorts'])}):")
    for symbol in active["shorts"]:
        print(f"  {symbol}")

    # Save results to CSV
    output_file = "breakout_signals_results.csv"
    full_results.to_csv(output_file, index=False)
    print(f"\n\nFull results saved to: {output_file}")
