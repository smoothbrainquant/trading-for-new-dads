# IQR Spread Factor Backtest Specification

**Version:** 1.0  
**Date:** 2025-10-27  
**Status:** Specification - Ready for Implementation

---

## 1. Executive Summary

This specification outlines a quantitative trading strategy based on the **IQR (Interquartile Range) spread** of cryptocurrency returns. The core hypothesis is that the dispersion of returns across the top 100 coins by market cap serves as a market regime indicator that predicts future performance of different market segments (majors vs. small caps).

### Key Objectives
1. Calculate 30-day percentage change for top 100 market cap coins
2. Compute 25th and 75th percentile of these changes
3. Calculate IQR spread = 75th percentile - 25th percentile
4. Test hypothesis: Low spread → bullish market; High spread → potential rollover
5. Analyze returns of majors and small caps conditional on IQR spread levels
6. Construct trading strategies based on IQR spread regimes

### Strategy Overview
- **Factor**: Market-wide return dispersion (IQR spread)
- **Universe**: Top 100 cryptocurrencies by market cap
- **Signal**: IQR spread level (low/medium/high)
- **Application**: Rotate between majors and small caps based on spread regime
- **Rebalancing**: Weekly (configurable)

---

## 2. Strategy Description

### 2.1 Core Concept

**IQR Spread** measures the dispersion of returns across the cryptocurrency market:

\[ \text{IQR Spread}_t = P_{75}(\text{Returns}_{30d}) - P_{25}(\text{Returns}_{30d}) \]

Where:
- \( P_{75} \) = 75th percentile of 30-day returns across top 100 coins
- \( P_{25} \) = 25th percentile of 30-day returns across top 100 coins
- **Low IQR Spread**: Narrow dispersion → Market moving together → Bullish regime
- **High IQR Spread**: Wide dispersion → Market fragmented → Potential rollover/bearish regime

### 2.2 Strategy Hypothesis

#### Hypothesis: IQR Spread as Market Regime Indicator

**Low Spread Regime (Compressed Returns):**
- **Characteristics**: Most coins moving together, low dispersion
- **Interpretation**: Strong market-wide momentum, risk-on environment
- **Expected Behavior**: Bullish continuation, broad-based rally
- **Positioning**: Long small caps (higher beta, outperform in risk-on)

**Medium Spread Regime (Normal Dispersion):**
- **Characteristics**: Typical market behavior, some winners and losers
- **Interpretation**: Neutral market, stock-picking environment
- **Expected Behavior**: Mixed performance, sector rotation
- **Positioning**: Balanced exposure or long majors (quality)

**High Spread Regime (Wide Dispersion):**
- **Characteristics**: Large gap between winners and losers
- **Interpretation**: Market stress, flight to quality, potential topping
- **Expected Behavior**: Increased volatility, potential reversal
- **Positioning**: Long majors (defensiveness), reduce small cap exposure

### 2.3 Market Segmentation

#### Majors (Large Caps)
- **Definition**: Top 10 coins by market cap
- **Examples**: BTC, ETH, BNB, SOL, XRP, ADA, DOGE
- **Characteristics**: Higher liquidity, lower volatility, "safe havens"
- **Beta**: Typically beta ~1.0 to BTC

#### Small Caps
- **Definition**: Coins ranked 51-100 by market cap
- **Examples**: Mid-tier DeFi, gaming, layer-2 projects
- **Characteristics**: Lower liquidity, higher volatility, higher beta
- **Beta**: Typically beta >1.5 to BTC

### 2.4 IQR Spread Calculation

#### Step 1: Universe Selection
```python
# On each calculation date, get top 100 coins by market cap
top_100_coins = coins.nlargest(100, 'market_cap')
```

#### Step 2: Calculate 30-Day Returns
```python
# Calculate 30-day percentage returns for each coin
returns_30d = (close_t / close_t-30 - 1) * 100  # Percentage returns
```

#### Step 3: Calculate Percentiles
```python
# Get 25th and 75th percentiles across top 100 coins
p25 = np.percentile(returns_30d, 25)
p75 = np.percentile(returns_30d, 75)
```

#### Step 4: Calculate IQR Spread
```python
# IQR spread is the difference between 75th and 25th percentiles
iqr_spread = p75 - p25
```

