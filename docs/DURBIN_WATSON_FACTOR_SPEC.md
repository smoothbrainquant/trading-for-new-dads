# Durbin-Watson Factor Trading Strategy Specification

**Version:** 1.0  
**Date:** 2025-10-30  
**Status:** Specification - Ready for Implementation

---

## 1. Executive Summary

This specification outlines a quantitative trading strategy based on the **Durbin-Watson (DW) statistic** for cryptocurrencies, enhanced with **directional regime filtering** using 5-day percent change. The core hypothesis tests whether coins exhibiting different levels of autocorrelation in returns show predictable performance patterns, and whether this effect varies by market regime.

### Key Objectives
1. Calculate rolling Durbin-Watson statistics for all cryptocurrencies
2. Rank coins by DW values (autocorrelation strength and direction)
3. Incorporate directional regime filtering using 5-day BTC percent change
4. Construct long/short portfolios based on DW rankings and regime
5. Test whether momentum-exhibiting coins (low DW) or mean-reverting coins (high DW) outperform
6. Compare performance across different market regimes

### Strategy Overview
- **Factor**: Durbin-Watson statistic (measures autocorrelation in returns)
- **Directional Filter**: 5-day BTC percent change (regime classification)
- **Universe**: All liquid cryptocurrencies with sufficient trading history
- **Rebalancing**: Weekly (configurable)
- **Market Neutrality**: Dollar-neutral long/short construction
- **Risk Management**: Equal weight or risk parity weighting

---

## 2. Strategy Description

### 2.1 Core Concept

The **Durbin-Watson statistic** measures autocorrelation in time series data. Originally designed to detect autocorrelation in regression residuals, it can be applied directly to return series to identify momentum or mean-reverting behavior.

**Durbin-Watson Formula:**

\[ DW = \frac{\sum_{t=2}^{T} (r_t - r_{t-1})^2}{\sum_{t=1}^{T} r_t^2} \]

Where:
- \( r_t \) = Return at time t
- \( T \) = Number of observations in window
- **DW statistic** ranges from 0 to 4

**Interpretation:**
- **DW ≈ 2.0**: No autocorrelation (random walk)
- **DW < 2.0**: Positive autocorrelation → **Momentum** (trending behavior)
  - DW = 1.0: Strong positive autocorrelation
  - DW = 0.0: Perfect positive autocorrelation
- **DW > 2.0**: Negative autocorrelation → **Mean Reversion** (oscillating behavior)
  - DW = 3.0: Strong negative autocorrelation
  - DW = 4.0: Perfect negative autocorrelation

**Relationship to Autocorrelation:**
\[ DW \approx 2(1 - \rho) \]

Where \( \rho \) is the first-order autocorrelation coefficient:
- \( \rho = +1 \) → DW ≈ 0 (perfect momentum)
- \( \rho = 0 \) → DW ≈ 2 (no autocorrelation)
- \( \rho = -1 \) → DW ≈ 4 (perfect mean reversion)

### 2.2 Strategy Hypotheses

#### Hypothesis A: Momentum Premium (Low DW)
- **Long**: Coins with low DW (DW < 2, positive autocorrelation, momentum)
- **Short**: Coins with high DW (DW > 2, negative autocorrelation, mean reversion)
- **Rationale**: Momentum persists; trending coins continue trending
- **Expected**: Momentum coins outperform mean-reverting coins

**Why this might work:**
1. **Trend Persistence**: Crypto exhibits strong momentum effects
2. **Information Diffusion**: News takes time to spread, creating autocorrelation
3. **Herding Behavior**: Retail investors chase trends
4. **Network Effects**: Growing coins attract more users → sustained trends

#### Hypothesis B: Mean Reversion Premium (High DW)
- **Long**: Coins with high DW (DW > 2, negative autocorrelation, mean reversion)
- **Short**: Coins with low DW (DW < 2, positive autocorrelation, momentum)
- **Rationale**: Mean reversion captures overshoots and corrections
- **Expected**: Mean-reverting coins offer more stable risk-adjusted returns

**Why this might work:**
1. **Volatility Overshoots**: Crypto has extreme price swings that correct
2. **Arbitrage**: Cross-exchange price differences create mean reversion
3. **Liquidity Provision**: Market makers profit from oscillations
4. **Risk-Adjusted Returns**: Lower volatility may lead to better Sharpe ratios

### 2.3 Directional Regime Integration

**Key Innovation: Combine DW factor with 5-day BTC percent change**

Insight from ADF Factor analysis: Strategy performance varies dramatically by market regime.

**Regime Classification:**
```python
btc_5d_pct_change = (btc_close_t / btc_close_t-5 - 1) * 100

if btc_5d_pct_change > 10:
    regime = "Strong Up"
elif btc_5d_pct_change > 0:
    regime = "Moderate Up"
elif btc_5d_pct_change > -10:
    regime = "Down"
else:
    regime = "Strong Down"
```

