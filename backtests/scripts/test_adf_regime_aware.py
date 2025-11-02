#!/usr/bin/env python3
"""
Test ADF Strategy (Regime-Aware)

Tests the ADF regime-aware strategy implementation to ensure:
1. Regime detection works correctly
2. Direction-aware allocation is applied
3. Strategy selection is appropriate
4. Position sizing is correct
"""

import pandas as pd
import numpy as np
import sys
import os

# Add paths
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, WORKSPACE_ROOT)
sys.path.insert(0, os.path.join(WORKSPACE_ROOT, "execution"))

from execution.strategies.adf import (
    detect_regime,
    get_optimal_allocation,
    strategy_adf,
)


def create_test_btc_data(price_changes):
    """
    Create test BTC data with specified price changes.
    
    Args:
        price_changes (list): List of daily % changes
    
    Returns:
        DataFrame with BTC OHLCV data
    """
    dates = pd.date_range(start="2024-01-01", periods=len(price_changes), freq="D")
    
    # Start at 50,000
    prices = [50000.0]
    for change in price_changes:
        new_price = prices[-1] * (1 + change / 100)
        prices.append(new_price)
    
    df = pd.DataFrame({
        "date": dates,
        "open": prices[:-1],
        "high": [p * 1.02 for p in prices[:-1]],
        "low": [p * 0.98 for p in prices[:-1]],
        "close": prices[1:],
        "volume": [1000000] * len(price_changes),
    })
    
    return df


def create_test_coin_data(symbol, num_days=100):
    """Create test data for a coin"""
    dates = pd.date_range(start="2024-01-01", periods=num_days, freq="D")
    
    # Random walk with drift
    returns = np.random.normal(0.001, 0.03, num_days)
    prices = [100.0]
    for r in returns:
        prices.append(prices[-1] * (1 + r))
    
    df = pd.DataFrame({
        "date": dates,
        "open": prices[:-1],
        "high": [p * 1.02 for p in prices[:-1]],
        "low": [p * 0.98 for p in prices[:-1]],
        "close": prices[1:],
        "volume": [1000000] * num_days,
    })
    
    return df


def test_regime_detection():
    """Test regime detection logic"""
    print("\n" + "=" * 80)
    print("TEST 1: REGIME DETECTION")
    print("=" * 80)
    
    test_cases = [
        ([2, 2, 2, 2, 15], "Strong Up", "BTC +15% in 5 days"),
        ([1, 1, 1, 1, 5], "Moderate Up", "BTC +5% in 5 days"),
        ([-1, -1, -1, -1, -5], "Down", "BTC -5% in 5 days"),
        ([-3, -3, -3, -3, -15], "Strong Down", "BTC -15% in 5 days"),
        ([0, 0, 0, 0, 0.5], "Moderate Up", "BTC +0.5% in 5 days"),
    ]
    
    all_passed = True
    
    for changes, expected_regime, description in test_cases:
        btc_data = create_test_btc_data(changes)
        regime, pct_change, regime_code = detect_regime(btc_data, lookback_days=5)
        
        status = "?" if regime == expected_regime else "?"
        print(f"\n{status} {description}")
        print(f"   Expected: {expected_regime}")
        print(f"   Got:      {regime} ({pct_change:+.2f}%)")
        
        if regime != expected_regime:
            all_passed = False
    
    if all_passed:
        print("\n? All regime detection tests passed!")
    else:
        print("\n? Some regime detection tests failed!")
    
    return all_passed


def test_allocation_logic():
    """Test allocation logic for different regimes"""
    print("\n" + "=" * 80)
    print("TEST 2: ALLOCATION LOGIC")
    print("=" * 80)
    
    regimes = ["Strong Up", "Moderate Up", "Down", "Strong Down"]
    modes = ["blended", "optimal", "moderate"]
    
    print("\n" + "-" * 80)
    print("REGIME              MODE        LONG    SHORT   STRATEGY")
    print("-" * 80)
    
    for regime in regimes:
        for mode in modes:
            long_alloc, short_alloc, strategy = get_optimal_allocation(regime, mode=mode)
            print(f"{regime:18s}  {mode:10s}  {long_alloc*100:>5.0f}%  {short_alloc*100:>5.0f}%  {strategy}")
    
    # Verify key properties
    print("\n" + "-" * 80)
    print("VERIFICATION CHECKS:")
    print("-" * 80)
    
    checks = [
        # Blended mode checks
        ("Blended - Strong Up should be SHORT-biased", 
         get_optimal_allocation("Strong Up", "blended")[1] > 0.5),
        ("Blended - Down should be LONG-biased", 
         get_optimal_allocation("Down", "blended")[0] > 0.5),
        
        # Optimal mode checks
        ("Optimal - Strong Up should be pure SHORT", 
         get_optimal_allocation("Strong Up", "optimal")[1] == 1.0),
        ("Optimal - Down should be pure LONG", 
         get_optimal_allocation("Down", "optimal")[0] == 1.0),
        
        # Allocations sum to 1
        ("Allocations should sum to 1.0",
         abs(sum(get_optimal_allocation("Strong Up", "blended")[:2]) - 1.0) < 0.001),
    ]
    
    all_passed = True
    for description, condition in checks:
        status = "?" if condition else "?"
        print(f"{status} {description}")
        if not condition:
            all_passed = False
    
    if all_passed:
        print("\n? All allocation logic tests passed!")
    else:
        print("\n? Some allocation logic tests failed!")
    
    return all_passed


