# How Mixed Rebalance Periods Work - Complete Mechanics

**Understanding how different strategies can rebalance at different frequencies**

---

## 🔍 The Core Question

**Problem:** You want to run multiple strategies together:
- Volatility Factor: Rebalance **daily** (1 day)
- DW Factor: Rebalance **weekly** (7 days)
- Kurtosis Factor: Rebalance **biweekly** (14 days)

**Question:** How does the system handle this when they're all running simultaneously?

---

## 📊 Two Different Contexts

### Context 1: Backtesting (Current Implementation)

**In backtesting, each strategy runs independently and they're combined at the analysis stage.**

### Context 2: Production Trading (What you'll build)

**In production, you need one unified position manager that handles all strategies.**

Let me explain both:

---

## 🧪 CONTEXT 1: Backtesting (How it works now)

### Current Architecture

```
run_all_backtests.py
    ├─ backtest_volatility_factor()  → rebalance_days=1  (daily)
    ├─ backtest_dw_factor()          → rebalance_days=7  (weekly)
    └─ backtest_kurtosis_factor()    → rebalance_days=14 (biweekly)

Each strategy:
  1. Runs independently
  2. Maintains its own portfolio
  3. Tracks its own positions
  4. Generates its own equity curve

Finally:
  - Results are compared side-by-side
  - Can be combined via Sharpe weighting
```

### How Rebalancing Works in Each Backtest

**Example: DW Factor with 7-day rebalancing**

```python
# In backtest_durbin_watson_factor.py

# Get all trading dates
trading_dates = ['2024-01-01', '2024-01-02', ..., '2024-12-31']

# Create rebalance schedule (every 7 days)
rebalance_dates = trading_dates[::7]  
# Result: ['2024-01-01', '2024-01-08', '2024-01-15', ...]

# Loop through ALL trading dates
for current_date in trading_dates:
    
    # Check if today is a rebalance day
    if current_date in rebalance_dates:
        # REBALANCE: Calculate new positions
        new_positions = calculate_dw_signals(current_date)
        current_positions = new_positions
        
    # ALWAYS: Calculate daily P&L using current positions
    portfolio_value = calculate_daily_pnl(current_positions, current_date)
    
    # Hold positions until next rebalance date
```

**Key Points:**
1. ✅ **Daily P&L calculation**: Every day, calculate returns using current positions
2. ✅ **Periodic rebalancing**: Only update positions on rebalance days
3. ✅ **Hold between rebalances**: Positions unchanged on non-rebalance days

### Visual Example: 7-Day Rebalancing

```
Timeline (Days):
Day:    1    2    3    4    5    6    7    8    9   10   11   12   13   14   15
        │    │    │    │    │    │    │    │    │    │    │    │    │    │    │
Action: R    H    H    H    H    H    H    R    H    H    H    H    H    H    R

Legend:
  R = Rebalance (calculate new positions, execute trades)
  H = Hold (keep existing positions, calculate P&L only)

Day 1:  Rebalance → Long BTC, ETH, SOL | Short DOGE, SHIB
Day 2-7: Hold positions, track daily P&L
Day 8:  Rebalance → Recalculate DW, new positions
Day 9-14: Hold positions
Day 15: Rebalance → Recalculate DW, new positions
```

### Code Flow for Mixed Frequencies

**When you run `run_all_backtests.py`:**

```python
# Pseudo-code showing actual flow

def main():
    all_results = []
    
    # Strategy 1: Volatility (daily rebalancing)
    print("Running Volatility Factor...")
    vol_result = backtest_volatility_factor(
        data,
        rebalance_days=1,  # Rebalances every day
        initial_capital=10000
    )
    # vol_result contains:
    # - portfolio_values: daily equity curve
    # - trades: all trades executed
    # - positions: position history
    all_results.append(vol_result)
    
    # Strategy 2: DW Factor (weekly rebalancing)  
    print("Running DW Factor...")
    dw_result = backtest_dw_factor(
        data,
        rebalance_days=7,  # Rebalances every 7 days
        initial_capital=10000
    )
    # dw_result contains:
    # - portfolio_values: daily equity curve
    # - trades: all trades executed (fewer trades than volatility)
    # - positions: position history
    all_results.append(dw_result)
    
    # Strategy 3: Kurtosis (biweekly rebalancing)
    print("Running Kurtosis Factor...")
    kurt_result = backtest_kurtosis_factor(
        data,
        rebalance_days=14,  # Rebalances every 14 days
        initial_capital=10000
    )
    all_results.append(kurt_result)
    
    # Now combine results
    summary = compare_strategies(all_results)
    print_summary(summary)
```

