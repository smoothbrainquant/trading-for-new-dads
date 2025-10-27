# Beta Factor Backtest Strategy

**Version:** 1.0  
**Date:** 2025-10-27  
**Status:** Specification - Ready for Implementation

---

## 1. Executive Summary

This specification outlines a quantitative trading strategy based on the **beta factor** for cryptocurrencies. The core hypothesis tests whether coins with different beta exposures to Bitcoin (BTC) exhibit predictable return patterns that can be exploited through long/short portfolio construction.

### Key Objectives
1. Calculate rolling beta to BTC for all cryptocurrencies
2. Rank coins by beta values (systematic risk exposure)
3. Construct long/short portfolios based on beta rankings
4. Test "Betting Against Beta" (BAB) hypothesis in crypto markets
5. Compare performance to existing factor strategies

### Strategy Overview
- **Factor**: Beta to BTC (systematic risk measure)
- **Universe**: All liquid cryptocurrencies with sufficient trading history
- **Rebalancing**: Weekly (configurable)
- **Market Neutrality**: Dollar-neutral long/short construction
- **Risk Management**: Risk parity weighting or equal weight

---

## 2. Strategy Description

### 2.1 Core Concept

**Beta** measures an asset's systematic risk relative to a benchmark (Bitcoin):

\[ \beta_i = \frac{\text{Cov}(R_i, R_{BTC})}{\text{Var}(R_{BTC})} \]

Where:
- \( R_i \) = Returns of coin i
- \( R_{BTC} \) = Returns of Bitcoin
- **Beta = 1**: Coin moves in line with BTC
- **Beta > 1**: Coin is more volatile than BTC (high beta)
- **Beta < 1**: Coin is less volatile than BTC (low beta)
- **Beta < 0**: Coin moves inverse to BTC (rare, but possible)

### 2.2 Strategy Hypothesis

Two competing hypotheses from traditional finance:

#### Hypothesis A: Betting Against Beta (BAB)
- **Long**: Low beta coins (defensive, stable)
- **Short**: High beta coins (aggressive, volatile)
- **Rationale**: Low beta assets historically outperform high beta assets on risk-adjusted basis
- **Academic Backing**: Frazzini & Pedersen (2014) "Betting Against Beta"

**Why this works in traditional finance:**
1. **Leverage Constraints**: Investors can't leverage, so they buy high-beta assets to increase exposure
2. **Behavioral Bias**: Preference for "lottery-like" payoffs drives demand for high-beta stocks
3. **Result**: High-beta assets become overvalued, low-beta assets undervalued

#### Hypothesis B: Traditional Risk Premium
- **Long**: High beta coins (aggressive, high systematic risk)
- **Short**: Low beta coins (defensive, low systematic risk)
- **Rationale**: Higher systematic risk should be compensated with higher returns (CAPM prediction)
- **Academic Backing**: Traditional Capital Asset Pricing Model (CAPM)

**Expected in rational markets:**
1. Higher risk → Higher expected returns
2. Beta measures systematic (non-diversifiable) risk
3. Investors demand compensation for bearing beta risk

### 2.3 Crypto Market Application

**Why BAB might work in crypto:**
1. **Retail Dominance**: Crypto markets are retail-heavy, behavioral biases pronounced
2. **Leverage Availability**: Perpetual futures make leverage easy, but retail may not use optimally
3. **Attention Seeking**: High-beta altcoins attract attention, potentially overvalued
4. **BTC as Safe Haven**: Low-beta coins behave like defensive assets in crypto ecosystem

**Why traditional risk premium might work:**
1. **Emerging Market**: Higher risk assets command premium in developing markets
2. **Maturation**: As market matures, rational risk pricing may emerge
3. **Institutional Entry**: Professional investors price risk more efficiently

### 2.4 Beta Calculation

#### Method: Rolling OLS Regression

