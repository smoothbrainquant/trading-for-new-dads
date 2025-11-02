# Dilution Factor Backtest: Outlier Analysis

**Date:** November 2, 2025  
**Status:** Investigation Complete

## Executive Summary

The dilution factor backtest showed extreme returns (2641% total, 101.6% annualized) that were driven by outliers in the underlying price data. After implementing outlier filtering (capping daily returns at ?20%), the strategy returns dropped to 624% total (52.1% annualized) - a **76% reduction in total returns**.

## Root Cause: Portfolio Construction Bug

### The Critical Bug

The backtest had a **data matching problem** in the portfolio construction logic:

```python
# BUGGY CODE (original):
# 1. Select top 10 long + top 10 short based on dilution
long_candidates = valid_signals.head(10)
short_candidates = valid_signals.tail(10)

# 2. Try to calculate volatility (requires price data)
long_candidates['volatility'] = calculate_volatility(...)

# 3. Filter out coins without price data
long_candidates = long_candidates[volatility.notna()]
# Result: Most coins get filtered out!
```

**The Problem:**
- Dilution data: 565 coins
- Price data: 172 coins  
- **Only 170 coins have BOTH**
- Strategy selected based on dilution first, then 15/20 positions had no price data
- **Result: 1-4 positions instead of 20**

### Data Coverage Analysis

| Dataset | Coins | Missing From Other |
|---------|-------|-------------------|
| Dilution data | 565 | - |
| Price data | 172 | - |
| **Both** | **170** | - |
| Dilution only | 395 | BNB, TON, USDC, TRX, OKB, etc. |

**Example (2025-09-01):**
- Selected: 10 long + 10 short = 20 positions
- With price data: 1 long (ZEC) + 4 shorts (MORPHO, ENA, ETHFI, W) = 5 positions
- **Lost 15/20 positions** = 75% of portfolio

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

| Metric | Original (Broken) | Outlier Filtered (Still Broken) | **FIXED (Proper Diversification)** |
|--------|----------|------------------|---------|
| **Total Return** | 2,641% | 624% | **-27.8%** ? |
| **Annualized Return** | 101.6% | 52.1% | **-6.7%** ? |
| **Volatility** | 98.0% | 83.5% | **40.3%** |
| **Sharpe Ratio** | 1.04 | 0.62 | **-0.17** ? |
| **Max Drawdown** | -88.8% | -89.5% | **-61.0%** |
| **Portfolio Size** | 1-4 positions ? | 1-4 positions ? | **10-16 positions** ? |

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
- ? **COMPLETELY FAKE** - caused by portfolio construction bug
- Portfolio collapsed to 1-4 concentrated positions
- Caught lucky extreme moves in undiversified portfolio
- **NOT ACHIEVABLE** even with perfect execution

**Outlier Filtered Results (624% return):**
- ? **STILL FAKE** - same portfolio bug, just capped returns
- Still only 1-4 positions, not properly diversified
- Better than original but still fundamentally broken

**FIXED Results (-27.8% return):**
- ? **REALISTIC** - proper 10-16 position diversification  
- ? Shows true performance of dilution factor
- **STRATEGY DOES NOT WORK** - loses money with proper implementation
- Do NOT trade this strategy

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

The dilution factor strategy **DOES NOT WORK**. The apparent 2,641% return was entirely due to a portfolio construction bug that caused the strategy to collapse into 1-4 concentrated positions and catch lucky outlier moves.

**The Truth:**
- **Original backtest**: 2,641% return with 1-4 positions ? FAKE (bug + luck)
- **Outlier filtered**: 624% return with 1-4 positions ? FAKE (bug + capped luck)  
- **Properly fixed**: -27.8% return with 10-16 positions ? REAL (loses money)

**Why It Failed:**
1. Only 170 coins have both dilution AND price data (out of 565 in universe)
2. Portfolio construction bug selected coins without checking price data availability
3. Most selections had no price data ? fell back to whatever was tradeable
4. Result: Accidental concentration in 1-4 coins
5. Those coins happened to have extreme moves ? fake good performance

**Bottom Line:**
- ? Strategy loses money with proper diversification (-6.7% annualized)
- ? Dilution factor does NOT predict returns in this implementation
- ? Do NOT trade this strategy under any circumstances

**Recommendation:** **ABANDON THIS STRATEGY**. The dilution factor does not provide predictive value for cryptocurrency returns when properly tested with adequate diversification.
