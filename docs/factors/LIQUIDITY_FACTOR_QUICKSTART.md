# Liquidity Factor Analysis - Quick Start Guide

This guide provides the fastest path to evaluating liquidity-based factors.

## Goals

1. **Liquid vs Illiquid (Volatility-Adjusted)**: Compare performance of liquid and illiquid coins after normalizing for volatility
2. **Orderbook Imbalance**: Test if orderbook imbalance predicts short-term price movements

---

## Quick Start (30 minutes)

### Step 1: Collect Single Snapshot (5 min)

Get current liquidity metrics for top markets:

```bash
python3 signals/calc_liquidity_metrics.py \
    --all \
    --depth 20 \
    --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
    --csv liquidity_metrics_latest.csv
```

**Output**: `liquidity_metrics_latest.csv` with metrics for ~20 instruments

**What to look for**:
- `spread_vol_adj`: Volatility-adjusted spread (lower = more liquid)
- `liquidity_score`: Composite liquidity metric (lower = more liquid)
- Wide variation indicates meaningful differences between assets

### Step 2: Generate Orderbook Imbalance Signals (5 min)

```bash
python3 signals/calc_orderbook_imbalance_signals.py \
    --all \
    --depth 10 \
    --threshold 0.2 \
    --csv orderbook_signals_latest.csv \
    --portfolio-csv orderbook_portfolio_latest.csv
```

**Output**: 
- `orderbook_signals_latest.csv`: All signals
- `orderbook_portfolio_latest.csv`: Filtered tradeable signals

**What to look for**:
- Distribution of LONG/SHORT/NEUTRAL signals
- Signal strength and agreement metrics
- Any extreme imbalances (|imbalance| > 0.5)

### Step 3: Collect Time Series Data (20 min)

Collect snapshots every 5 minutes for 1 hour (for initial testing):

```bash
python3 data/scripts/collect_liquidity_snapshots.py \
    --all \
    --interval 300 \
    --duration 3600 \
    --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
    --output data/raw/liquidity_snapshots_test.csv \
    --depth 20
```

**Output**: `data/raw/liquidity_snapshots_test.csv` with 12 snapshots per symbol

### Step 4: Quick Analysis (5 min - optional)

If you have at least 1 day of snapshot data:

```bash
python3 signals/analyze_liquidity_factor.py \
    --liquidity-file data/raw/liquidity_snapshots_test.csv \
    --price-file data/raw/combined_coinbase_coinmarketcap_daily.csv \
    --forward-days 1 \
    --output-dir backtests/results
```

**Output**:
- Correlation analysis (printed to console)
- Visualizations in `backtests/results/`
- `liquidity_factor_analysis.csv` with numerical results

---

## Understanding the Results

### Liquidity Metrics (from Step 1)

**Best metrics to focus on**:

1. **`liquidity_score`**: All-in-one metric (lower = more liquid)
   - Compare across assets to identify liquid vs illiquid

2. **`spread_vol_adj`**: Spread relative to volatility
   - Fair comparison across different volatility regimes

3. **`orderbook_imbalance`**: Current bid/ask balance
   - Positive = more bids (bullish), Negative = more asks (bearish)

**Example interpretation**:

```
Symbol              liquidity_score  spread_vol_adj  orderbook_imbalance
BTC/USDC:USDC       0.05            0.002           +0.15
DOGE/USDC:USDC      0.45            0.025           -0.32
```

- BTC is much more liquid (score 0.05 vs 0.45)
- BTC has slight bid pressure (+0.15)
- DOGE has ask pressure (-0.32) ? bearish signal

### Orderbook Imbalance Signals (from Step 2)

**Signal interpretation**:

```
signal = 1   ? LONG (more bids than asks)
signal = 0   ? NEUTRAL (balanced)
signal = -1  ? SHORT (more asks than bids)
```

**Signal quality**:
- `signal_strength`: 0.3+ is decent, 0.5+ is strong
- `signal_agreement`: 0.75+ means metrics agree (more reliable)

**Example**:

```
Symbol              imbalance_weighted  signal  signal_strength  signal_agreement
SOL/USDC:USDC       +0.42              1       0.42            0.85
ETH/USDC:USDC       -0.18              0       0.18            0.60
```

- SOL: Strong LONG signal (high strength + agreement)
- ETH: Neutral (below 0.2 threshold)

---

## Next Steps

### If Signals Look Promising

Collect more data for proper analysis:

```bash
# Collect snapshots every 15 minutes for 7 days
# Run this in background or via cron job
python3 data/scripts/collect_liquidity_snapshots.py \
    --all \
    --interval 900 \
    --duration 604800 \
    --price-data data/raw/combined_coinbase_coinmarketcap_daily.csv \
    --output data/raw/liquidity_snapshots_7d.csv \
    --append
```

This gives you:
- 672 snapshots per symbol (7 days * 96 snapshots/day)
- Enough data for meaningful statistical analysis

### If Signals Look Weak

Try different parameters:

```bash
# More conservative threshold (only trade strong signals)
python3 signals/calc_orderbook_imbalance_signals.py \
    --all \
    --threshold 0.3 \
    --csv orderbook_signals_conservative.csv

# Less decay (weight all levels equally)
python3 signals/calc_orderbook_imbalance_signals.py \
    --all \
    --no-decay-weights \
    --csv orderbook_signals_equal_weight.csv
```

---

