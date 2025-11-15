# Autocorrelation Factor Backtest Specification

**Version:** 1.0  
**Date:** 2025-10-27  
**Status:** Specification - Ready for Implementation

---

## 1. Executive Summary

This specification outlines a quantitative trading strategy based on the **autocorrelation factor** for cryptocurrency returns. The core hypothesis is that coins exhibiting positive or negative return autocorrelation display predictable momentum or mean-reversion patterns that can be exploited through long/short portfolio strategies.

### Key Objectives
1. Calculate rolling autocorrelation of returns for all cryptocurrencies
2. Rank coins by autocorrelation values (high to low)
3. Construct long/short portfolios based on autocorrelation rankings
4. Backtest the strategy and evaluate risk-adjusted performance
5. Compare to existing factor strategies (momentum, mean reversion, volatility)

---

## 2. Strategy Description

### 2.1 Core Concept

**Autocorrelation** measures the correlation between a time series and a lagged version of itself:
- **Positive Autocorrelation (> 0)**: Returns persist - recent positive returns tend to be followed by more positive returns (momentum)
- **Negative Autocorrelation (< 0)**: Returns reverse - recent positive returns tend to be followed by negative returns (mean reversion)
- **Zero Autocorrelation**: Random walk - past returns don't predict future returns

**Key Insight**: Autocorrelation at the return level captures short-term momentum or mean reversion dynamics that may not be captured by traditional price-based momentum factors.

### 2.2 Strategy Hypothesis

#### Hypothesis A: Momentum Strategy
- **Long**: Coins with high positive autocorrelation → Expect continued directional moves
- **Short**: Coins with negative/low autocorrelation → Expect reversals or chop
- **Rationale**: Trending markets exhibit return persistence; trade with the trend

#### Hypothesis B: Contrarian/Mean Reversion Strategy
- **Long**: Coins with negative autocorrelation → Expect mean reversion opportunities
- **Short**: Coins with high positive autocorrelation → Expect exhaustion/reversal
- **Rationale**: Strong autocorrelation regimes are unsustainable; fade extremes

### 2.3 Signal Calculation

#### Step 1: Calculate Daily Returns
```python
# Log returns for each coin
returns_t = log(close_t / close_t-1)
```

#### Step 2: Calculate Rolling Autocorrelation
```python
# Calculate autocorrelation with lag 1 over 30-day rolling window
# Lag 1: correlation between returns_t and returns_t-1
autocorr_t = rolling_autocorr(returns, lag=1, window=30)
```

#### Step 3: Rank Coins by Autocorrelation
```python
# Rank from lowest to highest autocorrelation
# Rank 1 = most negative autocorr (strongest mean reversion)
# Rank N = most positive autocorr (strongest momentum)
autocorr_rank_t = rank(autocorr_t)
```

#### Step 4: Generate Signals
```python
# Strategy A: Momentum
# Long top quintile (high positive autocorr), Short bottom quintile (negative autocorr)
if autocorr_rank_t >= 80th_percentile:
    signal = LONG
elif autocorr_rank_t <= 20th_percentile:
    signal = SHORT

# Strategy B: Contrarian
# Long bottom quintile (negative autocorr), Short top quintile (positive autocorr)
if autocorr_rank_t <= 20th_percentile:
    signal = LONG
elif autocorr_rank_t >= 80th_percentile:
    signal = SHORT
```

---

## 3. Implementation Specification

### 3.1 Data Requirements

#### Input Data
- **Source**: `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- **Fields Required**: `date`, `symbol`, `close`, `volume`, `market_cap`
- **Minimum History**: 60 days per coin (30 days for autocorrelation + 30 days buffer)
- **Universe**: All coins with sufficient liquidity and data quality

#### Data Filters
- **Liquidity Filter**: 30-day average daily volume > $5M USD
- **Market Cap Filter**: Market cap > $50M USD (optional)
- **Data Quality**: No more than 5 missing days in rolling window
- **Min Trading Days**: At least 25 out of 30 days with valid data

### 3.2 Autocorrelation Calculation

#### Method: Pearson Correlation with Lag 1
```python
import pandas as pd
import numpy as np

