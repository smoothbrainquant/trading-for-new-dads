# Mean-Variance Optimization (MVO) Portfolio Weights
## Updated: November 2, 2025 (Latest Run)

## Executive Summary

Completed comprehensive backtest analysis (2023-2025) for **12 strategies** and generated optimal portfolio weights using Mean-Variance Optimization (MVO) with constraints on negative Sharpe and regime-dependent strategies.

**Key Results:**
- **Expected Sharpe Ratio**: 6.389 (exceptionally high due to Dilution Factor)
- **Expected Annual Return**: 121.76%
- **Expected Volatility**: 19.06%
- **Expected Max Drawdown**: -1.61%

**?? Important Note**: The Dilution Factor shows exceptionally high returns (1009% total, 298% annualized) which dominates the optimization. This warrants further investigation for potential data quality issues or overfitting.

## Strategy Allocation

### Core Holdings (94.51%)

| Strategy | Weight | Sharpe | Ann. Return | Status |
|----------|--------|--------|-------------|--------|
| **Beta Factor (BAB)** | 34.58% | 0.560 | 15.06% | Betting Against Beta |
| **Dilution Factor** | 26.18% | 1.848 | 297.86% | ?? Exceptionally high returns |
| **Size Factor** | 18.53% | 0.700 | 14.82% | Long large-cap, short small-cap |
| **Volatility Factor** | 15.22% | 0.316 | 8.32% | Long low vol, short high vol |

### Supporting Strategies (5.50%)

| Strategy | Weight | Sharpe | Ann. Return | Status |
|----------|--------|--------|-------------|--------|
| **Kurtosis Factor** | 5.00% | 0.675 | 10.04% | **CAPPED** - Regime-dependent (bear_only) |
| **Breakout Signal** | 0.50% | 0.465 | 10.94% | Minimal allocation |

### Excluded Strategies (0% Allocation)

| Strategy | Sharpe | Ann. Return | Reason |
|----------|--------|-------------|--------|
| **Regime-Switching (Blended)** | 1.227 | 22.14% | Excluded by optimizer (capped at 35% but given 0%) |
| **Leverage Inverted** | 0.589 | 15.58% | Excluded by optimizer |
| **ADF Factor** | 0.458 | 8.27% | Excluded by optimizer |
| **Mean Reversion** | -0.032 | -2.43% | Negative Sharpe (capped at 5%, optimizer chose 0%) |
| **Days from High** | -0.241 | -18.86% | Negative Sharpe |
| **Carry Factor** | -0.814 | -12.26% | Worst performer |

## Backtest Results (2023-2025)

### Individual Strategy Performance

| Strategy | Total Return | Ann. Return | Sharpe | Sortino | Max DD | Days |
|----------|-------------|-------------|--------|---------|--------|------|
| **Dilution Factor** | 1009.07% | 297.86% | 1.848 | 2.928 | -72.87% | 906 |
| **Regime-Switching (Blended)** | 75.47% | 22.14% | 1.227 | 1.900 | -14.62% | 1027 |
| **Size Factor** | 47.48% | 14.82% | 0.700 | 1.049 | -29.49% | 1027 |
| **Beta Factor (BAB)** | 44.85% | 15.06% | 0.560 | 0.848 | -34.75% | 965 |
| **Breakout Signal** | 31.18% | 10.94% | 0.465 | 0.571 | -25.38% | 955 |
| **ADF Factor** | 25.05% | 8.27% | 0.458 | 0.707 | -25.94% | 1027 |
| **Leverage Inverted** | 15.58% | 5.79% | 0.589 | 0.840 | -8.61% | 1028 |
| **Volatility Factor** | 24.37% | 8.32% | 0.316 | 0.467 | -30.54% | 997 |
| **Kurtosis Factor** | 10.41% | 10.04% | 0.676 | 1.005 | -12.52% | 378 |
| **Mean Reversion** | -1.62% | -2.43% | -0.032 | -0.047 | -62.63% | 242 |
| **Days from High** | -28.00% | -18.86% | -0.243 | -0.340 | -66.64% | 574 |
| **Carry Factor** | -30.77% | -12.26% | -0.814 | -1.119 | -35.24% | 1027 |

## Strategy Correlation Analysis

### High Correlations (> 0.7)

