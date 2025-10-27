# OI Cache Date-Change Detection Update

## Summary

Updated the Coinalyze OI (Open Interest) cache to automatically invalidate when the date changes, even if the cache is less than 8 hours old. This ensures we always fetch fresh OI data when a new day starts.

## Problem

Previously, OI cache used only TTL (Time-To-Live) validation:
- Cache TTL: 8 hours
- Issue: If OI data was cached at 11 PM, it would remain valid until 7 AM the next day
- Result: Morning trading would use yesterday's OI data instead of fetching today's data

## Solution

Added **date-change detection** to OI cache validation:

### New Logic
```python
def _is_oi_cache_valid(cache_path):
    # 1. Check if date has changed (cache from previous day)
    if cache_date < today:
        return False  # INVALID - force refresh
    
    # 2. Check standard TTL
    if age > ttl_hours:
        return False  # INVALID - expired
    
    # 3. Valid: same day AND within TTL
    return True
```

### Validation Rules
| Scenario | Cache Age | Cache Date | Result | Reason |
|----------|-----------|------------|--------|--------|
| Morning after midnight | 6 hours | Yesterday | ❌ INVALID | Date changed |
| Same day, fresh | 2 hours | Today | ✅ VALID | Same day + within TTL |
| Same day, old | 10 hours | Today | ❌ INVALID | TTL expired |
| Yesterday, old | 24 hours | Yesterday | ❌ INVALID | Both date changed + TTL |

## Changes Made

### 1. Added `_is_oi_cache_valid()` method
**File:** `/workspace/data/scripts/coinalyze_cache.py`

New method that checks both date change AND TTL for OI-specific caching.

### 2. Updated `load_oi_history()` 
**File:** `/workspace/data/scripts/coinalyze_cache.py`

Changed from `_is_cache_valid()` to `_is_oi_cache_valid()` for OI data.

### 3. Updated `get_cache_info()`
**File:** `/workspace/data/scripts/coinalyze_cache.py`

Now correctly reports validation reason for OI cache files:
- `"date_changed"` - Cache is from a previous day
- `"ttl_expired"` - Cache exceeded TTL
- `"valid"` - Cache is valid

### 4. Updated documentation
Updated docstrings to explain the new date-change detection behavior.

## Testing

Created comprehensive test suite: `/workspace/data/scripts/test_oi_cache_date_change.py`

**Test Results:**
```
✅ PASS: Date Change Invalidation
   - Cache from yesterday (6h old) correctly invalidated
   
✅ PASS: Same Day Validation  
   - Cache from today (2h old) correctly validated
   
✅ PASS: TTL Expiration
   - Cache from today (10h old) correctly invalidated
```

All tests passed! ✅

## Impact

### For OI Divergence Strategy
- ✅ Always uses current day's OI data when available
- ✅ Automatically refreshes data after midnight
- ✅ Still benefits from 8-hour caching within the same day
- ✅ Reduces API calls (respects rate limits)

### For Carry Strategy
- ℹ️ No change - continues to use standard 1-hour TTL cache
- ℹ️ Funding rates don't require date-change detection

## Example Scenario

**Before:**
```
23:00 - Fetch OI data → Cache valid until 07:00 next day
00:30 - Use yesterday's cached OI data (stale!)
07:00 - Cache expires → Fetch fresh data
```

**After:**
```
23:00 - Fetch OI data → Cache valid until midnight or 07:00
00:01 - Date changed → Cache invalidated
00:30 - Fetch fresh OI data for today ✓
```

## Configuration

Default settings (no changes needed):
```python
cache = CoinalyzeCache(ttl_hours=8)  # OI data
```

The date-change detection is automatic for all OI cache operations.

## Files Modified

1. `/workspace/data/scripts/coinalyze_cache.py` - Core cache logic
2. `/workspace/data/scripts/test_oi_cache_date_change.py` - Test suite (new)

## Backward Compatibility

✅ Fully backward compatible
- Existing code continues to work without changes
- Only affects OI cache validation logic
- Non-OI caches (funding rates) use original TTL-only validation

---

**Date:** 2025-10-27  
**Status:** ✅ Implemented and Tested  
**Impact:** Low risk, high value - ensures fresh OI data for trading signals
