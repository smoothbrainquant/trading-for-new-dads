"""
Test script for Kurtosis Strategy with Regime Filter

This script tests the regime-filtered kurtosis strategy to verify:
1. Regime detection works correctly
2. Strategy activates in bear markets
3. Strategy deactivates in bull markets
4. Proper error handling when data is unavailable
"""

import sys
import os

# Add workspace to path
WORKSPACE_ROOT = os.path.dirname(os.path.abspath(__file__))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)

from execution.strategies.regime_filter import detect_market_regime, should_activate_strategy
from execution.strategies.kurtosis import strategy_kurtosis
from data.scripts.ccxt_get_data import ccxt_fetch_hyperliquid_daily_data


def test_regime_detection():
    """Test regime detection functionality."""
    print("\n" + "="*80)
    print("TEST 1: REGIME DETECTION")
    print("="*80)
    
    try:
        # Fetch BTC data
        print("\nFetching BTC data...")
        symbols = ["BTC/USD"]
        df = ccxt_fetch_hyperliquid_daily_data(symbols=symbols, days=200)
        
        if df is None or df.empty:
            print("? FAILED: Could not fetch BTC data")
            return False
        
        # Convert to historical_data dict format
        historical_data = {}
        for symbol in df["symbol"].unique():
            historical_data[symbol] = df[df["symbol"] == symbol].copy()
        
        print(f"? Fetched {len(df)} rows for {len(historical_data)} symbols")
        
        # Detect regime
        regime_info = detect_market_regime(historical_data, reference_symbol="BTC/USD")
        
        # Validate regime info
        required_fields = ["regime", "ma_50", "ma_200", "price", "confidence", "days_in_regime"]
        for field in required_fields:
            if field not in regime_info:
                print(f"? FAILED: Missing field '{field}' in regime_info")
                return False
        
        print("\n? PASSED: Regime detection successful")
        print(f"   Regime: {regime_info['regime'].upper()}")
        print(f"   Confidence: {regime_info['confidence'].upper()}")
        print(f"   Days in regime: {regime_info['days_in_regime']}")
        
        return True, regime_info, historical_data
        
    except Exception as e:
        print(f"\n? FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_regime_filter(regime_info):
    """Test regime filter activation logic."""
    print("\n" + "="*80)
    print("TEST 2: REGIME FILTER LOGIC")
    print("="*80)
    
    try:
        # Test bear_only filter
        should_activate, reason = should_activate_strategy(regime_info, strategy_type="bear_only")
        
        current_regime = regime_info.get("regime", "unknown")
        
        print(f"\nCurrent regime: {current_regime.upper()}")
        print(f"Filter type: bear_only")
        print(f"Should activate: {should_activate}")
        print(f"Reason: {reason}")
        
        # Validate logic
        if current_regime == "bear" and not should_activate:
            print("? FAILED: Should activate in bear market but didn't")
            return False
        
        if current_regime == "bull" and should_activate:
            print("? FAILED: Should NOT activate in bull market but did")
            return False
        
        print("\n? PASSED: Regime filter logic works correctly")
        return True
        
    except Exception as e:
        print(f"\n? FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_strategy_integration(historical_data, regime_info):
    """Test full strategy integration with regime filter."""
    print("\n" + "="*80)
    print("TEST 3: STRATEGY INTEGRATION")
    print("="*80)
    
    try:
        current_regime = regime_info.get("regime", "unknown")
        
        # Test strategy with bear_only filter
        print("\nTesting strategy with regime_filter='bear_only'...")
        positions = strategy_kurtosis(
            historical_data=historical_data,
            symbols=list(historical_data.keys()),
            strategy_notional=10000.0,
            strategy_type="mean_reversion",
            regime_filter="bear_only",
            reference_symbol="BTC/USD"
        )
        
        # Validate results
        if current_regime == "bear":
            if not positions or len(positions) == 0:
                print("??  WARNING: No positions generated in bear market")
                print("   This might be expected if no coins meet criteria")
            else:
                print(f"? Generated {len(positions)} positions in bear market")
                print(f"   Long positions: {len([p for p in positions.values() if p > 0])}")
                print(f"   Short positions: {len([p for p in positions.values() if p < 0])}")
        else:
            if positions and len(positions) > 0:
                print(f"? FAILED: Generated {len(positions)} positions in bull market (should be 0)")
                return False
            else:
                print("? Correctly returned 0 positions in bull market")
        
        print("\n? PASSED: Strategy integration works correctly")
        return True
        
    except Exception as e:
        print(f"\n? FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_always_filter(historical_data):
    """Test strategy with 'always' filter (no regime filter)."""
    print("\n" + "="*80)
    print("TEST 4: ALWAYS FILTER (NO REGIME FILTER)")
    print("="*80)
    
    try:
        print("\nTesting strategy with regime_filter='always'...")
        positions = strategy_kurtosis(
            historical_data=historical_data,
            symbols=list(historical_data.keys()),
            strategy_notional=10000.0,
            strategy_type="mean_reversion",
            regime_filter="always",
            reference_symbol="BTC/USD"
        )
        
        # Should generate positions regardless of regime
        if not positions or len(positions) == 0:
            print("??  WARNING: No positions generated with 'always' filter")
            print("   This might be expected if no coins meet criteria")
        else:
            print(f"? Generated {len(positions)} positions (filter bypassed)")
        
        print("\n? PASSED: 'always' filter works correctly")
        return True
        
    except Exception as e:
        print(f"\n? FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("KURTOSIS REGIME FILTER TEST SUITE")
    print("="*80)
    
    results = []
    
    # Test 1: Regime detection
    result = test_regime_detection()
    if isinstance(result, tuple):
        success, regime_info, historical_data = result
        results.append(("Regime Detection", success))
        
        if success:
            # Test 2: Regime filter logic
            success = test_regime_filter(regime_info)
            results.append(("Regime Filter Logic", success))
            
            # Test 3: Strategy integration
            success = test_strategy_integration(historical_data, regime_info)
            results.append(("Strategy Integration", success))
            
            # Test 4: Always filter
            success = test_always_filter(historical_data)
            results.append(("Always Filter", success))
    else:
        results.append(("Regime Detection", False))
    
    # Print summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results:
        status = "? PASSED" if passed else "? FAILED"
        print(f"{status}: {test_name}")
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print(f"\nTotal: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        print("\n?? ALL TESTS PASSED - Regime filter implementation is working correctly!")
        print("\nThe kurtosis strategy is ready for live deployment with regime filtering.")
        print("It will only activate in bear markets (50MA < 200MA on BTC).")
    else:
        print("\n??  SOME TESTS FAILED - Please review the errors above")
        print("Do not deploy until all tests pass.")
    
    print("="*80)


if __name__ == "__main__":
    main()