**Each backtest is completely independent:**

```
Volatility Factor:
  - Has its own position tracker
  - Rebalances on: Day 1, 2, 3, 4, 5, 6, 7, 8, ...
  - Portfolio value updated daily
  - Independent equity curve

DW Factor:
  - Has its own position tracker (separate from Volatility)
  - Rebalances on: Day 1, 8, 15, 22, 29, ...
  - Portfolio value updated daily
  - Independent equity curve

Kurtosis Factor:
  - Has its own position tracker (separate from both above)
  - Rebalances on: Day 1, 15, 29, 43, ...
  - Portfolio value updated daily
  - Independent equity curve
```

### How Results Are Combined

**After running all backtests independently:**

```python
# Method 1: Simple comparison (current)
print_comparison_table([vol_result, dw_result, kurt_result])

# Output:
# Strategy          Sharpe   Return   Max DD
# ──────────────────────────────────────────
# Volatility (1d)    1.20    +65%    -28%
# DW Factor (7d)     0.67    +26%    -37%
# Kurtosis (14d)     0.71    +29%    -31%

# Method 2: Sharpe-weighted portfolio
weights = calculate_sharpe_weights([vol_result, dw_result, kurt_result])

# Output:
# Strategy          Weight   Contribution
# ──────────────────────────────────────────
# Volatility (1d)    46.7%    +30.3% return
# DW Factor (7d)     26.1%    +6.8% return  
# Kurtosis (14d)     27.2%    +7.9% return
# ──────────────────────────────────────────
# Combined          100.0%    +45.0% return

# Combined Sharpe: ~0.95 (better than any individual!)
```

---

## 🚀 CONTEXT 2: Production Trading (How to implement)

**In production, you need ONE unified system that manages positions from all strategies.**

### Architecture for Production

```
Main Trading System
    │
    ├─ Strategy Manager
    │   ├─ Volatility Strategy (rebalance_days=1)
    │   ├─ DW Strategy (rebalance_days=7)
    │   └─ Kurtosis Strategy (rebalance_days=14)
    │
    ├─ Position Aggregator
    │   └─ Combines signals from all strategies
    │
    ├─ Portfolio Manager
    │   ├─ Tracks total positions
    │   ├─ Handles overlapping signals
    │   └─ Executes trades
    │
    └─ Risk Manager
        └─ Ensures total exposure limits
```

### Implementation Option 1: Time-Based Scheduler

**Use a daily scheduler that checks what needs rebalancing:**

```python
import datetime

class StrategyScheduler:
    """Manages multiple strategies with different rebalance frequencies."""
    
    def __init__(self):
        self.strategies = {
            'volatility': {
                'rebalance_days': 1,
                'last_rebalance': None,
                'allocation': 0.30  # 30% of capital
            },
            'dw_factor': {
                'rebalance_days': 7,
                'last_rebalance': None,
                'allocation': 0.35  # 35% of capital
            },
            'kurtosis': {
                'rebalance_days': 14,
                'last_rebalance': None,
                'allocation': 0.35  # 35% of capital
            }
        }
        self.positions = {}  # Combined positions
        
    def should_rebalance(self, strategy_name, current_date):
        """Check if strategy should rebalance today."""
        strategy = self.strategies[strategy_name]
        last_rebalance = strategy['last_rebalance']
        rebalance_days = strategy['rebalance_days']
        
        if last_rebalance is None:
            return True  # First run
        
        days_since = (current_date - last_rebalance).days
        return days_since >= rebalance_days
    
    def run_daily(self, current_date):
        """Run all strategies, rebalancing as needed."""
        
        print(f"\n=== {current_date.strftime('%Y-%m-%d')} ===")
        
        new_signals = {}
        
        # Check each strategy
        for strategy_name, config in self.strategies.items():
            if self.should_rebalance(strategy_name, current_date):
                print(f"  ✓ Rebalancing {strategy_name}")
                
                # Generate new signals for this strategy
                signals = self.generate_signals(strategy_name, current_date)
                new_signals[strategy_name] = signals
                
                # Update last rebalance date
                config['last_rebalance'] = current_date
            else:
                # Use existing signals
                days_since = (current_date - config['last_rebalance']).days
                days_until = config['rebalance_days'] - days_since
                print(f"  - Holding {strategy_name} ({days_until} days until rebalance)")
                new_signals[strategy_name] = self.get_current_signals(strategy_name)
        
        # Aggregate signals across all strategies
        combined_positions = self.aggregate_signals(new_signals)
        
        # Execute trades to reach target positions
        trades = self.calculate_trades(self.positions, combined_positions)
        self.execute_trades(trades)
        
        # Update positions
        self.positions = combined_positions
        
        return self.positions

# Usage
scheduler = StrategyScheduler()

# Run daily
for date in trading_dates:
    positions = scheduler.run_daily(date)
```