**Expected Regime Behavior (Based on ADF Insights):**

| Regime | % Time | Expected Winner | Rationale |
|--------|--------|----------------|-----------|
| **Strong Up (>10%)** | ~7% | Momentum (Low DW) | Trends accelerate in strong moves |
| **Moderate Up (0-10%)** | ~45% | Mean Reversion (High DW) | Choppy markets favor oscillations |
| **Down (0 to -10%)** | ~42% | Momentum (Low DW) | Clear downtrends persist |
| **Strong Down (<-10%)** | ~5% | Mean Reversion (High DW) | Crashes bounce back quickly |

### 2.4 DW Calculation

#### Method: Rolling Durbin-Watson on Returns

```python
import numpy as np
import pandas as pd

def calculate_rolling_dw(returns, window=60):
    """
    Calculate rolling Durbin-Watson statistic
    
    Parameters:
    - returns: Series of daily log returns
    - window: Rolling window in days (default: 60 days)
    
    Returns:
    - Series of rolling DW statistics
    - DW ~ 2: No autocorrelation (random walk)
    - DW < 2: Positive autocorrelation (momentum)
    - DW > 2: Negative autocorrelation (mean reversion)
    """
    def compute_dw(r):
        # Remove NaN values
        r_clean = r.dropna()
        
        if len(r_clean) < window * 0.7:  # Require 70% data availability
            return np.nan
        
        # Calculate numerator: sum of squared differences
        numerator = np.sum(np.diff(r_clean) ** 2)
        
        # Calculate denominator: sum of squared returns
        denominator = np.sum(r_clean ** 2)
        
        if denominator == 0:
            return np.nan
        
        dw = numerator / denominator
        return dw
    
    # Calculate rolling DW
    dw_stats = returns.rolling(window).apply(compute_dw, raw=False)
    
    return dw_stats
```

#### Alternative: DW from Autocorrelation

```python
def calculate_dw_from_acf(returns, window=60):
    """
    Calculate DW using first-order autocorrelation
    DW ≈ 2(1 - ρ₁)
    """
    def compute_acf_dw(r):
        r_clean = r.dropna()
        if len(r_clean) < window * 0.7:
            return np.nan
        
        # Calculate first-order autocorrelation
        rho_1 = r_clean.autocorr(lag=1)
        
        if pd.isna(rho_1):
            return np.nan
        
        # DW ≈ 2(1 - ρ)
        dw = 2 * (1 - rho_1)
        return dw
    
    dw_stats = returns.rolling(window).apply(compute_acf_dw, raw=False)
    return dw_stats
```

### 2.5 Calculation Parameters

**Default Parameters:**
- **Lookback Window**: 60 days (~2 months)
  - Long enough for stable autocorrelation estimate
  - Short enough to capture regime changes
- **Minimum Data**: 42 days (70% of 60 days)
- **Return Frequency**: Daily log returns
- **DW Calculation**: Direct formula (sum of squared differences)

**Parameter Variations to Test:**
- **30-day DW**: More reactive, captures short-term autocorrelation
- **60-day DW**: Baseline, balanced
- **90-day DW**: More stable, medium-term patterns
- **120-day DW**: Very stable, long-term autocorrelation

**Directional Filter Parameters:**
- **5-day BTC % Change**: Baseline for regime classification
- **Alternative**: 7-day, 10-day, or 14-day % change
- **Threshold**: ±10% for strong moves (configurable)

---

## 3. Signal Generation

### 3.1 Daily Signal Process

**Step 1: Calculate Returns**
```python
# Log returns for all coins
returns = np.log(close / close.shift(1))
```

**Step 2: Calculate DW Statistics**
```python
# For each coin, calculate rolling DW
dw_stats = calculate_rolling_dw(returns, window=60)
```

**Step 3: Calculate BTC Directional Regime**
```python
# 5-day BTC percent change
btc_5d_pct = (btc_close / btc_close.shift(5) - 1) * 100

# Classify regime
if btc_5d_pct > 10:
    regime = "Strong Up"
elif btc_5d_pct > 0:
    regime = "Moderate Up"
elif btc_5d_pct > -10:
    regime = "Down"
else:
    regime = "Strong Down"
```

**Step 4: Filter Universe**
```python
# Apply liquidity and data quality filters
valid_coins = coins[
    (coins['volume_30d_avg'] > MIN_VOLUME) &
    (coins['market_cap'] > MIN_MARKET_CAP) &
    (coins['dw_stat'].notna()) &
    (coins['data_quality'] > 0.7)
]
```

