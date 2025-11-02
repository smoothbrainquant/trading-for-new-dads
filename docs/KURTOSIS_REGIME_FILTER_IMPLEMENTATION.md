# Kurtosis Strategy with Regime Filter - Implementation Guide

**Date:** November 2, 2025  
**Status:** ? LIVE - Regime-filtered kurtosis strategy deployed  
**Strategy:** Mean Reversion Kurtosis Factor (Bear Market Only)

---

## Overview

The kurtosis mean reversion strategy has been updated with a **regime filter** that only activates during **bear markets**. This critical change prevents the strategy from experiencing the catastrophic losses (-25% to -90% annualized) that occur in bull markets.

### Performance Summary by Regime

| Regime | Annualized Return | Sharpe Ratio | Status |
|--------|------------------|--------------|--------|
| **Bear / Low Vol** | +28% to +50% | 1.79 | ? Active |
| **Bear / High Vol** | +25% to +49% | 1.54 | ? Active |
| **Bull / Low Vol** | -25% to -35% | -2.01 | ?? Filtered Out |
| **Bull / High Vol** | -22% to -36% | -1.22 | ?? Filtered Out |

---

## Implementation Details

### 1. Regime Detection Module

**Location:** `/workspace/execution/strategies/regime_filter.py`

**Core Function:** `detect_market_regime(historical_data, reference_symbol="BTC/USD")`

**Logic:**
- Uses 50-day vs 200-day moving average crossover on BTC
- **Bear Market:** 50MA < 200MA (strategy activates)
- **Bull Market:** 50MA > 200MA (strategy deactivates)
- Requires minimum 200 days of historical data
- Calculates confidence level based on MA separation

**Output:**
```python
{
    "regime": "bull" or "bear",
    "ma_50": float,
    "ma_200": float,
    "price": float,
    "confidence": "high" or "low",  # Based on MA separation >5%
    "days_in_regime": int,
    "ma_diff_pct": float
}
```

### 2. Updated Kurtosis Strategy

**Location:** `/workspace/execution/strategies/kurtosis.py`

**New Parameters:**
- `regime_filter` (str): "bear_only", "bull_only", or "always"
- `reference_symbol` (str): Symbol for regime detection (default: "BTC/USD")
- `strategy_type` (str): Changed default to "mean_reversion" (was "momentum")

**Behavior:**
1. Strategy checks regime before calculating any positions
2. If regime filter doesn't pass ? returns `{}` (empty positions)
3. If regime filter passes ? proceeds with normal position generation
4. Safe mode: If regime detection fails and filter is active ? returns `{}` (no positions)

### 3. Configuration Updates

**Location:** `/workspace/execution/all_strategies_config.json`

**Current Settings:**
```json
{
  "kurtosis": {
    "kurtosis_window": 30,
    "rebalance_days": 14,
    "long_percentile": 20,
    "short_percentile": 80,
    "weighting_method": "risk_parity",
    "long_allocation": 0.5,
    "short_allocation": 0.5,
    "strategy_type": "mean_reversion",
    "regime_filter": "bear_only",
    "reference_symbol": "BTC/USD"
  },
  "strategy_weights": {
    "kurtosis": 0.05  // 5% allocation (capped due to regime dependency)
  }
}
```

### 4. Main Execution Updates

**Location:** `/workspace/execution/main.py`

**Changes:**
- Updated parameter builder to pass `regime_filter` and `reference_symbol`
- Changed default `strategy_type` from "momentum" to "mean_reversion"

---

## Usage Guide

### Running the Strategy

The strategy will automatically activate/deactivate based on market regime:

```bash
# Standard execution (uses config file settings)
python3 execution/main.py --dry-run

# With specific signals including kurtosis
python3 execution/main.py --signals kurtosis,volatility,beta --dry-run

# Live execution (only when you're ready!)
python3 execution/main.py
```

### Expected Output

**In Bear Market (Strategy Active):**
```
================================================================================
MARKET REGIME DETECTION
================================================================================

Reference Symbol: BTC/USD
  Date: 2025-11-02
  Price: $67,234.56
  50-day MA: $65,123.45
  200-day MA: $68,456.78
  MA Separation: 4.86%

  ?? REGIME: BEAR
  Confidence: LOW
  Days in regime: 12
================================================================================

--------------------------------------------------------------------------------
KURTOSIS FACTOR STRATEGY WITH REGIME FILTER
--------------------------------------------------------------------------------
  Strategy type: mean_reversion
  Regime filter: bear_only
  ...

================================================================================
? STRATEGY ACTIVE - REGIME FILTER PASSED
================================================================================
  Bear market confirmed (low confidence: MAs close together)
  Current regime: BEAR
  Proceeding with position generation...
================================================================================

[... position generation proceeds normally ...]
```

