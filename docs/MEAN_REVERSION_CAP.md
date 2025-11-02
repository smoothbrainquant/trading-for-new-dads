# Mean Reversion Strategy - 5% Cap Implementation

## Change Summary

Added a **5% allocation cap** to the Mean Reversion strategy due to:
1. **Extreme volatility:** 76.94% annualized (4-5x other strategies)
2. **Regime dependence:** Sharpe ranges from +6.1 to -0.9 across years
3. **Zero edge:** Sharpe -0.032 over full period (essentially breakeven)
4. **Catastrophic downside risk:** -57% max drawdown in 2024

## Current Allocation (With Cap)

```
? Size Factor          27.46%  (Sharpe: 0.700)
? Beta Factor (BAB)    21.97%  (Sharpe: 0.560)
? Breakout Signal      18.17%  (Sharpe: 0.463)
? Volatility Factor    12.40%  (Sharpe: 0.316)
? Mean Reversion        5.00%  (Sharpe: -0.032) ? CAPPED
? Days from High        5.00%  (Sharpe: -0.241)
? Kurtosis Factor       5.00%  (Sharpe: -0.849)
? Carry Factor          5.00%  (Sharpe: -1.038)
```

**Expected Portfolio Sharpe:** 0.331

## Implementation Details

### Code Changes
Updated `run_all_backtests.py`:
- Modified `calculate_sharpe_weights_with_floor()` to accept `strategy_caps` parameter
- Added cap application logic before renormalization
- Updated `print_sharpe_weights()` to display capped strategies

### Usage
```python
strategy_caps = {
    'Mean Reversion': 0.05,  # Cap at 5%
}
weights_df = calculate_sharpe_weights_with_floor(
    summary_df, 
    min_weight=0.05, 
    strategy_caps=strategy_caps
)
```

## Impact Analysis

### Current Impact
Since Mean Reversion already had negative Sharpe (-0.032), it was already at the 5% floor. The cap ensures it **cannot exceed 5%** even if:
- Future backtests show improved performance
- Different time periods are tested
- Parameters are optimized

### Risk Management
The 5% cap limits exposure to Mean Reversion's risks:

| Metric | Uncapped Risk | Capped Risk (5%) |
|--------|---------------|------------------|
| Max Portfolio Impact | Unlimited | Max 5% loss from MR |
| Volatility Contribution | Could dominate | Limited to 5% ? 76.9% = ~3.8% |
| Drawdown Exposure | Full strategy DD | Max 5% ? 62.6% = ~3.1% |

**Example Scenario:**
- If Mean Reversion has another 2024-style crash (-37%)
- Uncapped allocation: Could be 10-15% ? portfolio loses 3.7-5.5%
- **Capped at 5%: Portfolio loses only 1.85%**

## Rationale

### Why Keep It at All?
Despite poor overall performance, we keep Mean Reversion at 5% minimum because:
1. **Diversification:** Different signal type (z-score based panic dips)
2. **Regime optionality:** May work in future bull markets (see 2023: +37%)
3. **Small allocation:** 5% won't hurt much, but could help in right conditions

### Why Cap It?
Even if it shows better performance in future tests:
1. **Volatility is structural:** 76% vol is inherent to the strategy, not fixable
2. **Regime dependence is fundamental:** Knife-catching works sometimes, fails catastrophically other times
3. **Small sample risk:** 242 trading days is not enough to trust statistical significance

## Comparison to Other Risk Controls

| Strategy | Issue | Control Mechanism |
|----------|-------|-------------------|
| **Mean Reversion** | Extreme volatility + regime dependence | **5% Cap** |
| **Kurtosis** | Consistently negative (-0.849 Sharpe) | 5% Floor (minimum allocation) |
| **Carry** | Fundamentally backwards (-1.038 Sharpe) | 5% Floor (minimum allocation) |
| **Days from High** | Consistently negative (-0.241 Sharpe) | 5% Floor (minimum allocation) |

## Future Considerations

### When to Remove the Cap
Consider removing the 5% cap if:
- [ ] Strategy shows positive Sharpe > 0.5 over 3+ years
- [ ] Volatility drops below 40% annualized
- [ ] Maximum drawdown controlled below -25%
- [ ] Win rate consistently above 55%
- [ ] Performance stable across different market regimes

### When to Disable Entirely
Consider disabling (set allocation to 0) if:
- [ ] Sharpe remains negative for 2+ additional years
- [ ] Another catastrophic drawdown occurs (-40%+)
- [ ] Better mean reversion alternatives are developed

## Testing

The cap implementation has been added to `run_all_backtests.py` and will be applied automatically in all future backtest runs. No manual intervention required.

To test with different caps:
```bash
# Modify strategy_caps in run_all_backtests.py, line ~1576
strategy_caps = {
    'Mean Reversion': 0.03,  # 3% cap
    'Another Strategy': 0.10,  # 10% cap
}
```
