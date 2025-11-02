# Days from High Backtest: Weight Calculation Error Analysis

## Executive Summary

The days from high backtest has a **critical weight calculation error** caused by duplicate symbol entries in the source data. The same asset (HYPE) appears with two different symbol formats (`HYPE/USDC` and `HYPE/USDC:USDC`), causing the backtest to treat them as separate instruments and incorrectly split portfolio allocation between them.

## Problem Description

### Symptom
When running the backtest for the 20-day from 200-day high strategy, portfolio weights are incorrectly allocated across duplicate symbols.

### Root Cause
The source data file (`top10_markets_100d_daily_data.csv`) contains duplicate entries for HYPE:
- `HYPE/USDC` - 100 occurrences
- `HYPE/USDC:USDC` - 100 occurrences

These represent the same underlying asset (possibly from different exchanges/data feeds) but are treated as separate instruments in the backtest.

### Impact
**Example from 2025-09-18:**
```
Portfolio Allocation (4 "positions"):
- HYPE/USDC:USDC:  22.13%
- HYPE/USDC:       22.13%  <- DUPLICATE
- SOL/USDC:USDC:   29.73%
- DOGE/USDC:USDC:  26.01%
```

**The problem:**
- HYPE should receive ~44% allocation total
- Instead, it's split into two 22% positions
- This doubles transaction costs (rebalancing both positions)
- Risk calculations are incorrect (treating 1 asset as 2)
- Position sizing is wrong (2x the number of intended positions)
- Weights don't reflect true portfolio concentration

### Evidence from Backtest Results

From `backtest_20d_200d_high_trades.csv`:
```csv
date,symbol,old_weight,new_weight,weight_change
2025-09-18,HYPE/USDC:USDC,0.0,0.22125799698410517,0.22125799698410517
2025-09-18,HYPE/USDC,0.0,0.22128295416257207,0.22128295416257207
2025-09-18,SOL/USDC:USDC,0.0,0.29734806994354485,0.29734806994354485
2025-09-18,DOGE/USDC:USDC,0.0,0.26011097890977786,0.26011097890977786
```

Weight sum: 0.221 + 0.221 + 0.297 + 0.260 = **0.999** ? (sums to 1.0, but wrong composition)

### Data Quality Issue

From `top10_markets_100d_daily_data.csv` on 2025-09-18:
```
date,symbol,open,high,low,close,volume
2025-09-18,HYPE/USDC,57.742,59.406,57.179,58.595,3774582.06
2025-09-18,HYPE/USDC:USDC,57.755,59.472,57.258,58.637,10639996.29
```

Both entries exist with nearly identical prices but different volumes, indicating they're from different data sources.

## Technical Details

### Where the Error Occurs

1. **Data Loading** (`backtest_20d_from_200d_high.py:load_data()`)
   - Loads CSV without deduplication
   - Both HYPE symbols pass through

2. **Days from High Calculation** (`calc_days_from_high.py:calculate_days_since_200d_high()`)
   - Processes each symbol independently
   - Both HYPE variants calculated separately

3. **Instrument Selection**
   - Both HYPE symbols meet the 20-day threshold
   - Both selected for portfolio

4. **Volatility Calculation** (`calc_vola.py:calculate_rolling_30d_volatility()`)
   - Both HYPE symbols get volatility calculated
   - Similar volatilities ? similar inverse volatilities

5. **Weight Calculation** (`calc_weights.py:calculate_weights()`)
   - Risk parity based on inverse volatility
   - Each HYPE symbol gets ~1/4 of total weight
   - **This is where the duplication becomes a weight error**

### Mathematical Impact on Risk Parity

Risk parity formula:
```
weight_i = (1 / volatility_i) / ?(1 / volatility_j)
```

**Correct scenario (1 HYPE symbol):**
```
Symbols: HYPE, SOL, DOGE
inv_vol: [1/0.85, 1/1.10, 1/1.25] = [1.176, 0.909, 0.800]
sum_inv_vol: 2.885
weights: [40.8%, 31.5%, 27.7%]
```

