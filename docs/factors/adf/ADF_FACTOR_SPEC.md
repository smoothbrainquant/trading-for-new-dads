# ADF Factor Trading Strategy Specification

**Version:** 1.0  
**Date:** 2025-10-27  
**Status:** Specification - Ready for Implementation

---

## 1. Executive Summary

This specification outlines a quantitative trading strategy based on the **Augmented Dickey-Fuller (ADF) test statistic** for cryptocurrencies. The core hypothesis tests whether coins with different degrees of mean reversion (stationarity) exhibit predictable return patterns that can be exploited through long/short portfolio construction.

### Key Objectives
1. Calculate rolling ADF test statistics for all cryptocurrencies
2. Rank coins by ADF values (stationarity/mean reversion strength)
3. Construct long/short portfolios based on ADF rankings
4. Test whether mean-reverting coins outperform trending coins
5. Compare performance to existing factor strategies

### Strategy Overview
- **Factor**: ADF test statistic (measures stationarity/mean reversion)
- **Universe**: All liquid cryptocurrencies with sufficient trading history
- **Rebalancing**: Weekly (configurable)
- **Market Neutrality**: Dollar-neutral long/short construction
- **Risk Management**: Equal weight or risk parity weighting

---

## 2. Strategy Description

### 2.1 Core Concept

The **Augmented Dickey-Fuller (ADF) test** is a statistical test that determines whether a time series is stationary (mean-reverting) or has a unit root (random walk/trending).

**ADF Test Equation:**
\[ \Delta y_t = \alpha + \beta t + \gamma y_{t-1} + \sum_{i=1}^{p} \delta_i \Delta y_{t-i} + \epsilon_t \]

Where:
- \( \Delta y_t \) = First difference of the time series (returns)
- \( y_{t-1} \) = Lagged level of the time series
- \( \gamma \) = Coefficient testing for unit root
- **ADF statistic** = t-statistic for \( \gamma \)

**Interpretation:**
- **More negative ADF** → More stationary → Stronger mean reversion
- **Less negative ADF** → Less stationary → More trending/random walk
- **ADF < critical value** → Reject unit root (stationary)
- **ADF > critical value** → Cannot reject unit root (non-stationary)

**Example ADF Values:**
- ADF = -4.5: Strongly mean-reverting (stationary)
- ADF = -2.0: Weakly mean-reverting
- ADF = -0.5: Non-stationary (random walk/trending)

### 2.2 Strategy Hypothesis

Two competing hypotheses for trading:

#### Hypothesis A: Mean Reversion Premium
- **Long**: Coins with low ADF (most mean-reverting/stationary)
- **Short**: Coins with high ADF (most trending/non-stationary)
- **Rationale**: Mean-reverting assets offer better risk-adjusted returns
- **Expected**: Mean-reverting coins are more predictable, less risky

**Why this might work:**
1. **Predictability**: Mean-reverting coins have predictable price behavior
2. **Risk Reduction**: Stationary assets have bounded volatility
3. **Trading Opportunity**: Clearer entry/exit signals for mean reversion
4. **Market Inefficiency**: Market may overpay for trending "momentum" coins

#### Hypothesis B: Trend Following Premium
- **Long**: Coins with high ADF (most trending/non-stationary)
- **Short**: Coins with low ADF (most mean-reverting/stationary)
- **Rationale**: Trending assets capture momentum and growth
- **Expected**: Trending coins benefit from sustained directional moves

**Why this might work:**
1. **Momentum**: Trending coins have sustained price moves
2. **Growth Premium**: Non-stationary = growth = higher returns
3. **Market Demand**: Investors prefer explosive growth over stability
4. **Behavioral**: Trending coins attract attention and capital

### 2.3 Crypto Market Application

**Why mean reversion might work in crypto:**
1. **High Volatility**: Crypto exhibits extreme overshoots and corrections
2. **Thin Markets**: Price dislocations common in smaller coins
3. **Sentiment Swings**: Rapid reversals after extreme moves
4. **Arbitrage**: Cross-exchange inefficiencies create mean reversion

