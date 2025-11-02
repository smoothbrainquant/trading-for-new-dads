# ADF Strategy Reorganization

**Date:** 2025-11-02  
**Status:** ? Complete

## Summary

The separate "regime-switching" strategy has been **merged into the ADF strategy**. There is now only **one** ADF strategy that includes all regime-aware functionality.

## What Changed

### Before
- Two separate strategies: `adf` (static) and `regime_switching` (dynamic)
- Confusing overlap between the two
- Separate config files and implementations

### After  
- **One unified strategy:** `adf` (with built-in regime awareness)
- Simpler, cleaner codebase
- Single config file: `execution/adf_config.json`

## File Mapping

| Old Location | New Location | Status |
|-------------|--------------|--------|
| `execution/strategies/regime_switching.py` | `execution/strategies/adf.py` | **Merged** |
| `execution/regime_switching_config.json` | `execution/adf_config.json` | **Renamed** |
| `backtests/scripts/test_regime_switching_strategy.py` | `backtests/scripts/test_adf_regime_aware.py` | **Renamed** |

## Updated Usage

### In main.py (Live Trading)
```bash
# Old (no longer works)
python3 execution/main.py --signal-config execution/regime_switching_config.json

# New (works)
python3 execution/main.py --signal-config execution/adf_config.json
```

### In Backtests
```bash
# Old (no longer works)
python3 backtests/scripts/run_all_backtests.py --run-regime-switching --regime-mode blended

# New (works)
python3 backtests/scripts/run_all_backtests.py --run-adf --adf-mode blended
```

### In Tests
```bash
# Old (no longer works)
python3 backtests/scripts/test_regime_switching_strategy.py

# New (works)
python3 backtests/scripts/test_adf_regime_aware.py
```

## Code Changes

### Strategy Import
```python
# Old (no longer works)
from execution.strategies import strategy_regime_switching

# New (works)
from execution.strategies import strategy_adf
```

### Strategy Registry
```python
# Old
STRATEGY_REGISTRY = {
    "adf": strategy_adf,
    "regime_switching": strategy_regime_switching,
}

# New (unified)
STRATEGY_REGISTRY = {
    "adf": strategy_adf,  # Now includes regime-aware logic
}
```

### Configuration
```json
// Old (execution/regime_switching_config.json)
{
  "strategy_weights": {
    "regime_switching": 1.0
  },
  "params": {
    "regime_switching": { "mode": "blended", ... }
  }
}

// New (execution/adf_config.json)
{
  "strategy_weights": {
    "adf": 1.0
  },
  "params": {
    "adf": { "mode": "blended", ... }
  }
}
```

## Documentation Status

### Updated Documentation
- ? `execution/strategies/adf.py` - Fully rewritten with regime logic
- ? `execution/main.py` - Updated parameter handling
- ? `backtests/scripts/run_all_backtests.py` - Updated backtest function
- ? `execution/adf_config.json` - Renamed and updated
- ? `backtests/scripts/test_adf_regime_aware.py` - Renamed and updated

### Documentation Needing Updates
The following docs still reference the old `regime_switching` as a separate strategy:
- ?? `docs/factors/adf/ADF_REGIME_SWITCHING_EXECUTIVE_SUMMARY.md`
- ?? `docs/factors/adf/ADF_REGIME_SWITCHING_IMPLEMENTATION.md`
- ?? `docs/factors/adf/REGIME_SWITCHING_QUICKSTART.md`
- ?? `docs/factors/adf/REGIME_SWITCHING_BACKTEST_INTEGRATION.md`
- ?? `docs/factors/adf/REGIME_SWITCHING_PORTFOLIO_WEIGHTS.md`
- ?? `docs/factors/adf/ADF_REGIME_LONGSHORT_ANALYSIS.md`

**Note:** These docs are still accurate in terms of strategy logic and performance metrics. Only file paths and command examples need updating. Treat all references to `regime_switching` as referring to the `adf` strategy with `mode` parameter.

## Key Takeaway

**There is no longer a separate "regime-switching" strategy.**  
All regime-aware functionality is now part of the **ADF strategy** via the `mode` parameter:
- `mode="blended"` - Conservative 80/20 split
- `mode="moderate"` - Balanced 70/30 split  
- `mode="optimal"` - Aggressive 100/0 split

## Migration Guide

If you have existing scripts or configs referencing `regime_switching`:

1. **Replace strategy name:** `regime_switching` ? `adf`
2. **Update config path:** `regime_switching_config.json` ? `adf_config.json`
3. **Update imports:** `from execution.strategies.regime_switching import strategy_regime_switching` ? `from execution.strategies.adf import strategy_adf`
4. **Update CLI flags:** `--run-regime-switching --regime-mode` ? `--run-adf --adf-mode`

## Questions?

The ADF strategy now encompasses all regime-aware logic. The performance metrics and strategy behavior remain identical - only the organization has changed for clarity.
