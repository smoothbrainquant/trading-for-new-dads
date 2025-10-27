# Coinalyze Aggregate Format Implementation

## Date: 2025-10-27

## Overview
Updated OI data fetching to use Coinalyze aggregate format per their API documentation. This provides more robust signals by aggregating OI data across ALL exchanges.

## Coinalyze API Specification

### Get Open Interest History

**Endpoint**: GET `/open-interest/history`

**Query Parameters**:
- `symbols` (required): Comma-separated list, max 20 symbols per request
  - Format: `BTCUSDT_PERP.A,ETHUSDT_PERP.A`
  - Each symbol consumes one API call
- `interval` (required): Time granularity
  - Options: `"1min"`, `"5min"`, `"15min"`, `"30min"`, `"1hour"`, `"2hour"`, `"4hour"`, `"6hour"`, `"12hour"`, `"daily"`
  - We use: `"daily"`
- `from` (required): Start timestamp (inclusive), UNIX seconds
- `to` (required): End timestamp (inclusive), UNIX seconds
- `convert_to_usd`: Convert to USD
  - Options: `"true"`, `"false"`
  - We use: `"true"`

## Symbol Format

### Aggregate Format (RECOMMENDED)
```
[SYMBOL]USDT_PERP.A
```

**Examples**:
- `BTCUSDT_PERP.A` - Bitcoin aggregate OI across all exchanges
- `ETHUSDT_PERP.A` - Ethereum aggregate OI across all exchanges
- `SOLUSDT_PERP.A` - Solana aggregate OI across all exchanges

**Benefits**:
- ✅ Aggregates OI data from all supported exchanges
- ✅ More robust signals (not dependent on single exchange)
- ✅ Reduces exchange-specific noise
- ✅ Better represents overall market sentiment

### Exchange-Specific Formats

**Hyperliquid**:
```
[SYMBOL].H
```
Example: `BTC.H`

**Binance**:
```
[SYMBOL]USDT_PERP.A
```
Example: `BTCUSDT_PERP.A`

**Other exchanges**: Follow similar patterns with exchange code suffix

## Implementation

### Symbol Building Function

```python
def _build_coinalyze_symbol(base: str, quote: str = 'USDT', exchange_code: str = 'A') -> str:
    """
    Build Coinalyze symbol. Default format uses aggregate data across all exchanges.
    
    Formats by exchange:
    - Aggregate (A): {BASE}USDT_PERP.A (e.g., BTCUSDT_PERP.A) - RECOMMENDED
    - Hyperliquid (H): {BASE}.H  (e.g., BTC.H)
    - Other: {BASE}{QUOTE}_PERP.{exchange_code}
    """
    if exchange_code == 'A':
        # Aggregate format: always use USDT
        return f"{base}USDT_PERP.A"
    elif exchange_code == 'H':
        return f"{base}.{exchange_code}"
    else:
        return f"{base}{quote}_PERP.{exchange_code}"
```

### API Call

```python
data = client.get_open_interest_history(
    symbols='BTCUSDT_PERP.A,ETHUSDT_PERP.A,SOLUSDT_PERP.A',
    interval='daily',
    from_ts=start_timestamp,
    to_ts=end_timestamp,
    convert_to_usd=True,
)
```

### Configuration

**In `all_strategies_config.json`**:
```json
{
  "strategy_weights": {
    "oi_divergence": 0.2
  },
  "params": {
    "oi_divergence": {
      "mode": "trend",
      "lookback": 30,
      "top_n": 10,
      "bottom_n": 10,
      "exchange_code": "A"
    }
  }
}
```

**Exchange Code Options**:
- `"A"` - Aggregate (all exchanges) - **RECOMMENDED**
- `"H"` - Hyperliquid only
- Other exchange codes as per Coinalyze documentation

## Usage Examples

