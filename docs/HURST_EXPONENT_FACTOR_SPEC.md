# Hurst Exponent Factor Strategy Specification

**Version:** 1.0  
**Date:** 2025-10-27  
**Status:** Draft - Ready for Implementation

---

## 1. Executive Summary

This specification outlines a quantitative trading strategy based on the **Hurst exponent** for cryptocurrencies. The core hypothesis tests whether coins with different time series properties (mean-reverting vs. trending) exhibit predictable return patterns that can be exploited through long/short portfolio construction.

### Key Objectives
1. Calculate rolling Hurst exponent for all cryptocurrencies
2. Rank coins by their Hurst exponent values
3. Construct long/short portfolios based on Hurst rankings
4. Test whether mean-reverting coins outperform trending coins
5. Compare performance to existing factor strategies

### Strategy Overview
- **Factor**: Hurst exponent (time series persistence measure)
- **Universe**: All liquid cryptocurrencies with sufficient trading history
- **Rebalancing**: Weekly (configurable)
- **Market Neutrality**: Dollar-neutral long/short construction
- **Risk Management**: Equal weight or risk parity weighting

---

## 2. Strategy Description

### 2.1 Core Concept

The **Hurst exponent (H)** measures the long-term memory and self-similarity of a time series:

\[ H = \frac{\log(R/S)}{\log(n)} \]

Where:
- **R/S** = Rescaled Range statistic
- **n** = Number of observations
- **H < 0.5**: Mean-reverting behavior (anti-persistent)
- **H = 0.5**: Random walk (no memory, geometric Brownian motion)
- **H > 0.5**: Trending behavior (persistent, momentum)

### 2.2 Strategy Hypothesis

Two competing hypotheses can be tested:

#### Hypothesis A: Long Mean-Reverting, Short Trending (BAB-like)
- **Long**: Low Hurst coins (H < 0.5, mean-reverting)
- **Short**: High Hurst coins (H > 0.5, trending/persistent)
- **Rationale**: Mean-reverting assets may be more stable and offer better risk-adjusted returns
- **Similar to**: "Betting Against Beta" anomaly from traditional finance

**Why this might work:**
1. **Volatility Control**: Mean-reverting coins have natural bounds, less prone to extreme moves
2. **Overreaction Correction**: Trending coins may be driven by momentum chasers, eventually reverse
3. **Risk Premium**: Markets may misprice mean-reverting behavior as "boring"
4. **Crypto-Specific**: High Hurst coins may be pump-and-dump candidates

#### Hypothesis B: Long Trending, Short Mean-Reverting (Momentum-like)
- **Long**: High Hurst coins (H > 0.5, trending/persistent)
- **Short**: Low Hurst coins (H < 0.5, mean-reverting)
- **Rationale**: Persistent trends contain information about future price direction
- **Similar to**: Traditional momentum strategies

**Why this might work:**
1. **Trend Following**: Persistent behavior indicates strong directional moves
2. **Information Diffusion**: Trends may reflect gradual information incorporation
3. **Behavioral Bias**: Under-reaction to news creates persistent price moves
4. **Network Effects**: Crypto adoption follows power laws with persistent growth

### 2.3 Hurst Exponent Calculation

#### Method 1: R/S Analysis (Rescaled Range)

The classical method for calculating the Hurst exponent:

```python
import numpy as np

def calculate_hurst_rs(prices, lags=None):
    """
    Calculate Hurst exponent using R/S (Rescaled Range) method
    
    Parameters:
    - prices: Array of price data
    - lags: List of lag sizes (default: geometric spacing)
    
    Returns:
    - hurst: Hurst exponent estimate
    """
    # Convert prices to log returns
    log_returns = np.log(prices[1:] / prices[:-1])
    
    # Use geometric spacing for lags if not specified
    if lags is None:
        n = len(log_returns)
        lags = np.unique(np.logspace(0.5, np.log10(n/2), 20).astype(int))
    
    # Calculate R/S for each lag
    rs_values = []
    for lag in lags:
        # Split returns into chunks of size 'lag'
        n_chunks = len(log_returns) // lag
        if n_chunks < 2:
            continue
            
        rs_list = []
        for i in range(n_chunks):
            chunk = log_returns[i*lag:(i+1)*lag]
            
            # Calculate mean
            mean = np.mean(chunk)
            
            # Calculate cumulative deviations from mean
            deviations = chunk - mean
            cumdev = np.cumsum(deviations)
            
            # Calculate range R
            R = np.max(cumdev) - np.min(cumdev)
            
            # Calculate standard deviation S
            S = np.std(chunk, ddof=1)
            
            # Calculate R/S for this chunk (avoid division by zero)
            if S > 0:
                rs_list.append(R / S)
        
        if len(rs_list) > 0:
            rs_values.append(np.mean(rs_list))
    
    # Fit log(R/S) vs log(lag) to get Hurst exponent
    # H is the slope of this relationship
    if len(rs_values) >= 2:
        log_lags = np.log(lags[:len(rs_values)])
        log_rs = np.log(rs_values)
        
        # Linear regression: log(R/S) = H * log(lag) + const
        hurst = np.polyfit(log_lags, log_rs, 1)[0]
        return hurst
    
    return np.nan
```

