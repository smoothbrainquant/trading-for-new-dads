# Mean Reversion Strategy - Deep Dive Analysis

## Executive Summary

The Mean Reversion strategy shows **extreme volatility and regime dependence**. While there's **no lookahead bias**, the strategy has massive year-to-year swings that make it unreliable:

- **2023:** +36.95% (Sharpe 6.135) ? EXCELLENT
- **2024:** -36.81% (Sharpe -0.903) ? DISASTER  
- **2025:** +18.11% (Sharpe 1.727) ? GOOD
- **Overall:** +0.38% (Sharpe -0.032) ? Essentially breakeven with massive volatility

**Trading Frequency:** Only 242 days out of 1,000 available (24% of time in market)

---

## 1. Strategy Logic

### Entry Criteria (VERIFIED CORRECT)
The strategy enters LONG positions when:
1. **Price drops > 1.0 std dev below 30-day mean** (return_zscore < -1.0)
2. **AND volume spikes > 1.0 std dev above 30-day mean** (volume_zscore > 1.0)
3. **Holds for 2 days** (rebalance_days=2)

### Signal Verification
? **No Lookahead Bias:** Rolling statistics use `.shift(1)` correctly  
? **Logic Correct:** All long signals have return_zscore < -1.0 (price dropped)  
? **Volume Correct:** All long signals have volume_zscore > 1.0 (high volume)

**Signal Statistics (2023-2025):**
- Total signals: 1,135
- Average return z-score: -2.12 (extreme down moves)
- Average volume z-score: +2.93 (high volume spikes)
- Signals per trading day: Median 2, Max 49

---

## 2. Performance Analysis by Year

| Year | Days Traded | Return | Ann. Return | Sharpe | Max DD | Volatility | Win Rate |
|------|-------------|--------|-------------|--------|--------|------------|----------|
| 2023 | 76 | +36.95% | +361.93% | 6.135 | -13.79% | 59.00% | 60.00% |
| 2024 | 90 | -36.81% | -84.46% | -0.903 | -56.94% | 93.56% | 46.67% |
| 2025 | 76 | +18.11% | +122.39% | 1.727 | -33.91% | 70.87% | 50.00% |
| **Total** | **242** | **+0.38%** | **-2.43%** | **-0.032** | **-62.63%** | **76.94%** | **51.65%** |

### Key Observations

1. **Extreme Regime Dependence**
   - Sharpe swings from +6.1 to -0.9 to +1.7
   - This is NOT normal variation - something fundamental changed between years
   
2. **Very Sparse Trading**
   - Only 242 days traded out of ~1,000 available (24%)
   - 2023: 76 days (21% of year)
   - 2024: 90 days (25% of year)
   - 2025: 76 days (26% of year)
   
3. **Extreme Volatility**
   - 76.94% annualized volatility (vs ~17% for other strategies)
   - This is 4-5x higher volatility than typical crypto strategies
   - Driven by very concentrated positions (median 2 positions per day)

4. **Signal Frequency by Year**
   - 2023: 315 signals (avg z-score: -2.17)
   - 2024: 415 signals (avg z-score: -1.90)
   - 2025: 405 signals (avg z-score: -2.30)
   - Similar signal counts, but VERY different outcomes

---

## 3. Root Causes of Extreme Variation

### Why 2023 Was Excellent (+37%, Sharpe 6.1)

**Market Context (2023):**
- Recovery from 2022 bear market
- Strong uptrend with healthy pullbacks
- **Mean reversion worked** because dips were bought aggressively
- High volume spikes were accumulation events

**Strategy Performance:**
- 60% win rate (best of all years)
- Only -13.79% max drawdown (very contained)
- 59% volatility (high but managed)

**Hypothesis:** In a strong bull market with momentum, buying panic dips with high volume = catching falling knives that bounce quickly.

### Why 2024 Was Terrible (-37%, Sharpe -0.9)