| Strategy Pair | Correlation | Implication |
|--------------|-------------|-------------|
| Volatility ? Beta | 0.949 | Very strong positive correlation |
| Size ? Volatility | 0.778 | Strong positive correlation |
| Mean Reversion ? Beta | -0.758 | Strong negative correlation |
| Mean Reversion ? Volatility | -0.753 | Strong negative correlation |
| Size ? Beta | 0.712 | Strong positive correlation |
| Mean Reversion ? Days from High | 0.710 | Strong positive correlation |

### Key Insights:
- **Volatility and Beta are nearly redundant** (0.949 correlation) - portfolio includes both at 15.22% and 34.58%
- **Mean Reversion acts as hedge** to Size/Volatility/Beta (-0.7+ correlations)
- **Size, Volatility, and Beta cluster together** (all 0.7+ correlations)

## Capping Strategy

### Strategies Capped at 5%

1. **Kurtosis Factor** (5.00% allocated)
   - **Reason**: Regime-dependent (bear_only filter)
   - **Sharpe**: 0.676 (positive but constrained)
   - **Regime Behavior**: Only trades in bear markets (50MA < 200MA on BTC)
   - **Active Days**: 378/1028 (36.1% bear, 63.9% bull)
   - **MVO Result**: Optimizer chose the maximum allowed (5%)

### Strategies Capped at 5% (Not Allocated)

2. **Mean Reversion** (0.00% allocated)
   - **Reason**: Negative Sharpe ratio
   - **Sharpe**: -0.032
   - **Performance**: -1.62% total return
   - **MVO Result**: Optimizer chose 0% despite 5% cap

3. **Days from High** (0.00% allocated)
   - **Reason**: Negative Sharpe ratio
   - **Sharpe**: -0.243
   - **Performance**: -28.00% total return
   - **MVO Result**: Optimizer chose 0%

4. **Carry Factor** (0.00% allocated)
   - **Reason**: Worst performer with strongly negative Sharpe
   - **Sharpe**: -0.814
   - **Performance**: -30.77% total return
   - **MVO Result**: Optimizer chose 0%

### Regime-Switching Strategy (Capped at 35%)

**Regime-Switching (Blended)** (0.00% allocated)
- **Cap**: 35% (to ensure diversification given newness of strategy)
- **Sharpe**: 1.227 (second highest)
- **Ann. Return**: 22.14%
- **MVO Result**: Surprisingly chose 0% despite excellent metrics
- **Likely Reason**: High correlation with other strategies already in portfolio

## Optimization Methodology

### Approach
1. Collected daily returns from all 12 strategy backtests (2023-2025)
2. Calculated expected returns (annualized mean) and covariance matrix
3. Performed constrained optimization to maximize Sharpe ratio
4. Applied strategy caps:
   - Negative Sharpe strategies: max 5%
   - Regime-dependent strategies (Kurtosis): max 5%
   - Regime-switching strategies: max 35%
   - Minimum weight: 0% (no forced allocation)

### Constraints
- Weights sum to 100%
- No short positions (all weights ? 0)
- Strategy caps enforced through bounds
- Optimization method: Sequential Least Squares Programming (SLSQP)