def calculate_rolling_autocorr(returns, lag=1, window=30):
    """
    Calculate rolling autocorrelation using Pearson correlation
    
    Parameters:
    - returns: Series of daily returns
    - lag: Number of periods to lag (default: 1)
    - window: Rolling window size (default: 30 days)
    
    Returns:
    - Series of autocorrelation values in range [-1, 1]
    """
    def autocorr_lag1(x):
        if len(x) < lag + 2:
            return np.nan
        # Correlation between x[t] and x[t-1]
        return pd.Series(x).autocorr(lag=lag)
    
    return returns.rolling(window).apply(autocorr_lag1)
```

#### Alternative Implementation: Manual Calculation
```python
def calculate_rolling_autocorr_manual(returns, lag=1, window=30):
    """
    Manual implementation of autocorrelation for transparency
    """
    autocorr_values = []
    
    for i in range(len(returns)):
        if i < window:
            autocorr_values.append(np.nan)
            continue
        
        # Get window of returns
        window_returns = returns.iloc[i-window:i].values
        
        # Create lagged series
        x = window_returns[lag:]
        y = window_returns[:-lag]
        
        # Calculate Pearson correlation
        if len(x) > 2:
            corr = np.corrcoef(x, y)[0, 1]
            autocorr_values.append(corr)
        else:
            autocorr_values.append(np.nan)
    
    return pd.Series(autocorr_values, index=returns.index)
```

### 3.3 Portfolio Construction

#### Signal Generation (Daily)
1. Calculate 30-day autocorrelation (lag 1) for all coins
2. Filter by liquidity and data quality
3. Rank coins by autocorrelation (ascending: negative to positive)
4. Select top and bottom quintiles (20% each)
5. Assign LONG/SHORT signals based on strategy type

#### Position Sizing
- **Equal Weight**: Each position gets equal allocation within long/short bucket
- **Risk Parity**: Weight inversely by 30-day volatility
- **Default**: Risk parity weighting (reduces impact of high-volatility coins)

#### Portfolio Parameters
- **Long Allocation**: 50% of capital (configurable)
- **Short Allocation**: 50% of capital (configurable)
- **Max Positions**: No hard limit (determined by quintile selection)
- **Rebalance Frequency**: Weekly (every 7 days) - default

### 3.4 Backtest Logic

#### No-Lookahead Implementation
```python
# CRITICAL: Avoid lookahead bias
# Autocorr calculated on day T uses returns from [T-30, T-1]
# Signal generated on day T uses data up to and including day T
# Position entered on day T uses returns from day T+1

autocorr_t = calculate_autocorr(returns.loc[:t])
signal_t = generate_signal(autocorr_t)
pnl_t1 = signal_t * returns.loc[t+1].shift(-1)  # Use next-day return
```

#### Entry Rules
- **Rebalance Days**: Every 7 days (e.g., Monday)
- **Signal Threshold**: Must be in top/bottom quintile
- **Minimum Autocorr Magnitude**: Optional filter for |autocorr| > 0.1

#### Exit Rules
- **Time-Based Exit**: Hold until next rebalance
- **No Stop Loss**: Simple buy-and-hold between rebalances
- **Automatic Exit**: Position removed if no longer in signal set at rebalance

---

## 4. File Structure

### 4.1 Script to Create

**File**: `backtests/scripts/backtest_autocorr_factor.py`

**Purpose**: Main backtest engine for autocorrelation factor strategy

**Parameters**:
```python
AUTOCORR_WINDOW = 30          # days for autocorrelation calculation
AUTOCORR_LAG = 1              # lag for autocorrelation (default: 1 day)
VOLATILITY_WINDOW = 30        # days for volatility calculation
REBALANCE_DAYS = 7            # rebalance frequency
LONG_PERCENTILE = 80          # top 20% for long (momentum strategy)
SHORT_PERCENTILE = 20         # bottom 20% for short (momentum strategy)
MIN_VOLUME = 5_000_000        # minimum daily volume ($)
MIN_MARKET_CAP = 50_000_000   # minimum market cap ($) - optional
LONG_ALLOCATION = 0.50        # 50% to long side
SHORT_ALLOCATION = 0.50       # 50% to short side
INITIAL_CAPITAL = 10_000      # starting capital
STRATEGY_TYPE = 'momentum'    # or 'contrarian'
WEIGHTING_METHOD = 'risk_parity'  # or 'equal_weight'
```

**Command-Line Interface**:
```bash
python3 backtests/scripts/backtest_autocorr_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy momentum \
  --autocorr-window 30 \
  --autocorr-lag 1 \
  --rebalance-days 7 \
  --long-percentile 80 \
  --short-percentile 20 \
  --weighting risk_parity \
  --start-date 2020-01-01 \
  --end-date 2025-10-27 \
  --output-prefix backtests/results/autocorr_factor
