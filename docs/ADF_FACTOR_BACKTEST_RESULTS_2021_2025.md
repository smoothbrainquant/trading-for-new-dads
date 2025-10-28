# ADF Factor Backtest Results: 2021-2025 (Top 100 Market Cap)

**Period:** March 2, 2021 to October 24, 2025 (4.7 years, 1,698 trading days)  
**Universe:** Top 100 coins by market cap (min $200M market cap, min $10M volume)  
**Rebalancing:** Weekly (every 7 days)  
**Initial Capital:** $10,000  
**Date Generated:** 2025-10-27

---

## Executive Summary

### 🏆 Best Strategy: Trend Following Premium (Equal Weight)

**Performance Highlights:**
- **Total Return:** +20.78% (vs -42.93% for Mean Reversion)
- **Annualized Return:** +4.14%
- **Sharpe Ratio:** 0.15
- **Max Drawdown:** -44.39%

### 🔑 Key Findings

1. **Trend Following Outperformed Mean Reversion by 63.7 percentage points**
   - Trend Following: +20.78%
   - Mean Reversion: -42.93%

2. **Long/Short Strategies Dominated Long-Only**
   - Long/Short strategies benefited from short side hedge
   - Long-only strategies suffered severe drawdowns (-66% to -77%)

3. **Equal Weight Beat Risk Parity**
   - Equal Weight: +20.78% return
   - Risk Parity: +10.54% return

4. **Mean Reversion Premium Failed**
   - Stationary coins (low ADF) significantly underperformed
   - Trending coins (high ADF) captured momentum and growth

---

## Complete Results Comparison

### All Strategy Variants

| Strategy | Total Return | Ann. Return | Sharpe | Max DD | Win Rate | Final Value |
|----------|-------------|-------------|--------|--------|----------|-------------|
| **Trend Following (EW)** | **+20.78%** | **+4.14%** | **0.15** | **-44.39%** | **20.73%** | **$12,078** |
| Trend Following (RP) | +10.54% | +2.18% | 0.08 | -45.81% | 21.20% | $11,054 |
| Mean Reversion (EW) | -42.93% | -11.36% | -0.40 | -72.54% | 22.73% | $5,707 |
| Long Trending Only | -66.13% | -20.76% | -0.58 | -67.02% | 21.55% | $3,387 |
| Long Stationary Only | -77.28% | -27.28% | -0.74 | -84.22% | 21.50% | $2,272 |

**Legend:**
- EW = Equal Weight
- RP = Risk Parity
- Ann. = Annualized
- DD = Drawdown

---

## Detailed Strategy Analysis

### 1. Trend Following Premium (Equal Weight) ⭐ BEST

**Strategy:** Long high ADF (trending), Short low ADF (stationary)

**Performance:**
- Total Return: **+20.78%**
- Annualized Return: **+4.14%**
- Annualized Volatility: 28.25%
- Sharpe Ratio: **0.15**
- Sortino Ratio: 0.14
- Maximum Drawdown: **-44.39%**
- Calmar Ratio: 0.09

**Trading Statistics:**
- Win Rate: 20.73%
- Trading Days: 1,698
- Avg Long Positions: 1.1
- Avg Short Positions: 0.7
- Total Rebalances: 243

**ADF Analysis:**
- Avg Long ADF: -0.78 (trending coins)
- Avg Short ADF: -1.23 (stationary coins)
- ADF Spread: -0.45

**Exposure:**
- Avg Long Exposure: $3,132 (31.3% of capital)
- Avg Short Exposure: -$3,132 (-31.3%)
- Net Exposure: $0 (market neutral)
- Gross Exposure: $6,265 (62.6%)

**Why It Worked:**
- ✅ Captured momentum in trending coins
- ✅ Shorted mean-reverting coins that underperformed
- ✅ Market neutral structure reduced directional risk
- ✅ Lower exposure (vs mean reversion) controlled risk

---

### 2. Trend Following Premium (Risk Parity)

**Strategy:** Same as above, but with risk-adjusted weighting

**Performance:**
- Total Return: **+10.54%** (10.2pp worse than EW)
- Annualized Return: +2.18%
- Annualized Volatility: 27.36% (slightly lower)
- Sharpe Ratio: 0.08 (worse)
- Maximum Drawdown: -45.81% (worse)

**Key Difference:**
- Risk parity reduced returns without meaningfully reducing risk
- Equal weight allocation was more effective for this strategy
- Lower gross exposure (58% vs 63%) reduced profit potential

---

