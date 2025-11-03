#!/usr/bin/env python3
"""
Collect Historical DeFi Snapshots

This script should be run DAILY to build a time series database of:
- Fees (from DefiLlama)
- TVL (from DefiLlama)
- Yields (from DefiLlama)
- Market cap / FDV (from CoinGecko)

After collecting for several months, you can backtest:
- Fee Yield factor
- Emission Yield factor
- Net Yield factor
- Revenue Productivity factor
"""

import pandas as pd
import sqlite3
from datetime import datetime
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append('/workspace')


def create_database():
    """Create SQLite database for storing historical snapshots"""
    db_path = "/workspace/data/defi_factors_history.db"
    conn = sqlite3.connect(db_path)
    
    # Create tables
    conn.execute("""
        CREATE TABLE IF NOT EXISTS factor_snapshots (
            snapshot_date DATE NOT NULL,
            symbol TEXT NOT NULL,
            tvl REAL,
            daily_fees REAL,
            daily_revenue REAL,
            utility_yield_pct REAL,
            total_tvl REAL,
            weighted_apy REAL,
            weighted_apy_base REAL,
            weighted_apy_reward REAL,
            market_cap REAL,
            fdv REAL,
            volume_24h REAL,
            current_price REAL,
            fee_yield_pct REAL,
            emission_yield_pct REAL,
            net_yield_pct REAL,
            revenue_productivity_pct REAL,
            turnover_pct REAL,
            PRIMARY KEY (snapshot_date, symbol)
        )
    """)
    
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_snapshot_date 
        ON factor_snapshots(snapshot_date)
    """)
    
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_symbol 
        ON factor_snapshots(symbol)
    """)
    
    conn.commit()
    conn.close()
    
    print(f"✓ Database created/verified: {db_path}")
    return db_path


def load_latest_factor_snapshot() -> pd.DataFrame:
    """Load the most recent factor calculation"""
    # Find latest comprehensive factors file
    data_dir = Path("/workspace/data/raw")
    files = list(data_dir.glob("comprehensive_defi_factors_*.csv"))
    
    if not files:
        raise FileNotFoundError("No comprehensive factor files found. Run factor pipeline first.")
    
    latest_file = max(files, key=lambda x: x.stem.split('_')[-1])
    
    print(f"Loading: {latest_file.name}")
    df = pd.read_csv(latest_file)
    
    # Add snapshot date
    date_str = latest_file.stem.split('_')[-1]
    df['snapshot_date'] = pd.to_datetime(date_str, format='%Y%m%d')
    
    return df


def store_snapshot(df: pd.DataFrame, db_path: str):
    """Store factor snapshot in database"""
    conn = sqlite3.connect(db_path)
    
    # Select relevant columns
    columns = [
        'snapshot_date', 'symbol', 'tvl', 'daily_fees', 'daily_revenue',
        'utility_yield_pct', 'total_tvl', 'weighted_apy', 'weighted_apy_base',
        'weighted_apy_reward', 'market_cap', 'fdv', 'volume_24h', 'current_price',
        'fee_yield_pct', 'emission_yield_pct', 'net_yield_pct',
        'revenue_productivity_pct', 'turnover_pct'
    ]
    
    df_to_store = df[[c for c in columns if c in df.columns]].copy()
    
    # Store (replace if exists for same date/symbol)
    df_to_store.to_sql('factor_snapshots', conn, if_exists='append', index=False)
    
    conn.commit()
    conn.close()
    
    snapshot_date = df['snapshot_date'].iloc[0]
    print(f"✓ Stored {len(df_to_store)} factor snapshots for {snapshot_date.date()}")


def get_stored_history(db_path: str) -> pd.DataFrame:
    """Retrieve all stored historical snapshots"""
    conn = sqlite3.connect(db_path)
    
    query = "SELECT * FROM factor_snapshots ORDER BY snapshot_date, symbol"
    df = pd.read_sql(query, conn)
    
    conn.close()
    
    return df


def print_database_summary(db_path: str):
    """Print summary of stored data"""
    conn = sqlite3.connect(db_path)
    
    # Count snapshots by date
    query = """
        SELECT 
            snapshot_date,
            COUNT(DISTINCT symbol) as num_tokens,
            COUNT(*) as num_records
        FROM factor_snapshots
        GROUP BY snapshot_date
        ORDER BY snapshot_date
    """
    
    summary = pd.read_sql(query, conn)
    conn.close()
    
    if summary.empty:
        print("\nNo data in database yet")
        return
    
    print("\n" + "=" * 60)
    print("Historical Data Summary")
    print("=" * 60)
    print(f"\nTotal snapshots: {len(summary)}")
    print(f"Date range: {summary['snapshot_date'].min()} to {summary['snapshot_date'].max()}")
    print(f"Total records: {summary['num_records'].sum()}")
    
    print("\nSnapshots by date:")
    for _, row in summary.iterrows():
        print(f"  {row['snapshot_date']}: {row['num_tokens']} tokens")


def main():
    """Collect and store today's factor snapshot"""
    print("=" * 60)
    print("Historical DeFi Snapshot Collector")
    print("=" * 60)
    print()
    
    # Create/verify database
    db_path = create_database()
    
    try:
        # Load latest factors
        print("\nLoading latest factor calculations...")
        df = load_latest_factor_snapshot()
        
        # Store in database
        print("\nStoring snapshot in database...")
        store_snapshot(df, db_path)
        
        # Show summary
        print_database_summary(db_path)
        
        print("\n" + "=" * 60)
        print("✅ Snapshot collection complete!")
        print("=" * 60)
        print("\nTo backtest factors, you need:")
        print("  - At least 12 months of snapshots (for annual calculations)")
        print("  - Run this script daily to build time series")
        print(f"  - Current snapshots: {len(pd.read_sql('SELECT DISTINCT snapshot_date FROM factor_snapshots', sqlite3.connect(db_path)))}")
        
    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease run the factor pipeline first:")
        print("  ./run_factor_pipeline.sh")


if __name__ == "__main__":
    main()
