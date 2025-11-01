# Hurst Exponent Factor Backtest

## Overview

The Hurst exponent factor backtest implements a quantitative trading strategy based on the Hurst exponent, which measures the long-term memory and persistence of time series data.

**Hurst Exponent Interpretation:**
- **H < 0.5**: Mean-reverting behavior (anti-persistent)
- **H = 0.5**: Random walk (no memory)
- **H > 0.5**: Trending behavior (persistent, momentum)

## Quick Start

### Basic Usage

```bash
# Run the baseline strategy (long mean-reverting, short trending)
python3 backtests/scripts/backtest_hurst_exponent_factor.py \
  --strategy long_mean_reverting \
  --hurst-window 90 \
  --rebalance-days 7 \
  --start-date 2020-01-01
```

### Run All Strategy Variants

```bash
# Run example script with all strategy variants
bash backtests/scripts/run_hurst_backtest_example.sh
```

## Strategy Variants

### 1. Long Mean-Reverting (Primary Strategy)
**Strategy:** `long_mean_reverting`

- **Long**: Bottom quintile (low Hurst, mean-reverting coins)
- **Short**: Top quintile (high Hurst, trending coins)
- **Hypothesis**: Mean-reverting assets provide more stable, risk-adjusted returns

```bash
python3 backtests/scripts/backtest_hurst_exponent_factor.py \
  --strategy long_mean_reverting
```

### 2. Long Trending
**Strategy:** `long_trending`

- **Long**: Top quintile (high Hurst, trending coins)
- **Short**: Bottom quintile (low Hurst, mean-reverting coins)
- **Hypothesis**: Persistent trends contain exploitable momentum

```bash
python3 backtests/scripts/backtest_hurst_exponent_factor.py \
  --strategy long_trending
```

### 3. Long Low Hurst Only
**Strategy:** `long_low_hurst`

- **Long**: Bottom quintile (low Hurst, mean-reverting)
- **Short**: None (50% cash)
- **Use Case**: Defensive positioning

```bash
python3 backtests/scripts/backtest_hurst_exponent_factor.py \
  --strategy long_low_hurst
```

### 4. Long High Hurst Only
**Strategy:** `long_high_hurst`

- **Long**: Top quintile (high Hurst, trending)
- **Short**: None (50% cash)
- **Use Case**: Momentum capture

```bash
python3 backtests/scripts/backtest_hurst_exponent_factor.py \
  --strategy long_high_hurst
```

## Parameters

### Core Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--strategy` | `long_mean_reverting` | Strategy variant |
| `--hurst-window` | 90 | Hurst calculation window (days) |
| `--rebalance-days` | 7 | Rebalance frequency (days) |
| `--weighting-method` | `equal_weight` | `equal_weight` or `risk_parity` |

### Portfolio Construction

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--long-allocation` | 0.5 | Allocation to long side (50%) |
| `--short-allocation` | 0.5 | Allocation to short side (50%) |
| `--initial-capital` | 10000 | Starting capital (USD) |
| `--leverage` | 1.0 | Leverage multiplier |

### Universe Filters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--min-volume` | 5000000 | Minimum 30d avg volume ($) |
| `--min-market-cap` | 50000000 | Minimum market cap ($) |
| `--long-percentile` | 20 | Long percentile threshold (bottom 20%) |
| `--short-percentile` | 80 | Short percentile threshold (top 20%) |

### Date Range

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--start-date` | None | Backtest start date (YYYY-MM-DD) |
| `--end-date` | None | Backtest end date (YYYY-MM-DD) |

## Examples

### Test Different Hurst Windows

```bash
# Test 30-day, 60-day, 90-day, and 180-day Hurst windows
for window in 30 60 90 180; do
  python3 backtests/scripts/backtest_hurst_exponent_factor.py \
    --strategy long_mean_reverting \
    --hurst-window $window \
    --output-prefix backtests/results/hurst_window_${window}
done
```

### Test Different Rebalancing Frequencies

```bash
# Test daily, weekly, bi-weekly, and monthly rebalancing
for days in 1 7 14 30; do
  python3 backtests/scripts/backtest_hurst_exponent_factor.py \
    --strategy long_mean_reverting \
    --rebalance-days $days \
    --output-prefix backtests/results/hurst_rebal_${days}d
done
```

### Risk Parity Weighting

```bash
# Use risk parity instead of equal weight
python3 backtests/scripts/backtest_hurst_exponent_factor.py \
  --strategy long_mean_reverting \
  --weighting-method risk_parity \
  --output-prefix backtests/results/hurst_risk_parity
