# Trendline Factor Trading Strategy Specification

**Version:** 1.0  
**Date:** 2025-10-28  
**Status:** Specification - Ready for Implementation

---

## 1. Executive Summary

This specification outlines a quantitative trading strategy based on **trendline analysis using rolling linear regression** for cryptocurrencies. The strategy combines trend direction (slope) with trend quality (R² score) to identify coins with the strongest and cleanest directional movements.

### Key Objectives
1. Calculate rolling linear regression on closing prices for all cryptocurrencies
2. Extract trendline slope (direction and magnitude) and R² score (trend quality)
3. Rank coins by combined trendline metrics (slope × R², or slope + R²)
4. Construct long/short portfolios based on trendline rankings
5. Test whether coins with strong, clean trends outperform
6. Compare performance to existing factor strategies

### Strategy Overview
- **Factor**: Trendline strength = f(slope, R²) from rolling linear regression
- **Universe**: All liquid cryptocurrencies with sufficient trading history
- **Rebalancing**: Weekly (configurable)
- **Market Neutrality**: Dollar-neutral long/short construction (optional)
- **Risk Management**: Equal weight or risk parity weighting

---

## 2. Strategy Description

### 2.1 Core Concept

The **Trendline Factor** uses rolling linear regression to fit a trendline to closing prices over a fixed lookback window. Two key metrics are extracted:

1. **Slope (β)**: Direction and magnitude of the trend
   - Positive slope → Uptrend
   - Negative slope → Downtrend
   - Larger magnitude → Stronger trend

2. **R² Score**: Quality/cleanness of the trend (coefficient of determination)
   - R² close to 1.0 → Clean, linear trend (low noise)
   - R² close to 0.0 → Noisy, no clear trend (high noise)
   - R² measures how well the linear model fits the data

**Linear Regression Model:**
\[ \text{Price}_t = \alpha + \beta \cdot t + \epsilon_t \]

Where:
- \( \text{Price}_t \) = Closing price at time t
- \( t \) = Time index (0, 1, 2, ..., n-1)
- \( \alpha \) = Intercept (starting price level)
- \( \beta \) = Slope (price change per day)
- \( \epsilon_t \) = Residual error
- **R²** = 1 - (SS_residual / SS_total) = Proportion of variance explained by the model

**Trendline Score:**
The strategy combines slope and R² to create a composite trendline score:

**Option 1: Multiplicative (Weighted Strength)**
\[ \text{Trendline Score} = \text{Slope} \times \text{R²} \]
- Prioritizes coins with both strong trends AND clean trends
- R² acts as a confidence filter

**Option 2: Additive (Balanced)**
\[ \text{Trendline Score} = w_1 \cdot \text{Normalized Slope} + w_2 \cdot \text{R²} \]
- Allows independent contribution from slope and R²
- More flexible, but requires normalization and weight tuning

**Option 3: R²-Filtered Slope (Conservative)**
\[ \text{Trendline Score} = \begin{cases} 
\text{Slope} & \text{if } R² > \text{threshold} \\
0 & \text{otherwise}
\end{cases} \]
- Only considers coins with clean trends (R² > 0.5 or 0.6)
- Reduces noise by filtering out choppy markets

### 2.2 Strategy Hypothesis

#### Hypothesis A: Strong Clean Trends Outperform (Momentum + Quality)
- **Long**: Coins with high positive slope AND high R² (strong uptrends)
- **Short**: Coins with low negative slope AND high R² (strong downtrends)
- **Rationale**: Trends with high R² are more likely to continue (less noise = more signal)

**Why this might work:**
1. **Trend Persistence**: Clean trends (high R²) indicate sustained directional pressure
2. **Signal-to-Noise**: High R² filters out false signals from noisy, range-bound markets
3. **Momentum Quality**: Not just momentum, but *clean* momentum
4. **Behavioral**: Strong, clean trends attract more capital → self-reinforcing
5. **Technical Trading**: Many traders follow trendlines → becomes self-fulfilling

#### Hypothesis B: Slope-Only Momentum (Ignore R²)
- **Long**: Highest slope (strongest uptrends)
- **Short**: Lowest slope (strongest downtrends)
- **Rationale**: Trend direction matters more than trend quality

**Why this might work:**
1. **Pure Momentum**: Captures price velocity regardless of path smoothness
2. **All Trends Matter**: Even noisy trends can be profitable
3. **Simplicity**: Slope is more intuitive and robust

#### Hypothesis C: R²-Only Quality (Trend Cleanliness)
- **Long**: Highest R² regardless of slope direction
- **Short**: Lowest R² (noisy, range-bound)
- **Rationale**: Clean trends (high R²) are more tradeable and predictable

**Why this might work:**
1. **Predictability**: Clean trends are easier to ride
2. **Lower Risk**: Less whipsaw, fewer false signals
3. **Regime Indicator**: High R² = trending regime, low R² = mean-reverting regime

### 2.3 Crypto Market Application

**Why trendline factor might work in crypto:**
1. **Strong Trends**: Crypto exhibits persistent trends (both up and down)
2. **Momentum**: Well-documented momentum effects in crypto
3. **Retail Behavior**: Retail traders heavily use technical analysis and trendlines
4. **FOMO/FUD**: Clean uptrends attract FOMO, clean downtrends trigger panic
5. **Limited Mean Reversion**: Unlike some equity markets, crypto trends can persist for months
6. **Network Effects**: Growing projects (high slope, high R²) attract more users → positive feedback

