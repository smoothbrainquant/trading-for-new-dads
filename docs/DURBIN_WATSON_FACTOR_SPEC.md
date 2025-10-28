# Durbin-Watson Factor Trading Strategy Specification

**Version:** 1.0  
**Date:** 2025-10-27  
**Status:** Specification - Ready for Implementation

---

## 1. Executive Summary

This specification outlines a quantitative trading strategy based on the **Durbin-Watson statistic**, which measures autocorrelation in price returns. The core hypothesis is that cryptocurrencies exhibit varying degrees of serial correlation in their returns, and these patterns can be exploited through systematic long/short portfolios.

### Key Objectives
1. Calculate Durbin-Watson statistic for all cryptocurrencies
2. Rank coins by their autocorrelation properties
3. Implement long/short portfolios based on DW rankings
4. Test whether momentum vs. mean reversion patterns are predictable
5. Compare performance to existing factor strategies

### Strategy Overview
- **Factor**: Durbin-Watson statistic (autocorrelation measure)
- **Universe**: All liquid cryptocurrencies with sufficient trading history
- **Rebalancing**: Weekly (configurable)
- **Market Neutrality**: Dollar-neutral long/short construction
- **Hypothesis**: Serial correlation patterns predict future returns

---

## 2. Strategy Description

### 2.1 Core Concept

The **Durbin-Watson statistic** tests for first-order autocorrelation in time series data (residuals):

\[ DW = \frac{\sum_{t=2}^{T} (r_t - r_{t-1})^2}{\sum_{t=1}^{T} r_t^2} \]

Where:
- \( r_t \) = Return at time t (can use raw returns or residuals from a model)
- \( T \) = Sample size (lookback window)

**Interpretation:**
- **DW ≈ 2**: No autocorrelation (random walk)
- **DW < 2**: Positive autocorrelation (momentum/trending behavior)
- **DW > 2**: Negative autocorrelation (mean reversion/oscillating behavior)
- **DW ≈ 0**: Strong positive autocorrelation (strong momentum)
- **DW ≈ 4**: Strong negative autocorrelation (strong mean reversion)

**Approximate Relationship:**
\[ DW \approx 2(1 - \rho) \]

Where \( \rho \) is the first-order autocorrelation coefficient:
- \( \rho = 0 \) → DW = 2 (no autocorrelation)
- \( \rho = +1 \) → DW = 0 (perfect positive autocorrelation)
- \( \rho = -1 \) → DW = 4 (perfect negative autocorrelation)

### 2.2 Trading Hypothesis

**Primary Hypothesis: Autocorrelation Reversal**
- Coins with **low DW** (high momentum) → Potential exhaustion → SHORT
- Coins with **high DW** (mean reversion) → Oversold/overbought → LONG

**Alternative Hypothesis: Autocorrelation Continuation**
- Coins with **low DW** (momentum) → Trend continues → LONG
- Coins with **high DW** (choppy) → Avoid or SHORT

### 2.3 Strategy Variants

#### Variant A: Contrarian (Mean Reversion) - Primary Strategy
- **Long**: Coins with high DW (2.5-4) = Mean reverting, recent oscillations
- **Short**: Coins with low DW (0-1.5) = Trending momentum (exhaustion bet)
- **Rationale**: Momentum exhausts, mean reversion pays off

#### Variant B: Momentum Continuation
- **Long**: Coins with low DW (0-1.5) = Strong trends continue
- **Short**: Coins with high DW (2.5-4) = Choppy, avoid
- **Rationale**: Momentum persists in crypto

#### Variant C: Sweet Spot
- **Long**: Moderate DW (1.5-2.0) = Stable, predictable
- **Short**: Extreme DW (0-1.0 or 3.0-4.0) = Unstable patterns
- **Rationale**: Avoid extremes, favor stability

### 2.4 Durbin-Watson Calculation

#### Implementation

```python
import numpy as np
import pandas as pd

def calculate_durbin_watson(returns, window=30):
    """
    Calculate rolling Durbin-Watson statistic
    
    DW = sum((r[t] - r[t-1])^2) / sum(r[t]^2)
    
    Parameters:
    - returns: Series of daily returns
    - window: Rolling window (default: 30 days)
    
    Returns:
    - Series of DW statistics
    """
    def dw_stat(x):
        if len(x) < 2:
            return np.nan
        
        # Remove NaN
        x_clean = x.dropna()
        if len(x_clean) < window * 0.7:  # Require 70% data
            return np.nan
        
        # Calculate DW
        numerator = np.sum(np.diff(x_clean)**2)
        denominator = np.sum(x_clean**2)
        
        if denominator == 0:
            return np.nan
            
        return numerator / denominator
    
    # Rolling calculation
    dw = returns.rolling(window).apply(dw_stat, raw=False)
    
    return dw
```

