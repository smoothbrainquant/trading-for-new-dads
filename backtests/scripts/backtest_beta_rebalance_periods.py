#!/usr/bin/env python3
"""
Backtest Beta Factor with Different Rebalance Periods

This script runs the beta factor backtest with different rebalance periods
to analyze how rebalancing frequency affects strategy performance.

Rebalance periods tested: [1, 2, 3, 5, 7, 10, 30] days
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

# Import the beta backtest module
from backtest_beta_factor import load_data, run_backtest, print_results


def compare_rebalance_periods(
    data,
    rebalance_periods=[1, 2, 3, 5, 7, 10, 30],
    strategy="betting_against_beta",
    beta_window=90,
    volatility_window=30,
    output_dir="backtests/results",
):
    """
    Run beta factor backtest with different rebalance periods.
    
    Args:
        data (pd.DataFrame): Historical OHLCV data
        rebalance_periods (list): List of rebalance periods to test (in days)
        strategy (str): Beta strategy type
        beta_window (int): Beta calculation window
        volatility_window (int): Volatility calculation window
        output_dir (str): Directory to save results
        
    Returns:
        pd.DataFrame: Comparison summary of all rebalance periods
    """
    print("=" * 80)
    print("BETA FACTOR - REBALANCE PERIOD COMPARISON")
    print("=" * 80)
    print(f"\nTesting rebalance periods: {rebalance_periods}")
    print(f"Strategy: {strategy}")
    print(f"Beta Window: {beta_window} days")
    print(f"Volatility Window: {volatility_window} days")
    
    results_summary = []
    all_results = {}
    
    for period in rebalance_periods:
        print("\n" + "=" * 80)
        print(f"TESTING REBALANCE PERIOD: {period} days")
        print("=" * 80)
        
        try:
            # Run backtest with this rebalance period
            results = run_backtest(
                data=data,
                strategy=strategy,
                beta_window=beta_window,
                volatility_window=volatility_window,
                rebalance_days=period,
                num_quintiles=5,
                long_percentile=20,
                short_percentile=80,
                weighting_method="equal_weight",
                initial_capital=10000,
                leverage=1.0,
                long_allocation=0.5,
                short_allocation=0.5,
                min_volume=5_000_000,
                min_market_cap=50_000_000,
            )
            
            # Store results
            all_results[period] = results
            
            # Extract key metrics
            metrics = results["metrics"]
            summary = {
                "rebalance_days": period,
                "total_return": metrics["total_return"],
                "annualized_return": metrics["annualized_return"],
                "annualized_volatility": metrics["annualized_volatility"],
                "sharpe_ratio": metrics["sharpe_ratio"],
                "sortino_ratio": metrics["sortino_ratio"],
                "max_drawdown": metrics["max_drawdown"],
                "calmar_ratio": metrics["calmar_ratio"],
                "win_rate": metrics["win_rate"],
                "trading_days": metrics["trading_days"],
                "avg_long_positions": metrics["avg_long_positions"],
                "avg_short_positions": metrics["avg_short_positions"],
                "avg_portfolio_beta": metrics["avg_portfolio_beta"],
                "final_value": metrics["final_value"],
            }
            results_summary.append(summary)
            
            # Save individual results
            output_prefix = os.path.join(
                output_dir, f"beta_rebalance_{period}d"
            )
            save_individual_results(results, output_prefix, period)
            
            print("\n" + "-" * 80)
            print(f"COMPLETED: Rebalance period {period} days")
            print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            print(f"Annualized Return: {metrics['annualized_return']:.2%}")
            print(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
            
        except Exception as e:
            print(f"\n❌ ERROR: Failed to backtest rebalance period {period} days")
            print(f"Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Create comparison DataFrame
    comparison_df = pd.DataFrame(results_summary)
    
    if not comparison_df.empty:
        # Sort by rebalance days
        comparison_df = comparison_df.sort_values("rebalance_days")
        
        # Save comparison summary
        comparison_file = os.path.join(output_dir, "beta_rebalance_comparison.csv")
        comparison_df.to_csv(comparison_file, index=False)
        print("\n" + "=" * 80)
        print("COMPARISON SUMMARY")
        print("=" * 80)
        print(f"\n✓ Saved comparison summary to: {comparison_file}")
        
        # Print comparison table
        print("\n" + "-" * 80)
        print("Performance Comparison:")
        print("-" * 80)
        print(comparison_df.to_string(index=False))
        
        # Find best performers
        print("\n" + "-" * 80)
        print("Best Performers:")
        print("-" * 80)
        
        best_sharpe = comparison_df.loc[comparison_df["sharpe_ratio"].idxmax()]
        print(f"Highest Sharpe Ratio: {best_sharpe['rebalance_days']:.0f} days "
              f"(Sharpe: {best_sharpe['sharpe_ratio']:.2f})")
        
        best_return = comparison_df.loc[comparison_df["annualized_return"].idxmax()]
        print(f"Highest Annualized Return: {best_return['rebalance_days']:.0f} days "
              f"(Return: {best_return['annualized_return']:.2%})")
        
        best_calmar = comparison_df.loc[comparison_df["calmar_ratio"].idxmax()]
        print(f"Highest Calmar Ratio: {best_calmar['rebalance_days']:.0f} days "
              f"(Calmar: {best_calmar['calmar_ratio']:.2f})")
        
        min_drawdown = comparison_df.loc[comparison_df["max_drawdown"].idxmax()]  # Less negative = better
        print(f"Lowest Max Drawdown: {min_drawdown['rebalance_days']:.0f} days "
              f"(Drawdown: {min_drawdown['max_drawdown']:.2%})")
        
        # Generate visualizations
        generate_comparison_plots(comparison_df, all_results, output_dir)
    
    return comparison_df


def save_individual_results(results, output_prefix, period):
    """
    Save individual backtest results to CSV files.
    
    Args:
        results (dict): Backtest results dictionary
        output_prefix (str): Prefix for output files
        period (int): Rebalance period
    """
    output_dir = os.path.dirname(output_prefix) or "."
    os.makedirs(output_dir, exist_ok=True)
    
    # Save portfolio values
    portfolio_file = f"{output_prefix}_portfolio_values.csv"
    results["portfolio_values"].to_csv(portfolio_file, index=False)
    
    # Save trades
    trades_file = f"{output_prefix}_trades.csv"
    results["trades"].to_csv(trades_file, index=False)
    
    # Save metrics
    metrics_file = f"{output_prefix}_metrics.csv"
    metrics_df = pd.DataFrame([results["metrics"]]).T
    metrics_df.columns = ["value"]
    metrics_df.to_csv(metrics_file)


def generate_comparison_plots(comparison_df, all_results, output_dir):
    """
    Generate comparison plots for different rebalance periods.
    
    Args:
        comparison_df (pd.DataFrame): Summary comparison DataFrame
        all_results (dict): Dictionary of all backtest results
        output_dir (str): Directory to save plots
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('Beta Factor - Rebalance Period Comparison', fontsize=16, fontweight='bold')
        
        # Plot 1: Sharpe Ratio vs Rebalance Period
        ax1 = axes[0, 0]
        ax1.plot(comparison_df['rebalance_days'], comparison_df['sharpe_ratio'], 
                marker='o', linewidth=2, markersize=8)
        ax1.set_xlabel('Rebalance Period (days)', fontsize=12)
        ax1.set_ylabel('Sharpe Ratio', fontsize=12)
        ax1.set_title('Sharpe Ratio vs Rebalance Period', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        
        # Plot 2: Annualized Return vs Rebalance Period
        ax2 = axes[0, 1]
        ax2.plot(comparison_df['rebalance_days'], comparison_df['annualized_return'] * 100, 
                marker='s', linewidth=2, markersize=8, color='green')
        ax2.set_xlabel('Rebalance Period (days)', fontsize=12)
        ax2.set_ylabel('Annualized Return (%)', fontsize=12)
        ax2.set_title('Annualized Return vs Rebalance Period', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        
        # Plot 3: Max Drawdown vs Rebalance Period
        ax3 = axes[1, 0]
        ax3.plot(comparison_df['rebalance_days'], comparison_df['max_drawdown'] * 100, 
                marker='^', linewidth=2, markersize=8, color='red')
        ax3.set_xlabel('Rebalance Period (days)', fontsize=12)
        ax3.set_ylabel('Max Drawdown (%)', fontsize=12)
        ax3.set_title('Max Drawdown vs Rebalance Period', fontsize=14, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        ax3.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        
        # Plot 4: Equity Curves
        ax4 = axes[1, 1]
        for period, results in sorted(all_results.items()):
            portfolio_values = results["portfolio_values"]
            portfolio_values['date'] = pd.to_datetime(portfolio_values['date'])
            normalized_values = portfolio_values['portfolio_value'] / portfolio_values['portfolio_value'].iloc[0]
            ax4.plot(portfolio_values['date'], normalized_values, 
                    label=f'{period}d', linewidth=1.5, alpha=0.8)
        
        ax4.set_xlabel('Date', fontsize=12)
        ax4.set_ylabel('Normalized Portfolio Value', fontsize=12)
        ax4.set_title('Equity Curves (Normalized)', fontsize=14, fontweight='bold')
        ax4.legend(loc='best', fontsize=10)
        ax4.grid(True, alpha=0.3)
        ax4.axhline(y=1, color='gray', linestyle='--', alpha=0.5)
        
        plt.tight_layout()
        
        # Save plot
        plot_file = os.path.join(output_dir, "beta_rebalance_comparison.png")
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        print(f"✓ Saved comparison plot to: {plot_file}")
        plt.close()
        
    except ImportError:
        print("\n⚠ Warning: matplotlib not available, skipping plots")
    except Exception as e:
        print(f"\n⚠ Warning: Failed to generate plots: {str(e)}")


def main():
    """Main function to run rebalance period comparison."""
    # Configuration
    price_data_path = "data/raw/combined_coinbase_coinmarketcap_daily.csv"
    output_dir = "backtests/results"
    rebalance_periods = [1, 2, 3, 5, 7, 10, 30]
    
    # Load data
    print(f"\nLoading data from: {price_data_path}")
    data = load_data(price_data_path)
    print(f"Loaded {len(data)} data points for {data['symbol'].nunique()} symbols")
    print(f"Date range: {data['date'].min().date()} to {data['date'].max().date()}")
    
    # Run comparison
    comparison_df = compare_rebalance_periods(
        data=data,
        rebalance_periods=rebalance_periods,
        strategy="betting_against_beta",
        beta_window=90,
        volatility_window=30,
        output_dir=output_dir,
    )
    
    print("\n" + "=" * 80)
    print("REBALANCE PERIOD COMPARISON COMPLETE")
    print("=" * 80)
    
    return comparison_df


if __name__ == "__main__":
    main()