**Why R² matters specifically in crypto:**
1. **Volatility**: Crypto is extremely volatile → R² helps filter noise
2. **Quality Trends**: Not all uptrends are equal → R² identifies sustainable moves
3. **Risk Management**: High R² trends have clearer entry/exit points (support/resistance)
4. **Regime Detection**: R² helps distinguish trending vs. range-bound markets

### 2.4 Trendline Calculation

#### Method: Rolling Linear Regression

```python
import numpy as np
import pandas as pd
from scipy import stats

def calculate_rolling_trendline(prices, window=30):
    """
    Calculate rolling linear regression on closing prices
    
    Parameters:
    - prices: Series of closing prices (levels, not returns)
    - window: Rolling window in days (default: 30 days)
    
    Returns:
    - DataFrame with columns: slope, intercept, r_squared, p_value, std_err
    """
    def fit_trendline(price_window):
        """Fit linear regression to price window"""
        n = len(price_window)
        if n < window * 0.7:  # Require 70% data availability
            return pd.Series({
                'slope': np.nan,
                'intercept': np.nan,
                'r_squared': np.nan,
                'p_value': np.nan,
                'std_err': np.nan
            })
        
        # Remove NaN values
        valid_mask = ~np.isnan(price_window.values)
        if valid_mask.sum() < window * 0.7:
            return pd.Series({
                'slope': np.nan,
                'intercept': np.nan,
                'r_squared': np.nan,
                'p_value': np.nan,
                'std_err': np.nan
            })
        
        valid_prices = price_window.values[valid_mask]
        valid_x = np.arange(len(valid_prices))
        
        # Fit linear regression using scipy
        slope, intercept, r_value, p_value, std_err = stats.linregress(valid_x, valid_prices)
        r_squared = r_value ** 2
        
        return pd.Series({
            'slope': slope,
            'intercept': intercept,
            'r_squared': r_squared,
            'p_value': p_value,
            'std_err': std_err
        })
    
    # Calculate rolling trendline metrics
    results = prices.rolling(window).apply(
        lambda x: fit_trendline(x),
        raw=False
    )
    
    return results

def calculate_normalized_slope(slope, price_level):
    """
    Normalize slope by price level to make slopes comparable across coins
    
    Returns: Annualized percentage slope
    """
    # Convert daily slope to percentage per day
    pct_slope_daily = (slope / price_level) * 100
    
    # Annualize (multiply by 365)
    pct_slope_annual = pct_slope_daily * 365
    
    return pct_slope_annual

def calculate_trendline_score(slope, r_squared, price_level, method='multiplicative'):
    """
    Calculate composite trendline score
    
    Parameters:
    - slope: Raw slope from linear regression
    - r_squared: R² from linear regression (0 to 1)
    - price_level: Current price (for normalization)
    - method: 'multiplicative', 'additive', 'filtered', or 'slope_only'
    
    Returns:
    - Trendline score (higher = stronger bullish trend, lower = stronger bearish trend)
    """
    # Normalize slope to percentage (comparable across coins)
    norm_slope = calculate_normalized_slope(slope, price_level)
    
    if method == 'multiplicative':
        # Slope × R² (prioritizes both strength and quality)
        return norm_slope * r_squared
    
    elif method == 'additive':
        # Weighted sum (requires slope normalization)
        # Normalize R² to match slope scale
        w_slope = 0.7
        w_r2 = 0.3
        return w_slope * norm_slope + w_r2 * (r_squared * 100)
    
    elif method == 'filtered':
        # Only use slope if R² is high enough (conservative)
        r2_threshold = 0.5
        if r_squared >= r2_threshold:
            return norm_slope
        else:
            return 0.0
    
    elif method == 'slope_only':
        # Pure momentum, ignore R²
        return norm_slope
    
    elif method == 'r2_only':
        # Pure quality, ignore direction
        return r_squared
    
    else:
        raise ValueError(f"Unknown method: {method}")
```

#### Implementation Notes

**Window Selection:**
- **Short Window (14-30 days)**: Captures recent trends, more reactive
- **Medium Window (30-60 days)**: Baseline, balanced between responsiveness and stability
- **Long Window (60-90 days)**: Captures longer-term trends, more stable

**Normalization:**
- **Critical**: Slope must be normalized by price level
- BTC at $40,000 with slope=100 ≠ ETH at $2,000 with slope=100
- Use percentage change per day (slope / price) × 100
- Annualize for interpretability: × 365

**R² Interpretation:**
- **R² > 0.8**: Very strong linear trend (excellent fit)
- **R² = 0.6-0.8**: Strong trend (good fit)
- **R² = 0.4-0.6**: Moderate trend (noisy but present)
- **R² < 0.4**: Weak/no trend (range-bound, noisy)

**Statistical Significance:**
- Can use p-value to filter statistically significant trends
- p-value < 0.05 → Slope significantly different from zero
- Optional filter: Only trade coins with p-value < 0.05

### 2.5 Trendline Calculation Parameters

**Default Parameters:**
- **Lookback Window**: 30 days (~1 month)
  - Long enough to establish trend
  - Short enough to be responsive
- **Minimum Data**: 21 days (70% of 30 days)
- **Price Frequency**: Daily close prices (levels, not returns)
- **Score Method**: Multiplicative (slope × R²)
- **R² Threshold**: No threshold (use all coins, let ranking decide)

**Parameter Variations to Test:**
- **14-day trendline**: Short-term momentum
- **30-day trendline**: Baseline
- **60-day trendline**: Medium-term trend
- **90-day trendline**: Long-term trend

---