**Why trend following might work:**
1. **Momentum Effects**: Strong trends persist in crypto (see momentum factor)
2. **Network Effects**: Growing coins attract more users → sustained growth
3. **Retail Behavior**: FOMO drives trends longer than in traditional markets
4. **Limited Shorting**: Hard to arbitrage = trends persist

### 2.4 ADF Calculation

#### Method: Rolling ADF Test

```python
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import adfuller

def calculate_rolling_adf(prices, window=60, regression='ct'):
    """
    Calculate rolling ADF test statistic
    
    Parameters:
    - prices: Series of price levels (not returns)
    - window: Rolling window in days (default: 60 days)
    - regression: Regression type ('c', 'ct', 'ctt', 'n')
                  'c': constant only
                  'ct': constant + trend (default)
                  'ctt': constant + linear/quadratic trend
                  'n': no constant, no trend
    
    Returns:
    - Series of rolling ADF statistics (more negative = more stationary)
    """
    adf_stats = []
    
    for i in range(len(prices)):
        if i < window:
            adf_stats.append(np.nan)
            continue
        
        # Extract window of prices
        window_prices = prices.iloc[i-window:i]
        
        # Run ADF test
        try:
            result = adfuller(window_prices, regression=regression, autolag='AIC')
            adf_statistic = result[0]  # Extract ADF statistic
            adf_stats.append(adf_statistic)
        except:
            adf_stats.append(np.nan)
    
    return pd.Series(adf_stats, index=prices.index)
```

#### Implementation Notes

**Regression Type:**
- Use `'ct'` (constant + trend) as default
- Accounts for both drift and trend in crypto prices
- More robust than constant-only or no-trend models

**Autolag Selection:**
- Use `autolag='AIC'` to automatically select optimal lag length
- AIC (Akaike Information Criterion) balances fit vs. complexity
- Prevents overfitting with too many lags

**Data Requirements:**
- Minimum 60 days of price data for reliable ADF test
- More data → more reliable test statistic
- Test window should be 2-3 months for crypto

### 2.5 ADF Calculation Parameters

**Default Parameters:**
- **Lookback Window**: 60 days (~2 months)
  - Long enough for reliable statistical test
  - Short enough to capture regime changes
- **Minimum Data**: 50 days (83% of 60 days)
- **Price Frequency**: Daily close prices (levels, not returns)
- **Regression**: 'ct' (constant + trend)
- **Autolag**: 'AIC' (automatic lag selection)

**Parameter Variations to Test:**
- **30-day ADF**: More reactive, captures short-term mean reversion
- **60-day ADF**: Baseline, balanced
- **90-day ADF**: More stable, captures medium-term patterns
- **120-day ADF**: Very stable, long-term stationarity

---

## 3. Signal Generation

### 3.1 Daily Signal Process

**Step 1: Calculate ADF Statistics**
```python
# For each coin, calculate rolling ADF on price levels
adf_stats = calculate_rolling_adf(coin_prices, window=60, regression='ct')
```

**Step 2: Filter Universe**
```python
# Apply liquidity and data quality filters
valid_coins = coins[
    (coins['volume_30d_avg'] > MIN_VOLUME) &
    (coins['market_cap'] > MIN_MARKET_CAP) &
    (coins['adf_stat'].notna()) &
    (coins['data_quality'] > 0.8)
]
```

**Step 3: Rank by ADF**
```python
# Rank from low ADF to high ADF
# Rank 1 = lowest ADF (most mean-reverting/stationary)
# Rank N = highest ADF (most trending/non-stationary)
adf_rank = valid_coins['adf_stat'].rank(ascending=True)
```

**Step 4: Generate Signals**
```python
# Strategy A: Mean Reversion Premium
# Long bottom quintile (low ADF = mean-reverting), Short top quintile (high ADF = trending)
if adf_rank <= 20th_percentile:
    signal = LONG  # Low ADF = stationary/mean-reverting
elif adf_rank >= 80th_percentile:
    signal = SHORT  # High ADF = non-stationary/trending

# Strategy B: Trend Following Premium
# Long top quintile (high ADF = trending), Short bottom quintile (low ADF = mean-reverting)
if adf_rank >= 80th_percentile:
    signal = LONG  # High ADF = trending
elif adf_rank <= 20th_percentile:
    signal = SHORT  # Low ADF = mean-reverting
```

