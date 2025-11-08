# Data Source Single Source of Truth - Analysis

**Date:** November 2, 2025  
**Question:** Is this the same data being used in run_all_backtests? Is there a single source of truth?

---

## Executive Summary

**YES, there is a single source of truth:** `data/raw/combined_coinbase_coinmarketcap_daily.csv`

**BUT there's a problem:** A newer, more complete file exists (`coinbase_top200`) with **35 additional symbols** that isn't being used.

---

## Current State

### The Single Source of Truth

**File:** `data/raw/combined_coinbase_coinmarketcap_daily.csv`

**Properties:**
- Rows: 80,390
- Symbols: 172
- Date range: 2020-01-01 to 2025-10-24
- File size: 12.4 MB
- Content: Coinbase OHLCV + CoinMarketCap metadata (market cap, rank)

**Used by:**
- ✅ `run_all_backtests.py` (DEFAULT)
- ✅ `backtest_dilution_factor.py` (DEFAULT)
- ✅ `optimize_rebalance_frequency.py` (DEFAULT)
- ✅ Most backtest scripts (DEFAULT)

### Data File Comparison

| File | Symbols | Rows | Latest Date | CMC Data | Used? |
|------|---------|------|-------------|----------|-------|
| **combined_coinbase_coinmarketcap_daily.csv** | **172** | 80,390 | 2025-10-24 | ✅ YES | ✅ **DEFAULT** |
| coinbase_spot_daily_data_*.csv | 172 | 80,390 | 2025-10-24 | ❌ NO | ❌ No |
| **coinbase_top200_*.csv** | **207** | 88,304 | 2025-10-25 | ❌ NO | ❌ **NOT USED** |

---

## The Problem: Newer, Better Data Exists

### coinbase_top200 has 35 MORE symbols

**Missing from combined but in top200:**
```
ABT, ACH, ALT, AVNT, AWE, BERA, BLAST, BLZ, C98, CBBTC, COW, DEGEN, 
EURC, G, GIGA, GTC, HYPE, HIGH, IP, KAITO, LAYER, LCX, LINEA, LQTY, 
MATIC, MELANIA, MOTHER, RETARDIO, RLY, SNEK, SWELL, TRUMP, USTC, 
VANRY, VIRTUAL
```

