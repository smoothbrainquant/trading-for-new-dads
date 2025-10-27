# Volatility Factor Backtest Strategy

## Overview

The Volatility Factor backtest implements a quantitative trading strategy based on realized volatility, testing the hypothesis that cryptocurrencies exhibit predictable return patterns based on their historical volatility. The strategy ranks coins by 30-day realized volatility and constructs long/short portfolios to capture the volatility risk premium.

## Strategy Description

### Core Concept

The volatility factor strategy ranks cryptocurrencies by their 30-day realized volatility and constructs portfolios based on volatility buckets. The core hypothesis is that volatility is a priced risk factor in crypto markets, similar to traditional equity markets.

**Key Question:** Do high-volatility coins outperform or underperform low-volatility coins on a risk-adjusted basis?

### Strategy Variants

1. **Long Low Vol, Short High Vol (`long_low_short_high`)**
   - Long position: Lowest volatility quintile (defensive)
   - Short position: Highest volatility quintile (aggressive)
   - Market neutral strategy
   - Tests "low volatility anomaly" - do stable coins outperform?

2. **Long High Vol (`long_high_vol`)**
   - Long position: Highest volatility quintile only
   - Tests hypothesis that high volatility = high expected returns
   - 50% exposure (default)

3. **Long Low Vol (`long_low_vol`)**
   - Long position: Lowest volatility quintile only
   - Tests defensive strategy - betting on stability
   - 50% exposure (default)

4. **Long High Vol, Short Low Vol (`long_high_short_low`)**
   - Long position: Highest volatility quintile
   - Short position: Lowest volatility quintile
   - Betting on volatility risk premium
   - Market neutral strategy

### Volatility Calculation

**30-Day Realized Volatility:**
```python
# Calculate daily log returns
daily_return_t = log(close_t / close_t-1)

# Calculate rolling volatility (annualized)
volatility_30d = std(daily_return_t, window=30) * sqrt(365)
```

**Key Features:**
- Uses log returns for better statistical properties
- 30-day rolling window (approximately 1 month)
- Annualized for comparability (multiply by sqrt(365))
- Minimum 30 days of data required

### Portfolio Construction

Within each volatility bucket, the strategy uses **equal weighting** or **risk parity weighting**:

1. **Equal Weight:**
   - Each coin receives equal portfolio weight within its bucket
   - Simple and transparent
   - Default method

2. **Risk Parity Weight:**
   - Weights inversely proportional to volatility
   - Lower volatility → Higher weight
   - Equalizes risk contribution across positions

## Signal Rules

### Ranking & Selection

**Daily Process:**
1. Calculate 30-day realized volatility for all coins
2. Rank coins by volatility (ascending: low to high)
3. Divide into quintiles (5 buckets)
4. Select top/bottom quintiles based on strategy

**Quintile Definitions:**
- **Quintile 1 (Low Vol):** Bottom 20% by volatility - most stable coins
- **Quintile 2-4 (Mid Vol):** Middle 60% - moderate volatility
- **Quintile 5 (High Vol):** Top 20% by volatility - most volatile coins

### Entry Rules

**For Long/Short Strategies:**
- Long: Enter coins in selected quintile (e.g., lowest vol quintile)
- Short: Enter coins in opposite quintile (e.g., highest vol quintile)
- Rebalance: Every N days (default: 7 days)
- Equal dollar allocation to long/short sides

**Filters:**
- Minimum 30 days of continuous price data
- Minimum daily volume > $1M (optional filter)
- Exclude coins with missing data in volatility window

### Exit Rules

- **Time-Based Exit:** Exit positions at next rebalance date
- **No Stop Loss:** Hold positions until rebalancing
- **Automatic Rebalancing:** Coins that drop out of target quintile are sold

## Backtest Implementation

### File Structure

**Main Script:** `backtests/scripts/backtest_volatility_factor.py`

**Output Files:**
1. `backtest_volatility_factor_portfolio_values.csv` - Daily portfolio values
2. `backtest_volatility_factor_trades.csv` - Trade history
3. `backtest_volatility_factor_metrics.csv` - Performance metrics
4. `backtest_volatility_factor_strategy_info.csv` - Strategy configuration

### Backtest Parameters