### 3.2 Entry Rules

**Rebalancing Schedule:**
- **Frequency**: Every 7 days (weekly, default)
- **Day**: Monday close (configurable)
- **Execution**: Assume next-day execution (avoid lookahead bias)

**Position Selection:**
- **Long Bucket**: Bottom (or top) quintile by ADF
- **Short Bucket**: Top (or bottom) quintile by ADF
- **Max Positions**: 10-20 longs + 10-20 shorts (configurable)
- **Min ADF Window**: At least 50 days of valid data

**Filters:**
- **Minimum Volume**: 30-day avg volume > $5M (configurable)
- **Minimum Market Cap**: > $50M (configurable)
- **Data Quality**: At least 80% valid data in ADF window
- **Exclude Stablecoins**: Remove USDT, USDC, DAI, etc.

### 3.3 Exit Rules

**Time-Based Exit:**
- Hold positions until next rebalance date
- No intra-period adjustments (except forced exits)

**Forced Exit Conditions:**
- Coin drops below minimum volume threshold
- Coin delisted from exchange
- Data quality deteriorates (missing data)

**No Stop Loss:**
- Hold through drawdowns until rebalance
- Strategy assumes ADF characteristics persist

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
1. Calculate new ADF values
2. Rank all coins by ADF
3. Select new long/short buckets
4. Exit all old positions
5. Enter new positions with target weights
```

---

## 5. Backtest Implementation

### 5.1 File Structure

**Main Script:** `backtests/scripts/backtest_adf_factor.py`

**Purpose:** Backtest engine for ADF-based strategies

**Output Directory:** `backtests/results/`

### 5.2 Command-Line Interface

```bash
python3 backtests/scripts/backtest_adf_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy mean_reversion_premium \
  --adf-window 60 \
  --rebalance-days 7 \
  --weighting-method equal_weight \
  --long-allocation 0.5 \
  --short-allocation 0.5 \
  --start-date 2020-01-01 \
  --end-date 2025-10-27 \
  --output-prefix backtest_adf_factor
```

### 5.3 Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--price-data` | (required) | Path to OHLCV CSV file |
| `--strategy` | `mean_reversion_premium` | Strategy variant: `mean_reversion_premium`, `trend_following_premium`, `long_stationary`, `long_trending` |
| `--adf-window` | 60 | ADF calculation window (days) |
| `--regression` | `'ct'` | ADF regression type: 'c', 'ct', 'ctt', 'n' |
| `--volatility-window` | 30 | Volatility window for risk parity (days) |
| `--rebalance-days` | 7 | Rebalance frequency (days) |
| `--num-quintiles` | 5 | Number of ADF buckets |
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
| `--output-prefix` | `backtest_adf_factor` | Output file prefix |

### 5.4 Output Files

#### 1. Portfolio Values
**File:** `backtest_adf_factor_portfolio_values.csv`

```csv
date,portfolio_value,cash,long_exposure,short_exposure,net_exposure,gross_exposure,num_longs,num_shorts,avg_adf_long,avg_adf_short
2020-01-01,10000.00,0.00,5000.00,-5000.00,0.00,10000.00,10,10,-3.85,-1.12
2020-01-08,10150.25,0.00,5075.13,-5075.13,0.00,10150.25,10,10,-3.92,-1.08
...
```

#### 2. Trade Log
**File:** `backtest_adf_factor_trades.csv`

```csv
date,symbol,signal,adf_stat,adf_rank,percentile,weight,position_size,market_cap,volume_30d_avg,volatility_30d
2020-01-08,BTC,LONG,-4.25,3,6.1,0.11,550.00,180000000000,25000000000,0.45
2020-01-08,ETH,LONG,-3.89,5,10.2,0.10,500.00,25000000000,8000000000,0.62
2020-01-08,DOGE,SHORT,-0.85,48,98.0,0.08,-400.00,2000000000,500000000,1.85
...
```

