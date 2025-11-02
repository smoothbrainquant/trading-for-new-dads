# Leverage and Dilution Data Update System

## Overview

This document describes the automated data update system for leverage and dilution factor strategies. The system ensures that all factor data is fresh and properly sourced from Open Interest (OI) and Market Cap data.

## Data Pipeline

The data update pipeline follows this sequence:

```
1. Open Interest Data (Coinalyze API)
   ?
2. Market Cap Data (CoinMarketCap API)
   ?
3. Leverage Metrics Calculation (OI / Market Cap)
   ?
4. Dilution Metrics Calculation (Supply Analysis)
```

## Automatic Updates

### Main Trading Script Integration

When running `main.py` with leverage or dilution strategies, the system automatically:

1. **Detects active strategies**: Checks if `leverage_inverted` or `dilution` strategies are enabled
2. **Refreshes data**: Runs the data update pipeline to ensure fresh data
3. **Reports status**: Provides clear feedback on data freshness

Example output:
```
[Factor Data Check] Leverage/Dilution strategies active - checking data freshness...

================================================================================
FACTOR DATA REFRESH CHECK
================================================================================
? Leverage strategy active - requires OI + Market Cap data
? Dilution strategy active - requires Market Cap data

Running data refresh pipeline...
This will update: OI ? Market Cap ? Leverage ? Dilution

? Factor data refresh completed successfully
```

### What Gets Updated

- **Market Cap Data**: Latest cryptocurrency market capitalizations from CoinMarketCap
- **Leverage Metrics**: OI/Market Cap ratios for all coins (calculated from fresh OI + Market Cap data)
- **Dilution Metrics**: Token supply metrics and dilution rates from CoinMarketCap
- **Open Interest Data**: (Optional) Can be skipped for faster updates, as OI data is large and slow

## Manual Data Refresh

### Full Refresh (All Data)

To manually refresh all factor data including OI:

```bash
python3 data/scripts/refresh_all_factor_data.py
```

This will:
1. Refresh Open Interest data (slow, ~20-30 minutes)
2. Refresh Market Cap data
3. Calculate Leverage metrics
4. Calculate Dilution metrics

### Fast Refresh (Skip OI)

For faster updates that skip OI refresh:

```bash
python3 data/scripts/refresh_all_factor_data.py --skip-oi
```

This will:
1. Skip OI refresh (uses existing OI data)
2. Refresh Market Cap data
3. Calculate Leverage metrics with existing OI
4. Calculate Dilution metrics

### Check Status Only

To check data freshness without refreshing:

```bash
python3 data/scripts/refresh_all_factor_data.py --check-only
```

### Force Refresh

To force refresh even if data appears fresh:

```bash
python3 data/scripts/refresh_all_factor_data.py --force
```

## Data Dependencies

### Leverage Strategy (`leverage_inverted`)

**Required Data:**
- Open Interest data: `data/raw/historical_open_interest_*.csv`
- Market Cap data: `data/raw/crypto_marketcap_latest.csv`
- Funding Rates data: `data/raw/historical_funding_rates_*.csv`

**Calculated Metrics:**
- OI/Market Cap ratio (primary leverage indicator)
- Funding rates (cost of leverage)
- OI growth trends
- Leverage scores

**Output:**
- `signals/leverage_ratios_top50_*.csv`
- `signals/historical_leverage_weekly_*.csv` (for historical strategy)

### Dilution Strategy (`dilution`)

**Required Data:**
- Market Cap data: `data/raw/crypto_marketcap_latest.csv`
- Historical dilution data: `crypto_dilution_historical_*.csv`

**Calculated Metrics:**
- Circulating supply percentage
- Potential dilution percentage
- Dilution velocity (unlock rate)
- Locked token amounts

**Output:**
- `crypto_dilution_top50.csv`

## API Requirements

### CoinMarketCap API (Required)

Set the `CMC_API` environment variable:

```bash
export CMC_API="your-coinmarketcap-api-key"
```

Used for:
- Market cap data (both strategies)
- Supply data (dilution strategy)

### Coinalyze API (Optional for fast refresh)

Set the `COINALYZE_API` environment variable:

```bash
export COINALYZE_API="your-coinalyze-api-key"
```

Used for:
- Open Interest data (leverage strategy)
- Only needed for full refresh with `--force` or when OI data is stale

## File Updates

The system automatically detects and uses the latest files:

### Leverage Analysis Scripts

- `signals/analyze_leverage_ratios.py` - Current leverage metrics
- `signals/analyze_leverage_ratios_historical.py` - Historical leverage analysis

These scripts now automatically:
- Find the latest OI data file (using pattern matching)
- Find the latest market cap file
- Find the latest funding rates file
- Provide clear error messages if data is missing

### Dilution Analysis Scripts

- `data/scripts/fetch_crypto_dilution_top50.py` - Dilution metrics calculation

This script fetches fresh supply data from CoinMarketCap API.

## Troubleshooting

### "Market cap data not found"

Run:
```bash
python3 data/scripts/fetch_coinmarketcap_data.py --output data/raw/crypto_marketcap_latest.csv
```

### "No Open Interest data found"

Run:
```bash
python3 data/scripts/refresh_oi_data.py
```

### "API key not found"

Ensure environment variables are set:
```bash
export CMC_API="your-key"
export COINALYZE_API="your-key"
```

### Data refresh timeout

If the data refresh times out (>5 minutes), you can:
1. Run manual refresh in background: `python3 data/scripts/refresh_all_factor_data.py &`
2. Use existing data for current run
3. Check API rate limits and network connectivity

## Best Practices

1. **Daily Trading**: Use automatic refresh in `main.py` (default behavior)
2. **Intraday Trading**: Use `--skip-oi` for faster refreshes
3. **Weekly Full Refresh**: Run full refresh with OI data weekly for comprehensive updates
4. **Monitor Warnings**: Pay attention to data freshness warnings in trading output

## Integration with Strategies

### Leverage Inverted Strategy

File: `execution/strategies/leverage_inverted.py`

Reads: `signals/historical_leverage_weekly_*.csv`

Strategy logic:
- LONG: Bottom 10 coins by OI/Market Cap (least leveraged - fundamentals)
- SHORT: Top 10 coins by OI/Market Cap (most leveraged - speculation)

### Dilution Strategy

File: `execution/strategies/dilution.py`

Reads: `crypto_dilution_historical_*.csv`

Strategy logic:
- LONG: Low dilution velocity (slow unlock)
- SHORT: High dilution velocity (aggressive unlock)

## Performance

- **Full refresh**: ~20-30 minutes (includes OI data download)
- **Fast refresh**: ~2-5 minutes (skips OI data download)
- **Leverage calculation**: ~30 seconds
- **Dilution calculation**: ~30 seconds

## Summary

The leverage and dilution data update system ensures that:

1. ? Data is automatically refreshed before trading
2. ? All metrics are calculated from fresh OI and Market Cap data
3. ? Scripts automatically find and use the latest data files
4. ? Clear error messages guide users to resolve data issues
5. ? Fast refresh option available for intraday updates

This behavior establishes the proper dependency chain: **OI Data + Market Cap Data ? Leverage & Dilution Metrics ? Trading Strategies**