```python
import numpy as np
import pandas as pd
from scipy import stats

def calculate_rolling_beta(coin_returns, btc_returns, window=90):
    """
    Calculate rolling beta using OLS regression
    
    Beta = Cov(R_coin, R_btc) / Var(R_btc)
    
    Parameters:
    - coin_returns: Series of daily returns for coin
    - btc_returns: Series of daily returns for BTC
    - window: Rolling window in days (default: 90 days ~3 months)
    
    Returns:
    - Series of rolling beta values
    """
    def ols_beta(y, x):
        # Remove NaN values
        mask = ~(np.isnan(x) | np.isnan(y))
        if mask.sum() < window * 0.7:  # Require 70% data availability
            return np.nan
        x_clean = x[mask]
        y_clean = y[mask]
        
        # Calculate beta using covariance method
        covariance = np.cov(y_clean, x_clean)[0, 1]
        variance = np.var(x_clean)
        
        if variance == 0:
            return np.nan
            
        return covariance / variance
    
    # Align the series
    aligned = pd.DataFrame({
        'coin': coin_returns,
        'btc': btc_returns
    })
    
    # Calculate rolling beta
    beta = aligned.rolling(window).apply(
        lambda x: ols_beta(x['coin'].values, x['btc'].values),
        raw=False
    )
    
    return beta['coin']
```

#### Alternative: Covariance Method

```python
def calculate_rolling_beta_cov(coin_returns, btc_returns, window=90):
    """
    Calculate rolling beta using covariance method (simpler)
    """
    # Calculate rolling covariance and variance
    rolling_cov = coin_returns.rolling(window).cov(btc_returns)
    rolling_var = btc_returns.rolling(window).var()
    
    # Beta = Covariance / Variance
    beta = rolling_cov / rolling_var
    
    return beta
```

### 2.5 Beta Calculation Parameters

**Default Parameters:**
- **Lookback Window**: 90 days (~3 months)
  - Long enough to be stable
  - Short enough to capture regime changes
- **Minimum Data**: 63 days (70% of 90 days)
- **Return Frequency**: Daily log returns
- **Benchmark**: Bitcoin (BTC) spot price

**Parameter Variations to Test:**
- **30-day beta**: More reactive, higher turnover
- **60-day beta**: Balanced
- **90-day beta**: Baseline, stable
- **180-day beta**: Very stable, slow to adapt

---

## 3. Signal Generation

### 3.1 Daily Signal Process

**Step 1: Calculate BTC Returns**
```python
btc_returns = np.log(btc_close / btc_close.shift(1))
```

**Step 2: Calculate Coin Returns**
```python
coin_returns = np.log(coin_close / coin_close.shift(1))
```

**Step 3: Calculate Rolling Beta**
```python
beta = calculate_rolling_beta(coin_returns, btc_returns, window=90)
```

**Step 4: Filter Universe**
```python
# Apply liquidity and data quality filters
valid_coins = coins[
    (coins['volume_30d_avg'] > MIN_VOLUME) &
    (coins['market_cap'] > MIN_MARKET_CAP) &
    (coins['beta'].notna()) &
    (coins['data_quality'] > 0.7)
]
```

**Step 5: Rank by Beta**
```python
# Rank from low beta to high beta
# Rank 1 = lowest beta (most defensive)
# Rank N = highest beta (most aggressive)
beta_rank = valid_coins['beta'].rank(ascending=True)
```

**Step 6: Generate Signals**
```python
# Strategy A: Betting Against Beta (BAB)
# Long bottom quintile (low beta), Short top quintile (high beta)
if beta_rank <= 20th_percentile:
    signal = LONG  # Low beta = defensive
elif beta_rank >= 80th_percentile:
    signal = SHORT  # High beta = aggressive

# Strategy B: Traditional Risk Premium
# Long top quintile (high beta), Short bottom quintile (low beta)
if beta_rank >= 80th_percentile:
    signal = LONG  # High beta = high risk premium
elif beta_rank <= 20th_percentile:
    signal = SHORT  # Low beta = low risk premium
```

### 3.2 Entry Rules

**Rebalancing Schedule:**
- **Frequency**: Every 7 days (weekly, default)
- **Day**: Monday close (configurable)
- **Execution**: Assume next-day execution (avoid lookahead bias)

**Position Selection:**
- **Long Bucket**: Bottom (or top) quintile by beta
- **Short Bucket**: Top (or bottom) quintile by beta
- **Max Positions**: 10 longs + 10 shorts (configurable)
- **Min Beta**: No minimum, but filter by data quality

**Filters:**
- **Minimum Volume**: 30-day avg volume > $5M (configurable)
- **Minimum Market Cap**: > $50M (configurable)
- **Data Quality**: At least 70% valid data in beta window
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
- Strategy assumes mean reversion in beta

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

