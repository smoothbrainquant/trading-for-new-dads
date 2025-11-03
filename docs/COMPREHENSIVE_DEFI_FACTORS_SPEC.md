# Comprehensive DeFi Factors Specification

**Date:** 2025-11-03  
**Status:** ✅ Complete  
**Branch:** `cursor/scrape-defillama-dashboard-aa53`

## Overview

This document specifies the five comprehensive DeFi factors that combine protocol fundamentals, tokenomics, and market dynamics to identify high-quality crypto assets.

## Factors Implemented

### 1. Fee Yield %
**Formula:** `annualized fees ÷ FDV (or MC) × 100`

**Interpretation:**
- Measures revenue generation relative to token valuation
- High fee yield = strong value accrual to token holders
- Similar to earnings yield in equity markets

**Example:**
- MKR: 207.70% (generating $1,167,201 daily fees with $205M FDV)
- UNI: 48.03% (generating $7,551,412 daily fees with $5.7B FDV)

**Signal:** Long tokens with high fee yield (top 20%)

---

### 2. Emission/Incentive Yield %
**Formula:** `annualized emission value ÷ FDV × 100`

**Calculation:**
```
emission_value_annual = TVL × reward_apy / 100
emission_yield = emission_value_annual / FDV × 100
```

**Interpretation:**
- Measures token dilution from staking/LP rewards
- High emission yield = inflationary tokenomics
- Low emission yield = sustainable token supply

**Example:**
- PENDLE: 15.08% (high emissions to incentivize liquidity)
- AAVE: 1.85% (moderate incentives)
- Most L1s: <0.1% (minimal dilution)

**Signal:** Long tokens with LOW emission yield (less dilution)

---

### 3. Net Yield %
**Formula:** `Fee Yield − Emission Yield`

**Interpretation:**
- Net value accrual after accounting for dilution
- Positive net yield = sustainable economics
- Negative net yield = paying more in emissions than earning in fees

**Example:**
- MKR: +207.70% (pure fee accrual, no emissions)
- LDO: +108.91% (high fees, low emissions)
- PENDLE: -14.46% (emissions exceed fees)

**Signal:** Long tokens with positive net yield

---

### 4. Revenue Productivity %
**Formula:** `annualized fees ÷ TVL × 100`

**Interpretation:**
- Efficiency of capital deployment
- How much revenue per dollar of TVL
- High productivity = efficient protocol design

**Example:**
- KNC: 262.49% (small TVL but generating fees)
- UNI: 50.48% (massive fees relative to TVL)
- ETHFI: 29.45% (efficient restaking)

**Signal:** Long tokens with high revenue productivity

---

### 5. Turnover %
**Formula:** `24h spot volume ÷ FDV × 100`

**Interpretation:**
- Liquidity and velocity proxy
- High turnover = liquid, actively traded
- Can indicate speculative interest or genuine usage

**Example:**
- USDT: 37.15% (ultimate liquidity vehicle)
- SNX: 31.95% (high trading activity)
- SUSHI: 11.92% (active DEX)

**Signal:** Long tokens with high turnover (liquid markets)

---

## Combined Multi-Factor Model

**Weights:**
```python
composite_score = (
    fee_yield × 0.25 +          # Revenue generation
    -emission_yield × 0.15 +     # Penalize dilution
    net_yield × 0.30 +           # Net value accrual (highest weight)
    revenue_productivity × 0.20 + # Capital efficiency
    turnover × 0.10              # Liquidity (lowest weight)
)
```

**Rationale:**
- Net yield (30%): Most important - captures sustainable economics
- Fee yield (25%): Revenue generation capability
- Revenue productivity (20%): Capital efficiency
- Emission yield (15%): Dilution penalty
- Turnover (10%): Liquidity/tradability

## Top Performers (Current)

### By Fee Yield
1. **MKR**: 207.70% - Maker generates massive fees
2. **LDO**: 108.91% - Lido's dominant ETH staking
3. **SUSHI**: 62.01% - DEX fees
4. **UNI**: 48.03% - Largest DEX by volume
5. **CAKE**: 32.75% - PancakeSwap multi-chain

