"""
Check Data Completeness for Backtests

This script checks the completeness and quality of all data files used by
the run_all_backtests.py script.

Data files checked:
1. Price data: data/raw/combined_coinbase_coinmarketcap_daily.csv
2. Market cap data: data/raw/coinmarketcap_monthly_all_snapshots.csv
3. Funding rates data: data/raw/historical_funding_rates_top100_ALL_HISTORY_*.csv
4. Leverage data: signals/historical_leverage_weekly_*.csv
5. Dilution data: crypto_dilution_historical_2021_2025.csv
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta
import glob

def check_file_exists(filepath):
    """Check if file exists and return file info."""
    if os.path.exists(filepath):
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        return True, size_mb
    return False, 0

def check_date_coverage(df, date_column='date', name='Dataset'):
    """Check date range and gaps in the data."""
    if date_column not in df.columns:
        return None
    
    df = df.copy()
    df[date_column] = pd.to_datetime(df[date_column])
    
    min_date = df[date_column].min()
    max_date = df[date_column].max()
    num_dates = df[date_column].nunique()
    expected_days = (max_date - min_date).days + 1
    
    # Check for date gaps
    all_dates = pd.date_range(min_date, max_date, freq='D')
    actual_dates = set(df[date_column].dt.date)
    missing_dates = [d for d in all_dates if d.date() not in actual_dates]
    
    return {
        'min_date': min_date,
        'max_date': max_date,
        'num_dates': num_dates,
        'expected_days': expected_days,
        'coverage_pct': (num_dates / expected_days * 100) if expected_days > 0 else 0,
        'missing_dates': len(missing_dates),
        'missing_dates_list': missing_dates[:10]  # First 10 missing dates
    }

def check_price_data(filepath):
    """Check price data completeness."""
    print("\n" + "=" * 80)
    print("1. PRICE DATA")
    print("=" * 80)
    print(f"File: {filepath}")
    
    exists, size_mb = check_file_exists(filepath)
    if not exists:
        print("❌ FILE NOT FOUND")
        return None
    
    print(f"✅ File exists ({size_mb:.2f} MB)")
    
    # Load data
    df = pd.read_csv(filepath)
    print(f"   Total rows: {len(df):,}")
    print(f"   Columns: {', '.join(df.columns.tolist())}")
    
    # Check for date column
    if 'date' not in df.columns:
        print("❌ Missing 'date' column")
        return None
    
    df['date'] = pd.to_datetime(df['date'])
    
    # Check symbols
    if 'symbol' in df.columns:
        num_symbols = df['symbol'].nunique()
        print(f"   Unique symbols: {num_symbols}")
        
        # Check for duplicates
        duplicates = df.groupby(['date', 'symbol']).size()
        duplicates = duplicates[duplicates > 1]
        if len(duplicates) > 0:
            print(f"⚠️  Found {len(duplicates)} date-symbol duplicates")
        else:
            print("✅ No duplicate date-symbol combinations")
    
    # Check date coverage
    coverage = check_date_coverage(df, 'date', 'Price Data')
    if coverage:
        print(f"\n   Date Range:")
        print(f"     Start: {coverage['min_date'].date()}")
        print(f"     End: {coverage['max_date'].date()}")
        print(f"     Days covered: {coverage['num_dates']:,} / {coverage['expected_days']:,} ({coverage['coverage_pct']:.1f}%)")
        if coverage['missing_dates'] > 0:
            print(f"⚠️  Missing {coverage['missing_dates']} dates")
            if coverage['missing_dates_list']:
                print(f"     First missing dates: {', '.join([str(d.date()) for d in coverage['missing_dates_list'][:5]])}")
    
    # Check for required columns
    required_cols = ['date', 'symbol', 'close']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        print(f"❌ Missing required columns: {', '.join(missing_cols)}")
    else:
        print("✅ All required columns present (date, symbol, close)")
    
    # Check for NaN values in critical columns
    critical_cols = ['close', 'volume']
    for col in critical_cols:
        if col in df.columns:
            nan_count = df[col].isna().sum()
            nan_pct = (nan_count / len(df) * 100)
            if nan_count > 0:
                print(f"⚠️  {col}: {nan_count:,} NaN values ({nan_pct:.2f}%)")
            else:
                print(f"✅ {col}: No NaN values")
    
    return df

def check_marketcap_data(filepath):
    """Check market cap data completeness."""
    print("\n" + "=" * 80)
    print("2. MARKET CAP DATA")
    print("=" * 80)
    print(f"File: {filepath}")
    
    exists, size_mb = check_file_exists(filepath)
    if not exists:
        print("❌ FILE NOT FOUND")
        return None
    
    print(f"✅ File exists ({size_mb:.2f} MB)")
    
    # Load data
    df = pd.read_csv(filepath)
    print(f"   Total rows: {len(df):,}")
    print(f"   Columns: {', '.join(df.columns.tolist())}")
    
    # Handle date column (could be 'date' or 'snapshot_date')
    date_col = None
    if 'snapshot_date' in df.columns:
        df['date'] = pd.to_datetime(df['snapshot_date'], format='%Y%m%d')
        date_col = 'date'
    elif 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        date_col = 'date'
    
    if date_col is None:
        print("❌ Missing date column (expected 'date' or 'snapshot_date')")
        return None
    
    # Check symbols
    symbol_col = 'symbol' if 'symbol' in df.columns else 'Symbol'
    if symbol_col in df.columns:
        num_symbols = df[symbol_col].nunique()
        print(f"   Unique symbols: {num_symbols}")
    
    # Check date coverage
    coverage = check_date_coverage(df, 'date', 'Market Cap Data')
    if coverage:
        print(f"\n   Date Range:")
        print(f"     Start: {coverage['min_date'].date()}")
        print(f"     End: {coverage['max_date'].date()}")
        print(f"     Snapshots: {coverage['num_dates']:,}")
        
        # Calculate average days between snapshots
        dates_sorted = df['date'].sort_values().unique()
        if len(dates_sorted) > 1:
            date_diffs = np.diff([pd.Timestamp(d) for d in dates_sorted])
            avg_days = np.mean([d.days for d in date_diffs])
            print(f"     Average days between snapshots: {avg_days:.1f}")
    
    # Check for required columns
    marketcap_col = 'market_cap' if 'market_cap' in df.columns else 'Market Cap'
    if marketcap_col not in df.columns:
        print("❌ Missing market cap column")
    else:
        nan_count = df[marketcap_col].isna().sum()
        nan_pct = (nan_count / len(df) * 100)
        if nan_count > 0:
            print(f"⚠️  {marketcap_col}: {nan_count:,} NaN values ({nan_pct:.2f}%)")
        else:
            print(f"✅ {marketcap_col}: No NaN values")
    
    return df

def check_funding_rates_data(filepath_pattern):
    """Check funding rates data completeness."""
    print("\n" + "=" * 80)
    print("3. FUNDING RATES DATA")
    print("=" * 80)
    
    # Find matching files (exclude summary files)
    matching_files = glob.glob(filepath_pattern)
    # Filter out summary files
    matching_files = [f for f in matching_files if 'summary' not in f.lower()]
    
    if not matching_files:
        # Try exact path
        if os.path.exists(filepath_pattern):
            matching_files = [filepath_pattern]
        else:
            print(f"❌ FILE NOT FOUND: {filepath_pattern}")
            return None
    
    # Use most recent file (sort by modification time)
    matching_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    filepath = matching_files[0]
    print(f"File: {filepath}")
    
    exists, size_mb = check_file_exists(filepath)
    if not exists:
        print("❌ FILE NOT FOUND")
        return None
    
    print(f"✅ File exists ({size_mb:.2f} MB)")
    
    # Load data
    df = pd.read_csv(filepath)
    print(f"   Total rows: {len(df):,}")
    print(f"   Columns: {', '.join(df.columns.tolist())}")
    
    # Handle date column
    date_col = None
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        date_col = 'date'
    elif 'timestamp' in df.columns:
        df['date'] = pd.to_datetime(df['timestamp'])
        date_col = 'date'
    
    if date_col is None:
        print("❌ Missing date column (expected 'date' or 'timestamp')")
        return None
    
    # Check symbols
    symbol_col = 'coin_symbol' if 'coin_symbol' in df.columns else 'symbol'
    if symbol_col in df.columns:
        num_symbols = df[symbol_col].nunique()
        print(f"   Unique symbols: {num_symbols}")
    
    # Check date coverage
    coverage = check_date_coverage(df, 'date', 'Funding Rates')
    if coverage:
        print(f"\n   Date Range:")
        print(f"     Start: {coverage['min_date'].date()}")
        print(f"     End: {coverage['max_date'].date()}")
        print(f"     Days covered: {coverage['num_dates']:,} / {coverage['expected_days']:,} ({coverage['coverage_pct']:.1f}%)")
        if coverage['missing_dates'] > 0:
            print(f"⚠️  Missing {coverage['missing_dates']} dates")
    
    # Check for funding rate column
    funding_col = 'funding_rate_pct' if 'funding_rate_pct' in df.columns else 'funding_rate'
    if funding_col not in df.columns:
        print("❌ Missing funding rate column")
    else:
        nan_count = df[funding_col].isna().sum()
        nan_pct = (nan_count / len(df) * 100)
        if nan_count > 0:
            print(f"⚠️  {funding_col}: {nan_count:,} NaN values ({nan_pct:.2f}%)")
        else:
            print(f"✅ {funding_col}: No NaN values")
    
    return df

def check_leverage_data(filepath_pattern):
    """Check leverage data completeness."""
    print("\n" + "=" * 80)
    print("4. LEVERAGE DATA")
    print("=" * 80)
    
    # Find matching files
    matching_files = glob.glob(filepath_pattern)
    if not matching_files:
        print(f"❌ FILE NOT FOUND: {filepath_pattern}")
        return None
    
    # Use most recent file
    filepath = matching_files[0]
    print(f"File: {filepath}")
    
    exists, size_mb = check_file_exists(filepath)
    if not exists:
        print("❌ FILE NOT FOUND")
        return None
    
    print(f"✅ File exists ({size_mb:.2f} MB)")
    
    # Load data
    df = pd.read_csv(filepath)
    print(f"   Total rows: {len(df):,}")
    print(f"   Columns: {', '.join(df.columns.tolist())}")
    
    # Check date column
    if 'date' not in df.columns:
        print("❌ Missing 'date' column")
        return None
    
    df['date'] = pd.to_datetime(df['date'])
    
    # Check symbols
    if 'coin_symbol' in df.columns:
        num_symbols = df['coin_symbol'].nunique()
        print(f"   Unique symbols: {num_symbols}")
    
    # Check date coverage
    coverage = check_date_coverage(df, 'date', 'Leverage Data')
    if coverage:
        print(f"\n   Date Range:")
        print(f"     Start: {coverage['min_date'].date()}")
        print(f"     End: {coverage['max_date'].date()}")
        print(f"     Weeks covered: {coverage['num_dates']:,}")
    
    # Check for required columns
    required_cols = ['oi_to_mcap_ratio', 'market_cap_usd', 'total_open_interest_usd']
    for col in required_cols:
        if col in df.columns:
            nan_count = df[col].isna().sum()
            nan_pct = (nan_count / len(df) * 100)
            if nan_count > 0:
                print(f"⚠️  {col}: {nan_count:,} NaN values ({nan_pct:.2f}%)")
            else:
                print(f"✅ {col}: No NaN values")
        else:
            print(f"❌ Missing column: {col}")
    
    return df

def check_dilution_data(filepath):
    """Check dilution data completeness."""
    print("\n" + "=" * 80)
    print("5. DILUTION DATA")
    print("=" * 80)
    print(f"File: {filepath}")
    
    exists, size_mb = check_file_exists(filepath)
    if not exists:
        print("❌ FILE NOT FOUND")
        return None
    
    print(f"✅ File exists ({size_mb:.2f} MB)")
    
    # Load data
    df = pd.read_csv(filepath)
    print(f"   Total rows: {len(df):,}")
    print(f"   Columns: {', '.join(df.columns.tolist())}")
    
    # Check date column
    if 'date' not in df.columns:
        print("❌ Missing 'date' column")
        return None
    
    df['date'] = pd.to_datetime(df['date'])
    
    # Check symbols
    symbol_col = None
    for col in ['symbol', 'coin', 'coin_id']:
        if col in df.columns:
            symbol_col = col
            break
    
    if symbol_col:
        num_symbols = df[symbol_col].nunique()
        print(f"   Unique symbols ({symbol_col}): {num_symbols}")
    
    # Check date coverage
    coverage = check_date_coverage(df, 'date', 'Dilution Data')
    if coverage:
        print(f"\n   Date Range:")
        print(f"     Start: {coverage['min_date'].date()}")
        print(f"     End: {coverage['max_date'].date()}")
        print(f"     Days covered: {coverage['num_dates']:,} / {coverage['expected_days']:,} ({coverage['coverage_pct']:.1f}%)")
        if coverage['missing_dates'] > 0:
            print(f"⚠️  Missing {coverage['missing_dates']} dates")
    
    # Check for dilution columns
    dilution_cols = [col for col in df.columns if 'dilution' in col.lower() or 'supply' in col.lower()]
    if dilution_cols:
        print(f"   Dilution-related columns: {', '.join(dilution_cols)}")
        for col in dilution_cols[:3]:  # Check first 3
            nan_count = df[col].isna().sum()
            nan_pct = (nan_count / len(df) * 100)
            if nan_count > 0:
                print(f"⚠️  {col}: {nan_count:,} NaN values ({nan_pct:.2f}%)")
            else:
                print(f"✅ {col}: No NaN values")
    else:
        print("❌ No dilution-related columns found")
    
    return df

def main():
    """Main execution function."""
    print("=" * 80)
    print("BACKTEST DATA COMPLETENESS CHECK")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Track overall status
    all_checks = []
    
    # 1. Price data
    price_df = check_price_data("data/raw/combined_coinbase_coinmarketcap_daily.csv")
    all_checks.append(("Price Data", price_df is not None))
    
    # 2. Market cap data
    marketcap_df = check_marketcap_data("data/raw/coinmarketcap_monthly_all_snapshots.csv")
    all_checks.append(("Market Cap Data", marketcap_df is not None))
    
    # 3. Funding rates data
    funding_df = check_funding_rates_data("data/raw/historical_funding_rates_top100_ALL_HISTORY_*.csv")
    all_checks.append(("Funding Rates Data", funding_df is not None))
    
    # 4. Leverage data
    leverage_df = check_leverage_data("signals/historical_leverage_weekly_*.csv")
    all_checks.append(("Leverage Data", leverage_df is not None))
    
    # 5. Dilution data
    dilution_df = check_dilution_data("crypto_dilution_historical_2021_2025.csv")
    all_checks.append(("Dilution Data", dilution_df is not None))
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    passed_checks = sum(1 for _, status in all_checks if status)
    total_checks = len(all_checks)
    
    for name, status in all_checks:
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {name}")
    
    print("\n" + "-" * 80)
    print(f"Total: {passed_checks}/{total_checks} datasets complete")
    
    if passed_checks == total_checks:
        print("\n✅ ALL DATA FILES COMPLETE - Ready for backtesting!")
    else:
        print(f"\n⚠️  {total_checks - passed_checks} dataset(s) missing or incomplete")
        print("   Some backtests may fail or be skipped")
    
    print("=" * 80)

if __name__ == "__main__":
    main()
