# Coinalyze API Rate Limiting Implementation

## Overview
Implemented global rate limiting for Coinalyze API calls to respect the 40 calls/minute limit across all parts of the application.

## Changes Made

### 1. Global Rate Limiter (`data/scripts/coinalyze_client.py`)

#### Added GlobalRateLimiter Class
- **Thread-safe**: Uses `threading.Lock()` to coordinate across multiple threads
- **Shared state**: Single global instance `_global_rate_limiter` shared by all `CoinalyzeClient` instances
- **Rate limiting**: Enforces 1.5 seconds between calls (40 calls/min)
- **Call tracking**: Logs every 10th API call to provide visibility

```python
class GlobalRateLimiter:
    """
    Global rate limiter to coordinate API calls across all CoinalyzeClient instances.
    Rate Limit: 40 API calls per minute per API key
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._last_request_time = 0
        self._min_request_interval = 1.5  # 40 calls/min = 1.5s per call
        self._call_count = 0
```

#### Enhanced Retry Logic
- **Automatic retries**: Up to 3 attempts for failed requests
- **429 handling**: Detects rate limit errors and uses exponential backoff (2s, 4s, 8s)
- **Timeout retries**: Automatically retries on timeout errors
- **Retry-After header**: Respects the API's `Retry-After` header when present

### 2. Informative Messages

Added user-facing messages in multiple locations to provide visibility into rate limiting:

#### main.py (line ~887)
```python
print(f"\n  Fetching funding rates from Coinalyze for {len(traded_symbols)} symbols...")
print(f"  Note: Rate limited to 40 calls/min (1.5s between calls)")
```

#### strategies/carry.py (line ~60)
```python
num_symbols = len(universe_symbols)
estimated_time = (num_symbols / 20 + 1) * 1.5  # chunks of 20, 1.5s per call
print(f"  Processing {num_symbols} symbols - Rate limited to 40 calls/min (~{estimated_time:.0f}s total)")
```

#### strategies/open_interest_divergence.py (line ~90)
```python
num_chunks = (len(items) + chunk - 1) // chunk
estimated_time = num_chunks * 1.5
print(f"    Rate limited to 40 calls/min: {num_chunks} API calls required (~{estimated_time:.0f}s total)")
```

## How It Works

### Rate Limiting Flow
1. Any `CoinalyzeClient` instance makes an API call
2. Before the HTTP request, `_rate_limit()` is called
3. The global rate limiter checks time since last request
4. If less than 1.5s has elapsed, the thread sleeps
5. Request proceeds only after minimum interval has passed

### Multiple Client Instances
Even though multiple `CoinalyzeClient` instances may be created throughout the codebase:
- `execution/get_carry.py` (lines 190, 333)
- `execution/strategies/open_interest_divergence.py` (line 61)

They all share the same `_global_rate_limiter`, ensuring coordinated rate limiting across the entire application.

### Chunking Strategy
Coinalyze allows up to 20 symbols per API call. The code chunks symbol requests:
- **20 symbols per call**: Minimizes total API calls
- **Sequential processing**: Chunks processed one at a time with rate limiting
- **Estimated time**: `(num_symbols / 20) * 1.5 seconds`

## Example Usage

### 100 Symbols
- Requires: ~5 API calls (100 / 20 = 5 chunks)
- Time estimate: ~7.5 seconds (5 calls × 1.5s)

### 200 Symbols
- Requires: ~10 API calls
- Time estimate: ~15 seconds

## Error Handling

### Rate Limit Exceeded (429)
```
WARNING: Rate limited (attempt 1/3). Waiting 2s before retry...
```
- Automatic retry with exponential backoff
- Up to 3 attempts before failing

### Timeout
```
ERROR: Request timeout
INFO: Retrying after timeout (attempt 1/3)...
```
- Automatic retry with 2s delay
- Up to 3 attempts

### Logging
Every 10th API call logs progress:
```
INFO: Coinalyze API calls made: 10
INFO: Coinalyze API calls made: 20
```

## Testing

To verify rate limiting is working:

1. Run main.py with carry or oi_divergence strategy
2. Check console output for rate limiting messages
3. Monitor total execution time matches estimates
4. Verify no 429 errors occur

## Benefits

1. **No rate limit errors**: Global coordination prevents exceeding 40/min limit
2. **Automatic retries**: Handles transient failures gracefully  
3. **User visibility**: Clear messages show progress and time estimates
4. **Thread-safe**: Works correctly in multi-threaded environments
5. **Efficient chunking**: Maximizes data per API call (20 symbols)

## Performance Impact

- **Minimum delay**: 1.5 seconds between API calls
- **Scalability**: Linear time increase with number of symbols
- **Predictable**: Users see estimated completion times upfront

## Future Enhancements

Potential improvements:
1. Configurable rate limit (for different API tiers)
2. Request queuing system for concurrent operations
3. Caching layer to reduce API calls for frequently requested data
4. Burst allowance (use unused capacity from previous minute)
