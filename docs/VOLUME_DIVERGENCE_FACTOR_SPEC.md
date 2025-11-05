# Volume Divergence Factor Trading Strategy Specification

**Version:** 1.0  
**Date:** 2025-10-28  
**Status:** Specification - Ready for Implementation

---

## 1. Executive Summary

This specification outlines a quantitative trading strategy based on **volume-price divergence analysis** for cryptocurrencies. The core hypothesis tests whether the relationship between price movements and volume changes contains predictive information about future returns.

### Key Objectives
1. Analyze the relationship between price changes and volume changes
2. Identify divergence patterns (price/volume disagreement)
3. Rank coins by volume divergence characteristics
4. Construct long/short portfolios based on volume-price dynamics
5. Test whether volume confirmation predicts continuation vs. reversal

### Strategy Overview
- **Factor**: Volume-Price Divergence (measures agreement/disagreement between price and volume)
- **Universe**: All liquid cryptocurrencies with sufficient trading history
- **Rebalancing**: Weekly (configurable)
- **Market Neutrality**: Dollar-neutral long/short construction
- **Risk Management**: Equal weight or risk parity weighting

---

## 2. Strategy Description

### 2.1 Core Concept

**Volume Divergence Analysis** examines the relationship between price movements and volume changes to identify strong vs. weak moves:

**Key Patterns:**

1. **Price Up + Volume Up** (Bullish Confirmation)
   - Rising prices supported by rising volume
   - Strong buying pressure
   - Likely continuation pattern

2. **Price Up + Volume Down** (Bearish Divergence)
   - Rising prices on declining volume
   - Weak buying pressure
   - Potential reversal signal

3. **Price Down + Volume Up** (Bearish Confirmation)
   - Falling prices on rising volume
   - Strong selling pressure
   - Likely continuation pattern

4. **Price Down + Volume Down** (Bullish Divergence)
   - Falling prices on declining volume
   - Weak selling pressure
   - Potential reversal signal

5. **Price Flat + Volume Up** (Accumulation/Distribution)
   - Sideways price with volume spike
   - Potential breakout/breakdown setup
   - Ambiguous signal - needs context

6. **Price Flat + Volume Down** (No Interest)
   - Sideways price with declining volume
   - Market indecision
   - Low conviction environment

### 2.2 Volume Divergence Metrics

We calculate several metrics to quantify volume-price relationships:

#### Metric 1: Price-Volume Correlation (PVC)
```python
# Rolling correlation between price changes and volume changes
price_change = log(close_t / close_t-1)
volume_change = log(volume_t / volume_t-1)

pvc_30d = correlation(price_change, volume_change, window=30)
```

**Interpretation:**
- **High positive PVC** (> 0.5): Price and volume move together (confirmation)
- **Low/zero PVC** (≈ 0): No relationship (divergence)
- **Negative PVC** (< 0): Inverse relationship (strong divergence)

#### Metric 2: Volume Momentum Indicator (VMI)
```python
# Compares recent volume to historical average
volume_ma_short = mean(volume_t, window=10)
volume_ma_long = mean(volume_t, window=30)

vmi = (volume_ma_short - volume_ma_long) / volume_ma_long
```

**Interpretation:**
- **VMI > 0.2**: Volume expanding significantly
- **VMI ≈ 0**: Volume stable
- **VMI < -0.2**: Volume contracting significantly

#### Metric 3: Divergence Score (DS)
```python
# Combines price direction, volume direction, and their relationship

# Calculate price momentum (30-day return)
price_momentum = (close_t - close_t-30) / close_t-30

# Calculate volume momentum (30-day volume change)
volume_momentum = (volume_t_avg_10d - volume_t-30_avg_10d) / volume_t-30_avg_10d

# Divergence Score
# Positive when price and volume agree (confirmation)
# Negative when price and volume disagree (divergence)
ds = sign(price_momentum) * sign(volume_momentum) * abs(price_momentum) * (1 + abs(volume_momentum))
```

**Interpretation:**
- **DS > 0.5**: Strong confirmation (price and volume agree, large moves)
- **DS ≈ 0**: Neutral (small moves or disagreement)
- **DS < -0.5**: Strong divergence (price and volume disagree)

