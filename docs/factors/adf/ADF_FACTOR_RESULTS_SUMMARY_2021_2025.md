# ADF Factor Results Summary (2021-2025)

**Quick Reference Guide**  
**Period:** March 2021 - October 2025 (4.7 years)  
**Universe:** Top 100 Coins by Market Cap

---

## 🏆 Winner: Trend Following Premium (Equal Weight)

```
Initial Capital:  $10,000
Final Value:      $12,078
Total Return:     +20.78%
Sharpe Ratio:     0.15
Max Drawdown:     -44.39%
```

---

## 📊 All Strategies Performance

```
┌────────────────────────────────┬─────────────┬──────────┬────────────┐
│ Strategy                        │ Total Ret.  │  Sharpe  │  Final $   │
├────────────────────────────────┼─────────────┼──────────┼────────────┤
│ ✅ Trend Following (EW)        │   +20.78%   │   0.15   │  $12,078   │
│ Trend Following (Risk Parity)  │   +10.54%   │   0.08   │  $11,054   │
│ Mean Reversion (EW)            │   -42.93%   │  -0.40   │   $5,707   │
│ Long Trending Only             │   -66.13%   │  -0.58   │   $3,387   │
│ ❌ Long Stationary Only         │   -77.28%   │  -0.74   │   $2,272   │
└────────────────────────────────┴─────────────┴──────────┴────────────┘
```

---

## 💡 Key Insights

### 1. Trend Following Crushed Mean Reversion
**Performance Gap: 63.7 percentage points**

- **Trend Following:** +20.78% (long trending, short stationary)
- **Mean Reversion:** -42.93% (long stationary, short trending)

**Why?** 2021-2025 was dominated by momentum, not mean reversion.

### 2. Long/Short Structure Essential
**All long-only strategies failed catastrophically:**

- Long Stationary: **-77.28%** (worst)
- Long Trending: **-66.13%**
- Long/Short Trend: **+20.78%** (best)

**Hedging saved the strategy.**

### 3. Equal Weight Beat Risk Parity
- Equal Weight: **+20.78%**
- Risk Parity: **+10.54%**

Risk parity over-weighted underperforming stationary coins.

### 4. ADF as Standalone Signal Has Issues

**Average Positions:** 1-2 coins at a time
- Very concentrated portfolios
- High idiosyncratic risk
- Thin universe after filters

**Recommendation:** Combine with other factors for diversification.

---

## 📈 Performance by Strategy Type

### Long/Short (Market Neutral)

| Strategy | Return | Max DD | Sharpe |
|----------|--------|--------|--------|
| Trend Following (EW) | **+20.78%** | -44.39% | **0.15** |
| Trend Following (RP) | +10.54% | -45.81% | 0.08 |
| Mean Reversion (EW) | -42.93% | -72.54% | -0.40 |

### Long-Only (Directional)

| Strategy | Return | Max DD | Sharpe |
|----------|--------|--------|--------|
| Long Trending | -66.13% | -67.02% | -0.58 |
| Long Stationary | **-77.28%** | **-84.22%** | -0.74 |

---

## 🎯 What Worked

✅ **Trend Following Strategy**
- Captured momentum in trending coins
- Avoided underperforming mean-reverting coins

✅ **Short Hedging**
- Reduced drawdowns significantly
- Market neutral structure

✅ **Equal Weighting**
- Simpler and more effective than risk parity

✅ **Higher Market Cap Focus**
- Better liquidity and data quality

---

## ❌ What Failed

❌ **Mean Reversion Strategy**
- Stationary coins severely underperformed
- Fighting the trend was costly

❌ **Long-Only Approaches**
- No hedge = catastrophic losses
- 66-84% drawdowns

❌ **Risk Parity Weighting**
- Over-weighted low-performers
- Didn't reduce risk meaningfully

❌ **Concentrated Portfolios**
- Only 1-2 positions at a time
- High idiosyncratic risk

---

## 🔍 ADF Statistics

### Performance by ADF Level

```
More Stationary (Low ADF) ──────────────► More Trending (High ADF)
        -2.45                  -1.23                -0.78
         ❌                     Poor                  ✅
    Worst Perf.                                  Best Perf.
  (Mean-Reverting)                              (Trending)
```

**Key Finding:** More negative ADF = worse performance in 2021-2025.

