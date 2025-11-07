# Rate of Change vs Funding Factor Specification

**Version:** 1.0  
**Date:** 2025-10-28  
**Status:** Specification - Ready for Implementation

---

## 1. Executive Summary

This specification outlines a quantitative trading strategy based on comparing **Rate of Change (RoC)** in prices versus **cumulative funding rates** over matched time periods. The core hypothesis tests whether the relationship between price momentum and funding costs contains predictive information for cryptocurrency returns.

### Key Objectives
1. Calculate rolling Rate of Change (RoC) for all cryptocurrencies over period N
2. Calculate cumulative funding rates over the same period N
3. Compare RoC vs funding to identify inefficient pricing
4. Test hypothesis: RoC should outpace funding in efficient markets
5. Construct long/short portfolios based on RoC-funding spread

### Strategy Overview
- **Factor**: RoC - Funding Spread (adjusted for same period)
- **Universe**: All liquid cryptocurrencies with perpetual futures
- **Rebalancing**: Weekly (configurable)
- **Market Neutrality**: Dollar-neutral long/short construction
- **Risk Management**: Equal weight or risk parity weighting

---

## 2. Strategy Description

### 2.1 Core Concept

**Rate of Change (RoC)** measures price momentum:
\[ \text{RoC}_t = \frac{P_t - P_{t-N}}{P_{t-N}} = \frac{P_t}{P_{t-N}} - 1 \]

**Cumulative Funding Rate** measures the cost/gain of holding a perpetual position:
\[ \text{CumFunding}_t = \sum_{i=t-N}^{t} \text{FundingRate}_i \]

**RoC-Funding Spread** (the factor):
\[ \text{Spread}_t = \text{RoC}_t - \text{CumFunding}_t \]

Where:
- \( P_t \) = Price at time t
- \( P_{t-N} \) = Price N periods ago
- \( \text{FundingRate}_i \) = Funding rate at time i (typically 8-hour periods)
- **Positive Spread** → Price gains exceed funding costs (momentum underpriced)
- **Negative Spread** → Funding costs exceed price gains (market overheated)

### 2.2 Strategy Hypothesis

#### Core Theory: Efficient Carry-Momentum Relationship

In efficient perpetual futures markets, **price momentum should exceed funding costs** for long positions to be rational. When this relationship breaks down, it signals trading opportunities:

**Hypothesis A: Momentum Dominance (Positive Spread)**
- **Signal**: RoC >> Cumulative Funding (large positive spread)
- **Interpretation**: Strong price momentum not reflected in funding → Momentum underpriced
- **Action**: **LONG** - Market hasn't fully priced in the trend
- **Expected**: Continued upward momentum, funding will catch up

**Hypothesis B: Funding Overload (Negative Spread)**
- **Signal**: RoC << Cumulative Funding (large negative spread)
- **Interpretation**: High funding costs with weak/negative price action → Overheated
- **Action**: **SHORT** - Longs paying premium despite poor performance
- **Expected**: Mean reversion, funding will collapse or price will fall further

**Hypothesis C: Efficient Pricing (Near-Zero Spread)**
- **Signal**: RoC ≈ Cumulative Funding (spread near zero)
- **Interpretation**: Fair value, no mispricing
- **Action**: **NEUTRAL** - No trading edge

### 2.3 Economic Intuition

**Why RoC Should Outpace Funding:**

1. **Rational Long Position**: If you're long a perpetual:
   - You pay funding rates (if positive)
   - You capture price appreciation (if any)
   - **Break-even**: Price gains must cover funding costs
   - **Profit**: RoC must exceed cumulative funding

2. **Market Signals**:
   - **High Funding + High RoC**: Normal bull market (both justified)
   - **High Funding + Low RoC**: Red flag (expensive to be long, but price not moving)
   - **Low Funding + High RoC**: Opportunity (cheap carry, strong momentum)
   - **Low Funding + Low RoC**: Neutral (low interest, low performance)

**Trading Edges:**

1. **Momentum Underpriced (Long Signal)**:
   - Price rising 30% over 30 days
   - But cumulative funding only 5%
   - **Spread = +25%** → Strong long signal
   - Market hasn't fully recognized the trend

