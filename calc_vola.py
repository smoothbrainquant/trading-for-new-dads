import pandas as pd
import numpy as np


def calculate_rolling_30d_volatility(csv_file_path):
    """
    Calculate rolling 30-day volatility for instruments from daily data CSV.
    
    Args:
        csv_file_path (str): Path to the CSV file containing daily data
                            Expected columns: date, symbol, open, high, low, close, volume
    
    Returns:
        pd.DataFrame: DataFrame with date, symbol, close, daily_return, and volatility_30d columns
    """
    # Read the CSV file
    df = pd.read_csv(csv_file_path)
    
    # Convert date to datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Sort by symbol and date to ensure proper ordering
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Calculate daily log returns for each symbol
    df['daily_return'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Calculate rolling 30-day volatility (annualized)
    # Rolling standard deviation of returns over 30 days * sqrt(365) to annualize
    df['volatility_30d'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=30, min_periods=30).std() * np.sqrt(365)
    )
    
    # Select relevant columns
    result = df[['date', 'symbol', 'close', 'daily_return', 'volatility_30d']].copy()
    
    return result


def calculate_rolling_30d_volatility_simple(csv_file_path):
    """
    Calculate rolling 30-day volatility (non-annualized) for instruments from daily data CSV.
    
    Args:
        csv_file_path (str): Path to the CSV file containing daily data
                            Expected columns: date, symbol, open, high, low, close, volume
    
    Returns:
        pd.DataFrame: DataFrame with date, symbol, close, daily_return, and volatility_30d columns
    """
    # Read the CSV file
    df = pd.read_csv(csv_file_path)
    
    # Convert date to datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Sort by symbol and date to ensure proper ordering
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Calculate daily log returns for each symbol
    df['daily_return'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Calculate rolling 30-day volatility (not annualized)
    df['volatility_30d'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=30, min_periods=30).std()
    )
    
    # Select relevant columns
    result = df[['date', 'symbol', 'close', 'daily_return', 'volatility_30d']].copy()
    
    return result


if __name__ == "__main__":
    # Example usage
    csv_file = "top10_markets_100d_daily_data.csv"
    
    # Calculate annualized volatility
    result = calculate_rolling_30d_volatility(csv_file)
    print("\nRolling 30-day Volatility (Annualized):")
    print(result.head(40))
    print("\nSummary Statistics:")
    print(result.groupby('symbol')['volatility_30d'].describe())
    
    # Save to CSV
    output_file = "rolling_30d_volatility.csv"
    result.to_csv(output_file, index=False)
    print(f"\nResults saved to {output_file}")
