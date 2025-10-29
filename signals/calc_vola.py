import pandas as pd
import numpy as np


def calculate_rolling_30d_volatility(data):
    """
    Calculate rolling 30-day volatility for instruments from daily data.

    Args:
        data (str or pd.DataFrame): Either a path to CSV file or a pandas DataFrame
                                   Expected columns: date, symbol, open, high, low, close, volume

    Returns:
        pd.DataFrame: DataFrame with date, symbol, close, daily_return, and volatility_30d columns
    """
    # Handle both CSV file path and DataFrame input
    if isinstance(data, str):
        # Read the CSV file
        df = pd.read_csv(data)
    elif isinstance(data, pd.DataFrame):
        # Use the DataFrame directly (make a copy to avoid modifying original)
        df = data.copy()
    else:
        raise TypeError("Input must be either a file path (str) or a pandas DataFrame")

    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"])

    # Sort by symbol and date to ensure proper ordering
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

    # Calculate daily log returns for each symbol
    df["daily_return"] = df.groupby("symbol")["close"].transform(lambda x: np.log(x / x.shift(1)))

    # Calculate rolling 30-day volatility (annualized)
    # Rolling standard deviation of returns over 30 days * sqrt(365) to annualize
    df["volatility_30d"] = df.groupby("symbol")["daily_return"].transform(
        lambda x: x.rolling(window=30, min_periods=30).std() * np.sqrt(365)
    )

    # Select relevant columns
    result = df[["date", "symbol", "close", "daily_return", "volatility_30d"]].copy()

    return result


def calculate_rolling_30d_volatility_simple(data):
    """
    Calculate rolling 30-day volatility (non-annualized) for instruments from daily data.

    Args:
        data (str or pd.DataFrame): Either a path to CSV file or a pandas DataFrame
                                   Expected columns: date, symbol, open, high, low, close, volume

    Returns:
        pd.DataFrame: DataFrame with date, symbol, close, daily_return, and volatility_30d columns
    """
    # Handle both CSV file path and DataFrame input
    if isinstance(data, str):
        # Read the CSV file
        df = pd.read_csv(data)
    elif isinstance(data, pd.DataFrame):
        # Use the DataFrame directly (make a copy to avoid modifying original)
        df = data.copy()
    else:
        raise TypeError("Input must be either a file path (str) or a pandas DataFrame")

    # Convert date to datetime
    df["date"] = pd.to_datetime(df["date"])

    # Sort by symbol and date to ensure proper ordering
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

    # Calculate daily log returns for each symbol
    df["daily_return"] = df.groupby("symbol")["close"].transform(lambda x: np.log(x / x.shift(1)))

    # Calculate rolling 30-day volatility (not annualized)
    df["volatility_30d"] = df.groupby("symbol")["daily_return"].transform(
        lambda x: x.rolling(window=30, min_periods=30).std()
    )

    # Select relevant columns
    result = df[["date", "symbol", "close", "daily_return", "volatility_30d"]].copy()

    return result


if __name__ == "__main__":
    # Example usage with CSV file path
    csv_file = "top10_markets_100d_daily_data.csv"

    print("=" * 60)
    print("Example 1: Using CSV file path")
    print("=" * 60)

    # Calculate annualized volatility from CSV file
    result = calculate_rolling_30d_volatility(csv_file)
    print("\nRolling 30-day Volatility (Annualized):")
    print(result.head(40))
    print("\nSummary Statistics:")
    print(result.groupby("symbol")["volatility_30d"].describe())

    # Save to CSV
    output_file = "rolling_30d_volatility.csv"
    result.to_csv(output_file, index=False)
    print(f"\nResults saved to {output_file}")

    # Example usage with DataFrame
    print("\n" + "=" * 60)
    print("Example 2: Using pandas DataFrame")
    print("=" * 60)

    # Load data into DataFrame
    df = pd.read_csv(csv_file)
    print(f"\nLoaded DataFrame with {len(df)} rows")

    # Filter to only BTC data for demonstration
    btc_df = df[df["symbol"] == "BTC/USDC:USDC"].copy()

    # Calculate volatility from DataFrame
    btc_result = calculate_rolling_30d_volatility(btc_df)
    print("\nBTC Rolling 30-day Volatility:")
    print(btc_result[btc_result["volatility_30d"].notna()].head(10))
    print(f"\nBTC Average 30d Volatility: {btc_result['volatility_30d'].mean():.4f}")
