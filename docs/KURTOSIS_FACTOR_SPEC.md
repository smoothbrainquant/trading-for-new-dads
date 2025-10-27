# Kurtosis Factor Backtest Specification

**Version:** 1.0  
**Date:** 2025-10-27  
**Status:** Draft

---

## 1. Executive Summary

This specification outlines a quantitative trading strategy based on the **kurtosis factor** for cryptocurrency returns. The core hypothesis is that coins with extreme return distributions (high or low kurtosis) exhibit predictable future performance patterns that can be exploited through a long/short portfolio strategy.

### Key Objectives
1. Calculate 30-day rolling kurtosis for all cryptocurrencies
2. Rank coins by kurtosis values
3. Construct long/short portfolios based on kurtosis rankings
4. Backtest the strategy and evaluate risk-adjusted performance
5. Compare to existing factor strategies (size, momentum, mean reversion)

---

## 2. Strategy Description

### 2.1 Core Concept

**Kurtosis** measures the "tailedness" of a return distribution:
- **High Kurtosis (> 3)**: Fat tails, prone to extreme moves, higher probability of outliers
- **Low Kurtosis (< 3)**: Thin tails, more stable returns, fewer extreme events
- **Normal Distribution**: Kurtosis = 3 (reference point)

### 2.2 Strategy Hypothesis

Two potential hypotheses to test:

#### Hypothesis A: Mean Reversion of Volatility Regimes
- **Long**: Coins with high kurtosis (recent extreme moves) → Expect stabilization
- **Short**: Coins with low kurtosis (recent stability) → Expect increased volatility
- **Rationale**: Extreme regimes tend to revert to normal

#### Hypothesis B: Momentum of Volatility Regimes
- **Long**: Coins with low kurtosis (stable returns) → Expect continued stability & positive returns
- **Short**: Coins with high kurtosis (unstable returns) → Expect continued instability & poor performance
- **Rationale**: Stable coins attract capital; unstable coins face redemptions

### 2.3 Signal Calculation

#### Step 1: Calculate Daily Returns
```python
# Log returns for each coin
returns_t = log(close_t / close_t-1)
```

#### Step 2: Calculate Rolling Kurtosis
```python
# 30-day rolling kurtosis using Fisher's definition (excess kurtosis)
# Excess kurtosis = kurtosis - 3
kurtosis_t = rolling_kurtosis(returns, window=30)
```

#### Step 3: Rank Coins by Kurtosis
```python
# Rank from lowest to highest kurtosis
# Rank 1 = lowest kurtosis (most stable)
# Rank N = highest kurtosis (most volatile/extreme)
kurtosis_rank_t = rank(kurtosis_t)
```

#### Step 4: Generate Signals
```python
# Strategy A: Mean Reversion
# Long bottom quintile (low kurtosis), Short top quintile (high kurtosis)
if kurtosis_rank_t <= 20th_percentile:
    signal = LONG
elif kurtosis_rank_t >= 80th_percentile:
    signal = SHORT

# Strategy B: Momentum
# Long top quintile (high kurtosis), Short bottom quintile (low kurtosis)
if kurtosis_rank_t >= 80th_percentile:
    signal = LONG
elif kurtosis_rank_t <= 20th_percentile:
    signal = SHORT
```

---

## 3. Implementation Specification

### 3.1 Data Requirements

#### Input Data
- **Source**: `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- **Fields Required**: `date`, `symbol`, `close`, `volume`, `market_cap`
- **Minimum History**: 60 days per coin (30 days for kurtosis + 30 days for stability)
- **Universe**: All coins with sufficient liquidity

#### Data Filters
- **Liquidity Filter**: 30-day average daily volume > $5M USD
- **Market Cap Filter**: Market cap > $50M USD
- **Data Quality**: No missing values in rolling window
- **Min Trading Days**: At least 45 out of 60 days with valid data

### 3.2 Kurtosis Calculation

#### Method: Fisher's Excess Kurtosis
```python
import pandas as pd
from scipy import stats

def calculate_rolling_kurtosis(returns, window=30):
    """
    Calculate rolling excess kurtosis (Fisher's definition)
    Excess kurtosis = kurtosis - 3
    - Normal distribution: excess kurtosis = 0
    - Leptokurtic (fat tails): excess kurtosis > 0
    - Platykurtic (thin tails): excess kurtosis < 0
    """
    return returns.rolling(window).apply(
        lambda x: stats.kurtosis(x, fisher=True, nan_policy='omit')
    )