#### Method 2: Simplified Variance Method (Faster)

A computationally simpler approximation:

```python
def calculate_hurst_variance(returns, max_lag=20):
    """
    Calculate Hurst exponent using variance method
    
    Parameters:
    - returns: Array of log returns
    - max_lag: Maximum lag to consider
    
    Returns:
    - hurst: Hurst exponent estimate
    """
    lags = range(2, max_lag + 1)
    variances = []
    
    for lag in lags:
        # Calculate variance of returns at different lags
        lagged_returns = returns[::lag]
        if len(lagged_returns) < 3:
            continue
        variances.append(np.var(lagged_returns))
    
    if len(variances) >= 2:
        # Fit log(variance) vs log(lag)
        # For fractional Brownian motion: var ~ lag^(2H)
        log_lags = np.log(list(lags[:len(variances)]))
        log_vars = np.log(variances)
        
        # Slope / 2 gives Hurst exponent
        slope = np.polyfit(log_lags, log_vars, 1)[0]
        hurst = slope / 2.0
        return hurst
    
    return np.nan
```

### 2.4 Calculation Parameters

**Default Parameters:**
- **Lookback Window**: 90 days (~3 months)
  - Long enough for statistical significance
  - Short enough to capture regime changes
- **Minimum Data**: 60 days (70% of 90 days)
- **Return Frequency**: Daily log returns
- **Method**: R/S Analysis (more robust)

**Parameter Variations to Test:**
- **30-day Hurst**: More reactive, captures short-term behavior
- **60-day Hurst**: Balanced approach
- **90-day Hurst**: Baseline, stable estimate
- **180-day Hurst**: Long-term persistent behavior

---

## 3. Signal Generation

### 3.1 Daily Signal Process

**Step 1: Calculate Returns**
```python
# Calculate daily log returns
returns = np.log(close / close.shift(1))
```

**Step 2: Calculate Rolling Hurst Exponent**
```python
# Calculate 90-day rolling Hurst exponent
def rolling_hurst(prices, window=90):
    hurst_values = []
    for i in range(len(prices)):
        if i < window:
            hurst_values.append(np.nan)
        else:
            window_prices = prices[i-window:i]
            hurst = calculate_hurst_rs(window_prices)
            hurst_values.append(hurst)
    return pd.Series(hurst_values, index=prices.index)

df['hurst_90d'] = df.groupby('symbol')['close'].transform(
    lambda x: rolling_hurst(x, window=90)
)
```

**Step 3: Filter Universe**
```python
# Apply liquidity and data quality filters
valid_coins = df[
    (df['volume_30d_avg'] > MIN_VOLUME) &
    (df['market_cap'] > MIN_MARKET_CAP) &
    (df['hurst_90d'].notna()) &
    (~df['hurst_90d'].isin([0, 1]))  # Remove degenerate cases
]
```

**Step 4: Rank by Hurst Exponent**
```python
# Rank from low Hurst to high Hurst
# Rank 1 = lowest Hurst (most mean-reverting)
# Rank N = highest Hurst (most trending)
hurst_rank = valid_coins['hurst_90d'].rank(ascending=True)
```

**Step 5: Generate Signals**
```python
# Strategy A: Long Mean-Reverting, Short Trending
# Long bottom quintile (low Hurst), Short top quintile (high Hurst)
if hurst_rank <= 20th_percentile:
    signal = LONG  # Low Hurst = mean-reverting
elif hurst_rank >= 80th_percentile:
    signal = SHORT  # High Hurst = trending

# Strategy B: Long Trending, Short Mean-Reverting
# Long top quintile (high Hurst), Short bottom quintile (low Hurst)
if hurst_rank >= 80th_percentile:
    signal = LONG  # High Hurst = trending
elif hurst_rank <= 20th_percentile:
    signal = SHORT  # Low Hurst = mean-reverting
```

