# Entropy Factor Trading Strategy Specification

**Version:** 1.0  
**Date:** 2025-10-27  
**Status:** Draft - Ready for Implementation

---

## 1. Executive Summary

This specification outlines a quantitative trading strategy based on the **entropy factor** for cryptocurrency returns. The core hypothesis is that coins with different levels of return entropy (randomness/unpredictability) exhibit predictable future performance patterns that can be exploited through a long/short portfolio strategy.

### Key Objectives
1. Calculate rolling entropy of returns for all cryptocurrencies
2. Rank coins by entropy values (information content/predictability)
3. Construct long/short portfolios based on entropy rankings
4. Backtest the strategy and evaluate risk-adjusted performance
5. Compare to existing factor strategies (volatility, kurtosis, skew)

### Strategy Overview
- **Factor**: Shannon entropy of return distribution (measure of randomness)
- **Universe**: All liquid cryptocurrencies with sufficient trading history
- **Rebalancing**: Weekly (configurable)
- **Market Neutrality**: Dollar-neutral long/short construction
- **Risk Management**: Risk parity weighting or equal weight

---

## 2. Strategy Description

### 2.1 Core Concept

**Entropy** measures the amount of uncertainty or randomness in a return distribution:

\[ H(X) = -\sum_{i=1}^{n} p(x_i) \log_2 p(x_i) \]

Where:
- \( H(X) \) = Shannon entropy (in bits)
- \( p(x_i) \) = Probability of return falling in bin i
- \( n \) = Number of bins in return distribution

**Interpretation:**
- **High Entropy**: Returns are unpredictable, uniform distribution, high randomness
- **Low Entropy**: Returns are predictable, concentrated distribution, low randomness
- **Maximum Entropy**: Uniform distribution (all outcomes equally likely)
- **Minimum Entropy**: Deterministic (one outcome certain)

### 2.2 Entropy vs. Volatility

**Key Distinction:**
- **Volatility**: Measures magnitude of price movements (standard deviation)
- **Entropy**: Measures unpredictability/randomness of price movements (information content)

**Example:**
- **High Vol, Low Entropy**: Large moves but predictable direction (trending)
- **High Vol, High Entropy**: Large moves in random directions (choppy)
- **Low Vol, High Entropy**: Small moves but unpredictable direction (noise)
- **Low Vol, Low Entropy**: Small moves in predictable direction (stable trend)

### 2.3 Strategy Hypothesis

Two potential hypotheses to test:

#### Hypothesis A: Mean Reversion of Entropy Regimes
- **Long**: High entropy coins (currently random/unpredictable) → Expect stabilization and trend formation
- **Short**: Low entropy coins (currently predictable) → Expect breakdown and increased randomness
- **Rationale**: Extreme entropy states tend to revert to normal

#### Hypothesis B: Momentum of Entropy Regimes
- **Long**: Low entropy coins (predictable/trending) → Expect continued trend and positive returns
- **Short**: High entropy coins (random/noisy) → Expect continued underperformance
- **Rationale**: Predictability attracts capital; randomness signals lack of conviction

### 2.4 Entropy Calculation

#### Method 1: Binned Shannon Entropy (Primary)

```python
import numpy as np
from scipy.stats import entropy as scipy_entropy

def calculate_shannon_entropy(returns, n_bins=10):
    """
    Calculate Shannon entropy of return distribution
    
    Parameters:
    - returns: Array of daily returns
    - n_bins: Number of bins for discretization (default: 10)
    
    Returns:
    - entropy: Shannon entropy in bits
    """
    # Remove NaN values
    returns_clean = returns[~np.isnan(returns)]
    
    if len(returns_clean) < 5:
        return np.nan
    
    # Create histogram (probability distribution)
    counts, bin_edges = np.histogram(returns_clean, bins=n_bins)
    
    # Convert to probabilities
    probabilities = counts / counts.sum()
    
    # Remove zero probabilities (log(0) is undefined)
    probabilities = probabilities[probabilities > 0]
    
    # Calculate Shannon entropy
    entropy = -np.sum(probabilities * np.log2(probabilities))
    
    return entropy

def calculate_rolling_entropy(returns, window=30, n_bins=10):
    """
    Calculate rolling entropy over a window
    
    Parameters:
    - returns: Series of daily returns
    - window: Rolling window in days (default: 30)
    - n_bins: Number of bins for discretization
    
    Returns:
    - Series of rolling entropy values
    """
    return returns.rolling(window).apply(
        lambda x: calculate_shannon_entropy(x, n_bins=n_bins),
        raw=True
    )
```