## 3. Signal Generation

### 3.1 Daily Signal Process

**Step 1: Calculate Trendline Metrics**
```python
# For each coin, calculate rolling trendline
for coin in universe:
    trendline = calculate_rolling_trendline(coin_prices, window=30)
    coin['slope'] = trendline['slope']
    coin['r_squared'] = trendline['r_squared']
    coin['p_value'] = trendline['p_value']
```

**Step 2: Normalize Slope**
```python
# Normalize slope by current price level
coin['norm_slope'] = (coin['slope'] / coin['close']) * 100 * 365  # Annualized %
```

**Step 3: Calculate Trendline Score**
```python
# Combine slope and R² into composite score
coin['trendline_score'] = coin['norm_slope'] * coin['r_squared']
```

**Step 4: Filter Universe**
```python
# Apply liquidity and data quality filters
valid_coins = coins[
    (coins['volume_30d_avg'] > MIN_VOLUME) &
    (coins['market_cap'] > MIN_MARKET_CAP) &
    (coins['trendline_score'].notna()) &
    (coins['r_squared'] > 0.2) &  # Optional: Filter out very noisy coins
    (coins['data_quality'] > 0.7)
]
```

**Step 5: Rank by Trendline Score**
```python
# Rank from low to high
# Low rank = negative slope with high R² (clean downtrend)
# High rank = positive slope with high R² (clean uptrend)
trendline_rank = valid_coins['trendline_score'].rank(ascending=True)
```

**Step 6: Generate Signals**
```python
# Strategy A: Long Strong Uptrends, Short Strong Downtrends
# Long top quintile (highest trendline scores = bullish trends)
if trendline_rank >= 80th_percentile:
    signal = LONG  # Strong positive slope × high R²

# Short bottom quintile (lowest trendline scores = bearish trends)
elif trendline_rank <= 20th_percentile:
    signal = SHORT  # Strong negative slope × high R²

# Strategy B: R²-Weighted Momentum
# Rank by: slope × R² (prioritizes clean trends)
# Long: High positive slope AND high R²
# Short: Low negative slope AND high R²
```

### 3.2 Entry Rules

**Rebalancing Schedule:**
- **Frequency**: Every 7 days (weekly, default)
- **Day**: Monday close (configurable)
- **Execution**: Assume next-day execution (avoid lookahead bias)

**Position Selection:**
- **Long Bucket**: Top quintile by trendline score (strong uptrends)
- **Short Bucket**: Bottom quintile by trendline score (strong downtrends)
- **Max Positions**: 10-20 longs + 10-20 shorts (configurable)
- **Min Trendline Window**: At least 21 days of valid data

**Filters:**
- **Minimum Volume**: 30-day avg volume > $5M (configurable)
- **Minimum Market Cap**: > $50M (configurable)
- **Minimum R²**: > 0.2 (optional, filters very noisy coins)
- **Statistical Significance**: p-value < 0.05 (optional filter)
- **Data Quality**: At least 70% valid data in trendline window
- **Exclude Stablecoins**: Remove USDT, USDC, DAI, etc.

**Optional Enhancements:**
- **Trend Confirmation**: Require slope to match recent returns (avoid stale trends)
- **Volatility Filter**: Exclude coins with extreme volatility (regime dependent)
- **R² Threshold**: Only trade coins with R² > 0.4 or 0.5 (conservative)

### 3.3 Exit Rules

**Time-Based Exit:**
- Hold positions until next rebalance date
- No intra-period adjustments (except forced exits)

**Forced Exit Conditions:**
- Coin drops below minimum volume threshold
- Coin delisted from exchange
- Data quality deteriorates (missing data)
- Optional: R² falls below threshold (trend breaks down)

**Optional: Trend Breakdown Exit**
- Monitor R² during holding period
- If R² drops significantly (e.g., from 0.7 to 0.3), trend may be breaking
- Early exit to reduce drawdown risk (requires daily monitoring)

**No Stop Loss:**
- Hold through drawdowns until rebalance (default)
- Strategy assumes clean trends persist

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
- Doesn't account for trend strength differences

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

#### Method 3: Score-Weighted (Experimental)
```python
# Weight proportional to absolute trendline score
# Stronger trends get higher weights

abs_score = np.abs(coin['trendline_score'])
weights = (abs_score / abs_score.sum()) * allocation
```

**Pros:**
- Allocates more capital to strongest trends
- Captures conviction in signal strength

**Cons:**
- Can be concentrated (few coins with very high scores)
- Sensitive to outliers

#### Method 4: R²-Weighted (Conservative)
```python
# Weight proportional to R² (trend quality)
# Cleaner trends get higher weights

r2 = coin['r_squared']
weights = (r2 / r2.sum()) * allocation
```

**Pros:**
- Prioritizes high-quality trends
- Reduces noise exposure

**Cons:**
- Ignores trend direction strength (slope)
- May underweight strong but slightly noisy trends

### 4.2 Portfolio Allocation

**Default Configuration:**
- **Long Allocation**: 50% of capital
- **Short Allocation**: 50% of capital
- **Cash**: 0% (fully invested, market neutral)
- **Leverage**: 1.0x (no leverage by default)

**Alternative Configurations:**
- **Long-Only**: 100% long, 0% short (trend following)
- **Long-Biased**: 75% long, 25% short (bullish tilt)
- **Levered Neutral**: 100% long, 100% short (2x gross leverage)

### 4.3 Rebalancing Logic