2. **Funding Overload (Short Signal)**:
   - Price flat or down -5% over 30 days
   - But cumulative funding at +15%
   - **Spread = -20%** → Strong short signal
   - Longs bleeding funding costs, likely capitulation soon

3. **Mean Reversion**:
   - Extreme spreads should revert to mean
   - Either funding adjusts or price adjusts
   - Strategy captures this convergence

### 2.4 Crypto Market Application

**Why this works in crypto:**

1. **Funding Rate Dynamics**:
   - Crypto perpetuals have 8-hour funding cycles
   - Funding can be very high (10-50% annualized)
   - Funding reacts to positioning, not just price
   - Creates disconnect between funding and spot momentum

2. **Behavioral Biases**:
   - **FOMO Longs**: Pay high funding despite weak momentum
   - **Stubbornness**: Hold losing positions, bleed funding
   - **Momentum Chasing**: Late entry = high funding + price reversal

3. **Market Inefficiencies**:
   - Funding rates can stay elevated even as momentum slows
   - Price can surge while funding remains low (underpriced)
   - Temporary dislocations create trading opportunities

4. **Leverage Effects**:
   - High leverage amplifies funding costs
   - Forced liquidations when funding eats into margin
   - Cascading effects when RoC-funding spread extreme

### 2.5 Calculation Methodology

#### Step 1: Calculate Rolling RoC

```python
def calculate_roc(prices, window=30):
    """
    Calculate rolling Rate of Change
    
    Parameters:
    - prices: Series of daily close prices
    - window: Lookback period in days (default: 30)
    
    Returns:
    - Series of RoC values (percentage returns)
    """
    # Simple percentage return over window
    roc = (prices / prices.shift(window)) - 1
    
    # Convert to percentage
    roc_pct = roc * 100
    
    return roc_pct
```

#### Step 2: Calculate Cumulative Funding

```python
def calculate_cumulative_funding(funding_rates, window=30):
    """
    Calculate cumulative funding rate over rolling window
    
    Parameters:
    - funding_rates: Series of funding rates (in %, e.g., 0.01% per 8h)
    - window: Lookback period in days (default: 30)
    
    Returns:
    - Series of cumulative funding over window (in %)
    
    Notes:
    - Funding typically happens every 8 hours (3x per day)
    - For daily data, use daily average funding rate
    - Cumulative = sum of all funding over window
    """
    # Rolling sum of funding rates
    cum_funding = funding_rates.rolling(window).sum()
    
    return cum_funding
```

#### Step 3: Calculate RoC-Funding Spread

```python
def calculate_roc_funding_spread(prices, funding_rates, window=30):
    """
    Calculate RoC minus cumulative funding spread
    
    Parameters:
    - prices: Series of daily close prices
    - funding_rates: Series of daily funding rates (%)
    - window: Lookback period in days (default: 30)
    
    Returns:
    - Series of RoC-Funding spread values (in %)
    """
    # Calculate RoC
    roc_pct = calculate_roc(prices, window)
    
    # Calculate cumulative funding
    cum_funding = calculate_cumulative_funding(funding_rates, window)
    
    # Calculate spread
    spread = roc_pct - cum_funding
    
    return spread
```

#### Step 4: Adjust for Annualization (Optional)

```python
def annualize_spread(spread, window=30):
    """
    Annualize the spread for comparability
    
    Parameters:
    - spread: RoC-Funding spread over window (%)
    - window: Period in days
    
    Returns:
    - Annualized spread (%)
    """
    # Annualize: (1 + spread/100)^(365/window) - 1
    annualized = ((1 + spread/100) ** (365/window) - 1) * 100
    
    return annualized
```

### 2.6 Calculation Parameters

**Default Parameters:**
- **Lookback Window**: 30 days (~1 month)
  - Captures medium-term momentum
  - Sufficient funding data (90 funding periods @ 8h)
- **Funding Frequency**: Daily average (aggregate 3x 8-hour funding)
- **Minimum Data**: 90% of window must have valid data
- **Price Source**: Daily close prices (spot or perpetual mark)
- **Funding Source**: Coinalyze aggregated funding rates (.A suffix)