#### Method 2: Normalized Entropy (Alternative)

```python
def calculate_normalized_entropy(returns, n_bins=10):
    """
    Calculate normalized entropy (0 to 1 scale)
    Normalized by maximum possible entropy for n_bins
    
    Returns:
    - normalized_entropy: Entropy / log2(n_bins)
    """
    entropy = calculate_shannon_entropy(returns, n_bins=n_bins)
    max_entropy = np.log2(n_bins)  # Maximum possible entropy
    
    return entropy / max_entropy if max_entropy > 0 else np.nan
```

#### Method 3: Approximate Entropy (Advanced)

```python
def calculate_approximate_entropy(returns, m=2, r=0.2):
    """
    Calculate Approximate Entropy (ApEn)
    Measures regularity and unpredictability in time series
    
    Parameters:
    - returns: Array of returns
    - m: Pattern length (default: 2)
    - r: Tolerance (default: 0.2 * std(returns))
    
    More sophisticated metric for time series
    Better captures temporal patterns
    """
    # Implementation of Pincus (1991) approximate entropy
    # See references for full algorithm
    pass  # To be implemented if needed
```

### 2.5 Entropy Calculation Parameters

**Default Parameters:**
- **Lookback Window**: 30 days (~1 month)
  - Long enough to capture distribution
  - Short enough to detect regime changes
- **Number of Bins**: 10 bins
  - Balances resolution vs. sample size
  - Too few bins: Low resolution
  - Too many bins: Sparse probabilities
- **Return Type**: Daily log returns
- **Base**: Log base 2 (entropy in bits)

**Parameter Variations to Test:**
- **Window**: 20, 30, 60, 90 days
- **Bins**: 5, 10, 15, 20 bins
- **Return Transformation**: Raw, log, standardized

---

## 3. Signal Generation

### 3.1 Daily Signal Process

**Step 1: Calculate Returns**
```python
# Daily log returns
returns = np.log(close / close.shift(1))
```

**Step 2: Calculate Rolling Entropy**
```python
# 30-day rolling entropy
entropy_30d = calculate_rolling_entropy(returns, window=30, n_bins=10)
```

**Step 3: Filter Universe**
```python
# Apply liquidity and data quality filters
valid_coins = coins[
    (coins['volume_30d_avg'] > MIN_VOLUME) &
    (coins['market_cap'] > MIN_MARKET_CAP) &
    (coins['entropy_30d'].notna()) &
    (coins['data_completeness'] > 0.8)
]
```

**Step 4: Rank by Entropy**
```python
# Rank from low entropy to high entropy
# Rank 1 = lowest entropy (most predictable)
# Rank N = highest entropy (most random)
entropy_rank = valid_coins['entropy_30d'].rank(ascending=True)
```

**Step 5: Generate Signals**
```python
# Strategy A: Momentum (Baseline)
# Long low entropy (predictable/trending), Short high entropy (random/choppy)
if entropy_rank <= 20th_percentile:
    signal = LONG   # Low entropy = predictable = good
elif entropy_rank >= 80th_percentile:
    signal = SHORT  # High entropy = random = bad

# Strategy B: Mean Reversion (Alternative)
# Long high entropy (random → stabilize), Short low entropy (predictable → break down)
if entropy_rank >= 80th_percentile:
    signal = LONG   # High entropy = mean reversion expected
elif entropy_rank <= 20th_percentile:
    signal = SHORT  # Low entropy = breakdown expected
```

