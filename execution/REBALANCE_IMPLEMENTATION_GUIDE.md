# How to Implement 7-Day Rebalancing in a Daily-Running System

## The Challenge

You have a trading system that runs **every day**, but your backtest shows that **7-day rebalancing is optimal**. How do you implement this?

**Key Question:** How do you persist portfolio weights between rebalance days?

---

## The Solution

Use a **Rebalance Scheduler** that:
1. Stores the last rebalance date
2. Stores target portfolio weights from that rebalance
3. Checks if today is a rebalance day (every 7 days)
4. On rebalance days: Calculate new signals and update weights
5. On non-rebalance days: Use stored weights (positions drift naturally)

---

## Implementation Overview

### File Structure
```
execution/
├── rebalance_scheduler.py      # NEW: Handles rebalance scheduling
├── .state/                      # NEW: Stores rebalance state
│   └── skew_factor_rebalance_state.json
├── main.py                      # Modified to use scheduler
└── strategies/
    └── skew_factor.py           # NEW: Skew factor strategy
```

---

## Step-by-Step Implementation

### Step 1: Create Rebalance Scheduler (✓ DONE)

The `RebalanceScheduler` class handles all persistence logic:

```python
from execution.rebalance_scheduler import RebalanceScheduler

# Initialize scheduler
scheduler = RebalanceScheduler(
    strategy_name='skew_factor',
    rebalance_days=7,  # Rebalance every 7 days
    force_rebalance=True  # Force rebalance on first run
)
```

**What it stores:**
- `last_rebalance_date`: Date of last rebalance
- `next_rebalance_date`: Date of next scheduled rebalance  
- `current_weights`: Portfolio weights from last rebalance
- `rebalance_history`: Last 52 rebalances for audit

**Storage location:** `execution/.state/skew_factor_rebalance_state.json`

---

### Step 2: Modify Daily Execution Flow

Here's the logic for your daily cron job:

```python
# main.py or main_skew_factor.py

from execution.rebalance_scheduler import RebalanceScheduler

def main():
    # Initialize scheduler
    scheduler = RebalanceScheduler(
        strategy_name='skew_factor',
        rebalance_days=7
    )
    
    # Check if today is a rebalance day
    if scheduler.should_rebalance():
        print("TODAY IS A REBALANCE DAY")
        
        # Step 1: Calculate new signals
        target_weights = calculate_skew_factor_signals()
        
        # Step 2: Record the rebalance
        scheduler.record_rebalance(target_weights)
        
        # Step 3: Execute trades
        execute_rebalance(target_weights)
    
    else:
        print("NOT A REBALANCE DAY - Holding positions")
        
        # Use weights from last rebalance
        target_weights = scheduler.get_current_weights()
        
        # Optional: Check if positions need minor adjustments
        # (e.g., if prices drifted significantly)
        check_position_drift(target_weights)
```

---

### Step 3: Key Decision - What Happens on Non-Rebalance Days?

You have 3 options:

#### Option A: Do Nothing (Recommended) ✅

**On non-rebalance days:**
- Don't calculate new signals
- Don't execute any trades
- Just let positions drift naturally

**Pros:**
- Simplest implementation
- Lowest transaction costs
- Matches backtest exactly

**Implementation:**
```python
if not scheduler.should_rebalance():
    print("Holding positions - no action needed")
    return  # Exit early
```

---

#### Option B: Monitor Only

**On non-rebalance days:**
- Check current positions vs target
- Monitor P&L and drift
- Alert if drift exceeds threshold
- But DON'T trade

**Pros:**
- Visibility into position drift
- Can catch issues early
- Still no trading costs

**Implementation:**
```python
if not scheduler.should_rebalance():
    target_weights = scheduler.get_current_weights()
    current_positions = get_current_positions()
    
    # Calculate drift
    drift = calculate_drift(target_weights, current_positions)
    print(f"Position drift: {drift:.2%}")
    
    # Alert if drift > 20%
    if abs(drift) > 0.20:
        print("⚠️  Warning: Significant drift detected")
    
    return  # Don't trade
```

