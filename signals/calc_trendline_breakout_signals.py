#!/usr/bin/env python3
"""
Trendline Breakout Signal Calculation Module

Calculates continuation signals based on trendline analysis:
- Fits linear regression to recent price history (trendline)
- Detects when price breaks out strongly from the trendline
- Only signals when trendline is clean and statistically significant

Signal Rules:
- LONG: Price breaks ABOVE a clean uptrend (continuation signal)
- SHORT: Price breaks BELOW a clean downtrend (continuation signal)

Signal Quality Filters:
- R² ≥ 0.5: Trendline must be clean (explains ≥50% of variance)
- P-value ≤ 0.05: Trendline must be statistically significant
- Z-score ≥ 1.5σ: Breakout must be strong (≥1.5 standard deviations)

Hypothesis: Clean trendlines with strong breakouts signal momentum continuation.
"""

import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime
import argparse
import sys


def calculate_rolling_trendline(data, window=30):
    """
    Calculate rolling linear regression on closing prices.
    
    Args:
        data (pd.DataFrame): DataFrame with date, symbol, close columns
        window (int): Rolling window size for trendline calculation
        
    Returns:
        pd.DataFrame: DataFrame with trendline metrics
    """
    df = data.copy()
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Calculate daily returns for volatility
    df['daily_return'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    def fit_trendline(prices, current_idx):
        """Fit linear regression to price window"""
        n = len(prices)
        
        # Remove NaN values
        valid_mask = ~np.isnan(prices.values)
        
        # Require at least 70% data availability
        min_periods = int(window * 0.7)
        if valid_mask.sum() < min_periods:
            return pd.Series({
                'slope': np.nan,
                'intercept': np.nan,
                'r_squared': np.nan,
                'p_value': np.nan,
                'predicted_price': np.nan
            })
        
        valid_prices = prices.values[valid_mask]
        valid_x = np.arange(len(valid_prices))
        
        try:
            # Fit linear regression
            slope, intercept, r_value, p_value, std_err = stats.linregress(valid_x, valid_prices)
            r_squared = r_value ** 2
            
            # Predict price at current index (end of window)
            predicted_price = slope * (len(valid_prices) - 1) + intercept
            
            return pd.Series({
                'slope': slope,
                'intercept': intercept,
                'r_squared': r_squared,
                'p_value': p_value,
                'predicted_price': predicted_price
            })
        except Exception as e:
            return pd.Series({
                'slope': np.nan,
                'intercept': np.nan,
                'r_squared': np.nan,
                'p_value': np.nan,
                'predicted_price': np.nan
            })
    
    # Calculate rolling trendline metrics for each coin
    def calculate_for_group(group):
        """Calculate trendline metrics for a single coin"""
        trendline_results = []
        
        for i in range(len(group)):
            if i < window - 1:
                trendline_results.append({
                    'slope': np.nan,
                    'intercept': np.nan,
                    'r_squared': np.nan,
                    'p_value': np.nan,
                    'predicted_price': np.nan
                })
            else:
                # Get window of prices
                price_window = group['close'].iloc[i-window+1:i+1]
                result = fit_trendline(price_window, i)
                trendline_results.append(result.to_dict())
        
        return pd.DataFrame(trendline_results)
    
    # Apply to each symbol
    trendline_df = df.groupby('symbol', group_keys=False).apply(
        calculate_for_group, include_groups=False
    ).reset_index(drop=True)
    
    # Merge back with original data
    for col in ['slope', 'intercept', 'r_squared', 'p_value', 'predicted_price']:
        df[col] = trendline_df[col].values
    
    return df


def calculate_breakout_metrics(df, window=30):
    """
    Calculate breakout metrics: distance from trendline normalized by volatility.
    
    Args:
        df (pd.DataFrame): DataFrame with close, predicted_price columns
        window (int): Window for volatility calculation
        
    Returns:
        pd.DataFrame: DataFrame with breakout metrics
    """
    df = df.copy()
    
    # Calculate distance from trendline (percentage)
    df['distance_from_trendline'] = (df['close'] - df['predicted_price']) / df['predicted_price'] * 100
    
    # Calculate rolling volatility (annualized)
    df['volatility'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=window, min_periods=int(window*0.7)).std() * np.sqrt(365)
    )
    
    # Normalize distance by volatility (Z-score)
    df['distance_rolling_mean'] = df.groupby('symbol')['distance_from_trendline'].transform(
        lambda x: x.rolling(window=window, min_periods=int(window*0.7)).mean()
    )
    df['distance_rolling_std'] = df.groupby('symbol')['distance_from_trendline'].transform(
        lambda x: x.rolling(window=window, min_periods=int(window*0.7)).std()
    )
    
    # Z-score: how extreme is the current distance
    df['breakout_z_score'] = (
        (df['distance_from_trendline'] - df['distance_rolling_mean']) / 
        df['distance_rolling_std']
    )
    
    # Replace inf/nan with 0
    df['breakout_z_score'] = df['breakout_z_score'].replace([np.inf, -np.inf], np.nan).fillna(0)
    
    # Normalized slope (percentage per year)
    df['norm_slope'] = (df['slope'] / df['close']) * 100 * 365
    df['norm_slope'] = df['norm_slope'].clip(-500, 500)
    
    return df


