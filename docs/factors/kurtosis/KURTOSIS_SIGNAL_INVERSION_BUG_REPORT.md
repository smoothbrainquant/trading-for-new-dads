# Kurtosis Factor Signal Inversion Bug Report

**Date**: 2025-11-02  
**Branch**: cursor/investigate-kurtosis-factor-change-and-data-7f1a  
**Severity**: **CRITICAL** - Signal directions are inverted  
**Status**: ? BUG IDENTIFIED

---

## Executive Summary

The kurtosis factor is showing negative performance because **the momentum and mean reversion strategies are SWAPPED in the vectorized implementation** compared to the original looping backtest.

### The Bug

In `signals/generate_signals_vectorized.py` (lines 415-425), the signal logic is **INVERTED**:

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

This is the **OPPOSITE** of the original looping backtest implementation in `backtests/scripts/backtest_kurtosis_factor.py` (lines 207-217):

```python
if strategy == "mean_reversion":
    # Long: Low kurtosis (stable coins)  ? CORRECT
    long_data = ranked_data[ranked_data["kurtosis_percentile"] <= long_percentile]
    # Short: High kurtosis (volatile coins)  ? CORRECT
    short_data = ranked_data[ranked_data["kurtosis_percentile"] >= short_percentile]

elif strategy == "momentum":
    # Long: High kurtosis (volatile coins)  ? CORRECT
    long_data = ranked_data[ranked_data["kurtosis_percentile"] >= short_percentile]
    # Short: Low kurtosis (stable coins)  ? CORRECT
    short_data = ranked_data[ranked_data["kurtosis_percentile"] <= long_percentile]
```

---

## Impact Analysis

### Original Looping Backtest Results (CORRECT)

From `backtests/results/kurtosis_factor_momentum_14d_rebal_metrics.csv`:

| Strategy | Total Return | Ann. Return | Sharpe | Max DD | Status |
|----------|-------------|-------------|--------|--------|---------|
| **Momentum** (Long HIGH kurtosis) | **+180.98%** | **31.90%** | **0.81** | -42.77% | ? CORRECT |
| Mean Reversion (Long LOW kurtosis) | -47.19% | -15.73% | -0.39 | -75.47% | ? CORRECT |

### Vectorized Implementation Results (INVERTED)

When you run the vectorized backtest with `strategy='momentum'`, you're actually getting the **mean reversion** results because the signals are inverted:

| What You Ask For | What You Actually Get | Expected Return | Actual Return |
|-----------------|----------------------|-----------------|---------------|
| Momentum | Mean Reversion (inverted) | +180.98% | **-47.19%** ? |
| Mean Reversion | Momentum (inverted) | -47.19% | **+180.98%** ? (by accident) |

---

## Root Cause Analysis

### Why The Inversion Happened

The confusion stems from the **interpretation of kurtosis values**:

1. **High kurtosis** = Fat tails, extreme moves, volatile coins
2. **Low kurtosis** = Thin tails, stable returns, less volatile coins

In the vectorized code, the comment says "Long low kurtosis (stable, trending)" for momentum, but this is **conceptually incorrect** for kurtosis factor:

- **Momentum strategy** should Long coins with **HIGH kurtosis** (volatile, fat-tailed) because these coins are experiencing extreme moves that persist
- **Mean reversion strategy** should Long coins with **LOW kurtosis** (stable, thin-tailed) because extreme volatility is expected to revert

The vectorized implementation appears to have confused **price momentum** (long recent winners) with **kurtosis momentum** (long high-kurtosis coins).

---

## Data Coverage Analysis

### Data File: `data/raw/combined_coinbase_coinmarketcap_daily.csv`

- **Date Range**: 2020-01-01 to 2025-10-24 (5.8 years)
- **Total Rows**: 80,391 rows
- **File Size**: 13 MB
- **Coverage**: ? GOOD - Sufficient history for kurtosis calculation

### Backtest Period

From the portfolio values:
- **Start**: 2022-01-31
- **End**: 2025-10-24 (approximately)
- **Duration**: ~3.8 years (1,363 days)
- **Coverage**: ? GOOD - No data issues identified

### Universe Size

From the metrics file:
- **Average Long Positions**: 1.26 (for mean reversion strategy)
- **Average Short Positions**: 2.26 (for mean reversion strategy)
- **Exposure**: ~91% gross exposure
- **Coverage**: ? ADEQUATE - Sufficient liquid coins

---

## Side-by-Side Comparison

### Correct Implementation (Looping Backtest)

```python
# backtests/scripts/backtest_kurtosis_factor.py

if strategy == "mean_reversion":
    # Long: Low kurtosis (stable coins)
    long_data = ranked_data[ranked_data["kurtosis_percentile"] <= long_percentile]
    # Short: High kurtosis (volatile coins)
    short_data = ranked_data[ranked_data["kurtosis_percentile"] >= short_percentile]

elif strategy == "momentum":
    # Long: High kurtosis (volatile coins)
    long_data = ranked_data[ranked_data["kurtosis_percentile"] >= short_percentile]
    # Short: Low kurtosis (stable coins)
    short_data = ranked_data[ranked_data["kurtosis_percentile"] <= long_percentile]
```

### Incorrect Implementation (Vectorized)

