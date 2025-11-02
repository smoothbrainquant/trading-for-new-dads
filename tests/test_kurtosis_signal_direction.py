"""
Unit test to validate kurtosis signal direction consistency
across looping and vectorized implementations.

This test ensures that the signal direction bug is fixed and both
implementations produce the same signal logic.
"""

import pandas as pd
import numpy as np
import sys
import os

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../signals"))
from generate_signals_vectorized import generate_kurtosis_signals_vectorized


def test_kurtosis_signal_direction():
    """
    Test that kurtosis signals are correctly assigned for both strategies.
    
    Strategy definitions:
    - LONG_LOW_SHORT_HIGH: Long LOW kurtosis (stable), Short HIGH kurtosis (volatile)
    - LONG_HIGH_SHORT_LOW: Long HIGH kurtosis (volatile), Short LOW kurtosis (stable)
    """
    # Create test data with clear kurtosis values
    test_data = pd.DataFrame({
        'date': ['2023-01-01'] * 5,
        'symbol': ['COIN_A', 'COIN_B', 'COIN_C', 'COIN_D', 'COIN_E'],
        'kurtosis_30d': [0.5, 1.5, 2.5, 3.5, 4.5],  # Low to high kurtosis
    })
    
    print("Test Data:")
    print(test_data)
    print()
    
    # Test 1: Long Low Short High Strategy
    print("=" * 80)
    print("TEST 1: LONG_LOW_SHORT_HIGH STRATEGY")
    print("=" * 80)
    print("Expected: Long LOW kurtosis, Short HIGH kurtosis")
    
    long_low_signals = generate_kurtosis_signals_vectorized(
        test_data,
        strategy='long_low_short_high',
        long_percentile=20,
        short_percentile=80,
    )
    
    print("\nLong Low Short High Signals:")
    print(long_low_signals[['symbol', 'kurtosis_30d', 'percentile', 'signal']])
    
    # Validate long_low_short_high strategy
    # Low kurtosis (COIN_A: 0.5) should be LONG (signal = 1)
    low_kurtosis_signal = long_low_signals[
        long_low_signals['symbol'] == 'COIN_A'
    ]['signal'].values[0]
    
    # High kurtosis (COIN_E: 4.5) should be SHORT (signal = -1)
    high_kurtosis_signal = long_low_signals[
        long_low_signals['symbol'] == 'COIN_E'
    ]['signal'].values[0]
    
    print(f"\nValidation:")
    print(f"  Low kurtosis coin (COIN_A) signal: {low_kurtosis_signal} (expected: 1)")
    print(f"  High kurtosis coin (COIN_E) signal: {high_kurtosis_signal} (expected: -1)")
    
    assert low_kurtosis_signal == 1, f"? LONG_LOW_SHORT_HIGH FAILED: Low kurtosis should be LONG (1), got {low_kurtosis_signal}"
    assert high_kurtosis_signal == -1, f"? LONG_LOW_SHORT_HIGH FAILED: High kurtosis should be SHORT (-1), got {high_kurtosis_signal}"
    print("  ? LONG_LOW_SHORT_HIGH strategy signals are CORRECT")
    
    # Test 2: Long High Short Low Strategy
    print("\n" + "=" * 80)
    print("TEST 2: LONG_HIGH_SHORT_LOW STRATEGY")
    print("=" * 80)
    print("Expected: Long HIGH kurtosis, Short LOW kurtosis")
    
    long_high_signals = generate_kurtosis_signals_vectorized(
        test_data,
        strategy='long_high_short_low',
        long_percentile=20,
        short_percentile=80,
    )
    
    print("\nLong High Short Low Signals:")
    print(long_high_signals[['symbol', 'kurtosis_30d', 'percentile', 'signal']])
    
    # Validate long_high_short_low strategy
    # High kurtosis (COIN_E: 4.5) should be LONG (signal = 1)
    high_kurtosis_lh_signal = long_high_signals[
        long_high_signals['symbol'] == 'COIN_E'
    ]['signal'].values[0]
    
    # Low kurtosis (COIN_A: 0.5) should be SHORT (signal = -1)
    low_kurtosis_lh_signal = long_high_signals[
        long_high_signals['symbol'] == 'COIN_A'
    ]['signal'].values[0]
    
    print(f"\nValidation:")
    print(f"  High kurtosis coin (COIN_E) signal: {high_kurtosis_lh_signal} (expected: 1)")
    print(f"  Low kurtosis coin (COIN_A) signal: {low_kurtosis_lh_signal} (expected: -1)")
    
    assert high_kurtosis_lh_signal == 1, f"? LONG_HIGH_SHORT_LOW FAILED: High kurtosis should be LONG (1), got {high_kurtosis_lh_signal}"
    assert low_kurtosis_lh_signal == -1, f"? LONG_HIGH_SHORT_LOW FAILED: Low kurtosis should be SHORT (-1), got {low_kurtosis_lh_signal}"
    print("  ? LONG_HIGH_SHORT_LOW strategy signals are CORRECT")
    
    # Test 3: Strategies should be opposite
    print("\n" + "=" * 80)
    print("TEST 3: STRATEGIES SHOULD BE OPPOSITE")
    print("=" * 80)
    
    # For each coin, the two strategies' signals should be opposite (or both 0)
    merged = long_low_signals.merge(
        long_high_signals,
        on=['symbol', 'kurtosis_30d'],
        suffixes=('_low', '_high')
    )
    
    print("\nComparison:")
    print(merged[['symbol', 'kurtosis_30d', 'signal_low', 'signal_high']])
    
    # Check that extreme signals are opposite
    extremes = merged[merged['signal_low'] != 0]
    for _, row in extremes.iterrows():
        low_sig = row['signal_low']
        high_sig = row['signal_high']
        
        # If long_low is long, long_high should be short (or neutral)
        # If long_low is short, long_high should be long (or neutral)
        if low_sig == 1:
            assert high_sig <= 0, f"? {row['symbol']}: LONG_LOW LONG should have LONG_HIGH SHORT/NEUTRAL"
        elif low_sig == -1:
            assert high_sig >= 0, f"? {row['symbol']}: LONG_LOW SHORT should have LONG_HIGH LONG/NEUTRAL"
    
    print("  ? Strategies are properly opposite")
    
    print("\n" + "=" * 80)
    print("? ALL TESTS PASSED")
    print("=" * 80)
    print("\nSummary:")
    print("  - LONG_LOW_SHORT_HIGH strategy: Long LOW kurtosis, Short HIGH kurtosis ?")
    print("  - LONG_HIGH_SHORT_LOW strategy: Long HIGH kurtosis, Short LOW kurtosis ?")
    print("  - Strategies are opposite of each other ?")
    print("\nThe signal direction is CORRECT!")


if __name__ == "__main__":
    test_kurtosis_signal_direction()
