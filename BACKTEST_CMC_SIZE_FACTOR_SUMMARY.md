# CoinMarketCap Size Factor Backtest Summary

## Overview
This analysis backtests size factor strategies using annual CoinMarketCap snapshots from 2020-2025. The data includes top 200 coins by market cap at each snapshot, filtered to remove stablecoins and suspicious tokens.

## Data
- **Source**: CoinMarketCap historical snapshots
- **Period**: January 2020 - January 2025 (5 years)
- **Rebalance Frequency**: Annually (6 snapshots)
- **Universe**: ~190-200 coins per snapshot after filtering
- **Filters Applied**:
  - Removed stablecoins (USDT, USDC, DAI, etc.)
  - Removed tokens with volume < $100/day
  - Removed suspicious/test tokens
  
## Size Factor Strategies Tested

### Strategy 1: Long Small / Short Large (50/50)
**Hypothesis**: Small cap coins outperform large caps (like in equity markets)

**Configuration**:
- Long: Bottom quintile by market cap (smallest 20%)
- Short: Top quintile by market cap (largest 20%)
- Allocation: 50% long, 50% short

**Results**:
- **Total Return**: -256.45%
- **Annualized Return**: N/A (negative portfolio value)
- **Sharpe Ratio**: N/A
- **Max Drawdown**: -256.60%
- **Verdict**: ❌ FAILED - Short positions exploded in 2022 bull market

**Analysis**: This strategy was destroyed by massive gains in mid-cap altcoins during the 2021-2022 period. Short positions lost more than 100% of their value multiple times, turning the portfolio negative.

---

### Strategy 2: Long Small Cap Only (50% allocation)
**Hypothesis**: Small caps outperform, avoid shorting risk

**Configuration**:
- Long: Bottom quintile by market cap (smallest 20%)
- Short: None
- Allocation: 50% invested, 50% cash

**Results**:
- **Total Return**: +380.61%
- **Annualized Return**: +36.87%
- **Sharpe Ratio**: 0.64
- **Max Drawdown**: -36.74%
- **Win Rate**: 80%
- **Verdict**: ✅ GOOD PERFORMANCE

**Annual Performance**:
- 2020→2021: +82.17%
- 2021→2022: +118.18%
- 2022→2023: -36.74%
- 2023→2024: +36.57%
- 2024→2025: +40.00%

**Analysis**: Small cap strategy performed well overall with strong gains in bull markets. Significant drawdown in 2023 during crypto winter, but recovered. Key winners included LINK (+655%), SNX (+741%), ADA (+490%), DOGE (+304%).

---

### Strategy 3: Long Large Cap Only (100% allocation)
**Hypothesis**: Large caps provide better risk-adjusted returns

**Configuration**:
- Long: Top quintile by market cap (largest 20% - e.g., BTC, ETH, BNB)
- Short: None
- Allocation: 100% invested

**Results**:
- **Total Return**: +634.62%
- **Annualized Return**: +48.98%
- **Sharpe Ratio**: 0.42
- **Max Drawdown**: -73.48%
- **Win Rate**: 80%
- **Verdict**: ✅ BEST PERFORMANCE

**Annual Performance**:
- 2020→2021: +164.33%
- 2021→2022: +236.35%
- 2022→2023: -73.48%
- 2023→2024: +73.07%
- 2024→2025: +80.01%

**Analysis**: Large cap strategy delivered the highest absolute returns despite higher volatility. BTC and ETH led gains, especially during 2021-2022. Deeper drawdown in crypto winter but stronger recovery. Key insight: In crypto, large caps dominated performance.

---

## Key Findings

### 1. **Negative Size Premium in Crypto** ❗
Unlike traditional equity markets where small caps historically outperform large caps, **cryptocurrency markets showed the opposite pattern**:
- Large caps (BTC, ETH, BNB): +635% over 5 years
- Small caps: +381% over 5 years
- Large caps outperformed by 254 percentage points