#### Step 5: Classify Regime
```python
# Define regime thresholds (can be static or dynamic)
# Using historical quintiles of IQR spread

if iqr_spread < 20th_percentile_historical:
    regime = 'LOW_SPREAD'  # Compressed, bullish
elif iqr_spread > 80th_percentile_historical:
    regime = 'HIGH_SPREAD'  # Wide dispersion, cautious
else:
    regime = 'MEDIUM_SPREAD'  # Normal
```

### 2.5 Additional Metrics

#### Median Return (50th Percentile)
```python
median_return = np.percentile(returns_30d, 50)
```
- Indicates overall market direction
- Used alongside IQR spread for context

#### Range (Max - Min)
```python
return_range = np.max(returns_30d) - np.min(returns_30d)
```
- Captures extreme outliers
- Complementary measure to IQR spread

#### Coefficient of Variation
```python
cv = np.std(returns_30d) / np.mean(returns_30d)
```
- Normalized dispersion measure
- Useful when mean returns vary significantly

---

## 3. Signal Generation

### 3.1 Daily Signal Process

**Step 1: Calculate IQR Spread**
```python
# For date T, calculate IQR spread using top 100 coins
iqr_spread_t = calculate_iqr_spread(
    prices_t, 
    lookback=30, 
    universe_size=100
)
```

**Step 2: Determine Regime**
```python
# Classify current IQR spread level
# Use rolling percentile of past 180 days of IQR spread
iqr_percentile = rank_percentile(
    iqr_spread_t, 
    iqr_spread_history[-180:]
)

if iqr_percentile <= 20:
    regime = 'LOW_SPREAD'
elif iqr_percentile >= 80:
    regime = 'HIGH_SPREAD'
else:
    regime = 'MEDIUM_SPREAD'
```

**Step 3: Generate Position Signals**
```python
# Strategy A: Majors vs Small Caps Rotation
if regime == 'LOW_SPREAD':
    # Risk-on: Favor small caps
    majors_weight = 0.30
    small_caps_weight = 0.70
    
elif regime == 'HIGH_SPREAD':
    # Risk-off: Favor majors
    majors_weight = 0.70
    small_caps_weight = 0.30
    
else:  # MEDIUM_SPREAD
    # Neutral: Balanced
    majors_weight = 0.50
    small_caps_weight = 0.50
```

### 3.2 Strategy Variants

#### Strategy 1: Dynamic Rotation (Majors vs Small Caps)
**Name:** `dynamic_rotation`

**Configuration:**
- Long majors: 30-70% (based on IQR spread)
- Long small caps: 70-30% (based on IQR spread)
- Fully invested (100% long)
- Rebalance weekly

**Logic:**
- Low spread → Overweight small caps (70%)
- High spread → Overweight majors (70%)

#### Strategy 2: Directional Long/Short
**Name:** `long_short`

**Configuration:**
- Low spread: Long small caps (100%), Short majors (optional)
- High spread: Long majors (100%), Short small caps (optional)
- Can use leverage (e.g., 100% long / 50% short)

**Logic:**
- Low spread → Long small caps only
- High spread → Long majors only

#### Strategy 3: Conditional Small Cap
**Name:** `conditional_smallcap`

**Configuration:**
- Low/Medium spread: Long small caps (100%)
- High spread: Exit to cash or rotate to majors
- Risk management overlay

**Logic:**
- Only hold small caps when spread is favorable

#### Strategy 4: Spread Mean Reversion
**Name:** `spread_mean_reversion`

**Configuration:**
- Extreme low spread: Reduce small cap exposure (expect widening)
- Extreme high spread: Increase small cap exposure (expect narrowing)
- Contrarian approach

**Logic:**
- Fade extremes in IQR spread

### 3.3 Entry Rules

**Rebalancing Schedule:**
- **Frequency**: Every 7 days (weekly, default)
- **Day**: Monday close (configurable)
- **Execution**: Assume next-day execution (avoid lookahead bias)

**Universe Selection:**
- **Majors**: Top 10 coins by market cap at rebalance date
- **Small Caps**: Coins ranked 51-100 by market cap at rebalance date
- **IQR Universe**: Top 100 coins by market cap at calculation date

