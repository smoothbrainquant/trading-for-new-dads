# Price Data Gap Filling - Complete Guide

**Created:** November 3, 2025  
**Purpose:** Systematically fill gaps in combined_coinbase_coinmarketcap_daily.csv

---

## Executive Summary

**Problem Identified:**
- ALL 172 symbols in dataset are stale (not updated to present)
- 93 symbols are 2+ years outdated (stopped Oct 2021)
- Major coins like BTC, ETH only need 10 days
- Major coins like USDT, XRP, DOT need 1400+ days (4 years!)

**Solution:**
- Automated script to backfill from CoinGecko API
- Prioritizes by market cap × staleness
- Can process all 172 symbols systematically

---

## The Scripts

### Version 1: `fill_price_data_gaps.py`
- General gap finder (finds gaps WITHIN date ranges)
- Found: No gaps within ranges (100% coverage for existing periods)
- Limitation: Doesn't prioritize "stale to present" gaps well

### Version 2: `fill_price_data_gaps_v2.py` ⭐ **RECOMMENDED**
- Focuses on "stale data" (coins not updated to present)
- Prioritizes by market cap × staleness
- Better for our use case (extending stopped coins to present)

---

## Quick Start

### 1. Analyze Current State

```bash
cd /workspace
python3 data/scripts/fill_price_data_gaps_v2.py --analyze --top 50
```

**Output:**
- Shows staleness distribution
- Lists top 50 stale coins by priority
- Saves `stale_price_data_analysis.csv`

### 2. Dry Run (No Changes)

```bash
# See what would be filled for top 10 coins
python3 data/scripts/fill_price_data_gaps_v2.py --dry-run --limit 10
```

**Output:**
- Shows exactly what dates would be fetched
- No API calls, no changes to data

### 3. Fill Gaps (Production)

```bash
# Fill top 10 coins (RECOMMENDED FIRST RUN)
python3 data/scripts/fill_price_data_gaps_v2.py --fill --limit 10

# Fill all stale coins (LONG RUNNING - 172 coins!)
python3 data/scripts/fill_price_data_gaps_v2.py --fill
```

**What happens:**
- Fetches missing data from CoinGecko API
- Creates backup: `combined_..._backup_YYYYMMDD_HHMMSS.csv`
- Updates `combined_coinbase_coinmarketcap_daily.csv`
- Respects rate limits (1.5s between calls)

---

## Current Analysis Results

### Overall Stats

- **Total symbols:** 172
- **Current (≤7 days old):** 0 (0.0%)
- **Stale (>7 days old):** 172 (100.0%)

### Staleness Distribution

| Category | Count | Percentage |
|----------|-------|------------|
| 8-30 days | 65 | 37.8% |
| 1-2 years | 14 | 8.1% |
| 2+ years | 93 | 54.1% |

### Top 30 Priority Coins

| # | Symbol | Rank | Market Cap | Last Date | Days Stale | Priority | Days Needed |
|---|--------|------|------------|-----------|------------|----------|-------------|
| 1 | **USDT** | 3 | $21.3B | 2021-10-28 | 1,467 | 213.4 | **1,467** |
| 2 | **BTC** | 1 | $1,947.3B | 2025-10-24 | 10 | 194.7 | **10** |
| 3 | **XRP** | 5 | $10.3B | 2021-01-19 | 1,749 | 102.5 | **1,749** |
| 4 | **DOT** | 6 | $9.0B | 2021-10-28 | 1,467 | 90.0 | **1,467** |
| 5 | **NEAR** | 24 | $8.7B | 2022-10-28 | 1,102 | 86.7 | **1,102** |
| 6 | **ADA** | 8 | $6.4B | 2021-10-28 | 1,467 | 63.8 | **1,467** |
| 7 | **HBAR** | 32 | $5.6B | 2022-10-28 | 1,102 | 56.5 | **1,102** |
| 8 | **SAND** | 35 | $5.5B | 2022-10-28 | 1,102 | 54.5 | **1,102** |
| 9 | **ETH** | 2 | $437.8B | 2025-10-24 | 10 | 43.8 | **10** |
| 10 | **STX** | 54 | $3.1B | 2022-10-28 | 1,102 | 30.9 | **1,102** |

**Key Findings:**
- BTC and ETH only need 10 days (quick wins!)
- USDT, XRP, DOT, ADA need 1400-1700 days (Oct 2021 batch)
- 65 symbols need 8-30 days (recent but not current)

---

## Recommended Approach

### Phase 1: Quick Wins (BTC, ETH, and other "recent" coins)

**Goal:** Update 65 symbols that only need 8-30 days

```bash
# Fill coins needing <100 days (fast)
python3 data/scripts/fill_price_data_gaps_v2.py --fill --limit 70
```

**Time:** ~2 hours (70 coins × 1.5s rate limit + API calls)  
**Impact:** Top coins (BTC, ETH, LINK, XLM, etc.) become current

### Phase 2: October 2021 Batch (Big backfill)

**Goal:** Backfill coins that stopped in Oct 2021

```bash
# Top 10 from Oct 2021 batch
python3 data/scripts/fill_price_data_gaps_v2.py --fill --limit 80
```

**Time:** ~3-4 hours (fetching 1400+ days takes multiple API calls)  
**Impact:** USDT, XRP, DOT, ADA, DOGE become current

### Phase 3: October 2022 Batch

