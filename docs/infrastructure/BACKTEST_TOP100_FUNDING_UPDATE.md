# Backtest Configuration Update - Top 100 Funding Rates Data

## Summary

Updated all backtest scripts and documentation to reference the expanded **top 100 historical funding rates dataset** instead of the previous top 50 dataset.

**Date**: October 28, 2025  
**New Dataset**: `historical_funding_rates_top100_ALL_HISTORY_20251028_002456.csv`

---

## What Changed

### Dataset Expansion
- **Previous**: Top 50 coins with 57,676 data points
- **New**: Top 100 coins with 99,032 data points (+72% increase)
- **Coverage**: 90 coins successfully fetched (90% coverage)
- **Date Range**: January 21, 2020 to October 28, 2025 (5.77 years)
- **File Size**: 8.6 MB

### Additional Coins (Ranks 51-100)
Added 44 new coins to the carry factor backtests, including:
- Mid-cap coins: Celestia, Stacks, Bonk, Injective, Immutable, Theta, The Graph
- Smaller caps: XDC, Quant, Pyth, Maker, SPX6900, Beam, Kaia, AIOZ, Starknet, Flow
- And many more across different market cap ranges

---

## Files Updated

### 1. Backtest Scripts

#### `/workspace/backtests/scripts/run_all_backtests.py`
**Line 840**: Updated default funding rates file path
```python
# Before
default='data/raw/historical_funding_rates_top50_ALL_HISTORY_20251027_102154.csv'

# After
default='data/raw/historical_funding_rates_top100_ALL_HISTORY_20251028_002456.csv'
```

**Updated help text**: 
```python
help='Path to funding rates data CSV file (top 100 coins, 2020-present)'
```

#### `/workspace/backtests/scripts/backtest_carry_factor.py`
**Line 607**: Updated default funding data file path
```python
# Before
default='historical_funding_rates_top50_ALL_HISTORY_20251025_123832.csv'

# After
default='historical_funding_rates_top100_ALL_HISTORY_20251028_002456.csv'
```

**Updated help text**:
```python
help='Path to historical funding rates CSV file (top 100 coins, 2020-present)'
```

### 2. Documentation

#### `/workspace/backtests/scripts/README_RUN_ALL_BACKTESTS.md`

**Line 56**: Updated example command
```bash
# Before
--funding-rates-file data/raw/historical_funding_rates_top100_20251025_124832.csv

# After
--funding-rates-file data/raw/historical_funding_rates_top100_ALL_HISTORY_20251028_002456.csv
```

**Line 67**: Updated parameter description
```markdown
# Before
- `--funding-rates-file`: Path to funding rates data CSV file

# After
- `--funding-rates-file`: Path to funding rates data CSV file (now includes top 100 coins with complete history from 2020-present)
```

---

## Dataset Details

### Top 100 Historical Funding Rates Dataset

**File**: `/workspace/data/raw/historical_funding_rates_top100_ALL_HISTORY_20251028_002456.csv`

**Specifications**:
- **Rows**: 99,032 data points
- **Coins**: 90 unique cryptocurrencies
- **Date Range**: 2020-01-21 to 2025-10-28
- **Days Covered**: 2,107 days
- **Columns**: rank, coin_name, coin_symbol, symbol, date, timestamp, funding_rate, funding_rate_pct, fr_open, fr_high, fr_low

**Longest History Coins**:
1. Monero (XMR): 2,108 days (5.77 years)
2. Tezos (XTZ): 2,094 days
3. IOTA (IOTA): 2,086 days
4. VeChain (VET): 2,084 days
5. Bitcoin (BTC): 1,906 days (5.22 years)

---

## Impact on Backtests

### Carry Factor Strategy Benefits

1. **Larger Universe**: More coins to select from when ranking by funding rates
   - Long positions: Broader selection of low (negative) funding rate coins
   - Short positions: More options for high (positive) funding rate coins

2. **Better Diversification**: 
   - Can allocate across 90 coins instead of 46
   - Reduces concentration risk
   - More stable risk parity weighting

3. **Mid-Cap Opportunities**:
   - Access to coins ranked 51-100
   - Potentially higher alpha from less efficient markets
   - Better capture of carry opportunities across market caps

4. **Longer History**:
   - More data for backtesting (5.77 years)
   - Covers multiple market cycles (bull, bear, recovery)
   - More reliable statistical inference

### Expected Performance Improvements