**Filters:**
- **Minimum Volume**: 30-day avg volume > $1M (configurable)
- **Minimum Market Cap**: > $10M (configurable)
- **Data Quality**: At least 28 days of valid data in 30-day window
- **Exclude Stablecoins**: Remove USDT, USDC, DAI, etc.

### 3.4 Exit Rules

**Time-Based Exit:**
- Hold positions until next rebalance date
- No intra-period adjustments (except forced exits)

**Forced Exit Conditions:**
- Coin drops below minimum volume threshold
- Coin delisted from exchange
- Coin falls out of top 100 (for IQR calculation only)

**No Stop Loss:**
- Hold through drawdowns until rebalance
- Strategy assumes regime persistence

---

## 4. Portfolio Construction

### 4.1 Basket Construction

#### Majors Basket (Top 10)
```python
# Equal-weight or market-cap-weight the top 10 coins
majors = coins.nlargest(10, 'market_cap')

# Equal weight (default)
majors_weights = np.ones(len(majors)) / len(majors)

# Or market-cap weight
majors_weights = majors['market_cap'] / majors['market_cap'].sum()
```

#### Small Caps Basket (Rank 51-100)
```python
# Equal-weight or market-cap-weight coins ranked 51-100
small_caps = coins.nlargest(100, 'market_cap').iloc[50:100]

# Equal weight (default)
small_caps_weights = np.ones(len(small_caps)) / len(small_caps)

# Or market-cap weight
small_caps_weights = small_caps['market_cap'] / small_caps['market_cap'].sum()
```

### 4.2 Allocation Methods

#### Method 1: Fixed Allocation (Baseline)
```python
# Simple binary allocation based on regime
if regime == 'LOW_SPREAD':
    majors_alloc = 0.30
    small_caps_alloc = 0.70
elif regime == 'HIGH_SPREAD':
    majors_alloc = 0.70
    small_caps_alloc = 0.30
else:
    majors_alloc = 0.50
    small_caps_alloc = 0.50
```

#### Method 2: Continuous Allocation (Smooth)
```python
# Smooth allocation based on IQR spread percentile
# Low percentile (compressed) → More small caps
# High percentile (dispersed) → More majors

iqr_pct = rank_percentile(iqr_spread, iqr_history)

# Linear interpolation
# 0th percentile → 70% small caps
# 100th percentile → 70% majors
small_caps_alloc = 0.70 - (iqr_pct * 0.40)  # 70% to 30%
majors_alloc = 1.0 - small_caps_alloc
```

#### Method 3: Dynamic with Threshold
```python
# Allocate more aggressively at extremes
if iqr_pct < 10:
    # Very low spread: Maximum risk-on
    small_caps_alloc = 0.90
elif iqr_pct > 90:
    # Very high spread: Maximum risk-off
    small_caps_alloc = 0.10
else:
    # Normal: Balanced
    small_caps_alloc = 0.50

majors_alloc = 1.0 - small_caps_alloc
```

### 4.3 Within-Basket Weighting

**Equal Weight (Default):**
```python
# Each coin in basket receives equal weight
weights = np.ones(len(basket)) / len(basket)
```

**Market Cap Weight:**
```python
# Weight proportional to market cap
weights = basket['market_cap'] / basket['market_cap'].sum()
```

**Risk Parity:**
```python
# Weight inversely proportional to volatility
volatility = basket['returns'].rolling(30).std()
inverse_vol = 1 / volatility
weights = inverse_vol / inverse_vol.sum()
```

---

## 5. Backtest Implementation

### 5.1 File Structure

**Main Script:** `backtests/scripts/backtest_iqr_spread_factor.py`

**Purpose:** Backtest engine for IQR spread-based regime strategies

**Output Directory:** `backtests/results/`

### 5.2 Command-Line Interface

```bash
python3 backtests/scripts/backtest_iqr_spread_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy dynamic_rotation \
  --lookback-days 30 \
  --rebalance-days 7 \
  --iqr-history-window 180 \
  --majors-count 10 \
  --small-caps-range 51-100 \
  --low-spread-threshold 20 \
  --high-spread-threshold 80 \
  --allocation-method fixed \
  --basket-weighting equal_weight \
  --initial-capital 10000 \
  --start-date 2020-01-01 \
  --end-date 2025-10-27 \
  --output-prefix backtest_iqr_spread
```

