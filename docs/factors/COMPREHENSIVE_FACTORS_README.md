# Comprehensive DeFi Factors - Quick Start

## ✅ All 5 Factors Implemented

1. **Fee Yield** = annualized fees ÷ FDV
2. **Emission Yield** = annualized incentives ÷ FDV  
3. **Net Yield** = Fee Yield − Emission Yield
4. **Revenue Productivity** = annualized fees ÷ TVL
5. **Turnover** = 24h spot volume ÷ FDV

## Quick Start

```bash
# Run full pipeline
./run_factor_pipeline.sh
```

Or run individually:

```bash
# Step 1: Fetch DefiLlama data (fees, TVL, yields)
python3 data/scripts/fetch_defillama_data.py
python3 data/scripts/map_defillama_to_universe.py

# Step 2: Fetch CoinGecko data (FDV, market cap, volume)
python3 data/scripts/fetch_coingecko_market_data.py

# Step 3: Calculate all factors and generate signals
python3 signals/calc_comprehensive_defi_factors.py
```

## Output Files

**Trading Signals** (use these):
- `signals/defi_factor_combined_signals.csv` ⭐ **Main file**
- `signals/defi_factor_fee_yield_signals.csv`
- `signals/defi_factor_net_yield_signals.csv`
- `signals/defi_factor_revenue_productivity_signals.csv`
- `signals/defi_factor_turnover_signals.csv`
- `signals/defi_factor_emission_yield_signals.csv`

**Raw Data**:
- `data/raw/comprehensive_defi_factors_YYYYMMDD.csv` - All factors

## Current Top Performers

### Fee Yield Leaders (Revenue Generators)
1. MKR: 207.70% - Maker protocol fees
2. LDO: 108.91% - Lido staking fees
3. SUSHI: 62.01% - DEX trading fees
4. UNI: 48.03% - Uniswap volume
5. CAKE: 32.75% - PancakeSwap multi-chain

### Net Yield Leaders (Sustainable Economics)
Same as Fee Yield (these protocols have minimal emissions)

### Revenue Productivity Leaders (Capital Efficient)
1. KNC: 262.49% - Kyber aggregator
2. PYTH: 84.83% - Oracle network
3. UNI: 50.48% - DEX efficiency
4. ETHFI: 29.45% - Restaking protocol
5. SUSHI: 27.82% - Multi-chain DEX

### Combined Multi-Factor (Current Longs)
ALGO, ADA, SUI, ENS, XTZ, DRIFT, DAI, BTC, BNB, PENDLE

## Factor Interpretations

| Factor | Good Signal | Bad Signal |
|--------|-------------|------------|
| Fee Yield | High (>10%) | Low (<1%) |
| Emission Yield | Low (<1%) | High (>10%) |
| Net Yield | Positive | Negative |
| Revenue Productivity | High (>20%) | Low (<1%) |
| Turnover | Moderate (3-15%) | Very Low (<1%) or Very High (>50%) |

## Data Coverage

- **46/170 tokens** have complete DeFi metrics
- **167/170 tokens** have market data (FDV, volume)
- **43/170 tokens** have TVL data

Tokens without coverage: Primarily L1s without DeFi protocols, payment tokens, memecoins

## Update Frequency

**Recommended: Daily**
- CoinGecko rate limit: 50 calls/minute (we use ~10)
- DefiLlama: No official limit (we use 0.3s delay)
- Total runtime: ~2-3 minutes

**Rebalancing: Monthly**
- Factors are relatively stable
- Reduces transaction costs
- Captures structural changes

## Documentation

- `docs/COMPREHENSIVE_DEFI_FACTORS_SPEC.md` - Full specification
- `docs/DEFILLAMA_INTEGRATION_GUIDE.md` - DefiLlama API guide
- `DEFILLAMA_INTEGRATION_SUMMARY.md` - Quick overview

## Example: Using Signals

```python
import pandas as pd

# Load combined signals
signals = pd.read_csv('signals/defi_factor_combined_signals.csv')

# Get long positions
longs = signals[signals['signal'] == 'long'].sort_values('composite_score', ascending=False)

print("Long Positions:")
for _, row in longs.iterrows():
    print(f"{row['symbol']}: "
          f"Score={row['composite_score']:.2f}, "
          f"Weight={row['weight']:.4f}, "
          f"Fee Yield={row['fee_yield_pct']:.2f}%")

# Calculate portfolio allocation
total_long_weight = longs['weight'].sum()
print(f"\nTotal long weight: {total_long_weight:.2f}")
```

## Backtest Template

```python
import pandas as pd
import numpy as np

# Load signals and price data
signals = pd.read_csv('signals/defi_factor_combined_signals.csv')
prices = pd.read_csv('data/raw/historical_prices.csv')  # Your price data

# Simulate portfolio
longs = signals[signals['signal'] == 'long']
portfolio_return = 0

for _, row in longs.iterrows():
    symbol = row['symbol']
    weight = row['weight']
    
    # Get next month return for this symbol
    symbol_return = get_forward_return(prices, symbol, days=30)
    portfolio_return += weight * symbol_return

print(f"Portfolio return: {portfolio_return:.2%}")
```

## Key Insights (Current Data)

1. **DeFi Blue Chips:** MKR, LDO, UNI dominate fee generation
2. **Emission Risk:** PENDLE has -14.46% net yield (high emissions)
3. **Liquidity Leaders:** USDT, SNX have 30%+ turnover
4. **Hidden Gems:** KNC has 262% revenue productivity but small FDV
5. **L1 Opportunity:** ADA, ALGO, SUI score high on composite despite low DeFi fees

## Next Steps

1. **Backtest:** Test historical performance of signals
2. **Optimize:** Adjust factor weights based on backtest
3. **Combine:** Merge with momentum, sentiment factors
4. **Automate:** Schedule daily updates via cron

---

**Status:** ✅ Production Ready  
**Last Updated:** 2025-11-03