### 3.2 Entry Rules

**Rebalancing Schedule:**
- **Frequency**: Every 7 days (weekly, default)
- **Day**: Monday close (configurable)
- **Execution**: Assume next-day execution (avoid lookahead bias)

**Position Selection:**
- **Long Bucket**: Bottom (or top) quintile by Hurst
- **Short Bucket**: Top (or bottom) quintile by Hurst
- **Max Positions**: 10 longs + 10 shorts (configurable)
- **Min Data Quality**: At least 70% valid data in Hurst window

**Filters:**
- **Minimum Volume**: 30-day avg volume > $5M (configurable)
- **Minimum Market Cap**: > $50M (configurable)
- **Data Quality**: At least 60 days valid data for 90-day Hurst
- **Exclude Stablecoins**: Remove USDT, USDC, DAI, etc.
- **Hurst Bounds**: Exclude H < 0 or H > 1 (calculation errors)

### 3.3 Exit Rules

**Time-Based Exit:**
- Hold positions until next rebalance date
- No intra-period adjustments (except forced exits)

**Forced Exit Conditions:**
- Coin drops below minimum volume threshold
- Coin delisted from exchange
- Data quality deteriorates (missing data)
- Hurst calculation becomes undefined

**No Stop Loss:**
- Hold through drawdowns until rebalance
- Strategy assumes Hurst properties persist

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

#### Method 2: Risk Parity (Advanced)
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
- **Long-Only**: 100% long, 0% short (test directional hypothesis)
- **Long-Biased**: 75% long, 25% short
- **Levered Neutral**: 100% long, 100% short (2x gross leverage)

### 4.3 Rebalancing Logic

**Full Rebalancing (Default):**
```python
# On rebalance date:
1. Calculate new Hurst exponents
2. Rank all coins by Hurst
3. Select new long/short buckets
4. Exit all old positions
5. Enter new positions with target weights
```

**Partial Rebalancing (Lower Turnover):**
```python
# Only rebalance positions that fall outside buckets
1. Keep positions still in target quintile
2. Exit positions that moved out
3. Add new positions that entered quintile
4. Reduces turnover by ~50%
```

---

## 5. Backtest Implementation

### 5.1 File Structure

**Main Script:** `backtests/scripts/backtest_hurst_exponent_factor.py`

**Purpose:** Backtest engine for Hurst exponent-based strategies

**Output Directory:** `backtests/results/`

### 5.2 Command-Line Interface

```bash
python3 backtests/scripts/backtest_hurst_exponent_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy long_mean_reverting \
  --hurst-window 90 \
  --rebalance-days 7 \
  --weighting-method equal_weight \
  --long-allocation 0.5 \
  --short-allocation 0.5 \
  --start-date 2020-01-01 \
  --end-date 2025-10-27 \
  --output-prefix backtest_hurst_factor
```

### 5.3 Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--price-data` | (required) | Path to OHLCV CSV file |
| `--strategy` | `long_mean_reverting` | Strategy variant: `long_mean_reverting`, `long_trending`, `long_low_hurst`, `long_high_hurst` |
| `--hurst-window` | 90 | Hurst calculation window (days) |
| `--hurst-method` | `rs` | Hurst method: `rs` (R/S analysis), `variance` (variance method) |
| `--volatility-window` | 30 | Volatility window for risk parity (days) |
| `--rebalance-days` | 7 | Rebalance frequency (days) |
| `--num-quintiles` | 5 | Number of Hurst buckets |
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
| `--output-prefix` | `backtest_hurst_factor` | Output file prefix |

### 5.4 Output Files

#### 1. Portfolio Values
**File:** `backtest_hurst_factor_portfolio_values.csv`

```csv
date,portfolio_value,cash,long_exposure,short_exposure,net_exposure,gross_exposure,num_longs,num_shorts,avg_hurst_long,avg_hurst_short
2020-01-01,10000.00,0.00,5000.00,-5000.00,0.00,10000.00,10,10,0.35,0.72
2020-01-08,10150.25,0.00,5075.13,-5075.13,0.00,10150.25,10,10,0.38,0.69
...
```

#### 2. Trade Log
**File:** `backtest_hurst_factor_trades.csv`

