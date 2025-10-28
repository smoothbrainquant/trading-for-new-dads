#!/usr/bin/env python3
"""
Optimize Rebalance Parameters for All Backtests

This script runs each backtest with different rebalance frequencies
to find the optimal parameter for each strategy based on:
- Sharpe Ratio (primary metric)
- Annualized Return
- Maximum Drawdown
- Calmar Ratio (Return / Max Drawdown)
"""

import pandas as pd
import numpy as np
import subprocess
import os
import sys
from datetime import datetime
import json

# Configuration for each backtest
BACKTESTS = {
    'carry_factor': {
        'script': 'backtest_carry_factor.py',
        'rebalance_param': '--rebalance-days',
        'test_values': [1, 3, 7, 14, 30],
        'default_value': 7,
        'output_prefix': 'backtests/results/backtest_carry_factor',
        'base_args': [
            '--price-data', 'data/raw/combined_coinbase_coinmarketcap_daily.csv',
            '--funding-data', 'data/raw/historical_funding_rates_top100_ALL_HISTORY_20251028_002456.csv'
        ]
    },
    'beta_factor': {
        'script': 'backtest_beta_factor.py',
        'rebalance_param': '--rebalance-days',
        'test_values': [1, 3, 7, 14, 30],
        'default_value': 7,
        'output_prefix': 'backtests/results/backtest_beta_factor',
        'base_args': [
            '--price-data', 'data/raw/combined_coinbase_coinmarketcap_daily.csv'
        ]
    },
    'volatility_factor': {
        'script': 'backtest_volatility_factor.py',
        'rebalance_param': '--rebalance-days',
        'test_values': [1, 3, 7, 14, 30],
        'default_value': 7,
        'output_prefix': 'backtests/results/backtest_volatility_factor',
        'base_args': [
            '--price-data', 'data/raw/combined_coinbase_coinmarketcap_daily.csv'
        ]
    },
    # Disabled: requires market cap data file or API
    # 'size_factor': {
    #     'script': 'backtest_size_factor.py',
    #     'rebalance_param': '--rebalance-days',
    #     'test_values': [1, 3, 7, 14, 30],
    #     'default_value': 7,
    #     'output_prefix': 'backtests/results/backtest_size_factor',
    #     'base_args': [
    #         '--price-data', 'data/raw/combined_coinbase_coinmarketcap_daily.csv'
    #     ]
    # },
    'kurtosis_factor': {
        'script': 'backtest_kurtosis_factor.py',
        'rebalance_param': '--rebalance-days',
        'test_values': [1, 3, 7, 14, 30],
        'default_value': 1,
        'output_prefix': 'backtests/results/backtest_kurtosis_factor',
        'base_args': [
            '--price-data', 'data/raw/combined_coinbase_coinmarketcap_daily.csv'
        ]
    },
    # Disabled: aggregated OI file not available
    # 'open_interest_divergence': {
    #     'script': 'backtest_open_interest_divergence.py',
    #     'rebalance_param': '--rebalance-days',
    #     'test_values': [1, 3, 7, 14, 30],
    #     'default_value': 7,
    #     'output_prefix': 'backtests/results/backtest_open_interest_divergence',
    #     'base_args': [
    #         '--price-data', 'data/raw/combined_coinbase_coinmarketcap_daily.csv',
    #         '--oi-data', 'data/raw/historical_open_interest_top100_since2020_20251026_113816.csv'
    #     ]
    # },
    'skew_factor': {
        'script': 'backtest_skew_factor.py',
        'rebalance_param': None,  # Daily rebalancing by design
        'test_values': None,
        'default_value': 1,
        'output_prefix': 'backtests/results/skew_factor',
        'base_args': [
            '--data-file', 'data/raw/combined_coinbase_coinmarketcap_daily.csv'
        ]
    }
}


