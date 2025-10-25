# Monthly Market Cap Snapshots - Documentation

## Overview

This repository contains monthly historical snapshots of cryptocurrency market data from CoinMarketCap, covering the top 200 cryptocurrencies by market capitalization for each month.

## Data Coverage

### Complete Coverage (34 months)
- **2023**: January - December (12 months)
- **2024**: January - December (12 months)  
- **2025**: January - October (10 months)

### Date Range
- **Start**: January 2023 (20230101)
- **End**: October 2025 (20251001)

## Files

### Individual Monthly Snapshots
Each month has its own CSV file in the format: `coinmarketcap_monthly_YYYYMM01.csv`

Example files:
- `coinmarketcap_monthly_20230101.csv` - January 2023
- `coinmarketcap_monthly_20240101.csv` - January 2024
- `coinmarketcap_monthly_20250101.csv` - January 2025

### Combined File
- `coinmarketcap_monthly_all_snapshots.csv` - All 34 monthly snapshots combined into one file
  - Total rows: 6,800 (200 cryptocurrencies × 34 months)
  - Columns: Rank, Name, Symbol, Market Cap, Price, Circulating Supply, Volume (24h), % 1h, % 24h, % 7d, snapshot_date

## Data Structure

Each snapshot file contains the following columns:

| Column | Description |
|--------|-------------|
| Rank | Ranking by market capitalization |
| Name | Full name of the cryptocurrency |
| Symbol | Trading symbol (e.g., BTC, ETH) |
| Market Cap | Total market capitalization in USD |
| Price | Price per unit in USD |
| Circulating Supply | Number of coins/tokens in circulation |
| Volume (24h) | 24-hour trading volume in USD |
| % 1h | Price change in last hour |
| % 24h | Price change in last 24 hours |
| % 7d | Price change in last 7 days |
| snapshot_date | Date of snapshot in YYYYMMDD format |

## Market Cap Trends

### 2023 Market Development
- **Q1 2023**: Recovery phase after 2022 bear market (~$0.79T - $1.17T)
- **Q2 2023**: Stabilization period (~$1.12T - $1.19T)
- **Q3 2023**: Slight pullback (~$1.03T)
- **Q4 2023**: Strong rally into year-end (~$1.30T - $1.44T)

### 2024 Market Development
- **Q1 2024**: Bitcoin ETF approval impact (~$1.62T - $2.29T)
- **Q2 2024**: All-time high territory (~$2.16T - $2.58T)
- **Q3 2024**: Consolidation phase (~$1.99T - $2.31T)
- **Q4 2024**: Year-end surge (~$2.12T - $3.43T)

### 2025 Market Development (YTD)
- **Q1 2025**: Strong start to the year (~$2.81T - $3.37T)
- **Q2 2025**: Volatility and recovery (~$2.72T - $3.28T)
- **Q3 2025**: Sustained growth (~$3.23T - $3.74T)
- **Oct 2025**: New highs (~$4.03T)

## Data Source

All data is sourced from CoinMarketCap's historical snapshot pages:
- URL format: `https://coinmarketcap.com/historical/YYYYMMDD/`
- Data is extracted from embedded JSON within the page HTML
- Each snapshot represents the state of the market on the 1st day of each month

## Scripts

### Data Fetching Scripts

1. **fetch_monthly_coinmarketcap_snapshots.py**
   - Fetches monthly snapshots for a rolling 12-month period
   - Used to keep data current

2. **fetch_monthly_2023_2024_snapshots.py**
   - Specific script used to backfill 2023-2024 data
   - Fetches 22 months of historical data (Jan 2023 - Oct 2024)
   - Includes 3-second delay between requests to be respectful to the server

### Usage Example

```python
import pandas as pd

# Load combined file
df = pd.read_csv('coinmarketcap_monthly_all_snapshots.csv')

# Filter for specific date
jan_2024 = df[df['snapshot_date'] == 20240101]

# Get Bitcoin data over time
btc_history = df[df['Symbol'] == 'BTC'].sort_values('snapshot_date')

# Calculate average market cap by month
monthly_avg = df.groupby('snapshot_date')['Market Cap'].mean()
```

## Data Quality Notes

- Each snapshot contains the top 200 cryptocurrencies by market cap at that time
- Rankings and included cryptocurrencies may change between snapshots
- All monetary values are in USD
- Market cap = Price × Circulating Supply
- Data represents a snapshot at a specific point in time (beginning of each month)

## Update History

- **October 2025**: Expanded dataset to include 2023-2024 monthly snapshots
  - Added 22 new monthly snapshots (Jan 2023 - Oct 2024)
  - Combined with existing 2024-2025 data
  - Total coverage: 34 months from January 2023 to October 2025

## Future Updates

To maintain current data, run the monthly snapshot script at the beginning of each month:
```bash
python3 fetch_monthly_coinmarketcap_snapshots.py
```

This will fetch the latest 12 months and update the combined file.
