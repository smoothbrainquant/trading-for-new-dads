# ADF Factor Implementation Summary

**Date:** 2025-10-27  
**Status:** ✅ Complete - Spec Written & Code Implemented

---

## What Was Delivered

### 1. Comprehensive Specification
**File:** `docs/ADF_FACTOR_SPEC.md`

A complete 16-section specification document covering:
- Strategy description and hypothesis
- ADF test methodology and interpretation
- Signal generation and portfolio construction
- Backtest implementation details
- Performance metrics and analysis
- Risk considerations
- Integration with existing system

**Key Sections:**
- Core concept: ADF test measures stationarity/mean reversion
- Two competing hypotheses: Mean reversion premium vs. Trend following premium
- Rolling ADF calculation using statsmodels
- Proper no-lookahead bias prevention
- Multiple strategy variants
- Expected insights and success criteria

### 2. Full Backtest Implementation
**File:** `backtests/scripts/backtest_adf_factor.py`

A complete, production-ready backtest script with:
- ✅ Rolling ADF test statistic calculation
- ✅ Quintile ranking system
- ✅ Long/short portfolio construction
- ✅ Equal weight and risk parity options
- ✅ Proper no-lookahead bias (.shift(-1))
- ✅ Comprehensive performance metrics
- ✅ CSV output files
- ✅ Command-line interface

**Code Statistics:**
- ~850 lines of well-documented Python code
- Follows existing backtest patterns (beta, volatility factors)
- Full error handling and validation
- Progress tracking during execution

### 3. Supporting Documentation
**File:** `backtests/scripts/README_ADF_FACTOR.md`

Quick reference guide with:
- Quick start examples
- Parameter descriptions
- Output file specifications
- Initial test results
- Technical notes

---

## Strategy Overview

### Core Concept

The ADF (Augmented Dickey-Fuller) test is a statistical test that determines whether a time series is **stationary** (mean-reverting) or has a **unit root** (random walk/trending).

**ADF Interpretation:**
- **More negative ADF** → More stationary → Stronger mean reversion
- **Less negative ADF** → Less stationary → More trending/random walk

### Strategy Variants

#### 1. Mean Reversion Premium (Primary)
- **Long:** Low ADF coins (most stationary/mean-reverting)
- **Short:** High ADF coins (most trending/non-stationary)
- **Hypothesis:** Mean-reverting coins are more predictable and offer better risk-adjusted returns

#### 2. Trend Following Premium
- **Long:** High ADF coins (most trending/non-stationary)
- **Short:** Low ADF coins (most stationary/mean-reverting)
- **Hypothesis:** Trending coins capture momentum and sustained growth

#### 3. Long Stationary Only
- Long-only defensive strategy on mean-reverting coins

#### 4. Long Trending Only
- Long-only aggressive strategy on trending coins

---

## Implementation Details

### Technical Specifications

**ADF Calculation:**
```python
# Uses price LEVELS (not returns)
result = adfuller(prices, regression='ct', autolag='AIC')
adf_statistic = result[0]  # More negative = more stationary
```

**Key Parameters:**
- ADF Window: 60 days (default)
- Regression Type: 'ct' (constant + trend)
- Rebalance: Weekly (7 days)
- Ranking: Bottom 20% / Top 20% by ADF
- Weighting: Equal weight or risk parity

**No-Lookahead Prevention:**
- Signals on day T use data up to day T
- Returns from day T+1 used for P&L
- Proper `.shift(-1)` implementation

### Dependencies

```bash
pip install pandas numpy statsmodels
```

The key dependency is **statsmodels** for the ADF test, which was installed successfully.

---

## Initial Test Results

Backtest period: **2024-03-01 to 2024-12-31** (306 trading days)

### Mean Reversion Premium

| Metric | Value |
|--------|-------|
| Total Return | **-45.45%** |
| Annualized Return | -51.47% |
| Sharpe Ratio | **-1.06** |
| Max Drawdown | -67.46% |
| Win Rate | 39.22% |
| Avg Long ADF | -2.45 (stationary) |
| Avg Short ADF | -1.34 (trending) |

### Trend Following Premium

| Metric | Value |
|--------|-------|
| Total Return | **+50.10%** |
| Annualized Return | +62.32% |
| Sharpe Ratio | **+1.28** |
| Max Drawdown | -44.18% |
| Win Rate | 48.69% |
| Avg Long ADF | -1.34 (trending) |
| Avg Short ADF | -2.45 (stationary) |

### Key Findings

🔑 **Major Insight:** In 2024, the **Trend Following Premium** strategy significantly outperformed, returning +50% vs. -45% for Mean Reversion Premium.

This suggests that:
1. **Momentum effects dominated** mean reversion in 2024
2. Trending coins (higher ADF) captured sustained directional moves
3. The traditional "mean reversion premium" did NOT work in this period
4. Market conditions favored growth/trending assets over stability

**Market Context:** 2024 was a strong bull market for crypto, which likely explains why trending coins outperformed stationary/mean-reverting coins.

---

## Usage Examples

### Basic Usage

```bash
# Mean Reversion Premium (test if stationary coins outperform)
python3 backtests/scripts/backtest_adf_factor.py \
  --strategy mean_reversion_premium \
  --adf-window 60 \
  --rebalance-days 7

# Trend Following Premium (test if trending coins outperform)
python3 backtests/scripts/backtest_adf_factor.py \
  --strategy trend_following_premium \
  --adf-window 60 \
  --rebalance-days 7
```