**Goal:** Backfill coins that stopped in Oct 2022

```bash
# Remaining coins
python3 data/scripts/fill_price_data_gaps_v2.py --fill --limit 100
```

**Time:** ~2-3 hours  
**Impact:** NEAR, HBAR, SAND, STX, FLOW become current

### Phase 4: Complete All

**Goal:** Fill all remaining symbols

```bash
# All symbols
python3 data/scripts/fill_price_data_gaps_v2.py --fill
```

**Time:** ~8-10 hours total (172 symbols, many with 1000+ days to fill)  
**Impact:** 100% of dataset current

---

## Expected Results

### Before

- Symbols current: 0/172 (0%)
- Top 10 coverage: 30% current, 70% stale
- Backtest join rate: 21.8%

### After (Phase 1)

- Symbols current: 65/172 (38%)
- Top 10 coverage: 100% current (all top 10 updated!)
- Backtest join rate: ~30-35%

### After (All Phases)

- Symbols current: 172/172 (100%)
- Top 10 coverage: 100% current
- Backtest join rate: ~40-45% (still limited by missing symbols, but all existing ones current)

---

## Important Notes

### Rate Limiting

**CoinGecko Free Tier:**
- 50 calls per minute
- Script uses 1.5 seconds between calls (40 calls/min, safe margin)
- Automatic rate limiting built-in

**For faster processing:**
- Get CoinGecko Pro API key
- Adjust `self.rate_limit` in script
- Pro tier: 500 calls/min

### API Limitations

**Symbols without CoinGecko mapping:**
- Script has ~80 symbol mappings built-in
- If symbol not mapped, shows warning and skips
- Can add more mappings to `_build_symbol_map()`

**Common unmapped symbols:**
- New/niche coins
- Exchange-specific tokens
- Some stablecoins

### Backup Safety

**Every run creates backup:**
- `combined_..._backup_YYYYMMDD_HHMMSS.csv`
- Original data never lost
- Can revert if issues found

### Data Quality

**CoinGecko data:**
- Generally high quality for major coins
- May have slight price differences vs Coinbase
- Volume data available
- OHLC estimated (CoinGecko returns price points, script uses as OHLC)

---

## Troubleshooting

### API Errors

```
✗ API error 429
```
**Solution:** Rate limit hit. Wait 1 minute, rerun.

```
⚠ No CoinGecko mapping for SYMBOL
```
**Solution:** Add mapping to `_build_symbol_map()` or skip coin.

### Script Errors

```
KeyError: 'market_cap'
```
**Solution:** Some rows missing CMC metadata. Script handles gracefully, uses 0.

```
No data returned
```
**Solution:** CoinGecko doesn't have data for that symbol/period. Skip or try alternative source.

### Large Files

**After filling all gaps:**
- Original: 80,390 rows, 12.4 MB
- Expected: ~150,000-200,000 rows, 20-25 MB
- No performance issues (pandas handles fine)

---

## Alternative Data Sources

If CoinGecko fails or has gaps, consider:

1. **Binance API** (for major coins)
   - More complete for coins listed on Binance
   - Free tier: 1200 requests/min
   
2. **Kraken API** (for XRP, etc.)
   - XRP has continuous coverage on Kraken
   - Free, no rate limits (reasonable use)
   
3. **CoinMarketCap API** (we already have some CMC data)
   - Historical data requires Pro plan
   - Can merge with existing CMC metadata

---

## After Filling Gaps

### Re-run Top 100 Analysis

```bash
python3 analyze_top100_coverage.py
```

**Expected improvement:**
- Before: 33% of top 100 current
- After: ~70-80% of top 100 current (limited by symbol coverage, not temporal gaps)

### Re-run Dilution Backtest

```bash
cd backtests/scripts
python3 run_all_backtests.py --run-dilution
```

**Expected improvement:**
- Before: 21.8% join rate (33 coins available)
- After: ~35-40% join rate (50-60 coins available)
- Still limited by missing symbols (need to add top200)

### Update Combined File to Top200

**After fixing temporal gaps, expand symbols:**

```bash
# 1. Merge top200 + CMC metadata
python3 merge_top200_with_cmc.py  # TODO: Create this script

# 2. Fill gaps for NEW symbols
python3 data/scripts/fill_price_data_gaps_v2.py --fill
```

**Final result:**
- 207 symbols (vs 172)
- 100% current temporal coverage
- ~60-70% join rate for backtests

---

## Files Generated

- `stale_price_data_analysis.csv` - Detailed analysis
- `combined_..._backup_*.csv` - Backups (one per run)
- Updated `combined_coinbase_coinmarketcap_daily.csv` - Main data file

---

## Summary Commands

```bash
# Quick reference

# 1. Analyze
python3 data/scripts/fill_price_data_gaps_v2.py --analyze

# 2. Test (dry run)
python3 data/scripts/fill_price_data_gaps_v2.py --dry-run --limit 5

# 3. Fill top 10 (recommended first)
python3 data/scripts/fill_price_data_gaps_v2.py --fill --limit 10

# 4. Fill all (full backfill, 8-10 hours)
python3 data/scripts/fill_price_data_gaps_v2.py --fill
```

---

**Status:** ✅ Scripts ready, analysis complete, ready to fill gaps

**Recommendation:** Start with Phase 1 (limit 70) to update BTC/ETH and other recent coins first. This gives immediate backtest improvement with minimal time investment.
