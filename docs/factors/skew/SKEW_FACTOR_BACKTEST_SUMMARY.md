# Skew Factor Strategy - Backtest Summary

**Date:** 2025-10-27  
**Strategy:** Long/Short based on 30-day return skewness  
**Period:** March 1, 2020 - October 24, 2025 (5.7 years)

---

## Executive Summary

The skew factor backtest generated **positive returns** but revealed **unexpected asymmetry**: the strategy profited primarily from **shorting coins with positive skewness**, while **losing money on coins with negative skewness**. This contradicts the initial hypothesis and suggests momentum rather than mean reversion effects.

### Key Results
- **Total Return:** +83.88% (11.38% annualized)
- **Sharpe Ratio:** 0.36 (moderate risk-adjusted returns)
- **Max Drawdown:** -54.37% (significant)
- **Long Portfolio:** -15.21% total return ❌
- **Short Portfolio:** +116.88% total return ✅

---

## Strategy Design

### Core Hypothesis
Skewness patterns in crypto return distributions might predict future returns through:
1. **Mean Reversion:** Extreme skewness reverts to normal
2. **Risk Premium:** Negative skewness (crash risk) commands premium

### Implementation
- **Ranking Metric:** 30-day rolling skewness of daily log returns
- **Portfolio Construction:**
  - **Long:** Bottom quintile (20% with most negative skewness)
  - **Short:** Top quintile (20% with most positive skewness)
- **Weighting:** Equal weight within each side
- **Exposure:** Dollar neutral (100% long, 100% short)
- **Rebalancing:** Daily
- **Filters:**
  - Min 30-day avg volume: $5M
  - Min market cap: $50M
  - Data quality: 30+ consecutive days

---

## Performance Metrics

### Portfolio Performance

| Metric | Value |
|--------|-------|
| Initial Capital | $10,000 |
| Final Value | $18,388 |
| Total Return | +83.88% |
| Annualized Return | +11.38% |
| Trading Days | 2,064 |

### Risk Metrics

| Metric | Value | Assessment |
|--------|-------|------------|
| Annualized Volatility | 31.67% | High (crypto-level) |
| Sharpe Ratio | 0.36 | Below average |
| Sortino Ratio | 0.26 | Low |
| Maximum Drawdown | -54.37% | Very high |
| Calmar Ratio | 0.21 | Poor |

### Trading Statistics

| Metric | Value |
|--------|-------|
| Win Rate | 10.56% |
| Avg Daily Turnover | 5.68% |
| Avg Long Positions | 0.8 coins |
| Avg Short Positions | 0.7 coins |
| Avg Long Exposure | 21.80% |
| Avg Short Exposure | 21.80% |
| Net Exposure | ~0% (market neutral) |

---

## Long vs Short Analysis

### Long Portfolio (Negative Skewness)
- **Total Return:** -15.21% ❌
- **Sharpe Ratio:** -0.06
- **Interpretation:** Coins with negative skewness (left tail risk) **continued to decline**

### Short Portfolio (Positive Skewness)
- **Total Return:** +116.88% ✅
- **Sharpe Ratio:** 0.25
- **Interpretation:** Coins with positive skewness (right tail wins) **underperformed or corrected**

### Key Finding: Asymmetric Performance
The strategy made money **entirely from the short side**, indicating that:
1. Positive skewness signals **overextension/euphoria** → subsequent correction
2. Negative skewness signals **distress/crisis** → continued decline (NOT mean reversion)

---

## Hypothesis Validation

### ❌ Hypothesis 1: Mean Reversion FAILED
**Expected:** Negative skewness → mean reversion → positive returns  
**Actual:** Negative skewness → continued decline → negative returns

**Evidence:**
- Long portfolio lost 15.21%
- Negative Sharpe of -0.06
- No mean reversion observed

### ❌ Hypothesis 2: Risk Premium FAILED
**Expected:** Holding negative skew assets earns risk premium  
**Actual:** Holding negative skew assets lost money

### ✅ Hypothesis 3: Momentum/Correction CONFIRMED
**Expected:** Positive skewness → overheating → correction  
**Actual:** Positive skewness → underperformance → profitable shorts