### 3.2 Entry Rules

**Rebalancing Schedule:**
- **Frequency**: Every 7 days (weekly, default)
- **Day**: Monday close (configurable)
- **Execution**: Assume next-day execution (avoid lookahead bias)

**Position Selection:**
- **Long Bucket**: Bottom (or top) quintile by entropy
- **Short Bucket**: Top (or bottom) quintile by entropy
- **Max Positions**: 10 longs + 10 shorts (configurable)
- **Min Entropy**: No minimum, but filter by data quality

**Filters:**
- **Minimum Volume**: 30-day avg volume > $5M (configurable)
- **Minimum Market Cap**: > $50M (configurable)
- **Data Quality**: At least 80% valid data in entropy window
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
- Strategy assumes entropy regime persistence

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
- Doesn't account for risk differences
- High-vol coins contribute more risk

#### Method 2: Risk Parity (Recommended)
```python
# Weight inversely proportional to volatility
# Each position contributes equal risk

volatility = returns.rolling(30).std() * np.sqrt(365)
inverse_vol = 1 / volatility
weights = (inverse_vol / inverse_vol.sum()) * allocation
```

**Pros:**
- Equalizes risk contribution
- More stable portfolio
- Better risk-adjusted returns

**Cons:**
- Requires volatility estimation
- More complex

#### Method 3: Entropy-Weighted (Experimental)
```python
# Weight inversely proportional to entropy
# Lower entropy = higher weight (reward predictability)

inverse_entropy = 1 / entropy
weights = (inverse_entropy / inverse_entropy.sum()) * allocation
```

**Pros:**
- Overweights predictable coins
- Directly exploits entropy signal

**Cons:**
- Can be unstable
- Low entropy coins may be illiquid

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
1. Calculate new entropy values
2. Rank all coins by entropy
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
4. Reduces turnover by ~40-60%
```

---

## 5. Backtest Implementation

### 5.1 File Structure

**Main Script:** `backtests/scripts/backtest_entropy_factor.py`

**Purpose:** Backtest engine for entropy-based strategies

**Output Directory:** `backtests/results/`

### 5.2 Command-Line Interface

```bash
python3 backtests/scripts/backtest_entropy_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy momentum \
  --entropy-window 30 \
  --entropy-bins 10 \
  --rebalance-days 7 \
  --weighting-method risk_parity \
  --long-allocation 0.5 \
  --short-allocation 0.5 \
  --start-date 2020-01-01 \
  --end-date 2025-10-27 \
  --output-prefix backtest_entropy_factor
```

### 5.3 Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--price-data` | (required) | Path to OHLCV CSV file |
| `--strategy` | `momentum` | Strategy variant: `momentum`, `mean_reversion`, `long_low_entropy`, `long_high_entropy` |
| `--entropy-window` | 30 | Entropy calculation window (days) |
| `--entropy-bins` | 10 | Number of bins for histogram |
| `--volatility-window` | 30 | Volatility window for risk parity (days) |
| `--rebalance-days` | 7 | Rebalance frequency (days) |
| `--num-quintiles` | 5 | Number of entropy buckets |
| `--long-percentile` | 20 | Percentile threshold for long (bottom 20%) |
| `--short-percentile` | 80 | Percentile threshold for short (top 20%) |
| `--weighting-method` | `equal_weight` | Weighting: `equal_weight`, `risk_parity`, `entropy_weighted` |
| `--min-volume` | 5000000 | Minimum 30d avg volume ($) |
| `--min-market-cap` | 50000000 | Minimum market cap ($) |
| `--initial-capital` | 10000 | Starting capital (USD) |
| `--leverage` | 1.0 | Leverage multiplier |
| `--long-allocation` | 0.5 | Long side allocation (50%) |
| `--short-allocation` | 0.5 | Short side allocation (50%) |
| `--start-date` | None | Backtest start (YYYY-MM-DD) |
| `--end-date` | None | Backtest end (YYYY-MM-DD) |
| `--output-prefix` | `backtest_entropy_factor` | Output file prefix |