#### 3. Performance Metrics
**File:** `backtest_adf_factor_metrics.csv`

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
avg_adf_long,-3.85
avg_adf_short,-1.12
total_rebalances,78
trading_days,547
```

#### 4. ADF Time Series
**File:** `backtest_adf_factor_adf_timeseries.csv`

```csv
date,symbol,adf_stat,adf_pvalue,adf_rank,percentile,is_stationary,price,returns_60d_mean,returns_60d_std
2020-01-08,BTC,-4.25,0.0003,3,6.1,True,8500.00,0.0015,0.042
2020-01-08,ETH,-3.89,0.0012,5,10.2,True,155.00,0.0018,0.055
...
```

#### 5. Strategy Info
**File:** `backtest_adf_factor_strategy_info.csv`

```csv
strategy,adf_window,regression,rebalance_days,weighting_method,long_symbols,short_symbols,avg_adf_long,avg_adf_short
mean_reversion_premium,60,ct,7,equal_weight,"BTC,ETH,USDC,...","DOGE,SHIB,APE,...",- -3.85,-1.12
```

---

## 6. Strategy Variants

### 6.1 Mean Reversion Premium - Primary Strategy
**Name:** `mean_reversion_premium`

**Configuration:**
- Long: Bottom quintile (low ADF, most stationary/mean-reverting)
- Short: Top quintile (high ADF, most trending/non-stationary)
- Allocation: 50% long, 50% short
- Market Neutral: Yes

**Hypothesis:** Mean-reverting coins outperform trending coins

**Expected Outcome:**
- Captures mean reversion premium
- Stable returns
- Lower correlation to market

### 6.2 Trend Following Premium
**Name:** `trend_following_premium`

**Configuration:**
- Long: Top quintile (high ADF, most trending/non-stationary)
- Short: Bottom quintile (low ADF, most mean-reverting/stationary)
- Allocation: 50% long, 50% short
- Market Neutral: Yes

**Hypothesis:** Trending coins earn momentum premium

**Expected Outcome:**
- Captures trend continuation
- Higher volatility
- Positive correlation to market

### 6.3 Long Stationary Only
**Name:** `long_stationary`

**Configuration:**
- Long: Bottom quintile (low ADF, most stationary)
- Short: None (50% cash)
- Allocation: 50% long, 0% short
- Market Neutral: No

**Hypothesis:** Stationary coins offer stable returns

**Expected Outcome:**
- Lower volatility
- Steady performance
- Defensive positioning

### 6.4 Long Trending Only
**Name:** `long_trending`

**Configuration:**
- Long: Top quintile (high ADF, most trending)
- Short: None (50% cash)
- Allocation: 50% long, 0% short
- Market Neutral: No

**Hypothesis:** Trending coins capture momentum

**Expected Outcome:**
- Higher volatility
- Strong bull market performance
- Momentum exposure

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

### 7.3 ADF-Specific Metrics
- **Average ADF Long**: Mean ADF of long positions
- **Average ADF Short**: Mean ADF of short positions
- **ADF Spread**: Difference between long and short ADF
- **Stationarity Rate**: % of long coins that are stationary (ADF p-value < 0.05)
- **ADF Stability**: Correlation of ADF ranks across periods

### 7.4 Trading Metrics
- **Win Rate**: % of profitable rebalancing periods
- **Average Turnover**: % of portfolio traded per rebalance
- **Number of Rebalances**: Total rebalancing events
- **Avg Long Positions**: Average number of long positions
- **Avg Short Positions**: Average number of short positions

---

## 8. No-Lookahead Bias Prevention

**Critical Rule:** Signals on day T use returns from day T+1

### 8.1 Implementation

```python
# Day T: Calculate ADF using price levels up to day T
adf_t = calculate_adf(
    coin_prices.loc[:t], 
    window=60,
    regression='ct'
)

# Day T: Rank coins and generate signals
signals_t = generate_signals(adf_t)

