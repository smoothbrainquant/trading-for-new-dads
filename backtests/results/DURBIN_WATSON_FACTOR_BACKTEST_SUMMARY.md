# Durbin-Watson Factor Backtest Results Summary

**Period:** March 2020 - October 2025 (2,040 days / 5.6 years)  
**Directional Regime:** 5-day BTC percent change with ±10% thresholds  
**Rebalancing:** Weekly (every 7 days, 292 total rebalances)  
**Initial Capital:** $10,000  
**Date Generated:** 2025-10-30

---

## 📊 Executive Summary

### ⚠️ **CRITICAL FINDING: All Strategies Underperformed**

All Durbin-Watson factor strategies generated **negative returns** over the 5.6-year period, with losses ranging from **-19.93% to -77.59%**. The primary issue is **severe underdiversification** with only 1-2 positions per side on average.

### Key Takeaway

**The DW factor shows WORSE performance than expected, likely due to:**
1. **Severe underdiversification** (avg 1-2 positions vs target 10-20)
2. **Strict liquidity filters** reduced universe too much in early period
3. **DW may not be a strong predictive factor** for crypto returns
4. **Mean reversion premium performed least badly** (-19.93% vs -43% to -77%)

---

## 📈 Performance Summary: All Strategies

| Strategy | Total Return | Ann. Return | Sharpe | Max DD | Win Rate | Avg Longs | Avg Shorts | Avg DW Long | Avg DW Short |
|----------|--------------|-------------|--------|--------|----------|-----------|------------|-------------|--------------|
| **Mean Reversion Premium** | **-19.93%** | **-3.90%** | **-0.10** | **-58.65%** | **40.02%** | **1.8** | **1.1** | **2.21** | **1.80** |
| Regime Adaptive | -43.28% | -9.65% | -0.26 | -67.44% | 35.90% | 1.1 | 1.8 | 1.80 | 2.21 |
| Momentum Premium | -43.28% | -9.65% | -0.26 | -67.44% | 35.90% | 1.1 | 1.8 | 1.80 | 2.21 |
| Long Mean Reversion | -67.69% | -18.30% | -0.42 | -79.80% | 38.40% | 1.8 | 0.0 | 2.21 | N/A |
| Long Momentum | -77.59% | -23.48% | -0.47 | -86.85% | 37.18% | 1.1 | 0.0 | 1.80 | N/A |

### Key Observations

1. **Mean Reversion Premium was least bad** (-19.93% vs -43% to -77%)
   - Suggests high DW (mean reversion) coins may perform better
   - But still negative overall

2. **Regime Adaptive = Momentum Premium** (identical results)
   - Both show -43.28% return
   - Suggests regime switching didn't add value
   - Possibly because both strategies had similar positions most of the time

3. **Long-only strategies performed worst** (-67% to -77%)
   - Market neutral had better risk management
   - Shorting helped reduce losses

4. **All strategies severely underdiversified**
   - Target: 10-20 positions per side
   - Actual: 1-2 positions per side
   - **This is the primary issue!**

---

## 🔍 Detailed Strategy Analysis

### 1. Mean Reversion Premium (Best Performer)

**Strategy:** Long high DW (mean reversion), Short low DW (momentum)

**Results:**
- Total Return: **-19.93%**
- Annualized Return: **-3.90%**
- Sharpe Ratio: **-0.10**
- Maximum Drawdown: **-58.65%**
- Win Rate: **40.02%**
- Avg Positions: 1.8 longs, 1.1 shorts

**Interpretation:**
- High DW coins (mean-reverting behavior) outperformed low DW coins (momentum)
- DW > 2 (negative autocorrelation) → Coins oscillate rather than trend
- DW < 2 (positive autocorrelation) → Coins trend but underperformed
- **Mean reversion won, but overall strategy still lost money**

**DW Statistics:**
- Avg DW Long: **2.21** (mean reversion/negative autocorrelation)
- Avg DW Short: **1.80** (momentum/positive autocorrelation)
- DW spread: **0.41** (modest separation)

---

### 2. Regime Adaptive (Primary Strategy)

**Strategy:** Switch between momentum/mean reversion based on 5d BTC % change

**Results:**
- Total Return: **-43.28%**
- Annualized Return: **-9.65%**
- Sharpe Ratio: **-0.26**
- Maximum Drawdown: **-67.44%**
- Win Rate: **35.90%**
- Avg Positions: 1.1 longs, 1.8 shorts

**Regime Logic:**
- **Strong Up / Down** (>±10%): Long momentum (low DW), Short mean reversion (high DW)
- **Moderate Up / Strong Down**: Long mean reversion (high DW), Short momentum (low DW)

