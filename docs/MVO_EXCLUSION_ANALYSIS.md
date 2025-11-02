# Why Good Strategies Were Excluded from MVO
## Analysis: Leverage Inverted & Regime-Switching

Date: November 2, 2025

---

## Executive Summary

Two strategies with **positive Sharpe ratios** were excluded (0% allocation) from the MVO optimization:

| Strategy | Sharpe | Return | Reason for Exclusion |
|----------|--------|--------|---------------------|
| **Regime-Switching (Blended)** | 1.227 ? (2nd best) | 24.33% | Dilution Factor dominance |
| **Leverage Inverted** | 0.589 | 5.79% | Too low absolute return |

Both exclusions are **mathematically correct** but raise questions about portfolio construction and the Dilution Factor's validity.

---

## Why Regime-Switching Was Excluded

### Standalone Metrics (Excellent)

```
Sharpe Ratio:      1.227  ? 2nd BEST of all strategies
Annual Return:     24.33% ? Better than most
Volatility:        18.04% ? Moderate
Max Drawdown:      -14.62% ? Low
Total Return:      75.47% ? Strong
Days Active:       1027   ? Full coverage
Correlation:       -0.011 ? Near-zero with allocated portfolio
```

### Why It Got 0% Despite 35% Cap

**The Dilution Factor Problem:**

Dilution Factor returns **12.2x MORE** than Regime-Switching:
- Dilution: 297.86% annual return
- Regime-Switching: 24.33% annual return
- Ratio: **12.2x**

**MVO Logic:**
```
"Every 1% allocated to Regime-Switching must come from somewhere"
"That 1% could be in Dilution (297.86%), Beta (19.97%), or Size (17.64%)"
"All of those have HIGHER returns than Regime-Switching (24.33%)"
"The diversification benefit doesn't offset the return loss"
? Optimal allocation: 0%
```

### Mathematical Proof

Impact on portfolio return if we force Regime-Switching allocation:

| Allocation | Portfolio Return | Change from Current |
|-----------|------------------|---------------------|
| **0%** (current) | **121.76%** | **Optimal** ? |
| 5% | 116.89% | -4.87% |
| 10% | 112.02% | -9.74% |
| 20% | 102.27% | -19.49% |
| 35% | 87.66% | -34.10% ? |

**Every allocation to Regime-Switching REDUCES total return.**

### Understanding the 35% Cap

The 35% cap is a **MAXIMUM**, not a minimum:
- Prevents over-allocation to new/unproven strategies
- Optimizer can choose 0% to 35%
- It chose 0% because that maximizes Sharpe
- Cap would only matter if optimizer wanted **MORE** than 35%

To force inclusion, you need a **minimum allocation** constraint.

---

## Why Leverage Inverted Was Excluded

### Standalone Metrics (Good)

```
Sharpe Ratio:      0.589  ? Positive
Annual Return:     5.79%  ? LOWEST among positive-Sharpe strategies
Volatility:        8.97%  ? Very low
Max Drawdown:      -8.61% ? Excellent
Total Return:      15.58% ? Positive
Days Active:       1028   ? Full coverage
```

### Why It Got 0%

**Too Low Absolute Return:**

Return ranking among positive-Sharpe strategies:
1. Dilution Factor: 297.86%
2. Beta Factor: 19.97%
3. Size Factor: 17.64%
4. Breakout: 14.56%
5. Volatility: 13.47%
6. Kurtosis: 12.11%
7. **Leverage Inverted: 5.79%** ?? **LOWEST**

**MVO Logic:**
```
"Leverage Inverted has decent Sharpe (0.589) from low volatility"
"But 5.79% return is too low compared to alternatives"
"Beta Factor has similar Sharpe (0.560) but 3.5x higher return (19.97%)"
"Size Factor has better Sharpe (0.700) and 3x higher return (17.64%)"
? Optimal allocation: 0%
```