#### Metric 4: Volume-Price Ratio (VPR)
```python
# Ratio of volume change to price change
price_change_pct = abs((close_t - close_t-1) / close_t-1)
volume_change_pct = abs((volume_t - volume_t-1) / volume_t-1)

# Avoid division by zero
if price_change_pct > 0.001:
    vpr = volume_change_pct / price_change_pct
else:
    vpr = 0

# Rolling average of VPR
vpr_30d = mean(vpr, window=30)
```

**Interpretation:**
- **High VPR** (> 10): Large volume changes relative to price changes (high liquidity)
- **Low VPR** (< 5): Small volume changes relative to price changes (thin trading)

### 2.3 Strategy Hypotheses

#### Hypothesis A: Confirmation Premium
**Long**: Coins with strong price-volume confirmation (high PVC, positive DS)  
**Short**: Coins with price-volume divergence (low PVC, negative DS)  
**Rationale**: Confirmed moves continue; divergent moves reverse

**Why this might work:**
1. **Volume Validates Price**: Volume confirms genuine demand/supply shifts
2. **Weak Hands**: Low-volume moves lack conviction, likely to reverse
3. **Smart Money**: High-volume moves indicate institutional participation
4. **Technical Analysis**: Classic TA principle of volume confirmation

#### Hypothesis B: Contrarian Divergence
**Long**: Coins with bearish divergence (price down, volume down)  
**Short**: Coins with bearish confirmation (price down, volume up)  
**Rationale**: Weak selling exhausts, strong selling continues

**Why this might work:**
1. **Exhaustion**: Declining volume on down moves signals capitulation
2. **Panic Selling**: High-volume selling indicates panic, often marks bottom
3. **Mean Reversion**: Oversold conditions with declining interest reverse
4. **Crypto Volatility**: Extreme moves often reverse quickly

#### Hypothesis C: Volume Momentum
**Long**: Coins with expanding volume (high VMI)  
**Short**: Coins with contracting volume (low VMI)  
**Rationale**: Rising volume precedes breakouts

**Why this might work:**
1. **Breakout Signal**: Volume expansion precedes price breakouts
2. **Interest Gauge**: Rising volume indicates growing interest
3. **Liquidity Premium**: High-volume coins have better liquidity
4. **Attention Effect**: Volume spikes attract more participants

### 2.4 Calculation Methodology

#### Data Preparation
```python
import pandas as pd
import numpy as np
from scipy.stats import pearsonr

def prepare_data(df):
    """
    Calculate all necessary metrics for volume divergence analysis.
    
    Args:
        df: DataFrame with date, symbol, close, volume
        
    Returns:
        DataFrame with volume divergence metrics
    """
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Calculate price returns
    df['price_change'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Calculate volume changes
    df['volume_change'] = df.groupby('symbol')['volume'].transform(
        lambda x: np.log(x.replace(0, np.nan) / x.shift(1).replace(0, np.nan))
    )
    
    # Calculate price momentum (30-day return)
    df['price_momentum_30d'] = df.groupby('symbol')['close'].transform(
        lambda x: (x - x.shift(30)) / x.shift(30)
    )
    
    # Calculate volume momentum indicators
    df['volume_ma_10d'] = df.groupby('symbol')['volume'].transform(
        lambda x: x.rolling(10, min_periods=10).mean()
    )
    df['volume_ma_30d'] = df.groupby('symbol')['volume'].transform(
        lambda x: x.rolling(30, min_periods=30).mean()
    )
    
    df['vmi'] = (df['volume_ma_10d'] - df['volume_ma_30d']) / df['volume_ma_30d']
    
    return df
```

#### Rolling Price-Volume Correlation
```python
def calculate_pvc(df, window=30):
    """
    Calculate rolling price-volume correlation.
    
    Args:
        df: DataFrame with symbol, date, price_change, volume_change
        window: Rolling window in days
        
    Returns:
        DataFrame with pvc column
    """
    def rolling_corr(group):
        # Calculate correlation between price_change and volume_change
        return group['price_change'].rolling(window, min_periods=window).corr(
            group['volume_change']
        )
    
    df['pvc_30d'] = df.groupby('symbol').apply(rolling_corr).reset_index(level=0, drop=True)
    return df
```

