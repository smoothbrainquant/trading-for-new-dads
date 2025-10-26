# Cryptocurrency Pairs Trading Research Specification

**Version:** 1.0  
**Date:** 2025-10-26  
**Status:** Draft

---

## 1. Executive Summary

This specification outlines a research project to develop and backtest cryptocurrency pairs trading strategies based on sector/category baskets. The core hypothesis is that coins within the same category exhibit correlated price movements, and temporary divergences from the basket's average performance present profitable mean-reversion trading opportunities.

### Key Objectives
1. Identify and categorize cryptocurrencies into meaningful baskets
2. Analyze correlation and covariance structures within each basket
3. Develop signals for identifying divergent coins
4. Backtest long/short strategies that capitalize on divergences
5. Compare category-based pairs trading to existing single-asset strategies

---

## 2. Category Definition & Data Collection

### 2.1 CoinMarketCap Category Research

#### Website Exploration
- **URL:** https://coinmarketcap.com/cryptocurrency-category/
- **Action Items:**
  - Manually review available categories
  - Document category definitions and membership criteria
  - Note the number of coins per category
  - Identify high-liquidity categories suitable for trading

#### API Integration
- **Endpoint Investigation:**
  - Research CMC API v1 endpoints for category listings
  - Target endpoint: `/v1/cryptocurrency/categories` (or similar)
  - Document available category metadata (name, description, market cap, volume)
  
- **Implementation:**
  - Create `data/scripts/fetch_cmc_categories.py`
  - Fetch category list with metadata
  - Fetch coin membership for each category
  - Store as `data/raw/cmc_categories.csv` and `data/raw/cmc_category_members.csv`

- **API Rate Limits:**
  - CMC free tier: 333 calls/day, 10k calls/month
  - Plan API calls accordingly
  - Cache category data (updates infrequently)

### 2.2 Custom Category Definitions

Since CMC categories may not cover all relevant groupings, we'll define custom baskets based on fundamental characteristics:

#### Proposed Custom Categories

| Category | Description | Example Coins | Rationale |
|----------|-------------|---------------|-----------|
| **ETH Ecosystem** | Ethereum and major ETH L2s, ETH-based DeFi | ETH, MATIC, ARB, OP, LDO, AAVE, UNI, MKR | Share ETH network effects, gas fees |
| **SOL Ecosystem** | Solana and SOL-native protocols | SOL, JTO, JUP, PYTH, RAY, ORCA | Correlated with Solana adoption |
| **BTC Ecosystem** | Bitcoin and BTC L2s | BTC, STX, ORDI, SATS | Bitcoin-centric value accrual |
| **L1 Smart Contract** | Alternative L1 blockchains | SOL, ADA, AVAX, DOT, ATOM, NEAR, FTM, ALGO | Direct competitors for L1 dominance |
| **L2 Scaling** | Ethereum Layer 2 networks | ARB, OP, MATIC, IMX, METIS, BOBA | Scaling solution competitors |
| **DeFi Blue Chips** | Established DeFi protocols | AAVE, UNI, MKR, SNX, CRV, CVX, LDO | DeFi adoption cycle correlation |
| **DEX Tokens** | Decentralized exchange tokens | UNI, SUSHI, CAKE, DYDX, GMX, JOE | DEX volume and competition |
| **Meme Coins** | Community-driven meme tokens | DOGE, SHIB, PEPE, FLOKI, BONK | Sentiment-driven, high correlation |
| **China Coins** | Chinese-origin projects | NEO, VET, QTUM, ONT | Regulatory and geographic correlation |
| **Dino Coins** | Pre-2017 cryptocurrencies | LTC, XRP, BCH, DASH, ETC, XLM, ZEC | Legacy status, lower innovation |
| **Privacy Coins** | Privacy-focused cryptocurrencies | XMR, ZEC, DASH, SCRT | Regulatory risk correlation |
| **Gaming/Metaverse** | Gaming and virtual world tokens | AXS, SAND, MANA, IMX, GALA, ENJ | Gaming cycle correlation |
| **AI/Compute** | AI and decentralized compute | FET, AGIX, RNDR, AKT, GRT, OCEAN | AI hype cycle correlation |
| **Oracle Networks** | Decentralized oracle providers | LINK, BAND, TRB, API3 | Data feed dependency |
| **Storage/Infra** | Decentralized storage/infrastructure | FIL, AR, STORJ, RNDR | Infrastructure adoption |
| **Stablecoins** | USD-pegged stable assets | USDT, USDC, DAI, USDD, FRAX | Low volatility, correlation to TradFi rates |

