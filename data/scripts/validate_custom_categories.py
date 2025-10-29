#!/usr/bin/env python3
"""
Validate Custom Category Mappings

This script validates the custom_categories.csv file against available price data:
1. Check for symbols in categories that don't exist in price data
2. Check for symbols in price data not assigned to any category
3. Analyze category sizes and overlap
4. Generate summary statistics
"""

import pandas as pd
import numpy as np
from collections import defaultdict
import os


def load_data():
    """Load category mappings and price data."""
    print("Loading data...")

    # Load custom categories
    categories_file = "data/raw/custom_categories.csv"
    if not os.path.exists(categories_file):
        print(f"ERROR: Category file not found: {categories_file}")
        return None, None

    categories_df = pd.read_csv(categories_file)
    print(f"  Loaded {len(categories_df)} category assignments")

    # Load price data
    price_file = "data/raw/combined_coinbase_coinmarketcap_daily.csv"
    if not os.path.exists(price_file):
        print(f"ERROR: Price file not found: {price_file}")
        return categories_df, None

    price_df = pd.read_csv(price_file)
    available_symbols = sorted(price_df["base"].unique())
    print(f"  Loaded price data for {len(available_symbols)} symbols")

    return categories_df, available_symbols


def validate_symbols(categories_df, available_symbols):
    """Validate that category symbols exist in price data."""
    print("\n" + "=" * 80)
    print("SYMBOL VALIDATION")
    print("=" * 80)

    category_symbols = set(categories_df["symbol"].unique())
    available_set = set(available_symbols)

    # Find symbols in categories but not in price data
    missing_symbols = sorted(category_symbols - available_set)

    # Find symbols in price data but not in categories
    uncategorized_symbols = sorted(available_set - category_symbols)

    print(f"\nTotal symbols in categories: {len(category_symbols)}")
    print(f"Total symbols with price data: {len(available_set)}")
    print(f"Overlap: {len(category_symbols & available_set)} symbols")

    if len(missing_symbols) > 0:
        print(f"\n⚠️  WARNING: {len(missing_symbols)} symbols in categories have NO price data:")
        print(f"  {', '.join(missing_symbols)}")
    else:
        print("\n✓ All symbols in categories have price data")

    if len(uncategorized_symbols) > 0:
        print(
            f"\n📋 INFO: {len(uncategorized_symbols)} symbols with price data NOT in any category:"
        )
        print(f"  {', '.join(uncategorized_symbols[:30])}")
        if len(uncategorized_symbols) > 30:
            print(f"  ... and {len(uncategorized_symbols) - 30} more")
    else:
        print("\n✓ All symbols with price data are categorized")

    return missing_symbols, uncategorized_symbols


def analyze_categories(categories_df):
    """Analyze category statistics."""
    print("\n" + "=" * 80)
    print("CATEGORY ANALYSIS")
    print("=" * 80)

    # Count symbols per category
    category_counts = (
        categories_df.groupby("category")
        .agg(
            {
                "symbol": "count",
            }
        )
        .rename(columns={"symbol": "num_symbols"})
    )

    # Count primary vs secondary assignments
    priority_counts = categories_df.groupby(["category", "priority"]).size().unstack(fill_value=0)
    category_counts = category_counts.join(priority_counts)

    category_counts = category_counts.sort_values("num_symbols", ascending=False)

    print(f"\nTotal unique categories: {len(category_counts)}")
    print(f"Total category assignments: {len(categories_df)}")
    print(
        f"Avg assignments per symbol: {len(categories_df) / categories_df['symbol'].nunique():.2f}"
    )

    print("\nCategory sizes (top 20):")
    print(category_counts.head(20).to_string())

    print("\nCategory sizes (bottom 10):")
    print(category_counts.tail(10).to_string())

    return category_counts


def analyze_multi_membership(categories_df):
    """Analyze symbols that belong to multiple categories."""
    print("\n" + "=" * 80)
    print("MULTI-CATEGORY MEMBERSHIP")
    print("=" * 80)

    symbol_counts = categories_df.groupby("symbol").size().sort_values(ascending=False)

    print(f"\nSymbols in multiple categories: {(symbol_counts > 1).sum()}")
    print(f"Symbols in only one category: {(symbol_counts == 1).sum()}")
    print(f"Max categories per symbol: {symbol_counts.max()}")

    print("\nTop symbols by number of categories:")
    for symbol, count in symbol_counts.head(15).items():
        cats = categories_df[categories_df["symbol"] == symbol]["category"].tolist()
        print(f"  {symbol}: {count} categories - {', '.join(cats)}")

    return symbol_counts


