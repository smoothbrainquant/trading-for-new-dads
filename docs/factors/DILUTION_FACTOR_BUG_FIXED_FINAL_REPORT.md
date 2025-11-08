# Dilution Factor Backtest: Bug Fixed - Final Report

**Date:** November 2, 2025  
**Status:** ? COMPLETE - Bug Fixed, Data Matched, Results Validated

---

## Executive Summary

The dilution factor backtest showed **2,641% returns** which were **completely fake** due to a portfolio construction bug. After fixing the bug and properly matching data sources, the strategy **loses -27.8%** (annualized -6.7%).

**The bug caused the portfolio to collapse from 20 intended positions to just 4.6 average positions, creating accidental concentration that caught lucky outliers.**

---

## The Data Matching Problem

### Coverage Analysis

| Dataset | Total Coins | Coverage |
|---------|-------------|----------|
| **Dilution data** | 565 coins | - |
| **Price data** | 172 coins | - |
| **BOTH (tradeable)** | **170 coins** | **30%** |

### Top 150 Coins by Market Cap

Of the top 150 coins by market cap:
- **87 tradeable** (58% coverage)
- **63 missing price data** (42%)

Missing major coins include: USDC (#7), TRX (#9), TON (#23), MNT (#25), OKB (#32), BGB (#34)

### Root Cause

The portfolio construction logic selected coins based on dilution data **first**, then tried to get price data for volatility calculation. Since 75% of selected coins lacked price data, they were silently dropped.

---

## The Bug

### Buggy Code Flow

```python
# Step 1: Select based on dilution (565 coin universe)
long_candidates = valid_signals.head(10)   # BNB, ADA, SHIB, FET, OKB...
short_candidates = valid_signals.tail(10)  # MORPHO, ENA, ETHFI...

# Step 2: Calculate volatility (requires price data - only 172 coins)
long_candidates['volatility'] = calculate_volatility(...)

# Step 3: Filter out coins without price data
long_candidates = long_candidates[volatility.notna()]
# Result: BNB ?, ADA ?, SHIB ?, FET ?, OKB ? ? only ZEC ?

# BROKEN: 1-4 positions instead of 20
```

### Fixed Code Flow

```python
# Step 1: Filter to coins WITH price data FIRST (170 coin universe)
available_coins = price_df['base'].unique()
valid_signals = valid_signals[valid_signals['symbol'].isin(available_coins)]

# Step 2: Pre-calculate volatility for ALL candidates
valid_signals['volatility'] = calculate_volatility(...)
valid_signals = valid_signals[volatility.notna()]

# Step 3: NOW select top/bottom from tradeable universe
adjusted_top_n = min(10, len(valid_signals) // 2)
long_candidates = valid_signals.head(adjusted_top_n)
short_candidates = valid_signals.tail(adjusted_top_n)

# FIXED: 10-16 properly diversified positions
```

---

## Results Comparison

### Performance Metrics

| Metric | Buggy (Broken) | Fixed (Correct) | Difference |
|--------|----------------|-----------------|------------|
| **Total Return** | +2,641.03% | **-27.77%** | -2,668.80% |
| **Annualized Return** | +101.59% | **-6.66%** | -108.24% |
| **Volatility** | 98.03% | 40.29% | -57.75% |
| **Sharpe Ratio** | 1.04 | **-0.17** | -1.20 |
| **Max Drawdown** | -88.84% | -60.98% | +27.86% |
| **Win Rate** | 50.65% | 51.45% | +0.79% |
| **Avg Positions** | **4.56** ? | **14.16** ? | +9.60 |
| **Median Positions** | **4** ? | **14** ? | +10 |

### Position Distribution

**Buggy Version (Broken):**
```
3 positions:  22.6% of days
4 positions:  33.5% of days
5 positions:  23.0% of days
6-8 positions: 20.9% of days
```

**Fixed Version (Correct):**
```
10 positions:  5.2% of days
12 positions: 33.4% of days
14 positions: 33.5% of days
16 positions: 16.0% of days
20 positions: 11.9% of days  ? Target achieved 12% of time
```

---

## Why The Buggy Version Had Fake Returns

### Example: September 2025

**Buggy Portfolio:**
- 1 long: ZEC (100% weight) ? Accidental concentration
- 3 shorts: MORPHO, ENA, ETHFI

**What Happened:**
- Oct 1, 2025: ZEC had +62.96% single-day return
- Portfolio return: **+58.5% in ONE day**
- This single day = ~45% of total cumulative returns

**If Properly Diversified:**
- 8 longs: ZEC would be 1/8 of long book
- Portfolio return: ~10-15% instead of 58.5%
- **8x leverage reduction** from proper diversification

### The Math

```
Impact of Concentration:
  Buggy:  100% ? 63% = +63% portfolio impact
  Fixed:  12.5% ? 63% = +7.9% portfolio impact
  
  Difference: 8x amplification from accidental concentration
```

---

## Files Created

### Code
- **`backtests/scripts/backtest_dilution_factor.py`** - Fixed version (main backtest)
- **`backtests/scripts/backtest_dilution_factor_comparison.py`** - Buggy vs Fixed comparison

### Documentation
- **`DILUTION_FACTOR_BUG_FIXED_FINAL_REPORT.md`** - This file (comprehensive summary)
- **`DILUTION_FACTOR_BUG_FIX_SUMMARY.md`** - Technical details
- **`docs/factors/DILUTION_FACTOR_OUTLIER_ANALYSIS.md`** - Detailed analysis
- **`tradeable_universe.txt`** - List of 170 tradeable coins

### Results
- **`dilution_factor_bug_vs_fixed_comparison.png`** - Visual comparison chart
- **`dilution_factor_bug_fix_comparison.csv`** - Metrics comparison table
- **`dilution_factor_portfolio_values.csv`** - Fixed backtest daily values
- **`dilution_factor_metrics.csv`** - Fixed backtest performance metrics
- **`dilution_factor_trades.csv`** - Fixed backtest trade history

### Data Matching
- **`tradeable_universe.txt`** - 170 coins with both dilution and price data
- Data coverage: 58% of top 150 coins by market cap

---

## Code Changes Made

### File: `backtests/scripts/backtest_dilution_factor.py`

**Lines 220-231 - ADDED:**
```python
# *** FIX: Filter to coins with price data BEFORE selecting top/bottom ***
# Get list of coins with sufficient price data
available_coins = price_df['base'].unique()
valid_signals = valid_signals[valid_signals['symbol'].isin(available_coins)]

# Pre-calculate volatility for all candidates
valid_signals['volatility'] = valid_signals['symbol'].apply(
    lambda s: calculate_volatility(price_df, s, rebal_date)
)

# Keep only coins with valid volatility (sufficient price history)
valid_signals = valid_signals[valid_signals['volatility'].notna()]
```

**Lines 233-244 - ADDED:**
```python
# Dynamically adjust position count based on available coins
# Need at least 4 coins total (2 long + 2 short minimum)
if len(valid_signals) < 4:
    print(f"  Warning: Only {len(valid_signals)} coins with valid data (need minimum 4)")
    return {}

# Adjust top_n if we don't have enough coins
adjusted_top_n = min(top_n, len(valid_signals) // 2)

if adjusted_top_n < top_n:
    print(f"  Note: Adjusted to {adjusted_top_n} positions per side (have {len(valid_signals)} valid coins)")
```

**Lines 246-251 - MODIFIED:**
```python
# Sort by dilution velocity
valid_signals = valid_signals.sort_values('dilution_velocity')

# Select long (lowest dilution) and short (highest dilution)
long_candidates = valid_signals.head(adjusted_top_n).copy()  # Changed: use adjusted_top_n
short_candidates = valid_signals.tail(adjusted_top_n).copy()  # Changed: use adjusted_top_n
```

---

## Verification Steps Completed

? **Data matching report created** - 170 tradeable coins identified  
? **Portfolio construction bug fixed** - Filters by price data availability first  
? **Buggy version re-run** - Reproduced original broken results (2,641% with 4.6 positions)  
? **Fixed version re-run** - Verified proper diversification (-27.8% with 14.2 positions)  
? **Side-by-side comparison** - Demonstrated impact of bug fix  
? **Visual comparison charts** - Created comprehensive visualization  
? **Documentation complete** - Full technical documentation provided  

---

## Key Takeaways

### 1. The Strategy Does Not Work

With proper diversification, the dilution factor strategy **loses money** (-6.7% annualized). The apparent profitability was entirely due to a bug.

### 2. Importance of Data Validation

Always verify that all data sources have adequate overlap before running strategies. A 30% overlap (170/565 coins) is insufficient for a strategy targeting top 150.

### 3. Silent Failures Are Dangerous

The original code silently dropped 15/20 positions without warning. This created a misleading backtest that appeared successful.

### 4. Diversification Matters

The bug created 8x leverage through accidental concentration. Proper diversification (14 positions vs 4) completely changed the risk/return profile.

### 5. Test Portfolio Composition

Monitor actual portfolio composition over time. If you expect 20 positions but only have 4, something is wrong.

---

## Recommendation

### ? DO NOT TRADE THIS STRATEGY

The dilution factor does not predict cryptocurrency returns when properly tested with adequate diversification.

**Reasons:**
1. Strategy loses money with proper implementation (-6.7% annualized)
2. Original results were due to bug + lucky outliers
3. Insufficient data coverage (only 58% of top 150 coins tradeable)
4. High volatility (40.3%) with negative returns = poor risk-adjusted performance

### ? What Was Learned

1. How to identify and fix portfolio construction bugs
2. Importance of data source validation and matching
3. Impact of diversification on strategy performance
4. Need for robust testing and position monitoring

---

## Conclusion

The investigation revealed that the dilution factor backtest's **2,641% return was completely fake**, caused by:

1. **Data mismatch** (565 dilution coins vs 172 price coins)
2. **Portfolio construction bug** (selected before checking data availability)
3. **Accidental concentration** (collapsed to 4 positions instead of 20)
4. **Lucky outliers** (ZEC +63% with 100% portfolio weight)

After fixing the bug and properly matching data:
- Portfolio: 10-16 properly diversified positions ?
- Performance: -27.8% total, -6.7% annualized ?
- **Recommendation: ABANDON STRATEGY** ?

The dilution factor does not provide predictive value for cryptocurrency returns in this implementation.

---

**Investigation Status:** ? COMPLETE  
**Bug Status:** ? FIXED  
**Data Matching:** ? COMPLETE  
**Strategy Status:** ? UNPROFITABLE - DO NOT TRADE
