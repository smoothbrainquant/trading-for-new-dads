"""
Long vs Short Performance Analysis by Year

Analyzes what would happen if you went long vs short each size bucket by year.
Shows which strategy (long small/short large, etc.) would have worked best.
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
    """Filter out stablecoins and low market cap coins."""
    stablecoin_symbols = [
        'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP', 'USDD', 'GUSD', 'FRAX',
        'USDK', 'PAX', 'HUSD', 'SUSD', 'USDS', 'LUSD', 'USDX', 'UST', 'OUSD',
        'USDN', 'FEI', 'EUROC', 'EURS', 'EURT', 'XAUT', 'PAXG', 'USDE', 'sUSD',
        'MAI', 'MIM', 'USTC', 'USDJ', 'CUSD', 'RSV', 'DUSD', 'USDQ', 'QCAD'
    ]
    
    df = df[df['Market Cap'] >= min_market_cap]
    df = df[~df['Symbol'].isin(stablecoin_symbols)]
    df = df[~df['Name'].str.contains('USD', case=False, na=False) | 
            ~df['Name'].str.contains('Dollar', case=False, na=False)]
    df = df[~df['Symbol'].str.match(r'^\d+$')]
    df = df[df['Symbol'].str.len() >= 2]
    df = df[df['Volume (24h)'] > 100]
    
    return df


def assign_size_buckets(df_snapshot, num_buckets=5):
    """Assign size buckets based on market cap."""
    df = df_snapshot.copy()
    df = df.sort_values('Market Cap', ascending=False)
    
    try:
        df['size_bucket'] = pd.qcut(
            df['Market Cap'], 
            q=num_buckets, 
            labels=range(1, num_buckets + 1),
            duplicates='drop'
        )
    except ValueError:
        df['size_bucket'] = pd.cut(
            df['Market Cap'].rank(method='first'),
            bins=num_buckets,
            labels=range(1, num_buckets + 1)
        )
    
    df['size_bucket'] = df['size_bucket'].astype(int)
    
    return df


def calculate_long_short_performance(df, num_buckets=5):
    """
    Calculate long and short performance for each bucket.
    
    Returns:
        pd.DataFrame: Performance metrics for long and short by bucket and year
    """
    dates = sorted(df['snapshot_date'].unique())
    results = []
    
    for date_idx in range(len(dates) - 1):
        current_date = dates[date_idx]
        next_date = dates[date_idx + 1]
        
        current_snapshot = df[df['snapshot_date'] == current_date].copy()
        next_snapshot = df[df['snapshot_date'] == next_date].copy()
        
        current_snapshot = assign_size_buckets(current_snapshot, num_buckets)
        
        period_days = (next_date - current_date).days
        period_years = period_days / 365.25
        period_label = f"{current_date.year}-{next_date.year}"
        
        print(f"\n{'='*80}")
        print(f"Period: {period_label} ({current_date.date()} to {next_date.date()})")
        print(f"{'='*80}")
        
        # Calculate for each bucket
        for bucket in range(1, num_buckets + 1):
            bucket_coins = current_snapshot[current_snapshot['size_bucket'] == bucket]
            
            if len(bucket_coins) == 0:
                continue
            
            returns_list = []
            
            for _, coin in bucket_coins.iterrows():
                symbol = coin['Symbol']
                current_price = coin['Price']
                
                next_price_data = next_snapshot[next_snapshot['Symbol'] == symbol]
                
                if len(next_price_data) > 0:
                    next_price = next_price_data['Price'].values[0]
                    price_return = (next_price - current_price) / current_price
                    returns_list.append(price_return)
            
            if len(returns_list) == 0:
                continue
            
            returns_array = np.array(returns_list)
            
            # Long performance
            long_mean_return = np.mean(returns_array)
            long_annualized = (1 + long_mean_return) ** (1 / period_years) - 1
            
            # Short performance (inverse of long)
            short_returns = -returns_array
            short_mean_return = np.mean(short_returns)
            short_annualized = (1 + short_mean_return) ** (1 / period_years) - 1 if (1 + short_mean_return) > 0 else -1
            
            # Statistics
            long_std = np.std(returns_array)
            short_std = np.std(short_returns)
            
            long_sharpe = long_mean_return / long_std if long_std > 0 else 0
            short_sharpe = short_mean_return / short_std if short_std > 0 else 0
            
            long_win_rate = np.sum(returns_array > 0) / len(returns_array)
            short_win_rate = np.sum(short_returns > 0) / len(short_returns)
            
            bucket_label = 'Largest' if bucket == 1 else 'Smallest' if bucket == num_buckets else f'Mid-{bucket-1}'
            
            print(f"\nBucket {bucket} ({bucket_label}):")
            print(f"  LONG:  {long_annualized:+.2%} | Sharpe: {long_sharpe:.3f} | Win Rate: {long_win_rate:.1%}")
            print(f"  SHORT: {short_annualized:+.2%} | Sharpe: {short_sharpe:.3f} | Win Rate: {short_win_rate:.1%}")
            
            results.append({
                'period': period_label,
                'start_date': current_date,
                'end_date': next_date,
                'bucket': bucket,
                'bucket_label': bucket_label,
                'position': 'LONG',
                'num_coins': len(returns_list),
                'mean_return': long_mean_return,
                'annualized_return': long_annualized,
                'std': long_std,
                'sharpe': long_sharpe,
                'win_rate': long_win_rate
            })
            
            results.append({
                'period': period_label,
                'start_date': current_date,
                'end_date': next_date,
                'bucket': bucket,
                'bucket_label': bucket_label,
                'position': 'SHORT',
                'num_coins': len(returns_list),
                'mean_return': short_mean_return,
                'annualized_return': short_annualized,
                'std': short_std,
                'sharpe': short_sharpe,
                'win_rate': short_win_rate
            })
    
    return pd.DataFrame(results)


def analyze_strategies(df_results):
    """
    Analyze different long/short strategy combinations.
    
    Strategies:
    1. Long small, Short large
    2. Long large, Short small
    3. Long small only
    4. Long large only
    5. Long mid only
    """
    
    periods = df_results['period'].unique()
    
    strategy_results = []
    
    for period in periods:
        period_data = df_results[df_results['period'] == period]
        
        # Get long and short returns for each bucket
        bucket_returns = {}
        for bucket in [1, 5]:  # 1 = largest, 5 = smallest
            long_data = period_data[(period_data['bucket'] == bucket) & (period_data['position'] == 'LONG')]
            short_data = period_data[(period_data['bucket'] == bucket) & (period_data['position'] == 'SHORT')]
            
            if len(long_data) > 0:
                bucket_returns[f'long_{bucket}'] = long_data['annualized_return'].values[0]
            if len(short_data) > 0:
                bucket_returns[f'short_{bucket}'] = short_data['annualized_return'].values[0]
        
        # Strategy 1: Long small (bucket 5), Short large (bucket 1)
        if 'long_5' in bucket_returns and 'short_1' in bucket_returns:
            strategy_results.append({
                'period': period,
                'strategy': 'Long Small + Short Large',
                'long_bucket': 5,
                'short_bucket': 1,
                'long_return': bucket_returns['long_5'],
                'short_return': bucket_returns['short_1'],
                'combined_return': (bucket_returns['long_5'] + bucket_returns['short_1']) / 2
            })
        
        # Strategy 2: Long large (bucket 1), Short small (bucket 5)
        if 'long_1' in bucket_returns and 'short_5' in bucket_returns:
            strategy_results.append({
                'period': period,
                'strategy': 'Long Large + Short Small',
                'long_bucket': 1,
                'short_bucket': 5,
                'long_return': bucket_returns['long_1'],
                'short_return': bucket_returns['short_5'],
                'combined_return': (bucket_returns['long_1'] + bucket_returns['short_5']) / 2
            })
        
        # Strategy 3: Long small only
        if 'long_5' in bucket_returns:
            strategy_results.append({
                'period': period,
                'strategy': 'Long Small Only',
                'long_bucket': 5,
                'short_bucket': None,
                'long_return': bucket_returns['long_5'],
                'short_return': 0,
                'combined_return': bucket_returns['long_5']
            })
        
        # Strategy 4: Long large only
        if 'long_1' in bucket_returns:
            strategy_results.append({
                'period': period,
                'strategy': 'Long Large Only',
                'long_bucket': 1,
                'short_bucket': None,
                'long_return': bucket_returns['long_1'],
                'short_return': 0,
                'combined_return': bucket_returns['long_1']
            })
    
    return pd.DataFrame(strategy_results)


def print_summary_tables(df_results):
    """Print summary tables for long vs short performance."""
    
    print("\n" + "="*120)
    print("LONG PERFORMANCE BY BUCKET AND YEAR")
    print("="*120)
    
    long_data = df_results[df_results['position'] == 'LONG']
    pivot_long = long_data.pivot(index='bucket', columns='period', values='annualized_return')
    pivot_long['Average'] = long_data.groupby('bucket')['annualized_return'].mean()
    print(pivot_long.to_string(float_format=lambda x: f'{x:+.2%}'))
    
    print("\n" + "="*120)
    print("SHORT PERFORMANCE BY BUCKET AND YEAR")
    print("="*120)
    
    short_data = df_results[df_results['position'] == 'SHORT']
    pivot_short = short_data.pivot(index='bucket', columns='period', values='annualized_return')
    pivot_short['Average'] = short_data.groupby('bucket')['annualized_return'].mean()
    print(pivot_short.to_string(float_format=lambda x: f'{x:+.2%}'))
    
    print("\n" + "="*120)
    print("LONG VS SHORT: WHICH WAS BETTER?")
    print("="*120)
    
    for period in df_results['period'].unique():
        period_data = df_results[df_results['period'] == period]
        print(f"\n{period}:")
        
        for bucket in sorted(df_results['bucket'].unique()):
            long = period_data[(period_data['bucket'] == bucket) & (period_data['position'] == 'LONG')]
            short = period_data[(period_data['bucket'] == bucket) & (period_data['position'] == 'SHORT')]
            
            if len(long) > 0 and len(short) > 0:
                long_ret = long['annualized_return'].values[0]
                short_ret = short['annualized_return'].values[0]
                bucket_label = long['bucket_label'].values[0]
                
                winner = "LONG" if long_ret > short_ret else "SHORT"
                winner_ret = max(long_ret, short_ret)
                
                print(f"  Bucket {bucket} ({bucket_label:8s}): {winner:5s} won ({winner_ret:+.2%})  [Long: {long_ret:+.2%}, Short: {short_ret:+.2%}]")


def print_strategy_comparison(df_strategies):
    """Print strategy comparison table."""
    
    print("\n" + "="*120)
    print("STRATEGY COMPARISON: WHICH LONG/SHORT COMBO WORKED BEST?")
    print("="*120)
    
    # Pivot by strategy and period
    pivot_strategies = df_strategies.pivot(index='strategy', columns='period', values='combined_return')
    pivot_strategies['Average'] = df_strategies.groupby('strategy')['combined_return'].mean()
    pivot_strategies = pivot_strategies.sort_values('Average', ascending=False)
    
    print("\nCombined Returns by Strategy and Year:")
    print(pivot_strategies.to_string(float_format=lambda x: f'{x:+.2%}'))
    
    # Best strategy by period
    print("\n" + "="*120)
    print("BEST STRATEGY BY PERIOD")
    print("="*120)
    
    for period in df_strategies['period'].unique():
        period_data = df_strategies[df_strategies['period'] == period].sort_values('combined_return', ascending=False)
        
        print(f"\n{period}:")
        for idx, row in period_data.iterrows():
            print(f"  {idx+1}. {row['strategy']:30s}: {row['combined_return']:+.2%}  "
                  f"(Long: {row['long_return']:+.2%}, Short: {row['short_return']:+.2%})")


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(
        description='Analyze Long vs Short Performance by Year',
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
        help='Minimum market cap in USD'
    )
    parser.add_argument(
        '--num-buckets',
        type=int,
        default=5,
        help='Number of size buckets'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='backtest_cmc_long_vs_short_annual.csv',
        help='Output CSV filename'
    )
    
    args = parser.parse_args()
    
    print("="*80)
    print("LONG VS SHORT PERFORMANCE ANALYSIS")
    print("="*80)
    
    # Load and filter data
    print(f"\nLoading data...")
    df = load_cmc_snapshots(args.data)
    df = filter_data(df, min_market_cap=args.min_market_cap)
    
    print(f"\nFiltered to {len(df)} rows with market cap >= ${args.min_market_cap:,.0f}")
    
    # Calculate long/short performance
    print("\nCalculating long and short performance...")
    results_df = calculate_long_short_performance(df, num_buckets=args.num_buckets)
    
    # Print summary tables
    print_summary_tables(results_df)
    
    # Analyze strategies
    print("\n\nAnalyzing long/short strategy combinations...")
    strategy_df = analyze_strategies(results_df)
    print_strategy_comparison(strategy_df)
    
    # Save results
    results_df.to_csv(args.output, index=False)
    strategy_df.to_csv(args.output.replace('.csv', '_strategies.csv'), index=False)
    
    print(f"\n{'='*80}")
    print(f"Results saved to:")
    print(f"  - {args.output}")
    print(f"  - {args.output.replace('.csv', '_strategies.csv')}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