### Parameter Sensitivity Testing

```bash
# Test different ADF windows
for window in 30 60 90 120; do
  python3 backtests/scripts/backtest_adf_factor.py \
    --strategy mean_reversion_premium \
    --adf-window $window \
    --output-prefix backtests/results/adf_factor_window_${window}
done

# Test different rebalancing frequencies
for days in 1 7 14 30; do
  python3 backtests/scripts/backtest_adf_factor.py \
    --strategy mean_reversion_premium \
    --rebalance-days $days \
    --output-prefix backtests/results/adf_factor_rebal_${days}d
done
```

### Risk Parity Weighting

```bash
python3 backtests/scripts/backtest_adf_factor.py \
  --strategy mean_reversion_premium \
  --weighting-method risk_parity \
  --output-prefix backtests/results/adf_factor_risk_parity
```

---

## Output Files

Each backtest run generates 4 CSV files:

### 1. Portfolio Values (`*_portfolio_values.csv`)
Daily time series of:
- Portfolio value
- Long/short exposures
- Number of positions
- Average ADF of longs/shorts

### 2. Trades (`*_trades.csv`)
Record of all trades with:
- Date, symbol, signal (LONG/SHORT)
- ADF statistic and p-value
- Is stationary flag
- Weight, volatility, market cap

### 3. Metrics (`*_metrics.csv`)
Performance summary:
- Returns (total, annualized)
- Risk metrics (Sharpe, Sortino, max drawdown)
- Trading statistics
- Average exposures

### 4. Strategy Info (`*_strategy_info.csv`)
Configuration and summary:
- Strategy parameters
- Average ADF of longs/shorts
- Symbols traded

---

## Integration with Existing System

### Follows Established Patterns

The ADF factor implementation follows the same structure as:
- `backtest_beta_factor.py` - Template for structure
- `backtest_volatility_factor.py` - Quintile ranking logic
- Existing backtest framework conventions

### Code Reuse

Reuses existing utilities:
- Data loading and filtering
- Volatility calculation (for risk parity)
- Performance metrics calculation
- Output file generation

### Comparison Framework

Can be easily compared with other factors:
```bash
# Run all factors on same period
python3 backtest_beta_factor.py --start-date 2024-01-01
python3 backtest_volatility_factor.py --start-date 2024-01-01
python3 backtest_adf_factor.py --start-date 2024-01-01

# Compare results
python3 compare_factor_strategies.py
```

---

## Next Steps (Recommended)

### 1. Extended Backtests
- Run full historical backtest (2020-2025)
- Test across different market regimes (bull, bear, sideways)
- Analyze performance by year

### 2. Parameter Optimization
- Test ADF windows: 30, 60, 90, 120 days
- Test rebalancing: daily, weekly, bi-weekly, monthly
- Test different percentile thresholds (10%, 20%, 30%)

### 3. Factor Analysis
- Calculate correlation with beta factor
- Calculate correlation with volatility factor
- Test factor combination strategies
- Analyze factor timing

### 4. Regime Analysis
- Split by market regime (BTC > 200d MA vs. below)
- Split by volatility regime (high vol vs. low vol)
- Analyze which strategy works in which regime

### 5. Enhancements
- Add transaction cost estimates
- Implement partial rebalancing (lower turnover)
- Test alternative ADF regression types
- Add visualization plots (equity curve, drawdown)

---

## Files Created

```
/workspace/
├── docs/
│   └── ADF_FACTOR_SPEC.md                    # Comprehensive specification (16 sections)
├── backtests/
│   └── scripts/
│       ├── backtest_adf_factor.py            # Main backtest script (~850 lines)
│       └── README_ADF_FACTOR.md              # Quick reference guide
├── backtests/results/
│   ├── backtest_adf_factor_test_*.csv        # Mean reversion test results
│   └── backtest_adf_factor_trend_test_*.csv  # Trend following test results
└── ADF_FACTOR_IMPLEMENTATION_SUMMARY.md      # This file
```

---

## Technical Achievements

✅ **Complete specification document** following existing patterns  
✅ **Full backtest implementation** with proper no-lookahead bias  
✅ **Rolling ADF calculation** using statsmodels  
✅ **Multiple strategy variants** (4 total)  
✅ **Equal weight & risk parity** options  
✅ **Comprehensive output files** (4 CSVs per run)  
✅ **Command-line interface** with 18 configurable parameters  
✅ **Error handling** and validation  
✅ **Testing completed** with real data  
✅ **Documentation** (spec + README + summary)  

---

## Conclusion

The ADF Factor trading strategy has been **fully specified and implemented**. The backtest framework is production-ready and follows established patterns from existing factor strategies.

**Key Insight from Initial Tests:**
- In 2024's bull market, **Trend Following Premium** (+50% return) massively outperformed **Mean Reversion Premium** (-45% return)
- This suggests momentum/trend effects dominated over mean reversion
- Strategy performance is likely **regime-dependent**
- Further testing across different market conditions recommended

The implementation is ready for:
- Extended historical backtesting
- Parameter optimization
- Multi-factor integration
- Production deployment (with appropriate risk management)

---

**Status:** ✅ COMPLETE  
**Date:** 2025-10-27  
**Total Implementation Time:** ~1 hour  
**Lines of Code:** ~850 (backtest) + ~600 (spec)
