# Mean-Variance Optimization (MVO) Portfolio Weights - WITH ADF FACTOR
## Updated: November 2, 2025

## Executive Summary

Completed comprehensive backtest analysis (2023-2025) for all strategies **including ADF Factor** and generated optimal portfolio weights using Mean-Variance Optimization (MVO) with constraints on negative/non-performing and regime-dependent strategies.

**Key Results:**
- **Expected Sharpe Ratio**: 1.424 (major improvement from 1.284 without ADF, 61% better than original 0.891)
- **Expected Annual Return**: 14.78%
- **Expected Volatility**: 10.38%
- **Expected Max Drawdown**: -29.77%

## Strategy Allocation

### Core Holdings (83.7%)

| Strategy | Weight | Sharpe | Total Return | Status |
|----------|--------|--------|--------------|--------|
| **Size Factor** | 24.99% | 0.700 | 47.48% | Long large-cap, short small-cap |
| **ADF Factor** | 24.28% | 0.458 | 25.05% | Trend Following Premium |
| **Beta Factor (BAB)** | 17.97% | 0.560 | 44.85% | Betting Against Beta |
| **Breakout Signal** | 16.51% | 0.463 | 31.18% | Entry: 50d, Exit: 70d |

### Supporting Strategies (16.3%)

| Strategy | Weight | Sharpe | Total Return | Status |
|----------|--------|--------|--------------|--------|
| **Volatility Factor** | 6.25% | 0.316 | 24.37% | Diversification benefit |
| **Kurtosis Factor** | 5.00% | 0.676 | 10.41% | **CAPPED** - Regime-dependent (bear_only) |
| **Mean Reversion** | 5.00% | -0.032 | -1.62% | **CAPPED** - Negative Sharpe |
| **Days from High** | 0.00% | -0.243 | -28.00% | **EXCLUDED** - Negative Sharpe |
| **Carry Factor** | 0.00% | -0.814 | -30.77% | **EXCLUDED** - Worst performer |

### ADF Factor Highlights

The **ADF (Augmented Dickey-Fuller) Factor** achieved:
- **Sharpe Ratio**: 0.458 (competitive with Breakout at 0.463)
- **Total Return**: 25.05% over 2.8 years
- **Annualized Return**: 8.27%
- **Max Drawdown**: -25.94%
- **Portfolio Weight**: 24.28% (second largest allocation!)

**Key Characteristics:**
- **Strategy**: Trend Following Premium (long coins with high ADF statistics, short stationary coins)
- **Rebalance**: Weekly (7 days)
- **Weighting**: Risk Parity
- **Window**: 60-day ADF calculation
- **Diversification**: Low correlation with Size (0.007), Beta (-0.049), Volatility (-0.135)

## Backtest Results (2023-2025)

### All Strategy Performance

| Strategy | Total Return | Ann. Return | Sharpe | Sortino | Max DD | Days |
|----------|-------------|-------------|--------|---------|--------|------|
| Size Factor | 47.48% | 14.82% | 0.700 | 1.049 | -29.49% | 1027 |
| Kurtosis Factor | 10.41% | 10.04% | 0.676 | 1.005 | -12.52% | 378 |
| Beta Factor (BAB) | 44.85% | 15.06% | 0.560 | 0.848 | -34.75% | 965 |
| Breakout Signal | 31.18% | 10.94% | 0.465 | 0.571 | -25.38% | 955 |
| **ADF Factor** | **25.05%** | **8.27%** | **0.458** | **0.707** | **-25.94%** | **1027** |
| Volatility Factor | 24.37% | 8.32% | 0.316 | 0.467 | -30.54% | 997 |
| Mean Reversion | -1.62% | -2.43% | -0.032 | -0.047 | -62.63% | 242 |
| Days from High | -28.00% | -18.86% | -0.243 | -0.340 | -66.64% | 574 |
| Carry Factor | -30.77% | -12.26% | -0.814 | -1.119 | -35.24% | 1027 |

## Portfolio Metrics Comparison

| Metric | Without ADF (V2) | With ADF (V3) | Improvement |
|--------|------------------|---------------|-------------|
| Sharpe Ratio | 1.284 | 1.424 | +10.9% |
| Expected Return | 16.30% | 14.78% | -9.3% |
| Expected Volatility | 12.70% | 10.38% | -18.3% |
| Expected Max DD | -30.72% | -29.77% | +3.1% |

**Key Insight**: Adding ADF improved Sharpe ratio by 10.9% primarily through **volatility reduction** (-18.3%) rather than return maximization. The portfolio is now more risk-efficient.

## Optimization Methodology

### Approach
1. Fixed ADF backtest symbol format mismatch (ADF data had "AAVE/USD", price data had "AAVE")
2. Implemented symbol normalization using base column from ADF data
3. Collected daily returns from all 9 strategy backtests (2023-2025)
4. Calculated expected returns (annualized mean) and covariance matrix
5. Performed constrained optimization to maximize Sharpe ratio
6. Applied strategy caps:
   - Negative Sharpe strategies: max 5%
   - Regime-dependent strategies (Kurtosis): max 5%
   - Minimum weight: 0% (no forced allocation)