### Example 1: Fetch Aggregate OI Data
```python
from execution.strategies.open_interest_divergence import _fetch_oi_history_for_universe

# Uses aggregate format by default
oi_df = _fetch_oi_history_for_universe(
    universe_symbols=['BTC/USDC:USDC', 'ETH/USDC:USDC'],
    exchange_code='A',  # Aggregate across all exchanges
    days=200
)

# Generates API calls for:
# - BTCUSDT_PERP.A
# - ETHUSDT_PERP.A
```

### Example 2: Strategy with Aggregate OI
```python
from execution.strategies import strategy_oi_divergence

positions = strategy_oi_divergence(
    historical_data=price_data,
    notional=100000,
    mode='trend',
    lookback=30,
    top_n=10,
    bottom_n=10,
    exchange_code='A'  # Use aggregate
)
```

### Example 3: Main Script Execution
```bash
# Uses config with exchange_code='A'
python3 execution/main.py \
    --signal-config execution/all_strategies_config.json \
    --dry-run
```

## API Call Batching

The implementation automatically batches symbols to respect Coinalyze limits:

```python
# Maximum 20 symbols per request
chunk_size = 20

# For 45 symbols, makes 3 API calls:
# Call 1: symbols 1-20
# Call 2: symbols 21-40  
# Call 3: symbols 41-45

# Rate limited to 40 calls/min (1.5s between calls)
```

## Data Format

### Request Example
```
GET /open-interest/history?symbols=BTCUSDT_PERP.A,ETHUSDT_PERP.A&interval=daily&from=1640000000&to=1672500000&convert_to_usd=true
```

### Response Format
```json
[
  {
    "symbol": "BTCUSDT_PERP.A",
    "history": [
      {
        "t": 1640000000,  // timestamp
        "o": 12500000000, // open OI (USD)
        "h": 13000000000, // high OI (USD)
        "l": 12300000000, // low OI (USD)
        "c": 12800000000  // close OI (USD)
      },
      ...
    ]
  },
  {
    "symbol": "ETHUSDT_PERP.A",
    "history": [...]
  }
]
```

### Processed DataFrame Columns
```python
['coin_symbol', 'coinalyze_symbol', 'date', 'oi_close']
```

Example:
```
coin_symbol  coinalyze_symbol     date        oi_close
BTC          BTCUSDT_PERP.A      2025-01-15  12800000000
ETH          ETHUSDT_PERP.A      2025-01-15  5600000000
```

## Files Modified

### 1. `execution/strategies/open_interest_divergence.py`
**Changes**:
- Updated `_build_coinalyze_symbol()` to default to aggregate format
- Changed default `exchange_code='A'` (was 'H')
- Added format documentation in docstrings
- Added logging for exchange format being used

### 2. `execution/main.py`
**Changes**:
- Updated config example to show `exchange_code: "A"`
- Changed default from 'H' to 'A' in strategy execution
- Added comment explaining aggregate format

### 3. `execution/all_strategies_config.json`
**Changes**:
- Changed `exchange_code` from `"H"` to `"A"`

## Testing

### Run Format Test
```bash
python3 test_coinalyze_format.py
```

**Expected Output**:
```
✅ ALL TESTS PASSED

Format is correct per Coinalyze API documentation.
Aggregate format (BTCUSDT_PERP.A) provides OI data across all exchanges.
```

### Verify Strategy Output
```bash
python3 execution/main.py --signal-config execution/all_strategies_config.json --dry-run
```

**Look for**:
```
Using aggregated OI data (aggregate (all exchanges))
Format: [SYMBOL]USDT_PERP.A (e.g., BTCUSDT_PERP.A)
```

## Benefits of Aggregate Format

### 1. Robustness
- Not dependent on single exchange
- Continues working if one exchange goes down
- Represents broader market sentiment

### 2. Signal Quality
- Reduces exchange-specific noise
- Better represents overall market OI trends
- Less susceptible to manipulation on single exchange