#### Method 3: Beta-Weighted (Experimental)
```python
# Weight inversely proportional to beta
# Neutralizes BTC exposure

inverse_beta = 1 / np.abs(beta)
weights = (inverse_beta / inverse_beta.sum()) * allocation
```

**Pros:**
- True market neutrality (zero BTC beta)
- Isolates alpha from beta exposure

**Cons:**
- Low beta coins get very high weights
- Can be unstable

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
1. Calculate new beta values
2. Rank all coins by beta
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

**Main Script:** `backtests/scripts/backtest_beta_factor.py`

**Purpose:** Backtest engine for beta-based strategies

**Output Directory:** `backtests/results/`

### 5.2 Command-Line Interface

```bash
python3 backtests/scripts/backtest_beta_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy betting_against_beta \
  --beta-window 90 \
  --rebalance-days 7 \
  --weighting-method risk_parity \
  --long-allocation 0.5 \
  --short-allocation 0.5 \
  --start-date 2020-01-01 \
  --end-date 2025-10-27 \
  --output-prefix backtest_beta_factor
```

### 5.3 Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--price-data` | (required) | Path to OHLCV CSV file |
| `--strategy` | `betting_against_beta` | Strategy variant: `betting_against_beta`, `traditional_risk_premium`, `long_low_beta`, `long_high_beta` |
| `--beta-window` | 90 | Beta calculation window (days) |
| `--volatility-window` | 30 | Volatility window for risk parity (days) |
| `--rebalance-days` | 7 | Rebalance frequency (days) |
| `--num-quintiles` | 5 | Number of beta buckets |
| `--long-percentile` | 20 | Percentile threshold for long (bottom 20%) |
| `--short-percentile` | 80 | Percentile threshold for short (top 20%) |
| `--weighting-method` | `equal_weight` | Weighting: `equal_weight`, `risk_parity`, `beta_weighted` |
| `--min-volume` | 5000000 | Minimum 30d avg volume ($) |
| `--min-market-cap` | 50000000 | Minimum market cap ($) |
| `--initial-capital` | 10000 | Starting capital (USD) |
| `--leverage` | 1.0 | Leverage multiplier |
| `--long-allocation` | 0.5 | Long side allocation (50%) |
| `--short-allocation` | 0.5 | Short side allocation (50%) |
| `--start-date` | None | Backtest start (YYYY-MM-DD) |
| `--end-date` | None | Backtest end (YYYY-MM-DD) |
| `--output-prefix` | `backtest_beta_factor` | Output file prefix |

### 5.4 Output Files

#### 1. Portfolio Values
**File:** `backtest_beta_factor_portfolio_values.csv`

```csv
date,portfolio_value,cash,long_exposure,short_exposure,net_exposure,gross_exposure,num_longs,num_shorts,portfolio_beta
2020-01-01,10000.00,0.00,5000.00,-5000.00,0.00,10000.00,10,10,0.02
2020-01-08,10150.25,0.00,5075.13,-5075.13,0.00,10150.25,10,10,-0.01
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
- `portfolio_beta`: Portfolio beta to BTC (should be ~0 for market neutral)

#### 2. Trade Log
**File:** `backtest_beta_factor_trades.csv`

```csv
date,symbol,signal,beta,beta_rank,percentile,weight,position_size,market_cap,volume_30d_avg,volatility_30d
2020-01-08,BTC,LONG,0.35,3,6.1,0.11,550.00,180000000000,25000000000,0.45
2020-01-08,ETH,LONG,0.42,5,10.2,0.10,500.00,25000000000,8000000000,0.62
2020-01-08,DOGE,SHORT,2.85,48,98.0,0.08,-400.00,2000000000,500000000,1.85
...
```

#### 3. Performance Metrics
**File:** `backtest_beta_factor_metrics.csv`

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
avg_long_beta,0.38
avg_short_beta,1.85
portfolio_beta_avg,0.02
total_rebalances,78
trading_days,547
```

#### 4. Beta Time Series
**File:** `backtest_beta_factor_beta_timeseries.csv`

```csv
date,symbol,beta,beta_rank,percentile,returns_90d_mean,returns_90d_std,volume_30d_avg,market_cap
2020-01-08,BTC,0.35,3,6.1,0.0018,0.042,25000000000,180000000000
2020-01-08,ETH,0.42,5,10.2,0.0022,0.055,8000000000,25000000000
...
```

