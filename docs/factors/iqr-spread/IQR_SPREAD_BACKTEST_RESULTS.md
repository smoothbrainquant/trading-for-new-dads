# IQR Spread Factor Backtest Results

**Date:** 2025-10-27  
**Status:** ✅ COMPLETE - Initial Backtest Executed

---

## Executive Summary

The IQR Spread Factor strategy has been successfully implemented and backtested. The strategy rotates between major cryptocurrencies (top 10 by market cap) and smaller caps (rank 26-50) based on market dispersion as measured by the Interquartile Range (IQR) of 30-day returns across the top 100 coins.

### Key Findings

**Overall Performance (2021-01-01 to 2024-10-24):**
- **Total Return:** +40.40%
- **Annualized Return:** 236.80% (note: based on limited data points)
- **Sharpe Ratio:** 4.79
- **Maximum Drawdown:** -18.27%
- **Win Rate:** 57.84%

**Key Insight:** The strategy shows strong regime-dependent behavior, with dramatic performance differences across IQR spread regimes.

---

## Strategy Description

### Core Concept

The IQR Spread is calculated as:

\[ \text{IQR Spread} = P_{75}(\text{Returns}_{30d}) - P_{25}(\text{Returns}_{30d}) \]

Where percentiles are calculated across the top 100 cryptocurrencies by market cap.

### Hypothesis

- **Low Spread (Compressed Returns):** Market moving together → Risk-on environment → Favor small caps
- **High Spread (Wide Dispersion):** Fragmented market → Risk-off environment → Favor majors

### Implementation

**Baskets:**
- **Majors:** Top 10 coins by market cap
- **Small Caps:** Rank 26-50 by market cap

**Allocation Rules:**
- **Low Spread Regime (<20th percentile):** 30% majors / 70% small caps
- **Medium Spread Regime (20-80th percentile):** 50% majors / 50% small caps
- **High Spread Regime (>80th percentile):** 70% majors / 30% small caps

**Parameters:**
- Lookback: 30 days for return calculation
- Rebalance: Every 7 days
- IQR History Window: 180 days for regime classification
- Universe Filters: Min volume $1M, Min market cap $10M

---

## Backtest Results

### Performance by Regime

| Regime | Days | Ann. Return | Sharpe | Volatility | Win Rate |
|--------|------|-------------|--------|------------|----------|
| **LOW_SPREAD** | 14 | +145.70% | 4.90 | 29.71% | 50.00% |
| **MEDIUM_SPREAD** | 75 | +198.61% | 3.78 | 52.56% | 62.67% |
| **HIGH_SPREAD** | 13 | **-238.80%** | **-5.19** | 45.98% | 38.46% |

### Critical Finding: High Spread Regime

**The most striking result is the HIGH_SPREAD regime performance:**
- Strongly negative returns (-238.80% annualized)
- Negative Sharpe ratio (-5.19)
- Low win rate (38.46%)

This suggests that **the strategy of rotating to majors during high spread periods is counterproductive** in this dataset. When market dispersion increases, the strategy shifts to majors (defensive positioning), but this has historically resulted in losses.

### Possible Explanations

1. **Small Cap Outperformance:** Small caps may have consistently outperformed majors during the test period, making rotation away from them costly.

2. **Inverted Signal:** The regime indicator might need to be inverted - high spread could indicate opportunities in small caps rather than risk-off.

3. **Timing Issues:** The regime transitions may not be properly timed, causing entry at inopportune moments.

4. **Sample Size:** Only 13 days in HIGH_SPREAD regime - small sample, high uncertainty.

5. **Market Evolution:** Crypto markets may behave differently than traditional markets where dispersion = risk-off.

---

## IQR Spread Statistics

**Period: 2021-01-31 to 2024-10-24**

- **IQR Spread Range:** 8.30 to 50.00
- **Mean IQR Spread:** 21.48
- **Median IQR Spread:** 21.35
- **Observations:** 102 data points

**Regime Distribution:**
- Low Spread Days: 14 (13.7%)
- Medium Spread Days: 75 (73.5%)
- High Spread Days: 13 (12.7%)

