import pandas as pd
from calc_days_from_high import get_current_days_since_high


def select_instruments_near_200d_high(data_source, max_days=20):
    """
    Select instruments that are within max_days of their 200-day high.
    
    Parameters:
    -----------
    data_source : str or pd.DataFrame
        Either a path to a CSV file or a pandas DataFrame
        Expected columns: date, symbol, open, high, low, close, volume
    max_days : int, optional
        Maximum days since 200-day high (default: 20)
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with instruments that are < max_days since their 200-day high
        Columns: date, symbol, high, rolling_200d_high, days_since_200d_high
    """
    # Get current days since high for all instruments
    current_status = get_current_days_since_high(data_source)
    
    # Filter for instruments < max_days since 200d high
    selected = current_status[current_status['days_since_200d_high'] < max_days].copy()
    
    # Sort by days_since_200d_high (ascending) to show most recent highs first
    selected = selected.sort_values('days_since_200d_high').reset_index(drop=True)
    
    return selected


if __name__ == "__main__":
    # Default data source
    csv_file = "top10_markets_100d_daily_data.csv"
    
    print("Selecting instruments < 20 days since 200-day high")
    print("=" * 80)
    
    # Get instruments near their 200-day high
    selected_instruments = select_instruments_near_200d_high(csv_file, max_days=20)
    
    print(f"\nFound {len(selected_instruments)} instruments within 20 days of 200d high:\n")
    print(selected_instruments.to_string(index=False))
    
    # Save results to CSV
    output_file = "selected_instruments_near_200d_high.csv"
    selected_instruments.to_csv(output_file, index=False)
    print(f"\n\nResults saved to: {output_file}")
