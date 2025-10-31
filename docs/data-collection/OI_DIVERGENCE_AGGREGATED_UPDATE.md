# OI Divergence Strategy: Aggregated Data Update

## Summary

Updated the OI Divergence strategy in `main.py` to use **aggregated Open Interest data** from local files instead of exchange-specific data from the Coinalyze API. This change makes the strategy more robust, faster, and exchange-agnostic.

## Changes Made

### 1. Modified Strategy Implementation
**File**: `execution/strategies/open_interest_divergence.py`

- **Added**: `_load_aggregated_oi_from_file()` function
  - Loads pre-downloaded aggregated OI data from CSV files
  - Automatically finds the latest `historical_open_interest_all_perps_since2020_*.csv` file
  - Filters data to relevant universe symbols and date range
  
- **Updated**: `strategy_oi_divergence()` function
  - Now uses aggregated OI data by default
  - `exchange_code` parameter is now ignored (kept for backward compatibility)
  - No longer makes Coinalyze API calls during execution
  - Updated docstring to reflect aggregated data usage

### 2. Updated Configuration
**File**: `execution/all_strategies_config.json`

- Added comment clarifying that `exchange_code` parameter is ignored
- Strategy now uses aggregated OI data from all exchanges

### 3. Updated Documentation
**File**: `execution/main.py`

- Updated example configuration to note that exchange_code is ignored for OI divergence

## Why This Change?

### Problem
- Coinalyze does **NOT** provide Open Interest data for Hyperliquid exchange (code 'H')
- Previous implementation would fail when trying to fetch Hyperliquid OI data
- Exchange-specific OI data required slow API calls with rate limiting

### Solution
- Use **aggregated OI data** across all exchanges (Binance, Bybit, OKX, etc.)
- Data is pre-downloaded and stored locally as CSV files
- Provides **more robust signals** by combining OI from multiple exchanges
- **Much faster** - no API calls during strategy execution
- **Exchange-agnostic** - signal is based on overall market OI, not specific exchange

## Benefits

1. **Faster Execution**: No API rate limits during live trading
2. **More Robust Signals**: Aggregated OI across exchanges provides better market picture
3. **Reliable**: No dependency on live API availability
4. **Historical Consistency**: Same data source for backtesting and live trading

## Data Source

The strategy now uses:
```
data/raw/historical_open_interest_all_perps_since2020_YYYYMMDD_HHMMSS.csv
```

This file contains:
- Aggregated OI data from major exchanges (Binance, Bybit, OKX, etc.)
- Daily OI values in USD
- Coverage: 100+ symbols since 2020
- Automatically prioritizes Binance data (exchange code 'A')

## Testing

Tested successfully:
- ✅ Aggregated OI data loading from file
- ✅ Strategy execution with aggregated data
- ✅ Integration with main.py execution flow
- ✅ Backward compatibility (exchange_code parameter accepted but ignored)

## Usage

No changes required in configuration or execution! The strategy automatically uses aggregated data:

```python
# Configuration (exchange_code is now ignored)
{
  "oi_divergence": {
    "mode": "divergence",
    "lookback": 30,
    "top_n": 10,
    "bottom_n": 10,
    "exchange_code": "H"  # Ignored - uses aggregated data
  }
}
```

```bash
# Execute with OI divergence strategy
python3 execution/main.py --signal-config execution/all_strategies_config.json --dry-run
```

## Migration Notes

- No action required for existing configurations
- `exchange_code` parameter is kept for backward compatibility but is no longer used
- Strategy will automatically find and use the most recent aggregated OI data file
- If aggregated OI file is missing, strategy will print clear error message

## Related Files

- Core implementation: `execution/strategies/open_interest_divergence.py`
- Configuration: `execution/all_strategies_config.json`
- Main execution: `execution/main.py`
- Documentation: `docs/OI_DIVERGENCE_SIGNALS_README.md`
- Data file: `data/raw/historical_open_interest_all_perps_since2020_*.csv`

## Conclusion

The OI Divergence strategy now uses aggregated Open Interest data from all exchanges, making it more robust, faster, and suitable for live trading on any exchange (including Hyperliquid). This resolves the issue where Coinalyze doesn't provide Hyperliquid-specific OI data, and provides better signals by using market-wide OI aggregates.
