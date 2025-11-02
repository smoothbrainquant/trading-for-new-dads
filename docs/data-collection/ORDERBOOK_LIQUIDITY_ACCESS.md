# Order Book Liquidity Data Access

## Summary

Yes, you **can access top of book liquidity** using **CCXT**, but **not from CoinMarketCap**.

## CCXT - Full Order Book Access ?

CCXT provides comprehensive order book data including:

### Available Data
- **Top of Book**: Best bid/ask prices and sizes
- **Order Book Depth**: Multiple price levels (configurable depth)
- **Real-time Data**: Live order book snapshots
- **Liquidity Metrics**: Bid/ask sizes at each level

### Methods

#### 1. `fetch_order_book(symbol, limit=None, params={})`
Fetches the full order book with multiple depth levels.

```python
import ccxt

exchange = ccxt.hyperliquid({'enableRateLimit': True})
orderbook = exchange.fetch_order_book('BTC/USDC:USDC', limit=10)

# Returns structure:
# {
#     'bids': [[price, size], [price, size], ...],  # Sorted highest to lowest
#     'asks': [[price, size], [price, size], ...],  # Sorted lowest to highest
#     'timestamp': 1234567890000,
#     'datetime': '2024-01-01T00:00:00.000Z'
# }

# Top of book
best_bid_price = orderbook['bids'][0][0]
best_bid_size = orderbook['bids'][0][1]
best_ask_price = orderbook['asks'][0][0]
best_ask_size = orderbook['asks'][0][1]
```

#### 2. `fetch_ticker(symbol, params={})`
Returns ticker data including top of book bid/ask (lighter weight).

```python
ticker = exchange.fetch_ticker('BTC/USDC:USDC')

# Includes:
bid = ticker['bid']          # Best bid price
ask = ticker['ask']          # Best ask price
bidVolume = ticker.get('bidVolume')  # Size at best bid (if available)
askVolume = ticker.get('askVolume')  # Size at best ask (if available)
```

### Liquidity Metrics You Can Calculate

From order book data, you can derive:

1. **Spread Metrics**
   - Absolute spread: `ask - bid`
   - Percentage spread: `(ask - bid) / bid * 100`
   - Mid price: `(bid + ask) / 2`

2. **Depth Metrics**
   - Total bid liquidity (USD): `sum(price * size for price, size in bids)`
   - Total ask liquidity (USD): `sum(price * size for price, size in asks)`
   - Volume-weighted average price at depth N
   - Bid/ask imbalance ratio

3. **Market Impact Estimation**
   - Cost to execute $X order
   - Slippage for given order size
   - Available liquidity within Y% of mid price

### Supported Exchanges

CCXT supports order book fetching on 100+ exchanges including:
- **Hyperliquid** (your current primary exchange)
- Binance
- Coinbase
- Kraken
- OKX
- Bybit
- And many more...

### Example Usage

See the new script at `/workspace/execution/fetch_orderbook_liquidity.py`:

```bash
# Fetch for specific symbols
python3 execution/fetch_orderbook_liquidity.py --symbols BTC/USDC:USDC ETH/USDC:USDC

# Fetch for top 10 active markets
python3 execution/fetch_orderbook_liquidity.py --all

# Specify depth (number of price levels)
python3 execution/fetch_orderbook_liquidity.py --depth 10 --all

# Save to CSV
python3 execution/fetch_orderbook_liquidity.py --all --csv orderbook_liquidity.csv

# Use different exchange
python3 execution/fetch_orderbook_liquidity.py --exchange binance --symbols BTC/USDT
```

## CoinMarketCap - No Order Book Data ?

CoinMarketCap API does **not provide** order book or liquidity data.

### What CoinMarketCap Provides
- Market capitalization
- Price data (aggregated across exchanges)
- 24h trading volume (aggregated)
- Historical snapshots
- Category/sector data
- Metadata (name, symbol, rank, etc.)

### What CoinMarketCap Does NOT Provide
- ? Order book data
- ? Bid/ask spreads
- ? Order book depth
- ? Real-time liquidity at specific price levels
- ? Exchange-specific order books

