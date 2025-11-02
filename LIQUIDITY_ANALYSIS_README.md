# Liquidity Factor Analysis - Complete Framework

This framework enables evaluation of two liquidity-based trading factors:

1. **Liquid vs Illiquid (Volatility-Adjusted)**: Do illiquid coins outperform after normalizing for volatility?
2. **Orderbook Imbalance**: Does bid/ask imbalance predict short-term price movements?

## Quick Start

For immediate testing (30 minutes):

```bash
# 1. Calculate current liquidity metrics (volatility-adjusted)
python3 signals/calc_liquidity_metrics.py \
    --all \
    --depth 20 \
    --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
    --csv liquidity_metrics_latest.csv

# 2. Generate orderbook imbalance signals
python3 signals/calc_orderbook_imbalance_signals.py \
    --all \
    --depth 10 \
    --threshold 0.2 \
    --csv orderbook_signals_latest.csv

# 3. Collect time series for analysis (1 hour test)
python3 data/scripts/collect_liquidity_snapshots.py \
    --all \
    --interval 300 \
    --duration 3600 \
    --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
    --output data/raw/liquidity_snapshots_test.csv
```

**See**: `docs/factors/LIQUIDITY_FACTOR_QUICKSTART.md` for detailed quick start guide

## Tools Created

### 1. Liquidity Metrics Calculator
**File**: `signals/calc_liquidity_metrics.py`

Calculates comprehensive liquidity metrics normalized by volatility:
- Volatility-adjusted spreads
- Market impact estimates (depth-based)
- Composite liquidity scores
- Volume-based illiquidity (Amihud)

**Key Metrics**:
- `liquidity_score`: Composite metric (lower = more liquid)
- `spread_vol_adj`: Spread / volatility (fair comparison)
- `depth_impact_1000_vol_adj`: Vol-adjusted market impact

### 2. Orderbook Imbalance Signal Generator
**File**: `signals/calc_orderbook_imbalance_signals.py`

Generates trading signals from orderbook imbalance:
- Value-weighted imbalance (primary)
- Top-of-book imbalance
- Depth-weighted imbalance (anti-spoofing)
- Composite imbalance scores

**Signals**:
- `+1`: LONG (more bids than asks)
- `-1`: SHORT (more asks than bids)
- `0`: NEUTRAL

### 3. Snapshot Collection System
**File**: `data/scripts/collect_liquidity_snapshots.py`

Automated collection of historical liquidity data:
- Single snapshot or continuous collection
- Configurable interval (seconds)
- Includes all metrics + imbalance
- Append mode for time series

**Usage**:
```bash
# Collect every 5 minutes for 24 hours
python3 data/scripts/collect_liquidity_snapshots.py \
    --all \
    --interval 300 \
    --duration 86400 \
    --output data/raw/liquidity_snapshots.csv \
    --append
```

### 4. Performance Analysis
**File**: `signals/analyze_liquidity_factor.py`

Analyzes relationship between liquidity and returns:
- Correlation analysis
- Quintile/decile performance comparison
- Liquid vs Illiquid portfolio returns
- Orderbook imbalance signal evaluation
- Statistical visualizations

**Output**:
- Correlation matrices
- Quintile return tables
- Scatter plots and bar charts
- Signal performance metrics

## Key Concepts

### Volatility-Adjusted Liquidity

**Problem**: Traditional liquidity metrics favor large-cap, low-volatility assets

**Solution**: Normalize by volatility
```
spread_vol_adj = spread_pct / volatility_30d
```

**Example**:
- BTC: 0.01% spread, 2% vol ? ratio = 0.005
- SHIB: 0.10% spread, 10% vol ? ratio = 0.010

Both are comparable despite 10x difference in raw spread!

### Orderbook Imbalance

**Theory**: Imbalance reveals supply/demand dynamics

**Calculation**:
```
imbalance = (total_bid_value - total_ask_value) / (total_bid_value + total_ask_value)
```

**Range**: -1 (all asks) to +1 (all bids)

**Signal**:
- `imbalance > +0.2` ? LONG (buying pressure)
- `imbalance < -0.2` ? SHORT (selling pressure)

### Liquidity Score (Composite)

Combines multiple liquidity dimensions:
```
liquidity_score = spread_vol_adj + depth_impact_1000_vol_adj
```

Lower score = more liquid relative to volatility

## Workflow

### Phase 1: Initial Testing (Week 1)

```bash
# Day 1-7: Collect data
python3 data/scripts/collect_liquidity_snapshots.py \
    --all \
    --interval 900 \
    --duration 604800 \
    --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
    --output data/raw/liquidity_snapshots_7d.csv \
    --append

# Day 8: Analyze results
python3 signals/analyze_liquidity_factor.py \
    --liquidity-file data/raw/liquidity_snapshots_7d.csv \
    --price-file data/raw/combined_coinbase_coinmarketcap_daily.csv \
    --forward-days 1 \
    --output-dir backtests/results
```

**Decision Point**: Do signals have predictive power?
- Yes ? Continue to Phase 2
- No ? Adjust parameters or conclude no signal

### Phase 2: Extended Testing (Week 2-3)

- Collect 21+ days of data
- Test multiple forward return periods (1h, 4h, 1d)
- Optimize thresholds and filters
- Out-of-sample validation

### Phase 3: Paper Trading (Week 4-6)

- Deploy signals in paper trading environment
- Monitor execution quality
- Compare live vs backtest performance
- Refine position sizing

### Phase 4: Live Trading (Week 7+)