# Day T+1: Apply signals using next day's returns
returns_t1 = price_data.loc[t+1, 'return']
pnl_t1 = signals_t * returns_t1  # Use .shift(-1) for proper alignment
```

### 8.2 Key Checks
- ✅ ADF calculated using only past prices (no future data)
- ✅ Signals generated at close of day T
- ✅ Positions executed at open of day T+1
- ✅ Returns from day T+1 used for P&L
- ✅ No future prices used in any calculation

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
  - 60 days for ADF calculation
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
- At least 80% of data points in ADF window
- Handles missing data gracefully

**Outlier Detection:**
- Remove days with returns > ±50% (likely data errors)
- Check for price discontinuities

---

## 10. Risk Considerations

### 10.1 Strategy Risks

**ADF Instability:**
- ADF can change rapidly during regime shifts
- Mean-reverting coins can become trending (and vice versa)
- Solution: Regular rebalancing, longer ADF windows

**Regime Dependency:**
- Mean reversion may only work in range-bound markets
- Trending markets may favor non-stationary coins
- Solution: Test across multiple market cycles

**False Positives:**
- ADF test can give false signals with small samples
- Statistical significance doesn't guarantee trading profit
- Solution: Use longer windows, combine with other filters

**Liquidity Risk:**
- Mean-reverting coins may be less liquid
- Trending coins may have better liquidity
- Solution: Strict volume filters

### 10.2 Implementation Risks

**Computational Cost:**
- ADF test is computationally expensive
- Running for many coins daily may be slow
- Solution: Optimize code, use multiprocessing, cache results

**Statistical Assumptions:**
- ADF assumes no structural breaks
- Crypto markets have frequent regime changes
- Solution: Use shorter windows, monitor for breaks

**Transaction Costs:**
- Frequent rebalancing = high fees
- Solution: Longer rebalance periods (7-14 days)

---

## 11. Expected Insights

### 11.1 Key Questions

**1. Does the mean reversion premium exist in crypto?**
- Do stationary coins outperform trending coins?
- Is the effect statistically significant?
- How large is the premium?

**2. Is ADF stable over time?**
- How much does ADF fluctuate?
- Are stationary coins persistently stationary?
- ADF rank correlation across periods?

**3. Does ADF vary by coin type?**
- DeFi vs. L1 vs. Meme coins?
- Market cap buckets?
- Different ADF characteristics?

**4. How does ADF correlate with other factors?**
- ADF vs. beta factor?
- ADF vs. volatility?
- ADF vs. momentum?
- Independent alpha source?

**5. Does market regime matter?**
- Bull markets: Mean reversion or trending?
- Bear markets: Which strategy works?
- High vol: ADF spreads wider?

### 11.2 Success Criteria

**Minimum Viable Results:**
- **Sharpe Ratio**: > 0.7
- **Maximum Drawdown**: < 30%
- **Win Rate**: > 50%
- **Market Correlation**: < 0.4 (for market neutral)
- **ADF Spread**: Significant difference between long/short

**Stretch Goals:**
- **Sharpe Ratio**: > 1.2
- **Maximum Drawdown**: < 20%
- **Calmar Ratio**: > 0.6
- **Alpha vs BTC**: > 10% annualized
- **Positive in All Regimes**: Consistent performance

---

## 12. Implementation Roadmap

### Phase 1: Core Implementation (Week 1)
- [ ] Create `backtests/scripts/backtest_adf_factor.py`
- [ ] Implement rolling ADF calculation function
- [ ] Implement quintile ranking and selection
- [ ] Add equal-weight portfolio construction
- [ ] Validate no-lookahead bias (use `.shift(-1)`)
- [ ] Run baseline backtest: Mean Reversion Premium

### Phase 2: Testing & Validation (Week 1)
- [ ] Validate ADF calculations (manual spot checks)
- [ ] Check for data quality issues
- [ ] Verify performance metrics calculations
- [ ] Test on different time periods
- [ ] Analyze ADF distribution across coins

### Phase 3: Strategy Variants (Week 2)
- [ ] Implement all 4 strategy variants
- [ ] Add risk parity weighting option
- [ ] Test different rebalancing frequencies
- [ ] Test different ADF windows (30d, 60d, 90d, 120d)
- [ ] Compare strategy performance

### Phase 4: Analysis & Documentation (Week 2)
- [ ] Run all strategy variants
- [ ] Compare all strategy variants
- [ ] Calculate correlation to BTC
- [ ] Compare to other factor strategies (beta, volatility, momentum)
- [ ] Generate performance visualizations
- [ ] Document findings and recommendations

---

## 13. Integration with Existing System

### 13.1 Code Reuse

**Existing Utilities:**
- `backtests/scripts/backtest_beta_factor.py` - Template structure
- `backtests/scripts/backtest_volatility_factor.py` - Quintile ranking logic
- `signals/calc_vola.py` - Volatility calculation (for risk parity)
- `signals/calc_weights.py` - Risk parity weight calculation

**Data Integration:**
- Use existing: `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- Same CSV format and naming conventions
- Store outputs in: `backtests/results/`

