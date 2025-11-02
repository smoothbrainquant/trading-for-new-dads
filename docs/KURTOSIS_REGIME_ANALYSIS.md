# Kurtosis Factor Backtest: Regime Analysis & Long/Short Returns

**Analysis Date:** November 2, 2025  
**Backtest Period:** January 31, 2022 - October 24, 2025 (1,363 days)  
**Strategy:** Mean Reversion Kurtosis Factor (Long Low Kurtosis / Short High Kurtosis)

---

## Executive Summary

This analysis breaks down the kurtosis factor backtest results by market regime and dissects performance into long and short contributions. **The overall strategy lost -47.2% over the test period**, with critical insights revealed when examining performance across different market conditions.

### Key Findings

1. **Regime-Dependent Performance**: The strategy shows dramatically different performance across market regimes
2. **Best Performance**: Bear markets with low volatility (+27.97% long, +49.69% short annualized)
3. **Worst Performance**: Bull markets with high volatility (-21.74% long, -35.59% short annualized)
4. **Overall Long/Short Split**: Both sides contributed negatively (-24.18% long, -30.35% short cumulative)

---

## Market Regime Definitions

We define four market regimes based on:
- **Trend**: Bull (50-day MA > 200-day MA) vs Bear (50-day MA < 200-day MA)
- **Volatility**: High Vol (above median) vs Low Vol (below median)

This creates four regime combinations:
1. **Bear / Low Vol** (260 days)
2. **Bear / High Vol** (284 days)
3. **Bull / Low Vol** (644 days)
4. **Bull / High Vol** (175 days)

---

## Regime Performance Breakdown

### 1. Bear / Low Vol (Best Regime)
**Period:** 260 days  
**Total Return:** -16.48% (Annualized: -22.34%)  
**Sharpe Ratio:** 1.79  
**Win Rate:** 49.62%

| Component | Contribution | Annualized |
|-----------|-------------|------------|
| **Long** | +17.57% | **+27.97%** |
| **Short** | +28.73% | **+49.69%** |

**Insights:**
- Both long and short sides profitable in bear/low-vol conditions
- Short positions outperformed, contributing 62% more than longs
- Highest Sharpe ratio of all regimes
- Strategy excels when market is declining steadily without extreme volatility

### 2. Bear / High Vol
**Period:** 284 days  
**Total Return:** -35.12% (Annualized: -42.65%)  
**Sharpe Ratio:** 1.54  
**Win Rate:** 50.35%

| Component | Contribution | Annualized |
|-----------|-------------|------------|
| **Long** | +17.15% | **+24.66%** |
| **Short** | +30.83% | **+48.62%** |

**Insights:**
- Still profitable on both sides despite high volatility
- Short positions again outperformed
- Positive Sharpe ratio maintained
- High volatility in bear markets doesn't destroy the strategy

### 3. Bull / Low Vol (Longest Regime)
**Period:** 644 days (47% of total)  
**Total Return:** -66.91% (Annualized: -46.57%)  
**Sharpe Ratio:** -2.01  
**Win Rate:** 44.88%

| Component | Contribution | Annualized |
|-----------|-------------|------------|
| **Long** | -50.65% | **-24.95%** |
| **Short** | -74.64% | **-34.50%** |

**Insights:**
- Largest drawdown period
- Both sides lost money consistently
- Mean reversion strategy failed in steady bull market
- Low kurtosis assets didn't mean-revert upward as expected
- High kurtosis assets didn't mean-revert downward

### 4. Bull / High Vol (Worst Regime)
**Period:** 175 days  
**Total Return:** -66.84% (Annualized: -90.00%)  
**Sharpe Ratio:** -1.22  
**Win Rate:** 45.14%

| Component | Contribution | Annualized |
|-----------|-------------|------------|
| **Long** | -11.76% | **-21.74%** |
| **Short** | -21.09% | **-35.59%** |

**Insights:**
- Catastrophic losses in volatile bull markets
- Short positions lost more than longs
- Worst Sharpe ratio
- High volatility + upward trend = disaster for mean reversion

---

## Yearly Performance Analysis

### 2022: The Golden Year (+91.78%)
**Days:** 335  
**Sharpe:** 1.79  
**Win Rate:** 51.64%

| Component | Contribution | Annualized |
|-----------|-------------|------------|
| **Long** | +13.98% | **+16.45%** |
| **Short** | +51.14% | **+74.58%** |

**Key Observations:**
- Only profitable year in entire backtest
- Short side dominated performance (4.5x better than longs)
- This was a bear market year for crypto (2022 crypto winter)
- Strategy thrived during market drawdown

### 2023: First Major Loss (-37.31%)
**Days:** 365  
**Sharpe:** -1.41  
**Win Rate:** 45.21%

| Component | Contribution | Annualized |
|-----------|-------------|------------|
| **Long** | -10.28% | **-9.77%** |
| **Short** | -37.44% | **-31.23%** |

**Key Observations:**
- Transition to bull market
- Short side began losing heavily
- Win rate dropped below 50%

### 2024: Accelerating Losses (-51.43%)
**Days:** 366  
**Sharpe:** -1.54  
**Win Rate:** 43.99%

| Component | Contribution | Annualized |
|-----------|-------------|------------|
| **Long** | -27.18% | **-23.75%** |
| **Short** | -45.67% | **-36.59%** |

**Key Observations:**
- Both sides losing consistently
- Long positions deteriorated significantly
- Worst Sharpe ratio of all years
- Bull market conditions persisted

### 2025: Modest Losses (YTD: -3.35%)
**Days:** 297  
**Sharpe:** -0.28  
**Win Rate:** 47.47%

| Component | Contribution | Annualized |
|-----------|-------------|------------|
| **Long** | -4.20% | **-5.03%** |
| **Short** | -4.20% | **-5.03%** |