#### Divergence Score
```python
def calculate_divergence_score(df):
    """
    Calculate divergence score combining price and volume momentum.
    
    Args:
        df: DataFrame with price_momentum_30d, vmi
        
    Returns:
        DataFrame with divergence_score column
    """
    # Sign agreement: +1 if same direction, -1 if opposite
    price_sign = np.sign(df['price_momentum_30d'])
    volume_sign = np.sign(df['vmi'])
    
    # Divergence score
    df['divergence_score'] = (
        price_sign * volume_sign * 
        np.abs(df['price_momentum_30d']) * 
        (1 + np.abs(df['vmi']))
    )
    
    return df
```

### 2.5 Calculation Parameters

**Default Parameters:**
- **PVC Window**: 30 days (correlation lookback)
- **VMI Short Window**: 10 days (recent volume average)
- **VMI Long Window**: 30 days (baseline volume average)
- **Momentum Window**: 30 days (price momentum calculation)
- **Minimum Data**: 30 days for valid calculation
- **Price/Volume Frequency**: Daily close prices and volumes

**Parameter Variations to Test:**
- **Short-term (15d)**: More reactive to recent changes
- **Medium-term (30d)**: Baseline, balanced
- **Long-term (60d)**: More stable, captures longer trends

---

## 3. Signal Generation

### 3.1 Daily Signal Process

**Step 1: Calculate Volume Divergence Metrics**
```python
# For each coin, calculate all metrics
df = prepare_data(price_volume_data)
df = calculate_pvc(df, window=30)
df = calculate_divergence_score(df)
```

**Step 2: Filter Universe**
```python
# Apply liquidity and data quality filters
valid_coins = df[
    (df['volume_ma_30d'] > MIN_VOLUME) &
    (df['market_cap'] > MIN_MARKET_CAP) &
    (df['pvc_30d'].notna()) &
    (df['divergence_score'].notna())
]
```

**Step 3: Rank by Divergence Metrics**

**Strategy A: Confirmation Premium**
```python
# Rank by divergence score (high = confirmation, low = divergence)
rank_divergence = valid_coins['divergence_score'].rank(ascending=False)

if rank_divergence <= 20th_percentile:
    signal = LONG  # Strong confirmation
elif rank_divergence >= 80th_percentile:
    signal = SHORT  # Strong divergence
```

**Strategy B: Volume Momentum**
```python
# Rank by volume momentum indicator
rank_vmi = valid_coins['vmi'].rank(ascending=False)

if rank_vmi <= 20th_percentile:
    signal = LONG  # Expanding volume
elif rank_vmi >= 80th_percentile:
    signal = SHORT  # Contracting volume
```

**Strategy C: Price-Volume Correlation**
```python
# Rank by PVC (high = strong agreement)
rank_pvc = valid_coins['pvc_30d'].rank(ascending=False)

if rank_pvc <= 20th_percentile:
    signal = LONG  # High correlation (confirmation)
elif rank_pvc >= 80th_percentile:
    signal = SHORT  # Low/negative correlation (divergence)
```

### 3.2 Entry Rules

**Rebalancing Schedule:**
- **Frequency**: Every 7 days (weekly, default)
- **Day**: Monday close (configurable)
- **Execution**: Assume next-day execution (avoid lookahead bias)

**Position Selection:**
- **Long Bucket**: Bottom (or top) quintile by selected metric
- **Short Bucket**: Top (or bottom) quintile by selected metric
- **Max Positions**: 10-20 longs + 10-20 shorts (configurable)
- **Min Window**: At least 30 days of valid price and volume data

**Filters:**
- **Minimum Volume**: 30-day avg volume > $5M (configurable)
- **Minimum Market Cap**: > $50M (configurable)
- **Data Quality**: At least 80% valid data in calculation window
- **Exclude Stablecoins**: Remove USDT, USDC, DAI, etc.
- **Exclude Zero Volume**: Remove days with zero or near-zero volume

### 3.3 Exit Rules

**Time-Based Exit:**
- Hold positions until next rebalance date
- No intra-period adjustments (except forced exits)

**Forced Exit Conditions:**
- Coin drops below minimum volume threshold
- Coin delisted from exchange
- Data quality deteriorates (missing data)
- Volume drops to near-zero (liquidity crisis)

**No Stop Loss:**
- Hold through drawdowns until rebalance
- Strategy assumes divergence characteristics persist

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

#### Method 2: Risk Parity (Volume-Adjusted)
```python
# Weight inversely proportional to volatility
volatility = coin_returns.rolling(30).std() * np.sqrt(365)
inverse_vol = 1 / volatility
weights = (inverse_vol / inverse_vol.sum()) * allocation
```

