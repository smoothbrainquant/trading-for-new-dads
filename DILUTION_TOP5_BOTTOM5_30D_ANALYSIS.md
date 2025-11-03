# Dilution Factor Backtest: Top/Bottom 5 with 30-Day Volatility Analysis

## Summary

**Parameters Tested:**
- **Positions**: Top 5 long (lowest dilution) + Bottom 5 short (highest dilution)
- **Volatility lookback**: 30 days
- **Min data points**: 10 days
- **Rebalance frequency**: 7 days (weekly)

**Critical Finding:** The modified parameters (5+5 positions, 30-day lookback) result in **WORSE coverage** than the original (10+10 positions, 90-day lookback).

---

## Coverage Comparison

| Configuration | Avg Positions | Max Positions | Target | Achievement |
|--------------|---------------|---------------|--------|-------------|
| **Original** (10+10, 90d vol) | 4.3 | 8 | 20 | 21.5% |
| **Modified** (5+5, 30d vol) | 0.8 | 4 | 10 | 8% |

**Result:** Modified parameters are **5.4x worse** in position coverage!

---

## Why 30-Day Volatility Made Things Worse

### The Counter-Intuitive Finding

One would expect shorter lookback windows to **increase** coverage, but the opposite occurred because:

1. **Data Availability is the Primary Issue**
   - Most coins simply don't have ANY data at the rebalance dates
   - Example: BNB listed Oct 22, 2025 (3 days of data)
   - CAKE listed June 12, 2025 (135 days)
   - HNT only has July-Oct 2023 (109 days total)

2. **The 30-Day Window Catches Fewer Coins**
   - When calculating volatility on Jan 1, 2023:
     - Need data from Dec 2, 2022 to Jan 1, 2023
     - IMX and SNX had continuous data → Got 31 points → **Vol calculated**
     - CAKE, BNB, HNT, HBAR had **0 points** → Vol = NaN → **Filtered out**

3. **The Problem Isn't the Lookback - It's Listing Dates**
   - 90-day lookback: Coins need to be listed by Oct 2022 for Jan 2023 rebalance
   - 30-day lookback: Coins need to be listed by Dec 2022 for Jan 2023 rebalance
   - But if coin not listed until 2024, **both fail equally**

### Detailed Position Coverage by Year

#### Modified (5+5, 30d):
```
2021: 1.5 positions (0.5 long, 0.9 short)
2022: 1.4 positions (0.7 long, 0.8 short)  
2023: 0.7 positions (0.2 long, 0.4 short) ← Getting worse
2024: 0.2 positions (0.1 long, 0.1 short) ← Nearly empty
2025: 0.4 positions (0.2 long, 0.2 short)
```

#### Original (10+10, 90d):
```
2021: 5.8 positions (1.9 long, 3.9 short)
2022: 4.1 positions (1.5 long, 2.6 short)
2023: 3.2 positions (0.8 long, 2.3 short)
2024: 3.7 positions (0.9 long, 2.8 short)
2025: 4.8 positions (2.2 long, 2.6 short)
```

**Original parameters are 5.4x better on average**

---

## Root Cause: Temporal Misalignment

### The Core Problem

The dilution data (from CoinMarketCap) goes back to 2021, but Hyperliquid price data has severe temporal gaps:

**Coin Listings by Year:**
- 2020: 27 coins
- 2021: 45 coins  
- 2022: 36 coins
- 2023: 19 coins
- 2024: 24 coins
- 2025: 21 coins

**Many "top" coins by CMC rank weren't listed on Hyperliquid until recently:**

| Coin | CMC Rank | Hyperliquid Listing | Data Points |
|------|----------|-------------------|-------------|
| BNB | 5 | Oct 22, 2025 | 3 days |
| CAKE | 61 | June 12, 2025 | 135 days |
| HNT | 107 | July 12, 2023 | 109 days |
| HBAR | 37 | Oct 13, 2022 | 16 days |
| QNT | 31 | June 24, 2021 | 127 days |
| RSR | 151 | April 22, 2025 | 186 days |

**Only 85 coins out of 496** in dilution data have good coverage (>200 price days, >5 dilution signals).

---

## Coverage Breakdown

### Stage 1: Dilution Signal Calculation
- **Input**: 200 coins per monthly snapshot
- **Output**: ~41-58 coins with valid dilution velocity
- **Attrition**: 70-80% filtered (missing circulating supply data)

### Stage 2: Rank Filtering
- Top 150 by market cap rank
- **Output**: Same ~41-58 coins (all within top 150)

### Stage 3: Price Data Availability
- For coins selected in top 5 / bottom 5:
  - Some don't exist in Hyperliquid at all (GT, OKB, FTT)
  - Others exist but weren't listed at rebalance date
- **Loss**: 40-80% of candidates

### Stage 4: Volatility Calculation  
- Requires minimum data points within lookback window
- **30-day lookback**: Requires 10+ days in past 30 days
- **90-day lookback**: Requires 20+ days in past 90 days

**Result**: Only 0-4 coins pass all filters (avg 0.8)

---

## Why Original Parameters Work Better

The **90-day lookback with 20-point minimum** works better because:

1. **Longer window = More chances to catch data**
   - If coin has sporadic data (listed mid-period, delisted, relisted), 90 days more likely to capture 20 points
   - 30-day window too narrow for coins with gaps

