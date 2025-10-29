#!/usr/bin/env python3
"""
Visualize Volatility Factor Rebalance Period Comparison Results

Creates visualization plots comparing different rebalance periods.
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os


def create_comparison_plots(comparison_file="backtests/results/volatility_rebalance_comparison.csv",
                           output_dir="backtests/results"):
    """
    Create visualization plots for rebalance period comparison.
    
    Args:
        comparison_file (str): Path to comparison CSV file
        output_dir (str): Directory to save plots
    """
    # Load comparison data
    df = pd.read_csv(comparison_file)
    df = df.sort_values("rebalance_days")
    
    # Create figure with subplots
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Volatility Factor: Rebalance Period Comparison', fontsize=16, fontweight='bold')
    
    # 1. Sharpe Ratio
    ax = axes[0, 0]
    bars = ax.bar(df['rebalance_days'].astype(str), df['sharpe_ratio'], color='steelblue', alpha=0.8)
    # Highlight best
    best_idx = df['sharpe_ratio'].idxmax()
    bars[best_idx].set_color('darkgreen')
    ax.set_xlabel('Rebalance Period (days)', fontweight='bold')
    ax.set_ylabel('Sharpe Ratio', fontweight='bold')
    ax.set_title('Sharpe Ratio by Rebalance Period', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    # Add value labels
    for i, (x, y) in enumerate(zip(df['rebalance_days'].astype(str), df['sharpe_ratio'])):
        ax.text(i, y + 0.02, f'{y:.3f}', ha='center', va='bottom', fontsize=9)
    
    # 2. Annualized Return
    ax = axes[0, 1]
    bars = ax.bar(df['rebalance_days'].astype(str), df['annualized_return'] * 100, color='orange', alpha=0.8)
    # Highlight best
    best_idx = df['annualized_return'].idxmax()
    bars[best_idx].set_color('darkgreen')
    ax.set_xlabel('Rebalance Period (days)', fontweight='bold')
    ax.set_ylabel('Annualized Return (%)', fontweight='bold')
    ax.set_title('Annualized Return by Rebalance Period', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    # Add value labels
    for i, (x, y) in enumerate(zip(df['rebalance_days'].astype(str), df['annualized_return'] * 100)):
        ax.text(i, y + 0.5, f'{y:.1f}%', ha='center', va='bottom', fontsize=9)
    
    # 3. Maximum Drawdown
    ax = axes[0, 2]
    bars = ax.bar(df['rebalance_days'].astype(str), df['max_drawdown'] * 100, color='red', alpha=0.8)
    # Highlight best (least negative)
    best_idx = df['max_drawdown'].idxmax()
    bars[best_idx].set_color('darkgreen')
    ax.set_xlabel('Rebalance Period (days)', fontweight='bold')
    ax.set_ylabel('Maximum Drawdown (%)', fontweight='bold')
    ax.set_title('Maximum Drawdown by Rebalance Period', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    # Add value labels
    for i, (x, y) in enumerate(zip(df['rebalance_days'].astype(str), df['max_drawdown'] * 100)):
        ax.text(i, y - 1, f'{y:.1f}%', ha='center', va='top', fontsize=9)
    
    # 4. Annualized Volatility
    ax = axes[1, 0]
    bars = ax.bar(df['rebalance_days'].astype(str), df['annualized_volatility'] * 100, color='purple', alpha=0.8)
    # Highlight best (lowest)
    best_idx = df['annualized_volatility'].idxmin()
    bars[best_idx].set_color('darkgreen')
    ax.set_xlabel('Rebalance Period (days)', fontweight='bold')
    ax.set_ylabel('Annualized Volatility (%)', fontweight='bold')
    ax.set_title('Annualized Volatility by Rebalance Period', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    # Add value labels
    for i, (x, y) in enumerate(zip(df['rebalance_days'].astype(str), df['annualized_volatility'] * 100)):
        ax.text(i, y + 0.3, f'{y:.1f}%', ha='center', va='bottom', fontsize=9)
    
    # 5. Number of Trades
    ax = axes[1, 1]
    bars = ax.bar(df['rebalance_days'].astype(str), df['num_trades'], color='teal', alpha=0.8)
    ax.set_xlabel('Rebalance Period (days)', fontweight='bold')
    ax.set_ylabel('Number of Trades', fontweight='bold')
    ax.set_title('Total Number of Trades by Rebalance Period', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    # Add value labels
    for i, (x, y) in enumerate(zip(df['rebalance_days'].astype(str), df['num_trades'])):
        ax.text(i, y + 50, f'{y:,.0f}', ha='center', va='bottom', fontsize=9)
    
    # 6. Win Rate
    ax = axes[1, 2]
    bars = ax.bar(df['rebalance_days'].astype(str), df['win_rate'] * 100, color='green', alpha=0.8)
    # Highlight best
    best_idx = df['win_rate'].idxmax()
    bars[best_idx].set_color('darkgreen')
    ax.set_xlabel('Rebalance Period (days)', fontweight='bold')
    ax.set_ylabel('Win Rate (%)', fontweight='bold')
    ax.set_title('Win Rate by Rebalance Period', fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    ax.axhline(y=50, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='50% baseline')
    ax.legend()
    # Add value labels
    for i, (x, y) in enumerate(zip(df['rebalance_days'].astype(str), df['win_rate'] * 100)):
        ax.text(i, y + 0.3, f'{y:.1f}%', ha='center', va='bottom', fontsize=9)
    
    plt.tight_layout()
    
    # Save plot
    plot_file = os.path.join(output_dir, "volatility_rebalance_comparison.png")
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"\n✓ Comparison plot saved to: {plot_file}")
    plt.close()
    
    # Create a second figure showing portfolio performance over time
    create_portfolio_comparison_plot(df, output_dir)


def create_portfolio_comparison_plot(df, output_dir):
    """
    Create a line plot comparing portfolio performance over time for different rebalance periods.
    
    Args:
        df (pd.DataFrame): Comparison dataframe
        output_dir (str): Directory to save plots
    """
    fig, ax = plt.subplots(figsize=(12, 7))
    
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
    
    # Load portfolio values for each rebalance period
    for idx, (_, row) in enumerate(df.iterrows()):
        rebalance_days = int(row['rebalance_days'])
        portfolio_file = os.path.join(
            output_dir,
            f"volatility_rebalance_{rebalance_days}d_portfolio_values.csv"
        )
        
        if os.path.exists(portfolio_file):
            portfolio_df = pd.read_csv(portfolio_file)
            portfolio_df['date'] = pd.to_datetime(portfolio_df['date'])
            
            # Plot portfolio value
            label = f"{rebalance_days}d (Sharpe: {row['sharpe_ratio']:.3f})"
            ax.plot(portfolio_df['date'], portfolio_df['portfolio_value'], 
                   label=label, linewidth=2, alpha=0.8, color=colors[idx % len(colors)])
    
    ax.set_xlabel('Date', fontweight='bold', fontsize=12)
    ax.set_ylabel('Portfolio Value ($)', fontweight='bold', fontsize=12)
    ax.set_title('Volatility Factor: Portfolio Value Over Time by Rebalance Period', 
                fontweight='bold', fontsize=14)
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=10000, color='black', linestyle='--', linewidth=1, alpha=0.5, label='Initial Capital')
    
    # Format y-axis
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    plt.tight_layout()
    
    # Save plot
    plot_file = os.path.join(output_dir, "volatility_rebalance_portfolio_comparison.png")
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    print(f"✓ Portfolio comparison plot saved to: {plot_file}")
    plt.close()


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Visualize Volatility Factor Rebalance Period Comparison"
    )
    parser.add_argument(
        "--comparison-file",
        type=str,
        default="backtests/results/volatility_rebalance_comparison.csv",
        help="Path to comparison CSV file",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="backtests/results",
        help="Output directory for plots",
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("CREATING VOLATILITY REBALANCE COMPARISON VISUALIZATIONS")
    print("=" * 80)
    
    create_comparison_plots(args.comparison_file, args.output_dir)
    
    print("\n" + "=" * 80)
    print("VISUALIZATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