**Step 5: Rank by DW**
```python
# Rank from low DW to high DW
# Rank 1 = lowest DW (strongest momentum, most positive autocorrelation)
# Rank N = highest DW (strongest mean reversion, most negative autocorrelation)
dw_rank = valid_coins['dw_stat'].rank(ascending=True)
```

**Step 6: Generate Regime-Conditional Signals**
```python
# Regime-Aware Strategy: Switch based on market regime

if regime in ["Strong Up", "Down"]:
    # Favor MOMENTUM in strong directional moves
    # Long bottom quintile (low DW = momentum), Short top quintile (high DW = mean reversion)
    if dw_rank <= 20th_percentile:
        signal = LONG  # Low DW = momentum
    elif dw_rank >= 80th_percentile:
        signal = SHORT  # High DW = mean reversion

elif regime in ["Moderate Up", "Strong Down"]:
    # Favor MEAN REVERSION in moderate/choppy moves
    # Long top quintile (high DW = mean reversion), Short bottom quintile (low DW = momentum)
    if dw_rank >= 80th_percentile:
        signal = LONG  # High DW = mean reversion
    elif dw_rank <= 20th_percentile:
        signal = SHORT  # Low DW = momentum
```

### 3.2 Entry Rules

**Rebalancing Schedule:**
- **Frequency**: Every 7 days (weekly, default)
- **Day**: Monday close (configurable)
- **Execution**: Assume next-day execution (avoid lookahead bias)

**Position Selection:**
- **Long Bucket**: Bottom or top quintile by DW (regime-dependent)
- **Short Bucket**: Top or bottom quintile by DW (regime-dependent)
- **Max Positions**: 10-20 longs + 10-20 shorts (configurable)
- **Min DW Window**: At least 42 days (70% of 60) of valid data

**Filters:**
- **Minimum Volume**: 30-day avg volume > $5M (configurable)
- **Minimum Market Cap**: > $50M (configurable)
- **Data Quality**: At least 70% valid data in DW window
- **Exclude Stablecoins**: Remove USDT, USDC, DAI, etc.
- **Exclude Extreme DW**: Remove DW < 0.5 or DW > 3.5 (data quality issues)

### 3.3 Exit Rules

**Time-Based Exit:**
- Hold positions until next rebalance date
- No intra-period adjustments (except forced exits)

**Forced Exit Conditions:**
- Coin drops below minimum volume threshold
- Coin delisted from exchange
- Data quality deteriorates (missing data)
- Regime change triggers strategy flip (optional)

**No Stop Loss:**
- Hold through drawdowns until rebalance
- Strategy assumes autocorrelation patterns persist within regime

---

## 4. Portfolio Construction

### 4.1 Weighting Methods

#### Method 1: Equal Weight (Baseline)
```python
# Simple equal allocation within each bucket
weight_per_position = allocation / num_positions

# Example: 50% allocation, 10 positions
# Each position: 5% weight
```

**Pros:**
- Simple, transparent
- Easy to implement
- No estimation error

**Cons:**
- Doesn't account for volatility differences
- High-vol coins contribute more risk

#### Method 2: Risk Parity
```python
# Weight inversely proportional to volatility
# Each position contributes equal risk

volatility = coin_returns.rolling(30).std() * np.sqrt(365)
inverse_vol = 1 / volatility
weights = (inverse_vol / inverse_vol.sum()) * allocation
```

**Pros:**
- Equalizes risk contribution
- More stable portfolio
- Better risk-adjusted returns

**Cons:**
- Requires volatility estimation
- Can overweight low-vol coins
- More complex

### 4.2 Portfolio Allocation

**Default Configuration:**
- **Long Allocation**: 50% of capital
- **Short Allocation**: 50% of capital
- **Cash**: 0% (fully invested, market neutral)
- **Leverage**: 1.0x (no leverage by default)

**Alternative Configurations:**
- **Long-Only**: 100% long, 0% short
- **Long-Biased**: 75% long, 25% short
- **Levered Neutral**: 100% long, 100% short (2x gross leverage)

### 4.3 Rebalancing Logic

**Full Rebalancing (Default):**
```python
# On rebalance date:
1. Calculate new DW values
2. Determine current regime (5d BTC % change)
3. Rank all coins by DW
4. Select new long/short buckets based on regime
5. Exit all old positions
6. Enter new positions with target weights
```

**Regime-Change Rebalancing (Advanced):**
```python
# Rebalance when regime changes
if previous_regime != current_regime:
    # Flip positions if regime switches between momentum/mean-reversion favorable
    rebalance_portfolio()
```

---

## 5. Backtest Implementation

### 5.1 File Structure

**Main Script:** `backtests/scripts/backtest_durbin_watson_factor.py`

**Purpose:** Backtest engine for DW-based strategies with directional filtering

