# Trendline Breakout Strategy Integration

## Summary

Successfully integrated the trendline breakout strategy into `main.py` with daily rebalancing (rebalance_days=1).

## Changes Made

### 1. Created Strategy Implementation
- **File**: `execution/strategies/trendline_breakout.py`
- **Function**: `strategy_trendline_breakout()`
- Implements momentum continuation strategy based on trendline analysis
- Uses rolling linear regression to identify clean trendlines
- Detects strong breakouts using Z-score normalization
- Long uptrend breakouts, short downtrend breakouts

### 2. Updated Strategy Registry
- **File**: `execution/main.py`
  - Added import for `strategy_trendline_breakout`
  - Added to `STRATEGY_REGISTRY` dictionary
  - Added parameter handling in `_build_strategy_params()`
  - Updated docstring to list trendline_breakout as supported signal

### 3. Updated Strategy Package
- **File**: `execution/strategies/__init__.py`
  - Added import and export for `strategy_trendline_breakout`

### 4. Updated Configuration
- **File**: `execution/all_strategies_config.json`
  - Added `trendline_breakout` to `strategy_weights` (weight: 0.0, disabled by default)
  - Added `trendline_breakout` parameters with optimal backtest values:
    - `rebalance_days`: 1 (daily rebalancing as requested)
    - `trendline_window`: 30 days
    - `breakout_threshold`: 1.5σ
    - `min_r2`: 0.5
    - `max_pvalue`: 0.05
    - `max_positions`: 10 per side
    - `weighting_method`: equal_weight
    - `long_allocation`: 0.5
    - `short_allocation`: 0.5

## Strategy Parameters

The trendline breakout strategy accepts the following parameters:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `trendline_window` | 30 | Days for linear regression calculation |
| `volatility_window` | 30 | Days for volatility normalization |
| `breakout_threshold` | 1.5 | Z-score threshold (standard deviations) |
| `min_r2` | 0.5 | Minimum R² for clean trendline |
| `max_pvalue` | 0.05 | Maximum p-value for statistical significance |
| `max_positions` | 10 | Maximum positions per side |
| `rebalance_days` | 1 | Rebalancing frequency (1=daily) |
| `weighting_method` | equal_weight | Position weighting (equal_weight or signal_weighted) |
| `long_allocation` | 0.5 | Allocation to long side |
| `short_allocation` | 0.5 | Allocation to short side |

## Usage Examples

### 1. Using the Default Config (Strategy Disabled)

By default, the trendline breakout strategy has a weight of 0.0 in `all_strategies_config.json`, so it won't run unless you modify the config.

```bash
python3 execution/main.py --dry-run
```

### 2. Using Only Trendline Breakout Strategy

```bash
python3 execution/main.py --signals trendline_breakout --dry-run
```

### 3. Using Custom Config File

Create a config file (e.g., `trendline_only_config.json`):

```json
{
  "strategy_weights": {
    "trendline_breakout": 1.0
  },
  "params": {
    "trendline_breakout": {
      "trendline_window": 30,
      "volatility_window": 30,
      "breakout_threshold": 1.5,
      "min_r2": 0.5,
      "max_pvalue": 0.05,
      "max_positions": 10,
      "rebalance_days": 1,
      "weighting_method": "equal_weight",
      "long_allocation": 0.5,
      "short_allocation": 0.5
    }
  }
}
```

Then run:

```bash
python3 execution/main.py --signal-config trendline_only_config.json --dry-run
```

### 4. Blending with Other Strategies

Modify `execution/all_strategies_config.json` to adjust weights:

```json
{
  "strategy_weights": {
    "trendline_breakout": 0.3,
    "mean_reversion": 0.4,
    "breakout": 0.3
  },
  "params": {
    ...
  }
}
```

## Rebalance Parameter ("qd")

The strategy is configured with `rebalance_days: 1`, which means:
- **Daily rebalancing** (checks for new signals every day)
- Optimal based on backtest results (2020-2025)
- Positions typically held for 5 days before natural exit

## Strategy Performance (Backtest 2020-2025)

Based on historical backtesting:
- **Total Return**: +93.44%
- **Annualized Return**: 12.31%
- **Sharpe Ratio**: 0.36
- **Max Drawdown**: -40.27%
- **Total Trades**: 129 over 5 years
- **Optimal Holding Period**: 5 days
- **Signal Quality**: R² ≥ 0.5, Z-score ≥ 1.5σ

## Signal Logic

### LONG Signal
- Price breaks **ABOVE** a clean uptrend
- Trendline has R² ≥ 0.5 (explains ≥50% of variance)
- Trendline is statistically significant (p-value ≤ 0.05)
- Breakout is strong (Z-score ≥ 1.5σ above trendline)

### SHORT Signal
- Price breaks **BELOW** a clean downtrend
- Trendline has R² ≥ 0.5
- Trendline is statistically significant (p-value ≤ 0.05)
- Breakout is strong (Z-score ≤ -1.5σ below trendline)

## Dependencies

The strategy requires:
- `pandas`
- `numpy`
- `scipy`

These are already included in `requirements.txt`.

## Testing

To test the integration:

```bash
# Install dependencies
pip install -r requirements.txt

# Run in dry-run mode with only trendline breakout
python3 execution/main.py --signals trendline_breakout --dry-run

# Run backtest (optional)
python3 backtests/scripts/backtest_trendline_breakout.py \
  --breakout-threshold 1.5 \
  --min-r2 0.5 \
  --holding-period 5 \
  --max-positions 10
```

## Notes

- Strategy is set to weight 0.0 in default config (disabled)
- To enable, modify `execution/all_strategies_config.json` or use custom config
- Daily rebalancing (`rebalance_days=1`) is optimal per backtest
- Market-neutral by default (50% long, 50% short allocation)
- Works best with clean, trending markets
- Lower win rate (8.5%) but large wins when they occur

## Related Files

- Strategy implementation: `execution/strategies/trendline_breakout.py`
- Signal calculator: `signals/calc_trendline_breakout_signals.py`
- Backtest script: `backtests/scripts/backtest_trendline_breakout.py`
- Documentation: `TRENDLINE_BREAKOUT_COMPLETE.md`
- Summary: `TRENDLINE_BREAKOUT_SUMMARY.md`

---

*Integration completed: 2025-10-30*