#### Method 3: Volume-Weighted
```python
# Weight proportional to trading volume
# Higher volume = higher weight (better liquidity)
volume_normalized = volume / volume.sum()
weights = volume_normalized * allocation
```

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

---

## 5. Backtest Implementation

### 5.1 File Structure

**Main Script:** `backtests/scripts/backtest_volume_divergence_factor.py`

**Purpose:** Backtest engine for volume divergence-based strategies

**Output Directory:** `backtests/results/`

### 5.2 Command-Line Interface

```bash
python3 backtests/scripts/backtest_volume_divergence_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy confirmation_premium \
  --metric divergence_score \
  --lookback-window 30 \
  --rebalance-days 7 \
  --weighting-method equal_weight \
  --long-allocation 0.5 \
  --short-allocation 0.5 \
  --start-date 2020-01-01 \
  --end-date 2025-10-28 \
  --output-prefix backtest_volume_divergence
```

### 5.3 Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--price-data` | (required) | Path to OHLCV CSV file |
| `--strategy` | `confirmation_premium` | Strategy variant: `confirmation_premium`, `volume_momentum`, `contrarian_divergence` |
| `--metric` | `divergence_score` | Primary metric: `divergence_score`, `pvc_30d`, `vmi` |
| `--lookback-window` | 30 | Calculation window (days) |
| `--vmi-short-window` | 10 | VMI short moving average (days) |
| `--vmi-long-window` | 30 | VMI long moving average (days) |
| `--rebalance-days` | 7 | Rebalance frequency (days) |
| `--num-quintiles` | 5 | Number of ranking buckets |
| `--long-percentile` | 20 | Percentile threshold for long (bottom 20%) |
| `--short-percentile` | 80 | Percentile threshold for short (top 20%) |
| `--weighting-method` | `equal_weight` | Weighting: `equal_weight`, `risk_parity`, `volume_weighted` |
| `--min-volume` | 5000000 | Minimum 30d avg volume ($) |
| `--min-market-cap` | 50000000 | Minimum market cap ($) |
| `--initial-capital` | 10000 | Starting capital (USD) |
| `--leverage` | 1.0 | Leverage multiplier |
| `--long-allocation` | 0.5 | Long side allocation (50%) |
| `--short-allocation` | 0.5 | Short side allocation (50%) |
| `--start-date` | None | Backtest start (YYYY-MM-DD) |
| `--end-date` | None | Backtest end (YYYY-MM-DD) |
| `--output-prefix` | `backtest_volume_divergence` | Output file prefix |

### 5.4 Output Files

#### 1. Portfolio Values
**File:** `backtest_volume_divergence_portfolio_values.csv`

```csv
date,portfolio_value,cash,long_exposure,short_exposure,net_exposure,gross_exposure,num_longs,num_shorts,avg_divergence_long,avg_divergence_short
2020-01-01,10000.00,0.00,5000.00,-5000.00,0.00,10000.00,10,10,0.45,-0.38
2020-01-08,10150.25,0.00,5075.13,-5075.13,0.00,10150.25,10,10,0.48,-0.35
...
```

#### 2. Trade Log
**File:** `backtest_volume_divergence_trades.csv`

```csv
date,symbol,signal,divergence_score,pvc_30d,vmi,rank,percentile,weight,position_size,market_cap,volume_30d_avg,price_momentum_30d
2020-01-08,BTC,LONG,0.52,0.68,0.15,3,6.1,0.11,550.00,180000000000,25000000000,0.045
2020-01-08,ETH,LONG,0.48,0.65,0.12,5,10.2,0.10,500.00,25000000000,8000000000,0.038
2020-01-08,DOGE,SHORT,-0.42,-0.15,-0.25,48,98.0,0.08,-400.00,2000000000,500000000,-0.082
...
```

