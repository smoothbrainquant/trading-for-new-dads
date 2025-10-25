"""
Backtest Size Factor by Bucket - Annual Returns and Sharpe Ratios

This script analyzes performance by size bucket (quintile) on an annual basis.
Only includes coins with market cap >= $500M to focus on established assets.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse


def load_cmc_snapshots(filepath):
    """Load CoinMarketCap historical snapshots."""
    df = pd.read_csv(filepath)
    df['snapshot_date'] = pd.to_datetime(df['snapshot_date'], format='%Y%m%d')
    df.columns = [col.strip() for col in df.columns]
    df = df.sort_values(['snapshot_date', 'Rank']).reset_index(drop=True)
    return df


def filter_data(df, min_market_cap=500_000_000):
    """
    Filter out stablecoins, weird tokens, and coins below market cap threshold.
    
    Args:
        df (pd.DataFrame): CoinMarketCap snapshot data
        min_market_cap (float): Minimum market cap in USD
        
    Returns:
        pd.DataFrame: Filtered data
    """
    # Known stablecoins
    stablecoin_symbols = [
        'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP', 'USDD', 'GUSD', 'FRAX',
        'USDK', 'PAX', 'HUSD', 'SUSD', 'USDS', 'LUSD', 'USDX', 'UST', 'OUSD',
        'USDN', 'FEI', 'EUROC', 'EURS', 'EURT', 'XAUT', 'PAXG', 'USDE', 'sUSD',
        'MAI', 'MIM', 'USTC', 'USDJ', 'CUSD', 'RSV', 'DUSD', 'USDQ', 'QCAD'
    ]
    
    print(f"\nOriginal data: {len(df)} rows")
    
    # Filter by market cap
    df = df[df['Market Cap'] >= min_market_cap]
    print(f"After market cap >= ${min_market_cap:,.0f} filter: {len(df)} rows")
    
    # Filter out stablecoins
    df = df[~df['Symbol'].isin(stablecoin_symbols)]
    df = df[~df['Name'].str.contains('USD', case=False, na=False) | 
            ~df['Name'].str.contains('Dollar', case=False, na=False)]
    print(f"After stablecoin filter: {len(df)} rows")
    
    # Filter out suspicious tokens
    df = df[~df['Symbol'].str.match(r'^\d+$')]
    df = df[df['Symbol'].str.len() >= 2]
    df = df[df['Volume (24h)'] > 100]
    
    print(f"After weird token filter: {len(df)} rows")
    
    return df


def assign_size_buckets(df_snapshot, num_buckets=5):
    """
    Assign size buckets based on market cap for a single snapshot.
    
    Args:
        df_snapshot (pd.DataFrame): Data for a single snapshot date
        num_buckets (int): Number of size buckets
        
    Returns:
        pd.DataFrame: Data with size_bucket column (1=largest, 5=smallest)
    """
    df = df_snapshot.copy()
    df = df.sort_values('Market Cap', ascending=False)
    
    # Assign buckets
    try:
        df['size_bucket'] = pd.qcut(
            df['Market Cap'], 
            q=num_buckets, 
            labels=range(1, num_buckets + 1),
            duplicates='drop'
        )
    except ValueError:
        # Fall back to rank-based if not enough unique values
        df['size_bucket'] = pd.cut(
            df['Market Cap'].rank(method='first'),
            bins=num_buckets,
            labels=range(1, num_buckets + 1)
        )
    
    df['size_bucket'] = df['size_bucket'].astype(int)
    
    return df


def calculate_bucket_returns(df, num_buckets=5):
    """
    Calculate returns for each size bucket between consecutive snapshots.
    
    Args:
        df (pd.DataFrame): Full dataset with all snapshots
        num_buckets (int): Number of size buckets
        
    Returns:
        pd.DataFrame: Annual returns by bucket
    """
    dates = sorted(df['snapshot_date'].unique())
    
    results = []
    
    for date_idx in range(len(dates) - 1):
        current_date = dates[date_idx]
        next_date = dates[date_idx + 1]
        
        # Get snapshots
        current_snapshot = df[df['snapshot_date'] == current_date].copy()
        next_snapshot = df[df['snapshot_date'] == next_date].copy()
        
        # Assign size buckets based on current snapshot
        current_snapshot = assign_size_buckets(current_snapshot, num_buckets)
        
        # Calculate period info
        period_days = (next_date - current_date).days
        period_years = period_days / 365.25
        period_label = f"{current_date.year}-{next_date.year}"
        
        print(f"\n{'='*80}")
        print(f"Period: {current_date.date()} to {next_date.date()} ({period_days} days)")
        print(f"{'='*80}")
        
        # Calculate returns for each bucket
        for bucket in range(1, num_buckets + 1):
            bucket_coins = current_snapshot[current_snapshot['size_bucket'] == bucket]
            
            if len(bucket_coins) == 0:
                continue
            
            # Calculate returns for coins in this bucket
            returns_list = []
            symbols_tracked = []
            
            for _, coin in bucket_coins.iterrows():
                symbol = coin['Symbol']
                current_price = coin['Price']
                
                # Find price in next snapshot
                next_price_data = next_snapshot[next_snapshot['Symbol'] == symbol]
                
                if len(next_price_data) > 0:
                    next_price = next_price_data['Price'].values[0]
                    price_return = (next_price - current_price) / current_price
                    log_return = np.log(next_price / current_price)
                    
                    returns_list.append(price_return)
                    symbols_tracked.append(symbol)
            
            if len(returns_list) == 0:
                continue
            
            # Calculate statistics
            returns_array = np.array(returns_list)
            
            # Equal-weighted portfolio return
            mean_return = np.mean(returns_array)
            median_return = np.median(returns_array)
            
            # Annualize return
            annualized_return = (1 + mean_return) ** (1 / period_years) - 1
            
            # Standard deviation of returns across coins
            return_std = np.std(returns_array)
            
            # Sharpe ratio (period Sharpe, not annualized)
            # Using cross-sectional std as proxy for risk
            sharpe = mean_return / return_std if return_std > 0 else 0
            
            # Annualized Sharpe (approximate)
            annualized_sharpe = sharpe * np.sqrt(1 / period_years) if period_years > 0 else sharpe
            
            # Win rate
            win_rate = np.sum(returns_array > 0) / len(returns_array)
            
            # Market cap stats
            bucket_mcap_min = bucket_coins['Market Cap'].min()
            bucket_mcap_max = bucket_coins['Market Cap'].max()
            bucket_mcap_median = bucket_coins['Market Cap'].median()
            
            # Top/bottom performers
            top_performers = sorted(zip(symbols_tracked, returns_list), key=lambda x: x[1], reverse=True)[:3]
            bottom_performers = sorted(zip(symbols_tracked, returns_list), key=lambda x: x[1])[:3]
            
            print(f"\nBucket {bucket} ({'Large' if bucket == 1 else 'Small' if bucket == num_buckets else 'Mid'})")
            print(f"  Coins: {len(returns_list)}/{len(bucket_coins)} tracked")
            print(f"  Market Cap Range: ${bucket_mcap_min:,.0f} - ${bucket_mcap_max:,.0f}")
            print(f"  Median Market Cap: ${bucket_mcap_median:,.0f}")
            print(f"  Mean Return: {mean_return:+.2%}")
            print(f"  Median Return: {median_return:+.2%}")
            print(f"  Annualized Return: {annualized_return:+.2%}")
            print(f"  Cross-sectional Std: {return_std:.2%}")
            print(f"  Sharpe Ratio: {sharpe:.3f}")
            print(f"  Annualized Sharpe: {annualized_sharpe:.3f}")
            print(f"  Win Rate: {win_rate:.1%}")
            print(f"  Top 3: {', '.join([f'{s} ({r:+.1%})' for s, r in top_performers])}")
            print(f"  Bottom 3: {', '.join([f'{s} ({r:+.1%})' for s, r in bottom_performers])}")
            
            results.append({
                'period': period_label,
                'start_date': current_date,
                'end_date': next_date,
                'days': period_days,
                'years': period_years,
                'bucket': bucket,
                'bucket_label': 'Large' if bucket == 1 else 'Small' if bucket == num_buckets else f'Mid-{bucket-1}',
                'num_coins': len(returns_list),
                'total_in_bucket': len(bucket_coins),
                'mcap_min': bucket_mcap_min,
                'mcap_max': bucket_mcap_max,
                'mcap_median': bucket_mcap_median,
                'mean_return': mean_return,
                'median_return': median_return,
                'annualized_return': annualized_return,
                'return_std': return_std,
                'sharpe_ratio': sharpe,
                'annualized_sharpe': annualized_sharpe,
                'win_rate': win_rate,
                'min_return': np.min(returns_array),
                'max_return': np.max(returns_array),
                'top_3': ', '.join([f'{s} ({r:+.1%})' for s, r in top_performers]),
                'bottom_3': ', '.join([f'{s} ({r:+.1%})' for s, r in bottom_performers])
            })
    
    return pd.DataFrame(results)


def print_summary_table(results_df, num_buckets=5):
    """Print summary tables by period and bucket."""
    
    print("\n" + "="*120)
    print("SUMMARY: ANNUAL RETURNS BY SIZE BUCKET")
    print("="*120)
    
    # Pivot table for returns
    pivot_returns = results_df.pivot(index='bucket', columns='period', values='annualized_return')
    pivot_returns['Average'] = results_df.groupby('bucket')['annualized_return'].mean()
    
    print("\nAnnualized Returns by Bucket and Year:")
    print(pivot_returns.to_string(float_format=lambda x: f'{x:+.2%}'))
    
    # Pivot table for Sharpe
    print("\n" + "="*120)
    pivot_sharpe = results_df.pivot(index='bucket', columns='period', values='annualized_sharpe')
    pivot_sharpe['Average'] = results_df.groupby('bucket')['annualized_sharpe'].mean()
    
    print("\nAnnualized Sharpe Ratios by Bucket and Year:")
    print(pivot_sharpe.to_string(float_format=lambda x: f'{x:.3f}'))
    
    # Win rates
    print("\n" + "="*120)
    pivot_winrate = results_df.pivot(index='bucket', columns='period', values='win_rate')
    pivot_winrate['Average'] = results_df.groupby('bucket')['win_rate'].mean()
    
    print("\nWin Rates by Bucket and Year:")
    print(pivot_winrate.to_string(float_format=lambda x: f'{x:.1%}'))
    
    # Market cap ranges
    print("\n" + "="*120)
    print("\nMedian Market Cap by Bucket and Year:")
    pivot_mcap = results_df.pivot(index='bucket', columns='period', values='mcap_median')
    print(pivot_mcap.to_string(float_format=lambda x: f'${x:,.0f}'))
    
    # Summary statistics
    print("\n" + "="*120)
    print("OVERALL STATISTICS BY BUCKET")
    print("="*120)
    
    summary = results_df.groupby('bucket').agg({
        'annualized_return': ['mean', 'std', 'min', 'max'],
        'annualized_sharpe': ['mean', 'std'],
        'win_rate': 'mean',
        'return_std': 'mean',
        'num_coins': 'mean'
    }).round(4)
    
    print(summary.to_string())
    
    # Best/Worst buckets by period
    print("\n" + "="*120)
    print("BEST AND WORST PERFORMING BUCKETS BY PERIOD")
    print("="*120)
    
    for period in results_df['period'].unique():
        period_data = results_df[results_df['period'] == period].sort_values('annualized_return', ascending=False)
        best = period_data.iloc[0]
        worst = period_data.iloc[-1]
        
        print(f"\n{period}:")
        print(f"  Best:  Bucket {int(best['bucket'])} ({best['bucket_label']}) - {best['annualized_return']:+.2%} (Sharpe: {best['annualized_sharpe']:.3f})")
        print(f"  Worst: Bucket {int(worst['bucket'])} ({worst['bucket_label']}) - {worst['annualized_return']:+.2%} (Sharpe: {worst['annualized_sharpe']:.3f})")


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(
        description='Analyze Size Factor Returns by Bucket and Year',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--data',
        type=str,
        default='coinmarketcap_historical_all_snapshots.csv',
        help='Path to CoinMarketCap snapshots CSV file'
    )
    parser.add_argument(
        '--min-market-cap',
        type=float,
        default=500_000_000,
        help='Minimum market cap in USD (default: 500M)'
    )
    parser.add_argument(
        '--num-buckets',
        type=int,
        default=5,
        help='Number of size buckets (quintiles)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='backtest_cmc_annual_bucket_returns.csv',
        help='Output CSV filename'
    )
    
    args = parser.parse_args()
    
    print("="*80)
    print("SIZE FACTOR ANALYSIS - ANNUAL RETURNS BY BUCKET")
    print("="*80)
    print(f"\nConfiguration:")
    print(f"  Data file: {args.data}")
    print(f"  Minimum market cap: ${args.min_market_cap:,.0f}")
    print(f"  Number of buckets: {args.num_buckets}")
    print("="*80)
    
    # Load data
    print(f"\nLoading data from {args.data}...")
    df = load_cmc_snapshots(args.data)
    print(f"Loaded {len(df)} rows")
    print(f"Snapshots: {sorted(df['snapshot_date'].unique())}")
    print(f"Unique symbols: {df['Symbol'].nunique()}")
    
    # Filter data
    print(f"\nFiltering data (min market cap: ${args.min_market_cap:,.0f})...")
    df = filter_data(df, min_market_cap=args.min_market_cap)
    
    print(f"\nCoins per snapshot after filtering:")
    for date in sorted(df['snapshot_date'].unique()):
        snapshot = df[df['snapshot_date'] == date]
        print(f"  {date.date()}: {len(snapshot)} coins")
    
    # Calculate bucket returns
    print("\nCalculating bucket returns...")
    results_df = calculate_bucket_returns(df, num_buckets=args.num_buckets)
    
    # Print summary tables
    print_summary_table(results_df, num_buckets=args.num_buckets)
    
    # Save results
    results_df.to_csv(args.output, index=False)
    print(f"\n{'='*80}")
    print(f"Results saved to: {args.output}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
