#!/usr/bin/env python3
"""
Demo: OI Cache Date-Change Detection

This demonstrates how the new OI cache invalidation works when the date changes.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from coinalyze_cache import CoinalyzeCache

def demo():
    print("="*80)
    print("DEMONSTRATION: OI Cache Date-Change Detection")
    print("="*80)
    
    # Initialize cache
    cache = CoinalyzeCache(ttl_hours=8)
    
    print("\n📋 Configuration:")
    print(f"   Cache directory: {cache.cache_dir}")
    print(f"   Cache TTL: {cache.ttl_hours} hours")
    
    print("\n📝 New Behavior:")
    print("   ✅ OI cache is INVALIDATED if date changes (even if <8h old)")
    print("   ✅ OI cache is VALID if same day AND within 8h")
    print("   ✅ Funding rate cache uses standard TTL-only validation")
    
    print("\n🎯 Benefits:")
    print("   • Always uses today's OI data when available")
    print("   • Automatically refreshes after midnight")
    print("   • Prevents stale OI signals in morning trading")
    print("   • Still caches efficiently during the day (8h TTL)")
    
    print("\n📊 Example Timeline:")
    print("   23:00 → Fetch OI data, cache created")
    print("   23:59 → Still using cache (same day, <8h)")
    print("   00:01 → ⚠️  Date changed! Cache invalidated")
    print("   00:02 → Fetch fresh OI data for new day")
    print("   08:00 → Still using cache (same day, <8h)")
    
    # Show current cache status
    info = cache.get_cache_info()
    
    if info['files']:
        print(f"\n📁 Current Cache Files ({len(info['files'])}):")
        print("-" * 80)
        for f in info['files']:
            status = "✓ VALID" if f['is_valid'] else "✗ EXPIRED"
            reason = f.get('validation_reason', 'N/A')
            is_oi = 'oi_history' in f['name']
            cache_type = "OI" if is_oi else "Funding"
            
            print(f"  {status:12s} [{cache_type:7s}] {f['name']:30s}")
            print(f"               Age: {f['age_hours']:.2f}h | Reason: {reason}")
            
            if is_oi and not f['is_valid'] and reason == 'date_changed':
                print(f"               ⚠️  Will be refreshed due to date change")
        print("-" * 80)
    else:
        print("\n📁 No cache files found (cache is empty)")
    
    print("\n✅ Date-change detection is now ACTIVE for OI cache!")
    print("="*80)


if __name__ == "__main__":
    demo()