**Parameter Variations to Test:**
- **7-day spread**: Short-term momentum vs funding
- **14-day spread**: Medium-short term
- **30-day spread**: Baseline
- **60-day spread**: Medium-long term
- **90-day spread**: Long-term trend vs funding

---

## 3. Signal Generation

### 3.1 Daily Signal Process

**Step 1: Calculate Spreads for All Coins**
```python
# For each coin:
roc_30d = calculate_roc(coin_prices, window=30)
cum_funding_30d = calculate_cumulative_funding(coin_funding_rates, window=30)
spread_30d = roc_30d - cum_funding_30d
```

**Step 2: Filter Universe**
```python
# Apply liquidity and data quality filters
valid_coins = coins[
    (coins['volume_30d_avg'] > MIN_VOLUME) &
    (coins['market_cap'] > MIN_MARKET_CAP) &
    (coins['spread'].notna()) &
    (coins['has_perpetual'] == True) &  # Must have funding data
    (coins['data_quality'] > 0.9)  # 90% data availability
]
```

**Step 3: Rank by RoC-Funding Spread**
```python
# Rank from low spread to high spread
# Rank 1 = most negative spread (funding overload - short signal)
# Rank N = most positive spread (momentum dominance - long signal)
spread_rank = valid_coins['spread'].rank(ascending=True)
```

**Step 4: Generate Signals**
```python
# Strategy: Long/Short Extremes
# Long: Top quintile (highest spread = RoC >> Funding)
# Short: Bottom quintile (lowest spread = RoC << Funding)

if spread_rank >= 80th_percentile:
    signal = LONG  # Strong momentum, low funding costs
elif spread_rank <= 20th_percentile:
    signal = SHORT  # Weak momentum, high funding costs
else:
    signal = NEUTRAL
```

### 3.2 Entry Rules

**Rebalancing Schedule:**
- **Frequency**: Every 7 days (weekly, default)
- **Day**: Monday close (configurable)
- **Execution**: Next-day execution (avoid lookahead bias)

**Position Selection:**
- **Long Bucket**: Top quintile by RoC-Funding spread
- **Short Bucket**: Bottom quintile by RoC-Funding spread
- **Max Positions**: 10-20 longs + 10-20 shorts (configurable)
- **Min Data Coverage**: At least 90% valid data in window

**Filters:**
- **Minimum Volume**: 30-day avg volume > $5M (configurable)
- **Minimum Market Cap**: > $50M (configurable)
- **Perpetual Available**: Must have funding rate data
- **Data Quality**: At least 90% valid price & funding data in window
- **Exclude Stablecoins**: Remove USDT, USDC, DAI, etc.

**Position Sizing:**
- **Equal Weight**: Default, 1/N allocation per position
- **Risk Parity**: Weight by inverse volatility
- **Spread-Weighted**: Weight by absolute spread magnitude (optional)

### 3.3 Exit Rules

**Time-Based Exit:**
- Hold positions until next rebalance date
- No intra-period adjustments (except forced exits)

**Forced Exit Conditions:**
- Coin drops below minimum volume threshold
- Coin delisted from exchange
- Funding data becomes unavailable
- Data quality deteriorates (>10% missing)

**No Stop Loss:**
- Hold through drawdowns until rebalance
- Strategy assumes spreads mean-revert

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
- No estimation error
- Easy to implement

**Cons:**
- Doesn't account for spread magnitude
- Ignores volatility differences

#### Method 2: Spread-Weighted
```python
# Weight by absolute spread magnitude
# Stronger signals get higher weights

abs_spread = np.abs(coin_spread)
weights = (abs_spread / abs_spread.sum()) * allocation
```

**Pros:**
- Captures conviction (larger spread = higher weight)
- Better Sharpe if spread magnitude is predictive

**Cons:**
- Concentrates risk in extreme spreads
- May overweight outliers

#### Method 3: Risk Parity
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
- Ignores spread magnitude

### 4.2 Portfolio Allocation