### 13.2 Comparison Framework

**Run all factors on same time period:**
```bash
# Beta factor
python3 backtest_beta_factor.py --start-date 2020-01-01

# Volatility factor
python3 backtest_volatility_factor.py --start-date 2020-01-01

# ADF factor (new)
python3 backtest_adf_factor.py --start-date 2020-01-01
```

**Calculate factor correlation matrix:**
- Correlation of daily returns across factors
- Identify diversification opportunities
- Build multi-factor portfolio

---

## 14. Academic References

### 14.1 Time Series Analysis

**ADF Test:**
- Dickey, D. A., & Fuller, W. A. (1979). "Distribution of the Estimators for Autoregressive Time Series with a Unit Root". *Journal of the American Statistical Association*.
- Said, S. E., & Dickey, D. A. (1984). "Testing for Unit Roots in Autoregressive-Moving Average Models of Unknown Order". *Biometrika*.

**Mean Reversion in Finance:**
- Poterba, J. M., & Summers, L. H. (1988). "Mean Reversion in Stock Prices: Evidence and Implications". *Journal of Financial Economics*.
- Fama, E. F., & French, K. R. (1988). "Permanent and Temporary Components of Stock Prices". *Journal of Political Economy*.

### 14.2 Statistical Arbitrage

**Mean Reversion Trading:**
- Gatev, E., Goetzmann, W. N., & Rouwenhorst, K. G. (2006). "Pairs Trading: Performance of a Relative-Value Arbitrage Rule". *Review of Financial Studies*.
- Avellaneda, M., & Lee, J. H. (2010). "Statistical Arbitrage in the US Equities Market". *Quantitative Finance*.

### 14.3 Crypto-Specific

**Crypto Time Series Properties:**
- Urquhart, A. (2016). "The Inefficiency of Bitcoin". *Economics Letters*.
- Nadarajah, S., & Chu, J. (2017). "On the Inefficiency of Bitcoin". *Economics Letters*.

---

## 15. Example Usage

### Basic Backtest
```bash
# Run Mean Reversion Premium (baseline)
python3 backtests/scripts/backtest_adf_factor.py \
  --strategy mean_reversion_premium \
  --adf-window 60 \
  --rebalance-days 7
```

### Test Trend Following
```bash
python3 backtests/scripts/backtest_adf_factor.py \
  --strategy trend_following_premium \
  --adf-window 60 \
  --rebalance-days 7
```

### Parameter Sensitivity
```bash
# Test different ADF windows
for window in 30 60 90 120; do
  python3 backtests/scripts/backtest_adf_factor.py \
    --strategy mean_reversion_premium \
    --adf-window $window \
    --output-prefix backtest_adf_factor_window_${window}
done
```

### Advanced Configuration
```bash
python3 backtests/scripts/backtest_adf_factor.py \
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
  --output-prefix backtest_adf_factor_custom
```

---

## 16. Next Steps

1. **Review Specification**: Validate approach and assumptions
2. **Implement Core Script**: Build `backtest_adf_factor.py` with ADF calculation
3. **Run Initial Backtest**: Test mean reversion premium strategy
4. **Analyze ADF Distribution**: Understand cross-section of stationarity
5. **Test Hypothesis**: Does mean reversion premium exist?
6. **Compare Strategies**: Mean reversion vs. trend following
7. **Parameter Optimization**: Find optimal ADF window and rebalance frequency
8. **Multi-Factor Integration**: Combine with beta, volatility, momentum factors

---

**Document Owner:** Research Team  
**Last Updated:** 2025-10-27  
**Status:** Specification - Ready for Implementation  
**Next Step:** Implement Phase 1 (Core backtest script)

---

**Disclaimer:** This backtest is for research purposes only. Past performance does not guarantee future results. Cryptocurrency trading involves substantial risk of loss. The ADF test is a statistical measure and may not guarantee predictive power in trading. Always conduct thorough research and risk management before deploying capital.
