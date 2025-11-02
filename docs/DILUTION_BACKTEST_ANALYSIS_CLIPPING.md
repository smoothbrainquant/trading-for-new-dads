# Dilution Factor Backtest - Data Joining Analysis & Clipping Results

**Date:** 2025-11-02  
**Analysis Type:** Data Quality Review & Return Clipping Comparison  
**Backtest Period:** 2021-02-01 to 2025-10-24 (1,605 days)

---

## ?? CRITICAL WARNING

**This analysis contains BUGGY code that produces fake positive returns.**

The portfolio construction bug causes accidental concentration (6 positions instead of 20), which artificially inflates returns. A bug-fixed version of the dilution factor strategy already exists and shows the **real performance is -28% total return** (loses money).

**Key Takeaways:**
1. ? **Data joining analysis is valid** - shows 21.8% coverage issue
2. ? **Return/clipping analysis is INVALID** - based on buggy concentrated portfolio
3. ? **Bug has been fixed** - see `/workspace/DILUTION_FACTOR_BUG_FIX_SUMMARY.md`
4. ? **Strategy is not viable** - loses money when properly implemented

**Read Section 10 (Conclusion) first for the corrected findings.**

---

## Executive Summary

The dilution factor backtest reveals **significant data joining issues** that severely limit the strategy's coverage:
- Only **21.8%** of top 150 coins by market cap have matching price data
- **395 out of 565** coins in dilution data have no price data
- Major coins like USDT, BNB, XRP, SOL, USDC are consistently missing from price dataset

**Impact of 1-99% Percentile Clipping:**
- Reduces extreme outlier returns (clipped 2% of all returns)
- Decreases volatility by 16% (97.2% ? 81.2%)
- Reduces Sharpe ratio by 0.45 (0.98 ? 0.53)
- Significantly dampens total returns (1809% ? 387%)

---

## 1. Data Joining Issues

### Symbol Coverage Analysis

| Category | Count | Percentage |
|----------|-------|------------|
| **Price data symbols** | 172 | 100% |
| **Dilution data symbols** | 565 | 100% |
| **Common symbols** | 170 | 30.1% of dilution |
| **Price only** | 2 | 1.2% |
| **Dilution only (MISSING)** | 395 | 69.9% |

### Critical Issue: Low Join Rate

**Average join rate: 21.8%**  
- Min: 13.3% (March 2021, February 2022)
- Max: 30.7%

This means that **at each rebalance date, only ~33 out of 150 top coins** have both dilution signals AND price data.

### Missing Major Coins

The following major coins consistently appear in dilution signals but lack price data:
- **USDT** (Tether) - Top 3 by market cap
- **BNB** (Binance Coin) - Top 5 by market cap  
- **XRP** (Ripple) - Top 10 by market cap
- **SOL** (Solana) - Top 10 by market cap
- **USDC** (USD Coin) - Top 10 by market cap
- **DOT** (Polkadot)
- **UNI** (Uniswap)
- **THETA**, **AVAX**, and others

### Join Rate Over Time

| Period | Avg Join Rate |
|--------|---------------|
| 2021 | 22.8% |
| 2022 | 19.7% |
| 2023 | 21.3% |
| 2024 | 22.5% |
| 2025 | 26.0% |

**Observation:** Join rates have improved slightly in 2025 but remain below 30%.

---

## 2. Return Clipping Analysis

### Clipping Thresholds (1-99% Percentiles)

```
Lower bound (1%):  -14.68% (clips extreme losses)
Upper bound (99%):  18.66% (clips extreme gains)
```

**Clipped returns:** 1,606 out of 80,296 (2.0%)

### Distribution Impact

The clipping removes:
- **Tail risk events:** Returns < -14.68% (extreme crashes)
- **Moonshot events:** Returns > 18.66% (explosive gains)

These extreme events, while rare, have **outsized impact** on cumulative performance.

---

## 3. Performance Comparison: No Clipping vs 1-99% Clipped

### Core Metrics

| Metric | No Clipping | 1-99% Clipped | Difference |
|--------|-------------|---------------|------------|
| **Total Return** | 1,809.03% | 387.28% | **-1,421.76%** |
| **Annualized Return** | 95.65% | 43.39% | **-52.26%** |
| **Volatility** | 97.19% | 81.24% | **-15.95%** |
| **Sharpe Ratio** | 0.984 | 0.534 | **-0.450** |
| **Sortino Ratio** | 1.775 | 0.871 | **-0.904** |
| **Max Drawdown** | -89.24% | -90.07% | **-0.83%** |
| **Win Rate** | 50.94% | 51.12% | **+0.19%** |

### Key Observations

1. **Massive Return Reduction:** Clipping reduces total returns by 1,422 percentage points
   - Unclipped: $10,000 ? $190,903
   - Clipped: $10,000 ? $48,728

2. **Volatility Reduction:** 16% decrease in annualized volatility
   - Shows that outlier returns drive much of the strategy's variance

3. **Sharpe Degradation:** Sharpe drops from ~1.0 to ~0.5
   - The strategy's extreme returns contribute positively to risk-adjusted performance
   - Clipping hurts more than it helps

