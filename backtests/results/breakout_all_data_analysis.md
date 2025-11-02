# Breakout Strategy: Full Dataset Analysis (2020-2024)

## Executive Summary

**Critical Finding**: The breakout strategy performs VERY DIFFERENTLY across market regimes. The long side loses money catastrophically over the full period, while shorts dominate. The original 50d/70d configuration ranks **9th out of 12** on the full dataset.

---

## Full Dataset Results (2020-2024)

### Original Config: 50d Entry / 70d Exit

| Side | Total Return | Ann. Return | Sharpe | Max DD | Win Rate | Final Value |
|------|-------------|-------------|--------|--------|----------|-------------|
| **Long Only** | -44.79% | -12.21% | -0.154 | **-96.20%** | 50.09% | $2,760 |
| **Short Only** | +66.34% | +11.80% | 0.141 | -75.84% | 45.11% | $8,317 |
| **Combined (50/50)** | **-4.17%** | **-0.93%** | -0.038 | -46.67% | 50.45% | $9,583 |

### Best Config: 20d Entry / 30d Exit

| Side | Total Return | Ann. Return | Sharpe | Max DD | Win Rate | Final Value |
|------|-------------|-------------|--------|--------|----------|-------------|
| **Long Only** | -53.58% | -15.15% | -0.179 | **-96.20%** | 50.32% | $2,321 |
| **Short Only** | +161.74% | +22.88% | 0.264 | -80.72% | 45.28% | $13,087 |
| **Combined (50/50)** | **+10.22%** | **+2.11%** | 0.084 | -46.67% | 50.56% | $11,022 |

### BEST Overall Config: 10d Entry / 15d Exit (Ultra-Fast)

| Metric | Value |
|--------|-------|
| **Total Return** | +25.48% |
| **Annualized Return** | +4.91% |
| **Sharpe Ratio** | 0.193 |
| **Max Drawdown** | -44.34% |
| **Final Value** | $12,548 |

---

## Parameter Ranking on Full Dataset (2020-2024)

| Rank | Configuration | Ann. Return | Sharpe | Total Return | Status |
|------|--------------|-------------|--------|--------------|--------|
| 1 | Entry 10d / Exit 15d | +4.91% | 0.193 | +25.48% | ?? Best |
| 2 | Entry 15d / Exit 20d | +3.79% | 0.150 | +19.21% | ?? Good |
| 3 | Entry 20d / Exit 30d | +2.11% | 0.084 | +10.22% | ?? Moderate |
| 4 | Entry 30d / Exit 50d | -0.31% | -0.013 | -1.43% | ?? Negative |
| 5 | Entry 50d / Exit 50d | -0.31% | -0.013 | -1.43% | ?? Negative |
| 6-7 | Entry 40d/50d / Exit 60d | -0.37% | -0.015 | -1.71% | ?? Negative |
| 8 | Entry 70d / Exit 90d | -0.89% | -0.037 | -3.94% | ?? Negative |
| **9** | **Entry 50d / Exit 70d (ORIGINAL)** | **-0.93%** | **-0.038** | **-4.17%** | **?? Negative** |
| 10 | Entry 100d / Exit 120d | -1.28% | -0.052 | -5.54% | ?? Negative |
| 11-12 | Entry 50d/60d / Exit 80d | -1.78% | -0.073 | -7.81% | ?? Negative |

**Key Insight**: ONLY the 3 fastest configurations (10d/15d, 15d/20d, 20d/30d) are profitable over the full period!

---

## Time Period Comparison

### 2023-2024 Period ONLY (Recent)

| Rank | Config | Ann. Return | Sharpe |
|------|--------|-------------|--------|
| 1 | 20d/30d | +9.63% | 0.558 |
| 2 | 30d/50d | +7.90% | 0.456 |
| **4** | **50d/70d (Original)** | **+6.88%** | **0.393** |

### 2020-2024 Full Period

| Rank | Config | Ann. Return | Sharpe |
|------|--------|-------------|--------|
| 1 | 10d/15d | +4.91% | 0.193 |
| 2 | 15d/20d | +3.79% | 0.150 |
| 3 | 20d/30d | +2.11% | 0.084 |
| **9** | **50d/70d (Original)** | **-0.93%** | **-0.038** |

---

## Critical Observations

### 1. ?? **LONG SIDE IS CATASTROPHIC**

**Full Period (2020-2024):**
- Original config: **-44.79%** total return (-96% max drawdown!)
- Best config: **-53.58%** total return
- Long breakouts LOSE MONEY in crypto across all parameter sets

**Recent Period (2023-2024):**
- Original config: +2.43% total return (barely positive)
- Best config: +1.17% total return

**Conclusion**: Long breakouts are unprofitable or barely break-even across ALL time periods.

### 2. ?? **SHORT SIDE DOMINATES**

**Full Period (2020-2024):**
- Original config: +66.34% total return
- Best config: +161.74% total return (2.6x return!)

**Recent Period (2023-2024):**
- Original config: +20.16% total return  
- Best config: +34.39% total return

**Conclusion**: Shorts are THE driver of returns. This is a short-biased strategy.

### 3. ?? **DIVERSIFICATION SAVES THE STRATEGY**

Without 50/50 diversification:
- Long-only: -96% max drawdown (catastrophic)
- Short-only: -80% max drawdown (very risky)

With 50/50 diversification:
- Combined: -47% max drawdown (acceptable)
- Volatility: 25% vs 80%+ for individual sides