### Stationarity Rate
- Only **10.4%** of observations were stationary (p < 0.05)
- Most crypto is non-stationary (trending/random walk)
- Expected in high-growth, emerging markets

---

## 📅 Market Regime Context

### 2021: Bull Market Peak
- Crypto at all-time highs
- Strong momentum
- Mean reversion failed

### 2022: Bear Market Collapse
- Terra/LUNA, FTX crashes
- BTC -77% from peak
- Trending coins fell less

### 2023: Recovery
- Sideways consolidation
- Gradual recovery
- Mixed signals

### 2024-2025: New Bull Run
- Bitcoin ETF approval
- New highs
- Momentum dominant again

**Overall:** Period favored momentum/trending over mean reversion.

---

## 💰 Exposure Analysis

```
Strategy             Gross Exposure    Utilization
─────────────────    ──────────────    ───────────
Trend Following      $6,265            62.6% ✅
Mean Reversion       $2,602            26.0% ⚠️
Long Trending        $1,367            13.7% ❌
Long Stationary      $920               9.2% ❌
```

**Issue:** Most strategies couldn't deploy capital effectively (few coins passed filters).

---

## 🎲 Win Rate Paradox

**All strategies had low win rates (~20-23%):**

```
Strategy              Win Rate    Total Return
────────────────────  ────────    ────────────
Trend Following       20.73%      +20.78% ✅
Mean Reversion        22.73%      -42.93% ❌
```

**Lesson:** Win rate ≠ profitability. Few big wins > many small losses.

---

## 🔄 Recommendations

### For Improvement

1. **Combine with Other Factors**
   - ADF + Momentum + Volatility
   - Multi-factor models more robust

2. **Expand Universe**
   - Top 200-300 coins
   - Increase from 1-2 to 5-10 positions

3. **Test Different Parameters**
   - ADF windows: 30d, 90d, 120d
   - Rebalancing: daily, bi-weekly, monthly
   - Percentile thresholds: 10%, 15%, 20%

4. **Add Regime Switching**
   - Bull markets → Trend Following
   - Bear/sideways → Different approach

5. **Improve Risk Management**
   - Position size limits
   - Stop losses
   - Dynamic risk budgeting

### For Live Trading

⚠️ **Proceed with Caution:**
- Strategy is highly concentrated (1-2 positions)
- Trend Following had positive returns but modest Sharpe (0.15)
- Needs diversification via other factors
- Add transaction cost modeling

✅ **Consider If:**
- You expect continued momentum markets
- You can combine with other signals
- You have good execution (low slippage)

❌ **Avoid:**
- Mean Reversion strategy (failed badly)
- Long-only approaches (too risky)
- Using ADF as sole factor

---

## 📁 Output Files Location

```
/workspace/backtests/results/
├── adf_mean_reversion_2021_top100_*.csv
├── adf_trend_following_2021_top100_*.csv
├── adf_trend_riskparity_2021_top100_*.csv
├── adf_long_stationary_2021_top100_*.csv
└── adf_long_trending_2021_top100_*.csv
```

Each strategy has 4 files:
- `*_portfolio_values.csv` - Daily portfolio values
- `*_trades.csv` - Trade history
- `*_metrics.csv` - Performance metrics
- `*_strategy_info.csv` - Configuration

---

## 📚 Related Documents

- **Full Analysis:** `/workspace/docs/ADF_FACTOR_BACKTEST_RESULTS_2021_2025.md`
- **Specification:** `/workspace/docs/ADF_FACTOR_SPEC.md`
- **Implementation:** `/workspace/backtests/scripts/backtest_adf_factor.py`
- **Quick Guide:** `/workspace/backtests/scripts/README_ADF_FACTOR.md`

---

## ✅ Bottom Line

**Best Strategy:** Trend Following Premium (Equal Weight)
- **Return:** +20.78% over 4.7 years
- **Sharpe:** 0.15 (positive but modest)
- **Drawdown:** -44.39% (manageable)

**Key Takeaway:** In momentum-driven markets, bet on the trend (high ADF), not mean reversion (low ADF).

**Warning:** Strategy needs diversification. Only 1-2 positions = high concentration risk. Combine with other factors for robustness.

---

**Date:** 2025-10-27  
**Status:** ✅ Complete  
**Tested:** 5 strategy variants  
**Winner:** Trend Following (EW) +20.78%
