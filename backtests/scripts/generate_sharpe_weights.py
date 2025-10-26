"""
Generate Strategy Weights Based on Sharpe Ratios

This script reads backtest results and generates portfolio weights for each
strategy based on their Sharpe ratios. Only strategies with positive Sharpe
ratios are included, and weights are normalized to sum to 1.0.
"""

import pandas as pd
import numpy as np
import argparse
import os


def calculate_sharpe_weights(backtest_results_file, output_file=None):
    """
    Calculate portfolio weights based on Sharpe ratios.
    
    Args:
        backtest_results_file (str): Path to backtest results CSV
        output_file (str): Path to save weights CSV (optional)
        
    Returns:
        pd.DataFrame: DataFrame with strategies and their weights
    """
    # Load backtest results
    results = pd.read_csv(backtest_results_file)
    
    print("="*80)
    print("GENERATING SHARPE-BASED PORTFOLIO WEIGHTS")
    print("="*80)
    print(f"\nInput file: {backtest_results_file}")
    print(f"\nLoaded {len(results)} strategies")
    
    # Display all strategies and their Sharpe ratios
    print("\nAll Strategies:")
    print("-"*80)
    for idx, row in results.iterrows():
        print(f"  {row['Strategy']:<20} | Sharpe: {row['Sharpe Ratio']:>8.3f} | Return: {row['Avg Return']:>8.2%}")
    
    # Filter for positive Sharpe ratios
    positive_sharpe = results[results['Sharpe Ratio'] > 0].copy()
    
    print(f"\nStrategies with positive Sharpe ratios: {len(positive_sharpe)}")
    
    if len(positive_sharpe) == 0:
        print("\nWARNING: No strategies have positive Sharpe ratios!")
        print("Cannot generate weights. Consider adjusting strategy parameters.")
        return None
    
    # Calculate weights proportional to Sharpe ratios
    total_sharpe = positive_sharpe['Sharpe Ratio'].sum()
    positive_sharpe['Weight'] = positive_sharpe['Sharpe Ratio'] / total_sharpe
    
    # Create output DataFrame
    weights_df = positive_sharpe[['Strategy', 'Description', 'Sharpe Ratio', 'Weight']].copy()
    weights_df['Weight_Pct'] = weights_df['Weight'] * 100
    
    # Verify weights sum to 1
    weight_sum = weights_df['Weight'].sum()
    
    print("\n" + "="*80)
    print("SHARPE-BASED PORTFOLIO WEIGHTS")
    print("="*80)
    print(f"\nWeighting Method: Proportional to Sharpe Ratio")
    print(f"Strategies included: {len(weights_df)}")
    print(f"Total weight: {weight_sum:.6f} (should be 1.0)")
    
    print("\nPortfolio Allocation:")
    print("-"*80)
    for idx, row in weights_df.iterrows():
        print(f"  {row['Strategy']:<20} | Sharpe: {row['Sharpe Ratio']:>8.3f} | Weight: {row['Weight']:>8.4f} ({row['Weight_Pct']:>6.2f}%)")
    
    print("\n" + "-"*80)
    print(f"  {'TOTAL':<20} | {'':>8} | Weight: {weight_sum:>8.4f} ({weight_sum*100:>6.2f}%)")
    print("="*80)
    
    # Calculate expected portfolio metrics (weighted average)
    expected_return = (positive_sharpe['Avg Return'] * weights_df['Weight']).sum()
    expected_sharpe = (positive_sharpe['Sharpe Ratio'] * weights_df['Weight']).sum()
    expected_sortino = (positive_sharpe['Sortino Ratio'] * weights_df['Weight']).sum()
    expected_max_dd = (positive_sharpe['Max Drawdown'] * weights_df['Weight']).sum()
    
    print("\nExpected Portfolio Metrics (Weighted Average):")
    print("-"*80)
    print(f"  Expected Return:        {expected_return:>8.2%}")
    print(f"  Expected Sharpe Ratio:  {expected_sharpe:>8.3f}")
    print(f"  Expected Sortino Ratio: {expected_sortino:>8.3f}")
    print(f"  Expected Max Drawdown:  {expected_max_dd:>8.2%}")
    print("="*80)
    
    # Save to file if specified
    if output_file:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        weights_df.to_csv(output_file, index=False)
        print(f"\nWeights saved to: {output_file}")
    
    return weights_df


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Generate portfolio weights based on Sharpe ratios',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--input-file',
        type=str,
        default='backtests/results/all_backtests_summary_2024.csv',
        help='Path to backtest results CSV file'
    )
    parser.add_argument(
        '--output-file',
        type=str,
        default='backtests/results/sharpe_weights_2024.csv',
        help='Output file for weights CSV'
    )
    
    args = parser.parse_args()
    
    # Calculate weights
    weights = calculate_sharpe_weights(args.input_file, args.output_file)
    
    if weights is not None:
        print("\n✓ Weight generation complete!")
    else:
        print("\n✗ Weight generation failed")


if __name__ == "__main__":
    main()
