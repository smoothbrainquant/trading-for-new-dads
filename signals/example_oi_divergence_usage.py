#!/usr/bin/env python3
"""
Example Usage: OI Divergence Signals

This script demonstrates how to use the OI divergence signal generator
for both analysis and trading execution.
"""

import sys

sys.path.insert(0, "/workspace")

from signals.generate_oi_divergence_signals import (
    get_current_signals,
    get_active_positions,
    load_price_data,
    load_oi_data,
    generate_oi_divergence_signals,
)


def example_1_get_current_signals():
    """Example 1: Get current trading signals"""
    print("=" * 80)
    print("EXAMPLE 1: Get Current Signals")
    print("=" * 80)

    # Load data
    print("\nLoading data...")
    price_df = load_price_data("data/raw/combined_coinbase_coinmarketcap_daily.csv")
    oi_df = load_oi_data(
        "data/raw/historical_open_interest_all_perps_since2020_20251026_115907.csv"
    )

    # Get current signals (divergence mode)
    signals = get_current_signals(
        price_data=price_df, oi_data=oi_df, mode="divergence", lookback=30, top_n=5, bottom_n=5
    )

    if not signals.empty:
        print(f"\nCurrent signals as of {signals['date'].iloc[0].date()}:")
        print("\nTop 5 LONG signals:")
        longs = signals[signals["position_side"] == "LONG"].sort_values("rank")
        print(longs[["rank", "symbol", "score_value", "z_ret", "z_doi"]].to_string(index=False))

        print("\nTop 5 SHORT signals:")
        shorts = signals[signals["position_side"] == "SHORT"].sort_values("rank", ascending=False)
        print(shorts[["rank", "symbol", "score_value", "z_ret", "z_doi"]].to_string(index=False))
    else:
        print("No signals available!")


def example_2_get_active_positions():
    """Example 2: Get active positions for execution"""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 2: Get Active Positions for Trading")
    print("=" * 80)

    # Load data
    price_df = load_price_data("data/raw/combined_coinbase_coinmarketcap_daily.csv")
    oi_df = load_oi_data(
        "data/raw/historical_open_interest_all_perps_since2020_20251026_115907.csv"
    )

    # Get active positions
    positions = get_active_positions(
        price_data=price_df, oi_data=oi_df, mode="divergence", lookback=30, top_n=10, bottom_n=10
    )

    print(f"\nMode: {positions['mode'].upper()}")
    print(f"Date: {positions['date']}")
    print(f"\nLONG positions ({len(positions['longs'])}):")
    for i, symbol in enumerate(positions["longs"], 1):
        print(f"  {i:2d}. {symbol}")

    print(f"\nSHORT positions ({len(positions['shorts'])}):")
    for i, symbol in enumerate(positions["shorts"], 1):
        print(f"  {i:2d}. {symbol}")


def example_3_compare_modes():
    """Example 3: Compare divergence vs trend mode"""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 3: Compare Divergence vs Trend Mode")
    print("=" * 80)

    # Load data
    price_df = load_price_data("data/raw/combined_coinbase_coinmarketcap_daily.csv")
    oi_df = load_oi_data(
        "data/raw/historical_open_interest_all_perps_since2020_20251026_115907.csv"
    )

    # Get divergence signals
    div_pos = get_active_positions(
        price_data=price_df, oi_data=oi_df, mode="divergence", top_n=10, bottom_n=10
    )

    # Get trend signals
    trend_pos = get_active_positions(
        price_data=price_df, oi_data=oi_df, mode="trend", top_n=10, bottom_n=10
    )

    print("\nDIVERGENCE MODE (Contrarian):")
    print(f"  LONG:  {', '.join(div_pos['longs'][:5])}...")
    print(f"  SHORT: {', '.join(div_pos['shorts'][:5])}...")

    print("\nTREND MODE (Momentum):")
    print(f"  LONG:  {', '.join(trend_pos['longs'][:5])}...")
    print(f"  SHORT: {', '.join(trend_pos['shorts'][:5])}...")

    # Find overlaps
    div_long_set = set(div_pos["longs"])
    trend_long_set = set(trend_pos["longs"])

    print("\n📊 Signal Comparison:")
    print(
        f"  Divergence longs that are Trend shorts: {div_long_set.intersection(set(trend_pos['shorts']))}"
    )
    print(
        f"  Divergence shorts that are Trend longs: {set(div_pos['shorts']).intersection(trend_long_set)}"
    )
    print("\n  → This is expected! Divergence is inverse of Trend mode.")


