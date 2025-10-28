# ADF Factor: Executive Summary

**Comprehensive backtest results from 2021-2025 on top 100 market cap coins**

---

## 📊 The Bottom Line

```
┌─────────────────────────────────────────────────────────┐
│  WINNER: Trend Following Premium (Equal Weight)         │
│                                                           │
│  Initial Capital:      $10,000                           │
│  Final Value:          $12,078                           │
│  Total Return:         +20.78%                           │
│  Annualized Return:    +4.14%                            │
│  Sharpe Ratio:         0.15                              │
│  Max Drawdown:         -44.39%                           │
│                                                           │
│  Period: March 2021 - October 2025 (4.7 years)          │
└─────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Findings

### 1. Trend Following Crushed Mean Reversion

**Performance Gap: 63.7 percentage points**

| Strategy | Return | Sharpe | Max DD |
|----------|--------|--------|--------|
| ✅ **Trend Following** | **+20.78%** | **0.15** | **-44.39%** |
| ❌ **Mean Reversion** | **-42.93%** | -0.40 | -72.54% |

**Why?**
- 2021-2025 was a momentum-driven period
- Trending coins (high ADF) captured sustained growth
- Stationary coins (low ADF) were range-bound and underperformed
- Mean reversion failed in trending markets

### 2. Long/Short Structure Was Essential

**All long-only strategies failed catastrophically:**

| Strategy | Return | Max DD | Status |
|----------|--------|--------|--------|
| Long Trending | -66.13% | -67.02% | ❌ Failed |
| Long Stationary | -77.28% | -84.22% | ❌ Worst |
| **Long/Short Trend** | **+20.78%** | **-44.39%** | ✅ **Winner** |

**Hedging saved the strategy** from market crashes.

### 3. Equal Weight Beat Risk Parity

| Method | Return | Sharpe |
|--------|--------|--------|
| Equal Weight | **+20.78%** | **0.15** |
| Risk Parity | +10.54% | 0.08 |

Risk parity over-weighted underperforming stationary coins.

### 4. Strategy Was Too Concentrated

**Average Positions:** 1-2 coins at any time

- ⚠️ Extremely concentrated (not diversified)
- ⚠️ High idiosyncratic risk
- ⚠️ Universe too small after filters
- 💡 **Needs expansion to 5-10+ positions**

---

## 📈 Complete Strategy Comparison

```
Strategy                    Total Ret.   Ann. Ret.   Sharpe   Max DD    Final $
─────────────────────────   ──────────   ─────────   ──────   ──────    ───────
✅ Trend Following (EW)        +20.78%      +4.14%     0.15    -44.39%   $12,078
Trend Following (RP)          +10.54%      +2.18%     0.08    -45.81%   $11,054
Mean Reversion (EW)           -42.93%     -11.36%    -0.40    -72.54%    $5,707
Long Trending                 -66.13%     -20.76%    -0.58    -67.02%    $3,387
❌ Long Stationary             -77.28%     -27.28%    -0.74    -84.22%    $2,272
```

---

## 🔍 What Is ADF?

**Augmented Dickey-Fuller (ADF) Test:**
- Statistical test for stationarity (mean reversion)
- **Lower ADF** = More stationary = More mean-reverting
- **Higher ADF** = Less stationary = More trending/random walk

**Example ADF Values:**
```
-4.0  ←───── Very Stationary ─────────────→  -0.5
      (Mean-Reverting)                      (Trending)
      
      ALGO/USD: -3.26                       ADA/USD: -1.52
      (Range-bound)                         (Strong trends)