### Mathematical Proof

If we forced 10% to Leverage Inverted:
```
Current: 121.76% expected return
With 10% Leverage: 110.16% expected return
Loss: -11.60%
```

The optimizer correctly excluded it to maximize returns.

---

## Comparison: Different Reasons for Exclusion

| Strategy | Sharpe | Return | Why Excluded? |
|----------|--------|--------|---------------|
| **Leverage Inverted** | 0.589 | 5.79% | **Absolute return too low** - lowest among positive-Sharpe strategies |
| **Regime-Switching** | 1.227 ? | 24.33% | **Dilution dominance** - would reduce returns despite excellent metrics |
| ADF Factor | 0.458 | 8.27% | Low return, moderate Sharpe |

**Key Difference:**
- Leverage excluded for **fundamental reasons** (low returns)
- Regime-Switching excluded due to **one outlier strategy** (Dilution)

---

## The Dilution Factor Distortion

### How Dilution Warps the Optimization

```
Normal MVO behavior:
  ? Balances return, risk, and diversification
  ? Allocates to strategies with best risk-adjusted returns
  ? Sharpe ratio drives allocation decisions

With Dilution Factor (297.86% return):
  ? Absolute return dominates over risk-adjustment
  ? Everything else looks unattractive by comparison
  ? Even excellent strategies (Sharpe 1.227) get excluded
  ? Expected portfolio Sharpe of 6.389 is unrealistic
```

### What If We Removed Dilution?

**Expected allocation WITHOUT Dilution Factor:**

| Strategy | Estimated Weight | Rationale |
|----------|-----------------|-----------|
| Regime-Switching | 25-35% | 2nd best Sharpe (1.227) |
| Beta Factor | 25-30% | Strong returns (19.97%) |
| Size Factor | 20-25% | Good Sharpe (0.700) |
| Kurtosis | 5-10% | Capped (regime-dependent) |
| Others | 5-15% | Diversification |

**Expected portfolio metrics:**
- Return: 18-25% (realistic)
- Sharpe: 1.2-1.5 (realistic)
- Better diversification

---

## How to Include Excluded Strategies

### Option 1: Cap Dilution Factor

```bash
# Limit Dilution to 15% to allow other strategies
python3 backtests/scripts/generate_mvo_weights.py --max-dilution 0.15
```

Expected result:
- Dilution: 15%
- Regime-Switching: 20-25%
- Beta: 20-25%
- Others: 30-40%

### Option 2: Force Minimum Allocations

Modify `generate_mvo_weights.py` to add minimum constraints:

```python
# Force minimum allocations
min_allocations = {
    'Regime-Switching (Blended)': 0.15,  # Force 15% minimum
    'Leverage Inverted': 0.05,            # Force 5% minimum
}

# Add to bounds
for strategy in strategies:
    min_weight = min_allocations.get(strategy, 0.0)
    max_weight = strategy_caps.get(strategy, 1.0)
    bounds.append((min_weight, max_weight))
```

### Option 3: Manual Allocation

Accept lower returns for better diversification:

```
Dilution Factor:       15%
Regime-Switching:      20%
Beta Factor:           20%
Size Factor:           15%
Volatility Factor:     10%
Kurtosis Factor:       10%
Leverage Inverted:      5%
Others:                 5%
```

Expected metrics:
- Return: 25-35%
- Sharpe: 1.3-1.8
- Max Drawdown: -15-25%
- 7-8 strategies active

---

## Recommendations

### Short-Term (Immediate)

1. **Validate Dilution Factor**
   - Review backtest methodology
   - Check for data quality issues
   - Verify no lookahead bias
   - Analyze out-of-sample performance

2. **Cap Dilution at 15-20%**
   - Prevents over-concentration
   - Allows other strategies to participate
   - More realistic return expectations

3. **Force 10-15% to Regime-Switching**
   - Excellent risk-adjusted returns
   - Near-zero correlation with portfolio
   - Proven methodology