**Default Configuration:**
- **Long Allocation**: 50% of capital
- **Short Allocation**: 50% of capital
- **Cash**: 0% (fully invested, market neutral)
- **Leverage**: 1.0x (no leverage by default)

**Alternative Configurations:**
- **Long-Only**: 100% long (top quintile), 0% short
- **Short-Only**: 0% long, 100% short (bottom quintile)
- **Long-Biased**: 70% long, 30% short
- **Levered Neutral**: 100% long, 100% short (2x gross)

### 4.3 Rebalancing Logic

**Full Rebalancing (Default):**
```python
# On rebalance date:
1. Calculate new RoC and cumulative funding for all coins
2. Calculate RoC-Funding spread
3. Rank all coins by spread
4. Select new long/short quintiles
5. Exit all old positions
6. Enter new positions with target weights
```

---

## 5. Backtest Implementation

### 5.1 File Structure

**Main Script:** `backtests/scripts/backtest_roc_funding_factor.py`

**Purpose:** Backtest engine for RoC vs Funding spread strategies

**Output Directory:** `backtests/results/`

### 5.2 Command-Line Interface

```bash
python3 backtests/scripts/backtest_roc_funding_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --funding-data data/raw/funding_rates_daily.csv \
  --strategy long_high_short_low_spread \
  --window 30 \
  --rebalance-days 7 \
  --weighting-method equal_weight \
  --long-allocation 0.5 \
  --short-allocation 0.5 \
  --start-date 2020-01-01 \
  --end-date 2025-10-28 \
  --output-prefix backtest_roc_funding_factor
```

### 5.3 Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--price-data` | (required) | Path to OHLCV CSV file |
| `--funding-data` | (required) | Path to funding rates CSV file |
| `--strategy` | `long_high_short_low_spread` | Strategy variant |
| `--window` | 30 | RoC and funding lookback window (days) |
| `--rebalance-days` | 7 | Rebalance frequency (days) |
| `--num-quintiles` | 5 | Number of spread buckets |
| `--long-percentile` | 80 | Percentile threshold for long (top 20%) |
| `--short-percentile` | 20 | Percentile threshold for short (bottom 20%) |
| `--weighting-method` | `equal_weight` | Weighting: `equal_weight`, `spread_weighted`, `risk_parity` |
| `--min-volume` | 5000000 | Minimum 30d avg volume ($) |
| `--min-market-cap` | 50000000 | Minimum market cap ($) |
| `--min-data-coverage` | 0.9 | Minimum data availability (90%) |
| `--initial-capital` | 10000 | Starting capital (USD) |
| `--leverage` | 1.0 | Leverage multiplier |
| `--long-allocation` | 0.5 | Long side allocation (50%) |
| `--short-allocation` | 0.5 | Short side allocation (50%) |
| `--start-date` | None | Backtest start (YYYY-MM-DD) |
| `--end-date` | None | Backtest end (YYYY-MM-DD) |
| `--output-prefix` | `backtest_roc_funding_factor` | Output file prefix |

### 5.4 Output Files

#### 1. Portfolio Values
**File:** `backtest_roc_funding_factor_portfolio_values.csv`

```csv
date,portfolio_value,cash,long_exposure,short_exposure,net_exposure,gross_exposure,num_longs,num_shorts,avg_spread_long,avg_spread_short
2020-01-01,10000.00,0.00,5000.00,-5000.00,0.00,10000.00,10,10,15.25,-8.50
2020-01-08,10250.50,0.00,5125.25,-5125.25,0.00,10250.50,10,10,14.80,-9.20
...
```

#### 2. Trade Log
**File:** `backtest_roc_funding_factor_trades.csv`

```csv
date,symbol,signal,roc_pct,cum_funding_pct,spread_pct,spread_rank,percentile,weight,position_size,volatility_30d
2020-01-08,BTC,LONG,25.50,5.20,20.30,48,98.0,0.11,550.00,0.45
2020-01-08,ETH,LONG,32.10,8.50,23.60,50,100.0,0.10,500.00,0.62
2020-01-08,DOGE,SHORT,-5.20,15.80,-21.00,1,2.0,0.08,-400.00,1.85
...
```