### 5.3 Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--price-data` | (required) | Path to OHLCV CSV file |
| `--strategy` | `dynamic_rotation` | Strategy variant: `dynamic_rotation`, `long_short`, `conditional_smallcap`, `spread_mean_reversion` |
| `--lookback-days` | 30 | Days for calculating returns (IQR input) |
| `--rebalance-days` | 7 | Rebalance frequency (days) |
| `--iqr-history-window` | 180 | Days of IQR history for percentile calculation |
| `--majors-count` | 10 | Number of coins in majors basket (top N) |
| `--small-caps-range` | `51-100` | Rank range for small caps basket |
| `--low-spread-threshold` | 20 | Percentile threshold for "low spread" (below = low) |
| `--high-spread-threshold` | 80 | Percentile threshold for "high spread" (above = high) |
| `--allocation-method` | `fixed` | Allocation method: `fixed`, `continuous`, `threshold` |
| `--basket-weighting` | `equal_weight` | Within-basket weighting: `equal_weight`, `market_cap`, `risk_parity` |
| `--min-volume` | 1000000 | Minimum 30d avg volume ($) |
| `--min-market-cap` | 10000000 | Minimum market cap ($) |
| `--initial-capital` | 10000 | Starting capital (USD) |
| `--start-date` | None | Backtest start (YYYY-MM-DD) |
| `--end-date` | None | Backtest end (YYYY-MM-DD) |
| `--output-prefix` | `backtest_iqr_spread` | Output file prefix |

### 5.4 Output Files

#### 1. IQR Spread Time Series
**File:** `backtest_iqr_spread_iqr_timeseries.csv`

```csv
date,iqr_spread,p25,p75,median,mean,std,min,max,range,iqr_percentile,regime
2020-01-01,25.3,5.2,30.5,15.8,16.2,18.4,-45.2,78.3,123.5,42.5,MEDIUM_SPREAD
2020-01-08,18.7,8.1,26.8,18.5,19.1,14.2,-28.3,62.1,90.4,28.3,LOW_SPREAD
...
```

**Fields:**
- `date`: Calculation date
- `iqr_spread`: 75th - 25th percentile (main signal)
- `p25`: 25th percentile of 30d returns
- `p75`: 75th percentile of 30d returns
- `median`: 50th percentile (median return)
- `mean`: Average return across universe
- `std`: Standard deviation of returns
- `min`: Minimum return (worst coin)
- `max`: Maximum return (best coin)
- `range`: Max - min (full range)
- `iqr_percentile`: Percentile rank of current IQR spread
- `regime`: Classification (LOW_SPREAD, MEDIUM_SPREAD, HIGH_SPREAD)

#### 2. Portfolio Values
**File:** `backtest_iqr_spread_portfolio_values.csv`

```csv
date,portfolio_value,cash,majors_exposure,smallcaps_exposure,majors_allocation,smallcaps_allocation,regime,iqr_spread
2020-01-01,10000.00,0.00,5000.00,5000.00,0.50,0.50,MEDIUM_SPREAD,25.3
2020-01-08,10125.50,0.00,3037.65,7087.85,0.30,0.70,LOW_SPREAD,18.7
...
```

#### 3. Performance by Regime
**File:** `backtest_iqr_spread_regime_performance.csv`

```csv
regime,num_days,majors_avg_return,smallcaps_avg_return,majors_sharpe,smallcaps_sharpe,majors_win_rate,smallcaps_win_rate
LOW_SPREAD,120,0.0015,0.0032,0.85,1.42,0.58,0.65
MEDIUM_SPREAD,180,0.0012,0.0018,0.72,0.95,0.54,0.58
HIGH_SPREAD,95,0.0018,0.0008,1.05,0.48,0.62,0.48
```

#### 4. Basket Performance
**File:** `backtest_iqr_spread_basket_performance.csv`

```csv
date,majors_return,smallcaps_return,majors_volatility,smallcaps_volatility,spread_return,iqr_spread
2020-01-01,0.0125,0.0218,0.042,0.085,0.0093,25.3
2020-01-08,-0.0032,0.0145,0.038,0.092,0.0177,18.7
...
```

#### 5. Performance Metrics
**File:** `backtest_iqr_spread_metrics.csv`