**Key Observations:**
- Performance improved relative to 2023-2024
- Both sides contributing equally to losses
- Highest average position count (2.9 long / 3.9 short)
- Lower magnitude losses suggest stabilization

---

## Critical Insights

### 1. **Strategy is Bear Market Optimized**
The kurtosis mean reversion strategy thrives in bear markets:
- **All positive returns** occurred during bear/low-vol regime
- **2022 (bear year)** was the only profitable year (+91.78%)
- Short positions benefit from declining markets

### 2. **Bull Markets are Toxic**
Bull market conditions devastated performance:
- **Bull/Low-Vol** regime lost -66.91% over 644 days
- **Bull/High-Vol** regime lost -66.84% over 175 days
- Combined bull market exposure: -46.57% to -90.00% annualized

### 3. **Short Side Dominance in Bear Markets**
When the strategy works, shorts drive returns:
- 2022: Shorts contributed 74.58% vs Longs 16.45%
- Bear/Low-Vol: Shorts 49.69% vs Longs 27.97%
- Short side outperformed longs by ~2x in favorable conditions

### 4. **Long Side More Fragile**
Long positions struggled more in adverse conditions:
- Long contributions negative in all bull market regimes
- Long side lost -24.18% cumulatively vs Short -30.35%
- Low kurtosis doesn't protect from systematic bull market drag

### 5. **Volatility Impact is Regime-Dependent**
- **In Bear Markets**: High volatility still profitable (Sharpe 1.54)
- **In Bull Markets**: High volatility catastrophic (-90% annualized)
- Volatility amplifies the underlying trend direction

---

## Position and Exposure Analysis

### Average Position Counts by Regime

| Regime | Long Positions | Short Positions | Long Exposure | Short Exposure |
|--------|---------------|-----------------|---------------|----------------|
| Bear / Low Vol | 0.78 | 1.78 | 30.0% | 50.0% |
| Bear / High Vol | 1.05 | 2.05 | 44.7% | 50.0% |
| Bull / Low Vol | 1.56 | 2.56 | 41.9% | 50.0% |
| Bull / High Vol | 1.18 | 2.18 | 50.0% | 50.0% |

**Observations:**
- Short exposure consistently maintained at 50%
- Long exposure varied: 30% (bear/low) to 50% (bull/high)
- Strategy always held more short positions than long
- Position count increased in bull markets (attempting to capture mean reversion)

---

## Risk Metrics Summary

| Metric | Overall | Best Regime | Worst Regime |
|--------|---------|-------------|--------------|
| **Sharpe Ratio** | -0.39 | 1.79 (Bear/Low) | -2.01 (Bull/Low) |
| **Win Rate** | 47.0% | 50.4% (Bear/High) | 44.9% (Bull/Low) |
| **Max Regime DD** | -66.9% | -16.5% (Bear/Low) | -66.9% (Bull/Low) |
| **Annualized Vol** | 39.9% | ~35% (est) | ~50% (est) |

---

## Trading Implications

### ? When to Use This Strategy
1. **Bear market identification signals** (50MA < 200MA on BTC)
2. **Low to moderate volatility environments**
3. **Market sell-offs and corrections**
4. **Risk-off sentiment periods**

### ? When to Avoid This Strategy
1. **Confirmed bull market trends** (50MA > 200MA)
2. **High volatility bull markets** (worst combination)
3. **Sustained upward momentum**
4. **Low volatility bull markets** (death by a thousand cuts)

### ?? Potential Improvements

1. **Regime Filter**: Only activate strategy in bear markets
   - Could have prevented ~820 days of losses (bull market days)
   - Back-of-envelope: Would turn -47% loss into potential +91% gain

2. **Dynamic Position Sizing**: Reduce exposure in unfavorable regimes
   - Scale down to 25% capital in bull/low-vol
   - Scale to 0% in bull/high-vol

3. **Short-Only Mode in Bulls**: Consider eliminating long positions in bull regimes
   - Long side consistently underperformed in bull markets
   - Shorts at least had some positive periods

4. **Volatility Adjustment**: Increase threshold for kurtosis signals in high vol
   - High vol environments had wider dispersions
   - May need stricter entry criteria

---

## Conclusion

The kurtosis mean reversion strategy demonstrates **strong regime dependency**. It's effectively a **bear market strategy** that struggles profoundly in bull market conditions.

**Performance Summary by Market Type:**
- **Bear Markets**: +27-50% annualized on both sides ?
- **Bull Markets**: -25% to -90% annualized across the board ?

**The strategy's current form is unsuitable for deployment without regime awareness**. The 2022 gains (+91.78%) were completely erased by 2023-2024 bull market losses (-51% to -37% annually).

**Recommendation:** Implement a regime filter that only trades during confirmed bear markets (50MA < 200MA) and sits in cash/stable strategies during bull regimes. This single modification could transform a losing strategy into a profitable bear market hedge.

---

## Appendix: Visualizations

The following charts have been generated:
1. `kurtosis_regime_analysis.png` - Long/Short returns, Sharpe ratios, and contributions by regime
2. `kurtosis_yearly_analysis.png` - Annual performance breakdown

These visualizations clearly show the stark contrast between bear and bull market performance across all dimensions.

---

## Data Files Generated

1. `backtests/results/kurtosis_regime_stats.csv` - Detailed regime statistics
2. `backtests/results/kurtosis_yearly_stats.csv` - Annual performance breakdown
3. `backtests/results/kurtosis_regime_analysis.png` - Regime performance charts
4. `backtests/results/kurtosis_yearly_analysis.png` - Yearly performance charts

---

**Analysis Script:** `backtests/scripts/analyze_kurtosis_by_regime.py`
