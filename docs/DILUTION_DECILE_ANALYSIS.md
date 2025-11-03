# Dilution Factor Decile Analysis

**Date:** November 3, 2025  
**Analysis Period:** February 2021 - October 2025 (4.75 years)  
**Universe:** Top 150 coins by market cap with dilution data  
**Rebalancing:** Monthly  
**Weighting:** Equal-weighted within deciles

---

## Executive Summary

This analysis examines the relationship between token dilution velocity and returns by sorting coins into 10 deciles based on their 12-month rolling dilution rates. The results reveal **complex, non-monotonic patterns** rather than a simple linear relationship.

### Key Findings

1. **Decile 2 Dominates**: The second-lowest dilution decile dramatically outperformed all others with **+118.9% annualized returns** and a **1.00 Sharpe ratio** - the only positive Sharpe in the entire analysis.

2. **Lowest Dilution Underperforms**: Surprisingly, Decile 1 (lowest dilution) had the worst performance at **-27.5% annualized returns** and **-97.96% max drawdown**.

3. **No Clear Linear Pattern**: There is no monotonic relationship between dilution and returns across deciles, suggesting dilution alone is insufficient as a factor.

4. **High Dilution Mixed Results**: Decile 10 (highest dilution) performed poorly but better than D1 at **-11.1% annualized returns**.

5. **Top Individual Winners**: Individual top performers like HBAR (+54.9% per period), SHIB (+28.1%), and XRP (+19.4%) span multiple deciles, indicating stock selection matters more than systematic decile exposure.

---

## Decile Performance Summary

| Decile | Dilution Category | Ann. Return | Sharpe | Max DD | Volatility | Days |
|--------|------------------|-------------|--------|--------|------------|------|
| **D1** | Lowest Dilution | **-27.52%** | -0.26 | -97.96% | 106.31% | 1,616 |
| **D2** | Very Low | **+118.86%** | **1.00** | -90.20% | 118.84% | 1,700 |
| **D3** | Low | -24.83% | -0.31 | -93.57% | 79.47% | 1,615 |
| **D4** | Low-Med | -19.81% | -0.23 | -93.54% | 86.19% | 1,677 |
| **D5** | Medium | +38.40% | 0.42 | -88.21% | 91.98% | 1,704 |
| **D6** | Med-High | -3.75% | -0.04 | -90.80% | 95.93% | 1,705 |
| **D7** | High | -45.30% | -0.42 | -98.86% | 108.88% | 1,570 |
| **D8** | Very High | -19.36% | -0.17 | -94.28% | 111.68% | 1,579 |
| **D9** | Extreme | -23.71% | -0.23 | -92.99% | 103.26% | 1,243 |
| **D10** | Highest Dilution | -11.06% | -0.10 | -92.86% | 106.34% | 1,707 |

### Observations

- **Only 2 positive Sharpe ratios**: Deciles 2 and 5
- **Extreme drawdowns**: All deciles experienced >88% max drawdowns
- **High volatility**: All deciles showed >79% annualized volatility
- **Non-linearity**: No monotonic relationship between dilution rank and returns

---

## Top 10 Individual Performers

| Rank | Symbol | Avg Period Return | Dilution Velocity (% / yr) | Typical Decile | Periods |
|------|--------|------------------|----------------------------|----------------|---------|
| 1 | **HBAR** | +54.85% | 13.03 | D8 (Very High) | 5 |
| 2 | **SHIB** | +28.15% | 1.30 | D1 (Lowest) | 26 |
| 3 | **XRP** | +19.37% | 3.37 | D5 (Medium) | 24 |
| 4 | **ENA** | +16.73% | 30.85 | D10 (Highest) | 5 |
| 5 | **JASMY** | +11.35% | 1.94 | D3 (Low) | 24 |
| 6 | **BONK** | +10.73% | 16.88 | D9 (Extreme) | 21 |
| 7 | **ZEC** | +9.83% | 6.65 | D8 (Very High) | 57 |
| 8 | **SUI** | +9.81% | 13.63 | D9 (Extreme) | 28 |
| 9 | **XLM** | +7.39% | 4.39 | D5 (Medium) | 57 |
| 10 | **FET** | +7.22% | 24.92 | D10 (Highest) | 28 |

