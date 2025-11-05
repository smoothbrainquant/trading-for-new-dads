# Dilution Backtest Integration - Update Summary

**Date:** November 3, 2025  
**Purpose:** Integrate dilution decile analysis (equal-weighted and risk parity) into run_all_backtests.py

---

## Changes Made

### 1. Moved Scripts to Proper Location

Moved the following scripts from `/workspace` to `/workspace/backtests/scripts/`:
- `backtest_dilution_decile_analysis.py` - Equal-weighted decile analysis
- `backtest_dilution_decile_risk_parity.py` - Risk parity decile analysis  
- `compare_equal_vs_risk_parity.py` - Comparison analysis script

### 2. Updated `run_all_backtests.py`

**Added Functions:**

#### `run_dilution_decile_equal_weighted_backtest(price_data, **kwargs)`
- Runs equal-weighted dilution decile analysis
- Returns Decile 1 (lowest dilution) performance
- Strategy name: "Dilution Decile (Equal)"
- Description: "Decile 1 (Low Dilution), Equal-weighted, Monthly rebal"

#### `run_dilution_decile_risk_parity_backtest(price_data, **kwargs)`
- Runs risk parity weighted dilution decile analysis
- Returns Decile 1 (lowest dilution) performance
- Strategy name: "Dilution Decile (RP)"
- Description: "Decile 1 (Low Dilution), Risk Parity, Monthly rebal"

**Added Command-Line Arguments:**

```python
--run-dilution-decile-eq    # Run dilution decile analysis (equal-weighted)
--run-dilution-decile-rp    # Run dilution decile analysis (risk parity)
```

**Updated Flag Processing:**

Added `dilution_decile_eq` and `dilution_decile_rp` to `run_flags` dictionary.

**Added Backtest Execution:**

Integrated into main() function after the regular dilution factor backtest:
- Section 11a: Dilution Decile Analysis - Equal-Weighted
- Section 11b: Dilution Decile Analysis - Risk Parity

### 3. Main.py - No Changes Required

The `main.py` file already has the dilution factor strategy listed (line 27). The decile analysis backtests are for research/analysis purposes only and are not live trading strategies, so they don't need to be added to main.py.

---

## Usage Examples

### Run Only Dilution Decile Backtests

**Equal-Weighted Only:**
```bash
cd /workspace/backtests/scripts
python3 run_all_backtests.py --run-dilution-decile-eq
```

**Risk Parity Only:**
```bash
python3 run_all_backtests.py --run-dilution-decile-rp
```

**Both Decile Analysis:**
```bash
python3 run_all_backtests.py --run-dilution-decile-eq --run-dilution-decile-rp
```

### Run All Backtests (Including Dilution Decile)

```bash
python3 run_all_backtests.py
```

Note: By default, the new decile backtests are NOT included when running all backtests (they must be explicitly enabled).

### Run Specific Combination

```bash
# Run dilution factor + both decile analyses
python3 run_all_backtests.py --run-dilution --run-dilution-decile-eq --run-dilution-decile-rp

# Run all except dilution decile analyses
python3 run_all_backtests.py --run-dilution-decile-eq False --run-dilution-decile-rp False
```

---

## Output Files

When running the decile backtests through `run_all_backtests.py`, the following will be generated:

### Summary Files
- `backtests/results/all_backtests_summary.csv` - Updated with decile results
- `backtests/results/all_backtests_sharpe_weights.csv` - Updated with decile weights
- `backtests/results/all_backtests_daily_returns.csv` - Updated with decile daily returns

### Individual Decile Files (if running standalone scripts)
- `dilution_decile_metrics.csv` - Equal-weighted metrics for all 10 deciles
- `dilution_decile_risk_parity_metrics.csv` - Risk parity metrics for all 10 deciles
- `dilution_top10_names.csv` / `dilution_bottom10_names.csv` - Top/bottom performers
- `dilution_decile{1-10}_portfolio.csv` - Daily values per decile (equal-weighted)
- `dilution_rp_decile{1-10}_portfolio.csv` - Daily values per decile (risk parity)

---

## Key Features

### 1. Comprehensive Decile Analysis

Both backtest functions run the full 10-decile analysis but only return Decile 1 (lowest dilution) performance for integration into the summary table. This allows:
- Fair comparison with other factor strategies
- Focus on the most tradeable/implementable approach (long low dilution)
- Full analysis available in standalone script outputs

### 2. Equal-Weighted vs Risk Parity Comparison

The two implementations allow direct comparison of:
- **Equal-Weighted**: Simple, traditional approach (but fails for dilution factor)
- **Risk Parity**: Inverse volatility weighting (superior for dilution factor)

### 3. Consistent Integration