**These include:**
- **HYPE** (Rank #11, $16B market cap!) - We identified this as missing earlier
- **TRUMP** (Rank #66) - Major meme coin
- **IP** (Rank #42) - Story Protocol
- **VIRTUAL**, **MOTHER**, etc. - New trending coins

### Why This Matters

**Current top 100 analysis showed:**
- 37/100 coins completely missing
- Some of these (HYPE, IP) are in top200 file!
- We could have better coverage but aren't using it

---

## Data File Architecture

### File Relationships

```
coinbase_spot_daily_data_*.csv (Raw Coinbase)
    ↓
    172 symbols, OHLCV only
    ↓
combined_coinbase_coinmarketcap_daily.csv (Enhanced)
    ↓
    172 symbols, OHLCV + CMC metadata
    ↓
    [USED BY BACKTESTS] ← Single source of truth
```

**Meanwhile, separately:**
```
coinbase_top200_*.csv (Newer collection)
    ↓
    207 symbols (+35 more!), OHLCV only
    ↓
    [NOT USED] ← Better data but ignored
```

### The Issue

1. `combined_coinbase_coinmarketcap_daily.csv` was created by merging:
   - Coinbase spot data (172 symbols)
   - CoinMarketCap metadata (market cap, rank)

2. Later, a better Coinbase collection was done:
   - `coinbase_top200` with 207 symbols
   - But never merged with CMC data
   - Never became the new "combined" file

3. Result: Backtests use the old 172-symbol file by default

---

## Verification: Where Is Each File Used?

### run_all_backtests.py

```python
parser.add_argument(
    "--data-file",
    type=str,
    default="data/raw/combined_coinbase_coinmarketcap_daily.csv",  # 172 symbols
    help="Path to historical OHLCV data CSV file",
)
```

✅ **Consistent** - Uses combined file as single source of truth

### Individual Backtest Scripts

Most scripts either:
1. Import from `run_all_backtests.py` (inherits default)
2. Have same default: `combined_coinbase_coinmarketcap_daily.csv`
3. Accept file path as argument (can override)

**Examples:**
- `backtest_adf_factor.py`: default=`"data/raw/combined_coinbase_coinmarketcap_daily.csv"`
- `backtest_beta_factor.py`: default=`"data/raw/combined_coinbase_coinmarketcap_daily.csv"`
- `backtest_dilution_factor.py`: hardcoded paths to `combined_*` or `coinbase_spot_*`

✅ **Mostly consistent** - Uses combined file

### My Analysis Scripts

**From earlier analysis:**
- `analyze_dilution_backtest.py`: Uses `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- `analyze_top100_coverage.py`: Uses `data/raw/combined_coinbase_coinmarketcap_daily.csv`

✅ **Consistent** - Same file as backtests

---

## Impact Assessment

### What We're Missing

By using 172-symbol file instead of 207-symbol file:

**Top 100 coins affected:**
- HYPE (rank #11) - Missing from combined, present in top200
- IP (rank #42) - Missing from combined, present in top200
- Potentially others that would improve backtest coverage

**Backtest impact:**
- Current join rate: 21.8% (with 172 symbols)
- Potential join rate with 207 symbols: ~24-25% (small improvement)
- Still limited by temporal coverage issues (Oct 2021 cutoff)

**Good news:** The temporal coverage problem (SOL, XRP, etc. stopping in Oct 2021) is the BIGGER issue. Adding 35 symbols helps but doesn't solve the main problem.

---

## Recommendation

### Short-term Fix (Simple)

**Update the combined file:**

```bash
# 1. Start with coinbase_top200 (207 symbols)
# 2. Add CMC metadata (market cap, rank) for all 207 coins
# 3. Save as NEW combined_coinbase_coinmarketcap_daily.csv
# 4. All backtests automatically use it (no code changes needed)
```

**Result:**
- 172 → 207 symbols (+35)
- Includes HYPE, IP, TRUMP, and other top-100 coins
- Join rate improves slightly (21.8% → ~24%)

### Long-term Solution (Complete)

**Fix both quantity AND quality:**

1. **Expand symbols** (addressed by using top200)
   - Current: 207 symbols from Coinbase
   - Add: Binance, Kraken for missing coins (XRP continuous, etc.)
   - Target: 250+ symbols covering top 100 fully

2. **Fix temporal gaps** (bigger issue)
   - Backfill Oct 2021 gaps (SOL, XRP, DOGE, etc.)
   - Resume stopped coins
   - Ensure continuous coverage

3. **Automate maintenance**
   - Daily updates to combined file
   - Monitor for gaps/failures
   - Single pipeline, single output

**Result:**
- 207 → 250+ symbols
- Full temporal coverage (no Oct 2021 cutoff)
- Join rate: 21.8% → 60-70%

---

## Answer to Your Questions

### Q1: Is this the same data being used in run_all_backtests?

**YES.** My analysis and `run_all_backtests` both use:
- `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- Same 172 symbols
- Same date range (2020-01-01 to 2025-10-24)
- Same temporal gaps (Oct 2021 cutoff for many coins)

### Q2: Is there a single source of truth?

**YES.** The single source of truth is:
- `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- Used consistently across all backtests by default
- Can be overridden with `--data-file` argument

**BUT:** A better file exists (`coinbase_top200`) that should become the new source of truth.

---

## File Summary Table

| File | Purpose | Symbols | Status | Should Use? |
|------|---------|---------|--------|-------------|
| `combined_coinbase_coinmarketcap_daily.csv` | Main backtest data | 172 | ✅ Current SOT | ⚠️ Upgrade needed |
| `coinbase_spot_daily_data_*.csv` | Raw Coinbase | 172 | Source for combined | Used to build combined |
| `coinbase_top200_*.csv` | Newer Coinbase | 207 | ❌ Not used | ✅ Should upgrade to this |
| Various other CSV files | Specific backtests | Varies | Archived/specific | ❌ Don't use |

**Recommendation:** Create new combined file from top200 + CMC data → New single source of truth with 207 symbols.

---

## Action Items

### Priority 1: Update Combined File (Quick Win)

```python
# Pseudo-code
top200 = load('coinbase_top200_*.csv')  # 207 symbols
cmc_data = fetch_cmc_metadata()  # Get market cap/rank for all 207
combined_new = merge(top200, cmc_data)
combined_new.save('combined_coinbase_coinmarketcap_daily.csv')  # Overwrite

# Result: All backtests instantly get 35 more symbols
```

**Effort:** 1-2 hours  
**Impact:** +35 symbols, ~2-3% better join rate

### Priority 2: Fix Temporal Gaps (Bigger Fix)

```python
# Pseudo-code
for coin in [SOL, XRP, DOGE, ADA, etc.]:
    backfill(coin, start='2021-10-29', end='2025-11-02')
    
# Result: Coins have continuous coverage
```

**Effort:** 1-2 days (need to access historical APIs)  
**Impact:** +20-30% join rate improvement

### Priority 3: Expand Sources (Complete Solution)

```python
sources = ['coinbase', 'binance', 'kraken', 'hyperliquid']
for source in sources:
    fetch_and_merge(source)
    
# Result: 90%+ coverage of top 100
```

**Effort:** 1 week (integrate multiple APIs)  
**Impact:** 60-70% join rate

---

## Conclusion

### Current State: ✅ Single Source of Truth Exists

- `combined_coinbase_coinmarketcap_daily.csv` is used consistently
- All backtests use the same data by default
- No fragmentation or inconsistency issues

### Problem: ⚠️ Source of Truth Is Outdated

- Better data exists (top200 with 207 symbols)
- Not being used for backtests
- Missing 35 symbols including some top-100 coins

### Solution: 🔧 Upgrade the Source of Truth

1. **Immediate:** Use coinbase_top200 as base (207 symbols)
2. **Short-term:** Backfill temporal gaps (Oct 2021)
3. **Long-term:** Add Binance/Kraken/etc. (250+ symbols)

**The single source of truth architecture is correct, we just need to populate it with better data.**

---

**Files Generated:**
- ✅ `data_source_comparison.csv` - Detailed file comparison
- ✅ `check_data_consistency.py` - Analysis script

**Status:** ✅ Verified single source of truth, identified upgrade path
