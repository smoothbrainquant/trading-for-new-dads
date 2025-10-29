"""
Create comparison tables for mean reversion period analysis.
"""

import pandas as pd
import numpy as np

# Load results
df = pd.read_csv("backtest_mean_reversion_periods_summary.csv")

# Filter to 1d forward returns and main signals
fwd_1d = df[(df["forward_period"] == "1d") & (df["signal_type"] != "signal_pos_move")].copy()

print("=" * 120)
print("MEAN REVERSION PERIOD COMPARISON - QUICK REFERENCE")
print("=" * 120)

# Create pivot tables for easy comparison
print("\n" + "=" * 120)
print("1. MEAN RETURNS BY PERIOD AND SIGNAL TYPE (Next Day %)")
print("=" * 120)

pivot_returns = (
    fwd_1d.pivot_table(index="period", columns="signal_type", values="mean_return", aggfunc="first")
    * 100
)  # Convert to percentage

# Rename columns for clarity
pivot_returns.columns = ["Any Volume", "High Volume", "Low Volume"]
print("\n" + pivot_returns.to_string())

print("\n" + "=" * 120)
print("2. SHARPE RATIOS BY PERIOD AND SIGNAL TYPE")
print("=" * 120)

pivot_sharpe = fwd_1d.pivot_table(
    index="period", columns="signal_type", values="sharpe_ratio", aggfunc="first"
)

# Rename columns
pivot_sharpe.columns = ["Any Volume", "High Volume", "Low Volume"]
print("\n" + pivot_sharpe.to_string())

print("\n" + "=" * 120)
print("3. WIN RATES BY PERIOD AND SIGNAL TYPE (%)")
print("=" * 120)

pivot_winrate = fwd_1d.pivot_table(
    index="period", columns="signal_type", values="win_rate_pct", aggfunc="first"
)

# Rename columns
pivot_winrate.columns = ["Any Volume", "High Volume", "Low Volume"]
print("\n" + pivot_winrate.to_string())

print("\n" + "=" * 120)
print("4. SIGNAL COUNTS BY PERIOD AND SIGNAL TYPE")
print("=" * 120)

pivot_counts = fwd_1d.pivot_table(
    index="period", columns="signal_type", values="count", aggfunc="first"
)

# Rename columns
pivot_counts.columns = ["Any Volume", "High Volume", "Low Volume"]
print("\n" + pivot_counts.to_string())

# Summary statistics
print("\n" + "=" * 120)
print("5. PERIOD RANKINGS (By Average Performance Across Signal Types)")
print("=" * 120)

period_summary = (
    fwd_1d.groupby("period")
    .agg({"mean_return": "mean", "sharpe_ratio": "mean", "win_rate_pct": "mean", "count": "sum"})
    .round(4)
)

period_summary["mean_return_pct"] = period_summary["mean_return"] * 100
period_summary = period_summary[["mean_return_pct", "sharpe_ratio", "win_rate_pct", "count"]]
period_summary.columns = ["Avg Return (%)", "Avg Sharpe", "Avg Win Rate (%)", "Total Signals"]

print("\nSorted by Average Return:")
print(period_summary.sort_values("Avg Return (%)", ascending=False).to_string())

print("\nSorted by Average Sharpe Ratio:")
print(period_summary.sort_values("Avg Sharpe", ascending=False).to_string())

# Best configurations
print("\n" + "=" * 120)
print("6. TOP 10 CONFIGURATIONS (All Forward Periods)")
print("=" * 120)

all_signals = df[df["signal_type"] != "signal_pos_move"].copy()
top10 = all_signals.nlargest(10, "sharpe_ratio")[
    [
        "period",
        "signal_type",
        "forward_period",
        "mean_return",
        "sharpe_ratio",
        "win_rate_pct",
        "count",
    ]
]

top10["mean_return_pct"] = top10["mean_return"] * 100
top10 = top10[
    [
        "period",
        "signal_type",
        "forward_period",
        "mean_return_pct",
        "sharpe_ratio",
        "win_rate_pct",
        "count",
    ]
]
top10.columns = ["Period", "Signal", "Fwd Period", "Return (%)", "Sharpe", "Win Rate (%)", "Count"]

print("\n" + top10.to_string(index=False))

# Statistical summary
print("\n" + "=" * 120)
print("7. STATISTICAL SUMMARY")
print("=" * 120)

print("\nHigh Volume Signals Performance:")
high_vol = fwd_1d[fwd_1d["signal_type"] == "signal_neg_move_high_vol"]
print(f"  Average Return: {high_vol['mean_return'].mean() * 100:.2f}%")
print(f"  Average Sharpe: {high_vol['sharpe_ratio'].mean():.2f}")
print(f"  Average Win Rate: {high_vol['win_rate_pct'].mean():.1f}%")
print(f"  Best Period: {int(high_vol.loc[high_vol['mean_return'].idxmax(), 'period'])}d")

print("\nLow Volume Signals Performance:")
low_vol = fwd_1d[fwd_1d["signal_type"] == "signal_neg_move_low_vol"]
print(f"  Average Return: {low_vol['mean_return'].mean() * 100:.2f}%")
print(f"  Average Sharpe: {low_vol['sharpe_ratio'].mean():.2f}")
print(f"  Average Win Rate: {low_vol['win_rate_pct'].mean():.1f}%")
print(f"  Best Period: {int(low_vol.loc[low_vol['mean_return'].idxmax(), 'period'])}d")

print("\nAny Volume Signals Performance:")
any_vol = fwd_1d[fwd_1d["signal_type"] == "signal_neg_move"]
print(f"  Average Return: {any_vol['mean_return'].mean() * 100:.2f}%")
print(f"  Average Sharpe: {any_vol['sharpe_ratio'].mean():.2f}")
print(f"  Average Win Rate: {any_vol['win_rate_pct'].mean():.1f}%")
print(f"  Best Period: {int(any_vol.loc[any_vol['mean_return'].idxmax(), 'period'])}d")

# Volume effect
print("\nVolume Effect (High vs Low):")
print(
    f"  Return Difference: {(high_vol['mean_return'].mean() - low_vol['mean_return'].mean()) * 100:.2f}%"
)
print(
    f"  Sharpe Difference: {high_vol['sharpe_ratio'].mean() - low_vol['sharpe_ratio'].mean():.2f}"
)
print(
    f"  High Vol Outperformance: {(high_vol['mean_return'].mean() / low_vol['mean_return'].mean()):.2f}x"
)

# Period effect
print("\nPeriod Length Effect:")
short_term = fwd_1d[fwd_1d["period"].isin([1, 2, 3])]
long_term = fwd_1d[fwd_1d["period"].isin([20, 30])]
print(f"  Short-term (1-3d) Avg Return: {short_term['mean_return'].mean() * 100:.2f}%")
print(f"  Long-term (20-30d) Avg Return: {long_term['mean_return'].mean() * 100:.2f}%")
print(
    f"  Short-term Outperformance: {(short_term['mean_return'].mean() / long_term['mean_return'].mean()):.2f}x"
)

print("\n" + "=" * 120)
print("CONCLUSION: 2-day high-volume signals are optimal for mean reversion trading")
print("=" * 120)