#### Alternative: Using Residuals from Market Model

```python
def calculate_durbin_watson_residuals(coin_returns, market_returns, window=30):
    """
    Calculate DW on residuals from market model
    
    Model: r_coin = alpha + beta * r_market + epsilon
    DW calculated on epsilon (idiosyncratic returns)
    
    This isolates coin-specific autocorrelation patterns
    """
    def dw_from_regression(coin_ret, mkt_ret):
        # Remove NaN
        mask = ~(np.isnan(coin_ret) | np.isnan(mkt_ret))
        if mask.sum() < window * 0.7:
            return np.nan
        
        coin_clean = coin_ret[mask]
        mkt_clean = mkt_ret[mask]
        
        # Run regression: coin = alpha + beta * market
        beta = np.cov(coin_clean, mkt_clean)[0,1] / np.var(mkt_clean)
        alpha = np.mean(coin_clean) - beta * np.mean(mkt_clean)
        
        # Calculate residuals
        residuals = coin_clean - (alpha + beta * mkt_clean)
        
        # Calculate DW on residuals
        numerator = np.sum(np.diff(residuals)**2)
        denominator = np.sum(residuals**2)
        
        if denominator == 0:
            return np.nan
            
        return numerator / denominator
    
    # Combine series
    df = pd.DataFrame({'coin': coin_returns, 'market': market_returns})
    
    # Rolling calculation
    dw = df.rolling(window).apply(
        lambda x: dw_from_regression(x['coin'].values, x['market'].values),
        raw=False
    )
    
    return dw['coin']
```

---

## 3. Signal Generation

### 3.1 Daily Signal Process

**Step 1: Calculate Returns**
```python
# Daily log returns
returns = np.log(close / close.shift(1))
```

**Step 2: Calculate Durbin-Watson Statistic**
```python
# 30-day rolling DW for each coin
dw_30d = calculate_durbin_watson(returns, window=30)
```

**Step 3: Filter Universe**
```python
valid_coins = coins[
    (coins['volume_30d_avg'] > MIN_VOLUME) &
    (coins['market_cap'] > MIN_MARKET_CAP) &
    (coins['dw_30d'].notna()) &
    (coins['data_quality'] > 0.7)
]
```

**Step 4: Rank by Durbin-Watson**
```python
# Rank from low DW to high DW
# Rank 1 = lowest DW (strongest momentum)
# Rank N = highest DW (strongest mean reversion)
dw_rank = valid_coins['dw_30d'].rank(ascending=True)
```

**Step 5: Generate Signals (Contrarian Strategy)**
```python
# Variant A: Contrarian (Primary)
# Long high DW (mean reverting), Short low DW (momentum exhaustion)
if dw_rank >= 80th_percentile:  # High DW (mean reversion)
    signal = LONG
elif dw_rank <= 20th_percentile:  # Low DW (momentum)
    signal = SHORT
else:
    signal = NEUTRAL
```

### 3.2 Entry Rules

**Rebalancing Schedule:**
- **Frequency**: Every 7 days (weekly)
- **Day**: Monday (configurable)
- **Execution**: Next-day execution (avoid lookahead bias)

**Position Selection:**
- **Long Bucket**: Top quintile by DW (mean reverting coins)
- **Short Bucket**: Bottom quintile by DW (momentum coins)
- **Max Positions**: 10-20 per side (configurable)

**Filters:**
- **Minimum Volume**: 30-day avg > $5M
- **Minimum Market Cap**: > $50M
- **Data Quality**: 70% valid data in DW window
- **Exclude Stablecoins**: Remove USDT, USDC, DAI, etc.
- **DW Range Filter**: Exclude extreme DW > 3.5 or < 0.5 (data quality issues)

### 3.3 Exit Rules

**Time-Based Exit:**
- Hold until next rebalance (7 days)
- No intra-period adjustments

**Forced Exit:**
- Coin drops below volume threshold
- Data quality deteriorates

**No Stop Loss:**
- Hold through drawdowns
- Strategy assumes pattern persistence

---

## 4. Portfolio Construction

### 4.1 Weighting Methods

#### Method 1: Equal Weight (Baseline)
```python
weight_per_position = allocation / num_positions
```

**Pros:** Simple, transparent  
**Cons:** Doesn't account for volatility