```

### 4.2 Output Files

All outputs saved to `backtests/results/` directory:

#### 1. Portfolio Values
**File**: `autocorr_factor_portfolio_values.csv`
```csv
date,portfolio_value,cash,long_exposure,short_exposure,net_exposure,gross_exposure,num_longs,num_shorts
2020-01-01,10000.00,10000.00,0.00,0.00,0.00,0.00,0,0
2020-01-08,10142.30,0.00,5071.15,-5071.15,0.00,10142.30,12,11
...
```

#### 2. Trade Log
**File**: `autocorr_factor_trades.csv`
```csv
date,symbol,signal,autocorr,autocorr_rank,percentile,weight,position_size,returns_30d_mean,returns_30d_std
2020-01-08,BTC,LONG,0.45,48,92.3,0.08,400.50,0.0023,0.035
2020-01-08,ETH,LONG,0.38,44,84.6,0.09,456.30,0.0031,0.042
2020-01-08,DOGE,SHORT,-0.25,3,5.8,0.07,-354.25,-0.0012,0.085
...
```

#### 3. Performance Metrics
**File**: `autocorr_factor_metrics.csv`
```csv
metric,value
initial_capital,10000.00
final_value,15234.56
total_return,0.5235
annualized_return,0.2145
annualized_volatility,0.2823
sharpe_ratio,0.760
sortino_ratio,1.125
max_drawdown,-0.1892
calmar_ratio,1.134
win_rate,0.5612
avg_long_positions,11.3
avg_short_positions,10.8
total_rebalances,78
trading_days,546
long_allocation,0.50
short_allocation,0.50
strategy_type,momentum
autocorr_window,30
autocorr_lag,1
```

#### 4. Autocorrelation Time Series
**File**: `autocorr_factor_timeseries.csv`
```csv
date,symbol,autocorr,autocorr_rank,percentile,returns_30d_mean,returns_30d_std,volume_30d_avg
2020-01-08,BTC,0.45,48,92.3,0.0023,0.035,25000000000
2020-01-08,ETH,0.38,44,84.6,0.0031,0.042,8000000000
2020-01-08,DOGE,-0.25,3,5.8,-0.0012,0.085,2000000000
...
```

#### 5. Visualization Files (Optional)
**File**: `autocorr_factor_equity_curve.png`
- Line chart: Portfolio value over time vs. BTC benchmark

**File**: `autocorr_factor_drawdown.png`
- Underwater plot showing drawdown periods

**File**: `autocorr_factor_autocorr_distribution.png`
- Histogram: Distribution of autocorrelation values

**File**: `autocorr_factor_quintile_returns.png`
- Bar chart: Average next-day returns by autocorr quintile

---

## 5. Performance Metrics

### 5.1 Return Metrics
- **Total Return**: Cumulative return over backtest period
- **Annualized Return**: Compound annual growth rate (CAGR)
- **Monthly Returns**: Time series of monthly performance
- **Rolling Returns**: 90-day rolling returns

### 5.2 Risk Metrics
- **Annualized Volatility**: Std of daily returns × √365
- **Sharpe Ratio**: (Return - RFR) / Volatility (assuming RFR = 0%)
- **Sortino Ratio**: (Return - RFR) / Downside Volatility
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Calmar Ratio**: Annualized Return / Max Drawdown
- **VaR (95%)**: Value at Risk at 95% confidence level
- **CVaR (95%)**: Conditional Value at Risk (expected shortfall)

### 5.3 Trading Metrics
- **Win Rate**: % of profitable daily returns
- **Average Trade Duration**: Days per position (typically = rebalance frequency)
- **Turnover**: Average % of portfolio traded per rebalance
- **Number of Rebalances**: Total rebalancing events
- **Avg Long Positions**: Average number of long positions held
- **Avg Short Positions**: Average number of short positions held

### 5.4 Long/Short Metrics
- **Long Side Return**: Isolated long portfolio performance
- **Short Side Return**: Isolated short portfolio performance
- **Long/Short Correlation**: Correlation between long and short returns
- **Market Neutrality**: Average net exposure (should be ~0 for market neutral)

### 5.5 Comparison Metrics
- **BTC Correlation**: Correlation of strategy returns to BTC returns
- **ETH Correlation**: Correlation of strategy returns to ETH returns
- **Alpha vs. BTC**: Excess return over BTC buy-and-hold
- **Beta vs. BTC**: Systematic risk relative to BTC
- **Information Ratio**: Alpha / Tracking Error

---

## 6. Backtest Validation

### 6.1 No-Lookahead Bias Checks
- ✅ Autocorrelation calculated using only past returns (t-30 to t-1)
- ✅ Signals generated on day T executed with returns from day T+1
- ✅ All data filters applied before signal generation
- ✅ No future information used in weight calculation
- ✅ Use `.shift(-1)` when mapping signals to forward returns

### 6.2 Survivorship Bias Checks
- ✅ Include all coins with sufficient history (no cherry-picking)
- ✅ Handle delisted coins (treat as zero return after delisting)
- ✅ Use point-in-time market cap and volume data
- ✅ No forward-filling of missing data beyond reasonable limits

### 6.3 Data Quality Checks
- ✅ Verify no missing data in autocorrelation calculation windows
- ✅ Check for outliers (e.g., flash crashes causing spurious autocorrelation)
- ✅ Validate volume and market cap filters applied correctly
- ✅ Ensure sufficient universe size at each rebalance date (min 20 coins)
- ✅ Handle edge cases: coins with constant prices (zero returns)

---

## 7. Strategy Variants to Test

### 7.1 Momentum Strategy (Default)
**Name**: `momentum`
- **Long**: Top quintile (high positive autocorr = trending)
- **Short**: Bottom quintile (negative autocorr = mean-reverting)
- **Hypothesis**: Positive autocorrelation persists; ride the trend

### 7.2 Contrarian Strategy
**Name**: `contrarian`
- **Long**: Bottom quintile (negative autocorr = oversold/bouncing)
- **Short**: Top quintile (high positive autocorr = overbought/exhaustion)
- **Hypothesis**: Extreme autocorrelation regimes are unsustainable

### 7.3 Long-Only Momentum
**Name**: `long_only_momentum`
- **Long**: Top quintile (high positive autocorr)
- **Short**: None (50% cash)
- **Purpose**: Directional bet on momentum without short exposure

### 7.4 Long-Only Contrarian
**Name**: `long_only_contrarian`
- **Long**: Bottom quintile (negative autocorr)
- **Short**: None (50% cash)
- **Purpose**: Directional bet on mean reversion without short exposure

### 7.5 Decile Strategy
**Name**: `decile_momentum`
- **Long**: Top decile (highest 10% autocorr)
- **Short**: Bottom decile (lowest 10% autocorr)
- **Purpose**: Focus on strongest signals with fewer positions

---

## 8. Parameter Sensitivity Analysis

After baseline backtest, test sensitivity to:

### 8.1 Autocorrelation Window
- 10 days, 20 days, **30 days (baseline)**, 45 days, 60 days
- **Hypothesis**: Shorter windows = more responsive; longer = smoother but lagged

### 8.2 Autocorrelation Lag
- **Lag 1 (baseline)**: Next-day autocorrelation
- Lag 2-5: Multi-day autocorrelation
- **Hypothesis**: Lag 1 captures intraday momentum; higher lags capture weekly patterns

### 8.3 Rebalance Frequency
- Daily (1d), **Weekly (7d, baseline)**, Bi-weekly (14d), Monthly (30d)
- **Hypothesis**: More frequent = higher turnover/costs; less frequent = drift

### 8.4 Quintile Thresholds
- Top/Bottom 10%, 15%, **20% (baseline)**, 25%, 30%
- **Hypothesis**: Narrower thresholds = stronger signal, fewer positions

### 8.5 Weighting Methods
- Equal weight, **Risk parity (baseline)**, Volatility-scaled, Autocorr-weighted
- **Hypothesis**: Risk parity reduces volatility drag

### 8.6 Allocation Split
- 100% long / 0% short, 75% long / 25% short, **50%/50% (baseline, market neutral)**
- **Hypothesis**: Market neutral provides diversification benefits

---

## 9. Integration with Existing System

### 9.1 Data Integration
- **Leverages**: Existing price data from `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- **Reuses**: Volume and market cap filters from other strategies
- **Consistent**: Same CSV output format as other backtests

