# Visual Guide: 7-Day Rebalancing in Daily-Running System

## The Question

**"How do you implement 7-day rebalancing if the system runs every day?"**

The answer: **Persist the rebalance schedule and weights in a state file.**

---

## Timeline Visualization

```
┌─────────────────────────────────────────────────────────────────────┐
│                    7-DAY REBALANCING CYCLE                          │
└─────────────────────────────────────────────────────────────────────┘

Day 1: REBALANCE DAY ✅
├─ Run: python3 main_skew_factor.py
├─ Action: Calculate NEW signals
├─ Signals: Long BTC, ETH | Short SOL, AVAX
├─ Execute: Place orders to rebalance
└─ Save: State file with weights + next rebalance date = Day 8

Day 2: Hold 📊
├─ Run: python3 main_skew_factor.py
├─ Check: Is today a rebalance day? NO (Day 8 scheduled)
├─ Action: Do nothing, positions drift naturally
└─ Exit: Script finishes quickly

Day 3: Hold 📊
├─ Run: python3 main_skew_factor.py
├─ Check: Is today a rebalance day? NO
├─ Action: Do nothing
└─ Exit: Script finishes quickly

Day 4: Hold 📊
├─ Same as Day 2-3

Day 5: Hold 📊
├─ Same as Day 2-3

Day 6: Hold 📊
├─ Same as Day 2-3

Day 7: Hold 📊
├─ Same as Day 2-3

Day 8: REBALANCE DAY ✅
├─ Run: python3 main_skew_factor.py
├─ Check: Is today a rebalance day? YES
├─ Action: Calculate NEW signals
├─ Signals: Long BTC, SOL | Short ETH, DOGE (changed!)
├─ Execute: Place orders to rebalance
└─ Save: State file with new weights + next rebalance date = Day 15

Day 9-14: Hold 📊
├─ Repeat cycle...

Day 15: REBALANCE DAY ✅
├─ Repeat cycle...
```

---

## What Gets Stored in State File

### Location
```
/workspace/execution/.state/skew_factor_rebalance_state.json
```

### Contents
```json
{
  "strategy_name": "skew_factor",
  "rebalance_days": 7,
  "last_rebalance_date": "2025-10-27",     ← When we last rebalanced
  "next_rebalance_date": "2025-11-03",     ← When to rebalance next
  "current_weights": {                      ← Portfolio from last rebalance
    "BTC-USD": 1000.0,                      ← Long $1000
    "ETH-USD": 800.0,                       ← Long $800
    "SOL-USD": -500.0,                      ← Short $500
    "AVAX-USD": -300.0                      ← Short $300
  },
  "rebalance_history": [...]                ← Last 52 rebalances
}
```

---

## Daily Execution Flow

### Pseudocode

```python
def main():
    # 1. Load state file
    scheduler = RebalanceScheduler('skew_factor', rebalance_days=7)
    
    # 2. Check if today is rebalance day
    if scheduler.should_rebalance():
        # --- REBALANCE DAY ---
        
        # Calculate fresh signals
        signals = calculate_skew_signals(data)
        
        # Convert to target weights
        target_weights = {
            'BTC-USD': 1000.0,
            'ETH-USD': 800.0,
            'SOL-USD': -500.0
        }
        
        # Execute trades
        execute_rebalance(target_weights)
        
        # Save state for next 7 days
        scheduler.record_rebalance(target_weights)
        # → Saves next_rebalance_date = today + 7 days
        
    else:
        # --- NON-REBALANCE DAY ---
        
        # Just check status
        print("Holding positions")
        print(f"Next rebalance in {scheduler.days_until_rebalance()} days")
        
        # Optional: Monitor drift
        current_weights = scheduler.get_current_weights()
        check_drift(current_weights)
        
        # EXIT - No trading!
```

---

## Position Drift Example

### Day 1: Rebalance
```
Target Weights:
  BTC-USD:  $1,000  (price = $50,000)  → Buy 0.02 BTC
  ETH-USD:  $800    (price = $4,000)   → Buy 0.2 ETH
  SOL-USD: -$500    (price = $100)     → Short 5 SOL

Save these weights to state file ✓
```