def run_backtest(strategy_name, config, rebalance_value=None):
    """
    Run a single backtest with specified rebalance parameter.
    
    Args:
        strategy_name (str): Name of the strategy
        config (dict): Configuration for the backtest
        rebalance_value (int): Rebalance frequency in days (None for strategies without this param)
        
    Returns:
        dict: Performance metrics or None if failed
    """
    script_path = os.path.join('backtests/scripts', config['script'])
    
    # Build command
    cmd = ['python3', script_path] + config['base_args']
    
    # Add rebalance parameter if applicable
    if rebalance_value is not None and config['rebalance_param'] is not None:
        output_suffix = f"_rebal_{rebalance_value}d"
        cmd.extend([config['rebalance_param'], str(rebalance_value)])
    else:
        output_suffix = "_default"
    
    # Add output prefix
    output_prefix = f"{config['output_prefix']}{output_suffix}"
    cmd.extend(['--output-prefix', output_prefix])
    
    print(f"\n{'='*80}")
    print(f"Running {strategy_name} with rebalance={rebalance_value or 'default'} days")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*80}")
    
    try:
        # Set up environment with proper PYTHONPATH
        env = os.environ.copy()
        workspace_dir = os.getcwd()
        signals_dir = os.path.join(workspace_dir, 'signals')
        backtests_dir = os.path.join(workspace_dir, 'backtests', 'scripts')
        
        # Add signals and backtests/scripts to PYTHONPATH
        if 'PYTHONPATH' in env:
            env['PYTHONPATH'] = f"{signals_dir}:{backtests_dir}:{env['PYTHONPATH']}"
        else:
            env['PYTHONPATH'] = f"{signals_dir}:{backtests_dir}"
        
        # Run the backtest
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
            env=env
        )
        
        if result.returncode != 0:
            print(f"ERROR: Backtest failed with return code {result.returncode}")
            print(f"STDERR: {result.stderr}")
            return None
        
        # Read the metrics file
        metrics_file = f"{output_prefix}_metrics.csv"
        
        if not os.path.exists(metrics_file):
            print(f"ERROR: Metrics file not found: {metrics_file}")
            return None
        
        metrics_df = pd.read_csv(metrics_file)
        
        # Extract key metrics
        metrics = {
            'rebalance_days': rebalance_value or config['default_value'],
            'sharpe_ratio': metrics_df['sharpe_ratio'].iloc[0] if 'sharpe_ratio' in metrics_df.columns else np.nan,
            'annualized_return': metrics_df['annualized_return'].iloc[0] if 'annualized_return' in metrics_df.columns else np.nan,
            'annualized_volatility': metrics_df['annualized_volatility'].iloc[0] if 'annualized_volatility' in metrics_df.columns else np.nan,
            'max_drawdown': metrics_df['max_drawdown'].iloc[0] if 'max_drawdown' in metrics_df.columns else np.nan,
            'total_return': metrics_df['total_return'].iloc[0] if 'total_return' in metrics_df.columns else np.nan,
            'win_rate': metrics_df['win_rate'].iloc[0] if 'win_rate' in metrics_df.columns else np.nan,
            'num_days': metrics_df['num_days'].iloc[0] if 'num_days' in metrics_df.columns else np.nan,
        }
        
        # Calculate Calmar ratio if not present
        if 'calmar_ratio' in metrics_df.columns:
            metrics['calmar_ratio'] = metrics_df['calmar_ratio'].iloc[0]
        else:
            if metrics['max_drawdown'] != 0 and not np.isnan(metrics['max_drawdown']):
                metrics['calmar_ratio'] = metrics['annualized_return'] / abs(metrics['max_drawdown'])
            else:
                metrics['calmar_ratio'] = np.nan
        
        print(f"\n✓ Completed {strategy_name} (rebalance={rebalance_value or 'default'}d)")
        print(f"  Sharpe: {metrics['sharpe_ratio']:.3f}")
        print(f"  Return: {metrics['annualized_return']*100:.2f}%")
        print(f"  Max DD: {metrics['max_drawdown']*100:.2f}%")
        print(f"  Calmar: {metrics['calmar_ratio']:.3f}")
        
        return metrics
        
    except subprocess.TimeoutExpired:
        print(f"ERROR: Backtest timed out after 600 seconds")
        return None
    except Exception as e:
        print(f"ERROR: Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return None


def optimize_strategy(strategy_name, config):
    """
    Run optimization for a single strategy.
    
    Args:
        strategy_name (str): Name of the strategy
        config (dict): Configuration for the backtest
        
    Returns:
        pd.DataFrame: Results for all tested rebalance values
    """
    print(f"\n\n{'#'*80}")
    print(f"# OPTIMIZING: {strategy_name.upper()}")
    print(f"{'#'*80}")
    
    # Skip if strategy doesn't have rebalance parameter
    if config['test_values'] is None:
        print(f"Skipping {strategy_name} - strategy has fixed daily rebalancing")
        return None
    
    results = []
    
    # Test each rebalance value
    for rebalance_value in config['test_values']:
        metrics = run_backtest(strategy_name, config, rebalance_value)
        
        if metrics is not None:
            metrics['strategy'] = strategy_name
            results.append(metrics)
    
    if len(results) == 0:
        print(f"WARNING: No successful runs for {strategy_name}")
        return None
    
    results_df = pd.DataFrame(results)
    
    # Find optimal values
    if not results_df['sharpe_ratio'].isna().all():
        best_sharpe_idx = results_df['sharpe_ratio'].idxmax()
        print(f"\n{'='*80}")
        print(f"OPTIMAL PARAMETERS FOR {strategy_name.upper()}")
        print(f"{'='*80}")
        print(f"Best Sharpe Ratio: {results_df.loc[best_sharpe_idx, 'sharpe_ratio']:.3f} "
              f"at {results_df.loc[best_sharpe_idx, 'rebalance_days']:.0f} days")
        
        if not results_df['calmar_ratio'].isna().all():
            best_calmar_idx = results_df['calmar_ratio'].idxmax()
            print(f"Best Calmar Ratio: {results_df.loc[best_calmar_idx, 'calmar_ratio']:.3f} "
                  f"at {results_df.loc[best_calmar_idx, 'rebalance_days']:.0f} days")
        
        if not results_df['annualized_return'].isna().all():
            best_return_idx = results_df['annualized_return'].idxmax()
            print(f"Best Ann. Return: {results_df.loc[best_return_idx, 'annualized_return']*100:.2f}% "
                  f"at {results_df.loc[best_return_idx, 'rebalance_days']:.0f} days")
    
    return results_df


def generate_summary_report(all_results):
    """
    Generate a comprehensive summary report of optimization results.
    
    Args:
        all_results (dict): Dictionary mapping strategy names to results DataFrames
    """
    print(f"\n\n{'#'*80}")
    print(f"# OPTIMIZATION SUMMARY - ALL STRATEGIES")
    print(f"{'#'*80}\n")
    
    summary_data = []
    
    for strategy_name, results_df in all_results.items():
        if results_df is None or results_df.empty:
            continue
        
        # Find best parameters
        if not results_df['sharpe_ratio'].isna().all():
            best_sharpe_idx = results_df['sharpe_ratio'].idxmax()
            best_row = results_df.loc[best_sharpe_idx]
            
            current_default = BACKTESTS[strategy_name]['default_value']
            default_row = results_df[results_df['rebalance_days'] == current_default]
            
            if len(default_row) > 0:
                default_sharpe = default_row['sharpe_ratio'].iloc[0]
            else:
                default_sharpe = np.nan
            
            summary_data.append({
                'Strategy': strategy_name,
                'Current Default (days)': current_default,
                'Default Sharpe': f"{default_sharpe:.3f}" if not np.isnan(default_sharpe) else 'N/A',
                'Optimal Rebalance (days)': int(best_row['rebalance_days']),
                'Optimal Sharpe': f"{best_row['sharpe_ratio']:.3f}",
                'Optimal Return': f"{best_row['annualized_return']*100:.2f}%",
                'Optimal Max DD': f"{best_row['max_drawdown']*100:.2f}%",
                'Optimal Calmar': f"{best_row['calmar_ratio']:.3f}" if not np.isnan(best_row['calmar_ratio']) else 'N/A',
                'Sharpe Improvement': f"{((best_row['sharpe_ratio'] - default_sharpe) / abs(default_sharpe) * 100):.1f}%" 
                                     if not np.isnan(default_sharpe) and default_sharpe != 0 else 'N/A'
            })
    
    if len(summary_data) > 0:
        summary_df = pd.DataFrame(summary_data)
        print(summary_df.to_string(index=False))
        
        # Save summary
        output_file = 'backtests/results/rebalance_optimization_summary.csv'
        summary_df.to_csv(output_file, index=False)
        print(f"\n✓ Summary saved to: {output_file}")
    
    # Save detailed results
    for strategy_name, results_df in all_results.items():
        if results_df is not None and not results_df.empty:
            output_file = f'backtests/results/rebalance_optimization_{strategy_name}.csv'
            results_df.to_csv(output_file, index=False)
            print(f"✓ Detailed results for {strategy_name} saved to: {output_file}")


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Optimize rebalance parameters for all backtest strategies',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--strategies',
        type=str,
        nargs='+',
        default=None,
        choices=list(BACKTESTS.keys()) + ['all'],
        help='Strategies to optimize (default: all)'
    )
    parser.add_argument(
        '--rebalance-values',
        type=int,
        nargs='+',
        default=None,
        help='Custom rebalance values to test (e.g., 1 3 7 14 30)'
    )
    
    args = parser.parse_args()
    
    # Determine which strategies to run
    if args.strategies is None or 'all' in args.strategies:
        strategies_to_run = list(BACKTESTS.keys())
    else:
        strategies_to_run = args.strategies
    
    # Override test values if specified
    if args.rebalance_values:
        for strategy in strategies_to_run:
            if BACKTESTS[strategy]['test_values'] is not None:
                BACKTESTS[strategy]['test_values'] = args.rebalance_values
    
    print("="*80)
    print("REBALANCE PARAMETER OPTIMIZATION")
    print("="*80)
    print(f"\nStrategies to optimize: {', '.join(strategies_to_run)}")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run optimization for each strategy
    all_results = {}
    
    for strategy_name in strategies_to_run:
        config = BACKTESTS[strategy_name]
        results_df = optimize_strategy(strategy_name, config)
        all_results[strategy_name] = results_df
    
    # Generate summary report
    generate_summary_report(all_results)
    
    print(f"\n{'='*80}")
    print(f"OPTIMIZATION COMPLETE")
    print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
