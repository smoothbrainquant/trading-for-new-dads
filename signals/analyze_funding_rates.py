#!/usr/bin/env python3
"""
Analyze Historical Funding Rates - Generate Insights
"""
import pandas as pd
import numpy as np
from datetime import datetime


def load_latest_data():
    """Load the most recent funding rates file"""
    import glob

    # Exclude summary files
    files = [f for f in glob.glob("historical_funding_rates_top50_*.csv") if "summary" not in f]
    if not files:
        raise FileNotFoundError("No funding rate data files found")
    latest = sorted(files)[-1]
    print(f"Loading: {latest}\n")
    return pd.read_csv(latest)


def analyze_funding_rates(df):
    """Perform comprehensive analysis"""

    print("=" * 80)
    print("FUNDING RATE ANALYSIS")
    print("=" * 80)

    # Basic statistics
    print(f"\nTotal Records: {len(df):,}")
    print(f"Unique Coins: {df['coin_symbol'].nunique()}")
    print(f"Date Range: {df['date'].min()} to {df['date'].max()}")
    print(f"Average Funding Rate: {df['funding_rate_pct'].mean():.4f}%")
    print(f"Median Funding Rate: {df['funding_rate_pct'].median():.4f}%")

    # Funding rate distribution
    print("\n" + "=" * 80)
    print("FUNDING RATE DISTRIBUTION")
    print("=" * 80)

    percentiles = df["funding_rate_pct"].quantile([0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
    print("\nPercentiles:")
    print(f"  1st:  {percentiles[0.01]:>8.4f}%")
    print(f"  5th:  {percentiles[0.05]:>8.4f}%")
    print(f" 25th:  {percentiles[0.25]:>8.4f}%")
    print(f" 50th:  {percentiles[0.50]:>8.4f}%")
    print(f" 75th:  {percentiles[0.75]:>8.4f}%")
    print(f" 95th:  {percentiles[0.95]:>8.4f}%")
    print(f" 99th:  {percentiles[0.99]:>8.4f}%")

    # Extreme funding rates
    print("\n" + "=" * 80)
    print("EXTREME FUNDING RATES")
    print("=" * 80)

    print("\nTop 10 Highest Funding Rates:")
    top_10 = df.nlargest(10, "funding_rate_pct")[
        ["date", "coin_name", "coin_symbol", "funding_rate_pct"]
    ]
    print(top_10.to_string(index=False))

    print("\nTop 10 Lowest (Most Negative) Funding Rates:")
    bottom_10 = df.nsmallest(10, "funding_rate_pct")[
        ["date", "coin_name", "coin_symbol", "funding_rate_pct"]
    ]
    print(bottom_10.to_string(index=False))

    # Coin-level analysis
    print("\n" + "=" * 80)
    print("TOP 10 COINS BY MARKET CAP - FUNDING RATE SUMMARY")
    print("=" * 80)

    top_10_coins = (
        df[df["rank"] <= 10]
        .groupby(["rank", "coin_name", "coin_symbol"])
        .agg({"funding_rate_pct": ["mean", "std", "min", "max", "count"]})
        .round(4)
    )

    top_10_coins.columns = ["Avg FR %", "Std %", "Min %", "Max %", "Days"]
    top_10_coins = top_10_coins.reset_index()
    print(top_10_coins.to_string(index=False))

    # Time-based analysis
    print("\n" + "=" * 80)
    print("FUNDING RATE TRENDS BY WEEK")
    print("=" * 80)

    df["week"] = pd.to_datetime(df["date"]).dt.to_period("W")
    weekly = df.groupby("week")["funding_rate_pct"].agg(["mean", "std", "min", "max"]).round(4)
    print(weekly.to_string())

    # Correlation analysis
    print("\n" + "=" * 80)
    print("COINS WITH CONSISTENTLY POSITIVE FUNDING RATES")
    print("=" * 80)

    positive_pct = (
        df[df["funding_rate_pct"] > 0].groupby("coin_symbol").size()
        / df.groupby("coin_symbol").size()
        * 100
    )
    positive_pct = positive_pct.sort_values(ascending=False)

    print("\nTop 10 (Most Often Positive):")
    for symbol, pct in positive_pct.head(10).items():
        coin_name = df[df["coin_symbol"] == symbol]["coin_name"].iloc[0]
        print(f"  {symbol:<10} ({coin_name:<30}): {pct:>6.2f}%")

    print("\nBottom 10 (Most Often Negative):")
    for symbol, pct in positive_pct.tail(10).items():
        coin_name = df[df["coin_symbol"] == symbol]["coin_name"].iloc[0]
        print(f"  {symbol:<10} ({coin_name:<30}): {pct:>6.2f}%")

    # Volatility ranking
    print("\n" + "=" * 80)
    print("FUNDING RATE VOLATILITY RANKING")
    print("=" * 80)

    volatility = (
        df.groupby(["coin_name", "coin_symbol"])["funding_rate_pct"]
        .std()
        .sort_values(ascending=False)
    )

    print("\nTop 10 Most Volatile:")
    for idx, (name, vol) in enumerate(volatility.head(10).items(), 1):
        coin_name, symbol = name
        print(f"  {idx:>2}. {symbol:<10} ({coin_name:<30}): {vol:>8.4f}%")

    print("\nTop 10 Most Stable:")
    for idx, (name, vol) in enumerate(volatility.tail(10).items(), 1):
        coin_name, symbol = name
        print(f"  {idx:>2}. {symbol:<10} ({coin_name:<30}): {vol:>8.4f}%")

    # Trading signals
    print("\n" + "=" * 80)
    print("POTENTIAL TRADING SIGNALS (Last 7 Days)")
    print("=" * 80)

    df["date_dt"] = pd.to_datetime(df["date"])
    last_7_days = df[df["date_dt"] >= df["date_dt"].max() - pd.Timedelta(days=7)]

    # High positive funding (potential short opportunity)
    high_funding = (
        last_7_days[last_7_days["funding_rate_pct"] > 1.0]
        .groupby("coin_symbol")
        .agg({"funding_rate_pct": "mean", "coin_name": "first"})
        .sort_values("funding_rate_pct", ascending=False)
    )

    if not high_funding.empty:
        print("\nHigh Positive Funding (Potential Short Setup):")
        for symbol, row in high_funding.head(5).iterrows():
            print(f"  {symbol:<10} ({row['coin_name']:<30}): {row['funding_rate_pct']:>6.3f}%")

    # High negative funding (potential long opportunity)
    low_funding = (
        last_7_days[last_7_days["funding_rate_pct"] < -0.5]
        .groupby("coin_symbol")
        .agg({"funding_rate_pct": "mean", "coin_name": "first"})
        .sort_values("funding_rate_pct")
    )

    if not low_funding.empty:
        print("\nHigh Negative Funding (Potential Long Setup):")
        for symbol, row in low_funding.head(5).iterrows():
            print(f"  {symbol:<10} ({row['coin_name']:<30}): {row['funding_rate_pct']:>6.3f}%")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


def main():
    try:
        df = load_latest_data()
        analyze_funding_rates(df)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please run fetch_historical_funding_rates_top50_improved.py first")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