#### 3. Performance Metrics
**File:** `backtest_volume_divergence_metrics.csv`

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
avg_divergence_long,0.45
avg_divergence_short,-0.38
total_rebalances,78
trading_days,547
```

#### 4. Divergence Time Series
**File:** `backtest_volume_divergence_timeseries.csv`

```csv
date,symbol,divergence_score,pvc_30d,vmi,rank,percentile,price_momentum_30d,volume_ma_10d,volume_ma_30d
2020-01-08,BTC,0.52,0.68,0.15,3,6.1,0.045,30000000000,28000000000
2020-01-08,ETH,0.48,0.65,0.12,5,10.2,0.038,9000000000,8500000000
...
```

---

## 6. Strategy Variants

### 6.1 Confirmation Premium (Primary Strategy)
**Name:** `confirmation_premium`

**Configuration:**
- Long: Top quintile (high divergence score, confirmation)
- Short: Bottom quintile (low/negative divergence score, divergence)
- Allocation: 50% long, 50% short
- Market Neutral: Yes

**Hypothesis:** Price moves confirmed by volume continue; divergent moves reverse

**Expected Outcome:**
- Captures trend continuation on confirmed moves
- Benefits from reversals on divergent moves
- Market-neutral exposure

### 6.2 Volume Momentum Strategy
**Name:** `volume_momentum`

**Configuration:**
- Long: Top quintile (high VMI, expanding volume)
- Short: Bottom quintile (low VMI, contracting volume)
- Allocation: 50% long, 50% short
- Market Neutral: Yes

**Hypothesis:** Rising volume precedes breakouts; falling volume signals exhaustion

**Expected Outcome:**
- Captures breakout moves
- Avoids low-interest, drifting coins
- Early entry before price acceleration

### 6.3 Contrarian Divergence Strategy
**Name:** `contrarian_divergence`

**Configuration:**
- Long: Coins with low volume on down moves (weak selling)
- Short: Coins with high volume on down moves (strong selling)
- Allocation: 50% long, 50% short
- Market Neutral: Yes

**Hypothesis:** Weak selling exhausts; strong selling continues

**Expected Outcome:**
- Mean reversion plays
- Contrarian positioning
- Higher turnover

### 6.4 High Correlation Only
**Name:** `high_correlation`

**Configuration:**
- Long: Top quintile (high PVC, strong agreement)
- Short: None (50% cash)
- Allocation: 50% long, 0% short
- Market Neutral: No

**Hypothesis:** Follow only strongly confirmed trends

**Expected Outcome:**
- Trend following
- Lower volatility
- Positive market correlation

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

### 7.3 Volume Divergence-Specific Metrics
- **Average Divergence Score Long**: Mean divergence score of long positions
- **Average Divergence Score Short**: Mean divergence score of short positions
- **Average PVC Long**: Mean price-volume correlation of longs
- **Average PVC Short**: Mean price-volume correlation of shorts
- **Volume Expansion Rate**: % of positions with expanding volume
- **Confirmation Rate**: % of long positions with positive divergence score

### 7.4 Trading Metrics
- **Win Rate**: % of profitable rebalancing periods
- **Average Turnover**: % of portfolio traded per rebalance
- **Number of Rebalances**: Total rebalancing events
- **Avg Long Positions**: Average number of long positions
- **Avg Short Positions**: Average number of short positions
- **Volume Concentration**: % of portfolio in highest volume coins

---

## 8. No-Lookahead Bias Prevention

**Critical Rule:** Signals on day T use returns from day T+1

### 8.1 Implementation

```python
# Day T: Calculate volume divergence metrics using data up to day T
divergence_t = calculate_divergence_metrics(
    price_volume_data.loc[:t], 
    window=30
)

# Day T: Rank coins and generate signals
signals_t = generate_signals(divergence_t)