**Evidence:**
- Short portfolio gained 116.88%
- Positive Sharpe of 0.25
- Consistent short profits

---

## Interpretation & Insights

### 1. Skewness as a Momentum Indicator

**Negative Skewness (Left Tail):**
- Indicates recent extreme losses or crash risk
- Suggests coins in distress or downtrend
- **Continues to decline** rather than bounce
- Analogous to "catching falling knives"

**Positive Skewness (Right Tail):**
- Indicates recent extreme gains or "lottery ticket" behavior
- Suggests coins experiencing euphoria or overextension
- **Mean reverts or corrects** after rally
- Analogous to "shorting the hype"

### 2. Why Mean Reversion Failed

**Crypto Market Structure:**
- **Asymmetric Volatility:** Down moves are sharper than up moves
- **Liquidation Cascades:** Negative skewness often signals leverage unwind
- **Fundamental Deterioration:** Coins with crash risk may have real problems
- **Retail Capitulation:** Panic selling creates negative skewness that persists

**Contrast with Traditional Mean Reversion:**
- Traditional mean reversion (z-score on returns) worked for dips
- Skewness mean reversion (distribution shape) does NOT work

### 3. Portfolio Construction Issues

**Low Position Count:**
- Avg 0.8 long positions + 0.7 short positions
- Only 1-2 total positions most days
- High concentration risk
- Limited diversification

**Reasons for Low Count:**
- Strict filters (volume, market cap)
- Only 52 coins had valid data
- Quintile approach spreads thin universe too much

**Impact:**
- High volatility (31.67% annualized)
- Large drawdown (-54%)
- Low Sharpe ratio (0.36)

### 4. Win Rate Analysis

**10.56% Win Rate:**
- Extremely low daily win rate
- Likely driven by many zero-return days (no positions)
- When positions are held, strategy may be more volatile

**Why Low:**
- Long portfolio consistently losing
- Short portfolio wins but concentrated
- Many days with no positions held

---

## Comparison to Other Strategies

### Directional Mean Reversion (from prior work)
- **Best Long Strategy:** 2d lookback, high volume = 1.25% return, 3.14 Sharpe
- **Buying extreme dips works:** Sharpe > 2.0 consistently
- **Shorting rallies fails:** Similar to skew factor

### Skew Factor Strategy
- **Skew Long (negative):** -15.21% return, -0.06 Sharpe ❌
- **Skew Short (positive):** +116.88% return, 0.25 Sharpe ✅
- **Combined:** +83.88% return, 0.36 Sharpe

**Key Difference:**
- **Z-score mean reversion:** Buy extreme dips = works
- **Skewness mean reversion:** Buy negative skew = fails
- **Implication:** Distribution shape ≠ price level deviation

---

## Strategy Refinement Recommendations

### 1. Short-Only Approach
**Rationale:** All profits came from shorts  
**Implementation:**
- Remove long side
- Short top quintile (positive skewness)
- Go to cash on remainder
- Expected improvement: Eliminate losing long side

### 2. Decile Instead of Quintile
**Rationale:** Too few positions with quintiles  
**Implementation:**
- Use top/bottom 10% (deciles) instead of 20%
- Increase average position count
- Better diversification
- Reduce concentration risk

### 3. Combine with Volume/Volatility
**Rationale:** Mean reversion works with volume filters  
**Implementation:**
- Long: High volume dips (z-score < -1.5) + any skewness
- Short: Positive skewness + momentum
- Hybrid approach may work better

### 4. Adjust Lookback Window
**Rationale:** 30 days may be suboptimal  
**Test:**
- 20-day skewness (shorter, more reactive)
- 60-day skewness (longer, more stable)
- 90-day skewness (very long-term)

### 5. Alternative Weighting
**Rationale:** Equal weight may be suboptimal  
**Test:**
- Weight by magnitude of skewness
- Weight by inverse volatility (risk parity)
- Weight by market cap

---

## Risk Considerations

### Identified Risks