**Current broken scenario (2 HYPE symbols):**
```
Symbols: HYPE/USDC:USDC, HYPE/USDC, SOL, DOGE
inv_vol: [1/0.85, 1/0.85, 1/1.10, 1/1.25] = [1.176, 1.176, 0.909, 0.800]
sum_inv_vol: 4.061
weights: [29.0%, 29.0%, 22.4%, 19.7%]  <- HYPE split into 2x29%
```

## Solution Options

### Option 1: Deduplicate in Data Loading (Recommended)
**Pros:**
- Fixes issue at the source
- Most comprehensive solution
- Prevents downstream errors

**Implementation:**
```python
def load_data(filepath):
    df = pd.read_csv(filepath)
    df["date"] = pd.to_datetime(df["date"])
    
    # Normalize symbols: prefer the format with ":USDC" suffix
    df = df[df["symbol"].str.contains(":")]
    
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    return df
```

### Option 2: Deduplicate in Selection Logic
**Pros:**
- More flexible (can choose which format to keep)

**Cons:**
- Requires changes in multiple places
- Error-prone

### Option 3: Clean Source Data
**Pros:**
- Cleanest long-term solution

**Cons:**
- Requires data pipeline changes
- Need to ensure consistency going forward

## Recommended Fix

**Implement Option 1** in the backtest script with the following logic:

1. **Load data** with normalization
2. **Prefer symbols with `:USDC` suffix** (they have higher volume in the data)
3. **Filter out duplicates** without the suffix
4. **Add validation** to check for duplicates

### Validation Checks to Add

```python
# After loading data, check for symbol duplicates
def check_for_duplicate_symbols(df):
    """Check if any base symbols have multiple variants"""
    # Extract base symbols (e.g., "HYPE" from "HYPE/USDC:USDC")
    df["base_symbol"] = df["symbol"].str.split("/").str[0]
    
    # Group by date and base symbol
    duplicates = df.groupby(["date", "base_symbol"])["symbol"].nunique()
    
    if (duplicates > 1).any():
        problem_dates = duplicates[duplicates > 1]
        print(f"WARNING: Found duplicate base symbols on {len(problem_dates)} date-symbol combinations")
        print(problem_dates.head(10))
        return False
    return True
```

## Performance Impact

### Current Backtest Results (With Bug)
```
Initial Capital:        $10,000.00
Final Value:            $ 8,672.89
Total Return:           -13.27%
Annualized Return:      -92.57%
Sharpe Ratio:           -1.09
Max Drawdown:           -26.24%
Trading Days:           20
Avg Positions:          4.1
```

**Expected improvement after fix:**
- Fewer positions (3-4 instead of 4-5)
- Lower transaction costs (fewer rebalances)
- More accurate risk measurement
- Correct position concentrations

## Next Steps

1. ? **Identified the root cause**: Duplicate HYPE symbols in source data
2. ?? **Implement fix**: Add symbol deduplication in `backtest_20d_from_200d_high.py`
3. ?? **Add validation**: Check for duplicate symbols in all backtest scripts
4. ?? **Rerun backtest**: Verify weights sum correctly and no duplicates
5. ?? **Update documentation**: Document symbol format standards

## Related Files

- `/workspace/backtests/scripts/backtest_20d_from_200d_high.py` - Main backtest script
- `/workspace/signals/calc_days_from_high.py` - Days calculation
- `/workspace/signals/calc_weights.py` - Weight calculation
- `/workspace/data/raw/top10_markets_100d_daily_data.csv` - Source data with duplicates
- `/workspace/backtests/results/backtest_20d_200d_high_*.csv` - Current buggy results

## Conclusion

This is a **data quality issue** that manifests as a **weight calculation error**. The fix is straightforward: deduplicate symbols during data loading. The bug significantly impacts backtest accuracy by doubling certain positions and distorting risk calculations.

