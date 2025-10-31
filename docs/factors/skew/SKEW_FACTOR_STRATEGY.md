# Skew Factor Trading Strategy Specification

**Version:** 1.0  
**Date:** 2025-10-27  
**Status:** Draft

---

## 1. Executive Summary

This specification outlines a simple long/short factor strategy based on return skewness. The core hypothesis is that cryptocurrencies exhibit predictable patterns based on their recent return distribution asymmetry, where skewness can signal future reversals or continuations.

### Key Objectives
1. Calculate 30-day rolling skewness for all cryptocurrencies
2. Rank coins by skewness metric
3. Implement long/short portfolio based on skewness rankings
4. Backtest performance with proper no-lookahead methodology
5. Compare to buy-and-hold and other existing strategies

---

## 2. Strategy Overview

### 2.1 Core Concept

**Skewness** measures the asymmetry of return distribution:
- **Negative skewness:** More extreme losses than gains (left tail)
- **Positive skewness:** More extreme gains than losses (right tail)

**Trading Hypothesis:**
Skewness patterns may predict future returns through mean reversion or momentum effects.

### 2.2 Signal Rules

#### Long/Short Formation
1. **Calculate Skewness:** 30-day rolling skewness of daily returns for each coin
2. **Rank Coins:** Sort all coins by skewness (low to high)
3. **Portfolio Construction:**
   - **Long:** Bottom quintile (20% with lowest/most negative skewness)
   - **Short:** Top quintile (20% with highest/most positive skewness)
4. **Rebalance:** Daily

#### Position Sizing
- **Equal Weight:** Each position gets equal notional weight within long and short portfolios
- **Dollar Neutral:** Long notional = Short notional (zero net exposure)

---

## 3. Data Requirements

### 3.1 Input Data

**Source:** `data/raw/combined_coinbase_coinmarketcap_daily.csv`

**Required Fields:**
- `date`: Trading date
- `symbol`: Cryptocurrency ticker
- `close`: Daily close price
- `volume`: Daily trading volume
- `market_cap`: Market capitalization

**Coverage:**
- 172 cryptocurrencies
- 2020-01-01 to present
- Daily frequency

### 3.2 Filters

**Liquidity Filter:**
- Minimum 30-day average volume > $5M USD
- Ensures tradeable liquidity

**Data Quality Filter:**
- Require at least 30 consecutive days of data for skewness calculation
- Exclude coins with missing data in the calculation window

**Market Cap Filter:**
- Minimum market cap > $50M USD
- Filters out micro-cap illiquid coins

---

## 4. Signal Calculation

### 4.1 Return Calculation

```python
# Daily log returns
returns_t = log(close_t / close_t-1)
```

### 4.2 Skewness Calculation

```python
# 30-day rolling skewness
skewness_t = skew(returns[t-29:t])  # Uses past 30 days of returns

# Python implementation
import pandas as pd
from scipy.stats import skew

df['returns'] = np.log(df['close'] / df['close'].shift(1))
df['skewness_30d'] = df.groupby('symbol')['returns'].rolling(30).apply(
    lambda x: skew(x), raw=True
).reset_index(level=0, drop=True)
```

### 4.3 Ranking and Signal Generation

```python
# For each date t
for each date t:
    # 1. Filter valid coins (liquidity, market cap, data quality)
    valid_coins = apply_filters(data, date=t)
    
    # 2. Rank by skewness
    ranked = valid_coins.sort_values('skewness_30d')
    
    # 3. Determine quintiles
    n_coins = len(ranked)
    quintile_size = n_coins // 5
    
    # 4. Generate signals
    long_signals = ranked.iloc[:quintile_size]['symbol']  # Bottom 20%
    short_signals = ranked.iloc[-quintile_size:]['symbol']  # Top 20%
    
    # 5. Calculate equal weights
    long_weight = 1.0 / len(long_signals)
    short_weight = -1.0 / len(short_signals)
```

