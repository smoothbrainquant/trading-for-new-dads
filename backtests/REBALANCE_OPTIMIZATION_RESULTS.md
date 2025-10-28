# Rebalance Parameter Optimization Results

**Date:** 2025-10-28  
**Optimization Script:** `backtests/scripts/optimize_rebalance_params.py`

## Executive Summary

We tested different rebalance frequencies (1, 3, 7, 14, 30 days) for each backtest strategy to identify optimal parameters. The optimization focused on maximizing Sharpe Ratio as the primary metric, with additional consideration for Calmar Ratio and total returns.

## Results by Strategy

### 1. Carry Factor Strategy ✅

**Status:** Optimization Complete

| Rebalance Days | Sharpe Ratio | Ann. Return | Max Drawdown | Calmar Ratio | Win Rate |
|---------------|--------------|-------------|--------------|--------------|----------|
| **1** (optimal) | **0.792** | **27.77%** | -38.09% | **0.729** | 52.19% |
| 3 | 0.433 | 15.98% | -52.39% | 0.305 | 52.10% |
| 7 (current) | 0.761 | 27.91% | -42.56% | 0.656 | 51.66% |
| 14 | -0.339 | -12.37% | -71.67% | -0.173 | 49.83% |
| 30 | -0.176 | -6.73% | -57.66% | -0.117 | 51.13% |

**Recommendation:** Change from 7-day to **1-day (daily) rebalancing**
- Improves Sharpe Ratio by 4.1%
- Better risk-adjusted returns (higher Calmar ratio)
- Lower maximum drawdown (-38% vs -43%)

**Key Insights:**
- Carry factor strategy benefits significantly from frequent rebalancing
- Performance degrades sharply beyond 7-day rebalancing
- Daily rebalancing likely captures short-term mean reversion in funding rates
- 14-day and 30-day rebalancing show negative returns, indicating missed opportunities

### 2. Beta Factor Strategy ⚠️

**Status:** Ran but returned NaN values (likely insufficient data or strategy implementation issue)

**Action Needed:** 
- Review beta factor backtest implementation
- Check if BTC data is available for beta calculation
- Verify minimum data requirements are met

### 3. Volatility Factor Strategy ❌

**Status:** Failed - directory path issue

**Error:** `OSError: Cannot save file into a non-existent directory: 'backtests/results/backtests/results'`

**Cause:** The volatility factor script has a bug where it's doubling the output directory path

**Action Needed:**
- Fix the path handling in `backtest_volatility_factor.py`
- The script appears to be prepending `backtests/results/` to an already complete path

### 4. Kurtosis Factor Strategy ❌

**Status:** Failed - missing scipy dependency

**Error:** `ModuleNotFoundError: No module named 'scipy'`

**Action Needed:**
- Add scipy to requirements.txt
- Install scipy: `pip install scipy`

### 5. Skew Factor Strategy ⏭️

**Status:** Skipped - strategy uses fixed daily rebalancing by design

**Note:** This strategy is already optimized for daily rebalancing and doesn't have a configurable rebalance parameter.

### 6. Size Factor Strategy ⏭️

**Status:** Disabled - requires market cap data file or API

### 7. Open Interest Divergence Strategy ⏭️

**Status:** Disabled - aggregated OI file not available

## Recommendations

### Immediate Actions

1. **Carry Factor:** ✅ Update default rebalance parameter from 7 to 1 day
   - Update script: `backtests/scripts/backtest_carry_factor.py`
   - Change line 631: `default=1` instead of `default=7`

2. **Fix Volatility Factor:** Fix the output path bug
   - Check `save_results()` function in `backtest_volatility_factor.py`
   - Ensure output_prefix is used correctly

3. **Fix Kurtosis Factor:** Install scipy dependency
   ```bash
   pip install scipy
   echo "scipy>=1.11.0" >> requirements.txt
   ```

4. **Review Beta Factor:** Investigate why metrics are NaN
   - Check if BTC data exists in dataset
   - Review beta calculation implementation
   - Verify data quality and coverage

### Next Steps for Complete Optimization

1. Fix the issues identified above
2. Re-run optimization for:
   - Beta Factor
   - Volatility Factor  
   - Kurtosis Factor

3. Consider testing additional rebalance frequencies:
   - For carry factor, test 1, 2, 5 days to fine-tune
   - Test semi-daily or 12-hour rebalancing if supported

4. Analyze transaction costs impact:
   - Daily rebalancing may have higher costs
   - Consider cost-benefit analysis at 1-day vs 7-day

## Performance Metrics Explained

- **Sharpe Ratio:** Risk-adjusted return (higher is better)
- **Annualized Return:** Expected yearly return percentage
- **Maximum Drawdown:** Largest peak-to-trough decline
- **Calmar Ratio:** Return / |Max Drawdown| (higher is better)
- **Win Rate:** Percentage of profitable days

## Files Generated

- `backtests/results/rebalance_optimization_summary.csv` - Summary of all results
- `backtests/results/rebalance_optimization_carry_factor.csv` - Detailed carry factor results
- `backtests/results/backtest_carry_factor_rebal_*d_*.csv` - Individual run results

## Methodology

Each strategy was tested with rebalance frequencies of 1, 3, 7, 14, and 30 days using identical data and parameters (except rebalance frequency). The optimization script:

1. Runs each backtest with different rebalance parameters
2. Collects performance metrics
3. Identifies optimal parameters based on Sharpe Ratio
4. Generates summary reports

**Script Location:** `backtests/scripts/optimize_rebalance_params.py`

**Usage:**
```bash
# Run all strategies
python3 backtests/scripts/optimize_rebalance_params.py

# Run specific strategy
python3 backtests/scripts/optimize_rebalance_params.py --strategies carry_factor

# Test custom rebalance values
python3 backtests/scripts/optimize_rebalance_params.py --rebalance-values 1 2 5 10
```
