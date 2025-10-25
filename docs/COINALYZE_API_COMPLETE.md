# Coinalyze API - Complete Documentation

## 🎉 All Endpoints Working!

Based on the official API documentation, all endpoints are now accessible with the correct symbol formats.

---

## 📊 API Overview

- **Base URL**: `https://api.coinalyze.net/v1`
- **Authentication**: Header `api_key: YOUR_KEY`
- **Rate Limit**: 40 API calls per minute per API key
- **Response Format**: JSON
- **Historical Data**: Returned in ascending order
- **Data Retention**: 
  - Intraday (1min - 12hour): 1500-2000 datapoints
  - Daily: All historical data retained

---

## 🔑 Symbol Format

### Futures (Perpetuals)
Format: `{BASE}{QUOTE}_PERP.{EXCHANGE_CODE}`

Examples:
- `BTCUSDT_PERP.A` - Binance BTC/USDT Perpetual
- `ETHUSDT_PERP.6` - Bybit ETH/USDT Perpetual
- `BTCUSD_PERP.0` - BitMEX BTC/USD Perpetual

### Futures (Dated)
Format: `{BASE}{QUOTE}.{EXCHANGE_CODE}`

Examples:
- `BTCUSDT.6` - Bybit BTC/USDT Future
- `MNTUSDT.6` - Bybit MNT/USDT Future

### Spot
Format: `{BASE}{QUOTE}.{EXCHANGE_CODE}`

Examples:
- `BTCUSD.C` - Coinbase BTC/USD Spot
- `ETHUSDT.A` - Binance ETH/USDT Spot

---

## 📍 All Available Endpoints

### 1. Get Exchanges ✅
```http
GET /exchanges
```

**Response:**
```json
[
  {
    "name": "Binance",
    "code": "A"
  }
]
```

**Stats**: 26 exchanges supported

---

### 2. Get Future Markets ✅
```http
GET /future-markets
```

**Response:**
```json
[
  {
    "symbol": "BTCUSDT_PERP.A",
    "exchange": "A",
    "symbol_on_exchange": "BTCUSDT",
    "base_asset": "BTC",
    "quote_asset": "USDT",
    "is_perpetual": true,
    "margined": "STABLE",
    "expire_at": null,
    "oi_lq_vol_denominated_in": "BASE_ASSET",
    "has_long_short_ratio_data": true,
    "has_ohlcv_data": true,
    "has_buy_sell_data": true
  }
]
```

**Stats**: 3,739 future markets available

---

### 3. Get Spot Markets ✅
```http
GET /spot-markets
```

**Response:**
```json
[
  {
    "symbol": "BTCUSD.C",
    "exchange": "C",
    "symbol_on_exchange": "BTC-USD",
    "base_asset": "BTC",
    "quote_asset": "USD",
    "has_buy_sell_data": true
  }
]
```

**Stats**: 6,839 spot markets available

---

### 4. Get Current Open Interest ✅
```http
GET /open-interest?symbols=BTCUSDT_PERP.A,ETHUSDT_PERP.A&convert_to_usd=false
```

**Parameters:**
- `symbols` (required): Comma-separated, max 20 symbols, each consumes one API call
- `convert_to_usd` (optional): "true" or "false" (default: "false")

**Response:**
```json
[
  {
    "symbol": "BTCUSDT_PERP.A",
    "value": 123456.78,
    "update": 1761391038435
  }
]
```

---

### 5. Get Current Funding Rate ✅
```http
GET /funding-rate?symbols=BTCUSDT_PERP.A,ETHUSDT_PERP.A
```

**Parameters:**
- `symbols` (required): Comma-separated, max 20 symbols

**Response:**
```json
[
  {
    "symbol": "BTCUSDT_PERP.A",
    "value": 0.0001,
    "update": 1761391039753
  }
]
```

---

### 6. Get Current Predicted Funding Rate ✅
```http
GET /predicted-funding-rate?symbols=BTCUSDT_PERP.A
```

**Parameters:**
- `symbols` (required): Comma-separated, max 20 symbols

**Response:**
```json
[
  {
    "symbol": "BTCUSDT_PERP.A",
    "value": 0.0001,
    "update": 1761391039753
  }
]
```

---

### 7. Get Open Interest History ✅
```http
GET /open-interest-history?symbols=BTCUSDT_PERP.A&interval=daily&from=1760000000&to=1761400000&convert_to_usd=false
```

**Parameters:**
- `symbols` (required): Comma-separated, max 20 symbols
- `interval` (required): "1min", "5min", "15min", "30min", "1hour", "2hour", "4hour", "6hour", "12hour", "daily"
- `from` (required): UNIX timestamp in seconds (inclusive)
- `to` (required): UNIX timestamp in seconds (inclusive)
- `convert_to_usd` (optional): "true" or "false"

**Response:**
```json
[
  {
    "symbol": "BTCUSDT_PERP.A",
    "history": [
      {
        "t": 1760000000,
        "o": 100000.5,
        "h": 105000.0,
        "l": 99000.0,
        "c": 103000.0
      }
    ]
  }
]
```

**Format**: Each history entry contains `t` (timestamp), `o` (open), `h` (high), `l` (low), `c` (close)

---

### 8. Get Funding Rate History ✅
```http
GET /funding-rate-history?symbols=BTCUSDT_PERP.A&interval=1hour&from=1760000000&to=1761400000
```

**Parameters:** Same as open interest history (except no convert_to_usd)

---

### 9. Get Predicted Funding Rate History ✅
```http
GET /predicted-funding-rate-history?symbols=BTCUSDT_PERP.A&interval=1hour&from=1760000000&to=1761400000
```

**Parameters:** Same as funding rate history