### 9.2 Code Reuse
- **`signals/calc_vola.py`**: For volatility calculation (risk parity weighting)
- **`signals/calc_weights.py`**: For risk parity weight calculation
- **Similar Structure**: Follow patterns from `backtest_volatility_factor.py`, `backtest_size_factor.py`

### 9.3 Comparison to Existing Strategies
Compare autocorrelation factor to:
- **Momentum Factor**: Price-based momentum (e.g., 30-day return)
- **Mean Reversion Factor**: Distance from moving average
- **Volatility Factor**: 30-day realized volatility rankings
- **Size Factor**: Market cap rankings
- **Kurtosis Factor**: Return distribution tail-heaviness

**Key Distinction**: Autocorrelation measures return *persistence* rather than return *magnitude* or *volatility*.

---

## 10. Expected Insights

### 10.1 Key Questions
1. **Does autocorrelation predict returns?**
   - Is there a relationship between current autocorrelation and future returns?
   - Which works better: momentum or contrarian strategy?

2. **Is autocorrelation a unique factor?**
   - Does autocorrelation provide alpha independent of momentum, volatility, size?
   - What is the correlation to other factors?
   - Can it be combined with other factors for enhanced performance?

3. **Does autocorrelation vary by market regime?**
   - Does the strategy work better in bull vs. bear markets?
   - How does performance change during high vs. low volatility periods?
   - Do different coins exhibit different autocorrelation patterns?