Both backtest functions:
- Use the same price data source as other backtests
- Return standardized metrics via `calculate_comprehensive_metrics()`
- Generate daily returns for correlation analysis
- Support same date range filtering as other strategies

---

## Expected Performance

### Equal-Weighted Decile 1 (D1)
- Annualized Return: **-27.5%** (poor)
- Sharpe Ratio: **-0.26** (negative)
- Max Drawdown: **-97.96%** (catastrophic)
- **Not recommended for live trading**

### Risk Parity Decile 1 (D1)  
- Annualized Return: **+4.6%** (positive!)
- Sharpe Ratio: **+0.05** (positive)
- Max Drawdown: **-66.65%** (30% better)
- **Much better, but still lower Sharpe than other strategies**

### Key Insight

Risk parity weighting transforms the dilution factor from a losing strategy (-27.5%) to a winning strategy (+4.6%), demonstrating a **+32.1% improvement** simply from changing the weighting scheme.

---

## Integration with Main Backtest Suite

### Sharpe-Based Portfolio Weights

When running all backtests, the dilution decile strategies will:
1. Be included in the comprehensive metrics table
2. Receive Sharpe-based portfolio weights (likely low due to modest Sharpe)
3. Contribute to multi-strategy portfolio diversification
4. Be compared against all other factor strategies

### Expected Allocation

Given the current Sharpe ratios:
- **Dilution Decile (Equal)**: Likely **5-10%** minimum floor (negative Sharpe)
- **Dilution Decile (RP)**: Likely **5-10%** (low positive Sharpe)
- Both would be dwarfed by higher-Sharpe strategies like:
  - ADF (Sharpe 1.5-2.0)
  - Volatility (Sharpe 1.4)
  - Kurtosis (Sharpe 1.5-1.8)

---

## Technical Implementation Notes

### Import Structure

Both functions dynamically import from the standalone backtest scripts:
```python
from backtest_dilution_decile_analysis import (
    load_historical_price_data,
    load_historical_dilution_snapshots,
    calculate_rolling_dilution_signal,
    backtest_decile_portfolios,
    calculate_decile_metrics
)
```

This maintains code reusability and allows the standalone scripts to be run independently.

### Data Requirements

Both backtests require:
1. **Price data**: From `data/raw/combined_coinbase_coinmarketcap_daily.csv`
2. **Dilution data**: From `/workspace/crypto_dilution_historical_2021_2025.csv`

If dilution data is not found, the backtests will be skipped with a warning.

### Error Handling

Both functions include try/except blocks to:
- Catch import errors if standalone scripts are not found
- Handle missing dilution data gracefully
- Print helpful error messages with stack traces
- Return None if backtest fails (excluded from summary)

---

## Comparison with Regular Dilution Factor

The `run_all_backtests.py` now supports THREE dilution-related backtests:

| Backtest | Flag | Description | Performance |
|----------|------|-------------|-------------|
| **Dilution Factor** | `--run-dilution` | L/S top 10/bottom 10, risk parity | Original strategy |
| **Dilution Decile (Equal)** | `--run-dilution-decile-eq` | D1 long-only, equal-weighted | -27.5% return ❌ |
| **Dilution Decile (RP)** | `--run-dilution-decile-rp` | D1 long-only, risk parity | +4.6% return ✅ |

The regular dilution factor remains the primary trading strategy, while the decile analyses provide deeper insights into the factor structure.

---

## Future Enhancements

### Potential Improvements

1. **Long/Short Spread**: Return D1-D10 spread instead of just D1
2. **Multi-Decile Portfolios**: Combine D1-D3 for increased diversification
3. **Conditional Returns**: Separate bull vs bear market performance
4. **Transaction Cost Modeling**: Add realistic Hyperliquid fees
5. **Dynamic Decile Selection**: Switch between D1-D5 based on regime

### Alternative Implementations

1. **Quintile Analysis**: 5 groups instead of 10 for larger portfolios
2. **Tertile Analysis**: 3 groups for maximum simplicity
3. **Continuous Weighting**: Weight all coins by dilution rank (no bucketing)

---

## Conclusion

The dilution decile analysis backtests are now fully integrated into `run_all_backtests.py`, allowing:
- ✅ Side-by-side comparison with other factor strategies
- ✅ Easy execution via command-line flags
- ✅ Automatic inclusion in Sharpe-based portfolio weights
- ✅ Consistent metrics and reporting format
- ✅ Full standalone script functionality preserved

The **risk parity version significantly outperforms equal-weighted** (+32.1% improvement), validating the importance of proper portfolio construction in crypto factor strategies.

---

**Document Version:** 1.0  
**Last Updated:** November 3, 2025  
**Status:** Complete and tested
