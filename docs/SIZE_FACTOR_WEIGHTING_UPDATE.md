# Size Factor Weighting Update

**Date**: 2025-11-02  
**Change**: Updated size factor backtest to use risk parity weighting

## Summary

Updated the size factor backtest in `run_all_backtests.py` to use `risk_parity` weighting instead of `equal_weight` to match the live trading implementation.

## Changes Made

### File: `backtests/scripts/run_all_backtests.py`

**Line 452**: Changed weighting method
```python
# BEFORE
weighting_method='equal_weight',

# AFTER  
weighting_method='risk_parity',  # Inverse volatility weighting (matches live trading)
```

**Line 471**: Updated description
```python
# BEFORE
"description": f"LONG small caps, SHORT large caps, {kwargs.get('rebalance_days', 7)}d rebal (VECTORIZED)",

# AFTER
"description": f"LONG small caps, SHORT large caps, risk parity weighting, {kwargs.get('rebalance_days', 7)}d rebal (VECTORIZED)",
```

## Rationale

The live trading implementation in `execution/strategies/size.py` uses inverse volatility weighting via `calc_weights()`:

```python
# execution/strategies/size.py (lines 120-123)
vola_long = calculate_rolling_30d_volatility(historical_data, long_symbols)
w_long = calc_weights(vola_long) if vola_long else {}
for symbol, w in w_long.items():
    target_positions[symbol] = target_positions.get(symbol, 0.0) + w * notional
```

The `calc_weights()` function implements risk parity (inverse volatility) weighting, which:
- Allocates less capital to high-volatility assets
- Allocates more capital to low-volatility assets
- Results in more balanced risk contribution across positions

## Impact

### Before (Equal Weight):
- Each position gets equal notional allocation
- High-volatility assets contribute more to portfolio risk
- Simpler but less risk-balanced

### After (Risk Parity):
- Positions weighted inversely by volatility
- More balanced risk contribution
- Matches live trading behavior exactly

## Consistency Status

? **RESOLVED**: Size factor now uses consistent weighting in both systems:

| System | Weighting Method | Status |
|--------|-----------------|--------|
| Backtest | `risk_parity` | ? Updated |
| Live Trading | `inverse_vol` (same as risk parity) | ? Already correct |

## Expected Performance Impact

The change from equal weight to risk parity may result in:
- **Slightly different backtest results** (positions will be reweighted)
- **Better risk-adjusted returns** (more balanced risk exposure)
- **More accurate comparison** with live trading performance

## Testing Recommendation

Rerun the size factor backtest to generate updated performance metrics:

```bash
cd /workspace/backtests/scripts
python3 run_all_backtests.py --run-size --start-date 2021-01-01
```

Compare new backtest results with previous runs to quantify the impact of risk parity weighting.

## Related Documentation

- Main consistency analysis: `docs/BACKTEST_VS_LIVE_CONSISTENCY_ANALYSIS.md`
- Size factor strategy: `execution/strategies/size.py`
- Vectorized backtest engine: `backtests/scripts/backtest_vectorized.py`