---

#### Option C: Rebalance Drift (Not Recommended) ❌

**On non-rebalance days:**
- Maintain exact target weights
- Trade to correct price drift

**Cons:**
- Defeats purpose of 7-day rebalancing
- Adds transaction costs
- Worse than daily rebalancing

**Don't do this unless you have a specific reason!**

---

## Example: Complete Integration

### Create Skew Factor Strategy Module

```python
# execution/strategies/skew_factor.py

def strategy_skew_factor(historical_data, notional, lookback=30, num_quintiles=5):
    """
    Skew factor strategy: Long negative skew, short positive skew.
    
    Args:
        historical_data: Dict of symbol -> DataFrame with OHLCV
        notional: Total notional to allocate
        lookback: Skewness calculation window (days)
        num_quintiles: Number of quintiles for ranking
        
    Returns:
        Dict[str, float]: Symbol -> notional amount (negative = short)
    """
    import numpy as np
    from scipy.stats import skew as scipy_skew
    
    positions = {}
    skewness_data = []
    
    # Calculate skewness for each symbol
    for symbol, df in historical_data.items():
        if len(df) < lookback + 1:
            continue
        
        # Calculate returns
        returns = np.log(df['close'] / df['close'].shift(1)).dropna()
        
        # Calculate rolling skewness
        if len(returns) >= lookback:
            recent_returns = returns.tail(lookback)
            skew_val = scipy_skew(recent_returns)
            
            if not np.isnan(skew_val):
                skewness_data.append({
                    'symbol': symbol,
                    'skewness': skew_val
                })
    
    if not skewness_data:
        print("  No valid skewness data")
        return {}
    
    # Sort by skewness
    skewness_data = sorted(skewness_data, key=lambda x: x['skewness'])
    
    # Select quintiles
    n = len(skewness_data)
    quintile_size = max(1, n // num_quintiles)
    
    # Long: Bottom quintile (most negative skewness)
    long_symbols = [x['symbol'] for x in skewness_data[:quintile_size]]
    
    # Short: Top quintile (most positive skewness)
    short_symbols = [x['symbol'] for x in skewness_data[-quintile_size:]]
    
    # Equal weight within each side
    long_weight = (notional / 2) / len(long_symbols) if long_symbols else 0
    short_weight = (notional / 2) / len(short_symbols) if short_symbols else 0
    
    # Build positions
    for symbol in long_symbols:
        positions[symbol] = long_weight
    
    for symbol in short_symbols:
        positions[symbol] = -short_weight  # Negative for short
    
    print(f"  Long: {len(long_symbols)} positions, ${long_weight*len(long_symbols):,.0f}")
    print(f"  Short: {len(short_symbols)} positions, ${short_weight*len(short_symbols):,.0f}")
    
    return positions
```

### Create Main Execution Script