### 4. ?? **FASTER = BETTER (on full dataset)**

Performance by speed:
- Ultra-fast (10-20d): **Positive returns** (2-5% annualized)
- Medium (30-50d): **Slightly negative** (-0.3% annualized)
- Slow (50-100d): **Negative** (-1% to -2% annualized)

**Why?** Faster signals capture mean reversion moves before they exhaust.

### 5. ?? **REGIME DEPENDENCY**

The strategy performs VERY differently across market conditions:

**Bull Market (2020-2021):**
- Long side likely profitable (prices breaking out and continuing)
- Portfolio peaked at $15,000+ in mid-2021

**Bear/Sideways (2021-2023):**
- Long side catastrophic (-96% max drawdown reached)
- Short side excellent (breakdowns continue)
- Portfolio drawdown to ~$9,000

**Recent Recovery (2023-2024):**
- Both sides moderate
- Short side still outperforms

---

## Position Analysis

### Average Positions (Full Dataset)

All configurations maintain ~30 total positions:
- **~12-13 long positions** (42%)
- **~17 short positions** (58%)

**Key Insight**: The strategy naturally holds MORE short positions, creating a structural short bias even with "50/50" allocation.

### Net Exposure

- Average net exposure: **-0.46% to -0.80%** (slightly net short)
- Gross exposure: ~95% (nearly fully invested)

---

## Risk Metrics Deep Dive

### Maximum Drawdowns by Side

| Config | Long Only | Short Only | Combined |
|--------|-----------|------------|----------|
| Original (50d/70d) | **-96.20%** | -75.84% | -46.67% |
| Best (20d/30d) | **-96.20%** | -80.72% | -46.67% |

**Critical**: Long side alone would cause portfolio destruction (-96% DD). Combined strategy reduces DD by 50%+.

### Volatility by Side

| Side | Volatility | Observation |
|------|------------|-------------|
| Long Only | 79-85% | Extremely volatile |
| Short Only | 84-87% | Extremely volatile |
| Combined | 24-25% | **70% volatility reduction!** |

---

## Market Regime Impact

### By Year (Estimated from equity curve):

**2020 (Bull Market Start):**
- Portfolio: $10,000 ? $11,000 (+10%)
- Long side likely driving

**2021 Q1-Q2 (Peak Bull):**
- Portfolio: $11,000 ? $15,000 (+36%)
- Long side peaked at $45,000+ (9x!)
- Best period for longs

**2021 Q3-2022 (Bear Market):**
- Portfolio: $15,000 ? $9,000 (-40%)
- Long side collapsed: $45,000 ? $2,000 (-96%)
- Short side expanded: $1,300 ? $10,000 (7.7x)

**2023-2024 (Recovery/Sideways):**
- Portfolio: $9,000 ? $9,600 (+7%)
- Choppy performance both sides

---

## Recommendations

### ? **FOR LIVE TRADING:**

1. **Use 10d/15d or 20d/30d configuration**
   - Only configs with positive long-term returns
   - Better Sharpe ratios

2. **Consider PURE short-only strategy**
   - Short-only with 20d/30d made 161% total (22.9% annualized)
   - Accept higher volatility/drawdown for higher returns
   - OR use smaller position sizes to control risk

3. **If using combined: Tilt toward shorts**
   - Try 30/70 (long/short) instead of 50/50
   - Aligns with natural short bias and better performance

4. **Add regime filters**
   - Long side works in strong bull markets only
   - Short side works consistently
   - Consider turning off longs in non-bull regimes

### ?? **CAUTION FLAGS:**

1. ?? **DO NOT use 50d/70d original config** - negative returns overall
2. ?? **DO NOT trade long-only** - catastrophic losses
3. ?? **DO NOT use slow signals (>50d)** - underperform across the board
4. ?? **Expect -45% max drawdown** even with combined strategy
5. ?? **Long side can lose 96%** - size positions accordingly

### ?? **FURTHER RESEARCH:**

1. Test pure short-only strategy with optimal sizing
2. Separate bull/bear market performance
3. Add momentum/trend filters for long entries
4. Test asymmetric allocations (30/70, 20/80)
5. Consider market cap filters (does it work better on large caps?)

---

## Conclusion

### **The Uncomfortable Truth:**

This is **NOT** a traditional trend-following strategy. It's a **SHORT-BIASED MEAN-REVERSION STRATEGY** disguised as breakout trading:

- **Upward breakouts fail** (mean revert) ? long side loses
- **Downward breakouts continue** (momentum) ? short side wins
- **Only fast signals work** (10-30d) ? capture reversals quickly
- **Diversification is mandatory** ? reduces catastrophic risk

### **Should You Trade It?**

**NO** if you:
- Want traditional trend following
- Can't handle 45%+ drawdowns  
- Expect both sides to be profitable
- Want to use original 50d/70d parameters

**YES** if you:
- Accept this is primarily a SHORT strategy
- Use 10d/15d or 20d/30d parameters
- Can handle high volatility
- Consider pure short-only with tight sizing
- Have strong risk management

### **Bottom Line:**

Over 4.5 years (2020-2024):
- **Original 50d/70d**: -4.17% total return (LOSE MONEY)
- **Best 10d/15d**: +25.48% total return (MAKE MONEY)
- **Short-only 20d/30d**: +161.74% total return (BEST PERFORMANCE)

**Use fast signals, tilt toward shorts, or trade short-only with proper risk management.**
