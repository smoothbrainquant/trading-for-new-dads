#!/usr/bin/env python3
"""
Data Validation Script
Analyzes all data files to identify:
- API source (ccxt, coinalyze, cmc, scrape)
- Data type (price, funding, market cap)
- Number of symbols
- Start date
- End date
"""

import pandas as pd
import os
from datetime import datetime
from pathlib import Path
import warnings

warnings.filterwarnings("ignore")


def identify_data_source(filename):
    """Identify API source based on filename patterns"""
    filename_lower = filename.lower()

    if "coinbase" in filename_lower or "ccxt" in filename_lower or "binance" in filename_lower:
        return "ccxt"
    elif "coinalyze" in filename_lower or "funding" in filename_lower:
        return "coinalyze"
    elif "coinmarketcap" in filename_lower or "cmc" in filename_lower:
        return "cmc"
    elif "hyperliquid" in filename_lower:
        return "ccxt"  # Also uses ccxt
    else:
        return "unknown"


def identify_data_type(filename, df):
    """Identify data type based on filename and column structure"""
    filename_lower = filename.lower()
    columns = df.columns.tolist()

    # Check for funding rate data
    if "funding" in filename_lower or "funding_rate" in columns:
        return "funding"

    # Check for market cap data
    if "market_cap" in columns or "market cap" in columns or "coinmarketcap" in filename_lower:
        return "market_cap"

    # Check for price data (OHLC)
    if all(col in columns for col in ["open", "high", "low", "close"]):
        return "price"

    # Check for volatility
    if "volatility" in filename_lower or "vola" in filename_lower:
        return "volatility"

    # Check for other types
    if "breakout" in filename_lower or "signal" in filename_lower:
        return "signals"

    return "other"


def extract_symbols(df, filename):
    """Extract unique symbols from dataframe"""
    filename_lower = filename.lower()

    # Check common symbol column names
    symbol_cols = ["symbol", "base", "coin_symbol", "Symbol"]

    for col in symbol_cols:
        if col in df.columns:
            symbols = df[col].dropna().unique().tolist()
            return symbols

    # If no symbol column found, try to extract from context
    if "Name" in df.columns:  # CoinMarketCap format
        return df["Name"].dropna().unique().tolist()

    return []


def extract_date_range(df):
    """Extract start and end dates from dataframe"""
    # Check common date column names
    date_cols = ["date", "Date", "timestamp", "snapshot_date"]

    for col in date_cols:
        if col in df.columns:
            try:
                # Convert to datetime
                dates = pd.to_datetime(df[col], errors="coerce")
                dates = dates.dropna()

                if len(dates) > 0:
                    start_date = dates.min()
                    end_date = dates.max()
                    return start_date, end_date
            except:
                continue

    return None, None


def analyze_data_file(filepath):
    """Analyze a single data file and return metadata"""
    try:
        # Read CSV file
        df = pd.read_csv(filepath)

        if df.empty:
            return None

        filename = os.path.basename(filepath)

        # Identify data source and type
        api_source = identify_data_source(filename)
        data_type = identify_data_type(filename, df)

        # Extract symbols
        symbols = extract_symbols(df, filename)
        n_symbols = len(symbols)

        # Extract date range
        start_date, end_date = extract_date_range(df)

        # Calculate file size
        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)

        # Count rows
        n_rows = len(df)

        return {
            "filename": filename,
            "api": api_source,
            "type": data_type,
            "n_symbols": n_symbols,
            "symbols": symbols[:10] if len(symbols) <= 10 else symbols[:10] + ["..."],
            "start_date": start_date.strftime("%Y-%m-%d") if start_date else "N/A",
            "end_date": end_date.strftime("%Y-%m-%d") if end_date else "N/A",
            "n_rows": n_rows,
            "file_size_mb": round(file_size_mb, 2),
            "columns": df.columns.tolist(),
        }

    except Exception as e:
        print(f"Error analyzing {os.path.basename(filepath)}: {str(e)}")
        return None


