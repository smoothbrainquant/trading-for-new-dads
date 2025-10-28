# ADF Factor Backtest Implementation

## Overview

The ADF (Augmented Dickey-Fuller) Factor strategy tests whether mean-reverting coins (stationary) outperform trending coins (non-stationary) or vice versa.

## Implementation

**Script:** `backtest_adf_factor.py`

**Key Features:**
- Rolling ADF test statistic calculation using statsmodels
- Ranks coins by stationarity (lower ADF = more mean-reverting)
- Long/short portfolio construction based on ADF quintiles
- Equal weight or risk parity weighting
- Weekly rebalancing (configurable)
- Proper no-lookahead bias prevention

## Strategy Variants

### 1. Mean Reversion Premium (Primary)
- **Long:** Bottom 20% by ADF (most stationary/mean-reverting)
- **Short:** Top 20% by ADF (most trending/non-stationary)
- **Hypothesis:** Stationary coins outperform trending coins

### 2. Trend Following Premium
- **Long:** Top 20% by ADF (most trending/non-stationary)
- **Short:** Bottom 20% by ADF (most stationary/mean-reverting)
- **Hypothesis:** Trending coins outperform stationary coins

### 3. Long Stationary Only
- **Long:** Bottom 20% by ADF (most stationary)
- **Short:** None (50% cash)

### 4. Long Trending Only
- **Long:** Top 20% by ADF (most trending)
- **Short:** None (50% cash)

## Quick Start

### Basic Usage

```bash
# Mean Reversion Premium (default)
python3 backtest_adf_factor.py \
  --strategy mean_reversion_premium \
  --adf-window 60 \
  --rebalance-days 7

# Trend Following Premium
python3 backtest_adf_factor.py \
  --strategy trend_following_premium \
  --adf-window 60 \
  --rebalance-days 7
```

### Advanced Configuration

```bash
python3 backtest_adf_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy mean_reversion_premium \
  --adf-window 60 \
  --regression ct \
  --volatility-window 30 \
  --rebalance-days 7 \
  --long-percentile 20 \
  --short-percentile 80 \
  --weighting-method risk_parity \
  --long-allocation 0.5 \
  --short-allocation 0.5 \
  --min-volume 10000000 \
  --min-market-cap 100000000 \
  --initial-capital 10000 \
  --leverage 1.0 \
  --start-date 2020-01-01 \
  --end-date 2025-10-27 \
  --output-prefix backtests/results/backtest_adf_factor
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--price-data` | `data/raw/combined_coinbase_coinmarketcap_daily.csv` | Path to OHLCV data |
| `--strategy` | `mean_reversion_premium` | Strategy variant |
| `--adf-window` | 60 | ADF calculation window (days) |
| `--regression` | `ct` | ADF regression type (c/ct/ctt/n) |
| `--volatility-window` | 30 | Volatility window for risk parity |
| `--rebalance-days` | 7 | Rebalance frequency |
| `--weighting-method` | `equal_weight` | equal_weight or risk_parity |
| `--initial-capital` | 10000 | Starting capital (USD) |
| `--long-allocation` | 0.5 | Long side allocation (50%) |
| `--short-allocation` | 0.5 | Short side allocation (50%) |

## Output Files

The backtest generates 4 CSV files:

1. **`*_portfolio_values.csv`**: Daily portfolio values and exposures
2. **`*_trades.csv`**: Trade log with ADF statistics
3. **`*_metrics.csv`**: Performance metrics (Sharpe, drawdown, etc.)
4. **`*_strategy_info.csv`**: Strategy configuration and ADF stats

## ADF Test Interpretation

**ADF Statistic Meaning:**
- **< -3.5**: Strongly stationary (mean-reverting)
- **-3.5 to -2.5**: Moderately stationary
- **-2.5 to -1.5**: Weakly stationary
- **> -1.5**: Non-stationary (trending/random walk)

**P-Value:**
- **< 0.05**: Reject unit root (stationary at 95% confidence)
- **> 0.05**: Cannot reject unit root (non-stationary)

## Initial Test Results (2024)

**Period:** 2024-03-01 to 2024-12-31

### Mean Reversion Premium
- Total Return: **-45.45%**
- Sharpe Ratio: **-1.06**
- Max Drawdown: **-67.46%**
- Avg Long ADF: **-2.45** (stationary)
- Avg Short ADF: **-1.34** (trending)

### Trend Following Premium
- Total Return: **+50.10%**
- Sharpe Ratio: **+1.28**
- Max Drawdown: **-44.18%**
- Avg Long ADF: **-1.34** (trending)
- Avg Short ADF: **-2.45** (stationary)

**Key Finding:** In 2024, trending coins (higher ADF) significantly outperformed stationary coins (lower ADF), suggesting momentum effects dominated mean reversion.

## Dependencies

```bash
pip install pandas numpy statsmodels
```

## Technical Notes

### ADF Calculation
- Uses price **levels** (not returns) for ADF test
- Rolling 60-day window by default
- Constant + trend regression (`ct`) recommended for crypto
- Automatic lag selection using AIC

### No-Lookahead Bias
- Signals generated on day T using data up to day T
- Returns from day T+1 used for P&L calculation
- Positions executed at close of day T

### Performance
- ADF test is computationally intensive
- ~100-150 coins with 60-day window takes 2-3 minutes
- Progress is displayed during calculation

## Related Documentation

- Full specification: `/workspace/docs/ADF_FACTOR_SPEC.md`
- Beta factor: `/workspace/docs/BETA_FACTOR_SPEC.md`
- Volatility factor: `/workspace/docs/VOLATILITY_FACTOR_SPEC.md`

## References

**Academic:**
- Dickey & Fuller (1979): "Distribution of Estimators for Autoregressive Time Series"
- Poterba & Summers (1988): "Mean Reversion in Stock Prices"

**Implementation:**
- statsmodels ADF test: `statsmodels.tsa.stattools.adfuller`
- Template: `backtest_beta_factor.py`

---

**Author:** Automated Factor Research System  
**Date:** 2025-10-27  
**Status:** ✅ Implemented and Tested