def detect_breakout_signals(data, 
                            breakout_threshold=1.5,
                            min_r2=0.5,
                            max_pvalue=0.05,
                            slope_direction='any'):
    """
    Detect breakout signals based on trendline metrics.
    
    Args:
        data (pd.DataFrame): DataFrame with trendline and breakout metrics
        breakout_threshold (float): Minimum Z-score for breakout (e.g., 1.5 = 1.5 std devs)
        min_r2 (float): Minimum R² for clean trendline
        max_pvalue (float): Maximum p-value for significant trendline
        slope_direction (str): 'positive', 'negative', or 'any'
        
    Returns:
        pd.DataFrame: DataFrame with signal column
    """
    df = data.copy()
    
    # Initialize signal
    df['signal'] = 'NEUTRAL'
    df['signal_strength'] = 0.0
    
    # Filter for clean trendlines
    clean_mask = (
        (df['r_squared'] >= min_r2) &
        (df['p_value'] <= max_pvalue) &
        (~df['breakout_z_score'].isna())
    )
    
    # Bullish breakout: price breaking above clean uptrend
    if slope_direction in ['positive', 'any']:
        bullish_mask = (
            clean_mask &
            (df['norm_slope'] > 0) &  # Uptrend
            (df['breakout_z_score'] > breakout_threshold) &  # Strong upward break
            (df['distance_from_trendline'] > 0)  # Above trendline
        )
        df.loc[bullish_mask, 'signal'] = 'LONG'
    
    # Bearish breakout: price breaking below clean downtrend
    if slope_direction in ['negative', 'any']:
        bearish_mask = (
            clean_mask &
            (df['norm_slope'] < 0) &  # Downtrend
            (df['breakout_z_score'] < -breakout_threshold) &  # Strong downward break
            (df['distance_from_trendline'] < 0)  # Below trendline
        )
        df.loc[bearish_mask, 'signal'] = 'SHORT'
    
    # Create signal strength score (for ranking)
    df['signal_strength'] = df['breakout_z_score'].abs() * df['r_squared']
    
    return df


