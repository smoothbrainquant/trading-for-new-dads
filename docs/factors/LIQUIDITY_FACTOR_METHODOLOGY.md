# Liquidity Factor Methodology

## Overview

This document describes the methodology for evaluating two key liquidity-based factors:

1. **Liquid vs Illiquid Coins (Volatility-Adjusted)**: Comparing performance of liquid and illiquid assets after normalizing for their inherent volatility
2. **Orderbook Imbalance**: Using bid/ask imbalance as a predictive signal for short-term price movements

## Research Questions

### A. Liquid vs Illiquid (Volatility-Adjusted)

**Hypothesis**: Illiquid coins may offer higher returns as compensation for illiquidity risk, but only when properly adjusted for their higher volatility. Conversely, liquid coins may be "overpriced" due to institutional preference.

**Key Question**: Do illiquid coins outperform after adjusting for volatility risk?

### B. Orderbook Imbalance

**Hypothesis**: Order book imbalance (more bids vs asks or vice versa) predicts short-term price movements because it reveals supply/demand dynamics.

**Key Question**: Does orderbook imbalance have predictive power for forward returns?

---

## Methodology

### Part A: Liquid vs Illiquid (Volatility-Adjusted)

#### 1. Data Collection

Use CCXT to collect orderbook snapshots at regular intervals:

```bash
# Collect snapshots every 5 minutes for 1 hour (12 snapshots)
python3 data/scripts/collect_liquidity_snapshots.py \
    --all \
    --interval 300 \
    --duration 3600 \
    --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
    --output data/raw/liquidity_snapshots.csv \
    --append

# Or single snapshot
python3 data/scripts/collect_liquidity_snapshots.py \
    --symbols BTC/USDC:USDC ETH/USDC:USDC SOL/USDC:USDC \
    --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
    --output data/raw/liquidity_snapshot_latest.csv
```

**Required Data**:
- Order book depth (20+ levels recommended)
- Historical price data for volatility calculation
- Ticker data for volume

#### 2. Liquidity Metrics Calculation

Calculate comprehensive liquidity metrics using `calc_liquidity_metrics.py`:

```bash
python3 signals/calc_liquidity_metrics.py \
    --all \
    --depth 20 \
    --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
    --csv liquidity_metrics.csv
```

**Key Metrics**:

1. **Spread-Based**:
   - `spread_pct`: Bid-ask spread as % of mid price
   - `spread_vol_adj`: Spread normalized by 30-day volatility
   - Formula: `spread_vol_adj = (spread_pct / volatility_30d)`
   - Interpretation: Higher = more illiquid relative to volatility

2. **Depth-Based**:
   - `depth_impact_1000`: Slippage % for $1,000 order
   - `depth_impact_1000_vol_adj`: Depth impact normalized by volatility
   - Measures: Cost to execute order of given size

3. **Composite Score**:
   - `liquidity_score`: Combined metric (spread + depth, vol-adjusted)
   - Formula: `liquidity_score = spread_vol_adj + depth_impact_1000_vol_adj`
   - Lower score = more liquid

4. **Volume-Based**:
   - `amihud_illiquidity`: |return| / volume (in millions)
   - Classic measure from academic literature

#### 3. Classification

Assets are classified into liquidity regimes:

- **Liquid**: Bottom 33% by liquidity_score
- **Medium**: Middle 33%
- **Illiquid**: Top 33%

Or use quintiles for more granular analysis.

#### 4. Performance Analysis

Compare returns across liquidity groups:

```bash
python3 signals/analyze_liquidity_factor.py \
    --liquidity-file data/raw/liquidity_snapshots.csv \
    --price-file data/raw/combined_coinbase_coinmarketcap_daily.csv \
    --forward-days 1 \
    --output-dir backtests/results
```

**Analysis Includes**:
- Correlation between liquidity metrics and forward returns
- Quintile analysis (returns by liquidity quintile)
- Liquid vs Illiquid portfolio comparison
- Risk-adjusted returns (Sharpe ratios)

#### 5. Expected Findings

**Possible Outcomes**:

1. **Illiquidity Premium**: Illiquid coins outperform (positive alpha)
   - Suggests market rewards illiquidity risk
   - Trading strategy: Overweight illiquid (with size limits)

2. **Liquidity Premium**: Liquid coins outperform
   - Suggests illiquid coins are fairly priced for risk
   - Trading strategy: Stick to liquid instruments

3. **No Relationship**: No clear pattern
   - Liquidity not a significant factor after vol adjustment
   - Use liquidity only as a filter (minimum threshold)

### Part B: Orderbook Imbalance

#### 1. Data Collection

Same as Part A - use `collect_liquidity_snapshots.py` which automatically includes imbalance metrics.

#### 2. Imbalance Metrics

Calculate using `calc_orderbook_imbalance_signals.py`:

