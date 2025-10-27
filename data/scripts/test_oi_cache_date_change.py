#!/usr/bin/env python3
"""
Test OI cache date-change detection

This test verifies that OI cache is invalidated when the date changes,
even if the cache is less than 8 hours old.
"""
import os
import sys
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
import json

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from coinalyze_cache import CoinalyzeCache

def test_date_change_invalidation():
    """Test that OI cache is invalidated when date changes"""
    print("="*80)
    print("TEST: OI Cache Date-Change Invalidation")
    print("="*80)
    
    # Create temp cache directory
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = CoinalyzeCache(cache_dir=tmpdir, ttl_hours=8)
        
        # Create a mock cache file from yesterday
        cache_path = cache._get_cache_path('oi_history', 'A_days30')
        
        # Create cache data
        mock_data = {
            'timestamp': (datetime.now() - timedelta(days=1)).isoformat(),
            'exchange_code': 'A',
            'days': 30,
            'data': [{'date': '2025-10-26', 'value': 100}]
        }
        
        with open(cache_path, 'w') as f:
            json.dump(mock_data, f)
        
        # Set file modification time to yesterday (but <8h ago - e.g., 6 hours ago)
        yesterday = datetime.now() - timedelta(hours=6)
        os.utime(cache_path, (yesterday.timestamp(), yesterday.timestamp()))
        
        print(f"\nTest Setup:")
        print(f"  Cache file: {cache_path.name}")
        print(f"  Mock mtime: {yesterday} ({yesterday.date()})")
        print(f"  Current time: {datetime.now()} ({datetime.now().date()})")
        print(f"  Age: 6 hours (within 8h TTL)")
        print(f"  Date changed: {yesterday.date() < datetime.now().date()}")
        
        # Test 1: Standard _is_cache_valid (should pass - <8h old)
        print(f"\nTest 1: Standard validation (_is_cache_valid)")
        is_valid_standard = cache._is_cache_valid(cache_path)
        print(f"  Result: {'✓ VALID' if is_valid_standard else '✗ INVALID'}")
        print(f"  Expected: ✓ VALID (age <8h)")
        
        # Test 2: OI-specific _is_oi_cache_valid (should fail - date changed)
        print(f"\nTest 2: OI-specific validation (_is_oi_cache_valid)")
        is_valid_oi = cache._is_oi_cache_valid(cache_path)
        print(f"  Result: {'✓ VALID' if is_valid_oi else '✗ INVALID'}")
        print(f"  Expected: ✗ INVALID (date changed)")
        
        # Verify results
        print(f"\n{'='*80}")
        if is_valid_standard and not is_valid_oi:
            print("✅ TEST PASSED")
            print("   - Standard validation: VALID (correctly checks only TTL)")
            print("   - OI validation: INVALID (correctly detects date change)")
            return True
        else:
            print("❌ TEST FAILED")
            print(f"   - Standard validation: {is_valid_standard} (expected: True)")
            print(f"   - OI validation: {is_valid_oi} (expected: False)")
            return False