#### Category Membership Rules
- **Primary Membership:** Each coin can belong to multiple categories
- **Liquidity Threshold:** Minimum 90-day average daily volume > $1M USD
- **Market Cap Threshold:** Minimum market cap > $10M USD
- **Data Availability:** Must have daily price data from 2020-01-01 onwards

### 2.3 Data Requirements

#### Price Data (Already Available)
- **Source:** `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- **Coverage:** 172 coins, 2020-01-01 to present
- **Fields:** date, symbol, open, high, low, close, volume, market_cap

#### Additional Data Needed
- **CMC Categories:** Fetch via API
- **Custom Category Mappings:** Manual curation → `data/raw/custom_categories.csv`
- **Fundamental Data:** Market cap, circulating supply, volume (already in combined dataset)

#### Expected Data Formats

**`data/raw/custom_categories.csv`:**
```csv
symbol,category,priority
ETH,ETH Ecosystem,primary
MATIC,ETH Ecosystem,primary
MATIC,L2 Scaling,primary
ARB,ETH Ecosystem,secondary
ARB,L2 Scaling,primary
...
```

**`data/raw/cmc_category_members.csv`:**
```csv
category_name,category_id,symbol,cmc_rank,market_cap
DeFi,6051f8bf2cd943685c3b5498,UNI,15,4500000000
DeFi,6051f8bf2cd943685c3b5498,AAVE,45,1200000000
...
```

---

## 3. Correlation & Covariance Analysis

### 3.1 Methodology

#### Return Calculation
- **Daily Returns:** `log(close_t / close_t-1)`
- **Rolling Windows:** 30d, 60d, 90d, 180d
- **Lookback Period:** Full history (2020-01-01 to present)

#### Correlation Analysis
For each category basket:
1. **Pairwise Correlations:** Compute correlation matrix of all coins in basket
2. **Average Intra-Basket Correlation:** Mean of upper triangle of correlation matrix
3. **Rolling Correlation:** Track how correlation evolves over time
4. **Correlation Stability:** Standard deviation of rolling correlation

#### Covariance Analysis
For each category basket:
1. **Covariance Matrix:** Daily return covariance
2. **Principal Components:** PCA to identify basket's main drivers
3. **Variance Explained:** % of variance explained by PC1, PC2, PC3

### 3.2 Basket Construction

#### Equal-Weight Basket Return
```python
basket_return_t = mean(return_i,t for all i in basket)
```

#### Market-Cap-Weighted Basket Return
```python
basket_return_t = sum(weight_i,t * return_i,t)
where weight_i,t = market_cap_i,t / sum(market_cap_j,t for all j in basket)
```

#### Rank-Weighted Basket Return (Inverse of Size)
```python
basket_return_t = sum(weight_i,t * return_i,t)
where weight_i,t = (1 / market_cap_rank_i,t) / sum(1 / market_cap_rank_j,t for all j)
```

### 3.3 Analysis Script

**File:** `signals/analyze_basket_correlations.py`

**Outputs:**
- `backtests/results/basket_correlation_summary.csv`: Summary statistics per basket
- `backtests/results/basket_correlation_matrices/`: Correlation heatmaps per basket
- `backtests/results/basket_pca_analysis.csv`: PCA results per basket

**Key Metrics to Track:**
- Average pairwise correlation
- Correlation stability (std of rolling correlation)
- % of variance explained by PC1
- Number of coins in basket with sufficient data
- Date range of available data

---

## 4. Divergence Signal Generation

### 4.1 Divergence Metrics

#### Z-Score Divergence
For each coin `i` in basket `B`:
```python
# Step 1: Calculate basket return (excluding coin i)
basket_return_t = mean(return_j,t for all j in B where j != i)