**Full Rebalancing (Default):**
```python
# On rebalance date:
1. Calculate new trendline metrics (slope, R², score)
2. Rank all coins by trendline score
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

**Adaptive Rebalancing (Experimental):**
```python
# Rebalance based on trend quality deterioration
1. Monitor R² of existing positions
2. If R² drops significantly → exit early
3. If new coins have much better scores → rotate
4. More active, higher turnover
```

---

## 5. Backtest Implementation

### 5.1 File Structure

**Main Script:** `backtests/scripts/backtest_trendline_factor.py`

**Purpose:** Backtest engine for trendline-based strategies

**Output Directory:** `backtests/results/`

### 5.2 Command-Line Interface

```bash
python3 backtests/scripts/backtest_trendline_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy long_uptrend_short_downtrend \
  --trendline-window 30 \
  --score-method multiplicative \
  --rebalance-days 7 \
  --weighting-method equal_weight \
  --long-allocation 0.5 \
  --short-allocation 0.5 \
  --start-date 2021-01-01 \
  --end-date 2025-10-28 \
  --output-prefix backtest_trendline_factor
```

### 5.3 Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--price-data` | (required) | Path to OHLCV CSV file |
| `--strategy` | `long_uptrend_short_downtrend` | Strategy variant (see Section 6) |
| `--trendline-window` | 30 | Trendline lookback window (days) |
| `--score-method` | `multiplicative` | Score method: `multiplicative`, `additive`, `filtered`, `slope_only`, `r2_only` |
| `--r2-threshold` | 0.0 | Minimum R² for filtering (0.0 = no filter) |
| `--pvalue-threshold` | 1.0 | Maximum p-value for filtering (1.0 = no filter) |
| `--volatility-window` | 30 | Volatility window for risk parity (days) |
| `--rebalance-days` | 7 | Rebalance frequency (days) |
| `--num-quintiles` | 5 | Number of trendline buckets |
| `--long-percentile` | 80 | Percentile threshold for long (top 20%) |
| `--short-percentile` | 20 | Percentile threshold for short (bottom 20%) |
| `--weighting-method` | `equal_weight` | Weighting: `equal_weight`, `risk_parity`, `score_weighted`, `r2_weighted` |
| `--min-volume` | 5000000 | Minimum 30d avg volume ($) |
| `--min-market-cap` | 50000000 | Minimum market cap ($) |
| `--initial-capital` | 10000 | Starting capital (USD) |
| `--leverage` | 1.0 | Leverage multiplier |
| `--long-allocation` | 0.5 | Long side allocation (50%) |
| `--short-allocation` | 0.5 | Short side allocation (50%) |
| `--start-date` | None | Backtest start (YYYY-MM-DD) |
| `--end-date` | None | Backtest end (YYYY-MM-DD) |
| `--output-prefix` | `backtest_trendline_factor` | Output file prefix |

### 5.4 Output Files

#### 1. Portfolio Values
**File:** `backtest_trendline_factor_portfolio_values.csv`

```csv
date,portfolio_value,cash,long_exposure,short_exposure,net_exposure,gross_exposure,num_longs,num_shorts,avg_trendline_score_long,avg_trendline_score_short,avg_r2_long,avg_r2_short
2021-01-01,10000.00,0.00,5000.00,-5000.00,0.00,10000.00,10,10,125.5,-85.2,0.72,0.68
2021-01-08,10350.75,0.00,5175.38,-5175.38,0.00,10350.75,10,10,132.3,-78.5,0.75,0.65
...
```

**Fields:**
- `date`: Trading date
- `portfolio_value`: Total portfolio NAV
- `cash`: Cash balance
- `long_exposure`: Dollar value of long positions
- `short_exposure`: Dollar value of short positions (negative)
- `net_exposure`: Long + short (market directional exposure)
- `gross_exposure`: |Long| + |Short| (total capital deployed)
- `num_longs`: Number of long positions
- `num_shorts`: Number of short positions
- `avg_trendline_score_long`: Average trendline score of long positions
- `avg_trendline_score_short`: Average trendline score of short positions
- `avg_r2_long`: Average R² of long positions
- `avg_r2_short`: Average R² of short positions

#### 2. Trade Log
**File:** `backtest_trendline_factor_trades.csv`

```csv
date,symbol,signal,slope,norm_slope,r_squared,trendline_score,trendline_rank,percentile,weight,position_size,price,market_cap,volume_30d_avg,p_value
2021-01-08,BTC,LONG,125.5,8.5,0.82,6.97,47,95.9,0.10,1000.00,42500.00,800000000000,30000000000,0.001
2021-01-08,ETH,LONG,85.3,15.2,0.78,11.86,49,100.0,0.11,1100.00,1850.00,220000000000,12000000000,0.003
2021-01-08,DOGE,SHORT,-0.02,-12.8,0.65,-8.32,2,4.1,0.08,-800.00,0.05,7000000000,800000000,0.015
...
```

#### 3. Performance Metrics
**File:** `backtest_trendline_factor_metrics.csv`

```csv
metric,value
initial_capital,10000.00
final_value,18575.50
total_return,0.8576
annualized_return,0.3245
annualized_volatility,0.2154
sharpe_ratio,1.51
sortino_ratio,2.18
max_drawdown,-0.2245
calmar_ratio,1.45
win_rate,0.5834
avg_long_positions,10.2
avg_short_positions,9.8
avg_trendline_score_long,118.5
avg_trendline_score_short,-72.3
avg_r2_long,0.71
avg_r2_short,0.67
total_rebalances,85
trading_days,630
```