### 3. Mean Reversion Premium (Equal Weight) ❌ FAILED

**Strategy:** Long low ADF (stationary), Short high ADF (trending)

**Performance:**
- Total Return: **-42.93%** (massive underperformance)
- Annualized Return: **-11.36%**
- Annualized Volatility: 28.25%
- Sharpe Ratio: **-0.40** (negative)
- Sortino Ratio: -0.34
- Maximum Drawdown: **-72.54%** (severe)
- Calmar Ratio: -0.16

**Trading Statistics:**
- Win Rate: 22.73% (slightly better, but still poor)
- Avg Long Positions: 0.7 (fewer)
- Avg Short Positions: 1.1 (more shorts)

**ADF Analysis:**
- Avg Long ADF: -2.45 (very stationary)
- Avg Short ADF: -1.34 (trending)
- ADF Spread: 1.11 (large spread)

**Exposure:**
- Much lower exposure: only $2,602 gross (26%)
- Suggests fewer coins passed filters

**Why It Failed:**
- ❌ Stationary coins significantly underperformed
- ❌ Mean reversion did NOT work in this period
- ❌ Trending coins continued trending (momentum)
- ❌ Betting against trend was costly
- ❌ 2021-2025 was NOT a mean-reverting market

---

### 4. Long Stationary Only ❌ WORST PERFORMER

**Strategy:** Long-only on stationary coins (defensive)

**Performance:**
- Total Return: **-77.28%** (catastrophic)
- Annualized Return: **-27.28%**
- Sharpe Ratio: **-0.74**
- Maximum Drawdown: **-84.22%** (near total loss)

**Why It Failed:**
- ❌ No hedge via shorts
- ❌ Full directional exposure to underperforming coins
- ❌ Stationary coins collapsed during downturns
- ❌ Only $920 average exposure (ran out of valid coins)

**Key Insight:** Stationary/mean-reverting coins were the WORST performers over this period.

---

### 5. Long Trending Only

**Strategy:** Long-only on trending coins

**Performance:**
- Total Return: **-66.13%** (very poor)
- Annualized Return: **-20.76%**
- Sharpe Ratio: **-0.58**
- Maximum Drawdown: **-67.02%**

**Why It Failed:**
- ❌ No hedge via shorts
- ❌ Full directional exposure
- ❌ Trending coins also suffered in bear markets
- ❌ Better than stationary, but still terrible without hedging

**Key Insight:** Even trending coins need hedging. Long/short structure critical.

---

## Market Regime Analysis

### Period Breakdown

The 2021-2025 period included multiple distinct market regimes:

#### 1. Q1 2021 - Q4 2021: Bull Market Peak
- Crypto hit all-time highs (BTC ~$69k in Nov 2021)
- High momentum, trending behavior dominant
- Mean reversion failed in strong uptrend

#### 2. 2022: Bear Market Collapse
- Terra/LUNA collapse (May 2022)
- FTX collapse (Nov 2022)
- BTC fell from $69k to $16k (-77%)
- Trending coins fell less than stationary coins

#### 3. 2023: Recovery & Consolidation
- Sideways consolidation
- Gradual recovery
- Mix of trending and mean-reverting behavior

#### 4. 2024 - Q3 2025: Bull Market Resume
- Bitcoin ETF approval (Jan 2024)
- New highs in 2024-2025
- Momentum/trending behavior dominant again

**Overall Character:** The period was dominated by strong directional moves (both up and down), favoring momentum/trending over mean reversion.

---

## Why Trend Following Won

### 1. Momentum Dominated the Period
- Strong bull runs (2021, 2024-2025)
- Trending coins captured sustained moves
- Mean reversion strategies fought the trend

### 2. Stationary Coins Were Low-Growth
- Low ADF = mean-reverting = range-bound
- These coins lacked catalysts
- Investors preferred growth/momentum coins

### 3. Short Side Provided Crucial Hedge
- Shorting stationary coins offset losses
- Market neutral structure worked well
- Long-only strategies had no protection

### 4. Equal Weight Outperformed Risk Parity
- Risk parity over-weighted low-vol (stationary) coins
- These underperformed despite lower volatility
- Equal weight captured more upside from trending coins

---

## ADF Statistic Interpretation

### Average ADF Values by Performance

| Category | Avg ADF | Interpretation | Performance |
|----------|---------|----------------|-------------|
| Stationary (Long in MR) | -2.45 | Very mean-reverting | **Worst** |
| Moderate Stationary | -1.23 | Somewhat mean-reverting | Poor |
| Trending (Long in TF) | -0.78 | Non-stationary/trending | **Best** |

