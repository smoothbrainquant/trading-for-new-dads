import pandas as pd
import numpy as np
from datetime import datetime


def calculate_days_since_200d_high(data_source):
    """
    Calculate days since last 200-day high for each symbol in the dataset.
    
    Parameters:
    -----------
    data_source : str or pd.DataFrame
        Either a path to a CSV file or a pandas DataFrame
        Expected columns: date, symbol, open, high, low, close, volume
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with columns: date, symbol, high, rolling_200d_high, days_since_200d_high
    """
    # Read the data - handle both CSV path and DataFrame
    if isinstance(data_source, str):
        df = pd.read_csv(data_source)
    elif isinstance(data_source, pd.DataFrame):
        df = data_source.copy()
    else:
        raise TypeError("data_source must be either a file path (str) or a pandas DataFrame")
    
    # Convert date to datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Sort by symbol and date to ensure proper ordering
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Group by symbol and calculate for each
    results = []
    
    for symbol, group in df.groupby('symbol'):
        # Calculate 200-day rolling maximum high
        group['rolling_200d_high'] = group['high'].rolling(window=200, min_periods=1).max()
        
        # Initialize days_since_200d_high
        group['days_since_200d_high'] = 0
        
        # Calculate days since 200d high
        days_counter = 0
        for idx in range(len(group)):
            current_high = group.iloc[idx]['high']
            rolling_high = group.iloc[idx]['rolling_200d_high']
            
            # If current high equals or exceeds the 200d rolling high, reset counter
            if current_high >= rolling_high:
                days_counter = 0
            else:
                days_counter += 1
            
            group.iloc[idx, group.columns.get_loc('days_since_200d_high')] = days_counter
        
        results.append(group)
    
    # Combine all symbols
    result_df = pd.concat(results, ignore_index=True)
    
    # Select relevant columns
    output_df = result_df[['date', 'symbol', 'high', 'rolling_200d_high', 'days_since_200d_high']]
    
    return output_df


def get_current_days_since_high(data_source):
    """
    Get the most recent days_since_200d_high value for each symbol.
    
    Parameters:
    -----------
    data_source : str or pd.DataFrame
        Either a path to a CSV file or a pandas DataFrame
        Expected columns: date, symbol, open, high, low, close, volume
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with the latest date's data for each symbol
    """
    full_results = calculate_days_since_200d_high(data_source)
    
    # Get the most recent date for each symbol
    latest_data = full_results.sort_values('date').groupby('symbol').tail(1).reset_index(drop=True)
    
    return latest_data


if __name__ == "__main__":
    # Example usage with CSV file
    csv_file = "top10_markets_100d_daily_data.csv"
    
    print("Example 1: Reading from CSV file")
    print("="*80)
    # Calculate days since 200d high for all dates
    print("Calculating days since 200-day high for all data...")
    full_results = calculate_days_since_200d_high(csv_file)
    
    # Display sample results
    print("\nSample results (first 20 rows):")
    print(full_results.head(20))
    
    # Get current status for each symbol
    print("\n" + "="*80)
    print("Current days since 200-day high for each symbol:")
    print("="*80)
    current_status = get_current_days_since_high(csv_file)
    print(current_status.to_string(index=False))
    
    # Save full results to CSV
    output_file = "days_since_200d_high_results.csv"
    full_results.to_csv(output_file, index=False)
    print(f"\nFull results saved to: {output_file}")
    
    # Example usage with DataFrame
    print("\n" + "="*80)
    print("Example 2: Reading from DataFrame")
    print("="*80)
    df = pd.read_csv(csv_file)
    # Filter to just one or two symbols for demonstration
    sample_df = df[df['symbol'].isin(['BTC/USDC:USDC', 'ETH/USDC:USDC'])].copy()
    
    print(f"Processing {len(sample_df)} rows for demonstration...")
    sample_results = calculate_days_since_200d_high(sample_df)
    print("\nSample results from DataFrame input:")
    print(sample_results.tail(10))
    
    print("\nCurrent status from DataFrame input:")
    sample_current = get_current_days_since_high(sample_df)
    print(sample_current.to_string(index=False))
