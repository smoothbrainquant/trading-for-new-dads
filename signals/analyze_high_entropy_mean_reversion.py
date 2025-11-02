"""
High Entropy Mean Reversion Analysis

Simple strategy: Trade high entropy coins (most random/choppy) expecting mean reversion.
No directionality filters - just buy high entropy and see if it mean reverts.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import argparse
import sys
import os

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 8)


def calculate_shannon_entropy(returns, n_bins=10):
    """Calculate Shannon entropy of return distribution."""
    returns_clean = returns[~np.isnan(returns)]
    
    if len(returns_clean) < 5:
        return np.nan
    
    counts, bin_edges = np.histogram(returns_clean, bins=n_bins)
    probabilities = counts / counts.sum()
    probabilities = probabilities[probabilities > 0]
    
    if len(probabilities) == 0:
        return np.nan
    
    entropy = -np.sum(probabilities * np.log2(probabilities))
    return entropy


def load_and_prepare_data(filepath, min_volume=5_000_000, min_market_cap=50_000_000):
    """Load data and calculate entropy + forward returns."""
    print(f"\nLoading data from {filepath}...")
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    print(f"Loaded {len(df)} rows for {df['symbol'].nunique()} symbols")
    print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    
    # Calculate daily log returns
    print("\nCalculating daily returns...")
    df['daily_return'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Calculate 30-day rolling entropy
    print("Calculating 30-day rolling entropy...")
    def rolling_entropy_func(x):
        if len(x) < 30 or x.isna().all():
            return np.nan
        try:
            return calculate_shannon_entropy(x.values, n_bins=10)
        except:
            return np.nan
    
    df['entropy_30d'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=30, min_periods=30).apply(
            rolling_entropy_func, raw=False
        )
    )
    
    # Calculate forward returns (multiple horizons)
    print("Calculating forward returns...")
    for days in [1, 5, 10, 20]:
        df[f'fwd_return_{days}d'] = df.groupby('symbol')['close'].transform(
            lambda x: (x.shift(-days) / x - 1)
        )
    
    # Calculate 30-day volatility
    print("Calculating 30-day volatility...")
    df['volatility_30d'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=30, min_periods=30).std() * np.sqrt(365)
    )
    
    # Filter by liquidity and market cap
    if 'volume' in df.columns:
        df['volume_30d_avg'] = df.groupby('symbol')['volume'].transform(
            lambda x: x.rolling(window=30, min_periods=20).mean()
        )
        df = df[df['volume_30d_avg'] >= min_volume]
        print(f"Filtered by volume (>${min_volume:,.0f}): {df['symbol'].nunique()} symbols remain")
    
    if 'market_cap' in df.columns:
        df = df[df['market_cap'] >= min_market_cap]
        print(f"Filtered by market cap (>${min_market_cap:,.0f}): {df['symbol'].nunique()} symbols remain")
    
    # Remove rows with missing entropy
    df = df.dropna(subset=['entropy_30d'])
    
    print(f"\nFinal dataset: {len(df)} observations across {df['symbol'].nunique()} symbols")
    
    return df


def analyze_high_entropy_strategy(df, top_pct=20):
    """
    Analyze strategy: Buy top X% highest entropy coins.
    
    Args:
        df: DataFrame with entropy and forward returns
        top_pct: Percentile threshold (e.g., 20 = top 20%)
    """
    print("\n" + "="*80)
    print(f"HIGH ENTROPY MEAN REVERSION STRATEGY (Top {top_pct}%)")
    print("="*80)
    
    # Calculate entropy percentile for each date
    df['entropy_percentile'] = df.groupby('date')['entropy_30d'].transform(
        lambda x: x.rank(pct=True) * 100
    )
    
    # Define high entropy group
    threshold = 100 - top_pct
    df['high_entropy'] = df['entropy_percentile'] >= threshold
    
    high_ent = df[df['high_entropy']]
    low_ent = df[~df['high_entropy']]
    
    print(f"\nHigh Entropy Group (top {top_pct}%):")
    print(f"  Observations: {len(high_ent):,}")
    print(f"  Mean entropy: {high_ent['entropy_30d'].mean():.4f} bits")
    print(f"  Median entropy: {high_ent['entropy_30d'].median():.4f} bits")
    print(f"  Mean volatility: {high_ent['volatility_30d'].mean():.2%}")
    
    print(f"\nLow Entropy Group (bottom {100-top_pct}%):")
    print(f"  Observations: {len(low_ent):,}")
    print(f"  Mean entropy: {low_ent['entropy_30d'].mean():.4f} bits")
    print(f"  Median entropy: {low_ent['entropy_30d'].median():.4f} bits")
    print(f"  Mean volatility: {low_ent['volatility_30d'].mean():.2%}")
    
    # Analyze forward returns
    print("\n" + "-"*80)
    print("FORWARD RETURNS COMPARISON")
    print("-"*80)
    
    results = []
    for days in [1, 5, 10, 20]:
        col = f'fwd_return_{days}d'
        
        high_returns = high_ent[col].dropna()
        low_returns = low_ent[col].dropna()
        
        if len(high_returns) == 0 or len(low_returns) == 0:
            continue
        
        # Calculate statistics
        high_mean = high_returns.mean()
        low_mean = low_returns.mean()
        spread = high_mean - low_mean
        
        # T-test
        t_stat, p_val = stats.ttest_ind(high_returns, low_returns)
        
        # Win rate
        high_win = (high_returns > 0).mean()
        low_win = (low_returns > 0).mean()
        
        results.append({
            'Horizon': f'{days}d',
            'High Entropy': f'{high_mean:.2%}',
            'Low Entropy': f'{low_mean:.2%}',
            'Spread': f'{spread:.2%}',
            'T-stat': f'{t_stat:.2f}',
            'P-value': f'{p_val:.4f}',
            'Significant': 'YES' if p_val < 0.05 else 'NO',
            'High Win Rate': f'{high_win:.1%}',
            'Low Win Rate': f'{low_win:.1%}'
        })
    
    results_df = pd.DataFrame(results)
    print(results_df.to_string(index=False))
    
    # Annualized returns
    print("\n" + "-"*80)
    print("ANNUALIZED RETURNS (assuming compounding)")
    print("-"*80)
    
    for days in [1, 5, 10, 20]:
        col = f'fwd_return_{days}d'
        
        high_returns = high_ent[col].dropna()
        low_returns = low_ent[col].dropna()
        
        if len(high_returns) == 0 or len(low_returns) == 0:
            continue
        
        # Annualized (simple approximation)
        periods_per_year = 365 / days
        high_ann = (1 + high_returns.mean()) ** periods_per_year - 1
        low_ann = (1 + low_returns.mean()) ** periods_per_year - 1
        spread_ann = high_ann - low_ann
        
        print(f"\n{days}-day holding period ({periods_per_year:.1f} periods/year):")
        print(f"  High Entropy: {high_ann:>10.2%}")
        print(f"  Low Entropy:  {low_ann:>10.2%}")
        print(f"  Spread:       {spread_ann:>10.2%}")
    
    return df, results_df


def analyze_by_entropy_quintile(df):
    """Detailed breakdown by entropy quintile."""
    print("\n" + "="*80)
    print("ANALYSIS BY ENTROPY QUINTILE")
    print("="*80)
    
    def assign_quintile(group):
        try:
            group['entropy_quintile'] = pd.qcut(
                group['entropy_30d'], 
                q=5, 
                labels=[1, 2, 3, 4, 5],
                duplicates='drop'
            )
        except ValueError:
            group['entropy_quintile'] = pd.cut(
                group['entropy_30d'].rank(method='first'),
                bins=5,
                labels=[1, 2, 3, 4, 5]
            )
        return group
    
    df = df.groupby('date', group_keys=False).apply(assign_quintile)
    
    print("\nForward Returns by Entropy Quintile:")
    print("-"*80)
    
    for days in [1, 5, 10, 20]:
        col = f'fwd_return_{days}d'
        
        stats_df = df.groupby('entropy_quintile')[col].agg([
            ('count', 'count'),
            ('mean', 'mean'),
            ('median', 'median'),
            ('std', 'std')
        ]).round(4)
        
        print(f"\n{days}-day Forward Returns:")
        print(stats_df.to_string())
        
        # Monotonicity test
        means = stats_df['mean'].values
        is_monotonic = all(means[i] <= means[i+1] for i in range(len(means)-1))
        print(f"  Monotonic increasing: {'YES' if is_monotonic else 'NO'}")
        print(f"  Q5/Q1 ratio: {means[-1]/means[0] if means[0] != 0 else 'N/A':.2f}x")
    
    return df


def create_visualizations(df, output_dir='backtests/results'):
    """Create visualizations."""
    print("\n" + "="*80)
    print("GENERATING VISUALIZATIONS")
    print("="*80)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Forward returns by entropy quintile (multiple horizons)
    print("\n1. Creating forward returns by quintile chart...")
    
    if 'entropy_quintile' not in df.columns:
        print("   Skipping (no quintiles assigned)")
    else:
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        axes = axes.flatten()
        
        for idx, days in enumerate([1, 5, 10, 20]):
            ax = axes[idx]
            col = f'fwd_return_{days}d'
            
            data = df.dropna(subset=[col, 'entropy_quintile'])
            
            means = data.groupby('entropy_quintile')[col].mean()
            stds = data.groupby('entropy_quintile')[col].sem()  # Standard error
            
            x = means.index.astype(int)
            colors = ['red' if m < 0 else 'green' for m in means]
            
            bars = ax.bar(x, means, color=colors, alpha=0.7, edgecolor='black')
            ax.errorbar(x, means, yerr=stds*1.96, fmt='none', 
                       ecolor='black', capsize=5, capthick=2)
            
            ax.set_xlabel('Entropy Quintile (1=Low, 5=High)', fontsize=11)
            ax.set_ylabel(f'{days}-Day Forward Return', fontsize=11)
            ax.set_title(f'{days}-Day Forward Returns by Entropy Quintile', 
                        fontsize=12, fontweight='bold')
            ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1%}'))
            ax.grid(axis='y', alpha=0.3)
            ax.set_xticks(x)
            
            # Add value labels
            for i, (bar, value) in enumerate(zip(bars, means)):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{value:.2%}',
                       ha='center', va='bottom' if height > 0 else 'top',
                       fontsize=9, fontweight='bold')
        
        plt.tight_layout()
        filename = f"{output_dir}/high_entropy_forward_returns_by_quintile.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"   Saved: {filename}")
        plt.close()
    
    # 2. High entropy vs low entropy comparison
    print("\n2. Creating high vs low entropy comparison...")
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    horizons = [1, 5, 10, 20]
    high_means = []
    low_means = []
    
    for days in horizons:
        col = f'fwd_return_{days}d'
        high = df[df['high_entropy']][col].mean()
        low = df[~df['high_entropy']][col].mean()
        high_means.append(high)
        low_means.append(low)
    
    x = np.arange(len(horizons))
    width = 0.35
    
    bars1 = ax.bar(x - width/2, high_means, width, label='High Entropy (Top 20%)',
                   color='orange', alpha=0.8, edgecolor='black')
    bars2 = ax.bar(x + width/2, low_means, width, label='Low Entropy (Bottom 80%)',
                   color='blue', alpha=0.8, edgecolor='black')
    
    ax.set_xlabel('Holding Period', fontsize=12)
    ax.set_ylabel('Mean Forward Return', fontsize=12)
    ax.set_title('High Entropy vs Low Entropy: Forward Returns by Horizon', 
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{h}d' for h in horizons])
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: f'{y:.1%}'))
    ax.legend(fontsize=11)
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.2%}',
                   ha='center', va='bottom' if height > 0 else 'top',
                   fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    filename = f"{output_dir}/high_entropy_vs_low_comparison.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"   Saved: {filename}")
    plt.close()
    
    # 3. Cumulative returns simulation
    print("\n3. Creating cumulative returns simulation...")
    
    # Simple simulation: assume we hold high entropy coins and rebalance every 5 days
    col = 'fwd_return_5d'
    
    high_data = df[df['high_entropy']].sort_values('date')
    low_data = df[~df['high_entropy']].sort_values('date')
    
    # Group by rebalance periods (every 5 days)
    high_data['period'] = (high_data.groupby('symbol').cumcount() // 5)
    low_data['period'] = (low_data.groupby('symbol').cumcount() // 5)
    
    # Calculate average return per period
    high_period_returns = high_data.groupby('period')[col].mean()
    low_period_returns = low_data.groupby('period')[col].mean()
    
    # Calculate cumulative returns
    high_cum = (1 + high_period_returns).cumprod()
    low_cum = (1 + low_period_returns).cumprod()
    
    fig, ax = plt.subplots(figsize=(14, 7))
    
    ax.plot(high_cum.values, label='High Entropy Strategy', 
           color='orange', linewidth=2)
    ax.plot(low_cum.values, label='Low Entropy Strategy', 
           color='blue', linewidth=2)
    ax.axhline(y=1, color='black', linestyle='--', linewidth=1, alpha=0.5)
    
    ax.set_xlabel('Rebalance Period (5 days each)', fontsize=12)
    ax.set_ylabel('Cumulative Return (Starting at 1.0)', fontsize=12)
    ax.set_title('Cumulative Returns: High Entropy vs Low Entropy (5-day rebalance)', 
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(alpha=0.3)
    
    # Add final values
    ax.text(len(high_cum)-1, high_cum.iloc[-1], 
           f'{high_cum.iloc[-1]:.2f}x',
           fontsize=10, fontweight='bold', color='orange',
           ha='right', va='bottom')
    ax.text(len(low_cum)-1, low_cum.iloc[-1], 
           f'{low_cum.iloc[-1]:.2f}x',
           fontsize=10, fontweight='bold', color='blue',
           ha='right', va='top')
    
    plt.tight_layout()
    filename = f"{output_dir}/high_entropy_cumulative_returns.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"   Saved: {filename}")
    plt.close()
    
    print("\n✓ All visualizations generated")


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(
        description='High Entropy Mean Reversion Analysis',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--price-data', type=str,
                       default='data/raw/combined_coinbase_coinmarketcap_daily.csv',
                       help='Path to price data')
    parser.add_argument('--min-volume', type=float, default=5_000_000,
                       help='Minimum volume filter')
    parser.add_argument('--min-market-cap', type=float, default=50_000_000,
                       help='Minimum market cap filter')
    parser.add_argument('--start-date', type=str, default='2021-01-01',
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default=None,
                       help='End date (YYYY-MM-DD)')
    parser.add_argument('--top-pct', type=int, default=20,
                       help='Top percentile for high entropy (default: 20)')
    parser.add_argument('--output-dir', type=str, default='backtests/results',
                       help='Output directory')
    
    args = parser.parse_args()
    
    print("="*80)
    print("HIGH ENTROPY MEAN REVERSION ANALYSIS")
    print("Strategy: Buy high entropy coins, expect mean reversion")
    print("="*80)
    
    # Load data
    df = load_and_prepare_data(
        args.price_data,
        min_volume=args.min_volume,
        min_market_cap=args.min_market_cap
    )
    
    # Filter by date
    if args.start_date:
        df = df[df['date'] >= pd.to_datetime(args.start_date)]
    if args.end_date:
        df = df[df['date'] <= pd.to_datetime(args.end_date)]
    
    print(f"\nAnalysis period: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"Total observations: {len(df):,}")
    
    # Run analysis
    df, results = analyze_high_entropy_strategy(df, top_pct=args.top_pct)
    df = analyze_by_entropy_quintile(df)
    
    # Create visualizations
    create_visualizations(df, output_dir=args.output_dir)
    
    # Save results
    output_file = f"{args.output_dir}/high_entropy_mean_reversion_results.csv"
    results.to_csv(output_file, index=False)
    print(f"\nResults saved to: {output_file}")
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