**Output Directory:** `backtests/results/`

### 5.2 Command-Line Interface

```bash
python3 backtests/scripts/backtest_durbin_watson_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy regime_adaptive \
  --dw-window 60 \
  --directional-window 5 \
  --directional-threshold 10 \
  --rebalance-days 7 \
  --weighting-method equal_weight \
  --long-allocation 0.5 \
  --short-allocation 0.5 \
  --start-date 2021-01-01 \
  --end-date 2025-10-30 \
  --output-prefix backtest_dw_factor
```

### 5.3 Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--price-data` | (required) | Path to OHLCV CSV file |
| `--strategy` | `regime_adaptive` | Strategy variant (see section 6) |
| `--dw-window` | 60 | DW calculation window (days) |
| `--directional-window` | 5 | Days for directional % change (5, 7, 10, 14) |
| `--directional-threshold` | 10 | Threshold for strong moves (±10%) |
| `--volatility-window` | 30 | Volatility window for risk parity (days) |
| `--rebalance-days` | 7 | Rebalance frequency (days) |
| `--num-quintiles` | 5 | Number of DW buckets |
| `--long-percentile` | 20 | Percentile threshold for long (bottom 20%) |
| `--short-percentile` | 80 | Percentile threshold for short (top 20%) |
| `--weighting-method` | `equal_weight` | Weighting: `equal_weight`, `risk_parity` |
| `--min-volume` | 5000000 | Minimum 30d avg volume ($) |
| `--min-market-cap` | 50000000 | Minimum market cap ($) |
| `--initial-capital` | 10000 | Starting capital (USD) |
| `--leverage` | 1.0 | Leverage multiplier |
| `--long-allocation` | 0.5 | Long side allocation (50%) |
| `--short-allocation` | 0.5 | Short side allocation (50%) |
| `--start-date` | None | Backtest start (YYYY-MM-DD) |
| `--end-date` | None | Backtest end (YYYY-MM-DD) |
| `--output-prefix` | `backtest_dw_factor` | Output file prefix |

### 5.4 Output Files

#### 1. Portfolio Values
**File:** `backtest_dw_factor_portfolio_values.csv`

```csv
date,portfolio_value,cash,long_exposure,short_exposure,net_exposure,gross_exposure,num_longs,num_shorts,avg_dw_long,avg_dw_short,btc_5d_pct,regime
2021-01-01,10000.00,0.00,5000.00,-5000.00,0.00,10000.00,10,10,1.45,2.65,5.2,Moderate Up
2021-01-08,10150.25,0.00,5075.13,-5075.13,0.00,10150.25,10,10,1.52,2.58,6.8,Moderate Up
...
```

#### 2. Trade Log
**File:** `backtest_dw_factor_trades.csv`

```csv
date,symbol,signal,dw_stat,dw_rank,percentile,weight,position_size,market_cap,volume_30d_avg,volatility_30d,btc_5d_pct,regime
2021-01-08,BTC,LONG,1.35,3,6.1,0.11,550.00,180000000000,25000000000,0.45,5.2,Moderate Up
2021-01-08,ETH,LONG,1.42,5,10.2,0.10,500.00,25000000000,8000000000,0.62,5.2,Moderate Up
2021-01-08,DOGE,SHORT,2.85,48,98.0,0.08,-400.00,2000000000,500000000,1.85,5.2,Moderate Up
...
```

#### 3. Performance Metrics
**File:** `backtest_dw_factor_metrics.csv`

```csv
metric,value
initial_capital,10000.00
final_value,15245.75
total_return,0.5246
annualized_return,0.2156
annualized_volatility,0.1842
sharpe_ratio,1.17
sortino_ratio,1.65
max_drawdown,-0.1834
calmar_ratio,1.17
win_rate,0.5623
avg_long_positions,9.8
avg_short_positions,9.5
avg_dw_long,1.45
avg_dw_short,2.65
total_rebalances,78
trading_days,547
strong_up_days,38
moderate_up_days,250
down_days,230
strong_down_days,29
```

#### 4. DW Time Series
**File:** `backtest_dw_factor_dw_timeseries.csv`

```csv
date,symbol,dw_stat,dw_rank,percentile,autocorr_lag1,returns_60d_mean,returns_60d_std,btc_5d_pct,regime
2021-01-08,BTC,1.35,3,6.1,-0.325,0.0015,0.042,5.2,Moderate Up
2021-01-08,ETH,1.42,5,10.2,-0.290,0.0018,0.055,5.2,Moderate Up
...
```

#### 5. Regime Performance
**File:** `backtest_dw_factor_regime_performance.csv`