#### 5. Strategy Info
**File:** `backtest_beta_factor_strategy_info.csv`

```csv
strategy,beta_window,rebalance_days,weighting_method,long_symbols,short_symbols,avg_long_beta,avg_short_beta
betting_against_beta,90,7,risk_parity,"BTC,ETH,USDC,...","DOGE,SHIB,APE,...",0.38,1.85
```

---

## 6. Strategy Variants

### 6.1 Betting Against Beta (BAB) - Primary Strategy
**Name:** `betting_against_beta`

**Configuration:**
- Long: Bottom quintile (low beta, defensive)
- Short: Top quintile (high beta, aggressive)
- Allocation: 50% long, 50% short
- Market Neutral: Yes

**Hypothesis:** Low beta coins outperform high beta coins on risk-adjusted basis

**Expected Outcome:**
- Low correlation to BTC
- Stable returns
- Positive Sharpe ratio if anomaly exists

### 6.2 Traditional Risk Premium
**Name:** `traditional_risk_premium`

**Configuration:**
- Long: Top quintile (high beta, aggressive)
- Short: Bottom quintile (low beta, defensive)
- Allocation: 50% long, 50% short
- Market Neutral: Yes

**Hypothesis:** High beta coins earn risk premium (CAPM prediction)

**Expected Outcome:**
- Higher returns if traditional theory holds
- Higher volatility
- Positive correlation to BTC

### 6.3 Long Low Beta Only
**Name:** `long_low_beta`

**Configuration:**
- Long: Bottom quintile (low beta)
- Short: None (50% cash)
- Allocation: 50% long, 0% short
- Market Neutral: No

**Hypothesis:** Defensive positioning in crypto

**Expected Outcome:**
- Lower volatility than BTC
- Positive but modest returns
- Outperforms in bear markets

### 6.4 Long High Beta Only
**Name:** `long_high_beta`

**Configuration:**
- Long: Top quintile (high beta)
- Short: None (50% cash)
- Allocation: 50% long, 0% short
- Market Neutral: No

**Hypothesis:** High beta = high returns (aggressive positioning)

**Expected Outcome:**
- Higher volatility than BTC
- Amplified returns in bull markets
- Large drawdowns in bear markets

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

### 7.3 Beta-Specific Metrics
- **Portfolio Beta**: Weighted average beta of all positions
- **Long Beta**: Average beta of long positions
- **Short Beta**: Average beta of short positions
- **Beta Neutrality**: Abs(portfolio beta) (should be ~0)
- **BTC Correlation**: Correlation of strategy returns to BTC
- **Alpha vs BTC**: Excess return over BTC buy-and-hold

### 7.4 Trading Metrics
- **Win Rate**: % of profitable rebalancing periods
- **Average Turnover**: % of portfolio traded per rebalance
- **Number of Rebalances**: Total rebalancing events
- **Avg Long Positions**: Average number of long positions
- **Avg Short Positions**: Average number of short positions
- **Hit Ratio**: % of correct long/short calls

### 7.5 Regime Analysis
- **Bull Market Performance**: Returns when BTC > 200d MA
- **Bear Market Performance**: Returns when BTC < 200d MA
- **High Vol Performance**: Returns when BTC 30d vol > median
- **Low Vol Performance**: Returns when BTC 30d vol < median

---

## 8. No-Lookahead Bias Prevention

**Critical Rule:** Signals on day T use returns from day T+1

### 8.1 Implementation

```python
# Day T: Calculate beta using data up to day T
beta_t = calculate_beta(
    coin_returns.loc[:t], 
    btc_returns.loc[:t], 
    window=90
)

# Day T: Rank coins and generate signals
signals_t = generate_signals(beta_t)

# Day T+1: Apply signals using next day's returns
returns_t1 = price_data.loc[t+1, 'return']
pnl_t1 = signals_t * returns_t1  # Use .shift(-1) for proper alignment
```

### 8.2 Key Checks
- ✅ Beta calculated using only past returns (no future data)
- ✅ Signals generated at close of day T
- ✅ Positions executed at open of day T+1 (or close of day T+1 for simplicity)
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
  - 90 days for beta calculation
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
- At least 70% of data points in beta window
- Handles missing data gracefully (skip vs. forward-fill)

**Outlier Detection:**
- Remove days with returns > ±50% (likely data errors)
- Cap returns at ±25% for beta calculation (optional)