### Key Insights

- **Winners span all deciles**: Top performers include coins from D1 (SHIB), D3 (JASMY), D5 (XRP, XLM), D8 (HBAR, ZEC), D9 (BONK, SUI), and D10 (ENA, FET)
- **High dilution can win**: 4 of top 10 are from high dilution deciles (D8-D10)
- **HBAR dominated**: Despite being in D8 (very high dilution), HBAR had the highest returns
- **Meme coins present**: SHIB and BONK both appear in top 10, suggesting narrative trumps dilution

---

## Bottom 10 Individual Performers

| Rank | Symbol | Avg Period Return | Dilution Velocity (% / yr) | Typical Decile | Periods |
|------|--------|------------------|----------------------------|----------------|---------|
| 1 | **FARTCOIN** | -21.38% | 0.00 | D2 | 5 |
| 2 | **SPX** | -20.97% | 0.00 | D2 | 2 |
| 3 | **STRK** | -9.75% | 18.97 | D9 (Extreme) | 19 |
| 4 | **XCN** | -6.88% | 11.57 | D7 (High) | 23 |
| 5 | **APE** | -6.51% | 17.20 | D10 (Highest) | 30 |
| 6 | **RSR** | -6.20% | 7.38 | D6 (Med-High) | 7 |
| 7 | **WIF** | -6.09% | -0.01 | D1 (Lowest) | 11 |
| 8 | **PYTH** | -5.96% | 21.11 | D9 (Extreme) | 9 |
| 9 | **PEPE** | -5.71% | 0.07 | D2 | 11 |
| 10 | **ZK** | -2.63% | 5.24 | D2 | 14 |

### Key Insights

- **Losers also span deciles**: Poor performers from D1 (WIF), D2 (FARTCOIN, SPX, PEPE, ZK), D6-D10
- **New tokens struggle**: Many recent launches (FARTCOIN, SPX, STRK, ZK) had negative returns
- **D2 paradox**: While D2 overall performed best, it contains 4 of bottom 10 performers
- **High dilution risk**: D9-D10 contains 3 of bottom 10 (STRK, APE, PYTH)

---

## Decile 1 vs Decile 10 Comparison

### Decile 1: Lowest Dilution (Most Deflationary)

- **Annualized Return:** -27.52%
- **Sharpe Ratio:** -0.26
- **Max Drawdown:** -97.96%
- **Volatility:** 106.31%

**Interpretation:** The lowest dilution coins had the worst performance. This counterintuitive result suggests:
- Low dilution tokens may be mature, large-cap coins with limited upside
- Sample included Bitcoin-like assets that performed poorly in this period
- Low dilution doesn't guarantee price appreciation

### Decile 10: Highest Dilution (Most Inflationary)

- **Annualized Return:** -11.06%
- **Sharpe Ratio:** -0.10
- **Max Drawdown:** -92.86%
- **Volatility:** 106.34%

**Interpretation:** High dilution coins underperformed but not as severely as D1:
- High dilution creates selling pressure but some tokens compensated with growth
- Better than D1 by +16.46% annually - opposite of hypothesis
- Similar volatility to D1 (~106%)

### Long D1 / Short D10 Strategy

**Return Spread:** -16.46% (D1 underperformed D10)  
**Sharpe Spread:** -0.15 (D1 had worse risk-adjusted returns)

**This would be a LOSING strategy** - the typical "low dilution outperforms" hypothesis **does not hold** in this dataset.

---

## Statistical Analysis

### Decile Distribution

- **Number of periods analyzed:** 57 monthly rebalances
- **Average coins per rebalance:** ~150 eligible coins
- **Data coverage:** 1,243 to 1,707 days per decile
- **Universe:** Top 150 by market cap, filtered for price data availability

### Return Patterns

1. **Best performing decile:** D2 (+118.86%)
2. **Worst performing decile:** D7 (-45.30%)
3. **Median decile return:** -21.81% (between D3 and D8)
4. **Return spread (D2 - D7):** 164.16 percentage points

### Risk Patterns

1. **Lowest volatility:** D3 (79.47%)
2. **Highest volatility:** D2 (118.84%) - coincides with highest returns
3. **Average volatility:** 101.89%
4. **Best Sharpe ratio:** D2 (1.00) - only positive Sharpe

