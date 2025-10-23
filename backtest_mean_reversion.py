"""
Backtest for Mean Reversion Factor Analysis

This script analyzes mean reversion patterns by:
1. Calculating z-scores for 1-day percentage moves
2. Calculating z-scores for 1-day volume changes
3. Comparing different combinations (high vol/high chg vs low vol/high chg, etc.)
4. Analyzing next 1-day returns for each category

The hypothesis is that certain combinations may show stronger mean reversion patterns.
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


def calculate_z_scores(data, lookback_window=30):
    """
    Calculate z-scores for 1-day returns and volume changes.
    
    Args:
        data (pd.DataFrame): Historical OHLCV data
        lookback_window (int): Window for calculating rolling mean and std
        
    Returns:
        pd.DataFrame: Data with z-scores added
    """
    df = data.copy()
    
    # Calculate 1-day percentage returns
    df['pct_change'] = df.groupby('symbol')['close'].transform(
        lambda x: x.pct_change()
    )
    
    # Calculate 1-day volume change
    df['volume_change'] = df.groupby('symbol')['volume'].transform(
        lambda x: x.pct_change()
    )
    
    # Calculate rolling mean and std for returns (shifted to avoid look-ahead bias)
    df['return_mean'] = df.groupby('symbol')['pct_change'].transform(
        lambda x: x.rolling(window=lookback_window, min_periods=lookback_window).mean().shift(1)
    )
    df['return_std'] = df.groupby('symbol')['pct_change'].transform(
        lambda x: x.rolling(window=lookback_window, min_periods=lookback_window).std().shift(1)
    )
    
    # Calculate rolling mean and std for volume (shifted to avoid look-ahead bias)
    df['volume_mean'] = df.groupby('symbol')['volume_change'].transform(
        lambda x: x.rolling(window=lookback_window, min_periods=lookback_window).mean().shift(1)
    )
    df['volume_std'] = df.groupby('symbol')['volume_change'].transform(
        lambda x: x.rolling(window=lookback_window, min_periods=lookback_window).std().shift(1)
    )
    
    # Calculate z-scores using shifted mean and std (no look-ahead bias)
    df['return_zscore'] = (df['pct_change'] - df['return_mean']) / df['return_std']
    df['volume_zscore'] = (df['volume_change'] - df['volume_mean']) / df['volume_std']
    
    # Calculate forward 1-day return
    df['forward_1d_return'] = df.groupby('symbol')['pct_change'].shift(-1)
    
    # Replace inf values with NaN
    df = df.replace([np.inf, -np.inf], np.nan)
    
    return df


def categorize_moves(data, return_threshold=1.0, volume_threshold=1.0):
    """
    Categorize moves into different buckets based on z-scores.
    
    Args:
        data (pd.DataFrame): Data with z-scores
        return_threshold (float): Z-score threshold for defining "high" returns
        volume_threshold (float): Z-score threshold for defining "high" volume
        
    Returns:
        pd.DataFrame: Data with category labels added
    """
    df = data.copy()
    
    # Create categories based on z-scores
    conditions = [
        (df['return_zscore'].abs() > return_threshold) & (df['volume_zscore'].abs() > volume_threshold),
        (df['return_zscore'].abs() > return_threshold) & (df['volume_zscore'].abs() <= volume_threshold),
        (df['return_zscore'].abs() <= return_threshold) & (df['volume_zscore'].abs() > volume_threshold),
        (df['return_zscore'].abs() <= return_threshold) & (df['volume_zscore'].abs() <= volume_threshold),
    ]
    
    categories = [
        'high_return_high_volume',
        'high_return_low_volume',
        'low_return_high_volume',
        'low_return_low_volume'
    ]
    
    df['category'] = np.select(conditions, categories, default='unknown')
    
    # Also create directional categories (up vs down)
    conditions_directional = [
        (df['return_zscore'] > return_threshold) & (df['volume_zscore'].abs() > volume_threshold),
        (df['return_zscore'] > return_threshold) & (df['volume_zscore'].abs() <= volume_threshold),
        (df['return_zscore'] < -return_threshold) & (df['volume_zscore'].abs() > volume_threshold),
        (df['return_zscore'] < -return_threshold) & (df['volume_zscore'].abs() <= volume_threshold),
    ]
    
    categories_directional = [
        'up_move_high_volume',
        'up_move_low_volume',
        'down_move_high_volume',
        'down_move_low_volume'
    ]
    
    df['category_directional'] = np.select(conditions_directional, categories_directional, default='neutral')
    
    return df


def analyze_mean_reversion(data):
    """
    Analyze mean reversion patterns by category.
    
    Args:
        data (pd.DataFrame): Data with categories and forward returns
        
    Returns:
        dict: Dictionary containing analysis results
    """
    # Filter out rows with missing data
    valid_data = data.dropna(subset=['return_zscore', 'volume_zscore', 'forward_1d_return', 'category'])
    
    # Overall statistics
    overall_stats = {
        'count': len(valid_data),
        'mean_forward_return': valid_data['forward_1d_return'].mean(),
        'median_forward_return': valid_data['forward_1d_return'].median(),
        'std_forward_return': valid_data['forward_1d_return'].std(),
    }
    
    # Statistics by category (absolute)
    category_stats = []
    for category in valid_data['category'].unique():
        if category == 'unknown':
            continue
        
        cat_data = valid_data[valid_data['category'] == category]
        
        stats = {
            'category': category,
            'count': len(cat_data),
            'mean_return_zscore': cat_data['return_zscore'].mean(),
            'mean_volume_zscore': cat_data['volume_zscore'].mean(),
            'mean_forward_return': cat_data['forward_1d_return'].mean(),
            'median_forward_return': cat_data['forward_1d_return'].median(),
            'std_forward_return': cat_data['forward_1d_return'].std(),
            'positive_days_pct': (cat_data['forward_1d_return'] > 0).sum() / len(cat_data) * 100,
            'sharpe_ratio': cat_data['forward_1d_return'].mean() / cat_data['forward_1d_return'].std() * np.sqrt(365) if cat_data['forward_1d_return'].std() > 0 else 0
        }
        
        category_stats.append(stats)
    
    # Statistics by directional category
    directional_stats = []
    for category in valid_data['category_directional'].unique():
        if category == 'neutral':
            continue
        
        cat_data = valid_data[valid_data['category_directional'] == category]
        
        stats = {
            'category': category,
            'count': len(cat_data),
            'mean_return_zscore': cat_data['return_zscore'].mean(),
            'mean_volume_zscore': cat_data['volume_zscore'].mean(),
            'mean_forward_return': cat_data['forward_1d_return'].mean(),
            'median_forward_return': cat_data['forward_1d_return'].median(),
            'std_forward_return': cat_data['forward_1d_return'].std(),
            'positive_days_pct': (cat_data['forward_1d_return'] > 0).sum() / len(cat_data) * 100,
            'sharpe_ratio': cat_data['forward_1d_return'].mean() / cat_data['forward_1d_return'].std() * np.sqrt(365) if cat_data['forward_1d_return'].std() > 0 else 0
        }
        
        directional_stats.append(stats)
    
    # Analyze by return z-score buckets
    return_buckets = pd.cut(valid_data['return_zscore'], bins=[-np.inf, -2, -1, 0, 1, 2, np.inf], 
                            labels=['<-2', '-2 to -1', '-1 to 0', '0 to 1', '1 to 2', '>2'])
    valid_data_copy = valid_data.copy()
    valid_data_copy['return_bucket'] = return_buckets
    
    bucket_stats = []
    for bucket in valid_data_copy['return_bucket'].unique():
        bucket_data = valid_data_copy[valid_data_copy['return_bucket'] == bucket]
        
        stats = {
            'return_bucket': str(bucket),
            'count': len(bucket_data),
            'mean_return_zscore': bucket_data['return_zscore'].mean(),
            'mean_forward_return': bucket_data['forward_1d_return'].mean(),
            'median_forward_return': bucket_data['forward_1d_return'].median(),
            'std_forward_return': bucket_data['forward_1d_return'].std(),
            'positive_days_pct': (bucket_data['forward_1d_return'] > 0).sum() / len(bucket_data) * 100,
        }
        
        bucket_stats.append(stats)
    
    return {
        'overall': overall_stats,
        'by_category': pd.DataFrame(category_stats),
        'by_directional_category': pd.DataFrame(directional_stats),
        'by_return_bucket': pd.DataFrame(bucket_stats),
        'detailed_data': valid_data
    }


def print_results(results):
    """
    Print analysis results in a formatted manner.
    
    Args:
        results (dict): Dictionary containing analysis results
    """
    print("\n" + "=" * 100)
    print("MEAN REVERSION FACTOR ANALYSIS")
    print("=" * 100)
    
    print("\nOVERALL STATISTICS:")
    print(f"  Total observations: {results['overall']['count']:,}")
    print(f"  Mean forward 1-day return: {results['overall']['mean_forward_return']:.4%}")
    print(f"  Median forward 1-day return: {results['overall']['median_forward_return']:.4%}")
    print(f"  Std forward 1-day return: {results['overall']['std_forward_return']:.4%}")
    
    print("\n" + "=" * 100)
    print("ANALYSIS BY CATEGORY (Absolute Z-Scores)")
    print("=" * 100)
    print("\nCategories based on |z-score| thresholds:")
    if not results['by_category'].empty:
        print(results['by_category'].to_string(index=False))
    
    print("\n" + "=" * 100)
    print("ANALYSIS BY DIRECTIONAL CATEGORY (Signed Z-Scores)")
    print("=" * 100)
    print("\nCategories based on directional z-scores:")
    if not results['by_directional_category'].empty:
        # Sort by mean forward return to see which strategies perform best
        sorted_df = results['by_directional_category'].sort_values('mean_forward_return', ascending=False)
        print(sorted_df.to_string(index=False))
    
    print("\n" + "=" * 100)
    print("ANALYSIS BY RETURN Z-SCORE BUCKET")
    print("=" * 100)
    print("\nMean reversion analysis by return z-score ranges:")
    if not results['by_return_bucket'].empty:
        # Sort by return bucket
        print(results['by_return_bucket'].to_string(index=False))
    
    print("\n" + "=" * 100)
    print("KEY INSIGHTS:")
    print("=" * 100)
    
    if not results['by_directional_category'].empty:
        directional_df = results['by_directional_category']
        
        # Find best and worst categories
        best_category = directional_df.loc[directional_df['mean_forward_return'].idxmax()]
        worst_category = directional_df.loc[directional_df['mean_forward_return'].idxmin()]
        
        print(f"\nBest performing category: {best_category['category']}")
        print(f"  Count: {best_category['count']:.0f}")
        print(f"  Mean forward return: {best_category['mean_forward_return']:.4%}")
        print(f"  Sharpe ratio: {best_category['sharpe_ratio']:.2f}")
        print(f"  Win rate: {best_category['positive_days_pct']:.1f}%")
        
        print(f"\nWorst performing category: {worst_category['category']}")
        print(f"  Count: {worst_category['count']:.0f}")
        print(f"  Mean forward return: {worst_category['mean_forward_return']:.4%}")
        print(f"  Sharpe ratio: {worst_category['sharpe_ratio']:.2f}")
        print(f"  Win rate: {worst_category['positive_days_pct']:.1f}%")
        
        # Test for mean reversion
        print("\nMean Reversion Evidence:")
        down_high_vol = directional_df[directional_df['category'] == 'down_move_high_volume']
        down_low_vol = directional_df[directional_df['category'] == 'down_move_low_volume']
        up_high_vol = directional_df[directional_df['category'] == 'up_move_high_volume']
        up_low_vol = directional_df[directional_df['category'] == 'up_move_low_volume']
        
        if not down_high_vol.empty:
            print(f"  Down moves + high volume -> next day return: {down_high_vol['mean_forward_return'].values[0]:.4%}")
        if not down_low_vol.empty:
            print(f"  Down moves + low volume -> next day return: {down_low_vol['mean_forward_return'].values[0]:.4%}")
        if not up_high_vol.empty:
            print(f"  Up moves + high volume -> next day return: {up_high_vol['mean_forward_return'].values[0]:.4%}")
        if not up_low_vol.empty:
            print(f"  Up moves + low volume -> next day return: {up_low_vol['mean_forward_return'].values[0]:.4%}")
    
    print("\n" + "=" * 100)


def save_results(results, output_prefix='backtest_mean_reversion'):
    """
    Save analysis results to CSV files.
    
    Args:
        results (dict): Dictionary containing analysis results
        output_prefix (str): Prefix for output filenames
    """
    # Save category statistics
    if not results['by_category'].empty:
        category_file = f"{output_prefix}_category_stats.csv"
        results['by_category'].to_csv(category_file, index=False)
        print(f"\nCategory statistics saved to: {category_file}")
    
    # Save directional category statistics
    if not results['by_directional_category'].empty:
        directional_file = f"{output_prefix}_directional_stats.csv"
        results['by_directional_category'].to_csv(directional_file, index=False)
        print(f"Directional statistics saved to: {directional_file}")
    
    # Save bucket statistics
    if not results['by_return_bucket'].empty:
        bucket_file = f"{output_prefix}_bucket_stats.csv"
        results['by_return_bucket'].to_csv(bucket_file, index=False)
        print(f"Bucket statistics saved to: {bucket_file}")
    
    # Save detailed data with z-scores
    detailed_file = f"{output_prefix}_detailed_data.csv"
    results['detailed_data'].to_csv(detailed_file, index=False)
    print(f"Detailed data saved to: {detailed_file}")


def main():
    """Main execution function for backtest."""
    parser = argparse.ArgumentParser(
        description='Backtest Mean Reversion Factor Analysis',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--data-file',
        type=str,
        default='top10_markets_100d_daily_data.csv',
        help='Path to historical OHLCV data CSV file'
    )
    parser.add_argument(
        '--lookback-window',
        type=int,
        default=30,
        help='Lookback window for calculating z-scores'
    )
    parser.add_argument(
        '--return-threshold',
        type=float,
        default=1.0,
        help='Z-score threshold for defining "high" returns'
    )
    parser.add_argument(
        '--volume-threshold',
        type=float,
        default=1.0,
        help='Z-score threshold for defining "high" volume'
    )
    parser.add_argument(
        '--output-prefix',
        type=str,
        default='backtest_mean_reversion',
        help='Prefix for output CSV files'
    )
    
    args = parser.parse_args()
    
    print("=" * 100)
    print("BACKTEST: Mean Reversion Factor Analysis")
    print("=" * 100)
    print(f"\nConfiguration:")
    print(f"  Data file: {args.data_file}")
    print(f"  Lookback window: {args.lookback_window} days")
    print(f"  Return threshold: {args.return_threshold} std devs")
    print(f"  Volume threshold: {args.volume_threshold} std devs")
    print("=" * 100)
    
    # Load data
    print("\nLoading data...")
    data = load_data(args.data_file)
    print(f"Loaded {len(data)} rows for {data['symbol'].nunique()} symbols")
    print(f"Date range: {data['date'].min().date()} to {data['date'].max().date()}")
    
    # Calculate z-scores
    print("\nCalculating z-scores...")
    data_with_zscores = calculate_z_scores(data, lookback_window=args.lookback_window)
    
    # Categorize moves
    print("Categorizing moves...")
    data_categorized = categorize_moves(
        data_with_zscores, 
        return_threshold=args.return_threshold,
        volume_threshold=args.volume_threshold
    )
    
    # Analyze mean reversion
    print("Analyzing mean reversion patterns...")
    results = analyze_mean_reversion(data_categorized)
    
    # Print results
    print_results(results)
    
    # Save results
    save_results(results, output_prefix=args.output_prefix)
    
    print("\n" + "=" * 100)
    print("ANALYSIS COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()