#### 3. Performance Metrics
**File:** `backtest_roc_funding_factor_metrics.csv`

```csv
metric,value
initial_capital,10000.00
final_value,18245.75
total_return,0.8246
annualized_return,0.3256
annualized_volatility,0.2142
sharpe_ratio,1.52
sortino_ratio,2.15
max_drawdown,-0.2234
calmar_ratio,1.46
win_rate,0.5923
avg_long_positions,9.6
avg_short_positions,9.8
avg_spread_long,16.25
avg_spread_short,-11.40
total_rebalances,78
trading_days,547
```

#### 4. Spread Time Series
**File:** `backtest_roc_funding_factor_spread_timeseries.csv`

```csv
date,symbol,roc_pct,cum_funding_pct,spread_pct,spread_rank,percentile,price,funding_30d_avg
2020-01-08,BTC,25.50,5.20,20.30,48,98.0,8500.00,0.173
2020-01-08,ETH,32.10,8.50,23.60,50,100.0,155.00,0.283
...
```

#### 5. Strategy Info
**File:** `backtest_roc_funding_factor_strategy_info.csv`

```csv
strategy,window,rebalance_days,weighting_method,long_symbols,short_symbols,avg_spread_long,avg_spread_short
long_high_short_low_spread,30,7,equal_weight,"BTC,ETH,SOL,...","DOGE,SHIB,APE,...",16.25,-11.40
```

---

## 6. Strategy Variants

### 6.1 Long High, Short Low Spread - Primary Strategy
**Name:** `long_high_short_low_spread`

**Configuration:**
- Long: Top quintile (highest spread = RoC >> Funding)
- Short: Bottom quintile (lowest spread = RoC << Funding)
- Allocation: 50% long, 50% short
- Market Neutral: Yes

**Hypothesis:** High spread coins outperform low spread coins

**Expected Outcome:**
- Captures momentum underpricing and funding overload
- Low correlation to market
- Mean reversion in spreads

### 6.2 Long High Spread Only
**Name:** `long_high_spread`

**Configuration:**
- Long: Top quintile (highest spread)
- Short: None (50% cash)
- Allocation: 50% long, 0% short
- Market Neutral: No

**Hypothesis:** Strong momentum with low funding costs

**Expected Outcome:**
- Captures momentum continuation
- Higher volatility
- Positive correlation to market

### 6.3 Short Low Spread Only
**Name:** `short_low_spread`

**Configuration:**
- Long: None (50% cash)
- Short: Bottom quintile (lowest spread)
- Allocation: 0% long, 50% short
- Market Neutral: No

**Hypothesis:** Weak momentum with high funding bleeds

**Expected Outcome:**
- Captures funding-induced capitulation
- Negative returns in bull markets
- Outperforms in bear markets

### 6.4 Long Low, Short High Spread (Contrarian)
**Name:** `long_low_short_high_spread`

**Configuration:**
- Long: Bottom quintile (lowest spread = potential mean reversion)
- Short: Top quintile (highest spread = potential exhaustion)
- Allocation: 50% long, 50% short
- Market Neutral: Yes

**Hypothesis:** Spreads mean-revert (contrarian bet)

**Expected Outcome:**
- Captures extreme spread reversions
- High volatility
- May underperform if trends persist

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

### 7.3 Spread-Specific Metrics
- **Average Spread Long**: Mean spread of long positions (%)
- **Average Spread Short**: Mean spread of short positions (%)
- **Spread Dispersion**: Std of spreads across universe
- **Spread Persistence**: Correlation of spreads across periods
- **Spread Mean Reversion**: Half-life of spread decay

### 7.4 Trading Metrics
- **Win Rate**: % of profitable rebalancing periods
- **Average Turnover**: % of portfolio traded per rebalance
- **Number of Rebalances**: Total rebalancing events
- **Avg Long Positions**: Average number of long positions
- **Avg Short Positions**: Average number of short positions