---

## 5. Backtesting Methodology

### 5.1 No-Lookahead Bias Prevention

**CRITICAL:** Signals generated on day `t` must use returns from day `t+1`

```python
# Calculate signals using data up to and including day t
signals_t = calculate_signals(data[data.date <= t])

# Apply returns from day t+1 for P&L
returns_t1 = data[data.date == t + 1]['returns']
pnl_t1 = signals_t * returns_t1.shift(-1)  # Use next-day returns
```

### 5.2 Backtest Implementation

**File:** `backtests/scripts/backtest_skew_factor.py`

**Procedure:**
1. **Load Data:** Read combined price data
2. **Calculate Returns:** Compute daily log returns
3. **Rolling Window:**
   - For each date `t` from start_date to end_date:
     - Filter valid coins (liquidity, market cap, data quality)
     - Calculate 30-day skewness for each coin using data up to day `t`
     - Rank coins by skewness
     - Generate long/short signals (bottom/top quintiles)
     - Calculate equal weights for long and short portfolios
     - Apply day `t+1` returns to positions
     - Record P&L, positions, turnover
4. **Calculate Performance Metrics**
5. **Generate Visualizations**

### 5.3 Portfolio Construction

**Long Portfolio:**
- Weight: +100% of capital
- Positions: Bottom 20% by skewness (most negative)
- Equal weight per position

**Short Portfolio:**
- Weight: -100% of capital (short)
- Positions: Top 20% by skewness (most positive)
- Equal weight per position

**Net Exposure:**
- Dollar neutral: Long notional = Short notional
- Net beta ≈ 0 (market neutral)

### 5.4 Rebalancing

**Frequency:** Daily
- Recalculate skewness each day
- Re-rank all coins
- Update long/short portfolios

**Turnover:** Track daily turnover
```python
turnover_t = sum(abs(weight_t - weight_t-1)) / 2
```

---

## 6. Performance Metrics

### 6.1 Strategy-Level Metrics

**Returns:**
- Total Return (cumulative)
- Annualized Return (CAGR)
- Daily/Monthly/Yearly returns

**Risk Metrics:**
- Annualized Volatility: `std(daily_returns) * sqrt(252)`
- Sharpe Ratio: `(Return - RFR) / Volatility`
- Sortino Ratio: `(Return - RFR) / Downside_Volatility`
- Maximum Drawdown: Largest peak-to-trough decline
- Calmar Ratio: `Annualized_Return / Max_Drawdown`

**Trading Metrics:**
- Average Turnover (daily %)
- Number of rebalances
- Average positions held (long/short)

### 6.2 Factor Analysis

**Long Portfolio Metrics:**
- Long-only returns
- Long-only Sharpe
- Average skewness of long portfolio
- Win rate of long positions

**Short Portfolio Metrics:**
- Short-only returns
- Short-only Sharpe  
- Average skewness of short portfolio
- Win rate of short positions

**Long-Short Spread:**
- Long portfolio return - Short portfolio return
- Information ratio
- Correlation between long and short portfolios

### 6.3 Benchmarks

**Comparison Strategies:**
1. **Buy & Hold BTC:** Long-only BTC benchmark
2. **Equal-Weight Index:** Equal-weight basket of all coins
3. **Market-Cap-Weight Index:** Market-cap weighted basket
4. **Existing Strategies:**
   - Breakout strategy
   - Mean reversion strategy
   - Funding rate carry strategy

**Comparison Metrics:**
- Sharpe ratio vs benchmarks
- Correlation to BTC
- Beta to crypto market
- Alpha generation

---

## 7. Expected Outputs

### 7.1 Data Files