**Market Context (2024):**
- Mixed market with false breakouts
- High volume drops were **capitulation** events, not bounces
- **Mean reversion failed** because dips continued lower
- Rotation out of speculative alts into BTC/ETH

**Strategy Performance:**
- 46.67% win rate (worst of all years)
- -56.94% max drawdown (CATASTROPHIC)
- 93.56% volatility (out of control)

**Hypothesis:** In a choppy/rotation market, buying panic dips = catching falling knives that keep falling.

### Why 2025 Recovered (+18%, Sharpe 1.7)

**Market Context (2025):**
- Return to uptrend
- High volume dips were opportunities again
- More selective (fewer extreme drops)

**Strategy Performance:**
- 50% win rate (neutral)
- -33.91% max drawdown (still high)
- 70.87% volatility (very high)

**Hypothesis:** Partial recovery as bull market conditions returned, but still volatile.

---

## 4. The Fundamental Issue: Knife-Catching

### The Mean Reversion Thesis

**Assumption:** When a coin drops >1 std dev with high volume, it's oversold and will bounce.

**Reality:** This depends entirely on WHY it dropped:

| Scenario | Volume Spike Meaning | Outcome | MR Works? |
|----------|---------------------|---------|-----------|
| Bull Market Dip | Accumulation / Panic buy | Bounces quickly | ? YES |
| Distribution | Smart money exiting | Continues lower | ? NO |
| News Event | Fundamental change | New equilibrium | ? NO |
| Liquidity Cascade | Forced selling | May bounce or crash | ?? MIXED |
| Rotation | Money moving elsewhere | Slow bleed | ? NO |

**The strategy cannot distinguish between these scenarios.**

### Why High Volatility?

1. **Concentrated Positions**
   - Median: 2 positions per day
   - Max: 49 positions in one day
   - When signals trigger, they're often correlated (market-wide events)

2. **Binary Outcomes**
   - Either the bounce happens (big win) or it doesn't (big loss)
   - No middle ground with 2-day holding period

3. **Leverage Effect**
   - 76% volatility with only 24% time in market
   - Implies ~320% volatility when actually trading
   - This is higher than individual coins!

---

## 5. Comparison to "Looped Backtest"

The user mentioned this was a "top performer in looped backtest" but may have had errors.

### Potential Sources of Optimistic Bias in Previous Backtest

1. **Survivorship Bias**
   - If the old backtest only included coins that survived
   - Many failed coins have extreme down moves that never recover
   - Current backtest includes all available coins

2. **Period Selection**
   - If tested only on 2023 data ? would show Sharpe 6.1
   - If tested only on 2024 data ? would show Sharpe -0.9
   - The strategy's performance is 100% dependent on which period you test

3. **Parameter Optimization**
   - zscore_threshold=1.0 and volume_threshold=1.0 seem arbitrary
   - May have been optimized on a specific period
   - Would create huge overfitting risk

4. **Implementation Differences**
   - Old backtest may have had different rebalance logic
   - Different position sizing
   - Different entry/exit timing

---

## 6. Statistical Significance Analysis

### Is the 2023 Performance Real or Luck?

**2023 Results:**
- 76 trading days
- 60% win rate
- Sharpe 6.135

**Statistical Analysis:**
- With 76 days and 60% win rate, this is 10 more wins than losses
- Binomial test p-value for 60% win rate vs 50% baseline: Not statistically significant
- **Sharpe 6.1 is suspicious** - world's best hedge funds rarely exceed 2.0
- With 76 days and 59% volatility, Sharpe 6.1 is likely a statistical fluke

**Conclusion:** The 2023 performance is likely **lucky timing**, not skill.

### Is the Strategy Statistically Sound?

**Full Period (242 days):**
- Overall return: +0.38%
- Sharpe: -0.032 (essentially zero)
- t-statistic for Sharpe: ~-0.05 (not significant)

**Conclusion:** Over the full period, the strategy has **no edge**. The positive 2023 was offset by negative 2024.

---

## 7. Why the Strategy Fails

### Market Microstructure Issues