```bash
python3 signals/calc_orderbook_imbalance_signals.py \
    --all \
    --depth 10 \
    --threshold 0.2 \
    --csv orderbook_signals.csv \
    --portfolio-csv orderbook_portfolio.csv
```

**Key Imbalance Metrics**:

1. **Value-Weighted Imbalance** (PRIMARY):
   ```
   imbalance = (total_bid_value - total_ask_value) / (total_bid_value + total_ask_value)
   ```
   - Range: -1 (all asks) to +1 (all bids)
   - Positive = bullish, Negative = bearish

2. **Top-of-Book Imbalance**:
   ```
   tob_imbalance = (best_bid_size - best_ask_size) / (best_bid_size + best_ask_size)
   ```
   - Focuses on immediate liquidity
   - More sensitive to short-term moves

3. **Depth-Weighted Imbalance**:
   - Applies exponential decay weights by level
   - Gives more weight to levels closer to mid price
   - More robust to spoofing

4. **Composite Imbalance**:
   - Average of multiple imbalance measures
   - More robust to individual metric noise

#### 3. Signal Generation

**Signal Rules**:
- `imbalance > +0.2` ? **LONG** signal (more bids)
- `imbalance < -0.2` ? **SHORT** signal (more asks)
- `-0.2 ? imbalance ? +0.2` ? **NEUTRAL**

**Signal Quality Metrics**:
- `signal_strength`: Absolute value of imbalance (0-1)
- `signal_agreement`: % of metrics agreeing on direction
- `signal_consistency`: How aligned different measures are

#### 4. Signal Filtering

Filter signals for portfolio construction:

```python
# Minimum signal strength
min_signal_strength = 0.3

# Minimum liquidity (to avoid illiquid instruments)
min_liquidity = 10000  # $10k

# Maximum spread (avoid wide spreads)
max_spread_pct = 0.1  # 0.1%
```

#### 5. Performance Evaluation

Analyze signal performance:

```bash
python3 signals/analyze_liquidity_factor.py \
    --liquidity-file data/raw/liquidity_snapshots.csv \
    --price-file data/raw/combined_coinbase_coinmarketcap_daily.csv \
    --forward-days 1
```

**Metrics**:
- Mean return by signal (LONG/SHORT/NEUTRAL)
- Directional accuracy (% of signals profitable)
- Sharpe ratio of signal returns
- Signal persistence (how long it lasts)

#### 6. Expected Findings

**Possible Outcomes**:

1. **Predictive Signal**: Clear relationship between imbalance and forward returns
   - Strategy: Trade in direction of imbalance
   - Holding period: Short-term (minutes to hours)

2. **Contrarian Signal**: Inverse relationship
   - Large imbalance precedes reversal (liquidity absorption)
   - Strategy: Fade extreme imbalances

3. **No Predictability**: Random relationship
   - Order book may be manipulated (spoofing)
   - Imbalance reflects liquidity, not intent

---

## Implementation Workflow

### Step 1: Collect Initial Data

```bash
# Get price data with volatility
python3 signals/calc_vola.py  # If needed

# Collect liquidity snapshot
python3 data/scripts/collect_liquidity_snapshots.py \
    --all \
    --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
    --output data/raw/liquidity_snapshot.csv
```

### Step 2: Calculate Metrics

```bash
# Calculate liquidity metrics (volatility-adjusted)
python3 signals/calc_liquidity_metrics.py \
    --all \
    --depth 20 \
    --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
    --csv liquidity_metrics.csv

# Generate orderbook imbalance signals
python3 signals/calc_orderbook_imbalance_signals.py \
    --all \
    --depth 10 \
    --threshold 0.2 \
    --csv orderbook_signals.csv
```

### Step 3: Collect Time Series (for backtesting)

For proper backtesting, collect snapshots over time:

```bash
# Collect every 5 minutes for 24 hours
python3 data/scripts/collect_liquidity_snapshots.py \
    --all \
    --interval 300 \
    --duration 86400 \
    --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
    --output data/raw/liquidity_snapshots_historical.csv \
    --append
```

**Recommended Collection Frequency**:
- Intraday signals: Every 5-15 minutes
- Daily signals: Once per day at same time
- Live trading: Real-time or every 30-60 seconds

### Step 4: Analyze Results

```bash
python3 signals/analyze_liquidity_factor.py \
    --liquidity-file data/raw/liquidity_snapshots_historical.csv \
    --price-file data/raw/combined_coinbase_coinmarketcap_daily.csv \
    --forward-days 1 \
    --output-dir backtests/results
```

This generates:
- Correlation analysis
- Quintile/decile returns
- Visualizations (scatter plots, bar charts)
- Statistical significance tests

---

## Key Metrics Explained

### Volatility-Adjusted Spread

**Formula**:
```
spread_vol_adj = spread_pct / volatility_30d
```