---

## 10. Risk Considerations

### 10.1 Strategy Risks

**Beta Instability:**
- Beta can change rapidly during market events
- Low beta coins can become high beta (regime shift)
- Solution: Regular rebalancing, longer beta windows

**Leverage in Crypto:**
- Many crypto investors use leverage
- May nullify leverage constraint hypothesis
- BAB may not work as well as in equities

**Liquidity Risk:**
- Low beta coins may be less liquid
- High beta coins may have better liquidity
- Solution: Strict volume filters, risk parity weighting

**Market Regime Dependency:**
- BAB may only work in specific market conditions
- May underperform in strong bull markets (missing upside)
- Solution: Test across multiple market cycles

**Funding Costs:**
- Shorting high-beta coins may be expensive (funding rates)
- Can erode returns in long short strategies
- Solution: Monitor funding rates, adjust exposure

### 10.2 Implementation Risks

**Execution Risk:**
- Slippage on rebalancing
- Market impact for large positions
- Solution: VWAP execution, split orders

**Transaction Costs:**
- Frequent rebalancing = high fees
- Solution: Longer rebalance periods (14d, 30d)

**Short Availability:**
- Not all coins available to short
- Borrow costs can be high
- Solution: Use perpetual futures, factor in funding

---

## 11. Expected Insights

### 11.1 Key Questions

**1. Does the BAB anomaly exist in crypto?**
- Do low beta coins outperform high beta coins?
- Is the effect statistically significant?
- How does magnitude compare to traditional finance?

**2. Is beta stable over time?**
- How much does beta fluctuate?
- Are low beta coins persistently low beta?
- Beta rank correlation across periods?

**3. Does beta vary by coin type?**
- DeFi vs. L1 vs. Meme coins?
- Market cap buckets?
- Different beta characteristics?

**4. How does beta correlate with other factors?**
- Beta vs. size factor?
- Beta vs. momentum?
- Beta vs. volatility?
- Independent alpha source?

**5. Does regime matter?**
- Bull markets: High beta outperforms?
- Bear markets: Low beta defensive?
- High vol: Beta spreads widen?

### 11.2 Success Criteria

**Minimum Viable Results:**
- **Sharpe Ratio**: > 0.7
- **Maximum Drawdown**: < 30%
- **Win Rate**: > 50%
- **BTC Correlation**: < 0.4 (for market neutral)
- **Portfolio Beta**: < 0.1 (near-zero beta exposure)

**Stretch Goals:**
- **Sharpe Ratio**: > 1.2
- **Maximum Drawdown**: < 20%
- **Calmar Ratio**: > 0.6
- **Alpha vs BTC**: > 10% annualized
- **Positive in Bear Markets**: Outperform BTC when BTC < 0

### 11.3 Comparison Benchmarks

**Factor Strategies:**
- Size factor (market cap)
- Momentum factor (past returns)
- Volatility factor (realized vol)
- Kurtosis factor (tail risk)

**Market Benchmarks:**
- BTC buy-and-hold
- Equal-weight crypto index
- Market-cap-weight crypto index

---

## 12. Implementation Roadmap

### Phase 1: Core Implementation (Week 1)
- [ ] Create `backtests/scripts/backtest_beta_factor.py`
- [ ] Implement rolling beta calculation function
- [ ] Implement quintile ranking and selection
- [ ] Add equal-weight portfolio construction
- [ ] Validate no-lookahead bias (use `.shift(-1)`)
- [ ] Run baseline backtest: Betting Against Beta

### Phase 2: Testing & Validation (Week 1-2)
- [ ] Validate beta calculations (manual spot checks)
- [ ] Check for data quality issues
- [ ] Verify performance metrics calculations
- [ ] Test on different time periods (2020-2025)
- [ ] Analyze beta distribution across coins

### Phase 3: Strategy Variants (Week 2)
- [ ] Implement all 4 strategy variants
- [ ] Add risk parity weighting option
- [ ] Test different rebalancing frequencies (7d, 14d, 30d)
- [ ] Test different beta windows (30d, 60d, 90d, 180d)
- [ ] Parameter sensitivity analysis

### Phase 4: Advanced Features (Week 3)
- [ ] Add beta-weighted portfolio construction
- [ ] Implement partial rebalancing (lower turnover)
- [ ] Add transaction cost estimation
- [ ] Test regime-dependent strategies
- [ ] Calculate factor exposures (size, momentum, etc.)

