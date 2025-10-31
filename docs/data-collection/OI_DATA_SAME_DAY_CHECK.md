# OI Data Same-Day Check Implementation

## Date: 2025-10-27

## Overview
Implemented strict same-day checks for OI (Open Interest) data with comprehensive warnings at multiple levels to ensure traders are aware when using stale data.

## Warning Levels

### Level 1: File Loading (Low-level)
**Location**: `execution/strategies/open_interest_divergence.py` → `_load_aggregated_oi_from_file()`

**Warnings issued:**
- ✅ **Same day (0 days behind)**: "✓ OI data is current (today: YYYY-MM-DD)"
- ⚠️ **Yesterday (1 day behind)**: "WARNING: OI data is from YESTERDAY"
- 🔴 **2+ days behind**: "WARNING: OI data is X days old - signals may be stale"
- ⚠️ **Future dates**: "WARNING: OI data has FUTURE dates - data quality issue"

**Example output:**
```
Loading aggregated OI data from: historical_open_interest_all_perps_since2020_20251026_115907.csv
⚠️  WARNING: OI data is from YESTERDAY (2025-10-26)
Using most recent available data
Consider refreshing OI data for today's trading signals
✓ Loaded 597 OI records for 3 symbols
Date range: 2025-04-11 to 2025-10-26
```

### Level 2: Strategy Execution (Mid-level)
**Location**: `execution/strategies/open_interest_divergence.py` → `strategy_oi_divergence()`

**Warnings issued when OI data is behind:**
```
⚠️  OI DIVERGENCE STRATEGY: OI data is 1 day(s) behind
     Today: 2025-10-27
     Latest OI data: 2025-10-26
     Strategy will use data from 2025-10-26 for signal generation
```

**Critical warning for 3+ days:**
```
🔴 CRITICAL: Data is significantly stale - signals may be unreliable
    Strongly recommend refreshing OI data before trading
```

**Signal generation warnings:**
```
⚠️  Generating signals from 2025-10-26 (today is 2025-10-27)
    Signals are 1 day(s) behind current date
```

### Level 3: Main Execution (Top-level)
**Location**: `execution/main.py` → `check_oi_data_freshness()` and main execution flow

**Pre-flight check output:**
```
================================================================================
CHECKING OI DATA FRESHNESS
================================================================================
OI data file: historical_open_interest_all_perps_since2020_20251026_115907.csv
Latest OI data: 2025-10-26
Today: 2025-10-27
⚠️  OI data is from YESTERDAY
   Signals will be based on yesterday's data
   Recommendation: Refresh OI data for today
```

**Trading alert for stale data (if OI strategy weight > 10%):**
```
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
⚠️  TRADING ALERT: OI Divergence strategy is using stale data
   Strategy weight: 20.0%
   Data age: 1 day(s) behind
   Impact: Signals may not reflect current market conditions
   Recommendation: Refresh OI data before executing trades
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

## Implementation Details

### 1. File-Level Check (`_load_aggregated_oi_from_file`)
```python
# Check data freshness - strict same-day check
if not df.empty:
    max_date = df['date'].max()
    today = pd.Timestamp(datetime.now().date())
    days_stale = (today - max_date).days
    
    if days_stale == 0:
        print(f"    ✓ OI data is current (today: {today.date()})")
    elif days_stale == 1:
        print(f"    ⚠️  WARNING: OI data is from YESTERDAY ({max_date.date()})")
        print(f"    Using most recent available data")
        print(f"    Consider refreshing OI data for today's trading signals")
    elif days_stale > 1:
        print(f"    ⚠️  WARNING: OI data is {days_stale} days old (last update: {max_date.date()})")
        print(f"    Today: {today.date()}")
        print(f"    Using most recent available data, but signals may be stale")
        print(f"    RECOMMENDATION: Refresh OI data before trading")
```

### 2. Strategy-Level Check (`strategy_oi_divergence`)
```python
# Check if OI data is same day as execution
today = pd.Timestamp(datetime.now().date())
oi_latest_date = oi_df['date'].max()
days_behind = (today - oi_latest_date).days

if days_behind > 0:
    print(f"  ⚠️  OI DIVERGENCE STRATEGY: OI data is {days_behind} day(s) behind")
    print(f"       Today: {today.date()}")
    print(f"       Latest OI data: {oi_latest_date.date()}")
    print(f"       Strategy will use data from {oi_latest_date.date()} for signal generation")
    if days_behind > 2:
        print(f"       🔴 CRITICAL: Data is significantly stale - signals may be unreliable")
        print(f"       Strongly recommend refreshing OI data before trading")
