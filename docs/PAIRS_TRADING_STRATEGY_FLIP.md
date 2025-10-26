# Pairs Trading Strategy Flip: Mean Reversion → Momentum

**Date:** 2025-10-26  
**Status:** Strategy Updated  
**Impact:** Critical change to signal generation logic

---

## Summary

The pairs trading strategy has been **flipped from mean reversion to momentum**:

### Previous Strategy (Mean Reversion)
- **LONG:** Underperformers (z_score < -1.5, percentile < 25)
- **SHORT:** Outperformers (z_score > 1.5, percentile > 75)
- **Logic:** Bet on reversion to the mean

### New Strategy (Momentum)
- **LONG:** Outperformers (z_score > 1.5, percentile > 75)
- **SHORT:** Underperformers (z_score < -1.5, percentile < 25)
- **Logic:** Bet on continuation of divergence

---

## Rationale

Phase 4 backtest results (2020-2025) revealed that **mean reversion fails in crypto markets**:

### Key Findings from Phase 4

| Signal Type | Previous Strategy | Count | Avg Return | Total P&L |
|-------------|------------------|-------|------------|-----------|
| **LONG** (underperformers) | Mean reversion | 11 | +0.23% | -$78 |
| **SHORT** (outperformers) | Mean reversion | 185 | -3.57% | -$71,646 |

**Critical Insight:** 
- SHORT positions (fading winners) lost $71,646
- LONG positions (fading losers) nearly broke even
- This indicates **momentum dominates** in crypto markets

### Why Mean Reversion Failed

1. **Bull Market Momentum (2020-2025)**
   - Outperforming coins continue to outperform
   - Shorting winners resulted in massive losses

2. **Asymmetric Signal Distribution**
   - 94.7% SHORT signals vs 5.3% LONG signals
   - Heavily biased toward losing side

3. **Structural Trends in Categories**
   - Dino Coins: Persistent decline (not mean-reverting)
   - Meme Coins: Momentum-driven hype cycles
   - L1 Coins: Winner-take-all dynamics

---

## Implementation Changes

### Files Modified

1. **`signals/calc_basket_divergence_signals.py`**
   - Line 6: Updated docstring to "momentum trading signals"
   - Lines 330-333: Updated function docstring
   - Lines 436-450: **Flipped signal logic**

2. **`backtests/scripts/backtest_basket_pairs_trading.py`**
   - Line 9: Updated comment to reflect momentum strategy

3. **`docs/PAIRS_TRADING_STRATEGY_FLIP.md`**
   - Created this documentation file

### Code Changes

**Before (Mean Reversion):**
```python
# Long signal: underperformer
long_condition = (
    (merged['z_score'] < -signal_threshold) &
    (merged['percentile_rank'] < 25) &
    (merged['basket_corr'] > min_correlation)
)
merged.loc[long_condition, 'signal'] = 'LONG'

# Short signal: outperformer
short_condition = (
    (merged['z_score'] > signal_threshold) &
    (merged['percentile_rank'] > 75) &
    (merged['basket_corr'] > min_correlation)
)
merged.loc[short_condition, 'signal'] = 'SHORT'
```

**After (Momentum):**
```python
# Long signal: outperformer (momentum strategy)
long_condition = (
    (merged['z_score'] > signal_threshold) &
    (merged['percentile_rank'] > 75) &
    (merged['basket_corr'] > min_correlation)
)
merged.loc[long_condition, 'signal'] = 'LONG'

# Short signal: underperformer (momentum strategy)
short_condition = (
    (merged['z_score'] < -signal_threshold) &
    (merged['percentile_rank'] < 25) &
    (merged['basket_corr'] > min_correlation)
)
merged.loc[short_condition, 'signal'] = 'SHORT'
```

---

## Expected Impact

### Signal Distribution Flip

**Previous (Mean Reversion):**
- LONG: 5.3% of signals (11 trades)
- SHORT: 94.7% of signals (185 trades)