# Step 2: Calculate relative performance
relative_perf_i,t = return_i,t - basket_return_t

# Step 3: Calculate rolling z-score
z_score_i,t = (relative_perf_i,t - mean(relative_perf_i, window=60)) / std(relative_perf_i, window=60)
```

#### Cumulative Divergence
For each coin `i` in basket `B`:
```python
# Step 1: Calculate cumulative returns over lookback window (e.g., 20 days)
cum_return_i = product(1 + return_i,t for t in [t-20, t]) - 1
cum_basket_return = product(1 + basket_return_t for t in [t-20, t]) - 1

# Step 2: Calculate divergence
divergence_i,t = cum_return_i - cum_basket_return
```

#### Percentile Rank Divergence
For each coin `i` in basket `B`:
```python
# Step 1: Calculate 20-day cumulative return for coin
cum_return_i = product(1 + return_i,t for t in [t-20, t]) - 1

# Step 2: Rank within basket
percentile_rank_i,t = percentile_rank(cum_return_i within basket B)
```

### 4.2 Signal Generation Rules

#### Mean-Reversion Signals (Short Outperformers, Long Underperformers)

**Long Signal (Underperformer):**
- Coin's z-score < -1.5 (significantly underperformed basket)
- Coin's percentile rank < 25th percentile within basket
- Coin has positive average correlation with basket (> 0.3)
- Minimum basket size: 5 coins with valid data

**Short Signal (Outperformer):**
- Coin's z-score > 1.5 (significantly outperformed basket)
- Coin's percentile rank > 75th percentile within basket
- Coin has positive average correlation with basket (> 0.3)
- Minimum basket size: 5 coins with valid data

#### Additional Filters
- **Liquidity Filter:** Only trade coins with 30-day avg volume > $5M
- **Volatility Filter:** Exclude coins with 30-day realized vol > 150% annualized
- **Market Cap Filter:** Minimum market cap > $50M
- **Data Quality:** Require at least 90 days of continuous price data

### 4.3 Implementation

**File:** `signals/calc_basket_divergence_signals.py`

**Inputs:**
- `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- `data/raw/custom_categories.csv`
- `data/raw/cmc_category_members.csv`

**Outputs:**
- `signals/basket_divergence_signals_full.csv`: All signals with scores
- `signals/basket_divergence_signals_current.csv`: Most recent signals
- `signals/basket_divergence_signals_by_category.csv`: Signals grouped by category

**Output Schema:**
```csv
date,symbol,category,signal,z_score,percentile_rank,basket_corr,basket_return_20d,coin_return_20d,divergence,market_cap,volume_30d_avg
2025-10-26,MATIC,L2 Scaling,LONG,-2.1,15.3,0.65,-0.05,-0.12,-0.07,8500000000,45000000
2025-10-26,ARB,L2 Scaling,SHORT,1.8,87.2,0.71,0.08,0.15,0.07,7200000000,120000000
...
```

---

## 5. Backtesting Strategy

### 5.1 Strategy Logic

#### Position Sizing
- **Portfolio Allocation:** Allocate X% of portfolio to pairs trading strategy
- **Position Sizing:** Equal-weight across all signals, OR weight by |z-score|
- **Max Positions:** Cap at N concurrent positions per category, M total positions
- **Leverage:** 1x for long positions, 1x for short positions (dollar-neutral)

#### Entry Rules
- **Signal Threshold:** |z-score| > 1.5
- **Holding Period:** Fixed N-day hold (e.g., 5, 10, 20 days)
- **Rebalance Frequency:** Daily check for new signals

#### Exit Rules
- **Mean Reversion Exit:** Close when z-score crosses back to [-0.5, 0.5]
- **Stop Loss:** Close if position loses > 10% (configurable)
- **Time-Based Exit:** Close after N days regardless of P&L
- **Take Profit:** Close if position gains > 15% (configurable)

