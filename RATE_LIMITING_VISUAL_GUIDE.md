# Visual Guide: Rate Limiting in main.py

## How main.py Works with Coinalyze Rate Limiting

### Before Rate Limiting
```
main.py calls carry strategy
  ↓
carry strategy creates CoinalyzeClient #1
  ↓
Fetches 100 symbols (5 API calls) → FAST, NO COORDINATION
  ↓
main.py calls OI divergence strategy  
  ↓
OI strategy creates CoinalyzeClient #2
  ↓
Fetches 50 symbols (3 API calls) → FAST, NO COORDINATION
  ↓
main.py fetches funding rates
  ↓
Creates CoinalyzeClient #3
  ↓
Fetches 20 symbols (1 API call) → FAST, NO COORDINATION

PROBLEM: 9 API calls in ~2 seconds = 270 calls/min >> 40 calls/min limit!
RESULT: 429 Rate Limit Error ❌
```

### After Rate Limiting Implementation
```
main.py calls carry strategy
  ↓
carry strategy creates CoinalyzeClient #1
  ↓                                      ↓
  ↓                           Uses Global Rate Limiter
  ↓                                      ↓
Fetches 100 symbols (5 API calls)       ↓
  Call 1: 0.0s ──────────────────────→ [GLOBAL LIMITER] → ✓ Go (first call)
  Call 2: 1.5s ──────────────────────→ [GLOBAL LIMITER] → Wait 1.5s → ✓ Go
  Call 3: 3.0s ──────────────────────→ [GLOBAL LIMITER] → Wait 1.5s → ✓ Go
  Call 4: 4.5s ──────────────────────→ [GLOBAL LIMITER] → Wait 1.5s → ✓ Go
  Call 5: 6.0s ──────────────────────→ [GLOBAL LIMITER] → Wait 1.5s → ✓ Go
  ↓
main.py calls OI divergence strategy
  ↓
OI strategy creates CoinalyzeClient #2
  ↓                                      ↓
  ↓                      Uses SAME Global Rate Limiter
  ↓                                      ↓
Fetches 50 symbols (3 API calls)        ↓
  Call 6: 7.5s ──────────────────────→ [GLOBAL LIMITER] → Wait 1.5s → ✓ Go
  Call 7: 9.0s ──────────────────────→ [GLOBAL LIMITER] → Wait 1.5s → ✓ Go
  Call 8: 10.5s ─────────────────────→ [GLOBAL LIMITER] → Wait 1.5s → ✓ Go
  ↓
main.py fetches funding rates
  ↓
Creates CoinalyzeClient #3
  ↓                                      ↓
  ↓                      Uses SAME Global Rate Limiter
  ↓                                      ↓
Fetches 20 symbols (1 API call)         ↓
  Call 9: 12.0s ─────────────────────→ [GLOBAL LIMITER] → Wait 1.5s → ✓ Go

RESULT: 9 API calls in ~12 seconds = 45 calls/min ≈ 40 calls/min limit ✓
No rate limit errors! ✓
```

## Code Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         main.py                              │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
   ┌─────────┐      ┌──────────────┐    ┌──────────────┐
   │  Carry  │      │ OI Divergence │    │  Funding     │
   │Strategy │      │   Strategy    │    │  Rates       │
   └─────────┘      └──────────────┘    └──────────────┘
        │                   │                   │
        ▼                   ▼                   ▼
   ┌─────────────────────────────────────────────────┐
   │         CoinalyzeClient Instances               │
   │  (Multiple instances, each in different module) │
   └─────────────────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │    GLOBAL RATE LIMITER             │
        │  (Single shared instance)          │
        │                                    │
        │  • Thread-safe lock                │
        │  • Tracks last request time        │
        │  • Enforces 1.5s interval          │
        │  • Counts total API calls          │
        └────────────────────────────────────┘
                         │
                         ▼
              ┌──────────────────┐
              │  Coinalyze API   │
              │  (40 calls/min)  │
              └──────────────────┘