### 7.5 Regime Analysis
- **Bull Market Performance**: Returns when BTC > 200d MA
- **Bear Market Performance**: Returns when BTC < 200d MA
- **High Funding Regime**: Returns when avg funding > median
- **Low Funding Regime**: Returns when avg funding < median

---

## 8. No-Lookahead Bias Prevention

**Critical Rule:** Signals on day T use returns from day T+1

### 8.1 Implementation

```python
# Day T: Calculate RoC using prices up to day T
roc_t = calculate_roc(coin_prices.loc[:t], window=30)

# Day T: Calculate cumulative funding using data up to day T
cum_funding_t = calculate_cumulative_funding(
    coin_funding_rates.loc[:t], 
    window=30
)

# Day T: Calculate spread and rank
spread_t = roc_t - cum_funding_t
signals_t = generate_signals(spread_t)

# Day T+1: Apply signals using next day's returns
returns_t1 = price_data.loc[t+1, 'return']
pnl_t1 = signals_t * returns_t1  # Use .shift(-1) for proper alignment
```

### 8.2 Key Checks
- ✅ RoC calculated using only past prices (no future data)
- ✅ Funding calculated using only past rates (no future data)
- ✅ Signals generated at close of day T
- ✅ Positions executed at open of day T+1
- ✅ Returns from day T+1 used for P&L
- ✅ No future prices or funding rates used

---

## 9. Data Requirements

### 9.1 Input Data

**Price Data Source:** `data/raw/combined_coinbase_coinmarketcap_daily.csv`

**Required Price Fields:**
- `date`: Trading date (YYYY-MM-DD)
- `symbol`: Coin ticker (BTC, ETH, etc.)
- `close`: Closing price
- `volume`: Trading volume (USD)
- `market_cap`: Market capitalization (USD)

**Funding Data Source:** Coinalyze API or cached CSV

**Required Funding Fields:**
- `date`: Trading date (YYYY-MM-DD)
- `symbol`: Coin ticker matching price data
- `funding_rate`: Daily average funding rate (%)
- `funding_rate_8h`: 8-hour funding rate (for daily aggregation)

**Minimum History:**
- **Per Coin**: 60 days minimum
  - 30 days for RoC and funding calculation
  - 30 days for backtest stability
- **Universe**: At least 20 coins with both price & funding data

### 9.2 Data Quality Filters

**Volume Filter:**
- 30-day average volume > $5M (default)
- Ensures liquidity for execution

**Market Cap Filter:**
- Market cap > $50M (default)
- Excludes micro-caps with poor data

**Data Completeness:**
- At least 90% of data points in window
- Handles missing data: skip coin for that period

**Funding Data Availability:**
- Must have perpetual futures with funding rates
- Exclude coins without funding data

**Outlier Detection:**
- Remove days with returns > ±50% (data errors)
- Cap funding rates at ±1% per 8h (extreme outliers)

### 9.3 Funding Data Integration

**Data Source:** Coinalyze Aggregated Funding Rates

```python
from execution.get_carry import fetch_coinalyze_aggregated_funding_rates

# Fetch aggregated market-wide funding rates
df_funding = fetch_coinalyze_aggregated_funding_rates(
    universe_symbols=['BTC', 'ETH', 'SOL', ...]
)

# Expected columns: base, quote, funding_rate, funding_rate_pct, coinalyze_symbol
# Convert 8-hour rates to daily average if needed
```

**Daily Aggregation:**
- Funding typically updates every 8 hours (3x per day)
- For daily analysis: use daily average or daily sum
- Ensure consistency in units (% per day vs % per 8h)

---

## 10. Risk Considerations

### 10.1 Strategy Risks

**Funding Data Quality:**
- Funding rates may have gaps or errors
- Different exchanges have different rates (use aggregated)
- Solution: Use Coinalyze aggregated data, handle missing gracefully

**Spread Persistence:**
- Spreads may not mean-revert quickly
- Extreme spreads can persist (trending markets)
- Solution: Regular rebalancing, test multiple windows

**Regime Dependency:**
- Strategy may work differently in bull vs bear markets
- High volatility may compress spreads
- Solution: Test across multiple market cycles

**Leverage Effects:**
- Actual funding costs depend on leverage
- Our calculation assumes 1x leverage
- Solution: Adjust for leverage if needed

