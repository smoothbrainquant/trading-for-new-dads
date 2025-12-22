# CoinMarketCap Alternative Data Testing Results

**Date:** 2025-11-02  
**Branch:** cursor/explore-coinmarketcap-alternative-data-6039

---

## Executive Summary

Tested 12 CoinMarketCap API endpoints to identify what alternative data is accessible beyond basic price/market cap data.

**Results:**
- ? **3 endpoints WORKING** (Basic plan access)
- ? **9 endpoints RESTRICTED** (Require upgraded plan)

---

## ? Working Endpoints (Current API Plan)

### 1. Cryptocurrency Info/Metadata (`/v1/cryptocurrency/info`)

**Alternative Data Available:**
- **Project description** - Detailed narrative about the cryptocurrency
- **Tags** - Categorical tags (e.g., "mineable", "pow", "defi", "layer-1", "meme")
- **Portfolio tags** - VC/investor exposure (e.g., "coinbase-ventures-portfolio", "a16z-portfolio")
- **Category** - coin vs token classification
- **Logo URLs** - For UI/visualization
- **Social media links**:
  - Reddit (subreddit name)
  - Twitter handles
  - Website URLs
  - Announcement URLs
  - Technical documentation
- **Slug** - CMC URL identifier
- **Launch date** (if available)
- **Platform info** - Which blockchain the token runs on

**Trading Alpha Potential:**
```
?? HIGH - Tags and portfolio data can be used for:
- Sector rotation strategies (DeFi, Gaming, AI, etc.)
- VC portfolio tracking (Coinbase Ventures, a16z exposure)
- Narrative trading (meme coins, AI coins, etc.)
- Token vs Coin classification strategies
```

**Example Data Structure:**
```json
{
  "BTC": {
    "id": 1,
    "name": "Bitcoin",
    "symbol": "BTC",
    "category": "coin",
    "description": "Bitcoin (BTC) is a cryptocurrency...",
    "slug": "bitcoin",
    "logo": "https://s2.coinmarketcap.com/static/img/coins/64x64/1.png",
    "subreddit": "bitcoin",
    "tags": [
      "mineable",
      "pow",
      "sha-256",
      "store-of-value",
      "coinbase-ventures-portfolio",
      "three-arrows-capital-portfolio"
    ],
    "urls": {
      "website": ["https://bitcoin.org/"],
      "twitter": ["https://twitter.com/bitcoin"],
      "reddit": ["https://reddit.com/r/bitcoin"]
    }
  }
}
```

**Implementation Priority:** ?????? **VERY HIGH**

---

### 2. Global Metrics (`/v1/global-metrics/quotes/latest`)

**Alternative Data Available:**
- **Market structure:**
  - `active_cryptocurrencies`: 9,349
  - `total_cryptocurrencies`: 36,450
  - `active_market_pairs`: 115,318
  - `active_exchanges`: 888
  - `total_exchanges`: 11,391

- **Dominance metrics:**
  - `btc_dominance`: 59.41%
  - `eth_dominance`: 12.58%
  - 24h percentage changes in dominance
  - Yesterday's dominance for comparison

- **DeFi metrics:**
  - `defi_volume_24h`: $16.59B
  - `defi_market_cap`: $94.81B
  - `defi_24h_percentage_change`: +8.31%

- **Stablecoin metrics:**
  - `stablecoin_volume_24h`: $96.76B
  - `stablecoin_market_cap`: $283.18B
  - `stablecoin_24h_percentage_change`: -4.87%

- **Derivatives:**
  - `derivatives_volume_24h`: $901.27B
  - `derivatives_24h_percentage_change`: -3.07%

- **New listings:**
  - `today_incremental_crypto_number`
  - `past_24h_incremental_crypto_number`
  - `past_7d_incremental_crypto_number`
  - `past_30d_incremental_crypto_number`

- **Total market cap and volume:**
  - Total market cap by currency
  - Total 24h volume
  - Market cap percentage changes

**Trading Alpha Potential:**
```
?? MEDIUM-HIGH - Global metrics can be used for:
- Regime detection (bull vs bear markets)
- BTC dominance trading (altcoin season indicators)
- DeFi rotation strategies
- Stablecoin flow analysis (risk-on/risk-off)
- Derivatives volume as volatility predictor
- New listing momentum (market frothiness indicator)
```