### 5.4 Output Files

#### 1. Portfolio Values
**File:** `backtest_entropy_factor_portfolio_values.csv`

```csv
date,portfolio_value,cash,long_exposure,short_exposure,net_exposure,gross_exposure,num_longs,num_shorts
2020-01-01,10000.00,0.00,5000.00,-5000.00,0.00,10000.00,10,10
2020-01-08,10142.50,0.00,5071.25,-5071.25,0.00,10142.50,10,10
...
```

#### 2. Trade Log
**File:** `backtest_entropy_factor_trades.csv`

```csv
date,symbol,signal,entropy,entropy_rank,percentile,weight,position_size,market_cap,volume_30d_avg,volatility_30d
2020-01-08,BTC,LONG,1.25,5,10.2,0.11,550.00,180000000000,25000000000,0.45
2020-01-08,ETH,LONG,1.42,8,16.3,0.10,500.00,25000000000,8000000000,0.62
2020-01-08,DOGE,SHORT,2.95,48,98.0,0.08,-400.00,2000000000,500000000,1.85
...
```

#### 3. Performance Metrics
**File:** `backtest_entropy_factor_metrics.csv`

```csv
metric,value
initial_capital,10000.00
final_value,14532.25
total_return,0.4532
annualized_return,0.1842
annualized_volatility,0.2156
sharpe_ratio,0.854
sortino_ratio,1.125
max_drawdown,-0.1845
calmar_ratio,0.998
win_rate,0.5234
avg_long_positions,9.5
avg_short_positions,9.2
avg_long_entropy,1.35
avg_short_entropy,2.75
total_rebalances,78
trading_days,574
```

#### 4. Entropy Time Series
**File:** `backtest_entropy_factor_entropy_timeseries.csv`

```csv
date,symbol,entropy,entropy_rank,percentile,returns_30d_mean,returns_30d_std,volume_30d_avg,market_cap
2020-01-08,BTC,1.25,5,10.2,0.0012,0.035,25000000000,180000000000
2020-01-08,ETH,1.42,8,16.3,0.0018,0.042,8000000000,25000000000
...
```

#### 5. Strategy Info
**File:** `backtest_entropy_factor_strategy_info.csv`

```csv
strategy,entropy_window,entropy_bins,rebalance_days,weighting_method,long_symbols,short_symbols,avg_long_entropy,avg_short_entropy
momentum,30,10,7,risk_parity,"BTC,ETH,SOL,...","DOGE,SHIB,PEPE,...",1.35,2.75
```

---

## 6. Strategy Variants

### 6.1 Momentum Strategy (Baseline)
**Name:** `momentum`

**Configuration:**
- Long: Bottom quintile (low entropy, predictable)
- Short: Top quintile (high entropy, random)
- Allocation: 50% long, 50% short
- Market Neutral: Yes

**Hypothesis:** Low entropy (predictable) coins outperform high entropy (random) coins

**Expected Outcome:**
- Positive returns if predictability is rewarded
- Low correlation to BTC
- Stable risk-adjusted performance

### 6.2 Mean Reversion Strategy
**Name:** `mean_reversion`

**Configuration:**
- Long: Top quintile (high entropy, random)
- Short: Bottom quintile (low entropy, predictable)
- Allocation: 50% long, 50% short
- Market Neutral: Yes

**Hypothesis:** Extreme entropy states revert to normal

**Expected Outcome:**
- Positive returns if entropy mean-reverts
- May underperform momentum strategy
- Higher volatility

### 6.3 Long Low Entropy Only
**Name:** `long_low_entropy`

**Configuration:**
- Long: Bottom quintile (low entropy)
- Short: None (50% cash)
- Allocation: 50% long, 0% short
- Market Neutral: No