```csv
date,symbol,signal,hurst_90d,hurst_rank,percentile,weight,position_size,market_cap,volume_30d_avg,volatility_30d
2020-01-08,BTC,LONG,0.42,5,10.2,0.11,550.00,180000000000,25000000000,0.45
2020-01-08,ETH,LONG,0.38,3,6.1,0.10,500.00,25000000000,8000000000,0.62
2020-01-08,DOGE,SHORT,0.85,48,98.0,0.08,-400.00,2000000000,500000000,1.85
...
```

#### 3. Performance Metrics
**File:** `backtest_hurst_factor_metrics.csv`

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
avg_hurst_long,0.39
avg_hurst_short,0.74
total_rebalances,78
trading_days,547
```

#### 4. Hurst Time Series
**File:** `backtest_hurst_factor_hurst_timeseries.csv`

```csv
date,symbol,hurst_90d,hurst_rank,percentile,returns_90d_mean,returns_90d_std,volume_30d_avg,market_cap
2020-01-08,BTC,0.42,5,10.2,0.0018,0.042,25000000000,180000000000
2020-01-08,ETH,0.38,3,6.1,0.0022,0.055,8000000000,25000000000
...
```

---

## 6. Strategy Variants

### 6.1 Long Mean-Reverting, Short Trending (Primary Strategy)
**Name:** `long_mean_reverting`

**Configuration:**
- Long: Bottom quintile (low Hurst, mean-reverting)
- Short: Top quintile (high Hurst, trending)
- Allocation: 50% long, 50% short
- Market Neutral: Yes

**Hypothesis:** Mean-reverting assets provide more stable returns

**Expected Outcome:**
- Lower volatility
- Defensive positioning
- Positive alpha if mean-reversion premium exists

### 6.2 Long Trending, Short Mean-Reverting
**Name:** `long_trending`

**Configuration:**
- Long: Top quintile (high Hurst, trending)
- Short: Bottom quintile (low Hurst, mean-reverting)
- Allocation: 50% long, 50% short
- Market Neutral: Yes

**Hypothesis:** Persistent trends contain exploitable momentum

**Expected Outcome:**
- Higher returns in trending markets
- Higher volatility
- Captures strong directional moves

### 6.3 Long Low Hurst Only
**Name:** `long_low_hurst`

**Configuration:**
- Long: Bottom quintile (low Hurst, mean-reverting)
- Short: None (50% cash)
- Allocation: 50% long, 0% short
- Market Neutral: No

**Hypothesis:** Mean-reverting coins as defensive positioning

**Expected Outcome:**
- Lower drawdowns
- Stable returns
- Outperforms in bear markets

### 6.4 Long High Hurst Only
**Name:** `long_high_hurst`

**Configuration:**
- Long: Top quintile (high Hurst, trending)
- Short: None (50% cash)
- Allocation: 50% long, 0% short
- Market Neutral: No

**Hypothesis:** Trending coins capture momentum

**Expected Outcome:**
- Higher returns in bull markets
- Higher volatility
- Momentum-like behavior

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

### 7.3 Hurst-Specific Metrics
- **Average Hurst Long**: Mean Hurst of long positions
- **Average Hurst Short**: Mean Hurst of short positions
- **Hurst Spread**: Difference between long and short buckets
- **Hurst Stability**: Correlation of Hurst ranks across periods
- **Alpha vs BTC**: Excess return over BTC buy-and-hold

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
# Day T: Calculate Hurst using data up to day T
hurst_t = calculate_hurst(
    prices.loc[:t], 
    window=90
)

# Day T: Rank coins and generate signals
signals_t = generate_signals(hurst_t)

# Day T+1: Apply signals using next day's returns
returns_t1 = price_data.loc[t+1, 'return']
pnl_t1 = signals_t * returns_t1  # Use .shift(-1) for proper alignment
```

### 8.2 Key Checks
- ✅ Hurst calculated using only past prices (no future data)
- ✅ Signals generated at close of day T
- ✅ Positions executed at open of day T+1 (or close of day T+1)
- ✅ Returns from day T+1 used for P&L
- ✅ No future prices used in any calculation

---

## 9. Data Requirements

### 9.1 Input Data

**Source:** `data/raw/combined_coinbase_coinmarketcap_daily.csv`

**Required Fields:**
- `date`: Trading date (YYYY-MM-DD)
- `symbol`: Coin ticker (BTC, ETH, etc.)
- `open`: Opening price
- `high`: High price
- `low`: Low price
- `close`: Closing price
- `volume`: Trading volume (USD)
- `market_cap`: Market capitalization (USD)

**Minimum History:**
- **Per Coin**: 120 days minimum
  - 90 days for Hurst calculation
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
- At least 70% of data points in Hurst window (60/90 days)
- Handles missing data gracefully