```python
# execution/main_skew_factor.py

import argparse
from datetime import datetime
from execution.rebalance_scheduler import RebalanceScheduler
from execution.strategies.skew_factor import strategy_skew_factor
from execution.main import (
    get_200d_daily_data,
    request_markets_by_volume,
    get_account_notional_value,
    get_current_positions,
    calculate_trade_amounts,
    send_orders_if_difference_exceeds_threshold
)

def main():
    parser = argparse.ArgumentParser(description='Skew Factor Strategy Execution')
    parser.add_argument('--rebalance-days', type=int, default=7,
                       help='Rebalance frequency in days')
    parser.add_argument('--lookback', type=int, default=30,
                       help='Skewness lookback window')
    parser.add_argument('--leverage', type=float, default=1.0,
                       help='Leverage multiplier')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run mode')
    args = parser.parse_args()
    
    print("="*80)
    print(f"SKEW FACTOR STRATEGY - {args.rebalance_days}D REBALANCING")
    print("="*80)
    
    # Initialize rebalance scheduler
    scheduler = RebalanceScheduler(
        strategy_name='skew_factor',
        rebalance_days=args.rebalance_days,
        force_rebalance=True  # Force rebalance if first run
    )
    
    # Print status
    scheduler.print_status()
    
    # Check if today is a rebalance day
    if scheduler.should_rebalance():
        print("\n→ REBALANCING TODAY")
        
        # Step 1: Get market data
        print("\n[1/5] Fetching market data...")
        symbols = request_markets_by_volume(min_volume=100000)
        historical_data = get_200d_daily_data(symbols)
        
        # Step 2: Get account value
        print("\n[2/5] Getting account value...")
        base_notional = get_account_notional_value()
        notional = base_notional * args.leverage
        
        # Step 3: Calculate skew factor signals
        print("\n[3/5] Calculating skew factor signals...")
        target_positions = strategy_skew_factor(
            historical_data=historical_data,
            notional=notional,
            lookback=args.lookback
        )
        
        # Step 4: Record rebalance
        print("\n[4/5] Recording rebalance...")
        scheduler.record_rebalance(target_positions)
        
        # Step 5: Execute trades
        print("\n[5/5] Executing trades...")
        current_positions = get_current_positions()
        trades = calculate_trade_amounts(
            target_positions,
            current_positions,
            notional,
            threshold=0.05  # 5% threshold
        )
        
        send_orders_if_difference_exceeds_threshold(
            trades,
            dry_run=args.dry_run,
            aggressive=False
        )
        
        print("\n✓ Rebalance complete")
        print(f"  Next rebalance: {scheduler.get_rebalance_info()['next_rebalance']}")
    
    else:
        print("\n→ NOT A REBALANCE DAY - Holding positions")
        print(f"  Days until next rebalance: {scheduler.get_days_until_rebalance()}")
        print(f"  Current positions: {len(scheduler.get_current_weights())}")
        
        # Optional: Monitor drift
        current_weights = scheduler.get_current_weights()
        if current_weights:
            print("\n  Current portfolio:")
            for symbol, notional in sorted(current_weights.items(), 
                                          key=lambda x: abs(x[1]), 
                                          reverse=True)[:10]:
                side = "LONG" if notional > 0 else "SHORT"
                print(f"    {symbol:20s}: {side:5s} ${abs(notional):>10,.0f}")
    
    print("\n" + "="*80)
    print("EXECUTION COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
```

---

## Daily Cron Job Setup

### Add to Crontab

```bash
# Run every day at 4:00 PM (after market close)
0 16 * * * cd /workspace && python3 execution/main_skew_factor.py --rebalance-days 7 --dry-run >> logs/skew_factor.log 2>&1
```

**What happens:**
- **Day 1-6:** Script checks scheduler, sees it's not a rebalance day, exits
- **Day 7:** Script checks scheduler, sees it IS a rebalance day, executes trades
- **Day 8-13:** Repeat (no trading)
- **Day 14:** Rebalance again

---

## State File Example

After first rebalance, `execution/.state/skew_factor_rebalance_state.json`:

```json
{
  "strategy_name": "skew_factor",
  "rebalance_days": 7,
  "last_rebalance_date": "2025-10-27",
  "next_rebalance_date": "2025-11-03",
  "current_weights": {
    "BTC-USD": 1000.0,
    "ETH-USD": 800.0,
    "SOL-USD": -500.0,
    "AVAX-USD": -300.0
  },
  "rebalance_history": [
    {
      "date": "2025-10-27",
      "num_positions": 4,
      "positions": ["BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD"]
    }
  ]
}
```

---

## Position Drift Explanation

### What is "Drift"?

When you rebalance on Day 1:
- BTC: $1,000 (at $50k = 0.02 BTC)
- ETH: $800 (at $4k = 0.2 ETH)