### Medium-Term (1-3 months)

1. **Monitor Dilution Performance**
   - Compare actual vs. expected returns
   - If underperforms, reduce allocation
   - If performs well, increase allocation

2. **Re-optimize Monthly**
   - Update with rolling 2-year window
   - Adjust caps based on realized performance
   - Check if Regime-Switching remains excluded

3. **Consider Leverage Inverted Separately**
   - Good defensive characteristics (low vol, low drawdown)
   - Could be valuable during bear markets
   - Track separately for potential tactical allocation

### Long-Term (3-6 months)

1. **Implement Dynamic Allocation**
   - Reduce Dilution if Sharpe drops below 1.5
   - Increase Regime-Switching in volatile markets
   - Use Leverage Inverted for tail risk hedging

2. **Develop Constraint Framework**
   - Min allocation: 5% for positive-Sharpe strategies
   - Max allocation: 25% for any single strategy
   - Force diversification across 6-8 strategies

3. **Regular Backtest Updates**
   - Quarterly re-runs with latest data
   - Track consistency of Dilution Factor
   - Monitor regime-switching effectiveness

---

## Key Takeaways

### For Regime-Switching

? **The strategy is excellent** (Sharpe 1.227, 24.33% return, -0.011 correlation)  
? **But Dilution Factor makes it look unattractive** (12x return difference)  
?? **Solution:** Cap Dilution at 15-20% and force 10-15% minimum for Regime-Switching

### For Leverage Inverted

? **Good risk characteristics** (Sharpe 0.589, -8.61% max DD)  
? **Absolute return too low** (5.79% vs 15-298% alternatives)  
?? **Solution:** Consider as defensive/tactical allocation, not core holding

### For the Portfolio

? **Current MVO is technically correct but questionable:**
- Dilution needs validation (1009% total return)
- Expected Sharpe of 6.389 is unrealistic
- Too concentrated (94.5% in 4 strategies)

? **Better approach:**
- Cap Dilution at 15-20%
- Force Regime-Switching minimum 10-15%
- Target 6-8 active strategies
- Expect 20-35% return, Sharpe 1.3-1.8

---

## Appendix: Correlation Matrix

Regime-Switching correlations with allocated strategies:

| Strategy | Correlation | Interpretation |
|----------|-------------|----------------|
| Beta Factor | -0.061 | Near-zero (excellent diversifier) |
| Dilution Factor | 0.041 | Near-zero (excellent diversifier) |
| Size Factor | -0.082 | Near-zero (excellent diversifier) |
| Volatility Factor | -0.062 | Near-zero (excellent diversifier) |
| Kurtosis Factor | -0.310 | Moderate negative (diversifier) |

**Regime-Switching provides EXCELLENT diversification benefits.**

Leverage Inverted correlations with allocated strategies:

| Strategy | Correlation | Interpretation |
|----------|-------------|----------------|
| Beta Factor | -0.358 | Moderate negative (diversifier) |
| Dilution Factor | 0.254 | Low positive |
| Size Factor | -0.135 | Low negative (diversifier) |
| Volatility Factor | -0.266 | Moderate negative (diversifier) |
| Kurtosis Factor | 0.360 | Moderate positive |

**Leverage Inverted also provides good diversification, especially vs. Beta/Volatility.**

---

## Files Referenced

- `backtests/results/all_backtests_summary.csv` - Strategy metrics
- `backtests/results/mvo_weights.csv` - Current MVO allocation
- `backtests/results/mvo_correlation.csv` - Strategy correlations
- `backtests/scripts/generate_mvo_weights.py` - MVO optimization script
- `docs/MVO_WEIGHTS_2025_11_02_UPDATED.md` - Full MVO analysis

---

*This analysis explains why mathematically sound strategies were excluded from MVO and provides actionable recommendations for portfolio construction.*
