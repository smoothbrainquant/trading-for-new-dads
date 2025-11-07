# RoC vs Funding Factor - Project Summary

## What Was Done

### 1. Specification Created
- Comprehensive 1,500+ line spec document
- Mathematical framework for RoC-Funding spread
- 4 strategy variants defined
- Complete implementation roadmap
- **Location**: `docs/ROC_FUNDING_FACTOR_SPEC.md`

### 2. Backtest Implementation
- Full Python backtest script (900+ lines)
- Multiple weighting methods (equal, spread-weighted, risk parity)
- Proper no-lookahead bias prevention
- Integration with existing data infrastructure
- **Location**: `backtests/scripts/backtest_roc_funding_factor.py`

### 3. Comprehensive Testing
Ran 8 different backtest configurations:
- 14-day window (best: +1.54% return, 0.02 Sharpe)
- 30-day window (baseline: +0.51% return, 0.01 Sharpe)
- 60-day window (+1.28% return, 0.02 Sharpe)
- Long-only strategy (-0.37% return, negative)
- Contrarian strategy (-0.44% return, negative)
- Spread-weighted approach (+0.56% return)
- Lower filters for more symbols (+0.86% return, -76.88% DD!)
- Recent period only (+0.52% return)

### 4. Results Analysis
- Comprehensive results document with statistical analysis
- Comparison to other factors (Beta, Momentum, Size)
- Theoretical analysis of why strategy failed
- Recommendations for future research
- **Location**: `docs/ROC_FUNDING_FACTOR_BACKTEST_RESULTS.md`

## Key Findings

### ❌ Hypothesis NOT Validated

**"RoC should outpace funding" does not provide reliable trading signal**

Performance Summary:
- Best Sharpe Ratio: 0.02 (essentially zero)
- Annualized Returns: 0.44% - 1.27% (insignificant)
- Maximum Drawdown: -24% to -77% (high risk)
- Win Rate: ~51% (no predictive power)

### Why It Failed

1. **Funding reflects positioning, not forecast**
   - High funding = many longs already positioned
   - Not a leading indicator of future returns

2. **Mean spread is negative (-20.53%)**
   - Funding costs typically exceed price gains
   - Perpetuals are expensive to hold long

3. **High noise-to-signal ratio**
   - Spread std dev: 50.54%
   - Extreme outliers dominate (-431% to +1,080%)

4. **No mean reversion in spreads**
   - Extreme spreads can persist
   - Neither momentum nor contrarian works

## Comparison to Other Factors

| Factor | Sharpe | Annual Return | Verdict |
|--------|--------|---------------|---------|
| Beta (BAB) | 0.72 | 28.85% | ✅ Works |
| Momentum | 0.8-1.2 | 20-40% | ✅ Works |
| Size | 0.5-0.8 | 15-25% | ✅ Works |
| **RoC-Funding** | **0.01** | **0.44%** | ❌ Fails |

## Recommendations

### ❌ DO NOT USE for live trading
- Returns below transaction costs
- No risk-adjusted edge
- More robust factors available

### ✅ Alternative Approaches
1. **Pure Carry Factor** - Trade funding rates directly
2. **Pure Momentum Factor** - Trade RoC without funding
3. **Beta Factor** - Proven 28.85% annualized return
4. **Multi-Factor Model** - Combine proven factors

### 🔬 Future Research (if interested)
1. **Shorter horizons** - Test intraday to 3-day periods
2. **Exchange-specific** - Don't use aggregated funding
3. **Regime-dependent** - Test bull/bear/sideways separately
4. **Nonlinear models** - Try ML approaches
5. **Funding shocks** - Event-driven vs periodic

## Deliverables

All files created and saved:

### Documentation
- `docs/ROC_FUNDING_FACTOR_SPEC.md` - Full specification
- `docs/ROC_FUNDING_FACTOR_BACKTEST_RESULTS.md` - Detailed analysis
- `ROC_FUNDING_FACTOR_SUMMARY.md` - This summary

### Code
- `backtests/scripts/backtest_roc_funding_factor.py` - Backtest engine

### Results (24 CSV files)
- `backtests/results/backtest_roc_funding_*_portfolio_values.csv`
- `backtests/results/backtest_roc_funding_*_trades.csv`
- `backtests/results/backtest_roc_funding_*_metrics.csv`

## Conclusion

This was a thorough investigation of the RoC-Funding spread factor. While the hypothesis didn't pan out, the negative result is valuable—it tells us what doesn't work and prevents wasted effort on a weak strategy.

**Key Takeaway**: Focus research efforts on proven factors (Beta, Momentum, Size) rather than this spread-based approach.

---
**Status**: COMPLETE
**Date**: 2025-10-28