```csv
metric,value
initial_capital,10000.00
final_value,15847.32
total_return,0.5847
annualized_return,0.2384
annualized_volatility,0.1956
sharpe_ratio,1.22
sortino_ratio,1.78
max_drawdown,-0.2145
calmar_ratio,1.11
win_rate,0.5821
avg_majors_allocation,0.48
avg_smallcaps_allocation,0.52
days_low_spread,120
days_medium_spread,180
days_high_spread,95
```

#### 6. Correlation Matrix
**File:** `backtest_iqr_spread_correlations.csv`

```csv
,iqr_spread,majors_return,smallcaps_return,btc_return,median_return
iqr_spread,1.00,-0.32,-0.18,-0.28,0.05
majors_return,-0.32,1.00,0.75,0.92,0.85
smallcaps_return,-0.18,0.75,1.00,0.68,0.88
btc_return,-0.28,0.92,0.68,1.00,0.78
median_return,0.05,0.85,0.88,0.78,1.00
```

---

## 6. Analysis & Validation

### 6.1 No-Lookahead Bias Prevention

**Critical Rule:** Signals on day T use returns from day T+1

**Implementation:**
```python
# Day T: Calculate IQR spread using 30-day returns ending on day T-1
returns_30d = calculate_returns(prices[t-30:t])
iqr_spread_t = calculate_iqr(returns_30d)

# Day T: Determine regime and allocations
regime_t = classify_regime(iqr_spread_t, iqr_history)
allocations_t = determine_allocations(regime_t)

# Day T+1: Apply allocations using next day's returns
returns_t1 = prices[t+1] / prices[t] - 1
pnl_t1 = allocations_t * returns_t1  # Use .shift(-1) for proper alignment
```

**Key Checks:**
- ✅ IQR spread calculated using only past returns
- ✅ Regime classification based on historical IQR values
- ✅ Positions executed at close of day T, returns from day T+1
- ✅ No future prices or returns used in any calculation

### 6.2 Universe Stability

**Dynamic Universe Issues:**
- Top 100 changes over time
- Coins enter/exit due to market cap fluctuations
- Survivorship bias if not handled properly

**Solutions:**
- Use point-in-time market cap rankings
- Include delisted coins (mark as zero return after delisting)
- Track universe composition changes
- Minimum 80% overlap for stability

### 6.3 Statistical Tests

**Regime Predictive Power:**
```python
# Test if IQR spread predicts future returns
# Low spread → Higher small cap returns?
# High spread → Higher major returns?

# Regression: future_return ~ iqr_spread + controls
# Calculate correlation, t-statistics, p-values
```

**Regime Persistence:**
```python
# Test if regimes are persistent
# Autocorrelation of IQR spread
# Transition probabilities between regimes
```

---

## 7. Expected Insights

### 7.1 Key Questions

**1. Does IQR spread predict returns?**
- Is low spread followed by continued outperformance?
- Does high spread signal market tops?
- Lead-lag relationship between spread and returns

**2. Do majors and small caps behave differently by regime?**
- Small caps outperform in low spread?
- Majors defensive in high spread?
- Beta differences across regimes

**3. Is IQR spread stable over time?**
- Mean reversion vs. trending behavior
- Regime persistence (autocorrelation)
- Structural breaks in spread behavior

**4. How does IQR spread relate to market conditions?**
- Correlation with BTC returns
- Correlation with market volatility
- Behavior in bull vs. bear markets

### 7.2 Success Criteria

**Minimum Viable Results:**
- **Sharpe Ratio**: > 0.8 (vs buy-and-hold)
- **Maximum Drawdown**: < 35%
- **Win Rate**: > 52%
- **Regime Separation**: Clear performance differences by regime
- **Alpha**: Positive alpha vs. equal-weight index

**Stretch Goals:**
- **Sharpe Ratio**: > 1.2
- **Maximum Drawdown**: < 25%
- **Calmar Ratio**: > 0.8
- **Regime Predictability**: Statistically significant (p < 0.05)
- **Outperform in Both Bull & Bear**: Robust across cycles

### 7.3 Comparison Benchmarks

**Strategy Benchmarks:**
- BTC buy-and-hold
- Equal-weight majors (top 10)
- Equal-weight small caps (rank 51-100)
- 50/50 balanced (majors + small caps)
- Market-cap-weight top 100

