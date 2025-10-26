#!/usr/bin/env python3
"""
Analyze Basket Correlations - Phase 2 of Pairs Trading Research

This script analyzes the correlation and covariance structure within each
category basket to identify suitable candidates for pairs trading.

Key Analyses:
1. Pairwise correlations within each basket
2. Rolling correlation analysis (30d, 60d, 90d, 180d)
3. Correlation stability over time
4. Principal Component Analysis (PCA)
5. Basket return calculations (equal-weight, market-cap-weight)

Outputs:
- basket_correlation_summary.csv: Summary statistics per basket
- basket_pca_analysis.csv: PCA results per basket
- basket_rolling_correlation.csv: Time series of rolling correlations
- basket_correlation_matrices/*.png: Correlation heatmaps per basket
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.decomposition import PCA
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

# Paths
DATA_PATH = Path('data/raw')
OUTPUT_PATH = Path('backtests/results')
MATRIX_PATH = OUTPUT_PATH / 'basket_correlation_matrices'

# Create output directories
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
MATRIX_PATH.mkdir(parents=True, exist_ok=True)

# Parameters
ROLLING_WINDOWS = [30, 60, 90, 180]  # days
MIN_PERIODS_RATIO = 0.5  # Minimum periods as ratio of window
MIN_BASKET_SIZE = 3  # Minimum symbols in basket for analysis
MIN_DATA_DAYS = 90  # Minimum days of data required per symbol


def load_data():
    """Load price data and category mappings."""
    print("Loading data...")
    
    # Load price data
    price_df = pd.read_csv(
        DATA_PATH / 'combined_coinbase_coinmarketcap_daily.csv',
        parse_dates=['date']
    )
    
    # Load category mappings
    category_df = pd.read_csv(DATA_PATH / 'category_mappings_validated.csv')
    
    print(f"Loaded {len(price_df):,} price records for {price_df['symbol'].nunique()} symbols")
    print(f"Loaded {len(category_df):,} category mappings for {category_df['symbol'].nunique()} symbols")
    
    return price_df, category_df


def calculate_returns(price_df):
    """Calculate daily log returns for all symbols."""
    print("\nCalculating daily returns...")
    
    # Use the 'base' column for the actual symbol (e.g., 'BTC' not 'BTC/USD')
    if 'base' in price_df.columns:
        symbol_col = 'base'
    else:
        symbol_col = 'symbol'
    
    # Sort by symbol and date
    price_df = price_df.sort_values([symbol_col, 'date'])
    
    # Calculate log returns
    price_df['return'] = price_df.groupby(symbol_col)['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Remove inf and na
    price_df = price_df.replace([np.inf, -np.inf], np.nan)
    
    # Create pivot table for returns using base symbol
    returns_pivot = price_df.pivot_table(
        index='date',
        columns=symbol_col,
        values='return'
    )
    
    print(f"Returns calculated for {len(returns_pivot.columns)} symbols")
    print(f"Date range: {returns_pivot.index.min()} to {returns_pivot.index.max()}")
    
    return price_df, returns_pivot


def filter_symbols_by_data_quality(returns_pivot, min_days=MIN_DATA_DAYS):
    """Filter symbols that have sufficient data."""
    # Count non-null days per symbol
    days_per_symbol = returns_pivot.notna().sum()
    
    # Filter symbols with enough data
    valid_symbols = days_per_symbol[days_per_symbol >= min_days].index.tolist()
    
    print(f"\nFiltered to {len(valid_symbols)} symbols with >= {min_days} days of data")
    
    return valid_symbols


def get_basket_symbols(category_df, category_name, valid_symbols):
    """Get list of symbols in a basket that have valid data."""
    basket_symbols = category_df[category_df['category'] == category_name]['symbol'].unique()
    basket_symbols = [s for s in basket_symbols if s in valid_symbols]
    return basket_symbols


def calculate_pairwise_correlation(returns_pivot, symbols):
    """Calculate pairwise correlation matrix for a basket."""
    basket_returns = returns_pivot[symbols].dropna(how='all')
    
    # Need at least 2 symbols with overlapping data
    valid_cols = basket_returns.notna().sum() >= 30  # At least 30 days of data
    basket_returns = basket_returns.loc[:, valid_cols]
    
    if basket_returns.shape[1] < 2:
        return None, None
    
    # Calculate correlation matrix
    corr_matrix = basket_returns.corr()
    
    # Calculate average correlation (excluding diagonal)
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
    avg_corr = corr_matrix.where(mask).stack().mean()
    
    return corr_matrix, avg_corr


def calculate_rolling_correlation(returns_pivot, symbols, window=60):
    """Calculate rolling average correlation for a basket."""
    basket_returns = returns_pivot[symbols]
    
    # Calculate rolling correlation for each pair
    rolling_corrs = []
    
    for i, sym1 in enumerate(symbols):
        for j, sym2 in enumerate(symbols):
            if i < j:  # Only upper triangle
                rolling_corr = basket_returns[sym1].rolling(window).corr(basket_returns[sym2])
                rolling_corrs.append(rolling_corr)
    
    if not rolling_corrs:
        return None
    
    # Average across all pairs
    avg_rolling_corr = pd.concat(rolling_corrs, axis=1).mean(axis=1)
    
    return avg_rolling_corr


def perform_pca_analysis(returns_pivot, symbols):
    """Perform PCA analysis on basket returns."""
    basket_returns = returns_pivot[symbols].dropna()
    
    if basket_returns.shape[0] < 30 or basket_returns.shape[1] < 2:
        return None
    
    # Standardize returns
    returns_std = (basket_returns - basket_returns.mean()) / basket_returns.std()
    
    # Perform PCA
    n_components = min(5, basket_returns.shape[1])
    pca = PCA(n_components=n_components)
    pca.fit(returns_std.fillna(0))
    
    # Get variance explained
    var_explained = pca.explained_variance_ratio_
    
    return {
        'n_components': n_components,
        'pc1_var': var_explained[0] if len(var_explained) > 0 else np.nan,
        'pc2_var': var_explained[1] if len(var_explained) > 1 else np.nan,
        'pc3_var': var_explained[2] if len(var_explained) > 2 else np.nan,
        'cum_var_3pc': var_explained[:3].sum() if len(var_explained) >= 3 else np.nan,
        'loadings_pc1': pca.components_[0] if len(var_explained) > 0 else None
    }


def calculate_basket_returns(price_df, symbols, method='equal_weight'):
    """Calculate basket returns using different weighting methods."""
    symbol_col = 'base' if 'base' in price_df.columns else 'symbol'
    basket_data = price_df[price_df[symbol_col].isin(symbols)].copy()
    
    if method == 'equal_weight':
        # Equal weight basket
        basket_returns = basket_data.groupby('date')['return'].mean()
        
    elif method == 'market_cap':
        # Market cap weighted basket
        basket_data['weighted_return'] = basket_data['return'] * basket_data['market_cap']
        basket_returns = basket_data.groupby('date').apply(
            lambda x: x['weighted_return'].sum() / x['market_cap'].sum() if x['market_cap'].sum() > 0 else np.nan
        )
        
    else:
        raise ValueError(f"Unknown weighting method: {method}")
    
    return basket_returns


def plot_correlation_heatmap(corr_matrix, category_name, output_path):
    """Generate and save correlation heatmap."""
    plt.figure(figsize=(12, 10))
    
    # Create mask for upper triangle
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
    
    # Plot heatmap
    sns.heatmap(
        corr_matrix,
        mask=mask,
        annot=True if len(corr_matrix) <= 15 else False,
        fmt='.2f',
        cmap='RdYlGn',
        center=0.5,
        vmin=0,
        vmax=1,
        square=True,
        linewidths=0.5,
        cbar_kws={'label': 'Correlation'}
    )
    
    plt.title(f'Correlation Matrix: {category_name}\n(Daily Returns)', fontsize=14, pad=20)
    plt.xlabel('Symbol', fontsize=12)
    plt.ylabel('Symbol', fontsize=12)
    plt.tight_layout()
    
    # Save
    safe_name = category_name.replace('/', '_').replace(' ', '_')
    plt.savefig(output_path / f'{safe_name}_correlation.png', dpi=150, bbox_inches='tight')
    plt.close()


def analyze_category(category_name, category_df, price_df, returns_pivot, valid_symbols):
    """Analyze correlation structure for a single category."""
    print(f"\n{'='*80}")
    print(f"Analyzing: {category_name}")
    print(f"{'='*80}")
    
    # Get basket symbols
    basket_symbols = get_basket_symbols(category_df, category_name, valid_symbols)
    
    if len(basket_symbols) < MIN_BASKET_SIZE:
        print(f"⚠️  Skipping: Only {len(basket_symbols)} symbols (min: {MIN_BASKET_SIZE})")
        return None
    
    print(f"Basket size: {len(basket_symbols)} symbols")
    print(f"Symbols: {', '.join(basket_symbols)}")
    
    # Calculate full-period correlation
    corr_matrix, avg_corr = calculate_pairwise_correlation(returns_pivot, basket_symbols)
    
    if corr_matrix is None:
        print(f"⚠️  Skipping: Insufficient overlapping data")
        return None
    
    print(f"Average pairwise correlation: {avg_corr:.3f}")
    
    # Calculate rolling correlations for different windows
    rolling_stats = {}
    for window in ROLLING_WINDOWS:
        rolling_corr = calculate_rolling_correlation(returns_pivot, basket_symbols, window)
        if rolling_corr is not None:
            rolling_stats[f'rolling_{window}d_mean'] = rolling_corr.mean()
            rolling_stats[f'rolling_{window}d_std'] = rolling_corr.std()
            print(f"Rolling {window}d correlation: {rolling_corr.mean():.3f} ± {rolling_corr.std():.3f}")
    
    # Perform PCA analysis
    pca_results = perform_pca_analysis(returns_pivot, basket_symbols)
    
    if pca_results:
        print(f"PCA - PC1 explains {pca_results['pc1_var']*100:.1f}% of variance")
        print(f"PCA - PC1+PC2+PC3 explain {pca_results['cum_var_3pc']*100:.1f}% of variance")
    
    # Calculate basket returns
    basket_returns_ew = calculate_basket_returns(price_df, basket_symbols, 'equal_weight')
    
    # Generate correlation heatmap
    plot_correlation_heatmap(corr_matrix, category_name, MATRIX_PATH)
    
    # Compile summary statistics
    summary = {
        'category': category_name,
        'n_symbols': len(basket_symbols),
        'n_symbols_in_corr': corr_matrix.shape[0],
        'avg_correlation': avg_corr,
        'min_correlation': corr_matrix.where(~np.eye(len(corr_matrix), dtype=bool)).min().min(),
        'max_correlation': corr_matrix.where(~np.eye(len(corr_matrix), dtype=bool)).max().max(),
        'std_correlation': corr_matrix.where(np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)).stack().std(),
    }
    
    # Add rolling stats
    summary.update(rolling_stats)
    
    # Add PCA stats
    if pca_results:
        summary.update({
            'pca_pc1_var': pca_results['pc1_var'],
            'pca_pc2_var': pca_results['pc2_var'],
            'pca_pc3_var': pca_results['pc3_var'],
            'pca_cum_var_3pc': pca_results['cum_var_3pc']
        })
    
    # Add data quality stats
    symbol_col = 'base' if 'base' in price_df.columns else 'symbol'
    basket_data = price_df[price_df[symbol_col].isin(basket_symbols)]
    summary['date_range_start'] = basket_data['date'].min()
    summary['date_range_end'] = basket_data['date'].max()
    summary['avg_data_days'] = basket_data.groupby(symbol_col)['date'].count().mean()
    
    return summary


def main():
    """Main analysis workflow."""
    print("="*80)
    print("BASKET CORRELATION ANALYSIS - PHASE 2")
    print("="*80)
    
    # Load data
    price_df, category_df = load_data()
    
    # Calculate returns
    price_df, returns_pivot = calculate_returns(price_df)
    
    # Filter symbols by data quality
    valid_symbols = filter_symbols_by_data_quality(returns_pivot, MIN_DATA_DAYS)
    
    # Get unique categories
    categories = sorted(category_df['category'].unique())
    print(f"\nAnalyzing {len(categories)} categories...")
    
    # Analyze each category
    all_summaries = []
    pca_details = []
    
    for category in categories:
        summary = analyze_category(category, category_df, price_df, returns_pivot, valid_symbols)
        if summary:
            all_summaries.append(summary)
    
    # Create summary DataFrame
    if not all_summaries:
        print("\n⚠️  No categories met minimum requirements for analysis")
        return
    
    summary_df = pd.DataFrame(all_summaries)
    
    # Sort by average correlation
    summary_df = summary_df.sort_values('avg_correlation', ascending=False)
    
    # Save summary
    summary_path = OUTPUT_PATH / 'basket_correlation_summary.csv'
    summary_df.to_csv(summary_path, index=False)
    print(f"\n✅ Saved summary to: {summary_path}")
    
    # Print top categories by correlation
    print("\n" + "="*80)
    print("TOP 10 CATEGORIES BY AVERAGE CORRELATION")
    print("="*80)
    
    top_10 = summary_df.head(10)
    for idx, row in top_10.iterrows():
        print(f"\n{row['category']}")
        print(f"  Symbols: {row['n_symbols']}")
        print(f"  Avg Correlation: {row['avg_correlation']:.3f}")
        print(f"  Correlation Range: [{row['min_correlation']:.3f}, {row['max_correlation']:.3f}]")
        if pd.notna(row.get('pca_pc1_var')):
            print(f"  PC1 Variance: {row['pca_pc1_var']*100:.1f}%")
        if pd.notna(row.get('rolling_60d_std')):
            print(f"  Correlation Stability (60d): {row['rolling_60d_std']:.3f}")
    
    # Print categories suitable for pairs trading
    print("\n" + "="*80)
    print("CATEGORIES RECOMMENDED FOR PAIRS TRADING")
    print("="*80)
    print("Criteria: avg_corr > 0.5, n_symbols >= 5, PC1 > 50%\n")
    
    suitable = summary_df[
        (summary_df['avg_correlation'] > 0.5) &
        (summary_df['n_symbols'] >= 5) &
        (summary_df.get('pca_pc1_var', 0) > 0.5)
    ]
    
    if len(suitable) > 0:
        for idx, row in suitable.iterrows():
            print(f"✅ {row['category']}")
            print(f"   Correlation: {row['avg_correlation']:.3f}, Symbols: {row['n_symbols']}, PC1: {row.get('pca_pc1_var', 0)*100:.1f}%")
    else:
        # Relaxed criteria
        print("No categories meet strict criteria. Showing relaxed recommendations:\n")
        relaxed = summary_df[
            (summary_df['avg_correlation'] > 0.4) &
            (summary_df['n_symbols'] >= 4)
        ].head(10)
        
        for idx, row in relaxed.iterrows():
            print(f"⚠️  {row['category']}")
            print(f"   Correlation: {row['avg_correlation']:.3f}, Symbols: {row['n_symbols']}")
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nOutputs saved to:")
    print(f"  - {summary_path}")
    print(f"  - {MATRIX_PATH}/*.png ({len(all_summaries)} heatmaps)")
    print(f"\nNext steps: Review results and proceed to Phase 3 (Signal Generation)")


if __name__ == '__main__':
    main()
