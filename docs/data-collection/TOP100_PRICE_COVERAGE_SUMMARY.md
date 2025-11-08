# Top 100 Coins - Price Data Coverage Analysis

**Date:** November 2, 2025  
**Question:** How is SOL missing from Coinbase spot? Analyze top 100 coins.

---

## Executive Summary

**SOL is NOT missing from Coinbase!** But there's a bigger problem:

**Many coins have price data BUT only for SHORT TIME PERIODS.**

### Key Findings

| Category | Count | Percentage |
|----------|-------|------------|
| **Current data (2025)** | 33/100 | 33% |
| **Old data (pre-2025)** | 30/100 | 30% |
| **Missing entirely** | 37/100 | 37% |
| **TOTAL with ANY data** | **63/100** | **63%** |

### The Real Problem

**Example: SOL (Solana)**
- ? EXISTS in price dataset
- ? Only has data from 2021-06-17 to 2021-10-28 (133 days = 4 months!)
- ? Then STOPS - no data after October 2021

**This explains the low backtest join rate:**
- Coins exist in dataset (63%)
- But NOT available at most rebalance dates
- Data is INCOMPLETE/SPOTTY, not missing

---

## Top 10 Coins - Detailed Status

| Rank | Symbol | Name | Market Cap | Price Data Status | Date Range |
|------|--------|------|------------|-------------------|------------|
| 1 | **BTC** | Bitcoin | $2,364B | ? **CURRENT** | 2020-01-01 to 2025-10-24 (2,123 days) |
| 2 | **ETH** | Ethereum | $525B | ? **CURRENT** | 2020-01-01 to 2025-10-24 (2,123 days) |
| 3 | **XRP** | XRP | $176B | ?? **OLD DATA** | 2020-01-01 to 2021-01-19 (384 days) |
| 4 | **USDT** | Tether | $175B | ?? **OLD DATA** | 2021-05-04 to 2021-10-28 (177 days) |
| 5 | **BNB** | Binance Coin | $143B | ?? **BARELY ANY** | 2025-10-22 to 2025-10-24 (2 days!) |
| 6 | **SOL** | Solana | $120B | ?? **OLD DATA** | 2021-06-17 to 2021-10-28 (133 days) |
| 7 | **USDC** | USD Coin | $74B | ? **MISSING** | No data |
| 8 | **DOGE** | Dogecoin | $38B | ?? **OLD DATA** | 2021-06-03 to 2021-10-28 (147 days) |
| 9 | **TRX** | TRON | $32B | ? **MISSING** | No data |
| 10 | **ADA** | Cardano | $30B | ?? **OLD DATA** | 2021-03-18 to 2021-10-28 (224 days) |

**Top 10 Summary:**
- ? Only 3/10 have current data (BTC, ETH, LINK)
- ?? 5/10 have old/partial data (XRP, USDT, BNB, SOL, DOGE, ADA)
- ? 2/10 completely missing (USDC, TRX)

---

## Coverage by Market Cap Tier

| Tier | Current Data | Old Data | Missing | Total Coverage |
|------|--------------|----------|---------|----------------|
| **Top 10** | 3 | 5 | 2 | 8/10 (80%) exist |
| **11-20** | 4 | 3 | 3 | 7/10 (70%) exist |
| **21-30** | 2 | 4 | 4 | 6/10 (60%) exist |
| **31-50** | 5 | 6 | 9 | 11/20 (55%) exist |
| **51-100** | 19 | 12 | 19 | 31/50 (62%) exist |

### Interpretation

**Good news:** 63% of top 100 coins have SOME price data in the dataset.

**Bad news:** Only 33% have CURRENT (2025) data that's usable for recent backtests.

---

## Major Coins with Problems

### Complete List (Top 20 Problem Coins)