- **Signal Quality**: Larger universe should improve signal-to-noise ratio
- **Capacity**: More coins means higher strategy capacity
- **Risk Management**: Better diversification reduces idiosyncratic risk
- **Robustness**: Longer history provides more confidence in results

---

## Usage

### Running Backtests with Updated Data

#### Default Usage (Automatic)
```bash
cd /workspace
python3 backtests/scripts/run_all_backtests.py
```
Will now automatically use the top 100 dataset.

#### Standalone Carry Factor Backtest
```bash
cd /workspace/backtests/scripts
python3 backtest_carry_factor.py
```
Will now automatically use the top 100 dataset.

#### Custom Date Range
```bash
python3 backtests/scripts/run_all_backtests.py \
    --start-date 2020-01-01 \
    --end-date 2025-10-28 \
    --initial-capital 10000
```

#### With Custom Top-N Parameters
```bash
cd /workspace/backtests/scripts
python3 backtest_carry_factor.py \
    --top-n 15 \
    --bottom-n 15 \
    --rebalance-days 7 \
    --start-date 2020-01-01
```

This will use top 15 and bottom 15 coins instead of default 10, leveraging the expanded universe.

---

## Backward Compatibility

### Old Files Still Available
The previous top 50 datasets are still available in `/workspace/data/raw/` for comparison:
- `historical_funding_rates_top50_ALL_HISTORY_20251027_102154.csv`
- `historical_funding_rates_top50_ALL_HISTORY_20251025_123832.csv`

### Manual Override
You can still use the old dataset by explicitly specifying it:
```bash
python3 backtests/scripts/run_all_backtests.py \
    --funding-rates-file data/raw/historical_funding_rates_top50_ALL_HISTORY_20251027_102154.csv
```

---

## Verification

### Confirm Updates Applied

**Check run_all_backtests.py**:
```bash
grep -A 2 "funding-rates-file" backtests/scripts/run_all_backtests.py | grep default
```
Should show: `historical_funding_rates_top100_ALL_HISTORY_20251028_002456.csv`

**Check backtest_carry_factor.py**:
```bash
grep -A 2 "funding-data" backtests/scripts/backtest_carry_factor.py | grep default
```
Should show: `historical_funding_rates_top100_ALL_HISTORY_20251028_002456.csv`

**Verify File Exists**:
```bash
ls -lh data/raw/historical_funding_rates_top100_ALL_HISTORY_20251028_002456.csv
```
Should show: 8.6 MB file

---

## Related Documentation

- **Dataset Details**: `/workspace/docs/HISTORICAL_FUNDING_RATES_TOP100_COMPLETE_SUMMARY.md`
- **Script Documentation**: `/workspace/backtests/scripts/README_RUN_ALL_BACKTESTS.md`
- **Carry Factor Spec**: `/workspace/docs/PAIRS_TRADING_SPEC.md` (mentions carry factor)

---

## Next Steps

### Recommended Actions

1. **Re-run Backtests**: Execute all backtests with the new expanded dataset
   ```bash
   cd /workspace
   python3 backtests/scripts/run_all_backtests.py --start-date 2020-01-01
   ```

2. **Compare Results**: Compare new results against previous top 50 backtests
   - Check if Sharpe ratio improved
   - Verify diversification benefits
   - Analyze performance across different market cap tiers

3. **Optimize Parameters**: With larger universe, consider:
   - Increasing `top_n` and `bottom_n` (e.g., 15 or 20 instead of 10)
   - Adjusting rebalance frequency
   - Testing different long/short allocations

4. **Test Extended History**: Leverage the 5+ years of data
   - Run full-period backtests (2020-2025)
   - Analyze cycle-specific performance (bull vs bear)
   - Check strategy consistency over time

---

## Summary

✅ **Successfully updated all backtest scripts to use top 100 funding rates data**
- Run all backtests script: Updated
- Carry factor backtest script: Updated
- Documentation: Updated
- Dataset: 8.6 MB, 90 coins, 5.77 years of history

The expanded dataset provides:
- **+72% more data** (99,032 vs 57,676 points)
- **+44 more coins** (90 vs 46 coins)
- **Better diversification** across market caps
- **Longer history** for more robust backtests

All backtest scripts will now automatically use the expanded top 100 dataset for carry factor strategies.

---

**Generated**: October 28, 2025  
**Author**: Background Agent  
**Status**: Complete ✅