#### 4. Trendline Time Series
**File:** `backtest_trendline_factor_trendline_timeseries.csv`

```csv
date,symbol,slope,norm_slope,intercept,r_squared,p_value,trendline_score,trendline_rank,percentile,price,volume_30d_avg,market_cap
2021-01-08,BTC,125.5,8.5,40000.0,0.82,0.001,6.97,47,95.9,42500.00,30000000000,800000000000
2021-01-08,ETH,85.3,15.2,1500.0,0.78,0.003,11.86,49,100.0,1850.00,12000000000,220000000000
...
```

#### 5. Strategy Info
**File:** `backtest_trendline_factor_strategy_info.csv`

```csv
strategy,trendline_window,score_method,r2_threshold,rebalance_days,weighting_method,long_symbols,short_symbols,avg_trendline_score_long,avg_trendline_score_short,avg_r2_long,avg_r2_short
long_uptrend_short_downtrend,30,multiplicative,0.0,7,equal_weight,"BTC,ETH,SOL,...","DOGE,SHIB,LTC,...",118.5,-72.3,0.71,0.67
```

---

## 6. Strategy Variants

### 6.1 Long Uptrends, Short Downtrends (Primary Strategy)
**Name:** `long_uptrend_short_downtrend`

**Configuration:**
- Long: Top quintile (highest trendline scores = strong uptrends with high R²)
- Short: Bottom quintile (lowest trendline scores = strong downtrends with high R²)
- Score Method: Multiplicative (slope × R²)
- Allocation: 50% long, 50% short
- Market Neutral: Yes

**Hypothesis:** Clean, strong trends (both up and down) are persistent and exploitable

**Expected Outcome:**
- Captures momentum with quality filter
- Reduced noise compared to pure momentum
- Market neutral with low correlation to BTC

### 6.2 Long-Only Strong Uptrends
**Name:** `long_only_uptrends`

**Configuration:**
- Long: Top quintile (highest trendline scores)
- Short: None (50% cash)
- Score Method: Multiplicative (slope × R²)
- Allocation: 50% long, 0% short
- Market Neutral: No

**Hypothesis:** Strong, clean uptrends continue

**Expected Outcome:**
- Pure momentum/trend following
- Higher volatility than market neutral
- Positive correlation to BTC
- Better performance in bull markets

### 6.3 Slope-Only Momentum
**Name:** `slope_only_momentum`

**Configuration:**
- Long: Highest slope (ignore R²)
- Short: Lowest slope (ignore R²)
- Score Method: slope_only
- Allocation: 50% long, 50% short
- Market Neutral: Yes

**Hypothesis:** Trend direction matters more than trend quality

**Expected Outcome:**
- Similar to pure momentum factor
- More trades in noisy conditions
- Higher turnover

### 6.4 R²-Filtered Conservative
**Name:** `r2_filtered_conservative`

**Configuration:**
- Long: Top quintile with R² > 0.5
- Short: Bottom quintile with R² > 0.5
- Score Method: filtered (only high R² coins)
- Allocation: 50% long, 50% short
- Market Neutral: Yes

**Hypothesis:** Only trade very clean trends

**Expected Outcome:**
- Lower turnover
- Fewer trades (higher quality)
- More stable returns
- May miss some profitable but noisy trends

### 6.5 R²-Only Quality
**Name:** `r2_only_quality`

**Configuration:**
- Long: Highest R² (cleanest trends, any direction)
- Short: Lowest R² (noisiest, range-bound)
- Score Method: r2_only
- Allocation: 50% long, 50% short
- Market Neutral: Yes

**Hypothesis:** Clean trends (high R²) are easier to trade and more profitable

**Expected Outcome:**
- Not directional (longs can be up or down)
- Tests whether trend quality matters more than direction
- Unique factor exposure

### 6.6 Short-Term Trendline (14-day)
**Name:** `short_term_trendline`

**Configuration:**
- Long: Top quintile by 14-day trendline score
- Short: Bottom quintile by 14-day trendline score
- Trendline Window: 14 days
- Rebalance: More frequently (3-5 days)
- Market Neutral: Yes

**Hypothesis:** Recent trends are more predictive

**Expected Outcome:**
- More reactive to price changes
- Higher turnover
- Captures short-term momentum

### 6.7 Long-Term Trendline (90-day)
**Name:** `long_term_trendline`

**Configuration:**
- Long: Top quintile by 90-day trendline score
- Short: Bottom quintile by 90-day trendline score
- Trendline Window: 90 days
- Rebalance: Less frequently (14-30 days)
- Market Neutral: Yes

**Hypothesis:** Long-term trends are more stable and persistent

**Expected Outcome:**
- More stable positions
- Lower turnover
- Captures major trends
- Less whipsaw

---

## 7. Performance Metrics

### 7.1 Return Metrics
- **Total Return**: Cumulative return over backtest period
- **Annualized Return**: CAGR = (Final / Initial)^(365/days) - 1
- **Monthly Returns**: Time series of monthly performance
- **Rolling Returns**: 90-day rolling returns
- **Return by Regime**: Bull vs. bear market performance

### 7.2 Risk Metrics
- **Annualized Volatility**: Std(daily returns) × √365
- **Sharpe Ratio**: (Return - RFR) / Volatility (RFR = 0%)
- **Sortino Ratio**: (Return - RFR) / Downside Volatility
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Calmar Ratio**: Annualized Return / Max Drawdown
- **Value at Risk (VaR)**: 95th percentile daily loss
- **Conditional VaR (CVaR)**: Expected loss beyond VaR