4. **Is autocorrelation stable over time?**
   - How much does autocorrelation vary day-to-day?
   - Are high-autocorr coins persistently high-autocorr?
   - What causes changes in autocorrelation regimes?

5. **What is the optimal lag?**
   - Lag 1 (next-day) vs. lag 2-5 (multi-day)?
   - Do different lags capture different phenomena?

### 10.2 Success Criteria
- **Minimum Sharpe Ratio**: > 0.5 (annualized)
- **Maximum Drawdown**: < 35%
- **Win Rate**: > 50%
- **Market Neutrality**: |Average Net Exposure| < 10%
- **Low BTC Correlation**: < 0.4 (for market neutral strategy)
- **Positive Alpha vs. BTC**: Outperform buy-and-hold on risk-adjusted basis

### 10.3 Risk Factors
- **Autocorrelation Instability**: Can change rapidly during regime shifts
- **Limited Predictive Power**: Past autocorr may not predict future autocorr
- **Regime Sensitivity**: May only work in certain market conditions (e.g., trending vs. ranging)
- **Transaction Costs**: Frequent rebalancing could erode returns
- **Liquidity Risk**: Extreme autocorr coins may have lower liquidity

---

## 11. Implementation Roadmap

### Phase 1: Core Implementation (Week 1)
- [ ] Create `backtests/scripts/backtest_autocorr_factor.py`
- [ ] Implement rolling autocorrelation calculation function
- [ ] Implement quintile ranking and selection logic
- [ ] Add portfolio construction with risk parity weighting
- [ ] Validate no-lookahead bias (use `.shift(-1)`)
- [ ] Run baseline backtest: momentum strategy, 30d window, 7d rebalance

