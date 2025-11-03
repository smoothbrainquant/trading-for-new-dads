# Ensemble Weights Update - November 2, 2025

## Summary

Updated `execution/all_strategies_config.json` with **Ensemble Method** weights - a robust optimization approach that is **30% more stable** than standard MVO.

## New Strategy Allocation

| Strategy | Weight | Change | Notes |
|----------|--------|--------|-------|
| **leverage_inverted** | 33.28% | +28.28pp ⬆️ | Largest allocation - low correlation diversifier |
| **volatility** | 14.36% | +8.73pp ⬆️ | High Sharpe 1.08, proven performer |
| **breakout** | 9.11% | -5.75pp ⬇️ | Reduced but still meaningful |
| **beta** | 8.25% | -7.92pp ⬇️ | Moderate allocation |
| **dilution** | 5.00% | 0.00pp → | Unchanged (capped at 5%) |
| **size** | 5.00% | -17.49pp ⬇️ | Capped due to negative Sharpe (-0.41) |
| **mean_reversion** | 5.00% | +0.50pp ⬆️ | Capped due to negative Sharpe (-0.16) |
| **carry** | 5.00% | +5.00pp ⬆️ | Now active (was 0%) |
| **kurtosis** | 5.00% | +0.50pp ⬆️ | Capped (regime-dependent) |
| **days_from_high** | 5.00% | +5.00pp ⬆️ | Now active (was 0%) |
| **adf** | 5.00% | -16.85pp ⬇️ | Capped due to negative Sharpe (-0.03) |
| **trendline_breakout** | 0.00% | 0.00pp → | Not included |
| **TOTAL** | **100.00%** | ✅ | Valid allocation |

## Portfolio Metrics

**Ensemble Method Performance:**
- **Expected Return:** 13.70% annually
- **Volatility:** 8.02%
- **Sharpe Ratio:** 1.709 ⭐ (Excellent)
- **Max Drawdown:** -38%
- **Stability:** 30% more stable than standard MVO

## Optimization Method

**Ensemble = Average of 3 Methods:**
1. **Regularized MVO** (with L2 penalty + shrinkage)
2. **Risk Parity** (equal risk contribution)
3. **Maximum Diversification** (maximize diversification ratio)

**Shrinkage Applied:**
- James-Stein shrinkage on returns (50% towards grand mean)
- Ledoit-Wolf shrinkage on covariance (30% towards constant correlation)

**Constraints:**
- 5% minimum weight per strategy (ensures diversification)
- Negative Sharpe strategies capped at 5%
- Regime-dependent strategies (Kurtosis) capped at 5%

## Key Changes Explained

### Major Increases

1. **Leverage Inverted: 5% → 33.28% (+28pp)**
   - Reason: Low correlation with other strategies (excellent diversifier)
   - Sharpe: 0.795 (strong risk-adjusted returns)
   - Stability: Consistently performs across time windows

2. **Volatility: 5.63% → 14.36% (+9pp)**
   - Reason: Highest Sharpe ratio (1.08) among all strategies
   - Proven performer with 230% total return
   - Low correlation with most strategies

### Major Decreases

1. **Size: 22.49% → 5.00% (-17pp)**
   - Reason: Negative Sharpe (-0.41) in recent period
   - Capped at 5% minimum for diversification

2. **ADF: 21.85% → 5.00% (-17pp)**
   - Reason: Negative Sharpe (-0.03) in recent period
   - Trend-following premium not performing well
   - Capped at 5% minimum for diversification

3. **Beta: 16.17% → 8.25% (-8pp)**
   - Reason: Moderate Sharpe (0.17), reduced allocation
   - Still meaningful exposure for factor diversification

### Newly Activated

1. **Carry: 0% → 5%**
   - Previously excluded, now at 5% minimum

2. **Days from High: 0% → 5%**
   - Previously excluded, now at 5% minimum

## Stability Analysis

**Turnover Comparison (Full Period vs 3-Month Window):**

| Method | Turnover | Stability |
|--------|----------|-----------|
| Standard MVO | 23.66% | ★☆☆☆☆ Poor |
| **Ensemble** | **16.60%** | **★★★★☆ Good** |
| Risk Parity | 16.56% | ★★★★★ Excellent |

**Improvement:** 30% reduction in turnover vs standard MVO

**Benefits:**
- Lower transaction costs
- More stable allocations over time
- Reduced overfitting to recent data
- Better out-of-sample performance

## Files Updated

1. ✅ **`execution/all_strategies_config.json`** - Main configuration file
   - Updated `strategy_weights` section
   - Updated `_weights_note` section
   - Added `_2025_11_02_ENSEMBLE_ROBUST` to history

## Related Files

- **`backtests/results/ensemble_weights.csv`** - Source data
- **`docs/MVO_STABILITY_SOLUTIONS.md`** - Full methodology
- **`backtests/scripts/generate_robust_weights.py`** - Generation script

## Implementation Notes

**For Live Trading:**
- Rebalance quarterly (every 90 days) to minimize turnover
- Use threshold-based rebalancing (only rebalance if drift >5%)
- Monitor monthly turnover (target <5% per month)
- Expected transaction costs: ~0.4% annual drag (with quarterly rebalancing)

**Monitoring:**
- Track realized Sharpe ratio (rolling 6-month)
- Compare to expected metrics
- Review weights semi-annually with updated backtest data

## Next Steps

1. ✅ Weights updated in config file
2. ⏭️ Deploy to live trading system
3. ⏭️ Monitor performance vs expectations
4. ⏭️ Review quarterly for rebalancing needs

---

**Updated:** November 2, 2025  
**Method:** Ensemble (Regularized MVO + Risk Parity + Max Diversification)  
**Sharpe:** 1.709  
**Stability:** 30% improvement vs standard MVO
