# Dilution Factor Backtest - Coverage Analysis

## Executive Summary

The dilution factor backtest shows **exceptional returns (+1,809%)** but has **severe coverage limitations** that significantly impact the reliability and representativeness of these results.

**Critical Finding**: The strategy averaged only **4.3 positions** instead of the target **20 positions** (10 long + 10 short).

---

## Backtest Performance

| Metric | Value |
|--------|-------|
| **Total Return** | +1,809.03% |
| **Annualized Return** | 203.60% |
| **Sharpe Ratio** | 1.034 |
| **Sortino Ratio** | 1.656 |
| **Max Drawdown** | -89.24% |
| **Win Rate** | 50.94% |
| **Test Period** | Feb 2, 2021 - Oct 24, 2025 (1,605 days / 4.4 years) |

---

## Coverage Analysis

### Overall Position Statistics

| Metric | Min | Max | Mean | Median | Target |
|--------|-----|-----|------|--------|--------|
| **Long Positions** | 0 | 4 | 1.4 | 1 | 10 |
| **Short Positions** | 0 | 5 | 2.8 | 3 | 10 |
| **Total Positions** | 0 | 8 | 4.3 | 4 | 20 |

### Coverage Achievement

- **Achieved target (20 positions)**: 0 times (0.0%)
- **Had 15+ positions**: 0 times (0.0%)
- **Had 10+ positions**: 0 times (0.0%)
- **Had <5 positions**: 34 times (59.6%)
- **Maximum positions ever**: 8 (vs target 20)

### Position Coverage by Year

| Year | Avg Total | Avg Long | Avg Short |
|------|-----------|----------|-----------|
| 2021 | 5.8 | 1.9 | 3.9 |
| 2022 | 4.1 | 1.5 | 2.6 |
| 2023 | 3.2 | 0.8 | 2.3 |
| 2024 | 3.7 | 0.9 | 2.8 |
| 2025 | 4.8 | 2.2 | 2.6 |

**Note**: Coverage actually *declined* from 2021 to 2023, then recovered slightly.

### Most Recent 10 Rebalances

| Date | Long | Short | Total |
|------|------|-------|-------|
| 2025-01-01 | 1 | 4 | 5 |
| 2025-02-01 | 2 | 1 | 3 |
| 2025-03-01 | 3 | 1 | 4 |
| 2025-04-01 | 3 | 3 | 6 |
| 2025-05-01 | 4 | 2 | 6 |
| 2025-06-01 | 3 | 1 | 4 |
| 2025-07-01 | 2 | 3 | 5 |
| 2025-08-01 | 2 | 5 | 7 |
| 2025-09-01 | 1 | 3 | 4 |
| 2025-10-01 | 1 | 3 | 4 |

---

## Data Availability Analysis

### Dilution Data Coverage

- **Total dilution records**: 11,600
- **Date range**: 2021-01-01 to 2025-10-01
- **Frequency**: Monthly snapshots (58 dates)
- **Coins per snapshot**: 200 (consistent)
- **Unique coins with dilution data**: 82 only

### Why Low Position Coverage?

The strategy filters through multiple stages:

#### Stage 1: Dilution Signal Calculation
- **Input**: 200 coins per snapshot
- **Output**: ~58 coins with valid dilution velocity
- **Attrition**: 71% filtered out (no circulating supply data)

#### Stage 2: Price Data Matching
- Example from 2025-01-01:
  - **Long candidates (10 targets)**: 6/10 have price data
    - Missing: GT, OKB, THETA, FTT
  - **Short candidates (10 targets)**: 8/10 have price data
    - Missing: BGB, GALA
- **Total with price data**: ~14 out of 20 targets

#### Stage 3: Volatility Calculation
- Requires 90 days of historical returns
- Additional filtering reduces further
- **Final result**: 1-8 positions (avg 4.3)

### Root Causes

1. **Limited dilution data**: Only 82 coins have circulating supply data
2. **Price data gaps**: Not all coins in CMC data are in Hyperliquid price data
3. **Strict volatility requirements**: 90-day lookback filters out newer coins
4. **Monthly rebalancing of dilution data**: Only 58 data points over 4.4 years

---