---

## Investment Implications

### What Works

1. **Avoid Systematic Decile Portfolios**: Only D2 and D5 had positive performance; most deciles lost money
2. **Individual Stock Selection Critical**: Top performers span all deciles, suggesting dilution is not the primary driver
3. **D2 Sweet Spot**: Second-lowest dilution decile had exceptional performance, suggesting moderate stability with growth potential
4. **Narrative Matters**: Meme coins (SHIB, BONK) and ecosystem plays (HBAR, SUI) outperformed regardless of dilution

### What Doesn't Work

1. **Simple Long Low / Short High**: Would have lost -16.46% annually
2. **Lowest Dilution Premium**: D1 had worst performance, contradicting typical "deflationary is better" narrative
3. **Linear Factor Assumption**: Non-monotonic relationship invalidates simple factor models
4. **Ignoring Token Economics Context**: Dilution velocity alone doesn't capture growth vs selling pressure dynamics

### Recommended Approach

Rather than pure dilution-based strategies, consider:

1. **Multi-factor models**: Combine dilution with momentum, fundamentals, and narrative
2. **Context-aware dilution**: Distinguish between:
   - **Growth dilution**: Ecosystem expansion (validators, developers)
   - **Unlock dilution**: Pure token unlock selling pressure
   - **Inflation dilution**: Protocol-level emission
3. **Dynamic weighting**: Overweight D2 and D5, avoid D1 and D7
4. **Individual security selection**: Screen for winners across all deciles rather than systematic exposure

---

## Methodological Notes

### Data Quality

- **Price data source:** Combined Coinbase/CoinMarketCap daily prices
- **Dilution data source:** Historical monthly snapshots (2021-2025)
- **Calculation method:** 12-month rolling dilution velocity
- **Filtering:** Top 150 by market cap, coins with sufficient price history

### Limitations

1. **Survivorship bias**: Only includes coins that maintained Top 150 status
2. **Look-ahead bias mitigation**: Used proper signal-to-return lag (monthly rebalance after signal)
3. **Transaction costs not included**: Real-world returns would be lower
4. **Equal weighting**: Results may differ with market-cap or risk-parity weighting
5. **Crypto bear/bull cycles**: Covers 2021-2025 including major bear market of 2022

### Future Work

1. **Conditional analysis**: Separate bull vs bear market performance
2. **Interaction effects**: Test dilution × momentum, dilution × size, dilution × volatility
3. **Nonlinear models**: Machine learning to capture complex patterns
4. **Regime-dependent strategies**: Different dilution strategies for different market conditions
5. **Token type analysis**: Compare L1s, DeFi, memes, stablecoins separately

---

## Conclusion

The dilution factor exhibits **strong non-linearity** and **context-dependence** that makes simple factor strategies ineffective. While **Decile 2** showed exceptional performance (+118.86% annualized), most other deciles lost money, and the **lowest dilution decile (D1) performed worst** at -27.52%.

This suggests that:
- **Dilution velocity alone is insufficient** for a standalone factor
- **Moderate dilution (D2) may signal growth potential** without excessive selling pressure
- **Individual selection within deciles matters more** than systematic decile exposure
- **Multi-factor approaches are necessary** to generate alpha in crypto markets

The **traditional hypothesis that low dilution outperforms high dilution is rejected** for this dataset and time period. Investors should avoid naive long/short dilution strategies and instead focus on context-aware, multi-factor approaches that account for growth dynamics, narratives, and market regimes.

---

## Files Generated

### Data Files
- `dilution_decile_metrics.csv` - Summary metrics for all 10 deciles
- `dilution_top10_names.csv` - Top 10 individual performers with dilution stats
- `dilution_bottom10_names.csv` - Bottom 10 individual performers with dilution stats
- `dilution_individual_coin_returns.csv` - All individual coin returns by rebalance period
- `dilution_decile1_portfolio.csv` through `dilution_decile10_portfolio.csv` - Daily portfolio values for each decile

### Visualizations
- `dilution_decile_comparison.png` - 4-panel comparison of decile performance
- `dilution_top_bottom_names.png` - Side-by-side comparison of top/bottom performers

### Scripts
- `backtest_dilution_decile_analysis.py` - Full analysis script (reproducible)
