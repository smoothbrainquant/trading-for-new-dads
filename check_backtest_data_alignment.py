"""
Check Data Alignment for Backtests

This script checks how well the different data sources align with each other,
which is critical for backtesting.

Checks:
1. Date range alignment across datasets
2. Symbol overlap between datasets
3. Data availability by time period
4. Potential backtest limitations
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
import glob

def load_data():
    """Load all data files used by backtests."""
    data = {}
    
    # 1. Price data
    price_file = "data/raw/combined_coinbase_coinmarketcap_daily.csv"
    if os.path.exists(price_file):
        df = pd.read_csv(price_file)
        df['date'] = pd.to_datetime(df['date'])
        data['price'] = df
        print(f"✅ Loaded price data: {len(df):,} rows, {df['symbol'].nunique()} symbols")
    else:
        print(f"❌ Price data not found")
        data['price'] = None
    
    # 2. Market cap data
    mcap_file = "data/raw/coinmarketcap_monthly_all_snapshots.csv"
    if os.path.exists(mcap_file):
        df = pd.read_csv(mcap_file)
        if 'snapshot_date' in df.columns:
            df['date'] = pd.to_datetime(df['snapshot_date'], format='%Y%m%d')
        else:
            df['date'] = pd.to_datetime(df['date'])
        data['marketcap'] = df
        print(f"✅ Loaded market cap data: {len(df):,} rows")
    else:
        print(f"❌ Market cap data not found")
        data['marketcap'] = None
    
    # 3. Funding rates data
    funding_files = glob.glob("data/raw/historical_funding_rates_top100_ALL_HISTORY_*.csv")
    funding_files = [f for f in funding_files if 'summary' not in f.lower()]
    if funding_files:
        funding_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        df = pd.read_csv(funding_files[0])
        df['date'] = pd.to_datetime(df['date'])
        data['funding'] = df
        print(f"✅ Loaded funding rates: {len(df):,} rows, {df['coin_symbol'].nunique()} symbols")
    else:
        print(f"❌ Funding rates data not found")
        data['funding'] = None
    
    # 4. Leverage data
    leverage_files = glob.glob("signals/historical_leverage_weekly_*.csv")
    if leverage_files:
        leverage_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        df = pd.read_csv(leverage_files[0])
        df['date'] = pd.to_datetime(df['date'])
        data['leverage'] = df
        print(f"✅ Loaded leverage data: {len(df):,} rows, {df['coin_symbol'].nunique()} symbols")
    else:
        print(f"❌ Leverage data not found")
        data['leverage'] = None
    
    # 5. Dilution data
    dilution_file = "crypto_dilution_historical_2021_2025.csv"
    if os.path.exists(dilution_file):
        df = pd.read_csv(dilution_file)
        df['date'] = pd.to_datetime(df['date'])
        data['dilution'] = df
        print(f"✅ Loaded dilution data: {len(df):,} rows")
    else:
        print(f"❌ Dilution data not found")
        data['dilution'] = None
    
    return data

def analyze_date_ranges(data):
    """Analyze date range alignment across datasets."""
    print("\n" + "=" * 80)
    print("DATE RANGE ALIGNMENT")
    print("=" * 80)
    
    date_ranges = {}
    for name, df in data.items():
        if df is not None and 'date' in df.columns:
            date_ranges[name] = {
                'min': df['date'].min(),
                'max': df['date'].max(),
                'days': df['date'].nunique()
            }
    
    if not date_ranges:
        print("No data with date columns found")
        return
    
    # Find common date range
    all_min_dates = [info['min'] for info in date_ranges.values()]
    all_max_dates = [info['max'] for info in date_ranges.values()]
    
    latest_start = max(all_min_dates)
    earliest_end = min(all_max_dates)
    
    print(f"\nIndividual Date Ranges:")
    print(f"{'Dataset':<15} {'Start Date':<12} {'End Date':<12} {'Days':<8} {'Coverage'}")
    print("-" * 80)
    
    for name, info in sorted(date_ranges.items()):
        coverage = "✅" if info['min'] <= latest_start and info['max'] >= earliest_end else "⚠️"
        print(f"{name.capitalize():<15} {info['min'].date()} {info['max'].date()} {info['days']:<8,} {coverage}")
    
    print(f"\n{'Common Date Range (overlap of all datasets):':<15}")
    print(f"  Start: {latest_start.date()}")
    print(f"  End: {earliest_end.date()}")
    print(f"  Days: {(earliest_end - latest_start).days + 1:,}")
    
    # Calculate backtest-ready period
    if earliest_end > latest_start:
        print(f"\n✅ Backtest-ready period: {latest_start.date()} to {earliest_end.date()}")
        print(f"   ({(earliest_end - latest_start).days + 1:,} days / {(earliest_end - latest_start).days / 365.25:.1f} years)")
    else:
        print(f"\n❌ No overlapping date range found across all datasets")
    
    return date_ranges

def analyze_symbol_overlap(data):
    """Analyze symbol overlap between datasets."""
    print("\n" + "=" * 80)
    print("SYMBOL OVERLAP ANALYSIS")
    print("=" * 80)
    
    # Extract symbols from each dataset
    symbols = {}
    
    if data.get('price') is not None:
        # Extract base symbol (before /)
        price_symbols = set(data['price']['symbol'].str.split('/').str[0].str.upper())
        symbols['price'] = price_symbols
        print(f"\nPrice data: {len(price_symbols)} unique base symbols")
    
    if data.get('marketcap') is not None:
        symbol_col = 'Symbol' if 'Symbol' in data['marketcap'].columns else 'symbol'
        mcap_symbols = set(data['marketcap'][symbol_col].str.upper())
        symbols['marketcap'] = mcap_symbols
        print(f"Market cap data: {len(mcap_symbols)} unique symbols")
    
    if data.get('funding') is not None:
        funding_symbols = set(data['funding']['coin_symbol'].str.upper())
        symbols['funding'] = funding_symbols
        print(f"Funding rates: {len(funding_symbols)} unique symbols")
    
    if data.get('leverage') is not None:
        leverage_symbols = set(data['leverage']['coin_symbol'].str.upper())
        symbols['leverage'] = leverage_symbols
        print(f"Leverage data: {len(leverage_symbols)} unique symbols")
    
    if data.get('dilution') is not None:
        dilution_symbols = set(data['dilution']['Symbol'].str.upper())
        symbols['dilution'] = dilution_symbols
        print(f"Dilution data: {len(dilution_symbols)} unique symbols")
    
    # Find common symbols across all datasets
    if len(symbols) > 1:
        common_symbols = set.intersection(*symbols.values())
        print(f"\n✅ Common symbols across ALL datasets: {len(common_symbols)}")
        
        # Show top common symbols (sorted by price data if available)
        if common_symbols and data.get('price') is not None:
            # Get volume-weighted top symbols
            recent_date = data['price']['date'].max()
            recent_window = data['price']['date'] >= (recent_date - pd.Timedelta(days=30))
            recent_df = data['price'][recent_window].copy()
            recent_df['base'] = recent_df['symbol'].str.split('/').str[0].str.upper()
            
            top_symbols = recent_df.groupby('base')['volume'].sum().sort_values(ascending=False)
            top_common = [s for s in top_symbols.index if s in common_symbols][:20]
            
            print(f"   Top 20 (by volume): {', '.join(top_common)}")
    
    # Analyze overlap for each backtest strategy
    print("\n" + "=" * 80)
    print("BACKTEST STRATEGY DATA AVAILABILITY")
    print("=" * 80)
    
    strategies = {
        'Breakout': ['price'],
        'Mean Reversion': ['price'],
        'Days from High': ['price'],
        'Size Factor': ['price', 'marketcap'],
        'Carry Factor': ['price', 'funding'],
        'Volatility Factor': ['price'],
        'Kurtosis Factor': ['price'],
        'Beta Factor': ['price'],
        'Leverage Inverted': ['price', 'leverage'],
        'Dilution Factor': ['price', 'dilution'],
        'Turnover Factor': ['price', 'marketcap'],
        'ADF Factor': ['price'],
    }
    
    print(f"\n{'Strategy':<20} {'Required Data':<30} {'Symbols':<10} {'Status'}")
    print("-" * 80)
    
    for strategy, required in strategies.items():
        # Check if all required data is available
        available = all(data.get(d) is not None for d in required)
        
        if not available:
            print(f"{strategy:<20} {', '.join(required):<30} {'N/A':<10} ❌ Missing data")
            continue
        
        # Find symbols that have all required data
        strategy_symbols = [symbols[d] for d in required if d in symbols]
        if strategy_symbols:
            common_strategy_symbols = set.intersection(*strategy_symbols)
            status = "✅" if len(common_strategy_symbols) >= 20 else "⚠️"
            print(f"{strategy:<20} {', '.join(required):<30} {len(common_strategy_symbols):<10} {status}")
        else:
            print(f"{strategy:<20} {', '.join(required):<30} {'Unknown':<10} ⚠️")

def analyze_data_quality_by_period(data):
    """Analyze data quality and availability by time period."""
    print("\n" + "=" * 80)
    print("DATA QUALITY BY TIME PERIOD")
    print("=" * 80)
    
    if data.get('price') is None:
        print("Price data not available for analysis")
        return
    
    df = data['price'].copy()
    df['year'] = df['date'].dt.year
    
    print(f"\nPrice Data Coverage by Year:")
    print(f"{'Year':<8} {'Symbols':<10} {'Days':<8} {'Total Rows':<12} {'Avg Rows/Day'}")
    print("-" * 60)
    
    yearly_stats = df.groupby('year').agg({
        'symbol': 'nunique',
        'date': 'nunique',
        'close': 'count'
    }).reset_index()
    
    for _, row in yearly_stats.iterrows():
        year = int(row['year'])
        symbols = int(row['symbol'])
        days = int(row['date'])
        rows = int(row['close'])
        avg_per_day = rows / days if days > 0 else 0
        
        print(f"{year:<8} {symbols:<10} {days:<8} {rows:<12,} {avg_per_day:<.1f}")
    
    # Check data quality for recent period (last 30 days)
    recent_date = df['date'].max()
    recent_start = recent_date - pd.Timedelta(days=30)
    recent_df = df[df['date'] >= recent_start]
    
    print(f"\nRecent Data Quality (last 30 days):")
    print(f"  Date range: {recent_start.date()} to {recent_date.date()}")
    print(f"  Symbols: {recent_df['symbol'].nunique()}")
    print(f"  Days: {recent_df['date'].nunique()}")
    print(f"  Total rows: {len(recent_df):,}")
    print(f"  Expected rows (if daily): {recent_df['symbol'].nunique() * recent_df['date'].nunique():,}")
    
    # Check for stale data (symbols with no recent updates)
    last_date_per_symbol = df.groupby('symbol')['date'].max()
    stale_symbols = last_date_per_symbol[last_date_per_symbol < (recent_date - pd.Timedelta(days=7))]
    
    if len(stale_symbols) > 0:
        print(f"\n⚠️  {len(stale_symbols)} symbols with no data in last 7 days:")
        for symbol, last_date in stale_symbols.head(10).items():
            print(f"     {symbol}: last update {last_date.date()}")
    else:
        print(f"\n✅ All symbols have recent data (within 7 days)")

def main():
    """Main execution function."""
    print("=" * 80)
    print("BACKTEST DATA ALIGNMENT CHECK")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Load all data
    data = load_data()
    
    # Analyze date ranges
    date_ranges = analyze_date_ranges(data)
    
    # Analyze symbol overlap
    analyze_symbol_overlap(data)
    
    # Analyze data quality by period
    analyze_data_quality_by_period(data)
    
    print("\n" + "=" * 80)
    print("ALIGNMENT CHECK COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
