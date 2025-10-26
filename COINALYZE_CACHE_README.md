# Coinalyze Data Caching

## Overview

The Coinalyze cache system significantly speeds up strategy execution by caching API responses locally. This is especially important because:

1. **Rate Limiting**: Coinalyze API is rate-limited to 40 calls/min (1.5s between calls)
2. **Slow Data Fetching**: Fetching data for 150+ symbols can take 5-10 minutes
3. **Repeated Runs**: Testing and development require multiple runs with the same data

## How It Works

### Cache Location
- **Directory**: `/workspace/data/.cache/coinalyze/`
- **Format**: JSON files with timestamp metadata
- **Auto-created**: Cache directory is created automatically on first use

### Cache Files
- `funding_rates_aggregated.json` - Aggregated funding rates across exchanges
- `funding_rates_H.json` - Hyperliquid funding rates
- `funding_rates_A.json` - Binance funding rates
- `oi_history_H_days200.json` - OI history for Hyperliquid (200 days)
- `oi_history_A_days200.json` - OI history for Binance (200 days)

### Time-To-Live (TTL)
- **Funding Rates**: 1 hour (current market data changes frequently)
- **OI History**: 6 hours (historical data is more stable)

Cache is automatically refreshed when expired.

## Usage

### Automatic Caching (Default)
The strategies automatically use caching when you run `main.py`:

```bash
# First run - fetches from API and caches (slow)
python3 execution/main.py --signal-config execution/all_strategies_config.json --dry-run

# Second run within TTL - uses cache (fast!)
python3 execution/main.py --signal-config execution/all_strategies_config.json --dry-run
```

### Manual Cache Management

#### View Cache Status
```bash
python3 data/scripts/manage_coinalyze_cache.py info
```

Output example:
```
================================================================================
COINALYZE CACHE INFORMATION
================================================================================

Cache directory: /workspace/data/.cache/coinalyze
TTL: 1 hours

Total files: 2
Valid: 2
Expired: 0

--------------------------------------------------------------------------------
Status     File                                     Size       Age (hrs)   
--------------------------------------------------------------------------------
✓ VALID    funding_rates_aggregated.json            45.2 KB         0.12
✓ VALID    oi_history_A_days200.json               128.5 KB         0.45
================================================================================
```

#### Pre-populate Cache
Pre-fetch data before running strategies (useful for development):

```bash
python3 data/scripts/manage_coinalyze_cache.py populate
```

This will:
1. Fetch top 100 symbols by volume
2. Cache aggregated funding rates
3. Skip OI history (not available for Hyperliquid)

#### Clear Cache
```bash
# Clear all cache
python3 data/scripts/manage_coinalyze_cache.py clear

# Clear only funding rates
python3 data/scripts/manage_coinalyze_cache.py clear funding

# Clear only OI history
python3 data/scripts/manage_coinalyze_cache.py clear oi
```

## Performance Impact

### Before Caching
```
First run: ~6-10 minutes (API rate limiting)
- Fetching 157 symbols with 1.5s between calls
- Multiple API endpoints (funding rates, OI history)
```

### After Caching
```
First run:  ~6-10 minutes (API fetch + cache save)
Second run: ~30-60 seconds (cache hit)

Speed improvement: 10-20x faster!
```

## Important Notes

### Hyperliquid Limitations
⚠️ **Open Interest history is NOT available for Hyperliquid via Coinalyze**

The `oi_divergence` strategy will:
- Print a warning when using `exchange_code='H'`
- Return no positions
- Recommend using `exchange_code='A'` (Binance) instead

### Cache Invalidation
Cache is automatically invalidated when:
- TTL expires (1 hour for funding, 6 hours for OI)
- Manual clear command is run
- Cache file is corrupted/unreadable

### API Key Required
You must have `COINALYZE_API` environment variable set:

```bash
export COINALYZE_API="your-api-key-here"
```

Get your API key from: https://coinalyze.net/

## Integration with Strategies

### Carry Strategy
Uses cached aggregated funding rates:
```python
from data.scripts.coinalyze_cache import fetch_coinalyze_aggregated_funding_cached

df_rates = fetch_coinalyze_aggregated_funding_cached(
    universe_symbols=universe_symbols,
    cache_ttl_hours=1,
)
```

### OI Divergence Strategy
Uses cached OI history:
```python
from data.scripts.coinalyze_cache import fetch_oi_history_cached

oi_df = fetch_oi_history_cached(
    universe_symbols=universe_symbols,
    exchange_code='A',  # Use Binance, not Hyperliquid
    days=200,
    cache_ttl_hours=6,
)
```

## Troubleshooting

### Cache Not Working
1. Check cache directory exists: `ls -la /workspace/data/.cache/coinalyze/`
2. Check file permissions
3. Check disk space
4. View logs for error messages

### Stale Data
If you need fresh data immediately:
```bash
# Force refresh by clearing cache
python3 data/scripts/manage_coinalyze_cache.py clear

# Then run strategies
python3 execution/main.py --signal-config execution/all_strategies_config.json --dry-run
```

### API Errors
If API calls fail:
1. Check `COINALYZE_API` environment variable
2. Verify API key is valid
3. Check rate limits (40 calls/min)
4. Cache will preserve last successful fetch if API is down

## Development Tips

### Testing with Cache
```bash
# Populate cache once
python3 data/scripts/manage_coinalyze_cache.py populate

# Now you can iterate quickly
python3 execution/main.py --dry-run  # Fast!
python3 execution/main.py --dry-run  # Fast!
python3 execution/main.py --dry-run  # Fast!
```

### Debugging Cache Issues
```python
from data.scripts.coinalyze_cache import CoinalyzeCache

cache = CoinalyzeCache()
info = cache.get_cache_info()
print(info)
```

## Summary

✅ **Automatic caching** - No code changes needed
✅ **Significant speedup** - 10-20x faster on cache hits
✅ **Smart TTLs** - Current data (1h) vs historical (6h)
✅ **Easy management** - Simple CLI for cache operations
✅ **Fallback support** - Auto-fetch on cache miss

The caching system makes development and testing much more efficient while respecting API rate limits!