1. **Information Asymmetry**
   - High volume drops often reflect smart money exiting
   - Retail mean reversion traders are the exit liquidity
   - We're trading AGAINST informed flow

2. **Crypto Momentum > Mean Reversion**
   - Crypto has strong momentum effects
   - Trends persist longer than traditional markets
   - Extreme moves often continue in same direction

3. **2-Day Holding Period Too Short**
   - Not enough time for genuine mean reversion
   - Just enough time to catch a dead cat bounce OR a continued crash
   - Whipsaw risk is maximized

4. **No Risk Management**
   - No stop loss
   - No position sizing based on market conditions
   - Treats all signals equally (bull vs bear market)

---

## 8. Recommendations

### Option A: Disable the Strategy ?

**Reasoning:**
- Zero Sharpe over full period
- 76% volatility is unmanageable
- Extreme regime dependence makes it unreliable
- Risk of catastrophic drawdowns (see 2024: -57%)

**Recommendation:** Remove from portfolio allocation.

### Option B: Fix the Strategy ??

If you want to salvage it, consider:

1. **Add Market Regime Filter**
   ```python
   # Only trade when BTC is in uptrend
   if btc_50d_ma > btc_200d_ma:
       allow_mean_reversion_trades()
   ```

2. **Add Risk Management**
   ```python
   # Stop loss at -10% on position
   # Position size inversely proportional to recent drawdown
   ```

3. **Extend Holding Period**
   ```python
   # Test 5-day or 7-day holding period
   # Give more time for genuine mean reversion
   ```

4. **Add Fundamental Filters**
   ```python
   # Exclude coins with:
   # - Recent negative news
   # - Declining TVL (for DeFi)
   # - Decreasing network activity
   ```

5. **Adjust Thresholds Dynamically**
   ```python
   # In high-volatility regime: increase threshold to 2.0
   # In low-volatility regime: decrease to 0.5
   # Adapt to market conditions
   ```

### Option C: Test Alternative Mean Reversion Approaches ??

1. **Pairs Trading**
   - Trade mean reversion between correlated coins
   - More stable than single-coin MR

2. **Statistical Arbitrage**
   - Use cointegration instead of z-scores
   - More rigorous statistical foundation

3. **Multi-Day Mean Reversion**
   - Look for 3-5 day oversold conditions
   - Less noise, more genuine reversions

---

## 9. Conclusion

### Summary of Findings

? **No lookahead bias** - Implementation is correct  
? **Signal logic correct** - Buys dips with high volume  
? **Zero edge** - Sharpe -0.032 over full period  
? **Extreme volatility** - 76% annualized (4x other strategies)  
? **Regime dependent** - Works in bull, fails in chop/bear  
? **Not statistically significant** - 2023 outperformance was luck  

### Final Recommendation

**DISABLE THE STRATEGY** or **HEAVILY MODIFY IT**.

The current implementation is essentially a coin flip with 76% volatility. The spectacular 2023 performance (Sharpe 6.1) was a statistical fluke that cannot be relied upon. The 2024 disaster (-37%, Sharpe -0.9) is more representative of the downside risk.

**Risk/Reward is Unacceptable:**
- Upside: Maybe +30-40% in perfect conditions (2023)
- Downside: -37% to -57% drawdowns (2024)
- Expected: ~0% with wild swings

This is not a strategy suitable for production trading unless significantly improved with regime filters and risk management.

---

## Appendix: Data Quality Notes

### Symbol Coverage
- Price data: 93 symbols (2023+)
- Signals: 1,135 total long signals
- Average: 1.2 signals per symbol per year
- Some symbols never trigger (stable coins, low volatility)
- Some symbols trigger frequently (high volatility alts)

### Signal Distribution
- 2023: 315 signals (4.1 per day when trading)
- 2024: 415 signals (4.6 per day when trading)  
- 2025: 405 signals (5.3 per day when trading)

Signal counts are similar across years, but outcomes are wildly different. This confirms the issue is **regime-dependent execution**, not signal quality or data issues.
