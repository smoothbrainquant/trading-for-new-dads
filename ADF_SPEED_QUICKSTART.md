# ADF Backtest Speed Optimization - Quick Start Guide

## TL;DR

**Question:** Can we speed up ADF backtest with a 20-day window instead of 60-day?

**Answer:** ❌ **NO** - 20-day produces different signals. Use these optimizations instead:

```bash
# Fast mode (recommended for development)
python3 backtests/scripts/backtest_adf_factor.py \
  --maxlag 4 \
  --cache-file backtests/results/adf_cache.csv

# First run: ~4 minutes (vs 6 minutes before)
# Subsequent runs: ~0 seconds (loads from cache!)
```

---

## What Changed?

### ✅ New Option 1: Fixed Maxlag (1.26x faster)

```bash
# Use maxlag=4 (default, faster)
python3 backtest_adf_factor.py --maxlag 4

# Use autolag="AIC" (slower, more optimal)
python3 backtest_adf_factor.py --maxlag 0
```

### ✅ New Option 2: Caching (∞ faster on reruns)

```bash
# First run: calculates and saves ADF
python3 backtest_adf_factor.py \
  --cache-file backtests/results/adf_cache_60d.csv

# Subsequent runs: instant load from cache
# Perfect for testing different strategies/parameters!
```

---

## Why Not 20-Day Window?

**Tested and found:**
- Only 1.3x faster (minimal gain)
- **Completely different signals** (rank correlation = 0.04)
- Captures short-term vs medium-term mean reversion
- Different strategy, not a replacement

**Recommendation:** Test 20-day as separate strategy if interested in short-term patterns

---

## Quick Commands

### Development (Fast + Cached)
```bash
python3 backtests/scripts/backtest_adf_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy mean_reversion_premium \
  --maxlag 4 \
  --cache-file backtests/results/adf_cache.csv
```

### Production (Optimal)
```bash
python3 backtests/scripts/backtest_adf_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy mean_reversion_premium \
  --maxlag 0
```

### Test 20-Day as Separate Strategy
```bash
python3 backtests/scripts/backtest_adf_factor.py \
  --adf-window 20 \
  --rebalance-days 3 \
  --output-prefix backtests/results/adf_shortterm
```

---

## Performance Summary

| Configuration | Time | Use Case |
|--------------|------|----------|
| Original (autolag) | ~6 min | Production |
| **New (maxlag=4)** | **~4 min** | **Default** |
| **Cached** | **~0 sec** | **Development** |
| 20-day window | ~4 min | Different strategy |

---

## Full Documentation

See detailed analysis and implementation:
- `ADF_SPEED_OPTIMIZATION_SUMMARY.md` - Complete summary
- `ADF_BACKTEST_SPEED_ANALYSIS.md` - Detailed analysis and recommendations