- Start with small allocation (1-5%)
- Gradually scale if performing well
- Continue monitoring and optimization

## Expected Findings

### Liquid vs Illiquid Factor

**Possible Outcomes**:

1. **Illiquidity Premium** (illiquid outperform)
   - Strategy: Overweight illiquid with size limits
   - Theory: Compensation for illiquidity risk

2. **Liquidity Premium** (liquid outperform)
   - Strategy: Focus on liquid instruments
   - Theory: Illiquid fairly priced for risk

3. **No Relationship**
   - Strategy: Use liquidity as filter only
   - Set minimum liquidity thresholds

### Orderbook Imbalance Signal

**Possible Outcomes**:

1. **Predictive Signal** (imbalance ? same direction return)
   - Strategy: Trade with imbalance
   - Timeframe: Short-term (minutes to hours)

2. **Contrarian Signal** (imbalance ? opposite direction)
   - Strategy: Fade extreme imbalances
   - Theory: Liquidity absorption

3. **No Predictability**
   - Strategy: Don't use for trading
   - Consider spoofing/manipulation

## Success Criteria

### For Liquidity Factor (Part A)

**Minimum Thresholds for Live Trading**:
- Correlation with returns: |r| > 0.05
- Quintile return spread: > 0.5% daily
- Sharpe ratio (long-short): > 1.0
- Consistency: 6+ months of data

### For Imbalance Signal (Part B)

**Minimum Thresholds for Live Trading**:
- Directional accuracy: > 52%
- Sharpe ratio: > 2.0 (intraday)
- Signal agreement: > 70%
- Win rate: > 55%

## Files and Documentation

### Scripts
```
signals/
??? calc_liquidity_metrics.py              # Calculate vol-adjusted metrics
??? calc_orderbook_imbalance_signals.py    # Generate imbalance signals
??? analyze_liquidity_factor.py            # Performance analysis

data/scripts/
??? collect_liquidity_snapshots.py         # Automated data collection

execution/
??? fetch_orderbook_liquidity.py           # Basic orderbook fetcher
```

### Documentation
```
docs/factors/
??? LIQUIDITY_FACTOR_METHODOLOGY.md        # Full methodology (40+ pages)
??? LIQUIDITY_FACTOR_QUICKSTART.md         # Quick start guide

docs/data-collection/
??? ORDERBOOK_LIQUIDITY_ACCESS.md          # CCXT vs CoinMarketCap guide
```

### Data Files
```
data/raw/
??? liquidity_snapshots.csv                # Historical snapshots
??? liquidity_metrics_latest.csv           # Latest metrics
??? orderbook_signals_latest.csv           # Latest signals

backtests/results/
??? liquidity_factor_analysis.csv          # Analysis results
??? liquidity_vs_returns.png               # Visualizations
??? orderbook_imbalance_analysis.png       # Imbalance plots
```

## Integration with Existing Strategies

### As a Factor

```python
from signals.calc_liquidity_metrics import calculate_liquidity_metrics

df_liq = calculate_liquidity_metrics(symbols, price_data=df_prices)

# Combine with existing factors
df_signals['composite_score'] = (
    df_signals['momentum_zscore'] +
    df_signals['mean_reversion_signal'] -
    df_liq['liquidity_score'] * 0.1  # Penalize illiquid
)
```

### As a Filter

```python
# Only trade liquid half of universe
median_score = df_liq['liquidity_score'].median()
tradeable = df_liq[df_liq['liquidity_score'] < median_score]['symbol']

df_portfolio = df_signals[df_signals['symbol'].isin(tradeable)]
```

### As a Signal

```python
from signals.calc_orderbook_imbalance_signals import calculate_orderbook_imbalance_signals

df_imb = calculate_orderbook_imbalance_signals(symbols)

# Filter for strong signals
strong = df_imb[
    (df_imb['signal'] != 0) &
    (df_imb['signal_strength'] > 0.3)
]

# Use for entry timing or position adjustment
```

## Limitations

### Data
- Snapshots may not capture full dynamics
- Exchange-specific (results may not generalize)
- Order books can be manipulated (spoofing)

### Strategy
- Illiquid assets have low capacity
- Transaction costs may offset premium
- Imbalance signals decay quickly

### Market Microstructure
- Liquidity varies by time of day
- Different behavior in different regimes
- Systematic liquidity risk exists

## Next Steps

1. **Read the guides**:
   - Quick start: `docs/factors/LIQUIDITY_FACTOR_QUICKSTART.md`
   - Full methodology: `docs/factors/LIQUIDITY_FACTOR_METHODOLOGY.md`

2. **Run initial test**:
   - Follow quick start (30 minutes)
   - Review outputs and decide if promising

3. **Collect time series**:
   - 7+ days continuous collection
   - Run analysis script
   - Evaluate statistical significance

4. **Optimize and deploy**:
   - If signal exists, optimize parameters
   - Paper trade, then live with small size
   - Monitor and iterate

## Support

- **Full Methodology**: See `docs/factors/LIQUIDITY_FACTOR_METHODOLOGY.md`
- **Quick Start**: See `docs/factors/LIQUIDITY_FACTOR_QUICKSTART.md`
- **Data Access**: See `docs/data-collection/ORDERBOOK_LIQUIDITY_ACCESS.md`
- **Example Scripts**: All scripts in `signals/` and `data/scripts/`

---

**Status**: ? Framework complete and ready for testing

**Created**: 2025-11-02

**Tools**: 4 scripts + 3 documentation files + examples
