#!/usr/bin/env python3
"""
Analyze ADF Regime-Switching Backtest by Long/Short Returns

Breaks down performance by:
- Regime (Strong Up, Moderate Up, Down, Strong Down)
- Strategy (Trend Following, Mean Reversion)
- Direction (Long vs Short positions)
"""

import pandas as pd
import numpy as np
import sys
import os


def load_trades(strategy_name):
    """Load trades for a strategy"""
    filepath = f"backtests/results/adf_{strategy_name}_2021_top100_trades.csv"
    if not os.path.exists(filepath):
        print(f"Warning: {filepath} not found")
        return pd.DataFrame()
    
    df = pd.read_csv(filepath)
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_price_data():
    """Load price data to calculate returns"""
    df = pd.read_csv("data/raw/combined_coinbase_coinmarketcap_daily.csv")
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    
    # Calculate next-day returns (for proper execution simulation)
    df["next_return"] = df.groupby("symbol")["close"].pct_change().shift(-1)
    return df


def load_regime_data():
    """Load regime classification from optimal portfolio"""
    df = pd.read_csv("backtests/results/adf_regime_switching_optimal_portfolio.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df[["date", "regime", "btc_5d_pct_change"]]


def calculate_position_returns(trades_df, prices_df):
    """
    Calculate returns for each position (long/short)
    
    Returns:
        DataFrame with date, symbol, signal, weight, return, pnl
    """
    # Merge trades with price data
    merged = trades_df.merge(
        prices_df[["date", "symbol", "next_return", "close"]],
        on=["date", "symbol"],
        how="left"
    )
    
    # Calculate position return based on direction
    # Long: positive weight, return = next_return * weight
    # Short: negative weight, return = -next_return * abs(weight)
    merged["position_return"] = np.where(
        merged["weight"] > 0,
        merged["next_return"] * merged["weight"],  # Long position
        merged["next_return"] * merged["weight"]   # Short position (weight is negative)
    )
    
    # Categorize direction
    merged["direction"] = np.where(merged["weight"] > 0, "LONG", "SHORT")
    
    return merged


def analyze_regime_direction_performance(
    trend_following_trades, 
    mean_reversion_trades,
    regime_data,
    prices_df
):
    """
    Analyze performance by regime, strategy, and direction
    """
    # Calculate position-level returns for both strategies
    tf_positions = calculate_position_returns(trend_following_trades, prices_df)
    mr_positions = calculate_position_returns(mean_reversion_trades, prices_df)
    
    # Add strategy labels
    tf_positions["strategy"] = "Trend Following"
    mr_positions["strategy"] = "Mean Reversion"
    
    # Combine all positions
    all_positions = pd.concat([tf_positions, mr_positions], ignore_index=True)
    
    # Merge with regime data
    all_positions = all_positions.merge(regime_data, on="date", how="left")
    
    # Filter out positions with missing returns
    all_positions = all_positions[all_positions["position_return"].notna()].copy()
    
    # Aggregate by date, regime, strategy, and direction
    daily_aggregated = (
        all_positions.groupby(["date", "regime", "strategy", "direction"])
        .agg({
            "position_return": "sum",  # Sum all position returns for the day
            "symbol": "count"  # Count number of positions
        })
        .reset_index()
        .rename(columns={"symbol": "num_positions", "position_return": "daily_return"})
    )
    
    # Calculate summary statistics by regime, strategy, and direction
    summary = (
        daily_aggregated.groupby(["regime", "strategy", "direction"])
        .agg({
            "daily_return": ["sum", "mean", "std", "count"],
            "num_positions": "mean"
        })
        .reset_index()
    )
    
    # Flatten column names
    summary.columns = [
        "regime", "strategy", "direction",
        "total_return", "avg_daily_return", "std_daily_return", "num_days",
        "avg_num_positions"
    ]
    
    # Calculate annualized metrics
    summary["annualized_return"] = summary["avg_daily_return"] * 365
    summary["annualized_volatility"] = summary["std_daily_return"] * np.sqrt(365)
    summary["sharpe_ratio"] = np.where(
        summary["annualized_volatility"] > 0,
        summary["annualized_return"] / summary["annualized_volatility"],
        0
    )
    
    # Calculate win rate
    win_rates = (
        daily_aggregated.groupby(["regime", "strategy", "direction"])
        .apply(lambda x: (x["daily_return"] > 0).sum() / len(x))
        .reset_index(name="win_rate")
    )
    
    summary = summary.merge(win_rates, on=["regime", "strategy", "direction"])
    
    return summary, daily_aggregated, all_positions


def print_regime_direction_analysis(summary):
    """Print detailed analysis of regime-direction performance"""
    
    print("\n" + "=" * 100)
    print("ADF REGIME-SWITCHING: LONG/SHORT BREAKDOWN")
    print("=" * 100)
    
    # Overall summary by direction
    print("\n" + "-" * 100)
    print("OVERALL PERFORMANCE BY DIRECTION")
    print("-" * 100)
    
    overall_direction = summary.groupby("direction").agg({
        "total_return": "sum",
        "num_days": "sum",
        "avg_num_positions": "mean"
    }).reset_index()
    
    for _, row in overall_direction.iterrows():
        print(f"\n{row['direction']} Positions:")
        print(f"  Total Return:          {row['total_return']:>10.2%}")
        print(f"  Trading Days:          {row['num_days']:>10.0f}")
        print(f"  Avg Positions/Day:     {row['avg_num_positions']:>10.1f}")
    
    # By regime
    for regime in ["Strong Up", "Moderate Up", "Down", "Strong Down"]:
        regime_data = summary[summary["regime"] == regime]
        if regime_data.empty:
            continue
            
        print("\n" + "=" * 100)
        print(f"REGIME: {regime.upper()}")
        print("=" * 100)
        
        for strategy in ["Trend Following", "Mean Reversion"]:
            strategy_data = regime_data[regime_data["strategy"] == strategy]
            if strategy_data.empty:
                continue
                
            print(f"\n{strategy}:")
            print("-" * 80)
            
            for direction in ["LONG", "SHORT"]:
                dir_data = strategy_data[strategy_data["direction"] == direction]
                if dir_data.empty:
                    continue
                
                row = dir_data.iloc[0]
                print(f"\n  {direction} Positions:")
                print(f"    Total Return:           {row['total_return']:>10.2%}")
                print(f"    Avg Daily Return:       {row['avg_daily_return']:>10.4%}")
                print(f"    Annualized Return:      {row['annualized_return']:>10.2%}")
                print(f"    Annualized Volatility:  {row['annualized_volatility']:>10.2%}")
                print(f"    Sharpe Ratio:           {row['sharpe_ratio']:>10.2f}")
                print(f"    Win Rate:               {row['win_rate']:>10.2%}")
                print(f"    Trading Days:           {row['num_days']:>10.0f}")
                print(f"    Avg Positions/Day:      {row['avg_num_positions']:>10.1f}")


def create_performance_comparison_table(summary):
    """Create comparison table of long vs short performance"""
    
    # Pivot to compare long vs short side by side
    comparison = []
    
    for regime in ["Strong Up", "Moderate Up", "Down", "Strong Down"]:
        for strategy in ["Trend Following", "Mean Reversion"]:
            regime_strat = summary[
                (summary["regime"] == regime) & 
                (summary["strategy"] == strategy)
            ]
            
            if regime_strat.empty:
                continue
            
            long_data = regime_strat[regime_strat["direction"] == "LONG"]
            short_data = regime_strat[regime_strat["direction"] == "SHORT"]
            
            row = {
                "Regime": regime,
                "Strategy": strategy,
                "Long_Return": long_data["annualized_return"].iloc[0] if len(long_data) > 0 else 0,
                "Short_Return": short_data["annualized_return"].iloc[0] if len(short_data) > 0 else 0,
                "Long_Sharpe": long_data["sharpe_ratio"].iloc[0] if len(long_data) > 0 else 0,
                "Short_Sharpe": short_data["sharpe_ratio"].iloc[0] if len(short_data) > 0 else 0,
                "Long_WinRate": long_data["win_rate"].iloc[0] if len(long_data) > 0 else 0,
                "Short_WinRate": short_data["win_rate"].iloc[0] if len(short_data) > 0 else 0,
                "Long_Days": long_data["num_days"].iloc[0] if len(long_data) > 0 else 0,
                "Short_Days": short_data["num_days"].iloc[0] if len(short_data) > 0 else 0,
            }
            
            row["Total_Return"] = row["Long_Return"] + row["Short_Return"]
            comparison.append(row)
    
    return pd.DataFrame(comparison)


def main():
    """Main execution"""
    
    print("=" * 100)
    print("ADF REGIME-SWITCHING: LONG/SHORT ANALYSIS")
    print("=" * 100)
    
    print("\nLoading data...")
    
    # Load data
    tf_trades = load_trades("trend_following")
    mr_trades = load_trades("mean_reversion")
    prices_df = load_price_data()
    regime_data = load_regime_data()
    
    print(f"  Trend Following trades: {len(tf_trades):,}")
    print(f"  Mean Reversion trades:  {len(mr_trades):,}")
    print(f"  Price data points:      {len(prices_df):,}")
    print(f"  Regime days:            {len(regime_data):,}")
    
    # Analyze performance by regime and direction
    print("\nAnalyzing performance by regime, strategy, and direction...")
    summary, daily_agg, all_positions = analyze_regime_direction_performance(
        tf_trades, mr_trades, regime_data, prices_df
    )
    
    # Print detailed analysis
    print_regime_direction_analysis(summary)
    
    # Create comparison table
    comparison_df = create_performance_comparison_table(summary)
    
    print("\n" + "=" * 100)
    print("LONG vs SHORT COMPARISON TABLE")
    print("=" * 100)
    print("\n", comparison_df.to_string(index=False))
    
    # Calculate overall long vs short contribution
    print("\n" + "=" * 100)
    print("OVERALL LONG/SHORT CONTRIBUTION")
    print("=" * 100)
    
    overall_long = summary[summary["direction"] == "LONG"]["total_return"].sum()
    overall_short = summary[summary["direction"] == "SHORT"]["total_return"].sum()
    overall_total = overall_long + overall_short
    
    print(f"\nTotal Returns Contribution:")
    print(f"  LONG Positions:   {overall_long:>10.2%}  ({overall_long/overall_total*100:>5.1f}% of total)")
    print(f"  SHORT Positions:  {overall_short:>10.2%}  ({overall_short/overall_total*100:>5.1f}% of total)")
    print(f"  TOTAL:            {overall_total:>10.2%}")
    
    # Best performing regime-strategy-direction combinations
    print("\n" + "=" * 100)
    print("TOP 10 BEST PERFORMING COMBINATIONS")
    print("=" * 100)
    
    top_performers = summary.nlargest(10, "annualized_return")[
        ["regime", "strategy", "direction", "annualized_return", "sharpe_ratio", "win_rate", "num_days"]
    ]
    print("\n", top_performers.to_string(index=False))
    
    # Worst performing combinations
    print("\n" + "=" * 100)
    print("TOP 10 WORST PERFORMING COMBINATIONS")
    print("=" * 100)
    
    worst_performers = summary.nsmallest(10, "annualized_return")[
        ["regime", "strategy", "direction", "annualized_return", "sharpe_ratio", "win_rate", "num_days"]
    ]
    print("\n", worst_performers.to_string(index=False))
    
    # Save results
    output_dir = "backtests/results"
    
    summary.to_csv(f"{output_dir}/adf_regime_longshort_summary.csv", index=False)
    comparison_df.to_csv(f"{output_dir}/adf_regime_longshort_comparison.csv", index=False)
    daily_agg.to_csv(f"{output_dir}/adf_regime_longshort_daily.csv", index=False)
    
    print("\n" + "=" * 100)
    print("OUTPUT FILES SAVED")
    print("=" * 100)
    print(f"  {output_dir}/adf_regime_longshort_summary.csv")
    print(f"  {output_dir}/adf_regime_longshort_comparison.csv")
    print(f"  {output_dir}/adf_regime_longshort_daily.csv")
    
    print("\n? Analysis complete!")


if __name__ == "__main__":
    main()
