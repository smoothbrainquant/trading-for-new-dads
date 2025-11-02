#!/usr/bin/env python3
"""
Unified Factor Data Refresh Script

This script orchestrates the complete data refresh pipeline for all factor strategies:
1. Refresh Open Interest data (from Coinalyze)
2. Refresh Market Cap data (from CoinMarketCap)
3. Calculate Leverage metrics (OI / Market Cap ratios)
4. Calculate Dilution metrics (supply metrics from CoinMarketCap)

Run this before executing trading strategies to ensure all factor data is fresh.

Usage:
    python3 data/scripts/refresh_all_factor_data.py
    python3 data/scripts/refresh_all_factor_data.py --force  # Force refresh regardless of freshness
    python3 data/scripts/refresh_all_factor_data.py --check-only  # Only check status
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import subprocess

# Add workspace root to path
WORKSPACE_ROOT = Path(__file__).parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))


def print_section(title):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def run_script(script_path, description, args=None, capture_output=False):
    """
    Run a Python script and handle errors.
    
    Args:
        script_path: Path to Python script
        description: Human-readable description
        args: Optional list of command-line arguments
        capture_output: If True, return output; if False, stream to console
    
    Returns:
        True if successful, False otherwise
    """
    print(f"\n? {description}")
    print(f"  Script: {script_path}")
    
    cmd = [sys.executable, str(script_path)]
    if args:
        cmd.extend(args)
    
    try:
        if capture_output:
            result = subprocess.run(
                cmd,
                cwd=str(WORKSPACE_ROOT),
                capture_output=True,
                text=True,
                check=True
            )
            print(result.stdout)
            return True
        else:
            result = subprocess.run(
                cmd,
                cwd=str(WORKSPACE_ROOT),
                check=True
            )
            return True
    except subprocess.CalledProcessError as e:
        print(f"\n? ERROR running {description}")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"Error details: {e.stderr}")
        return False
    except Exception as e:
        print(f"\n? EXCEPTION running {description}: {e}")
        return False


def check_api_keys():
    """Check if required API keys are set."""
    print_section("API KEY CHECK")
    
    required_keys = {
        "CMC_API": "CoinMarketCap (for market cap and dilution data)",
        "COINALYZE_API": "Coinalyze (for open interest data)"
    }
    
    missing_keys = []
    for key, description in required_keys.items():
        if os.environ.get(key):
            print(f"? {key} is set - {description}")
        else:
            print(f"? {key} is NOT set - {description}")
            missing_keys.append(key)
    
    if missing_keys:
        print(f"\n??  WARNING: Missing API keys: {', '.join(missing_keys)}")
        print("   Some data refresh operations may fail or use mock data")
        return False
    
    print("\n? All required API keys are set")
    return True


def refresh_open_interest_data(force=False):
    """Refresh Open Interest data from Coinalyze."""
    print_section("STEP 1: REFRESH OPEN INTEREST DATA")
    
    script = WORKSPACE_ROOT / "data" / "scripts" / "refresh_oi_data.py"
    
    if not script.exists():
        print(f"? ERROR: Script not found: {script}")
        return False
    
    args = []
    if force:
        args.append("--force")
    
    success = run_script(
        script,
        "Refreshing Open Interest data from Coinalyze",
        args=args
    )
    
    if success:
        print("\n? Open Interest data refresh complete")
    else:
        print("\n? Open Interest data refresh failed")
    
    return success


def refresh_market_cap_data():
    """Refresh Market Cap data from CoinMarketCap."""
    print_section("STEP 2: REFRESH MARKET CAP DATA")
    
    script = WORKSPACE_ROOT / "data" / "scripts" / "fetch_coinmarketcap_data.py"
    
    if not script.exists():
        print(f"? ERROR: Script not found: {script}")
        return False
    
    # Set output path to data/raw
    output_path = WORKSPACE_ROOT / "data" / "raw" / "crypto_marketcap_latest.csv"
    args = [
        "--limit", "300",
        "--output", str(output_path)
    ]
    
    success = run_script(
        script,
        "Fetching Market Cap data from CoinMarketCap",
        args=args
    )
    
    if success:
        print(f"\n? Market Cap data saved to: {output_path}")
    else:
        print("\n? Market Cap data refresh failed")
    
    return success


def calculate_leverage_metrics():
    """Calculate leverage metrics from OI and Market Cap data."""
    print_section("STEP 3: CALCULATE LEVERAGE METRICS")
    
    script = WORKSPACE_ROOT / "signals" / "analyze_leverage_ratios.py"
    
    if not script.exists():
        print(f"? ERROR: Script not found: {script}")
        return False
    
    success = run_script(
        script,
        "Calculating leverage metrics (OI / Market Cap ratios)"
    )
    
    if success:
        print("\n? Leverage metrics calculated")
    else:
        print("\n? Leverage metrics calculation failed")
    
    return success


def calculate_dilution_metrics():
    """Calculate dilution metrics from Market Cap data."""
    print_section("STEP 4: CALCULATE DILUTION METRICS")
    
    script = WORKSPACE_ROOT / "data" / "scripts" / "fetch_crypto_dilution_top50.py"
    
    if not script.exists():
        print(f"? ERROR: Script not found: {script}")
        return False
    
    # Set output path
    output_path = WORKSPACE_ROOT / "crypto_dilution_top50.csv"
    args = [
        "--limit", "150",
        "--output", str(output_path)
    ]
    
    success = run_script(
        script,
        "Calculating dilution metrics from supply data",
        args=args
    )
    
    if success:
        print(f"\n? Dilution metrics saved to: {output_path}")
    else:
        print("\n? Dilution metrics calculation failed")
    
    return success


def print_summary(results):
    """Print summary of data refresh operations."""
    print_section("DATA REFRESH SUMMARY")
    
    steps = [
        ("Open Interest Data", results.get("oi", False)),
        ("Market Cap Data", results.get("marketcap", False)),
        ("Leverage Metrics", results.get("leverage", False)),
        ("Dilution Metrics", results.get("dilution", False))
    ]
    
    print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    all_success = True
    for step_name, success in steps:
        status = "? SUCCESS" if success else "? FAILED"
        print(f"  {status:12s} - {step_name}")
        if not success:
            all_success = False
    
    print("\n" + "=" * 80)
    
    if all_success:
        print("? ALL DATA REFRESH OPERATIONS COMPLETED SUCCESSFULLY")
        print("\nFactor strategies can now be run with fresh data:")
        print("  - leverage_inverted: Uses OI/Market Cap ratios")
        print("  - dilution: Uses supply dilution metrics")
    else:
        print("??  SOME DATA REFRESH OPERATIONS FAILED")
        print("\nPlease review errors above and ensure:")
        print("  - API keys are set (CMC_API, COINALYZE_API)")
        print("  - Network connectivity is available")
        print("  - API rate limits have not been exceeded")
    
    print("=" * 80)
    
    return all_success


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Refresh all factor data (OI, Market Cap, Leverage, Dilution)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force refresh even if data is fresh"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check data status, do not refresh"
    )
    parser.add_argument(
        "--skip-oi",
        action="store_true",
        help="Skip Open Interest data refresh (faster for testing)"
    )
    
    args = parser.parse_args()
    
    print_section("UNIFIED FACTOR DATA REFRESH")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check API keys
    api_keys_ok = check_api_keys()
    
    if args.check_only:
        print("\n[Check-only mode - no data refresh performed]")
        return
    
    # Track results
    results = {}
    
    # Step 1: Refresh Open Interest data
    if args.skip_oi:
        print_section("STEP 1: SKIPPED - Open Interest Data")
        print("  (using existing OI data)")
        results["oi"] = True
    else:
        results["oi"] = refresh_open_interest_data(force=args.force)
    
    # Step 2: Refresh Market Cap data
    results["marketcap"] = refresh_market_cap_data()
    
    # Step 3: Calculate Leverage metrics (depends on OI + Market Cap)
    if results["oi"] and results["marketcap"]:
        results["leverage"] = calculate_leverage_metrics()
    else:
        print_section("STEP 3: SKIPPED - Leverage Metrics")
        print("  (requires both OI and Market Cap data to be fresh)")
        results["leverage"] = False
    
    # Step 4: Calculate Dilution metrics (depends on Market Cap)
    if results["marketcap"]:
        results["dilution"] = calculate_dilution_metrics()
    else:
        print_section("STEP 4: SKIPPED - Dilution Metrics")
        print("  (requires Market Cap data to be fresh)")
        results["dilution"] = False
    
    # Print summary
    all_success = print_summary(results)
    
    # Exit with appropriate code
    sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()