```python
# Configuration
VOLATILITY_WINDOW = 30          # Days for volatility calculation
NUM_QUINTILES = 5               # Number of volatility buckets
REBALANCE_DAYS = 7              # Rebalance frequency (days)
INITIAL_CAPITAL = 10000         # Starting capital (USD)
LEVERAGE = 1.0                  # Leverage multiplier
LONG_ALLOCATION = 0.5           # 50% to long positions
SHORT_ALLOCATION = 0.5          # 50% to short positions
WEIGHTING_METHOD = 'equal'      # 'equal' or 'risk_parity'
```

### Data Requirements

**Input Data:**
- **Price Data:** `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- **Required Fields:** date, symbol, open, high, low, close, volume
- **Minimum History:** 60 days (30 days for volatility + 30 days for backtest)

**Data Validation:**
- Check for missing values in price data
- Ensure sufficient history for all symbols
- Validate date continuity (no large gaps)

### No-Lookahead Bias Prevention

**Critical Rule:** Signals generated on day T use returns from day T+1

**Implementation:**
```python
# Day T: Calculate volatility using data up to and including day T
volatility_t = calculate_volatility(data[data.date <= t], window=30)

# Day T: Rank coins and determine positions
positions_t = rank_and_select(volatility_t)

# Day T+1: Apply positions using next day's returns
returns_t1 = data[data.date == t + 1]['return']
pnl_t1 = positions_t * returns_t1  # Use .shift(-1) to align properly
```

**Key Points:**
- Always use `.shift(-1)` when calculating forward returns
- Positions based on day T information
- Returns from day T+1 used for P&L calculation
- Rebalancing occurs at close of day T, executed at open of day T+1

## Performance Metrics

### Strategy-Level Metrics

**Returns:**
- Total Return: Cumulative return over backtest period
- Annualized Return: CAGR
- Daily Return: Average daily return

**Risk Metrics:**
- Annualized Volatility: Std of daily returns × sqrt(365)
- Sharpe Ratio: (Return - RFR) / Volatility (assume RFR = 0%)
- Sortino Ratio: (Return - RFR) / Downside Volatility
- Maximum Drawdown: Largest peak-to-trough decline
- Calmar Ratio: Annualized Return / Max Drawdown

**Trading Statistics:**
- Win Rate: % of profitable days
- Average Win: Mean return on winning days
- Average Loss: Mean return on losing days
- Total Rebalances: Number of rebalancing events
- Average Positions: Mean number of long/short positions

**Exposure Metrics:**
- Long Exposure: Average % allocated to longs
- Short Exposure: Average % allocated to shorts
- Net Exposure: Long - Short (market directional exposure)
- Gross Exposure: Long + Short (total capital deployed)

### Benchmark Comparisons

**Benchmarks:**
1. **Buy & Hold BTC:** Long-only BTC benchmark
2. **Equal-Weight Index:** Equal-weight basket of all coins
3. **Market-Cap-Weight Index:** Cap-weighted basket
4. **Other Factor Strategies:** Compare to size, momentum, carry factors

**Comparison Metrics:**
- Sharpe Ratio comparison
- Correlation to BTC/ETH
- Performance in bull vs. bear markets
- Drawdown comparison

## Usage

### Basic Usage

```bash
# Long low vol, short high vol (market neutral)
python3 backtests/scripts/backtest_volatility_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy long_low_short_high

# Long high volatility only
python3 backtests/scripts/backtest_volatility_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy long_high_vol

# Long low volatility only (defensive)
python3 backtests/scripts/backtest_volatility_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy long_low_vol
```

### Advanced Configuration

```bash
python3 backtests/scripts/backtest_volatility_factor.py \
  --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
  --strategy long_low_short_high \
  --volatility-window 30 \
  --num-quintiles 5 \
  --rebalance-days 7 \
  --weighting-method risk_parity \
  --initial-capital 10000 \
  --leverage 1.0 \
  --long-allocation 0.5 \
  --short-allocation 0.5 \
  --start-date 2023-01-01 \
  --end-date 2024-10-27 \
  --output-prefix backtest_volatility_factor
```

### Command-Line Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--price-data` | (required) | Path to historical OHLCV CSV file |
| `--strategy` | `long_low_short_high` | Strategy variant |
| `--volatility-window` | 30 | Volatility calculation window (days) |
| `--num-quintiles` | 5 | Number of volatility buckets |
| `--rebalance-days` | 7 | Rebalance frequency (days) |
| `--weighting-method` | `equal` | Weighting method: 'equal' or 'risk_parity' |
| `--initial-capital` | 10000 | Starting capital (USD) |
| `--leverage` | 1.0 | Leverage multiplier |
| `--long-allocation` | 0.5 | Allocation to long side (50%) |
| `--short-allocation` | 0.5 | Allocation to short side (50%) |
| `--start-date` | None | Backtest start date (YYYY-MM-DD) |
| `--end-date` | None | Backtest end date (YYYY-MM-DD) |
| `--output-prefix` | `backtest_volatility_factor` | Output file prefix |