### By Net Yield (Sustainable)
1. **MKR**: 207.70% - No emissions, pure fees
2. **LDO**: 108.91% - Minimal dilution
3. **SUSHI**: 62.01% - Sustainable model
4. **UNI**: 48.03% - Low emission, high fees
5. **CAKE**: 32.75% - Balanced tokenomics

### By Revenue Productivity
1. **KNC**: 262.49% - Hyper-efficient
2. **PYTH**: 84.83% - Oracle revenues
3. **UNI**: 50.48% - Efficient DEX
4. **ETHFI**: 29.45% - Restaking efficiency
5. **SUSHI**: 27.82% - Multi-chain efficiency

### Combined Multi-Factor (Top 10 Long)
1. ALGO - Low valuation L1
2. ADA - Stable L1 fundamentals
3. SUI - Emerging L1
4. ENS - Domain name protocol
5. XTZ - Proof-of-stake L1
6. DRIFT - Perps DEX
7. DAI - Stablecoin with utility
8. BTC - Store of value
9. BNB - Exchange token
10. PENDLE - (Negative score but in portfolio)

## Data Sources

### DefiLlama API (Free)
- Protocol fees (24h and historical)
- TVL (Total Value Locked)
- Reward APYs (staking/lending incentives)
- 6,623 protocols tracked

### CoinGecko API (Free)
- Fully Diluted Valuation (FDV)
- Market Capitalization
- 24h Spot Volume
- Current Price
- 167/170 tokens mapped

## Implementation

### Scripts Created

1. **`data/scripts/fetch_defillama_data.py`**
   - Fetches protocol fees, TVL, yields
   - Output: `defillama_*.csv` files

2. **`data/scripts/map_defillama_to_universe.py`**
   - Maps protocols to tradeable tokens
   - Output: `defillama_factors_*.csv`

3. **`data/scripts/fetch_coingecko_market_data.py`**
   - Fetches FDV, market cap, volume
   - Output: `coingecko_market_data_*.csv`

4. **`signals/calc_comprehensive_defi_factors.py`**
   - Calculates all 5 factors
   - Generates long/short signals
   - Output: `comprehensive_defi_factors_*.csv`

### Output Files

**Data Files:**
- `data/raw/comprehensive_defi_factors_YYYYMMDD.csv` - Complete dataset

**Signal Files:**
- `signals/defi_factor_fee_yield_signals.csv`
- `signals/defi_factor_emission_yield_signals.csv`
- `signals/defi_factor_net_yield_signals.csv`
- `signals/defi_factor_revenue_productivity_signals.csv`
- `signals/defi_factor_turnover_signals.csv`
- `signals/defi_factor_combined_signals.csv` ⭐ **Use this for trading**

## Signal Generation Parameters

**Filters:**
- Minimum FDV: $10M (filter out micro-caps)
- Valid data required for factor calculation

**Thresholds:**
- Long: Top 20% (percentile >= 80)
- Short: Bottom 20% (percentile <= 20)
- Neutral: Middle 60%

**Position Sizing:**
- Equal weight within long/short buckets
- Weight = 1 / num_longs for longs
- Weight = -1 / num_shorts for shorts

## Usage

### Daily Update Workflow

```bash
# 1. Fetch latest data
python3 data/scripts/fetch_defillama_data.py
python3 data/scripts/map_defillama_to_universe.py
python3 data/scripts/fetch_coingecko_market_data.py

# 2. Calculate factors and generate signals
python3 signals/calc_comprehensive_defi_factors.py

# 3. Use combined signals for trading
# File: signals/defi_factor_combined_signals.csv
```

### Reading Signal File

```python
import pandas as pd

# Load signals
signals = pd.read_csv('signals/defi_factor_combined_signals.csv')

# Filter to active positions
longs = signals[signals['signal'] == 'long']
shorts = signals[signals['signal'] == 'short']

# Get weights for portfolio construction
for _, row in longs.iterrows():
    print(f"Long {row['symbol']}: weight={row['weight']:.4f}")
```

## Factor Statistics (Current Snapshot)