**Outlier Detection:**
- Remove Hurst < 0 or Hurst > 1 (calculation errors)
- Cap returns at ±25% for Hurst calculation (optional)

---

## 10. Risk Considerations

### 10.1 Strategy Risks

**Hurst Instability:**
- Hurst exponent can change during market regime shifts
- Mean-reverting coins can become trending (and vice versa)
- Solution: Regular rebalancing, monitor Hurst stability

**Calculation Sensitivity:**
- Hurst estimation requires sufficient data
- Small sample bias possible with short windows
- Different methods (R/S vs. variance) may give different results
- Solution: Use robust method, validate on synthetic data

**Market Regime Dependency:**
- Strategy may only work in specific market conditions
- Mean-reversion may dominate in sideways markets
- Trending behavior may dominate in bull/bear markets
- Solution: Test across multiple market cycles

**Liquidity Risk:**
- Low Hurst (mean-reverting) coins may be less liquid
- High Hurst (trending) coins may have better liquidity
- Solution: Strict volume filters, risk parity weighting

### 10.2 Implementation Risks

**Computational Complexity:**
- Hurst calculation is computationally expensive
- R/S method requires multiple lag calculations
- Solution: Use efficient implementation, cache results

**Execution Risk:**
- Slippage on rebalancing
- Market impact for large positions
- Solution: VWAP execution, split orders

**Transaction Costs:**
- Weekly rebalancing = moderate turnover
- Solution: Monitor turnover, adjust rebalance frequency

---

## 11. Expected Insights

### 11.1 Key Questions

**1. Does Hurst exponent predict future returns?**
- Do mean-reverting coins outperform?
- Do trending coins outperform?
- Is the effect statistically significant?

**2. Is Hurst stable over time?**
- How much does Hurst fluctuate?
- Are low-Hurst coins persistently mean-reverting?
- Hurst rank correlation across periods?

**3. Does Hurst vary by coin type?**
- DeFi vs. L1 vs. Meme coins?
- Market cap buckets?
- Different Hurst characteristics?

**4. How does Hurst correlate with other factors?**
- Hurst vs. beta factor?
- Hurst vs. volatility factor?
- Hurst vs. momentum?
- Independent alpha source?

**5. What is optimal window length?**
- 30d, 60d, 90d, or 180d?
- Trade-off between stability and responsiveness

### 11.2 Success Criteria

**Minimum Viable Results:**
- **Sharpe Ratio**: > 0.7
- **Maximum Drawdown**: < 30%
- **Win Rate**: > 50%
- **BTC Correlation**: < 0.4 (for market neutral)
- **Hurst Spread**: Long bucket avg < 0.5, Short bucket avg > 0.6

**Stretch Goals:**
- **Sharpe Ratio**: > 1.2
- **Maximum Drawdown**: < 20%
- **Calmar Ratio**: > 0.6
- **Alpha vs BTC**: > 10% annualized
- **Positive in Bear Markets**: Outperform BTC when BTC < 0

---

## 12. Implementation Roadmap

### Phase 1: Core Implementation
- [ ] Create `backtests/scripts/backtest_hurst_exponent_factor.py`
- [ ] Implement Hurst exponent calculation (R/S method)
- [ ] Implement rolling Hurst calculation function
- [ ] Implement quintile ranking and selection
- [ ] Add equal-weight portfolio construction
- [ ] Validate no-lookahead bias (use `.shift(-1)`)
- [ ] Run baseline backtest: Long Mean-Reverting

### Phase 2: Testing & Validation
- [ ] Validate Hurst calculations on synthetic data (known H values)
- [ ] Test on known assets (BTC should be ~0.5, trending alts > 0.5)
- [ ] Check for data quality issues
- [ ] Verify performance metrics calculations
- [ ] Test on different time periods (2020-2025)
- [ ] Analyze Hurst distribution across coins

### Phase 3: Strategy Variants
- [ ] Implement all 4 strategy variants
- [ ] Add risk parity weighting option
- [ ] Test different rebalancing frequencies (7d, 14d, 30d)
- [ ] Test different Hurst windows (30d, 60d, 90d, 180d)
- [ ] Compare R/S vs. variance method
- [ ] Compare strategy performance

### Phase 4: Analysis & Documentation
- [ ] Calculate correlation to BTC
- [ ] Compare to other factor strategies (beta, volatility, skew)
- [ ] Analyze performance by market regime
- [ ] Test Hurst stability over time
- [ ] Generate performance visualizations
- [ ] Document findings and recommendations

