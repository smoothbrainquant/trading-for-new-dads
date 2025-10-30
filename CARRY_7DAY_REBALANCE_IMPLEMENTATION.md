# Carry Strategy 7-Day Rebalancing Implementation

## Summary

Modified the carry strategy to rebalance every **7 days** based on backtest results showing this is the optimal rebalancing frequency.

## Changes Made

### 1. Configuration Updated

**File:** `execution/all_strategies_config.json`

Added `rebalance_days: 7` parameter to carry strategy config:

```json
"carry": {
  "exchange_id": "hyperliquid",
  "top_n": 10,
  "bottom_n": 10,
  "rebalance_days": 7  // NEW: Optimal rebalance frequency from backtest
}
```

### 2. Carry Strategy Implementation

**File:** `execution/strategies/carry.py`

**Key Changes:**
- Added `rebalance_days` parameter to function signature (default: 7)
- Implemented state tracking to remember last rebalance date
- Returns cached positions if < 7 days since last rebalance
- Automatically scales cached positions to current notional value
- Saves state after each rebalance for next execution

**State File Location:** `execution/.carry_strategy_state.json`

**State Structure:**
```json
{
  "last_rebalance_date": "2025-10-29",
  "positions": {
    "BTC/USDC:USDC": 1500.0,
    "ETH/USDC:USDC": -800.0
  },
  "notional": 50000.0,
  "rebalance_days": 7,
  "top_n": 10,
  "bottom_n": 10
}
```

### 3. Main Execution Script

**File:** `execution/main.py`

Updated parameter building to pass `rebalance_days` from config to strategy:

```python
elif strategy_name == "carry":
    rebalance_days = int(p.get("rebalance_days", 7)) if isinstance(p, dict) else 7
    return (historical_data, list(historical_data.keys()), strategy_notional), {
        "exchange_id": exchange_id,
        "top_n": top_n,
        "bottom_n": bottom_n,
        "rebalance_days": rebalance_days,  // NEW
    }
```

### 4. Git Configuration

**File:** `.gitignore`

Added state file to prevent committing runtime data:
```
execution/.carry_strategy_state.json
```

---

## How It Works

### First Execution
```
🔄 Carry strategy: First run, calculating positions (will rebalance every 7d)
  [Fetches funding rates from Coinalyze]
  [Calculates long/short positions]
  ✓ Saved carry strategy state (next rebalance: 2025-11-05)
```

### Subsequent Executions (< 7 days)
```
📅 Carry strategy: Using cached positions (last rebalance: 2025-10-29, 3d ago)
   Next rebalance in 4 days
   Scaled positions from $50,000.00 to $52,500.00 (factor: 1.0500)
```

### After 7 Days
```
🔄 Carry strategy: Rebalancing (last: 2025-10-29, 7d ago, threshold: 7d)
  [Fetches fresh funding rates]
  [Calculates new positions]
  ✓ Saved carry strategy state (next rebalance: 2025-11-12)
```

---

## Benefits

Based on backtest results (`CARRY_REBALANCE_PERIOD_ANALYSIS.md`):

### ✅ Performance
- **27.91% annualized return** (nearly identical to daily rebalancing)
- **0.76 Sharpe ratio** (excellent risk-adjusted returns)
- **-42.56% max drawdown** (manageable)

### ✅ Efficiency
- **6.8x fewer trades** vs daily rebalancing (2,170 vs 14,750)
- **85% reduction in trading activity**
- **1.08% return per rebalance** (6x better than daily)

### ✅ Cost Savings
- **~$2,587 saved in transaction costs** (at 5 bps per trade)
- Break-even vs daily at ~2.3 bps trading fees
- Lower slippage and market impact

### ✅ Operational
- Reduced API calls to Coinalyze (once per week vs daily)
- Lower system load and monitoring overhead
- Easier to troubleshoot and verify positions

---

## Testing

To test the rebalancing logic:

### Day 1 - First Run
```bash
cd /workspace/execution
python3 main.py --dry-run
# Should show: "First run, calculating positions"
# State file created: .carry_strategy_state.json
```

### Day 2-6 - Cached Positions
```bash
python3 main.py --dry-run
# Should show: "Using cached positions (X days ago)"
# Returns same positions, scaled to current notional
```

### Day 7+ - Rebalance
```bash
python3 main.py --dry-run
# Should show: "Rebalancing (last: YYYY-MM-DD, 7d ago)"
# Fetches new funding rates and recalculates
```

### Manual Reset (for testing)
```bash
# Delete state file to force fresh calculation
rm execution/.carry_strategy_state.json
python3 main.py --dry-run
```

---

## Configuration Options

You can adjust the rebalance frequency in `execution/all_strategies_config.json`:

```json
"carry": {
  "rebalance_days": 7    // Change to 1, 3, 5, 10, 30, etc.
}
```

**Recommended values based on backtest:**
- `7` (weekly) - **OPTIMAL** ✅
- `1` (daily) - Only if transaction costs < 2.3 bps
- `3` (tri-weekly) - Acceptable but lower returns (15.98%)
- `10+` - **NOT RECOMMENDED** (negative returns)

---

## Monitoring

### Check Current State
```bash
cat execution/.carry_strategy_state.json | python3 -m json.tool
```

### View Last Rebalance
```bash
grep "last_rebalance_date" execution/.carry_strategy_state.json
```

### Force Rebalance (emergency)
```bash
# Delete state file to force recalculation
rm execution/.carry_strategy_state.json
```

---

## Important Notes

### Position Scaling
- Cached positions are automatically scaled to current account size
- If account grows from $50k to $60k, positions scale proportionally
- Maintains constant leverage and allocation percentages

### State File Location
- Stored in `execution/.carry_strategy_state.json`
- Not committed to git (in .gitignore)
- Recreated automatically if deleted

### Error Handling
- If state file is corrupted: Forces fresh calculation
- If state file is missing: Treats as first run
- If Coinalyze API fails during rebalance: Returns empty positions (safe)

### Multi-Exchange Support
- State is saved per-strategy, not per-exchange
- If running multiple exchanges, each maintains separate state
- Consider adding exchange_id to state file path if needed

---

## Backtest Reference

Full analysis available in:
- **Complete Report:** `/workspace/CARRY_REBALANCE_PERIOD_ANALYSIS.md`
- **Quick Start:** `/workspace/CARRY_REBALANCE_QUICKSTART.md`
- **Results Table:** `/workspace/CARRY_REBALANCE_RESULTS_TABLE.txt`
- **Raw Data:** `/workspace/backtests/results/backtest_carry_rebalance_periods_summary.csv`

**Key Finding:** 7-day rebalancing provides optimal balance of returns (27.91%), efficiency (2,170 trades), and costs (~$445 in fees vs $3,032 for daily).

---

## Version History

- **2025-10-29:** Initial implementation
  - Added 7-day rebalancing based on backtest results
  - Implemented state tracking and caching
  - Updated config and main.py

---

*Implementation based on comprehensive backtest of [1, 2, 3, 5, 7, 10, 30] day rebalance periods over 5.7 years (2020-2025)*
