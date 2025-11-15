#!/usr/bin/env python3
"""
Hurst Exponent Analysis by Market Direction

This script analyzes Hurst exponent performance segmented by:
1. High vs Low Hurst Exponent
2. Up vs Down market directionality (5-day % change)

Produces detailed breakdown showing which regime favors mean-reversion vs trending.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../signals'))


def load_data(filepath):
    """Load historical OHLCV data from CSV file."""
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    required_cols = ['date', 'symbol', 'close']
    optional_cols = ['volume', 'market_cap', 'open', 'high', 'low']
    
    cols_to_keep = required_cols.copy()
    for col in optional_cols:
        if col in df.columns:
            cols_to_keep.append(col)
    
    df = df[cols_to_keep]
    return df


def calculate_hurst_rs(returns, min_points=20):
    """Calculate Hurst exponent using R/S (Rescaled Range) method."""
    returns = returns[~np.isnan(returns)]
    
    if len(returns) < min_points:
        return np.nan
    
    n = len(returns)
    max_lag = n // 2
    
    if max_lag < 4:
        return np.nan
    
    lags = np.unique(np.logspace(0.5, np.log10(max_lag), min(20, max_lag)).astype(int))
    lags = lags[lags >= 2]
    
    if len(lags) < 3:
        return np.nan
    
    rs_values = []
    valid_lags = []
    
    for lag in lags:
        n_chunks = len(returns) // lag
        
        if n_chunks < 1:
            continue
        
        rs_list = []
        for i in range(n_chunks):
            chunk = returns[i*lag:(i+1)*lag]
            
            if len(chunk) < lag:
                continue
            
            mean = np.mean(chunk)
            deviations = chunk - mean
            cumdev = np.cumsum(deviations)
            
            R = np.max(cumdev) - np.min(cumdev)
            S = np.std(chunk, ddof=1)
            
            if S > 1e-10 and R > 0:
                rs_list.append(R / S)
        
        if len(rs_list) > 0:
            rs_values.append(np.mean(rs_list))
            valid_lags.append(lag)
    
    if len(rs_values) < 3:
        return np.nan
    
    try:
        log_lags = np.log(valid_lags)
        log_rs = np.log(rs_values)
        
        mask = np.isfinite(log_lags) & np.isfinite(log_rs)
        if np.sum(mask) < 3:
            return np.nan
        
        log_lags = log_lags[mask]
        log_rs = log_rs[mask]
        
        hurst = np.polyfit(log_lags, log_rs, 1)[0]
        
        if hurst < 0 or hurst > 1:
            return np.nan
        
        return hurst
        
    except (np.linalg.LinAlgError, ValueError):
        return np.nan


def calculate_rolling_hurst(data, window=90, min_periods=60):
    """Calculate rolling Hurst exponent for each cryptocurrency."""
    df = data.copy()
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Calculate daily log returns
    df['daily_return'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Calculate rolling Hurst exponent
    def rolling_hurst_series(returns_series):
        """Calculate rolling Hurst for a single coin's returns"""
        hurst_values = []
        
        for i in range(len(returns_series)):
            if i < min_periods:
                hurst_values.append(np.nan)
            else:
                start_idx = max(0, i - window + 1)
                window_returns = returns_series.iloc[start_idx:i+1].values
                hurst = calculate_hurst_rs(window_returns, min_points=min_periods)
                hurst_values.append(hurst)
        
        return pd.Series(hurst_values, index=returns_series.index)
    
    print("  Calculating rolling Hurst exponents...")
    df['hurst'] = df.groupby('symbol', group_keys=False)['daily_return'].apply(
        rolling_hurst_series
    )
    
    return df


def get_top_n_by_market_cap(data, n=100, date=None):
    """
    Get top N coins by market cap on a specific date or overall average.
    
    Args:
        data (pd.DataFrame): DataFrame with market_cap column
        n (int): Number of top coins to select
        date (pd.Timestamp): Specific date to filter by, or None for overall average
        
    Returns:
        list: List of top N symbols
    """
    if 'market_cap' not in data.columns:
        print("  Warning: No market_cap column, using all coins")
        return data['symbol'].unique().tolist()
    
    if date is not None:
        # Get top N on specific date
        date_data = data[data['date'] == date].copy()
        if date_data.empty:
            return []
        top_symbols = date_data.nlargest(n, 'market_cap')['symbol'].tolist()
    else:
        # Get top N by average market cap over entire period
        avg_market_cap = data.groupby('symbol')['market_cap'].mean().sort_values(ascending=False)
        top_symbols = avg_market_cap.head(n).index.tolist()
    
    return top_symbols