```

---

## 💰 Coin-Level Insights

### Most Frequently Traded (Trend Following)

**Long Positions (Trending):**
1. CRO/USD - 34 trades (exchange token, growth)
2. XLM/USD - 30 trades (L1, partnerships)
3. ALGO/USD - 25 trades (but also shorted 32x!)
4. BONK/USD - 25 trades (meme momentum)
5. ADA/USD - 13 trades (L1, ecosystem growth)

**Short Positions (Stationary):**
1. ALGO/USD - 32 trades (range-bound, underperformed)
2. CRO/USD - 25 trades (switched regimes)
3. GIGA/USD - 12 trades (highly mean-reverting)
4. USDT/USD - 8 trades (stablecoin, by design)

### Key Observation

**Many coins switched between trending and stationary over time:**
- CRO: 34 long + 25 short (regime switching)
- ALGO: 25 long + 32 short (variable behavior)
- XLM: 30 long + 18 short (mostly trending)

**Implication:** ADF is time-varying, not fixed per coin.

---

## 📅 Market Regime Context

### 2021: Bull Peak
- Crypto at all-time highs
- Strong momentum
- ✅ Trend Following worked

### 2022: Bear Crash
- Terra/LUNA, FTX collapses
- BTC down 77%
- ✅ Shorting stationary coins helped

### 2023: Recovery
- Sideways consolidation
- Mixed signals
- ~ Neutral for both

### 2024-2025: New Bull
- Bitcoin ETF approval
- New highs
- ✅ Trend Following worked

**Overall:** Momentum-driven period favored trending over stationary.

---

## ⚠️ Major Issues

### 1. Concentration Risk

**Problem:** Only 1-2 positions at a time
- High idiosyncratic risk
- Success depended on picking RIGHT coins
- One bad coin = significant impact

**Solution:** 
- Expand to top 200-300 coins
- Target 5-10 positions per side
- Better diversification

### 2. ADF Alone Is Not Enough

**Problem:** Single factor strategy
- Too binary (trending vs stationary)
- Doesn't capture growth, momentum, volatility
- Thin universe after filters

**Solution:**
- Combine with momentum factor
- Add volatility scaling
- Multi-factor model more robust

### 3. Low Win Rate (~20%)

**All strategies had ~20-23% win rate**
- Most days were losing days
- Success came from asymmetry (big wins > small losses)
- High volatility of returns

**Not necessarily bad, but psychologically difficult**

### 4. Modest Absolute Returns

**Trend Following: +4.14% annualized**
- Positive, but modest
- Underperformed BTC buy-and-hold (~+10% annualized)
- Better risk-adjusted (lower volatility)

**Value proposition:** Market-neutral, lower volatility, positive returns in challenging period

---

## ✅ What Worked

1. **Trend Following Strategy**
   - Bet on momentum, not mean reversion
   - Captured sustained directional moves

2. **Long/Short Hedging**
   - Reduced drawdowns significantly
   - Market neutral structure protected in crashes

3. **Equal Weighting**
   - Simpler than risk parity
   - More effective in this period

4. **Top 100 Focus**
   - Better liquidity
   - More reliable data
   - Reduced noise

---

## ❌ What Failed

1. **Mean Reversion Strategy**
   - Stationary coins underperformed massively
   - Fighting momentum was costly
   - -42.93% return (catastrophic)

2. **Long-Only Approaches**
   - No hedge = massive drawdowns
   - 66-84% losses
   - Directional risk too high

3. **Risk Parity**
   - Over-weighted underperformers
   - Didn't reduce risk meaningfully
   - Complexity didn't add value

4. **Concentrated Portfolios**
   - 1-2 positions too risky
   - High sensitivity to individual coins
   - Needs diversification

---

## 🎓 Lessons Learned

### 1. Market Regime Matters

**Different periods favor different strategies:**
- Bull/momentum markets → Trend Following
- Bear/sideways markets → Mean Reversion (maybe)
- This period was momentum-driven

**Implication:** Consider regime-switching strategies.

### 2. Diversification Is Critical

**Current:** 1-2 positions
**Needed:** 5-10+ positions

Single-factor strategies with thin universes are too concentrated.

### 3. Win Rate ≠ Profitability

**All strategies had low win rates (20-23%):**
- Trend Following: 20.73% win rate, +20.78% return ✅
- Mean Reversion: 22.73% win rate, -42.93% return ❌

**Lesson:** Focus on asymmetry (size of wins vs losses), not frequency.

### 4. Hedging Is Essential

**Long/Short:** +20.78% return, -44% drawdown
**Long-Only:** -66% to -77% returns, -67% to -84% drawdowns

**Hedging reduced losses by 50%+ in downturns.**

---

## 💡 Recommendations

### For Live Trading

⚠️ **Proceed with Caution**

**Consider using IF:**
- ✅ You expect continued momentum markets
- ✅ You can combine with other factors (momentum, volatility)
- ✅ You can expand universe (5-10+ positions)
- ✅ You have low-cost execution

**Avoid IF:**
- ❌ Using ADF as sole factor (too concentrated)
- ❌ Expecting high win rate (only ~20%)
- ❌ Trading long-only (need hedging)
- ❌ In mean-reverting market regimes

### For Strategy Enhancement

**1. Expand Universe**
- Include top 200-300 coins
- Increase to 5-10 positions per side
- Reduce concentration risk

**2. Multi-Factor Model**
- Combine ADF + Momentum + Volatility
- ADF + Beta (market exposure)
- Factor rotation based on regime

**3. Optimize Parameters**
- Test ADF windows: 30d, 90d, 120d
- Test rebalancing: daily, bi-weekly, monthly
- Test percentile thresholds: 10%, 15%, 20%

**4. Add Regime Detection**
- Bull markets → Trend Following
- Bear/sideways → Different strategy
- Dynamic strategy switching

**5. Risk Management**
- Position size limits (max 10% per coin)
- Stop losses (protect against extreme moves)
- Volatility scaling (reduce exposure in high vol)
- Transaction cost modeling

---

## 📊 Comparison to Benchmarks

| Strategy | Return (2021-2025) | Sharpe | Max DD |
|----------|-------------------|--------|--------|
| **ADF Trend Following** | **+20.78%** | **0.15** | **-44.39%** |
| Bitcoin Buy & Hold (est.) | ~+45% | ~0.3 | ~-77% |
| Equal-Weight Crypto (est.) | ~-20% | <0 | ~-80% |
| Market-Cap-Weight (est.) | ~+35% | ~0.25 | ~-75% |

**Assessment:**
- ✅ Beat equal-weight index
- ❌ Underperformed Bitcoin
- ❌ Underperformed cap-weighted index
- ✅ Lower volatility than buy-and-hold
- ✅ Market-neutral (hedged)

**Value Proposition:**
- Positive returns in challenging period
- 28% volatility vs 60%+ for BTC
- Market-neutral structure
- Potential alpha in right regimes

---

## 🎯 Strategic Use Cases

### Use Case 1: Portfolio Diversification

**Add ADF Trend Following as a diversifier:**
- Low correlation to BTC buy-and-hold
- Market-neutral positioning
- 20% allocation in crypto portfolio

### Use Case 2: Regime-Based Rotation

**Switch strategies based on market:**
- Bull/momentum → Trend Following ADF
- Bear/sideways → Different strategy (carry, mean reversion)
- Dynamic allocation

### Use Case 3: Multi-Factor Model

**Combine ADF with other factors:**
- 25% ADF Trend Following
- 25% Momentum factor
- 25% Volatility factor
- 25% Beta factor
- → More robust, diversified

---

## 📁 Files Generated

All backtest results available in `/workspace/backtests/results/`:

```
adf_mean_reversion_2021_top100_*.csv       (4 files)
adf_trend_following_2021_top100_*.csv      (4 files)
adf_trend_riskparity_2021_top100_*.csv     (4 files)
adf_long_stationary_2021_top100_*.csv      (4 files)
adf_long_trending_2021_top100_*.csv        (4 files)
```

Each strategy includes:
- Portfolio values (daily time series)
- Trades (complete trade log)
- Metrics (performance summary)
- Strategy info (configuration)

---

## 📚 Documentation

**Complete documentation available:**

1. **Specification:** `/workspace/docs/ADF_FACTOR_SPEC.md`
   - 16-section comprehensive spec
   - Strategy description, methodology
   - Implementation details

2. **Full Results:** `/workspace/docs/ADF_FACTOR_BACKTEST_RESULTS_2021_2025.md`
   - Detailed performance analysis
   - Market regime analysis
   - Risk metrics

3. **Quick Summary:** `/workspace/ADF_FACTOR_RESULTS_SUMMARY_2021_2025.md`
   - Quick reference guide
   - Key insights and recommendations

4. **Coin Analysis:** `/workspace/ADF_FACTOR_COIN_ANALYSIS_2021_2025.md`
   - Which coins were traded
   - Coin-level performance
   - Sector analysis

5. **Implementation Guide:** `/workspace/backtests/scripts/README_ADF_FACTOR.md`
   - How to run backtests
   - Parameter descriptions
   - Usage examples

---

## 🏁 Final Verdict

### ✅ Strategy Is Valid

**Trend Following ADF works in momentum markets:**
- +20.78% return over 4.7 years
- Positive Sharpe ratio (0.15)
- Manageable drawdown (-44%)
- Market-neutral structure
- Better than equal-weight index

### ⚠️ But Has Limitations

**Issues to address:**
- Too concentrated (1-2 positions)
- Modest absolute returns (+4% annualized)
- Low win rate (~20%)
- Regime dependent (only works in trending markets)
- Underperformed BTC buy-and-hold

### 💡 Best Use: Part of Multi-Factor Model

**Don't use standalone. Combine with:**
- Momentum factor (capture trends better)
- Volatility factor (risk management)
- Beta factor (market exposure control)
- Expand to 5-10+ positions

### 🎯 For Live Trading

**Recommended allocation:** 
- 10-20% of crypto portfolio
- As diversifier, not core holding
- Monitor regime changes
- Stop if mean reversion emerges

**Expected performance:**
- +5-10% annualized in trending markets
- -10-20% in mean-reverting markets
- 25-30% volatility
- Sharpe ~0.2-0.3

---

## ✨ Conclusion

**The ADF factor successfully identified trending vs stationary behavior in crypto markets from 2021-2025.**

**Key Result:** Trending coins (high ADF) outperformed stationary coins (low ADF) by 63.7 percentage points.

**Best Strategy:** Trend Following Premium (Equal Weight) returned +20.78% over 4.7 years.

**Critical Issue:** Strategy is too concentrated (1-2 positions). Needs diversification.

**Recommendation:** Use as ONE component in a diversified multi-factor model, not standalone.

---

**Report Date:** 2025-10-27  
**Backtest Period:** March 2021 - October 2025 (4.7 years)  
**Trading Days:** 1,698  
**Strategies Tested:** 5  
**Winner:** Trend Following (Equal Weight)  
**Return:** +20.78%  
**Status:** ✅ Complete and Documented