On Day 7 (before next rebalance):
- BTC rises 10% → Now worth $1,100 (still 0.02 BTC)
- ETH falls 5% → Now worth $760 (still 0.2 ETH)

**This is natural drift** - you don't trade to fix it!

### Why Not Fix Drift?

Because the backtest shows:
- **Daily rebalancing (fixing drift):** 83% return, 0.36 Sharpe
- **7-day rebalancing (letting drift):** 260% return, 0.80 Sharpe

Letting positions drift is **BETTER** than constantly rebalancing!

---

## Testing the Scheduler

```bash
# Test the scheduler module
cd /workspace
python3 execution/rebalance_scheduler.py
```

This will:
1. Create a test scheduler
2. Simulate first rebalance
3. Simulate next day (no rebalance)
4. Simulate 7 days later (rebalance)
5. Show state persistence

---

## Integration with Existing System

### Option 1: Add to main.py (Multi-Strategy)

```python
# In main.py, add rebalance scheduler check at start

# Check if strategies need rebalancing
strategy_schedulers = {}
if 'skew_factor' in blend_weights:
    scheduler = RebalanceScheduler('skew_factor', rebalance_days=7)
    if not scheduler.should_rebalance():
        # Remove skew_factor from today's blend
        blend_weights = {k: v for k, v in blend_weights.items() if k != 'skew_factor'}
        # Use cached weights instead
        cached_weights = scheduler.get_current_weights()
        # Add to target_positions
```

### Option 2: Separate Script (Recommended)

Create `main_skew_factor.py` as shown above and run it separately:

```bash
# Daily cron for other strategies (daily rebalancing)
0 16 * * * cd /workspace && python3 execution/main.py

# Separate cron for skew factor (7-day rebalancing)
0 16 * * * cd /workspace && python3 execution/main_skew_factor.py --rebalance-days 7
```

---

## Monitoring and Alerts

### Check Scheduler Status

```bash
# View state file directly
cat execution/.state/skew_factor_rebalance_state.json

# Or in Python
from execution.rebalance_scheduler import RebalanceScheduler
scheduler = RebalanceScheduler('skew_factor', rebalance_days=7)
scheduler.print_status()
```

### Add Alerts

```python
# In your monitoring script
if scheduler.get_days_until_rebalance() == 1:
    send_email("Skew factor rebalancing tomorrow")

if scheduler.get_days_since_rebalance() > 8:
    send_alert("Skew factor missed rebalance!")
```

---

## Manual Intervention

### Force Rebalance Now

```python
from execution.rebalance_scheduler import RebalanceScheduler

scheduler = RebalanceScheduler('skew_factor', rebalance_days=7)
scheduler.force_rebalance_now()

# Next run will rebalance regardless of schedule
```

### Reset Scheduler

```bash
# Delete state file to start fresh
rm execution/.state/skew_factor_rebalance_state.json
```

---

## Summary

### Key Points

1. ✅ **Use RebalanceScheduler** to manage rebalancing schedule
2. ✅ **Store weights in state file** (persists between runs)
3. ✅ **Check should_rebalance()** on every daily run
4. ✅ **On rebalance days:** Calculate signals + execute trades
5. ✅ **On other days:** Do nothing (let positions drift)
6. ✅ **State file location:** `execution/.state/`

### What Gets Persisted

- Last rebalance date
- Next rebalance date  
- Current portfolio weights
- Rebalance history

### What Doesn't Get Persisted

- Current positions (fetched from exchange each day)
- Current prices (fetched fresh each day)
- P&L (calculated from positions)

---

## Next Steps

1. ✅ Created `execution/rebalance_scheduler.py`
2. → Create `execution/strategies/skew_factor.py`
3. → Create `execution/main_skew_factor.py`
4. → Test with `--dry-run`
5. → Add to cron for daily execution
6. → Monitor first rebalance cycle

---

**Questions?** Check the module docstrings or test the scheduler:

```bash
python3 execution/rebalance_scheduler.py
```
