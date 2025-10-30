#!/usr/bin/env python3
"""
Calculate Durbin-Watson (DW) factor signals for cryptocurrencies.

The DW statistic measures autocorrelation in returns:
- DW ≈ 2: Random walk (no autocorrelation)
- DW < 2: Positive autocorrelation (momentum/trending)
- DW > 2: Negative autocorrelation (mean reversion)

Strategy: Contrarian
- Long: High DW (mean reverting coins)
- Short: Low DW (momentum coins that exhaust)
"""

import pandas as pd
import numpy as np
import argparse
from datetime import datetime


def calculate_durbin_watson(returns, window=30):
    """
    Calculate Durbin-Watson statistic.
    
    DW = sum((r[t] - r[t-1])^2) / sum(r[t]^2)
    
    Args:
        returns (pd.Series): Series of returns
        window (int): Window size
        
    Returns:
        float: DW statistic
    """
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
    
    # Filter extreme values
    if dw < 0 or dw > 4.5:
        return np.nan
        
    return dw


def load_data(filepath):
    """Load price data from CSV."""
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    return df


def calculate_dw_signals(data, dw_window=30, min_volume=5_000_000, 
                        top_n_market_cap=100, long_percentile=80, 
                        short_percentile=20):
    """
    Calculate DW factor signals.
    
    Args:
        data (pd.DataFrame): Price data with OHLCV
        dw_window (int): DW calculation window
        min_volume (float): Minimum volume filter
        top_n_market_cap (int): Select top N by market cap
        long_percentile (int): Percentile for long positions
        short_percentile (int): Percentile for short positions
        
    Returns:
        pd.DataFrame: Data with signals
    """
    df = data.copy()
    
    # Calculate daily returns
    df['daily_return'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Calculate rolling DW
    print(f"Calculating {dw_window}-day Durbin-Watson statistic...")
    df['dw'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=dw_window, min_periods=int(dw_window*0.7)).apply(
            calculate_durbin_watson, raw=False, kwargs={'window': dw_window}
        )
    )
    
    # Calculate 30-day average volume
    df['volume_30d_avg'] = df.groupby('symbol')['volume'].transform(
        lambda x: x.rolling(window=30, min_periods=20).mean()
    )
    
    # Filter by volume
    df = df[df['volume_30d_avg'] >= min_volume]
    
    # Filter by top N market cap on each date
    if top_n_market_cap:
        df['market_cap_rank'] = df.groupby('date')['market_cap'].rank(
            ascending=False, method='first'
        )
        df = df[df['market_cap_rank'] <= top_n_market_cap]
    
    # Remove extreme DW values
    df = df[(df['dw'] >= 0.5) & (df['dw'] <= 3.5)]
    
    # Calculate DW rank and percentile for each date
    df['dw_rank'] = df.groupby('date')['dw'].rank(method='first', ascending=True)
    df['dw_percentile'] = df.groupby('date')['dw_rank'].transform(
        lambda x: x / x.max() * 100
    )
    
    # Generate signals
    df['signal'] = 0
    df.loc[df['dw_percentile'] >= long_percentile, 'signal'] = 1  # Long high DW
    df.loc[df['dw_percentile'] <= short_percentile, 'signal'] = -1  # Short low DW
    
    # Calculate equal weights within each signal group
    def calc_weight(group):
        longs = (group['signal'] == 1).sum()
        shorts = (group['signal'] == -1).sum()
        
        group['weight'] = 0.0
        if longs > 0:
            group.loc[group['signal'] == 1, 'weight'] = 0.5 / longs
        if shorts > 0:
            group.loc[group['signal'] == -1, 'weight'] = -0.5 / shorts
        
        return group
    
    df = df.groupby('date', group_keys=False).apply(calc_weight)
    
    return df