### Phase 2: Testing & Validation (Week 1)
- [ ] Validate autocorrelation calculations against manual checks
- [ ] Run strategy on subset of data for quick validation
- [ ] Check for data quality issues (missing values, outliers)
- [ ] Verify performance metrics calculations
- [ ] Test on different time periods (2020-2021, 2022-2023, 2024+)

### Phase 3: Strategy Variants (Week 2)
- [ ] Implement contrarian strategy variant
- [ ] Implement long-only variants
- [ ] Implement decile strategy
- [ ] Test different rebalancing frequencies (1d, 7d, 14d, 30d)
- [ ] Test different autocorrelation windows (20d, 30d, 45d, 60d)
- [ ] Test different lags (lag 1-5)

### Phase 4: Parameter Sensitivity (Week 2)
- [ ] Run grid search over key parameters
- [ ] Analyze autocorrelation window sensitivity
- [ ] Analyze rebalance frequency impact
- [ ] Analyze quintile threshold variations
- [ ] Compare weighting methods (equal vs. risk parity)
- [ ] Document parameter sensitivity results

### Phase 5: Analysis & Documentation (Week 3)
- [ ] Compare to existing factor strategies (momentum, volatility, size, kurtosis)
- [ ] Calculate factor correlation matrix
- [ ] Analyze autocorrelation distribution across coins and time
- [ ] Generate quintile return analysis
- [ ] Test multi-factor models combining autocorr with other factors
- [ ] Create summary report and visualizations
- [ ] Update documentation with findings

---

## 12. Dependencies

### Python Packages
```
pandas>=2.0.0
numpy>=1.24.0
matplotlib>=3.7.0
seaborn>=0.12.0
scipy>=1.10.0  # optional, for statistical tests
```

### Existing Scripts
- `data/raw/combined_coinbase_coinmarketcap_daily.csv` (price data)
- `signals/calc_vola.py` (volatility calculation for risk parity)
- `signals/calc_weights.py` (risk parity weight calculation)
- `backtests/scripts/backtest_volatility_factor.py` (template structure)

Install dependencies:
```bash
pip install -r requirements.txt
```

---

## 13. Example Usage

### Basic Usage - Momentum Strategy
```bash
# Default: momentum strategy, 30d window, weekly rebalancing
python3 backtests/scripts/backtest_autocorr_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy momentum
```

### Contrarian Strategy
```bash
python3 backtests/scripts/backtest_autocorr_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy contrarian \
  --autocorr-window 30 \
  --rebalance-days 7
```

### Long-Only Momentum
```bash
python3 backtests/scripts/backtest_autocorr_factor.py \
  --strategy long_only_momentum \
  --long-allocation 1.0 \
  --short-allocation 0.0
```

### Custom Configuration
```bash
python3 backtests/scripts/backtest_autocorr_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy momentum \
  --autocorr-window 45 \
  --autocorr-lag 1 \
  --rebalance-days 14 \
  --long-percentile 85 \
  --short-percentile 15 \
  --weighting equal_weight \
  --long-allocation 0.6 \
  --short-allocation 0.4 \
  --min-volume 10000000 \
  --start-date 2021-01-01 \
  --end-date 2025-10-27 \
  --output-prefix backtests/results/autocorr_factor_custom
```

### Parameter Sensitivity Sweep
```bash
# Test different autocorrelation windows
for window in 10 20 30 45 60; do
  python3 backtests/scripts/backtest_autocorr_factor.py \
    --strategy momentum \
    --autocorr-window $window \
    --output-prefix backtests/results/autocorr_factor_window_${window}
done

# Test different rebalance frequencies
for rebal in 1 7 14 30; do
  python3 backtests/scripts/backtest_autocorr_factor.py \
    --strategy momentum \
    --rebalance-days $rebal \
    --output-prefix backtests/results/autocorr_factor_rebal_${rebal}d
done
```

---