```

### Custom Date Range

```bash
# Backtest specific period (2021-2024)
python3 backtests/scripts/backtest_hurst_exponent_factor.py \
  --strategy long_mean_reverting \
  --start-date 2021-01-01 \
  --end-date 2024-12-31 \
  --output-prefix backtests/results/hurst_2021_2024
```

## Output Files

The script generates 4 CSV files:

### 1. Portfolio Values (`*_portfolio_values.csv`)
Daily portfolio metrics including:
- `portfolio_value`: Total portfolio NAV
- `long_exposure`, `short_exposure`: Dollar exposure by side
- `num_longs`, `num_shorts`: Number of positions
- `avg_hurst_long`, `avg_hurst_short`: Average Hurst by side

### 2. Trades (`*_trades.csv`)
All rebalancing trades with:
- `date`, `symbol`: When and what
- `signal`: LONG or SHORT
- `hurst`: Hurst exponent value
- `weight`: Position size
- `market_cap`, `volume_30d_avg`: Filters

### 3. Metrics (`*_metrics.csv`)
Performance metrics:
- Returns: Total, annualized
- Risk: Volatility, Sharpe, Sortino, max drawdown
- Trading: Win rate, number of days
- Exposures: Long, short, net, gross

### 4. Strategy Info (`*_strategy_info.csv`)
Configuration and summary statistics

## Hurst Exponent Calculation

The backtest uses the **R/S (Rescaled Range)** method:

1. Split returns into chunks of various lag sizes
2. For each chunk:
   - Calculate cumulative deviations from mean
   - Compute range R (max - min of cumulative deviations)
   - Compute standard deviation S
   - Calculate R/S ratio
3. Fit log(R/S) vs log(lag) to get slope (Hurst exponent)

**Computational Note:** Hurst calculation is CPU-intensive. For 90-day windows on 172 coins × 2000 days, expect:
- First run: 2-5 minutes (calculating Hurst values)
- Subsequent runs: Faster if data cached

## Performance Considerations

### Hurst Window Selection

- **30 days**: Fast to compute, reactive, but noisy
- **60 days**: Good balance, moderate stability
- **90 days**: Default, stable estimates, slower
- **180 days**: Very stable but slow to adapt

### Rebalancing Frequency

- **Daily (1 day)**: High turnover, transaction costs
- **Weekly (7 days)**: Default, balanced
- **Bi-weekly (14 days)**: Lower turnover
- **Monthly (30 days)**: Low turnover, may miss signals

## Interpreting Results

### Key Metrics to Watch

1. **Sharpe Ratio**: Risk-adjusted returns (target > 0.7)
2. **Hurst Spread**: Difference between long and short buckets
   - Should be > 0.1 (meaningful separation)
3. **Win Rate**: Percentage of profitable days
4. **Max Drawdown**: Largest peak-to-trough decline

### Expected Results

**If mean-reversion premium exists:**
- `long_mean_reverting` should outperform `long_trending`
- Low Hurst portfolio should have positive returns
- High Hurst portfolio may underperform

**If momentum premium exists:**
- `long_trending` should outperform `long_mean_reverting`
- High Hurst portfolio should have positive returns
- Low Hurst portfolio may underperform

## Comparison to Other Factors

```bash
# Run all factor strategies on same time period
python3 backtests/scripts/backtest_beta_factor.py --start-date 2020-01-01
python3 backtests/scripts/backtest_volatility_factor.py --start-date 2020-01-01
python3 backtests/scripts/backtest_hurst_exponent_factor.py --start-date 2020-01-01

# Compare results
python3 backtests/scripts/generate_equity_curves.py
```

## Troubleshooting

### "Insufficient data" error
- Reduce `--hurst-window` to 60 or 30 days
- Check that price data exists for the date range

### Very slow execution
- Reduce date range with `--start-date` / `--end-date`
- Use smaller `--hurst-window` (30 or 60 days)
- Filter more aggressively with `--min-volume` / `--min-market-cap`

### No positions selected
- Check that coins pass liquidity filters
- Verify sufficient trading history (>= hurst_window)
- Try lowering `--min-volume` or `--min-market-cap`

## References

### Academic Papers
- Hurst, H. E. (1951). "Long-term storage capacity of reservoirs"
- Mandelbrot, B. B. (1968). "Fractional Brownian Motions"
- Peters, E. E. (1994). "Fractal Market Analysis"
- Lo, A. W. (1991). "Long-Term Memory in Stock Market Prices"

### Related Specs
- Full specification: `docs/HURST_EXPONENT_FACTOR_SPEC.md`
- Beta factor: `docs/BETA_FACTOR_SPEC.md`
- Volatility factor: `docs/VOLATILITY_FACTOR_SPEC.md`

## Contact

For questions or issues, refer to the main project README or specification document.