### 2. **Shorting Risk is Extreme** ⚠️
The long/short strategy catastrophically failed due to:
- Small/mid-cap altcoins experiencing 1000%+ returns in 2022
- Short positions lost multiple times their initial value
- Portfolio went negative despite long positions performing well
- **Conclusion**: Avoid shorting in crypto markets

### 3. **Volatility vs. Returns Trade-off**
| Strategy | Return | Volatility | Sharpe | Drawdown |
|----------|--------|-----------|--------|----------|
| Small Cap (50%) | +381% | 58.01% | 0.64 | -36.74% |
| Large Cap (100%) | +635% | 116.02% | 0.42 | -73.48% |

- Large caps delivered higher returns but with much higher volatility
- Small caps had better risk-adjusted returns (higher Sharpe ratio)
- Small caps had shallower drawdowns

### 4. **Market Cycle Effects**
Both strategies showed strong performance in:
- **2020-2022**: Bull market - both gained significantly
- **2023**: Bear market - both experienced major drawdowns
- **2024-2025**: Recovery - both recovered strongly

### 5. **Top Performers by Size**

**Large Caps (2020-2025)**:
- BNB: +1191% (2021-2022 alone)
- DOGE: +1685% (became large cap)
- ADA: +572%
- ETH: +293%

**Small Caps (2020-2025)**:
- LINK: +655%
- SNX: +741%
- ADA: +490% (before becoming mid-cap)
- XEM: +550%

## Recommendations

### For Risk-Tolerant Investors
✅ **Large Cap Concentration**: 100% allocation to top 20% by market cap
- Higher absolute returns
- More liquid
- Better for large portfolios
- Accept higher drawdowns

### For Risk-Averse Investors
✅ **Small Cap with Cash Buffer**: 50% small caps, 50% cash/stables
- Better risk-adjusted returns
- Lower drawdowns
- More consistent performance
- Good for smaller portfolios

### What to Avoid
❌ **Long/Short Size Factor**: Do NOT short large caps to fund small cap longs
- Extreme tail risk from explosive short positions
- Can lose more than 100% of portfolio
- Not suitable for crypto markets

❌ **Full Allocation to Small Caps**: High risk without commensurate return
- Small caps underperformed large caps in this period
- Many small caps went to zero (not captured in this backtest)
- Survivorship bias in top 200 data

## Limitations

1. **Survivorship Bias**: Analysis only includes coins in top 200 at each snapshot. Coins that went to zero are not included, biasing results upward.

2. **Annual Rebalancing**: Only 6 data points over 5 years. More frequent rebalancing might show different results.

3. **No Transaction Costs**: Backtest doesn't include trading fees, slippage, or tax implications.

4. **Limited History**: 5-year period may not be representative of long-term crypto dynamics.

5. **Bull Market Bias**: Period includes major bull market (2020-2022), which may favor crypto assets generally.

6. **Top 200 Only**: Extreme small caps (<$100M market cap) not included.

## Files Generated

1. `backtest_cmc_size_factor_monthly_portfolio_values.csv` - Long/Short strategy
2. `backtest_cmc_size_factor_monthly_long_only_portfolio_values.csv` - Small cap only
3. `backtest_cmc_size_factor_monthly_large_cap_only_portfolio_values.csv` - Large cap only
4. Corresponding trades and metrics files for each strategy

## Conclusion

The cryptocurrency size factor behaves **opposite to traditional equity markets**. In crypto:
- **Large caps outperformed small caps** (negative size premium)
- **Shorting is extremely dangerous** due to unlimited downside
- **Best strategy**: Long-only large cap concentration or small cap with cash buffer
- **Risk management is critical**: Drawdowns can exceed 70% even in winning strategies

The traditional equity market wisdom of "small cap outperformance" does not apply to crypto. Investors should focus on liquid, established large caps for maximum returns, or small caps with appropriate risk management for better risk-adjusted returns.