### 7.3 Trendline-Specific Metrics
- **Average Trendline Score Long**: Mean score of long positions
- **Average Trendline Score Short**: Mean score of short positions
- **Average R² Long**: Mean R² of long positions
- **Average R² Short**: Mean R² of short positions
- **Average Slope Long**: Mean normalized slope of long positions
- **Average Slope Short**: Mean normalized slope of short positions
- **R² Spread**: Difference between long and short R² (quality difference)
- **Slope Spread**: Difference between long and short slope (trend strength)
- **Trend Persistence**: Correlation of trendline scores across periods
- **R² Distribution**: Histogram/percentiles of R² values in universe

### 7.4 Trading Metrics
- **Win Rate**: % of profitable rebalancing periods
- **Average Turnover**: % of portfolio traded per rebalance
- **Number of Rebalances**: Total rebalancing events
- **Avg Long Positions**: Average number of long positions
- **Avg Short Positions**: Average number of short positions
- **Hit Ratio**: % of correct long/short calls
- **Avg Holding Period**: Days per position (for partial rebalancing)

### 7.5 Regime Analysis
- **Bull Market Performance**: Returns when BTC > 200d MA
- **Bear Market Performance**: Returns when BTC < 200d MA
- **High Volatility**: Returns when BTC 30d vol > median
- **Low Volatility**: Returns when BTC 30d vol < median
- **High R² Regime**: Performance when average R² is high (trending market)
- **Low R² Regime**: Performance when average R² is low (range-bound market)

---

## 8. No-Lookahead Bias Prevention

**Critical Rule:** Signals on day T use returns from day T+1

### 8.1 Implementation

```python
# Day T: Calculate trendline using price levels up to day T
trendline_t = calculate_rolling_trendline(
    coin_prices.loc[:t], 
    window=30
)

# Day T: Calculate trendline score
score_t = trendline_t['slope'] * trendline_t['r_squared']

# Day T: Rank coins and generate signals
signals_t = generate_signals(score_t)

# Day T+1: Apply signals using next day's returns
returns_t1 = price_data.loc[t+1, 'return']
pnl_t1 = signals_t * returns_t1  # Use .shift(-1) for proper alignment
```

### 8.2 Key Checks
- ✅ Trendline calculated using only past prices (no future data)
- ✅ Linear regression uses prices from [t-window, t]
- ✅ Signals generated at close of day T
- ✅ Positions executed at open of day T+1 (or close for simplicity)
- ✅ Returns from day T+1 used for P&L
- ✅ No future prices used in any calculation
- ✅ R² and slope calculated on same historical window

---

## 9. Data Requirements

### 9.1 Input Data

**Source:** `data/raw/combined_coinbase_coinmarketcap_daily.csv`

**Required Fields:**
- `date`: Trading date (YYYY-MM-DD)
- `symbol`: Coin ticker (BTC, ETH, etc.)
- `close`: Closing price (levels, not returns) **[CRITICAL]**
- `volume`: Trading volume (USD)
- `market_cap`: Market capitalization (USD)

**Minimum History:**
- **Per Coin**: 60 days minimum
  - 30 days for trendline calculation
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
- At least 70% of data points in trendline window
- Handles missing data gracefully (skip if < 70% data)

**Outlier Detection:**
- Remove days with returns > ±50% (likely data errors)
- Check for price discontinuities
- Flag extreme slope values (potential data errors)

---

## 10. Risk Considerations

### 10.1 Strategy Risks

**Trend Breakdown:**
- Clean trends (high R²) can break suddenly
- Regime shifts can cause rapid reversals
- Solution: Monitor R² during holding period, consider early exits

**Curve-Fitting:**
- Linear regression always finds a "best fit" line
- Even random data will have some slope and R²
- Solution: Use p-value filtering, require minimum R² threshold

**Overfitting to Past:**
- Trendlines are backward-looking
- Past trends don't guarantee future trends
- Solution: Combine with other factors, use out-of-sample testing

**Regime Dependency:**
- Works best in trending markets (high R² regime)
- May underperform in choppy/range-bound markets (low R² regime)
- Solution: Regime-adaptive weighting, adjust exposure based on market R²

**Momentum Crashes:**
- Momentum strategies can experience sudden, sharp reversals
- "Momentum crashes" documented in academic literature
- Solution: Position limits, stop losses (optional), diversification

### 10.2 Implementation Risks

**Computational Cost:**
- Rolling linear regression is computationally intensive
- Running for many coins daily may be slow
- Solution: Optimize code, vectorization, use `scipy.stats.linregress`, cache results

**Normalization Sensitivity:**
- Slope normalization critical for comparability
- Different normalization methods can give different rankings
- Solution: Test sensitivity, use standard approach (% per day annualized)

**R² Interpretation:**
- R² can be high even for non-linear trends if they're smooth
- Linear model may not capture non-linear patterns
- Solution: Acceptable limitation, linear trends are most tradeable

**Transaction Costs:**
- Frequent rebalancing = high fees
- Solution: Longer rebalance periods (7-14 days), partial rebalancing

**Slippage:**
- Strong trends may have momentum → higher slippage
- Solution: VWAP execution, realistic slippage assumptions

---

## 11. Expected Insights

### 11.1 Key Questions

**1. Does trend quality (R²) matter?**
- Do high R² trends outperform low R² trends?
- Is R² × slope better than slope alone?
- What's the optimal R² threshold?

**2. What's the optimal trendline window?**
- 14-day, 30-day, 60-day, or 90-day?
- Does shorter window = more reactive = better returns?
- Trade-off between responsiveness and stability

