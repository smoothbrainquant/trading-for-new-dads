# Carry Rates Fix - Removed Binance Dependency

## Overview
This document summarizes the changes made to remove Binance dependency from the carry rates code. The system now uses Coinalyze API exclusively to fetch funding rates from multiple exchanges (Bybit, OKX, Hyperliquid) without any reliance on Binance.

## Problem
The carry strategy and funding rate fetching code had multiple dependencies on Binance:
1. Direct CCXT calls to Binance API (geo-restricted in many locations)
2. Aggregated funding rates only queried Binance via Coinalyze
3. Multiple fallback mechanisms that relied on Binance

## Solution
Replaced all Binance dependencies with Coinalyze API calls to multiple exchanges:
- **Bybit (D)**: Large, reliable exchange with good liquidity
- **OKX (K)**: Major exchange with comprehensive perpetual markets
- **Hyperliquid (H)**: Decentralized perpetual DEX

## Files Modified

### 1. `/workspace/execution/get_carry.py`
**Changes:**
- Updated `fetch_coinalyze_aggregated_funding_rates()`:
  - Changed from using only Binance ('A') to using Bybit ('D'), OKX ('K'), and Hyperliquid ('H')
  - Updated aggregation options from `'binance_primary'` to `'bybit_primary'`
  - Updated documentation to reflect new exchange sources

- Updated main function:
  - Replaced Binance-based examples with Coinalyze-based examples
  - Now demonstrates:
    1. Aggregated funding rates across exchanges (recommended)
    2. Exchange-specific rates for Hyperliquid
    3. Exchange-specific rates for Bybit

- Deprecated Binance functions:
  - Added deprecation notices to `fetch_binance_funding_rates()` and `fetch_binance_funding_history()`
  - Functions kept for backward compatibility but marked as deprecated
  - Docstrings updated to recommend Coinalyze alternatives

- Updated `print_funding_summary()`:
  - Changed header from "BINANCE PERPETUAL FUTURES FUNDING RATES" to "PERPETUAL FUTURES FUNDING RATES"

### 2. `/workspace/execution/strategies/carry.py`
**Changes:**
- Updated primary fetch method:
  - Changed message from "using Binance as primary" to "aggregated across exchanges"
  - Updated success message to reflect aggregated data source

- Replaced Binance fallback:
  - Removed direct Binance CCXT calls
  - Replaced with `fetch_coinalyze_funding_rates_for_universe()` for exchange-specific data
  - Added exchange code mapping: `{'hyperliquid': 'H', 'bybit': 'D', 'okx': 'K'}`
  - Defaults to Hyperliquid ('H') if exchange not in mapping

- Updated error messages:
  - Removed references to Binance geo-restrictions
  - Updated troubleshooting to focus on Coinalyze API setup

### 3. `/workspace/execution/main.py`
**Changes:**
- Updated funding rate enrichment (lines ~1300-1339):
  - Primary method now uses `fetch_coinalyze_aggregated_funding_rates()` with mean aggregation
  - Fallback uses exchange-specific Coinalyze API based on `exchange_id`
  - Removed all Binance CCXT fallback code
  - Added proper exchange code mapping for different exchanges

## Benefits

1. **No Geo-Restrictions**: Coinalyze works globally without VPN requirements
2. **More Robust Signals**: Aggregating across multiple exchanges provides more reliable funding rate data
3. **Exchange Flexibility**: Can fetch funding rates for any exchange supported by Coinalyze
4. **Reduced Dependencies**: No longer requires working Binance API access
5. **Better Error Handling**: Graceful fallbacks between aggregated and exchange-specific data

## Usage

### Aggregated Funding Rates (Recommended)
```python
from execution.get_carry import fetch_coinalyze_aggregated_funding_rates

universe = ['BTC/USDC:USDC', 'ETH/USDC:USDC', 'SOL/USDC:USDC']
df = fetch_coinalyze_aggregated_funding_rates(
    universe_symbols=universe,
    aggregation='mean'  # Options: 'mean', 'median', 'bybit_primary'
)
```

### Exchange-Specific Funding Rates
```python
from execution.get_carry import fetch_coinalyze_funding_rates_for_universe

universe = ['BTC/USDC:USDC', 'ETH/USDC:USDC']

# Hyperliquid
df_hl = fetch_coinalyze_funding_rates_for_universe(universe, exchange_code='H')

# Bybit
df_bybit = fetch_coinalyze_funding_rates_for_universe(universe, exchange_code='D')

# OKX
df_okx = fetch_coinalyze_funding_rates_for_universe(universe, exchange_code='K')
```

### Running the Updated Script
```bash
# Set your Coinalyze API key
export COINALYZE_API_KEY="your_api_key_here"

# Run the script
python3 execution/get_carry.py
```

## Exchange Codes Reference
- **H**: Hyperliquid (decentralized perpetual DEX)
- **D**: Bybit (centralized exchange)
- **K**: OKX (centralized exchange)
- **A**: Binance (deprecated - no longer used)

## Migration Notes

### For Existing Code
1. Replace any direct calls to `fetch_binance_funding_rates()` with `fetch_coinalyze_aggregated_funding_rates()`
2. The aggregated function returns data in the same format with columns: `base`, `quote`, `funding_rate`, `funding_rate_pct`, `num_exchanges`
3. Ensure `COINALYZE_API_KEY` environment variable is set

### Backward Compatibility
- Binance functions are still available but deprecated
- They will continue to work but are not recommended for new code
- Consider them legacy code that may be removed in future versions

## Testing
To verify the changes work correctly:

1. Ensure Coinalyze API key is set:
   ```bash
   export COINALYZE_API_KEY="your_key"
   ```

2. Test aggregated funding rates:
   ```bash
   python3 execution/get_carry.py
   ```

3. Test carry strategy (requires full setup):
   ```bash
   python3 execution/main.py
   ```

## Dependencies
- `data.scripts.coinalyze_client`: Coinalyze API client
- `data.scripts.coinalyze_cache`: Caching layer for rate limiting
- Environment variable: `COINALYZE_API_KEY`

## Notes
- Rate limiting: Coinalyze API is limited to 40 calls/min with 1.5s between calls
- Caching: The system uses 8-hour cache TTL for funding rates
- The aggregated approach is recommended as it provides more robust market-wide signals
- Exchange-specific rates should only be used when trading on that specific exchange

## Summary
All Binance dependencies have been successfully removed from the carry rates code. The system now exclusively uses Coinalyze API to aggregate funding rates from multiple major exchanges (Bybit, OKX, Hyperliquid), providing more robust and globally accessible funding rate data.
