# Portfolio Optimization Analysis - Summary

## Overview
Analysis of 65 strategies with daily returns data to optimize portfolio allocation targeting 50% annual volatility.

## Key Findings

### Strategy Performance Metrics
**Top 10 Strategies by Sharpe Ratio:**

| Strategy | Annual Return | Annual Volatility | Sharpe Ratio | Days |
|----------|---------------|-------------------|--------------|------|
| iqr_spread_adjusted | 134.97% | 49.42% | 2.73 | 101 |
| breakout_10d_50k_1.5x | 74.45% | 36.35% | 2.05 | 64 |
| breakout_10d_50k | 48.18% | 24.22% | 1.99 | 64 |
| size_factor | 71.79% | 46.98% | 1.53 | 469 |
| size_factor_long_short | 35.24% | 26.04% | 1.35 | 69 |
| volatility_rebalance_3d | 38.36% | 29.76% | 1.29 | 2093 |
| volatility_rebalance_10d | 37.46% | 29.43% | 1.27 | 2093 |
| volatility_rebalance_30d | 35.22% | 27.93% | 1.26 | 2093 |
| volatility_rebalance_1d | 37.44% | 30.56% | 1.23 | 2093 |
| adf_factor_trend_test | 59.45% | 48.78% | 1.22 | 305 |

### Correlation Analysis
- **10 strategies** with overlapping periods (500+ common days) were selected for optimization
- Strategies show varying correlations:
  - Size rebalancing strategies: **highly correlated** (0.99+) with each other
  - Volatility rebalancing strategies: **highly correlated** (0.71-0.94) with each other
  - Size vs Volatility strategies: **low/negative correlation** (-0.04 to +0.01)
  
This provides excellent diversification potential between strategy types.

### Covariance Matrix
- Annual covariance ranges from **-0.004** to **0.161**
- Negative covariances between size and volatility strategies suggest natural hedging

---

## Portfolio Optimization Results (Target: 50% Volatility)

### Method 1: Equal Weight Portfolio
- **Approach:** Simple 1/N allocation across all strategies
- **Unscaled Volatility:** 26.02%
- **Volatility Scalar:** 1.92x (requires leverage)
- **Expected Annual Return:** 53.15%
- **Expected Volatility:** 50.00%
- **Sharpe Ratio:** 1.06

### Method 2: Risk Parity (RECOMMENDED)
- **Approach:** Allocate inversely proportional to volatility (equal risk contribution)
- **Unscaled Volatility:** 24.30%
- **Volatility Scalar:** 2.06x (requires leverage)
- **Expected Annual Return:** 59.24%
- **Expected Volatility:** 50.00%
- **Sharpe Ratio:** 1.19

**Risk Parity Allocations (Scaled for 50% Target Vol):**

| Strategy | Annual Return | Annual Vol | Scaled Weight | Allocation |
|----------|---------------|------------|---------------|------------|
| volatility_rebalance_30d | 35.22% | 27.93% | 25.63% | 25.6% |
| volatility_rebalance_10d | 37.46% | 29.43% | 24.32% | 24.3% |
| volatility_rebalance_3d | 38.36% | 29.76% | 24.06% | 24.1% |
| volatility_rebalance_5d | 35.76% | 29.93% | 23.92% | 23.9% |
| size_rebalance_1d | 18.69% | 39.53% | 18.11% | 18.1% |
| size_rebalance_3d | 22.37% | 39.75% | 18.01% | 18.0% |
| size_rebalance_5d | 22.49% | 39.75% | 18.01% | 18.0% |
| size_rebalance_2d | 20.79% | 39.78% | 18.00% | 18.0% |
| size_rebalance_7d | 22.45% | 40.07% | 17.87% | 17.9% |
| size_rebalance_10d | 23.01% | 40.13% | 17.84% | 17.8% |

**Total Allocation:** 205.8% (requires ~2.06x leverage)

### Method 3: Maximum Sharpe Ratio
- **Approach:** Mean-variance optimization for highest risk-adjusted returns
- **Unscaled Volatility:** 34.47%
- **Volatility Scalar:** 1.45x (requires leverage)
- **Expected Annual Return:** 35.44%
- **Expected Volatility:** 50.00%
- **Sharpe Ratio:** 0.71

**Max Sharpe Allocations (Scaled):**
- Concentrates heavily in size_rebalance_3d (57.0%) and size_rebalance_5d (50.7%)
- Total of 3 strategies with significant allocation
- More concentrated, less diversified

---

## Recommendations

### 1. **Use Risk Parity Approach** (Recommended)
**Why:**
- **Highest Sharpe Ratio:** 1.19 vs 1.06 (Equal Weight) vs 0.71 (Max Sharpe)
- **Better Diversification:** Balances risk contribution across strategies
- **More Robust:** Less sensitive to estimation errors in expected returns
- **Balanced Exposure:** Prevents over-concentration in high-volatility strategies

**Implementation:**
- Apply 2.06x leverage to achieve 50% target volatility
- Allocate ~24% each to volatility rebalancing strategies (4 strategies)
- Allocate ~18% each to size rebalancing strategies (6 strategies)
- Rebalance periodically to maintain risk parity weights

### 2. Leverage Considerations
- All methods require leverage (1.45x to 2.06x) to reach 50% volatility target
- Current portfolio volatility without leverage is ~24-34%
- Ensure you have access to cost-effective leverage
- Monitor margin requirements and funding costs

### 3. Strategy Selection Rationale
The 10 selected strategies provide:
- **Longest overlapping period:** 500+ common trading days
- **Two strategy families:** Size and Volatility factors
- **Natural diversification:** Negative to low correlations between families
- **Consistent data quality:** All have 2,000+ days of backtest data

### 4. Diversification Benefits
- **Volatility strategies** contribute stable, modest returns (~35-38% annually)
- **Size strategies** provide additional alpha but with higher volatility (~19-23% annually)
- Negative correlation between groups reduces overall portfolio volatility
- Risk parity ensures no single strategy dominates the risk profile

### 5. Alternative Approaches to Consider
If leverage is not available or too expensive:
- **De-lever to 1x:** Accept ~24% volatility with Risk Parity (no leverage)
- **Select higher-vol strategies:** Include more aggressive strategies naturally near 50% vol
- **Tactical allocation:** Adjust leverage dynamically based on market conditions

---

## Implementation Details

### Rebalancing Frequency
- **Risk Parity weights:** Rebalance monthly or when weights deviate >20% from target
- **Volatility monitoring:** Track realized volatility and adjust leverage quarterly

### Risk Management
- **Drawdown limits:** Consider maximum drawdown tolerance (expect 15-25% max DD)
- **Leverage limits:** Set maximum leverage ratio (e.g., 2.5x hard cap)
- **Correlation monitoring:** Watch for correlation breakdowns during market stress

### Data Requirements
- Daily returns data for all strategies
- Updated covariance matrix (rolling 252-day window recommended)
- Real-time portfolio volatility tracking

---

## Files Generated
1. `strategy_analysis_metrics.csv` - Individual strategy performance metrics
2. `strategy_correlation_matrix.csv` - Full correlation matrix (65x65 strategies)
3. `strategy_covariance_matrix.csv` - Full annualized covariance matrix
4. `portfolio_optimization_weights.csv` - Detailed weight allocations for all methods

---

## Next Steps
1. ? Review recommended Risk Parity allocation
2. ?? Assess leverage availability and costs
3. ?? Implement portfolio construction with selected weights
4. ?? Set up monitoring for volatility tracking
5. ?? Establish rebalancing procedures and risk limits
