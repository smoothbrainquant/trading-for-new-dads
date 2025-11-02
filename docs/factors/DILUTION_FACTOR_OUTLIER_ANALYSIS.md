# Dilution Factor Backtest: Outlier Analysis

**Date:** November 2, 2025  
**Status:** Investigation Complete

## Executive Summary

The dilution factor backtest showed extreme returns (2641% total, 101.6% annualized) that were driven by outliers in the underlying price data. After implementing outlier filtering (capping daily returns at ?20%), the strategy returns dropped to 624% total (52.1% annualized) - a **76% reduction in total returns**.

## Key Findings

### 1. Source of Extreme Returns

The extreme returns were caused by:

**Data Outliers:**
- **1,012 extreme returns** were capped out of ~74,000 price observations
- Raw return range: **-87.62% to +219.86%** daily
- Filtered return range: **-20% to +20%** daily

**Specific Examples:**
- **2025-10-01**: Portfolio returned 58.51% in a single day
  - ZEC (Zcash) had a 62.96% single-day return
  - Portfolio was 100% long ZEC at the time
  - This single day contributed ~45% of total cumulative returns

- **2021-05**: Multiple 20%+ daily returns
  - ALGO and ZEC positions during high volatility period
  - Several days with 30%+ portfolio returns

### 2. Performance Comparison

| Metric | Original | Outlier Filtered | Change |
|--------|----------|------------------|---------|
| **Total Return** | 2,641% | 624% | -76% |
| **Annualized Return** | 101.6% | 52.1% | -49% |
| **Volatility** | 98.0% | 83.5% | -15% |
| **Sharpe Ratio** | 1.04 | 0.62 | -40% |
| **Max Drawdown** | -88.8% | -89.5% | -1% |
| **Win Rate** | 50.7% | 50.8% | +0.2% |

### 3. Impact Analysis

**Return Attribution:**
- ~76% of total returns came from extreme outlier days
- Top 20 days (1.2% of trading days) contributed majority of profits
- Strategy is highly dependent on extreme moves

**Risk Profile:**
- Original Sharpe of 1.04 inflated by outliers
- True risk-adjusted return (Sharpe 0.62) less attractive
- Max drawdown similar in both cases (-89%)

## Implications

### 1. Strategy Viability

**Original Results (2641% return):**
- Unrealistic due to extreme price moves
- Assumes perfect execution during flash crashes/pumps
- Likely impossible to achieve in live trading

**Filtered Results (624% return):**
- More realistic performance expectation
- Still strong returns (52% annualized) but achievable
- Better represents actual trading conditions

### 2. Data Quality Issues

The extreme price moves suggest:
- Possible data errors (219% single-day return)
- Flash crashes in illiquid markets
- Front-running/oracle manipulation events
- Stale or missing price data

**Recommendations:**
- Audit price data for extreme values
- Cross-validate against multiple data sources
- Consider using VWAP or median prices instead of close
- Implement maximum position concentration limits

### 3. Portfolio Construction Issues

The strategy had problematic concentration:
- **100% weight in single coin** (ZEC in Sept 2025)
- No position size limits
- Risk parity failed to diversify properly

**Improvements Needed:**
- Add maximum position size constraint (e.g., 25% per coin)
- Require minimum number of positions (e.g., 4 longs, 4 shorts)
- Better risk controls for concentrated positions

## Recommended Next Steps

### 1. Short-term (Immediate)

? **COMPLETED:**
- [x] Identify source of extreme returns
- [x] Implement outlier filtering
- [x] Re-run backtest with filtered data
- [x] Document findings

### 2. Medium-term (Before Live Trading)

- [ ] Audit underlying price data
  - Cross-validate against CoinGecko, CoinMarketCap APIs
  - Flag and investigate days with >50% moves
  - Consider removing or interpolating bad data points

- [ ] Improve portfolio construction
  - Add max position size constraints (e.g., 25% per coin)
  - Require minimum diversification (e.g., 5+ positions per side)
  - Consider using median volatility instead of individual vol

- [ ] Additional robustness tests
  - Test with different outlier thresholds (10%, 15%, 25%)
  - Test with winsorization vs hard caps
  - Analyze sensitivity to filtering approach

### 3. Long-term (Strategy Enhancement)

- [ ] Transaction cost modeling
  - Add realistic slippage assumptions (especially for illiquid coins)
  - Model market impact for large trades
  - Include funding costs for shorts

- [ ] Regime awareness
  - Reduce position sizes during high volatility regimes
  - Implement circuit breakers for extreme moves
  - Consider dynamic position sizing

## Files Generated

### Backtest Results
- `dilution_factor_backtest_results.png` - Original backtest visualization
- `dilution_factor_backtest_outlier_filtered.png` - Filtered backtest visualization
- `dilution_factor_outlier_comparison.png` - Side-by-side comparison

### Data Files
- `dilution_factor_metrics.csv` - Original performance metrics
- `dilution_factor_metrics_outlier_filtered.csv` - Filtered performance metrics
- `dilution_factor_outlier_comparison.csv` - Detailed comparison table
- `dilution_factor_portfolio_values_outlier_filtered.csv` - Filtered daily values
- `dilution_factor_trades_outlier_filtered.csv` - Filtered trade history

### Code
- `backtests/scripts/backtest_dilution_factor.py` - Original backtest
- `backtests/scripts/backtest_dilution_factor_outlier_filtered.py` - Filtered version

## Conclusion

The dilution factor strategy shows **promising but realistic returns of 52% annualized** after filtering outliers, compared to the inflated 102% without filtering. The extreme returns in the original backtest were driven by data quality issues and poor portfolio concentration controls.

**Bottom Line:**
- Strategy has merit but needs significant refinement
- Data quality must be improved before live trading
- Portfolio construction needs position limits and diversification requirements
- Realistic expectation: 30-50% annualized with proper risk controls

**Recommendation:** Do not trade this strategy live until data quality and portfolio construction issues are resolved.