**In Bull Market (Strategy Inactive):**
```
================================================================================
MARKET REGIME DETECTION
================================================================================

Reference Symbol: BTC/USD
  Date: 2025-11-02
  Price: $67,234.56
  50-day MA: $68,456.78
  200-day MA: $65,123.45
  MA Separation: 5.12%

  ?? REGIME: BULL
  Confidence: HIGH
  Days in regime: 45
================================================================================

--------------------------------------------------------------------------------
KURTOSIS FACTOR STRATEGY WITH REGIME FILTER
--------------------------------------------------------------------------------
  Strategy type: mean_reversion
  Regime filter: bear_only
  ...

================================================================================
?? STRATEGY INACTIVE - REGIME FILTER
================================================================================
  Reason: Bull market detected - strategy inactive (kurtosis mean reversion is bear-market only)
  Current regime: BULL
  Filter setting: bear_only

  No positions will be generated.
  Strategy will remain flat (all capital in cash/stables).
================================================================================
```

---

## Configuration Options

### Regime Filter Settings

| Setting | Description | Use Case |
|---------|-------------|----------|
| `"bear_only"` | Only activate in bear markets | **RECOMMENDED** for mean_reversion |
| `"bull_only"` | Only activate in bull markets | For momentum variant (untested) |
| `"always"` | No regime filter | **DANGEROUS** - Will lose money in bulls |

### Strategy Type Settings

| Type | Description | Best Regime | Status |
|------|-------------|-------------|--------|
| `"mean_reversion"` | Long low kurtosis, Short high kurtosis | Bear markets | ? Implemented with filter |
| `"momentum"` | Long high kurtosis, Short low kurtosis | Unknown | ?? No regime filter yet |

---

## Safety Features

### 1. Fail-Safe Defaults
- If regime detection fails ? Strategy deactivates (returns no positions)
- If BTC data unavailable ? Strategy deactivates
- If insufficient data (<200 days) ? Strategy deactivates

### 2. Warning System
```
??  WARNING: Mean reversion mode without regime filter!
??  This strategy loses -25% to -90% annualized in bull markets!
??  Strongly recommend setting regime_filter='bear_only'
```

### 3. Confidence Levels
- **High Confidence:** MAs separated by >5% (clear trend)
- **Low Confidence:** MAs separated by <5% (potential transition)
- Strategy activates in both but notes the confidence level

---

## Capital Management

### Current Allocation
- **Strategy Weight:** 5% of portfolio (capped)
- **Reason for Cap:** High regime dependency and negative overall Sharpe
- **Effective Allocation:** 0% in bulls, 5% in bears

### Expected Behavior
- **Bull Market Days (~60% of time):** 0% allocation, capital remains in other strategies
- **Bear Market Days (~40% of time):** 5% allocation, generates long/short positions
- **Average Utilization:** ~2% of portfolio (5% ? 40% market time)

### Rebalancing
- **Frequency:** 14 days (bi-weekly) when active
- **Positions:** Up to 10 long + 10 short
- **Weighting:** Risk parity (inverse volatility weighting)

---

## Testing & Validation

### Test Script

Create a test file to verify regime detection:

```python
# test_regime_filter.py
import sys
sys.path.insert(0, '/workspace')

from execution.strategies.regime_filter import detect_market_regime, should_activate_strategy
from data.scripts.ccxt_get_data import ccxt_fetch_hyperliquid_daily_data

# Fetch BTC data
print("Fetching BTC data...")
symbols = ["BTC/USD"]
historical_data = {}

df = ccxt_fetch_hyperliquid_daily_data(symbols=symbols, days=200)
if df is not None and not df.empty:
    for symbol in df["symbol"].unique():
        historical_data[symbol] = df[df["symbol"] == symbol].copy()

# Detect regime
regime_info = detect_market_regime(historical_data, reference_symbol="BTC/USD")

# Check activation
should_activate, reason = should_activate_strategy(regime_info, strategy_type="bear_only")

print("\n" + "="*80)
print("REGIME FILTER TEST RESULTS")
print("="*80)
print(f"Regime: {regime_info['regime'].upper()}")
print(f"Should Activate: {should_activate}")
print(f"Reason: {reason}")
print("="*80)
```

### Expected Backtest Improvement

**Without Regime Filter (2022-2025):**
- Total Return: -47.2%
- Sharpe Ratio: -0.39
- Max Drawdown: -75.5%

**With Regime Filter (Estimated):**
- Total Return: **+35% to +50%** (bear market performance only)
- Sharpe Ratio: **1.5 to 1.8** (bear market performance only)
- Max Drawdown: **-20% to -30%** (within bear markets)
- Time in Market: **~40%** (only bear market periods)

