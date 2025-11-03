# DefiLlama Data Integration Guide

**Date:** 2025-11-03  
**Status:** ✅ Complete  
**Branch:** `cursor/scrape-defillama-dashboard-aa53`

## Executive Summary

Successfully integrated DefiLlama's **free public API** (no scraping needed!) to fetch comprehensive DeFi metrics for crypto factor analysis. The integration enables new factor signals based on:

- **Utility Yield:** Daily fees / TVL (revenue generation efficiency)
- **On-chain Yield:** Staking and lending APYs
- **TVL Data:** Total Value Locked across protocols
- **DEX Liquidity:** Volume and liquidity metrics

## Key Finding: DefiLlama API is FREE! 🎉

**Good news:** DefiLlama's API is completely free for public data access. No need for web scraping.

### Available Data (All Free)
- ✅ 6,623 protocols with TVL data
- ✅ 1,423 protocols with fee/revenue data
- ✅ 18,882 yield pools
- ✅ 908 DEXs with volume data
- ✅ Real-time price data for major coins

## Implementation

### 1. Data Fetching Scripts

#### `data/scripts/fetch_defillama_data.py`
Main data fetcher that pulls from DefiLlama API:

```python
# Usage
python3 data/scripts/fetch_defillama_data.py
```

**Fetches:**
- Protocol TVL (top 200 by size)
- Daily fees and revenue (utility yield calculation)
- Yield pools (18,882 pools with APYs)
- DEX liquidity and volume data

**Output Files:**
- `data/raw/defillama_utility_yields_YYYYMMDD.csv`
- `data/raw/defillama_yields_YYYYMMDD.csv`
- `data/raw/defillama_dex_data_YYYYMMDD.csv`
- `data/raw/defillama_tvl_YYYYMMDD.csv`

**Rate Limiting:** Built-in 0.3s delay between requests to be respectful

#### `data/scripts/map_defillama_to_universe.py`
Maps DeFi protocol data to your tradeable universe (170 coins):

```python
# Usage
python3 data/scripts/map_defillama_to_universe.py
```

**Mapping Strategy:**
1. Direct symbol matching (AAVE → AAVE, UNI → UNI)
2. Protocol token mapping (Sky → MKR, dYdX V3 → DRIFT)
3. Yield pool aggregation (multiple staking pools per token)

**Output:**
- `data/raw/defillama_factors_YYYYMMDD.csv` - Combined factor data

**Results (Current):**
- 46 tradeable tokens with DeFi data
- 29 tokens with utility yield data
- 24 tokens with on-chain yield data
- 7 tokens with both metrics

### 2. Factor Signal Generation

#### `signals/calc_utility_yield_factor.py`
Generates factor signals based on DefiLlama data:

```python
# Usage
python3 signals/calc_utility_yield_factor.py
```

**Signal Types:**
1. **Total Yield:** Utility yield + On-chain yield
2. **Utility Yield Only:** Protocol fee generation efficiency
3. **On-chain Yield Only:** Staking/lending APYs
4. **Combined:** Equal-weight average across methods

**Signal Logic:**
- **Long:** Top 20% (percentile >= 80)
- **Short:** Bottom 20% (percentile <= 20)
- **Neutral:** Middle 60%
- **Filter:** Minimum $1M TVL

**Output Files:**
- `signals/utility_yield_total_yield_signals_full.csv`
- `signals/utility_yield_utility_yield_signals_current.csv`
- `signals/utility_yield_onchain_yield_signals_current.csv`
- `signals/utility_yield_combined_signals.csv`

## Current Signal Results

### Combined Signals (Latest Run)

**Long Positions (9 tokens):**
- ARB, BNT, BTC, DRIFT, EIGEN, ENA, OP, RPL, SNX

**Short Positions (8 tokens):**
- (Middle/low yield protocols)