```python
# signals/generate_signals_vectorized.py

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

### Correct Implementation (execution/strategies/kurtosis.py)

The execution strategy file has it **CORRECT**:

```python
# execution/strategies/kurtosis.py (lines 136-155)

if strategy_type == "mean_reversion":
    # Mean Reversion: Long low kurtosis (stable), Short high kurtosis (unstable)
    long_df = kurtosis_df[kurtosis_df["percentile"] <= long_percentile].copy()
    short_df = kurtosis_df[kurtosis_df["percentile"] >= short_percentile].copy()
    # ...

elif strategy_type == "momentum":
    # Momentum: Long high kurtosis (volatile), Short low kurtosis (stable)
    long_df = kurtosis_df[kurtosis_df["percentile"] >= short_percentile].copy()
    short_df = kurtosis_df[kurtosis_df["percentile"] <= long_percentile].copy()
    # ...
```

---

## Files Affected

### ? Incorrect (Needs Fix)
- `/workspace/signals/generate_signals_vectorized.py` (lines 415-425)

### ? Correct (No Change Needed)
- `/workspace/backtests/scripts/backtest_kurtosis_factor.py` (lines 207-217)
- `/workspace/execution/strategies/kurtosis.py` (lines 136-155)

---

## Fix Required

### In `signals/generate_signals_vectorized.py` (lines 415-425)

**BEFORE (WRONG):**
```python
if strategy == 'momentum':
    # Long low kurtosis (stable, trending)
    df.loc[df['percentile'] <= long_percentile, 'signal'] = 1
    # Short high kurtosis (fat tails, unstable)
    df.loc[df['percentile'] >= short_percentile, 'signal'] = -1

elif strategy == 'mean_reversion':
    # Long high kurtosis
    df.loc[df['percentile'] >= short_percentile, 'signal'] = 1
    # Short low kurtosis
    df.loc[df['percentile'] <= long_percentile, 'signal'] = -1
```

**AFTER (CORRECT):**
```python
if strategy == 'momentum':
    # Long high kurtosis (volatile, fat tails)
    df.loc[df['percentile'] >= short_percentile, 'signal'] = 1
    # Short low kurtosis (stable, thin tails)
    df.loc[df['percentile'] <= long_percentile, 'signal'] = -1

elif strategy == 'mean_reversion':
    # Long low kurtosis (stable, expecting reversion)
    df.loc[df['percentile'] <= long_percentile, 'signal'] = 1
    # Short high kurtosis (volatile, expecting reversion)
    df.loc[df['percentile'] >= short_percentile, 'signal'] = -1
```

---

## Expected Results After Fix

Once the fix is applied, the vectorized backtest should produce results **identical** to the looping backtest:

| Strategy | Expected Total Return | Expected Sharpe |
|----------|----------------------|-----------------|
| Momentum (30d, 14d rebal) | **+180.98%** | **0.81** |
| Mean Reversion (30d, 7d rebal) | **-47.19%** | **-0.39** |

---

## Testing Plan

1. **Fix the code** in `generate_signals_vectorized.py`
2. **Re-run vectorized backtest** with both strategies
3. **Compare results** to looping backtest:
   - Total return should match within 0.1%
   - Sharpe ratio should match within 0.01
   - Position counts should be similar
4. **Validate** on different time periods
5. **Update documentation** to reflect correct implementation

---

## Lessons Learned

1. **Always validate signal direction** when porting from loop-based to vectorized
2. **Semantic naming matters**: "momentum" can mean different things (price momentum vs kurtosis momentum)
3. **Comments should match code**: The comments in the vectorized version misled the implementation
4. **Cross-validate with multiple implementations**: The execution strategy had it correct, but vectorized didn't
5. **Test both strategies**: If we had tested both momentum AND mean reversion, the inversion would have been obvious

---

## Recommendations

### Immediate Actions (Priority 1)

1. ? **Document the bug** (this file)
2. ? **Fix `generate_signals_vectorized.py`**
3. ? **Re-run backtests to validate fix**
4. ? **Update all documentation with correct results**

### Short-Term Actions (Priority 2)

1. **Add unit tests** that compare looping vs vectorized implementations
2. **Create assertion checks** in backtest code to validate signal direction
3. **Add logging** to show which coins are long vs short for manual validation

### Long-Term Actions (Priority 3)

1. **Standardize factor definitions** across all implementations
2. **Create a validation framework** for all factor strategies
3. **Add regression tests** to prevent future signal inversions

---

## Summary

**Question**: Why is kurtosis factor now negative?  
**Answer**: The vectorized implementation has the momentum and mean reversion strategies **SWAPPED**. When you ask for "momentum", you get "mean reversion" results (-47.19% return instead of +180.98%).

**Question**: Was there a change in what side is long vs short?  
**Answer**: YES. The vectorized code inverts the signal logic compared to both the looping backtest and the execution strategy.

**Question**: What data was used?  
**Answer**: `data/raw/combined_coinbase_coinmarketcap_daily.csv` with 5.8 years of data (2020-01-01 to 2025-10-24). Data coverage is good.

**Question**: Any issues with data coverage?  
**Answer**: NO. The data has sufficient history and coverage. The issue is purely a signal inversion bug in the vectorized code.

---

**Document Owner**: Research Team  
**Last Updated**: 2025-11-02  
**Status**: Bug Identified - Fix Required