```csv
regime,num_days,pct_time,total_return,annualized_return,sharpe_ratio,max_drawdown,win_rate,avg_dw_long,avg_dw_short
Strong Up,38,6.9,0.32,1.13,4.17,-0.071,0.237,1.35,2.75
Moderate Up,250,45.6,0.15,0.36,1.36,-0.273,0.252,1.48,2.68
Down,230,42.3,0.28,0.57,2.17,-0.145,0.216,1.42,2.62
Strong Down,29,5.1,0.10,0.34,0.66,-0.181,0.195,1.52,2.70
```

#### 6. Strategy Info
**File:** `backtest_dw_factor_strategy_info.csv`

```csv
strategy,dw_window,directional_window,directional_threshold,rebalance_days,weighting_method,long_symbols,short_symbols,avg_dw_long,avg_dw_short
regime_adaptive,60,5,10,7,equal_weight,"BTC,ETH,USDC,...","DOGE,SHIB,APE,...",1.45,2.65
```

---

## 6. Strategy Variants

### 6.1 Regime-Adaptive (Primary Strategy)
**Name:** `regime_adaptive`

**Configuration:**
- **Strong Up / Down Regimes**: Long low DW (momentum), Short high DW (mean reversion)
- **Moderate Up / Strong Down Regimes**: Long high DW (mean reversion), Short low DW (momentum)
- Allocation: 50% long, 50% short
- Market Neutral: Yes

**Hypothesis:** Strategy selection should adapt to market regime

**Expected Outcome:**
- Best overall performance
- Captures momentum in trending markets
- Captures mean reversion in choppy markets
- Lower drawdowns across regimes

### 6.2 Momentum Premium (Static)
**Name:** `momentum_premium`

**Configuration:**
- Long: Bottom quintile (low DW, momentum/positive autocorrelation)
- Short: Top quintile (high DW, mean reversion/negative autocorrelation)
- Allocation: 50% long, 50% short
- Market Neutral: Yes
- No regime filtering

**Hypothesis:** Momentum persists in crypto; trending behavior outperforms

**Expected Outcome:**
- Strong performance in trending markets
- Weak performance in choppy markets
- Higher volatility
- Positive correlation to market

### 6.3 Mean Reversion Premium (Static)
**Name:** `mean_reversion_premium`

**Configuration:**
- Long: Top quintile (high DW, mean reversion/negative autocorrelation)
- Short: Bottom quintile (low DW, momentum/positive autocorrelation)
- Allocation: 50% long, 50% short
- Market Neutral: Yes
- No regime filtering

**Hypothesis:** Mean reversion dominates; oscillating behavior offers better risk-adjusted returns

**Expected Outcome:**
- Strong performance in range-bound markets
- Weak performance in strong trending markets
- Lower volatility
- Negative correlation to market

### 6.4 Long Momentum Only
**Name:** `long_momentum`

**Configuration:**
- Long: Bottom quintile (low DW, momentum)
- Short: None (50% cash)
- Allocation: 50% long, 0% short
- Market Neutral: No

**Hypothesis:** Pure momentum exposure in crypto

**Expected Outcome:**
- Strong bull market performance
- High volatility
- Positive market correlation

### 6.5 Long Mean Reversion Only
**Name:** `long_mean_reversion`

**Configuration:**
- Long: Top quintile (high DW, mean reversion)
- Short: None (50% cash)
- Allocation: 50% long, 0% short
- Market Neutral: No

**Hypothesis:** Defensive positioning via mean-reverting assets

**Expected Outcome:**
- Lower volatility
- Steady performance
- Outperforms in bear markets

---

## 7. Performance Metrics

### 7.1 Return Metrics
- **Total Return**: Cumulative return over backtest period
- **Annualized Return**: CAGR = (Final / Initial)^(365/days) - 1
- **Monthly Returns**: Time series of monthly performance
- **Rolling Returns**: 90-day rolling returns

### 7.2 Risk Metrics
- **Annualized Volatility**: Std(daily returns) × √365
- **Sharpe Ratio**: (Return - RFR) / Volatility (RFR = 0%)
- **Sortino Ratio**: (Return - RFR) / Downside Volatility
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Calmar Ratio**: Annualized Return / Max Drawdown
- **Value at Risk (VaR)**: 95th percentile daily loss
- **Conditional VaR (CVaR)**: Expected loss beyond VaR

### 7.3 DW-Specific Metrics
- **Average DW Long**: Mean DW of long positions
- **Average DW Short**: Mean DW of short positions
- **DW Spread**: Difference between long and short DW
- **Autocorrelation Long**: Mean first-order autocorrelation of longs
- **Autocorrelation Short**: Mean first-order autocorrelation of shorts
- **DW Stability**: Correlation of DW ranks across periods