## 14. Command-Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--price-data` | (required) | Path to historical OHLCV CSV file |
| `--strategy` | `momentum` | Strategy type: 'momentum', 'contrarian', 'long_only_momentum', 'long_only_contrarian', 'decile_momentum' |
| `--autocorr-window` | 30 | Window for autocorrelation calculation (days) |
| `--autocorr-lag` | 1 | Lag for autocorrelation calculation (days) |
| `--volatility-window` | 30 | Window for volatility calculation (days) |
| `--rebalance-days` | 7 | Rebalance frequency (days) |
| `--long-percentile` | 80 | Percentile threshold for long positions (momentum: 80, contrarian: 20) |
| `--short-percentile` | 20 | Percentile threshold for short positions (momentum: 20, contrarian: 80) |
| `--weighting` | `risk_parity` | Position weighting: 'equal_weight' or 'risk_parity' |
| `--initial-capital` | 10000 | Starting capital (USD) |
| `--long-allocation` | 0.5 | Allocation to long side (0.0 to 1.0) |
| `--short-allocation` | 0.5 | Allocation to short side (0.0 to 1.0) |
| `--min-volume` | 5000000 | Minimum 30d avg daily volume (USD) |
| `--min-market-cap` | 50000000 | Minimum market cap (USD), optional |
| `--start-date` | None | Backtest start date (YYYY-MM-DD) |
| `--end-date` | None | Backtest end date (YYYY-MM-DD) |
| `--output-prefix` | `backtests/results/autocorr_factor` | Output file prefix |

---

## 15. Academic Background

### 15.1 Autocorrelation in Financial Markets

**Traditional Finance Research:**
- **Lo & MacKinlay (1988)**: "Stock Market Prices Do Not Follow Random Walks" - documented positive autocorrelation in equity indices
- **Jegadeesh & Titman (1993)**: "Returns to Buying Winners and Selling Losers" - momentum based on return autocorrelation
- **Lehmann (1990)**: "Fads, Martingales, and Market Efficiency" - short-term reversal (negative autocorrelation)

**Key Findings:**
- **Short-term (daily to weekly)**: Often negative autocorrelation due to bid-ask bounce, microstructure noise
- **Medium-term (1-12 months)**: Positive autocorrelation (momentum)
- **Long-term (3-5 years)**: Negative autocorrelation (mean reversion)

### 15.2 Crypto Market Considerations

**Unique Characteristics:**
- **24/7 Trading**: No overnight gaps, different microstructure
- **High Volatility**: Stronger autocorrelation during trending regimes
- **Retail Dominance**: Behavioral biases may create stronger momentum
- **Lower Liquidity**: Thinner order books → potential for stronger autocorrelation
- **Sentiment-Driven**: News/social media can create persistent trends

**Hypothesized Drivers:**
- **Momentum**: Herding behavior, trend-following algos, FOMO
- **Mean Reversion**: Profit-taking, arbitrage, microstructure effects

### 15.3 Related Strategies

- **Time Series Momentum**: Uses past price returns (not autocorrelation)
- **Cross-Sectional Momentum**: Ranks assets by returns (not autocorrelation)
- **Short-Term Reversal**: Exploits negative autocorrelation
- **Volatility Timing**: Uses volatility regimes (related but different)

**Key Difference**: Autocorrelation measures return *persistence* structure, not return magnitude.

---

## 16. Risk Considerations

### 16.1 Strategy Risks
- **Regime Risk**: Autocorrelation patterns may shift during market regime changes
- **Overfitting Risk**: Optimal parameters may be data-specific
- **Transaction Costs**: Frequent rebalancing can erode returns
- **Liquidity Risk**: High-autocorr coins may have lower liquidity
- **Crowding Risk**: If widely adopted, autocorr signals may weaken

### 16.2 Market Risks
- **Volatility Spikes**: Extreme moves can disrupt autocorrelation patterns
- **Black Swan Events**: Sudden regime shifts invalidate historical patterns
- **Correlation Breakdown**: Long/short correlation may increase during crashes
- **Funding Costs**: Short positions may incur significant funding in bull markets

### 16.3 Implementation Risks
- **Data Quality**: Missing or incorrect data can corrupt autocorrelation calculations
- **Execution Slippage**: Market impact on rebalancing trades
- **Model Risk**: Autocorrelation may not be predictive out-of-sample

