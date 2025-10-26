# Coinalyze API Fix Summary

## Problem Identified
Coinalyze API was returning empty data, causing carry and OI divergence strategies to fail silently. This resulted in **79% of capital ($159k/$200k)** not being allocated in live trading.

## Root Cause
**Incorrect symbol format for Hyperliquid in Coinalyze API**
- Code was using: `BTCUSDC_PERP.H` 
- Coinalyze expects: `BTC.H` (simple format for Hyperliquid)
- Other exchanges like Binance use: `BTCUSDT_PERP.A`

## Files Fixed

### 1. `/workspace/execution/get_carry.py`
**Changes:**
- Fixed `_build_coinalyze_symbol()` to use correct format for Hyperliquid
- Added warning when Coinalyze returns no funding rate data
- Better error messages showing which symbols were requested

### 2. `/workspace/execution/strategies/open_interest_divergence.py`
**Changes:**
- Fixed `_build_coinalyze_symbol()` to use correct format
- Enhanced error message with troubleshooting steps
- Clearer indication when OI data is missing

### 3. `/workspace/execution/strategies/carry.py`
**Changes:**
- Improved warning messages with ⚠️ indicators
- Better fallback error handling

### 4. `/workspace/execution/main.py`
**Added Capital Utilization Warning System:**
- Calculates and displays total capital utilization
- Shows per-strategy utilization breakdown
- **Warns when < 50% capital is deployed**
- Provides troubleshooting suggestions

## Results

### Before Fix:
```
Mean Reversion:  0% ($0 / $127,420)      ❌
Size:           111% ($22,956 / $20,640)  ✓
Carry:           0% ($0 / $18,400)        ❌
OI Divergence:   0% ($0 / $13,540)       ❌
Breakout:       65% ($6,518 / $10,000)
Days from High: 85% ($8,497 / $10,000)

Total Utilization: ~19% ($38k / $200k)
```

### After Fix:
```
Mean Reversion:  0% ($0 / $647)          ❌ (still an issue)
Size:           200% ($210 / $105)        ✓
Carry:          200% ($187 / $93)         ✓ FIXED!
OI Divergence:   0% ($0 / $69)           ❌ (still an issue)
Breakout:       200% ($102 / $51)         ✓
Days from High: 100% ($51 / $51)          ✓

Total Utilization: 43% (on ~$1k account)
```

## Remaining Issues

### 1. Mean Reversion Strategy (63.71% weight)
**Status:** Not finding any signals
**Possible causes:**
- Market conditions don't meet criteria (extreme dips with high volume)
- Parameters too conservative (zscore_threshold=1.5, volume_threshold=1.0)
- Only looks for 2-day lookback period

**Recommendation:** Investigate why mean_reversion isn't generating signals. This is the largest allocation (63.71%) and currently deploying 0%.

### 2. OI Divergence Strategy (6.77% weight)  
**Status:** Still returning no data
**Next steps to debug:**
- Verify Coinalyze has OI history data for Hyperliquid symbols
- Test `get_open_interest_history()` endpoint directly
- May need different symbol format for historical vs current data

## Warning System

The main.py now displays clear warnings when strategies fail:

```
⚠️  WARNING: LOW CAPITAL UTILIZATION (43.3%)
    Expected ~100% utilization with leverage, but only 43.3% is allocated.
    This means most strategies are NOT finding signals:
      ❌ mean_reversion      :   0.0% ($0.00 / $647.49)
      ✓ size                : 200.0% ($209.87 / $104.93)
      ✓ carry               : 200.0% ($186.94 / $93.47)
      ❌ oi_divergence       :   0.0% ($0.00 / $68.79)
      ✓ breakout            : 200.0% ($101.63 / $50.82)
      ✓ days_from_high      : 100.0% ($50.82 / $50.82)
```

## Testing

To verify the fixes:
```bash
cd /workspace
PYTHONPATH=/workspace:/workspace/data/scripts:/workspace/execution \
  python3 execution/main.py \
  --dry-run \
  --leverage 2 \
  --signal-config backtests/results/all_backtests_sharpe_weights.json \
  --rebalance-threshold 0.01
```

## Future Improvements

1. **Mean Reversion**: Add parameter sweep to find optimal thresholds
2. **OI Divergence**: Debug why OI history isn't being fetched
3. **Monitoring**: Add alerts when strategies consistently return 0 signals
4. **Fallback**: Consider reducing weights of non-performing strategies dynamically