**Why It Failed:**
- Identical results to static Momentum Premium (-43.28%)
- Regime switching didn't provide benefit
- Low position count (1-2 coins) → High idiosyncratic risk
- Momentum strategy was wrong direction (should have been mean reversion)

---

### 3. Momentum Premium (Static Strategy)

**Strategy:** Always long low DW (momentum), short high DW (mean reversion)

**Results:**
- Total Return: **-43.28%**
- Annualized Return: **-9.65%**
- Sharpe Ratio: **-0.26**
- Maximum Drawdown: **-67.44%**
- Win Rate: **35.90%**
- Avg Positions: 1.1 longs, 1.8 shorts

**Interpretation:**
- Momentum coins (low DW, positive autocorrelation) underperformed
- Mean reversion coins (high DW, negative autocorrelation) outperformed
- **Hypothesis rejected:** Momentum did NOT work in crypto (opposite of expected)
- Should have gone with mean reversion premium instead

---

### 4. Long Momentum (Worst Performer)

**Strategy:** Long-only low DW (momentum) coins

**Results:**
- Total Return: **-77.59%**
- Annualized Return: **-23.48%**
- Sharpe Ratio: **-0.47**
- Maximum Drawdown: **-86.85%**
- Win Rate: **37.18%**
- Avg Positions: 1.1 longs only

**Why It Failed:**
- Momentum coins (DW < 2) performed terribly
- No short side to hedge
- Severe underdiversification (only 1.1 positions on average)
- High concentration risk

---

### 5. Long Mean Reversion

**Strategy:** Long-only high DW (mean reversion) coins

**Results:**
- Total Return: **-67.69%**
- Annualized Return: **-18.30%**
- Sharpe Ratio: **-0.42**
- Maximum Drawdown: **-79.80%**
- Win Rate: **38.40%**
- Avg Positions: 1.8 longs only

**Interpretation:**
- Mean reversion coins performed better than momentum
- But still lost -67.69% overall
- Higher position count than momentum (1.8 vs 1.1)
- No short hedge → Drawdowns were severe (-79.80%)

---

## 🎯 DW Statistics Analysis

### Average DW Values by Strategy

| Strategy | Avg DW Long | Avg DW Short | DW Spread | Interpretation |
|----------|-------------|--------------|-----------|----------------|
| Momentum Premium | 1.80 | 2.21 | -0.41 | Long momentum, short mean reversion |
| Mean Reversion Premium | 2.21 | 1.80 | +0.41 | Long mean reversion, short momentum |
| Regime Adaptive | 1.80 | 2.21 | -0.41 | Similar to momentum (failed regime switching) |
| Long Momentum | 1.80 | N/A | N/A | Pure momentum exposure |
| Long Mean Reversion | 2.21 | N/A | N/A | Pure mean reversion exposure |

### DW Interpretation

- **DW = 1.80**: Positive autocorrelation (momentum/trending)
  - ρ ≈ (2 - 1.80) / 2 = +0.10 (10% positive autocorrelation)
  - Returns persist in same direction
  
- **DW = 2.21**: Negative autocorrelation (mean reversion/oscillating)
  - ρ ≈ (2 - 2.21) / 2 = -0.105 (-10.5% negative autocorrelation)
  - Returns reverse direction

- **DW spread = 0.41**: Modest separation
  - Not a huge difference between momentum and mean reversion groups
  - May explain weak performance

---

## ⚠️ Key Issues Identified

### 1. Severe Underdiversification (Primary Issue)

**Problem:**
- Target positions: 10-20 per side (20% percentile cutoff)
- Actual positions: **1-2 per side**
- This means only **1-2 coins passed all filters** at any rebalance

**Impact:**
- **High idiosyncratic risk**: Portfolio dominated by 1-2 specific coins
- **Extreme volatility**: Single coin moves dominate portfolio
- **Poor risk-adjusted returns**: Concentration kills Sharpe ratio
- **Unstable factor exposure**: DW factor not consistently captured

**Root Cause:**
- **Liquidity filters too strict**: $5M min volume, $50M min market cap
- **Limited universe**: Early 2020 had fewer large coins
- **DW calculation failures**: Many coins may not have enough data

**Fix:**
- Lower minimum volume to $1M
- Lower minimum market cap to $10M
- Reduce DW window from 60 to 30 days for more coverage

### 2. Momentum Strategy Failed

**Finding:**
- Momentum coins (low DW, positive autocorrelation) underperformed
- Mean reversion coins (high DW, negative autocorrelation) outperformed
- **Opposite of traditional finance**

