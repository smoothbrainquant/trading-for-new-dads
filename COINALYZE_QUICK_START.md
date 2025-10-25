# Coinalyze API Quick Start Guide

## 📋 Summary

I've explored the Coinalyze API and discovered the following:

### ✅ Working Endpoints
1. **`GET /exchanges`** - Returns list of 26 supported exchanges
   - No parameters required
   - Returns exchange codes and names

### ⚠️ Partially Working Endpoints
2. **`GET /open-interest`** - Open interest data
   - Requires `symbols` parameter (format unknown)
   - Returns empty array for tested symbols
   
3. **`GET /funding-rate`** - Funding rate data
   - Requires `symbols` parameter (format unknown)
   - Returns empty array for tested symbols

### ❌ Not Available (404 errors)
- Symbol/market listing endpoints
- Historical data endpoints  
- Liquidation data
- Volume data
- Market tickers/prices
- Long/short ratios
- And many more (see full documentation)

## 🚀 Quick Usage

### Using the Python Client

```python
from coinalyze_client import CoinalyzeClient

# Initialize client (uses COINALYZE_API env var)
client = CoinalyzeClient()

# Get list of exchanges
exchanges = client.get_exchanges()
print(f"Found {len(exchanges)} exchanges")

# Try to get open interest (currently returns empty)
oi_data = client.get_open_interest("BTCUSDT")
```

### Using Command Line

```bash
# Get exchanges
python3 coinalyze_client.py

# Or use curl directly
curl -H "api_key: $COINALYZE_API" "https://api.coinalyze.net/v1/exchanges"
```

## 📊 Supported Exchanges

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

## 📁 Files Created

1. **`COINALYZE_API_ENDPOINTS.md`** - Complete API documentation
2. **`coinalyze_client.py`** - Python client for the API
3. **`COINALYZE_QUICK_START.md`** - This file

## ⚠️ Known Issues

1. **Symbol Format Unknown**: The correct symbol format for data endpoints hasn't been determined
   - Tested: `BTCUSDT`, `BTC`, `A_BTCUSDT`, `BINANCE:BTCUSDT`, etc.
   - All return empty arrays

2. **Limited Documentation**: Unable to access official API docs
   - Website behind Cloudflare protection
   - No documentation endpoint in API itself

3. **Rate Limiting**: API enforces rate limits
   - Returns 429 error when exceeded
   - Client implements 1.5s delay between requests

## 🔍 Next Steps

To fully utilize this API:

1. **Contact Coinalyze Support** for:
   - Official API documentation
   - Correct symbol naming format
   - List of available symbols/pairs
   - API key permissions/subscription tiers

2. **Check Your API Key**:
   - Verify it has appropriate permissions
   - Check if your subscription includes data access

3. **Try Alternative Approaches**:
   - Look for Coinalyze GitHub repositories
   - Check community forums/Discord
   - Review example code from other users

## 💡 API Key Setup

The API key is already configured in your environment:
```bash
echo $COINALYZE_API
# e050ca99-c275-4fa6-8953-1f2795555ed4
```

## 🔗 Resources

- **Base URL**: `https://api.coinalyze.net/v1`
- **Authentication**: Header `api_key: YOUR_KEY`
- **Format**: JSON responses

---

**Status**: Initial exploration complete. Limited endpoints available without proper symbol format.