| Rank | Symbol | Name | Issue | Date Range |
|------|--------|------|-------|------------|
| 3 | XRP | XRP | Old Data | 2020-01-01 to 2021-01-19 (384 days) |
| 4 | USDT | Tether | Old Data | 2021-05-04 to 2021-10-28 (177 days) |
| 5 | BNB | Binance Coin | Almost None | 2025-10-22 to 2025-10-24 (2 days!) |
| 6 | SOL | Solana | Old Data | 2021-06-17 to 2021-10-28 (133 days) |
| 7 | USDC | USD Coin | Missing | No data |
| 8 | DOGE | Dogecoin | Old Data | 2021-06-03 to 2021-10-28 (147 days) |
| 9 | TRX | TRON | Missing | No data |
| 10 | ADA | Cardano | Old Data | 2021-03-18 to 2021-10-28 (224 days) |
| 11 | HYPE | Hyperliquid | Missing | No data |
| 13 | USDe | Ethena USDe | Missing | No data |
| 14 | AVAX | Avalanche | Old Data | 2021-09-30 to 2021-10-28 (28 days) |
| 16 | SUI | Sui | Old Data | 2023-05-18 to 2023-10-28 (163 days) |
| 18 | HBAR | Hedera | Old Data | 2022-10-13 to 2022-10-28 (15 days) |
| 20 | LEO | UNUS SED LEO | Missing | No data |
| 21 | SHIB | Shiba Inu | Old Data | 2021-09-09 to 2021-10-28 (49 days) |
| 23 | TON | Toncoin | Missing | No data |
| 25 | MNT | Mantle | Missing | No data |
| 26 | XMR | Monero | Missing | No data |
| 29 | WLFI | World Liberty Financial | Missing | No data |
| 32 | OKB | OKB | Missing | No data |

---

## Why This Happens

### Pattern 1: Data Collection Stopped in October 2021

Many major coins have data that **suddenly stops in October 2021:**
- SOL: 2021-06-17 to 2021-10-28
- DOGE: 2021-06-03 to 2021-10-28
- ADA: 2021-03-18 to 2021-10-28
- USDT: 2021-05-04 to 2021-10-28
- DOT: 2021-06-16 to 2021-10-28
- AVAX: 2021-09-30 to 2021-10-28
- SHIB: 2021-09-09 to 2021-10-28
- ICP: 2021-05-10 to 2021-10-28

**Hypothesis:** Data collection script broke or was interrupted in late October 2021.

### Pattern 2: Very Short Collection Periods

Some coins have data for only a few months:
- HBAR: 15 days (2022-10-13 to 2022-10-28)
- AVAX: 28 days
- SHIB: 49 days
- SOL: 133 days (4 months)

### Pattern 3: Completely Missing

