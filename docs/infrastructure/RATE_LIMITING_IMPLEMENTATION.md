# Coinalyze API Rate Limiting Implementation

## Summary
Implemented global rate limiting for Coinalyze API calls in `main.py` and related modules to respect the 40 calls/minute limit.

## Problem
The Coinalyze API has a rate limit of 40 calls per minute. Previously, multiple `CoinalyzeClient` instances were created throughout the codebase without coordinated rate limiting, which could potentially exceed this limit when:
- The carry strategy fetches funding rates for many symbols
- The OI divergence strategy fetches open interest history
- Main.py fetches funding rates for trade allocation breakdown

## Solution

### 1. Global Rate Limiter (data/scripts/coinalyze_client.py)

Added a thread-safe `GlobalRateLimiter` class that coordinates all API calls:

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

**Key Features:**
- **Thread-safe**: Uses `threading.Lock()` for concurrent safety
- **Global coordination**: Single instance shared by all `CoinalyzeClient` instances
- **Enforces 1.5s interval**: 40 calls/min = 1 call per 1.5 seconds
- **Call tracking**: Logs progress every 10 calls

### 2. Enhanced Retry Logic

Improved `_request()` method with automatic retries:

```python
def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 3):
    """Make API request with rate limiting, error handling, and automatic retries"""
```

**Retry Behavior:**
- **429 Rate Limit Errors**: Exponential backoff (2s, 4s, 8s)
- **Timeout Errors**: 2-second delay before retry
- **Max 3 attempts**: Prevents infinite loops
- **Respects Retry-After header**: Uses server-specified wait time when available

### 3. User-Facing Messages

Added informative messages throughout the codebase:

#### execution/main.py (line 887-888)
```python
print(f"\n  Fetching funding rates from Coinalyze for {len(traded_symbols)} symbols...")
print(f"  Note: Rate limited to 40 calls/min (1.5s between calls)")
```

#### execution/strategies/carry.py (line 60-62)
```python
num_symbols = len(universe_symbols)
estimated_time = (num_symbols / 20 + 1) * 1.5
print(f"  Processing {num_symbols} symbols - Rate limited to 40 calls/min (~{estimated_time:.0f}s total)")
```

#### execution/strategies/open_interest_divergence.py (line 88-90)
```python
num_chunks = (len(items) + chunk - 1) // chunk
estimated_time = num_chunks * 1.5
print(f"    Rate limited to 40 calls/min: {num_chunks} API calls required (~{estimated_time:.0f}s total)")
```

## Files Modified

1. **data/scripts/coinalyze_client.py**
   - Added `GlobalRateLimiter` class
   - Modified `CoinalyzeClient` to use global rate limiter
   - Enhanced `_request()` with retry logic

2. **execution/main.py**
   - Added rate limiting message when fetching funding rates (line 887-888)

3. **execution/strategies/carry.py**
   - Added rate limiting message with time estimate (line 60-62)

4. **execution/strategies/open_interest_divergence.py**
   - Added rate limiting message with time estimate (line 88-90)

## How It Works

### Rate Limiting Flow
```
Client Instance 1 → _rate_limit() → GlobalRateLimiter.wait() → Waits if needed → Makes API call
Client Instance 2 → _rate_limit() → GlobalRateLimiter.wait() → Waits if needed → Makes API call
Client Instance N → _rate_limit() → GlobalRateLimiter.wait() → Waits if needed → Makes API call
```

All instances share the same `_global_rate_limiter`, ensuring coordination.

### Timing Examples

**Small Request (20 symbols, 1 API call):**
- Time: ~1.5 seconds

**Medium Request (100 symbols, 5 API calls):**
- Chunks: 100 / 20 = 5 chunks
- Time: ~7.5 seconds (5 calls × 1.5s)

**Large Request (200 symbols, 10 API calls):**
- Chunks: 200 / 20 = 10 chunks  
- Time: ~15 seconds (10 calls × 1.5s)

## Verification

Successfully tested with real API calls:
- ✓ Global rate limiter enforces 1.5s intervals
- ✓ Multiple client instances share rate limiting state
- ✓ Subsequent calls are properly delayed
- ✓ Total execution time matches expectations

Test output:
```
Call 1: Success (took 0.41s)  # First call immediate
Call 2: Success (took 1.22s)  # Waited 1.5s from call 1
Call 3: Success (took 1.50s)  # Waited 1.5s from call 2
Total time: 3.13s             # Expected: 3.0-3.5s
✓ Rate limiting is working correctly!
```

## Benefits

1. **Prevents Rate Limit Errors**: Global coordination prevents exceeding 40/min limit
2. **Automatic Retries**: Handles transient failures and rate limit errors gracefully
3. **User Transparency**: Clear messages show progress and time estimates
4. **Thread-Safe**: Works correctly in multi-threaded environments
5. **Efficient Chunking**: Maximizes data per API call (20 symbols per request)
6. **Predictable Performance**: Users see upfront how long operations will take

## Usage

No code changes required! The rate limiting is automatic:

```python
# Rate limiting happens automatically
from data.scripts.coinalyze_client import CoinalyzeClient

client = CoinalyzeClient()
result = client.get_funding_rate('BTC.H')  # Automatically rate limited
```

Multiple instances share the same rate limiter:

```python
client1 = CoinalyzeClient()
client2 = CoinalyzeClient()

# Both calls use the global rate limiter
result1 = client1.get_funding_rate('BTC.H')    # Call 1: immediate
result2 = client2.get_funding_rate('ETH.H')    # Call 2: waits 1.5s
```

## Performance Impact

- **Per-call delay**: 1.5 seconds minimum between calls
- **Chunking efficiency**: 20 symbols per call (API maximum)
- **Predictable scaling**: Linear time increase with number of symbols

Example for 100-symbol universe:
- API calls needed: ~5 (100 / 20)
- Total time: ~7.5 seconds (5 × 1.5s)
- Rate compliance: 5 calls / 7.5s = 40 calls/min ✓

## Error Handling

### Rate Limit (429)
```
WARNING: Rate limited (attempt 1/3). Waiting 2s before retry...
```
Automatic retry with exponential backoff.

### Timeout
```
ERROR: Request timeout
INFO: Retrying after timeout (attempt 1/3)...
```
Automatic retry after 2-second delay.

### Max Retries Exceeded
```
ERROR: Maximum retry attempts exceeded
```
Operation fails after 3 attempts.

## Future Enhancements

Potential improvements:
1. Configurable rate limit (for different API tier plans)
2. Request queue system for better concurrency
3. Caching layer to reduce duplicate API calls
4. Burst allowance (use unused capacity from previous minute)
5. Priority queue (critical requests get priority)

## Testing

To verify rate limiting in your environment:

```bash
# 1. Set your API key
export COINALYZE_API="your_api_key_here"

# 2. Run main.py with carry or oi_divergence strategy
python3 execution/main.py --signals carry --dry-run

# 3. Watch for rate limiting messages:
#    "Rate limited to 40 calls/min (1.5s between calls)"
#    "Processing N symbols - Rate limited to 40 calls/min (~Xs total)"
```

## Conclusion

The implementation successfully addresses the Coinalyze API rate limit by:
- ✅ Enforcing 40 calls/min limit globally across all code
- ✅ Providing automatic retry with exponential backoff
- ✅ Showing clear progress messages to users
- ✅ Being thread-safe for concurrent operations
- ✅ Maintaining existing API without breaking changes