def analyze_hurst_by_direction(data, hurst_window=90, forward_window=5, 
                                top_n=100, start_date=None, end_date=None):
    """
    Analyze Hurst exponent performance by market direction.
    
    Args:
        data (pd.DataFrame): Historical OHLCV data
        hurst_window (int): Window for Hurst calculation
        forward_window (int): Forward window for returns (5 days)
        top_n (int): Number of top market cap coins
        start_date (str): Analysis start date
        end_date (str): Analysis end date
        
    Returns:
        dict: Analysis results
    """
    print("=" * 80)
    print("HURST EXPONENT ANALYSIS BY MARKET DIRECTION")
    print("=" * 80)
    print(f"\nParameters:")
    print(f"  Top N Coins: {top_n}")
    print(f"  Hurst Window: {hurst_window} days")
    print(f"  Forward Window: {forward_window} days (directional signal)")
    print(f"  Period: {start_date or 'earliest'} to {end_date or 'latest'}")
    
    # Step 1: Calculate Hurst exponents
    print("\n" + "-" * 80)
    print("Step 1: Calculating Hurst exponents...")
    min_periods = int(hurst_window * 0.7)
    hurst_data = calculate_rolling_hurst(data, window=hurst_window, min_periods=min_periods)
    
    # Step 2: Filter to top N coins by market cap
    print("\n" + "-" * 80)
    print("Step 2: Filtering to top market cap coins...")
    top_symbols = get_top_n_by_market_cap(hurst_data, n=top_n)
    print(f"  Top {top_n} coins selected: {len(top_symbols)} symbols")
    hurst_data = hurst_data[hurst_data['symbol'].isin(top_symbols)]
    
    # Step 3: Calculate forward returns
    print("\n" + "-" * 80)
    print("Step 3: Calculating forward returns...")
    hurst_data['forward_return'] = hurst_data.groupby('symbol')['close'].transform(
        lambda x: (x.shift(-forward_window) / x - 1)
    )
    
    # Also calculate 5-day percentage change for directional classification
    hurst_data['pct_change_5d'] = hurst_data.groupby('symbol')['close'].transform(
        lambda x: (x / x.shift(forward_window) - 1)
    )
    
    # Step 4: Filter by date range
    if start_date:
        hurst_data = hurst_data[hurst_data['date'] >= pd.to_datetime(start_date)]
    if end_date:
        hurst_data = hurst_data[hurst_data['date'] <= pd.to_datetime(end_date)]
    
    # Step 5: Clean data - remove NaN values
    print("\n" + "-" * 80)
    print("Step 4: Cleaning data...")
    print(f"  Rows before cleaning: {len(hurst_data)}")
    
    analysis_data = hurst_data[
        hurst_data['hurst'].notna() & 
        hurst_data['forward_return'].notna() &
        hurst_data['pct_change_5d'].notna() &
        (hurst_data['hurst'] >= 0) & 
        (hurst_data['hurst'] <= 1)
    ].copy()
    
    print(f"  Rows after cleaning: {len(analysis_data)}")
    print(f"  Unique coins: {analysis_data['symbol'].nunique()}")
    print(f"  Date range: {analysis_data['date'].min().date()} to {analysis_data['date'].max().date()}")
    
    if analysis_data.empty:
        print("\n  ERROR: No valid data for analysis!")
        return None
    
    # Step 6: Classify by Hurst (high/low) and Direction (up/down)
    print("\n" + "-" * 80)
    print("Step 5: Classifying data...")
    
    # Classify Hurst: above/below median
    hurst_median = analysis_data['hurst'].median()
    analysis_data['hurst_class'] = np.where(
        analysis_data['hurst'] >= hurst_median,
        'High HE',
        'Low HE'
    )
    
    # Classify Direction: up/down based on past 5-day change
    analysis_data['direction_class'] = np.where(
        analysis_data['pct_change_5d'] >= 0,
        'Up',
        'Down'
    )
    
    # Create combined classification
    analysis_data['segment'] = (
        analysis_data['hurst_class'] + ' / ' + analysis_data['direction_class']
    )
    
    print(f"  Hurst median: {hurst_median:.3f}")
    print(f"  Hurst range: [{analysis_data['hurst'].min():.3f}, {analysis_data['hurst'].max():.3f}]")
    print(f"\n  Segment distribution:")
    print(analysis_data['segment'].value_counts().sort_index())
    
    # Step 7: Calculate performance by segment
    print("\n" + "-" * 80)
    print("Step 6: Calculating performance metrics...")
    
    results = {}
    
    for segment in analysis_data['segment'].unique():
        segment_data = analysis_data[analysis_data['segment'] == segment]
        
        # Calculate metrics
        mean_return = segment_data['forward_return'].mean()
        median_return = segment_data['forward_return'].median()
        std_return = segment_data['forward_return'].std()
        sharpe = (mean_return / std_return) * np.sqrt(252/forward_window) if std_return > 0 else 0
        
        win_rate = (segment_data['forward_return'] > 0).sum() / len(segment_data)
        
        # Annualized metrics
        periods_per_year = 252 / forward_window
        annualized_return = (1 + mean_return) ** periods_per_year - 1
        annualized_vol = std_return * np.sqrt(periods_per_year)
        
        results[segment] = {
            'count': len(segment_data),
            'mean_return': mean_return,
            'median_return': median_return,
            'std_return': std_return,
            'annualized_return': annualized_return,
            'annualized_vol': annualized_vol,
            'sharpe_ratio': sharpe,
            'win_rate': win_rate,
            'avg_hurst': segment_data['hurst'].mean(),
            'unique_coins': segment_data['symbol'].nunique()
        }
    
    # Step 8: Calculate summary statistics
    print("\n" + "-" * 80)
    print("Step 7: Calculating summary statistics...")
    
    # By Hurst class only
    hurst_summary = {}
    for hurst_class in ['Low HE', 'High HE']:
        class_data = analysis_data[analysis_data['hurst_class'] == hurst_class]
        if not class_data.empty:
            mean_return = class_data['forward_return'].mean()
            std_return = class_data['forward_return'].std()
            periods_per_year = 252 / forward_window
            
            hurst_summary[hurst_class] = {
                'count': len(class_data),
                'mean_return': mean_return,
                'annualized_return': (1 + mean_return) ** periods_per_year - 1,
                'annualized_vol': std_return * np.sqrt(periods_per_year),
                'sharpe_ratio': (mean_return / std_return) * np.sqrt(periods_per_year) if std_return > 0 else 0,
                'win_rate': (class_data['forward_return'] > 0).sum() / len(class_data),
                'avg_hurst': class_data['hurst'].mean()
            }
    
    # By Direction only
    direction_summary = {}
    for direction in ['Up', 'Down']:
        dir_data = analysis_data[analysis_data['direction_class'] == direction]
        if not dir_data.empty:
            mean_return = dir_data['forward_return'].mean()
            std_return = dir_data['forward_return'].std()
            periods_per_year = 252 / forward_window
            
            direction_summary[direction] = {
                'count': len(dir_data),
                'mean_return': mean_return,
                'annualized_return': (1 + mean_return) ** periods_per_year - 1,
                'annualized_vol': std_return * np.sqrt(periods_per_year),
                'sharpe_ratio': (mean_return / std_return) * np.sqrt(periods_per_year) if std_return > 0 else 0,
                'win_rate': (dir_data['forward_return'] > 0).sum() / len(dir_data),
                'avg_5d_pct_change': dir_data['pct_change_5d'].mean()
            }
    
    return {
        'segment_results': results,
        'hurst_summary': hurst_summary,
        'direction_summary': direction_summary,
        'data': analysis_data,
        'hurst_median': hurst_median,
        'total_observations': len(analysis_data),
        'date_range': (analysis_data['date'].min(), analysis_data['date'].max())
    }


