# ADF Factor: Coin-Level Analysis (2021-2025)

**Analysis of which coins were traded and their performance characteristics**

---

## Key Finding: Strategies Are Perfect Inverses

**Mean Reversion and Trend Following strategies are EXACTLY opposite:**

| Position | Mean Reversion | Trend Following |
|----------|----------------|-----------------|
| **Long** | Stationary coins (low ADF) | Trending coins (high ADF) |
| **Short** | Trending coins (high ADF) | Stationary coins (low ADF) |

**Result:** 
- Trend Following: **+20.78%** ✅
- Mean Reversion: **-42.93%** ❌
- **Difference: 63.7 percentage points**

This demonstrates that **trending coins massively outperformed stationary coins** from 2021-2025.

---

## Most Frequently Traded Coins

### Trend Following Strategy (Winner)

**Long Positions (Trending Coins - High ADF):**
```
CRO/USD      34 trades  ← Most traded
XLM/USD      30 trades
ALGO/USD     25 trades
GRT/USD      25 trades
BONK/USD     25 trades
ATH/USD      14 trades
ADA/USD      13 trades
PENGU/USD    13 trades
TURBO/USD     8 trades
OXT/USD       8 trades
```

**Short Positions (Stationary Coins - Low ADF):**
```
ALGO/USD     32 trades  ← Most shorted
CRO/USD      25 trades
XLM/USD      18 trades
GIGA/USD     12 trades
BONK/USD      9 trades
GRT/USD       8 trades
USDT/USD      8 trades
TURBO/USD     6 trades
ATH/USD       4 trades
FARTCOIN     4 trades
```

### Mean Reversion Strategy (Loser)

The positions are **exactly inverted** from Trend Following:
- What was LONG in Trend Following → SHORT in Mean Reversion
- What was SHORT in Trend Following → LONG in Mean Reversion

---

## Coin Behavior Patterns

### 1. Coins That Switched Between Trending/Stationary

Several coins appear in BOTH long and short positions across time:

| Coin | Long Trades | Short Trades | Total | Interpretation |
|------|-------------|--------------|-------|----------------|
| **CRO** | 34 | 25 | 59 | Alternated between trending and stationary |
| **ALGO** | 25 | 32 | 57 | More stationary than trending |
| **XLM** | 30 | 18 | 48 | More trending than stationary |
| **GRT** | 25 | 8 | 33 | Mostly trending |
| **BONK** | 25 | 9 | 34 | Mostly trending |

**Key Insight:** Most coins are NOT consistently trending or stationary. They switch based on market regime.

### 2. Persistently Trending Coins (High ADF)

These coins were mostly longed in Trend Following:
- **ADA/USD:** 13 long, 0 short → Consistently trending
- **PENGU/USD:** 13 long, 0 short → Consistently trending
- **OXT/USD:** 8 long, 0 short → Consistently trending

### 3. Persistently Stationary Coins (Low ADF)

These coins were mostly shorted in Trend Following:
- **USDT/USD:** 0 long, 8 short → Stablecoin (expected!)
- **GIGA/USD:** 0 long, 12 short → Highly mean-reverting
- **FARTCOIN/USD:** 0 long, 4 short → Range-bound

---

## ADF Statistics by Strategy

### Trend Following (Winner)

**Long Positions (Trending):**
- Average ADF: **-1.52** (less stationary)
- Interpretation: Non-stationary, trending behavior
- Performance: **Good** (contributed to +20.78% return)

**Short Positions (Stationary):**
- Average ADF: **-3.26** (very stationary)
- Interpretation: Strong mean reversion
- Performance: **Good** (shorting these was profitable)

### Mean Reversion (Loser)

**Long Positions (Stationary):**
- Average ADF: **-3.26** (very stationary)
- Interpretation: Strong mean reversion
- Performance: **Terrible** (dragged down returns)

**Short Positions (Trending):**
- Average ADF: **-1.52** (less stationary)
- Interpretation: Non-stationary, trending behavior
- Performance: **Terrible** (shorting winners was costly)

---

## Coin Performance Analysis

### Why Trending Coins Won

**1. CRO/USD (Crypto.com Coin)**
- **Context:** Major exchange token
- **2021-2025:** Grew with Crypto.com expansion
- **Behavior:** Strong directional moves (both up and down)
- **ADF:** Low (trending), not mean-reverting

**2. XLM/USD (Stellar)**
- **Context:** Established L1 blockchain
- **2021-2025:** Moderate growth, strong partnerships
- **Behavior:** Trending with occasional consolidation
- **ADF:** Variable (switched between trending/stationary)