def calculate_trendline_breakout_signals(data_source,
                                         trendline_window=30,
                                         volatility_window=30,
                                         breakout_threshold=1.5,
                                         min_r2=0.5,
                                         max_pvalue=0.05,
                                         slope_direction='any'):
    """
    Calculate trendline breakout signals for all symbols in dataset.
    
    Parameters:
    -----------
    data_source : str or pd.DataFrame
        Either a path to a CSV file or a pandas DataFrame
        Expected columns: date, symbol, close, volume (optional), market_cap (optional)
    
    trendline_window : int
        Window size for trendline calculation (default: 30 days)
    
    volatility_window : int
        Window size for volatility calculation (default: 30 days)
    
    breakout_threshold : float
        Z-score threshold for breakout signal (default: 1.5 standard deviations)
    
    min_r2 : float
        Minimum R² for clean trendline (default: 0.5)
    
    max_pvalue : float
        Maximum p-value for significant trendline (default: 0.05)
    
    slope_direction : str
        'positive' (uptrends only), 'negative' (downtrends only), or 'any' (both)
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with columns:
        - date, symbol, close, volume, market_cap (if available)
        - slope: Trendline slope (price change per day)
        - norm_slope: Normalized slope (annualized %)
        - r_squared: Trendline R² (quality/cleanness)
        - p_value: Statistical significance
        - predicted_price: Where trendline says price should be
        - distance_from_trendline: How far price is from trendline (%)
        - breakout_z_score: Normalized breakout strength (standard deviations)
        - volatility: Annualized volatility
        - signal: 'LONG', 'SHORT', or 'NEUTRAL'
        - signal_strength: Composite signal quality score
    """
    # Read the data
    if isinstance(data_source, str):
        df = pd.read_csv(data_source)
    elif isinstance(data_source, pd.DataFrame):
        df = data_source.copy()
    else:
        raise TypeError("data_source must be either a file path (str) or a pandas DataFrame")
    
    # Convert date to datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Sort by symbol and date
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    print(f"Calculating trendline breakout signals...")
    print(f"  Data points: {len(df)}")
    print(f"  Symbols: {df['symbol'].nunique()}")
    print(f"  Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"  Trendline window: {trendline_window} days")
    print(f"  Breakout threshold: {breakout_threshold}σ")
    print(f"  Min R²: {min_r2}")
    
    # Step 1: Calculate trendline metrics
    print("\nStep 1: Calculating rolling trendline...")
    df = calculate_rolling_trendline(df, window=trendline_window)
    
    # Step 2: Calculate breakout metrics
    print("Step 2: Calculating breakout metrics...")
    df = calculate_breakout_metrics(df, window=volatility_window)
    
    # Step 3: Detect breakout signals
    print("Step 3: Detecting breakout signals...")
    df = detect_breakout_signals(
        df,
        breakout_threshold=breakout_threshold,
        min_r2=min_r2,
        max_pvalue=max_pvalue,
        slope_direction=slope_direction
    )
    
    # Count signals
    long_signals = (df['signal'] == 'LONG').sum()
    short_signals = (df['signal'] == 'SHORT').sum()
    neutral = (df['signal'] == 'NEUTRAL').sum()
    
    print(f"\nSignal Summary:")
    print(f"  LONG signals: {long_signals}")
    print(f"  SHORT signals: {short_signals}")
    print(f"  NEUTRAL: {neutral}")
    print(f"  Total: {len(df)}")
    
    # Select relevant columns for output
    output_cols = [
        'date', 'symbol', 'close',
        'slope', 'norm_slope', 'r_squared', 'p_value',
        'predicted_price', 'distance_from_trendline',
        'breakout_z_score', 'volatility',
        'signal', 'signal_strength'
    ]
    
    # Include optional columns if they exist
    if 'volume' in df.columns:
        output_cols.insert(3, 'volume')
    if 'market_cap' in df.columns:
        output_cols.insert(3, 'market_cap')
    
    return df[output_cols]


def get_current_signals(signals_df, top_n=20):
    """
    Get the most recent signals for each symbol.
    
    Args:
        signals_df (pd.DataFrame): Full signals DataFrame
        top_n (int): Number of top signals to return per side
        
    Returns:
        pd.DataFrame: Current signals sorted by signal strength
    """
    # Get the most recent date
    latest_date = signals_df['date'].max()
    
    # Filter for recent signals (within last 5 days)
    recent_cutoff = latest_date - pd.Timedelta(days=5)
    recent_signals = signals_df[
        (signals_df['date'] >= recent_cutoff) &
        (signals_df['signal'] != 'NEUTRAL')
    ].copy()
    
    # Get most recent signal per symbol
    current_signals = recent_signals.sort_values('date').groupby('symbol').tail(1)
    
    # Sort by signal strength
    current_signals = current_signals.sort_values('signal_strength', ascending=False)
    
    # Separate long and short
    long_signals = current_signals[current_signals['signal'] == 'LONG'].head(top_n)
    short_signals = current_signals[current_signals['signal'] == 'SHORT'].head(top_n)
    
    # Combine and return
    result = pd.concat([long_signals, short_signals]).sort_values(
        ['signal', 'signal_strength'], ascending=[True, False]
    )
    
    return result


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Calculate trendline breakout signals',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate signals with default parameters
  python calc_trendline_breakout_signals.py
  
  # Use custom parameters
  python calc_trendline_breakout_signals.py --min-r2 0.7 --breakout-threshold 2.0
  
  # Only uptrend breakouts
  python calc_trendline_breakout_signals.py --slope-direction positive
        """
    )
    
    parser.add_argument(
        '--price-data',
        type=str,
        default='data/raw/combined_coinbase_coinmarketcap_daily.csv',
        help='Path to price data CSV (default: data/raw/combined_coinbase_coinmarketcap_daily.csv)'
    )
    
    parser.add_argument(
        '--trendline-window',
        type=int,
        default=30,
        help='Trendline calculation window in days (default: 30)'
    )
    
    parser.add_argument(
        '--volatility-window',
        type=int,
        default=30,
        help='Volatility window for breakout normalization (default: 30)'
    )
    
    parser.add_argument(
        '--breakout-threshold',
        type=float,
        default=1.5,
        help='Z-score threshold for breakout signal (default: 1.5)'
    )
    
    parser.add_argument(
        '--min-r2',
        type=float,
        default=0.5,
        help='Minimum R² for clean trendline (default: 0.5)'
    )
    
    parser.add_argument(
        '--max-pvalue',
        type=float,
        default=0.05,
        help='Maximum p-value for significant trendline (default: 0.05)'
    )
    
    parser.add_argument(
        '--slope-direction',
        type=str,
        default='any',
        choices=['positive', 'negative', 'any'],
        help='Required slope direction (default: any)'
    )
    
    parser.add_argument(
        '--output',
        type=str,
        default='signals/trendline_breakout_signals_full.csv',
        help='Output CSV file path (default: signals/trendline_breakout_signals_full.csv)'
    )
    
    parser.add_argument(
        '--current-output',
        type=str,
        default='signals/trendline_breakout_signals_current.csv',
        help='Current signals output file (default: signals/trendline_breakout_signals_current.csv)'
    )
    
    args = parser.parse_args()
    
    # Calculate signals
    signals_df = calculate_trendline_breakout_signals(
        data_source=args.price_data,
        trendline_window=args.trendline_window,
        volatility_window=args.volatility_window,
        breakout_threshold=args.breakout_threshold,
        min_r2=args.min_r2,
        max_pvalue=args.max_pvalue,
        slope_direction=args.slope_direction
    )
    
    # Save full signals
    signals_df.to_csv(args.output, index=False)
    print(f"\n✓ Saved full signals to: {args.output}")
    
    # Get and save current signals
    current_signals = get_current_signals(signals_df, top_n=20)
    current_signals.to_csv(args.current_output, index=False)
    print(f"✓ Saved current signals to: {args.current_output}")
    
    # Display current signals
    if not current_signals.empty:
        print("\n" + "="*80)
        print("CURRENT TRENDLINE BREAKOUT SIGNALS")
        print("="*80)
        
        for signal_type in ['LONG', 'SHORT']:
            type_signals = current_signals[current_signals['signal'] == signal_type]
            if not type_signals.empty:
                print(f"\n{signal_type} Signals ({len(type_signals)}):")
                print("-" * 80)
                for _, row in type_signals.iterrows():
                    print(f"  {row['symbol']:10s}  "
                          f"Signal Strength: {row['signal_strength']:6.2f}  "
                          f"R²: {row['r_squared']:5.3f}  "
                          f"Z-score: {row['breakout_z_score']:6.2f}σ  "
                          f"Date: {row['date'].strftime('%Y-%m-%d')}")
        print("="*80)
    else:
        print("\nNo current signals found.")


if __name__ == '__main__':
    main()