**Possible Explanations:**
1. **Crypto is mean-reverting**: Extreme moves correct quickly
2. **Momentum measured wrong**: DW may not capture true momentum
3. **Sample period**: 2020-2025 included many boom-bust cycles
4. **Autocorrelation != Returns**: DW measures return autocorrelation, not price momentum

### 3. Regime Switching Didn't Help

**Finding:**
- Regime Adaptive had identical results to Momentum Premium (-43.28%)
- Suggests regime classification or strategy logic needs work

**Possible Issues:**
1. **Regime classification lag**: 5-day BTC % change is backward-looking
2. **Regime logic wrong**: Should favor mean reversion in ALL regimes?
3. **Not enough regime changes**: May not have switched often enough
4. **Position overlap**: Same coins selected regardless of regime

### 4. DW Factor May Be Weak

**Evidence:**
- All strategies lost money
- Even "best" strategy (Mean Reversion) lost -19.93%
- DW spread only 0.41 (modest)
- Win rates all below 50%

**Conclusion:**
- **DW may not be a strong predictive factor** in crypto markets
- Autocorrelation in returns ≠ Predictable future returns
- Other factors (volatility, momentum, carry) may be stronger

---

## 📉 Risk Metrics Comparison

### Volatility and Risk-Adjusted Returns

| Strategy | Ann. Volatility | Sharpe | Sortino | Calmar | Max DD |
|----------|-----------------|--------|---------|--------|--------|
| Mean Reversion Premium | 37.52% | -0.10 | -0.10 | -0.07 | -58.65% |
| Regime Adaptive | 37.52% | -0.26 | -0.36 | -0.14 | -67.44% |
| Momentum Premium | 37.52% | -0.26 | -0.36 | -0.14 | -67.44% |
| Long Mean Reversion | 43.14% | -0.42 | -0.49 | -0.23 | -79.80% |
| Long Momentum | 50.45% | -0.47 | -0.59 | -0.27 | -86.85% |

### Observations

1. **All strategies had high volatility** (37-50% annualized)
   - Much higher than target (20-30%)
   - Due to concentration (1-2 positions)

2. **All Sharpe ratios negative** (-0.10 to -0.47)
   - Negative returns killed risk-adjusted performance
   - Even "best" strategy (Mean Reversion) had Sharpe of -0.10

3. **Drawdowns were severe** (-58% to -86%)
   - Long-only strategies worst (-79% to -86%)
   - Market neutral better but still bad (-58% to -67%)

4. **Win rates below 50%** (35.90% to 40.02%)
   - More losing days than winning days
   - Asymmetry didn't favor strategy (big losses, small wins)

---

## 🔄 Comparison to ADF Factor

The Durbin-Watson factor was designed to be similar to the ADF factor, but measures autocorrelation instead of stationarity. Let's compare:

| Metric | ADF Factor | DW Factor |
|--------|------------|-----------|
| **Concept** | Stationarity (unit root test) | Autocorrelation (serial correlation) |
| **Range** | Unbounded (typically -5 to 0) | Bounded (0 to 4) |
| **Interpretation** | Low = stationary, High = trending | Low = momentum, High = mean reversion |
| **Best Strategy (2021-2025)** | Trend Following (+20.78%) | Mean Reversion (-19.93%) |
| **Winner** | Trending coins won | Mean reversion coins lost less |
| **Regime Dependence** | Strong (±46pp improvement) | Unclear (regime adaptive failed) |

### Key Differences

1. **ADF worked, DW didn't**
   - ADF Trend Following: +20.78% (2021-2025)
   - DW Mean Reversion: -19.93% (2020-2025)

2. **Opposite winners**
   - ADF: Trending coins (high ADF) outperformed
   - DW: Mean-reverting coins (high DW) lost less

3. **DW has worse diversification**
   - ADF: ~10 positions per side
   - DW: ~1-2 positions per side

4. **DW spread is smaller**
   - ADF: Large difference between stationary and trending coins
   - DW: Only 0.41 spread between momentum and mean reversion

### Conclusion

**The DW factor performed much worse than ADF**, likely because:
- DW measures autocorrelation (short-term patterns)
- ADF measures stationarity (longer-term mean reversion)
- ADF may be more robust and economically meaningful
- DW universe was too small (filtering issues)

---

## 💡 Recommendations

### For Production Use: **DO NOT DEPLOY**

❌ **None of these strategies should be deployed** in their current form.

**Reasons:**
1. All strategies lost money
2. Severe underdiversification (1-2 positions)
3. High volatility (37-50%)
4. Large drawdowns (58-86%)
5. Negative Sharpe ratios