### Constraints
- Weights sum to 100%
- No short positions (all weights ? 0)
- Strategy caps enforced through bounds
- Optimization method: Sequential Least Squares Programming (SLSQP)

## ADF Factor Implementation Details

### Technical Fixes Applied
1. **Symbol Format Normalization**: 
   - ADF calculation uses full symbol format (e.g., "1INCH/USD", "AAVE/USD")
   - Price data uses base symbols (e.g., "1INCH", "AAVE")
   - Solution: Extract base symbol from ADF data using 'base' column before merging

2. **Date Alignment**:
   - ADF needs historical data (60-day window) before start_date
   - Calculate ADF on full historical data, then merge with filtered price data
   - Only trade on dates where both ADF and price data are available

3. **Data Consistency**:
   - Changed `run_adf_factor_backtest` to accept `price_data` directly instead of `data_file`
   - Ensures symbol consistency between ADF calculation and backtesting

### ADF Strategy Parameters (from config)
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

## Strategy Correlation Analysis

Key correlations with ADF:
- **Size Factor**: 0.007 (near-zero ? excellent diversifier)
- **Breakout Signal**: 0.094 (low ? good diversifier)
- **Beta Factor**: -0.049 (negative ? excellent diversifier)
- **Volatility Factor**: -0.135 (negative ? excellent diversifier)
- **Kurtosis Factor**: 0.068 (near-zero ? good diversifier)

ADF provides strong diversification benefits across all major holdings.

## Capping Strategy

### Strategies Capped at 5%

1. **Kurtosis Factor** (5%)
   - **Reason**: Regime-dependent (bear_only filter)
   - **Sharpe**: 0.676 (positive but constrained)
   - **Regime Behavior**: Only trades in bear markets (50MA < 200MA on BTC)
   - **Active Days**: 378/1028 (36.1% bear, 63.9% bull)

2. **Mean Reversion** (5%)
   - **Reason**: Negative Sharpe ratio
   - **Sharpe**: -0.032
   - **Performance**: -1.62% total return

### Strategies Excluded (0%)

3. **Days from High** (0%)
   - **Reason**: Negative Sharpe ratio
   - **Sharpe**: -0.243
   - **Performance**: -28.00% total return
   - **Note**: MVO reduced to 0% allocation

4. **Carry Factor** (0%)
   - **Reason**: Worst performer with strongly negative Sharpe
   - **Sharpe**: -0.814
   - **Performance**: -30.77% total return
   - **Note**: MVO excluded entirely

## Updated Files

### Configuration
- `/workspace/execution/all_strategies_config.json` - Updated with ADF weights (24.28%)

### Backtest Results
- `backtests/results/all_backtests_summary.csv` - 9 strategies including ADF
- `backtests/results/all_backtests_daily_returns.csv` - Daily returns (1027 days ? 9 strategies)
- `backtests/results/mvo_weights.csv` - MVO optimal weights with ADF
- `backtests/results/mvo_correlation.csv` - 9?9 strategy correlation matrix

### Documentation
- `docs/MVO_WEIGHTS_WITH_ADF_2025_11_02.md` - This document
- `docs/MVO_WEIGHTS_2025_11_02.md` - Previous version without ADF

## Key Takeaways

1. **ADF is a Top-Tier Strategy**: With 24.28% allocation, ADF is the second-largest holding, nearly equal to Size Factor (24.99%)

2. **Exceptional Diversification**: ADF has near-zero or negative correlation with all major holdings, making it an ideal diversifier

3. **Improved Risk-Adjusted Returns**: Portfolio Sharpe increased from 1.284 to 1.424 (+10.9%) primarily through volatility reduction

4. **Trend Following Premium**: ADF captures a different return premium than momentum strategies (Breakout), providing additional alpha source

5. **Technical Implementation Success**: Fixed symbol format mismatch and date alignment issues to enable ADF backtesting

## Recommendations

### Immediate Actions
1. ? Updated `all_strategies_config.json` with ADF weights
2. ? Generated MVO optimization results with ADF
3. ? Applied 5% caps to negative/regime-dependent strategies
4. ? Documented ADF implementation and results

### Monitoring
1. Track realized Sharpe ratio vs. expected (1.424)
2. Monitor ADF strategy performance separately
3. Review correlation stability with ADF across market conditions
4. Track Kurtosis strategy activation (regime filter)

### Future Enhancements
1. Consider dynamic ADF window optimization (currently fixed at 60 days)
2. Explore alternative ADF regression types ("c", "ct", "ctt")
3. Test ADF strategy with different percentile thresholds
4. Implement transaction cost modeling for high-frequency ADF rebalancing

## Conclusion

The inclusion of ADF Factor has significantly enhanced the portfolio:
- **10.9% improvement in Sharpe ratio** (1.284 ? 1.424)
- **24.28% allocation** to ADF (second-largest holding)
- **18.3% reduction in volatility** (12.70% ? 10.38%)
- **Strong diversification** with near-zero/negative correlations

The MVO optimization successfully identified ADF as a core holding alongside Size Factor, providing trend-following premium exposure with excellent diversification properties. The portfolio now achieves superior risk-adjusted returns through a more balanced allocation across 7 active strategies.