```

### 3. Main Execution Check (`check_oi_data_freshness`)
```python
def check_oi_data_freshness():
    """Check the freshness of OI data for trading signals."""
    # Find OI data file
    # Read and check dates
    df = pd.read_csv(oi_file, usecols=['date'], nrows=100000)
    df['date'] = pd.to_datetime(df['date'])
    max_date = df['date'].max()
    today = pd.Timestamp(datetime.now().date())
    days_behind = (today - max_date).days
    
    if days_behind == 0:
        print("✓ OI data is CURRENT (same day)")
        return {'status': 'current', 'days_behind': 0}
    elif days_behind == 1:
        print("⚠️  OI data is from YESTERDAY")
        return {'status': 'yesterday', 'days_behind': 1}
    elif days_behind > 1:
        print(f"🔴 WARNING: OI data is {days_behind} DAYS OLD")
        return {'status': 'stale', 'days_behind': days_behind}
```

## Data Freshness Status Codes

| Status | Days Behind | Severity | Action |
|--------|-------------|----------|--------|
| `current` | 0 | ✅ Good | Proceed with trading |
| `yesterday` | 1 | ⚠️ Caution | Consider refreshing; acceptable for most use cases |
| `stale` | 2+ | 🔴 Critical | Strongly recommend refresh before trading |
| `future` | <0 | ⚠️ Warning | Data quality issue; investigate |
| `missing` | N/A | ❌ Error | Run data collection; strategy won't work |

## Testing

### Run Diagnostic Test
```bash
python3 test_oi_data_warnings.py
```

**Expected output when data is from yesterday:**
```
⚠️  ACCEPTABLE: OI data is from yesterday
   Trading signals will be 1 day behind
   ACTION: Consider refreshing before important trades
```

### Run Main Script with OI Strategy
```bash
python3 execution/main.py --signal-config execution/all_strategies_config.json --dry-run
```

**If OI data is stale and OI strategy has >10% weight:**
```
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
⚠️  TRADING ALERT: OI Divergence strategy is using stale data
   Strategy weight: 20.0%
   Data age: 1 day(s) behind
   Impact: Signals may not reflect current market conditions
   Recommendation: Refresh OI data before executing trades
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

## Data Refresh Workflow

### When to Refresh OI Data

1. **Daily**: Before market open or before first trade execution
2. **Real-time trading**: Every few hours for up-to-date signals
3. **After alerts**: When seeing "YESTERDAY" or "DAYS OLD" warnings

### How to Refresh OI Data

```bash
# Run OI data collection script
python3 data/scripts/fetch_all_open_interest_since_2020_all_perps.py

# Verify data is current
python3 test_oi_data_warnings.py
```

## Benefits

1. **Prevents Trading on Stale Data**: Immediate awareness of data staleness
2. **Multi-Level Warnings**: Catches issues at file, strategy, and execution levels
3. **Clear Actionable Messages**: Users know exactly what to do
4. **Risk Management**: Critical warnings for significantly stale data
5. **Automated Checks**: No manual verification needed

## Use Cases

### Use Case 1: Daily Trading Bot
- Runs every day at market open
- Checks OI data freshness automatically
- Issues alert if data is from yesterday
- Optionally auto-refresh data before trading

### Use Case 2: Real-Time Trading
- Runs multiple times per day
- Requires same-day data
- Fails gracefully with warnings if data is stale
- Logs warnings for monitoring

### Use Case 3: Backtesting
- Uses historical OI data
- Warnings less critical but still informative
- Helps identify data gaps

## Configuration

### Enable/Disable OI Freshness Check

The check runs automatically when OI divergence strategy is enabled in config:

```json
{
  "strategy_weights": {
    "oi_divergence": 0.2,  // 20% - triggers freshness check
    "other_strategy": 0.8
  }
}
```

### Adjust Warning Thresholds

Currently hardcoded:
- Same day (0): ✅ Good
- Yesterday (1): ⚠️ Warning
- 2+ days: 🔴 Critical

To adjust, modify thresholds in:
- `execution/strategies/open_interest_divergence.py`
- `execution/main.py`

## Troubleshooting

### "OI data is from YESTERDAY"
**Normal situation**: Data collection runs once per day
**Action**: Acceptable for most use cases; refresh if needed

### "OI data is X DAYS OLD"
**Problem**: Data collection hasn't run recently
**Action**: Run data collection script immediately

### "OI data has FUTURE dates"
**Problem**: Data quality or timezone issue
**Action**: Check data collection script for bugs

### "No OI data file found"
**Problem**: Data collection never run or file moved
**Action**: Run initial data collection

## Files Modified

1. `execution/strategies/open_interest_divergence.py` - Three-level warnings
2. `execution/main.py` - Pre-flight freshness check and trading alert
3. `test_oi_data_warnings.py` - Diagnostic test script

## Performance Impact

- **Minimal**: Date checks are fast (< 1 second)
- **File reading**: Uses `nrows=100000` for quick sampling
- **No API calls**: All checks use local file
- **Early detection**: Fails fast if data is missing

## Next Steps

1. Consider automating OI data refresh as pre-trading step
2. Add monitoring/alerting for data staleness in production
3. Integrate with scheduling system (cron) for daily refresh
4. Add retry logic if data collection fails

## Conclusion

The implementation provides comprehensive same-day data checking with clear, actionable warnings at multiple levels. Users are immediately aware when OI data is stale and can take appropriate action before executing trades.
