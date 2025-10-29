#!/usr/bin/env python3
"""
Backtest Carry Factor Strategy with Multiple Rebalance Period Comparisons

This script tests the carry factor strategy across different rebalance periods:
1, 2, 3, 5, 7, 10, 30 days.

For each rebalance period, we:
1. Run the full carry factor backtest
2. Collect performance metrics
3. Compare Sharpe ratios, returns, and other metrics across periods
4. Identify the optimal rebalance frequency

The goal is to find the sweet spot that balances:
- Transaction costs (fewer rebalances = lower costs)
- Alpha capture (more frequent rebalancing = better adaptation to funding rate changes)
- Risk management (appropriate frequency for position adjustments)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse
import sys
import os

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'signals'))

# Import from the carry factor backtest script
from backtest_carry_factor import (
    load_price_data,
    load_funding_rates,
    backtest,
    calculate_performance_metrics,
)


def run_rebalance_period_comparison(
    price_data,
    funding_data,
    rebalance_periods,
    top_n=10,
    bottom_n=10,
    volatility_window=30,
    start_date=None,
    end_date=None,
    initial_capital=10000,
    leverage=1.0,
    long_allocation=0.5,
    short_allocation=0.5,
):
    """
    Run backtest for multiple rebalance periods and compare results.

    Args:
        price_data (pd.DataFrame): Historical OHLCV data
        funding_data (pd.DataFrame): Historical funding rates data
        rebalance_periods (list): List of rebalance periods to test (in days)
        top_n (int): Number of highest funding rate coins to short
        bottom_n (int): Number of lowest funding rate coins to long
        volatility_window (int): Window for volatility calculation
        start_date (str): Start date for backtest
        end_date (str): End date for backtest
        initial_capital (float): Initial portfolio capital
        leverage (float): Leverage multiplier
        long_allocation (float): Allocation to long side
        short_allocation (float): Allocation to short side

    Returns:
        dict: Dictionary containing comparison results for all periods
    """
    all_results = []
    all_portfolio_values = {}
    all_trades = {}

    print("\n" + "=" * 80)
    print("TESTING MULTIPLE REBALANCE PERIODS")
    print("=" * 80)

    for rebalance_days in rebalance_periods:
        print(f"\n{'=' * 80}")
        print(f"TESTING REBALANCE PERIOD: {rebalance_days} DAYS")
        print("=" * 80)

        try:
            # Run backtest for this rebalance period
            results = backtest(
                price_data=price_data,
                funding_data=funding_data,
                top_n=top_n,
                bottom_n=bottom_n,
                volatility_window=volatility_window,
                rebalance_days=rebalance_days,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                leverage=leverage,
                long_allocation=long_allocation,
                short_allocation=short_allocation,
            )

            # Extract metrics
            metrics = results["metrics"]
            portfolio_df = results["portfolio_values"]
            trades_df = results["trades"]

            # Store portfolio values and trades for this period
            all_portfolio_values[rebalance_days] = portfolio_df
            all_trades[rebalance_days] = trades_df

            # Calculate number of rebalances (unique trade dates)
            num_rebalances = len(trades_df["date"].unique()) if not trades_df.empty else 0

            # Calculate average positions per rebalance
            avg_positions_per_rebalance = len(trades_df) / num_rebalances if num_rebalances > 0 else 0

            # Compile summary
            summary = {
                "rebalance_days": rebalance_days,
                "total_return": metrics["total_return"],
                "annualized_return": metrics["annualized_return"],
                "annualized_volatility": metrics["annualized_volatility"],
                "sharpe_ratio": metrics["sharpe_ratio"],
                "max_drawdown": metrics["max_drawdown"],
                "win_rate": metrics["win_rate"],
                "num_days": metrics["num_days"],
                "final_value": metrics["final_value"],
                "avg_long_positions": metrics["avg_long_positions"],
                "avg_short_positions": metrics["avg_short_positions"],
                "avg_total_positions": metrics["avg_total_positions"],
                "avg_long_exposure": metrics["avg_long_exposure"],
                "avg_short_exposure": metrics["avg_short_exposure"],
                "avg_net_exposure": metrics["avg_net_exposure"],
                "avg_gross_exposure": metrics["avg_gross_exposure"],
                "num_rebalances": num_rebalances,
                "total_trades": len(trades_df),
                "avg_positions_per_rebalance": avg_positions_per_rebalance,
            }

            # Add funding rate statistics if available
            if "avg_long_funding_rate" in metrics:
                summary["avg_long_funding_rate"] = metrics["avg_long_funding_rate"]
                summary["avg_short_funding_rate"] = metrics["avg_short_funding_rate"]
                summary["total_expected_funding_income"] = metrics["total_expected_funding_income"]

            all_results.append(summary)

            print(f"\n✓ Completed {rebalance_days}d rebalance period")
            print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            print(f"  Annualized Return: {metrics['annualized_return']:.2%}")
            print(f"  Max Drawdown: {metrics['max_drawdown']:.2%}")
            print(f"  Number of Rebalances: {num_rebalances}")

        except Exception as e:
            print(f"\n✗ Error testing {rebalance_days}d rebalance period: {e}")
            import traceback

            traceback.print_exc()
            continue

    return {
        "summary": pd.DataFrame(all_results),
        "portfolio_values": all_portfolio_values,
        "trades": all_trades,
    }


def print_comparison_results(comparison_results):
    """
    Print comparison results in a formatted manner.

    Args:
        comparison_results (dict): Dictionary containing comparison results
    """
    summary_df = comparison_results["summary"]

    if summary_df.empty:
        print("\nNo results to display.")
        return

    print("\n" + "=" * 120)
    print("REBALANCE PERIOD COMPARISON SUMMARY")
    print("=" * 120)

    # Sort by Sharpe ratio (descending)
    summary_df = summary_df.sort_values("sharpe_ratio", ascending=False)

    print("\n" + "=" * 120)
    print("PERFORMANCE METRICS (Sorted by Sharpe Ratio)")
    print("=" * 120)

    # Display key metrics
    display_cols = [
        "rebalance_days",
        "sharpe_ratio",
        "annualized_return",
        "annualized_volatility",
        "max_drawdown",
        "win_rate",
        "total_return",
    ]

    print("\n" + summary_df[display_cols].to_string(index=False))

    print("\n" + "=" * 120)
    print("TRADING ACTIVITY METRICS")
    print("=" * 120)

    activity_cols = [
        "rebalance_days",
        "num_rebalances",
        "total_trades",
        "avg_positions_per_rebalance",
        "num_days",
    ]

    print("\n" + summary_df[activity_cols].to_string(index=False))

    print("\n" + "=" * 120)
    print("EXPOSURE METRICS")
    print("=" * 120)

    exposure_cols = [
        "rebalance_days",
        "avg_long_exposure",
        "avg_short_exposure",
        "avg_net_exposure",
        "avg_gross_exposure",
    ]

    print("\n" + summary_df[exposure_cols].to_string(index=False))

    # Identify best periods by different metrics
    print("\n" + "=" * 120)
    print("BEST REBALANCE PERIODS BY METRIC")
    print("=" * 120)

    metrics_to_check = {
        "Sharpe Ratio": ("sharpe_ratio", False),
        "Annualized Return": ("annualized_return", False),
        "Max Drawdown": ("max_drawdown", True),  # True = lower is better
        "Win Rate": ("win_rate", False),
        "Total Return": ("total_return", False),
    }

    for metric_name, (col_name, ascending) in metrics_to_check.items():
        best = summary_df.sort_values(col_name, ascending=ascending).iloc[0]
        print(f"\n{metric_name}:")
        print(f"  Best period: {best['rebalance_days']:.0f} days")
        print(f"  Value: {best[col_name]:.4f}")
        print(f"  Annualized Return: {best['annualized_return']:.2%}")
        print(f"  Sharpe Ratio: {best['sharpe_ratio']:.2f}")

    # Funding rate analysis if available
    if "avg_long_funding_rate" in summary_df.columns:
        print("\n" + "=" * 120)
        print("FUNDING RATE METRICS")
        print("=" * 120)

        funding_cols = [
            "rebalance_days",
            "avg_long_funding_rate",
            "avg_short_funding_rate",
            "total_expected_funding_income",
        ]

        print("\n" + summary_df[funding_cols].to_string(index=False))

    print("\n" + "=" * 120)


def print_detailed_analysis(comparison_results):
    """
    Print detailed analysis comparing rebalance periods.

    Args:
        comparison_results (dict): Dictionary containing comparison results
    """
    summary_df = comparison_results["summary"]

    print("\n" + "=" * 120)
    print("DETAILED ANALYSIS: REBALANCE FREQUENCY TRADE-OFFS")
    print("=" * 120)

    # Calculate efficiency metrics
    summary_df["return_per_rebalance"] = (
        summary_df["total_return"] / summary_df["num_rebalances"]
    )
    summary_df["sharpe_per_rebalance"] = (
        summary_df["sharpe_ratio"] / summary_df["num_rebalances"]
    )

    print("\nReturn Efficiency (Return per Rebalance):")
    efficiency_df = summary_df[["rebalance_days", "return_per_rebalance", "num_rebalances"]].copy()
    efficiency_df = efficiency_df.sort_values("return_per_rebalance", ascending=False)
    print(efficiency_df.to_string(index=False))

    print("\nRisk-Adjusted Return (Sharpe per Rebalance):")
    sharpe_eff_df = summary_df[["rebalance_days", "sharpe_per_rebalance", "num_rebalances"]].copy()
    sharpe_eff_df = sharpe_eff_df.sort_values("sharpe_per_rebalance", ascending=False)
    print(sharpe_eff_df.to_string(index=False))

    # Rebalance frequency vs performance scatter data
    print("\n" + "=" * 120)
    print("CORRELATION ANALYSIS")
    print("=" * 120)

    correlations = {
        "Rebalance Days vs Sharpe": summary_df["rebalance_days"].corr(summary_df["sharpe_ratio"]),
        "Rebalance Days vs Return": summary_df["rebalance_days"].corr(
            summary_df["annualized_return"]
        ),
        "Rebalance Days vs Volatility": summary_df["rebalance_days"].corr(
            summary_df["annualized_volatility"]
        ),
        "Rebalance Days vs Drawdown": summary_df["rebalance_days"].corr(
            summary_df["max_drawdown"]
        ),
        "Num Rebalances vs Return": summary_df["num_rebalances"].corr(
            summary_df["annualized_return"]
        ),
    }

    for corr_name, corr_value in correlations.items():
        print(f"  {corr_name}: {corr_value:.3f}")

    print("\n" + "=" * 120)


def save_comparison_results(comparison_results, output_prefix="backtest_carry_rebalance_periods"):
    """
    Save comparison results to CSV files.

    Args:
        comparison_results (dict): Dictionary containing comparison results
        output_prefix (str): Prefix for output filenames
    """
    # Save summary comparison
    summary_file = f"{output_prefix}_summary.csv"
    comparison_results["summary"].to_csv(summary_file, index=False)
    print(f"\nSummary comparison saved to: {summary_file}")

    # Save portfolio values for each period
    for period, portfolio_df in comparison_results["portfolio_values"].items():
        portfolio_file = f"{output_prefix}_{period}d_portfolio_values.csv"
        portfolio_df.to_csv(portfolio_file, index=False)
        print(f"Portfolio values ({period}d) saved to: {portfolio_file}")

    # Save trades for each period
    for period, trades_df in comparison_results["trades"].items():
        if not trades_df.empty:
            trades_file = f"{output_prefix}_{period}d_trades.csv"
            trades_df.to_csv(trades_file, index=False)
            print(f"Trades ({period}d) saved to: {trades_file}")


def main():
    """Main execution function for rebalance period comparison."""
    parser = argparse.ArgumentParser(
        description="Backtest Carry Factor Strategy with Multiple Rebalance Period Comparisons",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--price-data",
        type=str,
        default="combined_coinbase_coinmarketcap_daily.csv",
        help="Path to historical OHLCV price data CSV file",
    )
    parser.add_argument(
        "--funding-data",
        type=str,
        default="historical_funding_rates_top100_ALL_HISTORY_20251028_002456.csv",
        help="Path to historical funding rates CSV file",
    )
    parser.add_argument(
        "--rebalance-periods",
        type=str,
        default="1,2,3,5,7,10,30",
        help='Comma-separated list of rebalance periods to test (in days)',
    )
    parser.add_argument(
        "--top-n", type=int, default=10, help="Number of highest funding rate coins to short"
    )
    parser.add_argument(
        "--bottom-n", type=int, default=10, help="Number of lowest funding rate coins to long"
    )
    parser.add_argument(
        "--volatility-window", type=int, default=30, help="Volatility calculation window in days"
    )
    parser.add_argument(
        "--initial-capital", type=float, default=10000, help="Initial portfolio capital in USD"
    )
    parser.add_argument(
        "--leverage", type=float, default=1.0, help="Leverage multiplier (1.0 = no leverage)"
    )
    parser.add_argument(
        "--long-allocation", type=float, default=0.5, help="Allocation to long side (0.5 = 50%)"
    )
    parser.add_argument(
        "--short-allocation", type=float, default=0.5, help="Allocation to short side (0.5 = 50%)"
    )
    parser.add_argument(
        "--start-date", type=str, default=None, help="Start date for backtest (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date", type=str, default=None, help="End date for backtest (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default="backtest_carry_rebalance_periods",
        help="Prefix for output CSV files",
    )

    args = parser.parse_args()

    # Parse rebalance periods
    rebalance_periods = [int(p.strip()) for p in args.rebalance_periods.split(",")]

    print("=" * 120)
    print("CARRY FACTOR BACKTEST - REBALANCE PERIOD COMPARISON")
    print("=" * 120)
    print(f"\nConfiguration:")
    print(f"  Price data file: {args.price_data}")
    print(f"  Funding data file: {args.funding_data}")
    print(f"  Rebalance periods to test: {rebalance_periods}")
    print(f"  Long positions (lowest FR): {args.bottom_n} coins")
    print(f"  Short positions (highest FR): {args.top_n} coins")
    print(f"  Volatility window: {args.volatility_window}d")
    print(f"  Initial capital: ${args.initial_capital:,.2f}")
    print(f"  Leverage: {args.leverage}x")
    print(f"  Long allocation: {args.long_allocation:.1%}")
    print(f"  Short allocation: {args.short_allocation:.1%}")
    print(f"  Start date: {args.start_date or 'First available'}")
    print(f"  End date: {args.end_date or 'Last available'}")
    print("=" * 120)

    # Load price data
    print("\nLoading price data...")
    price_data = load_price_data(args.price_data)
    print(f"Loaded {len(price_data)} rows for {price_data['base_symbol'].nunique()} symbols")
    print(f"Date range: {price_data['date'].min().date()} to {price_data['date'].max().date()}")

    # Load funding rates data
    print("\nLoading funding rates data...")
    funding_data = load_funding_rates(args.funding_data)
    print(f"Loaded {len(funding_data)} rows for {funding_data['coin_symbol'].nunique()} symbols")
    print(f"Date range: {funding_data['date'].min().date()} to {funding_data['date'].max().date()}")

    # Run comparison
    print("\nRunning rebalance period comparison...")
    comparison_results = run_rebalance_period_comparison(
        price_data=price_data,
        funding_data=funding_data,
        rebalance_periods=rebalance_periods,
        top_n=args.top_n,
        bottom_n=args.bottom_n,
        volatility_window=args.volatility_window,
        start_date=args.start_date,
        end_date=args.end_date,
        initial_capital=args.initial_capital,
        leverage=args.leverage,
        long_allocation=args.long_allocation,
        short_allocation=args.short_allocation,
    )

    # Print results
    print_comparison_results(comparison_results)
    print_detailed_analysis(comparison_results)

    # Save results
    save_comparison_results(comparison_results, output_prefix=args.output_prefix)

    print("\n" + "=" * 120)
    print("COMPARISON COMPLETE")
    print("=" * 120)


if __name__ == "__main__":
    main()