```

#### Alternative: Pandas Built-in Kurtosis
```python
def calculate_rolling_kurtosis_pandas(returns, window=30):
    """
    Using pandas built-in kurtosis (also uses Fisher's definition)
    """
    return returns.rolling(window).kurt()
```

### 3.3 Portfolio Construction

#### Signal Generation (Daily)
1. Calculate 30-day kurtosis for all coins
2. Filter by liquidity and data quality
3. Rank coins by kurtosis (ascending or descending based on strategy)
4. Select top and bottom quintiles (20% each)
5. Assign LONG/SHORT signals

#### Position Sizing
- **Equal Weight**: Each position gets equal allocation within long/short bucket
- **Risk Parity**: Weight inversely by 30-day volatility
- **Default**: Risk parity weighting

#### Portfolio Parameters
- **Long Allocation**: 50% of capital (configurable)
- **Short Allocation**: 50% of capital (configurable)
- **Max Positions**: 10 longs + 10 shorts (configurable)
- **Rebalance Frequency**: Weekly (every 7 days)

### 3.4 Backtest Logic

#### No-Lookahead Implementation
```python
# CRITICAL: Avoid lookahead bias
# Kurtosis calculated on day T uses returns from [T-30, T-1]
# Signal generated on day T uses data up to and including day T
# Position entered on day T uses returns from day T+1

kurtosis_t = calculate_kurtosis(returns.loc[:t])
signal_t = generate_signal(kurtosis_t)
pnl_t1 = signal_t * returns.loc[t+1]  # Use next-day return
```

#### Entry Rules
- **Rebalance Days**: Every 7 days (e.g., Monday)
- **Signal Threshold**: Must be in top/bottom quintile
- **Position Limits**: Max 10 positions per side

#### Exit Rules
- **Time-Based Exit**: Hold until next rebalance
- **No Stops**: Simple buy-and-hold between rebalances
- **Automatic Exit**: Position removed if no longer in signal set

---

## 4. File Structure

### 4.1 Script to Create

**File**: `backtests/scripts/backtest_kurtosis_factor.py`

**Purpose**: Main backtest engine for kurtosis factor strategy

**Parameters**:
```python
KURTOSIS_WINDOW = 30           # days for kurtosis calculation
VOLATILITY_WINDOW = 30         # days for volatility calculation
REBALANCE_DAYS = 7             # rebalance frequency
LONG_PERCENTILE = 20           # bottom 20% for long (or top 20% for momentum)
SHORT_PERCENTILE = 80          # top 20% for short (or bottom 20% for momentum)
MIN_VOLUME = 5_000_000         # minimum daily volume ($)
MIN_MARKET_CAP = 50_000_000    # minimum market cap ($)
LONG_ALLOCATION = 0.50         # 50% to long side
SHORT_ALLOCATION = 0.50        # 50% to short side
INITIAL_CAPITAL = 10_000       # starting capital
STRATEGY_TYPE = 'mean_reversion'  # or 'momentum'
WEIGHTING_METHOD = 'risk_parity'  # or 'equal_weight'
```

**Command-Line Interface**:
```bash
python3 backtest_kurtosis_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy mean_reversion \
  --kurtosis-window 30 \
  --rebalance-days 7 \
  --long-percentile 20 \
  --short-percentile 80 \
  --weighting risk_parity \
  --start-date 2020-01-01 \
  --end-date 2025-10-26 \
  --output-prefix backtests/results/kurtosis_factor