**Top Performers by Total Yield:**
1. **UNI:** 50.88% (Utility: 50.74%, Yield: 0.15%) - $5.4B TVL
2. **PENDLE:** 35.23% (Utility: 0.08%, Yield: 35.15%) - $6.9B TVL
3. **ETHFI:** 29.45% (Utility: 29.45%, Yield: 0.00%) - $1.0B TVL
4. **SUSHI:** 27.82% (Utility: 27.82%, Yield: 0.00%) - $316M TVL
5. **AERO:** 24.28% (Utility: 24.28%, Yield: 0.00%) - $536M TVL

## Data Schema

### Factor Data (`defillama_factors_YYYYMMDD.csv`)

| Column | Description | Example |
|--------|-------------|---------|
| `symbol` | Trading symbol | AAVE, UNI, LINK |
| `tvl` | Protocol TVL (from utility yield) | 37,898,738,567 |
| `daily_fees` | Daily fee generation | 2,628,798 |
| `utility_yield_pct` | Annualized fee yield (%) | 2.53 |
| `total_tvl` | Pool TVL (from yields) | 282,612,120 |
| `weighted_apy` | TVL-weighted APY (%) | 0.20 |
| `total_yield_pct` | Utility + On-chain yield (%) | 2.73 |
| `date` | Data date | 20251103 |

## Factor Theory & Usage

### Utility Yield Factor

**Theory:**
High utility yield indicates protocols generating significant fees relative to TVL, suggesting strong product-market fit and potential token value accrual.

**Calculation:**
```
Utility Yield = (Daily Fees × 365) / TVL × 100
```

**Use Cases:**
- **Value investing:** Identify undervalued DeFi tokens with strong fundamentals
- **Quality screening:** Filter for revenue-generating protocols
- **Risk assessment:** Low utility yield may indicate overvaluation

### On-chain Yield Factor

**Theory:**
Tokens with staking/lending opportunities provide yield, potentially supporting price floors and attracting capital.

**Calculation:**
```
Weighted APY = Σ(Pool APY × Pool TVL) / Total TVL
```

**Use Cases:**
- **Income strategy:** Long high-yield tokens for carry
- **Yield curve analysis:** Compare on-chain yields vs risk-free rate
- **Network security:** Higher staking yields often correlate with network security

### Total Yield Factor

**Theory:**
Combined metric captures both protocol revenue and staking income, providing comprehensive view of token productivity.

**Use Cases:**
- **Multi-factor models:** Combine with momentum, value, sentiment
- **Portfolio construction:** Weight allocations by total yield
- **Sector rotation:** Identify attractive DeFi sub-sectors

## Integration with Existing System

### Data Pipeline Flow

```
DefiLlama API
    ↓
fetch_defillama_data.py (Raw data collection)
    ↓
data/raw/defillama_*.csv
    ↓
map_defillama_to_universe.py (Symbol mapping)
    ↓
data/raw/defillama_factors_*.csv
    ↓
calc_utility_yield_factor.py (Signal generation)
    ↓
signals/utility_yield_*_signals.csv
    ↓
[Backtest & Portfolio Construction]
```

### Recommended Update Frequency

- **Daily:** Price-sensitive factors (for active trading)
- **Weekly:** Moderate rebalancing strategies
- **Monthly:** ✅ Recommended - Captures structural changes, reduces API load

### Automation Script

Create a cron job or scheduled task:

```bash
#!/bin/bash
# update_defillama_factors.sh

cd /workspace

# Fetch latest data
python3 data/scripts/fetch_defillama_data.py

# Map to tradeable universe
python3 data/scripts/map_defillama_to_universe.py

# Generate signals
python3 signals/calc_utility_yield_factor.py

echo "DefiLlama factors updated: $(date)"
```

## Next Steps & Recommendations

### 1. Backtesting (High Priority)
Create backtest to validate signal performance:

```python
# Backtest structure
- Historical DefiLlama data (need to collect time series)
- Price data (already have)
- Test different rebalancing frequencies
- Transaction cost analysis
```