**Signals File:** `signals/skew_factor_signals.csv`
```csv
date,symbol,skewness_30d,rank,quintile,signal,weight,market_cap,volume_30d
2025-10-27,BTC,-0.45,15,2,NEUTRAL,0.0,1200000000000,50000000000
2025-10-27,ETH,-1.23,3,1,LONG,0.05,450000000000,20000000000
2025-10-27,SOL,0.89,145,5,SHORT,-0.05,85000000000,3000000000
...
```

**Backtest Results:** `backtests/results/skew_factor_backtest_results.csv`
```csv
date,portfolio_value,daily_return,long_return,short_return,turnover,num_long,num_short,net_exposure
2020-02-01,1000000,0.0,0.0,0.0,0.0,0,0,0.0
2020-02-02,1003500,0.0035,0.0042,-0.0007,0.85,25,25,0.0
...
```

**Performance Summary:** `backtests/results/skew_factor_performance.csv`
```csv
metric,value
total_return,0.45
annualized_return,0.12
annualized_volatility,0.25
sharpe_ratio,0.48
max_drawdown,-0.32
calmar_ratio,0.38
avg_turnover,0.15
long_only_return,0.08
short_only_return,0.04
win_rate_long,0.52
win_rate_short,0.49
avg_positions_long,28
avg_positions_short,28
```

### 7.2 Visualizations

**Files:**
- `backtests/results/skew_factor_equity_curve.png`: Cumulative returns over time
- `backtests/results/skew_factor_drawdown.png`: Drawdown chart
- `backtests/results/skew_factor_long_short_comparison.png`: Long vs short portfolio performance
- `backtests/results/skew_factor_skewness_distribution.png`: Distribution of skewness values over time
- `backtests/results/skew_factor_turnover.png`: Daily turnover over time

---

## 8. Implementation Plan

### Phase 1: Signal Generation (Week 1)
- [ ] **Task 1.1:** Implement skewness calculation with 30-day rolling window
- [ ] **Task 1.2:** Implement ranking and quintile logic
- [ ] **Task 1.3:** Apply liquidity and market cap filters
- [ ] **Task 1.4:** Generate signal files with all coins and rankings
- [ ] **Task 1.5:** Validate signals (check for data leakage, missing values)

### Phase 2: Backtesting (Week 1)
- [ ] **Task 2.1:** Implement `backtest_skew_factor.py` script
- [ ] **Task 2.2:** Ensure no-lookahead bias with `.shift(-1)` for returns
- [ ] **Task 2.3:** Calculate daily portfolio returns (long, short, combined)
- [ ] **Task 2.4:** Track turnover and positions
- [ ] **Task 2.5:** Validate backtest logic (manual checks on sample dates)

### Phase 3: Analysis (Week 2)
- [ ] **Task 3.1:** Calculate all performance metrics
- [ ] **Task 3.2:** Compare to benchmarks (BTC, equal-weight, existing strategies)
- [ ] **Task 3.3:** Analyze long vs short portfolio performance
- [ ] **Task 3.4:** Generate all visualization plots
- [ ] **Task 3.5:** Document results in summary markdown file

### Phase 4: Sensitivity Analysis (Week 2)
- [ ] **Task 4.1:** Test different lookback windows (20d, 30d, 60d, 90d)
- [ ] **Task 4.2:** Test different portfolio constructions (quintiles, deciles, terciles)
- [ ] **Task 4.3:** Test alternative weighting schemes (volatility-weighted, market-cap weighted)
- [ ] **Task 4.4:** Test transaction cost sensitivity (0%, 0.05%, 0.1%, 0.2%)
- [ ] **Task 4.5:** Compare performance across different market regimes (bull, bear, sideways)

---

## 9. Research Questions

### 9.1 Primary Questions
1. **Does skewness predict future returns?**
   - Do coins with negative skewness outperform?
   - Do coins with positive skewness underperform?

2. **Is the strategy profitable?**
   - Positive Sharpe ratio?
   - Positive alpha vs benchmarks?
   - Acceptable drawdowns?