**Priority: HIGH** - This affects portfolio construction and risk management.

## Fix Implementation (COMPLETED)

### Code Change Applied

Updated the `load_data()` function in `backtest_20d_from_200d_high.py`:

```python
def load_data(filepath):
    df = pd.read_csv(filepath)
    df["date"] = pd.to_datetime(df["date"])
    
    # Deduplicate symbols: filter to keep only symbols with ":USDC" suffix
    # This fixes the duplicate HYPE/USDC and HYPE/USDC:USDC issue
    # We prefer the ":USDC" format as it has higher volume in the data
    if ":" in df["symbol"].iloc[0]:
        df = df[df["symbol"].str.contains(":")].copy()
    
    # Check for remaining duplicates
    base_symbols = df["symbol"].str.split("/").str[0]
    duplicates_by_date = df.groupby(["date", base_symbols])["symbol"].nunique()
    if (duplicates_by_date > 1).any():
        print("WARNING: Found duplicate base symbols after filtering!")
    
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    return df
```

### Verification Results

**Weight Verification (2025-09-18):**
```
HYPE/USDC:USDC:  28.41%
DOGE/USDC:USDC:  33.40%
SOL/USDC:USDC:   38.18%
----------------
Total:          100.00% ✓
```

**Symbol Count:**
- Original: 4 positions (including duplicate HYPE)
- Fixed: 3 positions (no duplicates: HYPE, SOL, DOGE)
- HYPE symbols: 1 (✓ duplicate removed)

### Performance Comparison

| Metric                | Original (Bug) | Fixed      | Improvement |
|-----------------------|----------------|------------|-------------|
| Final Value           | $8,672.89      | $8,843.18  | +$170.28    |
| Total Return          | -13.27%        | -11.57%    | +1.70 pp    |
| Annualized Return     | -92.57%        | -89.41%    | +3.17 pp    |
| Sharpe Ratio          | -1.09          | -1.11      | -0.02       |
| Max Drawdown          | -26.24%        | -24.60%    | +1.64 pp    |
| **Avg Positions**     | **4.1**        | **3.0**    | **-1.1**    |

**Key Improvements:**
1. ✅ Correct number of positions (3.0 vs 4.1)
2. ✅ Better performance (+$170.28 or +1.96%)
3. ✅ Reduced unnecessary rebalancing (58 trades vs more frequent rebalancing)
4. ✅ More accurate risk measurement
5. ✅ Proper portfolio concentration
6. ✅ Weights sum to exactly 1.0

### Status

**ISSUE RESOLVED** ✅

The weight calculation error has been successfully fixed by implementing symbol deduplication in the data loading process. The backtest now correctly allocates weights without duplicate symbols, resulting in more accurate performance metrics and proper portfolio construction.

---

## Impact on run_all_backtests.py

### Additional Discovery

The standalone script `backtest_20d_from_200d_high.py` is **NOT** used by `run_all_backtests.py`. Instead:

1. `run_all_backtests.py` uses the **vectorized** implementation through `run_days_from_high_backtest()` 
2. The data loading function `load_all_data()` **also had the same bug** - no symbol deduplication
3. This means **ALL backtests** in `run_all_backtests.py` were potentially affected by duplicate symbols

### Fix Applied

Updated `run_all_backtests.py` line 196-206 to add the same deduplication logic:
- Filter to keep only symbols with `:USDC` suffix
- Add validation to detect remaining duplicates
- Log the deduplication process

This ensures all backtests (breakout, mean reversion, volatility, beta, carry, days from high, etc.) work with clean, deduplicated data.

### Files Fixed

1. ✅ `/workspace/backtests/scripts/backtest_20d_from_200d_high.py` - Standalone script
2. ✅ `/workspace/backtests/scripts/run_all_backtests.py` - Centralized backtest runner

**Note:** The deduplication should ideally happen at the data collection/ingestion stage to prevent this issue from affecting any analysis or trading code that uses the raw data.