**Example execution timeline:**

```
Day 1 (Monday):
  ✓ Rebalancing volatility (every 1 day)
  ✓ Rebalancing dw_factor (every 7 days) 
  ✓ Rebalancing kurtosis (every 14 days)
  → Combined: 15 positions

Day 2 (Tuesday):
  ✓ Rebalancing volatility (every 1 day)
  - Holding dw_factor (6 days until rebalance)
  - Holding kurtosis (13 days until rebalance)
  → Combined: 12 positions (vol changed, others held)

Day 3 (Wednesday):
  ✓ Rebalancing volatility (every 1 day)
  - Holding dw_factor (5 days until rebalance)
  - Holding kurtosis (12 days until rebalance)
  → Combined: 11 positions

...

Day 8 (Monday):
  ✓ Rebalancing volatility (every 1 day)
  ✓ Rebalancing dw_factor (every 7 days)
  - Holding kurtosis (7 days until rebalance)
  → Combined: 16 positions (vol + DW changed)

Day 15 (Monday):
  ✓ Rebalancing volatility (every 1 day)
  ✓ Rebalancing dw_factor (every 7 days)
  ✓ Rebalancing kurtosis (every 14 days)
  → Combined: 18 positions (all rebalanced)
```

### Implementation Option 2: Day-of-Week Scheduler

**Simpler approach using calendar days:**

```python
import datetime

def run_trading_system(current_date):
    """Run trading system with day-of-week based rebalancing."""
    
    day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
    week_number = current_date.isocalendar()[1]
    
    strategies_to_rebalance = []
    
    # Daily strategies (run every day)
    strategies_to_rebalance.append('volatility')
    strategies_to_rebalance.append('breakout')
    
    # Weekly strategies (run on Mondays)
    if day_of_week == 0:  # Monday
        strategies_to_rebalance.append('dw_factor')
        strategies_to_rebalance.append('size_factor')
        strategies_to_rebalance.append('carry_factor')
    
    # Biweekly strategies (run every other Monday)
    if day_of_week == 0 and week_number % 2 == 0:
        strategies_to_rebalance.append('kurtosis')
        strategies_to_rebalance.append('beta')
    
    print(f"\n{current_date.strftime('%Y-%m-%d %A')} - Rebalancing: {strategies_to_rebalance}")
    
    # Generate signals for strategies that need rebalancing
    all_signals = {}
    for strategy in strategies_to_rebalance:
        all_signals[strategy] = generate_signals(strategy, current_date)
    
    # Combine signals
    combined_positions = combine_signals(all_signals)
    
    # Execute trades
    execute_rebalance(combined_positions)

# Example output:
# 2024-01-01 Monday - Rebalancing: ['volatility', 'breakout', 'dw_factor', 'size_factor', 'carry_factor', 'kurtosis', 'beta']
# 2024-01-02 Tuesday - Rebalancing: ['volatility', 'breakout']
# 2024-01-03 Wednesday - Rebalancing: ['volatility', 'breakout']
# ...
# 2024-01-08 Monday - Rebalancing: ['volatility', 'breakout', 'dw_factor', 'size_factor', 'carry_factor']
# 2024-01-09 Tuesday - Rebalancing: ['volatility', 'breakout']
# ...
# 2024-01-15 Monday - Rebalancing: ['volatility', 'breakout', 'dw_factor', 'size_factor', 'carry_factor', 'kurtosis', 'beta']
```