**Interpretation**:
- BTC: 0.01% spread, 2% daily vol ? ratio = 0.01/2 = 0.005
- SHIB: 0.10% spread, 10% daily vol ? ratio = 0.10/10 = 0.010

Even though SHIB has 10x wider spread, it's only 2x worse relative to its volatility. This makes comparison fair.

**Why Important**: Traditional spread metrics favor large-cap coins with low volatility. Vol-adjustment levels the playing field.

### Orderbook Imbalance

**Formula**:
```
imbalance = (? bid_value - ? ask_value) / (? bid_value + ? ask_value)
```

**Example**:
- Total bids: $1M
- Total asks: $500K
- Imbalance: (1M - 0.5M) / (1M + 0.5M) = 0.33

**Interpretation**:
- +0.33 = Strong bullish pressure (more buy orders)
- Signal: LONG
- Expected: Price likely to increase short-term

### Market Impact (Depth)

**Formula**:
Walk the order book to calculate average execution price for $X order.

**Example** ($1000 buy order):
```
Ask levels:
$100.00 @ 5 units ? Fill $500
$100.10 @ 3 units ? Fill $300.30
$100.20 @ 2 units ? Fill $200.40 (partial)

Avg execution price: $100.067
Mid price: $100.00
Impact: 0.067% (6.7 bps)
```

**Vol-Adjusted**: If daily vol is 2%, then `depth_impact_vol_adj = 0.067/2 = 0.034`

---

## Best Practices

### Data Quality

1. **Snapshot Timing**:
   - Avoid market opens/closes (high volatility)
   - Prefer consistent times (e.g., every hour on the hour)
   - Account for timezone differences

2. **Depth Selection**:
   - Minimum: 10 levels (captures immediate liquidity)
   - Recommended: 20 levels (better depth analysis)
   - Maximum: 50 levels (diminishing returns, slower)

3. **Symbol Universe**:
   - Focus on actively traded perpetuals
   - Exclude extremely low-volume pairs
   - Check for stale order books (no recent trades)

### Signal Generation

1. **Threshold Selection**:
   - Start conservative (?0.3 for imbalance)
   - Backtest to optimize
   - Consider dynamic thresholds by market regime

2. **Filtering**:
   - Always filter by minimum liquidity
   - Exclude wide-spread instruments (>0.2%)
   - Check signal agreement across metrics

3. **Position Sizing**:
   - Scale by signal strength
   - Cap positions in illiquid assets (max 2% notional)
   - Use liquidity_score for sizing limits

### Analysis

1. **Forward Returns**:
   - 1-day: Tests daily rebalancing strategy
   - 1-hour: Tests intraday signal
   - Multiple periods: Tests persistence

2. **Statistical Significance**:
   - Require minimum sample size (n > 100)
   - Use t-tests for mean differences
   - Adjust for multiple testing (Bonferroni)

3. **Robustness Checks**:
   - Out-of-sample testing (train/test split)
   - Different market regimes (bull/bear/sideways)
   - Exclude outliers (cap returns at ?3 std)

---

## Integration with Existing Strategies

### As a Factor

Add liquidity as a factor alongside existing ones:

```python
# In your strategy
from signals.calc_liquidity_metrics import calculate_liquidity_metrics

# Get liquidity scores
df_liq = calculate_liquidity_metrics(
    symbols=active_symbols,
    price_data=df_prices
)

# Combine with other factors
df_signals['liquidity_score'] = df_liq.set_index('symbol')['liquidity_score']
df_signals['composite_score'] = (
    df_signals['momentum_zscore'] +
    df_signals['mean_reversion_signal'] -
    df_signals['liquidity_score'] * 0.1  # Penalize illiquid
)
```

### As a Filter

Use liquidity as a constraint:

```python
# Only trade liquid assets
min_liquidity = df_liq['liquidity_score'].quantile(0.5)
tradeable = df_liq[df_liq['liquidity_score'] < min_liquidity]['symbol']

df_portfolio = df_signals[df_signals['symbol'].isin(tradeable)]
```

### As a Signal

Use orderbook imbalance for timing:

```python
from signals.calc_orderbook_imbalance_signals import calculate_orderbook_imbalance_signals

# Get imbalance signals
df_imb = calculate_orderbook_imbalance_signals(symbols=active_symbols)

# Filter for strong signals
strong_signals = df_imb[
    (df_imb['signal'] != 0) &
    (df_imb['signal_strength'] > 0.3) &
    (df_imb['signal_agreement'] > 0.75)
]

# Use for entry timing or weighting
for symbol in strong_signals['symbol']:
    signal_direction = strong_signals[strong_signals['symbol']==symbol]['signal'].iloc[0]
    # Increase/decrease position based on signal
```

---

## Limitations and Considerations

### Data Limitations