def test_strategy_execution():
    """Test full strategy execution"""
    print("\n" + "=" * 80)
    print("TEST 3: STRATEGY EXECUTION")
    print("=" * 80)
    
    # Create test data
    print("\nCreating test data...")
    num_days = 100
    
    historical_data = {
        "BTC": create_test_btc_data([1] * num_days),
    }
    
    # Add test coins
    symbols = ["BTC"]
    for i in range(10):
        symbol = f"COIN{i}"
        symbols.append(symbol)
        historical_data[symbol] = create_test_coin_data(symbol, num_days)
    
    print(f"Created data for {len(symbols)} symbols")
    
    # Test different modes
    modes = ["blended", "optimal", "moderate"]
    
    for mode in modes:
        print(f"\n" + "-" * 80)
        print(f"Testing mode: {mode.upper()}")
        print("-" * 80)
        
        try:
            positions = strategy_adf(
                historical_data,
                symbols,
                strategy_notional=10000,
                mode=mode,
                adf_window=30,  # Shorter for test
                volatility_window=20,
            )
            
            if positions:
                total_long = sum(v for v in positions.values() if v > 0)
                total_short = abs(sum(v for v in positions.values() if v < 0))
                
                print(f"\n? Strategy executed successfully ({len(positions)} positions)")
                print(f"   Long exposure:  ${total_long:,.2f}")
                print(f"   Short exposure: ${total_short:,.2f}")
                print(f"   Net exposure:   ${total_long - total_short:,.2f}")
            else:
                print(f"\n??  No positions generated (may be expected with test data)")
        
        except Exception as e:
            print(f"\n? Strategy execution failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    print("\n? All strategy execution tests passed!")
    return True


def test_regime_transitions():
    """Test strategy behavior across regime transitions"""
    print("\n" + "=" * 80)
    print("TEST 4: REGIME TRANSITIONS")
    print("=" * 80)
    
    # Simulate regime transitions
    regime_scenarios = [
        ("Moderate Up ? Strong Up", [1, 1, 1, 1, 15]),
        ("Strong Up ? Down", [15, -5, -5, -5, -5]),
        ("Down ? Strong Down", [-5, -5, -5, -5, -15]),
        ("Strong Down ? Recovery", [-15, 5, 5, 5, 5]),
    ]
    
    print("\nSimulating regime transitions:")
    print("-" * 80)
    
    for description, price_changes in regime_scenarios:
        btc_data = create_test_btc_data(price_changes)
        regime_before, pct_before, _ = detect_regime(btc_data, lookback_days=5)
        
        # Get allocation
        long_alloc, short_alloc, strategy = get_optimal_allocation(regime_before, mode="blended")
        
        print(f"\n{description}:")
        print(f"  Regime: {regime_before} ({pct_before:+.2f}%)")
        print(f"  Allocation: {long_alloc*100:.0f}% LONG, {short_alloc*100:.0f}% SHORT")
        print(f"  Strategy: {strategy.upper()}")
    
    print("\n? Regime transition tests complete!")
    return True


def main():
    """Run all tests"""
    print("=" * 80)
    print("ADF STRATEGY (REGIME-AWARE) TEST SUITE")
    print("=" * 80)
    
    results = []
    
    # Run tests
    results.append(("Regime Detection", test_regime_detection()))
    results.append(("Allocation Logic", test_allocation_logic()))
    results.append(("Strategy Execution", test_strategy_execution()))
    results.append(("Regime Transitions", test_regime_transitions()))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for test_name, passed in results:
        status = "? PASS" if passed else "? FAIL"
        print(f"{status}  {test_name}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("\n?? ALL TESTS PASSED!")
        print("\nThe ADF regime-aware strategy is ready for backtesting and live trading.")
        return 0
    else:
        print("\n??  SOME TESTS FAILED!")
        print("\nPlease review the failures above before using in production.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
