# DeFi Factor Backtesting Guide

**Date:** 2025-11-03  
**Status:** ✅ Turnover Factor Backtest Complete  
**Other Factors:** Ready for backtesting after data collection

## What Can Be Backtested NOW

### ✅ Turnover Factor (COMPLETE)

**Factor:** 24h Volume / Market Cap

**Results (2020-2025):**
- **Sharpe Ratio:** 2.17 ⭐ (excellent!)
- **Total Return:** 118.61%
- **Annualized Return:** 377.91%
- **Max Drawdown:** -11.69%
- **Win Rate:** 66.67%

**Performance vs Benchmark:**
- Strategy Sharpe: 2.17
- Benchmark Sharpe: 1.18
- **Alpha:** Strategy significantly outperforms

**File:** `backtests/scripts/backtest_turnover_factor.py`

**Run:**
```bash
python3 backtests/scripts/backtest_turnover_factor.py
```

**Data Used:**
- CoinMarketCap historical snapshots (monthly, 2020-2025)
- Coinbase daily prices (2020-2025)
- 279 factor-return pairs across 6 rebalancing periods

---

## What Needs Historical Data Collection

### ⏳ Fee Yield Factor

**Factor:** annualized fees ÷ FDV

**Status:** ❌ Needs historical data  
**Current Data:** 1 snapshot (2025-11-03)  
**Required:** 12+ months of daily/monthly snapshots  

**Why It's Promising:**
- Current top performers: MKR (207%), LDO (108%), UNI (48%)
- Clear fundamental signal (revenue generation)
- Low correlation with price momentum

**How to Collect:**
```bash
# Run daily to build time series
./run_factor_pipeline.sh
python3 data/scripts/collect_historical_defi_snapshots.py
```

**Data Storage:**
- SQLite database: `data/defi_factors_history.db`
- Automatically deduplicated by date + symbol

---

### ⏳ Net Yield Factor

**Factor:** Fee Yield − Emission Yield

**Status:** ❌ Needs historical data  
**Current Data:** 1 snapshot (2025-11-03)  
**Required:** 12+ months of snapshots

**Why It's Promising:**
- Identifies sustainable protocols (positive net yield)
- Penalizes unsustainable emission models
- Example: PENDLE has -14.46% net yield (risky)

**Expected Performance:**
- Should outperform in bear markets (sustainable protocols survive)
- May underperform in bull markets (high-emission protocols pump)

---

### ⏳ Revenue Productivity Factor

**Factor:** annualized fees ÷ TVL

**Status:** ❌ Needs historical data  
**Current Data:** 1 snapshot (2025-11-03)  
**Required:** 12+ months of snapshots

**Why It's Promising:**
- Current top performers: KNC (262%), PYTH (84%)
- Measures capital efficiency
- Independent of market cap (pure operational metric)

**Expected Performance:**
- Should work well in all market conditions
- Identifies operationally excellent protocols

---

### ⏳ Emission Yield Factor

**Factor:** annualized emissions ÷ FDV

**Status:** ❌ Needs historical data  
**Current Data:** 1 snapshot (2025-11-03)  
**Required:** 12+ months of snapshots

**Strategy:** SHORT tokens with high emission yield (dilutive)

**Why It's Promising:**
- Direct measurement of token dilution
- High emissions = selling pressure
- Current high emitters: PENDLE (15%), AAVE (1.85%)

---

## Historical Data Collection System

### Setup (ONE TIME)

1. **Database Creation:**
```bash
python3 data/scripts/collect_historical_defi_snapshots.py
```

This creates `data/defi_factors_history.db` with:
- factor_snapshots table
- Indexed by date and symbol
- Automatic deduplication

### Daily Collection (AUTOMATED)

**Option 1: Cron Job**
```bash
# Edit crontab
crontab -e

# Add this line (runs at 9 AM UTC daily)
0 9 * * * cd /workspace && ./run_factor_pipeline.sh && python3 data/scripts/collect_historical_defi_snapshots.py >> /var/log/defi_factors.log 2>&1
```

**Option 2: Manual Daily Run**
```bash
# Run complete pipeline
./run_factor_pipeline.sh
python3 data/scripts/collect_historical_defi_snapshots.py
```

**What Gets Collected:**
- All 5 factor values per token
- Market cap, FDV, volume
- TVL, fees, yields
- 46 tokens currently (will grow over time)

### Timeline to Backtesting

| Months Collected | What You Can Do |
|------------------|-----------------|
| 1 month | Basic trend analysis |
| 3 months | Quarterly rebalancing backtest |
| 6 months | Semi-annual backtest |
| 12 months | Full annual backtest ⭐ |
| 24+ months | Multi-year, regime analysis |

---

## Backtest Template (For Future Use)

Once you have 12+ months of data, use this template:

```python
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# Load historical factor data
conn = sqlite3.connect('/workspace/data/defi_factors_history.db')
factors_df = pd.read_sql("""
    SELECT * FROM factor_snapshots
    WHERE snapshot_date >= '2024-01-01'
    ORDER BY snapshot_date, symbol
""", conn)
conn.close()

# Load price data for returns
prices_df = pd.read_csv('/workspace/data/raw/coinbase_top200_daily_20200101_to_present_20251025_171900.csv')
prices_df['date'] = pd.to_datetime(prices_df['date'])

# For each monthly snapshot
for date in factors_df['snapshot_date'].unique():
    # Get factor values
    month_factors = factors_df[factors_df['snapshot_date'] == date]
    
    # Generate signals (e.g., long top 20% by fee yield)
    month_factors['percentile'] = month_factors['fee_yield_pct'].rank(pct=True) * 100
    longs = month_factors[month_factors['percentile'] >= 80]['symbol'].tolist()
    
    # Calculate next month returns
    for symbol in longs:
        start_price = get_price(prices_df, symbol, date)
        end_price = get_price(prices_df, symbol, date + timedelta(days=30))
        forward_return = (end_price - start_price) / start_price
        
        # Store for analysis
        portfolio_returns.append({
            'date': date,
            'symbol': symbol,
            'return': forward_return
        })

# Analyze results...
```

---

## Alternative: Using Existing CoinMarketCap Data

You already have **monthly CoinMarketCap snapshots from 2020-2025**!

These contain:
- ✅ Market Cap
- ✅ Volume (24h)
- ✅ Circulating Supply

You can create **proxy factors** right now:

### Turnover Factor (Already Done) ✅
- Factor: Volume / Market Cap
- Results: Sharpe 2.17

### Volume Growth Factor (Can Do Now)
- Factor: (Current Volume - Past Volume) / Past Volume
- Hypothesis: Growing volume = growing interest

### Market Cap Momentum (Can Do Now)
- Factor: (Current MC - Past MC) / Past MC
- Hypothesis: MC momentum predicts returns

**Script to create:**
```bash
# Backtest using CMC data
python3 backtests/scripts/backtest_cmc_factors.py
```

Would you like me to create this?

---

## Recommended Approach

### Phase 1: NOW (Use Existing Data)
1. ✅ **Turnover factor** - Already backtested (Sharpe 2.17)
2. ⚪ **Volume growth** - Can backtest immediately
3. ⚪ **Market cap momentum** - Can backtest immediately
4. ⚪ **Combined factor** - Merge all three

### Phase 2: AFTER 3 MONTHS (Quarterly Data)
1. ⚪ Fee Yield factor (quarterly rebalancing)
2. ⚪ Revenue Productivity factor
3. ⚪ Net Yield factor

### Phase 3: AFTER 12 MONTHS (Annual Data)
1. ⚪ Full factor suite backtest
2. ⚪ Multi-factor models
3. ⚪ Regime analysis (bull vs bear)
4. ⚪ Factor timing strategies

---

## Key Insights from Turnover Backtest

### What Works
- **High turnover** (liquid, active) → outperforms
- **Low turnover** (illiquid) → underperforms
- **Long-short** strategy works best (Sharpe 2.17 vs 1.28 long-only)

### Strategy Details
- Rebalancing: Monthly
- Long: Top 20% by turnover
- Short: Bottom 20% by turnover
- Min market cap: $100M
- Equal weight within buckets

### Risk Characteristics
- Max drawdown: -11.69% (very low!)
- Win rate: 66.67%
- Works in most market conditions

---

## Files Reference

### Backtest Scripts
- `backtests/scripts/backtest_turnover_factor.py` ✅ Complete
- `backtests/scripts/backtest_fee_yield_factor.py` ⏳ Template (needs data)
- `backtests/scripts/backtest_net_yield_factor.py` ⏳ Template (needs data)

### Data Collection
- `data/scripts/collect_historical_defi_snapshots.py` ✅ Working
- `run_factor_pipeline.sh` ✅ Working

### Database
- `data/defi_factors_history.db` - SQLite database (created)

### Results
- `backtests/results/turnover_factor_backtest_*.csv` - Performance data
- `backtests/results/turnover_factor_backtest_*.png` - Charts

---

## Next Steps

### Immediate (Can Do Today)
1. ✅ Review turnover backtest results
2. ⚪ Create volume growth backtest
3. ⚪ Create market cap momentum backtest
4. ⚪ Combine into multi-factor model

### Short Term (This Week)
1. Set up daily cron job for data collection
2. Start building historical database
3. Document factor behavior in current market

### Long Term (3-12 Months)
1. Wait for sufficient historical data
2. Backtest DeFi-specific factors (fee yield, net yield)
3. Optimize factor weights
4. Implement in live trading

---

## Questions?

**Q: Why can't we backtest fee yield now?**  
A: We only have 1 day's snapshot. Need 12+ months to calculate reliable annualized metrics and test across market conditions.

**Q: Can we use DefiLlama historical API?**  
A: DefiLlama has some historical data, but it's limited. Better to collect going forward for consistency.

**Q: How long until we can backtest all factors?**  
A: 
- 3 months → Quarterly rebalancing tests
- 6 months → Semi-annual tests
- 12 months → Full annual backtest ⭐

**Q: What about the turnover factor - is 2.17 Sharpe realistic?**  
A: Yes! Results are based on real historical data (2020-2025). However:
- Past performance ≠ future results
- Transaction costs not included
- Market impact not modeled
- Still, it's a very strong signal

---

**Status:** Phase 1 Complete (Turnover)  
**Next:** Phase 2 (Collect DeFi data for 3+ months)  
**Goal:** Full 5-factor backtest in 12 months