## Strategy Hypothesis

### Academic Background

**Volatility Factor in Traditional Finance:**
- **Low Volatility Anomaly:** Low vol stocks historically outperform high vol stocks on risk-adjusted basis
- **Betting Against Beta (BAB):** Strategy of long low-beta, short high-beta assets
- **Risk-Return Puzzle:** Observed empirical relationship differs from CAPM predictions

**Key Research:**
- Baker, Bradley, & Wurgler (2011): "Benchmarks as Limits to Arbitrage"
- Frazzini & Pedersen (2014): "Betting Against Beta"
- Ang et al. (2006): "The Cross-Section of Volatility and Expected Returns"

### Crypto Market Application

**Potential Drivers:**
1. **Leverage Constraints:** Retail investors prefer high-vol coins for lottery-like payoffs
2. **Attention Bias:** High-vol coins attract more attention → overvaluation
3. **Risk Premium Puzzle:** High volatility may not be compensated with higher returns
4. **Flight to Quality:** In down markets, investors rotate to stable coins

**Alternative Hypothesis:**
- High volatility → High expected returns (traditional risk premium)
- Crypto markets may behave differently than traditional assets
- Volatility clustering and momentum effects

### Expected Outcomes

**Low Vol Strategy (Long Low Vol):**
- Lower drawdowns
- More stable returns
- May underperform in strong bull markets
- Outperforms in bear markets (defensive)

**High Vol Strategy (Long High Vol):**
- Higher potential returns
- Higher drawdowns
- Captures explosive moves in bull markets
- Underperforms in bear markets

**Market Neutral (Long Low, Short High):**
- Low correlation to BTC/ETH
- Captures volatility risk premium
- More stable performance across market regimes
- Positive Sharpe if low vol anomaly exists

## Risk Considerations

### Potential Risks

1. **Volatility Clustering:** Volatility is not constant - high vol periods cluster
2. **Market Regime Dependency:** Strategy may perform differently in bull vs. bear markets
3. **Liquidity Risk:** High vol coins may have lower liquidity
4. **Extreme Events:** Tail risk in high volatility coins (coins going to zero)
5. **Funding Costs:** If shorting, funding rates can be significant

### Risk Mitigation

1. **Rebalancing Frequency:** Not too frequent (avoid overtrading) or too infrequent (drift)
2. **Position Limits:** Cap individual position sizes
3. **Volatility Scaling:** Use risk parity to control risk contribution
4. **Filters:** Minimum volume/market cap requirements
5. **Leverage Control:** Conservative leverage (1x-2x max)

## Implementation Roadmap

### Phase 1: Core Implementation (Week 1)
- [ ] Implement `backtests/scripts/backtest_volatility_factor.py`
- [ ] Add 30-day volatility calculation function
- [ ] Implement quintile ranking and selection
- [ ] Add equal-weight portfolio construction
- [ ] Validate no-lookahead bias (use `.shift(-1)`)

### Phase 2: Testing & Validation (Week 1)
- [ ] Run baseline backtest: Long Low, Short High
- [ ] Validate results against manual calculations
- [ ] Check for data quality issues
- [ ] Verify performance metrics calculations
- [ ] Test on different time periods

### Phase 3: Strategy Variants (Week 2)
- [ ] Implement all 4 strategy variants
- [ ] Add risk parity weighting option
- [ ] Test different rebalancing frequencies (1d, 7d, 30d)
- [ ] Test different volatility windows (20d, 30d, 60d)
- [ ] Parameter sensitivity analysis

### Phase 4: Analysis & Documentation (Week 2)
- [ ] Compare all strategy variants
- [ ] Analyze performance by market regime
- [ ] Calculate correlation to BTC/ETH
- [ ] Compare to other factor strategies (size, momentum, carry)
- [ ] Generate performance visualizations
- [ ] Document findings and recommendations

## Output Files Schema

### Portfolio Values CSV
```csv
date,portfolio_value,num_long_positions,num_short_positions,long_exposure,short_exposure,net_exposure,gross_exposure
2023-01-01,10000.00,10,10,0.50,0.50,0.00,1.00
2023-01-02,10125.50,10,10,0.50,0.50,0.00,1.00
...
```