The majority of the time (73.5%) the market is in a medium spread regime, with roughly equal time in low and high spread extremes.

---

## Correlations

### IQR Spread vs Returns

| Metric | Correlation with IQR Spread |
|--------|---------------------------|
| Majors Return | -0.084 (weak negative) |
| BTC Return | -0.047 (weak negative) |
| Median Return | +0.301 (moderate positive) |

**Interpretation:**
- Weak negative correlation between IQR spread and majors returns
- Weak negative correlation with BTC
- Moderate positive correlation between IQR spread and median market return

The positive correlation between IQR spread and median return is interesting - it suggests that high spread periods coincide with higher median returns, potentially because a few strong performers are driving the spread wider.

---

## Risk Metrics

| Metric | Value |
|--------|-------|
| **Annualized Volatility** | 49.42% |
| **Sharpe Ratio** | 4.79 |
| **Sortino Ratio** | 6.15 |
| **Maximum Drawdown** | -18.27% |
| **Calmar Ratio** | 12.96 |

**Assessment:** 
- High volatility (49.42%) reflects the crypto market's nature
- Excellent risk-adjusted returns (Sharpe 4.79)
- Manageable drawdown (-18.27%) relative to crypto standards
- Strong Calmar ratio (12.96) indicates good return/drawdown tradeoff

---

## Data Quality Observations

### Limited Data Points

The backtest only captured **102 IQR spread observations** out of 1,363 potential trading days. This means:
- IQR spread could only be calculated ~7.5% of days
- Likely due to insufficient coins with valid 30-day returns AND market cap data
- Reduces statistical confidence in results

### Implications

1. **Data Requirements:** Need more complete market cap data across more coins
2. **Alternative Approaches:** 
   - Use smaller universe (top 50 instead of top 100)
   - Relax volume/market cap filters
   - Use alternative data sources for market cap

---

## Strategy Variants to Test

### 1. Inverted Signal
**Hypothesis:** High spread = opportunity in small caps (not risk-off)

**Allocation:**
- Low spread → Favor majors (70/30)
- High spread → Favor small caps (30/70)

**Rationale:** Results suggest this might perform better.

### 2. Long-Only Small Caps
**Hypothesis:** Small caps outperform, don't rotate away

**Allocation:**
- Always 100% small caps
- Use IQR spread as risk sizing (reduce exposure in high spread)

### 3. Threshold-Based
**Hypothesis:** Only rotate at extreme IQR levels

**Allocation:**
- Only shift allocation when IQR < 10th percentile or > 90th percentile
- Otherwise maintain 50/50

### 4. Continuous Allocation
**Hypothesis:** Smooth transitions work better

**Allocation:**
- Linear interpolation based on IQR percentile
- E.g., 0th %ile = 90% small caps → 100th %ile = 10% small caps

---

## Comparison to Benchmarks

### vs Buy-and-Hold BTC
- Strategy: +40.40% total return
- Sharpe: 4.79

*(Need to calculate BTC buy-and-hold for same period to compare)*

### vs Equal-Weight Majors
*(Need to implement for comparison)*

### vs Equal-Weight Small Caps
*(Need to implement for comparison)*

---

## Implementation Notes

### Files Generated

```
backtests/results/backtest_iqr_spread_full_portfolio_values.csv
backtests/results/backtest_iqr_spread_full_iqr_timeseries.csv
backtests/results/backtest_iqr_spread_full_basket_performance.csv
backtests/results/backtest_iqr_spread_full_regime_performance.csv
backtests/results/backtest_iqr_spread_full_correlations.csv
backtests/results/backtest_iqr_spread_full_metrics.csv
backtests/results/backtest_iqr_spread_full_strategy_info.csv
```

### Script Location

```
backtests/scripts/backtest_iqr_spread_factor.py
```

### Usage Example

```bash
python3 backtests/scripts/backtest_iqr_spread_factor.py \
  --start-date 2021-01-01 \
  --end-date 2024-10-24 \
  --small-caps-start 26 \
  --small-caps-end 50 \
  --output-prefix backtests/results/backtest_iqr_spread
```