# Day T+1: Apply signals using next day's returns
returns_t1 = price_data.loc[t+1, 'return']
pnl_t1 = signals_t * returns_t1  # Use .shift(-1) for proper alignment
```

### 8.2 Key Checks
- ✅ Volume divergence calculated using only past data (no future data)
- ✅ Signals generated at close of day T
- ✅ Positions executed at open of day T+1
- ✅ Returns from day T+1 used for P&L
- ✅ No future prices or volumes used in any calculation
- ✅ Volume moving averages use only historical data

---

## 9. Data Requirements

### 9.1 Input Data

**Source:** `data/raw/combined_coinbase_coinmarketcap_daily.csv`

**Required Fields:**
- `date`: Trading date (YYYY-MM-DD)
- `symbol`: Coin ticker (BTC, ETH, etc.)
- `close`: Closing price (levels, not returns)
- `volume`: Trading volume (USD or base currency)
- `market_cap`: Market capitalization (USD)

**Minimum History:**
- **Per Coin**: 60 days minimum
  - 30 days for divergence calculation
  - 30 days for backtest stability
- **Universe**: At least 30 coins with valid data at any time

### 9.2 Data Quality Filters

**Volume Filter:**
- 30-day average volume > $5M (default)
- Ensures liquidity for execution
- Filters out illiquid, unreliable volume data

**Market Cap Filter:**
- Market cap > $50M (default)
- Excludes micro-caps with poor data quality

**Data Completeness:**
- At least 80% of data points in calculation window
- Handles missing data gracefully
- Remove coins with excessive gaps

**Volume Outlier Detection:**
- Remove days with volume = 0 (exchange outages)
- Flag volume spikes > 10x average (potential data errors)
- Check for volume discontinuities (exchange listings/delistings)

**Price Outlier Detection:**
- Remove days with returns > ±50% (likely data errors)
- Check for price discontinuities

---

## 10. Risk Considerations

### 10.1 Strategy Risks

**Volume Data Quality:**
- Volume data less reliable than price data
- Exchange-reported volume may include wash trading
- Different exchanges report volume differently
- Solution: Use multiple volume filters, cross-check data sources

**Market Regime Dependency:**
- Volume patterns may differ in bull vs. bear markets
- High-volume moves in crashes may be different from rallies
- Solution: Test across multiple market cycles, regime-aware parameters

**Liquidity Risk:**
- Low-volume coins may have unreliable volume data
- Execution may differ from backtested prices
- Solution: Strict volume filters, minimum liquidity thresholds

**Flash Crashes:**
- Volume spikes during flash crashes can trigger false signals
- Extreme events may violate normal volume-price relationships
- Solution: Outlier detection, maximum position sizes

### 10.2 Implementation Risks

**Computational Cost:**
- Rolling correlations are computationally expensive
- Running for many coins daily may be slow
- Solution: Optimize code, use vectorized operations, cache results

**Volume Reporting Inconsistencies:**
- Some exchanges report volume in base currency, others in quote
- CMC vs. exchange-reported volume may differ
- Solution: Standardize volume to USD, use consistent data source

**Transaction Costs:**
- Frequent rebalancing = high fees
- Volume-based strategies may have higher turnover
- Solution: Longer rebalance periods (7-14 days), turnover limits

**Slippage on Low Volume:**
- Backtests assume perfect execution
- Real trades on low-volume coins face slippage
- Solution: Volume-weighted position sizing, execution cost modeling

---

## 11. Expected Insights

### 11.1 Key Questions

**1. Does volume confirmation predict continuation?**
- Do high divergence score moves continue?
- Is volume a reliable confirmation indicator?
- How strong is the predictive power?

**2. Does volume divergence predict reversals?**
- Do low-volume up moves reverse?
- Do high-volume down moves continue?
- Which divergence patterns are most predictive?

**3. How does volume momentum perform?**
- Does expanding volume precede breakouts?
- Does contracting volume signal consolidation?
- Optimal window for volume momentum?

**4. Price-volume correlation stability?**
- How stable is PVC over time?
- Does PVC vary by coin type?
- Regime-dependent correlations?

**5. Comparison to pure price-based factors?**
- Does volume add information beyond price?
- Orthogonal to momentum/trend factors?
- Combination strategies?

### 11.2 Success Criteria

**Minimum Viable Results:**
- **Sharpe Ratio**: > 0.7
- **Maximum Drawdown**: < 30%
- **Win Rate**: > 50%
- **Market Correlation**: < 0.4 (for market neutral)
- **Information Ratio vs. Price-Only**: > 0.5

**Stretch Goals:**
- **Sharpe Ratio**: > 1.2
- **Maximum Drawdown**: < 20%
- **Calmar Ratio**: > 0.6
- **Alpha vs BTC**: > 10% annualized
- **Positive in All Regimes**: Consistent performance
- **Additive to Other Factors**: Low correlation to beta, volatility, momentum

---

## 12. Implementation Roadmap

### Phase 1: Core Implementation (Week 1)
- [ ] Create `backtests/scripts/backtest_volume_divergence_factor.py`
- [ ] Implement volume divergence calculation functions
  - [ ] Price-Volume Correlation (PVC)
  - [ ] Volume Momentum Indicator (VMI)
  - [ ] Divergence Score (DS)
  - [ ] Volume-Price Ratio (VPR)
- [ ] Implement quintile ranking and selection
- [ ] Add equal-weight portfolio construction
- [ ] Validate no-lookahead bias (use `.shift(-1)`)
- [ ] Run baseline backtest: Confirmation Premium

### Phase 2: Testing & Validation (Week 1)
- [ ] Validate volume divergence calculations (manual spot checks)
- [ ] Check for data quality issues (zero volumes, outliers)
- [ ] Verify performance metrics calculations
- [ ] Test on different time periods (2020-2021, 2022-2023, 2024-2025)
- [ ] Analyze distribution of divergence metrics across coins

### Phase 3: Strategy Variants (Week 2)
- [ ] Implement all 4 strategy variants
- [ ] Add risk parity and volume-weighted options
- [ ] Test different rebalancing frequencies (3d, 7d, 14d, 30d)
- [ ] Test different lookback windows (15d, 30d, 60d, 90d)
- [ ] Compare strategy performance

### Phase 4: Analysis & Documentation (Week 2)
- [ ] Run all strategy variants
- [ ] Calculate correlation to BTC and other factors
- [ ] Compare to existing strategies (momentum, beta, volatility)
- [ ] Generate performance visualizations
- [ ] Analyze regime-dependent performance
- [ ] Document findings and recommendations
- [ ] Create results summary document

---

## 13. Integration with Existing System

### 13.1 Code Reuse

**Existing Utilities:**
- `backtests/scripts/backtest_volatility_factor.py` - Template structure, quintile ranking
- `backtests/scripts/backtest_beta_factor.py` - Portfolio construction
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

# Volume Divergence factor (new)
python3 backtest_volume_divergence_factor.py --start-date 2020-01-01
```