**3. How does trendline factor correlate with other factors?**
- Trendline vs. momentum factor?
- Trendline vs. beta factor?
- Trendline vs. volatility factor?
- Is this an independent alpha source?

**4. Does market regime matter?**
- Bull markets: Strong uptrends persist?
- Bear markets: Strong downtrends persist?
- High vol: R² spreads wider?
- Low vol: R² less predictive?

**5. Is slope or R² more important?**
- Compare slope-only vs. R²-only vs. combined
- Which metric drives returns?
- Is R² just a noise filter or does it add alpha?

**6. What's the distribution of R² in crypto?**
- How many coins have high R² (clean trends)?
- Does R² change over time (regime shifts)?
- Are certain coin types more likely to have clean trends?

### 11.2 Success Criteria

**Minimum Viable Results:**
- **Sharpe Ratio**: > 0.8
- **Maximum Drawdown**: < 30%
- **Win Rate**: > 50%
- **Market Correlation**: < 0.5 (for market neutral)
- **R² Advantage**: R²-weighted outperforms slope-only

**Stretch Goals:**
- **Sharpe Ratio**: > 1.5
- **Maximum Drawdown**: < 20%
- **Calmar Ratio**: > 0.8
- **Alpha vs BTC**: > 15% annualized
- **Positive in All Regimes**: Consistent across bull/bear
- **Low Factor Correlation**: < 0.6 correlation to other factors

### 11.3 Comparison Benchmarks

**Factor Strategies:**
- Momentum factor (pure momentum, no R²)
- Beta factor (systematic risk)
- Volatility factor (realized vol)
- ADF factor (mean reversion vs. trending)

**Market Benchmarks:**
- BTC buy-and-hold
- Equal-weight crypto index
- Market-cap-weight crypto index

---

## 12. Implementation Roadmap

### Phase 1: Core Implementation (Week 1)
- [ ] Create `backtests/scripts/backtest_trendline_factor.py`
- [ ] Implement rolling linear regression function (`calculate_rolling_trendline`)
- [ ] Implement slope normalization (`calculate_normalized_slope`)
- [ ] Implement trendline score calculation (multiplicative method first)
- [ ] Implement quintile ranking and selection
- [ ] Add equal-weight portfolio construction
- [ ] Validate no-lookahead bias (use `.shift(-1)`)
- [ ] Run baseline backtest: Long Uptrends, Short Downtrends

### Phase 2: Testing & Validation (Week 1)
- [ ] Validate trendline calculations (manual spot checks)
- [ ] Check slope normalization (verify comparability across coins)
- [ ] Verify R² values (reasonable distribution)
- [ ] Check for data quality issues
- [ ] Verify performance metrics calculations
- [ ] Test on different time periods
- [ ] Analyze R² and slope distributions across coins

### Phase 3: Strategy Variants (Week 2)
- [ ] Implement all 6+ strategy variants
- [ ] Add risk parity weighting option
- [ ] Add score-weighted and R²-weighted methods
- [ ] Test different score methods (multiplicative, additive, filtered)
- [ ] Test different rebalancing frequencies
- [ ] Test different trendline windows (14d, 30d, 60d, 90d)
- [ ] Compare strategy performance

### Phase 4: Analysis & Documentation (Week 2)
- [ ] Run all strategy variants
- [ ] Compare slope-only vs. R²-weighted vs. combined
- [ ] Calculate correlation to BTC
- [ ] Compare to other factor strategies
- [ ] Regime analysis (bull/bear, high/low vol, high/low R²)
- [ ] Generate performance visualizations
- [ ] Document findings and recommendations

### Phase 5: Enhancements (Future)
- [ ] Add p-value filtering option
- [ ] Implement adaptive R² threshold (regime-dependent)
- [ ] Add trend breakdown detection (early exit logic)
- [ ] Test non-linear trendlines (polynomial, exponential)
- [ ] Multi-factor integration (combine with beta, momentum, etc.)
- [ ] Portfolio-level R² monitoring (aggregate trend quality)

---

## 13. Integration with Existing System

### 13.1 Code Reuse

**Existing Utilities:**
- `backtests/scripts/backtest_beta_factor.py` - Template structure
- `backtests/scripts/backtest_volatility_factor.py` - Quintile ranking logic
- `backtests/scripts/backtest_adf_factor.py` - Time series analysis approach
- `signals/calc_vola.py` - Volatility calculation (for risk parity)
- `signals/calc_weights.py` - Risk parity weight calculation

**New Utility Functions:**
- `signals/calc_trendline.py` - Trendline calculation (reusable)
- Could be used by other strategies or signals

**Data Integration:**
- Use existing: `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- Same CSV format and naming conventions
- Store outputs in: `backtests/results/`

### 13.2 Comparison Framework

**Run all factors on same time period:**
```bash
# Beta factor
python3 backtests/scripts/backtest_beta_factor.py --start-date 2021-01-01

# Volatility factor
python3 backtests/scripts/backtest_volatility_factor.py --start-date 2021-01-01

# ADF factor
python3 backtests/scripts/backtest_adf_factor.py --start-date 2021-01-01