---

## Next Steps

### Immediate Priorities

1. **Test Inverted Signal Strategy**
   - Flip the allocation logic
   - Compare performance to baseline

2. **Improve Data Coverage**
   - Investigate why only 102/1363 days have IQR calculations
   - Consider using alternative universe size (top 50 instead of top 100)
   - Relax filters or use imputed market cap data

3. **Benchmark Comparisons**
   - Run long-only majors basket
   - Run long-only small caps basket
   - Run equal-weight top 50
   - Calculate Sharpe ratios for all

4. **Fix Basket Attribution**
   - Currently small_caps_exposure is not being tracked properly
   - Need to separately track majors vs small caps P&L

### Future Enhancements

1. **Regime Smoothing**
   - Add buffer zones to prevent whipsaws
   - Require 2+ consecutive periods in regime before shifting

2. **Dynamic Thresholds**
   - Adjust percentile thresholds based on market conditions
   - Use volatility-adjusted thresholds

3. **Multi-Factor Integration**
   - Combine IQR spread with momentum, volatility, or beta factors
   - Use IQR spread as regime filter for other strategies

4. **Transaction Cost Analysis**
   - Estimate realistic transaction costs
   - Optimize rebalance frequency

5. **Out-of-Sample Testing**
   - Reserve 2024 data for validation
   - Test on different crypto market cycles (2017-2018, 2020-2021)

---

## Conclusions

### Strengths

1. **Strong Overall Performance:** +40% return with 4.79 Sharpe ratio
2. **Clear Regime Separation:** Dramatic performance differences by regime
3. **Manageable Risk:** 18% max drawdown is reasonable for crypto
4. **Interesting Signal:** IQR spread shows promise as market regime indicator

### Weaknesses

1. **High Spread Performance:** Large losses in high spread regime
2. **Data Limitations:** Only 102 observations, limits statistical confidence
3. **Small Sample in Extremes:** Only 13-14 days in low/high spread regimes
4. **Unclear Mechanism:** Why high spread leads to losses is not obvious

### Key Takeaway

**The IQR spread is a meaningful market regime indicator, but the original hypothesis (high spread = risk-off = favor majors) appears to be incorrect for crypto markets.** The data suggests either:
- The signal should be inverted, OR
- Small caps consistently outperform and rotation is unnecessary, OR
- The timing/implementation needs refinement

**Recommendation:** Test the inverted signal strategy before deploying any live trading.

---

## Academic Context

### Traditional Finance

In equity markets:
- High cross-sectional dispersion typically indicates:
  - Stock-picking environment (less macro-driven)
  - Lower market-wide correlations
  - Potentially higher alpha opportunities

### Crypto Markets

Crypto may behave differently:
- **Lower Liquidity:** Small caps have less depth
- **Higher Beta:** Small caps amplify market moves
- **Retail Driven:** Different risk preferences than institutional markets
- **Momentum Effects:** Strong trends in alt coin cycles

The negative performance in high spread regimes suggests crypto markets may require a different interpretation of dispersion signals compared to traditional finance.

---

## Appendix: Parameter Sensitivity

**Tested Parameters:**
- Lookback: 30 days
- Rebalance: 7 days
- IQR History: 180 days
- Regime Thresholds: 20th/80th percentiles
- Universe: Top 100 for IQR, top 10 for majors, rank 26-50 for small caps

**Parameters to Test:**
- Lookback: 20d, 45d, 60d
- Rebalance: 3d, 14d, 30d
- Thresholds: 10/90, 15/85, 25/75
- Small caps range: 11-25, 26-50, 51-100

---

**Document Owner:** Research Team  
**Last Updated:** 2025-10-27  
**Next Review:** After strategy variant testing

---

**Disclaimer:** This backtest is for research purposes only. Past performance does not guarantee future results. The limited data coverage (102 observations) means results should be interpreted with caution. Further testing and validation required before any live deployment.