4. **Drawdown Similar:** Max drawdowns are nearly identical (-89% vs -90%)
   - Suggests clipping doesn't meaningfully protect against crashes
   - The strategy is exposed to systemic drawdowns regardless

5. **Win Rate Unchanged:** 51% vs 51%
   - Clipping doesn't improve consistency
   - Extreme events are net positive for the strategy

---

## 4. Visual Analysis

### Portfolio Value Trajectory

![Clipping Comparison](../dilution_backtest_clipping_comparison.png)

**Key Visual Insights:**

1. **2021 Spike (Early):** Unclipped version shows massive spike in early 2021
   - Likely driven by extreme altcoin rallies
   - Clipped version misses this entirely

2. **2022-2024 Grind:** Both versions show similar drawdown patterns
   - Clipping doesn't prevent losses during bear markets
   - Both strategies struggle equally

3. **2025 Recovery:** Unclipped version explodes upward in late 2025
   - Another outlier event that drives cumulative performance
   - Clipped version shows modest recovery

### Rolling Returns

The 30-day rolling returns chart shows:
- **Unclipped:** More extreme swings (+250% to -50% monthly)
- **Clipped:** Dampened swings (+150% to -50% monthly)
- **Pattern:** Both follow similar trends, just different magnitudes

---

## 5. Root Cause Analysis

### Why is the unclipped version so much better?

The dilution factor strategy appears to be an **extreme outlier strategy**:
- Bets on low-dilution coins that occasionally "moon" (+100-200%)
- These rare events drive the majority of cumulative returns
- Clipping removes the upside while keeping downside exposure

### Crypto Market Dynamics

In crypto:
- **Fat tails are real:** Extreme moves (+50% days) are not rare
- **Asymmetric payoffs:** Low-dilution coins can 10x during bull runs
- **Dilution signal captures structural edge:** Coins with low dilution fundamentally outperform

Clipping to 1-99% percentiles **removes the strategy's core edge**.

---

## 6. Data Quality Issues - Detailed Breakdown

### Issue #1: Price Data Coverage

**Root cause:** Price data comes from Coinbase/CoinMarketCap combined dataset, which primarily covers:
- Coins traded on Coinbase
- Coins with sufficient liquidity
- Excludes many centralized exchange tokens (BNB)
- Excludes stablecoins (USDT, USDC) from price movements

**Impact:**
- Strategy can only trade ~30% of top 150 coins
- Systematically excludes largest coins
- Portfolio is biased toward mid/small caps with Coinbase listings

### Issue #2: Symbol Matching

**Current approach:** Direct string matching between:
- Dilution data: `Symbol` column (e.g., "BTC", "ETH")
- Price data: `base` column (e.g., "BTC", "ETH")

**This works correctly** - the matching logic is sound. The problem is **data availability**, not matching logic.

### Issue #3: Rebalance Date Availability

Example from 2021-02-01:
```
Dilution signals (top 150): 150 coins
With price data:             33 coins (22%)
Without price data:          117 coins (78%)
Missing: USDT, DOT, ADA, BNB, USDC
```

**Result:** Strategy forced to pick from limited universe of 33 coins, not 150.

---

## 7. Portfolio Construction Impact

### Intended Strategy
- Long top 10 LOW dilution (deflationary)
- Short top 10 HIGH dilution (inflationary)
- Universe: Top 150 by market cap

### Actual Implementation (Due to Data Issues)
- Long top 3-5 LOW dilution **with available price data**
- Short top 3-5 HIGH dilution **with available price data**
- Universe: ~33 coins with both dilution + price data

### Position Counts Over Time

From the backtest results:
```
Average positions per rebalance: 4-6 (target was 20)
Typical split: 3 long, 3 short (target was 10 long, 10 short)
```

**Concentration risk:** Strategy is far more concentrated than intended.

---

## 8. Recommendations

### A. Fix Data Coverage (High Priority)

1. **Expand price data sources:**
   - Add Binance data (BNB, many altcoins)
   - Add Kraken data (XRP, DOT)
   - Add Hyperliquid perpetuals data (strategy uses these anyway)

2. **Symbol mapping improvements:**
   - Create mapping table for exchange-specific symbols
   - Handle stablecoins separately
   - Consider using CMC IDs instead of tickers

3. **Expected impact:**
   - Join rate: 21.8% ? 60-70%
   - Position count: 6 ? 20
   - Better diversification
   - More robust results

### B. Clipping Decision (Medium Priority)

**Recommendation: DO NOT clip returns**

**Reasoning:**
1. **Strategy relies on outliers:** The dilution edge manifests in extreme moves
2. **No downside protection:** Clipping doesn't reduce drawdowns meaningfully
3. **Sharpe degradation:** Risk-adjusted returns suffer
4. **Total return destruction:** Clipping removes 1,400% of returns

**Alternative approaches:**
- Position sizing: Limit per-coin allocation (already using risk parity)
- Stop losses: Exit positions with >X% loss (adds complexity)
- Leverage reduction: Use 0.5x leverage to reduce overall exposure
- Accept volatility: This is crypto - 100% volatility is normal