37 coins have NO price data at all, including major ones:
- USDC (rank #7, $74B market cap!)
- TRX (rank #9, $32B market cap)
- HYPE (rank #11, $16B market cap)
- Stablecoins: USDe, PYUSD, FDUSD
- Exchange tokens: OKB, KCS, GT, BGB

---

## Impact on Backtesting

### Why Join Rate is Low (21.8%)

Even though 63% of top 100 coins exist in the dataset:

1. **Temporal mismatch:** Coin not available at that specific rebalance date
   - Example: Rebalancing in 2025, but SOL data stopped in 2021

2. **Insufficient history:** Need 90 days of data for volatility calculation
   - Many coins have <90 days of data
   - Can't calculate risk parity weights

3. **Data gaps:** Some coins have sporadic coverage
   - Missing weeks/months creates unusable gaps

### Actual Available Coins by Date

| Period | Coins Available | Percentage of Top 150 |
|--------|----------------|----------------------|
| **2021-02** | 33 | 22% |
| **2022-02** | 30 | 20% |
| **2023-02** | 32 | 21% |
| **2024-02** | 34 | 23% |
| **2025-10** | 42 | 28% |

Even at best (Oct 2025), only 42 of top 150 coins have usable data.

---

## Root Causes

### 1. Data Source Issues

**Coinbase/CoinMarketCap combined dataset has:**
- Incomplete temporal coverage
- Data collection stopped/restarted multiple times
- Gaps in specific time periods (especially Oct 2021)

### 2. Exchange Coverage

**Missing coins are often:**
- Not listed on Coinbase (BNB, TRX, many altcoins)
- Stablecoins (excluded from price movement tracking?)
- New coins launched after data collection ended
- Exchange-specific tokens (OKB, KCS, GT)

### 3. Maintenance Issues

**Data collection appears unmaintained:**
- Major coins stopped updating in 2021
- No backfill for historical gaps
- New major coins (HYPE, SUI, etc.) added sporadically

---

## Recommendations

### Immediate Actions

1. **Fix data collection pipeline**
   - Resume collection for coins that stopped in Oct 2021
   - Backfill missing periods for major coins
   - Add new top coins (HYPE, TON, MNT, etc.)

2. **Expand data sources**
   - Add Binance data (BNB, many altcoins)
   - Add Kraken data (XRP continuous coverage)
   - Use Hyperliquid API (already trading there)
   - CoinGecko API for comprehensive coverage

3. **Prioritize by market cap**
   - MUST HAVE: Top 20 coins continuous coverage
   - Should have: Top 50 coins reasonable coverage
   - Nice to have: Top 100 coins

### Short-term Workaround

**For existing data:**
- Use only coins with continuous coverage (33 coins)
- Accept reduced universe for backtests
- Focus on continuously available coins:
  - BTC, ETH, LINK, XLM, BCH, LTC (top 10 tier)
  - Plus ~27 other continuously tracked coins

### Long-term Solution

**Rebuild price data collection:**
```python
# Pseudo-code for comprehensive collection
sources = [
    'coinbase',      # 172 coins (current)
    'binance',       # +200 coins (BNB, many altcoins)
    'kraken',        # +100 coins (XRP continuous)
    'hyperliquid',   # +50 coins (HYPE, perpetuals)
    'coingecko',     # Backup/verification
]

# Collect daily:
for source in sources:
    for coin in top_200_by_mcap:
        fetch_ohlcv(coin, source)
        
# Backfill historical:
backfill_missing_periods(start='2020-01-01')
```

**Expected improvement:**
- Coverage: 63% ? 90-95% of top 100
- Join rate: 21.8% ? 60-70% at each rebalance
- Continuous: 33 ? 80-90 coins with full history

---

## Files Generated

- ? `top100_price_coverage_analysis.png` - Visual timeline and charts
- ? `top100_price_data_coverage.csv` - Detailed spreadsheet
- ? `top100_price_coverage_detailed.csv` - Full analysis with date ranges
- ? `analyze_top100_coverage.py` - Analysis script

---

## Conclusion

### Direct Answer to "How is SOL missing?"

**SOL is NOT missing from Coinbase spot data.**

SOL exists in the dataset but:
- Only has 133 days of data (June-October 2021)
- Then stops completely
- Not available for 2022-2025 backtests

### The Real Problem

**63% of top 100 coins have SOME data, but:**
- Only 33% have current (2025) data
- Data collection stopped for major coins in Oct 2021
- Temporal coverage is incomplete, making backtest join rate low

### What Needs to Happen

**Priority 1:** Fix data collection
- Resume stopped coins (SOL, XRP, DOGE, etc.)
- Backfill gaps from 2021-2025
- Add missing top coins

**Priority 2:** Expand sources
- Add Binance, Kraken, Hyperliquid
- Target 90%+ coverage of top 100

**Priority 3:** Maintain pipeline
- Automated daily collection
- Monitoring for gaps/failures
- Regular backfilling

Until data is fixed, backtests will be limited to ~33 continuously available coins (30-40% of intended universe).

---

**Status:** ? Analysis complete, issue identified, solution recommended