### Handling Overlapping Positions

**What if multiple strategies want to trade the same asset?**

**Method 1: Weighted Average (Recommended)**

```python
def combine_signals(strategy_signals):
    """Combine signals from multiple strategies."""
    
    combined = {}
    
    # Example:
    # Volatility wants: BTC +30% (long)
    # DW Factor wants: BTC +20% (long)
    # Kurtosis wants: BTC -10% (short)
    
    # Weighted by strategy allocation:
    # Combined BTC = 0.30 * (+30%) + 0.35 * (+20%) + 0.35 * (-10%)
    #              = +9.0% + 7.0% - 3.5%
    #              = +12.5% (net long)
    
    for symbol in all_symbols:
        weighted_position = 0
        
        for strategy_name, signals in strategy_signals.items():
            strategy_weight = strategies[strategy_name]['allocation']
            strategy_position = signals.get(symbol, 0)
            weighted_position += strategy_weight * strategy_position
        
        if abs(weighted_position) > 0.01:  # Minimum threshold
            combined[symbol] = weighted_position
    
    return combined
```

**Method 2: Separate Buckets (Alternative)**

```python
def combine_signals_separate(strategy_signals):
    """Keep strategy positions separate."""
    
    combined = {}
    
    # Example:
    # Volatility bucket: BTC +10% of total capital
    # DW bucket: BTC +7% of total capital
    # Kurtosis bucket: BTC -3.5% of total capital
    # Total BTC: +13.5% of total capital
    
    for strategy_name, signals in strategy_signals.items():
        strategy_allocation = strategies[strategy_name]['allocation']
        
        for symbol, position in signals.items():
            if symbol not in combined:
                combined[symbol] = 0
            
            # Scale position by strategy allocation
            combined[symbol] += position * strategy_allocation
    
    return combined
```

### Complete Production Example