### 16.4 Risk Mitigation
- **Position Limits**: Cap individual position sizes
- **Volatility Scaling**: Use risk parity to control volatility contribution
- **Diversification**: Maintain sufficient number of positions (>10 per side)
- **Regular Monitoring**: Track autocorrelation stability over time
- **Adaptive Parameters**: Consider regime-dependent parameter adjustments

---

## 17. Expected Results

### 17.1 Baseline Expectations

**Momentum Strategy:**
- **Expected Sharpe**: 0.5 - 1.0 (if momentum persists)
- **Expected Max DD**: 20% - 35%
- **Expected Win Rate**: 52% - 58%
- **BTC Correlation**: 0.2 - 0.4 (some directional bias)

**Contrarian Strategy:**
- **Expected Sharpe**: 0.3 - 0.8 (if mean reversion exists)
- **Expected Max DD**: 25% - 40%
- **Expected Win Rate**: 50% - 55%
- **BTC Correlation**: -0.1 to 0.2 (potentially negative)

### 17.2 Comparison to Other Factors

**Expected Factor Correlations:**
- **Momentum Factor**: High correlation (0.6-0.8) - autocorr captures momentum dynamics
- **Volatility Factor**: Moderate correlation (0.3-0.5) - trending = volatility
- **Size Factor**: Low correlation (0.0-0.3) - orthogonal
- **Kurtosis Factor**: Moderate correlation (0.3-0.6) - extreme returns affect both

**Diversification Value:**
- Autocorr may provide unique signal not fully captured by price momentum
- Potential for factor combination strategies

---

## 18. Next Steps

1. **Implement Baseline Script** (Day 1-2)
   - Code autocorrelation calculation
   - Implement momentum strategy
   - Run on full dataset

2. **Validate Results** (Day 2-3)
   - Check no-lookahead bias
   - Verify autocorrelation calculations
   - Analyze quintile returns

3. **Test Strategy Variants** (Day 3-4)
   - Run contrarian strategy
   - Test long-only variants
   - Compare results

4. **Parameter Sensitivity** (Day 4-5)
   - Test different windows, lags, rebalance frequencies
   - Identify optimal parameters
   - Document findings

5. **Factor Analysis** (Day 5-7)
   - Compare to existing factors
   - Calculate factor correlations
   - Test multi-factor models
   - Generate final report

---

## 19. References

### Academic Papers
1. **Lo, A. W., & MacKinlay, A. C. (1988)**. "Stock Market Prices Do Not Follow Random Walks: Evidence from a Simple Specification Test." *Review of Financial Studies*, 1(1), 41-66.

2. **Jegadeesh, N., & Titman, S. (1993)**. "Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency." *Journal of Finance*, 48(1), 65-91.

3. **Lehmann, B. N. (1990)**. "Fads, Martingales, and Market Efficiency." *Quarterly Journal of Economics*, 105(1), 1-28.

4. **Moskowitz, T. J., Ooi, Y. H., & Pedersen, L. H. (2012)**. "Time Series Momentum." *Journal of Financial Economics*, 104(2), 228-250.

### Crypto-Specific Research
1. **Liu, Y., Tsyvinski, A., & Wu, X. (2022)**. "Common Risk Factors in Cryptocurrency." *Journal of Finance*, 77(2), 1133-1177.

2. **Hu, A. S., Parlour, C. A., & Rajan, U. (2019)**. "Cryptocurrencies: Stylized Facts on a New Investible Instrument." *Financial Management*, 48(4), 1049-1068.

### Codebase References
- Price data: `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- Volatility calc: `signals/calc_vola.py`
- Risk parity weights: `signals/calc_weights.py`
- Template: `backtests/scripts/backtest_volatility_factor.py`

---

**Document Version:** 1.0  
**Date:** 2025-10-27  
**Status:** Specification - Ready for Implementation  
**Next Step:** Implement Phase 1 (Core backtest script)

---

**Disclaimer:** This backtest is for research purposes only. Past performance does not guarantee future results. Cryptocurrency trading involves substantial risk of loss. The autocorrelation factor may not be predictive in all market conditions.
