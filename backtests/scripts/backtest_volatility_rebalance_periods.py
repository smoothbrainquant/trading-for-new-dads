#!/usr/bin/env python3
"""
Compare Volatility Factor Backtest Results Across Different Rebalance Periods

This script runs the volatility factor backtest with different rebalance frequencies
and compares the results to find the optimal rebalance period.

Rebalance periods tested: [1, 2, 3, 5, 7, 10, 30] days
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "signals"))
from backtest_volatility_factor import backtest, load_data


def run_rebalance_period_comparison(
    price_data,
    rebalance_periods=[1, 2, 3, 5, 7, 10, 30],
    strategy="long_low_short_high",
    num_quintiles=5,
    volatility_window=30,
    start_date=None,
    end_date=None,
    initial_capital=10000,
    leverage=1.0,
    long_allocation=0.5,
    short_allocation=0.5,
    weighting_method="equal",
    output_dir="backtests/results",
):
    """
    Run backtests for different rebalance periods and compare results.
    
    Args:
        price_data (pd.DataFrame): Historical OHLCV data
        rebalance_periods (list): List of rebalance periods to test (in days)
        strategy (str): Volatility factor strategy type
        num_quintiles (int): Number of volatility quintiles
        volatility_window (int): Window for volatility calculation
        start_date (str): Start date for backtest
        end_date (str): End date for backtest
        initial_capital (float): Initial portfolio capital
        leverage (float): Leverage multiplier
        long_allocation (float): Allocation to long side
        short_allocation (float): Allocation to short side
        weighting_method (str): 'equal' or 'risk_parity'
        output_dir (str): Directory to save results
        
    Returns:
        dict: Dictionary containing all backtest results
    """
    print("=" * 80)
    print("VOLATILITY FACTOR: REBALANCE PERIOD COMPARISON")
    print("=" * 80)
    print(f"\nTesting rebalance periods: {rebalance_periods}")
    print(f"Strategy: {strategy}")
    print(f"Volatility window: {volatility_window}d")
    print(f"Num quintiles: {num_quintiles}")
    print(f"Weighting method: {weighting_method}")
    print(f"Initial capital: ${initial_capital:,.2f}")
    print("=" * 80)
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Store all results
    all_results = {}
    comparison_data = []
    
    # Run backtest for each rebalance period
    for rebalance_days in rebalance_periods:
        print(f"\n{'='*80}")
        print(f"TESTING REBALANCE PERIOD: {rebalance_days} DAYS")
        print(f"{'='*80}")
        
        try:
            # Run backtest
            results = backtest(
                price_data=price_data,
                strategy=strategy,
                num_quintiles=num_quintiles,
                volatility_window=volatility_window,
                rebalance_days=rebalance_days,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                leverage=leverage,
                long_allocation=long_allocation,
                short_allocation=short_allocation,
                weighting_method=weighting_method,
            )
            
            all_results[rebalance_days] = results
            
            # Extract key metrics for comparison
            metrics = results["metrics"]
            comparison_data.append({
                "rebalance_days": rebalance_days,
                "total_return": metrics["total_return"],
                "annualized_return": metrics["annualized_return"],
                "annualized_volatility": metrics["annualized_volatility"],
                "sharpe_ratio": metrics["sharpe_ratio"],
                "max_drawdown": metrics["max_drawdown"],
                "win_rate": metrics["win_rate"],
                "num_days": metrics["num_days"],
                "avg_long_positions": metrics["avg_long_positions"],
                "avg_short_positions": metrics["avg_short_positions"],
                "avg_total_positions": metrics["avg_total_positions"],
                "avg_net_exposure": metrics["avg_net_exposure"],
                "avg_gross_exposure": metrics["avg_gross_exposure"],
                "num_trades": len(results["trades"]) if not results["trades"].empty else 0,
            })
            
            # Save individual results
            output_prefix = f"volatility_rebalance_{rebalance_days}d"
            
            # Save portfolio values
            portfolio_file = os.path.join(output_dir, f"{output_prefix}_portfolio_values.csv")
            results["portfolio_values"].to_csv(portfolio_file, index=False)
            
            # Save trades
            if not results["trades"].empty:
                trades_file = os.path.join(output_dir, f"{output_prefix}_trades.csv")
                results["trades"].to_csv(trades_file, index=False)
            
            # Save metrics
            metrics_file = os.path.join(output_dir, f"{output_prefix}_metrics.csv")
            metrics_df = pd.DataFrame([metrics])
            metrics_df.to_csv(metrics_file, index=False)
            
            print(f"\n✓ Completed {rebalance_days}d rebalance backtest")
            print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
            print(f"  Annualized Return: {metrics['annualized_return']:.2%}")
            print(f"  Max Drawdown: {metrics['max_drawdown']:.2%}")
            
        except Exception as e:
            print(f"\n✗ Error running backtest for {rebalance_days}d: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Create comparison DataFrame
    comparison_df = pd.DataFrame(comparison_data)
    
    if not comparison_df.empty:
        # Sort by Sharpe ratio descending
        comparison_df = comparison_df.sort_values("sharpe_ratio", ascending=False)
        
        # Save comparison results
        comparison_file = os.path.join(output_dir, "volatility_rebalance_comparison.csv")
        comparison_df.to_csv(comparison_file, index=False)
        print(f"\n\nComparison results saved to: {comparison_file}")
        
        # Print comparison summary
        print_comparison_summary(comparison_df)
    
    return {
        "all_results": all_results,
        "comparison": comparison_df,
    }


def print_comparison_summary(comparison_df):
    """
    Print a formatted comparison summary of all rebalance periods.
    
    Args:
        comparison_df (pd.DataFrame): DataFrame with comparison metrics
    """
    print("\n" + "=" * 80)
    print("REBALANCE PERIOD COMPARISON SUMMARY")
    print("=" * 80)
    
    print("\n📊 Performance Metrics Comparison (sorted by Sharpe Ratio):\n")
    
    # Format the display
    display_df = comparison_df.copy()
    
    # Create formatted columns for display
    print(f"{'Rebalance':>10} | {'Total':>10} | {'Annual':>10} | {'Annual':>10} | {'Sharpe':>8} | {'Max':>10} | {'Win':>8} | {'Trades':>8}")
    print(f"{'Days':>10} | {'Return':>10} | {'Return':>10} | {'Vol':>10} | {'Ratio':>8} | {'DD':>10} | {'Rate':>8} | {'Count':>8}")
    print("-" * 107)
    
    for _, row in display_df.iterrows():
        print(
            f"{row['rebalance_days']:>10.0f} | "
            f"{row['total_return']:>9.2%} | "
            f"{row['annualized_return']:>9.2%} | "
            f"{row['annualized_volatility']:>9.2%} | "
            f"{row['sharpe_ratio']:>8.3f} | "
            f"{row['max_drawdown']:>9.2%} | "
            f"{row['win_rate']:>7.2%} | "
            f"{row['num_trades']:>8,.0f}"
        )
    
    print("\n" + "=" * 80)
    
    # Highlight best performers
    print("\n🏆 Best Performers:")
    best_sharpe = display_df.iloc[0]
    print(f"  Best Sharpe Ratio:      {best_sharpe['rebalance_days']:.0f}d ({best_sharpe['sharpe_ratio']:.3f})")
    
    best_return_idx = display_df["annualized_return"].idxmax()
    best_return = display_df.loc[best_return_idx]
    print(f"  Best Annualized Return: {best_return['rebalance_days']:.0f}d ({best_return['annualized_return']:.2%})")
    
    best_dd_idx = display_df["max_drawdown"].idxmax()  # Least negative = best
    best_dd = display_df.loc[best_dd_idx]
    print(f"  Best Max Drawdown:      {best_dd['rebalance_days']:.0f}d ({best_dd['max_drawdown']:.2%})")
    
    lowest_vol_idx = display_df["annualized_volatility"].idxmin()
    lowest_vol = display_df.loc[lowest_vol_idx]
    print(f"  Lowest Volatility:      {lowest_vol['rebalance_days']:.0f}d ({lowest_vol['annualized_volatility']:.2%})")
    
    print("\n" + "=" * 80)
    
    # Trading statistics
    print("\n📈 Trading Statistics:")
    print(f"\n{'Rebalance':>10} | {'Avg Long':>10} | {'Avg Short':>10} | {'Avg Total':>10} | {'Net Exp':>10} | {'Gross Exp':>10}")
    print(f"{'Days':>10} | {'Positions':>10} | {'Positions':>10} | {'Positions':>10} | {'':>10} | {'':>10}")
    print("-" * 73)
    
    for _, row in display_df.iterrows():
        print(
            f"{row['rebalance_days']:>10.0f} | "
            f"{row['avg_long_positions']:>10.1f} | "
            f"{row['avg_short_positions']:>10.1f} | "
            f"{row['avg_total_positions']:>10.1f} | "
            f"{row['avg_net_exposure']:>9.2%} | "
            f"{row['avg_gross_exposure']:>9.2%}"
        )
    
    print("\n" + "=" * 80)


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Compare Volatility Factor Backtest Results Across Rebalance Periods",
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
        default="long_low_short_high",
        choices=["long_low_short_high", "long_low_vol", "long_high_vol", "long_high_short_low"],
        help="Volatility factor strategy type",
    )
    parser.add_argument(
        "--num-quintiles", type=int, default=5, help="Number of volatility quintiles"
    )
    parser.add_argument(
        "--volatility-window", type=int, default=30, help="Volatility calculation window in days"
    )
    parser.add_argument(
        "--weighting-method",
        type=str,
        default="equal",
        choices=["equal", "risk_parity"],
        help="Portfolio weighting method",
    )
    parser.add_argument(
        "--initial-capital", type=float, default=10000, help="Initial portfolio capital"
    )
    parser.add_argument(
        "--leverage", type=float, default=1.0, help="Leverage multiplier"
    )
    parser.add_argument(
        "--long-allocation", type=float, default=0.5, help="Allocation to long side"
    )
    parser.add_argument(
        "--short-allocation", type=float, default=0.5, help="Allocation to short side"
    )
    parser.add_argument(
        "--start-date", type=str, default=None, help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date", type=str, default=None, help="End date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--output-dir", type=str, default="backtests/results", help="Output directory"
    )
    
    args = parser.parse_args()
    
    # Load price data
    print("\nLoading price data...")
    price_data = load_data(args.price_data)
    print(f"Loaded {len(price_data)} rows for {price_data['symbol'].nunique()} symbols")
    print(f"Date range: {price_data['date'].min().date()} to {price_data['date'].max().date()}")
    
    # Run comparison
    results = run_rebalance_period_comparison(
        price_data=price_data,
        rebalance_periods=args.rebalance_periods,
        strategy=args.strategy,
        num_quintiles=args.num_quintiles,
        volatility_window=args.volatility_window,
        start_date=args.start_date,
        end_date=args.end_date,
        initial_capital=args.initial_capital,
        leverage=args.leverage,
        long_allocation=args.long_allocation,
        short_allocation=args.short_allocation,
        weighting_method=args.weighting_method,
        output_dir=args.output_dir,
    )
    
    print("\n" + "=" * 80)
    print("COMPARISON COMPLETE")
    print("=" * 80)
    print(f"\nResults saved to: {args.output_dir}/")
    print(f"  - Individual backtest results: volatility_rebalance_*d_*.csv")
    print(f"  - Comparison summary: volatility_rebalance_comparison.csv")
    print("=" * 80)


if __name__ == "__main__":
    main()
