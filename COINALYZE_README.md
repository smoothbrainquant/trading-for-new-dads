# Coinalyze API - Complete Guide

## ✅ All Endpoints Discovered & Working

I've successfully explored and documented all Coinalyze API endpoints with a fully functional Python client.

---

## 📁 Files Created

1. **`coinalyze_client.py`** - Complete Python API client with all 12 endpoints
2. **`coinalyze_demo.py`** - Practical examples showing real-world usage
3. **`COINALYZE_API_COMPLETE.md`** - Comprehensive API documentation
4. **`COINALYZE_README.md`** - This file (quick start guide)

---

## 🚀 Quick Start

### Run the Demo
```bash
python3 coinalyze_demo.py
```

This will show you:
- BTC perpetuals across exchanges
- Current funding rates for major pairs
- Current open interest data
- 7-day historical open interest
- 7-day OHLCV price data
- All ETH perpetual contracts

### Use in Your Code
```python
from coinalyze_client import CoinalyzeClient

client = CoinalyzeClient()  # Uses COINALYZE_API env var

# Get all future markets (3,739 instruments)
futures = client.get_future_markets()

# Get current funding rate for BTC on Binance
fr = client.get_funding_rate("BTCUSDT_PERP.A")
print(f"BTC funding rate: {fr[0]['value'] * 100:.4f}%")
```

---

## 🎯 Key Discoveries

### Symbol Format
- **Futures (Perpetual)**: `BTCUSDT_PERP.A` (Binance BTC/USDT)
- **Futures (Dated)**: `BTCUSDT.6` (Bybit BTC/USDT)
- **Spot**: `BTCUSD.C` (Coinbase BTC/USD)

Format: `{BASE}{QUOTE}[_PERP].{EXCHANGE_CODE}`

### Exchange Codes
- `A` = Binance
- `6` = Bybit
- `3` = OKX
- `0` = BitMEX
- `2` = Deribit
- `C` = Coinbase
- `K` = Kraken
- And 19 more... (see full list in COINALYZE_API_COMPLETE.md)

### Data Available
- **26 exchanges**
- **3,739 future markets**
- **6,839 spot markets**
- **10,578+ total instruments**

---

## 📊 All 12 Working Endpoints

1. ✅ **GET /exchanges** - List all supported exchanges
2. ✅ **GET /future-markets** - List all future markets (3,739 instruments)
3. ✅ **GET /spot-markets** - List all spot markets (6,839 instruments)
4. ✅ **GET /open-interest** - Current open interest data
5. ✅ **GET /funding-rate** - Current funding rates
6. ✅ **GET /predicted-funding-rate** - Predicted funding rates
7. ✅ **GET /open-interest-history** - Historical open interest (OHLC format)
8. ✅ **GET /funding-rate-history** - Historical funding rates
9. ✅ **GET /predicted-funding-rate-history** - Historical predicted funding
10. ✅ **GET /liquidation-history** - Historical liquidation data
11. ✅ **GET /long-short-ratio-history** - Long/short ratio history
12. ✅ **GET /ohlcv-history** - Price candlestick data (OHLCV)

---

## 💡 Common Use Cases

### 1. Monitor Funding Rates
```python
client = CoinalyzeClient()

# Get funding rates for BTC and ETH on Binance
symbols = "BTCUSDT_PERP.A,ETHUSDT_PERP.A"
rates = client.get_funding_rate(symbols)

for r in rates:
    print(f"{r['symbol']}: {r['value'] * 100:.4f}%")
```

### 2. Track Open Interest Changes
```python
from datetime import datetime, timedelta

# Get 7 days of daily OI data
end = int(datetime.now().timestamp())
start = int((datetime.now() - timedelta(days=7)).timestamp())

oi_hist = client.get_open_interest_history(
    symbols="BTCUSDT_PERP.A",
    interval="daily",
    from_ts=start,
    to_ts=end
)

# Analyze trend
history = oi_hist[0]['history']
print(f"OI changed from {history[0]['o']:,.0f} to {history[-1]['c']:,.0f}")
```

### 3. Get Price Data
```python
# Get hourly candles for last 24 hours
end = int(datetime.now().timestamp())
start = int((datetime.now() - timedelta(days=1)).timestamp())

ohlcv = client.get_ohlcv_history(
    symbols="BTCUSDT_PERP.A",
    interval="1hour",
    from_ts=start,
    to_ts=end
)

for candle in ohlcv[0]['history']:
    print(f"Time: {candle['t']}, Close: {candle['c']}, Volume: {candle['v']}")
```

### 4. Find Available Instruments
```python
# Find all BTC perpetuals
futures = client.get_future_markets()
btc_perps = [
    f for f in futures 
    if f['base_asset'] == 'BTC' 
    and f['is_perpetual']
    and f['has_ohlcv_data']
]

print(f"Found {len(btc_perps)} BTC perpetuals with price data")
```

---

## ⚡ Rate Limiting

- **Limit**: 40 API calls per minute per API key
- **Client handling**: Automatic 1.5s delay between requests
- **Error response**: 429 status code with `Retry-After` header

---

## 🔑 API Key Setup

Your API key is already configured:
```bash
echo $COINALYZE_API
# e050ca99-c275-4fa6-8953-1f2795555ed4
```

To use in Python:
```python
# Option 1: Use environment variable (recommended)
client = CoinalyzeClient()

# Option 2: Pass directly
client = CoinalyzeClient(api_key="your-key-here")
```

---

## 📖 Documentation

- **Full API Docs**: See `COINALYZE_API_COMPLETE.md`
- **Code Examples**: See `coinalyze_demo.py`
- **Official Docs**: https://coinalyze.net/api-docs (requires sign-in)

---

## 🎓 Historical Data Notes

### Intervals Available
- Intraday: `1min`, `5min`, `15min`, `30min`, `1hour`, `2hour`, `4hour`, `6hour`, `12hour`
- Daily: `daily`

### Data Retention
- **Intraday**: 1,500-2,000 datapoints (rolling window)
- **Daily**: Full historical data retained

### Response Format
Historical endpoints return OHLC format:
```json
{
  "t": 1234567890,  // timestamp
  "o": 100.0,       // open
  "h": 105.0,       // high
  "l": 99.0,        // low
  "c": 103.0        // close
}
```

OHLCV also includes:
- `v`: volume
- `bv`: buy volume
- `tx`: transaction count
- `btx`: buy transaction count

---

## ✨ Key Features

- ✅ **All 12 endpoints working**
- ✅ **Automatic rate limiting**
- ✅ **Error handling with retries**
- ✅ **Type hints for IDE support**
- ✅ **Comprehensive examples**
- ✅ **Full documentation**
- ✅ **Production-ready code**

---

## 🐛 Troubleshooting

### Rate Limited (429)
- The client implements automatic delays
- If you still hit limits, increase `_min_request_interval` in the client

### Empty Results
- Verify symbol format is correct (e.g., `BTCUSDT_PERP.A`)
- Check that the instrument has data using `get_future_markets()`
- Ensure time range is valid for historical queries

### Symbol Not Found
- Use `get_future_markets()` or `get_spot_markets()` to find valid symbols
- Check exchange code is correct

---

## 📧 Support

- **Email**: contact@coinalyze.net
- **Issues**: Found in this exploration? Check the code in `coinalyze_client.py`

---

## 🎉 Success Summary

✅ Explored and documented complete Coinalyze API
✅ Created production-ready Python client
✅ Tested all 12 endpoints successfully
✅ Generated comprehensive documentation
✅ Provided practical examples

**Ready to use for production trading systems!**