**Factor Strategies:**
- Size factor (large vs. small)
- Beta factor (low vs. high beta)
- Momentum factor (winners vs. losers)
- Volatility factor (low vs. high vol)

---

## 8. Risk Considerations

### 8.1 Strategy Risks

**Regime Instability:**
- IQR spread can change rapidly
- False signals during transitions
- Solution: Smooth transitions, use buffer zones

**Liquidity Risk:**
- Small caps may have poor liquidity
- Execution slippage on rebalancing
- Solution: Volume filters, limit position sizes

**Survivorship Bias:**
- Top 100 changes over time
- Delisted coins create gaps
- Solution: Point-in-time universe, include delistings

**Correlation Risk:**
- Majors and small caps both correlate to BTC
- Limited diversification benefit
- Solution: Consider BTC correlation in allocation

**Regime Persistence:**
- Regimes may not persist long enough
- High turnover if regimes flip frequently
- Solution: Longer rebalance periods, regime smoothing

### 8.2 Implementation Risks

**Execution Risk:**
- Small caps harder to execute
- Market impact for larger portfolios
- Solution: VWAP execution, phased entry

**Transaction Costs:**
- Frequent rebalancing = high fees
- Small caps have higher trading costs
- Solution: Optimize rebalance frequency

**Data Quality:**
- Market cap data may lag
- Missing data for some coins
- Solution: Multiple data sources, validation checks

---

## 9. Implementation Roadmap

### Phase 1: Core Implementation (Week 1)
- [ ] Create `backtests/scripts/backtest_iqr_spread_factor.py`
- [ ] Implement IQR spread calculation function
- [ ] Implement regime classification logic
- [ ] Build majors and small caps basket construction
- [ ] Validate no-lookahead bias (use `.shift(-1)`)
- [ ] Run baseline backtest: Dynamic Rotation strategy

### Phase 2: Analysis & Validation (Week 1-2)
- [ ] Generate IQR spread time series
- [ ] Analyze regime distributions and transitions
- [ ] Calculate performance by regime
- [ ] Validate predictive power (statistical tests)
- [ ] Check for data quality issues
- [ ] Verify performance metrics calculations

### Phase 3: Strategy Variants (Week 2)
- [ ] Implement all 4 strategy variants
- [ ] Test different allocation methods (fixed, continuous, threshold)
- [ ] Test different regime thresholds (20/80, 25/75, 30/70)
- [ ] Test different lookback windows (20d, 30d, 45d, 60d)
- [ ] Test different rebalancing frequencies (3d, 7d, 14d)
- [ ] Compare all variants

### Phase 4: Regime Analysis (Week 2-3)
- [ ] Analyze regime persistence (autocorrelation)
- [ ] Transition probability matrix
- [ ] Lead-lag analysis (spread → returns)
- [ ] Correlation with market conditions
- [ ] Identify regime change signals
- [ ] Test regime smoothing techniques

### Phase 5: Results & Documentation (Week 3)
- [ ] Generate all output CSV files
- [ ] Create performance visualizations:
  - IQR spread over time
  - Regime coloring on equity curve
  - Performance by regime (bar charts)
  - Correlation heatmap
  - Drawdown analysis
- [ ] Calculate correlation to other factors
- [ ] Compare to benchmark strategies
- [ ] Create comprehensive summary report
- [ ] Document findings and recommendations

---

## 10. Visualization Requirements

### 10.1 IQR Spread Time Series Plot
```python
# Line plot of IQR spread over time
# Color-coded by regime (low=green, medium=yellow, high=red)
# Include horizontal lines for thresholds
```

### 10.2 Equity Curve with Regime Overlay
```python
# Portfolio value over time
# Background shading by regime
# Compare to benchmarks (BTC, equal-weight)
```

### 10.3 Performance by Regime
```python
# Bar chart: Average returns by regime for majors vs. small caps
# Error bars showing volatility
# Statistical significance indicators
```

### 10.4 Correlation Heatmap
```python
# Heatmap: IQR spread vs. majors/small caps returns
# Include BTC, median return, volatility
```

### 10.5 Regime Transition Matrix
```python
# Heatmap: Transition probabilities between regimes
# LOW → LOW, LOW → MEDIUM, etc.
```

