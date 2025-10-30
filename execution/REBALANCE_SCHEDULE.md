# Optimal Rebalance Schedule for Trading Strategies

## Overview

This document specifies the optimal rebalancing frequencies for each strategy based on comprehensive backtesting analysis.

## Recommended Schedule

### Primary Recommendation: Weekly Rebalancing (Every 7 Days)

Run `main.py` **every 7 days** (weekly) for optimal risk-adjusted returns.

```bash
# Example cron schedule for weekly execution (Sundays at 00:00 UTC)
0 0 * * 0 /path/to/python /workspace/execution/main.py
```

### Strategy-Specific Optimal Periods

Based on backtest analysis from OI_REBALANCE_PERIOD_ANALYSIS.md:

| Strategy | Optimal Rebalance Period | Sharpe Ratio | Ann. Return |
|----------|-------------------------|--------------|-------------|
| **OI Divergence** | **7 days** ⭐ | 0.193 | 7.59% |
| OI Trend | 5 days | 0.073 | 2.80% |
| Mean Reversion | 2 days (from previous analysis) | - | - |
| Breakout | Variable | - | - |
| Days from High | Variable | - | - |

### Why 7 Days for OI Divergence?

The backtest analysis (testing periods: 1, 2, 3, 5, 7, 10, 30 days) revealed:

1. **Very short periods (1-5 days) underperform** due to noise and potentially higher transaction costs
2. **7-day rebalancing is optimal** for capturing medium-term OI-price divergences
3. **Longer periods (10-30 days)** show declining performance as signals become stale

Key Results for 7-Day Rebalance:
- Total Return: +42.83% (nearly 5 years)
- Annualized Return: 7.59%
- Sharpe Ratio: 0.193
- Max Drawdown: -57.76%

### Current Configuration

The `all_strategies_config.json` file is already configured with optimal parameters:

```json
{
  "oi_divergence": {
    "mode": "divergence",    // ✓ Optimal (2.7x better than "trend")
    "lookback": 30,          // ✓ Optimal
    "top_n": 10,            // ✓ Optimal
    "bottom_n": 10,         // ✓ Optimal
    "exchange_code": "A"    // ✓ Aggregate across exchanges
  }
}
```

## Implementation Notes

### Manual Execution
```bash
# Dry run to verify positions
python3 execution/main.py --dry-run

# Live execution (runs once, rebalances portfolio)
python3 execution/main.py
```

### Automated Execution (Recommended)

**Linux/Mac (crontab):**
```bash
# Edit crontab
crontab -e

# Add weekly execution (every Sunday at 00:00 UTC)
0 0 * * 0 cd /workspace && python3 execution/main.py >> logs/execution.log 2>&1
```

**Alternative: Every 7 days from specific date**
```bash
# If you want to maintain exact 7-day intervals from a specific start date
# Run manually first, then set up a 7-day cron:
# (This example runs every 7 days starting from the date of first execution)
0 0 */7 * * cd /workspace && python3 execution/main.py >> logs/execution.log 2>&1
```

### Portfolio Rebalance Threshold

The script uses a threshold parameter to avoid excessive trading. Current default:
- **Threshold: 5%** of portfolio value
- Trades only execute when position difference exceeds this threshold

Adjust threshold if needed:
```bash
python3 execution/main.py --threshold 0.03  # 3% threshold for more frequent adjustments
python3 execution/main.py --threshold 0.10  # 10% threshold for less frequent adjustments
```

## Capital Allocation

Current strategy weights in `all_strategies_config.json`:
- Mean Reversion: 63.7%
- Size: 10.3%
- Carry: 9.2%
- **OI Divergence: 6.8%** ← Allocate more capital for better returns?
- Breakout: 5.0%
- Days from High: 5.0%

**Note:** Consider increasing OI Divergence allocation given its strong risk-adjusted returns (Sharpe: 0.193).

## Performance Monitoring

After implementing 7-day rebalancing:

1. Track execution logs for successful rebalances
2. Monitor Sharpe ratio over rolling periods
3. Compare live performance vs backtest expectations
4. Adjust if market conditions significantly change

---

**Last Updated:** October 29, 2025  
**Analysis Reference:** OI_REBALANCE_PERIOD_ANALYSIS.md