```

### 4.2 Output Files

All outputs saved to `backtests/results/` directory:

#### 1. Portfolio Values
**File**: `kurtosis_factor_portfolio_values.csv`
```csv
date,portfolio_value,cash,long_exposure,short_exposure,net_exposure,gross_exposure,num_longs,num_shorts
2020-01-01,10000.00,10000.00,0.00,0.00,0.00,0.00,0,0
2020-01-08,10125.50,0.00,5062.75,-5062.75,0.00,10125.50,10,10
...
```

#### 2. Trade Log
**File**: `kurtosis_factor_trades.csv`
```csv
date,symbol,signal,kurtosis,kurtosis_rank,percentile,weight,position_size,market_cap,volume_30d_avg
2020-01-08,BTC,LONG,0.25,5,10.2,0.15,750.00,180000000000,25000000000
2020-01-08,ETH,LONG,0.31,8,16.3,0.14,700.00,25000000000,8000000000
2020-01-08,DOGE,SHORT,5.2,45,91.8,0.12,-600.00,15000000000,2000000000
...
```

#### 3. Performance Metrics
**File**: `kurtosis_factor_metrics.csv`
```csv
metric,value
total_return,0.3521
annualized_return,0.1842
annualized_volatility,0.2156
sharpe_ratio,0.854
max_drawdown,-0.1523
win_rate,0.5342
avg_long_positions,9.2
avg_short_positions,8.7
total_rebalances,82
trading_days,574
long_allocation,0.50
short_allocation,0.50
strategy_type,mean_reversion
```

#### 4. Kurtosis Time Series
**File**: `kurtosis_factor_kurtosis_timeseries.csv`
```csv
date,symbol,kurtosis,kurtosis_rank,percentile,returns_30d_mean,returns_30d_std,volume_30d_avg
2020-01-08,BTC,0.25,5,10.2,0.0012,0.035,25000000000
2020-01-08,ETH,0.31,8,16.3,0.0018,0.042,8000000000
...
```

#### 5. Visualization Files
**File**: `kurtosis_factor_equity_curve.png`
- Line chart: Portfolio value over time
- Comparison: Strategy vs. BTC buy-and-hold

**File**: `kurtosis_factor_drawdown.png`
- Underwater plot showing drawdown periods

**File**: `kurtosis_factor_kurtosis_distribution.png`
- Histogram: Distribution of kurtosis values over time

**File**: `kurtosis_factor_quintile_returns.png`
- Bar chart: Average returns by kurtosis quintile

---

## 5. Performance Metrics

### 5.1 Return Metrics
- **Total Return**: Cumulative return over backtest period
- **Annualized Return**: CAGR
- **Monthly Returns**: Time series of monthly performance
- **Rolling Returns**: 90-day rolling returns

### 5.2 Risk Metrics
- **Annualized Volatility**: Std of daily returns × √252
- **Sharpe Ratio**: (Return - RFR) / Volatility (assuming RFR = 0)
- **Sortino Ratio**: (Return - RFR) / Downside Volatility
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Calmar Ratio**: Return / Max Drawdown
- **VaR (95%)**: Value at Risk at 95% confidence
- **CVaR (95%)**: Conditional Value at Risk

### 5.3 Trading Metrics
- **Win Rate**: % of profitable rebalancing periods
- **Average Trade Duration**: Days per position
- **Turnover**: Average % of portfolio traded per rebalance
- **Number of Rebalances**: Total rebalancing events
- **Avg Long Positions**: Average number of long positions
- **Avg Short Positions**: Average number of short positions

### 5.4 Long/Short Metrics
- **Long Performance**: Isolated long side returns
- **Short Performance**: Isolated short side returns
- **Long/Short Correlation**: Correlation between long and short returns
- **Market Neutrality**: Average net exposure (should be ~0)

### 5.5 Comparison Metrics
- **BTC Correlation**: Correlation of strategy returns to BTC
- **ETH Correlation**: Correlation of strategy returns to ETH
- **Alpha vs. BTC**: Excess return over BTC buy-and-hold
- **Beta vs. BTC**: Systematic risk relative to BTC

---

## 6. Backtest Validation

### 6.1 No-Lookahead Bias Checks
- ✅ Kurtosis calculated using only past returns
- ✅ Signals generated on day T executed with returns from day T+1
- ✅ All data filters applied before signal generation
- ✅ No future information used in weight calculation

### 6.2 Survivorship Bias Checks
- ✅ Include all coins with sufficient history (no cherry-picking)
- ✅ Handle delisted coins (mark as zero return after delisting)
- ✅ Use point-in-time market cap and volume data

### 6.3 Data Quality Checks
- ✅ Verify no missing data in kurtosis calculation windows
- ✅ Check for outliers (e.g., flash crashes, data errors)
- ✅ Validate volume and market cap filters are applied correctly
- ✅ Ensure sufficient universe size at each rebalance date

---

## 7. Strategy Variants to Test

### 7.1 Mean Reversion Strategy
**Name**: `mean_reversion`
- **Long**: Bottom quintile (low kurtosis = stable)
- **Short**: Top quintile (high kurtosis = unstable)
- **Hypothesis**: Extreme regimes revert to normal

### 7.2 Momentum Strategy
**Name**: `momentum`
- **Long**: Top quintile (high kurtosis = recent winners)
- **Short**: Bottom quintile (low kurtosis = recent stability)
- **Hypothesis**: Volatility regimes persist

### 7.3 Decile Spread Strategy
**Name**: `decile_spread`
- **Long**: Bottom decile (lowest 10% kurtosis)
- **Short**: Top decile (highest 10% kurtosis)
- **Purpose**: Maximize signal strength by using extremes

### 7.4 Long-Only Strategy
**Name**: `long_only`
- **Long**: Bottom quintile or top quintile (depending on hypothesis)
- **Short**: None (50% cash)
- **Purpose**: Test directional hypothesis without short side

---

## 8. Parameter Sensitivity Analysis

After baseline backtest, test sensitivity to:

### 8.1 Kurtosis Window
- 10 days, 20 days, **30 days (baseline)**, 45 days, 60 days, 90 days
- **Hypothesis**: Shorter windows = more reactive; longer windows = more stable

### 8.2 Rebalance Frequency
- Daily, **Weekly (baseline)**, Bi-weekly, Monthly
- **Hypothesis**: More frequent = higher turnover; less frequent = lower costs

### 8.3 Quintile Thresholds
- Top/Bottom 10%, 15%, **20% (baseline)**, 25%, 30%
- **Hypothesis**: Narrower thresholds = stronger signal, fewer positions

### 8.4 Weighting Methods
- Equal weight, **Risk parity (baseline)**, Market cap weight, Kurtosis weight
- **Hypothesis**: Risk parity reduces volatility impact

### 8.5 Allocation Split
- 100% long / 0% short, 75% long / 25% short, **50%/50% (baseline)**
- **Hypothesis**: Market neutral provides diversification

---

## 9. Integration with Existing System

### 9.1 Data Integration
- **Leverages**: Existing price data from CoinMarketCap/Coinbase
- **Reuses**: Volume and market cap filters from other strategies
- **Consistent**: Same CSV format as other backtests

### 9.2 Code Reuse
- **`calc_vola.py`**: For volatility calculation (risk parity weighting)
- **`calc_weights.py`**: For risk parity weight calculation
- **Similar structure**: Follow patterns from `backtest_size_factor.py` and `backtest_mean_reversion.py`

### 9.3 Comparison to Existing Strategies
Compare kurtosis factor to:
- **Size Factor**: Market cap rankings
- **Momentum Factor**: Price returns rankings
- **Mean Reversion Factor**: Distance from moving average
- **Funding Rate Factor**: Funding rate divergence
- **Open Interest Factor**: OI divergence signals

---

## 10. Expected Insights

### 10.1 Key Questions
1. **Does kurtosis predict returns?**
   - Is there a relationship between current kurtosis and future returns?
   - Which direction: mean reversion or momentum?

2. **Is kurtosis a unique factor?**
   - Does kurtosis provide alpha independent of size, momentum, volatility?
   - What is the correlation to other factors?

3. **Does kurtosis vary by market regime?**
   - Does the strategy work better in bull vs. bear markets?
   - How does performance change during high volatility periods?

4. **Is kurtosis stable?**
   - How much does kurtosis vary over time?
   - Are high-kurtosis coins persistently high-kurtosis?

### 10.2 Success Criteria
- **Minimum Sharpe Ratio**: > 0.5
- **Maximum Drawdown**: < 40%
- **Win Rate**: > 50%
- **Market Neutrality**: |Average Net Exposure| < 10%
- **Low BTC Correlation**: < 0.3

### 10.3 Risk Factors
- **Kurtosis Instability**: May change rapidly during market events
- **Limited Predictive Power**: Kurtosis may be descriptive, not predictive
- **Regime Sensitivity**: May only work in specific market conditions
- **Liquidity Risk**: Extreme kurtosis coins may be illiquid

---

## 11. Implementation Roadmap

### Phase 1: Basic Implementation (Day 1)
- [x] Create specification document
- [ ] Implement `backtest_kurtosis_factor.py`
- [ ] Calculate rolling kurtosis
- [ ] Generate long/short signals
- [ ] Implement portfolio construction logic
- [ ] Run baseline backtest (mean_reversion, 30d window, weekly rebalance)

### Phase 2: Validation & Metrics (Day 2)
- [ ] Validate no-lookahead bias
- [ ] Calculate all performance metrics
- [ ] Generate output CSV files
- [ ] Create equity curve visualization
- [ ] Create drawdown visualization

### Phase 3: Strategy Variants (Day 3)
- [ ] Implement momentum strategy variant
- [ ] Implement decile spread variant
- [ ] Implement long-only variant
- [ ] Compare all variants
- [ ] Identify best-performing approach

### Phase 4: Parameter Sensitivity (Day 4)
- [ ] Test kurtosis window sensitivity (10d - 90d)
- [ ] Test rebalance frequency (daily, weekly, monthly)
- [ ] Test quintile threshold variations
- [ ] Test weighting methods
- [ ] Document parameter sensitivity results

### Phase 5: Analysis & Documentation (Day 5)
- [ ] Compare to existing factor strategies
- [ ] Analyze kurtosis distribution across coins
- [ ] Generate kurtosis quintile return analysis
- [ ] Create summary report
- [ ] Update `docs/RESEARCH_TODO.md`

---

## 12. Dependencies

### Python Packages
```
pandas>=2.0.0
numpy>=1.24.0
scipy>=1.10.0
matplotlib>=3.7.0
seaborn>=0.12.0
```

### Existing Scripts
- `data/raw/combined_coinbase_coinmarketcap_daily.csv` (price data)
- `signals/calc_vola.py` (volatility calculation)
- `signals/calc_weights.py` (risk parity weights)

---

## 13. Example Usage

### Basic Backtest
```bash
# Run mean reversion strategy (baseline)
python3 backtests/scripts/backtest_kurtosis_factor.py \
  --strategy mean_reversion \
  --kurtosis-window 30 \
  --rebalance-days 7