---

### 10. Get Liquidation History ✅
```http
GET /liquidation-history?symbols=BTCUSDT_PERP.A&interval=1hour&from=1760000000&to=1761400000&convert_to_usd=false
```

**Parameters:** Same as open interest history

---

### 11. Get Long/Short Ratio History ✅
```http
GET /long-short-ratio-history?symbols=BTCUSDT_PERP.A&interval=1hour&from=1760000000&to=1761400000
```

**Parameters:** Same as funding rate history

---

### 12. Get OHLCV History ✅
```http
GET /ohlcv-history?symbols=BTCUSDT_PERP.A,BTCUSD.C&interval=daily&from=1760000000&to=1761400000
```

**Parameters:**
- `symbols` (required): Works for both futures and spot
- `interval` (required): Same as other historical endpoints
- `from` (required): UNIX timestamp
- `to` (required): UNIX timestamp

**Response:**
```json
[
  {
    "symbol": "BTCUSDT_PERP.A",
    "history": [
      {
        "t": 1761350400,
        "o": 50000.0,
        "h": 51000.0,
        "l": 49500.0,
        "c": 50500.0,
        "v": 1000.5,
        "bv": 500.25,
        "tx": 10000,
        "btx": 5000
      }
    ]
  }
]
```

**Format**: 
- `t`: timestamp
- `o`: open price
- `h`: high price
- `l`: low price
- `c`: close price
- `v`: volume
- `bv`: buy volume
- `tx`: number of transactions
- `btx`: number of buy transactions

---

## 🔄 Exchange Codes Reference

| Code | Exchange | Code | Exchange |
|------|----------|------|----------|
| A | Binance | 6 | Bybit |
| 0 | BitMEX | 2 | Deribit |
| 3 | OKX | 4 | Huobi |
| 7 | Phemex | 8 | dYdX |
| C | Coinbase | F | Bitfinex |
| K | Kraken | G | Gemini |
| Y | Gate.io | H | Hyperliquid |
| B | Bitstamp | W | WOO X |
| P | Poloniex | V | Vertex |
| D | Bitforex | U | Bithumb |
| L | BitFlyer | M | BtcMarkets |
| I | Bit2c | E | MercadoBitcoin |
| N | Independent Reserve | J | Luno |

---

## 💻 Python Usage Examples

### Basic Usage
```python
from coinalyze_client_updated import CoinalyzeClient

client = CoinalyzeClient()  # Uses COINALYZE_API env var

# Get all future markets
futures = client.get_future_markets()
print(f"Found {len(futures)} futures")

# Get current open interest for BTC
oi = client.get_open_interest("BTCUSDT_PERP.A")
print(f"BTC OI: {oi}")

# Get funding rate
fr = client.get_funding_rate("BTCUSDT_PERP.A,ETHUSDT_PERP.A")
print(f"Funding rates: {fr}")
```

### Historical Data
```python
from datetime import datetime, timedelta

# Last 7 days of daily data
end_ts = int(datetime.now().timestamp())
start_ts = int((datetime.now() - timedelta(days=7)).timestamp())

# Get OI history
oi_hist = client.get_open_interest_history(
    symbols="BTCUSDT_PERP.A",
    interval="daily",
    from_ts=start_ts,
    to_ts=end_ts
)

# Get OHLCV data
ohlcv = client.get_ohlcv_history(
    symbols="BTCUSDT_PERP.A",
    interval="1hour",
    from_ts=start_ts,
    to_ts=end_ts
)
```

### Finding Symbols
```python
# Get all BTC perpetuals on Binance
futures = client.get_future_markets()
btc_binance = [
    f for f in futures 
    if f['base_asset'] == 'BTC' 
    and f['exchange'] == 'A'
    and f['is_perpetual']
]

print(f"BTC perpetuals on Binance: {[f['symbol'] for f in btc_binance]}")
```

---

## 🚨 Error Handling

**Status Codes:**
- `200` - Success
- `400` - Bad parameter(s)
- `401` - Invalid/missing API key
- `429` - Too many requests (check `Retry-After` header)
- `500` - Server error

**Rate Limiting:**
- 40 calls per minute per API key
- If you hit 429, check the `Retry-After` header
- The Python client implements automatic rate limiting (1.5s between calls)

---

## 📈 Data Statistics

- **Exchanges**: 26 supported
- **Future Markets**: 3,739 instruments
- **Spot Markets**: 6,839 instruments
- **Total Instruments**: 10,578+

---

## 🎯 Use Cases

1. **Trading Signals**: Monitor funding rates across exchanges
2. **Risk Management**: Track open interest changes
3. **Market Analysis**: Analyze liquidation data
4. **Arbitrage**: Compare prices across exchanges using OHLCV
5. **Sentiment Analysis**: Long/short ratios
6. **Historical Backtesting**: Access historical data for all metrics

---

## 📝 Notes

- Free API with attribution requirement (cite Coinalyze in public use)
- Data returned in ascending order
- Intraday data retention: 1500-2000 datapoints
- Daily data: Full history retained
- Each symbol in a multi-symbol request counts as one API call
- Maximum 20 symbols per request

---

## 📧 Support

For errors or suggestions: contact@coinalyze.net

---

## ✅ Testing Results

All 12 endpoints tested and working:
- ✅ Exchanges
- ✅ Future markets (3,739 instruments)
- ✅ Spot markets (6,839 instruments)
- ✅ Current open interest
- ✅ Current funding rate
- ✅ Predicted funding rate
- ✅ Open interest history
- ✅ Funding rate history
- ✅ Predicted funding rate history
- ✅ Liquidation history
- ✅ Long/short ratio history
- ✅ OHLCV history
