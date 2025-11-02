#!/usr/bin/env python3
"""
Historical Dilution Analysis (2021-2025)

This script analyzes how token dilution has progressed over time for top cryptocurrencies.
It tracks circulating supply changes and correlates dilution with price performance.

Key metrics:
- Circulating supply growth over time
- Dilution velocity (tokens unlocked per year)
- Price performance vs dilution rate
- Coins that had the most aggressive unlock schedules
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os


def load_current_supply_data(filepath='crypto_dilution_top150.csv'):
    """
    Load current supply data to get max supply reference.
    
    Args:
        filepath (str): Path to current dilution data
        
    Returns:
        pd.DataFrame: Current supply data with max_supply info
    """
    if not os.path.exists(filepath):
        print(f"WARNING: {filepath} not found. Using default path...")
        filepath = '/workspace/crypto_dilution_top150.csv'
    
    df = pd.read_csv(filepath)
    print(f"Loaded current data for {len(df)} coins")
    return df


def load_historical_snapshots(filepath='data/raw/coinmarketcap_monthly_all_snapshots.csv'):
    """
    Load historical monthly snapshots.
    
    Args:
        filepath (str): Path to historical snapshots
        
    Returns:
        pd.DataFrame: Historical data with parsed dates
    """
    if not os.path.exists(filepath):
        filepath = '/workspace/data/raw/coinmarketcap_monthly_all_snapshots.csv'
    
    df = pd.read_csv(filepath)
    
    # Parse snapshot_date (format: YYYYMMDD)
    df['date'] = pd.to_datetime(df['snapshot_date'], format='%Y%m%d')
    
    # Filter to 2021 onwards
    df = df[df['date'] >= '2021-01-01'].copy()
    
    print(f"Loaded {len(df)} historical records from {df['date'].min()} to {df['date'].max()}")
    print(f"Covering {df['Symbol'].nunique()} unique symbols across {df['date'].nunique()} dates")
    
    return df


def calculate_historical_dilution_metrics(historical_df, current_df):
    """
    Calculate dilution metrics over time by tracking circulating supply changes.
    
    Args:
        historical_df (pd.DataFrame): Historical snapshots
        current_df (pd.DataFrame): Current supply data with max_supply
        
    Returns:
        pd.DataFrame: Dilution metrics over time
    """
    # Merge current max_supply into historical data
    max_supply_map = current_df.set_index('symbol')[['max_supply', 'name']].to_dict()
    
    historical_df['max_supply'] = historical_df['Symbol'].map(max_supply_map['max_supply'])
    historical_df['coin_name'] = historical_df['Symbol'].map(max_supply_map['name'])
    
    # Calculate circulating % and dilution metrics for each snapshot
    historical_df['circulating_pct'] = np.where(
        historical_df['max_supply'].notna() & (historical_df['max_supply'] > 0),
        (historical_df['Circulating Supply'] / historical_df['max_supply']) * 100,
        np.nan
    )
    
    historical_df['locked_tokens'] = np.where(
        historical_df['max_supply'].notna(),
        historical_df['max_supply'] - historical_df['Circulating Supply'],
        np.nan
    )
    
    historical_df['potential_dilution_pct'] = np.where(
        (historical_df['max_supply'].notna()) & (historical_df['Circulating Supply'] > 0),
        ((historical_df['max_supply'] - historical_df['Circulating Supply']) / historical_df['Circulating Supply']) * 100,
        np.nan
    )
    
    return historical_df


def analyze_dilution_velocity(historical_df):
    """
    Calculate dilution velocity (token unlock rate over time) for each coin.
    
    Args:
        historical_df (pd.DataFrame): Historical data with dilution metrics
        
    Returns:
        pd.DataFrame: Summary of dilution velocity by coin
    """
    results = []
    
    # Only analyze coins with max_supply defined
    coins_with_max = historical_df[historical_df['max_supply'].notna()]['Symbol'].unique()
    
    for symbol in coins_with_max:
        coin_data = historical_df[historical_df['Symbol'] == symbol].sort_values('date')
        
        if len(coin_data) < 2:
            continue
        
        # Get first and last snapshots
        first = coin_data.iloc[0]
        last = coin_data.iloc[-1]
        
        # Calculate changes
        days_elapsed = (last['date'] - first['date']).days
        years_elapsed = days_elapsed / 365.25
        
        if years_elapsed == 0:
            continue
        
        circ_change = last['Circulating Supply'] - first['Circulating Supply']
        circ_pct_start = first['circulating_pct']
        circ_pct_end = last['circulating_pct']
        circ_pct_change = circ_pct_end - circ_pct_start
        
        # Price performance
        price_start = first['Price']
        price_end = last['Price']
        price_return = ((price_end - price_start) / price_start) * 100 if price_start > 0 else np.nan
        
        # Dilution velocity (tokens per year)
        dilution_velocity = circ_change / years_elapsed
        dilution_pct_per_year = circ_pct_change / years_elapsed
        
        results.append({
            'symbol': symbol,
            'name': first.get('coin_name', first['Name']),
            'max_supply': first['max_supply'],
            'start_date': first['date'],
            'end_date': last['date'],
            'years_elapsed': years_elapsed,
            'circ_supply_start': first['Circulating Supply'],
            'circ_supply_end': last['Circulating Supply'],
            'circ_pct_start': circ_pct_start,
            'circ_pct_end': circ_pct_end,
            'tokens_unlocked': circ_change,
            'dilution_velocity_tokens_per_year': dilution_velocity,
            'dilution_velocity_pct_per_year': dilution_pct_per_year,
            'price_start': price_start,
            'price_end': price_end,
            'price_return_pct': price_return,
            'market_cap_start': first['Market Cap'],
            'market_cap_end': last['Market Cap'],
            'rank_start': first['Rank'],
            'rank_end': last['Rank'],
        })
    
    df = pd.DataFrame(results)
    return df


def analyze_dilution_vs_performance(velocity_df):
    """
    Analyze correlation between dilution rate and price performance.
    
    Args:
        velocity_df (pd.DataFrame): Dilution velocity data
        
    Returns:
        dict: Analysis results
    """
    # Filter to coins with valid data
    valid_data = velocity_df[
        velocity_df['price_return_pct'].notna() & 
        velocity_df['dilution_velocity_pct_per_year'].notna()
    ].copy()
    
    if len(valid_data) < 10:
        return {'error': 'Insufficient data for correlation analysis'}
    
    # Calculate correlation
    correlation = valid_data['dilution_velocity_pct_per_year'].corr(valid_data['price_return_pct'])
    
    # Categorize by dilution rate
    valid_data['dilution_category'] = pd.cut(
        valid_data['dilution_velocity_pct_per_year'],
        bins=[-np.inf, 0, 5, 10, np.inf],
        labels=['Deflationary', 'Low Dilution', 'Medium Dilution', 'High Dilution']
    )
    
    category_performance = valid_data.groupby('dilution_category').agg({
        'price_return_pct': ['mean', 'median', 'count']
    }).round(2)
    
    return {
        'correlation': correlation,
        'category_performance': category_performance,
        'valid_samples': len(valid_data)
    }


def print_historical_analysis(velocity_df, correlation_results):
    """
    Print comprehensive historical dilution analysis.
    
    Args:
        velocity_df (pd.DataFrame): Dilution velocity data
        correlation_results (dict): Correlation analysis results
    """
    print("\n" + "=" * 80)
    print("HISTORICAL DILUTION ANALYSIS (2021-2025)")
    print("=" * 80)
    
    print(f"\nCoins analyzed: {len(velocity_df)}")
    print(f"Average time period: {velocity_df['years_elapsed'].mean():.2f} years")
    
    # Overall dilution statistics
    print("\n" + "-" * 80)
    print("DILUTION VELOCITY STATISTICS")
    print("-" * 80)
    print(f"Average dilution: {velocity_df['dilution_velocity_pct_per_year'].mean():.2f}% per year")
    print(f"Median dilution: {velocity_df['dilution_velocity_pct_per_year'].median():.2f}% per year")
    print(f"Max dilution: {velocity_df['dilution_velocity_pct_per_year'].max():.2f}% per year ({velocity_df.loc[velocity_df['dilution_velocity_pct_per_year'].idxmax(), 'symbol']})")
    
    # Most diluted coins
    print("\n" + "-" * 80)
    print("TOP 10 MOST AGGRESSIVE UNLOCK SCHEDULES (Highest Dilution Velocity)")
    print("-" * 80)
    top_dilution = velocity_df.nlargest(10, 'dilution_velocity_pct_per_year')
    display_cols = ['symbol', 'name', 'circ_pct_start', 'circ_pct_end', 'dilution_velocity_pct_per_year', 'price_return_pct']
    print(top_dilution[display_cols].to_string(index=False))
    
    # Least diluted / deflationary
    print("\n" + "-" * 80)
    print("TOP 10 LEAST DILUTED / DEFLATIONARY COINS")
    print("-" * 80)
    least_dilution = velocity_df.nsmallest(10, 'dilution_velocity_pct_per_year')
    print(least_dilution[display_cols].to_string(index=False))
    
    # Correlation analysis
    if 'correlation' in correlation_results:
        print("\n" + "-" * 80)
        print("DILUTION vs PRICE PERFORMANCE CORRELATION")
        print("-" * 80)
        print(f"Correlation coefficient: {correlation_results['correlation']:.3f}")
        print(f"(Negative = dilution hurts price, Positive = dilution doesn't hurt price)")
        print(f"\nSample size: {correlation_results['valid_samples']} coins")
        
        print("\nAverage Returns by Dilution Category:")
        print(correlation_results['category_performance'])
    
    # Top performers despite dilution
    print("\n" + "-" * 80)
    print("TOP PERFORMERS WITH HIGH DILUTION (>5% per year)")
    print("-" * 80)
    high_dilution = velocity_df[velocity_df['dilution_velocity_pct_per_year'] > 5]
    if len(high_dilution) > 0:
        top_performers = high_dilution.nlargest(10, 'price_return_pct')
        print(top_performers[display_cols].to_string(index=False))
    else:
        print("No coins with >5% dilution per year")
    
    # Worst performers with low dilution
    print("\n" + "-" * 80)
    print("WORST PERFORMERS WITH LOW DILUTION (<2% per year)")
    print("-" * 80)
    low_dilution = velocity_df[velocity_df['dilution_velocity_pct_per_year'] < 2]
    if len(low_dilution) > 0:
        worst_performers = low_dilution.nsmallest(10, 'price_return_pct')
        print(worst_performers[display_cols].to_string(index=False))
    else:
        print("No coins with <2% dilution per year")


def save_historical_analysis(historical_df, velocity_df, output_dir=''):
    """
    Save historical analysis results to CSV files.
    
    Args:
        historical_df (pd.DataFrame): Historical data with dilution metrics
        velocity_df (pd.DataFrame): Dilution velocity summary
        output_dir (str): Output directory
    """
    # Save full historical dilution metrics
    historical_output = os.path.join(output_dir, 'crypto_dilution_historical_2021_2025.csv')
    historical_df_export = historical_df[[
        'date', 'Symbol', 'Name', 'Rank', 'Price', 'Market Cap',
        'Circulating Supply', 'max_supply', 'circulating_pct', 
        'potential_dilution_pct', 'locked_tokens'
    ]].copy()
    historical_df_export.to_csv(historical_output, index=False)
    print(f"\n? Saved historical dilution data to: {historical_output}")
    
    # Save velocity summary
    velocity_output = os.path.join(output_dir, 'crypto_dilution_velocity_2021_2025.csv')
    velocity_df.to_csv(velocity_output, index=False)
    print(f"? Saved dilution velocity summary to: {velocity_output}")


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze Historical Crypto Dilution (2021-2025)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--current-data",
        type=str,
        default="crypto_dilution_top150.csv",
        help="Path to current dilution data with max_supply info"
    )
    parser.add_argument(
        "--historical-data",
        type=str,
        default="data/raw/coinmarketcap_monthly_all_snapshots.csv",
        help="Path to historical monthly snapshots"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="",
        help="Output directory for results"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("HISTORICAL CRYPTO DILUTION ANALYSIS")
    print("=" * 80)
    print("\nAnalyzing token unlock velocity and correlation with price performance")
    print("Time period: 2021 - 2025")
    
    # Load data
    print("\n" + "-" * 80)
    print("LOADING DATA")
    print("-" * 80)
    current_df = load_current_supply_data(args.current_data)
    historical_df = load_historical_snapshots(args.historical_data)
    
    # Calculate historical dilution metrics
    print("\n" + "-" * 80)
    print("CALCULATING DILUTION METRICS")
    print("-" * 80)
    historical_df = calculate_historical_dilution_metrics(historical_df, current_df)
    
    # Analyze dilution velocity
    print("\n" + "-" * 80)
    print("ANALYZING DILUTION VELOCITY")
    print("-" * 80)
    velocity_df = analyze_dilution_velocity(historical_df)
    print(f"Calculated dilution velocity for {len(velocity_df)} coins")
    
    # Correlation analysis
    print("\n" + "-" * 80)
    print("CORRELATION ANALYSIS")
    print("-" * 80)
    correlation_results = analyze_dilution_vs_performance(velocity_df)
    
    # Print comprehensive analysis
    print_historical_analysis(velocity_df, correlation_results)
    
    # Save results
    save_historical_analysis(historical_df, velocity_df, args.output_dir)
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