### 3. Data Availability
- More comprehensive data coverage
- Better for smaller coins (might only trade on some exchanges)
- Historical data more complete

### 4. Simplicity
- Single format for all symbols
- No need to specify which exchange per symbol
- Easier configuration

## Comparison: Aggregate vs Exchange-Specific

### Aggregate (A) - RECOMMENDED
```python
exchange_code='A'
# BTC -> BTCUSDT_PERP.A (all exchanges)
# ETH -> ETHUSDT_PERP.A (all exchanges)
```

**Pros**:
- ✅ Most robust signals
- ✅ Comprehensive market view
- ✅ Less noise
- ✅ Default choice

**Cons**:
- ⚠️ May lag single-exchange moves
- ⚠️ Can't trade exchange-specific arbitrage

### Hyperliquid (H)
```python
exchange_code='H'
# BTC -> BTC.H (Hyperliquid only)
# ETH -> ETH.H (Hyperliquid only)
```

**Pros**:
- ✅ Specific to trading venue
- ✅ No lag from aggregation

**Cons**:
- ⚠️ Single point of failure
- ⚠️ More noise
- ⚠️ Exchange-specific anomalies

## Migration Guide

### Updating from Exchange-Specific to Aggregate

**Before (Hyperliquid-specific)**:
```json
{
  "oi_divergence": {
    "exchange_code": "H"
  }
}
```

**After (Aggregate)**:
```json
{
  "oi_divergence": {
    "exchange_code": "A"
  }
}
```

**Impact**:
- ✅ Signals become more robust
- ✅ Better represents overall market
- ⚠️ May see different positions (expected)
- ⚠️ Need to refresh OI data with new format

### Refresh Data with New Format

```bash
# Run data collection with aggregate format
python3 data/scripts/fetch_all_open_interest_since_2020_all_perps.py

# Verify format
head data/raw/historical_open_interest_all_perps_since2020_*.csv
# Should see: BTCUSDT_PERP.A, ETHUSDT_PERP.A, etc.
```

## Performance

### API Efficiency
- **Before**: 1 call per symbol per exchange
- **After**: 1 call per symbol (aggregated)
- **Savings**: Significant reduction in API calls

### Example
For 50 symbols:
- Exchange-specific: 50 calls × N exchanges
- Aggregate: 50 calls total (3 batches of 20)

### Rate Limiting
- Coinalyze limit: 40 calls/minute
- Our implementation: 1.5s between batches
- For 100 symbols: ~8 seconds total (5 batches)

## Troubleshooting

### Issue: "Symbol not found"
**Cause**: Coin might not have aggregate data
**Solution**: Try exchange-specific format or check Coinalyze supported symbols

### Issue: Data differs from single exchange
**Expected**: Aggregate data represents sum across all exchanges
**Solution**: This is normal and provides better signals

### Issue: Missing historical data
**Cause**: Coin might not have been on all exchanges historically
**Solution**: Acceptable - aggregate will include available exchanges

## Best Practices

1. **Always use aggregate format ('A')** unless you have specific reason for single exchange
2. **Refresh data regularly** to get latest aggregate OI
3. **Monitor data quality** - check that symbols have sufficient history
4. **Document exchange code** in config comments for clarity
5. **Test with small universe** before running on full symbol list

## References

- Coinalyze API Documentation: [API docs]
- Symbol format specification: `[SYMBOL]USDT_PERP.A` for aggregate
- Interval: `'daily'` for daily OHLC
- Conversion: `convert_to_usd=True` for USD values

## Conclusion

✅ **Implementation Complete**

The system now uses Coinalyze aggregate format (`[SYMBOL]USDT_PERP.A`) by default:
- More robust signals across all exchanges
- Follows Coinalyze API documentation exactly
- Uses 'daily' interval with USD conversion
- Properly batches up to 20 symbols per request

This provides better quality signals for the OI divergence strategy by representing overall market sentiment rather than single-exchange behavior.
