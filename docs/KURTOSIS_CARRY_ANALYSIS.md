# Kurtosis and Carry Factor Analysis

## Executive Summary

Both the **Kurtosis Factor (Momentum)** and **Carry Factor** strategies are showing consistent negative returns across all years (2023-2025). This document analyzes what's going wrong and why.

---

## 1. Kurtosis Factor Issues

### Performance by Year

| Year | Return | Annualized | Sharpe | Max DD | Win Rate |
|------|--------|------------|--------|---------|----------|
| 2023 | -16.47% | -17.86% | -1.133 | -20.90% | 45.51% |
| 2024 | -12.29% | -12.26% | -0.708 | -18.50% | 50.00% |
| 2025 | -12.48% | -15.16% | -0.782 | -18.43% | 47.97% |
| **Overall** | **-35.45%** | **-14.82%** | **-0.849** | **-38.04%** | **47.94%** |

**Period:** Jan 31, 2023 - Oct 23, 2025 (997 days)

### Root Cause

The **momentum interpretation of kurtosis is incorrect**:

- **Kurtosis** measures the "tailedness" of a distribution (fat tails vs thin tails)
- **High kurtosis** means more extreme outliers, NOT necessarily upward momentum
- **Low kurtosis** means more normal distribution, NOT necessarily downward momentum

The strategy goes **long high kurtosis** (assuming momentum) and **short low kurtosis**, but:
- High kurtosis coins may be experiencing high volatility in BOTH directions
- The fat tails could be downside moves, not just upside
- The strategy is effectively betting on volatility, not directional momentum

### Recommendation

? **DISABLE Kurtosis Momentum Strategy** - It's fundamentally flawed and consistently loses money.

Consider testing:
- Kurtosis mean-reversion strategy (opposite direction)
- Using kurtosis as a risk filter, not a signal
- Combining kurtosis with actual price momentum indicators

---

## 2. Carry Factor Issues

### Performance by Year

| Year | Return | Annualized | Sharpe | Max DD | Win Rate | Avg Long FR | Avg Short FR | Expected Funding |
|------|--------|------------|--------|---------|----------|-------------|--------------|------------------|
| 2023 | -9.11% | -9.14% | -0.651 | -18.13% | 50.55% | +0.06% | +1.13% | +0.016%/day |
| 2024 | -18.31% | -18.26% | -1.057 | -28.31% | 46.17% | +0.33% | +1.72% | +0.021%/day |
| 2025 | -19.46% | -23.42% | -1.471 | -26.01% | 47.97% | -0.41% | +0.93% | +0.020%/day |
| **Overall** | **-39.78%** | **-16.41%** | **-1.040** | **-44.00%** | **48.30%** | **+0.06%** | **+1.28%** | **+0.019%/day** |

**Period:** Jan 1, 2023 - Oct 23, 2025 (1027 days)

### The Problem: Price Movement Overwhelms Funding Income

The carry strategy has THREE components:

1. **Funding Income** (what we're trying to capture)
   - Long positions with negative FR: We receive funding ?
   - Long positions with positive FR: We pay funding ?
   - Short positions with positive FR: We receive funding ?
   - Short positions with negative FR: We pay funding ?

2. **Price Movement** (the overwhelming factor)
   - Coins with high funding rates (we short): Often performing WELL ? losses on shorts
   - Coins with low funding rates (we long): Often performing POORLY ? losses on longs

3. **Net Result**
   - Expected funding income: ~0.02% per day (~7% annualized)
   - Actual losses: -16.4% annualized
   - **Price losses overwhelm funding by ~23% per year**

### Why It's Failing

**Fundamental Issue:** Funding rates are a MOMENTUM indicator, not a contrarian signal.

- **High positive funding rates** ? Market expects price to rise ? Longs are paying premiums ? Price usually DOES rise
- **Low/negative funding rates** ? Market expects price to fall ? Shorts are paying premiums ? Price usually DOES fall

**Our strategy does the OPPOSITE:**
- We SHORT high funding rate coins (expecting mean reversion) ? But prices keep rising
- We LONG low funding rate coins (expecting mean reversion) ? But prices keep falling

### The Data Confirms This

**2023:** Long FR = +0.06%, Short FR = +1.13%
- We're longing coins with slightly positive FR (we pay)
- We're shorting coins with high positive FR (we receive)
- Net funding: +0.016%/day
- But we lost -9.11% for the year!

**2024:** Long FR = +0.33%, Short FR = +1.72%
- Same pattern, worse results: -18.31%

**2025:** Long FR = -0.41%, Short FR = +0.93%
- Finally some negative FR on longs (we receive!)
- But STILL losing: -19.46% (worst year!)

### Why 2025 is Worst Despite Better Funding

The 2025 Sharpe of -1.471 (worst of all years) despite having negative FR on longs suggests:
- The coins with negative funding rates are crashing even harder
- The mean-reversion thesis is completely broken
- Funding rates have predictive power for MOMENTUM, not mean-reversion

---

## 3. Root Cause: Mean-Reversion vs Momentum

Both strategies assume **mean-reversion** but crypto exhibits **momentum**:

### Kurtosis Factor
- **Assumption:** High kurtosis = extreme moves = reversion coming
- **Reality:** High kurtosis = volatility continues in same direction

### Carry Factor  
- **Assumption:** Extreme funding rates = overbought/oversold = reversion coming
- **Reality:** Extreme funding rates = strong directional conviction = trend continues

---

## 4. Default Start Date Issue

**Current default:** `2023-01-01`
**Data available:** 2020-01-21 to 2025-10-28

### Funding Rate Data Availability
- 2020: 18 coins
- 2021: 35 coins
- 2022: 46 coins
- 2023: 62 coins
- 2024: 84 coins
- 2025: 90 coins

**Recommendation:** Change default to `2021-01-01` for:
- 4.8 years of data vs 2.8 years
- More market cycles (bull, bear, recovery)
- Better validation across different market conditions
- 2020 has too few coins (18), but 2021 is reasonable (35)

---

## 5. Recommendations

### Immediate Actions

1. **Kurtosis Factor:**
   - ? Disable momentum strategy (consistently -15% annualized)
   - ? Test mean-reversion strategy (inverse signals)
   - ? Use kurtosis as risk filter, not primary signal

2. **Carry Factor:**
   - ? Disable contrarian carry strategy (consistently -16% annualized)
   - ? Test MOMENTUM-based carry strategy:
     - Long high funding rate coins (instead of shorting them)
     - Short low funding rate coins (instead of longing them)
   - ? Add momentum filters to existing strategy

3. **Backtest Configuration:**
   - Change default `--start-date` from `2023-01-01` to `2021-01-01`
   - Update documentation to explain date selection rationale

### Strategy Fixes to Test

#### Carry Factor - Momentum Interpretation
```python
# CURRENT (failing):
Long: Lowest funding rates (coins expected to rise)
Short: Highest funding rates (coins expected to fall)

# PROPOSED (untested):
Long: Highest funding rates (follow the momentum)  
Short: Lowest funding rates (fade the weakness)
```

#### Carry Factor - Hybrid Approach
```python
# Only take carry trades when funding income justifies it:
Long: Negative funding rates < -5% (we receive substantial funding)
Short: Positive funding rates > +5% (we receive substantial funding)
Skip: Marginal funding rates (price risk > funding income)
```

---

## 6. Data Quality Observations

### Symbol Overlap Issues
- Price data: 93 symbols (2023+)
- Funding data: 90 symbols (2023+)
- **Overlap: Only 37 symbols** (41% of price data)

This limited overlap may be contributing to poor performance:
- Missing many tradeable coins
- Sample bias toward certain market caps/sectors
- Need to investigate symbol mapping issues

### Overlapping Symbols
AAVE, ALGO, ARB, BCH, BNB, BONK, BTC, ENA, ENS, ETC, ETH, FARTCOIN, FIL, FLOKI, GRT, IMX, LDO, LINK, LTC, MOG, ONDO, OP, PEPE, POPCAT, RNDR, SEI, SHIB, SOL, STX, SUI, TIA, TON, TRX, UNI, USDT, WIF, XRP

---

## Conclusion

Both strategies are fundamentally flawed due to incorrect assumptions about market behavior:

1. **Kurtosis ? Momentum:** Fat tails don't predict direction
2. **Funding Rates = Momentum, not Mean-Reversion:** High FR predicts continuation, not reversal
3. **Crypto has strong momentum effects:** Contrarian strategies struggle

**Action Required:** Either fix these strategies or remove them from the portfolio allocation.