**Hypothesis:** Predictable coins generate consistent returns

**Expected Outcome:**
- Lower volatility than market
- Positive but modest returns
- Defensive positioning

### 6.4 Long High Entropy Only
**Name:** `long_high_entropy`

**Configuration:**
- Long: Top quintile (high entropy)
- Short: None (50% cash)
- Allocation: 50% long, 0% short
- Market Neutral: No

**Hypothesis:** Random coins are undervalued (contrarian)

**Expected Outcome:**
- Higher volatility
- Potentially higher returns if mean reversion works
- Risky positioning

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

### 7.3 Entropy-Specific Metrics
- **Average Long Entropy**: Mean entropy of long positions
- **Average Short Entropy**: Mean entropy of short positions
- **Entropy Spread**: Long entropy - Short entropy
- **Entropy Stability**: Correlation of entropy ranks period-to-period
- **Entropy vs Returns**: Correlation between entropy and future returns

### 7.4 Trading Metrics
- **Win Rate**: % of profitable rebalancing periods
- **Average Turnover**: % of portfolio traded per rebalance
- **Number of Rebalances**: Total rebalancing events
- **Avg Long Positions**: Average number of long positions
- **Avg Short Positions**: Average number of short positions
- **Hit Ratio**: % of correct long/short calls

### 7.5 Comparison Metrics
- **BTC Correlation**: Correlation of strategy returns to BTC
- **Alpha vs BTC**: Excess return over BTC buy-and-hold
- **Correlation to Volatility Factor**: Independence from vol factor
- **Correlation to Kurtosis Factor**: Independence from tail risk factor

---

## 8. No-Lookahead Bias Prevention

**Critical Rule:** Signals on day T use returns from day T+1

### 8.1 Implementation

```python
# Day T: Calculate entropy using data up to day T
entropy_t = calculate_rolling_entropy(
    returns.loc[:t], 
    window=30,
    n_bins=10
)

# Day T: Rank coins and generate signals
signals_t = generate_signals(entropy_t)

# Day T+1: Apply signals using next day's returns
returns_t1 = price_data.loc[t+1, 'return']
pnl_t1 = signals_t * returns_t1  # Use .shift(-1) for proper alignment
```

### 8.2 Key Checks
- ✅ Entropy calculated using only past returns (no future data)
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
- `close`: Closing price
- `volume`: Trading volume (USD)
- `market_cap`: Market capitalization (USD)

**Minimum History:**
- **Per Coin**: 60 days minimum
  - 30 days for entropy calculation
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
- At least 80% of data points in entropy window
- Handles missing data gracefully

**Outlier Detection:**
- Remove days with returns > ±50% (likely data errors)
- Flag coins with excessive missing data

---

## 10. Risk Considerations

### 10.1 Strategy Risks

**Entropy Instability:**
- Entropy can change rapidly during market events
- High entropy coins can suddenly become low entropy
- Solution: Regular rebalancing, longer entropy windows

**Bin Selection Sensitivity:**
- Number of bins affects entropy calculation
- Too few bins: Poor resolution
- Too many bins: Sparse probabilities, noisy estimates
- Solution: Test multiple bin configurations (5, 10, 15, 20)

**Sample Size Issues:**
- 30-day window may be too short for reliable entropy
- Small sample → unreliable probability estimates
- Solution: Test longer windows (60d, 90d)

**Market Regime Dependency:**
- Entropy interpretation may vary by market regime
- Bull market: Low entropy = strong trend (good)
- Bear market: Low entropy = strong downtrend (bad)
- Solution: Test across multiple market cycles

**Correlation with Volatility:**
- Entropy and volatility may be correlated
- May not provide independent alpha
- Solution: Calculate factor correlation matrix

### 10.2 Implementation Risks

**Execution Risk:**
- Slippage on rebalancing
- Market impact for large positions
- Solution: VWAP execution, split orders

**Transaction Costs:**
- Frequent rebalancing = high fees
- Solution: Longer rebalance periods (14d, 30d)

