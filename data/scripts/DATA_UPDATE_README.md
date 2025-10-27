# Data Update Guide

This guide explains how to update all data sources used in the trading system.

## Quick Start - Update All Data

To update all data sources at once, run:

```bash
cd /workspace/data/scripts
python3 update_all_data.py
```

This will update (in order):
1. **Market Cap data** from CoinMarketCap (top 100 cryptocurrencies)
2. **Price data** from Coinbase spot markets (top 50 by volume, 100 days)
3. **Open Interest data** from Coinalyze (top 50 coins, all history)
4. **Funding Rates (carry) data** from Coinalyze (top 50 coins, all history)

### Prerequisites

Set the following environment variables:

```bash
export CMC_API="your_coinmarketcap_api_key"
export COINALYZE_API="your_coinalyze_api_key"
```

**Note:** If `CMC_API` is not set, mock market cap data will be used. If `COINALYZE_API` is not set, OI and funding rate updates will fail.

### Options

Skip specific data updates if needed:

```bash
# Skip market cap update
python3 update_all_data.py --skip-marketcap

# Skip price data update
python3 update_all_data.py --skip-price

# Skip open interest update
python3 update_all_data.py --skip-oi

# Skip funding rates update
python3 update_all_data.py --skip-funding

# Specify custom output directory
python3 update_all_data.py --output-dir /path/to/output
```

### Expected Runtime

- Market Cap: ~5 seconds
- Price Data: ~2-3 minutes (50 symbols)
- Open Interest: ~3-5 minutes (47 symbols)
- Funding Rates: ~3-5 minutes (46 symbols)

**Total: ~10-15 minutes**

## Individual Data Update Scripts

You can also update each data source individually:

### 1. Market Cap Data

```bash
cd /workspace/data/scripts
python3 fetch_coinmarketcap_data.py --limit 100 --output /workspace/data/raw/crypto_marketcap_latest.csv
```

**Output:** `/workspace/data/raw/crypto_marketcap_latest.csv`

### 2. Price Data (Coinbase Spot - PRIMARY SOURCE)

Coinbase spot is the primary price data source. It provides reliable, high-quality spot price data.

#### Quick Update (Last 100 Days)

```bash
cd /workspace/data/scripts
python3 -c "
import ccxt
from datetime import datetime, timedelta
import pandas as pd
import time

exchange = ccxt.coinbase({'enableRateLimit': True})
tickers = exchange.fetch_tickers()

# Get top 50 volume pairs
volume_data = []
for symbol, ticker in tickers.items():
    if ('/USD' in symbol or '/USDT' in symbol or '/USDC' in symbol) and ':' not in symbol:
        volume_data.append({
            'symbol': symbol,
            'volume': ticker.get('quoteVolume', 0) or ticker.get('baseVolume', 0) or 0
        })

volume_df = pd.DataFrame(volume_data)
volume_df = volume_df.sort_values('volume', ascending=False)
top_pairs = volume_df.head(50)['symbol'].tolist()

# Fetch data
end_date = datetime.now()
start_date = end_date - timedelta(days=100)
since = exchange.parse8601(start_date.isoformat())

all_data = []
for idx, symbol in enumerate(top_pairs, 1):
    try:
        print(f'[{idx}/{len(top_pairs)}] {symbol}...', end=' ')
        ohlcv = exchange.fetch_ohlcv(symbol=symbol, timeframe='1d', since=since, limit=100)
        if ohlcv:
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['symbol'] = symbol
            df = df[['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
            all_data.append(df)
            print(f'✓ {len(df)} days')
        time.sleep(0.5)
    except Exception as e:
        print(f'✗ {e}')

combined_df = pd.concat(all_data, ignore_index=True)
combined_df = combined_df.sort_values(['date', 'symbol']).reset_index(drop=True)
combined_df.to_csv('/workspace/data/raw/coinbase_spot_latest.csv', index=False)
print(f'\\nSaved {len(combined_df)} records to coinbase_spot_latest.csv')
"
```

#### Full Historical Download

For complete historical data (from 2020-01-01):

```bash
cd /workspace/data/raw
python3 ../scripts/download_coinbase_spot_historical.py
```

Or for top 200 coins:

```bash
cd /workspace/data/raw
python3 ../scripts/download_top200_historical_coinbase.py
```

**Output:** 
- `/workspace/data/raw/coinbase_spot_latest.csv` (quick update)
- `/workspace/data/raw/coinbase_spot_daily_data_*.csv` (full historical)

### 3. Open Interest Data

```bash
cd /workspace/data/raw
python3 ../scripts/fetch_all_historical_open_interest_max.py
```

This fetches all available daily OI data from 2019 to present for the top 50 coins.

**Output:** 
- `/workspace/data/raw/historical_open_interest_top50_ALL_HISTORY_*.csv`
- `/workspace/data/raw/open_interest_data_availability_*.csv`
- `/workspace/data/raw/historical_open_interest_top50_ALL_HISTORY_summary_*.csv`

### 4. Funding Rates (Carry) Data

```bash
cd /workspace/data/raw
python3 ../scripts/fetch_all_historical_funding_rates_max.py
```

This fetches all available daily funding rate data from 2019 to present for the top 50 coins.

**Output:**
- `/workspace/data/raw/historical_funding_rates_top50_ALL_HISTORY_*.csv`
- `/workspace/data/raw/funding_rates_data_availability_*.csv`
- `/workspace/data/raw/historical_funding_rates_top50_ALL_HISTORY_summary_*.csv`

## Data Sources

### Price Data Priority Order

1. **Coinbase Spot** (PRIMARY) - Most reliable, good coverage for major coins
2. Historical alternatives available for specific use cases

### Why Coinbase Spot?

- High liquidity and reliability
- Good coverage of major cryptocurrencies
- Stable API with good rate limits
- Spot prices are less volatile than futures
- Better for backtesting strategies

## Output Files Location

All data files are saved to: `/workspace/data/raw/`

## Troubleshooting

### API Key Issues

If you get errors about missing API keys:

```bash
# Check if variables are set
echo $CMC_API
echo $COINALYZE_API

# Set them if missing
export CMC_API="your_key_here"
export COINALYZE_API="your_key_here"
```

### Rate Limiting

If you encounter rate limiting errors:
- The scripts have built-in rate limiting delays
- For Coinbase: Wait 1-2 minutes between runs
- For Coinalyze: Wait 3-5 minutes between runs

### Data Not Found

If scripts can't find `coinmarketcap_historical_all_snapshots.csv`:
- Make sure you're running from the correct directory
- The OI and funding rate scripts need to be run from `/workspace/data/raw/`

### Geo-Restrictions

Some exchanges (Binance, Bybit) may block certain regions:
- This is why we default to Coinbase for price data
- Coinbase has better global availability

## Automated Updates

To set up automated data updates (e.g., daily), you can use cron:

```bash
# Edit crontab
crontab -e

# Add line to run update every day at 2 AM
0 2 * * * cd /workspace/data/scripts && /usr/bin/python3 update_all_data.py >> /var/log/data_update.log 2>&1
```

## Data Retention

- **Market Cap**: Latest snapshot (100 coins)
- **Price Data**: 100 days (quick update) or full history (manual script)
- **Open Interest**: Full history from 2019 (retained indefinitely by Coinalyze)
- **Funding Rates**: Full history from 2019 (retained indefinitely by Coinalyze)

## See Also

- [CoinMarketCap API Documentation](https://coinmarketcap.com/api/documentation/v1/)
- [Coinalyze API Documentation](https://coinalyze.net/api/)
- [CCXT Documentation](https://docs.ccxt.com/)