3. **Long vs Short asymmetry?**
   - Does long portfolio drive returns?
   - Does short portfolio contribute?
   - Is there directional asymmetry like mean reversion?

### 9.2 Secondary Questions
1. **Optimal lookback period?**
   - Is 30 days optimal?
   - Compare 20d, 30d, 60d, 90d

2. **Portfolio construction?**
   - Are quintiles optimal?
   - Test deciles, terciles, top/bottom 10%

3. **Transaction costs impact?**
   - How sensitive to fees?
   - What is breakeven turnover level?

4. **Market regime dependency?**
   - Does strategy work in all regimes?
   - Better in bull or bear markets?

---

## 10. Expected Insights

### 10.1 Hypotheses

**Hypothesis 1: Mean Reversion**
- Coins with extreme negative skewness (crash risk) may rebound
- Coins with extreme positive skewness (momentum) may correct
- **Test:** Negative skewness → positive future returns

**Hypothesis 2: Risk Premium**
- Negative skewness = crash risk = compensation required
- Investors demand premium for holding negative skew assets
- **Test:** Negative skewness → positive risk premium

**Hypothesis 3: Momentum/Continuation**
- Positive skewness = upside momentum = continues
- Negative skewness = downside momentum = continues
- **Test:** Positive skewness → positive future returns (opposite of H1)

### 10.2 Success Criteria

**Minimum Performance Targets:**
- Sharpe Ratio > 0.5 (annualized)
- Max Drawdown < 40%
- Positive returns vs buy-and-hold BTC
- Low correlation to BTC (< 0.5)
- Turnover < 50% daily

---

## 11. Risk Considerations

### 11.1 Strategy Risks

**Market Risk:**
- Dollar-neutral but not market-neutral (crypto beta exposure)
- Extreme market moves can cause both long and short to lose

**Correlation Risk:**
- Assumes stable correlation structure
- Correlations spike to 1 during crashes

**Liquidity Risk:**
- Small coins may have thin markets
- Slippage on rebalancing

**Short Squeeze Risk:**
- Shorting crypto can be expensive (funding rates)
- Short positions vulnerable to squeezes

### 11.2 Implementation Risks

**Transaction Costs:**
- Daily rebalancing = high turnover
- Fees of 0.05-0.1% can erode returns
- Slippage on market orders

**Data Quality:**
- Missing data can cause incorrect rankings
- Outliers can skew skewness calculation

**Execution:**
- Assumes perfect execution at close prices
- Real-world execution may differ

### 11.3 Backtest Risks

**Overfitting:**
- Single parameter (30d lookback) reduces overfitting risk
- Still need out-of-sample validation

**Survivorship Bias:**
- Dataset may not include delisted coins
- May overstate historical returns

**Regime Shift:**
- Past patterns may not continue
- Crypto market evolving rapidly

---

## 12. Next Steps

1. **Review Spec:** Validate approach and assumptions
2. **Implement Signals:** Build skewness calculation and ranking
3. **Build Backtest:** Implement no-lookahead backtest framework
4. **Analyze Results:** Generate metrics and visualizations
5. **Document Findings:** Create results summary document
6. **Compare Strategies:** Benchmark against existing strategies
7. **Iterate:** Refine based on findings

---

## 13. References

### Academic Literature
- Harvey & Siddique (2000): "Conditional Skewness in Asset Pricing Tests"
- Bali, Engle & Murray (2016): "Empirical Asset Pricing: The Cross Section of Stock Returns"
- Conrad, Dittmar & Ghysels (2013): "Ex Ante Skewness and Expected Stock Returns"

### Existing Codebase
- Price data: `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- Backtest examples: `backtests/scripts/backtest_mean_reversion.py`
- Signal examples: `signals/calc_breakout_signals.py`
- Analysis examples: `signals/analyze_directional_mean_reversion.py`

---

**Document Owner:** Research Team  
**Last Updated:** 2025-10-27  
**Next Review:** After Phase 3 completion
