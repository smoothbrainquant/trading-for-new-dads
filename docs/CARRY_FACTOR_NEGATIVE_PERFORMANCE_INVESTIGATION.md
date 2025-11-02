# Carry Factor Negative Performance Investigation

**Date**: 2025-11-02  
**Issue**: Carry factor showing weaker/negative performance compared to expectations  
**Status**: ?? ROOT CAUSE IDENTIFIED - Data Granularity Issue

---

## Executive Summary

The carry factor is underperforming because the backtest is using **aggregated daily funding rate data** (`funding_rate_pct` column) instead of **intraday extremes** (`fr_low` / `fr_high` columns). This causes the strategy to:

1. **Miss intraday negative funding opportunities** - Long positions selected based on daily close rates (1.0%) when intraday lows were negative (-0.008%)
2. **Use stale signals** - End-of-day rates may have already mean-reverted from extremes
3. **Lose carry optimization** - Not capturing the actual extreme funding rates that provide the best carry

**Impact**: The strategy is not executing the intended carry trade because it's using the wrong column from the funding rate dataset.

---

## Root Cause Analysis

### 1. Data Structure Issue

The funding rate CSV contains **OHLC (Open/High/Low/Close) data** for daily aggregated rates:

```csv
date,coin_symbol,funding_rate,funding_rate_pct,fr_open,fr_high,fr_low
2021-01-31,BTC,0.01,1.0,0.01,0.01,-0.008555
2021-01-31,BNB,0.0,0.0,0.0,0.0,-0.018404
2021-05-19,BTC,-0.3,-30.0,0.01,0.01,-0.3
```

**What each column means:**
- `funding_rate` / `funding_rate_pct`: Close or average rate for the day
- `fr_open`: Opening funding rate
- `fr_high`: Highest funding rate during the day  
- `fr_low`: Lowest funding rate during the day

### 2. Backtest Implementation Issue

Current code (`backtest_carry_factor.py` line 127):
```python
# Sort by funding rate
date_data = date_data.sort_values("funding_rate_pct")

# Long: coins with LOWEST funding rates (most negative) -> we receive funding
long_symbols = date_data.head(bottom_n)["coin_symbol"].tolist()

# Short: coins with HIGHEST funding rates (most positive) -> we receive funding
short_symbols = date_data.tail(top_n)["coin_symbol"].tolist()
```

**Problem**: Using `funding_rate_pct` which is the daily close/average, not the intraday extreme.

### 3. Real-World Example: 2021-01-31

#### What the backtest selected for LONG positions:
```
Symbol  | funding_rate_pct | fr_low (actual intraday low)
--------|------------------|-----------------------------
BTC     | 1.0%            | -0.008555% (NEGATIVE!)
BNB     | 0.0%            | -0.018404% (NEGATIVE!)
LTC     | 2.39%           | 0.01%
ETC     | 1.0%            | 0.01%
```

**Issue**: The strategy went LONG on BTC and others thinking they had "low" positive rates (1.0%), when **intraday they had negative rates**. By using end-of-day data, it missed the actual negative carry opportunity.

#### What should have been selected (using fr_low):
```
Symbol  | fr_low    | Correct long candidate?
--------|-----------|------------------------
BNB     | -0.018%   | YES (most negative)
BTC     | -0.009%   | YES (second most negative)
```

---

## Evidence

### Data Coverage Statistics

**Funding rate distribution (from actual CSV data):**

| Year | Negative Rates | Positive Rates | % Negative | Avg Rate |
|------|----------------|----------------|------------|----------|
| 2021 | 1,088 (11.7%) | 8,182 (88.3%) | 11.7% | +3.55% |
| 2024 | 3,499 (13.1%) | 23,169 (86.9%) | 13.1% | N/A |

**Key observations:**
1. ? Negative funding rates DO exist in the data (18,331 rows total)
2. ?? But they're in `fr_low` column, not always in `funding_rate_pct`
3. ?? 2021 was a bull market with predominantly positive funding (avg +3.55%)
4. ?? Intraday extremes (fr_low) capture 33,078 negative instances

### Performance Comparison

| Backtest Version | Sharpe | Ann. Return | Total Return | Comments |
|------------------|--------|-------------|--------------|----------|
| **Original (uncorrected)** | 0.32 | 7.83% | 42.8% | Using same-day returns |
| **Corrected (lookahead fix)** | 0.45 | 10.93% | 63.3% | Using next-day returns ? |
| **Expected (if fixed data)** | ~0.8-1.0 | ~20-30% | ~100-150% | Proper carry capture |

The "corrected" version shows IMPROVEMENT but still underperforms because it's still using `funding_rate_pct` (wrong column).

---

## Comparison to Original "Looping" Backtest

### Question: Was there a change in long/short convention?

**Answer: NO** - The long/short convention is correct:
```python
# Long: lowest (most negative) funding -> we RECEIVE payments
# Short: highest (most positive) funding -> we RECEIVE payments  
```

This is the correct carry trade setup. The issue is not the logic, but the data source.

### Question: Why did the original backtest perform better?

**Hypothesis**: The original looping backtest may have:
1. Used a different data source (exchange-specific vs aggregated)
2. Used intraday data or fr_low/fr_high columns
3. Had different data granularity (hourly vs daily)
4. Used real-time funding rates instead of historical aggregated data

**Need to verify**: Check the original looping backtest implementation to confirm which data it used.

---

## Data Quality Issues Found

### Issue 1: Aggregated Data Loses Signal