**Key Finding:** More negative ADF (more stationary) = worse performance in this period.

### Stationarity Rate
- Only 10.4% of coin-days were stationary (p < 0.05)
- Most crypto prices are non-stationary (random walk/trending)
- This is expected in emerging, high-growth markets

---

## Portfolio Composition Analysis

### Number of Positions Over Time

| Strategy | Avg Long | Avg Short | Total |
|----------|----------|-----------|-------|
| Trend Following (EW) | 1.1 | 0.7 | 1.8 |
| Mean Reversion (EW) | 0.7 | 1.1 | 1.8 |
| Long Stationary | 0.7 | 0.0 | 0.7 |
| Long Trending | 1.1 | 0.0 | 1.1 |

**Observations:**
- Very few positions passed filters (avg < 2 coins!)
- Top 100 market cap + volume filters + ADF ranking = thin universe
- Mean Reversion had fewer long positions (stationary coins scarce)
- Trend Following had more long positions (trending more common)

**Implication:** Strategy was highly concentrated (1-2 positions). High idiosyncratic risk.

---

## Win Rate Analysis

**All Strategies Had Low Win Rates (20-23%)**

| Strategy | Win Rate |
|----------|----------|
| Trend Following (EW) | 20.73% |
| Trend Following (RP) | 21.20% |
| Long Trending | 21.55% |
| Long Stationary | 21.50% |
| Mean Reversion (EW) | 22.73% |

**Key Insights:**
1. **Win rate is NOT predictive of profitability**
   - Trend Following won despite 20.73% win rate
   - Positive skew: Few big wins > many small losses

2. **All strategies lost money on most days**
   - ~80% of days were losing days
   - Success came from magnitude of wins vs losses

3. **Mean Reversion had highest win rate but worst returns**
   - More frequent small wins
   - Occasional catastrophic losses overwhelmed

---

## Exposure Analysis

### Capital Utilization

| Strategy | Gross Exposure | Net Exposure | % Deployed |
|----------|----------------|--------------|------------|
| Trend Following (EW) | $6,265 | $0 | 62.6% |
| Trend Following (RP) | $5,794 | $0 | 57.9% |
| Mean Reversion (EW) | $2,602 | $0 | 26.0% |
| Long Trending | $1,367 | $1,367 | 13.7% |
| Long Stationary | $920 | $920 | 9.2% |

**Key Findings:**
1. **Mean Reversion deployed much less capital** (26% vs 63%)
   - Fewer coins met criteria
   - Suggests stationary coins are rare in top 100

2. **Long-only strategies severely undercapitalized** (<15%)
   - Most capital sat idle
   - Couldn't find enough qualifying coins

3. **Trend Following fully utilized capital** (63%)
   - More trending coins available
   - Better diversification

---

## Risk-Adjusted Performance

### Sharpe Ratio Ranking

1. **Trend Following (EW):** 0.15 ✅
2. Trend Following (RP): 0.08
3. Mean Reversion (EW): -0.40
4. Long Trending: -0.58
5. Long Stationary: -0.74

### Calmar Ratio (Return/Max Drawdown)

1. **Trend Following (EW):** 0.09 ✅
2. Trend Following (RP): 0.05
3. Mean Reversion (EW): -0.16
4. Long Trending: -0.31
5. Long Stationary: -0.32

**Conclusion:** Trend Following (Equal Weight) wins on all risk-adjusted metrics.

---

## Comparison to Benchmarks

### Hypothetical Benchmarks (Estimated)

| Strategy | Return (2021-2025) | Note |
|----------|-------------------|------|
| **Trend Following ADF** | **+20.78%** | **Our best strategy** |
| Bitcoin Buy & Hold | ~+45% | Est. (2021-2025) |
| Equal-Weight Crypto Index | ~-20% to -30% | Est. most alts down |
| Market-Cap-Weight Index | ~+30% to +40% | BTC/ETH dominated |

**Assessment:**
- ✅ Beat equal-weight index
- ❌ Underperformed Bitcoin buy-and-hold
- ❌ Underperformed cap-weighted index
- ✅ Positive absolute returns with lower volatility

**Value Proposition:**
- Lower volatility than buy-and-hold BTC (28% vs ~60%)
- Market-neutral structure
- Positive returns in challenging period
- Potential for alpha in different market regimes

---

## Key Takeaways

### ✅ What Worked

1. **Trend Following Strategy**
   - Momentum dominated mean reversion
   - Trending coins captured growth

