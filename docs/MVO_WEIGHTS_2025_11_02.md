# Mean-Variance Optimization (MVO) Portfolio Weights
## Updated: November 2, 2025

## Executive Summary

Completed comprehensive backtest analysis (2023-2025) for all strategies and generated optimal portfolio weights using Mean-Variance Optimization (MVO) with constraints on negative/non-performing and regime-dependent strategies.

**Key Results:**
- **Expected Sharpe Ratio**: 1.284 (significant improvement from previous 0.891)
- **Expected Annual Return**: 16.30%
- **Expected Volatility**: 12.70%
- **Expected Max Drawdown**: -30.72%

## Strategy Allocation

### Core Holdings (85.5%)

| Strategy | Weight | Sharpe | Status |
|----------|--------|--------|--------|
| **Size Factor** | 36.00% | 0.700 | Long large-cap, short small-cap |
| **Breakout Signal** | 25.77% | 0.465 | Entry: 50d, Exit: 70d |
| **Beta Factor (BAB)** | 23.72% | 0.560 | Betting Against Beta |

### Supporting Strategies (14.5%)

| Strategy | Weight | Sharpe | Status |
|----------|--------|--------|--------|
| **Kurtosis Factor** | 5.00% | 0.676 | **CAPPED** - Regime-dependent (bear_only) |
| **Mean Reversion** | 5.00% | -0.032 | **CAPPED** - Negative Sharpe |
| **Volatility Factor** | 3.98% | 0.316 | Diversification benefit |
| **Days from High** | 0.52% | -0.243 | **CAPPED** - Negative Sharpe |
| **Carry Factor** | 0.00% | -0.814 | **EXCLUDED** - Worst performer |

### Excluded Strategies

| Strategy | Reason |
|----------|--------|
| **ADF Factor** | Backtest error (index out of bounds) |
| **Trendline Breakout** | Not analyzed in this cycle |

## Backtest Results (2023-2025)

### Individual Strategy Performance

| Strategy | Total Return | Ann. Return | Sharpe | Sortino | Max DD | Days |
|----------|-------------|-------------|--------|---------|--------|------|
| Size Factor | 47.48% | 14.82% | 0.700 | 1.049 | -29.49% | 1027 |
| Kurtosis Factor | 10.41% | 10.04% | 0.676 | 1.005 | -12.52% | 378 |
| Beta Factor (BAB) | 44.85% | 15.06% | 0.560 | 0.848 | -34.75% | 965 |
| Breakout Signal | 31.18% | 10.94% | 0.465 | 0.571 | -25.38% | 955 |
| Volatility Factor | 24.37% | 8.32% | 0.316 | 0.467 | -30.54% | 997 |
| Mean Reversion | -1.62% | -2.43% | -0.032 | -0.047 | -62.63% | 242 |
| Days from High | -28.00% | -18.86% | -0.243 | -0.340 | -66.64% | 574 |
| Carry Factor | -30.77% | -12.26% | -0.814 | -1.119 | -35.24% | 1027 |

## Capping Strategy

### Strategies Capped at 5%

1. **Kurtosis Factor** (5%)
   - **Reason**: Regime-dependent (bear_only filter)
   - **Sharpe**: 0.676 (positive but constrained)
   - **Regime Behavior**: Only trades in bear markets (50MA < 200MA on BTC)
   - **Active Days**: 378/1028 (36.1% bear, 63.9% bull)

2. **Mean Reversion** (5%)
   - **Reason**: Negative Sharpe ratio
   - **Sharpe**: -0.032
   - **Performance**: -1.62% total return

3. **Days from High** (0.52%)
   - **Reason**: Negative Sharpe ratio
   - **Sharpe**: -0.243
   - **Performance**: -28.00% total return
   - **Note**: MVO reduced to minimal allocation

4. **Carry Factor** (0%)
   - **Reason**: Worst performer with strongly negative Sharpe
   - **Sharpe**: -0.814
   - **Performance**: -30.77% total return
   - **Note**: MVO excluded entirely

## Strategy Correlation Analysis

Key correlation insights:

- **Breakout Signal**: Near-zero correlation with Size (0.028) and Beta (0.012) ? excellent diversifier
- **Volatility Factor**: High correlation with Beta (0.570) ? included at 3.98% for additional diversification
- **Kurtosis Factor**: Moderate correlation with Breakout (0.280) and Beta (0.164)

## Optimization Methodology

### Approach
1. Collected daily returns from all strategy backtests (2023-2025)
2. Calculated expected returns (annualized mean) and covariance matrix
3. Performed constrained optimization to maximize Sharpe ratio
4. Applied strategy caps:
   - Negative Sharpe strategies: max 5%
   - Regime-dependent strategies: max 5%
   - Minimum weight: 0% (no forced allocation)

