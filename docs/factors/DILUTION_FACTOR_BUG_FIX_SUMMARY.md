# Dilution Factor Backtest: Critical Bug Fix Summary

**Date:** November 2, 2025  
**Investigation:** Portfolio Construction Bug Analysis

## TL;DR

The dilution factor backtest showing **2,641% returns was completely fake**, caused by a portfolio construction bug that collapsed the strategy to 1-4 concentrated positions instead of the intended 20. After fixing the bug, the strategy **loses money (-27.8% total, -6.7% annualized)**.

## The Bug

### What Was Supposed to Happen
- Long top 10 coins with lowest dilution
- Short top 10 coins with highest dilution  
- 20 total positions with risk parity weighting
- Monthly rebalancing

### What Actually Happened
- Selected 20 coins based on dilution data (565 coin universe)
- Tried to get price data for volatility calculation
- **15/20 coins had NO price data** (only 172 coins in price dataset)
- Fell back to 1-4 positions that happened to have data
- **100% weight in single coin** on some days (e.g., ZEC on Sept 2025)

## The Numbers

```
Data Coverage:
  Dilution data: 565 coins
  Price data:    172 coins
  BOTH:          170 coins (30% coverage)
  
Portfolio Composition (Before Fix):
  Expected: 10 long + 10 short = 20 positions
  Actual:   1-2 long + 2-3 short = 1-5 positions
  Diversification: FAILED (75% of selections dropped)
  
Portfolio Composition (After Fix):
  Actual:   5-8 long + 5-8 short = 10-16 positions  
  Diversification: WORKING
```

## Performance Comparison

| Version | Total Return | Annualized | Sharpe | Positions | Status |
|---------|--------------|------------|--------|-----------|--------|
| **Original (Broken)** | +2,641% | +101.6% | 1.04 | 1-4 | ? BUG |
| **Outlier Filtered (Still Broken)** | +624% | +52.1% | 0.62 | 1-4 | ? BUG |
| **Fixed (Proper Diversification)** | **-27.8%** | **-6.7%** | **-0.17** | 10-16 | ? REAL |

## Root Cause Analysis

### Code Path (Buggy Version)

```python
def construct_risk_parity_portfolio(signals, price_df, rebal_date, top_n=10):
    # Step 1: Filter to top 150 by market cap
    valid_signals = signals.nsmallest(150, 'rank')
    
    # Step 2: Sort by dilution velocity
    valid_signals = valid_signals.sort_values('dilution_velocity')
    
    # Step 3: Select top 10 long + top 10 short
    long_candidates = valid_signals.head(10)    # BNB, ADA, SHIB, FET, OKB, etc.
    short_candidates = valid_signals.tail(10)   # MORPHO, ENA, ETHFI, etc.
    
    # Step 4: Calculate volatility (REQUIRES PRICE DATA!)
    long_candidates['volatility'] = calculate_volatility(...)
    # Problem: Most coins don't have price data!
    
    # Step 5: Filter out coins without volatility
    long_candidates = long_candidates[volatility.notna()]
    # Result: BNB ?, ADA ?, SHIB ?, FET ?, OKB ? ? only ZEC ?
    
    # Final portfolio: 1 long (ZEC) + 3-4 shorts = 4-5 total instead of 20
```

### Code Path (Fixed Version)

```python
def construct_risk_parity_portfolio(signals, price_df, rebal_date, top_n=10):
    # Step 1: Filter to top 150 by market cap
    valid_signals = signals.nsmallest(150, 'rank')
    
    # Step 2: FILTER TO COINS WITH PRICE DATA FIRST!
    available_coins = price_df['base'].unique()  # Only 172 coins
    valid_signals = valid_signals[valid_signals['symbol'].isin(available_coins)]
    
    # Step 3: Pre-calculate volatility for ALL candidates
    valid_signals['volatility'] = calculate_volatility(...)
    valid_signals = valid_signals[volatility.notna()]
    
    # Step 4: NOW select top/bottom from tradeable universe
    adjusted_top_n = min(10, len(valid_signals) // 2)  # Adjust if insufficient
    long_candidates = valid_signals.head(adjusted_top_n)
    short_candidates = valid_signals.tail(adjusted_top_n)
    
    # Final portfolio: 5-8 longs + 5-8 shorts = 10-16 properly diversified
```

## Why Original Results Were So High

### Example: September 2025

**Buggy Portfolio:**
- 1 long: ZEC (100% weight)
- 3 shorts: MORPHO (-37%), ENA (-31%), ETHFI (-32%)

**What Happened:**
- Oct 1, 2025: ZEC had +62.96% single-day return
- Portfolio return: 1.0 ? 62.96% + (-1.0) ? ~8% = **+58.5% in ONE day**
- This one day contributed ~45% of total cumulative returns

**If Properly Diversified:**
- 8 longs: ZEC would be 1/8 ? 62.96% = +7.9% contribution
- 8 shorts: diluted impact
- Portfolio return: ~10-15% instead of 58.5%

### The Math

```
Concentration Impact:
  Buggy:  100% weight ? 63% return = +63% portfolio impact
  Fixed:  12.5% weight ? 63% return = +7.9% portfolio impact
  
  Difference: 8x leverage from accidental concentration
```

## Files Changed

### Fixed Files
- `backtests/scripts/backtest_dilution_factor.py` - Fixed portfolio construction logic

### Key Changes
```python
# Line 220-231: NEW - Filter to coins with price data BEFORE selection
available_coins = price_df['base'].unique()
valid_signals = valid_signals[valid_signals['symbol'].isin(available_coins)]

# Pre-calculate volatility for all candidates
valid_signals['volatility'] = valid_signals['symbol'].apply(
    lambda s: calculate_volatility(price_df, s, rebal_date)
)

# Keep only coins with valid volatility
valid_signals = valid_signals[valid_signals['volatility'].notna()]

# Line 239-244: NEW - Dynamic position sizing based on available coins
adjusted_top_n = min(top_n, len(valid_signals) // 2)
if adjusted_top_n < top_n:
    print(f"  Note: Adjusted to {adjusted_top_n} positions per side")
```

## Lessons Learned

### 1. Always Validate Data Coverage
- Check that all required data sources overlap
- Don't assume universe consistency across datasets
- Add explicit data availability checks before selection

### 2. Fail Fast, Not Silently
- Original code silently dropped 15/20 positions
- Should have raised an error or logged a warning
- Fixed version logs when positions are adjusted

### 3. Test Portfolio Composition
- Monitor actual number of positions over time
- Should have noticed 4 positions instead of 20
- Add assertions: `assert len(portfolio) >= min_positions`

### 4. Beware of Survivorship Bias
- The few coins that survived data filtering weren't random
- They were coins Coinbase/CoinMarketCap both track
- This created selection bias toward larger, more liquid coins

## Recommendation

**DO NOT TRADE THE DILUTION FACTOR STRATEGY**

The strategy loses money (-6.7% annualized) when properly implemented with adequate diversification. The apparent profitability was entirely due to a portfolio construction bug that caused accidental concentration in a few coins that happened to have extreme returns.

The dilution factor does not appear to have predictive value for cryptocurrency returns in this implementation.

---

**Status:** Bug identified and fixed. Strategy performance confirmed to be negative with proper diversification. Strategy should be abandoned.
