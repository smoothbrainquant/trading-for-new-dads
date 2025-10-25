# Historical Funding Rates - Top 50 Coins

## Overview

This dataset contains **90 days of historical funding rates** for the **top 50 cryptocurrencies** by market capitalization, fetched from Coinalyze API using CoinMarketCap rankings.

## Dataset Summary

- **Total Data Points**: 4,154
- **Coins Covered**: 47 out of 50 (3 coins don't have perpetual contracts)
- **Date Range**: July 28, 2025 - October 25, 2025 (90 days)
- **Interval**: Daily aggregated funding rates
- **Exchange Sources**: Primarily Binance, Bybit, OKX perpetual futures

## Files Generated

### 1. `historical_funding_rates_top50_YYYYMMDD_HHMMSS.csv`
Complete historical dataset with the following columns:
- `rank`: CoinMarketCap rank
- `coin_name`: Full coin name
- `coin_symbol`: Coin ticker symbol
- `symbol`: Coinalyze symbol (e.g., BTCUSD_PERP.A)
- `date`: Date of the funding rate
- `timestamp`: Unix timestamp
- `funding_rate`: Funding rate (decimal)
- `funding_rate_pct`: Funding rate as percentage
- `fr_open`, `fr_high`, `fr_low`: Daily OHLC for funding rates

### 2. `historical_funding_rates_top50_summary_YYYYMMDD_HHMMSS.csv`
Summary statistics per coin:
- Average funding rate
- Standard deviation (volatility)
- Min/Max funding rates
- Number of data points

## Key Findings

### Top 5 Highest Average Funding Rates
1. **Monero (XMR)**: 1.65% - Highest average funding rate
2. **OKB**: 0.89%
3. **Bitcoin Cash (BCH)**: 0.85%
4. **Stellar (XLM)**: 0.85%
5. **Uniswap (UNI)**: 0.82%

### Top 5 Lowest Average Funding Rates
1. **MANTRA (OM)**: -4.49% - Extreme negative funding
2. **Tether USDT**: -4.19% - Stablecoin with negative funding
3. **Ethena (ENA)**: -0.69%
4. **Aptos (APT)**: -0.25%
5. **Cosmos (ATOM)**: -0.16%

### Most Volatile Funding Rates
1. **MANTRA (OM)**: 16.46% std dev - Extreme volatility (min: -140.6%, max: 0.5%)
2. **Tether USDT**: 13.19% std dev
3. **Aptos (APT)**: 4.17% std dev
4. **Cosmos (ATOM)**: 3.29% std dev
5. **Pepe (PEPE)**: 3.27% std dev

## Coins Without Perpetual Contracts

The following 3 coins from the top 50 don't have perpetual futures on major exchanges:
- UNUS SED LEO (LEO)
- Bitget Token (BGB)
- Ethena USDe (USDe)

## Interpretation

### Positive Funding Rates
Indicate that **longs are paying shorts**, suggesting:
- Bullish market sentiment
- More traders taking long positions
- Perp price > spot price

### Negative Funding Rates
Indicate that **shorts are paying longs**, suggesting:
- Bearish market sentiment
- More traders taking short positions
- Perp price < spot price

### High Volatility
Large standard deviations indicate:
- Rapid sentiment changes
- Potential trading opportunities
- Higher risk

## Usage Examples

### Load and Analyze with Python
```python
import pandas as pd

# Load the data
df = pd.read_csv('historical_funding_rates_top50_20251025_114132.csv')

# Get Bitcoin funding rates
btc_fr = df[df['coin_symbol'] == 'BTC']

# Calculate average funding rate by coin
avg_fr = df.groupby('coin_symbol')['funding_rate_pct'].mean()

# Find days with extreme funding rates
extreme_fr = df[abs(df['funding_rate_pct']) > 5]
```

### Visualize Funding Rates
```python
import matplotlib.pyplot as plt

# Plot BTC funding rate over time
btc_fr = df[df['coin_symbol'] == 'BTC']
plt.plot(pd.to_datetime(btc_fr['date']), btc_fr['funding_rate_pct'])
plt.title('Bitcoin Funding Rate (90 Days)')
plt.xlabel('Date')
plt.ylabel('Funding Rate (%)')
plt.show()
```

## Data Sources

- **Funding Rates**: Coinalyze API (https://coinalyze.net)
- **Coin Rankings**: CoinMarketCap historical snapshots
- **Exchange Priority**: Binance > Bybit > OKX > BitMEX > Deribit

## Notes

1. Funding rates are typically paid every 8 hours on most exchanges
2. Daily data represents aggregated daily funding rates
3. Some coins have fewer than 90 data points (e.g., newly listed perpetuals)
4. Rate limits: Coinalyze API allows 40 calls/minute
5. The script uses 3-5 second delays between batches to respect rate limits

## Scripts

### Main Script
- `fetch_historical_funding_rates_top50_improved.py`: Production script with retry logic

### Features
- Automatic mapping from coin symbols to Coinalyze perpetual symbols
- Rate limit handling with retry logic
- Batched requests (3 symbols per batch)
- Comprehensive error handling
- Progress logging

## Future Enhancements

Potential improvements:
- [ ] Fetch intraday funding rates (1-hour, 4-hour intervals)
- [ ] Add more exchanges (Kraken, Huobi, etc.)
- [ ] Historical backfill (1+ years of data)
- [ ] Real-time streaming updates
- [ ] Funding rate arbitrage signal detection
- [ ] Correlation analysis with price movements
- [ ] Machine learning prediction models

## Contact

For questions or issues with the Coinalyze API: contact@coinalyze.net

---

**Generated**: October 25, 2025  
**Last Updated**: October 25, 2025
