#!/usr/bin/env python3
"""
Backtest Trendline Breakout Strategy - Rebalance Period Analysis

This script runs the trendline breakout backtest with different rebalance periods
to analyze the impact of rebalancing frequency on strategy performance.

Rebalance periods tested: [1, 2, 3, 5, 7, 10, 30] days
"""

import pandas as pd
import numpy as np
import sys
import os
import argparse
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from backtests.scripts.backtest_trendline_breakout import (
    load_data,
    run_backtest,
    save_results,
    print_results
)


def run_rebalance_period_analysis(
    data,
    rebalance_periods=[1, 2, 3, 5, 7, 10, 30],
    output_dir='backtests/results',
    **backtest_kwargs
):
    """
    Run backtests with different rebalance periods.
    
    Args:
        data (pd.DataFrame): Historical price data
        rebalance_periods (list): List of rebalance periods to test
        output_dir (str): Output directory for results
        **backtest_kwargs: Additional arguments to pass to run_backtest
    
    Returns:
        dict: Dictionary with results for each rebalance period
    """
    results_by_period = {}
    
    print("=" * 80)
    print("TRENDLINE BREAKOUT - REBALANCE PERIOD ANALYSIS")
    print("=" * 80)
    print(f"\nTesting rebalance periods: {rebalance_periods}")
    print(f"Output directory: {output_dir}")
    print("\n" + "=" * 80)
    
    for rebalance_days in rebalance_periods:
        print(f"\n{'=' * 80}")
        print(f"TESTING REBALANCE PERIOD: {rebalance_days} DAYS")
        print(f"{'=' * 80}\n")
        
        try:
            # Run backtest with this rebalance period
            results = run_backtest(
                data=data,
                rebalance_days=rebalance_days,
                **backtest_kwargs
            )
            
            # Print results
            print_results(results)
            
            # Save results with rebalance period suffix
            output_prefix = os.path.join(
                output_dir,
                f'backtest_trendline_breakout_rebalance_{rebalance_days}d'
            )
            save_results(results, output_prefix)
            
            # Store results
            results_by_period[rebalance_days] = results
            
            print(f"\n✓ Completed backtest for {rebalance_days}-day rebalance period")
            
        except Exception as e:
            print(f"\n✗ Error running backtest for {rebalance_days}-day period: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    return results_by_period


def generate_comparison_summary(results_by_period, output_dir='backtests/results'):
    """
    Generate a summary comparing all rebalance periods.
    
    Args:
        results_by_period (dict): Dictionary with results for each period
        output_dir (str): Output directory for summary
    """
    if not results_by_period:
        print("\nNo results to summarize.")
        return
    
    print("\n" + "=" * 80)
    print("REBALANCE PERIOD COMPARISON SUMMARY")
    print("=" * 80)
    
    # Collect metrics for all periods
    summary_data = []
    
    for rebalance_days, results in sorted(results_by_period.items()):
        metrics = results['metrics']
        strategy_info = results['strategy_info']
        
        summary_data.append({
            'rebalance_days': rebalance_days,
            'total_return': metrics['total_return'],
            'annualized_return': metrics['annualized_return'],
            'annualized_volatility': metrics['annualized_volatility'],
            'sharpe_ratio': metrics['sharpe_ratio'],
            'sortino_ratio': metrics['sortino_ratio'],
            'max_drawdown': metrics['max_drawdown'],
            'calmar_ratio': metrics['calmar_ratio'],
            'win_rate': metrics['win_rate'],
            'num_trades': metrics['num_trades'],
            'num_long_trades': metrics['num_long_trades'],
            'num_short_trades': metrics['num_short_trades'],
            'avg_positions': metrics['avg_positions'],
            'avg_r2': metrics['avg_r2'],
            'avg_breakout_z_score': metrics['avg_breakout_z_score'],
            'avg_signal_strength': metrics['avg_signal_strength'],
            'final_value': metrics['final_value'],
            'trading_days': metrics['trading_days']
        })
    
    # Create summary DataFrame
    summary_df = pd.DataFrame(summary_data)
    
    # Print summary table
    print("\nPerformance Metrics by Rebalance Period:")
    print("-" * 80)
    
    # Key metrics table
    print("\nReturns and Risk:")
    display_cols = ['rebalance_days', 'total_return', 'annualized_return', 
                    'annualized_volatility', 'sharpe_ratio', 'max_drawdown']
    print(summary_df[display_cols].to_string(index=False))
    
    print("\n\nRisk-Adjusted Metrics:")
    display_cols = ['rebalance_days', 'sharpe_ratio', 'sortino_ratio', 
                    'calmar_ratio', 'win_rate']
    print(summary_df[display_cols].to_string(index=False))
    
    print("\n\nTrading Statistics:")
    display_cols = ['rebalance_days', 'num_trades', 'num_long_trades', 
                    'num_short_trades', 'avg_positions']
    print(summary_df[display_cols].to_string(index=False))
    
    print("\n\nSignal Quality:")
    display_cols = ['rebalance_days', 'avg_r2', 'avg_breakout_z_score', 
                    'avg_signal_strength']
    print(summary_df[display_cols].to_string(index=False))
    
    # Find best performing periods
    print("\n" + "=" * 80)
    print("RANKINGS BY METRIC")
    print("=" * 80)
    
    metrics_to_rank = {
        'Total Return': ('total_return', False),
        'Sharpe Ratio': ('sharpe_ratio', False),
        'Sortino Ratio': ('sortino_ratio', False),
        'Calmar Ratio': ('calmar_ratio', False),
        'Win Rate': ('win_rate', False),
        'Max Drawdown': ('max_drawdown', True)  # True = lower is better
    }
    
    for metric_name, (metric_col, ascending) in metrics_to_rank.items():
        ranked = summary_df.nsmallest(3, metric_col) if ascending else summary_df.nlargest(3, metric_col)
        print(f"\n{metric_name}:")
        for idx, row in enumerate(ranked.itertuples(), 1):
            value = getattr(row, metric_col)
            if metric_col in ['total_return', 'annualized_return', 'annualized_volatility', 
                             'max_drawdown', 'win_rate']:
                print(f"  {idx}. {row.rebalance_days:>2}d: {value:>8.2%}")
            else:
                print(f"  {idx}. {row.rebalance_days:>2}d: {value:>8.2f}")
    
    # Save summary
    summary_file = os.path.join(output_dir, 'trendline_breakout_rebalance_period_summary.csv')
    summary_df.to_csv(summary_file, index=False)
    print(f"\n✓ Saved summary to: {summary_file}")
    
    # Generate equity curves comparison
    print("\n" + "=" * 80)
    print("GENERATING EQUITY CURVES")
    print("=" * 80)
    
    equity_curves = []
    for rebalance_days, results in sorted(results_by_period.items()):
        portfolio_df = results['portfolio_values'].copy()
        portfolio_df['rebalance_period'] = f'{rebalance_days}d'
        equity_curves.append(portfolio_df[['date', 'portfolio_value', 'rebalance_period']])
    
    if equity_curves:
        all_curves = pd.concat(equity_curves, ignore_index=True)
        equity_file = os.path.join(output_dir, 'trendline_breakout_rebalance_period_equity_curves.csv')
        all_curves.to_csv(equity_file, index=False)
        print(f"✓ Saved equity curves to: {equity_file}")
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Backtest trendline breakout with different rebalance periods'
    )
    
    # Data parameters
    parser.add_argument('--price-data', type=str,
                       default='data/raw/combined_coinbase_coinmarketcap_daily.csv',
                       help='Path to historical OHLCV CSV file')
    
    # Rebalance periods to test
    parser.add_argument('--rebalance-periods', type=int, nargs='+',
                       default=[1, 2, 3, 5, 7, 10, 30],
                       help='Rebalance periods to test (in days)')
    
    # Trendline parameters
    parser.add_argument('--trendline-window', type=int, default=30,
                       help='Trendline calculation window in days')
    parser.add_argument('--volatility-window', type=int, default=30,
                       help='Volatility window for breakout normalization')
    parser.add_argument('--breakout-threshold', type=float, default=1.5,
                       help='Z-score threshold for breakout signal')
    parser.add_argument('--min-r2', type=float, default=0.5,
                       help='Minimum R² for clean trendline')
    parser.add_argument('--max-pvalue', type=float, default=0.05,
                       help='Maximum p-value for significant trendline')
    parser.add_argument('--slope-direction', type=str, default='any',
                       choices=['positive', 'negative', 'any'],
                       help='Required slope direction for breakout')
    
    # Portfolio parameters
    parser.add_argument('--max-positions', type=int, default=10,
                       help='Maximum positions per side')
    parser.add_argument('--holding-period', type=int, default=5,
                       help='Days to hold each signal')
    parser.add_argument('--weighting-method', type=str, default='equal_weight',
                       choices=['equal_weight', 'signal_weighted', 'risk_parity'],
                       help='Position weighting method')
    
    # Capital and leverage
    parser.add_argument('--initial-capital', type=float, default=10000,
                       help='Initial capital in USD')
    parser.add_argument('--leverage', type=float, default=1.0,
                       help='Leverage multiplier')
    parser.add_argument('--long-allocation', type=float, default=0.5,
                       help='Allocation to long side')
    parser.add_argument('--short-allocation', type=float, default=0.5,
                       help='Allocation to short side')
    
    # Universe filters
    parser.add_argument('--min-volume', type=float, default=5_000_000,
                       help='Minimum 30-day average volume in USD')
    parser.add_argument('--min-market-cap', type=float, default=50_000_000,
                       help='Minimum market cap in USD')
    
    # Date range
    parser.add_argument('--start-date', type=str, default=None,
                       help='Backtest start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default=None,
                       help='Backtest end date (YYYY-MM-DD)')
    
    # Output
    parser.add_argument('--output-dir', type=str,
                       default='backtests/results',
                       help='Output directory for results')
    
    args = parser.parse_args()
    
    # Load data
    print(f"\nLoading data from: {args.price_data}")
    data = load_data(args.price_data)
    print(f"Loaded {len(data)} data points for {data['symbol'].nunique()} symbols")
    print(f"Date range: {data['date'].min().date()} to {data['date'].max().date()}")
    
    # Prepare backtest kwargs
    backtest_kwargs = {
        'trendline_window': args.trendline_window,
        'volatility_window': args.volatility_window,
        'breakout_threshold': args.breakout_threshold,
        'min_r2': args.min_r2,
        'max_pvalue': args.max_pvalue,
        'slope_direction': args.slope_direction,
        'max_positions': args.max_positions,
        'holding_period': args.holding_period,
        'weighting_method': args.weighting_method,
        'initial_capital': args.initial_capital,
        'leverage': args.leverage,
        'long_allocation': args.long_allocation,
        'short_allocation': args.short_allocation,
        'min_volume': args.min_volume,
        'min_market_cap': args.min_market_cap,
        'start_date': args.start_date,
        'end_date': args.end_date
    }
    
    # Run analysis
    results_by_period = run_rebalance_period_analysis(
        data=data,
        rebalance_periods=args.rebalance_periods,
        output_dir=args.output_dir,
        **backtest_kwargs
    )
    
    # Generate comparison summary
    generate_comparison_summary(results_by_period, output_dir=args.output_dir)
    
    print("\n" + "=" * 80)
    print("ALL BACKTESTS COMPLETE")
    print("=" * 80)
    print(f"\nResults saved to: {args.output_dir}")


if __name__ == '__main__':
    main()
