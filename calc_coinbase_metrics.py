#!/usr/bin/env python3
"""
Calculate trading metrics from Coinbase historical data:
- ADV (Average Daily Volume): 20-day rolling average, lagged 1 day
- RVOL (Relative Volume): volume / ADV
- Dollar Volume: close * volume
- ADV Dollar Volume: 20-day rolling average of dollar volume, lagged 1 day
"""

import pandas as pd
import numpy as np

def calculate_metrics(input_file, output_file):
    """Calculate trading metrics from Coinbase data."""
    
    # Read the data
    print(f"Reading data from {input_file}...")
    df = pd.read_csv(input_file)
    
    print(f"Loaded {len(df)} rows")
    print(f"Symbols: {df['symbol'].nunique()}")
    
    # Convert date to datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Sort by symbol and date
    df = df.sort_values(['symbol', 'date'])
    
    # Calculate metrics for each symbol
    print("Calculating metrics...")
    
    # Calculate dollar volume (close * volume)
    df['dollar_volume'] = df['close'] * df['volume']
    
    # Group by symbol to calculate rolling metrics
    grouped = df.groupby('symbol')
    
    # ADV: 20-day rolling average of volume, lagged 1 day
    df['adv_20d'] = grouped['volume'].transform(
        lambda x: x.rolling(window=20, min_periods=1).mean().shift(1)
    )
    
    # RVOL: current volume / ADV
    df['rvol'] = df['volume'] / df['adv_20d']
    
    # ADV of dollar volume: 20-day rolling average of dollar volume, lagged 1 day
    df['adv_dollar_volume_20d'] = grouped['dollar_volume'].transform(
        lambda x: x.rolling(window=20, min_periods=1).mean().shift(1)
    )
    
    # Handle infinities and NaNs in RVOL (when ADV is 0 or NaN)
    df['rvol'] = df['rvol'].replace([np.inf, -np.inf], np.nan)
    
    # Save to CSV
    print(f"Saving results to {output_file}...")
    df.to_csv(output_file, index=False)
    
    print("\nSample of calculated metrics:")
    print(df[['date', 'symbol', 'close', 'volume', 'dollar_volume', 
              'adv_20d', 'rvol', 'adv_dollar_volume_20d']].head(25))
    
    print(f"\nResults saved to {output_file}")
    print(f"Total rows: {len(df)}")
    
    # Summary statistics
    print("\nSummary statistics:")
    print(df[['volume', 'dollar_volume', 'adv_20d', 'rvol', 'adv_dollar_volume_20d']].describe())

if __name__ == "__main__":
    input_file = "coinbase_spot_daily_data_20200101_20251024_110130.csv"
    output_file = "coinbase_spot_daily_data_with_metrics.csv"
    
    calculate_metrics(input_file, output_file)
