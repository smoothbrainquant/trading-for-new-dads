#!/usr/bin/env python3
"""
Test CMC_API Environment Variable

This script verifies that the CMC_API environment variable is properly
configured and accessible to the fetch functions.
"""

import os
from fetch_coinmarketcap_data import fetch_historical_top100_quarterly

def main():
    print("=" * 80)
    print("CMC_API ENVIRONMENT VARIABLE TEST")
    print("=" * 80)
    
    # Check if CMC_API is set
    api_key = os.environ.get('CMC_API')
    
    if api_key:
        print(f"\n✓ CMC_API environment variable is SET")
        print(f"  Key length: {len(api_key)} characters")
        print(f"  First 8 chars: {api_key[:8]}...")
        print(f"  Last 4 chars: ...{api_key[-4:]}")
    else:
        print("\n❌ CMC_API environment variable is NOT set")
        print("\nTo set it, run:")
        print("  export CMC_API='your-api-key-here'")
        print("\nOr add to your ~/.bashrc or ~/.zshrc:")
        print("  echo 'export CMC_API=\"your-api-key-here\"' >> ~/.bashrc")
        return
    
    print("\n" + "=" * 80)
    print("TESTING API ACCESS")
    print("=" * 80)
    
    print("\nAttempting to fetch historical data (this will make actual API calls)...")
    print("Fetching only 2020-Q1 to test (1 API call)...")
    
    from datetime import datetime
    
    # Test with just one quarter to avoid using many API credits
    df = fetch_historical_top100_quarterly(
        api_key=None,  # Will automatically use CMC_API env var
        start_year=2020,
        end_date=datetime(2020, 3, 31),  # Only Q1 2020
        limit=10,  # Only top 10 to save credits
        delay_seconds=0
    )
    
    if df is not None and len(df) > 0:
        print("\n✓ API test SUCCESSFUL!")
        print(f"\nReceived {len(df)} records:")
        print(df[['snapshot_date', 'quarter', 'symbol', 'name', 'market_cap']].to_string(index=False))
    else:
        print("\n❌ API test FAILED")
        print("This could mean:")
        print("  1. Invalid API key")
        print("  2. API plan doesn't include historical data")
        print("  3. Network/connection issue")
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