#### Long/Short Pairing
- **Option 1 - Basket Hedging:** Long underperformers, short equal-weight basket
- **Option 2 - Pairwise Hedging:** Long underperformer, short outperformer in same basket
- **Option 3 - Market Neutral:** Maintain 0 net beta by balancing long/short notional

### 5.2 Backtest Implementation

**File:** `backtests/scripts/backtest_basket_pairs_trading.py`

#### Parameters
```python
LOOKBACK_WINDOW = 60  # days for z-score calculation
SIGNAL_THRESHOLD = 1.5  # |z-score| threshold for entry
HOLDING_PERIOD = 10  # days
STOP_LOSS = -0.10  # -10%
TAKE_PROFIT = 0.15  # +15%
MAX_POSITIONS_PER_CATEGORY = 3
MAX_TOTAL_POSITIONS = 20
POSITION_SIZE_METHOD = 'equal_weight'  # or 'z_score_weight'
BASKET_WEIGHT_METHOD = 'market_cap'  # 'equal_weight', 'market_cap', 'inverse_rank'
```

#### Backtest Procedure
1. **Data Preparation:**
   - Load price data, category mappings
   - Calculate daily returns for all coins
   - Filter by liquidity and data quality

2. **Rolling Window Backtest:**
   - For each day `t`:
     - Calculate basket returns for all categories
     - Calculate z-scores for all coins in all baskets
     - Generate signals based on thresholds
     - Apply liquidity/volatility/market cap filters
     - Enter new positions (up to max limits)
     - Check exit conditions for existing positions
     - Record P&L, exposure, turnover

3. **Performance Calculation:**
   - Calculate daily strategy returns
   - Compute cumulative returns, Sharpe ratio, max drawdown
   - Calculate turnover, win rate, avg hold period
   - Break down performance by category

#### No-Lookahead Validation
- **Critical Rule:** Signals generated on day `t` use returns from day `t+1`
- **Signal Calculation:** Use data up to and including day `t`
- **Execution:** Apply returns from day `t+1` for P&L
- **Example:**
  ```python
  signal_t = generate_signal(data[data.date <= t])
  return_t1 = data[data.date == t + 1]['return']
  pnl_t1 = signal_t * return_t1
  ```

### 5.3 Performance Metrics

#### Strategy-Level Metrics
- **Total Return:** Cumulative return over backtest period
- **Annualized Return:** CAGR
- **Annualized Volatility:** Std of daily returns * sqrt(252)
- **Sharpe Ratio:** (Return - RFR) / Volatility
- **Sortino Ratio:** (Return - RFR) / Downside Volatility
- **Max Drawdown:** Largest peak-to-trough decline
- **Calmar Ratio:** Return / Max Drawdown
- **Win Rate:** % of profitable trades
- **Avg Win:** Average return on winning trades
- **Avg Loss:** Average return on losing trades
- **Profit Factor:** Gross profit / Gross loss
- **Turnover:** Daily avg % of portfolio traded

#### Category-Level Metrics
- Track performance by category to identify which baskets work best
- Analyze correlation breakdown during crisis periods
- Identify categories with highest mean-reversion vs. momentum

#### Comparison Benchmarks
- **Buy & Hold BTC:** Long-only BTC benchmark
- **Equal-Weight Crypto Index:** Buy and hold equal-weight basket of all coins
- **Market-Cap-Weight Index:** Buy and hold market-cap-weighted basket
- **Existing Strategies:** Compare to breakout, carry, mean reversion strategies

### 5.4 Output Artifacts

**Files:**
- `backtests/results/pairs_trading_equity_curve.csv`: Daily portfolio value
- `backtests/results/pairs_trading_performance_summary.csv`: Summary metrics
- `backtests/results/pairs_trading_trades_log.csv`: Trade-by-trade log
- `backtests/results/pairs_trading_category_breakdown.csv`: Performance by category
- `backtests/results/pairs_trading_equity_curve.png`: Equity curve plot
- `backtests/results/pairs_trading_drawdown.png`: Drawdown plot
- `backtests/results/pairs_trading_category_heatmap.png`: Category performance heatmap

