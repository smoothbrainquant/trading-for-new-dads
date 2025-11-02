"""
Compare Breakout Strategy Parameters

Tests different entry/exit window combinations to find optimal parameters.
Includes the original configuration (50d entry, 70d exit).
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "signals"))

from backtest_breakout_signals import backtest


def load_data(filepath):
    """Load historical OHLCV data."""
    df = pd.read_csv(filepath)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    return df


def run_parameter_comparison(
    data,
    parameter_configs,
    initial_capital=10000,
    leverage=1.0,
    long_allocation=0.5,
    short_allocation=0.5,
    start_date="2023-01-01",
    end_date=None,
):
    """
    Run backtests for multiple parameter configurations.
    
    Args:
        data: Price data DataFrame
        parameter_configs: List of dicts with entry_window, exit_window, volatility_window
        initial_capital: Starting capital
        leverage: Leverage multiplier
        long_allocation: Long side allocation
        short_allocation: Short side allocation
        start_date: Backtest start date
        end_date: Backtest end date
        
    Returns:
        DataFrame with comparison results
    """
    results = []
    
    print("=" * 120)
    print("BREAKOUT PARAMETER COMPARISON")
    print("=" * 120)
    print(f"\nTesting {len(parameter_configs)} parameter configurations...")
    print(f"Dataset: {data['symbol'].nunique()} symbols, {len(data['date'].unique())} unique dates")
    print(f"Period: {start_date} to {end_date or 'latest'}")
    print(f"Initial capital: ${initial_capital:,.2f}")
    print("=" * 120)
    
    for i, config in enumerate(parameter_configs, 1):
        entry_window = config["entry_window"]
        exit_window = config["exit_window"]
        volatility_window = config.get("volatility_window", 30)
        
        config_name = f"Entry_{entry_window}d_Exit_{exit_window}d"
        is_original = (entry_window == 50 and exit_window == 70)
        
        print(f"\n[{i}/{len(parameter_configs)}] Testing: {config_name}" + 
              (" (ORIGINAL)" if is_original else ""))
        print("-" * 120)
        
        try:
            backtest_results = backtest(
                data=data,
                entry_window=entry_window,
                exit_window=exit_window,
                volatility_window=volatility_window,
                initial_capital=initial_capital,
                leverage=leverage,
                long_allocation=long_allocation,
                short_allocation=short_allocation,
                start_date=start_date,
                end_date=end_date,
            )
            
            metrics = backtest_results["metrics"]
            
            results.append({
                "Configuration": config_name,
                "Entry Window": entry_window,
                "Exit Window": exit_window,
                "Volatility Window": volatility_window,
                "Is Original": is_original,
                "Total Return": metrics["total_return"],
                "Annualized Return": metrics["annualized_return"],
                "Sharpe Ratio": metrics["sharpe_ratio"],
                "Max Drawdown": metrics["max_drawdown"],
                "Win Rate": metrics["win_rate"],
                "Volatility": metrics["annualized_volatility"],
                "Avg Long Positions": metrics["avg_long_positions"],
                "Avg Short Positions": metrics["avg_short_positions"],
                "Avg Total Positions": metrics["avg_total_positions"],
                "Avg Net Exposure": metrics["avg_net_exposure"],
                "Avg Gross Exposure": metrics["avg_gross_exposure"],
                "Final Value": metrics["final_value"],
                "Num Days": metrics["num_days"],
            })
            
            print(f"  ? Completed | Return: {metrics['annualized_return']:.2%} | " +
                  f"Sharpe: {metrics['sharpe_ratio']:.3f} | " +
                  f"Max DD: {metrics['max_drawdown']:.2%}")
            
        except Exception as e:
            print(f"  ? Error: {e}")
            continue
    
    # Create results DataFrame
    results_df = pd.DataFrame(results)
    
    # Sort by Sharpe Ratio (descending)
    results_df = results_df.sort_values("Sharpe Ratio", ascending=False).reset_index(drop=True)
    
    return results_df


def print_comparison_table(results_df):
    """Print formatted comparison table."""
    print("\n" + "=" * 120)
    print("PARAMETER COMPARISON RESULTS")
    print("=" * 120)
    
    if results_df.empty:
        print("No results to display")
        return
    
    # Format the display
    display_df = results_df.copy()
    
    # Add rank column
    display_df.insert(0, "Rank", range(1, len(display_df) + 1))
    
    # Format percentage columns
    pct_cols = ["Total Return", "Annualized Return", "Max Drawdown", "Win Rate", 
                "Volatility", "Avg Net Exposure", "Avg Gross Exposure"]
    for col in pct_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"{x:.2%}")
    
    # Format ratio columns
    if "Sharpe Ratio" in display_df.columns:
        display_df["Sharpe Ratio"] = display_df["Sharpe Ratio"].apply(lambda x: f"{x:.3f}")
    
    # Format position columns
    pos_cols = ["Avg Long Positions", "Avg Short Positions", "Avg Total Positions"]
    for col in pos_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"{x:.1f}")
    
    # Format value columns
    if "Final Value" in display_df.columns:
        display_df["Final Value"] = display_df["Final Value"].apply(lambda x: f"${x:,.2f}")
    
    # Mark original configuration
    if "Is Original" in display_df.columns:
        display_df["Original"] = display_df["Is Original"].apply(lambda x: "?" if x else "")
        display_df = display_df.drop(columns=["Is Original"])
    
    # Print main metrics table
    main_metrics = [
        "Rank", "Configuration", "Original", "Entry Window", "Exit Window",
        "Annualized Return", "Sharpe Ratio", "Max Drawdown", "Win Rate"
    ]
    
    print("\nCore Performance Metrics:")
    print(display_df[main_metrics].to_string(index=False))
    
    # Print additional metrics
    print("\n" + "=" * 120)
    print("Position and Exposure Metrics:")
    additional_metrics = [
        "Rank", "Configuration", "Avg Long Positions", "Avg Short Positions",
        "Avg Total Positions", "Avg Net Exposure", "Avg Gross Exposure"
    ]
    print(display_df[additional_metrics].to_string(index=False))
    
    print("\n" + "=" * 120)
    print("Final Results:")
    final_metrics = [
        "Rank", "Configuration", "Total Return", "Final Value", "Num Days"
    ]
    print(display_df[final_metrics].to_string(index=False))
    
    print("\n" + "=" * 120)


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Compare Breakout Strategy Parameters",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--data-file",
        type=str,
        default="../../data/raw/combined_coinbase_coinmarketcap_daily.csv",
        help="Path to historical OHLCV data CSV file",
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
        "--start-date", type=str, default="2023-01-01", help="Start date for backtest (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date", type=str, default=None, help="End date for backtest (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="backtests/results/breakout_parameter_comparison.csv",
        help="Output file for comparison results",
    )
    
    args = parser.parse_args()
    
    # Load data
    print("\nLoading data...")
    data = load_data(args.data_file)
    print(f"Loaded {len(data)} rows for {data['symbol'].nunique()} symbols")
    print(f"Date range: {data['date'].min().date()} to {data['date'].max().date()}")
    
    # Define parameter configurations to test
    # Include original (50d entry, 70d exit) plus variations
    parameter_configs = [
        # Original configuration
        {"entry_window": 50, "exit_window": 70, "volatility_window": 30},
        
        # Shorter entry windows (faster signals)
        {"entry_window": 20, "exit_window": 30, "volatility_window": 30},
        {"entry_window": 30, "exit_window": 50, "volatility_window": 30},
        {"entry_window": 40, "exit_window": 60, "volatility_window": 30},
        
        # Longer entry windows (more confirmation)
        {"entry_window": 60, "exit_window": 80, "volatility_window": 30},
        {"entry_window": 70, "exit_window": 90, "volatility_window": 30},
        
        # Different exit widths (tighter vs wider stops)
        {"entry_window": 50, "exit_window": 60, "volatility_window": 30},  # Tighter stop
        {"entry_window": 50, "exit_window": 80, "volatility_window": 30},  # Wider stop
        {"entry_window": 50, "exit_window": 50, "volatility_window": 30},  # Same entry/exit
        
        # Aggressive short-term
        {"entry_window": 10, "exit_window": 15, "volatility_window": 20},
        {"entry_window": 15, "exit_window": 20, "volatility_window": 20},
        
        # Ultra long-term
        {"entry_window": 100, "exit_window": 120, "volatility_window": 30},
    ]
    
    # Run parameter comparison
    results_df = run_parameter_comparison(
        data=data,
        parameter_configs=parameter_configs,
        initial_capital=args.initial_capital,
        leverage=args.leverage,
        long_allocation=args.long_allocation,
        short_allocation=args.short_allocation,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    
    # Print comparison table
    print_comparison_table(results_df)
    
    # Save results
    if not results_df.empty:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(args.output_file), exist_ok=True)
        
        # Save with original numeric values
        results_df.to_csv(args.output_file, index=False)
        print(f"\nComparison results saved to: {args.output_file}")
    
    print("\n" + "=" * 120)
    print("PARAMETER COMPARISON COMPLETE")
    print("=" * 120)


if __name__ == "__main__":
    main()