### Phase 5: Analysis & Documentation (Week 3)
- [ ] Compare all strategy variants
- [ ] Analyze performance by market regime
- [ ] Calculate correlation to BTC/ETH
- [ ] Compare to other factor strategies
- [ ] Generate performance visualizations
- [ ] Create summary report
- [ ] Document findings and recommendations

---

## 13. Integration with Existing System

### 13.1 Code Reuse

**Existing Utilities:**
- `backtests/scripts/backtest_size_factor.py` - Template structure
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
# Size factor
python3 backtest_size_factor.py --start-date 2020-01-01

# Volatility factor
python3 backtest_volatility_factor.py --start-date 2020-01-01

# Kurtosis factor
python3 backtest_kurtosis_factor.py --start-date 2020-01-01

# Beta factor (new)
python3 backtest_beta_factor.py --start-date 2020-01-01
```

**Calculate factor correlation matrix:**
- Correlation of daily returns across factors
- Identify diversification opportunities
- Build multi-factor portfolio

---

## 14. Academic References

### 14.1 Traditional Finance

**Betting Against Beta:**
- Frazzini, A., & Pedersen, L. H. (2014). "Betting Against Beta". *Journal of Financial Economics*.
- Black, F. (1972). "Capital Market Equilibrium with Restricted Borrowing". *Journal of Business*.
- Baker, M., Bradley, B., & Wurgler, J. (2011). "Benchmarks as Limits to Arbitrage".

**CAPM and Beta:**
- Sharpe, W. F. (1964). "Capital Asset Prices: A Theory of Market Equilibrium". *Journal of Finance*.
- Fama, E. F., & French, K. R. (1992). "The Cross-Section of Expected Stock Returns".

### 14.2 Crypto-Specific

**Risk Factors in Crypto:**
- Liu, Y., Tsyvinski, A., & Wu, X. (2022). "Common Risk Factors in Cryptocurrency". *Journal of Finance*.
- Hu, A., Parlour, C. A., & Rajan, U. (2019). "Cryptocurrencies: Stylized Facts on a New Investible Instrument". *Financial Management*.

**Crypto Beta:**
- Hoang, L. T., & Baur, D. G. (2021). "How Stable Are Cryptocurrencies? A Cross-Country Analysis". *Journal of International Financial Markets*.

---

## 15. Example Usage

### Basic Backtest
```bash
# Run Betting Against Beta (baseline)
python3 backtests/scripts/backtest_beta_factor.py \
  --strategy betting_against_beta \
  --beta-window 90 \
  --rebalance-days 7
```

### Test Traditional Risk Premium
```bash
python3 backtests/scripts/backtest_beta_factor.py \
  --strategy traditional_risk_premium \
  --beta-window 90 \
  --rebalance-days 7
```

### Parameter Sensitivity
```bash
# Test different beta windows
for window in 30 60 90 180; do
  python3 backtests/scripts/backtest_beta_factor.py \
    --strategy betting_against_beta \
    --beta-window $window \
    --output-prefix backtests/results/beta_factor_window_${window}
done
```

### Advanced Configuration
```bash
python3 backtests/scripts/backtest_beta_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy betting_against_beta \
  --beta-window 90 \
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
  --output-prefix backtests/results/beta_factor_custom
```

---

## 16. Next Steps

1. **Implement baseline script**: Start with `betting_against_beta` strategy
2. **Validate beta calculation**: Test on known pairs (e.g., ETH-BTC beta)
3. **Run initial backtest**: Generate first results
4. **Analyze beta distribution**: Understand cross-section of betas
5. **Test hypothesis**: Does BAB work in crypto?
6. **Compare strategies**: BAB vs. traditional risk premium
7. **Parameter optimization**: Find optimal beta window and rebalance frequency
8. **Multi-factor integration**: Combine with size, momentum, volatility factors

---

**Document Owner:** Research Team  
**Last Updated:** 2025-10-27  
**Status:** Ready for Implementation  
**Next Step:** Implement Phase 1 (Core backtest script)

---

**Disclaimer:** This backtest is for research purposes only. Past performance does not guarantee future results. Cryptocurrency trading involves substantial risk of loss. The "Betting Against Beta" strategy may not work in crypto markets as it does in traditional finance. Always conduct thorough research and risk management before deploying capital.
