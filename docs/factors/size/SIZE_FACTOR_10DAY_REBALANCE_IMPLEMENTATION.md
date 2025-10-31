# Size Factor: 10-Day Rebalancing Implementation

**Date:** 2025-10-29  
**Status:** ✅ Implemented and Configured

---

## Summary

Based on comprehensive backtesting analysis, the **10-day rebalancing period** has been implemented as the optimal frequency for the size factor strategy. This configuration provides:

- **Best Sharpe Ratio:** 0.39 (highest risk-adjusted return)
- **Highest Annual Return:** 15.89%
- **Reduced Transaction Costs:** 88% fewer trades vs daily rebalancing
- **Optimal Balance:** Between portfolio optimization and transaction drag

---

## Changes Made

### 1. Configuration Update (`execution/all_strategies_config.json`)

Added `rebalance_days: 10` parameter to size strategy config:

```json
{
  "params": {
    "size": {
      "top_n": 10,
      "bottom_n": 10,
      "limit": 100,
      "rebalance_days": 10,
      "_comment": "Optimal rebalance frequency: 10 days (Sharpe: 0.39, Annual Return: 15.89%). Run strategy every 10 days for best risk-adjusted returns."
    }
  }
}
```

### 2. Strategy Implementation (`execution/strategies/size.py`)

**Added intelligent caching system:**

- ✅ Checks last calculation date before fetching new market cap data
- ✅ Reuses cached weights if within 10-day window
- ✅ Scales cached weights to current notional value
- ✅ Automatically recalculates when cache expires
- ✅ Saves new calculations to cache with timestamp

**Cache Location:** `execution/.cache/size_strategy_cache.json`

**Cache Contents:**
```json
{
  "last_calculation_date": "2025-10-29T12:00:00",
  "weights": {
    "BTC/USDC:USDC": -5000.0,
    "SHIB/USDC:USDC": 2500.0,
    ...
  },
  "notional": 100000.0,
  "rebalance_days": 10,
  "params": {
    "top_n": 10,
    "bottom_n": 10,
    "limit": 100
  }
}
```

### 3. Main Script Update (`execution/main.py`)

Updated `_build_strategy_params()` to pass `rebalance_days` parameter:

```python
elif strategy_name == "size":
    top_n = int(p.get("top_n", 10)) if isinstance(p, dict) else 10
    bottom_n = int(p.get("bottom_n", 10)) if isinstance(p, dict) else 10
    limit = int(p.get("limit", 100)) if isinstance(p, dict) else 100
    rebalance_days = int(p.get("rebalance_days", 10)) if isinstance(p, dict) else 10
    return (historical_data, list(historical_data.keys()), strategy_notional), {
        "top_n": top_n,
        "bottom_n": bottom_n,
        "limit": limit,
        "rebalance_days": rebalance_days,
    }
```

### 4. Git Configuration

Added cache directory to `.gitignore`:
```
# Strategy cache files
execution/.cache/
```

---

## How It Works

### First Run (No Cache)
```
Day 0: main.py runs
├── Size strategy called
├── No cache found
├── Fetches market cap data from CoinMarketCap
├── Calculates optimal positions
├── Saves to cache with timestamp
└── Returns positions for trading
```

### Subsequent Runs (Within 10 Days)
```
Day 1-9: main.py runs
├── Size strategy called
├── Cache found (X days old)
├── X < 10 days → Use cached weights
├── Scales weights to current notional
├── Filters to current universe
└── Returns cached positions (no API call)
```

### Cache Expiration (After 10 Days)
```
Day 10+: main.py runs
├── Size strategy called
├── Cache found (10+ days old)
├── Cache expired → Recalculate
├── Fetches fresh market cap data
├── Calculates new optimal positions
├── Updates cache with new timestamp
└── Returns new positions for trading
```

---

## Benefits

### 1. **Optimal Performance**
- Achieves highest Sharpe ratio (0.39)
- Best annualized return (15.89%)
- Near-optimal drawdown control (-41.86%)

### 2. **Reduced Transaction Costs**
- Only ~481 rebalances per year vs ~3,960 for daily
- 88% reduction in trading activity
- Lower slippage and exchange fees

### 3. **API Efficiency**
- CoinMarketCap API called only every 10 days
- Reduces rate limit concerns
- Conserves API quota

### 4. **Operational Simplicity**
- main.py can run daily without issues
- Caching handled automatically
- No manual intervention needed

---

## Usage Examples

### Running Daily (Recommended)
```bash
# Set up cron to run daily at 9 AM UTC
0 9 * * * cd /workspace && python3 execution/main.py --dry-run

# Size factor will:
# - Use cached weights on days 0-9
# - Recalculate on day 10
# - Automatically manage cache lifecycle
```

### Manual Cache Management

**Check cache status:**
```bash
cat execution/.cache/size_strategy_cache.json | jq .
```

