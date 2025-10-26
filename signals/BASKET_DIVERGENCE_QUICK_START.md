# Basket Divergence Signals - Quick Start Guide

**Generated:** 2025-10-26  
**Phase:** 3 Complete  
**Script:** `signals/calc_basket_divergence_signals.py`

---

## What Are Basket Divergence Signals?

Basket divergence signals identify cryptocurrencies that have significantly diverged from their sector/category average performance. The hypothesis is that these divergences will mean-revert, creating profitable trading opportunities.

### Signal Types

- **LONG**: Coin has significantly underperformed its basket (buy the dip)
- **SHORT**: Coin has significantly outperformed its basket (fade the rally)
- **NONE**: No significant divergence

---

## Quick Usage

### View Current Signals

```bash
# See latest signals
cat signals/basket_divergence_signals_current.csv

# View in readable format
column -t -s, signals/basket_divergence_signals_current.csv | less -S
```

### View Historical Signals

```bash
# All signals since 2020
head -50 signals/basket_divergence_signals_full.csv

# Count signals by category
tail -n +2 signals/basket_divergence_signals_full.csv | cut -d, -f3,4 | sort | uniq -c
```

### Generate Fresh Signals

```bash
# Tier 1 categories (recommended)
python3 signals/calc_basket_divergence_signals.py \
    --categories "Meme Coins,Dino Coins"

# All categories
python3 signals/calc_basket_divergence_signals.py \
    --all-categories \
    --min-basket-size 3

# Custom parameters
python3 signals/calc_basket_divergence_signals.py \
    --categories "Meme Coins" \
    --lookback 90 \
    --threshold 2.0 \
    --basket-weight market_cap
```

---

## Understanding the Signals

### Key Metrics

**Z-Score:**
- Measures how many standard deviations coin is from basket average
- Z < -1.5 → LONG signal (underperformer)
- Z > +1.5 → SHORT signal (outperformer)
- Based on 60-day rolling window

**Percentile Rank:**
- Coin's rank within basket based on 20-day returns
- 0-25th percentile → LONG signal
- 75-100th percentile → SHORT signal

**Basket Correlation:**
- Rolling 60-day correlation between coin and basket
- Must be > 0.3 to generate signal
- Higher correlation = more reliable mean reversion

### Example Signal Interpretation

```csv
date,symbol,category,signal,z_score,percentile_rank,basket_corr,divergence
2025-10-20,GIGA,Meme Coins,LONG,-2.18,16.67,0.77,-0.092
```

**Translation:**
- GIGA underperformed Meme basket by 2.18 standard deviations
- Ranked 16.67th percentile (bottom 17% of basket)
- 77% correlated with basket (high)
- Divergence: -9.2% relative underperformance
- **Action:** Consider going LONG (expecting mean reversion up)

---

## Current Signals Summary (2025-10-24)

### Active Categories

| Category | Symbols | Current Signals |
|----------|---------|-----------------|
| Meme Coins | 11 | 10 observations (all NONE currently) |
| Dino Coins | 5 | 2 observations (ALGO, XLM) |

### Recent Active Signals

Most recent LONG/SHORT signals were on **2025-10-20**:

**LONG:**
- GIGA (Meme Coins): z-score = -2.18

**SHORT:**
- FLOKI (Meme Coins): z-score = 5.04

---

## Signal Statistics

### Overall (2020-2025)

- **Total Observations:** 7,707
- **Active Signals:** 245 (3.2%)
  - LONG: 13 (0.2%)
  - SHORT: 232 (3.0%)
  - NONE: 7,462 (96.8%)

### By Category

| Category | LONG | SHORT | Total Obs |
|----------|------|-------|-----------|
| Meme Coins | 13 | 50 | 2,128 |
| Dino Coins | 0 | 142 | 4,287 |
| L1 Smart Contract | 0 | 20 | 681 |
| SOL Ecosystem | 0 | 20 | 611 |

**Note:** SHORT signals dominate (94.7% of active signals), suggesting bull market regime or momentum persistence.

---

## Filters Applied

All signals are pre-filtered by:

- ✅ **Liquidity:** 30-day avg volume > $5M
- ✅ **Market Cap:** > $50M
- ✅ **Volatility:** < 150% annualized
- ✅ **Data Quality:** ≥ 90 days of continuous data
- ✅ **Correlation:** > 0.3 with basket

---

## Categories Analyzed

### Tier 1 (Highest Quality)

1. **Meme Coins** (11 symbols)
   - DOGE, SHIB, PEPE, BONK, WIF, FLOKI, etc.
   - Best signal quality (balanced LONG/SHORT)
   - High volatility → frequent divergences

2. **Dino Coins** (5 symbols)
   - LTC, XRP, XLM, ALGO, EOS
   - Longest history (2020-2025)
   - Only SHORT signals (persistent underperformers)

### Tier 2 (Active)

3. **L1 Smart Contract** (4 symbols)
   - SOL, ADA, AVAX, DOT
   - Only SHORT signals
   - Small basket size

4. **SOL Ecosystem** (3 symbols)
   - SOL, BONK, WIF
   - Only SHORT signals
   - Shortest history

### Skipped Categories

