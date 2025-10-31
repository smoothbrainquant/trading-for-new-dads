# OI Auto-Refresh Quick Start Guide

## TL;DR

**OI data now refreshes automatically!** No manual intervention needed.

- ✅ Triggers when data is 1+ days old OR file is >8 hours old
- ✅ Only runs when OI divergence strategy is active
- ✅ Integrated into main.py execution flow
- ✅ Clear status messages and error handling

## Quick Reference

### Automatic (Recommended)

```bash
# Just run main.py - auto-refresh happens automatically
python3 execution/main.py --dry-run

# OI data will be checked and refreshed if:
# - Data content is 1+ days behind, OR
# - File modification time is >8 hours old
```

### Manual Check

```bash
# Check status without downloading
python3 data/scripts/refresh_oi_data.py --check-only
```

**Example output:**
```
================================================================================
OI DATA STATUS
================================================================================
Status: current
Latest data date: 2025-10-28
File age: 2.3 hours
Days behind: 0
File: /workspace/data/raw/historical_open_interest_all_perps_since2020_20251028_080000.csv
Needs refresh: False
```

### Manual Refresh

```bash
# Refresh only if needed (smart)
python3 data/scripts/refresh_oi_data.py

# Force refresh even if current
python3 data/scripts/refresh_oi_data.py --force
```

## Requirements

### Environment Variables

```bash
# Required for downloading OI data
export COINALYZE_API="your_api_key_here"
```

**Without COINALYZE_API:**
- Auto-refresh will fail gracefully
- Trading continues with existing data
- Warning message displayed

### Dependencies

Already in `requirements.txt`:
- pandas
- requests
- (Coinalyze client is included in repo)

## When Does Auto-Refresh Trigger?

### Content Freshness Check

```python
if latest_date_in_data < today:
    # Data is stale - DOWNLOAD
```

### File Age Check

```python
if file_modification_time > 8_hours_ago:
    # File is old - DOWNLOAD
```

### Both Checks Must Pass

Data is considered **fresh** only if:
1. Content date = today's date, AND
2. File age < 8 hours

## What Happens During Refresh?

### Step 1: Check Status (Instant)
```
OI DATA FRESHNESS CHECK
Status: stale_file
File age: 10.2 hours
Reason: File is 10.2 hours old (>8 hour threshold)
```

### Step 2: Trigger Download (~5-10 min)
```
DOWNLOADING FRESH OI DATA
Fetching OI data for 200 symbols (rate limited to 40/min)
Estimated time: 7.5 minutes

[   10/200] BTC     : BTCUSDT_PERP.A | Elapsed: 0.3m | Remaining: 7.1m
[   20/200] ETH     : ETHUSDT_PERP.A | Elapsed: 0.5m | Remaining: 6.8m
...
```

### Step 3: Save & Report
```
✓ OI DATA DOWNLOAD COMPLETE
File: /workspace/data/raw/historical_open_interest_all_perps_since2020_20251028_143022.csv
Date range: 2020-01-01 → 2025-10-28
Unique bases: 195
Total rows: 284,567
File size: 15.3 MB
Time taken: 7.2 minutes
```

## Integration with Trading

### Pre-flight Checks

```python
# In main.py, before strategies run:

if 'oi_divergence' in strategy_weights and weight > 0:
    oi_result = check_and_refresh_oi_data_if_needed()
    
    if oi_result['refreshed']:
        print("✓ OI DATA AUTOMATICALLY REFRESHED")
    elif oi_result['status'] == 'current':
        print("✓ OI data is current")
    else:
        print("⚠️  WARNING: Using existing data")
```

### Strategy Execution

- OI divergence strategy runs normally
- Uses latest available data
- No code changes needed in strategy logic

## Performance

### Download Time

| Symbols | Time    |
|---------|---------|
| 50      | ~2 min  |
| 100     | ~4 min  |
| 200     | ~8 min  |
| 300     | ~12 min |

Rate limited to **40 calls/min** (Coinalyze API limit)

### Disk Usage

- Each file: ~10-50 MB
- Typical: ~15-20 MB per download
- Old files accumulate (manual cleanup recommended)

**Cleanup old files:**
```bash
# Keep only last 7 OI data files
cd /workspace/data/raw
ls -t historical_open_interest_all_perps_since2020_*.csv | tail -n +8 | xargs rm -f
```

## Troubleshooting

### "COINALYZE_API environment variable not set"

**Solution:**
```bash
export COINALYZE_API="your_api_key"
```

Get API key from: https://coinalyze.net/

### "OI DATA REFRESH FAILED"

**Common causes:**
1. No internet connection
2. Coinalyze API down or rate limited
3. Invalid API key
4. Disk space full

