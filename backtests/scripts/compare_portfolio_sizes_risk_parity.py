"""
Compare Risk Parity Strategies with Different Portfolio Sizes

This script runs backtests for multiple strategies with different portfolio sizes:
1. Top/Bottom 5 (5 longs + 5 shorts)
2. Top/Bottom 10 (10 longs + 10 shorts)
3. Top/Bottom Decile (top/bottom 10% of universe)
4. Top/Bottom Quintile (top/bottom 20% of universe)

All strategies use risk parity (inverse volatility) weighting.
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backtests", "scripts"))

# Import backtest functions
from run_all_backtests import (
    load_all_data,
    calculate_comprehensive_metrics,
    run_volatility_factor_backtest,
    run_beta_factor_backtest,
    run_carry_factor_backtest,
    run_size_factor_backtest,
    run_kurtosis_factor_backtest,
)

# Import vectorized backtest engine
from backtest_vectorized import backtest_factor_vectorized


def run_portfolio_size_comparison(price_data, marketcap_data, funding_data):
    """Run comparison across different portfolio sizes."""
    
    print("\n" + "=" * 120)
    print("RISK PARITY PORTFOLIO SIZE COMPARISON")
    print("=" * 120)
    print("\nComparing portfolio sizes:")
    print("  1. Top/Bottom 5 (5 longs + 5 shorts)")
    print("  2. Top/Bottom 10 (10 longs + 10 shorts)")
    print("  3. Top/Bottom Decile (top/bottom 10% of universe)")
    print("  4. Top/Bottom Quintile (top/bottom 20% of universe)")
    print("\nAll strategies use RISK PARITY (inverse volatility) weighting")
    print("=" * 120)
    
    # Common parameters
    common_params = {
        "initial_capital": 10000,
        "start_date": "2021-01-01",
        "end_date": None,
        "leverage": 1.0,
        "long_allocation": 0.5,
        "short_allocation": 0.5,
        "volatility_window": 30,
    }
    
    all_results = []
    
    # Portfolio size configurations
    size_configs = [
        ("Top/Bottom 5", {"top_n": 5, "bottom_n": 5, "long_percentile": 5, "short_percentile": 95, "num_quintiles": 20}),
        ("Top/Bottom 10", {"top_n": 10, "bottom_n": 10, "long_percentile": 10, "short_percentile": 90, "num_quintiles": 10}),
        ("Top/Bottom Decile", {"top_n": None, "bottom_n": None, "long_percentile": 10, "short_percentile": 90, "num_quintiles": 10}),
        ("Top/Bottom Quintile", {"top_n": None, "bottom_n": None, "long_percentile": 20, "short_percentile": 80, "num_quintiles": 5}),
    ]
    
    # Run Volatility Factor with different portfolio sizes
    print("\n\n" + "#" * 120)
    print("# VOLATILITY FACTOR (Long Low Vol, Short High Vol)")
    print("#" * 120)
    
    for size_name, size_params in size_configs:
        print(f"\n{'=' * 100}")
        print(f"Running: Volatility Factor - {size_name} (Risk Parity)")
        print(f"{'=' * 100}")
        
        try:
            results = backtest_factor_vectorized(
                price_data=price_data,
                factor_type='volatility',
                strategy='long_low_short_high',
                num_quintiles=size_params["num_quintiles"],
                long_percentile=size_params.get("long_percentile"),
                short_percentile=size_params.get("short_percentile"),
                window=30,
                rebalance_days=3,  # Optimal for volatility
                weighting_method='risk_parity',
                **common_params,
            )
            
            metrics = calculate_comprehensive_metrics(
                results["portfolio_values"], common_params["initial_capital"]
            )
            
            all_results.append({
                "Strategy": f"Volatility Factor - {size_name}",
                "Portfolio Size": size_name,
                "Factor": "Volatility",
                "Weighting": "Risk Parity",
                **metrics
            })
            
            print(f"✓ Completed: Sharpe {metrics['sharpe_ratio']:.3f}, Return {metrics['annualized_return']:.2%}")
        except Exception as e:
            print(f"✗ Failed: {e}")
    
    # Run Beta Factor with different portfolio sizes
    print("\n\n" + "#" * 120)
    print("# BETA FACTOR (Betting Against Beta)")
    print("#" * 120)
    
    for size_name, size_params in size_configs:
        print(f"\n{'=' * 100}")
        print(f"Running: Beta Factor - {size_name} (Risk Parity)")
        print(f"{'=' * 100}")
        
        try:
            results = backtest_factor_vectorized(
                price_data=price_data,
                factor_type='beta',
                strategy='betting_against_beta',
                beta_window=90,
                num_quintiles=size_params["num_quintiles"],
                long_percentile=size_params.get("long_percentile"),
                short_percentile=size_params.get("short_percentile"),
                rebalance_days=5,  # Optimal for beta
                weighting_method='risk_parity',
                **common_params,
            )
            
            metrics = calculate_comprehensive_metrics(
                results["portfolio_values"], common_params["initial_capital"]
            )
            
            all_results.append({
                "Strategy": f"Beta Factor - {size_name}",
                "Portfolio Size": size_name,
                "Factor": "Beta",
                "Weighting": "Risk Parity",
                **metrics
            })
            
            print(f"✓ Completed: Sharpe {metrics['sharpe_ratio']:.3f}, Return {metrics['annualized_return']:.2%}")
        except Exception as e:
            print(f"✗ Failed: {e}")
    
    # Run Carry Factor with different portfolio sizes
    if funding_data is not None:
        print("\n\n" + "#" * 120)
        print("# CARRY FACTOR (Long Negative Funding, Short Positive Funding)")
        print("#" * 120)
        
        for size_name, size_params in size_configs:
            print(f"\n{'=' * 100}")
            print(f"Running: Carry Factor - {size_name} (Risk Parity)")
            print(f"{'=' * 100}")
            
            try:
                # Prepare funding data
                funding_df = funding_data.copy()
                if 'coin_symbol' in funding_df.columns:
                    funding_df['symbol'] = funding_df['coin_symbol']
                
                results = backtest_factor_vectorized(
                    price_data=price_data,
                    factor_type='carry',
                    strategy='carry',
                    funding_data=funding_df,
                    top_n=size_params.get("top_n", 10),
                    bottom_n=size_params.get("bottom_n", 10),
                    rebalance_days=7,  # Optimal for carry
                    weighting_method='risk_parity',
                    funding_column='funding_rate_pct',
                    **common_params,
                )
                
                metrics = calculate_comprehensive_metrics(
                    results["portfolio_values"], common_params["initial_capital"]
                )
                
                all_results.append({
                    "Strategy": f"Carry Factor - {size_name}",
                    "Portfolio Size": size_name,
                    "Factor": "Carry",
                    "Weighting": "Risk Parity",
                    **metrics
                })
                
                print(f"✓ Completed: Sharpe {metrics['sharpe_ratio']:.3f}, Return {metrics['annualized_return']:.2%}")
            except Exception as e:
                print(f"✗ Failed: {e}")
    
    # Run Size Factor with different portfolio sizes
    if marketcap_data is not None:
        print("\n\n" + "#" * 120)
        print("# SIZE FACTOR (Long Small Caps, Short Large Caps)")
        print("#" * 120)
        
        for size_name, size_params in size_configs:
            print(f"\n{'=' * 100}")
            print(f"Running: Size Factor - {size_name} (Risk Parity)")
            print(f"{'=' * 100}")
            
            try:
                mcap_df = marketcap_data.copy()
                if 'Market Cap' in mcap_df.columns:
                    mcap_df['market_cap'] = mcap_df['Market Cap']
                if 'Symbol' in mcap_df.columns:
                    mcap_df['symbol'] = mcap_df['Symbol']
                
                results = backtest_factor_vectorized(
                    price_data=price_data,
                    factor_type='size',
                    strategy='long_small_short_large',
                    marketcap_data=mcap_df,
                    num_buckets=5,
                    rebalance_days=10,  # Optimal for size
                    weighting_method='risk_parity',
                    marketcap_column='market_cap',
                    **common_params,
                )
                
                metrics = calculate_comprehensive_metrics(
                    results["portfolio_values"], common_params["initial_capital"]
                )
                
                all_results.append({
                    "Strategy": f"Size Factor - {size_name}",
                    "Portfolio Size": size_name,
                    "Factor": "Size",
                    "Weighting": "Risk Parity",
                    **metrics
                })
                
                print(f"✓ Completed: Sharpe {metrics['sharpe_ratio']:.3f}, Return {metrics['annualized_return']:.2%}")
            except Exception as e:
                print(f"✗ Failed: {e}")
    
    # Run Kurtosis Factor with different portfolio sizes
    print("\n\n" + "#" * 120)
    print("# KURTOSIS FACTOR (Long Low Kurtosis, Short High Kurtosis - Bear Markets Only)")
    print("#" * 120)
    
    for size_name, size_params in size_configs:
        print(f"\n{'=' * 100}")
        print(f"Running: Kurtosis Factor - {size_name} (Risk Parity)")
        print(f"{'=' * 100}")
        
        try:
            results = backtest_factor_vectorized(
                price_data=price_data,
                factor_type='kurtosis',
                strategy='long_low_short_high',
                kurtosis_window=30,
                long_percentile=size_params.get("long_percentile", 20),
                short_percentile=size_params.get("short_percentile", 80),
                rebalance_days=14,  # Optimal for kurtosis
                weighting_method='risk_parity',
                regime_filter='bear_only',
                reference_symbol='BTC',
                kurtosis_column='kurtosis_30d',
                **common_params,
            )
            
            metrics = calculate_comprehensive_metrics(
                results["portfolio_values"], common_params["initial_capital"]
            )
            
            all_results.append({
                "Strategy": f"Kurtosis Factor - {size_name}",
                "Portfolio Size": size_name,
                "Factor": "Kurtosis",
                "Weighting": "Risk Parity",
                **metrics
            })
            
            print(f"✓ Completed: Sharpe {metrics['sharpe_ratio']:.3f}, Return {metrics['annualized_return']:.2%}")
        except Exception as e:
            print(f"✗ Failed: {e}")
    
    return pd.DataFrame(all_results)


def print_comparison_table(results_df):
    """Print formatted comparison table."""
    print("\n\n" + "=" * 120)
    print("PORTFOLIO SIZE COMPARISON RESULTS")
    print("=" * 120)
    
    if results_df.empty:
        print("No results to display")
        return
    
    # Format display
    display_df = results_df.copy()
    
    # Select key metrics
    key_metrics = [
        "Strategy",
        "Portfolio Size",
        "annualized_return",
        "sharpe_ratio",
        "sortino_ratio",
        "max_drawdown",
        "win_rate",
    ]
    
    display_df = display_df[key_metrics]
    
    # Format percentages
    display_df["annualized_return"] = display_df["annualized_return"].apply(lambda x: f"{x:.2%}")
    display_df["max_drawdown"] = display_df["max_drawdown"].apply(lambda x: f"{x:.2%}")
    display_df["win_rate"] = display_df["win_rate"].apply(lambda x: f"{x:.2%}")
    
    # Format ratios
    display_df["sharpe_ratio"] = display_df["sharpe_ratio"].apply(lambda x: f"{x:.3f}")
    display_df["sortino_ratio"] = display_df["sortino_ratio"].apply(lambda x: f"{x:.3f}")
    
    print(display_df.to_string(index=False))
    print("=" * 120)


def main():
    """Main execution."""
    print("=" * 120)
    print("RISK PARITY PORTFOLIO SIZE COMPARISON")
    print("=" * 120)
    
    # Mock args for load_all_data
    class Args:
        data_file = "data/raw/combined_coinbase_coinmarketcap_daily.csv"
        marketcap_file = "data/raw/coinmarketcap_monthly_all_snapshots.csv"
        funding_rates_file = "data/raw/historical_funding_rates_top100_ALL_HISTORY_20251028_002456.csv"
        oi_data_file = "data/raw/historical_open_interest_all_perps_since2020_20251027_042634.csv"
        run_oi_divergence = False
        run_leverage_inverted = False
    
    args = Args()
    
    # Load data once
    loaded_data = load_all_data(args)
    
    if loaded_data["price_data"] is None:
        print("ERROR: Price data not available")
        return
    
    # Run comparison
    results_df = run_portfolio_size_comparison(
        loaded_data["price_data"],
        loaded_data["marketcap_data"],
        loaded_data["funding_data"],
    )
    
    # Print results
    print_comparison_table(results_df)
    
    # Save results
    output_file = "backtests/results/risk_parity_portfolio_size_comparison.csv"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    results_df.to_csv(output_file, index=False)
    print(f"\nResults saved to: {output_file}")
    
    print("\n" + "=" * 120)
    print("COMPARISON COMPLETE")
    print("=" * 120)


if __name__ == "__main__":
    main()