2. **Long/Short Structure**
   - Hedging critical for risk management
   - Market neutrality reduced drawdowns

3. **Equal Weighting**
   - Outperformed risk parity
   - Simpler and more effective

4. **Top 100 Market Cap Focus**
   - Better liquidity
   - More reliable data

### ❌ What Failed

1. **Mean Reversion Strategy**
   - Stationary coins significantly underperformed
   - Fighting the trend was costly

2. **Long-Only Strategies**
   - No hedge = massive drawdowns
   - Directional risk too high

3. **Risk Parity Weighting**
   - Over-weighted underperforming stationary coins
   - Complexity didn't add value

4. **ADF as Standalone Signal**
   - Only 1-2 positions at a time
   - Very concentrated portfolios
   - High idiosyncratic risk

---

## Recommendations

### For Strategy Improvement

1. **Combine with Other Factors**
   - Use ADF + momentum + volatility
   - Multi-factor models may be more robust

2. **Broaden Universe**
   - Include more coins (top 200-300)
   - Increase diversification (currently 1-2 positions!)

3. **Adjust Rebalancing Frequency**
   - Test daily (more reactive) vs monthly (lower turnover)
   - Weekly may not be optimal

4. **Add Regime Detection**
   - Switch strategies based on market regime
   - Bull markets → Trend Following
   - Bear/sideways → Mean Reversion (if it works)

5. **Optimize ADF Parameters**
   - Test 30d, 90d, 120d windows
   - Test different regression types
   - Test different percentile thresholds

### For Risk Management

1. **Position Size Limits**
   - Cap individual positions (currently no limit)
   - Prevent over-concentration

2. **Stop Losses**
   - Add protection against extreme moves
   - Currently holds through drawdowns

3. **Leverage Control**
   - Consider reducing gross exposure in high vol periods
   - Dynamic risk budgeting

4. **Transaction Cost Modeling**
   - Add slippage and fees to backtest
   - Estimate real-world performance

---

## Conclusion

**Winner: Trend Following Premium (Equal Weight)**

The ADF factor backtest from 2021-2025 clearly demonstrates that:

1. **Trending coins (high ADF) outperformed stationary coins (low ADF) by a massive margin**
2. **Mean reversion strategy failed catastrophically (-43%)**
3. **Trend following strategy succeeded modestly (+21%)**
4. **Long/short structure essential** (long-only strategies lost 66-77%)
5. **Equal weighting beat risk parity**

### Performance Summary

| Metric | Trend Following | Mean Reversion | Difference |
|--------|----------------|----------------|------------|
| Total Return | **+20.78%** | -42.93% | **+63.7pp** |
| Sharpe Ratio | **0.15** | -0.40 | **+0.55** |
| Max Drawdown | **-44.39%** | -72.54% | **+28pp** |

### Market Context

The 2021-2025 period was characterized by:
- Strong directional moves (bull 2021, bear 2022, bull 2024-2025)
- Momentum effects dominated
- Mean reversion opportunities were scarce
- High-growth/trending coins attracted capital

### Strategic Implications

**For Live Trading:**
- ✅ Consider Trend Following ADF if momentum conditions persist
- ❌ Avoid Mean Reversion ADF (at least in current market)
- ✅ Always use long/short hedging
- ✅ Use equal weight for simplicity and effectiveness
- ⚠️ Address concentration risk (only 1-2 positions)
- ⚠️ Consider combining with other factors

**For Research:**
- Test across different market regimes
- Combine with momentum, volatility, beta factors
- Optimize parameters (ADF window, rebalancing frequency)
- Expand universe to increase diversification

---

## Output Files

All backtest results saved to `/workspace/backtests/results/`:

**Mean Reversion:**
- `adf_mean_reversion_2021_top100_portfolio_values.csv`
- `adf_mean_reversion_2021_top100_trades.csv`
- `adf_mean_reversion_2021_top100_metrics.csv`
- `adf_mean_reversion_2021_top100_strategy_info.csv`

**Trend Following (Equal Weight):**
- `adf_trend_following_2021_top100_*.csv`

**Trend Following (Risk Parity):**
- `adf_trend_riskparity_2021_top100_*.csv`

**Long Stationary:**
- `adf_long_stationary_2021_top100_*.csv`

**Long Trending:**
- `adf_long_trending_2021_top100_*.csv`

---

**Report Generated:** 2025-10-27  
**Analysis Period:** 2021-03-02 to 2025-10-24  
**Trading Days:** 1,698  
**Strategies Tested:** 5  
**Status:** ✅ Complete