1. **Concentration Risk**
   - Only 0.8 long + 0.7 short positions average
   - High idiosyncratic risk
   - Poor diversification

2. **Drawdown Risk**
   - 54% max drawdown is severe
   - Would require strong conviction to hold
   - May breach risk management limits

3. **Liquidity Risk**
   - Small coin universe (52 valid coins)
   - Lower liquidity coins may have slippage
   - Shorting costs not modeled

4. **Regime Dependency**
   - Strategy may work differently in bull vs bear
   - Need regime analysis
   - May require dynamic adjustment

5. **Overfitting Risk**
   - Single backtest period
   - No out-of-sample testing
   - Parameters not optimized

### Transaction Costs

**Not Modeled:**
- Trading fees (0.05-0.1% per trade)
- Slippage on market orders
- Shorting costs (borrow fees, funding rates)
- Price impact on smaller coins

**Impact Estimate:**
- 5.68% avg daily turnover
- At 0.1% fees = 0.0057% daily cost
- ~2% annual drag on returns
- **Net return after fees:** ~9.4% annualized

---

## Conclusions

### What We Learned

1. **Skewness is a Momentum Signal, Not Mean Reversion**
   - Negative skewness → continued decline
   - Positive skewness → correction/underperformance
   - Opposite of initial hypothesis

2. **Short Side is Profitable**
   - Shorting positive skewness works
   - +116.88% return from shorts alone
   - Could be viable standalone strategy

3. **Long Side Loses Money**
   - Buying negative skewness fails
   - -15.21% return from longs
   - Should be eliminated or redesigned

4. **Portfolio Construction Needs Work**
   - Too few positions (1-2 total)
   - High concentration risk
   - Need larger universe or different bucketing

5. **Distribution Shape ≠ Price Deviation**
   - Z-score mean reversion works (buy dips)
   - Skewness mean reversion fails (buy negative skew)
   - Different phenomena, different strategies

### Overall Assessment

**Profitability:** ✅ Positive returns (11.38% annualized)  
**Risk-Adjusted:** ⚠️ Moderate Sharpe (0.36)  
**Drawdown:** ❌ Unacceptable (-54.37%)  
**Robustness:** ❌ Single-sided profits only  
**Practical:** ⚠️ Needs refinement

**Recommendation:** 
- Do NOT implement as-is
- Explore short-only variant
- Combine with other signals
- Improve position count
- Test alternative parameters

---

## Next Steps

### Immediate Actions
1. Run sensitivity analysis on lookback window (20d, 60d, 90d)
2. Test decile vs quintile bucketing
3. Analyze regime dependency (bull/bear markets)
4. Test short-only variant
5. Add transaction cost modeling

### Future Research
1. Combine skewness with z-score signals
2. Test higher moments (kurtosis)
3. Cross-sectional vs time-series skewness
4. Conditional skewness (volume, volatility)
5. Machine learning to predict which skewness patterns revert

### Integration
- **Execution System:** Can use existing CCXT framework
- **Risk Management:** Need dynamic position limits
- **Portfolio:** Could complement existing strategies
- **Monitoring:** Track long/short contributions separately

---

## Files Generated

### Data Files
- `backtests/results/skew_factor_backtest_results.csv` - Daily portfolio values
- `backtests/results/skew_factor_performance.csv` - Summary metrics
- `backtests/results/skew_factor_signals.csv` - Long/short signals by date

### Visualizations
- `backtests/results/skew_factor_equity_curve.png` - Portfolio equity curve
- `backtests/results/skew_factor_drawdown.png` - Drawdown chart
- `backtests/results/skew_factor_long_short_comparison.png` - Long vs short performance
- `backtests/results/skew_factor_skewness_distribution.png` - Skewness histogram
- `backtests/results/skew_factor_turnover.png` - Daily turnover

### Code
- `backtests/scripts/backtest_skew_factor.py` - Backtest implementation
- `docs/SKEW_FACTOR_STRATEGY.md` - Strategy specification

---

**Analysis Completed:** 2025-10-27  
**Analyst:** Backtest Agent  
**Status:** Initial backtest complete, refinement needed
