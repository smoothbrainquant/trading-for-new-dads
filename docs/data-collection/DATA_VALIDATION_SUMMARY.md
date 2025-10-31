# Data Validation Summary

**Generated:** 2025-10-25  
**Total Files:** 65 CSV files  
**Total Size:** 29.86 MB  
**Total Rows:** 327,030

---

## 📊 Summary by API Source

| API Source | Files | Type | N Symbols | Date Range | Size (MB) | Rows |
|------------|-------|------|-----------|------------|-----------|------|
| **CCXT** | 8 | Price, Market Cap, Other | 1,076 unique | 2020-01-01 to 2025-10-24 | 21.59 | 232,161 |
| **Coinalyze** | 9 | Funding Rates | 490 unique | 2020-01-21 to 2025-10-25 | 6.24 | 73,601 |
| **CMC** | 42 | Market Cap | 8,920 total | 2020-01-05 to 2025-10-01 | 1.71 | 16,000 |
| **Unknown** | 6 | Various (derived) | 46 unique | 2024-06-11 to 2025-10-23 | 0.32 | 5,268 |

---

## 🔍 Detailed Breakdown

### 1. CCXT (Exchange Data) - 8 Files

#### Price Data (5 files)
- **Main Dataset:** `coinbase_spot_daily_data_20200101_20251024_110130.csv`
  - **Type:** Price (OHLCV)
  - **Symbols:** 172 spot pairs
  - **Date Range:** 2020-01-01 to 2025-10-24 (5.8 years)
  - **Rows:** 80,390
  - **Size:** 4.8 MB
  - **Key Symbols:** BTC/USD, ETH/USD, SOL/USD, XRP/USD, etc.

- **Other Price Files:** 4 smaller datasets with varying date ranges and symbols (22-27 symbols each)

#### Market Cap Data (1 file)
- **Combined Dataset:** `combined_coinbase_coinmarketcap_daily.csv`
  - **Type:** Price + Market Cap (combined)
  - **Symbols:** 172 cryptocurrencies
  - **Date Range:** 2020-01-01 to 2025-10-24
  - **Rows:** 80,390
  - **Size:** 12.41 MB

#### Other Data (2 files)
- **Hyperliquid Markets:** 436 markets by volume
- **Hyperliquid Perpetuals:** 215 perpetual futures contracts

---

### 2. Coinalyze (Funding Rates) - 9 Files

#### Main Historical Dataset
- **File:** `historical_funding_rates_top50_ALL_HISTORY_20251025_123832.csv`
  - **Type:** Funding Rates (daily OHLC)
  - **Symbols:** 46 cryptocurrencies
  - **Date Range:** 2020-01-21 to 2025-10-25 (5.76 years)
  - **Rows:** 57,676
  - **Size:** 4.93 MB
  - **Key Symbols:** BTC, ETH, XRP, SOL, BNB, ADA, DOT, etc.

#### Recent Snapshots (90-day)
- **Top 50 (90d):** 4,154 rows, 47 coins
- **Top 100 (90d):** 8,384 rows, 94 coins

#### Summary Files (3 files)
- Data availability reports
- Per-coin statistics (avg, std, min, max)

---

### 3. CoinMarketCap (CMC) - 42 Files

#### Historical Snapshots (6 files)
- **Annual snapshots:** 2020, 2021, 2022, 2023, 2024, 2025
- **Type:** Market Cap, Price, Volume, % Changes
- **Symbols:** Top 200 cryptocurrencies per snapshot
- **Rows:** 200 per snapshot
- **All Snapshots Combined:** 1,200 rows, 499 unique symbols

#### Monthly Snapshots (36 files)
- **Period:** 2023-01 to 2025-10
- **Type:** Market Cap, Price, Volume, % Changes
- **Symbols:** Top 200 per month
- **Rows:** 200 per snapshot
- **All Monthly Combined:** 6,800 rows, 422 unique symbols

---

### 4. Unknown/Derived (6 Files)

These files appear to be generated from analysis scripts or transformations:

#### Price Data (2 files)
- `top10_markets_100d_daily_data.csv` - 10 markets, 100 days
- `top10_markets_500d_daily_data.csv` - 10 markets, 500 days

#### Volatility (1 file)
- `rolling_30d_volatility.csv` - 30-day rolling volatility for 10 symbols

#### Signals (1 file)
- `selected_longs_breakout.csv` - Breakout signals for 10 instruments

#### Other (2 files)
- `directional_mean_reversion_by_period.csv` - Mean reversion analysis
- `selected_instruments_near_200d_high.csv` - Instruments near 200-day high

---

## 📈 Key Datasets Overview

### Primary Data Sources

| Dataset | API | Type | Symbols | Start Date | End Date | Rows |
|---------|-----|------|---------|------------|----------|------|
| **Coinbase Spot Price** | CCXT | Price | 172 | 2020-01-01 | 2025-10-24 | 80,390 |
| **Funding Rates (Full History)** | Coinalyze | Funding | 46 | 2020-01-21 | 2025-10-25 | 57,676 |
| **Combined Price + Market Cap** | CCXT + CMC | Price + Market Cap | 172 | 2020-01-01 | 2025-10-24 | 80,390 |
| **CMC Monthly Snapshots** | CMC | Market Cap | 422 | 2023-01-01 | 2025-10-01 | 6,800 |
| **CMC Historical Snapshots** | CMC | Market Cap | 499 | 2020-01-05 | 2025-01-05 | 1,200 |

---

## 🎯 Data Coverage Summary

### By Data Type

| Type | Files | Total Rows | Unique Symbols | Date Range |
|------|-------|------------|----------------|------------|
| **Price (OHLCV)** | 7 | 155,499 | ~180 | 2020-01-01 to 2025-10-24 |
| **Funding Rates** | 9 | 73,601 | 490 total | 2020-01-21 to 2025-10-25 |
| **Market Cap** | 43 | 96,390 | ~500 | 2020-01-05 to 2025-10-01 |
| **Volatility** | 1 | 866 | 10 | 2025-06-30 to 2025-10-07 |
| **Signals** | 1 | 10 | 10 | 2025-10-07 |
| **Other** | 4 | 664 | Various | Various |

---

## 📝 Data Quality Notes

### ✅ Strengths

1. **Long History:** Price and funding data go back to 2020 (5+ years)
2. **High Coverage:** 172+ spot pairs, 46+ funding rates, 500+ market cap records
3. **Daily Granularity:** All primary datasets have daily frequency
4. **Clean Format:** Consistent CSV structure with proper date columns
5. **Multiple Sources:** Data from multiple APIs for cross-validation

### ⚠️ Limitations

1. **CMC Date Issue:** CoinMarketCap files show dates as "1970-01-01" (snapshot_date field should be used instead)
2. **Missing Data:** Not all coins have complete history (new listings)
3. **API Coverage:** Some files marked as "unknown" source (likely derived/processed)

---

## 🔄 Recommended Next Steps

1. **Data Consolidation:** Merge price + funding + market cap into unified dataset
2. **Date Validation:** Fix CMC date parsing to use snapshot_date field
3. **Symbol Standardization:** Standardize symbol formats (e.g., BTC vs BTC/USD vs BTCUSD_PERP)
4. **Gap Analysis:** Identify missing dates or symbols in key datasets
5. **Data Versioning:** Consider archiving old snapshots to reduce file count

---

## 📊 File Manifest

**Full validation results saved to:**
- `/workspace/data/raw/data_validation_summary_20251025_165028.csv`

**To re-run validation:**
```bash
python3 data/scripts/validate_data_sources.py
```

---

**Last Updated:** 2025-10-25