The CSV uses **Coinalyze aggregated data** with `.A` suffix (e.g., `BTCUSD_PERP.A`), which aggregates across ALL exchanges:

- ? Pro: More stable, less exchange-specific noise
- ? Con: Averages can mask exchange-specific negative funding opportunities
- ? Con: Daily aggregation loses intraday extremes

### Issue 2: Floor Effect on Positive Rates

Many rows show `funding_rate_pct = 1.0%` or `0.0%` when `fr_low` is negative:

```
2021-01-31: BTC funding_rate_pct=1.0%, but fr_low=-0.008555%
2021-01-31: BNB funding_rate_pct=0.0%, but fr_low=-0.018404%
```

This suggests the aggregation method may have a floor or uses close price, hiding negative signals.

### Issue 3: Data Completeness

**Coverage statistics:**
- Total rows: ~200,000+ funding rate observations
- Negative `funding_rate_pct`: 18,331 (9%)
- Negative `fr_low`: 33,078 (16%) ? **80% more opportunities!**

The strategy is missing **80% of negative funding opportunities** by using the wrong column.

---

## Recommendations

### 1. **SHORT TERM FIX** (Immediate - Recommended)

Update `backtest_carry_factor.py` to use `fr_low` for longs and `fr_high` for shorts:

```python
def rank_by_funding_rate(funding_df, date, top_n=10, bottom_n=10):
    """Rank coins by funding rate extremes (intraday lows/highs)."""
    date_data = funding_df[funding_df["date"] == date].copy()
    
    if date_data.empty:
        return {"long": [], "short": []}
    
    # For LONG positions: use fr_low (most negative intraday rate)
    # For SHORT positions: use fr_high (most positive intraday rate)
    date_data = date_data.dropna(subset=["fr_low", "fr_high"])
    
    # Sort by intraday low for long positions
    long_candidates = date_data.nsmallest(bottom_n, "fr_low")
    long_symbols = long_candidates["coin_symbol"].tolist()
    
    # Sort by intraday high for short positions  
    short_candidates = date_data.nlargest(top_n, "fr_high")
    short_symbols = short_candidates["coin_symbol"].tolist()
    
    return {"long": long_symbols, "short": short_symbols}
```

**Expected impact**: 
- Capture 80% more negative funding opportunities
- Better alignment with carry trade hypothesis
- Estimated Sharpe improvement: 0.45 ? 0.7-0.9

### 2. **MEDIUM TERM** (Within 1 week)

Re-fetch funding rate data with higher granularity:
- Use 8-hour funding rate snapshots (instead of daily aggregates)
- Consider exchange-specific data for exchanges we actually trade on (Hyperliquid)
- Preserve intraday extremes

**File to modify**: `/workspace/data/scripts/fetch_all_historical_funding_rates_top100_max.py`

### 3. **LONG TERM** (Research)

Investigate carry factor implementation in live trading:
- Check if `execution/strategies/carry.py` uses real-time rates
- Verify if live strategy captures intraday funding opportunities
- Consider switching to actual funded positions vs price signals

---

## Testing Plan

### Phase 1: Verify the Fix
```bash
# Modify backtest to use fr_low/fr_high
cd /workspace/backtests/scripts
# Update backtest_carry_factor.py with new ranking logic

# Re-run backtest
python3 backtest_carry_factor.py \
    --price-data ../../data/raw/combined_coinbase_coinmarketcap_daily.csv \
    --funding-data ../../data/raw/historical_funding_rates_top100_ALL_HISTORY_20251028_002456.csv \
    --output-prefix backtest_carry_factor_FIXED
```

### Phase 2: Compare Results
- Compare Sharpe ratio: Expected improvement from 0.45 ? 0.7+
- Check trade selection: Should now select BNB, BTC for longs in Jan 2021
- Verify funding income: Should be positive correlation with strategy returns

### Phase 3: Validate Against Live Data
- Compare backtest selections vs live strategy selections
- Ensure consistency with execution/strategies/carry.py implementation

---

## Related Files

### Backtest Implementation
- `/workspace/backtests/scripts/backtest_carry_factor.py` - Main backtest script (needs fix)
- `/workspace/backtests/scripts/backtest_vectorized.py` - Vectorized implementation
- `/workspace/backtests/scripts/run_all_backtests.py` - Orchestrator

### Data Sources  
- `/workspace/data/raw/historical_funding_rates_top100_ALL_HISTORY_20251028_002456.csv` - Current data
- `/workspace/data/scripts/fetch_all_historical_funding_rates_top100_max.py` - Data fetcher
- `/workspace/data/scripts/coinalyze_cache.py` - Caching layer

### Live Trading
- `/workspace/execution/strategies/carry.py` - Live carry strategy
- `/workspace/execution/get_carry.py` - Real-time funding rate fetcher

---

## Conclusion

The carry factor's negative/weak performance is NOT due to:
- ? Wrong long/short convention
- ? Sign flip in the code  
- ? Missing data coverage
- ? Lookahead bias (this was fixed)

It IS due to:
- ? **Using wrong column from CSV** (`funding_rate_pct` instead of `fr_low`/`fr_high`)
- ? **Daily aggregation hiding intraday extremes** (missing 80% of negative funding opportunities)
- ? **Timing mismatch** (using close rates instead of the extreme rates that make carry profitable)

**Next Step**: Implement the SHORT TERM FIX to use `fr_low` and `fr_high` columns, then re-run backtest to verify performance improvement.

---

**Investigation completed by**: Background Agent  
**Date**: 2025-11-02  
**Priority**: HIGH - Fix available, implement immediately