#### Method 2: Risk Parity
```python
volatility = returns.rolling(30).std() * np.sqrt(365)
inverse_vol = 1 / volatility
weights = (inverse_vol / inverse_vol.sum()) * allocation
```

**Pros:** Equalizes risk contribution  
**Cons:** More complex

#### Method 3: DW-Weighted
```python
# Weight by distance from DW=2 (neutral)
dw_distance = np.abs(dw - 2.0)
weights = (dw_distance / dw_distance.sum()) * allocation
```

**Pros:** Emphasizes extreme patterns  
**Cons:** Can be unstable

### 4.2 Portfolio Allocation

**Default:**
- **Long**: 50% of capital (high DW coins)
- **Short**: 50% of capital (low DW coins)
- **Market Neutral**: Yes

**Alternative:**
- **Long-Only**: 100% long high DW
- **Short-Only**: 100% short low DW
- **Asymmetric**: 70% long, 30% short

---

## 5. Backtest Implementation

### 5.1 File Structure

**Main Script:** `backtests/scripts/backtest_durbin_watson_factor.py`

**Output Directory:** `backtests/results/`

### 5.2 Command-Line Interface

```bash
python3 backtests/scripts/backtest_durbin_watson_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy contrarian \
  --dw-window 30 \
  --rebalance-days 7 \
  --weighting-method equal_weight \
  --start-date 2020-01-01 \
  --end-date 2025-10-27
```

### 5.3 Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--price-data` | (required) | Path to OHLCV CSV |
| `--strategy` | `contrarian` | Strategy: `contrarian`, `momentum_continuation`, `sweet_spot` |
| `--dw-window` | 30 | DW calculation window (days) |
| `--dw-method` | `raw_returns` | Method: `raw_returns` or `residuals` |
| `--rebalance-days` | 7 | Rebalance frequency |
| `--num-quintiles` | 5 | Number of DW buckets |
| `--long-percentile` | 80 | Long threshold (top 20%) |
| `--short-percentile` | 20 | Short threshold (bottom 20%) |
| `--weighting-method` | `equal_weight` | Weighting: `equal_weight`, `risk_parity`, `dw_weighted` |
| `--min-volume` | 5000000 | Minimum volume ($) |
| `--min-market-cap` | 50000000 | Minimum market cap ($) |
| `--initial-capital` | 10000 | Starting capital |
| `--long-allocation` | 0.5 | Long allocation (50%) |
| `--short-allocation` | 0.5 | Short allocation (50%) |

### 5.4 Output Files

#### 1. Portfolio Values
**File:** `backtest_durbin_watson_portfolio_values.csv`

```csv
date,portfolio_value,long_exposure,short_exposure,net_exposure,num_longs,num_shorts,avg_long_dw,avg_short_dw
2020-01-01,10000.00,5000.00,-5000.00,0.00,10,10,2.85,0.95
```

#### 2. Trade Log
**File:** `backtest_durbin_watson_trades.csv`

```csv
date,symbol,signal,dw_30d,dw_rank,percentile,weight,returns_30d,autocorr_30d
2020-01-08,BTC,LONG,2.92,45,92.3,0.10,0.025,0.042
```

#### 3. Performance Metrics
**File:** `backtest_durbin_watson_metrics.csv`

```csv
metric,value
total_return,0.45
annualized_return,0.18
sharpe_ratio,0.92
max_drawdown,-0.28
```

#### 4. DW Distribution
**File:** `backtest_durbin_watson_dw_distribution.csv`

```csv
date,avg_dw,median_dw,dw_10pct,dw_90pct,pct_momentum,pct_neutral,pct_mean_reverting
2020-01-01,2.05,2.02,1.25,2.85,18.5,60.2,21.3
```

---

## 6. Strategy Variants

### 6.1 Contrarian (Primary Strategy)
**Name:** `contrarian`

**Logic:**
- Long: High DW (2.5-4) = Mean reverting
- Short: Low DW (0-1.5) = Momentum exhaustion

**Hypothesis:** Mean reversion pays off, momentum exhausts

**Expected:**
- Market neutral
- Positive Sharpe if contrarian edge exists

### 6.2 Momentum Continuation
**Name:** `momentum_continuation`

**Logic:**
- Long: Low DW (0-1.5) = Momentum continues
- Short: High DW (2.5-4) = Choppy, weak

**Hypothesis:** Trends persist in crypto

**Expected:**
- Positive correlation to market
- Higher volatility

### 6.3 Sweet Spot
**Name:** `sweet_spot`