**Computational Complexity:**
- Entropy calculation more complex than simple stats
- May slow down backtests
- Solution: Optimize code, use vectorization

---

## 11. Expected Insights

### 11.1 Key Questions

**1. Does entropy predict returns?**
- Is there a relationship between current entropy and future returns?
- Which direction: momentum or mean reversion?

**2. Is entropy different from volatility?**
- Do entropy and volatility capture different information?
- What is the correlation between entropy and volatility factors?

**3. Does entropy vary by coin type?**
- DeFi vs. L1 vs. Meme coins?
- Market cap buckets?
- Different entropy characteristics?

**4. Is entropy stable over time?**
- How much does entropy fluctuate?
- Are high-entropy coins persistently high-entropy?
- Entropy rank correlation across periods?

**5. How does entropy relate to market regimes?**
- Bull markets: What entropy patterns?
- Bear markets: What entropy patterns?
- High vol: Does entropy increase?

### 11.2 Success Criteria

**Minimum Viable Results:**
- **Sharpe Ratio**: > 0.5
- **Maximum Drawdown**: < 40%
- **Win Rate**: > 48%
- **Low BTC Correlation**: < 0.4
- **Independent from Volatility Factor**: Correlation < 0.6

**Stretch Goals:**
- **Sharpe Ratio**: > 1.0
- **Maximum Drawdown**: < 30%
- **Calmar Ratio**: > 0.5
- **Alpha vs Volatility Factor**: > 5% annualized
- **Positive in All Regimes**: Works in bull and bear markets

### 11.3 Comparison Benchmarks

**Factor Strategies:**
- Volatility factor (realized vol)
- Kurtosis factor (tail risk)
- Skewness factor (asymmetry)
- Beta factor (systematic risk)

**Market Benchmarks:**
- BTC buy-and-hold
- Equal-weight crypto index
- Market-cap-weight crypto index

---

## 12. Implementation Roadmap

### Phase 1: Core Implementation (Week 1)
- [ ] Create `backtests/scripts/backtest_entropy_factor.py`
- [ ] Implement Shannon entropy calculation function
- [ ] Implement rolling entropy calculation
- [ ] Implement quintile ranking and selection
- [ ] Add equal-weight portfolio construction
- [ ] Validate no-lookahead bias (use `.shift(-1)`)

### Phase 2: Testing & Validation (Week 1)
- [ ] Run baseline backtest: Momentum strategy
- [ ] Validate entropy calculations (manual spot checks)
- [ ] Check for data quality issues
- [ ] Verify performance metrics calculations
- [ ] Test on different time periods
- [ ] Analyze entropy distribution across coins

### Phase 3: Strategy Variants (Week 2)
- [ ] Implement all 4 strategy variants
- [ ] Add risk parity weighting option
- [ ] Test different rebalancing frequencies (7d, 14d, 30d)
- [ ] Test different entropy windows (20d, 30d, 60d, 90d)
- [ ] Test different bin configurations (5, 10, 15, 20 bins)
- [ ] Parameter sensitivity analysis

### Phase 4: Analysis & Documentation (Week 2)
- [ ] Compare all strategy variants
- [ ] Calculate correlation to volatility/kurtosis factors
- [ ] Analyze entropy vs. returns relationship
- [ ] Generate entropy distribution visualizations
- [ ] Create comprehensive summary report
- [ ] Document findings and recommendations

---

## 13. Integration with Existing System

### 13.1 Code Reuse

**Existing Utilities:**
- `backtests/scripts/backtest_volatility_factor.py` - Template structure
- `backtests/scripts/backtest_kurtosis_factor.py` - Similar higher-moment factor
- `signals/calc_vola.py` - Volatility calculation (for risk parity)
- `signals/calc_weights.py` - Risk parity weight calculation