```python
#!/usr/bin/env python3
"""
Production trading system with mixed rebalance frequencies.
"""

import datetime
import pandas as pd
from typing import Dict, List

class MultiStrategyTrader:
    """Manages multiple strategies with different rebalance frequencies."""
    
    def __init__(self, initial_capital=100000):
        self.capital = initial_capital
        self.positions = {}  # Current positions {symbol: weight}
        
        # Strategy configurations
        self.strategies = {
            'volatility': {
                'rebalance_days': 1,
                'last_rebalance': None,
                'allocation': 0.30,  # 30% of capital
                'current_signals': {}
            },
            'dw_factor': {
                'rebalance_days': 7,
                'last_rebalance': None,
                'allocation': 0.35,  # 35% of capital
                'current_signals': {}
            },
            'kurtosis': {
                'rebalance_days': 14,
                'last_rebalance': None,
                'allocation': 0.35,  # 35% of capital
                'current_signals': {}
            }
        }
    
    def should_rebalance(self, strategy_name: str, current_date: datetime.date) -> bool:
        """Check if strategy needs rebalancing."""
        config = self.strategies[strategy_name]
        
        if config['last_rebalance'] is None:
            return True
        
        days_since = (current_date - config['last_rebalance']).days
        return days_since >= config['rebalance_days']
    
    def generate_signals(self, strategy_name: str, date: datetime.date) -> Dict[str, float]:
        """Generate trading signals for a strategy."""
        
        if strategy_name == 'volatility':
            # Call volatility signal generator
            from signals.calc_volatility_signals import calculate_volatility_signals
            return calculate_volatility_signals(date)
            
        elif strategy_name == 'dw_factor':
            # Call DW signal generator
            from signals.calc_dw_signals import calculate_dw_signals
            return calculate_dw_signals(date)
            
        elif strategy_name == 'kurtosis':
            # Call kurtosis signal generator
            from signals.calc_kurtosis_signals import calculate_kurtosis_signals
            return calculate_kurtosis_signals(date)
        
        return {}
    
    def aggregate_signals(self) -> Dict[str, float]:
        """Combine signals from all strategies."""
        combined = {}
        
        for strategy_name, config in self.strategies.items():
            allocation = config['allocation']
            signals = config['current_signals']
            
            for symbol, weight in signals.items():
                if symbol not in combined:
                    combined[symbol] = 0
                combined[symbol] += weight * allocation
        
        return combined
    
    def calculate_trades(self, current_positions: Dict[str, float], 
                        target_positions: Dict[str, float]) -> Dict[str, float]:
        """Calculate trades needed to reach target positions."""
        trades = {}
        
        all_symbols = set(current_positions.keys()) | set(target_positions.keys())
        
        for symbol in all_symbols:
            current = current_positions.get(symbol, 0)
            target = target_positions.get(symbol, 0)
            trade = target - current
            
            if abs(trade) > 0.001:  # Minimum trade size threshold
                trades[symbol] = trade
        
        return trades
    
    def execute_trades(self, trades: Dict[str, float]):
        """Execute trades (send to exchange)."""
        if not trades:
            print("  No trades needed")
            return
        
        print(f"  Executing {len(trades)} trades:")
        for symbol, trade in trades.items():
            direction = "BUY" if trade > 0 else "SELL"
            amount = abs(trade) * self.capital
            print(f"    {direction} {symbol}: ${amount:,.2f} ({trade:+.2%} of capital)")
            
            # TODO: Send to exchange via CCXT
            # exchange.create_order(symbol, 'market', direction, amount)
    
    def run_daily(self, current_date: datetime.date):
        """Main daily execution function."""
        
        print(f"\n{'='*80}")
        print(f"{current_date.strftime('%Y-%m-%d %A')}")
        print('='*80)
        
        # Check each strategy and rebalance if needed
        for strategy_name, config in self.strategies.items():
            if self.should_rebalance(strategy_name, current_date):
                print(f"✓ Rebalancing {strategy_name}")
                
                # Generate new signals
                new_signals = self.generate_signals(strategy_name, current_date)
                config['current_signals'] = new_signals
                config['last_rebalance'] = current_date
                
                print(f"  → {len(new_signals)} positions")
            else:
                days_since = (current_date - config['last_rebalance']).days
                days_until = config['rebalance_days'] - days_since
                print(f"- Holding {strategy_name} (next rebalance in {days_until} days)")
        
        # Aggregate all signals
        print("\nAggregating signals...")
        target_positions = self.aggregate_signals()
        print(f"  → {len(target_positions)} total positions")
        
        # Calculate and execute trades
        print("\nCalculating trades...")
        trades = self.calculate_trades(self.positions, target_positions)
        self.execute_trades(trades)
        
        # Update positions
        self.positions = target_positions
        
        # Calculate P&L
        # TODO: Fetch prices and calculate daily P&L
        
        print(f"\nCurrent capital: ${self.capital:,.2f}")
        print(f"Active positions: {len(self.positions)}")

# Usage
def main():
    trader = MultiStrategyTrader(initial_capital=100000)
    
    # Run for a period
    start_date = datetime.date(2024, 1, 1)
    end_date = datetime.date(2024, 12, 31)
    current = start_date
    
    while current <= end_date:
        # Skip weekends
        if current.weekday() < 5:  # Monday-Friday
            trader.run_daily(current)
        
        current += datetime.timedelta(days=1)

if __name__ == '__main__':
    main()
```

### Example Output

```
================================================================================
2024-01-01 Monday
================================================================================
✓ Rebalancing volatility
  → 8 positions
✓ Rebalancing dw_factor
  → 6 positions
✓ Rebalancing kurtosis
  → 7 positions

Aggregating signals...
  → 15 total positions

Calculating trades...
  Executing 15 trades:
    BUY BTC: $8,500.00 (+8.50% of capital)
    BUY ETH: $5,200.00 (+5.20% of capital)
    ...

Current capital: $100,000.00
Active positions: 15

================================================================================
2024-01-02 Tuesday
================================================================================
✓ Rebalancing volatility
  → 7 positions
- Holding dw_factor (next rebalance in 6 days)
- Holding kurtosis (next rebalance in 13 days)

Aggregating signals...
  → 14 total positions

Calculating trades...
  Executing 3 trades:
    SELL DOGE: $2,100.00 (-2.10% of capital)
    BUY MATIC: $1,800.00 (+1.80% of capital)
    ...

Current capital: $100,423.00
Active positions: 14
```

---

## ⚖️ Key Considerations

### 1. Position Sizing

**How much capital to allocate to each strategy?**