### 7.4 Regime Metrics
- **Strong Up Performance**: Returns when BTC 5d % change > 10%
- **Moderate Up Performance**: Returns when BTC 5d % change 0-10%
- **Down Performance**: Returns when BTC 5d % change 0 to -10%
- **Strong Down Performance**: Returns when BTC 5d % change < -10%
- **Regime Win Rate**: % profitable days by regime
- **Regime Sharpe**: Sharpe ratio by regime

### 7.5 Trading Metrics
- **Win Rate**: % of profitable rebalancing periods
- **Average Turnover**: % of portfolio traded per rebalance
- **Number of Rebalances**: Total rebalancing events
- **Avg Long Positions**: Average number of long positions
- **Avg Short Positions**: Average number of short positions
- **Regime Switches**: Number of regime changes

---

## 8. No-Lookahead Bias Prevention

**Critical Rule:** Signals on day T use returns from day T+1

### 8.1 Implementation

```python
# Day T: Calculate DW using returns up to day T
returns_t = price_data.loc[:t, 'return']
dw_t = calculate_dw(returns_t, window=60)

# Day T: Calculate BTC 5-day % change using data up to day T
btc_5d_pct_t = (btc_close_t / btc_close_t-5 - 1) * 100
regime_t = classify_regime(btc_5d_pct_t)

# Day T: Rank coins and generate signals based on regime
signals_t = generate_signals(dw_t, regime_t)

# Day T+1: Apply signals using next day's returns
returns_t1 = price_data.loc[t+1, 'return']
pnl_t1 = signals_t * returns_t1  # Use .shift(-1) for proper alignment
```

### 8.2 Key Checks
- ✅ DW calculated using only past returns (no future data)
- ✅ Regime classified using data up to day T
- ✅ Signals generated at close of day T
- ✅ Positions executed at open/close of day T+1
- ✅ Returns from day T+1 used for P&L
- ✅ No future prices or regimes used in any calculation

---

## 9. Data Requirements

### 9.1 Input Data

**Source:** `data/raw/combined_coinbase_coinmarketcap_daily.csv`

**Required Fields:**
- `date`: Trading date (YYYY-MM-DD)
- `symbol`: Coin ticker (BTC, ETH, etc.)
- `close`: Closing price (levels, not returns)
- `volume`: Trading volume (USD)
- `market_cap`: Market capitalization (USD)

**Minimum History:**
- **Per Coin**: 90 days minimum
  - 60 days for DW calculation
  - 30 days for backtest stability
- **Universe**: At least 30 coins with valid data at any time

### 9.2 Data Quality Filters

**Volume Filter:**
- 30-day average volume > $5M (default)
- Ensures liquidity for execution

**Market Cap Filter:**
- Market cap > $50M (default)
- Excludes micro-caps with poor data quality

**Data Completeness:**
- At least 70% of data points in DW window
- Handles missing data gracefully

**Outlier Detection:**
- Remove days with returns > ±50% (likely data errors)
- Check for extreme DW values (< 0.5 or > 3.5)

---

## 10. Risk Considerations

### 10.1 Strategy Risks

**DW Instability:**
- DW can change rapidly during regime shifts
- Momentum coins can become mean-reverting (and vice versa)
- Solution: Regular rebalancing, regime-aware positioning

**Regime Misclassification:**
- Using past 5-day returns to classify regime introduces lag
- Regime may change during holding period
- Solution: Use leading indicators, faster rebalancing

**Regime Transition Risk:**
- Strategy performance suffers during regime transitions
- May be positioned for wrong regime when it changes
- Solution: Blend strategies, use probability-weighted allocation

**Autocorrelation Decay:**
- Autocorrelation patterns may not persist
- Short-term autocorrelation ≠ long-term predictability
- Solution: Test multiple DW windows, validate out-of-sample

### 10.2 Implementation Risks

**Computational Cost:**
- DW calculation for many coins can be slow
- Solution: Optimize code, vectorize calculations, cache results

**Parameter Sensitivity:**
- Results may be sensitive to DW window, regime threshold
- Solution: Robustness testing, multiple parameter sets

**Transaction Costs:**
- Frequent rebalancing = high fees
- Regime changes may trigger full rebalancing
- Solution: Longer rebalance periods, partial rebalancing

**Overfitting to Regimes:**
- Regime thresholds optimized on historical data
- May not generalize to future
- Solution: Use standard thresholds (±10%), out-of-sample testing

---

## 11. Expected Insights

### 11.1 Key Questions

**1. Does autocorrelation predict returns in crypto?**
- Do momentum coins (low DW) outperform mean-reverting coins (high DW)?
- Is the effect statistically significant?
- How does DW compare to other momentum/mean reversion measures?

**2. Is DW predictive power regime-dependent?**
- Does momentum work better in trending regimes?
- Does mean reversion work better in choppy regimes?
- What is the optimal regime classification threshold?