def test_same_day_cache():
    """Test that OI cache is valid when cached on the same day"""
    print("\n" + "="*80)
    print("TEST: OI Cache Same-Day Validation")
    print("="*80)
    
    # Create temp cache directory
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = CoinalyzeCache(cache_dir=tmpdir, ttl_hours=8)
        
        # Create a mock cache file from earlier today
        cache_path = cache._get_cache_path('oi_history', 'A_days30')
        
        # Create cache data
        mock_data = {
            'timestamp': datetime.now().isoformat(),
            'exchange_code': 'A',
            'days': 30,
            'data': [{'date': '2025-10-27', 'value': 100}]
        }
        
        with open(cache_path, 'w') as f:
            json.dump(mock_data, f)
        
        # Set file modification time to 2 hours ago (same day, within TTL)
        two_hours_ago = datetime.now() - timedelta(hours=2)
        os.utime(cache_path, (two_hours_ago.timestamp(), two_hours_ago.timestamp()))
        
        print(f"\nTest Setup:")
        print(f"  Cache file: {cache_path.name}")
        print(f"  Mock mtime: {two_hours_ago} ({two_hours_ago.date()})")
        print(f"  Current time: {datetime.now()} ({datetime.now().date()})")
        print(f"  Age: 2 hours (within 8h TTL)")
        print(f"  Same day: {two_hours_ago.date() == datetime.now().date()}")
        
        # Test OI-specific validation (should pass - same day and within TTL)
        print(f"\nTest: OI-specific validation (_is_oi_cache_valid)")
        is_valid_oi = cache._is_oi_cache_valid(cache_path)
        print(f"  Result: {'✓ VALID' if is_valid_oi else '✗ INVALID'}")
        print(f"  Expected: ✓ VALID (same day, within TTL)")
        
        # Verify results
        print(f"\n{'='*80}")
        if is_valid_oi:
            print("✅ TEST PASSED")
            print("   - OI validation: VALID (correctly allows same-day cache)")
            return True
        else:
            print("❌ TEST FAILED")
            print(f"   - OI validation: {is_valid_oi} (expected: True)")
            return False


def test_ttl_expiration():
    """Test that OI cache is invalidated when TTL expires (even same day)"""
    print("\n" + "="*80)
    print("TEST: OI Cache TTL Expiration")
    print("="*80)
    
    # Create temp cache directory with short TTL
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = CoinalyzeCache(cache_dir=tmpdir, ttl_hours=1)  # 1 hour TTL
        
        # Create a mock cache file from 2 hours ago (same day but TTL expired)
        cache_path = cache._get_cache_path('oi_history', 'A_days30')
        
        # Create cache data
        mock_data = {
            'timestamp': (datetime.now() - timedelta(hours=2)).isoformat(),
            'exchange_code': 'A',
            'days': 30,
            'data': [{'date': '2025-10-27', 'value': 100}]
        }
        
        with open(cache_path, 'w') as f:
            json.dump(mock_data, f)
        
        # Set file modification time to 2 hours ago (same day but beyond 1h TTL)
        two_hours_ago = datetime.now() - timedelta(hours=2)
        os.utime(cache_path, (two_hours_ago.timestamp(), two_hours_ago.timestamp()))
        
        print(f"\nTest Setup:")
        print(f"  Cache file: {cache_path.name}")
        print(f"  Mock mtime: {two_hours_ago} ({two_hours_ago.date()})")
        print(f"  Current time: {datetime.now()} ({datetime.now().date()})")
        print(f"  Age: 2 hours (beyond 1h TTL)")
        print(f"  Same day: {two_hours_ago.date() == datetime.now().date()}")
        
        # Test OI-specific validation (should fail - TTL expired)
        print(f"\nTest: OI-specific validation (_is_oi_cache_valid)")
        is_valid_oi = cache._is_oi_cache_valid(cache_path)
        print(f"  Result: {'✓ VALID' if is_valid_oi else '✗ INVALID'}")
        print(f"  Expected: ✗ INVALID (TTL expired)")
        
        # Verify results
        print(f"\n{'='*80}")
        if not is_valid_oi:
            print("✅ TEST PASSED")
            print("   - OI validation: INVALID (correctly detects TTL expiration)")
            return True
        else:
            print("❌ TEST FAILED")
            print(f"   - OI validation: {is_valid_oi} (expected: False)")
            return False


if __name__ == "__main__":
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*20 + "OI CACHE DATE-CHANGE DETECTION TESTS" + " "*22 + "║")
    print("╚" + "="*78 + "╝")
    print()
    
    results = []
    
    # Run tests
    results.append(("Date Change Invalidation", test_date_change_invalidation()))
    results.append(("Same Day Validation", test_same_day_cache()))
    results.append(("TTL Expiration", test_ttl_expiration()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(result for _, result in results)
    print("="*80)
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED")
        sys.exit(1)
