# ADF Factor Activation Log

**Date:** 2025-11-01  
**Status:** ? ACTIVATED

---

## Summary

The ADF (Augmented Dickey-Fuller) factor has been **fully activated** in both live trading (`main.py`) and automated backtesting (`run_all_backtests.py`).

---

## Changes Made

### 1. `/workspace/execution/strategies/__init__.py`

**Uncommented:**
- Line 11: `from .adf import strategy_adf`
- Line 24: `"strategy_adf",` in `__all__` list

**Status:** ? Import active

---

### 2. `/workspace/execution/main.py`

**Uncommented:**
- Line 16: Removed `[COMMENTED OUT - not active]` note from docstring
- Line 84: `strategy_adf,` import
- Line 121: `"adf": strategy_adf,` registry entry
- Lines 287-309: Full parameter handling block (23 lines) for ADF strategy

**Status:** ? Ready for live trading

---

### 3. `/workspace/execution/all_strategies_config.json`

**Changed:**
- Line 12: `"_adf_commented_out": 0.0` ? `"adf": 0.0`
- Line 98: Status changed from `"COMMENTED OUT - Not active yet"` ? `"ACTIVE - Available for use (set weight > 0 to enable)"`
- Line 97: Renamed params key from `"_adf_commented_out"` ? `"adf"`
- Line 109: Updated comment to reflect active status

**Current weight:** 0.0 (safe default - not yet trading)

**Status:** ? Config ready

---

### 4. `/workspace/backtests/scripts/run_all_backtests.py`

**Uncommented:**
- Lines 754-808: `run_adf_factor_backtest()` function (55 lines)
- Lines 1193-1208: CLI arguments for ADF (3 args)
  - `--run-adf` (default: True)
  - `--adf-strategy` (default: "trend_following_premium")
  - `--adf-window` (default: 60)
- Lines 1383-1399: Execution block (17 lines)
  - Changed `weighting_method` from `"equal_weight"` to `"risk_parity"` (optimal)

**Status:** ? Will run in automated backtests

---

## Configuration Details

### Optimal Parameters (Active in Config)

```json
{
  "adf_window": 60,
  "regression": "ct",
  "volatility_window": 30,
  "rebalance_days": 7,
  "long_percentile": 20,
  "short_percentile": 80,
  "strategy_type": "trend_following_premium",
  "weighting_method": "risk_parity",
  "long_allocation": 0.5,
  "short_allocation": 0.5
}
```

### Strategy Logic

**Trend Following Premium (Optimal):**
- **Long:** Coins with high ADF (less negative) = trending/non-stationary
- **Short:** Coins with low ADF (more negative) = stationary/mean-reverting

**Weighting:** Risk parity (optimal, beat equal weight in backtest)

---

## Performance Metrics (2021-2025)

| Metric | Value |
|--------|-------|
| Total Return | +126.29% |
| Sharpe Ratio | 0.49 |
| Max Drawdown | -50.60% |
| Rebalance | 7 days (weekly) |

---

## Next Steps to Enable in Live Trading

### Current Status
- ? Code activated and ready
- ? Config parameters set
- ?? **Weight = 0.0** (not trading yet)

### To Start Trading

1. **Set allocation weight** in `/workspace/execution/all_strategies_config.json`:
   ```json
   "adf": 0.06  // Start with ~6% based on Sharpe 0.49
   ```

2. **Rebalance other weights** proportionally to maintain total = 1.0

3. **Test in dry-run mode:**
   ```bash
   cd /workspace/execution
   python3 main.py --dry-run
   ```

4. **Verify** ADF appears in output and calculates positions correctly

5. **Run live** when confident:
   ```bash
   python3 main.py
   ```

---

## Backtest Activation

### To Run ADF Backtest

```bash
cd /workspace/backtests/scripts
python3 run_all_backtests.py --run-adf
```

**Will run automatically** by default (`--run-adf` defaults to `True`)

### Available ADF Strategies

- `trend_following_premium` (default, optimal)
- `mean_reversion_premium` (failed in backtest)
- `long_trending` (long only trending coins)
- `long_stationary` (long only stationary coins)

---

## Risk Warnings

?? **Before deploying:**

1. **Market regime dependent:** Works in momentum markets, may fail in mean-reverting regimes
2. **Computational cost:** ~2-3 minutes to calculate ADF for 100 coins
3. **Concentration risk:** Strategy typically holds 2-4 positions per side
4. **Weekly rebalancing:** More transaction costs than monthly strategies
5. **Requires statsmodels:** Already in requirements.txt

---

## Testing Checklist

- [x] ? Code uncommented in all files
- [x] ? Imports verified (no syntax errors)
- [x] ? No linting errors
- [x] ? Config updated with correct keys
- [x] ? Backtest function uses optimal params (risk_parity)
- [ ] ? Run dry-run test of main.py
- [ ] ? Verify ADF calculations complete
- [ ] ? Check position sizes are reasonable
- [ ] ? Run full backtest to verify results
- [ ] ? Monitor for 1-2 weeks before full allocation

---

## Files Modified

1. `/workspace/execution/strategies/__init__.py` - Uncommented import
2. `/workspace/execution/main.py` - Uncommented strategy + params
3. `/workspace/execution/all_strategies_config.json` - Renamed keys, updated status
4. `/workspace/backtests/scripts/run_all_backtests.py` - Uncommented function + CLI + execution

---

## Related Documentation

- **Summary:** `/workspace/ADF_INTEGRATION_SUMMARY.md`
- **Backtest Results:** `/workspace/ADF_FACTOR_RESULTS_SUMMARY_2021_2025.md`
- **Full Analysis:** `/workspace/docs/ADF_FACTOR_BACKTEST_RESULTS_2021_2025.md`
- **Factor Spec:** `/workspace/docs/ADF_FACTOR_SPEC.md`
- **Backtest Script:** `/workspace/backtests/scripts/backtest_adf_factor.py`

---

## Activation Complete ?

The ADF factor is now **fully activated** and ready for:
- ? Live trading (set weight > 0 to enable)
- ? Automated backtesting (runs by default)
- ? Manual testing via main.py --dry-run

**Recommended:** Start with small allocation (3-6%) and monitor performance before increasing weight.
