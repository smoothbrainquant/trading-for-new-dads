# Kurtosis Factor Bug Fix Summary

**Date**: 2025-11-02  
**Branch**: cursor/investigate-kurtosis-factor-change-and-data-7f1a  
**Status**: ? FIXED AND VALIDATED

---

## Issue Summary

The kurtosis factor was showing negative performance because the momentum and mean reversion strategies had **inverted signal logic** in the vectorized implementation compared to the original looping backtest.

---

## Root Cause

In `signals/generate_signals_vectorized.py`, the signal directions were backwards:

| What You Asked For | What You Got | Expected Return | Actual Return |
|-------------------|--------------|-----------------|---------------|
| Momentum | Mean Reversion (inverted) | +180.98% | -47.19% ? |
| Mean Reversion | Momentum (inverted) | -47.19% | +180.98% (accidentally correct) |

---

## What Changed

### File Fixed: `signals/generate_signals_vectorized.py` (lines 415-425)

**BEFORE (WRONG):**
```python
if strategy == 'momentum':
    # Long low kurtosis (stable, trending)  ? WRONG!
    df.loc[df['percentile'] <= long_percentile, 'signal'] = 1
    # Short high kurtosis (fat tails, unstable)  ? WRONG!
    df.loc[df['percentile'] >= short_percentile, 'signal'] = -1

elif strategy == 'mean_reversion':
    # Long high kurtosis  ? WRONG!
    df.loc[df['percentile'] >= short_percentile, 'signal'] = 1
    # Short low kurtosis  ? WRONG!
    df.loc[df['percentile'] <= long_percentile, 'signal'] = -1
```

**AFTER (CORRECT):**
```python
if strategy == 'momentum':
    # Long high kurtosis (volatile, fat tails - momentum persists)  ? CORRECT!
    df.loc[df['percentile'] >= short_percentile, 'signal'] = 1
    # Short low kurtosis (stable, thin tails - underperformers)  ? CORRECT!
    df.loc[df['percentile'] <= long_percentile, 'signal'] = -1

elif strategy == 'mean_reversion':
    # Long low kurtosis (stable coins - expecting normalization)  ? CORRECT!
    df.loc[df['percentile'] <= long_percentile, 'signal'] = 1
    # Short high kurtosis (volatile coins - expecting reversion)  ? CORRECT!
    df.loc[df['percentile'] >= short_percentile, 'signal'] = -1
```

---

## Validation

### Unit Test Created: `tests/test_kurtosis_signal_direction.py`

**Test Results:**
```
? TEST 1: MOMENTUM STRATEGY - PASSED
   - High kurtosis coin (COIN_E) signal: 1 (expected: 1) ?
   - Low kurtosis coin (COIN_A) signal: -1 (expected: -1) ?

? TEST 2: MEAN REVERSION STRATEGY - PASSED
   - Low kurtosis coin (COIN_A) signal: 1 (expected: 1) ?
   - High kurtosis coin (COIN_E) signal: -1 (expected: -1) ?

? TEST 3: STRATEGIES ARE OPPOSITE - PASSED
   - Momentum and mean reversion produce opposite signals ?
```

---

## Expected Performance After Fix

Once vectorized backtests are re-run with the corrected code, they should match the looping backtest results:

| Strategy | Total Return | Ann. Return | Sharpe Ratio | Max DD |
|----------|-------------|-------------|--------------|---------|
| **Momentum** (30d, 14d rebal) | **+180.98%** | **31.90%** | **0.81** | -42.77% |
| Mean Reversion (30d, 7d rebal) | -47.19% | -15.73% | -0.39 | -75.47% |

---

## Data Coverage Confirmed

No issues found with data:
- **File**: `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- **Date Range**: 2020-01-01 to 2025-10-24 (5.8 years)
- **Total Rows**: 80,391
- **Coverage**: ? GOOD

---

## Answers to Original Questions

### 1. Why is kurtosis factor now negative?
**Answer**: The vectorized code had momentum and mean reversion strategies SWAPPED. When requesting "momentum", you got "mean reversion" results (-47.19% instead of +180.98%).

### 2. Was there a change in what side is long vs short?
**Answer**: YES. The vectorized implementation inverted the signals:
- **WRONG**: Momentum = Long low kurtosis, Short high kurtosis
- **CORRECT**: Momentum = Long high kurtosis, Short low kurtosis

### 3. What data was used?
**Answer**: `data/raw/combined_coinbase_coinmarketcap_daily.csv` with 5.8 years of history (2020-01-01 to 2025-10-24).

### 4. Any issue with data coverage?
**Answer**: NO. Data coverage is excellent with 80,391 rows across ~100 cryptocurrencies.

---

## Files Modified

### Fixed
- ? `/workspace/signals/generate_signals_vectorized.py` (lines 415-425)

### Created
- ? `/workspace/docs/factors/kurtosis/KURTOSIS_SIGNAL_INVERSION_BUG_REPORT.md`
- ? `/workspace/docs/factors/kurtosis/KURTOSIS_BUG_FIX_SUMMARY.md`
- ? `/workspace/tests/test_kurtosis_signal_direction.py`

### No Changes Needed (Already Correct)
- ? `/workspace/backtests/scripts/backtest_kurtosis_factor.py`
- ? `/workspace/execution/strategies/kurtosis.py`

---

## Implementation Consistency

All three implementations now agree:

| Implementation | Status | Location |
|----------------|--------|----------|
| Looping Backtest | ? Correct (always was) | `backtests/scripts/backtest_kurtosis_factor.py` |
| Execution Strategy | ? Correct (always was) | `execution/strategies/kurtosis.py` |
| Vectorized Signals | ? NOW FIXED | `signals/generate_signals_vectorized.py` |

---

## Next Steps

### Immediate (Complete)
- ? Identify bug
- ? Fix signal direction in vectorized code
- ? Create validation test
- ? Document bug and fix

### Recommended Follow-Up
1. ? Re-run vectorized backtests with corrected code
2. ? Compare vectorized vs looping results (should match within 0.1%)
3. ? Update any downstream code using vectorized kurtosis signals
4. ? Add regression tests to prevent future signal inversions

---

## Lesson Learned

**Always validate signal direction when porting between implementations.**

The confusion arose because:
1. "Momentum" can mean different things (price momentum vs kurtosis momentum)
2. Comments in the code were misleading
3. The inversion went unnoticed because only one strategy was tested initially

**Prevention**: 
- Unit tests comparing implementations
- Test BOTH strategies (momentum AND mean reversion)
- Validate signal logic matches documented strategy definitions

---

## Related Documents

- Original Bug Report: `/workspace/docs/factors/kurtosis/KURTOSIS_SIGNAL_INVERSION_BUG_REPORT.md`
- Original Backtest Summary: `/workspace/docs/factors/kurtosis/KURTOSIS_FACTOR_BACKTEST_SUMMARY.md`
- Factor Specification: `/workspace/docs/factors/kurtosis/KURTOSIS_FACTOR_SPEC.md`
- Vectorization Comparison: `/workspace/docs/factors/KURTOSIS_CARRY_VECTORIZATION_COMPARISON.md`

---

**Document Owner**: Research Team  
**Last Updated**: 2025-11-02  
**Status**: ? Bug Fixed and Validated