---

## 11. Integration with Existing System

### 11.1 Code Reuse

**Existing Utilities:**
- `backtests/scripts/backtest_size_factor.py` - Template structure
- `backtests/scripts/backtest_beta_factor.py` - Basket construction
- `signals/calc_vola.py` - Volatility calculation (for risk parity)
- `signals/calc_weights.py` - Risk parity weight calculation

**Data Integration:**
- Use existing: `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- Same CSV format and naming conventions
- Store outputs in: `backtests/results/`

### 11.2 Multi-Factor Integration

**Combine with Existing Factors:**
- Use IQR spread as regime filter for other strategies
- Apply beta factor only in low spread regimes
- Apply momentum factor with regime overlay
- Dynamic factor rotation based on IQR spread

**Example:**
```python
# Conditional factor strategy
if iqr_regime == 'LOW_SPREAD':
    # Risk-on: Use high-beta, momentum strategies
    apply_momentum_factor()
elif iqr_regime == 'HIGH_SPREAD':
    # Risk-off: Use low-vol, quality strategies
    apply_low_volatility_factor()
```

---

## 12. Academic & Theoretical Background

### 12.1 Traditional Finance

**Cross-Sectional Dispersion:**
- Used in equity markets as breadth indicator
- Low dispersion → Market-driven regime
- High dispersion → Stock-picking regime

**Market Breadth Indicators:**
- Advance-decline line
- Percentage of stocks above moving averages
- IQR spread is similar concept for crypto

### 12.2 Crypto-Specific Research

**Altcoin Seasonality:**
- "Altcoin season" = low dispersion, broad rally
- "Bitcoin dominance" = high dispersion, flight to quality
- IQR spread quantifies these regimes

**Market Maturity:**
- Crypto markets becoming more dispersed over time?
- Increasing importance of fundamentals vs. beta?

---

## 13. Example Usage

### Basic Backtest
```bash
# Run dynamic rotation strategy (baseline)
python3 backtests/scripts/backtest_iqr_spread_factor.py \
  --strategy dynamic_rotation \
  --lookback-days 30 \
  --rebalance-days 7
```

### Test Different Regimes
```bash
# Test with tighter regime bands
python3 backtests/scripts/backtest_iqr_spread_factor.py \
  --strategy dynamic_rotation \
  --low-spread-threshold 25 \
  --high-spread-threshold 75
```

### Parameter Sensitivity
```bash
# Test different lookback windows
for lookback in 20 30 45 60; do
  python3 backtests/scripts/backtest_iqr_spread_factor.py \
    --strategy dynamic_rotation \
    --lookback-days $lookback \
    --output-prefix backtest_iqr_spread_${lookback}d
done
```

### Advanced Configuration
```bash
python3 backtests/scripts/backtest_iqr_spread_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy dynamic_rotation \
  --lookback-days 30 \
  --rebalance-days 7 \
  --iqr-history-window 180 \
  --majors-count 10 \
  --small-caps-range 51-100 \
  --low-spread-threshold 20 \
  --high-spread-threshold 80 \
  --allocation-method continuous \
  --basket-weighting risk_parity \
  --initial-capital 10000 \
  --start-date 2020-01-01 \
  --end-date 2025-10-27 \
  --output-prefix backtest_iqr_spread_advanced
```

---

## 14. Next Steps

1. **Implement baseline script**: Start with dynamic_rotation strategy
2. **Validate IQR spread calculation**: Manual spot checks
3. **Run initial backtest**: Generate first results
4. **Analyze regime behavior**: Check if regimes make sense
5. **Test predictive power**: Statistical tests on regime → returns
6. **Iterate on parameters**: Optimize thresholds and lookbacks
7. **Compare strategies**: All 4 variants
8. **Document findings**: Comprehensive summary report

---

**Document Owner:** Research Team  
**Last Updated:** 2025-10-27  
**Status:** Specification - Ready for Implementation  
**Next Step:** Implement Phase 1 (Core backtest script)

---

**Disclaimer:** This backtest is for research purposes only. Past performance does not guarantee future results. Cryptocurrency trading involves substantial risk of loss. The IQR spread indicator is experimental and should be validated thoroughly before any live trading application.
