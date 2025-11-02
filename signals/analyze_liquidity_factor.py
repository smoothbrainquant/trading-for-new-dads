"""
Analyze Liquidity Factor Performance

This script analyzes the relationship between liquidity metrics and returns
to evaluate whether liquid vs illiquid coins (relative to volatility) have
different risk/return characteristics.

Analysis includes:
1. Liquidity-volatility normalized metrics vs returns
2. Orderbook imbalance as a predictive signal
3. Liquid vs illiquid portfolio comparison
4. Factor performance attribution
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from typing import Optional, Tuple
import os


def analyze_liquidity_factor(
    liquidity_file: str,
    price_file: str,
    forward_returns_days: int = 1,
    output_dir: str = "backtests/results"
) -> pd.DataFrame:
    """
    Analyze relationship between liquidity metrics and forward returns.
    
    Args:
        liquidity_file: CSV with liquidity snapshots
        price_file: CSV with historical prices
        forward_returns_days: Days ahead to calculate returns
        output_dir: Directory to save results
    
    Returns:
        DataFrame with analysis results
    """
    print(f"\n{'='*120}")
    print(f"LIQUIDITY FACTOR ANALYSIS")
    print(f"{'='*120}\n")
    
    # Load data
    print("Loading data...")
    df_liq = pd.read_csv(liquidity_file)
    df_liq['timestamp'] = pd.to_datetime(df_liq['timestamp'])
    df_liq['date'] = df_liq['timestamp'].dt.date
    
    df_price = pd.read_csv(price_file)
    df_price['date'] = pd.to_datetime(df_price['date']).dt.date
    
    print(f"Liquidity records: {len(df_liq)}")
    print(f"Price records: {len(df_price)}")
    
    # Calculate forward returns
    print(f"\nCalculating {forward_returns_days}-day forward returns...")
    df_price = df_price.sort_values(['symbol', 'date'])
    df_price[f'return_{forward_returns_days}d'] = df_price.groupby('symbol')['close'].pct_change(forward_returns_days).shift(-forward_returns_days)
    
    # Merge liquidity with returns
    # Use latest liquidity snapshot per day per symbol
    df_liq_daily = df_liq.groupby(['symbol', 'date']).last().reset_index()
    
    # Convert symbol format if needed (BTC -> BTC/USDC:USDC)
    # Standardize symbol format in price data
    df_merged = pd.merge(
        df_liq_daily,
        df_price[['date', 'symbol', 'close', f'return_{forward_returns_days}d']],
        on=['date', 'symbol'],
        how='inner'
    )
    
    print(f"Merged records: {len(df_merged)}")
    print(f"Date range: {df_merged['date'].min()} to {df_merged['date'].max()}")
    
    if df_merged.empty:
        print("No merged data. Check symbol formats match between files.")
        return pd.DataFrame()
    
    # Analyze relationships
    results = {}
    
    # 1. Liquidity metrics vs returns
    print(f"\n{'='*120}")
    print("LIQUIDITY METRICS VS RETURNS")
    print(f"{'='*120}\n")
    
    metrics = [
        ('spread_pct', 'Spread %'),
        ('spread_vol_adj', 'Volatility-Adjusted Spread'),
        ('depth_impact_1000', 'Market Impact ($1k)'),
        ('depth_impact_1000_vol_adj', 'Vol-Adj Market Impact'),
        ('liquidity_score', 'Liquidity Score'),
        ('orderbook_imbalance', 'Orderbook Imbalance'),
        ('top_of_book_imbalance', 'Top-of-Book Imbalance'),
    ]
    
    for metric, label in metrics:
        if metric in df_merged.columns:
            corr = df_merged[[metric, f'return_{forward_returns_days}d']].corr().iloc[0, 1]
            results[f'{metric}_correlation'] = corr
            print(f"{label:30s}: correlation = {corr:>7.4f}")
    
    # 2. Quintile analysis - sort by liquidity metric
    print(f"\n{'='*120}")
    print("QUINTILE ANALYSIS - LIQUIDITY SCORE")
    print(f"{'='*120}\n")
    
    if 'liquidity_score' in df_merged.columns:
        quintile_results = analyze_by_quintile(
            df_merged,
            metric='liquidity_score',
            return_col=f'return_{forward_returns_days}d'
        )
        print(quintile_results)
        results['quintile_analysis'] = quintile_results
    
    # 3. Liquid vs Illiquid comparison
    print(f"\n{'='*120}")
    print("LIQUID VS ILLIQUID COMPARISON")
    print(f"{'='*120}\n")
    
    if 'liquidity_score' in df_merged.columns:
        liquid_illiquid_results = compare_liquid_illiquid(
            df_merged,
            metric='liquidity_score',
            return_col=f'return_{forward_returns_days}d'
        )
        print(liquid_illiquid_results)
        results['liquid_illiquid'] = liquid_illiquid_results
    
    # 4. Orderbook imbalance signal analysis
    print(f"\n{'='*120}")
    print("ORDERBOOK IMBALANCE SIGNAL ANALYSIS")
    print(f"{'='*120}\n")
    
    if 'orderbook_imbalance' in df_merged.columns:
        imbalance_results = analyze_imbalance_signal(
            df_merged,
            imbalance_col='orderbook_imbalance',
            return_col=f'return_{forward_returns_days}d',
            threshold=0.2
        )
        print(imbalance_results)
        results['imbalance_analysis'] = imbalance_results
    
    # 5. Create visualizations
    print(f"\n{'='*120}")
    print("GENERATING VISUALIZATIONS")
    print(f"{'='*120}\n")
    
    os.makedirs(output_dir, exist_ok=True)
    
    create_visualizations(df_merged, forward_returns_days, output_dir)
    
    print(f"? Visualizations saved to {output_dir}/")
    
    # Save analysis results
    results_df = pd.DataFrame([results])
    results_file = f"{output_dir}/liquidity_factor_analysis.csv"
    results_df.to_csv(results_file, index=False)
    print(f"? Analysis results saved to {results_file}")
    
    return df_merged


def analyze_by_quintile(
    df: pd.DataFrame,
    metric: str,
    return_col: str
) -> pd.DataFrame:
    """
    Analyze returns by liquidity metric quintiles.
    
    Args:
        df: DataFrame with liquidity metrics and returns
        metric: Liquidity metric column name
        return_col: Return column name
    
    Returns:
        DataFrame with quintile statistics
    """
    # Remove NaN values
    df_clean = df[[metric, return_col]].dropna()
    
    # Create quintiles (lower score = more liquid)
    df_clean['quintile'] = pd.qcut(df_clean[metric], q=5, labels=['Q1_Liquid', 'Q2', 'Q3', 'Q4', 'Q5_Illiquid'])
    
    # Calculate statistics by quintile
    quintile_stats = df_clean.groupby('quintile')[return_col].agg([
        ('count', 'count'),
        ('mean_return', 'mean'),
        ('std_return', 'std'),
        ('median_return', 'median'),
        ('sharpe', lambda x: x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0)
    ]).reset_index()
    
    # Add return differential
    q1_return = quintile_stats.iloc[0]['mean_return']
    quintile_stats['return_vs_liquid'] = quintile_stats['mean_return'] - q1_return
    
    return quintile_stats


def compare_liquid_illiquid(
    df: pd.DataFrame,
    metric: str,
    return_col: str,
    percentile_threshold: float = 0.3
) -> pd.DataFrame:
    """
    Compare liquid (bottom 30%) vs illiquid (top 30%) performance.
    
    Args:
        df: DataFrame with liquidity metrics and returns
        metric: Liquidity metric column
        return_col: Return column
        percentile_threshold: Percentile for top/bottom classification
    
    Returns:
        DataFrame with comparison statistics
    """
    df_clean = df[[metric, return_col]].dropna()
    
    # Define thresholds
    liquid_threshold = df_clean[metric].quantile(percentile_threshold)
    illiquid_threshold = df_clean[metric].quantile(1 - percentile_threshold)
    
    # Classify
    liquid = df_clean[df_clean[metric] <= liquid_threshold][return_col]
    illiquid = df_clean[df_clean[metric] >= illiquid_threshold][return_col]
    
    results = pd.DataFrame({
        'Group': ['Liquid (Bottom 30%)', 'Illiquid (Top 30%)', 'Difference'],
        'Count': [len(liquid), len(illiquid), np.nan],
        'Mean Return': [liquid.mean(), illiquid.mean(), illiquid.mean() - liquid.mean()],
        'Std Return': [liquid.std(), illiquid.std(), np.nan],
        'Sharpe (annualized)': [
            liquid.mean() / liquid.std() * np.sqrt(252) if liquid.std() > 0 else 0,
            illiquid.mean() / illiquid.std() * np.sqrt(252) if illiquid.std() > 0 else 0,
            np.nan
        ]
    })
    
    return results


def analyze_imbalance_signal(
    df: pd.DataFrame,
    imbalance_col: str,
    return_col: str,
    threshold: float = 0.2
) -> pd.DataFrame:
    """
    Analyze orderbook imbalance as a directional signal.
    
    Args:
        df: DataFrame with imbalance and returns
        imbalance_col: Imbalance column name
        return_col: Return column name
        threshold: Signal threshold
    
    Returns:
        DataFrame with signal performance
    """
    df_clean = df[[imbalance_col, return_col]].dropna()
    
    # Create signals
    df_clean['signal'] = 0
    df_clean.loc[df_clean[imbalance_col] > threshold, 'signal'] = 1  # Long
    df_clean.loc[df_clean[imbalance_col] < -threshold, 'signal'] = -1  # Short
    
    # Calculate directional returns
    df_clean['signal_return'] = df_clean['signal'] * df_clean[return_col]
    
    # Statistics by signal
    results = df_clean.groupby('signal').agg({
        return_col: ['count', 'mean', 'std'],
        'signal_return': ['mean', 'std']
    }).reset_index()
    
    results.columns = ['Signal', 'Count', 'Mean_Return', 'Std_Return', 'Mean_Signal_Return', 'Std_Signal_Return']
    results['Signal'] = results['Signal'].map({-1: 'SHORT', 0: 'NEUTRAL', 1: 'LONG'})
    
    # Overall signal performance
    overall = pd.DataFrame({
        'Signal': ['Overall (Long+Short)'],
        'Count': [len(df_clean[df_clean['signal'] != 0])],
        'Mean_Return': [df_clean[df_clean['signal'] != 0][return_col].mean()],
        'Std_Return': [df_clean[df_clean['signal'] != 0][return_col].std()],
        'Mean_Signal_Return': [df_clean[df_clean['signal'] != 0]['signal_return'].mean()],
        'Std_Signal_Return': [df_clean[df_clean['signal'] != 0]['signal_return'].std()],
    })
    
    results = pd.concat([results, overall], ignore_index=True)
    
    # Add Sharpe ratios
    results['Sharpe'] = results['Mean_Signal_Return'] / results['Std_Signal_Return'] * np.sqrt(252)
    results['Sharpe'] = results['Sharpe'].fillna(0)
    
    return results


def create_visualizations(
    df: pd.DataFrame,
    forward_days: int,
    output_dir: str
):
    """Create and save visualization plots."""
    
    return_col = f'return_{forward_days}d'
    
    # 1. Liquidity Score vs Returns Scatter
    if 'liquidity_score' in df.columns and return_col in df.columns:
        plt.figure(figsize=(12, 6))
        
        df_plot = df[['liquidity_score', return_col]].dropna()
        df_plot = df_plot[np.abs(df_plot[return_col]) < 0.5]  # Remove outliers
        
        plt.subplot(1, 2, 1)
        plt.hexbin(df_plot['liquidity_score'], df_plot[return_col], gridsize=30, cmap='viridis')
        plt.colorbar(label='Count')
        plt.xlabel('Liquidity Score (lower = more liquid)')
        plt.ylabel(f'{forward_days}d Forward Return')
        plt.title('Liquidity Score vs Forward Returns')
        
        # Add trend line
        z = np.polyfit(df_plot['liquidity_score'], df_plot[return_col], 1)
        p = np.poly1d(z)
        plt.plot(df_plot['liquidity_score'].sort_values(), 
                p(df_plot['liquidity_score'].sort_values()), 
                "r--", alpha=0.8, linewidth=2)
        
        # Quintile returns
        plt.subplot(1, 2, 2)
        df_plot['quintile'] = pd.qcut(df_plot['liquidity_score'], q=5, 
                                       labels=['Q1\nLiquid', 'Q2', 'Q3', 'Q4', 'Q5\nIlliquid'])
        quintile_means = df_plot.groupby('quintile')[return_col].mean()
        
        bars = plt.bar(range(5), quintile_means * 100, color='steelblue', alpha=0.7)
        plt.xlabel('Liquidity Quintile')
        plt.ylabel(f'Mean {forward_days}d Return (%)')
        plt.title('Returns by Liquidity Quintile')
        plt.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        plt.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/liquidity_vs_returns.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"? Saved liquidity_vs_returns.png")
    
    # 2. Orderbook Imbalance Analysis
    if 'orderbook_imbalance' in df.columns and return_col in df.columns:
        plt.figure(figsize=(14, 5))
        
        df_plot = df[['orderbook_imbalance', return_col]].dropna()
        df_plot = df_plot[np.abs(df_plot[return_col]) < 0.5]
        
        # Scatter plot
        plt.subplot(1, 3, 1)
        plt.hexbin(df_plot['orderbook_imbalance'], df_plot[return_col], 
                  gridsize=30, cmap='RdYlGn', vmin=0)
        plt.colorbar(label='Count')
        plt.xlabel('Orderbook Imbalance')
        plt.ylabel(f'{forward_days}d Forward Return')
        plt.title('Imbalance vs Returns')
        plt.axvline(x=0, color='black', linestyle='--', linewidth=1)
        plt.axhline(y=0, color='black', linestyle='--', linewidth=1)
        
        # Binned analysis
        plt.subplot(1, 3, 2)
        bins = [-1, -0.3, -0.1, 0.1, 0.3, 1]
        labels = ['Strong\nSell', 'Sell', 'Neutral', 'Buy', 'Strong\nBuy']
        df_plot['imbalance_bin'] = pd.cut(df_plot['orderbook_imbalance'], bins=bins, labels=labels)
        
        bin_means = df_plot.groupby('imbalance_bin')[return_col].mean()
        colors = ['darkred', 'red', 'gray', 'green', 'darkgreen']
        
        bars = plt.bar(range(len(bin_means)), bin_means * 100, color=colors, alpha=0.7)
        plt.xlabel('Imbalance Signal')
        plt.ylabel(f'Mean {forward_days}d Return (%)')
        plt.title('Returns by Imbalance Signal')
        plt.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        plt.grid(axis='y', alpha=0.3)
        
        # Distribution of imbalance
        plt.subplot(1, 3, 3)
        plt.hist(df_plot['orderbook_imbalance'], bins=50, color='steelblue', alpha=0.7)
        plt.xlabel('Orderbook Imbalance')
        plt.ylabel('Frequency')
        plt.title('Imbalance Distribution')
        plt.axvline(x=0, color='red', linestyle='--', linewidth=2)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/orderbook_imbalance_analysis.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"? Saved orderbook_imbalance_analysis.png")
    
    # 3. Spread metrics comparison
    spread_metrics = ['spread_pct', 'spread_vol_adj']
    available_metrics = [m for m in spread_metrics if m in df.columns]
    
    if available_metrics and return_col in df.columns:
        fig, axes = plt.subplots(1, len(available_metrics), figsize=(7*len(available_metrics), 5))
        if len(available_metrics) == 1:
            axes = [axes]
        
        for i, metric in enumerate(available_metrics):
            df_plot = df[[metric, return_col]].dropna()
            df_plot = df_plot[np.abs(df_plot[return_col]) < 0.5]
            
            # Create deciles
            df_plot['decile'] = pd.qcut(df_plot[metric], q=10, labels=False, duplicates='drop')
            decile_means = df_plot.groupby('decile')[return_col].mean()
            
            axes[i].plot(decile_means.index, decile_means * 100, marker='o', linewidth=2)
            axes[i].set_xlabel('Decile (0=liquid, 9=illiquid)')
            axes[i].set_ylabel(f'Mean {forward_days}d Return (%)')
            axes[i].set_title(f'{metric} vs Returns')
            axes[i].axhline(y=0, color='black', linestyle='--', linewidth=1)
            axes[i].grid(alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f'{output_dir}/spread_metrics_analysis.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"? Saved spread_metrics_analysis.png")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze liquidity factor performance",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--liquidity-file",
        type=str,
        required=True,
        help="CSV file with liquidity snapshots"
    )
    parser.add_argument(
        "--price-file",
        type=str,
        required=True,
        help="CSV file with historical prices"
    )
    parser.add_argument(
        "--forward-days",
        type=int,
        default=1,
        help="Days ahead for forward returns"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="backtests/results",
        help="Output directory for results"
    )
    
    args = parser.parse_args()
    
    # Run analysis
    df_results = analyze_liquidity_factor(
        liquidity_file=args.liquidity_file,
        price_file=args.price_file,
        forward_returns_days=args.forward_days,
        output_dir=args.output_dir
    )
    
    if not df_results.empty:
        print(f"\n? Analysis complete!")
        print(f"  Results saved to {args.output_dir}/")
    else:
        print(f"\n? Analysis failed - no data to analyze")
    
    print("\nDone!")