### C. Backtest Validation (High Priority)

Before going live, we need to:

1. **Verify with expanded data:**
   - Re-run with Binance/Kraken/Hyperliquid data
   - Ensure top coins are included
   - Check if results hold with full universe

2. **Out-of-sample testing:**
   - Current results are potentially overfit to 33-coin subset
   - Need to validate on full 150-coin universe

3. **Transaction cost sensitivity:**
   - Currently using 0.1% per trade
   - With 20 positions (vs 6), costs will increase
   - Model realistic slippage

---

## 9. Live Trading Considerations

### Current State (If Deployed Today)

With current data limitations:
- **Tradeable universe:** ~33 coins (not 150)
- **Position count:** 4-6 (not 20)
- **Concentration:** High (3x more than intended)
- **Performance:** Unknown (out-of-sample untested with full data)

### Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Limited universe | **HIGH** | Expand data sources |
| Concentration | **HIGH** | More positions with better data |
| Outlier dependency | **MEDIUM** | Accept as strategy characteristic |
| Data staleness | **MEDIUM** | Monthly dilution updates sufficient |
| Execution risk | **LOW** | Weekly rebalancing allows careful execution |

---

## 10. Conclusion

### ?? CRITICAL FINDINGS

**This entire analysis is INVALID due to a portfolio construction bug.**

### Key Findings

1. **Portfolio Construction Bug (Most Important)**
   - **My analysis code still contains the bug** that was already identified and fixed
   - Bug causes accidental concentration (6 positions instead of 20)
   - ALL positive returns in this analysis are artifacts of the bug
   - **Properly fixed code shows -28% total return, not +1,809%**

2. **Data Joining Issue:** Only 21.8% of top 150 coins have both dilution + price data
   - Root cause: Limited price data coverage (Coinbase-centric)
   - This is a real issue but secondary to the bug

3. **Clipping Analysis:** Analysis shows 1-99% clipping hurts performance
   - But this is on BUGGY code with accidental concentration
   - Clipping impact on properly diversified portfolio is unknown
   - This analysis is **not actionable**

4. **Strategy Viability:** **STRATEGY IS NOT VIABLE**
   - Bug-fixed code (from `/workspace/DILUTION_FACTOR_BUG_FIX_SUMMARY.md`) shows:
     - Total return: **-27.8%** (loses money)
     - Annualized: **-6.7%** (loses money)
     - Sharpe: **-0.17** (negative risk-adjusted returns)
   - The dilution factor does NOT have predictive power when properly implemented

### What Went Wrong

The bug in my analysis code:
```python
# BUGGY (what I used):
# 1. Select top/bottom 10 from FULL universe (565 coins)
# 2. Try to get price data
# 3. Most coins missing -> falls back to 4-6 positions
# 4. Accidental concentration creates fake returns

# CORRECT (already fixed in backtest_dilution_factor.py):
# 1. Filter to coins with price data FIRST (172 coins)
# 2. Select top/bottom 10 from AVAILABLE universe
# 3. Get 10-16 positions consistently
# 4. Proper diversification shows real (negative) returns
```

### Actual Next Steps

**DO NOT TRADE THIS STRATEGY**

1. **Abandon dilution factor strategy**
   - Properly implemented strategy loses money
   - No edge when properly diversified
   - Data coverage issues are real but not the main problem

2. **Learn from this analysis**
   - Always verify portfolio composition (I should have noticed 6 vs 20 positions)
   - Read existing bug fix documentation before re-running backtests
   - Positive backtest returns in crypto should trigger skepticism, not excitement

3. **Use the bug-fixed code**
   - If re-running ANY dilution backtests, use `/workspace/backtests/scripts/backtest_dilution_factor.py`
   - Do NOT use the code in my `analyze_dilution_backtest.py` (it has the bug)
   - The bug has already been identified and fixed

### Correct Performance Numbers

**From the bug-fixed implementation:**
```
Total Return:       -27.8%
Annualized Return:   -6.7%
Sharpe Ratio:        -0.17
Max Drawdown:       -61.0%
Positions:          10-16 (proper diversification)
```

This is the REAL performance. All other numbers in this document are wrong.

---

## Appendix: Technical Details

### Files Generated
- `dilution_backtest_clipping_comparison.png` - Visual comparison
- `dilution_backtest_clipped_portfolio.csv` - Daily portfolio values (clipped)
- `dilution_backtest_join_analysis.csv` - Join rate by date

### Methodology
- **Clipping:** 1st and 99th percentiles of ALL returns
- **Risk Parity:** Inverse volatility weighting (90-day lookback)
- **Rebalancing:** Monthly (57 rebalances over 4.7 years)
- **Transaction costs:** 0.1% per trade
- **Initial capital:** $10,000

### Code Location
- Analysis script: `/workspace/analyze_dilution_backtest.py`
- Main backtest: `/workspace/backtests/scripts/backtest_dilution_factor.py`
- Run all backtests: `/workspace/backtests/scripts/run_all_backtests.py`

---

**Analysis completed:** 2025-11-02  
**Author:** Background Agent (Cursor AI)