**Transaction Costs:**
- Frequent rebalancing incurs fees
- Funding is collected continuously, RoC is point-to-point
- Solution: Test longer rebalance periods

### 10.2 Implementation Risks

**Funding Data Latency:**
- Real-time funding may lag
- Historical funding may be revised
- Solution: Use cached aggregated data with proper timestamps

**Execution Risk:**
- Slippage on rebalancing
- Market impact for large positions
- Solution: VWAP execution, split orders

**Short Availability:**
- Not all coins available to short
- Borrow costs additional to funding
- Solution: Use perpetual futures, factor in total costs

---

## 11. Expected Insights

### 11.1 Key Questions

**1. Does RoC-Funding spread predict returns?**
- Do high spread coins outperform low spread coins?
- Is the effect statistically significant?
- How large is the alpha?

**2. What is the optimal window?**
- 7d, 14d, 30d, 60d, or 90d?
- Short vs medium vs long-term spreads?
- Which captures best predictive signal?

**3. How do spreads behave over time?**
- Do they mean-revert or trend?
- Half-life of spread decay?
- Persistence across periods?

**4. Does spread vary by coin type?**
- DeFi vs L1 vs Meme coins?
- Large cap vs small cap?
- Different spread characteristics?

**5. How does this factor correlate with others?**
- RoC-Funding vs momentum factor?
- RoC-Funding vs beta factor?
- Independent alpha source?

**6. Does market regime matter?**
- Bull markets: Does momentum dominate?
- Bear markets: Does funding overload matter?
- High vol: Do spreads widen?

### 11.2 Success Criteria

**Minimum Viable Results:**
- **Sharpe Ratio**: > 0.8
- **Maximum Drawdown**: < 30%
- **Win Rate**: > 50%
- **Market Correlation**: < 0.5 (for market neutral)
- **Spread Significance**: t-stat > 2.0 for long-short spread

**Stretch Goals:**
- **Sharpe Ratio**: > 1.5
- **Maximum Drawdown**: < 20%
- **Calmar Ratio**: > 0.7
- **Alpha vs BTC**: > 15% annualized
- **Positive in All Regimes**: Consistent performance

---

## 12. Implementation Roadmap

### Phase 1: Core Implementation (Week 1)
- [ ] Create `backtests/scripts/backtest_roc_funding_factor.py`
- [ ] Implement RoC calculation function
- [ ] Implement cumulative funding calculation function
- [ ] Implement spread calculation and ranking
- [ ] Add equal-weight portfolio construction
- [ ] Validate no-lookahead bias (use `.shift(-1)`)
- [ ] Integrate with Coinalyze funding data

### Phase 2: Testing & Validation (Week 1)
- [ ] Validate RoC calculations (spot checks)
- [ ] Validate funding aggregation (cross-check with raw data)
- [ ] Check for data quality issues
- [ ] Verify performance metrics calculations
- [ ] Test on different time periods
- [ ] Analyze spread distribution across coins

### Phase 3: Strategy Variants (Week 2)
- [ ] Implement all 4 strategy variants
- [ ] Add risk parity weighting option
- [ ] Add spread-weighted option
- [ ] Test different windows (7d, 14d, 30d, 60d, 90d)
- [ ] Test different rebalancing frequencies
- [ ] Compare strategy performance

### Phase 4: Analysis & Documentation (Week 2)
- [ ] Run all strategy variants
- [ ] Calculate correlation to BTC and other factors
- [ ] Analyze spread persistence and mean reversion
- [ ] Compare to momentum and carry factors
- [ ] Generate performance visualizations
- [ ] Document findings and recommendations

---

## 13. Integration with Existing System

### 13.1 Code Reuse

**Existing Utilities:**
- `backtests/scripts/backtest_beta_factor.py` - Template structure
- `execution/get_carry.py` - Funding rate fetching (Coinalyze)
- `signals/calc_vola.py` - Volatility calculation (for risk parity)
- `signals/calc_weights.py` - Risk parity weight calculation