```

### Test Momentum Strategy
```bash
python3 backtests/scripts/backtest_kurtosis_factor.py \
  --strategy momentum \
  --kurtosis-window 30 \
  --rebalance-days 7
```

### Parameter Sensitivity Run
```bash
# Test different kurtosis windows
for window in 10 20 30 45 60 90; do
  python3 backtests/scripts/backtest_kurtosis_factor.py \
    --strategy mean_reversion \
    --kurtosis-window $window \
    --output-prefix backtests/results/kurtosis_factor_window_${window}
done
```

### Custom Configuration
```bash
python3 backtests/scripts/backtest_kurtosis_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy mean_reversion \
  --kurtosis-window 45 \
  --rebalance-days 14 \
  --long-percentile 15 \
  --short-percentile 85 \
  --weighting equal_weight \
  --long-allocation 0.6 \
  --short-allocation 0.4 \
  --min-volume 10000000 \
  --min-market-cap 100000000 \
  --start-date 2021-01-01 \
  --end-date 2025-10-26 \
  --output-prefix backtests/results/kurtosis_factor_custom
```

---

## 14. References

### Academic Literature
- Mandelbrot, B. (1963). "The Variation of Certain Speculative Prices" - Fat tails in financial returns
- Harvey, C. R., & Siddique, A. (2000). "Conditional Skewness in Asset Pricing Tests" - Higher moments in pricing
- Jondeau, E., & Rockinger, M. (2003). "Conditional Volatility, Skewness, and Kurtosis: Existence, Persistence, and Comovements"

### Crypto-Specific Research
- Liu, Y., Tsyvinski, A. (2021). "Risks and Returns of Cryptocurrency" - Crypto return characteristics
- Borri, N. (2019). "Conditional Tail-Risk in Cryptocurrency Markets" - Extreme events in crypto

---

## 15. Next Steps

1. **Implement baseline script**: Start with mean_reversion strategy
2. **Run initial backtest**: Validate code and generate first results
3. **Analyze results**: Check if kurtosis has predictive power
4. **Iterate**: Test momentum variant and parameter variations
5. **Compare**: Benchmark against existing strategies
6. **Document**: Update findings and integrate into research pipeline

---

**Document Owner**: Research Team  
**Last Updated**: 2025-10-27  
**Next Review**: After Phase 1 implementation
