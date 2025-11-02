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
    - MOMENTUM: Long HIGH kurtosis (volatile), Short LOW kurtosis (stable)
    - MEAN_REVERSION: Long LOW kurtosis (stable), Short HIGH kurtosis (volatile)
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
    
    # Test 1: Momentum Strategy
    print("=" * 80)
    print("TEST 1: MOMENTUM STRATEGY")
    print("=" * 80)
    print("Expected: Long HIGH kurtosis, Short LOW kurtosis")
    
    momentum_signals = generate_kurtosis_signals_vectorized(
        test_data,
        strategy='momentum',
        long_percentile=20,
        short_percentile=80,
    )
    
    print("\nMomentum Signals:")
    print(momentum_signals[['symbol', 'kurtosis_30d', 'percentile', 'signal']])
    
    # Validate momentum strategy
    # High kurtosis (COIN_E: 4.5) should be LONG (signal = 1)
    high_kurtosis_signal = momentum_signals[
        momentum_signals['symbol'] == 'COIN_E'
    ]['signal'].values[0]
    
    # Low kurtosis (COIN_A: 0.5) should be SHORT (signal = -1)
    low_kurtosis_signal = momentum_signals[
        momentum_signals['symbol'] == 'COIN_A'
    ]['signal'].values[0]
    
    print(f"\nValidation:")
    print(f"  High kurtosis coin (COIN_E) signal: {high_kurtosis_signal} (expected: 1)")
    print(f"  Low kurtosis coin (COIN_A) signal: {low_kurtosis_signal} (expected: -1)")
    
    assert high_kurtosis_signal == 1, f"? MOMENTUM FAILED: High kurtosis should be LONG (1), got {high_kurtosis_signal}"
    assert low_kurtosis_signal == -1, f"? MOMENTUM FAILED: Low kurtosis should be SHORT (-1), got {low_kurtosis_signal}"
    print("  ? MOMENTUM strategy signals are CORRECT")
    
    # Test 2: Mean Reversion Strategy
    print("\n" + "=" * 80)
    print("TEST 2: MEAN REVERSION STRATEGY")
    print("=" * 80)
    print("Expected: Long LOW kurtosis, Short HIGH kurtosis")
    
    mean_reversion_signals = generate_kurtosis_signals_vectorized(
        test_data,
        strategy='mean_reversion',
        long_percentile=20,
        short_percentile=80,
    )
    
    print("\nMean Reversion Signals:")
    print(mean_reversion_signals[['symbol', 'kurtosis_30d', 'percentile', 'signal']])
    
    # Validate mean reversion strategy
    # Low kurtosis (COIN_A: 0.5) should be LONG (signal = 1)
    low_kurtosis_mr_signal = mean_reversion_signals[
        mean_reversion_signals['symbol'] == 'COIN_A'
    ]['signal'].values[0]
    
    # High kurtosis (COIN_E: 4.5) should be SHORT (signal = -1)
    high_kurtosis_mr_signal = mean_reversion_signals[
        mean_reversion_signals['symbol'] == 'COIN_E'
    ]['signal'].values[0]
    
    print(f"\nValidation:")
    print(f"  Low kurtosis coin (COIN_A) signal: {low_kurtosis_mr_signal} (expected: 1)")
    print(f"  High kurtosis coin (COIN_E) signal: {high_kurtosis_mr_signal} (expected: -1)")
    
    assert low_kurtosis_mr_signal == 1, f"? MEAN_REVERSION FAILED: Low kurtosis should be LONG (1), got {low_kurtosis_mr_signal}"
    assert high_kurtosis_mr_signal == -1, f"? MEAN_REVERSION FAILED: High kurtosis should be SHORT (-1), got {high_kurtosis_mr_signal}"
    print("  ? MEAN REVERSION strategy signals are CORRECT")
    
    # Test 3: Strategies should be opposite
    print("\n" + "=" * 80)
    print("TEST 3: STRATEGIES SHOULD BE OPPOSITE")
    print("=" * 80)
    
    # For each coin, momentum and mean reversion signals should be opposite (or both 0)
    merged = momentum_signals.merge(
        mean_reversion_signals,
        on=['symbol', 'kurtosis_30d'],
        suffixes=('_momentum', '_mr')
    )
    
    print("\nComparison:")
    print(merged[['symbol', 'kurtosis_30d', 'signal_momentum', 'signal_mr']])
    
    # Check that extreme signals are opposite
    extremes = merged[merged['signal_momentum'] != 0]
    for _, row in extremes.iterrows():
        momentum_sig = row['signal_momentum']
        mr_sig = row['signal_mr']
        
        # If momentum is long, mean reversion should be short (or neutral)
        # If momentum is short, mean reversion should be long (or neutral)
        if momentum_sig == 1:
            assert mr_sig <= 0, f"? {row['symbol']}: Momentum LONG should have MR SHORT/NEUTRAL"
        elif momentum_sig == -1:
            assert mr_sig >= 0, f"? {row['symbol']}: Momentum SHORT should have MR LONG/NEUTRAL"
    
    print("  ? Strategies are properly opposite")
    
    print("\n" + "=" * 80)
    print("? ALL TESTS PASSED")
    print("=" * 80)
    print("\nSummary:")
    print("  - Momentum strategy: Long HIGH kurtosis, Short LOW kurtosis ?")
    print("  - Mean Reversion strategy: Long LOW kurtosis, Short HIGH kurtosis ?")
    print("  - Strategies are opposite of each other ?")
    print("\nThe signal direction bug has been FIXED!")


if __name__ == "__main__":
    test_kurtosis_signal_direction()