### Constraints
- Weights sum to 100%
- No short positions (all weights ? 0)
- Strategy caps enforced through bounds
- Optimization method: Sequential Least Squares Programming (SLSQP)

## Portfolio Metrics Comparison

| Metric | Previous (V1) | Current (V2) | Improvement |
|--------|--------------|--------------|-------------|
| Sharpe Ratio | 0.891 | 1.284 | +44.1% |
| Expected Return | 13.62% | 16.30% | +19.7% |
| Expected Volatility | 15.29% | 12.70% | -16.9% |
| Expected Max DD | -30.27% | -30.72% | -1.5% |

## Implementation Notes

### Updated Files
- `/workspace/execution/all_strategies_config.json` - Updated strategy weights
- `/workspace/backtests/results/mvo_weights.csv` - MVO optimization results
- `/workspace/backtests/results/mvo_correlation.csv` - Strategy correlation matrix
- `/workspace/backtests/results/all_backtests_summary.csv` - Individual backtest results
- `/workspace/backtests/results/all_backtests_daily_returns.csv` - Daily returns for MVO

### Key Changes from Previous Allocation
1. **Reduced Size Factor**: 45.43% ? 36.00% (still largest holding)
2. **Reduced Breakout**: 32.23% ? 25.77% (increased diversification)
3. **Increased Beta**: 22.34% ? 23.72% (strong risk-adjusted returns)
4. **Added Kurtosis**: 0% ? 5.00% (capped, regime-dependent)
5. **Added Mean Reversion**: 0% ? 5.00% (capped, negative Sharpe)
6. **Added Volatility**: 0% ? 3.98% (diversification benefit)
7. **Added Days from High**: 0% ? 0.52% (minimal allocation)

### Regime-Dependent Strategy: Kurtosis
- **Filter**: bear_only (only trades when 50MA < 200MA on BTC)
- **Rationale**: Strong performance in bear markets (Sharpe 1.79) but toxic in bull markets (Sharpe -2.5)
- **Cap Justification**: 5% ensures exposure to bear market alpha while limiting risk from regime shifts

## Validation

### Backtest Quality
- **Data Period**: 2023-01-01 to 2025-10-23 (1027 days)
- **Implementation**: Vectorized backtests (30-50x faster)
- **Lookahead Bias**: Avoided via next-day returns (`.shift(-1)`)
- **Transaction Costs**: Not explicitly modeled (risk-parity/equal weight reduce turnover)

### Risk Considerations
1. **Backtested Period**: 2023-2025 includes both bull and bear markets
2. **Out-of-Sample Risk**: Future performance may differ
3. **Regime Shifts**: Kurtosis strategy only active in bear markets
4. **Correlation Risk**: Some strategies have moderate correlation (Volatility-Beta: 0.570)

## Recommendations

### Immediate Actions
1. ? Updated `all_strategies_config.json` with new weights
2. ? Generated MVO optimization results
3. ? Applied 5% caps to negative/regime-dependent strategies

### Monitoring
1. Track realized Sharpe ratio vs. expected (1.284)
2. Monitor Kurtosis strategy activation (regime filter)
3. Review correlation stability across market conditions
4. Re-optimize weights quarterly with updated backtest data

### Future Enhancements
1. Fix ADF strategy backtest error for potential inclusion
2. Analyze Trendline Breakout strategy
3. Consider transaction cost modeling
4. Implement dynamic regime detection for Kurtosis allocation

## Files Generated

- `backtests/results/all_backtests_summary.csv` - Strategy performance metrics
- `backtests/results/all_backtests_daily_returns.csv` - Daily returns (1027 days ? 8 strategies)
- `backtests/results/all_backtests_sharpe_weights.csv` - Sharpe-weighted allocation (baseline)
- `backtests/results/mvo_weights.csv` - MVO optimal weights
- `backtests/results/mvo_correlation.csv` - Strategy correlation matrix
- `docs/MVO_WEIGHTS_2025_11_02.md` - This summary document

## Conclusion

The MVO optimization with strategy caps has produced a robust portfolio allocation with:
- **44% improvement in Sharpe ratio** (0.891 ? 1.284)
- **Better diversification** across 7 strategies (vs. 3 previously)
- **Risk management** via 5% caps on negative/regime-dependent strategies
- **Strong expected performance**: 16.30% return, 12.70% volatility

The allocation balances high-conviction strategies (Size, Breakout, Beta at 85.5%) with diversifying strategies (Volatility at 3.98%) and risk-managed exposure to negative performers (capped at 5%) and regime-dependent strategies (Kurtosis at 5%).
