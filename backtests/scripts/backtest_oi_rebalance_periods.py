#!/usr/bin/env python3
"""
Backtest OI Divergence Strategy with Multiple Rebalance Periods
Tests rebalance periods: [1, 2, 3, 5, 7, 10, 30] days
"""

import sys
import os
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backtests.scripts.backtest_open_interest_divergence import (
    load_price_data,
    load_oi_data,
    backtest,
    BacktestConfig,
)


def run_rebalance_period_comparison(
    price_path: str,
    oi_path: str,
    rebalance_periods: list,
    mode: str = "divergence",
    lookback: int = 30,
    top_n: int = 10,
    bottom_n: int = 10,
):
    """Run backtests for multiple rebalance periods and compare results."""
    
    print(f"\n{'='*80}")
    print(f"OI {mode.upper()} - Rebalance Period Comparison")
    print(f"{'='*80}\n")
    
    # Load data once
    print(f"Loading data...")
    print(f"  Price data: {price_path}")
    print(f"  OI data: {oi_path}")
    price_df = load_price_data(price_path)
    oi_df = load_oi_data(oi_path)
    print(f"  ✓ Loaded {len(price_df)} price records, {len(oi_df)} OI records\n")
    
    results_summary = []
    all_portfolio_values = {}
    
    for period in rebalance_periods:
        print(f"\nRunning backtest with {period}-day rebalance period...")
        
        cfg = BacktestConfig(
            lookback=lookback,
            volatility_window=30,
            rebalance_days=period,
            top_n=top_n,
            bottom_n=bottom_n,
            mode=mode,
            initial_capital=10000.0,
        )
        
        try:
            result = backtest(price_df, oi_df, cfg)
            metrics = result["metrics"]
            pv = result["portfolio_values"]
            
            # Store results
            all_portfolio_values[f"{period}d"] = pv
            
            summary_row = {
                "rebalance_period": period,
                "final_value": metrics["final_value"],
                "total_return": metrics["total_return"],
                "annualized_return": metrics["annualized_return"],
                "annualized_volatility": metrics["annualized_volatility"],
                "sharpe_ratio": metrics["sharpe_ratio"],
                "max_drawdown": metrics["max_drawdown"],
            }
            results_summary.append(summary_row)
            
            # Print summary
            print(f"  ✓ Rebalance Period: {period} days")
            print(f"    Final Value: ${metrics['final_value']:,.2f}")
            print(f"    Total Return: {metrics['total_return']*100:.2f}%")
            print(f"    Annualized Return: {metrics['annualized_return']*100:.2f}%")
            print(f"    Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
            print(f"    Max Drawdown: {metrics['max_drawdown']*100:.2f}%")
            
        except Exception as e:
            print(f"  ✗ Error with {period}-day period: {e}")
            continue
    
    # Create summary DataFrame
    summary_df = pd.DataFrame(results_summary)
    
    if not summary_df.empty:
        print(f"\n{'='*80}")
        print("COMPARISON SUMMARY")
        print(f"{'='*80}\n")
        print(summary_df.to_string(index=False))
        
        # Find best performing configurations
        print(f"\n{'='*80}")
        print("BEST PERFORMING CONFIGURATIONS")
        print(f"{'='*80}")
        best_sharpe = summary_df.loc[summary_df["sharpe_ratio"].idxmax()]
        best_return = summary_df.loc[summary_df["annualized_return"].idxmax()]
        min_dd = summary_df.loc[summary_df["max_drawdown"].idxmax()]
        
        print(f"\nBest Sharpe Ratio: {best_sharpe['rebalance_period']:.0f} days")
        print(f"  Sharpe: {best_sharpe['sharpe_ratio']:.3f}")
        print(f"  Ann. Return: {best_sharpe['annualized_return']*100:.2f}%")
        
        print(f"\nBest Annualized Return: {best_return['rebalance_period']:.0f} days")
        print(f"  Ann. Return: {best_return['annualized_return']*100:.2f}%")
        print(f"  Sharpe: {best_return['sharpe_ratio']:.3f}")
        
        print(f"\nLowest Max Drawdown: {min_dd['rebalance_period']:.0f} days")
        print(f"  Max Drawdown: {min_dd['max_drawdown']*100:.2f}%")
        print(f"  Sharpe: {min_dd['sharpe_ratio']:.3f}")
        
        # Save results
        output_dir = Path("backtests/results")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        summary_path = output_dir / f"oi_{mode}_rebalance_comparison_summary.csv"
        summary_df.to_csv(summary_path, index=False)
        print(f"\n✓ Saved summary to {summary_path}")
        
        # Save individual portfolio values
        for period_name, pv_df in all_portfolio_values.items():
            pv_path = output_dir / f"oi_{mode}_rebalance_{period_name}_portfolio_values.csv"
            pv_df.to_csv(pv_path, index=False)
        print(f"✓ Saved {len(all_portfolio_values)} portfolio value files")
        
        # Generate visualizations
        generate_comparison_charts(summary_df, all_portfolio_values, mode, output_dir)
        
    return summary_df, all_portfolio_values


def generate_comparison_charts(summary_df, portfolio_values, mode, output_dir):
    """Generate comparison charts for different rebalance periods."""
    
    print(f"\nGenerating comparison charts...")
    
    # Set style
    plt.style.use('seaborn-v0_8-darkgrid')
    sns.set_palette("husl")
    
    # 1. Equity Curves
    fig, ax = plt.subplots(figsize=(14, 8))
    for period_name, pv_df in sorted(portfolio_values.items()):
        pv_df = pv_df.copy()
        pv_df["date"] = pd.to_datetime(pv_df["date"])
        pv_df = pv_df.sort_values("date")
        
        # Normalize to 100
        normalized = (pv_df["portfolio_value"] / pv_df["portfolio_value"].iloc[0]) * 100
        ax.plot(pv_df["date"], normalized, label=period_name, linewidth=2)
    
    ax.set_xlabel("Date", fontsize=12)
    ax.set_ylabel("Portfolio Value (Base = 100)", fontsize=12)
    ax.set_title(f"OI {mode.upper()} - Equity Curves by Rebalance Period", fontsize=14, fontweight='bold')
    ax.legend(title="Rebalance Period", fontsize=10, loc='best')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    
    equity_path = output_dir / f"oi_{mode}_rebalance_comparison_equity_curves.png"
    plt.savefig(equity_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ Saved equity curves to {equity_path}")
    plt.close()
    
    # 2. Performance Metrics Comparison
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # Sharpe Ratio
    axes[0, 0].bar(summary_df["rebalance_period"].astype(str) + "d", 
                    summary_df["sharpe_ratio"], 
                    color='steelblue', edgecolor='black')
    axes[0, 0].set_title("Sharpe Ratio", fontweight='bold')
    axes[0, 0].set_ylabel("Sharpe Ratio")
    axes[0, 0].grid(True, alpha=0.3, axis='y')
    axes[0, 0].tick_params(axis='x', rotation=0)
    
    # Annualized Return
    axes[0, 1].bar(summary_df["rebalance_period"].astype(str) + "d", 
                    summary_df["annualized_return"] * 100, 
                    color='green', edgecolor='black')
    axes[0, 1].set_title("Annualized Return", fontweight='bold')
    axes[0, 1].set_ylabel("Return (%)")
    axes[0, 1].grid(True, alpha=0.3, axis='y')
    axes[0, 1].tick_params(axis='x', rotation=0)
    
    # Max Drawdown
    axes[1, 0].bar(summary_df["rebalance_period"].astype(str) + "d", 
                    summary_df["max_drawdown"] * 100, 
                    color='red', edgecolor='black')
    axes[1, 0].set_title("Max Drawdown", fontweight='bold')
    axes[1, 0].set_ylabel("Drawdown (%)")
    axes[1, 0].set_xlabel("Rebalance Period")
    axes[1, 0].grid(True, alpha=0.3, axis='y')
    axes[1, 0].tick_params(axis='x', rotation=0)
    
    # Annualized Volatility
    axes[1, 1].bar(summary_df["rebalance_period"].astype(str) + "d", 
                    summary_df["annualized_volatility"] * 100, 
                    color='orange', edgecolor='black')
    axes[1, 1].set_title("Annualized Volatility", fontweight='bold')
    axes[1, 1].set_ylabel("Volatility (%)")
    axes[1, 1].set_xlabel("Rebalance Period")
    axes[1, 1].grid(True, alpha=0.3, axis='y')
    axes[1, 1].tick_params(axis='x', rotation=0)
    
    plt.suptitle(f"OI {mode.upper()} - Performance Metrics by Rebalance Period", 
                 fontsize=14, fontweight='bold', y=1.00)
    plt.tight_layout()
    
    metrics_path = output_dir / f"oi_{mode}_rebalance_comparison_metrics.png"
    plt.savefig(metrics_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ Saved metrics comparison to {metrics_path}")
    plt.close()
    
    # 3. Return vs Risk Scatter
    fig, ax = plt.subplots(figsize=(10, 8))
    scatter = ax.scatter(summary_df["annualized_volatility"] * 100,
                         summary_df["annualized_return"] * 100,
                         s=summary_df["sharpe_ratio"] * 100,
                         c=summary_df["rebalance_period"],
                         cmap='viridis',
                         alpha=0.7,
                         edgecolors='black',
                         linewidth=2)
    
    # Add labels for each point
    for idx, row in summary_df.iterrows():
        ax.annotate(f"{int(row['rebalance_period'])}d",
                    (row["annualized_volatility"] * 100, row["annualized_return"] * 100),
                    xytext=(5, 5), textcoords='offset points', fontsize=9)
    
    ax.set_xlabel("Annualized Volatility (%)", fontsize=12)
    ax.set_ylabel("Annualized Return (%)", fontsize=12)
    ax.set_title(f"OI {mode.upper()} - Return vs Risk by Rebalance Period\n(bubble size = Sharpe Ratio)", 
                 fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Rebalance Period (days)', fontsize=11)
    
    plt.tight_layout()
    scatter_path = output_dir / f"oi_{mode}_rebalance_comparison_scatter.png"
    plt.savefig(scatter_path, dpi=300, bbox_inches='tight')
    print(f"  ✓ Saved scatter plot to {scatter_path}")
    plt.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Backtest OI Divergence with Multiple Rebalance Periods",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--price-data",
        type=str,
        default="data/raw/combined_coinbase_coinmarketcap_daily.csv",
        help="Path to price data CSV",
    )
    parser.add_argument(
        "--oi-data",
        type=str,
        default="data/raw/historical_open_interest_all_perps_since2020_20251027_044505.csv",
        help="Path to OI data CSV",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="divergence",
        choices=["trend", "divergence"],
        help="Strategy mode",
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=30,
        help="Lookback window for score calculation",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=10,
        help="Number of top-ranked coins to go long",
    )
    parser.add_argument(
        "--bottom-n",
        type=int,
        default=10,
        help="Number of bottom-ranked coins to go short",
    )
    parser.add_argument(
        "--rebalance-periods",
        type=int,
        nargs="+",
        default=[1, 2, 3, 5, 7, 10, 30],
        help="List of rebalance periods to test (in days)",
    )
    
    args = parser.parse_args()
    
    summary_df, portfolio_values = run_rebalance_period_comparison(
        price_path=args.price_data,
        oi_path=args.oi_data,
        rebalance_periods=args.rebalance_periods,
        mode=args.mode,
        lookback=args.lookback,
        top_n=args.top_n,
        bottom_n=args.bottom_n,
    )
    
    print(f"\n{'='*80}")
    print("Backtest Complete!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
