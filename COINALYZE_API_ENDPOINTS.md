# Coinalyze API Endpoints Documentation

## Base Information
- **Base URL**: `https://api.coinalyze.net/v1`
- **Authentication**: API key passed in header as `api_key`
- **Rate Limiting**: Yes - "Too Many Requests" error (429) when exceeded
- **Response Format**: JSON

## Discovered Endpoints

### 1. Exchanges (✓ Working)
**Endpoint**: `GET /exchanges`

**Description**: Returns list of all supported exchanges

**Parameters**: None required

**Response**: Array of exchange objects
```json
[
  {
    "code": "A",
    "name": "Binance"
  },
  {
    "code": "6",
    "name": "Bybit"
  }
]
```

**Exchange Codes**:
- `A` - Binance
- `0` - BitMEX
- `2` - Deribit
- `3` - OKX
- `4` - Huobi
- `6` - Bybit
- `7` - Phemex
- `8` - dYdX
- `B` - Bitstamp
- `C` - Coinbase
- `D` - Bitforex
- `E` - MercadoBitcoin
- `F` - Bitfinex
- `G` - Gemini
- `H` - Hyperliquid
- `I` - Bit2c
- `J` - Luno
- `K` - Kraken
- `L` - BitFlyer
- `M` - BtcMarkets
- `N` - Independent Reserve
- `P` - Poloniex
- `U` - Bithumb
- `V` - Vertex
- `W` - WOO X
- `Y` - Gate.io

**Example**:
```bash
curl -H "api_key: YOUR_API_KEY" "https://api.coinalyze.net/v1/exchanges"
```

---

### 2. Open Interest (Partial)
**Endpoint**: `GET /open-interest`

**Description**: Get open interest data for cryptocurrency futures

**Parameters**:
- `symbols` (required): Comma-separated list of symbols

**Response**: Array of open interest data (format TBD - returned empty in tests)

**Notes**: 
- Endpoint exists and accepts requests
- Returns 400 error if `symbols` parameter is missing
- Returns empty array for tested symbols (BTCUSDT, BTC, A_BTCUSDT, etc.)
- Correct symbol format unknown - may require specific exchange prefix or different naming

**Example**:
```bash
curl -H "api_key: YOUR_API_KEY" "https://api.coinalyze.net/v1/open-interest?symbols=BTCUSDT"
```

---

### 3. Funding Rate (Partial)
**Endpoint**: `GET /funding-rate`

**Description**: Get funding rate data for cryptocurrency perpetual futures

**Parameters**:
- `symbols` (required): Comma-separated list of symbols

**Response**: Array of funding rate data (format TBD - returned empty in tests)

**Notes**: 
- Endpoint exists and accepts requests
- Returns 400 error if `symbols` parameter is missing
- Returns empty array for tested symbols
- Correct symbol format unknown

**Example**:
```bash
curl -H "api_key: YOUR_API_KEY" "https://api.coinalyze.net/v1/funding-rate?symbols=BTCUSDT"
```

---

## Endpoints Not Found (404)

The following endpoints were tested but returned 404 errors:

### Symbol/Market Listing
- `/symbols`
- `/markets`
- `/pairs`
- `/symbols-list`
- `/available-pairs`
- `/instruments`
- `/contracts`
- `/perpetuals`
- `/futures-list`
- `/coins`
- `/futures`
- `/futures/symbols`
- `/futures/markets`
- `/futures/exchanges`

### Historical Data
- `/open-interest/history`
- `/funding-rate/history`
- `/open-interest/symbols`
- `/funding-rate/symbols`
- `/historical`
- `/historical/open-interest`
- `/historical/funding-rate`
- `/historical/liquidations`
- `/history`

### Liquidations
- `/liquidation`
- `/liquidations`
- `/liquidations/symbols`
- `/liquidations/history`

### Volume & Aggregated Data
- `/volume`
- `/volume/symbols`
- `/aggregated-open-interest`
- `/aggregated-funding-rate`
- `/total-open-interest`

### Market Data
- `/ticker`
- `/tickers`
- `/market-data`
- `/price`
- `/prices`
- `/quotes`
- `/orderbook`
- `/trades`
- `/ohlcv`

### Long/Short Ratios
- `/long-short-ratio`
- `/long-short-ratio/symbols`

### Other
- `/info`
- `/help`
- `/status`
- `/dominance`
- `/top-gainers`
- `/top-losers`
- `/market-overview`
- `/statistics`
- `/futures-data`

---

## API Rate Limits

The API implements rate limiting:
- Status Code: `429`
- Response: `{"message":"Too Many Requests. See the \"Retry-After\" header."}`
- Recommendation: Add delays between requests (2-3 seconds minimum)

---

## Usage Recommendations

1. **Always check for rate limiting**: Implement retry logic with exponential backoff
2. **Symbol format unknown**: The correct symbol format for data endpoints needs clarification
3. **Use `/exchanges` endpoint**: This is the most reliable endpoint for getting exchange information
4. **Contact Coinalyze support**: For official documentation on:
   - Correct symbol formats
   - Available data endpoints
   - Historical data access
   - Subscription tier limitations

---

## Python Example

```python
import os
import requests
import time

API_KEY = os.environ.get('COINALYZE_API')
BASE_URL = "https://api.coinalyze.net/v1"

def get_exchanges():
    """Get list of all supported exchanges"""
    url = f"{BASE_URL}/exchanges"
    headers = {'api_key': API_KEY}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

def get_open_interest(symbols):
    """
    Get open interest data
    
    Args:
        symbols: Comma-separated string of symbols (format unknown)
    """
    url = f"{BASE_URL}/open-interest"
    headers = {'api_key': API_KEY}
    params = {'symbols': symbols}
    
    response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

# Example usage
exchanges = get_exchanges()
print(f"Found {len(exchanges)} exchanges")

time.sleep(2)  # Rate limiting

# Note: Symbol format needs to be determined
oi_data = get_open_interest("BTCUSDT")
print(f"Open interest data: {oi_data}")
```

---

## Status Summary

✅ **Working**: 
- `/exchanges` - Fully functional

⚠️ **Partially Working**: 
- `/open-interest` - Endpoint exists but returns empty data
- `/funding-rate` - Endpoint exists but returns empty data

❌ **Not Found**: 
- Most other typical crypto API endpoints (see list above)

---

## Next Steps

To fully utilize this API, you should:

1. Check official Coinalyze documentation or contact support for:
   - Complete endpoint list
   - Correct symbol format and naming conventions
   - Available historical data endpoints
   - Subscription tier features

2. Verify if your API key has the necessary permissions for data access

3. Determine if there's a separate endpoint to list available symbols/pairs
