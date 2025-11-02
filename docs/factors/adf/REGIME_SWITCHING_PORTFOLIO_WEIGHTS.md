# Regime-Switching Strategy: Portfolio Weight Allocation

**Understanding How Weights Are Calculated** ??

---

## ?? Question: Will Strategy Weights Work Appropriately?

**Short Answer:** Yes, but with smart caps to ensure diversification.

---

## ?? How Sharpe-Based Weights Work

### Standard Algorithm

The backtest suite uses Sharpe-ratio-based weighting:

```python
weight_i = sharpe_i / sum(sharpe_j for all j)
```

**Without caps, regime-switching would dominate:**

| Strategy | Sharpe | Uncapped Weight |
|----------|--------|-----------------|
| Regime-Switching (Blended) | 2.20 | ~65% |
| Volatility | 1.41 | ~15% |
| Kurtosis | 0.81 | ~8% |
| Beta (BAB) | 0.68 | ~7% |
| Carry | 0.45 | ~5% |

**Problem:** Over-concentration in one strategy (even a good one) increases risk!

---

## ??? Strategy Caps (Risk Management)

### Current Configuration

```python
strategy_caps = {
    'Mean Reversion': 0.05,                    # 5% cap
    'Regime-Switching (Blended)': 0.35,        # 35% cap
    'Regime-Switching (Moderate)': 0.35,       # 35% cap  
    'Regime-Switching (Optimal)': 0.40,        # 40% cap
}
```

### Rationale

**Regime-Switching Caps (35-40%):**

1. **High Sharpe Deserves Significant Allocation**
   - Sharpe 2.0-2.5 is exceptional
   - Should get larger weight than other strategies
   - Cap at 35-40% allows this while ensuring diversification

2. **Risk Management**
   - New strategy (only backtested, not live-traded)
   - Out-of-sample performance unknown
   - Cap prevents over-exposure to untested strategy

3. **Diversification Benefits**
   - Other strategies provide different alpha sources
   - Uncorrelated returns improve portfolio Sharpe
   - Cap ensures meaningful allocation to other factors

4. **Mode-Specific Caps**
   - **Blended (35%):** Most conservative, lower cap appropriate
   - **Moderate (35%):** Balanced, same cap as blended
   - **Optimal (40%):** Most aggressive, slightly higher cap justified

**Mean Reversion Cap (5%):**
- Extreme volatility and regime dependence
- Negative Sharpe in some regimes
- Kept at minimum allocation for diversification only

---

## ?? Example Weight Allocation

### Scenario: All Strategies Enabled

**Input (Hypothetical Sharpe Ratios):**

| Strategy | Sharpe | Uncapped Weight | Cap | Final Weight |
|----------|--------|-----------------|-----|--------------|
| Regime-Switching (Blended) | 2.20 | 65.2% | 35% | **35.0%** ?? |
| Volatility | 1.41 | 15.3% | - | **19.8%** ?? |
| Kurtosis | 0.81 | 8.5% | - | **11.0%** ?? |
| Beta (BAB) | 0.68 | 7.2% | - | **9.3%** ?? |
| Carry | 0.45 | 5.0% | - | **6.5%** ?? |
| ADF (TF) | 0.35 | 5.0% (min) | - | **6.5%** ?? |
| Breakout | 0.25 | 5.0% (min) | - | **6.5%** ?? |
| Mean Reversion | -0.40 | 5.0% (min) | 5% | **5.0%** |
| Days from High | 0.15 | 5.0% (min) | - | **0.4%** |

**After Capping and Renormalization:**
- Regime-switching capped at 35%
- Excess weight distributed proportionally to other strategies
- All strategies get minimum 5% (or their natural weight if higher)
- Total weights sum to 100%

---

## ?? Visual Representation

### Without Caps (Not Recommended)
```
Regime-Switching: ???????????????????????????????????? 65%
Volatility:       ???????? 15%
Kurtosis:         ???? 8%
Beta:             ??? 7%
Others:           ?? 5%
```

**Problem:** Over-concentrated!

### With Caps (Current Implementation)
```
Regime-Switching: ???????????????????? 35%
Volatility:       ?????????? 20%
Kurtosis:         ?????? 11%
Beta:             ????? 9%
Carry:            ???? 7%
ADF (TF):         ???? 7%
Others:           ?????? 11%
```

**Better:** Diversified while giving top strategy significant weight!

---

## ?? How to Adjust Caps

### Option 1: More Aggressive (Higher Regime-Switching)

```python
strategy_caps = {
    'Mean Reversion': 0.05,
    'Regime-Switching (Blended)': 0.50,   # Increase to 50%
    'Regime-Switching (Moderate)': 0.50,
    'Regime-Switching (Optimal)': 0.60,   # Increase to 60%
}
```

**Use when:**
- High confidence in strategy after paper trading
- Want maximum exposure to best performer
- Comfortable with concentration risk

### Option 2: More Conservative (Lower Regime-Switching)

```python
strategy_caps = {
    'Mean Reversion': 0.05,
    'Regime-Switching (Blended)': 0.25,   # Decrease to 25%
    'Regime-Switching (Moderate)': 0.25,
    'Regime-Switching (Optimal)': 0.30,   # Decrease to 30%
}
```

**Use when:**
- Testing new strategy (recommended initially)
- Want maximum diversification
- Conservative risk management

### Option 3: No Caps (Not Recommended Initially)