### Trades CSV
```csv
date,symbol,old_weight,new_weight,weight_change,volatility_30d,quintile,position_type
2023-01-01,BTC,0.00,0.05,0.05,0.45,1,long
2023-01-01,ETH,0.00,0.05,0.05,0.52,1,long
2023-01-01,DOGE,0.00,-0.05,-0.05,1.85,5,short
...
```

### Metrics CSV
```csv
initial_capital,final_value,total_return,annualized_return,annualized_volatility,sharpe_ratio,max_drawdown,win_rate,num_days,avg_long_positions,avg_short_positions
10000,12500,0.25,0.45,0.35,1.29,-0.15,0.55,365,10.0,10.0
```

### Strategy Info CSV
```csv
strategy,volatility_window,num_quintiles,rebalance_days,weighting_method,long_symbols,short_symbols
long_low_short_high,30,5,7,equal,"BTC,ETH,USDC,...","DOGE,SHIB,PEPE,..."
```

## Integration with Existing System

### Code Reuse

**Existing Utilities:**
- `backtests/scripts/backtest_size_factor.py` - Template for structure
- `backtests/scripts/backtest_carry_factor.py` - Risk parity weighting
- `calc_vola.py` - Volatility calculation (may need custom window)
- `calc_weights.py` - Risk parity weight calculation

**Data Integration:**
- Use existing price data: `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- Follow same CSV format and naming conventions
- Store outputs in `backtests/results/`

### Comparison to Other Factors

**Factor Comparison Framework:**
- Run all factor strategies on same time period
- Calculate correlation matrix of factor returns
- Combine factors for multi-factor model
- Analyze factor timing and regime dependence

**Multi-Factor Potential:**
- Combine volatility + size + momentum
- Factor rotation based on market conditions
- Risk-balanced multi-factor portfolio

## Expected Results

### Success Criteria

**Minimum Viable Results:**
- Sharpe Ratio > 0.5 (annualized)
- Maximum Drawdown < 30%
- Win Rate > 45%
- Low correlation to BTC (< 0.6)

**Stretch Goals:**
- Sharpe Ratio > 1.0
- Maximum Drawdown < 20%
- Positive returns in bear market periods
- Outperform equal-weight benchmark on risk-adjusted basis

### Key Questions to Answer

1. **Does the low volatility anomaly exist in crypto?**
   - Do low vol coins outperform high vol coins?
   - Is the effect stronger in certain market regimes?

2. **What is the optimal volatility window?**
   - 20d, 30d, 60d, or 90d?
   - Does shorter window = more trading = higher costs?

3. **What is the optimal rebalancing frequency?**
   - Daily (high turnover), weekly (balanced), or monthly (low turnover)?
   - Trade-off between adaptation and transaction costs

4. **How does volatility factor correlate with other factors?**
   - Correlation to size factor?
   - Correlation to momentum factor?
   - Diversification benefits?

## References

### Academic Literature

1. **Baker, Bradley, & Wurgler (2011):** "Benchmarks as Limits to Arbitrage: Understanding Low-Volatility Anomalies"
2. **Frazzini & Pedersen (2014):** "Betting Against Beta"
3. **Ang, Hodrick, Xing, & Zhang (2006):** "The Cross-Section of Volatility and Expected Returns"
4. **Blitz & van Vliet (2007):** "The Volatility Effect: Lower Risk Without Lower Return"

### Crypto-Specific Research

1. **Liu, Tsyvinski, & Wu (2022):** "Common Risk Factors in Cryptocurrency"
2. **Hu, Parlour, & Rajan (2019):** "Cryptocurrencies: Stylized Facts on a New Investible Instrument"

### Codebase References

- Price data: `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- Size factor: `backtests/scripts/backtest_size_factor.py`
- Carry factor: `backtests/scripts/backtest_carry_factor.py`
- Volatility calc: `signals/calc_vola.py`
- Backtest framework: `backtests/scripts/backtest_mean_reversion.py`

---

**Document Version:** 1.0  
**Date:** 2025-10-27  
**Status:** Specification - Ready for Implementation  
**Next Step:** Implement Phase 1 (Core backtest script)

---

**Disclaimer:** This backtest is for research purposes only. Past performance does not guarantee future results. Cryptocurrency trading involves substantial risk of loss.