### CoinMarketCap Use Cases in This Codebase
Currently used for:
1. Market cap data for size factor analysis
2. Symbol universe selection (top N by market cap)
3. Historical rankings and dominance metrics
4. Volume data (aggregated across exchanges)

See: `/workspace/data/scripts/fetch_coinmarketcap_data.py`

## Comparison Table

| Feature | CCXT | CoinMarketCap |
|---------|------|---------------|
| Order Book Data | ? Yes | ? No |
| Top of Book (Bid/Ask) | ? Yes | ? No |
| Order Book Depth | ? Yes (configurable) | ? No |
| Real-time Data | ? Yes | ?? Limited |
| Exchange-specific | ? Yes | ? Aggregated only |
| Market Cap | ? No | ? Yes |
| Historical Rankings | ? Limited | ? Yes |
| API Rate Limits | Exchange-dependent | Tiered by plan |

## Recommendations

### For Order Book Liquidity Analysis
**Use CCXT** - It provides:
- Direct exchange access
- Full order book depth
- Real-time bid/ask data
- Multiple exchanges support

### For Market Cap & Universe Selection
**Use CoinMarketCap** - It provides:
- Comprehensive market cap data
- Historical rankings
- Cross-exchange aggregation
- Sector/category classifications

### Combined Strategy
1. **CoinMarketCap**: Select trading universe (e.g., top 100 by market cap)
2. **CCXT**: Fetch order book liquidity for selected symbols
3. Filter by liquidity metrics (spread, depth, etc.)
4. Execute trades on liquid instruments

## Implementation Notes

### Rate Limits
- **CCXT/Hyperliquid**: 1200 requests/minute, 20 requests/second
- **CoinMarketCap**: Varies by plan (Basic: 333/day, Hobbyist: 10K/month)

### Best Practices
1. Use `fetch_ticker()` for lightweight top-of-book checks
2. Use `fetch_order_book()` when depth analysis is needed
3. Enable rate limiting: `{'enableRateLimit': True}`
4. Cache order book data when appropriate
5. Handle exchange-specific errors gracefully

### Existing Related Scripts
- `/workspace/execution/get_bid_ask.py` - Fetch bid/ask using `fetch_ticker()`
- `/workspace/execution/fetch_orderbook_liquidity.py` - **NEW**: Full order book liquidity
- `/workspace/data/scripts/fetch_coinmarketcap_data.py` - Market cap data
- `/workspace/execution/hyperliquid_twap.py` - Includes `fetch_order_book()` implementation

## Example: Liquidity-Filtered Universe

```python
import ccxt
import pandas as pd
from data.scripts.fetch_coinmarketcap_data import fetch_coinmarketcap_data
from execution.fetch_orderbook_liquidity import fetch_orderbook_liquidity

# Step 1: Get top 50 by market cap from CoinMarketCap
df_marketcap = fetch_coinmarketcap_data(limit=50)
symbols = df_marketcap['symbol'].tolist()

# Step 2: Convert to CCXT format (e.g., BTC -> BTC/USDC:USDC)
ccxt_symbols = [f"{sym}/USDC:USDC" for sym in symbols]

# Step 3: Fetch order book liquidity
df_liquidity = fetch_orderbook_liquidity(symbols=ccxt_symbols, depth=10)

# Step 4: Filter by liquidity criteria
min_liquidity = 100_000  # $100k minimum liquidity
max_spread_pct = 0.1     # 0.1% maximum spread

liquid_symbols = df_liquidity[
    (df_liquidity['total_bid_liquidity_usd'] > min_liquidity) &
    (df_liquidity['total_ask_liquidity_usd'] > min_liquidity) &
    (df_liquidity['spread_pct'] < max_spread_pct)
]

print(f"Filtered to {len(liquid_symbols)} liquid instruments")
```

## Conclusion

- ? **Use CCXT** for order book and top of book liquidity data
- ? **Don't use CoinMarketCap** for liquidity (it doesn't provide it)
- ?? **Combine both**: CoinMarketCap for universe selection, CCXT for liquidity filtering
- ?? **New tool available**: `execution/fetch_orderbook_liquidity.py` for comprehensive liquidity analysis