**3. Is DW stable over time?**
- How much does DW fluctuate?
- Are low-DW coins persistently low-DW?
- DW rank correlation across periods?

**4. How does DW correlate with other factors?**
- DW vs. ADF (both measure mean reversion/stationarity)?
- DW vs. beta factor?
- DW vs. volatility?
- DW vs. momentum factor?
- Independent alpha source?

**5. Does DW vary by coin type?**
- DeFi vs. L1 vs. Meme coins?
- Market cap buckets?
- Different autocorrelation characteristics?

### 11.2 Success Criteria

**Minimum Viable Results:**
- **Sharpe Ratio**: > 0.7
- **Maximum Drawdown**: < 30%
- **Win Rate**: > 50%
- **Market Correlation**: < 0.4 (for market neutral)
- **DW Spread**: Significant difference between long/short
- **Regime Improvement**: Regime-adaptive outperforms static strategies

**Stretch Goals:**
- **Sharpe Ratio**: > 1.2
- **Maximum Drawdown**: < 20%
- **Calmar Ratio**: > 0.6
- **Alpha vs BTC**: > 10% annualized
- **Positive in All Regimes**: Consistent performance
- **Regime Switching Gain**: +20pp over best static strategy

---

## 12. Implementation Roadmap

### Phase 1: Core Implementation (Week 1)
- [ ] Create `backtests/scripts/backtest_durbin_watson_factor.py`
- [ ] Implement rolling DW calculation function
- [ ] Implement directional regime classification (5d % change)
- [ ] Implement quintile ranking and selection
- [ ] Add equal-weight portfolio construction
- [ ] Validate no-lookahead bias (use `.shift(-1)`)
- [ ] Run baseline backtest: Regime-Adaptive strategy

### Phase 2: Testing & Validation (Week 1)
- [ ] Validate DW calculations (manual spot checks)
- [ ] Validate regime classification (match ADF analysis)
- [ ] Check for data quality issues
- [ ] Verify performance metrics calculations
- [ ] Test on different time periods (2021-2025)
- [ ] Analyze DW distribution across coins

### Phase 3: Strategy Variants (Week 2)
- [ ] Implement all 5 strategy variants
- [ ] Add risk parity weighting option
- [ ] Test different rebalancing frequencies (7d, 14d, 30d)
- [ ] Test different DW windows (30d, 60d, 90d, 120d)
- [ ] Test different directional windows (5d, 7d, 10d, 14d)
- [ ] Test different regime thresholds (±5%, ±10%, ±15%)
- [ ] Compare strategy performance

### Phase 4: Analysis & Documentation (Week 2)
- [ ] Run all strategy variants
- [ ] Analyze performance by regime (match ADF-style analysis)
- [ ] Compare static vs regime-adaptive strategies
- [ ] Calculate correlation to BTC
- [ ] Compare to other factor strategies (ADF, beta, volatility)
- [ ] Calculate factor correlation matrix
- [ ] Generate performance visualizations
- [ ] Document findings and recommendations

---

## 13. Integration with Existing System

### 13.1 Code Reuse

**Existing Utilities:**
- `backtests/scripts/backtest_adf_factor.py` - Template structure (very similar!)
- `backtests/scripts/backtest_beta_factor.py` - Quintile ranking logic
- `signals/calc_vola.py` - Volatility calculation (for risk parity)
- `signals/calc_weights.py` - Risk parity weight calculation

**Data Integration:**
- Use existing: `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- Same CSV format and naming conventions
- Store outputs in: `backtests/results/`

### 13.2 Comparison Framework

**Run all factors on same time period:**
```bash
# ADF factor (with directionality)
python3 backtest_adf_factor.py --strategy regime_aware --start-date 2021-01-01

# Beta factor
python3 backtest_beta_factor.py --strategy betting_against_beta --start-date 2021-01-01

# Volatility factor
python3 backtest_volatility_factor.py --strategy long_low_short_high --start-date 2021-01-01