def save_signals(df, output_file):
    """Save signals to CSV."""
    # Keep relevant columns
    output_cols = [
        'date', 'symbol', 'close', 'volume', 'market_cap',
        'dw', 'dw_rank', 'dw_percentile', 'signal', 'weight'
    ]
    
    output_df = df[output_cols].copy()
    output_df = output_df[output_df['signal'] != 0]  # Only positions
    output_df = output_df.sort_values(['date', 'signal', 'symbol'])
    
    output_df.to_csv(output_file, index=False)
    print(f"\n✓ Saved signals to: {output_file}")
    
    # Print summary
    total_signals = len(output_df)
    long_signals = (output_df['signal'] == 1).sum()
    short_signals = (output_df['signal'] == -1).sum()
    dates = output_df['date'].nunique()
    symbols = output_df['symbol'].nunique()
    
    print(f"\nSignal Summary:")
    print(f"  Total signals:    {total_signals:,}")
    print(f"  Long signals:     {long_signals:,}")
    print(f"  Short signals:    {short_signals:,}")
    print(f"  Unique dates:     {dates:,}")
    print(f"  Unique symbols:   {symbols:,}")
    print(f"  Avg per date:     {total_signals/dates:.1f}")


def print_sample_signals(df, n=10):
    """Print sample signals."""
    sample = df[df['signal'] != 0].head(n)
    
    print("\nSample Signals (first 10):")
    print("-" * 100)
    print(f"{'Date':<12} {'Symbol':<10} {'DW':>8} {'Percentile':>12} {'Signal':>8} {'Weight':>10}")
    print("-" * 100)
    
    for _, row in sample.iterrows():
        signal_str = 'LONG' if row['signal'] == 1 else 'SHORT'
        print(f"{row['date'].strftime('%Y-%m-%d'):<12} {row['symbol']:<10} "
              f"{row['dw']:>8.2f} {row['dw_percentile']:>11.1f}% {signal_str:>8} "
              f"{row['weight']:>10.4f}")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Calculate Durbin-Watson factor signals'
    )
    
    parser.add_argument(
        '--data-file',
        type=str,
        default='data/raw/combined_coinbase_coinmarketcap_daily.csv',
        help='Path to price data CSV'
    )
    parser.add_argument(
        '--dw-window',
        type=int,
        default=30,
        help='DW calculation window (days)'
    )
    parser.add_argument(
        '--min-volume',
        type=float,
        default=5_000_000,
        help='Minimum 30-day average volume'
    )
    parser.add_argument(
        '--top-n-market-cap',
        type=int,
        default=100,
        help='Select top N coins by market cap'
    )
    parser.add_argument(
        '--long-percentile',
        type=int,
        default=80,
        help='Percentile threshold for long positions'
    )
    parser.add_argument(
        '--short-percentile',
        type=int,
        default=20,
        help='Percentile threshold for short positions'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        default=None,
        help='Start date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        default=None,
        help='End date (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--output-file',
        type=str,
        default='signals/dw_factor_signals.csv',
        help='Output file path'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("DURBIN-WATSON FACTOR SIGNAL GENERATOR")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  DW Window:           {args.dw_window} days")
    print(f"  Min Volume:          ${args.min_volume:,.0f}")
    print(f"  Top N Market Cap:    {args.top_n_market_cap}")
    print(f"  Long Percentile:     {args.long_percentile}% (top {100-args.long_percentile}%)")
    print(f"  Short Percentile:    {args.short_percentile}% (bottom {args.short_percentile}%)")
    
    # Load data
    print(f"\nLoading data from: {args.data_file}")
    data = load_data(args.data_file)
    print(f"Loaded {len(data):,} rows for {data['symbol'].nunique()} symbols")
    
    # Filter by date
    if args.start_date:
        data = data[data['date'] >= pd.to_datetime(args.start_date)]
    if args.end_date:
        data = data[data['date'] <= pd.to_datetime(args.end_date)]
    
    print(f"Date range: {data['date'].min().date()} to {data['date'].max().date()}")
    
    # Calculate signals
    print("\nCalculating signals...")
    signals_df = calculate_dw_signals(
        data,
        dw_window=args.dw_window,
        min_volume=args.min_volume,
        top_n_market_cap=args.top_n_market_cap,
        long_percentile=args.long_percentile,
        short_percentile=args.short_percentile
    )
    
    # Print sample
    print_sample_signals(signals_df)
    
    # Save signals
    save_signals(signals_df, args.output_file)
    
    print("\n" + "=" * 80)
    print("SIGNAL GENERATION COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    main()