### Objective Function
Maximize portfolio Sharpe ratio:
```
Sharpe = (Portfolio Return - Risk Free Rate) / Portfolio Volatility
```
Where:
- Portfolio Return = weighted sum of strategy returns
- Portfolio Volatility = sqrt(weights' ? Covariance Matrix ? weights)
- Risk Free Rate = 0% (assumed)

## Key Observations

### 1. Dilution Factor Dominance
The Dilution Factor's exceptional performance (1009% total return, Sharpe 1.848) dominates the optimization, receiving 26.18% allocation. This warrants investigation:
- Is the backtest period representative?
- Are there data quality issues?
- Is there potential overfitting to recent conditions?
- Max drawdown of -72.87% suggests high volatility despite high returns

### 2. Regime-Switching Exclusion
Despite strong metrics (Sharpe 1.227, 22% return), Regime-Switching received 0% allocation. Possible reasons:
- Correlation with existing positions
- Optimizer prefers other strategies given covariance structure
- Cap at 35% may not have been the binding constraint

### 3. Volatility-Beta Redundancy
Volatility and Beta have 0.949 correlation but both received significant allocations (15.22% and 34.58%). This suggests:
- Both strategies contribute to portfolio optimization despite correlation
- May benefit from consolidating or choosing one

### 4. Leverage Inverted Exclusion
Despite positive Sharpe (0.589) and low correlation with many strategies, received 0% allocation. May be worth investigating separately.

## Comparison with Previous Allocation

### Previous (from Nov 2 earlier):
- Size Factor: 36.00%
- Breakout Signal: 25.77%
- Beta Factor: 23.72%
- Kurtosis: 5.00%
- Mean Reversion: 5.00%
- Volatility: 3.98%
- Days from High: 0.52%

### Current (Latest Run):
- Beta Factor: 34.58%
- Dilution Factor: 26.18% ?? (new/added)
- Size Factor: 18.53%
- Volatility Factor: 15.22%
- Kurtosis Factor: 5.00%
- Breakout Signal: 0.50%
- Others: 0.00%

### Key Differences:
1. **Dilution Factor added**: 26.18% allocation (wasn't in previous run or had different data)
2. **Regime-Switching excluded**: 0% despite strong performance
3. **Beta increased**: 23.72% ? 34.58%
4. **Size decreased**: 36.00% ? 18.53%
5. **Breakout significantly reduced**: 25.77% ? 0.50%

## Implementation Recommendations

### Immediate Actions
1. ? Generated MVO optimization results
2. ?? **INVESTIGATE Dilution Factor** - verify data quality and backtest methodology
3. ?? **REVIEW Regime-Switching exclusion** - consider forced minimum allocation given strong standalone metrics
4. ?? **EVALUATE Volatility-Beta overlap** - consider consolidating given 0.949 correlation

### Before Production Deployment
1. **Validate Dilution Factor backtest**:
   - Review data sources
   - Check for lookahead bias
   - Verify signal generation logic
   - Analyze out-of-sample performance
   
2. **Consider Alternative Allocations**:
   - Force-include Regime-Switching at 10-15%
   - Cap Dilution Factor at 15-20% until validated
   - Evaluate Leverage Inverted separately
   
3. **Address Correlation Clustering**:
   - Consider choosing one of Volatility/Beta (given 0.949 correlation)
   - Or reduce allocations proportionally

### Monitoring Requirements
1. Track Dilution Factor performance vs. backtest expectations
2. Monitor regime transitions for Kurtosis strategy activation
3. Compare realized Sharpe ratio vs. expected (6.389 is very high)
4. Re-evaluate correlations quarterly - they may shift in different market regimes

## Files Generated

- `backtests/results/all_backtests_summary.csv` - Strategy performance metrics (12 strategies)
- `backtests/results/all_backtests_daily_returns.csv` - Daily returns (1028 days ? 12 strategies)
- `backtests/results/all_backtests_sharpe_weights.csv` - Sharpe-weighted allocation (baseline)
- `backtests/results/mvo_weights.csv` - **MVO optimal weights (THIS RUN)**
- `backtests/results/mvo_correlation.csv` - Strategy correlation matrix
- `docs/MVO_WEIGHTS_2025_11_02_UPDATED.md` - This summary document

## Conclusion

The MVO optimization produced a portfolio with exceptional expected metrics:
- **Sharpe Ratio**: 6.389 (extremely high, warrants scrutiny)
- **Annual Return**: 121.76%
- **Volatility**: 19.06%
- **Max Drawdown**: -1.61%

**However, these results are driven largely by the Dilution Factor's exceptional performance, which requires validation before production deployment.**

### Recommended Path Forward:

**Option 1: Conservative (Recommended)**
- Cap Dilution Factor at 15%
- Force-include Regime-Switching at 10%
- Rerun MVO with adjusted constraints
- Expected result: More balanced, 30-40% annual return, Sharpe ~1.5

**Option 2: Moderate**
- Use current MVO but with 20% cap on Dilution
- Add 5% forced minimum for Regime-Switching
- Rebalance monthly to validate Dilution performance

**Option 3: Aggressive (Current MVO)**
- Deploy current allocation
- Monitor Dilution Factor closely
- Prepare contingency to reduce if underperforms

**Validation is critical before deploying this allocation to real capital.**