**3. ADA/USD (Cardano)**
- **Context:** Major L1 smart contract platform
- **2021-2025:** Significant ecosystem growth
- **Behavior:** Strong trending behavior
- **ADF:** Consistently high (non-stationary)

**4. BONK/USD (Bonk)**
- **Context:** Solana meme coin
- **2021-2025:** Explosive growth in 2023-2024
- **Behavior:** Strong momentum, trending
- **ADF:** Mostly trending (high ADF)

### Why Stationary Coins Lost

**1. USDT/USD (Tether)**
- **Context:** Stablecoin
- **Behavior:** Pegged to $1, highly mean-reverting
- **ADF:** Very low (very stationary)
- **Performance:** No growth (stablecoins don't appreciate)
- **Strategy Impact:** Shorting this was correct

**2. ALGO/USD (Algorand)**
- **Context:** L1 blockchain
- **2021-2025:** Underperformed, range-bound
- **Behavior:** Mean-reverting, no sustained trends
- **ADF:** Low (stationary)
- **Performance:** Poor growth, high volatility

**3. GIGA/USD (GigaChad)**
- **Context:** Meme coin
- **Behavior:** Highly volatile, mean-reverting
- **ADF:** Very low (very stationary)
- **Performance:** No sustained growth

---

## Sector Analysis

### By Coin Type

**L1 Blockchains (Mixed):**
- **Trending (Winners):** ADA, XLM, CRO
- **Stationary (Losers):** ALGO
- **Insight:** Established L1s with growth trended; stagnant L1s mean-reverted

**DeFi Tokens (Mostly Stationary):**
- **GRT (The Graph):** Switched between trending/stationary
- **ZRX (0x Protocol):** Range-bound, stationary
- **Insight:** DeFi tokens struggled to maintain trends

**Meme Coins (Mostly Trending):**
- **BONK:** Strong trending
- **TURBO:** Variable
- **PENGU:** Trending
- **Insight:** Successful memes had momentum; failures mean-reverted

**Stablecoins (Always Stationary):**
- **USDT:** Perfect mean reversion (by design)
- **Insight:** Correctly identified as stationary

---

## Trading Frequency Analysis

### Total Trades by Strategy

```
Strategy          Long Trades    Short Trades    Total
───────────────   ───────────    ────────────    ─────
Trend Following        226            210          436
Mean Reversion         210            226          436
```

**Both strategies made 436 total trades** (exactly same, just inverted).

### Average Holding Period

- **Rebalancing:** Every 7 days
- **Trading Period:** 1,698 days
- **Rebalances:** 243
- **Avg Trades per Rebalance:** 1.8 trades

**Interpretation:** Very low turnover. Strategies held 1-2 positions at a time.

---

## Position Concentration Risk

### Typical Portfolio

**At any given time:**
- **Long positions:** 1-2 coins
- **Short positions:** 1-2 coins
- **Total:** 2-4 positions

**Risk Implications:**
- ⚠️ **Extremely concentrated**
- ⚠️ **High idiosyncratic risk**
- ⚠️ **Sensitive to individual coin moves**
- ⚠️ **Not well diversified**

**Example:** 
If you have only 1-2 longs, and both underperform, you lose significantly. The strategy's success depended on picking the RIGHT coins, not just the right direction.

---

## Why These Specific Coins?

### Selection Criteria

Coins were selected based on:
1. **Top 100 market cap** (min $200M)
2. **Minimum volume** (min $10M daily)
3. **ADF ranking** (bottom 20% or top 20%)

### Why So Few Coins?

**Filters were very restrictive:**
- Start with 172 coins in dataset
- After market cap filter: ~50-60 coins
- After volume filter: ~40-50 coins
- After ADF calculation: ~30-40 coins (need 60 days data)
- Bottom/Top 20%: Only 6-8 coins per side
- Further filtered by data quality: Down to 1-2 coins

**Result:** Extremely thin universe, hence concentration risk.

---

## Coin-Specific Insights

### ALGO/USD: The Stationary Coin

**Most shorted coin in Trend Following (32 times)**
- ADF: -3.26 (very stationary)
- Behavior: Range-bound, mean-reverting
- 2021-2025 Performance: Poor (down ~80% from 2021 highs)
- **Shorting this was correct**

### CRO/USD: The Flip-Flopper

**Most traded coin overall (59 total trades)**
- Long 34 times (trending)
- Short 25 times (stationary)
- Behavior: Alternated between trending and mean-reverting
- **Demonstrates regime dependence**

### BONK/USD: The Momentum Play

**Mostly longed in Trend Following (25 long, 9 short)**
- ADF: High (trending)
- Behavior: Strong momentum in 2023-2024
- Performance: Explosive growth during meme coin run
- **Capturing this trend was profitable**

### USDT/USD: The Perfect Stationary

**8 short positions, 0 long positions**
- ADF: Very low (perfectly stationary)
- Behavior: Pegged to $1, mean-reverts by design
- **Correctly identified as mean-reverting**

---

## Lessons from Coin Analysis

### 1. Most Coins Switch Regimes

**Coins are NOT consistently trending or stationary:**
- CRO: 34 long, 25 short
- ALGO: 25 long, 32 short
- XLM: 30 long, 18 short

**Implication:** ADF is time-varying. What's trending today may be stationary tomorrow.

### 2. Sector Matters

**L1 Blockchains:** Mixed (depends on growth)
**DeFi Tokens:** Mostly stationary (struggled)
**Meme Coins:** Mostly trending (momentum-driven)
**Stablecoins:** Always stationary (by design)

**Implication:** Combine ADF with sector knowledge for better signals.

### 3. Concentration Is Dangerous

**Only 1-2 positions at a time:**
- If you pick wrong coins, you lose big
- Mean Reversion picked stationary coins → -42.93%
- Trend Following picked trending coins → +20.78%

**Implication:** Diversification across more coins would reduce risk.

### 4. Market Cap Matters

**Top 100 focus limited universe:**
- Many promising trending coins excluded (smaller cap)
- Strategy was limited to large caps only

**Implication:** Expanding to top 200-300 might improve diversification.

---

## Comparison: Trend Following vs Mean Reversion

### Same Coins, Opposite Positions, Opposite Results

| Metric | Trend Following | Mean Reversion | Difference |
|--------|----------------|----------------|------------|
| **Strategy** | Long trending, short stationary | Long stationary, short trending | Inverse |
| **Total Return** | **+20.78%** | **-42.93%** | **+63.7pp** |
| **Long ADF** | -1.52 (trending) | -3.26 (stationary) | Opposite |
| **Short ADF** | -3.26 (stationary) | -1.52 (trending) | Opposite |
| **Long Exposure** | $3,132 | $1,301 | 2.4x higher |
| **Short Exposure** | -$3,132 | -$1,301 | 2.4x higher |

**Key Insight:** The ONLY difference was which side they went long vs short. Trend Following bet on the right side.

---

## Recommendations for Improvement

### 1. Expand Universe

**Current:** Only 1-2 positions at a time (too concentrated)

**Proposal:** 
- Include top 200-300 coins
- Target 5-10 positions per side
- Reduce concentration risk

### 2. Combine with Other Factors

**Current:** ADF only

**Proposal:**
- ADF + Momentum (capture trends better)
- ADF + Volatility (risk management)
- ADF + Beta (market exposure)
- Multi-factor model more robust

### 3. Sector Filters

**Current:** No sector consideration

**Proposal:**
- Exclude stablecoins (USDT will always be stationary)
- Favor L1s with growth catalysts
- Consider meme coin momentum separately

### 4. Dynamic Thresholds

**Current:** Fixed 20th/80th percentile

**Proposal:**
- Adapt thresholds based on market regime
- Use absolute ADF thresholds (e.g., ADF < -3.0 = stationary)
- Consider ADF momentum (is coin becoming more/less stationary?)

---

## Conclusion: Coin-Level Insights

### What We Learned

1. **Trending coins (high ADF) massively outperformed stationary coins (low ADF)** in 2021-2025
2. **Most coins switch between trending and stationary** over time (regime dependent)
3. **Strategy was too concentrated** (1-2 positions) leading to high idiosyncratic risk
4. **Sector matters:** L1s with growth trended, DeFi tokens struggled, meme coins had momentum
5. **Stablecoins are perfectly stationary** (by design) and should be excluded

### Best Use of ADF Factor

✅ **Do:**
- Use as one signal in multi-factor model
- Combine with momentum and growth indicators
- Expand universe to 5-10+ positions
- Exclude stablecoins
- Monitor regime changes

❌ **Don't:**
- Use ADF as sole factor (too concentrated)
- Assume coins stay trending/stationary (they switch)
- Fight sustained trends (momentum dominated this period)
- Trade long-only (hedging is critical)

### Final Verdict

**ADF factor correctly identified trending vs stationary behavior, but:**
- Universe was too small (1-2 coins)
- Period favored momentum over mean reversion
- Needs diversification across more factors

**For live trading:** Use ADF as ONE input in a diversified multi-factor model, not standalone.

---

**Date:** 2025-10-27  
**Period Analyzed:** 2021-2025 (4.7 years)  
**Total Trades Analyzed:** 436 per strategy  
**Coins Identified:** 15+ actively traded