**Data Integration:**
- Price: `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- Funding: Coinalyze API (cached) or preprocessed CSV
- Store outputs in: `backtests/results/`

### 13.2 Comparison Framework

**Run against other factors:**
```bash
# Momentum factor (pure RoC)
python3 backtest_momentum_factor.py --window 30

# Carry factor (pure funding)
python3 backtest_carry_factor.py --window 30

# RoC-Funding factor (new)
python3 backtest_roc_funding_factor.py --window 30
```

**Calculate factor correlation matrix:**
- Momentum returns vs RoC-Funding returns
- Carry returns vs RoC-Funding returns
- Identify incremental alpha

---

## 14. Academic References

### 14.1 Momentum & Mean Reversion

**Momentum:**
- Jegadeesh, N., & Titman, S. (1993). "Returns to Buying Winners and Selling Losers". *Journal of Finance*.
- Carhart, M. M. (1997). "On Persistence in Mutual Fund Performance". *Journal of Finance*.

**Mean Reversion:**
- Poterba, J. M., & Summers, L. H. (1988). "Mean Reversion in Stock Prices". *Journal of Financial Economics*.

### 14.2 Carry & Funding Rates

**Carry Trade:**
- Brunnermeier, M. K., Nagel, S., & Pedersen, L. H. (2008). "Carry Trades and Currency Crashes". *NBER Macroeconomics Annual*.

**Crypto Funding:**
- Kozhan, R., & Viswanath-Natraj, G. (2021). "Decentralized Stablecoins and Collateral Risk". *Working Paper*.

### 14.3 Crypto-Specific

**Perpetual Futures:**
- Makarov, I., & Schoar, A. (2020). "Trading and Arbitrage in Cryptocurrency Markets". *Journal of Financial Economics*.

---

## 15. Example Usage

### Basic Backtest
```bash
# Run long high spread, short low spread (baseline)
python3 backtests/scripts/backtest_roc_funding_factor.py \
  --strategy long_high_short_low_spread \
  --window 30 \
  --rebalance-days 7
```

### Test Different Windows
```bash
# Test window sensitivity
for window in 7 14 30 60 90; do
  python3 backtests/scripts/backtest_roc_funding_factor.py \
    --strategy long_high_short_low_spread \
    --window $window \
    --output-prefix backtest_roc_funding_window_${window}
done
```

### Advanced Configuration
```bash
python3 backtests/scripts/backtest_roc_funding_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --funding-data data/raw/funding_rates_daily.csv \
  --strategy long_high_short_low_spread \
  --window 30 \
  --rebalance-days 7 \
  --long-percentile 80 \
  --short-percentile 20 \
  --weighting-method spread_weighted \
  --long-allocation 0.5 \
  --short-allocation 0.5 \
  --min-volume 10000000 \
  --min-market-cap 100000000 \
  --min-data-coverage 0.9 \
  --initial-capital 10000 \
  --leverage 1.0 \
  --start-date 2021-01-01 \
  --end-date 2025-10-28 \
  --output-prefix backtest_roc_funding_custom
```

---

## 16. Next Steps

1. **Review Specification**: Validate approach and assumptions
2. **Prepare Funding Data**: Ensure daily funding rates available (Coinalyze)
3. **Implement Core Script**: Build `backtest_roc_funding_factor.py`
4. **Run Initial Backtest**: Test long high short low spread strategy
5. **Analyze Spread Distribution**: Understand cross-section of spreads
6. **Test Hypothesis**: Does high spread → high returns?
7. **Parameter Optimization**: Find optimal window and rebalance frequency
8. **Compare to Pure Momentum/Carry**: Quantify incremental value

---

**Document Owner:** Research Team  
**Last Updated:** 2025-10-28  
**Status:** Specification - Ready for Implementation  
**Next Step:** Implement Phase 1 (Core backtest script)

---

**Disclaimer:** This backtest is for research purposes only. Past performance does not guarantee future results. Cryptocurrency trading involves substantial risk of loss. Funding rates are subject to change and may not be available for all coins. The relationship between RoC and funding may vary significantly across market regimes. Always conduct thorough research and risk management before deploying capital.