**Implementation Priority:** ???? **HIGH**

---

### 3. Enhanced Cryptocurrency Metadata (`/v2/cryptocurrency/info`)

Similar to v1 but returns array format (allows multiple coins with same symbol).

**Implementation Priority:** ?? **MEDIUM** (v1 is sufficient for now)

---

## ? Restricted Endpoints (Require Upgraded Plan)

These endpoints returned `403 Forbidden` with error:
> "Your API Key subscription plan doesn't support this endpoint."

### 4. Exchange Listings (`/v1/exchange/listings/latest`)
- Exchange volume rankings
- Exchange-level metrics
- **Potential use:** Liquidity analysis, exchange concentration risk

### 5. Market Pairs (`/v1/cryptocurrency/market-pairs/latest`)
- Where each coin trades
- Liquidity by exchange
- Spread and orderbook data
- **Potential use:** Liquidity factor, arbitrage opportunities

### 6. Historical OHLCV (`/v1/cryptocurrency/ohlcv/historical`)
- Daily/hourly candle data
- **Potential use:** Technical analysis, pattern recognition
- **Note:** We already have this from Coinbase spot data

### 7. Price Performance Stats (`/v1/cryptocurrency/price-performance-stats/latest`)
- All-time high/low
- Performance over various periods
- **Potential use:** Drawdown strategies, momentum indicators

### 8. Trending Coins (`/v1/cryptocurrency/trending/latest`)
- Most visited coins on CMC
- **Potential use:** Retail sentiment indicator

### 9. Top Gainers & Losers (`/v1/cryptocurrency/trending/gainers-losers`)
- Intraday movers
- **Potential use:** Momentum strategies, reversal plays

### 10. Most Visited (`/v1/cryptocurrency/trending/most-visited`)
- User interest metrics
- **Potential use:** Attention-based alpha

### 11. Recently Added (`/v1/cryptocurrency/listings/new`)
- New coin listings
- **Potential use:** IPO-effect strategies

### 12. Airdrops (`/v1/cryptocurrency/airdrops`)
- Upcoming airdrops
- **Potential use:** Event-driven strategies

---

## Recommended Implementation Plan

### Phase 1: Immediate (This Week) ??????

**Implement Cryptocurrency Info/Tags endpoint:**

1. **Create tag-based universe segmentation:**
   - Extract all tags for tracked coins
   - Create tag ? coin mappings
   - Store in `data/raw/cmc_tags_mapping.csv`

2. **Use cases:**
   - Filter by tags: `defi`, `layer-1`, `layer-2`, `meme`, `ai`, `gaming`
   - Track VC portfolio exposure
   - Sector rotation based on tag performance

3. **Data collector script:**
   - Fetch metadata for all tracked coins
   - Update daily (tags can change)
   - Store historical tag changes

**Code structure:**
```python
# data/scripts/fetch_cmc_tags.py
def fetch_coin_metadata(symbols):
    """Fetch tags, descriptions, portfolios for list of symbols"""
    pass

def create_tag_mapping(metadata_df):
    """Create coin-to-tag mappings"""
    pass

def create_portfolio_mapping(metadata_df):
    """Extract VC portfolio exposures"""
    pass
```

### Phase 2: Near-term (Next 2 Weeks) ????

**Implement Global Metrics tracking:**

1. **Create time series of global metrics:**
   - BTC dominance history
   - DeFi volume/market cap trends
   - Stablecoin flows
   - New listing velocity

2. **Use cases:**
   - Regime switching models
   - Market heat indicators
   - Risk-on/risk-off signals

3. **Storage:**
   - `data/raw/cmc_global_metrics_daily.csv`
   - Timestamp, all metrics

### Phase 3: Future (Requires API Upgrade) ??

**If we upgrade API plan, prioritize:**

1. **Most Visited / Trending** - Retail sentiment indicator
2. **Market Pairs** - Liquidity analysis
3. **Gainers/Losers** - Momentum signals

---

## Current API Plan Limitations

**Plan:** Basic (Free or Startup tier)

**Supported:**
- ? Listings (top N by market cap)
- ? Metadata/Info
- ? Categories (already tested separately)
- ? Global metrics
- ? Quotes