---

## 13. Academic References

### 13.1 Time Series Analysis

**Hurst Exponent & Fractional Brownian Motion:**
- Hurst, H. E. (1951). "Long-term storage capacity of reservoirs". *Transactions of the American Society of Civil Engineers*.
- Mandelbrot, B. B., & Van Ness, J. W. (1968). "Fractional Brownian Motions, Fractional Noises and Applications". *SIAM Review*.
- Peters, E. E. (1994). "Fractal Market Analysis: Applying Chaos Theory to Investment and Economics".

**R/S Analysis:**
- Lo, A. W. (1991). "Long-Term Memory in Stock Market Prices". *Econometrica*.
- Couillard, M., & Davison, M. (2005). "A comment on measuring the Hurst exponent of financial time series".

### 13.2 Finance Applications

**Mean Reversion & Persistence:**
- Poterba, J. M., & Summers, L. H. (1988). "Mean reversion in stock prices: Evidence and Implications".
- Cutler, D. M., Poterba, J. M., & Summers, L. H. (1991). "Speculative dynamics".

**Crypto-Specific:**
- Bariviera, A. F. (2017). "The inefficiency of Bitcoin revisited: A dynamic approach". *Economics Letters*.
- Sensoy, A. (2019). "The inefficiency of Bitcoin revisited: A high-frequency analysis with alternative currencies".

---

## 14. Integration with Existing System

### 14.1 Code Reuse

**Existing Utilities:**
- `backtests/scripts/backtest_beta_factor.py` - Template structure
- `backtests/scripts/backtest_volatility_factor.py` - Quintile ranking logic
- `signals/calc_vola.py` - Volatility calculation (for risk parity)

**Data Integration:**
- Use existing: `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- Same CSV format and naming conventions
- Store outputs in: `backtests/results/`

### 14.2 Comparison Framework

**Run all factors on same time period:**
```bash
# Beta factor
python3 backtest_beta_factor.py --start-date 2020-01-01

# Volatility factor
python3 backtest_volatility_factor.py --start-date 2020-01-01

# Hurst exponent factor (new)
python3 backtest_hurst_exponent_factor.py --start-date 2020-01-01
```

**Calculate factor correlation matrix:**
- Correlation of daily returns across factors
- Identify diversification opportunities
- Build multi-factor portfolio

---

## 15. Example Usage

### Basic Backtest
```bash
# Run Long Mean-Reverting (baseline)
python3 backtests/scripts/backtest_hurst_exponent_factor.py \
  --strategy long_mean_reverting \
  --hurst-window 90 \
  --rebalance-days 7
```

### Test Long Trending
```bash
python3 backtests/scripts/backtest_hurst_exponent_factor.py \
  --strategy long_trending \
  --hurst-window 90 \
  --rebalance-days 7
```

### Parameter Sensitivity
```bash
# Test different Hurst windows
for window in 30 60 90 180; do
  python3 backtests/scripts/backtest_hurst_exponent_factor.py \
    --strategy long_mean_reverting \
    --hurst-window $window \
    --output-prefix backtests/results/hurst_factor_window_${window}
done
```

### Advanced Configuration
```bash
python3 backtests/scripts/backtest_hurst_exponent_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy long_mean_reverting \
  --hurst-window 90 \
  --hurst-method rs \
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
  --output-prefix backtests/results/hurst_factor_custom
```

---

## 16. Next Steps

1. **Validate Hurst Calculation**: Test on synthetic fractional Brownian motion
2. **Implement Baseline Script**: Start with `long_mean_reverting` strategy
3. **Run Initial Backtest**: Generate first results
4. **Analyze Hurst Distribution**: Understand cross-section of Hurst values
5. **Test Hypothesis**: Does mean-reversion premium exist in crypto?
6. **Compare Strategies**: Mean-reverting vs. trending
7. **Parameter Optimization**: Find optimal Hurst window and rebalance frequency
8. **Multi-Factor Integration**: Combine with beta, volatility, momentum factors

---

**Document Owner:** Research Team  
**Last Updated:** 2025-10-27  
**Status:** Ready for Implementation  
**Next Step:** Implement Phase 1 (Core backtest script)

---

**Disclaimer:** This backtest is for research purposes only. Past performance does not guarantee future results. Cryptocurrency trading involves substantial risk of loss. The Hurst exponent is a statistical measure and may not predict future price behavior. Always conduct thorough research and risk management before deploying capital.