**Expected (Momentum):**
- LONG: 94.7% of signals (was SHORT)
- SHORT: 5.3% of signals (was LONG)

### Performance Expectations

If momentum hypothesis is correct:
- **LONG trades** (now outperformers): Should profit from continuation
- **SHORT trades** (now underperformers): Fewer signals, should profit from continued decline
- **Overall Sharpe ratio**: Expected to improve significantly
- **Drawdown**: Should reduce from 101% to < 50%

---

## Next Steps

### 1. Regenerate Signals
```bash
python3 signals/calc_basket_divergence_signals.py \
    --categories "Meme Coins,DeFi Blue Chips,Dino Coins" \
    --lookback 60 \
    --threshold 1.5
```

This will create new signal files with flipped logic.

### 2. Re-run Backtest
```bash
python3 backtests/scripts/backtest_basket_pairs_trading.py \
    --signal-file signals/basket_divergence_signals_full.csv
```

### 3. Compare Results

Compare momentum strategy results to Phase 4 baseline:

| Metric | Mean Reversion (Phase 4) | Momentum (Expected) |
|--------|-------------------------|---------------------|
| Total Return | -74.66% | **Positive** |
| Sharpe Ratio | -0.04 | **> 0.5** |
| Max Drawdown | 101% | **< 50%** |
| Win Rate | 42.86% | **> 50%** |
| Profit Factor | 0.47 | **> 1.5** |

---

## Risk Considerations

### Momentum Strategy Risks

1. **Regime Dependency**
   - Momentum works in trending markets
   - May fail in mean-reverting/ranging markets
   - Consider adding regime filter

2. **Reversal Risk**
   - Strong divergences may eventually revert
   - Need tight stop losses
   - Monitor position duration

3. **Concentration Risk**
   - May generate more LONG than SHORT signals
   - Not naturally market-neutral
   - Consider position limits per direction

### Mitigation Strategies

1. **Add Trend Filter**
   - Only LONG when basket trending up
   - Only SHORT when basket trending down

2. **Dynamic Thresholds**
   - Higher thresholds in low-volatility regimes
   - Lower thresholds in high-volatility regimes

3. **Position Limits**
   - Cap at 50% of capital in one direction
   - Force some market neutrality

---

## Historical Context

### Phase 4 Recommendations

From `docs/PAIRS_TRADING_PHASE4_COMPLETE.md`, the following recommendations led to this flip:

> **Recommendation #1: Test LONG-Only Strategy**
> 
> Since LONG trades are break-even and SHORT trades lose heavily:
> - Remove SHORT signals entirely
> - Focus only on fading underperformers (LONG signals)
> - This aligns with "buy the dip" mentality in crypto

This momentum flip is a **more aggressive version** of that recommendation:
- Instead of removing SHORT signals, we flip them
- Instead of only LONG underperformers, we LONG outperformers
- This fully embraces momentum instead of mean reversion

---

## Testing Checklist

After regenerating signals and re-running backtest:

- [ ] Verify signal counts are flipped (~185 LONG, ~11 SHORT)
- [ ] Verify LONG trades are now on outperformers
- [ ] Verify SHORT trades are now on underperformers
- [ ] Check overall return is positive
- [ ] Check Sharpe ratio > 0.5
- [ ] Check max drawdown < 50%
- [ ] Compare equity curve to Phase 4
- [ ] Analyze by category (Meme, Dino, L1, SOL)
- [ ] Check exit reason distribution
- [ ] Validate no lookahead bias

---

## References

- **Original Spec:** `docs/PAIRS_TRADING_SPEC.md` (describes mean reversion strategy)
- **Phase 4 Results:** `docs/PAIRS_TRADING_PHASE4_COMPLETE.md` (motivation for flip)
- **Signal Script:** `signals/calc_basket_divergence_signals.py` (implementation)
- **Backtest Script:** `backtests/scripts/backtest_basket_pairs_trading.py` (execution)

---

**Document Owner:** Research Team  
**Last Updated:** 2025-10-26  
**Next Review:** After momentum backtest completion