---

## Risk Warnings

### ?? Regime Transition Risk
- MAs are lagging indicators
- May enter bull market ~10-20 days after actual peak
- May exit bear market ~10-20 days after actual bottom
- **Mitigation:** Low confidence warnings when MAs are close

### ?? Data Dependency
- Requires 200 days of BTC historical data
- Requires accurate BTC price data
- **Mitigation:** Fail-safe defaults to inactive if data unavailable

### ?? Whipsaw Risk
- Rapid regime changes can cause whipsaws
- Strategy may activate/deactivate multiple times in sideways markets
- **Mitigation:** 14-day rebalance frequency reduces trade frequency

### ?? Bull Market Miss
- Will miss any gains if kurtosis strategy works in bull markets
- Based on backtest, this is a **FEATURE not a BUG** (prevents -90% losses)

---

## Monitoring Checklist

### Daily Checks
- [ ] Verify regime detection is working (check logs)
- [ ] Confirm positions only generated in bear markets
- [ ] Monitor BTC 50MA and 200MA spread

### Weekly Checks
- [ ] Review regime transitions in past week
- [ ] Verify strategy activated/deactivated appropriately
- [ ] Check performance during active periods

### Monthly Checks
- [ ] Compare strategy performance to bear market expectations (+25-50% annualized)
- [ ] Review false positives/negatives in regime detection
- [ ] Validate BTC data quality

---

## Troubleshooting

### Problem: Strategy Not Activating in Known Bear Market

**Possible Causes:**
1. Insufficient BTC data (<200 days)
2. BTC symbol mismatch (check "BTC/USD" vs "BTC-USD")
3. 50MA still above 200MA (not officially bear yet)

**Solutions:**
- Check logs for regime detection output
- Verify BTC data availability: `historical_data["BTC/USD"]`
- Manually check moving averages
- Consider using `regime_filter="always"` temporarily (with caution!)

### Problem: Strategy Active in Bull Market

**Possible Causes:**
1. `regime_filter` not set to `"bear_only"` in config
2. Regime detection module not loading
3. BTC data stale or incorrect

**Solutions:**
- Verify config: `params.kurtosis.regime_filter == "bear_only"`
- Check for import errors in logs
- Refresh BTC data
- **IMMEDIATELY DEACTIVATE** if confirmed bug (set weight to 0.0)

### Problem: Regime Detection Failing

**Possible Causes:**
1. BTC symbol not in historical_data dict
2. Insufficient data points (<200)
3. Data quality issues (NaN values)

**Solutions:**
- Add fallback symbols: ["BTC/USD", "BTC-USD", "BTCUSD"]
- Extend data fetch period
- Check data for gaps/NaN values
- Default to inactive (safe mode)

---

## Future Enhancements

### Potential Improvements

1. **Multi-Factor Regime Detection**
   - Add volatility regime (already implemented in `get_volatility_regime()`)
   - Add momentum regime
   - Combine signals for higher confidence

2. **Adaptive Parameters**
   - Tighter thresholds in low-confidence regimes
   - Wider thresholds in high-confidence regimes
   - Dynamic position sizing based on days in regime

3. **Regime Transition Handling**
   - Gradual position reduction as regime weakens
   - Early warning system (MAs converging)
   - Faster exit than entry

4. **Alternative Regime Indicators**
   - Fear & Greed Index
   - Funding rate regime
   - Market cap weighted index
   - RSI-based regime

---

## References

- **Backtest Analysis:** `/workspace/docs/KURTOSIS_REGIME_ANALYSIS.md`
- **Regime Filter Code:** `/workspace/execution/strategies/regime_filter.py`
- **Kurtosis Strategy:** `/workspace/execution/strategies/kurtosis.py`
- **Config File:** `/workspace/execution/all_strategies_config.json`
- **Backtest Script:** `/workspace/backtests/scripts/backtest_kurtosis_factor.py`
- **Regime Analysis Script:** `/workspace/backtests/scripts/analyze_kurtosis_by_regime.py`

---

## Change Log

### 2025-11-02: Initial Implementation
- ? Created `regime_filter.py` module
- ? Updated `kurtosis.py` with regime detection
- ? Modified `main.py` parameter passing
- ? Updated config with `regime_filter: "bear_only"`
- ? Changed default `strategy_type` to "mean_reversion"
- ? Documented implementation

### Status: READY FOR LIVE DEPLOYMENT

**Recommendation:** Start with 5% allocation (current setting) and monitor for 1-2 regime transitions before increasing allocation.

---

**END OF DOCUMENT**
