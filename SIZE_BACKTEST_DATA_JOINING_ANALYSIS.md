# Size Factor Backtest - Data Joining Analysis

## Executive Summary

The size factor backtest has **data joining inefficiencies** that result in:
- **5.72% data loss** (4,600 price data rows dropped)
- **23 symbols completely excluded** (13% of available symbols)
- **Suboptimal join method** (exact date match instead of as-of merge)

## Current Implementation

### Data Sources
1. **Price Data**: Daily OHLCV data
   - 80,390 rows
   - 2,124 unique dates (daily)
   - 172 unique symbols
   - Date range: 2020-01-01 to 2025-10-24

2. **Market Cap Data**: Monthly snapshots
   - 14,000 rows
   - 70 unique dates (monthly snapshots, typically 1st of month)
   - 737 unique symbols
   - Date range: 2020-01-01 to 2025-10-01

### Join Logic (`backtest_vectorized.py`, lines 139-167)

```python
# Current approach in prepare_factor_data() for 'size' factor:
merged = price_df_clean.merge(
    mcap_subset,
    on=['date', 'symbol'],  # JOIN ON BOTH DATE AND SYMBOL
    how='left'
)

# Forward-fill market cap within each symbol
merged = merged.sort_values(['symbol', 'date'])
merged['market_cap'] = merged.groupby('symbol')['market_cap'].ffill()

# Drop rows with no market cap data
merged = merged.dropna(subset=['market_cap'])
```

### Join Performance

| Metric | Value |
|--------|-------|
| **Initial join coverage** | 2.63% (only 2,115 of 80,390 rows match) |
| **Post-forward-fill coverage** | 94.28% (75,790 of 80,390 rows) |
| **Data loss** | 5.72% (4,600 rows dropped) |
| **Symbols lost** | 23 symbols (13% of 172 total) |
| **Symbols retained** | 149 symbols |

## Issues Identified

### 1. Exact Date Matching Inefficiency

**Problem**: The join requires exact date matches between daily price data and monthly market cap snapshots.

**Impact**:
- Only 2.63% of rows match initially (when price date equals snapshot date)
- Most price data rows (97.37%) don't have market cap data after initial join
- Forward-fill fixes most issues but is inefficient

**Example**:
```
Price dates:  2020-01-01, 2020-01-02, 2020-01-03, ..., 2020-01-31
MCap dates:   2020-01-01, 2020-02-01, 2020-03-01, ...
Join matches: 2020-01-01 only (1 match out of 31 days)
```

### 2. Lost Symbols

**Problem**: 23 symbols exist in price data but are completely excluded from the backtest.

**Lost symbols**:
- BTRST, LA, AIOZ, IO, ELA, METIS, TRB, AERO, PERP, XCN, and 13 others

**Reason**:
- These symbols never appear in market cap snapshots at the exact same dates they have price data
- Forward-fill can't help if there's no initial match

### 3. Data Loss Before First Snapshot

**Problem**: Any price data before a symbol's first market cap snapshot is lost.

**Example**:
- Symbol "XYZ" has price data from 2020-01-01
- But first market cap snapshot is 2020-06-01
- All price data from Jan-May is dropped (5 months of data lost)

## Recommended Fix

### Option 1: Use `pd.merge_asof()` (Preferred)

Replace the exact date join with an as-of merge that finds the most recent market cap for each price data row:

```python
# In prepare_factor_data() for 'size' factor:
price_sorted = price_df_clean.sort_values(['symbol', 'date'])
mcap_sorted = mcap_subset.sort_values(['symbol', 'date'])

merged = pd.merge_asof(
    price_sorted,
    mcap_sorted,
    on='date',
    by='symbol',
    direction='backward'  # Use most recent past market cap
)
```

**Benefits**:
- No need for forward-fill (more efficient)
- Better coverage (should reach ~94%+ directly)
- More intuitive (each price uses the most recent known market cap)

### Option 2: Pre-expand Market Cap Data

Pre-fill market cap to daily frequency before joining:

```python
# Expand market cap to daily frequency
daily_dates = pd.date_range(mcap_subset['date'].min(), mcap_subset['date'].max(), freq='D')
symbols = mcap_subset['symbol'].unique()
date_symbol_grid = pd.MultiIndex.from_product([daily_dates, symbols], names=['date', 'symbol'])

mcap_daily = mcap_subset.set_index(['date', 'symbol']).reindex(date_symbol_grid)
mcap_daily['market_cap'] = mcap_daily.groupby('symbol')['market_cap'].ffill()
mcap_daily = mcap_daily.reset_index()

# Now join on date and symbol with full coverage
merged = price_df_clean.merge(mcap_daily, on=['date', 'symbol'], how='left')
```

**Benefits**:
- 100% coverage for dates after first snapshot
- Clear and explicit
- No surprises with forward-fill

## Testing Recommendations

1. **Verify symbol coverage**: Ensure all symbols in price data that should be included are retained
2. **Check date alignment**: Verify market cap values align correctly with price data dates
3. **Test edge cases**: 
   - Symbols with sparse market cap data
   - New symbols added mid-backtest
   - Symbols with gaps in market cap data
4. **Compare results**: Run backtest with old and new join methods to ensure consistency

## Impact Assessment

**Current state**:
- Backtest is functional but suboptimal
- Missing 13% of symbols (23 coins)
- 5.72% data loss may skew results

**After fix**:
- Should retain more symbols
- Better data coverage
- More accurate backtest results
- Cleaner, more maintainable code

## Files to Modify

1. **`backtests/scripts/backtest_vectorized.py`**
   - Function: `prepare_factor_data()` (lines 139-167)
   - Change: Replace exact date join + forward-fill with `pd.merge_asof()`

## Related Code

The size factor backtest is called from:
- `backtests/scripts/run_all_backtests.py` (lines 1868-1881)
- Which calls `run_size_factor_backtest()` (lines 411-481)
- Which calls `backtest_factor_vectorized()` from `backtest_vectorized.py`
- Which calls `prepare_factor_data()` for 'size' factor (the problematic section)