## Risk Implications

### Concentration Risk

With an average of **4.3 positions** instead of 20:

1. **Individual position impact**: Each position represents ~23% of portfolio (vs expected ~5%)
2. **Idiosyncratic risk**: High exposure to coin-specific events
3. **Diversification failure**: Not achieving intended risk spreading

### Return Attribution

The exceptional +1,809% return is likely driven by:

1. **Lucky picks**: A few concentrated positions with extreme returns
2. **Survivorship bias**: Strategy couldn't short coins without price data
3. **High volatility**: With <5 positions, portfolio volatility is amplied

### Max Drawdown Context

- **Max drawdown**: -89.24%
- With only 4-5 positions, this extreme drawdown makes sense
- A single coin's collapse could cause 20-25% portfolio drawdown
- Multiple simultaneous failures → catastrophic loss

---

## Comparison: Expected vs Actual

| Metric | Expected (20 pos) | Actual (4.3 pos) | Impact |
|--------|-------------------|------------------|--------|
| **Position size** | ~5% each | ~23% each | 4.6x larger |
| **Diversification** | High | Very low | Poor risk mgmt |
| **Idiosyncratic risk** | Diversified away | Fully exposed | High |
| **Strategy reliability** | Representative | Questionable | Luck vs skill |
| **Risk-adjusted returns** | Sharpe ~1.0 | Sharpe 1.034 | Overstated? |

---

## Example: January 2025 Rebalance

**Target**: 10 long + 10 short = 20 positions

**Actual**: 1 long + 4 short = 5 positions

### Selected Positions
- **Long (lowest dilution)**: BNB (-5.57%), possibly ADA, SHIB, etc.
- **Short (highest dilution)**: FET (59.13%), RENDER (46.41%), APE (38.33%), SUI (19.05%)

**Concentration**: 
- 1 long position = 50% of long allocation = 25% of total portfolio
- Each short = 12.5% of short allocation = 6.25% of total portfolio

---

## Recommendations

### For Using These Results

1. **Treat with caution**: The +1,809% return is not representative of a properly diversified dilution strategy
2. **Expect lower returns**: With 20 positions, returns would likely be significantly lower but more stable
3. **Risk is understated**: The 4.3 position average means much higher concentration risk than reported

### For Improving the Strategy

1. **Expand dilution data coverage**:
   - Add more coins with circulating supply data
   - Use alternative data sources (blockchain explorers, project APIs)
   - Target: 150+ coins with dilution data

2. **Relax filtering criteria**:
   - Reduce volatility lookback from 90 to 30 days
   - Allow coins with partial history
   - Use proxy volatility for new listings

3. **Alternative position sizing**:
   - Work with available positions but adjust allocation
   - Accept 5-10 positions but size appropriately
   - Document concentration explicitly

4. **Data infrastructure**:
   - Improve price data coverage (add exchanges beyond Hyperliquid)
   - Automate dilution data collection
   - Build coin master mapping (CMC → trading symbols)

### For Live Trading

**CAUTION**: Do not trade this strategy at the backtest scale without acknowledging:

1. **Actual position count**: You will hold 4-5 positions, not 20
2. **Concentration risk**: Each position is 20-25% of portfolio
3. **Liquidity risk**: Some positions may have low liquidity
4. **Data dependency**: Strategy breaks if dilution data feed fails

**Recommended approach**:
- Start with small allocation (5-10% of portfolio)
- Monitor actual position counts
- Set position concentration limits (max 15% per coin)
- Use stop-losses given concentration risk

---

## Conclusion

The dilution factor strategy shows **exceptional performance (+1,809%)** but operates with **severe coverage constraints** that:

1. Make the backtest results **not representative** of the intended strategy
2. Introduce **extreme concentration risk** not reflected in standard metrics
3. Suggest returns are partially driven by **lucky concentrated bets** rather than diversified factor exposure
4. Require **significant data infrastructure improvements** before production deployment

The strategy concept (long low dilution, short high dilution) is sound, but the execution is **severely constrained by data availability**.

**Bottom line**: The strategy is trading **4-5 concentrated positions** instead of **20 diversified positions**, which fundamentally changes its risk/return profile.