1. **Snapshot Frequency**:
   - Order books change rapidly
   - Single snapshot may not be representative
   - Consider using moving averages

2. **Exchange-Specific**:
   - Liquidity varies by exchange
   - Results may not generalize
   - Use exchange where you trade

3. **Manipulation**:
   - Order books can be spoofed
   - Large fake orders to create imbalance
   - Look for confirmed fills, not just quotes

### Strategy Limitations

1. **Capacity Constraints**:
   - Illiquid assets have low capacity
   - Can't scale to large AUM
   - Self-impact from your trades

2. **Transaction Costs**:
   - Illiquid assets = higher slippage
   - May offset illiquidity premium
   - Model realistic execution costs

3. **Signal Decay**:
   - Orderbook imbalance is short-lived
   - May change before you execute
   - Need fast execution infrastructure

### Market Microstructure

1. **Time of Day Effects**:
   - Liquidity varies by time
   - US market hours vs Asia hours
   - Consider timezone in analysis

2. **Market Regime**:
   - Liquidity dries up in crashes
   - Imbalance patterns differ by regime
   - Test across different market conditions

3. **Correlation Effects**:
   - Liquidity changes together across assets
   - Systematic liquidity risk
   - Diversify across liquidity regimes

---

## Success Metrics

### Part A: Liquid vs Illiquid

**Evidence of Signal**:
- Monotonic relationship between liquidity_score and returns
- Significant return differential (top vs bottom quintile)
- Consistent across time periods
- Sharpe ratio improvement when incorporated

**Threshold for Live Trading**:
- |correlation| > 0.05 with forward returns
- Quintile spread > 0.5% daily return
- Sharpe ratio > 1.0 for long-short portfolio
- Consistent over 6+ months of data

### Part B: Orderbook Imbalance

**Evidence of Signal**:
- Directional accuracy > 52%
- Mean signal return > 0
- Positive Sharpe ratio (annualized > 1.5)
- Signal agreement > 70%

**Threshold for Live Trading**:
- Sharpe ratio > 2.0 (intraday strategy)
- Win rate > 55%
- Average winning trade > average losing trade
- Signal persists for at least 5-15 minutes

---

## Next Steps

1. **Initial Analysis** (Week 1):
   - Collect 7 days of snapshots (every 15 min)
   - Calculate metrics and correlations
   - Determine if signal exists

2. **Deep Dive** (Week 2-3):
   - If signal exists, collect more data (30+ days)
   - Optimize thresholds and parameters
   - Test across different market regimes

3. **Paper Trading** (Week 4-6):
   - Deploy signal in paper trading
   - Monitor execution quality
   - Refine filters and position sizing

4. **Live Trading** (Week 7+):
   - Start with small allocation (1-5%)
   - Monitor performance vs backtest
   - Scale up if performing well

---

## References

### Academic Literature

- Amihud, Y. (2002): "Illiquidity and stock returns: cross-section and time-series effects"
- P?stor, ?., & Stambaugh, R. F. (2003): "Liquidity risk and expected stock returns"
- Cont, R., et al. (2014): "The price impact of order book events"

### Related Documentation

- `/workspace/docs/data-collection/ORDERBOOK_LIQUIDITY_ACCESS.md` - Data access methods
- `/workspace/execution/fetch_orderbook_liquidity.py` - Basic liquidity fetcher
- `/workspace/signals/calc_vola.py` - Volatility calculation

### Tools Created

1. **Data Collection**:
   - `data/scripts/collect_liquidity_snapshots.py` - Automated snapshot collection

2. **Metrics Calculation**:
   - `signals/calc_liquidity_metrics.py` - Volatility-adjusted liquidity metrics
   - `signals/calc_orderbook_imbalance_signals.py` - Imbalance signal generation

3. **Analysis**:
   - `signals/analyze_liquidity_factor.py` - Factor performance analysis

---

## FAQ

**Q: How often should I collect snapshots?**
A: Depends on strategy horizon. Intraday: every 5-15 min. Daily: once per day. Start with 1-hour intervals for initial testing.

**Q: What if liquidity and returns are uncorrelated?**
A: Still useful as a filter (minimum liquidity threshold) and for position sizing. Not all factors need to be predictive.

**Q: Can I use this with other exchanges besides Hyperliquid?**
A: Yes! All scripts support any CCXT exchange. Just pass `--exchange binance` etc.

**Q: How much historical data do I need?**
A: Minimum 100 observations per symbol (e.g., 100 days of daily data). More is better for statistical significance.

**Q: What about HFT/market making implications?**
A: These metrics are designed for low-frequency trading (minutes to days). HFT requires tick-by-tick data and different methodology.

**Q: Should I use this for execution or alpha?**
A: Both! Liquidity metrics inform execution (where/when to trade) AND alpha (which assets to overweight).
