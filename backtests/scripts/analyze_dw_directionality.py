#!/usr/bin/env python3
"""
Analyze Durbin-Watson Factor with Directional Context

This script analyzes the relationship between:
1. DW statistic (autocorrelation measure)
2. Recent directional momentum (5-day % change)
3. Forward returns

Goal: Determine if combining DW + direction improves signal quality
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../signals'))


def load_data(filepath):
    """Load historical OHLCV data."""
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    return df


def calculate_durbin_watson(returns, window=30):
    """Calculate Durbin-Watson statistic."""
    if len(returns) < 2:
        return np.nan
    
    clean_returns = returns.dropna()
    if len(clean_returns) < window * 0.7:
        return np.nan
    
    numerator = np.sum(np.diff(clean_returns)**2)
    denominator = np.sum(clean_returns**2)
    
    if denominator == 0 or np.isnan(denominator):
        return np.nan
    
    dw = numerator / denominator
    if dw < 0 or dw > 4.5:
        return np.nan
        
    return dw


def prepare_analysis_data(data, dw_window=30, min_volume=5_000_000, min_market_cap=50_000_000):
    """
    Prepare data with DW, directional momentum, and forward returns.
    """
    df = data.copy()
    
    # Calculate daily log returns
    df['daily_return'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Calculate rolling DW
    print("Calculating Durbin-Watson statistic...")
    df['dw'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=dw_window, min_periods=int(dw_window*0.7)).apply(
            calculate_durbin_watson, raw=False, kwargs={'window': dw_window}
        )
    )
    
    # Calculate 5-day percentage change (directional momentum)
    print("Calculating 5-day returns...")
    df['pct_chg_5d'] = df.groupby('symbol')['close'].transform(
        lambda x: (x / x.shift(5) - 1)
    )
    
    # Calculate forward returns for analysis (1d, 5d, 10d)
    print("Calculating forward returns...")
    df['forward_1d'] = df.groupby('symbol')['daily_return'].shift(-1)
    df['forward_5d'] = df.groupby('symbol')['close'].transform(
        lambda x: (x.shift(-5) / x - 1)
    )
    df['forward_10d'] = df.groupby('symbol')['close'].transform(
        lambda x: (x.shift(-10) / x - 1)
    )
    
    # Apply filters
    print("Applying filters...")
    df['volume_30d_avg'] = df.groupby('symbol')['volume'].transform(
        lambda x: x.rolling(window=30, min_periods=20).mean()
    )
    
    # Filter by volume and market cap
    df = df[
        (df['volume_30d_avg'] >= min_volume) & 
        (df['market_cap'] >= min_market_cap)
    ]
    
    # Remove extreme DW values
    df = df[(df['dw'] >= 0.5) & (df['dw'] <= 3.5)]
    
    return df


def create_dw_buckets(df, num_buckets=5):
    """
    Bucket coins by DW values.
    1 = lowest DW (momentum), 5 = highest DW (mean reversion)
    """
    df = df.copy()
    df['dw_bucket'] = pd.qcut(df['dw'], q=num_buckets, labels=['Low DW', 'Low-Mid', 'Mid', 'Mid-High', 'High DW'], duplicates='drop')
    return df


def create_direction_buckets(df, num_buckets=3):
    """
    Bucket coins by 5-day % change.
    1 = down, 2 = flat, 3 = up
    """
    df = df.copy()
    df['direction_bucket'] = pd.qcut(df['pct_chg_5d'], q=num_buckets, labels=['Down', 'Flat', 'Up'], duplicates='drop')
    return df


def analyze_dw_direction_combinations(df):
    """
    Analyze forward returns by DW bucket + direction bucket combinations.
    """
    # Remove rows with missing data
    analysis_df = df[['dw', 'dw_bucket', 'pct_chg_5d', 'direction_bucket', 
                      'forward_1d', 'forward_5d', 'forward_10d']].dropna()
    
    print(f"\nTotal observations for analysis: {len(analysis_df):,}")
    
    # Group by DW bucket and direction bucket
    grouped = analysis_df.groupby(['dw_bucket', 'direction_bucket'])
    
    results = []
    for (dw_bucket, direction_bucket), group in grouped:
        results.append({
            'dw_bucket': dw_bucket,
            'direction_bucket': direction_bucket,
            'count': len(group),
            'avg_dw': group['dw'].mean(),
            'avg_5d_chg': group['pct_chg_5d'].mean() * 100,
            'fwd_1d_mean': group['forward_1d'].mean() * 100,
            'fwd_5d_mean': group['forward_5d'].mean() * 100,
            'fwd_10d_mean': group['forward_10d'].mean() * 100,
            'fwd_1d_sharpe': (group['forward_1d'].mean() / group['forward_1d'].std()) * np.sqrt(252) if group['forward_1d'].std() > 0 else 0,
            'fwd_5d_sharpe': (group['forward_5d'].mean() / group['forward_5d'].std()) * np.sqrt(252/5) if group['forward_5d'].std() > 0 else 0,
            'win_rate_1d': (group['forward_1d'] > 0).mean() * 100,
            'win_rate_5d': (group['forward_5d'] > 0).mean() * 100,
        })
    
    results_df = pd.DataFrame(results)
    return results_df


def print_analysis(results_df):
    """Print detailed analysis results."""
    print("\n" + "=" * 120)
    print("DURBIN-WATSON + DIRECTIONALITY ANALYSIS")
    print("=" * 120)
    
    print("\nHow to read this table:")
    print("  - DW Bucket: Low DW = momentum (trend), High DW = mean reversion (choppy)")
    print("  - Direction: Down/Flat/Up based on past 5-day % change")
    print("  - Forward returns show what happens NEXT after observing DW + direction")
    print("  - Sharpe: Annualized Sharpe ratio of forward returns\n")
    
    # Sort by 5-day forward return
    results_sorted = results_df.sort_values('fwd_5d_mean', ascending=False)
    
    print("\n{:<12} {:<12} {:>8} {:>8} {:>10} {:>10} {:>10} {:>10} {:>12} {:>12}".format(
        'DW Bucket', 'Direction', 'Count', 'Avg DW', '5d Chg%', 'Fwd 1d%', 'Fwd 5d%', 'Fwd 10d%', '5d Sharpe', 'WinRate 5d'
    ))
    print("-" * 120)
    
    for _, row in results_sorted.iterrows():
        print("{:<12} {:<12} {:>8,} {:>8.2f} {:>10.2f} {:>10.2f} {:>10.2f} {:>10.2f} {:>12.2f} {:>12.1f}%".format(
            row['dw_bucket'],
            row['direction_bucket'],
            int(row['count']),
            row['avg_dw'],
            row['avg_5d_chg'],
            row['fwd_1d_mean'],
            row['fwd_5d_mean'],
            row['fwd_10d_mean'],
            row['fwd_5d_sharpe'],
            row['win_rate_5d']
        ))
    
    print("\n" + "=" * 120)


def identify_best_strategies(results_df):
    """Identify best long and short candidates."""
    print("\n" + "=" * 80)
    print("STRATEGY RECOMMENDATIONS")
    print("=" * 80)
    
    # Best long candidates (highest forward returns)
    best_long = results_df.nlargest(3, 'fwd_5d_mean')
    print("\n🟢 BEST LONG CANDIDATES (Top 3 by 5-day forward return):")
    print("-" * 80)
    for idx, row in best_long.iterrows():
        print(f"\n  {row['dw_bucket']} + {row['direction_bucket']}")
        print(f"    Avg DW:           {row['avg_dw']:.2f}")
        print(f"    Recent 5d change: {row['avg_5d_chg']:+.2f}%")
        print(f"    Forward 5d ret:   {row['fwd_5d_mean']:+.2f}%")
        print(f"    5d Sharpe:        {row['fwd_5d_sharpe']:.2f}")
        print(f"    Win rate:         {row['win_rate_5d']:.1f}%")
        print(f"    Sample size:      {row['count']:,}")
    
    # Best short candidates (lowest/most negative forward returns)
    best_short = results_df.nsmallest(3, 'fwd_5d_mean')
    print("\n🔴 BEST SHORT CANDIDATES (Top 3 by 5-day forward return):")
    print("-" * 80)
    for idx, row in best_short.iterrows():
        print(f"\n  {row['dw_bucket']} + {row['direction_bucket']}")
        print(f"    Avg DW:           {row['avg_dw']:.2f}")
        print(f"    Recent 5d change: {row['avg_5d_chg']:+.2f}%")
        print(f"    Forward 5d ret:   {row['fwd_5d_mean']:+.2f}%")
        print(f"    5d Sharpe:        {row['fwd_5d_sharpe']:.2f}")
        print(f"    Win rate:         {row['win_rate_5d']:.1f}%")
        print(f"    Sample size:      {row['count']:,}")
    
    print("\n" + "=" * 80)


def analyze_pure_dw_vs_directional(results_df):
    """Compare pure DW strategy vs DW + directional."""
    print("\n" + "=" * 80)
    print("COMPARISON: PURE DW vs DW + DIRECTIONAL")
    print("=" * 80)
    
    # Pure DW strategy (ignoring direction) - weighted average by count
    dw_only_data = []
    for dw_bucket in results_df['dw_bucket'].unique():
        bucket_data = results_df[results_df['dw_bucket'] == dw_bucket]
        weighted_fwd = np.average(bucket_data['fwd_5d_mean'], weights=bucket_data['count'])
        dw_only_data.append({
            'dw_bucket': dw_bucket,
            'count': bucket_data['count'].sum(),
            'fwd_5d_mean': weighted_fwd,
            'fwd_5d_sharpe': bucket_data['fwd_5d_sharpe'].mean()
        })
    dw_only = pd.DataFrame(dw_only_data)
    
    print("\n📊 Pure DW Strategy (ignoring direction):")
    print("{:<12} {:>8} {:>15} {:>15}".format('DW Bucket', 'Count', 'Fwd 5d Ret%', '5d Sharpe'))
    print("-" * 50)
    for _, row in dw_only.iterrows():
        print("{:<12} {:>8,} {:>15.2f} {:>15.2f}".format(
            row['dw_bucket'], int(row['count']), row['fwd_5d_mean'], row['fwd_5d_sharpe']
        ))
    
    # DW + Directional strategy (using direction)
    print("\n📊 DW + Directional Strategy:")
    print("  Best long:  High DW + specific direction")
    print("  Best short: Low DW + specific direction")
    
    best_long_combo = results_df.nlargest(1, 'fwd_5d_mean').iloc[0]
    best_short_combo = results_df.nsmallest(1, 'fwd_5d_mean').iloc[0]
    
    print(f"\n  Long:  {best_long_combo['dw_bucket']} + {best_long_combo['direction_bucket']}")
    print(f"         Forward 5d: {best_long_combo['fwd_5d_mean']:+.2f}%")
    print(f"  Short: {best_short_combo['dw_bucket']} + {best_short_combo['direction_bucket']}")
    print(f"         Forward 5d: {best_short_combo['fwd_5d_mean']:+.2f}%")
    print(f"\n  Long-Short Spread: {best_long_combo['fwd_5d_mean'] - best_short_combo['fwd_5d_mean']:.2f}%")
    
    # Compare to pure DW
    high_dw_only = dw_only[dw_only['dw_bucket'] == 'High DW'].iloc[0]['fwd_5d_mean']
    low_dw_only = dw_only[dw_only['dw_bucket'] == 'Low DW'].iloc[0]['fwd_5d_mean']
    pure_spread = high_dw_only - low_dw_only
    
    print(f"\n  Pure DW Long-Short Spread: {pure_spread:.2f}%")
    print(f"  Improvement from adding direction: {(best_long_combo['fwd_5d_mean'] - best_short_combo['fwd_5d_mean']) - pure_spread:+.2f}%")
    
    print("\n" + "=" * 80)


def save_results(results_df, output_file):
    """Save results to CSV."""
    results_df.to_csv(output_file, index=False)
    print(f"\n✓ Saved detailed results to: {output_file}")


def main():
    """Main analysis function."""
    print("=" * 80)
    print("DURBIN-WATSON + DIRECTIONALITY ANALYSIS")
    print("=" * 80)
    
    # Load data
    data_file = 'data/raw/combined_coinbase_coinmarketcap_daily.csv'
    print(f"\nLoading data from: {data_file}")
    data = load_data(data_file)
    print(f"Loaded {len(data):,} rows for {data['symbol'].nunique()} symbols")
    
    # Prepare analysis data
    print("\nPreparing analysis data...")
    df = prepare_analysis_data(data, dw_window=30)
    print(f"After filtering: {len(df):,} observations")
    
    # Filter to 2023-2024 for consistency with backtest
    df = df[(df['date'] >= '2023-01-01') & (df['date'] <= '2024-01-01')]
    print(f"Period 2023-2024: {len(df):,} observations")
    
    # Create buckets
    print("\nCreating DW and direction buckets...")
    df = create_dw_buckets(df, num_buckets=5)
    df = create_direction_buckets(df, num_buckets=3)
    
    # Analyze combinations
    print("\nAnalyzing DW + direction combinations...")
    results_df = analyze_dw_direction_combinations(df)
    
    # Print results
    print_analysis(results_df)
    
    # Identify best strategies
    identify_best_strategies(results_df)
    
    # Compare pure DW vs directional
    analyze_pure_dw_vs_directional(results_df)
    
    # Save results
    output_file = 'backtests/results/dw_directionality_analysis.csv'
    save_results(results_df, output_file)
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