**Trade Log Schema:**
```csv
entry_date,exit_date,symbol,category,signal,entry_price,exit_price,return,hold_days,exit_reason,z_score_entry,basket_return,market_cap
2025-01-15,2025-01-25,MATIC,L2 Scaling,LONG,0.85,0.92,0.082,10,mean_revert,-2.1,-0.05,8500000000
...
```

---

## 6. Implementation Roadmap

### Phase 1: Data Collection & Category Definition (Week 1)
- [ ] **Task 1.1:** Manually explore CMC category webpage, document categories
- [ ] **Task 1.2:** Investigate CMC API for category endpoints
- [ ] **Task 1.3:** Implement `data/scripts/fetch_cmc_categories.py`
- [ ] **Task 1.4:** Create custom category mapping file `data/raw/custom_categories.csv`
- [ ] **Task 1.5:** Validate category membership (check for missing coins, duplicates)

### Phase 2: Correlation Analysis (Week 1-2)
- [ ] **Task 2.1:** Implement `signals/analyze_basket_correlations.py`
- [ ] **Task 2.2:** Calculate pairwise correlations for all baskets
- [ ] **Task 2.3:** Perform PCA analysis for each basket
- [ ] **Task 2.4:** Generate correlation heatmaps and summary statistics
- [ ] **Task 2.5:** Identify baskets with highest/lowest correlation stability

### Phase 3: Signal Generation (Week 2)
- [ ] **Task 3.1:** Implement basket return calculation (equal-weight, market-cap-weight)
- [ ] **Task 3.2:** Implement z-score divergence calculation
- [ ] **Task 3.3:** Implement percentile rank divergence calculation
- [ ] **Task 3.4:** Apply liquidity, volatility, and market cap filters
- [ ] **Task 3.5:** Generate signal files: `signals/basket_divergence_signals_full.csv`

### Phase 4: Backtesting (Week 3)
- [ ] **Task 4.1:** Implement `backtests/scripts/backtest_basket_pairs_trading.py`
- [ ] **Task 4.2:** Validate no-lookahead bias (use `.shift(-1)` for returns)
- [ ] **Task 4.3:** Run backtest with baseline parameters
- [ ] **Task 4.4:** Generate performance metrics and trade log
- [ ] **Task 4.5:** Create visualization scripts (equity curve, drawdown, heatmaps)

### Phase 5: Parameter Sensitivity & Optimization (Week 4)
- [ ] **Task 5.1:** Test multiple lookback windows (30d, 60d, 90d, 180d)
- [ ] **Task 5.2:** Test multiple signal thresholds (1.0, 1.5, 2.0)
- [ ] **Task 5.3:** Test multiple holding periods (5d, 10d, 20d, 30d)
- [ ] **Task 5.4:** Test different basket weighting schemes
- [ ] **Task 5.5:** Compare market-neutral vs. long-only vs. long-short strategies

### Phase 6: Analysis & Documentation (Week 4)
- [ ] **Task 6.1:** Compare pairs trading to existing single-asset strategies
- [ ] **Task 6.2:** Analyze performance by market regime (bull, bear, sideways)
- [ ] **Task 6.3:** Identify best-performing categories and worst-performing categories
- [ ] **Task 6.4:** Document findings in `docs/PAIRS_TRADING_RESULTS.md`
- [ ] **Task 6.5:** Update `docs/RESEARCH_TODO.md` with next steps

---

## 7. Expected Insights

### Key Questions to Answer
1. **Correlation Structure:**
   - Which categories have the strongest intra-basket correlation?
   - How stable are correlations over time?
   - Do correlations break down during market stress?

2. **Divergence Patterns:**
   - How often do coins diverge significantly from their basket?
   - What is the typical time for divergences to mean-revert?
   - Are divergences more pronounced in certain categories?