def main():
    """Main function to validate all data sources"""
    print("=" * 80)
    print("DATA VALIDATION REPORT")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Path to data directory
    data_dir = Path("/workspace/data/raw")

    # Get all CSV files
    csv_files = sorted(data_dir.glob("*.csv"))

    print(f"Found {len(csv_files)} CSV files in data/raw/")
    print()

    # Analyze each file
    results = []
    for filepath in csv_files:
        result = analyze_data_file(filepath)
        if result:
            results.append(result)

    # Create summary dataframe
    df_summary = pd.DataFrame(results)

    if df_summary.empty:
        print("No data files could be analyzed.")
        return

    # Print summary by API source
    print("=" * 80)
    print("SUMMARY BY API SOURCE")
    print("=" * 80)

    for api in df_summary["api"].unique():
        api_data = df_summary[df_summary["api"] == api]
        print(f"\n📊 API: {api.upper()}")
        print(f"   Files: {len(api_data)}")
        print(f"   Total Size: {api_data['file_size_mb'].sum():.2f} MB")
        print(f"   Total Rows: {api_data['n_rows'].sum():,}")

        # Group by data type
        for dtype in api_data["type"].unique():
            type_data = api_data[api_data["type"] == dtype]
            print(f"   - {dtype.upper()}: {len(type_data)} files")

    print("\n" + "=" * 80)
    print("DETAILED FILE INFORMATION")
    print("=" * 80)

    # Group by API and data type
    for api in sorted(df_summary["api"].unique()):
        api_data = df_summary[df_summary["api"] == api]

        for dtype in sorted(api_data["type"].unique()):
            type_data = api_data[api_data["type"] == dtype]

            print(f"\n{'='*80}")
            print(f"API: {api.upper()} | Type: {dtype.upper()}")
            print(f"{'='*80}")

            for _, row in type_data.iterrows():
                print(f"\n📁 {row['filename']}")
                print(f"   • API: {row['api']}")
                print(f"   • Type: {row['type']}")
                print(f"   • N Symbols: {row['n_symbols']}")
                print(f"   • Start Date: {row['start_date']}")
                print(f"   • End Date: {row['end_date']}")
                print(f"   • Rows: {row['n_rows']:,}")
                print(f"   • Size: {row['file_size_mb']} MB")

                if row["n_symbols"] > 0 and row["n_symbols"] <= 10:
                    symbols_str = ", ".join([str(s) for s in row["symbols"]])
                    print(f"   • Symbols: {symbols_str}")
                elif row["n_symbols"] > 10:
                    symbols_str = ", ".join([str(s) for s in row["symbols"][:5]])
                    print(f"   • Symbols (first 5): {symbols_str}, ...")

    # Save summary to CSV
    output_file = f"/workspace/data/raw/data_validation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    # Prepare export dataframe (without lists)
    export_df = df_summary.copy()
    export_df["symbols"] = export_df["symbols"].apply(
        lambda x: ", ".join([str(s) for s in x]) if isinstance(x, list) else str(x)
    )
    export_df["columns"] = export_df["columns"].apply(
        lambda x: ", ".join(x) if isinstance(x, list) else str(x)
    )

    export_df.to_csv(output_file, index=False)

    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)

    print(f"\n📊 Total Files Analyzed: {len(results)}")
    print(f"📊 Total Size: {df_summary['file_size_mb'].sum():.2f} MB")
    print(f"📊 Total Rows: {df_summary['n_rows'].sum():,}")

    print("\n📊 By API Source:")
    api_summary = (
        df_summary.groupby("api")
        .agg({"filename": "count", "file_size_mb": "sum", "n_rows": "sum", "n_symbols": "sum"})
        .round(2)
    )
    api_summary.columns = ["Files", "Size (MB)", "Total Rows", "Total Symbols"]
    print(api_summary.to_string())

    print("\n📊 By Data Type:")
    type_summary = (
        df_summary.groupby("type")
        .agg({"filename": "count", "file_size_mb": "sum", "n_rows": "sum"})
        .round(2)
    )
    type_summary.columns = ["Files", "Size (MB)", "Total Rows"]
    print(type_summary.to_string())

    print("\n" + "=" * 80)
    print(f"✅ Validation complete! Summary saved to:")
    print(f"   {output_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