- **DeFi Blue Chips:** Only 2 symbols passed filters (needs adjustment)
- **L2 Scaling:** Only 1 symbol passed filters
- **AI/Compute:** Only 2 symbols passed filters

---

## Output Files

### `basket_divergence_signals_full.csv`

Complete historical signals from 2020-01-29 to 2025-10-24.

**Columns:**
```
date, symbol, category, signal, z_score, percentile_rank, basket_corr,
basket_return_20d, coin_return_20d, divergence, market_cap, volume_30d, volatility_30d
```

**Use Case:** Backtesting, historical analysis

### `basket_divergence_signals_current.csv`

Most recent signals only (latest date).

**Use Case:** Live trading, current opportunities

### `basket_divergence_signals_by_category.csv`

Summary statistics by category.

**Columns:**
```
category, LONG, SHORT, NONE
```

**Use Case:** Quick overview, category selection

---

## Python API Usage

### Load Signals

```python
import pandas as pd

# Load full signals
signals = pd.read_csv('signals/basket_divergence_signals_full.csv')
signals['date'] = pd.to_datetime(signals['date'])

# Filter to active signals only
active = signals[signals['signal'].isin(['LONG', 'SHORT'])]

# Get current signals
current = signals[signals['date'] == signals['date'].max()]
```

### Analyze by Category

```python
# Signal counts by category
print(signals.groupby(['category', 'signal']).size().unstack(fill_value=0))

# Average z-score by signal type
print(active.groupby('signal')['z_score'].describe())
```

### Filter by Criteria

```python
# Strong LONG signals (z < -2)
strong_longs = active[(active['signal'] == 'LONG') & (active['z_score'] < -2)]

# High correlation signals
high_corr = active[active['basket_corr'] > 0.7]

# Recent signals (last 30 days)
recent = active[active['date'] >= '2025-09-24']
```

---

## Trading Strategy Example

### Simple Mean Reversion

1. **Entry:**
   - LONG when z-score < -1.5 and percentile < 25
   - SHORT when z-score > +1.5 and percentile > 75

2. **Exit:**
   - Close when z-score crosses back to [-0.5, 0.5]
   - Or after 10 days (time-based)
   - Stop loss at -10%, take profit at +15%

3. **Position Sizing:**
   - Equal weight across all active signals
   - Max 20 concurrent positions
   - Max 3 positions per category

4. **Risk Management:**
   - Dollar-neutral (equal long/short notional)
   - Daily rebalancing
   - Monitor correlation breakdown

### Backtest (Phase 4)

```python
# To be implemented in Phase 4
python3 backtests/scripts/backtest_basket_pairs_trading.py \
    --signal-file signals/basket_divergence_signals_full.csv \
    --holding-period 10 \
    --stop-loss 0.10 \
    --take-profit 0.15 \
    --max-positions 20
```

---

## Next Steps

### For Research

1. ✅ **Phase 3 Complete:** Signals generated
2. 🔄 **Phase 4 Next:** Backtest signals
3. ⏳ **Phase 5:** Parameter optimization
4. ⏳ **Phase 6:** Live trading integration

### For Users

1. **Explore signals:**
   ```bash
   cat signals/basket_divergence_signals_current.csv
   ```

2. **Understand baskets:**
   ```bash
   cat data/raw/category_mappings_validated.csv | grep "Meme Coins"
   ```

3. **Generate custom signals:**
   ```bash
   python3 signals/calc_basket_divergence_signals.py --help
   ```

4. **Wait for Phase 4 backtest results** to see profitability

---

## FAQs

### Q: Why are there so few LONG signals?

**A:** The market has been in a bull regime where coins tend to outperform their baskets (momentum). This creates more SHORT opportunities than LONG. Consider:
- Using asymmetric thresholds (-2.0 for LONG, +1.5 for SHORT)
- Focusing on SHORT-only strategy
- Adding trend filters to avoid fighting momentum

### Q: Why did DeFi Blue Chips fail?

**A:** Only 2 DeFi tokens passed the strict filters (volume > $5M, market cap > $50M, volatility < 150%). Consider:
- Relaxing filters for DeFi category
- Adding more DeFi tokens to data collection
- Using tiered filters by category

### Q: Can I use this for live trading?

**A:** Not yet! Phase 3 only generates signals. Wait for:
- Phase 4 backtest results (validate profitability)
- Transaction cost analysis
- Slippage modeling
- Live execution integration (Phase 6)

### Q: What's the expected Sharpe ratio?

**A:** Unknown until Phase 4 backtest completes. Target: > 0.5 (good), stretch: > 1.0 (excellent).

### Q: How often should I regenerate signals?

**A:** Daily. Run the script every day to get fresh signals based on latest prices.

---

## Support & Documentation

- **Full Spec:** `docs/PAIRS_TRADING_SPEC.md`
- **Phase 2 Results:** `docs/PAIRS_TRADING_PHASE2_COMPLETE.md`
- **Phase 3 Results:** `docs/PAIRS_TRADING_PHASE3_COMPLETE.md`
- **Script Help:** `python3 signals/calc_basket_divergence_signals.py --help`

---

**Happy Trading! 🚀**  
*Remember: Backtest before you trade. Past performance doesn't guarantee future results.*
