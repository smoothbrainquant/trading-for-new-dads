#!/usr/bin/env python3
"""
Visualize Historical Dilution Trends

Creates visualizations showing:
- Dilution progression over time for top coins
- Correlation between dilution and price performance
- Token unlock schedules comparison
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime


def load_data():
    """Load historical dilution data."""
    historical_df = pd.read_csv('crypto_dilution_historical_2021_2025.csv')
    velocity_df = pd.read_csv('crypto_dilution_velocity_2021_2025.csv')
    
    # Parse dates
    historical_df['date'] = pd.to_datetime(historical_df['date'])
    velocity_df['start_date'] = pd.to_datetime(velocity_df['start_date'])
    velocity_df['end_date'] = pd.to_datetime(velocity_df['end_date'])
    
    return historical_df, velocity_df


def plot_circulating_supply_progression(historical_df, top_n=15):
    """
    Plot circulating supply % over time for top diluting coins.
    
    Args:
        historical_df (pd.DataFrame): Historical dilution data
        top_n (int): Number of coins to show
    """
    # Get coins with most dilution
    latest_date = historical_df['date'].max()
    latest_data = historical_df[historical_df['date'] == latest_date].copy()
    
    # Get top coins by current market cap that have max_supply
    top_coins = latest_data[latest_data['max_supply'].notna()].nlargest(top_n, 'Market Cap')
    
    fig, ax = plt.subplots(figsize=(14, 8))
    
    for symbol in top_coins['Symbol']:
        coin_data = historical_df[historical_df['Symbol'] == symbol].sort_values('date')
        if len(coin_data) > 1:
            ax.plot(coin_data['date'], coin_data['circulating_pct'], 
                   marker='o', label=symbol, linewidth=2, markersize=4)
    
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Circulating Supply %', fontsize=12)
    ax.set_title(f'Token Circulation Progress Over Time (Top {top_n} by Market Cap)', fontsize=14, fontweight='bold')
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 105)
    
    plt.tight_layout()
    plt.savefig('dilution_progression_top_coins.png', dpi=300, bbox_inches='tight')
    print(f"? Saved: dilution_progression_top_coins.png")
    plt.close()


def plot_dilution_vs_performance(velocity_df):
    """
    Scatter plot of dilution velocity vs price performance.
    
    Args:
        velocity_df (pd.DataFrame): Dilution velocity data
    """
    # Filter valid data
    valid_data = velocity_df[
        velocity_df['price_return_pct'].notna() & 
        velocity_df['dilution_velocity_pct_per_year'].notna()
    ].copy()
    
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Color by dilution category
    colors = []
    for dilution in valid_data['dilution_velocity_pct_per_year']:
        if dilution < 0:
            colors.append('green')
        elif dilution < 5:
            colors.append('blue')
        elif dilution < 10:
            colors.append('orange')
        else:
            colors.append('red')
    
    # Size by market cap
    sizes = np.log10(valid_data['market_cap_end'] + 1) * 20
    
    scatter = ax.scatter(valid_data['dilution_velocity_pct_per_year'], 
                        valid_data['price_return_pct'],
                        c=colors, s=sizes, alpha=0.6, edgecolors='black', linewidth=0.5)
    
    # Add labels for notable coins
    for idx, row in valid_data.iterrows():
        # Label top performers and biggest diluters
        if (row['price_return_pct'] > 500 or 
            row['dilution_velocity_pct_per_year'] > 20 or
            row['price_return_pct'] < -70):
            ax.annotate(row['symbol'], 
                       (row['dilution_velocity_pct_per_year'], row['price_return_pct']),
                       fontsize=8, alpha=0.8, 
                       xytext=(5, 5), textcoords='offset points')
    
    # Add trend line
    z = np.polyfit(valid_data['dilution_velocity_pct_per_year'], valid_data['price_return_pct'], 1)
    p = np.poly1d(z)
    x_trend = np.linspace(valid_data['dilution_velocity_pct_per_year'].min(), 
                          valid_data['dilution_velocity_pct_per_year'].max(), 100)
    ax.plot(x_trend, p(x_trend), "r--", alpha=0.5, linewidth=2, label='Trend line')
    
    # Add reference lines
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.3)
    ax.axvline(x=0, color='black', linestyle='-', linewidth=1, alpha=0.3)
    
    ax.set_xlabel('Dilution Velocity (% per year)', fontsize=12)
    ax.set_ylabel('Price Return % (2021-2025)', fontsize=12)
    ax.set_title('Token Dilution vs Price Performance (2021-2025)', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='green', label='Deflationary (<0%)'),
        Patch(facecolor='blue', label='Low Dilution (0-5%)'),
        Patch(facecolor='orange', label='Medium Dilution (5-10%)'),
        Patch(facecolor='red', label='High Dilution (>10%)')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
    
    # Add correlation text
    corr = valid_data['dilution_velocity_pct_per_year'].corr(valid_data['price_return_pct'])
    ax.text(0.02, 0.98, f'Correlation: {corr:.3f}', 
           transform=ax.transAxes, fontsize=11, verticalalignment='top',
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.tight_layout()
    plt.savefig('dilution_vs_performance.png', dpi=300, bbox_inches='tight')
    print(f"? Saved: dilution_vs_performance.png")
    plt.close()


def plot_aggressive_unlockers(velocity_df, top_n=20):
    """
    Bar chart of most aggressive unlock schedules.
    
    Args:
        velocity_df (pd.DataFrame): Dilution velocity data
        top_n (int): Number of coins to show
    """
    top_diluters = velocity_df.nlargest(top_n, 'dilution_velocity_pct_per_year')
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    
    # Chart 1: Dilution velocity
    colors1 = ['red' if x < 0 else 'orange' for x in top_diluters['price_return_pct']]
    ax1.barh(range(len(top_diluters)), top_diluters['dilution_velocity_pct_per_year'], 
            color=colors1, alpha=0.7, edgecolor='black')
    ax1.set_yticks(range(len(top_diluters)))
    ax1.set_yticklabels(top_diluters['symbol'], fontsize=10)
    ax1.set_xlabel('Dilution Velocity (% per year)', fontsize=11)
    ax1.set_title(f'Top {top_n} Most Aggressive Unlock Schedules', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='x')
    ax1.invert_yaxis()
    
    # Chart 2: Their price performance
    colors2 = ['green' if x > 0 else 'red' for x in top_diluters['price_return_pct']]
    ax2.barh(range(len(top_diluters)), top_diluters['price_return_pct'], 
            color=colors2, alpha=0.7, edgecolor='black')
    ax2.set_yticks(range(len(top_diluters)))
    ax2.set_yticklabels(top_diluters['symbol'], fontsize=10)
    ax2.set_xlabel('Price Return % (2021-2025)', fontsize=11)
    ax2.set_title('Their Price Performance', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='x')
    ax2.axvline(x=0, color='black', linestyle='-', linewidth=1)
    ax2.invert_yaxis()
    
    plt.tight_layout()
    plt.savefig('aggressive_unlockers.png', dpi=300, bbox_inches='tight')
    print(f"? Saved: aggressive_unlockers.png")
    plt.close()


def plot_dilution_categories_performance(velocity_df):
    """
    Box plot showing price performance by dilution category.
    
    Args:
        velocity_df (pd.DataFrame): Dilution velocity data
    """
    valid_data = velocity_df[
        velocity_df['price_return_pct'].notna() & 
        velocity_df['dilution_velocity_pct_per_year'].notna()
    ].copy()
    
    # Categorize
    valid_data['dilution_category'] = pd.cut(
        valid_data['dilution_velocity_pct_per_year'],
        bins=[-np.inf, 0, 5, 10, np.inf],
        labels=['Deflationary\n(<0%)', 'Low Dilution\n(0-5%)', 'Medium Dilution\n(5-10%)', 'High Dilution\n(>10%)']
    )
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    categories = ['Deflationary\n(<0%)', 'Low Dilution\n(0-5%)', 'Medium Dilution\n(5-10%)', 'High Dilution\n(>10%)']
    data_to_plot = [valid_data[valid_data['dilution_category'] == cat]['price_return_pct'].values 
                    for cat in categories]
    
    bp = ax.boxplot(data_to_plot, labels=categories, patch_artist=True,
                   showmeans=True, meanline=True,
                   boxprops=dict(facecolor='lightblue', alpha=0.7),
                   medianprops=dict(color='red', linewidth=2),
                   meanprops=dict(color='green', linewidth=2, linestyle='--'))
    
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.3)
    ax.set_ylabel('Price Return % (2021-2025)', fontsize=12)
    ax.set_title('Price Performance by Dilution Category', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    # Add sample sizes
    for i, cat in enumerate(categories):
        count = len(data_to_plot[i])
        median = np.median(data_to_plot[i])
        mean = np.mean(data_to_plot[i])
        ax.text(i+1, ax.get_ylim()[0], f'n={count}\n?={mean:.0f}%\nM={median:.0f}%', 
               ha='center', va='top', fontsize=9, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='red', linewidth=2, label='Median'),
        Line2D([0], [0], color='green', linewidth=2, linestyle='--', label='Mean')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=10)
    
    plt.tight_layout()
    plt.savefig('dilution_categories_performance.png', dpi=300, bbox_inches='tight')
    print(f"? Saved: dilution_categories_performance.png")
    plt.close()


def plot_selected_coins_timeline(historical_df, coins_of_interest):
    """
    Plot detailed timeline for selected coins of interest.
    
    Args:
        historical_df (pd.DataFrame): Historical dilution data
        coins_of_interest (list): List of symbols to plot
    """
    fig, axes = plt.subplots(len(coins_of_interest), 1, figsize=(14, 4*len(coins_of_interest)), sharex=True)
    
    if len(coins_of_interest) == 1:
        axes = [axes]
    
    for ax, symbol in zip(axes, coins_of_interest):
        coin_data = historical_df[historical_df['Symbol'] == symbol].sort_values('date')
        
        if len(coin_data) == 0:
            continue
        
        # Twin axis for price
        ax2 = ax.twinx()
        
        # Plot circulating %
        ax.fill_between(coin_data['date'], 0, coin_data['circulating_pct'], 
                        alpha=0.3, color='blue', label='Circulating %')
        ax.plot(coin_data['date'], coin_data['circulating_pct'], 
               color='blue', linewidth=2, marker='o', markersize=5)
        
        # Plot price on secondary axis
        ax2.plot(coin_data['date'], coin_data['Price'], 
                color='green', linewidth=2, marker='s', markersize=4, alpha=0.7, label='Price')
        
        ax.set_ylabel('Circulating %', fontsize=11, color='blue')
        ax2.set_ylabel('Price (USD)', fontsize=11, color='green')
        ax.tick_params(axis='y', labelcolor='blue')
        ax2.tick_params(axis='y', labelcolor='green')
        
        coin_name = coin_data.iloc[0]['Name']
        ax.set_title(f'{symbol} ({coin_name}) - Dilution vs Price', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 105)
        
        # Add stats box
        start_circ = coin_data.iloc[0]['circulating_pct']
        end_circ = coin_data.iloc[-1]['circulating_pct']
        circ_change = end_circ - start_circ
        
        start_price = coin_data.iloc[0]['Price']
        end_price = coin_data.iloc[-1]['Price']
        price_change = ((end_price - start_price) / start_price) * 100 if start_price > 0 else 0
        
        stats_text = f'Circ: {start_circ:.1f}% ? {end_circ:.1f}% (+{circ_change:.1f}%)\nPrice: ${start_price:.2f} ? ${end_price:.2f} ({price_change:+.1f}%)'
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
               fontsize=9, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))
    
    axes[-1].set_xlabel('Date', fontsize=12)
    plt.tight_layout()
    plt.savefig('selected_coins_timeline.png', dpi=300, bbox_inches='tight')
    print(f"? Saved: selected_coins_timeline.png")
    plt.close()


def main():
    """Main execution function."""
    print("=" * 80)
    print("VISUALIZING HISTORICAL DILUTION TRENDS")
    print("=" * 80)
    
    # Load data
    print("\nLoading data...")
    historical_df, velocity_df = load_data()
    print(f"? Loaded historical data: {len(historical_df)} records")
    print(f"? Loaded velocity data: {len(velocity_df)} coins")
    
    # Generate visualizations
    print("\nGenerating visualizations...")
    
    print("\n1. Circulating supply progression for top coins...")
    plot_circulating_supply_progression(historical_df, top_n=15)
    
    print("\n2. Dilution vs performance scatter plot...")
    plot_dilution_vs_performance(velocity_df)
    
    print("\n3. Most aggressive unlock schedules...")
    plot_aggressive_unlockers(velocity_df, top_n=20)
    
    print("\n4. Performance by dilution category...")
    plot_dilution_categories_performance(velocity_df)
    
    print("\n5. Detailed timelines for selected coins...")
    # Select interesting coins: high diluters, good performers, mix
    coins_of_interest = ['SOL', 'AVAX', 'HBAR', 'SUI', 'IMX']
    plot_selected_coins_timeline(historical_df, coins_of_interest)
    
    print("\n" + "=" * 80)
    print("VISUALIZATION COMPLETE")
    print("=" * 80)
    print("\nGenerated files:")
    print("  - dilution_progression_top_coins.png")
    print("  - dilution_vs_performance.png")
    print("  - aggressive_unlockers.png")
    print("  - dilution_categories_performance.png")
    print("  - selected_coins_timeline.png")


if __name__ == "__main__":
    main()