**Calculate factor correlation matrix:**
- Correlation of daily returns across factors
- Identify diversification opportunities
- Build multi-factor portfolio

**Multi-Factor Model:**
```python
# Combine volume divergence with other factors
portfolio_return = (
    0.25 * beta_factor_return +
    0.25 * volatility_factor_return +
    0.25 * volume_divergence_return +
    0.25 * momentum_factor_return
)
```

---

## 14. Academic References

### 14.1 Volume-Price Relationship

**Classic Technical Analysis:**
- Granville, J. E. (1963). "Granville's New Key to Stock Market Profits"
- Blume, L., Easley, D., & O'Hara, M. (1994). "Market Statistics and Technical Analysis: The Role of Volume". *Journal of Finance*.
- Karpoff, J. M. (1987). "The Relation Between Price Changes and Trading Volume: A Survey". *Journal of Financial and Quantitative Analysis*.

**Volume and Information:**
- Campbell, J. Y., Grossman, S. J., & Wang, J. (1993). "Trading Volume and Serial Correlation in Stock Returns". *Quarterly Journal of Economics*.
- Lee, C. M., & Swaminathan, B. (2000). "Price Momentum and Trading Volume". *Journal of Finance*.

### 14.2 Volume-Based Strategies

**On-Balance Volume (OBV):**
- Granville, J. E. (1976). "Granville's New Strategy of Daily Stock Market Timing for Maximum Profit"

**Volume Confirmation:**
- Arms, R. W. (1989). "The Arms Index (TRIN): An Introduction to the Volume Analysis of Stock and Bond Markets"

**Volume and Momentum:**
- Gervais, S., Kaniel, R., & Mingelgrin, D. H. (2001). "The High-Volume Return Premium". *Journal of Finance*.

### 14.3 Crypto-Specific

**Crypto Volume Analysis:**
- Caporale, G. M., & Plastun, A. (2019). "The Day of the Week Effect in the Cryptocurrency Market". *Finance Research Letters*.
- Balcilar, M., Bouri, E., Gupta, R., & Roubaud, D. (2017). "Can Volume Predict Bitcoin Returns and Volatility? A Quantiles-Based Approach". *Economic Modelling*.

**Wash Trading:**
- Cong, L. W., Li, X., Tang, K., & Yang, Y. (2020). "Crypto Wash Trading". *Working Paper*.

---

## 15. Example Usage

### Basic Backtest
```bash
# Run Confirmation Premium (baseline)
python3 backtests/scripts/backtest_volume_divergence_factor.py \
  --strategy confirmation_premium \
  --metric divergence_score \
  --lookback-window 30 \
  --rebalance-days 7
```

