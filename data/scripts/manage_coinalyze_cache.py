#!/usr/bin/env python3
"""
Coinalyze Cache Management Script

Usage:
    python3 manage_coinalyze_cache.py info          # Show cache info
    python3 manage_coinalyze_cache.py populate      # Pre-populate cache
    python3 manage_coinalyze_cache.py clear         # Clear all cache
    python3 manage_coinalyze_cache.py clear funding # Clear funding rate cache
    python3 manage_coinalyze_cache.py clear oi      # Clear OI cache
"""
import sys
import argparse
from coinalyze_cache import CoinalyzeCache
from pathlib import Path


def show_info():
    """Show cache information"""
    cache = CoinalyzeCache()
    info = cache.get_cache_info()
    
    print("="*80)
    print("COINALYZE CACHE INFORMATION")
    print("="*80)
    print(f"\nCache directory: {info['cache_dir']}")
    print(f"TTL: {info['ttl_hours']} hours")
    print(f"\nTotal files: {len(info['files'])}")
    
    if not info['files']:
        print("\nNo cache files found.")
        return
    
    valid_count = sum(1 for f in info['files'] if f['is_valid'])
    expired_count = len(info['files']) - valid_count
    
    print(f"Valid: {valid_count}")
    print(f"Expired: {expired_count}")
    
    print("\n" + "-"*80)
    print(f"{'Status':<10} {'File':<40} {'Size':<10} {'Age (hrs)':<12}")
    print("-"*80)
    
    for f in sorted(info['files'], key=lambda x: x['age_hours']):
        status = "✓ VALID" if f['is_valid'] else "✗ EXPIRED"
        size_kb = f['size'] / 1024
        print(f"{status:<10} {f['name']:<40} {size_kb:>7.1f} KB  {f['age_hours']:>10.2f}")
    
    print("="*80)


def populate_cache():
    """Pre-populate cache with fresh data"""
    print("="*80)
    print("PRE-POPULATING COINALYZE CACHE")
    print("="*80)
    
    # Get market universe (top symbols by volume)
    print("\n[1/3] Fetching market universe...")
    try:
        import sys
        from pathlib import Path
        workspace_root = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(workspace_root))
        
        from execution.ccxt_get_markets_by_volume import ccxt_get_markets_by_volume
        
        df = ccxt_get_markets_by_volume()
        if df is not None and not df.empty:
            df_filtered = df[df['notional_volume_24h'] >= 100000]
            universe_symbols = df_filtered['symbol'].head(100).tolist()  # Top 100 by volume
            print(f"  Selected {len(universe_symbols)} symbols (volume >= $100k)")
        else:
            print("  Could not fetch markets. Using default universe.")
            universe_symbols = ['BTC/USDC:USDC', 'ETH/USDC:USDC', 'SOL/USDC:USDC']
    except Exception as e:
        print(f"  Error: {e}")
        universe_symbols = ['BTC/USDC:USDC', 'ETH/USDC:USDC', 'SOL/USDC:USDC']
    
    # Fetch and cache funding rates
    print("\n[2/3] Fetching funding rates (aggregated)...")
    try:
        from coinalyze_cache import fetch_coinalyze_aggregated_funding_cached
        
        df_funding = fetch_coinalyze_aggregated_funding_cached(
            universe_symbols=universe_symbols,
            cache_ttl_hours=1,
        )
        
        if df_funding is not None and not df_funding.empty:
            print(f"  ✓ Cached {len(df_funding)} funding rates")
        else:
            print("  ⚠️  No funding rate data available")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    # Fetch and cache OI history (Note: may not be available for Hyperliquid)
    print("\n[3/3] Fetching OI history...")
    print("  NOTE: OI history is NOT available for Hyperliquid on Coinalyze")
    print("  Skipping OI cache population. Use exchange_code='A' (Binance) if needed.")
    
    print("\n" + "="*80)
    print("CACHE POPULATION COMPLETE")
    print("="*80)
    
    # Show updated cache info
    print("")
    show_info()


def clear_cache(data_type=None):
    """Clear cache"""
    cache = CoinalyzeCache()
    
    print("="*80)
    if data_type:
        print(f"CLEARING {data_type.upper()} CACHE")
    else:
        print("CLEARING ALL CACHE")
    print("="*80)
    
    cache.clear_cache(data_type)
    
    print("\n✓ Cache cleared successfully")
    print("="*80)


def main():
    parser = argparse.ArgumentParser(
        description='Manage Coinalyze API cache',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 manage_coinalyze_cache.py info          # Show cache info
  python3 manage_coinalyze_cache.py populate      # Pre-populate cache
  python3 manage_coinalyze_cache.py clear         # Clear all cache
  python3 manage_coinalyze_cache.py clear funding # Clear funding rate cache
  python3 manage_coinalyze_cache.py clear oi      # Clear OI cache
        """
    )
    
    parser.add_argument('command', choices=['info', 'populate', 'clear'],
                       help='Command to execute')
    parser.add_argument('cache_type', nargs='?', choices=['funding', 'oi'],
                       help='Cache type (for clear command)')
    
    args = parser.parse_args()
    
    if args.command == 'info':
        show_info()
    elif args.command == 'populate':
        populate_cache()
    elif args.command == 'clear':
        if args.cache_type == 'funding':
            clear_cache('funding_rates')
        elif args.cache_type == 'oi':
            clear_cache('oi_history')
        else:
            clear_cache()
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
