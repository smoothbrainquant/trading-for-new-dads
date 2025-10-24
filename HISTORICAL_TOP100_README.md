# Historical Top 100 Coins - Quarterly Data Fetch

This document explains how to fetch historical top 100 cryptocurrencies by market cap on a quarterly basis using the CoinMarketCap API.

## Overview

The `fetch_historical_top100_quarterly()` function fetches snapshots of the top 100 cryptocurrencies at the end of each quarter (March 31, June 30, September 30, December 31) starting from 2020.

## Requirements

### API Access
- **CoinMarketCap API Key** with historical data access
- ⚠️ **Paid Plan Required**: Historical endpoints are not available on the free tier
- Recommended: Basic Plan ($29/month) or higher

### Python Dependencies
```bash
pip install -r requirements.txt
```

Required packages:
- pandas >= 2.0.0
- requests >= 2.28.0
- python-dateutil >= 2.8.0

## Usage

### Method 1: Command Line

#### Fetch Current Snapshot (default)
```bash
export CMC_API="your-api-key-here"
python3 fetch_coinmarketcap_data.py --limit 100
```

#### Fetch Historical Quarterly Data
```bash
export CMC_API="your-api-key-here"
python3 fetch_coinmarketcap_data.py \
    --historical \
    --start-year 2020 \
    --limit 100 \
    --output historical_top100_quarterly.csv \
    --delay 1.5
```

### Method 2: Python Function

```python
from fetch_coinmarketcap_data import fetch_historical_top100_quarterly

# Fetch quarterly data from 2020 onwards
df = fetch_historical_top100_quarterly(
    api_key="your-api-key-here",  # Or None to use CMC_API env var
    start_year=2020,
    limit=100,
    delay_seconds=1.5  # Respect API rate limits
)

# Save to CSV
df.to_csv('historical_top100_quarterly.csv', index=False)
```

### Method 3: Run Example Script

```bash
export CMC_API="your-api-key-here"
python3 example_historical_fetch.py
```

## Function Parameters

```python
fetch_historical_top100_quarterly(
    api_key=None,          # API key (or set CMC_API env var)
    start_year=2020,       # Starting year
    end_date=None,         # End date (default: today)
    limit=100,             # Coins per quarter (1-5000)
    convert='USD',         # Currency conversion
    delay_seconds=1        # Delay between API calls
)
```

## Output Data Schema

The function returns a pandas DataFrame with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| `snapshot_date` | str | Date of snapshot (YYYY-MM-DD) |
| `quarter` | str | Quarter identifier (e.g., "2020-Q1") |
| `symbol` | str | Cryptocurrency symbol (e.g., "BTC") |
| `name` | str | Full name (e.g., "Bitcoin") |
| `cmc_rank` | int | Rank by market cap (1-100) |
| `market_cap` | float | Market capitalization in USD |
| `price` | float | Price in USD |
| `volume_24h` | float | 24-hour trading volume |
| `percent_change_24h` | float | 24-hour price change % |
| `percent_change_7d` | float | 7-day price change % |
| `market_cap_dominance` | float | Market cap dominance % |
| `circulating_supply` | float | Circulating supply |
| `total_supply` | float | Total supply |
| `max_supply` | float | Maximum supply |

## Example Output

```
snapshot_date  quarter  cmc_rank symbol   name          market_cap
2020-03-31     2020-Q1  1        BTC      Bitcoin       120000000000
2020-03-31     2020-Q1  2        ETH      Ethereum      15000000000
2020-03-31     2020-Q1  3        XRP      XRP           8000000000
...
2024-12-31     2024-Q4  1        BTC      Bitcoin       850000000000
2024-12-31     2024-Q4  2        ETH      Ethereum      380000000000
```

## Rate Limits and Best Practices

### API Rate Limits
- **Basic Plan**: 333 calls/day, 10,000 calls/month
- **Hobbyist Plan**: 1,000 calls/day, 30,000 calls/month
- Use `delay_seconds` parameter to respect rate limits

### Estimated Time
- **2020 to 2025** (20 quarters): ~20-30 seconds with 1.5s delay
- **2015 to 2025** (40 quarters): ~60 seconds with 1.5s delay

### Cost Optimization
1. **Cache Results**: Save data to CSV and reuse
2. **Incremental Updates**: Only fetch new quarters
3. **Use Larger Delays**: Prevent hitting rate limits

## Data Analysis Examples

### 1. Always in Top 100
```python
# Find coins that appeared in all quarters
coin_quarters = df.groupby('symbol')['quarter'].nunique()
total_quarters = df['quarter'].nunique()
always_top100 = coin_quarters[coin_quarters == total_quarters]
print(f"Always in top 100: {always_top100.index.tolist()}")
```

### 2. New Entrants by Quarter
```python
# Track when coins first entered top 100
first_appearance = df.groupby('symbol')['snapshot_date'].min()
for quarter in sorted(df['quarter'].unique()):
    quarter_coins = df[df['quarter'] == quarter]['symbol'].unique()
    print(f"{quarter}: {len(quarter_coins)} coins")
```

### 3. Market Cap Evolution
```python
# Track market cap changes for specific coin
btc_data = df[df['symbol'] == 'BTC'][['quarter', 'market_cap', 'cmc_rank']]
print(btc_data.to_string(index=False))
```

### 4. Ranking Volatility
```python
# Find coins with most volatile rankings
rank_volatility = df.groupby('symbol')['cmc_rank'].std()
most_volatile = rank_volatility.nlargest(10)
print("Most volatile rankings:", most_volatile)
```

## Troubleshooting

### Error: "No data was successfully fetched"
**Causes**:
1. Invalid or expired API key
2. Free tier plan (historical data requires paid plan)
3. Network connectivity issues

**Solutions**:
- Verify API key: `echo $CMC_API`
- Check API plan at https://coinmarketcap.com/api/
- Test with current data endpoint first

### Error: "Rate limit exceeded"
**Solutions**:
- Increase `delay_seconds` parameter
- Upgrade API plan for higher limits
- Spread requests over multiple days

### Missing Dates
- Some historical dates may not have data
- Function will skip failed dates and continue
- Check `failed_dates` list in output

## API Pricing

| Plan | Price | Daily Calls | Monthly Calls | Historical Data |
|------|-------|-------------|---------------|-----------------|
| Free | $0 | 333 | 10,000 | ❌ No |
| Basic | $29/mo | 333 | 10,000 | ✅ Yes |
| Hobbyist | $79/mo | 1,000 | 30,000 | ✅ Yes |
| Startup | $299/mo | 3,334 | 100,000 | ✅ Yes |

Get API key: https://coinmarketcap.com/api/

## Next Steps

After fetching historical data, you can:
1. **Backtest Strategies**: Test trading strategies on historical top 100
2. **Analyze Trends**: Study market cap concentration over time
3. **Build Indices**: Create custom crypto indices
4. **Risk Analysis**: Understand volatility and ranking changes
5. **Portfolio Optimization**: Size factor analysis based on market cap

## Related Files

- `fetch_coinmarketcap_data.py` - Main implementation
- `example_historical_fetch.py` - Usage examples with analysis
- `backtest_size_factor.py` - Size factor backtesting using market cap data
- `SIZE_FACTOR_README.md` - Size factor strategy documentation