**Check:**
```bash
# Test API key
curl -H "Authorization: Bearer $COINALYZE_API" https://api.coinalyze.net/v1/exchanges

# Check disk space
df -h /workspace/data/raw
```

### Download takes >15 minutes

**Possible causes:**
- Network latency
- Coinalyze API slow response
- Too many symbols in universe

**Normal behavior:**
- 200 symbols = 5-10 minutes
- Rate limiting adds delays

### "No OI data file found"

**Solution:**
```bash
# Force download manually
python3 data/scripts/refresh_oi_data.py --force
```

## Testing

### Test Auto-Refresh

```bash
# 1. Delete existing OI data
rm /workspace/data/raw/historical_open_interest_all_perps_since2020_*.csv

# 2. Run main.py (should trigger download)
python3 execution/main.py --dry-run

# 3. Check that new file was created
ls -lh /workspace/data/raw/historical_open_interest_all_perps_since2020_*.csv
```

### Test Freshness Check

```bash
# Check current status
python3 data/scripts/refresh_oi_data.py --check-only
```

**Expected output if fresh:**
```
Status: current
Needs refresh: False
```

**Expected output if stale:**
```
Status: stale_file  (or stale_content)
Needs refresh: True
Reason: File is 10.2 hours old (>8 hour threshold)
```

## Advanced Usage

### Custom Start Year

```bash
# Download from 2021 instead of 2020
python3 data/scripts/refresh_oi_data.py --start-year 2021
```

### Programmatic Access

```python
from data.scripts.refresh_oi_data import (
    get_oi_data_status,
    check_and_refresh_oi_data
)

# Check status
status = get_oi_data_status()
print(f"Data is fresh: {not status['needs_refresh']}")

# Refresh if needed
result = check_and_refresh_oi_data(force=False)
if result['refreshed']:
    print("Data was refreshed")
```

## Monitoring

### Success Indicators ✅

- "✓ OI data is current - no refresh needed"
- "✓ OI DATA AUTOMATICALLY REFRESHED"
- "✓ OI DATA DOWNLOAD COMPLETE"
- File timestamp is recent

### Warning Indicators ⚠️

- "⚠️ CRITICAL: OI DATA REFRESH FAILED"
- "⚠️ Error checking OI data"
- Download takes >15 minutes

### Action Required 🔴

- "❌ ERROR: COINALYZE_API environment variable not set"
  → Set API key in environment
  
- "❌ ERROR: Could not load perpetual markets universe"
  → Check API key validity and network
  
- "❌ ERROR: No OI data fetched"
  → Check Coinalyze API status

## Best Practices

### Daily Operations

1. **Let auto-refresh handle it**
   - No manual intervention needed
   - Runs automatically when needed

2. **Monitor first run of the day**
   - May trigger download (8-hour threshold)
   - Check console for refresh status

3. **Verify API key monthly**
   - Ensure COINALYZE_API is valid
   - Check API rate limits

### Cleanup

**Weekly:**
```bash
# Keep last 14 OI files (2 weeks)
cd /workspace/data/raw
ls -t historical_open_interest_all_perps_since2020_*.csv | tail -n +15 | xargs rm -f
```

**Monthly:**
```bash
# Keep only last 7 files
cd /workspace/data/raw
ls -t historical_open_interest_all_perps_since2020_*.csv | tail -n +8 | xargs rm -f
```

## FAQ

**Q: When should I manually refresh?**
A: Rarely needed. Auto-refresh handles it. Manual refresh useful for:
- Testing new setup
- After API credential changes
- Forcing immediate update

**Q: How often does it download?**
A: Only when needed:
- Once per day minimum (if data is current)
- More often if file is >8 hours old

**Q: Can I disable auto-refresh?**
A: Yes, set OI divergence strategy weight to 0:
```json
{"strategy_weights": {"oi_divergence": 0.0}}
```

**Q: Does it slow down trading?**
A: No impact if data is fresh (instant check).
If download needed: 5-10 min delay on first run.

**Q: What if download fails?**
A: Trading continues with existing data.
Warning message displayed.
Retry on next run.

**Q: Can I run in background?**
A: Yes, download is non-interactive:
```bash
nohup python3 data/scripts/refresh_oi_data.py > oi_refresh.log 2>&1 &
```

## Summary

### Before Auto-Refresh
- ❌ Manual monitoring required
- ❌ Could trade on stale data
- ❌ High risk of outdated signals

### After Auto-Refresh
- ✅ Automatic monitoring
- ✅ Always uses fresh data (<8h old)
- ✅ Low risk, high reliability
- ✅ Clear status feedback

**Just run your trading strategy - OI data handles itself!**