```

## Timeline Example: 100 Symbols

```
Time    Action                           Status
─────────────────────────────────────────────────────────
0.0s    main.py starts                   
0.1s    Carry strategy activated         ✓ Initialized
0.2s    CoinalyzeClient created          ✓ Connected
0.3s    Fetching 100 symbols...          
0.3s    │ Chunk 1/5 (symbols 1-20)      → API Call 1 ✓ (immediate)
1.8s    │ Chunk 2/5 (symbols 21-40)     → API Call 2 ✓ (waited 1.5s)
3.3s    │ Chunk 3/5 (symbols 41-60)     → API Call 3 ✓ (waited 1.5s)
4.8s    │ Chunk 4/5 (symbols 61-80)     → API Call 4 ✓ (waited 1.5s)
6.3s    │ Chunk 5/5 (symbols 81-100)    → API Call 5 ✓ (waited 1.5s)
6.5s    Carry strategy complete          ✓ 100 symbols processed
6.5s    OI divergence activated          ✓ Initialized
6.6s    CoinalyzeClient created          ✓ Connected
6.7s    Fetching 60 symbols...           
7.8s    │ Chunk 1/3 (symbols 1-20)      → API Call 6 ✓ (waited 1.5s)
9.3s    │ Chunk 2/3 (symbols 21-40)     → API Call 7 ✓ (waited 1.5s)
10.8s   │ Chunk 3/3 (symbols 41-60)     → API Call 8 ✓ (waited 1.5s)
11.0s   OI divergence complete           ✓ 60 symbols processed
11.1s   Fetching funding for trades...   
12.3s   │ Trade allocation (20 symbols)  → API Call 9 ✓ (waited 1.5s)
12.5s   main.py complete                 ✓ All done!

Total: 9 API calls in 12.5 seconds
Rate: 9 / (12.5/60) = 43.2 calls/min ≈ 40 calls/min ✓
```

## User Messages During Execution

```bash
$ python3 execution/main.py --signals carry,oi_divergence --dry-run

================================================================================
AUTOMATED TRADING STRATEGY EXECUTION - MULTI-SIGNAL BLEND (config-driven)
================================================================================

[4/7] Building target positions from selected signals...
--------------------------------------------------------------------------------
Strategy: carry | Allocation: $50,000.00 (50.00%)
  Fetching market-wide funding rates from Coinalyze (using Binance as primary)...
  Processing 100 symbols - Rate limited to 40 calls/min (~8s total)
  
  [Rate limiting in progress...]
  Got funding rates for 95 symbols from Binance (market proxy)
  ...
  
--------------------------------------------------------------------------------
Strategy: oi_divergence | Allocation: $50,000.00 (50.00%)
  Filtering to top 50 symbols by market cap...
    Fetching OI for 50 symbols (exchange=A, days=30)
    Rate limited to 40 calls/min: 3 API calls required (~5s total)
    
    [Rate limiting in progress...]
    Fetched 50 symbols with OI data
    ...

Combined Target Positions (from multi-signal blend):
================================================================================
  BTC/USDC:USDC: LONG $15,234.56
  ETH/USDC:USDC: LONG $12,456.78
  ...

[6/7] Calculating trade amounts (>5% threshold)...

  Fetching funding rates from Coinalyze for 20 symbols...
  Note: Rate limited to 40 calls/min (1.5s between calls)
  
  [Rate limiting in progress...]
  
TRADE ALLOCATION BREAKDOWN BY SIGNAL
--------------------------------------------------------------------------------
...

[7/7] Trade Execution (DRY RUN)
================================================================================
```

## Key Points

### ✅ What This Fixes
- Prevents 429 "Rate Limit Exceeded" errors
- Coordinates all Coinalyze API calls across entire application
- Automatically retries on rate limit errors with backoff
- Shows users clear progress and time estimates

### ✅ How It Works
- Global rate limiter shared by ALL CoinalyzeClient instances
- Thread-safe locking prevents race conditions
- Enforces minimum 1.5 seconds between ANY API calls
- Works automatically - no code changes needed by users

### ✅ Performance
- Predictable: Users see estimated time upfront
- Efficient: 20 symbols per API call (maximum allowed)
- Scalable: Linear increase with number of symbols
- Example: 100 symbols = ~8 seconds total

### ✅ User Experience
```
Before: ❌ Error 429: Rate limit exceeded
After:  ✓ Processing 100 symbols - Rate limited to 40 calls/min (~8s total)
```

Users now see:
1. How many symbols are being processed
2. How long it will take
3. Progress as it happens
4. Clear success/failure messages
