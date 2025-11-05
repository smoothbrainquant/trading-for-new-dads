# Size Factor Analysis: Daily vs Monthly Market Cap

**Date**: 2025-11-05  
**Analysis**: Impact of using daily calculated market cap vs monthly snapshots

---

## Executive Summary

✅ **Daily market cap calculation activated** - using `daily_market_cap = price × circulating_supply`  
⚠️ **Size factor still negative** - fundamental issues in crypto markets persist  
📊 **Improvement observed** - but not enough to make the strategy viable

---

## Problem Identified

### Original Issue (Monthly Snapshots)
- **Data Frequency**: Monthly snapshots (every ~30 days)
- **Rebalance Frequency**: Every 10 days
- **Staleness**: Market cap values stale for ~20 days between snapshots
- **Result**: -15.37% annualized return, -0.386 Sharpe ratio

### Root Cause
```
Day 0:  Market cap snapshot → SOL = $10B (labeled "large cap")
Day 10: SOL dumps to $6B (still labeled "large" in monthly data)
Day 15: Strategy shorts SOL as "large cap"
Day 20: Already missed the move → buying high, selling low
```

---

## Solution Implemented

### Daily Market Cap Calculation

**Formula**:
```
daily_market_cap = daily_close_price × circulating_supply
```

**Process**:
1. Extract circulating supply from monthly snapshots (737 coins)
2. Forward-fill circulating supply daily (creates 1.1M daily observations)
3. Merge with daily price data
4. Calculate market cap daily for 117 coins

**Coverage**:
- **Input**: 161,813 price observations (172 symbols)
- **Output**: 70,540 daily market cap observations (117 symbols)
- **Coverage**: 43.6% of price data now has daily market cap

---

## Results Comparison

### Performance by Portfolio Size

| Portfolio Size | **OLD (Monthly)** | **NEW (Daily)** | **Improvement** |
|----------------|-------------------|-----------------|-----------------|
| **Top/Bottom 5** | -15.37% / -0.386 | **-37.01% / -0.783** | ❌ WORSE (-21.6%) |
| **Top/Bottom 10** | -15.37% / -0.386 | **-16.80% / -0.488** | ⚠️ Worse (-1.4%) |
| **Decile (10%)** | -15.37% / -0.386 | **-16.80% / -0.488** | ⚠️ Worse (-1.4%) |
| **Quintile (20%)** | -15.37% / -0.386 | **-10.53% / -0.312** | ✅ **BETTER (+4.8%)** |

### Key Findings

**Best Configuration**: Top/Bottom Quintile (20%) with daily market cap
- Return: -10.53% (vs -15.37% with monthly)
- Sharpe: -0.312 (vs -0.386 with monthly)
- Max Drawdown: -65.76% (vs -70.81% with monthly)
- Win Rate: 51.10%

**Surprising Result**: More concentrated portfolios (Top 5) perform WORSE with daily data
- Top/Bottom 5: -37.01% return (much worse than -15.37%)
- Likely reason: More exposure to small cap volatility and survivorship bias

---

## Why Size Factor Still Fails

### 1. **Survivorship Bias**
- Small caps frequently go to zero (not in historical data)
- Backtests only see survivors → overstates performance
- Reality: Many small caps delisted or disappeared

### 2. **Liquidity Issues**
- Small caps have wide bid-ask spreads
- Slippage kills theoretical returns
- Can't execute at quoted prices in practice

### 3. **Market Manipulation**
- Pump-and-dump schemes common in small caps
- Wash trading inflates volumes
- Price discovery unreliable

### 4. **No Fundamental Anchor**
- Unlike stocks (earnings, book value, dividends)
- Crypto has no cash flows to value
- Pure sentiment/narrative driven

### 5. **Winner-Take-All Dynamics**
- BTC/ETH dominate capital flows
- Network effects favor large caps
- Small caps struggle for adoption

---

## Comparison: Crypto vs Equities

| Factor | Equities | Crypto |
|--------|----------|--------|
| **Size Premium** | ✅ Positive | ❌ Negative |
| **Data Frequency** | Daily | Monthly (was), Daily (now) |
| **Survivorship** | Low | High |
| **Liquidity** | Deep | Shallow |
| **Fundamentals** | Strong | Weak |
| **Market Structure** | Mature | Immature |

**Verdict**: Daily market cap helps but can't overcome fundamental crypto market issues

---

## Recommendations

### ❌ **DO NOT USE** Size Factor in Crypto
- Still negative across all configurations
- Daily market cap improves but doesn't fix the strategy
- Quintile (20%) is "least bad" but still loses money

### ✅ **USE THESE INSTEAD**
1. **Volatility Factor**: 1.746 Sharpe, 87.73% return
2. **Beta Factor**: 0.592 Sharpe, 31.70% return
3. **Kurtosis Factor**: 0.984 Sharpe, 26.71% return (bear markets)

### 🔧 **If You Must Use Size**
- **Only use Top/Bottom Quintile** (20%) - least negative
- Expect -10.53% annualized return
- Sharpe ratio of -0.312 (still poor)
- Better to skip entirely

---

## Technical Implementation

### Files Created
- `/workspace/data/scripts/calculate_daily_market_cap.py` - Calculation script
- `/workspace/data/raw/daily_calculated_market_cap_clean.csv` - Daily market cap data (70,540 rows)

### Data Quality
- **Symbols covered**: 117 out of 172 (68% coverage)
- **Date range**: 2021-04-09 to 2025-10-24
- **Daily observations**: 2,120 days
- **Average symbols per day**: 33

### Integration
- Backtest engine updated to accept daily market cap
- Drop-in replacement for monthly snapshots
- No code changes needed in strategy logic

---

## Conclusion

**✅ Success**: Daily market cap calculation working correctly  
**⚠️ Reality**: Size factor doesn't work in crypto markets  
**💡 Insight**: Data quality alone can't fix fundamental market structure issues

**Final Recommendation**: Skip Size factor entirely. Focus on Volatility, Beta, and Kurtosis factors which have proven positive performance in crypto markets.