### 2. Factor Combinations
Combine with existing factors:
- **Momentum + Utility Yield:** High yield + positive momentum
- **Value + Total Yield:** Low P/E + high yield
- **Sentiment + Yield:** Social buzz + fundamentals

### 3. Enhanced Data Collection

**Additional Metrics Available:**
- Protocol-specific TVL trends
- Fee breakdown by chain
- Token holder distribution (from Etherscan API)
- Active addresses (requires blockchain APIs)

**Missing Metrics (Need Alternative Sources):**
- ❌ **Active Addresses:** Not directly available from DefiLlama
  - Alternative: Etherscan, Blockchain.com APIs
- ❌ **Net Yield Gap:** Need risk-free rate data
  - Alternative: FRED API for Treasury yields
- ❌ **Liquidity / Market Cap:** Need market cap data
  - Alternative: CoinGecko API (free tier: 50 calls/min)

### 4. Historical Data Collection

Current limitation: Only snapshot data. For backtesting, need historical time series.

**Solution:**
```python
# Collect daily and store incrementally
import sqlite3

def store_daily_snapshot(df, date):
    """Store daily factor snapshot in database"""
    conn = sqlite3.connect('data/defillama_history.db')
    df['snapshot_date'] = date
    df.to_sql('factor_snapshots', conn, if_exists='append', index=False)
    conn.close()
```

## API Documentation

**Base URL:** `https://api.llama.fi`

**Key Endpoints:**
- `/protocols` - All protocols with TVL
- `/overview/fees` - Fee and revenue data
- `/protocol/{slug}` - Detailed protocol data

**Yields URL:** `https://yields.llama.fi`
- `/pools` - All yield pools

**Rate Limits:** None officially stated, but be respectful with 0.3-1s delays

**Documentation:** https://defillama.com/docs/api

## File Structure

```
/workspace/
├── data/
│   ├── scripts/
│   │   ├── fetch_defillama_data.py          # Main data fetcher
│   │   ├── map_defillama_to_universe.py     # Symbol mapper
│   │   └── test_defillama_api.py            # API test script
│   └── raw/
│       ├── defillama_utility_yields_*.csv   # Protocol fee data
│       ├── defillama_yields_*.csv           # Yield pool data
│       ├── defillama_dex_data_*.csv         # DEX volume data
│       ├── defillama_tvl_*.csv              # TVL data
│       └── defillama_factors_*.csv          # Combined factors
├── signals/
│   ├── calc_utility_yield_factor.py         # Signal generator
│   ├── utility_yield_*_signals_full.csv     # All signals
│   └── utility_yield_*_signals_current.csv  # Current long/short
└── docs/
    └── DEFILLAMA_INTEGRATION_GUIDE.md       # This file
```

## Troubleshooting

### Issue: No data for certain tokens
**Solution:** Check symbol mapping in `map_defillama_to_universe.py`. Some protocols use different ticker symbols.

### Issue: Infinite yield values
**Cause:** Protocols with fees but zero TVL (data inconsistency)
**Solution:** Script filters these automatically with `replace([np.inf, -np.inf], np.nan)`

### Issue: API request failures
**Solution:** Check internet connectivity, API status at https://defillama.com/docs/api

## Comparison to Initial Request

**Original ask:** "Can you scrape their main dashboard?"

**Actual solution:** 
- ✅ No scraping needed - free API access
- ✅ More reliable than web scraping
- ✅ Structured data (JSON/CSV)
- ✅ Comprehensive metrics
- ✅ Easy to maintain and update

## Credits & References

- **DefiLlama:** https://defillama.com
- **API Docs:** https://defillama.com/docs/api
- **Yield Dashboard:** https://defillama.com/yields
- **Project GitHub:** https://github.com/DefiLlama

## Support & Maintenance

**Update this integration when:**
1. DefiLlama changes API structure
2. New protocols added to tradeable universe
3. New metrics become available
4. Rate limiting policies change

**Contact:** Check DefiLlama Discord for API support

---

**Status:** ✅ Production Ready  
**Last Updated:** 2025-11-03  
**Version:** 1.0.0
