# Beta Factor Integration Summary

## Overview

Integrated the **Betting Against Beta (BAB)** strategy into `main.py` with optimal parameters based on comprehensive backtesting across 7 different rebalance periods.

## Changes Made

### 1. Created Beta Strategy Module
**File:** `/workspace/execution/strategies/beta.py`

- Implements Betting Against Beta (BAB) strategy
- Long low-beta coins (defensive), short high-beta coins (aggressive)
- Market-neutral approach
- Supports equal-weight and risk parity weighting
- Uses optimal **5-day rebalancing** (best Sharpe: 0.68, Return: 26.98%)

### 2. Updated Strategy Registry
**File:** `/workspace/execution/strategies/__init__.py`

- Added `strategy_beta` import
- Exported in `__all__` list

### 3. Updated Main Execution
**File:** `/workspace/execution/main.py`

#### Added to imports:
```python
from execution.strategies import (
    ...
    strategy_beta,
)
```

#### Added to STRATEGY_REGISTRY:
```python
STRATEGY_REGISTRY = {
    ...
    "beta": strategy_beta,
}
```

#### Added parameter builder in `_build_strategy_params`:
```python
elif strategy_name == "beta":
    beta_window = int(p.get("beta_window", 90))
    volatility_window = int(p.get("volatility_window", 30))
    rebalance_days = int(p.get("rebalance_days", 5))  # OPTIMAL
    long_percentile = int(p.get("long_percentile", 20))
    short_percentile = int(p.get("short_percentile", 80))
    weighting_method = p.get("weighting_method", "equal_weight")
    long_allocation = float(p.get("long_allocation", 0.5))
    short_allocation = float(p.get("short_allocation", 0.5))
    return (historical_data, list(historical_data.keys()), strategy_notional), {
        "beta_window": beta_window,
        "volatility_window": volatility_window,
        "rebalance_days": rebalance_days,
        "long_percentile": long_percentile,
        "short_percentile": short_percentile,
        "weighting_method": weighting_method,
        "long_allocation": long_allocation,
        "short_allocation": short_allocation,
    }
```

### 4. Updated Configuration
**File:** `/workspace/execution/all_strategies_config.json`

#### Added beta to strategy weights:
```json
"strategy_weights": {
    ...
    "beta": 0.0
}
```
*Note: Weight is 0 (inactive by default) - can be enabled by adjusting weight*

#### Added beta parameters with optimal settings:
```json
"beta": {
    "beta_window": 90,
    "volatility_window": 30,
    "rebalance_days": 5,
    "long_percentile": 20,
    "short_percentile": 80,
    "weighting_method": "equal_weight",
    "long_allocation": 0.5,
    "short_allocation": 0.5,
    "_comment": "Optimal rebalance_days=5 based on backtest (Sharpe: 0.68, Return: 26.98%). Betting Against Beta strategy: long low-beta coins, short high-beta coins."
}
```

## Optimal Parameters (From Backtest Analysis)

### Why 5-Day Rebalancing?

Comprehensive backtesting across periods [1, 2, 3, 5, 7, 10, 30] days showed:

| Period | Sharpe | Ann. Return | Max DD |
|--------|--------|-------------|--------|
| 1d     | 0.29   | 11.82%      | -57.41%|
| 2d     | 0.48   | 19.62%      | -54.95%|
| 3d     | 0.57   | 22.76%      | -50.28%|
| **5d** | **0.68** | **26.98%** | **-46.95%** |
| 7d     | 0.37   | 15.09%      | -55.37%|
| 10d    | 0.60   | 24.46%      | -46.98%|
| 30d    | 0.67   | 25.02%      | -41.14%|

**5-day rebalancing achieved:**
- ✅ Highest Sharpe ratio (0.68)
- ✅ Highest annualized return (26.98%)
- ✅ Good drawdown control (-46.95%)
- ✅ Optimal balance between alpha capture and trading costs

### Parameter Details

```python
beta_window = 90          # Rolling window for beta calculation
volatility_window = 30    # Window for volatility (risk parity)
rebalance_days = 5        # OPTIMAL: Rebalance every 5 days
long_percentile = 20      # Long bottom 20% (low beta)
short_percentile = 80     # Short top 20% (high beta)
weighting_method = "equal_weight"  # Equal weight within buckets
long_allocation = 0.5     # 50% to long side
short_allocation = 0.5    # 50% to short side
```

## Usage

### To Enable Beta Strategy

Edit `/workspace/execution/all_strategies_config.json`:

```json
{
  "strategy_weights": {
    "beta": 0.15,  // Allocate 15% to beta strategy
    ...
  }
}
```

### To Run with Beta Only

```bash
python3 execution/main.py --signals beta --dry-run
```

### To Adjust Rebalance Period

Edit config:
```json
"beta": {
    "rebalance_days": 5,  // Change to 10 or 30 if preferred
    ...
}
```

## Strategy Logic

1. **Calculate Beta:** 90-day rolling beta to BTC for all coins
2. **Rank:** Rank coins by beta (low to high)
3. **Select:**
   - Long: Bottom 20% (low beta, defensive)
   - Short: Top 20% (high beta, aggressive)
4. **Weight:** Equal weight or risk parity within buckets
5. **Rebalance:** Every 5 days (optimal)
6. **Result:** Market-neutral portfolio with negative overall beta

## Backtest Results

**Test Period:** April 19, 2020 - October 24, 2025 (2,015 days)
**Strategy:** Betting Against Beta (5-day rebalance)

- **Total Return:** 273.78%
- **Annualized Return:** 26.98%
- **Sharpe Ratio:** 0.68
- **Max Drawdown:** -46.95%
- **Sortino Ratio:** 0.92
- **Win Rate:** 38.2%
- **Portfolio Beta:** -0.28 (negative, as expected)

## Files Generated

### Strategy Implementation
- `/workspace/execution/strategies/beta.py` - Beta strategy module

### Configuration
- `/workspace/execution/all_strategies_config.json` - Updated with beta params
- `/workspace/execution/main.py` - Updated with beta integration

### Backtest Results
- `/workspace/backtests/results/beta_rebalance_comparison.csv` - Comparison table
- `/workspace/backtests/results/beta_rebalance_comparison.png` - Visualization
- `/workspace/backtests/results/beta_rebalance_*d_*.csv` - Individual period results

### Documentation
- `/workspace/BETA_REBALANCE_PERIOD_ANALYSIS.md` - Full backtest analysis
- `/workspace/BETA_INTEGRATION_SUMMARY.md` - This file

## Testing

To verify the integration works:

```bash
# Test with dry-run
python3 execution/main.py --signals beta --dry-run

# Check if beta is recognized
python3 -c "from execution.strategies import strategy_beta; print('Beta strategy loaded successfully!')"
```

## Next Steps

1. **Test in production:** Enable beta with small allocation (5-10%)
2. **Monitor performance:** Track realized vs. backtested performance
3. **Consider alternatives:**
   - 30-day rebalancing for lower costs (-41.14% max DD)
   - Risk parity weighting for better risk adjustment
4. **Combine with other factors:** Test multi-factor combinations

## References

- Backtest script: `/workspace/backtests/scripts/backtest_beta_factor.py`
- Rebalance comparison: `/workspace/backtests/scripts/backtest_beta_rebalance_periods.py`
- Full analysis: `/workspace/BETA_REBALANCE_PERIOD_ANALYSIS.md`

---

*Integration completed: October 29, 2025*
*Optimal parameters: 5-day rebalance (Sharpe: 0.68, Return: 26.98%)*