## Common Issues

### Issue: "No merged data" in analysis

**Cause**: Symbol format mismatch between liquidity and price files

**Solution**: Check symbol formats:
```bash
# Check liquidity file symbols
head -5 data/raw/liquidity_snapshots_test.csv | cut -d',' -f1

# Check price file symbols  
head -5 data/raw/combined_coinbase_coinmarketcap_daily.csv | cut -d',' -f2
```

Both should use same format (e.g., `BTC/USDC:USDC` or `BTC`)

### Issue: Rate limit errors

**Cause**: Fetching too many symbols too quickly

**Solution**: 
- Reduce number of symbols: `--symbols BTC/USDC:USDC ETH/USDC:USDC SOL/USDC:USDC`
- Increase sleep time in code (edit scripts)
- Use `--depth 10` instead of `--depth 20`

### Issue: Missing volatility data

**Cause**: No historical prices in price data file

**Solution**:
- Ensure price file has 30+ days of history per symbol
- Run without `--price-data` flag (will skip vol-adjustment)

---

## Interpretation Examples

### Example 1: Strong Liquidity Factor

**Results**:
```
Correlation: liquidity_score vs 1d return = -0.08
Quintile Analysis:
  Q1 (Liquid):    0.12% daily return
  Q5 (Illiquid):  0.05% daily return
```

**Interpretation**: 
- Liquid coins outperform (negative correlation)
- Liquidity premium exists
- **Strategy**: Overweight liquid assets

### Example 2: Weak Liquidity Factor

**Results**:
```
Correlation: liquidity_score vs 1d return = 0.01
Quintile Analysis:
  Q1: 0.08%
  Q5: 0.09%
```

**Interpretation**:
- No clear relationship
- Liquidity not predictive after vol-adjustment
- **Strategy**: Use liquidity only as filter (min threshold)

### Example 3: Strong Imbalance Signal

**Results**:
```
Signal Performance:
  LONG signals:  Mean return = +0.25%, Sharpe = 2.1
  SHORT signals: Mean return = +0.18%, Sharpe = 1.8
  Directional accuracy: 58%
```

**Interpretation**:
- Imbalance predicts direction (58% accuracy)
- Both long and short profitable (directional strategy)
- **Strategy**: Trade in direction of imbalance

### Example 4: Weak Imbalance Signal

**Results**:
```
Signal Performance:
  LONG signals:  Mean return = +0.05%, Sharpe = 0.3
  SHORT signals: Mean return = +0.02%, Sharpe = 0.1
  Directional accuracy: 49%
```

**Interpretation**:
- No predictive power (49% = random)
- Low Sharpe ratios
- **Strategy**: Don't use imbalance for this market/timeframe

---

## File Reference

### Scripts

- **Metrics Calculator**: `signals/calc_liquidity_metrics.py`
- **Imbalance Signals**: `signals/calc_orderbook_imbalance_signals.py`
- **Data Collection**: `data/scripts/collect_liquidity_snapshots.py`
- **Analysis**: `signals/analyze_liquidity_factor.py`

### Documentation

- **Full Methodology**: `docs/factors/LIQUIDITY_FACTOR_METHODOLOGY.md`
- **Data Access**: `docs/data-collection/ORDERBOOK_LIQUIDITY_ACCESS.md`

### Output Files

- **Latest Metrics**: `liquidity_metrics_latest.csv`
- **Latest Signals**: `orderbook_signals_latest.csv`
- **Time Series**: `data/raw/liquidity_snapshots_*.csv`
- **Analysis Results**: `backtests/results/liquidity_factor_*.csv`
- **Visualizations**: `backtests/results/*.png`

---

## Decision Framework

After collecting 7+ days of data, use this framework to decide:

### Decision Tree

1. **Is there correlation between liquidity_score and returns?**
   - Yes (|corr| > 0.05) ? Go to #2
   - No ? Use liquidity only as filter

2. **Which direction?**
   - Negative (liquid outperform) ? Overweight liquid
   - Positive (illiquid outperform) ? Overweight illiquid (with capacity limits)

3. **Does orderbook imbalance predict returns?**
   - Yes (Sharpe > 1.5) ? Go to #4
   - No ? Skip imbalance signals

4. **What timeframe?**
   - 1-hour returns best ? Intraday strategy
   - 1-day returns best ? Daily rebalancing
   - Both work ? Multi-timeframe strategy

5. **Live trading ready?**
   - Sharpe > 2.0 AND consistent > 3 months ? Yes, start small
   - Otherwise ? Collect more data or optimize further

---

## Recommended Timeline

**Week 1**: 
- Collect snapshots every 15 min, 24/7
- Initial analysis after 7 days
- Decide if signal exists

**Week 2-3**: 
- Continue collection (build to 21+ days)
- Optimize thresholds and parameters
- Out-of-sample testing

**Week 4-6**: 
- Paper trading (if signal looks good)
- Monitor execution quality
- Compare live vs backtest

**Week 7+**: 
- Small live allocation (1-5%)
- Scale up if performing

---

## Support

For issues or questions:
1. Check full methodology: `docs/factors/LIQUIDITY_FACTOR_METHODOLOGY.md`
2. Review existing scripts in `signals/` and `data/scripts/`
3. Check order book access guide: `docs/data-collection/ORDERBOOK_LIQUIDITY_ACCESS.md`

---

Good luck with your analysis! ??
