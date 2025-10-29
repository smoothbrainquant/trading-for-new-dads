# Backtest Performance - Quick Start Guide

## TL;DR - The Problem

Your backtests take **1+ hour** because of 3 extremely slow backtests:
- **ADF Factor**: 30-60+ minutes (expensive statistical tests)
- **Beta Factor**: 10-20 minutes (rolling covariance calculations)
- **Kurtosis Factor**: 5-15 minutes (4th moment calculations)

## Solution: Use `--skip-slow` Flag

### Fast Mode (5-10 minutes) ⚡
```bash
python3 backtests/scripts/run_all_backtests.py --skip-slow
```

This runs 7 fast backtests and skips the 3 slow ones.

### Complete Mode (1+ hours) 🐢
```bash
python3 backtests/scripts/run_all_backtests.py
```

This runs all 10 backtests including the slow ones.

## What You Get Now

### ✅ Timing for Each Backtest
```
Running Breakout Signal Backtest
    ⏱️  Completed in 2.45 seconds

Running Mean Reversion Backtest
    ⏱️  Completed in 3.12 seconds
```

### ✅ Timing Summary at the End
```
⏱️  EXECUTION TIME SUMMARY
========================================================
  ADF Factor                     1847.23s  (65.2%)
  Beta Factor (BAB)               523.45s  (18.5%)
  Kurtosis Factor                 287.12s  (10.1%)
  OI Divergence                    85.34s   (3.0%)
  ...
```

### ✅ Warning Before Slow Backtests
```
⚠️  WARNING: ADF backtest is VERY computationally expensive (use --skip-slow to skip)
```

### ✅ Data Loading Progress
```
⏱️  Loading data files (this happens only once)...
  📊 Loading price data...
     ✓ Loaded 80391 rows
✅ All data loaded in 2.34 seconds
```

## Backtests Summary

| Backtest | Speed | Included with --skip-slow? |
|----------|-------|---------------------------|
| Breakout Signal | ⚡ Fast (~2-3s) | ✅ Yes |
| Mean Reversion | ⚡ Fast (~3-5s) | ✅ Yes |
| Size Factor | ⚡ Fast (~5-8s) | ✅ Yes |
| Carry Factor | ⚡ Fast (~3-5s) | ✅ Yes |
| Days from High | ⚡ Fast (~2-4s) | ✅ Yes |
| OI Divergence | ⚡ Fast (~80-120s) | ✅ Yes |
| Volatility Factor | ⚡ Fast (~10-20s) | ✅ Yes |
| **Kurtosis Factor** | 🐢 **Slow (5-15min)** | ❌ **SKIPPED** |
| **Beta Factor** | 🐢 **Slow (10-20min)** | ❌ **SKIPPED** |
| **ADF Factor** | 🐢 **VERY SLOW (30-60min)** | ❌ **SKIPPED** |

## Example Usage

### For Daily Development & Testing
```bash
# Fast mode - results in 5-10 minutes
python3 backtests/scripts/run_all_backtests.py --skip-slow \
    --start-date 2023-01-01 \
    --output-file backtests/results/fast_summary.csv
```

### For Weekly/Monthly Complete Analysis
```bash
# Complete mode - all 10 backtests (1+ hours)
python3 backtests/scripts/run_all_backtests.py \
    --start-date 2023-01-01 \
    --output-file backtests/results/complete_summary.csv
```

### To Run Only Specific Backtests
```bash
# Run only fast backtests manually
python3 backtests/scripts/run_all_backtests.py \
    --no-run-adf \
    --no-run-beta \
    --no-run-kurtosis
```

## Performance Comparison

| Mode | Time | Backtests | Use Case |
|------|------|-----------|----------|
| **--skip-slow** | 5-10 min | 7 strategies | Daily development, testing, iteration |
| **Complete** | 60-90+ min | 10 strategies | Final analysis, research reports |

## Next Steps

1. **Try it now with --skip-slow**
   ```bash
   python3 backtests/scripts/run_all_backtests.py --skip-slow
   ```

2. **Review the timing summary** to understand which backtests take longest

3. **Use fast mode by default** for development

4. **Run complete mode** only when you need all strategies

For more details, see: `BACKTEST_PERFORMANCE_OPTIMIZATION.md`
