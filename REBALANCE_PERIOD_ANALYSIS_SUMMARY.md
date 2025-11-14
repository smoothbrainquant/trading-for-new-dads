# Days From High Strategy - Rebalance Period Analysis

## Overview
This analysis tests different rebalance periods for the "Days from High" momentum strategy to determine optimal holding periods. The strategy selects instruments within 20 days of their 200-day high and uses risk parity weighting (inverse volatility).

## Test Configuration
- **Strategy**: Days from 200d High (20-day threshold)
- **Data**: Top 10 markets, 500 days of daily data
- **Period**: January 27, 2025 - October 23, 2025 (270 trading days)
- **Initial Capital**: $10,000
- **Rebalance Periods Tested**: [1, 2, 3, 5, 7, 10, 30] trading days

## Results Summary

| Rebalance Period | Final Value | Total Return | Annualized Return | Sharpe Ratio | Max Drawdown | Win Rate | Num Rebalances |
|-----------------|-------------|--------------|-------------------|--------------|--------------|----------|----------------|
| **1 day** | $8,495.54 | -15.04% | -19.79% | -0.40 | -29.59% | 29.00% | 135 |
| **2 days** | $8,602.17 | -13.98% | -18.43% | -0.38 | -26.03% | 29.00% | 90 |
| **3 days** ⭐ | $9,266.79 | **-7.33%** | **-9.79%** | **-0.19** | -28.07% | 30.48% | 68 |
| **5 days** | $7,752.61 | -22.47% | -29.13% | -0.61 | -27.22% | 29.00% | 45 |
| **7 days** | $8,073.94 | -19.26% | -25.13% | -0.47 | -35.51% | 29.74% | 34 |
| **10 days** | $9,164.45 | -8.36% | -11.13% | -0.23 | -29.38% | 31.23% | 25 |
| **30 days** | $7,424.08 | -25.76% | -33.16% | -0.61 | -33.86% | 31.97% | 9 |

## Key Findings

### 🏆 Best Performing Rebalance Period: **3 Days**
- **Best Total Return**: -7.33% (vs. -15.04% for daily rebalancing)
- **Best Sharpe Ratio**: -0.19 (least negative among all periods)
- **Moderate Trading**: 68 rebalances over 270 days
- **Reduced Transaction Costs**: ~49% fewer rebalances vs. daily

### 📊 Performance Patterns

1. **Very Frequent Rebalancing (1-2 days)**
   - Highest trading costs due to frequent rebalancing
   - Lower returns likely due to whipsawing in/out of positions
   - Daily (1d) had 135 rebalances, 2x more than 3-day period

2. **Optimal Range (3-10 days)** ✅
   - **3-day rebalancing clearly outperforms**
   - 10-day also shows relatively good performance (-8.36% return)
   - Better balance between adapting to market and reducing costs

3. **Infrequent Rebalancing (30 days)**
   - Worst performance (-25.76% return)
   - Unable to adapt quickly to market changes
   - Only 9 rebalances over entire period

### 💡 Insights

1. **Transaction Cost Impact**: More frequent rebalancing (daily, 2-day) appears to hurt performance, suggesting transaction costs and slippage materially impact returns

2. **Signal Decay**: The 3-day sweet spot suggests that the "days from high" signal remains relevant for ~3 trading days before requiring reassessment

3. **Risk-Adjusted Returns**: The 3-day period has the best Sharpe ratio (-0.19), indicating superior risk-adjusted performance

4. **Win Rate Pattern**: Win rate slightly improves with longer holding periods (29% for 1-2 days vs. 32% for 30 days), but this doesn't translate to better returns

### ⚠️ Market Context Note

All rebalance periods showed negative returns during this test period (Jan-Oct 2025), indicating challenging market conditions for this momentum strategy. The analysis focuses on **relative performance** across rebalance periods rather than absolute profitability.

## Recommendations

1. **Use 3-day rebalancing** as the primary strategy
   - Best risk-adjusted returns
   - Reasonable trading frequency (68 rebalances in 270 days)
   - Reduces transaction costs vs. daily rebalancing

2. **Consider 10-day as alternative** for lower turnover environments
   - Second-best performance (-8.36% return)
   - Only 25 rebalances, significantly lower transaction costs
   - Higher win rate (31.23%)

3. **Avoid daily and 30-day extremes**
   - Daily: Too frequent, likely eroded by costs
   - 30-day: Too infrequent, misses market regime changes

## Files Generated

All detailed results are saved in `/workspace/backtests/results/`:

- **Comparison Report**: `rebalance_period_comparison.csv`
- **Individual Period Results**:
  - Portfolio values: `days_from_high_rebalance_{period}d_portfolio.csv`
  - Trade history: `days_from_high_rebalance_{period}d_trades.csv`
  - Metrics: `days_from_high_rebalance_{period}d_metrics.csv`

## Script Location

The analysis script is available at:
`/workspace/backtests/scripts/backtest_days_from_high_rebalance_periods.py`

Run with custom parameters:
```bash
python3 backtests/scripts/backtest_days_from_high_rebalance_periods.py \
  --data-file data/raw/your_data.csv \
  --rebalance-periods "1,2,3,5,7,10,30" \
  --days-threshold 20 \
  --initial-capital 10000
```

---

**Analysis Date**: October 30, 2025  
**Backtest Period**: January 27, 2025 - October 23, 2025 (270 trading days)
