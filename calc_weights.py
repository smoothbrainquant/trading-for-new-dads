import pandas as pd
import numpy as np


def calculate_inverse_volatility_weights(selected_instruments_file, volatility_file):
    """
    Calculate inverse volatility weights for selected instruments.
    
    Inverse volatility weighting gives higher weights to instruments with lower volatility,
    which is a risk-based portfolio construction approach.
    
    Parameters:
    -----------
    selected_instruments_file : str
        Path to CSV file containing selected instruments
        Expected columns: date, symbol, high, rolling_200d_high, days_since_200d_high
    volatility_file : str
        Path to CSV file containing volatility data
        Expected columns: date, symbol, close, daily_return, volatility_30d
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with columns: symbol, volatility_30d, inverse_vol, weight
        where weight is the normalized inverse volatility weight
    """
    # Load selected instruments
    selected = pd.read_csv(selected_instruments_file)
    print(f"Loaded {len(selected)} selected instruments")
    
    # Load volatility data
    vol_data = pd.read_csv(volatility_file)
    vol_data['date'] = pd.to_datetime(vol_data['date'])
    print(f"Loaded {len(vol_data)} volatility records")
    
    # Get the latest volatility for each symbol
    latest_vol = vol_data.sort_values('date').groupby('symbol').last().reset_index()
    latest_vol = latest_vol[['symbol', 'date', 'close', 'volatility_30d']]
    
    # Get unique symbols from selected instruments
    selected_symbols = selected['symbol'].unique()
    
    # Filter volatility data to only include selected instruments
    weights_df = latest_vol[latest_vol['symbol'].isin(selected_symbols)].copy()
    
    # Remove any instruments with missing volatility data
    weights_df = weights_df.dropna(subset=['volatility_30d'])
    
    if len(weights_df) == 0:
        raise ValueError("No valid volatility data found for selected instruments")
    
    # Calculate inverse volatility
    weights_df['inverse_vol'] = 1.0 / weights_df['volatility_30d']
    
    # Calculate normalized weights (sum to 1)
    total_inverse_vol = weights_df['inverse_vol'].sum()
    weights_df['weight'] = weights_df['inverse_vol'] / total_inverse_vol
    
    # Sort by weight (descending)
    weights_df = weights_df.sort_values('weight', ascending=False).reset_index(drop=True)
    
    # Select relevant columns for output
    result = weights_df[['symbol', 'date', 'close', 'volatility_30d', 'inverse_vol', 'weight']].copy()
    
    return result


if __name__ == "__main__":
    # Input files
    selected_instruments_file = "selected_instruments_near_200d_high.csv"
    volatility_file = "rolling_30d_volatility.csv"
    
    print("=" * 80)
    print("Calculating Inverse Volatility Weights for Selected Instruments")
    print("=" * 80)
    print()
    
    # Calculate weights
    weights = calculate_inverse_volatility_weights(selected_instruments_file, volatility_file)
    
    print(f"\nCalculated weights for {len(weights)} instruments:\n")
    print(weights.to_string(index=False))
    
    # Display summary statistics
    print("\n" + "=" * 80)
    print("Summary Statistics")
    print("=" * 80)
    print(f"\nTotal instruments: {len(weights)}")
    print(f"Sum of weights: {weights['weight'].sum():.6f} (should be 1.0)")
    print(f"\nVolatility range: {weights['volatility_30d'].min():.4f} - {weights['volatility_30d'].max():.4f}")
    print(f"Weight range: {weights['weight'].min():.4f} - {weights['weight'].max():.4f}")
    print(f"Mean weight: {weights['weight'].mean():.4f}")
    print(f"Median weight: {weights['weight'].median():.4f}")
    
    # Show allocation percentages
    print("\n" + "=" * 80)
    print("Allocation Percentages")
    print("=" * 80)
    for idx, row in weights.iterrows():
        print(f"{row['symbol']:20s}: {row['weight']*100:6.2f}% (volatility: {row['volatility_30d']:.4f})")
    
    # Save to CSV
    output_file = "inverse_volatility_weights.csv"
    weights.to_csv(output_file, index=False)
    print(f"\n\nWeights saved to: {output_file}")