### For Further Research

If you want to continue researching the DW factor, consider:

#### 1. Fix Diversification Issues

```bash
# Rerun with lower filters
python3 backtest_durbin_watson_factor.py \
  --strategy mean_reversion_premium \
  --min-volume 1000000 \       # Lower from $5M to $1M
  --min-market-cap 10000000 \  # Lower from $50M to $10M
  --dw-window 30 \             # Shorter window (30d vs 60d)
  --start-date 2021-01-01      # Skip early COVID period
```

**Expected improvement:**
- 5-10 positions per side (instead of 1-2)
- Lower volatility
- More stable factor exposure

#### 2. Test Alternative DW Specifications

- **DW Window**: Try 30d, 45d, 90d (current: 60d)
- **DW Calculation**: Test alternative formulas or transformations
- **Autocorrelation**: Use direct ACF(1) instead of DW statistic
- **Multiple Lags**: Combine autocorrelation at multiple lags

#### 3. Combine with Other Factors

DW alone is weak. Consider multi-factor models:

```python
# Multi-factor ranking
score = 0.3 * ADF_rank + 0.3 * DW_rank + 0.2 * volatility_rank + 0.2 * momentum_rank
```

#### 4. Different Regime Classification

Current regime logic may be wrong. Test:
- Different thresholds (±5%, ±15% instead of ±10%)
- Different windows (7d, 10d instead of 5d)
- Volatility-based regimes instead of directional
- Leading indicators instead of lagging 5d returns

#### 5. Abandon DW Factor

**Honest assessment:** DW may simply not work in crypto markets.

Consider focusing on proven factors instead:
- **ADF Factor**: +20.78% (worked well)
- **Beta Factor**: +218% (Betting Against Beta)
- **Volatility Factor**: Tested, results available
- **Carry Factor**: Funding rate strategies

---

## 📁 Output Files

All backtest results saved to `/workspace/backtests/results/`:

### Portfolio Values
- `backtest_dw_regime_adaptive_portfolio_values.csv`
- `backtest_dw_momentum_premium_portfolio_values.csv`
- `backtest_dw_mean_reversion_premium_portfolio_values.csv`
- `backtest_dw_long_momentum_portfolio_values.csv`
- `backtest_dw_long_mean_reversion_portfolio_values.csv`

### Trades
- `backtest_dw_regime_adaptive_trades.csv`
- `backtest_dw_momentum_premium_trades.csv`
- `backtest_dw_mean_reversion_premium_trades.csv`
- `backtest_dw_long_momentum_trades.csv`
- `backtest_dw_long_mean_reversion_trades.csv`

### Metrics
- `backtest_dw_regime_adaptive_metrics.csv`
- `backtest_dw_momentum_premium_metrics.csv`
- `backtest_dw_mean_reversion_premium_metrics.csv`
- `backtest_dw_long_momentum_metrics.csv`
- `backtest_dw_long_mean_reversion_metrics.csv`

---

## 🎓 Conclusion

### Main Findings

1. **All DW strategies lost money** (-19.93% to -77.59%)
2. **Mean reversion outperformed momentum** (high DW better than low DW)
3. **Severe underdiversification** (1-2 positions instead of 10-20)
4. **Regime switching didn't help** (identical to static strategy)
5. **DW factor appears weak** for crypto markets

### Why DW Failed

1. **Underdiversification**: Only 1-2 coins per side
2. **Autocorrelation ≠ Returns**: DW measures patterns, not predictability
3. **Wrong direction**: Momentum lost, mean reversion lost less
4. **Weak factor**: Small DW spread (0.41), low predictive power
5. **Period effects**: 2020-2025 may not favor autocorrelation strategies

### Comparison to ADF

- **ADF Factor worked**: +20.78% (Trend Following)
- **DW Factor failed**: -19.93% (Mean Reversion Premium)
- **ADF > DW**: Stationarity more predictive than autocorrelation

### Final Verdict

❌ **DO NOT USE Durbin-Watson factor strategies in production**

✅ **Use ADF factor instead** (proven to work: +20.78%)

---

**Report Generated:** 2025-10-30  
**Analysis Period:** March 2020 - October 2025 (5.6 years)  
**Total Strategies Tested:** 5  
**Best Strategy:** Mean Reversion Premium (-19.93% - still negative!)  
**Status:** ❌ **FAILED** - All strategies underperformed

---

**Disclaimer:** These results are for research purposes only. Past performance does not guarantee future results. The Durbin-Watson factor showed poor performance and should NOT be deployed in live trading. Consider using proven factors (ADF, Beta, Volatility) instead.