### Day 4: Mid-Cycle (No Rebalance)
```
Prices changed:
  BTC: $50,000 → $52,000 (+4%)
  ETH: $4,000 → $3,900 (-2.5%)
  SOL: $100 → $105 (+5%)

Position values NOW:
  BTC-USD:  0.02 BTC × $52,000  = $1,040  (was $1,000)
  ETH-USD:  0.2 ETH × $3,900    = $780    (was $800)
  SOL-USD: -5 SOL × $105        = -$525   (was -$500)

Do we rebalance? NO!
We HOLD the same number of contracts:
  - Still hold 0.02 BTC (even though worth more)
  - Still hold 0.2 ETH (even though worth less)
  - Still short 5 SOL (even though costs more)

This is NATURAL DRIFT - it's OK!
```

### Day 8: Next Rebalance
```
NOW we recalculate signals:
  - New skewness values
  - New rankings
  - Maybe different coins selected

Calculate NEW target weights:
  BTC-USD:  $1,200  ← Different from last time
  SOL-USD:  $600    ← Now LONG instead of SHORT
  DOGE-USD: -$400   ← New position

Execute trades to hit new targets
Save new weights to state file ✓
```

---

## Why This Works

### Transaction Cost Savings

**Daily rebalancing:**
```
Day 1: Trade (rebalance)
Day 2: Trade (rebalance) ← unnecessary cost
Day 3: Trade (rebalance) ← unnecessary cost
Day 4: Trade (rebalance) ← unnecessary cost
Day 5: Trade (rebalance) ← unnecessary cost
Day 6: Trade (rebalance) ← unnecessary cost
Day 7: Trade (rebalance) ← unnecessary cost
Day 8: Trade (rebalance)

Total: 8 trades in 8 days
Cost: 5.68% daily turnover × 8 days = ~45% turnover
Fees: ~0.45% of portfolio
```

**7-day rebalancing:**
```
Day 1: Trade (rebalance)
Day 2: Hold (no cost) ← save money
Day 3: Hold (no cost) ← save money
Day 4: Hold (no cost) ← save money
Day 5: Hold (no cost) ← save money
Day 6: Hold (no cost) ← save money
Day 7: Hold (no cost) ← save money
Day 8: Trade (rebalance)

Total: 2 trades in 8 days
Cost: 2.61% daily turnover × 2 days = ~5.2% turnover
Fees: ~0.052% of portfolio

SAVINGS: 86% fewer trades!
```

### Signal Persistence

Skewness patterns are persistent:
- **Daily changes:** Mostly noise
- **Weekly changes:** True signal shifts

By rebalancing weekly:
- Capture real changes in skewness
- Ignore daily noise
- Let profitable trends run

---

## Implementation Checklist

### Setup (One-Time)

- [x] Create `execution/rebalance_scheduler.py`
- [ ] Create `execution/strategies/skew_factor.py`
- [ ] Create `execution/main_skew_factor.py`
- [ ] Test with `--dry-run`
- [ ] Verify state file creation

### Daily Operations

- [ ] Add to cron: Run script daily at 4 PM
- [ ] Monitor logs: Check rebalance triggers
- [ ] Verify state file: Updated after each rebalance
- [ ] Track P&L: Between rebalance periods

### Monitoring

- [ ] Alert if missed rebalance (>8 days since last)
- [ ] Alert if drift >30% (unusual)
- [ ] Log execution time (should be <5 sec on hold days)
- [ ] Track rebalance count (should be ~52/year for weekly)

---

## Common Questions

### Q: What if I miss a day?

**A:** No problem! The scheduler checks the date.

```
Scenario:
- Last rebalance: Oct 20
- Next rebalance: Oct 27
- System down Oct 27
- System runs Oct 28

Result:
- Oct 28 is AFTER Oct 27
- should_rebalance() returns True
- Rebalances on Oct 28 instead
- Next rebalance: Nov 4 (7 days from Oct 28)
```

### Q: What if I want to force a rebalance early?

**A:** Use `force_rebalance_now()`:

