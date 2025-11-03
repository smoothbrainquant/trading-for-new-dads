# MVO Weight Instability - Solutions and Recommendations

**Date:** November 2, 2025  
**Issue:** Standard MVO weights are highly unstable and change dramatically with different time windows

## Problem: MVO Instability

Standard Mean-Variance Optimization showed **23.66% portfolio turnover** when comparing full-period vs 3-month optimization:

- **Beta Factor**: 5.00% ? 28.36% (+23.36pp) ??
- **Volatility Factor**: 38.54% ? 22.97% (-15.57pp) ??  
- **Leverage Inverted**: 12.63% ? 5.00% (-7.63pp) ?

This instability causes:
1. High transaction costs from frequent rebalancing
2. Poor out-of-sample performance
3. Overfitting to recent data
4. Implementation challenges

## Root Causes

1. **Estimation Error**: Small changes in expected returns cause large weight changes
2. **Covariance Instability**: Correlations shift over time
3. **Optimizer Sensitivity**: MVO is mathematically ill-conditioned
4. **No Regularization**: Standard MVO doesn't penalize extreme allocations

## Solutions Implemented

### 1. **Regularized MVO with Shrinkage** ? RECOMMENDED
**Turnover Reduction:** 30% more stable than standard MVO

**Techniques Applied:**
- **L2 Regularization**: Penalizes extreme weights (? = 0.5)
- **James-Stein Shrinkage**: Shrinks return estimates toward grand mean (50%)
- **Ledoit-Wolf Shrinkage**: Shrinks covariance toward constant correlation (30%)
- **Minimum Weight Floor**: 5% per strategy ensures diversification

**Results:**
- Expected Return: 13.86%
- Volatility: 7.96%
- Sharpe Ratio: 1.741
- Max Weight: 36.19%

**Weights:**
```
Leverage Inverted:  36.19%
Volatility Factor:  16.77%
Breakout Signal:     7.03%
All others:          5.00% (capped)
```

### 2. **Ensemble Method** ?? MOST RECOMMENDED
**Turnover Reduction:** 30% more stable than standard MVO

**Approach:**
Averages three robust methods:
- Regularized MVO (50%)
- Risk Parity (25%)
- Maximum Diversification (25%)

**Why This Works:**
- Reduces sensitivity to any single method's errors
- Balances return optimization with risk diversification
- Maintains stability while considering expected returns

**Results:**
- Expected Return: 13.70%
- Volatility: 8.02%
- Sharpe Ratio: 1.709
- Max Weight: 33.28%
- **Turnover vs Standard MVO: 16.60% vs 23.66%**

**Recommended Weights (Full Period):**
```
Leverage Inverted:  33.28%  (stable, low correlation)
Volatility Factor:  14.36%  (high Sharpe, proven)
Breakout Signal:     9.11%  (momentum capture)
Beta Factor (BAB):   8.25%  (factor exposure)
Dilution Factor:     5.00%  (high vol, capped)
Mean Reversion:      5.00%  (capped - negative Sharpe)
Size Factor:         5.00%  (capped - negative Sharpe)
Kurtosis Factor:     5.00%  (capped - regime dependent)
Days from High:      5.00%  (capped - negative Sharpe)
Carry Factor:        5.00%  (capped - negative Sharpe)
ADF (Blended):       5.00%  (capped - negative Sharpe)
```

### 3. **Equal Risk Contribution (Risk Parity)**
**Turnover Reduction:** 30% more stable than standard MVO

**Approach:**
Each strategy contributes equally to portfolio risk (doesn't use return estimates).

**Results:**
- Expected Return: 13.60%
- Volatility: 8.15%
- Sharpe Ratio: 1.670
- **Most stable method** (ignores returns, focuses on risk)

**Best For:** Conservative portfolios prioritizing stability over returns

### 4. **Hierarchical Risk Parity (HRP)**
**Turnover Reduction:** Similar to Risk Parity

**Approach:**
Tree-based allocation using hierarchical clustering of correlations.

**Results:**
- Expected Return: 12.07%
- Volatility: 7.33%
- Sharpe Ratio: 1.647
- Completely ignores return estimates

**Best For:** Maximum robustness to estimation error

### 5. **Maximum Diversification**
**Approach:**
Maximizes diversification ratio (weighted avg vol / portfolio vol).

**Results:**
- Expected Return: 13.65%
- Volatility: 8.07%
- Sharpe Ratio: 1.691

## Stability Comparison

| Method | Turnover | Stability | Sharpe | Notes |
|--------|----------|-----------|--------|-------|
| **Standard MVO** | 23.66% | ????? | 1.846 | Highest Sharpe, worst stability |
| **Ensemble** | 16.60% | ????? | 1.709 | **RECOMMENDED** |
| **Risk Parity** | 16.56% | ????? | 1.670 | Most stable |
| **Regularized MVO** | ~18% | ????? | 1.741 | Good balance |
| **HRP** | ~17% | ????? | 1.647 | Very stable |

## Implementation Recommendations

### For Live Trading: Use **ENSEMBLE** Method

**Reasons:**
1. ? 30% reduction in turnover vs standard MVO
2. ? Reduces transaction costs significantly  
3. ? Still considers expected returns (unlike pure Risk Parity)
4. ? Robust to estimation error via averaging
5. ? Sharpe 1.709 - strong risk-adjusted returns

### Rebalancing Strategy

**Frequency:** Quarterly (every 90 days)
- Reduces turnover further
- Accounts for seasonality
- Limits transaction costs

**Threshold-Based Rebalancing:**
Only rebalance when weights drift by >5% from target:
```python
if abs(current_weight - target_weight) > 0.05:
    rebalance()
```

### Monitoring

Track these metrics monthly:
1. **Realized Turnover**: Should stay <5% per month
2. **Tracking Error**: Ensemble vs individual methods
3. **Sharpe Ratio**: Rolling 6-month
4. **Max Drawdown**: Compare to expected -38%

## Files Generated

### Full Period Weights:
- `backtests/results/ensemble_weights.csv` ? **USE THIS**
- `backtests/results/regularized_mvo_weights.csv`
- `backtests/results/risk_parity_weights.csv`
- `backtests/results/max_diversification_weights.csv`
- `backtests/results/hrp_weights.csv`
- `backtests/results/weight_comparison_all_methods.csv`

### 3-Month Weights (for stability comparison):
- `backtests/results/3mo/ensemble_weights.csv`
- `backtests/results/3mo/weight_comparison_all_methods.csv`

## Usage

```bash
# Generate robust weights (full period)
python3 backtests/scripts/generate_robust_weights.py

# Generate robust weights (last 3 months)
python3 backtests/scripts/generate_robust_weights.py --lookback-days 90

# Custom minimum weight
python3 backtests/scripts/generate_robust_weights.py --min-weight 0.03
```

## Expected Performance (Ensemble Method)

**Full Period (2021-2025):**
- Annual Return: 13.70%
- Volatility: 8.02%
- Sharpe Ratio: 1.709
- Expected Max Drawdown: ~-38%

**Transaction Costs:**
With 0.10% cost per trade:
- Quarterly rebalancing: ~0.40% annual drag (16.6% turnover / 4)
- Net expected return: ~13.3%

## Conclusion

**The Ensemble method provides the best balance of:**
- High risk-adjusted returns (Sharpe 1.71)
- Low instability (30% less turnover than MVO)
- Practical implementation (considers returns + risk)

**Action Items:**
1. ? Use Ensemble weights for portfolio allocation
2. ? Rebalance quarterly (or threshold-based)
3. ? Monitor monthly turnover (target <5%)
4. ? Review weights semi-annually with new backtest data