# Trendline factor (new)
python3 backtests/scripts/backtest_trendline_factor.py --start-date 2021-01-01
```

**Calculate factor correlation matrix:**
- Correlation of daily returns across factors
- Identify diversification opportunities
- Build multi-factor portfolio

---

## 14. Academic References

### 14.1 Momentum and Trend Following

**Momentum in Finance:**
- Jegadeesh, N., & Titman, S. (1993). "Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency". *Journal of Finance*.
- Moskowitz, T. J., Ooi, Y. H., & Pedersen, L. H. (2012). "Time Series Momentum". *Journal of Financial Economics*.

**Trend Following:**
- Hurst, B., Ooi, Y. H., & Pedersen, L. H. (2017). "A Century of Evidence on Trend-Following Investing". *Journal of Portfolio Management*.
- Faber, M. T. (2007). "A Quantitative Approach to Tactical Asset Allocation". *Journal of Wealth Management*.

### 14.2 Technical Analysis

**Trendline Analysis:**
- Lo, A. W., Mamaysky, H., & Wang, J. (2000). "Foundations of Technical Analysis: Computational Algorithms, Statistical Inference, and Empirical Implementation". *Journal of Finance*.
- Brock, W., Lakonishok, J., & LeBaron, B. (1992). "Simple Technical Trading Rules and the Stochastic Properties of Stock Returns". *Journal of Finance*.

**R² and Trend Quality:**
- Treynor, J. L., & Mazuy, K. (1966). "Can Mutual Funds Outguess the Market?". *Harvard Business Review*.
- Sharpe, W. F. (1966). "Mutual Fund Performance". *Journal of Business*.

### 14.3 Crypto-Specific

**Momentum in Crypto:**
- Liu, Y., Tsyvinski, A., & Wu, X. (2022). "Common Risk Factors in Cryptocurrency". *Journal of Finance*.
- Hu, A., Parlour, C. A., & Rajan, U. (2019). "Cryptocurrencies: Stylized Facts on a New Investible Instrument". *Financial Management*.

**Crypto Trends:**
- Corbet, S., Lucey, B., & Yarovaya, L. (2018). "Datestamping the Bitcoin and Ethereum Bubbles". *Finance Research Letters*.
- Bouri, E., Gupta, R., & Roubaud, D. (2019). "Herding Behaviour in Cryptocurrencies". *Finance Research Letters*.

---

## 15. Example Usage

### Basic Backtest
```bash
# Run Long Uptrends, Short Downtrends (baseline)
python3 backtests/scripts/backtest_trendline_factor.py \
  --strategy long_uptrend_short_downtrend \
  --trendline-window 30 \
  --score-method multiplicative \
  --rebalance-days 7
```

### Test Slope-Only Momentum
```bash
python3 backtests/scripts/backtest_trendline_factor.py \
  --strategy slope_only_momentum \
  --trendline-window 30 \
  --score-method slope_only \
  --rebalance-days 7
```

### Test R²-Filtered Conservative
```bash
python3 backtests/scripts/backtest_trendline_factor.py \
  --strategy r2_filtered_conservative \
  --trendline-window 30 \
  --score-method filtered \
  --r2-threshold 0.5 \
  --rebalance-days 7
```

### Parameter Sensitivity: Test Different Windows
```bash
# Test different trendline windows
for window in 14 30 60 90; do
  python3 backtests/scripts/backtest_trendline_factor.py \
    --strategy long_uptrend_short_downtrend \
    --trendline-window $window \
    --score-method multiplicative \
    --output-prefix backtests/results/trendline_window_${window}
done
```

### Parameter Sensitivity: Test Different Score Methods
```bash
# Test different score methods
for method in multiplicative slope_only r2_only filtered; do
  python3 backtests/scripts/backtest_trendline_factor.py \
    --strategy long_uptrend_short_downtrend \
    --trendline-window 30 \
    --score-method $method \
    --output-prefix backtests/results/trendline_method_${method}
done
```

### Advanced Configuration
```bash
python3 backtests/scripts/backtest_trendline_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy long_uptrend_short_downtrend \
  --trendline-window 30 \
  --score-method multiplicative \
  --r2-threshold 0.3 \
  --pvalue-threshold 0.05 \
  --volatility-window 30 \
  --rebalance-days 7 \
  --long-percentile 80 \
  --short-percentile 20 \
  --weighting-method risk_parity \
  --long-allocation 0.5 \
  --short-allocation 0.5 \
  --min-volume 10000000 \
  --min-market-cap 100000000 \
  --initial-capital 10000 \
  --leverage 1.0 \
  --start-date 2021-01-01 \
  --end-date 2025-10-28 \
  --output-prefix backtests/results/trendline_factor_custom
```

---

## 16. Next Steps

1. **Review Specification**: Validate approach, assumptions, and methodology
2. **Implement Core Script**: Build `backtest_trendline_factor.py` with linear regression
3. **Run Initial Backtest**: Test long uptrends, short downtrends strategy
4. **Analyze Distributions**: Understand cross-section of slopes and R² values
5. **Test Hypothesis**: Does R² improve momentum strategies?
6. **Compare Methods**: Multiplicative vs. slope-only vs. filtered
7. **Parameter Optimization**: Find optimal window and score method
8. **Factor Correlation**: Compare to momentum, beta, volatility factors
9. **Multi-Factor Integration**: Combine with existing factors

---

**Document Owner:** Research Team  
**Last Updated:** 2025-10-28  
**Status:** Specification - Ready for Implementation  
**Next Step:** Implement Phase 1 (Core backtest script)

---

**Disclaimer:** This backtest is for research purposes only. Past performance does not guarantee future results. Cryptocurrency trading involves substantial risk of loss. Trendlines are backward-looking and may not predict future price movements. Linear regression assumes linear relationships which may not hold in non-linear markets. Always conduct thorough research and risk management before deploying capital.