**Data Integration:**
- Use existing: `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- Same CSV format and naming conventions
- Store outputs in: `backtests/results/`

### 13.2 Comparison Framework

**Run all factors on same time period:**
```bash
# Volatility factor
python3 backtest_volatility_factor.py --start-date 2020-01-01

# Kurtosis factor
python3 backtest_kurtosis_factor.py --start-date 2020-01-01

# Entropy factor (new)
python3 backtest_entropy_factor.py --start-date 2020-01-01
```

**Calculate factor correlation matrix:**
- Correlation of daily returns across factors
- Identify diversification opportunities
- Build multi-factor portfolio

---

## 14. Academic References

### 14.1 Information Theory
- **Shannon, C. E. (1948).** "A Mathematical Theory of Communication". *Bell System Technical Journal*.
- **Cover, T. M., & Thomas, J. A. (2006).** "Elements of Information Theory". *Wiley*.

### 14.2 Entropy in Finance
- **Philippatos, G. C., & Wilson, C. J. (1972).** "Entropy, Market Risk, and the Selection of Efficient Portfolios". *Applied Economics*.
- **Maasoumi, E., & Racine, J. (2002).** "Entropy and Predictability of Stock Market Returns". *Journal of Econometrics*.
- **Zhou, R., Cai, R., & Tong, G. (2013).** "Applications of Entropy in Finance: A Review". *Entropy*.

### 14.3 Crypto-Specific
- **Pele, D. T., Lazar, E., & Dufour, A. (2017).** "Information Entropy and Measures of Market Risk". *Entropy*.
- **Bariviera, A. F. (2017).** "The Inefficiency of Bitcoin Revisited: A Dynamic Approach". *Economics Letters*.

---

## 15. Example Usage

### Basic Backtest
```bash
# Run momentum strategy (baseline)
python3 backtests/scripts/backtest_entropy_factor.py \
  --strategy momentum \
  --entropy-window 30 \
  --entropy-bins 10 \
  --rebalance-days 7
```

### Test Mean Reversion Strategy
```bash
python3 backtests/scripts/backtest_entropy_factor.py \
  --strategy mean_reversion \
  --entropy-window 30 \
  --entropy-bins 10 \
  --rebalance-days 7
```

### Parameter Sensitivity Run
```bash
# Test different entropy windows
for window in 20 30 60 90; do
  python3 backtests/scripts/backtest_entropy_factor.py \
    --strategy momentum \
    --entropy-window $window \
    --output-prefix backtests/results/entropy_factor_window_${window}
done

# Test different bin configurations
for bins in 5 10 15 20; do
  python3 backtests/scripts/backtest_entropy_factor.py \
    --strategy momentum \
    --entropy-bins $bins \
    --output-prefix backtests/results/entropy_factor_bins_${bins}
done
```

### Advanced Configuration
```bash
python3 backtests/scripts/backtest_entropy_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy momentum \
  --entropy-window 60 \
  --entropy-bins 15 \
  --volatility-window 30 \
  --rebalance-days 14 \
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
  --output-prefix backtests/results/entropy_factor_custom
```

---

## 16. Next Steps

1. **Review specification**: Validate approach and assumptions
2. **Implement core script**: Start with momentum strategy
3. **Validate entropy calculation**: Test on sample data
4. **Run initial backtest**: Generate first results
5. **Analyze entropy distribution**: Understand cross-section of entropy
6. **Test hypothesis**: Does entropy predict returns?
7. **Compare strategies**: Momentum vs. mean reversion
8. **Parameter optimization**: Find optimal window and bins
9. **Multi-factor integration**: Combine with volatility, kurtosis factors

---

**Document Owner:** Research Team  
**Last Updated:** 2025-10-27  
**Status:** Draft - Ready for Implementation  
**Next Step:** Implement Phase 1 (Core backtest script)

---

**Disclaimer:** This backtest is for research purposes only. Past performance does not guarantee future results. Cryptocurrency trading involves substantial risk of loss. Entropy-based strategies are experimental and may not work in real markets. Always conduct thorough research and risk management before deploying capital.