**Logic:**
- Long: Moderate DW (1.5-2.0) = Stable
- Short: Extreme DW (< 1.0 or > 3.0) = Unstable

**Hypothesis:** Avoid extremes, favor predictability

**Expected:**
- Lower turnover
- Stable returns

### 6.4 Long High DW Only
**Name:** `long_high_dw`

**Logic:**
- Long: High DW (mean reverting)
- Short: None (50% cash)

**Hypothesis:** Mean reversion alpha

**Expected:**
- Defensive positioning
- Lower volatility

---

## 7. Performance Metrics

### 7.1 Return Metrics
- Total Return
- Annualized Return (CAGR)
- Monthly/Quarterly Returns
- Rolling Returns (90-day)

### 7.2 Risk Metrics
- Annualized Volatility
- Sharpe Ratio
- Sortino Ratio
- Maximum Drawdown
- Calmar Ratio
- VaR / CVaR (95%)

### 7.3 DW-Specific Metrics
- **Avg Long DW**: Average DW of long portfolio
- **Avg Short DW**: Average DW of short portfolio
- **DW Spread**: Long DW - Short DW
- **DW Stability**: Consistency of DW rankings
- **Autocorrelation Realized**: Actual autocorr of positions

### 7.4 Trading Metrics
- Win Rate
- Average Turnover
- Number of Rebalances
- Avg Positions (long/short)
- Hit Ratio

### 7.5 Factor Analysis
- **Long Portfolio Return**: Isolated long performance
- **Short Portfolio Return**: Isolated short performance
- **Long-Short Spread**: Long - Short
- **Correlation to BTC**: Market correlation
- **Beta to Market**: Systematic risk

---

## 8. No-Lookahead Bias Prevention

**Critical Rule:** Signals on day T use returns from day T+1

### Implementation

```python
# Day T: Calculate DW using data up to day T
dw_t = calculate_durbin_watson(returns.loc[:t], window=30)

# Day T: Rank and generate signals
signals_t = generate_signals(dw_t)

# Day T+1: Apply returns from next day
returns_t1 = price_data.loc[t+1, 'return']
pnl_t1 = signals_t * returns_t1.shift(-1)  # Proper alignment
```

---

## 9. Data Requirements

### 9.1 Input Data

**Source:** `data/raw/combined_coinbase_coinmarketcap_daily.csv`

**Fields:**
- `date`, `symbol`, `open`, `high`, `low`, `close`, `volume`, `market_cap`

**Minimum History:**
- 60 days per coin (30 for DW + 30 for backtest)

### 9.2 Filters

**Volume:** > $5M (30-day avg)  
**Market Cap:** > $50M  
**Data Quality:** 70% completeness in DW window  
**Outliers:** Remove returns > ±50%

---

## 10. Expected Insights

### 10.1 Key Questions

**1. Do autocorrelation patterns predict returns?**
- Do high DW coins outperform?
- Do low DW coins exhaust?

**2. Which strategy works best?**
- Contrarian vs. Momentum
- Market dependent?

**3. Is DW stable over time?**
- How much does DW fluctuate?
- Rank persistence?

**4. How does DW correlate with other factors?**
- DW vs. volatility?
- DW vs. momentum?
- DW vs. size?

### 10.2 Success Criteria

**Minimum:**
- Sharpe Ratio > 0.5
- Max Drawdown < 35%
- Win Rate > 48%
- Correlation to BTC < 0.5

**Stretch:**
- Sharpe Ratio > 1.0
- Max Drawdown < 25%
- Positive in bear markets

---

## 11. Risk Considerations

### 11.1 Strategy Risks

**Pattern Instability:**
- DW can change rapidly
- Autocorrelation not constant

**Market Regime:**
- May only work in specific conditions
- Bull vs. bear sensitivity

**Liquidity:**
- Extreme DW coins may be illiquid

**Short Squeeze:**
- Shorting momentum can be risky

### 11.2 Implementation Risks

**Transaction Costs:**
- Weekly rebalancing = moderate turnover
- Fees can erode returns

**Execution:**
- Slippage on rebalances
- Market impact

**Data Quality:**
- DW sensitive to outliers
- Missing data affects calculation

---

## 12. Implementation Roadmap

### Phase 1: Core Implementation (Week 1)
- [ ] Create `backtests/scripts/backtest_durbin_watson_factor.py`
- [ ] Implement DW calculation function (raw returns)
- [ ] Implement quintile ranking
- [ ] Add equal-weight portfolio construction
- [ ] Validate no-lookahead bias

