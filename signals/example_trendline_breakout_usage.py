#!/usr/bin/env python3
"""
Example usage of trendline breakout signals.

This script demonstrates how to:
1. Load and filter trendline breakout signals
2. Rank signals by quality
3. Build a portfolio based on signals
4. Monitor signal performance

Usage:
    python3 signals/example_trendline_breakout_usage.py
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def load_signals(filepath='signals/trendline_breakout_signals_full.csv'):
    """Load trendline breakout signals from CSV."""
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    return df


def get_current_signals(signals_df, lookback_days=10, min_signal_strength=1.0):
    """
    Get current active signals.
    
    Args:
        signals_df: Full signals DataFrame
        lookback_days: How many days back to look for signals
        min_signal_strength: Minimum signal strength to consider
        
    Returns:
        DataFrame with current signals
    """
    # Get latest date
    latest_date = signals_df['date'].max()
    cutoff_date = latest_date - pd.Timedelta(days=lookback_days)
    
    # Filter for recent signals
    recent = signals_df[
        (signals_df['date'] >= cutoff_date) &
        (signals_df['signal'] != 'NEUTRAL') &
        (signals_df['signal_strength'] >= min_signal_strength)
    ].copy()
    
    # Get most recent signal per symbol
    current = recent.sort_values('date').groupby('symbol').tail(1)
    
    # Sort by signal strength
    current = current.sort_values('signal_strength', ascending=False)
    
    return current


def filter_high_quality_signals(signals_df, min_r2=0.7, min_z_score=2.0):
    """
    Filter for highest quality signals.
    
    Args:
        signals_df: Signals DataFrame
        min_r2: Minimum R² threshold
        min_z_score: Minimum absolute Z-score
        
    Returns:
        Filtered DataFrame
    """
    return signals_df[
        (signals_df['r_squared'] >= min_r2) &
        (signals_df['breakout_z_score'].abs() >= min_z_score)
    ]


def build_portfolio(signals_df, max_longs=10, max_shorts=10, 
                   long_allocation=0.5, short_allocation=0.5):
    """
    Build a portfolio from signals.
    
    Args:
        signals_df: Current signals DataFrame
        max_longs: Maximum long positions
        max_shorts: Maximum short positions
        long_allocation: Total allocation to long side (0-1)
        short_allocation: Total allocation to short side (0-1)
        
    Returns:
        Dictionary with portfolio positions
    """
    # Separate longs and shorts
    longs = signals_df[signals_df['signal'] == 'LONG'].copy()
    shorts = signals_df[signals_df['signal'] == 'SHORT'].copy()
    
    # Select top signals
    selected_longs = longs.nlargest(max_longs, 'signal_strength')
    selected_shorts = shorts.nlargest(max_shorts, 'signal_strength')
    
    # Calculate equal weights
    if len(selected_longs) > 0:
        selected_longs['weight'] = long_allocation / len(selected_longs)
    else:
        selected_longs['weight'] = 0
        
    if len(selected_shorts) > 0:
        selected_shorts['weight'] = short_allocation / len(selected_shorts)
    else:
        selected_shorts['weight'] = 0
    
    portfolio = {
        'long': selected_longs,
        'short': selected_shorts,
        'num_longs': len(selected_longs),
        'num_shorts': len(selected_shorts),
        'long_exposure': long_allocation if len(selected_longs) > 0 else 0,
        'short_exposure': short_allocation if len(selected_shorts) > 0 else 0
    }
    
    return portfolio


def display_portfolio(portfolio):
    """Display portfolio positions."""
    print("\n" + "="*80)
    print("PORTFOLIO POSITIONS")
    print("="*80)
    
    print(f"\nLong Positions: {portfolio['num_longs']}")
    print(f"Long Exposure: {portfolio['long_exposure']*100:.1f}%")
    if portfolio['num_longs'] > 0:
        print("-" * 80)
        print(f"{'Symbol':<12} {'Weight':<8} {'Strength':<10} {'R²':<8} {'Z-score':<10}")
        print("-" * 80)
        for _, row in portfolio['long'].iterrows():
            print(f"{row['symbol']:<12} {row['weight']*100:>6.1f}%  "
                  f"{row['signal_strength']:>8.2f}  {row['r_squared']:>6.3f}  "
                  f"{row['breakout_z_score']:>+8.2f}σ")
    
    print(f"\nShort Positions: {portfolio['num_shorts']}")
    print(f"Short Exposure: {portfolio['short_exposure']*100:.1f}%")
    if portfolio['num_shorts'] > 0:
        print("-" * 80)
        print(f"{'Symbol':<12} {'Weight':<8} {'Strength':<10} {'R²':<8} {'Z-score':<10}")
        print("-" * 80)
        for _, row in portfolio['short'].iterrows():
            print(f"{row['symbol']:<12} {row['weight']*100:>6.1f}%  "
                  f"{row['signal_strength']:>8.2f}  {row['r_squared']:>6.3f}  "
                  f"{row['breakout_z_score']:>+8.2f}σ")
    
    print("\n" + "="*80)


def display_signal_summary(signals_df):
    """Display summary statistics of signals."""
    print("\n" + "="*80)
    print("SIGNAL SUMMARY")
    print("="*80)
    
    longs = signals_df[signals_df['signal'] == 'LONG']
    shorts = signals_df[signals_df['signal'] == 'SHORT']
    
    print(f"\nTotal Signals: {len(signals_df)}")
    print(f"  Long: {len(longs)}")
    print(f"  Short: {len(shorts)}")
    
    print(f"\nAverage Metrics:")
    print(f"  Signal Strength: {signals_df['signal_strength'].mean():.2f}")
    print(f"  R²: {signals_df['r_squared'].mean():.3f}")
    print(f"  Z-score: {signals_df['breakout_z_score'].abs().mean():.2f}σ")
    print(f"  Volatility: {signals_df['volatility'].mean()*100:.1f}%")
    
    if len(longs) > 0:
        print(f"\nLong Signals:")
        print(f"  Avg Strength: {longs['signal_strength'].mean():.2f}")
        print(f"  Avg R²: {longs['r_squared'].mean():.3f}")
        print(f"  Avg Z-score: {longs['breakout_z_score'].mean():.2f}σ")
    
    if len(shorts) > 0:
        print(f"\nShort Signals:")
        print(f"  Avg Strength: {shorts['signal_strength'].mean():.2f}")
        print(f"  Avg R²: {shorts['r_squared'].mean():.3f}")
        print(f"  Avg Z-score: {shorts['breakout_z_score'].mean():.2f}σ")
    
    print("="*80)


def main():
    """Main example workflow."""
    print("\n" + "="*80)
    print("TRENDLINE BREAKOUT SIGNALS - EXAMPLE USAGE")
    print("="*80)
    
    # 1. Load signals
    print("\n1. Loading signals...")
    signals = load_signals()
    print(f"   Loaded {len(signals)} data points")
    print(f"   Date range: {signals['date'].min().date()} to {signals['date'].max().date()}")
    
    # 2. Get current signals
    print("\n2. Getting current signals...")
    current = get_current_signals(signals, lookback_days=10, min_signal_strength=1.0)
    print(f"   Found {len(current)} current signals")
    
    if len(current) == 0:
        print("\n   No current signals found. Try increasing lookback_days or lowering min_signal_strength.")
        return
    
    # 3. Display signal summary
    display_signal_summary(current)
    
    # 4. Filter for high quality (optional)
    print("\n3. Filtering for high quality signals (R² ≥ 0.7, |Z| ≥ 2.0)...")
    high_quality = filter_high_quality_signals(current, min_r2=0.7, min_z_score=2.0)
    print(f"   High quality signals: {len(high_quality)}")
    
    # 5. Build portfolio with default parameters
    print("\n4. Building portfolio (top 10 longs, top 10 shorts)...")
    portfolio = build_portfolio(current, max_longs=10, max_shorts=10)
    
    # 6. Display portfolio
    display_portfolio(portfolio)
    
    # 7. Example: Build conservative portfolio with high quality signals
    if len(high_quality) > 0:
        print("\n5. Building conservative portfolio (high quality signals only)...")
        conservative_portfolio = build_portfolio(
            high_quality, 
            max_longs=5, 
            max_shorts=5,
            long_allocation=0.3,
            short_allocation=0.3
        )
        display_portfolio(conservative_portfolio)
    
    # 8. Save portfolio to CSV (optional)
    print("\n6. Saving portfolio positions...")
    all_positions = pd.concat([
        portfolio['long'][['symbol', 'signal', 'weight', 'signal_strength', 'r_squared', 'breakout_z_score']],
        portfolio['short'][['symbol', 'signal', 'weight', 'signal_strength', 'r_squared', 'breakout_z_score']]
    ])
    all_positions.to_csv('signals/trendline_breakout_portfolio.csv', index=False)
    print(f"   Saved to: signals/trendline_breakout_portfolio.csv")
    
    print("\n" + "="*80)
    print("COMPLETE")
    print("="*80)
    print("\nNext steps:")
    print("  1. Review portfolio positions in signals/trendline_breakout_portfolio.csv")
    print("  2. Adjust parameters (max_longs, max_shorts, quality filters)")
    print("  3. Implement in your trading system with 5-day holding period")
    print("  4. Monitor performance and rebalance daily")
    print("="*80)


if __name__ == '__main__':
    main()
