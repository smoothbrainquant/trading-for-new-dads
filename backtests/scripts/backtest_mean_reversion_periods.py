"""
Backtest Mean Reversion Strategy with Multiple Period Comparisons

This script tests mean reversion strategies using z-scores for price moves and volume
across different lookback periods: 1, 2, 3, 5, 10, 20, 30 days.

For each period, we:
1. Calculate z-scores for N-day percentage price changes
2. Calculate z-scores for N-day volume changes
3. Test mean reversion signals (buy extreme negative z-scores, expect reversion)
4. Compare performance metrics across all periods

OPTIMAL CONFIGURATION (from comprehensive analysis):
- Lookback Period: 2 days (or 10 days as secondary)
- Return Threshold: z-score < -1.5
- Volume Threshold: |z-score| >= 1.0 (high volume filter CRITICAL)
- Direction: LONG ONLY (shorting rallies loses money)
- Expected Performance: 1.25% next-day return, 3.14 Sharpe, 59.2% win rate

See DIRECTIONAL_MEAN_REVERSION_SUMMARY.md for complete analysis.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse


def load_data(filepath):
    """
    Load historical OHLCV data from CSV file.
    
    Args:
        filepath (str): Path to CSV file with OHLCV data
        
    Returns:
        pd.DataFrame: DataFrame with date, symbol, open, high, low, close, volume
    """
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    return df


def calculate_period_returns(data, periods):
    """
    Calculate N-day returns and volume changes for multiple periods.
    
    Args:
        data (pd.DataFrame): Historical OHLCV data
        periods (list): List of periods to calculate (e.g., [1, 2, 3, 5, 10, 20, 30])
        
    Returns:
        pd.DataFrame: Data with period returns added
    """
    df = data.copy()
    
    for period in periods:
        # Calculate N-day percentage returns
        df[f'return_{period}d'] = df.groupby('symbol')['close'].transform(
            lambda x: x.pct_change(periods=period)
        )
        
        # Calculate N-day volume change
        df[f'volume_change_{period}d'] = df.groupby('symbol')['volume'].transform(
            lambda x: x.pct_change(periods=period)
        )
    
    return df


def calculate_z_scores_for_period(data, period, zscore_lookback=30):
    """
    Calculate z-scores for a specific period's returns and volume changes.
    
    Args:
        data (pd.DataFrame): Data with period returns
        period (int): Period for which to calculate z-scores
        zscore_lookback (int): Lookback window for calculating rolling mean and std
        
    Returns:
        pd.DataFrame: Data with z-scores added
    """
    df = data.copy()
    
    return_col = f'return_{period}d'
    volume_col = f'volume_change_{period}d'
    
    # Calculate rolling mean and std for returns (shifted to avoid look-ahead bias)
    df[f'return_{period}d_mean'] = df.groupby('symbol')[return_col].transform(
        lambda x: x.rolling(window=zscore_lookback, min_periods=zscore_lookback).mean().shift(1)
    )
    df[f'return_{period}d_std'] = df.groupby('symbol')[return_col].transform(
        lambda x: x.rolling(window=zscore_lookback, min_periods=zscore_lookback).std().shift(1)
    )
    
    # Calculate rolling mean and std for volume (shifted to avoid look-ahead bias)
    df[f'volume_{period}d_mean'] = df.groupby('symbol')[volume_col].transform(
        lambda x: x.rolling(window=zscore_lookback, min_periods=zscore_lookback).mean().shift(1)
    )
    df[f'volume_{period}d_std'] = df.groupby('symbol')[volume_col].transform(
        lambda x: x.rolling(window=zscore_lookback, min_periods=zscore_lookback).std().shift(1)
    )
    
    # Calculate z-scores (no look-ahead bias)
    df[f'return_zscore_{period}d'] = (
        (df[return_col] - df[f'return_{period}d_mean']) / df[f'return_{period}d_std']
    )
    df[f'volume_zscore_{period}d'] = (
        (df[volume_col] - df[f'volume_{period}d_mean']) / df[f'volume_{period}d_std']
    )
    
    return df


def calculate_forward_returns(data):
    """
    Calculate forward returns for strategy evaluation.
    
    Args:
        data (pd.DataFrame): Data with signals
        
    Returns:
        pd.DataFrame: Data with forward returns added
    """
    df = data.copy()
    
    # Calculate 1-day return for immediate evaluation
    df['pct_change_1d'] = df.groupby('symbol')['close'].transform(lambda x: x.pct_change())
    
    # Forward 1-day return (next day's return) - shifted to avoid look-ahead bias
    df['forward_1d_return'] = df.groupby('symbol')['pct_change_1d'].shift(-1)
    
    # Forward 2-day cumulative return
    df['forward_2d_return'] = df.groupby('symbol')['close'].transform(
        lambda x: x.pct_change(periods=2).shift(-2)
    )
    
    # Forward 5-day cumulative return
    df['forward_5d_return'] = df.groupby('symbol')['close'].transform(
        lambda x: x.pct_change(periods=5).shift(-5)
    )
    
    return df


def generate_signals_for_period(data, period, return_threshold=-1.5, volume_threshold=1.0):
    """
    Generate mean reversion signals for a specific period.
    
    Mean reversion logic:
    - Buy when return z-score < -threshold (extreme negative move)
    - Optionally filter for high volume (volume z-score > volume_threshold)
    
    Args:
        data (pd.DataFrame): Data with z-scores
        period (int): Period for signal generation
        return_threshold (float): Z-score threshold for returns (negative value)
        volume_threshold (float): Z-score threshold for volume (positive value)
        
    Returns:
        pd.DataFrame: Data with signals added
    """
    df = data.copy()
    
    return_zscore_col = f'return_zscore_{period}d'
    volume_zscore_col = f'volume_zscore_{period}d'
    
    # Signal 1: Extreme negative move (any volume)
    df[f'signal_neg_move_{period}d'] = (df[return_zscore_col] < return_threshold).astype(int)
    
    # Signal 2: Extreme negative move + high volume
    df[f'signal_neg_move_high_vol_{period}d'] = (
        (df[return_zscore_col] < return_threshold) & 
        (df[volume_zscore_col].abs() > volume_threshold)
    ).astype(int)
    
    # Signal 3: Extreme negative move + low volume
    df[f'signal_neg_move_low_vol_{period}d'] = (
        (df[return_zscore_col] < return_threshold) & 
        (df[volume_zscore_col].abs() <= volume_threshold)
    ).astype(int)
    
    # Signal 4: Extreme positive move (for comparison - short signal)
    df[f'signal_pos_move_{period}d'] = (df[return_zscore_col] > -return_threshold).astype(int)
    
    return df


def analyze_signals_for_period(data, period):
    """
    Analyze signal performance for a specific period.
    
    Args:
        data (pd.DataFrame): Data with signals and forward returns
        period (int): Period to analyze
        
    Returns:
        dict: Performance metrics for each signal type
    """
    results = []
    
    # Define signal columns to analyze
    signal_types = [
        f'signal_neg_move_{period}d',
        f'signal_neg_move_high_vol_{period}d',
        f'signal_neg_move_low_vol_{period}d',
        f'signal_pos_move_{period}d'
    ]
    
    for signal_col in signal_types:
        # Get rows where signal is active
        signal_data = data[data[signal_col] == 1].copy()
        
        if len(signal_data) == 0:
            continue
        
        # Calculate metrics for different forward return periods
        for fwd_period, fwd_col in [
            ('1d', 'forward_1d_return'),
            ('2d', 'forward_2d_return'),
            ('5d', 'forward_5d_return')
        ]:
            valid_data = signal_data.dropna(subset=[fwd_col])
            
            if len(valid_data) == 0:
                continue
            
            mean_return = valid_data[fwd_col].mean()
            median_return = valid_data[fwd_col].median()
            std_return = valid_data[fwd_col].std()
            win_rate = (valid_data[fwd_col] > 0).sum() / len(valid_data) * 100
            
            # Annualized Sharpe ratio
            if fwd_period == '1d':
                annualization_factor = np.sqrt(365)
            elif fwd_period == '2d':
                annualization_factor = np.sqrt(365/2)
            else:  # 5d
                annualization_factor = np.sqrt(365/5)
            
            sharpe = (mean_return / std_return * annualization_factor) if std_return > 0 else 0
            
            results.append({
                'period': period,
                'signal_type': signal_col.replace(f'_{period}d', ''),
                'forward_period': fwd_period,
                'count': len(valid_data),
                'mean_return': mean_return,
                'median_return': median_return,
                'std_return': std_return,
                'win_rate_pct': win_rate,
                'sharpe_ratio': sharpe
            })
    
    return results


def run_period_comparison(data, periods, zscore_lookback=30, return_threshold=-1.5, volume_threshold=1.0):
    """
    Run complete analysis comparing all periods.
    
    Args:
        data (pd.DataFrame): Historical OHLCV data
        periods (list): List of periods to test
        zscore_lookback (int): Lookback for calculating z-scores
        return_threshold (float): Z-score threshold for returns
        volume_threshold (float): Z-score threshold for volume
        
    Returns:
        pd.DataFrame: Comprehensive results comparing all periods
    """
    print("\nCalculating returns for all periods...")
    df = calculate_period_returns(data, periods)
    
    print("Calculating forward returns...")
    df = calculate_forward_returns(df)
    
    all_results = []
    
    for period in periods:
        print(f"Processing {period}d period...")
        
        # Calculate z-scores for this period
        df = calculate_z_scores_for_period(df, period, zscore_lookback)
        
        # Generate signals
        df = generate_signals_for_period(df, period, return_threshold, volume_threshold)
        
        # Analyze signals
        period_results = analyze_signals_for_period(df, period)
        all_results.extend(period_results)
    
    results_df = pd.DataFrame(all_results)
    
    # Replace inf values with NaN
    results_df = results_df.replace([np.inf, -np.inf], np.nan)
    
    return results_df, df


def print_summary_results(results_df):
    """
    Print summary of results in a formatted manner.
    
    Args:
        results_df (pd.DataFrame): Results from period comparison
    """
    print("\n" + "=" * 120)
    print("MEAN REVERSION STRATEGY - PERIOD COMPARISON SUMMARY")
    print("=" * 120)
    
    # Focus on negative move signals (main mean reversion signals)
    neg_signals = results_df[results_df['signal_type'].str.contains('signal_neg_move')]
    
    if neg_signals.empty:
        print("No results found.")
        return
    
    # Show results by forward period
    for fwd_period in ['1d', '2d', '5d']:
        print(f"\n{'=' * 120}")
        print(f"FORWARD {fwd_period.upper()} RETURNS")
        print('=' * 120)
        
        period_data = neg_signals[neg_signals['forward_period'] == fwd_period].copy()
        
        if period_data.empty:
            continue
        
        # Sort by mean return (descending)
        period_data = period_data.sort_values('mean_return', ascending=False)
        
        print("\nMean Reversion Signals (sorted by mean return):")
        print(period_data.to_string(index=False))
        
        # Find best period for each signal type
        print(f"\n{'=' * 120}")
        print(f"BEST PERIOD BY SIGNAL TYPE (Forward {fwd_period.upper()}):")
        print('=' * 120)
        
        for signal_type in period_data['signal_type'].unique():
            signal_data = period_data[period_data['signal_type'] == signal_type]
            best = signal_data.loc[signal_data['mean_return'].idxmax()]
            
            print(f"\n{signal_type}:")
            print(f"  Best period: {best['period']}d")
            print(f"  Mean return: {best['mean_return']:.4%}")
            print(f"  Win rate: {best['win_rate_pct']:.1f}%")
            print(f"  Sharpe ratio: {best['sharpe_ratio']:.2f}")
            print(f"  Count: {best['count']:.0f}")
    
    print("\n" + "=" * 120)


def print_detailed_analysis(results_df):
    """
    Print detailed analysis for specific signal types.
    
    Args:
        results_df (pd.DataFrame): Results from period comparison
    """
    print("\n" + "=" * 120)
    print("DETAILED ANALYSIS: SIGNAL TYPE COMPARISON")
    print("=" * 120)
    
    # Compare signal types for 1d forward returns
    fwd_1d = results_df[results_df['forward_period'] == '1d'].copy()
    
    if fwd_1d.empty:
        return
    
    print("\nComparison across periods (Forward 1d returns):")
    
    # Pivot table for easier comparison
    pivot = fwd_1d.pivot_table(
        index='period',
        columns='signal_type',
        values='mean_return',
        aggfunc='first'
    )
    
    print("\nMean Returns by Period and Signal Type:")
    print(pivot.to_string())
    
    pivot_sharpe = fwd_1d.pivot_table(
        index='period',
        columns='signal_type',
        values='sharpe_ratio',
        aggfunc='first'
    )
    
    print("\nSharpe Ratios by Period and Signal Type:")
    print(pivot_sharpe.to_string())
    
    pivot_count = fwd_1d.pivot_table(
        index='period',
        columns='signal_type',
        values='count',
        aggfunc='first'
    )
    
    print("\nSignal Counts by Period and Signal Type:")
    print(pivot_count.to_string())


def save_results(results_df, detailed_data, output_prefix='backtest_mean_reversion_periods'):
    """
    Save analysis results to CSV files.
    
    Args:
        results_df (pd.DataFrame): Summary results
        detailed_data (pd.DataFrame): Detailed data with all calculations
        output_prefix (str): Prefix for output filenames
    """
    # Save summary results
    summary_file = f"{output_prefix}_summary.csv"
    results_df.to_csv(summary_file, index=False)
    print(f"\nSummary results saved to: {summary_file}")
    
    # Save detailed data (select relevant columns only to reduce file size)
    relevant_cols = ['date', 'symbol', 'close', 'volume']
    
    # Add period return columns
    period_cols = [col for col in detailed_data.columns if 'return_' in col or 'volume_' in col or 'signal_' in col or 'forward_' in col]
    relevant_cols.extend(period_cols)
    
    # Filter to only existing columns
    relevant_cols = [col for col in relevant_cols if col in detailed_data.columns]
    
    detailed_file = f"{output_prefix}_detailed.csv"
    detailed_data[relevant_cols].to_csv(detailed_file, index=False)
    print(f"Detailed data saved to: {detailed_file}")


def main():
    """Main execution function for backtest."""
    parser = argparse.ArgumentParser(
        description='Backtest Mean Reversion with Multiple Period Comparisons',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--data-file',
        type=str,
        default='combined_coinbase_coinmarketcap_daily.csv',
        help='Path to historical OHLCV data CSV file'
    )
    parser.add_argument(
        '--periods',
        type=str,
        default='2,10',
        help='Comma-separated list of periods to test (default: "2,10" optimal, full: "1,2,3,5,10,20,30")'
    )
    parser.add_argument(
        '--zscore-lookback',
        type=int,
        default=30,
        help='Lookback window for calculating z-scores'
    )
    parser.add_argument(
        '--return-threshold',
        type=float,
        default=-1.5,
        help='Z-score threshold for returns (use negative value, optimal: -1.5)'
    )
    parser.add_argument(
        '--volume-threshold',
        type=float,
        default=1.0,
        help='Z-score threshold for volume (optimal: 1.0 for high volume filter)'
    )
    parser.add_argument(
        '--output-prefix',
        type=str,
        default='backtest_mean_reversion_periods',
        help='Prefix for output CSV files'
    )
    
    args = parser.parse_args()
    
    # Parse periods
    periods = [int(p.strip()) for p in args.periods.split(',')]
    
    print("=" * 120)
    print("BACKTEST: Mean Reversion Strategy - Period Comparison")
    print("=" * 120)
    print(f"\nConfiguration:")
    print(f"  Data file: {args.data_file}")
    print(f"  Periods to test: {periods}")
    print(f"  Z-score lookback: {args.zscore_lookback} days")
    print(f"  Return threshold: {args.return_threshold} std devs")
    print(f"  Volume threshold: {args.volume_threshold} std devs")
    print("=" * 120)
    
    # Load data
    print("\nLoading data...")
    data = load_data(args.data_file)
    print(f"Loaded {len(data)} rows for {data['symbol'].nunique()} symbols")
    print(f"Date range: {data['date'].min().date()} to {data['date'].max().date()}")
    
    # Run period comparison
    print("\nRunning period comparison analysis...")
    results_df, detailed_data = run_period_comparison(
        data,
        periods,
        zscore_lookback=args.zscore_lookback,
        return_threshold=args.return_threshold,
        volume_threshold=args.volume_threshold
    )
    
    # Print results
    print_summary_results(results_df)
    print_detailed_analysis(results_df)
    
    # Save results
    save_results(results_df, detailed_data, output_prefix=args.output_prefix)
    
    print("\n" + "=" * 120)
    print("ANALYSIS COMPLETE")
    print("=" * 120)


if __name__ == "__main__":
    main()