def example_4_historical_analysis():
    """Example 4: Analyze historical signal performance"""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 4: Historical Signal Analysis")
    print("=" * 80)

    import pandas as pd

    # Load data
    price_df = load_price_data("data/raw/combined_coinbase_coinmarketcap_daily.csv")
    oi_df = load_oi_data(
        "data/raw/historical_open_interest_all_perps_since2020_20251026_115907.csv"
    )

    # Generate last 90 days of signals
    print("\nGenerating signals for analysis...")
    all_signals = generate_oi_divergence_signals(
        price_data=price_df, oi_data=oi_df, mode="divergence", lookback=30, top_n=10, bottom_n=10
    )

    if all_signals.empty:
        print("No historical signals available!")
        return

    # Filter last 90 days
    latest_date = all_signals["date"].max()
    ninety_days_ago = latest_date - pd.Timedelta(days=90)
    recent = all_signals[all_signals["date"] >= ninety_days_ago]

    print(f"\nAnalyzing signals from {ninety_days_ago.date()} to {latest_date.date()}:")
    print(f"  Total signal records: {len(recent):,}")
    print(f"  Unique trading days: {recent['date'].nunique()}")
    print(f"  Unique symbols traded: {recent['symbol'].nunique()}")

    # Count by position
    long_count = (recent["position_side"] == "LONG").sum()
    short_count = (recent["position_side"] == "SHORT").sum()

    print(f"\n  LONG signals:  {long_count:,} ({long_count/len(recent)*100:.1f}%)")
    print(f"  SHORT signals: {short_count:,} ({short_count/len(recent)*100:.1f}%)")

    # Most frequently signaled symbols
    print("\n📈 Most frequently signaled (LONG):")
    long_freq = recent[recent["position_side"] == "LONG"]["symbol"].value_counts().head(5)
    for symbol, count in long_freq.items():
        print(f"  {symbol}: {count} days")

    print("\n📉 Most frequently signaled (SHORT):")
    short_freq = recent[recent["position_side"] == "SHORT"]["symbol"].value_counts().head(5)
    for symbol, count in short_freq.items():
        print(f"  {symbol}: {count} days")


def example_5_for_trading_bot():
    """Example 5: Integration pattern for trading bot"""
    print("\n\n" + "=" * 80)
    print("EXAMPLE 5: Trading Bot Integration Pattern")
    print("=" * 80)

    # This is a template for how you'd use this in a trading bot
    print("\nPseudo-code for trading bot integration:\n")

    code = """
    # In your main trading loop:
    
    from signals.generate_oi_divergence_signals import get_active_positions, load_price_data, load_oi_data
    
    # Initialize
    price_df = load_price_data('data/raw/combined_coinbase_coinmarketcap_daily.csv')
    oi_df = load_oi_data('data/raw/historical_open_interest_all_perps_since2020_*.csv')
    
    # Get current positions
    positions = get_active_positions(
        price_data=price_df,
        oi_data=oi_df,
        mode='divergence',
        top_n=10,
        bottom_n=10
    )
    
    # Calculate position sizes (risk parity or equal weight)
    notional_per_side = total_capital * 0.5
    long_size = notional_per_side / len(positions['longs'])
    short_size = notional_per_side / len(positions['shorts'])
    
    # Execute longs
    for symbol in positions['longs']:
        target_position = long_size
        current_position = get_current_position(symbol)
        
        if abs(current_position - target_position) > threshold:
            execute_order(symbol, target_position - current_position)
    
    # Execute shorts
    for symbol in positions['shorts']:
        target_position = -short_size
        current_position = get_current_position(symbol)
        
        if abs(current_position - target_position) > threshold:
            execute_order(symbol, target_position - current_position)
    
    # Close positions not in current signal
    all_target_symbols = set(positions['longs'] + positions['shorts'])
    for symbol in get_all_open_positions():
        if symbol not in all_target_symbols:
            close_position(symbol)
    """

    print(code)


if __name__ == "__main__":
    # Run all examples
    example_1_get_current_signals()
    example_2_get_active_positions()
    example_3_compare_modes()
    example_4_historical_analysis()
    example_5_for_trading_bot()

    print("\n" + "=" * 80)
    print("✅ All examples completed!")
    print("=" * 80)