### Phase 2: Testing & Validation (Week 1)
- [ ] Run baseline: Contrarian strategy
- [ ] Validate DW calculations (manual checks)
- [ ] Check data quality issues
- [ ] Verify metrics calculations
- [ ] Test different time periods

### Phase 3: Strategy Variants (Week 2)
- [ ] Implement all strategy variants
- [ ] Test momentum_continuation
- [ ] Test sweet_spot
- [ ] Add risk parity weighting
- [ ] Test different DW windows (20d, 30d, 60d)

### Phase 4: Analysis & Documentation (Week 2)
- [ ] Compare all variants
- [ ] Analyze DW distribution over time
- [ ] Calculate correlation to BTC and other factors
- [ ] Generate visualizations
- [ ] Document findings

---

## 13. Integration with Existing System

### 13.1 Code Reuse

**Templates:**
- `backtests/scripts/backtest_beta_factor.py` - Structure
- `backtests/scripts/backtest_skew_factor.py` - Quintile logic
- `signals/calc_vola.py` - Rolling calculations

**Data:**
- Use: `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- Output: `backtests/results/`

### 13.2 Factor Comparison

Run alongside:
- Beta factor
- Volatility factor
- Skew factor
- Kurtosis factor

Calculate correlation matrix and diversification benefits.

---

## 14. Academic References

### Statistical Background
- Durbin, J., & Watson, G. S. (1950). "Testing for Serial Correlation in Least Squares Regression". *Biometrika*.
- Breusch, T. S. (1978). "Testing for Autocorrelation in Dynamic Linear Models". *Australian Economic Papers*.

### Autocorrelation in Finance
- Lo, A. W., & MacKinlay, A. C. (1988). "Stock Market Prices Do Not Follow Random Walks: Evidence from a Simple Specification Test". *Review of Financial Studies*.
- Poterba, J. M., & Summers, L. H. (1988). "Mean Reversion in Stock Prices". *Journal of Financial Economics*.

### Crypto Markets
- Liu, Y., Tsyvinski, A., & Wu, X. (2022). "Common Risk Factors in Cryptocurrency". *Journal of Finance*.

---

## 15. Example Usage

### Basic Backtest
```bash
# Run contrarian strategy (baseline)
python3 backtests/scripts/backtest_durbin_watson_factor.py \
  --strategy contrarian \
  --dw-window 30 \
  --rebalance-days 7
```

### Test Momentum Continuation
```bash
python3 backtests/scripts/backtest_durbin_watson_factor.py \
  --strategy momentum_continuation \
  --dw-window 30 \
  --rebalance-days 7
```

### Parameter Sensitivity
```bash
# Test different DW windows
for window in 20 30 60 90; do
  python3 backtests/scripts/backtest_durbin_watson_factor.py \
    --strategy contrarian \
    --dw-window $window \
    --output-prefix durbin_watson_window_${window}
done
```

### Advanced
```bash
python3 backtests/scripts/backtest_durbin_watson_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy contrarian \
  --dw-window 30 \
  --dw-method raw_returns \
  --rebalance-days 7 \
  --weighting-method risk_parity \
  --long-allocation 0.5 \
  --short-allocation 0.5 \
  --min-volume 10000000 \
  --min-market-cap 100000000 \
  --start-date 2020-01-01 \
  --end-date 2025-10-27
```

---

## 16. Visualization Plan

### Charts to Generate
1. **Equity Curve**: Cumulative returns over time
2. **Drawdown**: Underwater plot
3. **DW Distribution**: Histogram of DW values by date
4. **Long vs Short**: Separated performance
5. **DW Heatmap**: DW values across coins over time
6. **Autocorrelation Decay**: Average autocorr by lag
7. **Turnover**: Daily portfolio turnover

---

## 17. Next Steps

1. **Implement Core Script**: Start with contrarian strategy
2. **Validate DW Calculation**: Test on known assets
3. **Run Initial Backtest**: Generate first results
4. **Analyze DW Distribution**: Understand cross-section
5. **Test Hypothesis**: Does autocorrelation predict returns?
6. **Compare Strategies**: Contrarian vs momentum
7. **Multi-Factor Integration**: Combine with other factors

---

**Document Owner:** Research Team  
**Created:** 2025-10-27  
**Status:** Specification Complete - Ready for Implementation  
**Next Step:** Implement Phase 1 (Core backtest script)

---

**Disclaimer:** This backtest is for research purposes only. Past performance does not guarantee future results. Cryptocurrency trading involves substantial risk of loss. The Durbin-Watson statistic is traditionally used for regression diagnostics, and its application to trading is experimental.
