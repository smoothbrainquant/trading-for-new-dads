"""
Backtest Kurtosis Factor with Different Rebalance Periods

This script runs the kurtosis factor backtest with multiple rebalance periods
and compares the performance metrics across different rebalancing frequencies.

Rebalance periods tested: [1, 2, 3, 5, 7, 10, 30] days
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))
from backtest_kurtosis_factor import load_data, backtest


def run_rebalance_period_comparison(
    price_data,
    rebalance_periods=[1, 2, 3, 5, 7, 10, 30],
    strategy="momentum",
    kurtosis_window=30,
    volatility_window=30,
    long_percentile=20,
    short_percentile=80,
    max_positions=10,
    weighting="risk_parity",
    initial_capital=10000,
    leverage=1.0,
    long_allocation=0.5,
    short_allocation=0.5,
    min_volume=5_000_000,
    min_market_cap=50_000_000,
    start_date=None,
    end_date=None,
):
    """
    Run kurtosis factor backtest with different rebalance periods.

    Args:
        price_data (pd.DataFrame): Historical OHLCV data
        rebalance_periods (list): List of rebalance periods to test (in days)
        strategy (str): Strategy type ('mean_reversion' or 'momentum')
        kurtosis_window (int): Window for kurtosis calculation
        volatility_window (int): Window for volatility calculation
        long_percentile (float): Percentile threshold for long positions
        short_percentile (float): Percentile threshold for short positions
        max_positions (int): Maximum positions per side
        weighting (str): Weighting method ('risk_parity' or 'equal_weight')
        initial_capital (float): Initial portfolio capital
        leverage (float): Leverage multiplier
        long_allocation (float): Allocation to long side
        short_allocation (float): Allocation to short side
        min_volume (float): Minimum volume filter
        min_market_cap (float): Minimum market cap filter
        start_date (str): Start date for backtest
        end_date (str): End date for backtest

    Returns:
        dict: Dictionary containing all results and comparison summary
    """
    print("=" * 80)
    print("KURTOSIS FACTOR - REBALANCE PERIOD COMPARISON")
    print("=" * 80)
    print(f"\nTesting rebalance periods: {rebalance_periods}")
    print(f"Strategy: {strategy}")
    print(f"Kurtosis window: {kurtosis_window}d")
    print(f"Volatility window: {volatility_window}d")
    print("=" * 80)

    all_results = {}
    comparison_metrics = []

    for rebal_days in rebalance_periods:
        print(f"\n{'='*80}")
        print(f"RUNNING BACKTEST: {rebal_days}-DAY REBALANCE PERIOD")
        print(f"{'='*80}")

        # Run backtest for this rebalance period
        results = backtest(
            price_data=price_data,
            strategy=strategy,
            kurtosis_window=kurtosis_window,
            volatility_window=volatility_window,
            rebalance_days=rebal_days,
            long_percentile=long_percentile,
            short_percentile=short_percentile,
            max_positions=max_positions,
            weighting=weighting,
            initial_capital=initial_capital,
            leverage=leverage,
            long_allocation=long_allocation,
            short_allocation=short_allocation,
            min_volume=min_volume,
            min_market_cap=min_market_cap,
            start_date=start_date,
            end_date=end_date,
        )

        # Store results
        all_results[rebal_days] = results

        # Extract key metrics for comparison
        metrics = results["metrics"]
        comparison_metrics.append(
            {
                "rebalance_days": rebal_days,
                "total_return": metrics["total_return"],
                "annualized_return": metrics["annualized_return"],
                "annualized_volatility": metrics["annualized_volatility"],
                "sharpe_ratio": metrics["sharpe_ratio"],
                "max_drawdown": metrics["max_drawdown"],
                "win_rate": metrics["win_rate"],
                "avg_long_positions": metrics["avg_long_positions"],
                "avg_short_positions": metrics["avg_short_positions"],
                "avg_gross_exposure": metrics["avg_gross_exposure"],
                "total_trades": len(results["trades"]),
                "num_days": metrics["num_days"],
            }
        )

        print(f"\n{rebal_days}-day rebalance results:")
        print(f"  Total Return: {metrics['total_return']:.2%}")
        print(f"  Annualized Return: {metrics['annualized_return']:.2%}")
        print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown: {metrics['max_drawdown']:.2%}")

    # Create comparison DataFrame
    comparison_df = pd.DataFrame(comparison_metrics)

    # Find best performers
    best_return = comparison_df.loc[comparison_df["annualized_return"].idxmax()]
    best_sharpe = comparison_df.loc[comparison_df["sharpe_ratio"].idxmax()]
    best_drawdown = comparison_df.loc[comparison_df["max_drawdown"].idxmax()]

    print("\n" + "=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)

    print("\nBest Performers:")
    print(
        f"  Highest Annualized Return: {best_return['rebalance_days']:.0f}-day "
        f"({best_return['annualized_return']:.2%})"
    )
    print(
        f"  Highest Sharpe Ratio: {best_sharpe['rebalance_days']:.0f}-day "
        f"({best_sharpe['sharpe_ratio']:.2f})"
    )
    print(
        f"  Best Max Drawdown: {best_drawdown['rebalance_days']:.0f}-day "
        f"({best_drawdown['max_drawdown']:.2%})"
    )

    print("\nDetailed Comparison:")
    print(comparison_df.to_string(index=False))

    return {
        "all_results": all_results,
        "comparison": comparison_df,
        "best_return": best_return,
        "best_sharpe": best_sharpe,
        "best_drawdown": best_drawdown,
    }


def save_comparison_results(results, output_dir="backtests/results", strategy="momentum"):
    """
    Save comparison results to CSV files.

    Args:
        results (dict): Results dictionary from run_rebalance_period_comparison
        output_dir (str): Directory to save results
        strategy (str): Strategy type for file naming
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_prefix = f"{output_dir}/kurtosis_{strategy}_rebalance_comparison"

    # Save comparison summary
    comparison_file = f"{base_prefix}_summary.csv"
    results["comparison"].to_csv(comparison_file, index=False)
    print(f"\nComparison summary saved to: {comparison_file}")

    # Save individual portfolio values for each rebalance period
    for rebal_days, result in results["all_results"].items():
        prefix = f"{output_dir}/kurtosis_{strategy}_{rebal_days}d_rebal"

        # Portfolio values
        portfolio_file = f"{prefix}_portfolio_values.csv"
        result["portfolio_values"].to_csv(portfolio_file, index=False)

        # Trades
        if not result["trades"].empty:
            trades_file = f"{prefix}_trades.csv"
            result["trades"].to_csv(trades_file, index=False)

        # Kurtosis timeseries
        if not result["kurtosis_timeseries"].empty:
            kurtosis_file = f"{prefix}_kurtosis_timeseries.csv"
            result["kurtosis_timeseries"].to_csv(kurtosis_file, index=False)

        # Metrics
        metrics_file = f"{prefix}_metrics.csv"
        pd.DataFrame([result["metrics"]]).to_csv(metrics_file, index=False)

        # Strategy info
        strategy_file = f"{prefix}_strategy_info.csv"
        result["strategy_info"]["rebalance_days"] = rebal_days
        pd.DataFrame([result["strategy_info"]]).to_csv(strategy_file, index=False)

        print(f"  {rebal_days}-day rebalance results saved with prefix: {prefix}")

    print("\n" + "=" * 80)
    print("ALL RESULTS SAVED")
    print("=" * 80)


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Backtest Kurtosis Factor with Different Rebalance Periods",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--price-data",
        type=str,
        default="data/raw/combined_coinbase_coinmarketcap_daily.csv",
        help="Path to historical OHLCV price data CSV file",
    )
    parser.add_argument(
        "--rebalance-periods",
        type=int,
        nargs="+",
        default=[1, 2, 3, 5, 7, 10, 30],
        help="List of rebalance periods to test (in days)",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="momentum",
        choices=["mean_reversion", "momentum", "long_only_stable", "long_only_volatile"],
        help="Strategy type",
    )
    parser.add_argument(
        "--kurtosis-window", type=int, default=30, help="Window for kurtosis calculation in days"
    )
    parser.add_argument(
        "--volatility-window",
        type=int,
        default=30,
        help="Window for volatility calculation in days",
    )
    parser.add_argument(
        "--long-percentile", type=float, default=20, help="Percentile threshold for long positions"
    )
    parser.add_argument(
        "--short-percentile",
        type=float,
        default=80,
        help="Percentile threshold for short positions",
    )
    parser.add_argument("--max-positions", type=int, default=10, help="Maximum positions per side")
    parser.add_argument(
        "--weighting",
        type=str,
        default="risk_parity",
        choices=["risk_parity", "equal_weight"],
        help="Position weighting method",
    )
    parser.add_argument(
        "--initial-capital", type=float, default=10000, help="Initial portfolio capital in USD"
    )
    parser.add_argument("--leverage", type=float, default=1.0, help="Leverage multiplier")
    parser.add_argument(
        "--long-allocation", type=float, default=0.5, help="Allocation to long side"
    )
    parser.add_argument(
        "--short-allocation", type=float, default=0.5, help="Allocation to short side"
    )
    parser.add_argument(
        "--min-volume", type=float, default=5_000_000, help="Minimum 30d avg daily volume filter"
    )
    parser.add_argument(
        "--min-market-cap", type=float, default=50_000_000, help="Minimum market cap filter"
    )
    parser.add_argument(
        "--start-date", type=str, default=None, help="Start date for backtest (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date", type=str, default=None, help="End date for backtest (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="backtests/results",
        help="Directory for output CSV files",
    )

    args = parser.parse_args()

    # Load data
    print(f"\nLoading price data from {args.price_data}...")
    price_data = load_data(args.price_data)
    print(f"Loaded {len(price_data)} rows for {price_data['symbol'].nunique()} symbols")
    print(f"Date range: {price_data['date'].min().date()} to {price_data['date'].max().date()}")

    # Run comparison
    results = run_rebalance_period_comparison(
        price_data=price_data,
        rebalance_periods=args.rebalance_periods,
        strategy=args.strategy,
        kurtosis_window=args.kurtosis_window,
        volatility_window=args.volatility_window,
        long_percentile=args.long_percentile,
        short_percentile=args.short_percentile,
        max_positions=args.max_positions,
        weighting=args.weighting,
        initial_capital=args.initial_capital,
        leverage=args.leverage,
        long_allocation=args.long_allocation,
        short_allocation=args.short_allocation,
        min_volume=args.min_volume,
        min_market_cap=args.min_market_cap,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    # Save results
    save_comparison_results(results, output_dir=args.output_dir, strategy=args.strategy)

    print("\n" + "=" * 80)
    print("REBALANCE PERIOD COMPARISON COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