| Factor | Mean | Median | Std Dev | Data Coverage |
|--------|------|--------|---------|---------------|
| Fee Yield % | 13.72 | 0.01 | 35.57 | 46 tokens |
| Emission Yield % | 0.37 | 0.00 | 2.23 | 46 tokens |
| Net Yield % | 13.35 | 0.00 | 35.75 | 46 tokens |
| Revenue Productivity % | 12.20 | 0.08 | 42.17 | 43 tokens |
| Turnover % | 5.39 | 3.49 | 6.83 | 46 tokens |

## Theoretical Foundation

### Fee Yield
**Academic Basis:** Similar to earnings yield (E/P ratio) in equity markets

**Crypto Context:**
- Protocols with token sinks (fee burns, buybacks) → higher yield
- Utility tokens capturing protocol value → better fundamentals
- Example: MKR captures all surplus from Maker protocol

### Emission Yield
**Academic Basis:** Dilution analysis from corporate finance

**Crypto Context:**
- High emissions = inflation → negative for holders
- "Vampire attacks" use high emissions temporarily
- Sustainable protocols minimize emissions over time

### Net Yield
**Academic Basis:** Free cash flow yield

**Crypto Context:**
- Positive net yield = protocol pays for itself
- Negative net yield = subsidized growth (unsustainable?)
- Best protocols: high fees, low emissions

### Revenue Productivity
**Academic Basis:** Return on Assets (ROA)

**Crypto Context:**
- TVL as "assets under management"
- High productivity = efficient protocol design
- Low TVL requirement = capital efficient

### Turnover
**Academic Basis:** Trading volume / market cap ratio

**Crypto Context:**
- High turnover = liquid, tradable
- Very high turnover (>50%) may indicate speculation
- Low turnover (<1%) may indicate illiquidity

## Backtesting Recommendations

### Portfolio Construction
```python
# Long-only portfolio
weights = signals[signals['signal'] == 'long']['weight']
returns = calculate_returns(weights)

# Long-short portfolio (market neutral)
combined_weights = signals['weight']  # Includes negative shorts
returns = calculate_returns(combined_weights)
```

### Rebalancing Frequency
- **Monthly:** Recommended (factor stability)
- **Weekly:** Possible (captures shifts)
- **Daily:** Not recommended (high turnover costs)

### Risk Management
- Max position size: 10% per token
- Diversification: Min 10 positions
- Stop loss: Consider -20% individual token stop

## Limitations & Considerations

### Data Quality
1. **DefiLlama Coverage:** Not all tokens have protocol data
   - Only 46/170 tokens have complete metrics
   - L1s without DeFi apps may score poorly

2. **Fee Attribution:** Some tokens capture fees indirectly
   - Example: SOL validators earn fees, but not captured

3. **Emission Calculation:** Simplified model
   - Actual emissions may vary by epoch/period
   - Doesn't account for vesting schedules

### Factor Biases
1. **Fee Yield:** Biased toward DeFi protocols
   - L1s and payment tokens may score low despite utility

2. **Turnover:** May favor memecoins/speculation
   - High turnover ≠ good investment necessarily

3. **Revenue Productivity:** Penalizes stablecoins
   - USDT has low "productivity" but high utility

## Future Enhancements

### Additional Factors (Roadmap)
1. **Active Addresses:** Blockchain API integration
2. **Net Yield Gap:** Compare to risk-free rate (T-bills)
3. **P/F Ratio:** Price / Fees (valuation metric)
4. **Growth Rates:** YoY fee growth, TVL growth
5. **Sticky TVL:** TVL stability (resilience metric)

### Historical Data
- Build time series database
- Calculate rolling averages
- Identify factor momentum

### Risk Factors
- Add volatility normalization
- Include drawdown metrics
- Correlation with BTC/ETH

## References

### Data Sources
- DefiLlama: https://defillama.com
- CoinGecko: https://www.coingecko.com
- Token Terminal: https://tokenterminal.com (alternative)

### Academic Literature
- Sharpe (1964): Capital Asset Pricing Model
- Fama-French (1993): Multi-factor models
- Liu & Tsyvinski (2021): Risks and Returns of Cryptocurrency

### Crypto Research
- Messari: Protocol analysis frameworks
- Delphi Digital: Tokenomics research
- Bankless: DeFi fundamental analysis

---

**Last Updated:** 2025-11-03  
**Version:** 1.0.0  
**Maintained By:** Quant Team