```python
strategy_caps = {
    'Mean Reversion': 0.05,
    # Regime-switching uncapped
}
```

**Use when:**
- After extensive live trading validation
- Very high confidence in out-of-sample performance
- Willing to accept concentration risk

**?? Warning:** Only after 6+ months of successful live trading!

---

## ?? Expected Portfolio Metrics

### With Current Caps (35-40%)

**Portfolio Allocation:**
- Regime-Switching: 35%
- Other High-Sharpe Strategies: 45%
- Diversification Strategies: 20%

**Expected Portfolio Sharpe:** 1.6-1.9

**Benefits:**
- Balanced exposure to best strategy
- Meaningful diversification
- Reduced concentration risk
- Better risk-adjusted returns through diversification

### Without Caps (65%+ Regime-Switching)

**Portfolio Allocation:**
- Regime-Switching: 65%
- Other Strategies: 35%

**Expected Portfolio Sharpe:** 1.8-2.1

**Risks:**
- High concentration risk
- Over-reliance on one strategy
- Greater exposure to strategy-specific risks
- Higher potential drawdown if strategy fails

**Trade-off:** ~10% higher Sharpe but significantly higher concentration risk.

---

## ?? Recommendations

### Phase 1: Initial Deployment (Current)

**Caps:** 35-40% (as configured)

**Rationale:**
- Strategy is new (only backtested)
- Need live trading validation
- Prudent risk management
- Still gets significant allocation due to high Sharpe

**Duration:** First 3-6 months of live trading

### Phase 2: After Validation

**Caps:** 45-50% (if performance confirmed)

**Criteria:**
- 3+ months of live trading
- Out-of-sample Sharpe > 1.8
- Max drawdown < 25%
- No technical failures
- Regime distribution as expected

### Phase 3: Mature Strategy

**Caps:** 50-60% (if consistently strong)

**Criteria:**
- 6+ months of live trading
- Proven out-of-sample performance
- Sharpe consistently > 2.0
- Risk metrics within expectations
- Market conditions tested across multiple regimes

### Never: Uncapped

**Reason:** Even the best strategy should have some cap
- Prevents over-concentration
- Allows for strategy rotation
- Maintains diversification benefits
- Reduces tail risk

**Maximum Recommended Cap:** 60-70%

---

## ?? Monitoring Weight Allocation

### Key Metrics to Track

**Weekly:**
- Actual vs target weights
- Rebalancing needs
- Strategy performance vs expected

**Monthly:**
- Weight drift from targets
- Contribution to portfolio return
- Risk contribution (volatility share)

**Quarterly:**
- Review cap appropriateness
- Adjust based on performance
- Recalculate optimal allocations

### Warning Signs

**Increase Caps If:**
- Strategy Sharpe > expected by 20%+
- Consistently low drawdowns
- Smooth equity curve
- Other strategies underperforming

**Decrease Caps If:**
- Sharpe < expected by 30%+
- Unexpected drawdowns
- Regime detection failing
- Correlated losses with other strategies

---

## ?? Key Insights

### 1. Caps Are Dynamic

**Current caps (35-40%) are starting points:**
- Based on backtest performance
- Assumes no live trading history
- Should be adjusted based on actual results

**Review frequency:** Every 3-6 months

### 2. Sharpe Weighting Is Imperfect

**Limitations:**
- Backward-looking (past Sharpe may not persist)
- Doesn't account for correlation
- Ignores higher moments (skew, kurtosis)
- Can over-concentrate in recent winners

**Caps help mitigate these limitations**

### 3. Diversification Has Value

**Even with a 2.5 Sharpe strategy:**
- Other strategies provide different alpha
- Reduces single-strategy risk
- Improves portfolio stability
- Better downside protection

**Optimal is NOT "100% best strategy"**

### 4. Conservative Is Appropriate Initially

**For new strategies:**
- Start with lower caps (25-30%)
- Gradually increase as confidence builds
- Never rush to full allocation
- Paper trade first, then small live, then scale

---

## ? Summary

### Current Configuration: Smart and Appropriate

**Why It Works:**

1. **Regime-Switching gets largest allocation** (35-40%)
   - Reflects its superior Sharpe (2.0-2.5)
   - Appropriate for best-performing strategy

2. **Cap prevents over-concentration**
   - Ensures meaningful diversification
   - Reduces single-strategy risk
   - Allows other alpha sources to contribute

3. **Minimum 5% floor for all strategies**
   - Maintains diversification
   - Captures uncorrelated returns
   - Provides strategy rotation optionality

4. **Gradual path to increase**
   - Start at 35-40%
   - Increase to 45-50% after validation
   - Max out at 60-70% for mature strategy

### Adjustment Path

```
Backtest ? Paper Trade ? Small Live ? Increase Cap ? Full Allocation
35%        ?    35%     ?    40%    ?     50%      ?      60%
(current)      (1 month)    (3 months)  (6 months)   (12+ months)
```

### Bottom Line

**Yes, the strategy weights will work appropriately!**

The capping mechanism ensures:
- ? Regime-switching gets significant weight (deserved)
- ? Portfolio remains diversified (risk management)
- ? Path to increase allocation as confidence builds
- ? Protection against over-concentration

**Recommendation:** Keep current caps (35-40%) for initial deployment, then adjust based on live trading results.

---

**Document Date:** 2025-11-02  
**Status:** Current Configuration Appropriate  
**Next Review:** After 3 months of live trading