3. **Strategy Performance:**
   - Does pairs trading outperform buy-and-hold on a risk-adjusted basis?
   - Which categories provide the best pairs trading opportunities?
   - How does pairs trading compare to existing strategies (breakout, carry)?

4. **Risk Characteristics:**
   - What is the maximum drawdown of pairs trading strategies?
   - How does pairs trading perform during bear markets?
   - What is the correlation of pairs trading returns to BTC/ETH?

### Success Criteria
- **Minimum Sharpe Ratio:** > 0.5 (annualized)
- **Maximum Drawdown:** < 30%
- **Win Rate:** > 50%
- **Profit Factor:** > 1.5
- **Low BTC Correlation:** < 0.4

### Risk Factors to Monitor
- **Correlation Breakdown:** Baskets may decorrelate during extreme events
- **Liquidity Risk:** Smaller coins may have thin markets, high slippage
- **Shorting Costs:** Funding rates for shorts can be significant
- **Regime Shift:** Mean-reversion may fail if coins undergo structural change
- **Survivorship Bias:** Categories may include delisted/failed coins

---

## 8. Integration with Existing System

### Data Integration
- Leverage existing price data: `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- Reuse market cap, volume, and symbol data already collected
- Add category mappings as new dimension to existing data

### Signal Integration
- Pairs trading signals can be combined with existing signals:
  - Breakout signals
  - Carry factor signals
  - Mean reversion signals
  - Days-from-high signals

### Backtest Integration
- Follow existing backtest framework conventions:
  - Same metrics (Sharpe, drawdown, turnover)
  - Same file naming conventions
  - Same output directory structure

### Execution Integration
- Pairs trades can be executed using existing execution scripts:
  - `execution/ccxt_make_order.py` for order placement
  - `execution/check_positions.py` for position monitoring
  - Support for both long and short positions

---

## 9. Alternative Approaches to Consider

### Statistical Arbitrage Variants
1. **Cointegration-Based Pairs:** Instead of correlation, test for cointegration between coin pairs
2. **Residual Trading:** Trade residuals from regression of coin returns on basket returns
3. **Eigenportfolio Trading:** Trade first few principal components of basket

### Machine Learning Approaches
1. **Clustering:** Use ML to discover categories (vs. manual definition)
2. **Regime Detection:** Use HMM/state-space models to detect correlation regimes
3. **Prediction:** Train model to predict which divergences will mean-revert

### Alternative Signals
1. **Funding Rate Divergence:** Trade coins with funding rates diverging from basket
2. **Open Interest Divergence:** Trade coins with OI diverging from basket OI
3. **On-Chain Metrics:** Incorporate on-chain data (active addresses, transaction volume)

---

## 10. References & Resources

### CoinMarketCap API Documentation
- Main docs: https://coinmarketcap.com/api/documentation/v1/
- Categories endpoint: `/v1/cryptocurrency/categories` (if available)
- Rate limits: https://coinmarketcap.com/api/features/

### Academic Literature
- Gatev, Goetzmann, Rouwenhorst (2006): "Pairs Trading: Performance of a Relative-Value Arbitrage Rule"
- Do & Faff (2010): "Does Simple Pairs Trading Still Work?"
- Krauss (2017): "Statistical Arbitrage Pairs Trading Strategies: Review and Outlook"

### Existing Codebase
- Price data: `data/raw/combined_coinbase_coinmarketcap_daily.csv`
- CMC fetching: `data/scripts/fetch_coinmarketcap_data.py`
- Backtest examples: `backtests/scripts/backtest_mean_reversion.py`
- Signal examples: `signals/calc_open_interest_divergence.py`

---

## 11. Next Steps

1. **Review & Approval:** Get feedback on this spec from team/stakeholders
2. **Set Up Dev Environment:** Ensure CMC API key is configured (`CMC_API` env var)
3. **Begin Phase 1:** Start with category research and data collection
4. **Iterate:** Update this spec as we learn more during implementation

---

**Document Owner:** Research Team  
**Last Updated:** 2025-10-26  
**Next Review:** After Phase 2 completion