**View cache age:**
```bash
python3 -c "
import json
from datetime import datetime
with open('execution/.cache/size_strategy_cache.json') as f:
    cache = json.load(f)
last_calc = datetime.fromisoformat(cache['last_calculation_date'])
days_ago = (datetime.now() - last_calc).days
print(f'Cache age: {days_ago} days')
print(f'Rebalance in: {cache[\"rebalance_days\"] - days_ago} days')
"
```

**Force recalculation (clear cache):**
```bash
rm execution/.cache/size_strategy_cache.json
python3 execution/main.py --dry-run
```

---

## Strategy Output Examples

### First Calculation
```
Strategy: size | Allocation: $10,000.00 (10.00%)
🔄 No cache found - calculating SIZE weights (will cache for 10 days)
  Allocated $5,000.00 to SIZE LONGS (bottom 10 market caps) across 8 symbols
  Allocated $5,000.00 to SIZE SHORTS (top 10 market caps) across 7 symbols
💾 Cached SIZE weights (valid for 10 days)
```

### Using Cache (Days 1-9)
```
Strategy: size | Allocation: $10,000.00 (10.00%)
⚡ Using cached SIZE weights (calculated 3 days ago)
   Next recalculation in 7 days
   Using 15 cached positions (scaled to $10,000.00)
```

### Cache Expiration (Day 10+)
```
Strategy: size | Allocation: $10,000.00 (10.00%)
🔄 Cache expired (10 days old) - recalculating SIZE weights
  Allocated $5,000.00 to SIZE LONGS (bottom 10 market caps) across 9 symbols
  Allocated $5,000.00 to SIZE SHORTS (top 10 market caps) across 6 symbols
💾 Cached SIZE weights (valid for 10 days)
```

---

## Configuration Options

### Adjust Rebalance Frequency

Edit `execution/all_strategies_config.json`:

```json
{
  "params": {
    "size": {
      "rebalance_days": 7,  // Change to 7 for weekly rebalancing
      ...
    }
  }
}
```

**Supported Values:**
- `1`: Daily (not recommended, high costs)
- `2-3`: Every 2-3 days (moderate costs)
- `5`: Every 5 days (good balance)
- `7`: Weekly (slightly lower return than 10d)
- `10`: **Optimal** (default, best Sharpe)
- `30`: Monthly (suboptimal, excessive drift)

### Override Via Code

```python
from execution.strategies import strategy_size

# Use custom rebalance period
positions = strategy_size(
    historical_data=data,
    universe_symbols=symbols,
    notional=100000.0,
    rebalance_days=14  # Override config
)
```

---

## Monitoring & Maintenance

### What to Monitor

1. **Cache Health**
   - Check cache file exists and is not corrupted
   - Verify timestamps are updating correctly

2. **Performance Tracking**
   - Compare actual returns to backtest expectations
   - Monitor transaction costs vs backtest assumptions

3. **Market Cap Data Quality**
   - Ensure CoinMarketCap API is returning valid data
   - Check for missing symbols or API errors

### Troubleshooting

**Problem: Cache not being used**
- Check `execution/.cache/` directory exists and is writable
- Verify JSON file is valid (not corrupted)
- Check system datetime is correct

**Problem: Excessive recalculations**
- Verify `rebalance_days` parameter is set correctly
- Check cache file isn't being deleted between runs
- Ensure cache directory is in `.gitignore` (not reset by git operations)

**Problem: Stale positions**
- Positions are intentionally held for `rebalance_days`
- This is optimal per backtest analysis
- If markets change dramatically, consider force-recalculation

---

## Backtest Validation

The 10-day rebalancing frequency was selected based on comprehensive backtesting:

**Test Period:** 2020-01-31 to 2025-10-24 (5.73 years)  
**Test Periods:** [1, 2, 3, 5, 7, 10, 30] days  
**Winner:** 10 days

See `backtests/results/SIZE_REBALANCE_PERIOD_ANALYSIS.md` for full analysis.

---

## Next Steps

1. **Monitor Live Performance**
   - Track actual returns vs backtest
   - Measure transaction costs
   - Compare to other rebalance frequencies

2. **Periodic Re-evaluation**
   - Re-run backtests annually
   - Adjust if market conditions change fundamentally
   - Consider regime-based rebalancing

3. **Integration with Other Factors**
   - Size factor is now configured optimally
   - Can be combined with other strategies in portfolio
   - Current weight: 10.3% of total portfolio

---

## Files Modified

1. ✅ `execution/all_strategies_config.json` - Added rebalance_days parameter
2. ✅ `execution/strategies/size.py` - Implemented caching logic
3. ✅ `execution/main.py` - Pass rebalance_days to strategy
4. ✅ `.gitignore` - Exclude cache directory from git

## Files Created

1. ✅ `SIZE_FACTOR_10DAY_REBALANCE_IMPLEMENTATION.md` - This document
2. 📁 `execution/.cache/` - Cache directory (created at runtime)
3. 📄 `execution/.cache/size_strategy_cache.json` - Cache file (created at runtime)

---

*Implementation completed: 2025-10-29*  
*Based on backtest analysis showing 10-day rebalancing achieves 15.89% annual return with 0.39 Sharpe ratio*
