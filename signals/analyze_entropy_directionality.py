"""
Analyze Entropy Factor with Directionality using 5-day Returns

This script analyzes the relationship between entropy and forward 5-day returns:
1. Calculate entropy for all coins
2. Calculate 5-day forward percentage changes
3. Break down by entropy quintiles
4. Analyze returns by directionality (up/down trends)
5. Generate visualizations and summary statistics
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import argparse
import sys
import os

# Set style
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
    
    # Calculate 5-day forward percentage change (NO LOOKAHEAD)
    print("Calculating 5-day forward returns...")
    df['pct_change_5d_forward'] = df.groupby('symbol')['close'].transform(
        lambda x: (x.shift(-5) / x - 1)  # Forward-looking: next 5 days
    )
    
    # Calculate 5-day historical percentage change (for context)
    df['pct_change_5d_past'] = df.groupby('symbol')['close'].transform(
        lambda x: (x / x.shift(5) - 1)  # Backward-looking: past 5 days
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
    
    # Remove rows with missing entropy or forward returns
    df = df.dropna(subset=['entropy_30d', 'pct_change_5d_forward'])
    
    print(f"\nFinal dataset: {len(df)} observations across {df['symbol'].nunique()} symbols")
    
    return df


def assign_entropy_quintiles(df):
    """Assign entropy quintiles for each date."""
    print("\nAssigning entropy quintiles...")
    
    def assign_quintile(group):
        try:
            group['entropy_quintile'] = pd.qcut(
                group['entropy_30d'], 
                q=5, 
                labels=['Q1_Low', 'Q2', 'Q3', 'Q4', 'Q5_High'],
                duplicates='drop'
            )
        except ValueError:
            # If qcut fails (not enough unique values), use rank-based approach
            group['entropy_quintile'] = pd.cut(
                group['entropy_30d'].rank(method='first'),
                bins=5,
                labels=['Q1_Low', 'Q2', 'Q3', 'Q4', 'Q5_High']
            )
        return group
    
    df = df.groupby('date', group_keys=False).apply(assign_quintile)
    return df


def assign_directionality(df):
    """Assign directionality based on past 5-day returns."""
    print("\nAssigning directionality based on past 5-day returns...")
    
    # Simple binary: up or down
    df['direction'] = df['pct_change_5d_past'].apply(
        lambda x: 'Up' if x > 0 else 'Down' if x < 0 else 'Flat'
    )
    
    # Quartile-based momentum
    def assign_momentum_quartile(group):
        try:
            group['momentum_quartile'] = pd.qcut(
                group['pct_change_5d_past'],
                q=4,
                labels=['Q1_Down_Strong', 'Q2_Down_Weak', 'Q3_Up_Weak', 'Q4_Up_Strong'],
                duplicates='drop'
            )
        except:
            group['momentum_quartile'] = 'Unknown'
        return group
    
    df = df.groupby('date', group_keys=False).apply(assign_momentum_quartile)
    
    return df


def analyze_entropy_returns(df):
    """Analyze relationship between entropy and forward returns."""
    print("\n" + "="*80)
    print("ENTROPY vs FORWARD 5-DAY RETURNS ANALYSIS")
    print("="*80)
    
    # Overall statistics
    print("\nOverall Statistics:")
    print(f"  Mean 5d forward return: {df['pct_change_5d_forward'].mean():.4%}")
    print(f"  Median 5d forward return: {df['pct_change_5d_forward'].median():.4%}")
    print(f"  Std dev 5d forward return: {df['pct_change_5d_forward'].std():.4%}")
    print(f"  Mean entropy: {df['entropy_30d'].mean():.4f} bits")
    print(f"  Median entropy: {df['entropy_30d'].median():.4f} bits")
    
    # Correlation
    corr = df[['entropy_30d', 'pct_change_5d_forward']].corr().iloc[0, 1]
    print(f"\nCorrelation (Entropy vs Forward 5d Return): {corr:.4f}")
    
    # Returns by entropy quintile
    print("\n" + "-"*80)
    print("5-DAY FORWARD RETURNS BY ENTROPY QUINTILE")
    print("-"*80)
    
    quintile_stats = df.groupby('entropy_quintile').agg({
        'pct_change_5d_forward': ['mean', 'median', 'std', 'count'],
        'entropy_30d': ['mean', 'min', 'max'],
        'volatility_30d': 'mean'
    }).round(4)
    
    print(quintile_stats.to_string())
    
    # Statistical significance test
    print("\n" + "-"*80)
    print("STATISTICAL SIGNIFICANCE TESTS")
    print("-"*80)
    
    quintiles = ['Q1_Low', 'Q2', 'Q3', 'Q4', 'Q5_High']
    returns_by_quintile = [df[df['entropy_quintile'] == q]['pct_change_5d_forward'].dropna() for q in quintiles]
    
    # ANOVA test
    try:
        f_stat, p_value = stats.f_oneway(*returns_by_quintile)
        print(f"\nANOVA F-statistic: {f_stat:.4f}")
        print(f"ANOVA p-value: {p_value:.6f}")
        print(f"Significant at 5% level: {'YES' if p_value < 0.05 else 'NO'}")
    except:
        print("\nANOVA test failed (insufficient data)")
    
    # T-test: Q1 (Low Entropy) vs Q5 (High Entropy)
    q1_returns = df[df['entropy_quintile'] == 'Q1_Low']['pct_change_5d_forward'].dropna()
    q5_returns = df[df['entropy_quintile'] == 'Q5_High']['pct_change_5d_forward'].dropna()
    
    if len(q1_returns) > 0 and len(q5_returns) > 0:
        t_stat, p_value = stats.ttest_ind(q1_returns, q5_returns)
        print(f"\nT-test (Q1_Low vs Q5_High):")
        print(f"  Q1 (Low Entropy) mean return: {q1_returns.mean():.4%}")
        print(f"  Q5 (High Entropy) mean return: {q5_returns.mean():.4%}")
        print(f"  Difference: {(q5_returns.mean() - q1_returns.mean()):.4%}")
        print(f"  T-statistic: {t_stat:.4f}")
        print(f"  P-value: {p_value:.6f}")
        print(f"  Significant at 5% level: {'YES' if p_value < 0.05 else 'NO'}")
    
    return quintile_stats


def analyze_entropy_by_directionality(df):
    """Analyze entropy effect conditional on directionality."""
    print("\n" + "="*80)
    print("ENTROPY EFFECT BY DIRECTIONALITY")
    print("="*80)
    
    # Remove rows with missing direction info
    df_clean = df.dropna(subset=['direction', 'entropy_quintile'])
    
    # Returns by entropy and direction
    print("\n5-Day Forward Returns by Entropy Quintile and Direction:")
    print("-"*80)
    
    pivot = df_clean.pivot_table(
        values='pct_change_5d_forward',
        index='entropy_quintile',
        columns='direction',
        aggfunc=['mean', 'count']
    )
    
    print(pivot.to_string())
    
    # Returns by entropy and momentum quartile
    df_momentum = df.dropna(subset=['momentum_quartile', 'entropy_quintile'])
    
    if len(df_momentum) > 0:
        print("\n" + "-"*80)
        print("\n5-Day Forward Returns by Entropy Quintile and Momentum Quartile:")
        print("-"*80)
        
        pivot_momentum = df_momentum.pivot_table(
            values='pct_change_5d_forward',
            index='entropy_quintile',
            columns='momentum_quartile',
            aggfunc='mean'
        )
        
        print(pivot_momentum.to_string())
    
    # Calculate entropy spread (Q5 - Q1) by direction
    print("\n" + "-"*80)
    print("ENTROPY SPREAD (Q5_High - Q1_Low) BY DIRECTION:")
    print("-"*80)
    
    for direction in df_clean['direction'].unique():
        subset = df_clean[df_clean['direction'] == direction]
        
        q1_mean = subset[subset['entropy_quintile'] == 'Q1_Low']['pct_change_5d_forward'].mean()
        q5_mean = subset[subset['entropy_quintile'] == 'Q5_High']['pct_change_5d_forward'].mean()
        spread = q5_mean - q1_mean
        
        print(f"\n{direction} Trend:")
        print(f"  Q1 (Low Entropy): {q1_mean:.4%}")
        print(f"  Q5 (High Entropy): {q5_mean:.4%}")
        print(f"  Spread (Q5 - Q1): {spread:.4%}")


def create_visualizations(df, output_dir='backtests/results'):
    """Create visualizations of entropy-return relationships."""
    print("\n" + "="*80)
    print("GENERATING VISUALIZATIONS")
    print("="*80)
    
    os.makedirs(output_dir, exist_ok=True)
    
    df_clean = df.dropna(subset=['entropy_quintile', 'pct_change_5d_forward'])
    
    # 1. Box plot: Forward returns by entropy quintile
    print("\n1. Creating box plot: Forward returns by entropy quintile...")
    fig, ax = plt.subplots(figsize=(12, 6))
    
    quintile_order = ['Q1_Low', 'Q2', 'Q3', 'Q4', 'Q5_High']
    df_clean['entropy_quintile'] = pd.Categorical(
        df_clean['entropy_quintile'], 
        categories=quintile_order, 
        ordered=True
    )
    
    sns.boxplot(
        data=df_clean,
        x='entropy_quintile',
        y='pct_change_5d_forward',
        ax=ax,
        palette='RdYlGn_r'
    )
    
    ax.set_xlabel('Entropy Quintile', fontsize=12)
    ax.set_ylabel('5-Day Forward Return', fontsize=12)
    ax.set_title('5-Day Forward Returns by Entropy Quintile', fontsize=14, fontweight='bold')
    ax.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.1%}'.format(y)))
    
    plt.tight_layout()
    filename = f"{output_dir}/entropy_forward_returns_boxplot.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"   Saved: {filename}")
    plt.close()
    
    # 2. Bar plot: Mean returns by entropy quintile
    print("\n2. Creating bar plot: Mean returns by entropy quintile...")
    fig, ax = plt.subplots(figsize=(12, 6))
    
    mean_returns = df_clean.groupby('entropy_quintile')['pct_change_5d_forward'].mean()
    mean_returns = mean_returns.reindex(quintile_order)
    
    colors = ['green' if x > 0 else 'red' for x in mean_returns]
    bars = ax.bar(range(len(mean_returns)), mean_returns, color=colors, alpha=0.7, edgecolor='black')
    
    ax.set_xticks(range(len(mean_returns)))
    ax.set_xticklabels(mean_returns.index)
    ax.set_xlabel('Entropy Quintile', fontsize=12)
    ax.set_ylabel('Mean 5-Day Forward Return', fontsize=12)
    ax.set_title('Mean 5-Day Forward Returns by Entropy Quintile', fontsize=14, fontweight='bold')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.2%}'.format(y)))
    ax.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for i, (bar, value) in enumerate(zip(bars, mean_returns)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{value:.2%}',
                ha='center', va='bottom' if height > 0 else 'top',
                fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    filename = f"{output_dir}/entropy_forward_returns_barplot.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"   Saved: {filename}")
    plt.close()
    
    # 3. Grouped bar plot: Returns by entropy and direction
    print("\n3. Creating grouped bar plot: Returns by entropy and direction...")
    df_direction = df_clean.dropna(subset=['direction'])
    
    if len(df_direction) > 0:
        fig, ax = plt.subplots(figsize=(14, 7))
        
        pivot = df_direction.pivot_table(
            values='pct_change_5d_forward',
            index='entropy_quintile',
            columns='direction',
            aggfunc='mean'
        )
        pivot = pivot.reindex(quintile_order)
        
        pivot.plot(kind='bar', ax=ax, width=0.8, edgecolor='black')
        
        ax.set_xlabel('Entropy Quintile', fontsize=12)
        ax.set_ylabel('Mean 5-Day Forward Return', fontsize=12)
        ax.set_title('5-Day Forward Returns by Entropy Quintile and Direction', 
                     fontsize=14, fontweight='bold')
        ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
        ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.2%}'.format(y)))
        ax.legend(title='Past 5d Direction', fontsize=10)
        ax.grid(axis='y', alpha=0.3)
        plt.xticks(rotation=0)
        
        plt.tight_layout()
        filename = f"{output_dir}/entropy_returns_by_direction.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"   Saved: {filename}")
        plt.close()
    
    # 4. Scatter plot: Entropy vs forward returns (sample)
    print("\n4. Creating scatter plot: Entropy vs forward returns (sample)...")
    
    # Sample to avoid overcrowding
    sample_size = min(10000, len(df_clean))
    df_sample = df_clean.sample(n=sample_size, random_state=42)
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    scatter = ax.scatter(
        df_sample['entropy_30d'],
        df_sample['pct_change_5d_forward'],
        c=df_sample['volatility_30d'],
        cmap='viridis',
        alpha=0.5,
        s=10
    )
    
    # Add regression line
    z = np.polyfit(df_sample['entropy_30d'], df_sample['pct_change_5d_forward'], 1)
    p = np.poly1d(z)
    x_line = np.linspace(df_sample['entropy_30d'].min(), df_sample['entropy_30d'].max(), 100)
    ax.plot(x_line, p(x_line), "r--", linewidth=2, label=f'Linear fit: y={z[0]:.4f}x+{z[1]:.4f}')
    
    ax.set_xlabel('30-Day Entropy (bits)', fontsize=12)
    ax.set_ylabel('5-Day Forward Return', fontsize=12)
    ax.set_title(f'Entropy vs 5-Day Forward Returns (Sample: {sample_size:,} points)', 
                 fontsize=14, fontweight='bold')
    ax.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.3)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda y, _: '{:.0%}'.format(y)))
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)
    
    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('30-Day Volatility', fontsize=10)
    
    plt.tight_layout()
    filename = f"{output_dir}/entropy_returns_scatter.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"   Saved: {filename}")
    plt.close()
    
    # 5. Heatmap: Returns by entropy and momentum quartile
    print("\n5. Creating heatmap: Returns by entropy and momentum quartile...")
    df_momentum = df_clean.dropna(subset=['momentum_quartile'])
    
    if len(df_momentum) > 0:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        pivot = df_momentum.pivot_table(
            values='pct_change_5d_forward',
            index='entropy_quintile',
            columns='momentum_quartile',
            aggfunc='mean'
        )
        pivot = pivot.reindex(quintile_order)
        
        sns.heatmap(
            pivot,
            annot=True,
            fmt='.2%',
            cmap='RdYlGn',
            center=0,
            ax=ax,
            cbar_kws={'label': 'Mean 5d Forward Return'}
        )
        
        ax.set_xlabel('Past 5-Day Momentum Quartile', fontsize=12)
        ax.set_ylabel('Entropy Quintile', fontsize=12)
        ax.set_title('Mean 5-Day Forward Returns: Entropy × Momentum', 
                     fontsize=14, fontweight='bold')
        
        plt.tight_layout()
        filename = f"{output_dir}/entropy_momentum_heatmap.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"   Saved: {filename}")
        plt.close()
    
    print("\n✓ All visualizations generated successfully")


def save_summary(df, output_dir='backtests/results'):
    """Save summary statistics to CSV."""
    print("\n" + "="*80)
    print("SAVING SUMMARY STATISTICS")
    print("="*80)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Summary by entropy quintile
    summary = df.groupby('entropy_quintile').agg({
        'pct_change_5d_forward': ['count', 'mean', 'median', 'std'],
        'entropy_30d': ['mean', 'min', 'max'],
        'volatility_30d': 'mean',
        'pct_change_5d_past': 'mean'
    }).round(6)
    
    filename = f"{output_dir}/entropy_directionality_summary.csv"
    summary.to_csv(filename)
    print(f"\nSummary statistics saved to: {filename}")
    
    # Summary by entropy and direction
    df_clean = df.dropna(subset=['direction', 'entropy_quintile'])
    
    pivot = df_clean.pivot_table(
        values='pct_change_5d_forward',
        index='entropy_quintile',
        columns='direction',
        aggfunc=['mean', 'count']
    )
    
    filename = f"{output_dir}/entropy_by_direction_summary.csv"
    pivot.to_csv(filename)
    print(f"Direction breakdown saved to: {filename}")
    
    print("\n✓ Summary files saved successfully")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description='Analyze Entropy Factor with Directionality using 5-day Returns',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--price-data', type=str,
                       default='data/raw/combined_coinbase_coinmarketcap_daily.csv',
                       help='Path to historical OHLCV price data CSV file')
    parser.add_argument('--min-volume', type=float, default=5_000_000,
                       help='Minimum 30d avg daily volume filter')
    parser.add_argument('--min-market-cap', type=float, default=50_000_000,
                       help='Minimum market cap filter')
    parser.add_argument('--start-date', type=str, default='2021-01-01',
                       help='Start date for analysis (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default=None,
                       help='End date for analysis (YYYY-MM-DD)')
    parser.add_argument('--output-dir', type=str, default='backtests/results',
                       help='Directory to save output files')
    
    args = parser.parse_args()
    
    print("="*80)
    print("ENTROPY + DIRECTIONALITY ANALYSIS")
    print("Using 5-Day Forward Percentage Change")
    print("="*80)
    
    # Load and prepare data
    df = load_and_prepare_data(
        args.price_data,
        min_volume=args.min_volume,
        min_market_cap=args.min_market_cap
    )
    
    # Filter by date range
    if args.start_date:
        df = df[df['date'] >= pd.to_datetime(args.start_date)]
        print(f"\nFiltered to start date: {args.start_date}")
    
    if args.end_date:
        df = df[df['date'] <= pd.to_datetime(args.end_date)]
        print(f"Filtered to end date: {args.end_date}")
    
    print(f"\nAnalysis period: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"Total observations: {len(df):,}")
    
    # Assign quintiles and directionality
    df = assign_entropy_quintiles(df)
    df = assign_directionality(df)
    
    # Run analyses
    analyze_entropy_returns(df)
    analyze_entropy_by_directionality(df)
    
    # Create visualizations
    create_visualizations(df, output_dir=args.output_dir)
    
    # Save summary
    save_summary(df, output_dir=args.output_dir)
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nOutputs saved to: {args.output_dir}/")
    print("  - entropy_forward_returns_boxplot.png")
    print("  - entropy_forward_returns_barplot.png")
    print("  - entropy_returns_by_direction.png")
    print("  - entropy_returns_scatter.png")
    print("  - entropy_momentum_heatmap.png")
    print("  - entropy_directionality_summary.csv")
    print("  - entropy_by_direction_summary.csv")


if __name__ == "__main__":
    main()