def analyze_category_overlap(categories_df):
    """Analyze overlap between categories."""
    print("\n" + "=" * 80)
    print("CATEGORY OVERLAP ANALYSIS")
    print("=" * 80)

    # Create category pairs
    symbols_by_category = defaultdict(set)
    for _, row in categories_df.iterrows():
        symbols_by_category[row["category"]].add(row["symbol"])

    # Find overlapping category pairs
    overlaps = []
    categories = sorted(symbols_by_category.keys())

    for i, cat1 in enumerate(categories):
        for cat2 in categories[i + 1 :]:
            overlap = symbols_by_category[cat1] & symbols_by_category[cat2]
            if len(overlap) > 0:
                overlaps.append(
                    {
                        "category_1": cat1,
                        "category_2": cat2,
                        "overlap_count": len(overlap),
                        "cat1_size": len(symbols_by_category[cat1]),
                        "cat2_size": len(symbols_by_category[cat2]),
                        "overlap_pct": 100
                        * len(overlap)
                        / min(len(symbols_by_category[cat1]), len(symbols_by_category[cat2])),
                    }
                )

    overlap_df = pd.DataFrame(overlaps).sort_values("overlap_count", ascending=False)

    print(f"\nTotal category pairs with overlap: {len(overlap_df)}")
    print("\nTop 20 category pairs by overlap:")
    print(
        overlap_df.head(20)[["category_1", "category_2", "overlap_count", "overlap_pct"]].to_string(
            index=False
        )
    )

    return overlap_df


def check_data_availability(categories_df, available_symbols):
    """Check data availability for categorized symbols."""
    print("\n" + "=" * 80)
    print("DATA AVAILABILITY CHECK")
    print("=" * 80)

    # Load price data to check date ranges
    price_df = pd.read_csv("data/raw/combined_coinbase_coinmarketcap_daily.csv")
    price_df["date"] = pd.to_datetime(price_df["date"])

    # Get data summary per symbol
    data_summary = price_df.groupby("base").agg(
        {"date": ["min", "max", "count"], "volume": "mean", "market_cap": "mean"}
    )
    data_summary.columns = ["start_date", "end_date", "num_days", "avg_volume", "avg_market_cap"]

    # Filter to categorized symbols
    categorized_symbols = categories_df["symbol"].unique()
    valid_symbols = [s for s in categorized_symbols if s in available_symbols]

    data_summary_cat = data_summary.loc[valid_symbols]

    print(f"\nData availability for {len(data_summary_cat)} categorized symbols:")
    print(f"  Earliest start date: {data_summary_cat['start_date'].min()}")
    print(f"  Latest end date: {data_summary_cat['end_date'].max()}")
    print(f"  Avg days of data: {data_summary_cat['num_days'].mean():.0f}")
    print(f"  Min days of data: {data_summary_cat['num_days'].min():.0f}")
    print(f"  Max days of data: {data_summary_cat['num_days'].max():.0f}")

    # Check for symbols with limited data
    limited_data = data_summary_cat[data_summary_cat["num_days"] < 90]
    if len(limited_data) > 0:
        print(f"\n⚠️  WARNING: {len(limited_data)} symbols have < 90 days of data:")
        for symbol in limited_data.index[:10]:
            print(f"  {symbol}: {limited_data.loc[symbol, 'num_days']:.0f} days")

    return data_summary_cat


def generate_category_file_for_backtest(
    categories_df, available_symbols, output_file="data/raw/category_mappings_validated.csv"
):
    """Generate a clean category file for backtesting (only valid symbols)."""
    print("\n" + "=" * 80)
    print("GENERATING VALIDATED CATEGORY FILE")
    print("=" * 80)

    # Filter to only symbols with price data
    valid_df = categories_df[categories_df["symbol"].isin(available_symbols)].copy()

    print(
        f"\nFiltered {len(categories_df)} assignments down to {len(valid_df)} with valid price data"
    )
    print(f"Categories: {valid_df['category'].nunique()}")
    print(f"Symbols: {valid_df['symbol'].nunique()}")

    valid_df.to_csv(output_file, index=False)
    print(f"\n✓ Saved validated categories to: {output_file}")

    return valid_df


def main():
    """Main validation function."""
    print("=" * 80)
    print("CUSTOM CATEGORY VALIDATION")
    print("=" * 80)

    # Load data
    categories_df, available_symbols = load_data()

    if categories_df is None or available_symbols is None:
        print("ERROR: Could not load required data")
        return

    # Run validations
    missing_symbols, uncategorized = validate_symbols(categories_df, available_symbols)

    category_counts = analyze_categories(categories_df)

    symbol_counts = analyze_multi_membership(categories_df)

    overlap_df = analyze_category_overlap(categories_df)

    data_summary = check_data_availability(categories_df, available_symbols)

    # Generate validated file
    valid_df = generate_category_file_for_backtest(categories_df, available_symbols)

    # Summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)
    print(f"✓ Total categories: {categories_df['category'].nunique()}")
    print(f"✓ Total symbols in categories: {categories_df['symbol'].nunique()}")
    print(
        f"✓ Symbols with valid price data: {len([s for s in categories_df['symbol'].unique() if s in available_symbols])}"
    )
    print(f"✓ Average symbols per category: {len(valid_df) / valid_df['category'].nunique():.1f}")
    print(f"✓ Average categories per symbol: {len(valid_df) / valid_df['symbol'].nunique():.2f}")

    if len(missing_symbols) > 0:
        print(f"\n⚠️  {len(missing_symbols)} symbols in categories have no price data")

    if len(uncategorized) > 0:
        print(f"\n📋 {len(uncategorized)} symbols with price data are not categorized")

    print("\n" + "=" * 80)
    print("VALIDATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