# DW factor (new)
python3 backtest_durbin_watson_factor.py --strategy regime_adaptive --start-date 2021-01-01
```

**Calculate factor correlation matrix:**
- Correlation of daily returns across factors
- Identify diversification opportunities
- Build multi-factor portfolio

**Expected Correlations:**
- DW vs ADF: High correlation (both measure mean reversion/autocorrelation)
- DW vs Beta: Moderate correlation (both capture systematic patterns)
- DW vs Volatility: Low correlation (different risk dimensions)

---

## 14. Academic References

### 14.1 Time Series Analysis

**Durbin-Watson Test:**
- Durbin, J., & Watson, G. S. (1950). "Testing for Serial Correlation in Least Squares Regression I". *Biometrika*.
- Durbin, J., & Watson, G. S. (1951). "Testing for Serial Correlation in Least Squares Regression II". *Biometrika*.

**Autocorrelation in Finance:**
- Lo, A. W., & MacKinlay, A. C. (1988). "Stock Market Prices Do Not Follow Random Walks: Evidence from a Simple Specification Test". *Review of Financial Studies*.
- Jegadeesh, N., & Titman, S. (1993). "Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency". *Journal of Finance*.

### 14.2 Momentum and Mean Reversion

**Momentum:**
- Carhart, M. M. (1997). "On Persistence in Mutual Fund Performance". *Journal of Finance*.
- Asness, C. S., Moskowitz, T. J., & Pedersen, L. H. (2013). "Value and Momentum Everywhere". *Journal of Finance*.

**Mean Reversion:**
- Poterba, J. M., & Summers, L. H. (1988). "Mean Reversion in Stock Prices: Evidence and Implications". *Journal of Financial Economics*.
- Fama, E. F., & French, K. R. (1988). "Permanent and Temporary Components of Stock Prices". *Journal of Political Economy*.

### 14.3 Crypto-Specific

**Crypto Time Series Properties:**
- Urquhart, A. (2016). "The Inefficiency of Bitcoin". *Economics Letters*.
- Nadarajah, S., & Chu, J. (2017). "On the Inefficiency of Bitcoin". *Economics Letters*.

**Crypto Factors:**
- Liu, Y., Tsyvinski, A., & Wu, X. (2022). "Common Risk Factors in Cryptocurrency". *Journal of Finance*.

---

## 15. Example Usage

### Basic Backtest
```bash
# Run Regime-Adaptive strategy (baseline)
python3 backtests/scripts/backtest_durbin_watson_factor.py \
  --strategy regime_adaptive \
  --dw-window 60 \
  --directional-window 5 \
  --directional-threshold 10 \
  --rebalance-days 7
```

### Test Static Strategies
```bash
# Momentum Premium (static)
python3 backtests/scripts/backtest_durbin_watson_factor.py \
  --strategy momentum_premium \
  --dw-window 60 \
  --rebalance-days 7

# Mean Reversion Premium (static)
python3 backtests/scripts/backtest_durbin_watson_factor.py \
  --strategy mean_reversion_premium \
  --dw-window 60 \
  --rebalance-days 7
```

### Parameter Sensitivity
```bash
# Test different DW windows
for window in 30 60 90 120; do
  python3 backtests/scripts/backtest_durbin_watson_factor.py \
    --strategy regime_adaptive \
    --dw-window $window \
    --output-prefix backtest_dw_factor_window_${window}
done

# Test different directional windows
for dir_window in 5 7 10 14; do
  python3 backtests/scripts/backtest_durbin_watson_factor.py \
    --strategy regime_adaptive \
    --directional-window $dir_window \
    --output-prefix backtest_dw_factor_dirwindow_${dir_window}
done

# Test different regime thresholds
for threshold in 5 10 15; do
  python3 backtests/scripts/backtest_durbin_watson_factor.py \
    --strategy regime_adaptive \
    --directional-threshold $threshold \
    --output-prefix backtest_dw_factor_threshold_${threshold}
done
```

### Advanced Configuration
```bash
python3 backtests/scripts/backtest_durbin_watson_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy regime_adaptive \
  --dw-window 60 \
  --directional-window 5 \
  --directional-threshold 10 \
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
  --start-date 2021-01-01 \
  --end-date 2025-10-30 \
  --output-prefix backtest_dw_factor_custom
```

---

## 16. Next Steps

1. **Review Specification**: Validate approach and assumptions
2. **Implement Core Script**: Build `backtest_durbin_watson_factor.py` with DW calculation
3. **Run Initial Backtest**: Test regime-adaptive strategy
4. **Analyze DW Distribution**: Understand cross-section of autocorrelation
5. **Test Regime Hypothesis**: Does performance vary by directional regime?
6. **Compare Strategies**: Regime-adaptive vs. static momentum/mean reversion
7. **Parameter Optimization**: Find optimal DW window, directional window, threshold
8. **Multi-Factor Integration**: Combine with ADF, beta, volatility factors
9. **Compare to ADF**: Is DW superior to ADF for mean reversion detection?

---

**Document Owner:** Research Team  
**Last Updated:** 2025-10-30  
**Status:** Specification - Ready for Implementation  
**Next Step:** Implement Phase 1 (Core backtest script)

---

**Disclaimer:** This backtest is for research purposes only. Past performance does not guarantee future results. Cryptocurrency trading involves substantial risk of loss. The Durbin-Watson statistic is a measure of autocorrelation and may not guarantee predictive power in trading. Always conduct thorough research and risk management before deploying capital.