### Test Volume Momentum
```bash
python3 backtests/scripts/backtest_volume_divergence_factor.py \
  --strategy volume_momentum \
  --metric vmi \
  --vmi-short-window 10 \
  --vmi-long-window 30 \
  --rebalance-days 7
```

### Test Contrarian Divergence
```bash
python3 backtests/scripts/backtest_volume_divergence_factor.py \
  --strategy contrarian_divergence \
  --metric divergence_score \
  --lookback-window 30 \
  --rebalance-days 7
```

### Parameter Sensitivity
```bash
# Test different lookback windows
for window in 15 30 60 90; do
  python3 backtests/scripts/backtest_volume_divergence_factor.py \
    --strategy confirmation_premium \
    --lookback-window $window \
    --output-prefix backtest_volume_divergence_window_${window}
done
```

### Advanced Configuration
```bash
python3 backtests/scripts/backtest_volume_divergence_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy confirmation_premium \
  --metric divergence_score \
  --lookback-window 30 \
  --vmi-short-window 10 \
  --vmi-long-window 30 \
  --rebalance-days 7 \
  --long-percentile 20 \
  --short-percentile 80 \
  --weighting-method volume_weighted \
  --long-allocation 0.5 \
  --short-allocation 0.5 \
  --min-volume 10000000 \
  --min-market-cap 100000000 \
  --initial-capital 10000 \
  --leverage 1.0 \
  --start-date 2020-01-01 \
  --end-date 2025-10-28 \
  --output-prefix backtest_volume_divergence_custom
```

---

## 16. Visualization Examples

### Suggested Plots

**1. Volume Divergence Distribution**
```python
# Histogram of divergence scores across all coins and dates
plt.hist(df['divergence_score'].dropna(), bins=50)
plt.xlabel('Divergence Score')
plt.ylabel('Frequency')
plt.title('Distribution of Volume Divergence Scores')
```

**2. PVC Time Series**
```python
# Average PVC for long vs. short portfolios over time
plt.plot(long_portfolio['avg_pvc'], label='Long Portfolio')
plt.plot(short_portfolio['avg_pvc'], label='Short Portfolio')
plt.xlabel('Date')
plt.ylabel('Price-Volume Correlation')
plt.legend()
```

**3. Volume Expansion Analysis**
```python
# Scatter plot: VMI vs. future returns
plt.scatter(df['vmi'], df['forward_return_7d'], alpha=0.3)
plt.xlabel('Volume Momentum Indicator')
plt.ylabel('7-Day Forward Return')
plt.title('Volume Expansion vs. Future Returns')
```

**4. Confirmation vs. Divergence Performance**
```python
# Cumulative returns: High divergence score vs. Low divergence score
plt.plot(high_ds_returns.cumsum(), label='High Divergence Score (Confirmation)')
plt.plot(low_ds_returns.cumsum(), label='Low Divergence Score (Divergence)')
plt.xlabel('Date')
plt.ylabel('Cumulative Return')
plt.legend()
```

---

## 17. Next Steps

1. **Review Specification**: Validate approach and assumptions
2. **Implement Core Script**: Build `backtest_volume_divergence_factor.py` with all metrics
3. **Data Quality Check**: Analyze volume data quality, identify wash trading concerns
4. **Run Initial Backtest**: Test confirmation premium strategy
5. **Analyze Metric Distribution**: Understand cross-section of divergence patterns
6. **Test Hypotheses**: Does volume confirmation predict continuation?
7. **Compare Strategies**: Confirmation vs. momentum vs. contrarian
8. **Parameter Optimization**: Find optimal windows and thresholds
9. **Multi-Factor Integration**: Combine with beta, volatility, momentum factors
10. **Live Testing**: Paper trade the best strategy variant

---

**Document Owner:** Research Team  
**Last Updated:** 2025-10-28  
**Status:** Specification - Ready for Implementation  
**Next Step:** Implement Phase 1 (Core backtest script with all divergence metrics)

---

**Disclaimer:** This backtest is for research purposes only. Past performance does not guarantee future results. Cryptocurrency trading involves substantial risk of loss. Volume data quality varies across exchanges and may include wash trading or other manipulations. Always conduct thorough research and risk management before deploying capital.