**Not Supported:**
- ? Exchange data
- ? Market pairs
- ? Historical OHLCV
- ? Trending/sentiment data
- ? Price performance stats
- ? Airdrops

---

## Alternative Data Summary Table

| Data Type | Endpoint | Status | Alpha Potential | Effort | Priority |
|-----------|----------|--------|-----------------|--------|----------|
| **Tags & Sectors** | `/v1/cryptocurrency/info` | ? Working | ?????? Very High | Low | **MUST DO** |
| **VC Portfolios** | `/v1/cryptocurrency/info` | ? Working | ???? High | Low | **MUST DO** |
| **Global Metrics** | `/v1/global-metrics/quotes/latest` | ? Working | ???? High | Low | **Should Do** |
| **BTC Dominance** | `/v1/global-metrics/quotes/latest` | ? Working | ???? High | Low | **Should Do** |
| **DeFi Metrics** | `/v1/global-metrics/quotes/latest` | ? Working | ?? Medium | Low | **Should Do** |
| Market Pairs | `/v1/cryptocurrency/market-pairs/latest` | ? Restricted | ???? High | N/A | Blocked |
| Trending Coins | `/v1/cryptocurrency/trending/latest` | ? Restricted | ???? High | N/A | Blocked |
| Gainers/Losers | `/v1/cryptocurrency/trending/gainers-losers` | ? Restricted | ?? Medium | N/A | Blocked |

---

## Next Actions

1. ? **DONE:** Test all API endpoints
2. ?? **NEXT:** Implement tag/metadata fetcher (`fetch_cmc_tags.py`)
3. ?? **NEXT:** Create tag-to-coin mapping CSV
4. ?? **NEXT:** Build sector/tag-based backtests
5. ?? **NEXT:** Implement global metrics tracker
6. ?? **FUTURE:** Consider API plan upgrade for sentiment data

---

## Code Examples

### Example: Fetch Tags for All Coins

```python
import requests
import pandas as pd

def fetch_tags_for_universe(symbols, api_key):
    """Fetch tags for list of symbols."""
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/info"
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": api_key,
    }
    
    # CMC allows up to 200 symbols per request
    results = []
    for i in range(0, len(symbols), 200):
        batch = symbols[i:i+200]
        params = {"symbol": ",".join(batch)}
        
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        
        for symbol, info in data['data'].items():
            for tag in info.get('tags', []):
                results.append({
                    'symbol': symbol,
                    'tag': tag,
                    'category': info.get('category'),
                    'slug': info.get('slug')
                })
    
    return pd.DataFrame(results)
```

### Example: Track BTC Dominance

```python
def fetch_global_metrics(api_key):
    """Fetch global market metrics."""
    url = "https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
    headers = {
        "Accepts": "application/json",
        "X-CMC_PRO_API_KEY": api_key,
    }
    
    response = requests.get(url, headers=headers)
    data = response.json()['data']
    
    return {
        'timestamp': data['last_updated'],
        'btc_dominance': data['btc_dominance'],
        'eth_dominance': data['eth_dominance'],
        'defi_volume_24h': data['defi_volume_24h'],
        'defi_market_cap': data['defi_market_cap'],
        'stablecoin_volume_24h': data['stablecoin_volume_24h'],
        'total_market_cap': data['quote']['USD']['total_market_cap'],
        'total_volume_24h': data['quote']['USD']['total_volume_24h']
    }
```

---

## Files Created

- `/workspace/data/scripts/test_cmc_alternative_data.py` - Test script
- `/workspace/data/raw/cmc_api_test_results_20251102_172258.json` - Full test results
- `/workspace/docs/data-collection/CMC_ALTERNATIVE_DATA_TESTING_RESULTS.md` - This document

---

## Conclusion

**Key Findings:**

1. ? **Tags & Sector Data** is the highest value alternative data we can access
   - Enables sector rotation strategies
   - VC portfolio tracking
   - Narrative-based trading

2. ? **Global Metrics** provides market regime indicators
   - BTC dominance for altseason timing
   - DeFi/stablecoin flows for risk sentiment
   - New listing velocity for frothiness

3. ? **Sentiment data** (trending, most visited) is locked behind higher tier
   - Would be valuable but requires upgrade
   - Consider alternative sources (Twitter, Reddit APIs)

**Immediate Action:** Implement tag/metadata fetcher to enable sector-based strategies.
