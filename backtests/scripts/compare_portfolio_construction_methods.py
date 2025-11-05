#!/usr/bin/env python3
"""
Portfolio Construction Method Comparison

Compare different portfolio construction approaches with risk parity weighting:
1. Top/bottom 5 coins
2. Top/bottom 10 coins  
3. Decile approach (top 10%, bottom 10%)
4. Quintile approach (top 20%, bottom 20%)

Tests multiple factor strategies:
- Size factor
- Beta factor (BAB)
- Volatility factor
- Carry factor
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backtests.scripts.backtest_vectorized import backtest_factor_vectorized
from backtests.scripts.run_all_backtests import calculate_comprehensive_metrics
from data.scripts.fetch_coinmarketcap_data import fetch_mock_marketcap_data


def run_size_factor_comparison(price_data, marketcap_data):
    """Compare size factor with different portfolio construction methods."""
    print("\n" + "="*80)
    print("SIZE FACTOR - Portfolio Construction Comparison")
    print("="*80)
    
    results = {}
    
    # Ensure marketcap data has the right format
    mcap_df = marketcap_data.copy()
    if 'Market Cap' in mcap_df.columns and 'market_cap' not in mcap_df.columns:
        mcap_df['market_cap'] = mcap_df['Market Cap']
    if 'Symbol' in mcap_df.columns and 'symbol' not in mcap_df.columns:
        mcap_df['symbol'] = mcap_df['Symbol']
    
    configs = [
        ("Top/Bottom 5", {"strategy": "long_small_short_large", "num_buckets": None, "top_n": 5, "bottom_n": 5}),
        ("Top/Bottom 10", {"strategy": "long_small_short_large", "num_buckets": None, "top_n": 10, "bottom_n": 10}),
        ("Decile (10%)", {"strategy": "long_small_short_large", "num_buckets": 10, "long_percentile": 10, "short_percentile": 90}),
        ("Quintile (20%)", {"strategy": "long_small_short_large", "num_buckets": 5, "long_percentile": 20, "short_percentile": 80}),
    ]
    
    for name, config in configs:
        print(f"\n{'-'*80}")
        print(f"Configuration: {name}")
        print(f"Parameters: {config}")
        print(f"{'-'*80}")
        
        try:
            result = backtest_factor_vectorized(
                price_data=price_data,
                factor_type='size',
                strategy=config.get("strategy", "long_small_short_large"),
                marketcap_data=mcap_df,
                num_buckets=config.get("num_buckets", 5),
                volatility_window=30,
                rebalance_days=7,
                initial_capital=10000,
                leverage=1.0,
                long_allocation=0.5,
                short_allocation=0.5,
                weighting_method='risk_parity',
                marketcap_column='market_cap',
                long_percentile=config.get("long_percentile", 20),
                short_percentile=config.get("short_percentile", 80),
            )
            
            metrics = calculate_comprehensive_metrics(result["portfolio_values"], 10000)
            results[name] = {
                "metrics": metrics,
                "portfolio_values": result["portfolio_values"],
                "config": config,
            }
            
            print(f"\n✓ {name} completed:")
            print(f"  Total Return: {metrics['total_return']*100:.2f}%")
            print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
            print(f"  Max Drawdown: {metrics['max_drawdown']*100:.2f}%")
            
        except Exception as e:
            print(f"\n✗ {name} failed: {e}")
            import traceback
            traceback.print_exc()
    
    return results


def run_beta_factor_comparison(price_data):
    """Compare beta factor (BAB) with different portfolio construction methods."""
    print("\n" + "="*80)
    print("BETA FACTOR (BAB) - Portfolio Construction Comparison")
    print("="*80)
    
    results = {}
    
    configs = [
        ("Top/Bottom 5", {"num_buckets": None, "max_positions_per_side": 5, "long_percentile": 20, "short_percentile": 80}),
        ("Top/Bottom 10", {"num_buckets": None, "max_positions_per_side": 10, "long_percentile": 20, "short_percentile": 80}),
        ("Decile (10%)", {"num_buckets": 10, "max_positions_per_side": None, "long_percentile": 10, "short_percentile": 90}),
        ("Quintile (20%)", {"num_buckets": 5, "max_positions_per_side": None, "long_percentile": 20, "short_percentile": 80}),
    ]
    
    for name, config in configs:
        print(f"\n{'-'*80}")
        print(f"Configuration: {name}")
        print(f"Parameters: {config}")
        print(f"{'-'*80}")
        
        try:
            result = backtest_factor_vectorized(
                price_data=price_data,
                factor_type='beta',
                strategy='betting_against_beta',
                beta_window=90,
                volatility_window=30,
                rebalance_days=5,
                num_quintiles=config.get("num_buckets", 5),
                long_percentile=config.get("long_percentile", 20),
                short_percentile=config.get("short_percentile", 80),
                weighting_method='risk_parity',
                initial_capital=10000,
                leverage=1.0,
                long_allocation=0.5,
                short_allocation=0.5,
            )
            
            metrics = calculate_comprehensive_metrics(result["portfolio_values"], 10000)
            results[name] = {
                "metrics": metrics,
                "portfolio_values": result["portfolio_values"],
                "config": config,
            }
            
            print(f"\n✓ {name} completed:")
            print(f"  Total Return: {metrics['total_return']*100:.2f}%")
            print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
            print(f"  Max Drawdown: {metrics['max_drawdown']*100:.2f}%")
            
        except Exception as e:
            print(f"\n✗ {name} failed: {e}")
            import traceback
            traceback.print_exc()
    
    return results


def run_volatility_factor_comparison(price_data):
    """Compare volatility factor with different portfolio construction methods."""
    print("\n" + "="*80)
    print("VOLATILITY FACTOR - Portfolio Construction Comparison")
    print("="*80)
    
    results = {}
    
    configs = [
        ("Top/Bottom 5", {"num_quintiles": None, "max_positions_per_side": 5, "long_percentile": 20, "short_percentile": 80}),
        ("Top/Bottom 10", {"num_quintiles": None, "max_positions_per_side": 10, "long_percentile": 20, "short_percentile": 80}),
        ("Decile (10%)", {"num_quintiles": 10, "max_positions_per_side": None, "long_percentile": 10, "short_percentile": 90}),
        ("Quintile (20%)", {"num_quintiles": 5, "max_positions_per_side": None, "long_percentile": 20, "short_percentile": 80}),
    ]
    
    for name, config in configs:
        print(f"\n{'-'*80}")
        print(f"Configuration: {name}")
        print(f"Parameters: {config}")
        print(f"{'-'*80}")
        
        try:
            result = backtest_factor_vectorized(
                price_data=price_data,
                factor_type='volatility',
                strategy='long_low_short_high',
                volatility_window=30,
                rebalance_days=3,
                num_quintiles=config.get("num_quintiles", 5),
                long_percentile=config.get("long_percentile", 20),
                short_percentile=config.get("short_percentile", 80),
                weighting_method='risk_parity',
                initial_capital=10000,
                leverage=1.0,
                long_allocation=0.5,
                short_allocation=0.5,
            )
            
            metrics = calculate_comprehensive_metrics(result["portfolio_values"], 10000)
            results[name] = {
                "metrics": metrics,
                "portfolio_values": result["portfolio_values"],
                "config": config,
            }
            
            print(f"\n✓ {name} completed:")
            print(f"  Total Return: {metrics['total_return']*100:.2f}%")
            print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
            print(f"  Max Drawdown: {metrics['max_drawdown']*100:.2f}%")
            
        except Exception as e:
            print(f"\n✗ {name} failed: {e}")
            import traceback
            traceback.print_exc()
    
    return results


def create_comparison_summary(all_results):
    """Create summary table and visualizations comparing all methods."""
    print("\n" + "="*80)
    print("PORTFOLIO CONSTRUCTION METHOD COMPARISON SUMMARY")
    print("="*80)
    
    # Build summary dataframe
    rows = []
    for strategy, results in all_results.items():
        for method, data in results.items():
            metrics = data["metrics"]
            rows.append({
                "Strategy": strategy,
                "Method": method,
                "Total Return (%)": metrics["total_return"] * 100,
                "Sharpe Ratio": metrics["sharpe_ratio"],
                "Max Drawdown (%)": metrics["max_drawdown"] * 100,
                "Win Rate (%)": metrics.get("win_rate", 0) * 100,
                "Annual Return (%)": metrics.get("annualized_return", 0) * 100,
                "Annual Volatility (%)": metrics.get("annualized_volatility", 0) * 100,
            })
    
    summary_df = pd.DataFrame(rows)
    
    # Save to CSV
    output_path = "/workspace/backtests/results/portfolio_construction_comparison.csv"
    summary_df.to_csv(output_path, index=False)
    print(f"\n✓ Summary saved to: {output_path}")
    
    # Print formatted tables
    print("\n" + "="*80)
    print("RESULTS BY STRATEGY")
    print("="*80)
    
    for strategy in summary_df["Strategy"].unique():
        strategy_df = summary_df[summary_df["Strategy"] == strategy].copy()
        strategy_df = strategy_df.sort_values("Sharpe Ratio", ascending=False)
        
        print(f"\n{strategy}")
        print("-" * 80)
        print(strategy_df[["Method", "Total Return (%)", "Sharpe Ratio", "Max Drawdown (%)"]].to_string(index=False))
        
        # Highlight best method
        best_sharpe = strategy_df.iloc[0]
        print(f"\n✓ Best Method (Sharpe): {best_sharpe['Method']} - Sharpe {best_sharpe['Sharpe Ratio']:.3f}")
    
    # Overall ranking
    print("\n" + "="*80)
    print("OVERALL RANKING (by Sharpe Ratio)")
    print("="*80)
    
    ranked_df = summary_df.sort_values("Sharpe Ratio", ascending=False)
    print(ranked_df[["Strategy", "Method", "Sharpe Ratio", "Total Return (%)"]].head(10).to_string(index=False))
    
    # Create visualizations
    create_visualizations(summary_df, all_results)
    
    return summary_df


def create_visualizations(summary_df, all_results):
    """Create comparison visualizations."""
    print("\n" + "="*80)
    print("Creating visualizations...")
    print("="*80)
    
    # Set style
    sns.set_style("whitegrid")
    plt.rcParams['figure.figsize'] = (16, 12)
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Sharpe Ratio comparison
    ax = axes[0, 0]
    pivot_sharpe = summary_df.pivot(index="Method", columns="Strategy", values="Sharpe Ratio")
    pivot_sharpe.plot(kind="bar", ax=ax)
    ax.set_title("Sharpe Ratio by Method and Strategy", fontsize=14, fontweight='bold')
    ax.set_ylabel("Sharpe Ratio")
    ax.set_xlabel("Portfolio Construction Method")
    ax.legend(title="Strategy", bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 2. Total Return comparison
    ax = axes[0, 1]
    pivot_return = summary_df.pivot(index="Method", columns="Strategy", values="Total Return (%)")
    pivot_return.plot(kind="bar", ax=ax)
    ax.set_title("Total Return by Method and Strategy", fontsize=14, fontweight='bold')
    ax.set_ylabel("Total Return (%)")
    ax.set_xlabel("Portfolio Construction Method")
    ax.legend(title="Strategy", bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 3. Max Drawdown comparison
    ax = axes[1, 0]
    pivot_dd = summary_df.pivot(index="Method", columns="Strategy", values="Max Drawdown (%)")
    pivot_dd.plot(kind="bar", ax=ax)
    ax.set_title("Max Drawdown by Method and Strategy", fontsize=14, fontweight='bold')
    ax.set_ylabel("Max Drawdown (%)")
    ax.set_xlabel("Portfolio Construction Method")
    ax.legend(title="Strategy", bbox_to_anchor=(1.05, 1), loc='upper left')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.grid(True, alpha=0.3)
    plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 4. Risk-Adjusted Return (Sharpe) heatmap
    ax = axes[1, 1]
    pivot_sharpe_heat = summary_df.pivot(index="Method", columns="Strategy", values="Sharpe Ratio")
    sns.heatmap(pivot_sharpe_heat, annot=True, fmt='.2f', cmap='RdYlGn', center=0, ax=ax, cbar_kws={'label': 'Sharpe Ratio'})
    ax.set_title("Sharpe Ratio Heatmap", fontsize=14, fontweight='bold')
    ax.set_xlabel("Strategy")
    ax.set_ylabel("Portfolio Construction Method")
    
    plt.tight_layout()
    
    # Save figure
    output_path = "/workspace/backtests/results/portfolio_construction_comparison.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Visualization saved to: {output_path}")
    plt.close()
    
    # Create equity curve comparison for each strategy
    for strategy, results in all_results.items():
        fig, ax = plt.subplots(figsize=(14, 7))
        
        for method, data in results.items():
            pv = data["portfolio_values"].copy()
            pv["normalized"] = pv["portfolio_value"] / pv["portfolio_value"].iloc[0] * 100
            ax.plot(pv["date"], pv["normalized"], label=method, linewidth=2, alpha=0.8)
        
        ax.set_title(f"{strategy} - Equity Curves by Construction Method", fontsize=14, fontweight='bold')
        ax.set_xlabel("Date")
        ax.set_ylabel("Portfolio Value (Normalized to 100)")
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)
        
        output_path = f"/workspace/backtests/results/portfolio_construction_{strategy.lower().replace(' ', '_')}_equity.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"✓ {strategy} equity curve saved to: {output_path}")
        plt.close()


def main():
    """Main execution function."""
    print("="*80)
    print("PORTFOLIO CONSTRUCTION METHOD COMPARISON")
    print("Comparing: Top/Bottom 5, 10, Decile (10%), Quintile (20%)")
    print("Weighting: Risk Parity (Inverse Volatility)")
    print("="*80)
    
    # Load data
    print("\nLoading price data...")
    # Try multiple possible data file locations
    possible_paths = [
        "/workspace/data/raw/combined_coinbase_coinmarketcap_daily.csv",
        "/workspace/data/raw/combined_coinbase_coinmarketcap_daily_backup_20251103_022623.csv",
        "/workspace/data/processed/ohlcv_data_2020_2025.csv",
    ]
    
    price_data_path = None
    for path in possible_paths:
        if os.path.exists(path):
            price_data_path = path
            break
    
    if not os.path.exists(price_data_path):
        print(f"✗ Price data not found at {price_data_path}")
        print("Please ensure data is available before running backtests.")
        return
    
    price_data = pd.read_csv(price_data_path)
    price_data['date'] = pd.to_datetime(price_data['date'])
    print(f"✓ Loaded {len(price_data)} rows of price data")
    print(f"  Date range: {price_data['date'].min()} to {price_data['date'].max()}")
    print(f"  Symbols: {price_data['symbol'].nunique()}")
    
    # Load market cap data
    print("\nLoading market cap data...")
    try:
        marketcap_data = fetch_mock_marketcap_data()
        print(f"✓ Loaded market cap data: {len(marketcap_data)} symbols")
    except Exception as e:
        print(f"⚠ No market cap data available - size factor will be skipped: {e}")
        marketcap_data = None
    
    all_results = {}
    
    # Run comparisons for each strategy
    if marketcap_data is not None:
        all_results["Size Factor"] = run_size_factor_comparison(price_data, marketcap_data)
    
    all_results["Beta Factor (BAB)"] = run_beta_factor_comparison(price_data)
    all_results["Volatility Factor"] = run_volatility_factor_comparison(price_data)
    
    # Create summary and visualizations
    if all_results:
        summary_df = create_comparison_summary(all_results)
        
        print("\n" + "="*80)
        print("COMPARISON COMPLETE")
        print("="*80)
        print(f"\nResults saved to /workspace/backtests/results/")
        print("  - portfolio_construction_comparison.csv")
        print("  - portfolio_construction_comparison.png")
        print("  - portfolio_construction_*_equity.png (per strategy)")
    else:
        print("\n✗ No results generated")


if __name__ == "__main__":
    main()