2. **Quality over Quantity**
   - The 90-day / 20-point filter ensures coins have sustained trading
   - Filters out newly listed coins with insufficient history
   - 30-day / 10-point allows coins with very short/unstable history

3. **Top 10+10 Casting Wider Net**
   - With only 40-50 coins having dilution signals, top 10+10 more likely to find matches
   - Top 5+5 is too selective given the already-limited pool

---

## Backtest Results Comparison

### Modified Parameters (5+5, 30d):
```
Total Return:     -91.45%
Annualized:       -77.28%
Sharpe Ratio:     -0.661
Max Drawdown:     -97.14%
Win Rate:         48.43%
Days:             606
```
**Status:** FAILED - Negative returns, catastrophic drawdown

### Original Parameters (10+10, 90d):
```
Total Return:     +1,809%
Annualized:       +203.60%
Sharpe Ratio:     1.034
Max Drawdown:     -89.24%
Win Rate:         50.94%
Days:             1,605
```
**Status:** Strong returns but severe under-diversification (avg 4.3 positions vs target 20)

---

## Recommendations

### ❌ Do NOT Use Modified Parameters (5+5, 30d)

Reasons:
1. **Worse coverage**: 0.8 vs 4.3 average positions
2. **Negative returns**: -91% vs +1,809%
3. **More days with 0 positions**: 21 days vs fewer with original
4. **Strategy breaks down completely** in 2024-2025

### ⚠️ Original Parameters Have Issues Too

The +1,809% return from original (10+10, 90d) is **not reliable** because:
- Only 4.3 positions instead of 20
- Extreme concentration risk (23% per position vs 5% intended)
- Returns likely from lucky picks, not diversified factor exposure
- Max drawdown -89% reflects concentration

### ✅ Recommended Approaches

#### Option 1: Accept Current Reality
- **Keep**: 10+10 positions, 90-day volatility
- **Acknowledge**: Will only get ~4 positions on average
- **Size accordingly**: 20-25% per position (concentrated portfolio)
- **Implications**:
  - This is a concentrated bet strategy, not diversified factor
  - Higher risk / higher return profile
  - Requires strong conviction and risk management
  - Use smaller allocation (5-10% of total portfolio)

#### Option 2: Fix the Data (Recommended)
-**Expand price data sources**:
  - Add other exchanges beyond Hyperliquid
  - Include Binance, Coinbase, FTX historical
  - This will bring in coins like BNB, CAKE, etc much earlier
- **Improve dilution data coverage**:
  - Use blockchain explorers for circulating supply
  - Add more coins (target 150+ with dilution data)
- **Expected outcome**: Achieve 15-20 positions regularly

#### Option 3: Adjust Strategy Design
- **Relax rank filter**: Instead of top 150, use top 500
- **Use flexible position count**: Accept 5-15 positions dynamically
- **Adjust weights**: Equal weight instead of risk parity (simpler with few positions)
- **Add fallback logic**: If <8 positions, skip rebalance

---

## Data Availability Table

### Coins with Good Coverage (85 total)

Available in both dilution and price data with >200 days and >5 signals:

```
1INCH, AAVE, ADA, AERO, AIOZ, AKT, ALGO, ALICE, ANKR, APE, 
API3, ARB, ARKM, ATH, ATOM, AUDIO, AXL, BCH, BICO, BLUR, 
BNT, BONK, BTC, CRO, CRV, CVC, DASH, DIA, EGLD, ENS, 
EOS, ETC, ETH, ETHFI, FIL, FLOKI, GIGA, GLM, GRT, IMX, 
JTO, KAVA, KNC, LDO, LINK, LTC, MAGIC, MINA, MOG, MORPHO, 
NKN, OGN, ONDO, OXT, PENDLE, PENGU, PEPE, PNUT, POLS, POPCAT, 
POWR, PRIME, PYR, PYTH, RENDER, RPL, SKL, SNX, STORJ, STRK, 
STX, SUPER, SUSHI, T, TAO, TIA, TRAC, TURBO, WIF, XLM, 
XRP, XTZ, ZEC, ZETA, ZRX
```

**These 85 coins should be the focus** of any dilution strategy until data coverage improves.

---

## Conclusion

**The user's request to use "top/bottom 5 with 30d volatility" makes the strategy significantly worse:**

| Metric | Original (10/10, 90d) | Modified (5/5, 30d) | Change |
|--------|----------------------|-------------------|--------|
| Avg Positions | 4.3 | 0.8 | **-81%** ⚠️ |
| Total Return | +1,809% | -91% | **-2,100%** ⚠️ |
| Sharpe Ratio | 1.034 | -0.661 | **-164%** ⚠️ |
| Max Drawdown | -89% | -97% | **-9%** ⚠️ |

**Recommendation**: **Revert to original parameters** (10+10, 90d) and instead focus on:
1. Improving data coverage by adding more exchanges
2. Accepting the 4-5 position reality and sizing accordingly
3. Treating this as a concentrated strategy, not diversified factor

**The core issue is data availability, not parameter tuning.** No amount of parameter adjustment will fix temporal misalignment between dilution data (2021+) and Hyperliquid listings (mostly 2024-2025).