```python
from execution.rebalance_scheduler import RebalanceScheduler

scheduler = RebalanceScheduler('skew_factor', rebalance_days=7)
scheduler.force_rebalance_now()
```

This sets next rebalance to today, so next run will rebalance.

### Q: Do I need to track positions between rebalances?

**A:** No! Positions are stored on the exchange.

The state file only stores:
- Target weights from last rebalance
- Rebalance schedule

Current positions are fetched fresh from exchange each day.

### Q: What if positions drift significantly?

**A:** That's OK and expected!

From backtest:
- Letting positions drift = 260% return
- Daily rebalancing = 84% return

**Drift is GOOD** (as long as you rebalance every 7 days).

### Q: Can I change rebalance frequency later?

**A:** Yes, but carefully:

```python
# Change from 7 to 14 days
scheduler = RebalanceScheduler('skew_factor', rebalance_days=14)
scheduler.force_rebalance_now()  # Reset schedule
```

Or delete state file to start fresh:
```bash
rm execution/.state/skew_factor_rebalance_state.json
```

---

## Cron Setup Examples

### Run Daily at 4 PM EST

```bash
# Edit crontab
crontab -e

# Add line:
0 16 * * * cd /workspace && python3 execution/main_skew_factor.py --rebalance-days 7 >> logs/skew_factor.log 2>&1
```

### Run Daily at Market Close (Multiple Timezones)

```bash
# US Market Close (4 PM ET)
0 21 * * * cd /workspace && TZ="America/New_York" python3 execution/main_skew_factor.py >> logs/skew.log 2>&1

# Crypto runs 24/7, so pick a consistent time
0 0 * * * cd /workspace && python3 execution/main_skew_factor.py >> logs/skew.log 2>&1
```

### With Error Notifications

```bash
# If fails, send email
0 16 * * * cd /workspace && python3 execution/main_skew_factor.py || echo "Skew factor failed" | mail -s "Alert" you@email.com
```

---

## Summary Diagram

```
┌──────────────────────────────────────────────────────────┐
│              7-DAY REBALANCING SYSTEM                    │
└──────────────────────────────────────────────────────────┘

┌─────────────────┐
│   Daily Cron    │  Runs every day at 4 PM
│   4:00 PM       │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  RebalanceScheduler     │  Checks: Is today a rebalance day?
│  .should_rebalance()    │
└─────────┬───────────────┘
          │
      ┌───┴───┐
      │       │
  YES │       │ NO
      │       │
      ▼       ▼
┌─────────┐  ┌────────────────┐
│Rebalance│  │  Hold Positions│
│Calculate│  │  Do Nothing    │
│Execute  │  │  Exit Early    │
│Save     │  └────────────────┘
└─────────┘
      │
      ▼
┌──────────────────────────┐
│ State File Updated       │
│ next_rebalance_date =    │
│   today + 7 days         │
└──────────────────────────┘
```

---

## Testing Commands

```bash
# 1. Test the scheduler module
python3 execution/rebalance_scheduler.py

# 2. Check state file
cat execution/.state/skew_factor_rebalance_state.json | python3 -m json.tool

# 3. Dry run execution
python3 execution/main_skew_factor.py --dry-run --rebalance-days 7

# 4. Force rebalance (if needed)
python3 -c "from execution.rebalance_scheduler import RebalanceScheduler; \
            s = RebalanceScheduler('skew_factor', 7); \
            s.force_rebalance_now()"
```

---

## Files Created

1. ✅ `execution/rebalance_scheduler.py` - Scheduler class
2. ✅ `execution/.state/` - State directory (auto-created)
3. ✅ `execution/REBALANCE_IMPLEMENTATION_GUIDE.md` - Full guide
4. ✅ `REBALANCE_7DAY_VISUAL_GUIDE.md` - This visual guide
5. ✅ `SKEW_REBALANCE_OPTIMIZATION.md` - Backtest results

---

**Ready to implement? Start with:**

1. Test the scheduler: `python3 execution/rebalance_scheduler.py`
2. Read the full guide: `execution/REBALANCE_IMPLEMENTATION_GUIDE.md`
3. Create your strategy module
4. Test with `--dry-run`
5. Add to cron