def print_results(results):
    """Print analysis results in formatted tables."""
    if results is None:
        print("\nNo results to display.")
        return
    
    print("\n" + "=" * 80)
    print("RESULTS: HURST EXPONENT BY MARKET DIRECTION")
    print("=" * 80)
    
    print(f"\nAnalysis Summary:")
    print(f"  Total Observations: {results['total_observations']:,}")
    print(f"  Date Range: {results['date_range'][0].date()} to {results['date_range'][1].date()}")
    print(f"  Hurst Median (cutoff): {results['hurst_median']:.3f}")
    
    # Segment Results (2x2 matrix)
    print("\n" + "=" * 80)
    print("SEGMENT BREAKDOWN (Hurst × Direction)")
    print("=" * 80)
    
    segments = ['Low HE / Up', 'Low HE / Down', 'High HE / Up', 'High HE / Down']
    
    print(f"\n{'Segment':<20} {'Count':>8} {'Avg Hurst':>10} {'Mean Ret':>10} "
          f"{'Ann. Ret':>10} {'Sharpe':>8} {'Win Rate':>10}")
    print("-" * 86)
    
    for segment in segments:
        if segment in results['segment_results']:
            r = results['segment_results'][segment]
            print(f"{segment:<20} {r['count']:>8,} {r['avg_hurst']:>10.3f} {r['mean_return']:>9.2%} "
                  f"{r['annualized_return']:>9.1%} {r['sharpe_ratio']:>8.2f} {r['win_rate']:>9.1%}")
    
    # Hurst Summary
    print("\n" + "=" * 80)
    print("HURST EXPONENT SUMMARY (Aggregated)")
    print("=" * 80)
    
    print(f"\n{'HE Class':<15} {'Count':>8} {'Avg Hurst':>10} {'Mean Ret':>10} "
          f"{'Ann. Ret':>10} {'Sharpe':>8} {'Win Rate':>10}")
    print("-" * 81)
    
    for he_class in ['Low HE', 'High HE']:
        if he_class in results['hurst_summary']:
            r = results['hurst_summary'][he_class]
            print(f"{he_class:<15} {r['count']:>8,} {r['avg_hurst']:>10.3f} {r['mean_return']:>9.2%} "
                  f"{r['annualized_return']:>9.1%} {r['sharpe_ratio']:>8.2f} {r['win_rate']:>9.1%}")
    
    # Direction Summary
    print("\n" + "=" * 80)
    print("MARKET DIRECTION SUMMARY (Aggregated)")
    print("=" * 80)
    
    print(f"\n{'Direction':<15} {'Count':>8} {'Avg 5d Chg':>11} {'Mean Ret':>10} "
          f"{'Ann. Ret':>10} {'Sharpe':>8} {'Win Rate':>10}")
    print("-" * 82)
    
    for direction in ['Up', 'Down']:
        if direction in results['direction_summary']:
            r = results['direction_summary'][direction]
            print(f"{direction:<15} {r['count']:>8,} {r['avg_5d_pct_change']:>10.2%} {r['mean_return']:>9.2%} "
                  f"{r['annualized_return']:>9.1%} {r['sharpe_ratio']:>8.2f} {r['win_rate']:>9.1%}")
    
    # Key Insights
    print("\n" + "=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)
    
    seg_results = results['segment_results']
    
    # Best/worst segments
    best_segment = max(seg_results.items(), key=lambda x: x[1]['annualized_return'])
    worst_segment = min(seg_results.items(), key=lambda x: x[1]['annualized_return'])
    
    print(f"\n1. Best Performing Segment:")
    print(f"   {best_segment[0]}: {best_segment[1]['annualized_return']:.1%} annualized return")
    print(f"   (Sharpe: {best_segment[1]['sharpe_ratio']:.2f}, Win Rate: {best_segment[1]['win_rate']:.1%})")
    
    print(f"\n2. Worst Performing Segment:")
    print(f"   {worst_segment[0]}: {worst_segment[1]['annualized_return']:.1%} annualized return")
    print(f"   (Sharpe: {worst_segment[1]['sharpe_ratio']:.2f}, Win Rate: {worst_segment[1]['win_rate']:.1%})")
    
    # Hurst effect
    he_summary = results['hurst_summary']
    if 'Low HE' in he_summary and 'High HE' in he_summary:
        low_he_ret = he_summary['Low HE']['annualized_return']
        high_he_ret = he_summary['High HE']['annualized_return']
        he_diff = low_he_ret - high_he_ret
        
        print(f"\n3. Hurst Exponent Effect:")
        print(f"   Low HE: {low_he_ret:.1%} annualized")
        print(f"   High HE: {high_he_ret:.1%} annualized")
        print(f"   Difference: {he_diff:.1%} (Low HE {'outperforms' if he_diff > 0 else 'underperforms'})")
    
    # Direction effect
    dir_summary = results['direction_summary']
    if 'Up' in dir_summary and 'Down' in dir_summary:
        up_ret = dir_summary['Up']['annualized_return']
        down_ret = dir_summary['Down']['annualized_return']
        dir_diff = up_ret - down_ret
        
        print(f"\n4. Market Direction Effect:")
        print(f"   Up Markets: {up_ret:.1%} annualized")
        print(f"   Down Markets: {down_ret:.1%} annualized")
        print(f"   Difference: {dir_diff:.1%}")
    
    # Interaction effects
    if all(seg in seg_results for seg in ['Low HE / Up', 'Low HE / Down', 'High HE / Up', 'High HE / Down']):
        print(f"\n5. Interaction Effects:")
        
        # Low HE in up vs down
        low_he_up = seg_results['Low HE / Up']['annualized_return']
        low_he_down = seg_results['Low HE / Down']['annualized_return']
        print(f"   Low HE - Up: {low_he_up:.1%} | Down: {low_he_down:.1%} | Diff: {low_he_up - low_he_down:.1%}")
        
        # High HE in up vs down
        high_he_up = seg_results['High HE / Up']['annualized_return']
        high_he_down = seg_results['High HE / Down']['annualized_return']
        print(f"   High HE - Up: {high_he_up:.1%} | Down: {high_he_down:.1%} | Diff: {high_he_up - high_he_down:.1%}")
        
        # Which does better in up markets?
        up_diff = low_he_up - high_he_up
        print(f"\n   In UP markets: {'Low HE' if up_diff > 0 else 'High HE'} outperforms by {abs(up_diff):.1%}")
        
        # Which does better in down markets?
        down_diff = low_he_down - high_he_down
        print(f"   In DOWN markets: {'Low HE' if down_diff > 0 else 'High HE'} outperforms by {abs(down_diff):.1%}")


def save_results(results, output_prefix):
    """Save analysis results to CSV files."""
    if results is None:
        print("\nNo results to save.")
        return
    
    output_dir = os.path.dirname(output_prefix) or '.'
    os.makedirs(output_dir, exist_ok=True)
    
    # Save segment results
    segment_file = f"{output_prefix}_segment_results.csv"
    segment_df = pd.DataFrame(results['segment_results']).T
    segment_df.index.name = 'segment'
    segment_df.to_csv(segment_file)
    print(f"\n✓ Saved segment results to: {segment_file}")
    
    # Save hurst summary
    hurst_file = f"{output_prefix}_hurst_summary.csv"
    hurst_df = pd.DataFrame(results['hurst_summary']).T
    hurst_df.index.name = 'hurst_class'
    hurst_df.to_csv(hurst_file)
    print(f"✓ Saved Hurst summary to: {hurst_file}")
    
    # Save direction summary
    direction_file = f"{output_prefix}_direction_summary.csv"
    direction_df = pd.DataFrame(results['direction_summary']).T
    direction_df.index.name = 'direction'
    direction_df.to_csv(direction_file)
    print(f"✓ Saved direction summary to: {direction_file}")
    
    # Save detailed data
    data_file = f"{output_prefix}_detailed_data.csv"
    results['data'][['date', 'symbol', 'hurst', 'hurst_class', 'pct_change_5d', 
                     'direction_class', 'forward_return', 'segment']].to_csv(data_file, index=False)
    print(f"✓ Saved detailed data to: {data_file}")


def main():
    """Main function to run Hurst exponent directional analysis."""
    parser = argparse.ArgumentParser(
        description='Analyze Hurst exponent by market direction'
    )
    
    # Data parameters
    parser.add_argument('--price-data', type=str,
                       default='data/raw/combined_coinbase_coinmarketcap_daily.csv',
                       help='Path to historical OHLCV CSV file')
    
    # Analysis parameters
    parser.add_argument('--top-n', type=int, default=100,
                       help='Number of top market cap coins')
    parser.add_argument('--hurst-window', type=int, default=90,
                       help='Hurst calculation window in days')
    parser.add_argument('--forward-window', type=int, default=5,
                       help='Forward return window in days')
    
    # Date range
    parser.add_argument('--start-date', type=str, default='2023-01-01',
                       help='Analysis start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default=None,
                       help='Analysis end date (YYYY-MM-DD)')
    
    # Output
    parser.add_argument('--output-prefix', type=str,
                       default='backtests/results/hurst_direction_analysis',
                       help='Prefix for output files')
    
    args = parser.parse_args()
    
    # Load data
    print(f"\nLoading data from: {args.price_data}")
    data = load_data(args.price_data)
    print(f"Loaded {len(data)} data points for {data['symbol'].nunique()} symbols")
    print(f"Date range: {data['date'].min().date()} to {data['date'].max().date()}")
    
    # Run analysis
    results = analyze_hurst_by_direction(
        data=data,
        hurst_window=args.hurst_window,
        forward_window=args.forward_window,
        top_n=args.top_n,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    # Print results
    print_results(results)
    
    # Save results
    save_results(results, args.output_prefix)
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