```python
# Option A: Equal allocation
volatility_allocation = 1/3  # 33.3%
dw_allocation = 1/3          # 33.3%
kurtosis_allocation = 1/3    # 33.3%

# Option B: Sharpe-weighted (better)
vol_sharpe = 1.20
dw_sharpe = 0.67
kurt_sharpe = 0.71
total_sharpe = vol_sharpe + dw_sharpe + kurt_sharpe

volatility_allocation = vol_sharpe / total_sharpe  # 46.5%
dw_allocation = dw_sharpe / total_sharpe           # 26.0%
kurtosis_allocation = kurt_sharpe / total_sharpe   # 27.5%
```

### 2. Overlapping Positions

**What if strategies want different positions in same asset?**

```python
# Example: BTC positions from each strategy

# Volatility: Wants BTC +15% (bullish)
# DW Factor: Wants BTC +10% (bullish)
# Kurtosis: Wants BTC -5% (bearish)

# Weighted average:
btc_position = (0.465 * 0.15) + (0.260 * 0.10) + (0.275 * (-0.05))
             = 0.0698 + 0.0260 - 0.0138
             = 0.0820 (net +8.2% long)

# This is fine! Strategies complement each other.
```

### 3. Transaction Costs

**Mixed frequencies reduce costs:**

```python
# Daily rebalancing everything:
# - 3 strategies × 10 positions × 365 days = 10,950 trades/year
# - Cost: ~0.1% × 10,950 = 1,095% (impossible!)

# Mixed frequencies:
# - Volatility: 10 pos × 365 days = 3,650 trades
# - DW: 10 pos × 52 weeks = 520 trades
# - Kurtosis: 10 pos × 26 biweeks = 260 trades
# - Total: 4,430 trades/year
# - Cost: ~0.1% × 4,430 = 443% (still high but 60% less!)

# Key: Not all strategies trade daily → lower total costs
```

### 4. Reconciliation

**Daily reconciliation process:**

```python
def daily_reconciliation(date):
    """Ensure positions match across all systems."""
    
    # 1. Get actual positions from exchange
    actual_positions = exchange.fetch_positions()
    
    # 2. Get expected positions from strategy system
    expected_positions = trader.positions
    
    # 3. Compare
    discrepancies = {}
    for symbol in set(actual_positions.keys()) | set(expected_positions.keys()):
        actual = actual_positions.get(symbol, 0)
        expected = expected_positions.get(symbol, 0)
        diff = actual - expected
        
        if abs(diff) > 0.01:  # 1% threshold
            discrepancies[symbol] = diff
    
    # 4. Alert if discrepancies found
    if discrepancies:
        alert_ops_team(f"Position discrepancies: {discrepancies}")
        
    # 5. Update P&L
    portfolio_value = sum(actual_positions[sym] * prices[sym] 
                         for sym in actual_positions)
    log_daily_pnl(date, portfolio_value)
```

---

## ✅ Summary

### In Backtesting (Current Implementation)

✅ **Each strategy runs independently**
- Volatility backtest runs with rebalance_days=1
- DW backtest runs with rebalance_days=7
- Results compared side-by-side
- No interaction between strategies

✅ **Already working!** No changes needed for backtesting.

### In Production (What You Need to Build)

📋 **Need unified position manager**
- One system tracks all positions
- Daily scheduler checks what needs rebalancing
- Aggregates signals from multiple strategies
- Executes net trades

📋 **Implementation steps:**
1. Create `MultiStrategyTrader` class (see example above)
2. Set up daily scheduler
3. Implement signal aggregation
4. Add risk management
5. Connect to exchange

---

## 🎯 Bottom Line

**Question:** "How will it work to handle mixed rebalance periods?"

**Answer:**

**For backtesting (current):** It already works! Each strategy backtests independently with its own rebalance frequency, then results are compared.

**For production (future):** You'll need to build a unified trading system that:
1. Runs daily
2. Checks each strategy's rebalance schedule
3. Generates signals for strategies that need rebalancing
4. Holds signals for strategies that don't
5. Aggregates all signals into combined positions
6. Executes only the net trades needed

The key insight: **Strategies don't interfere with each other** - they just contribute their signals, and the system combines them appropriately based on each strategy's allocation.

---

**Files created:**
- `docs/MIXED_REBALANCE_MECHANICS.md` (this file)

**Status:** ✅ Fully explained with code examples
