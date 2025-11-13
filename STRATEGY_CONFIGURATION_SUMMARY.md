# Strategy Configuration Summary

**As of: 2025-11-07**  
**Configuration File: `/workspace/execution/all_strategies_config.json`**

---

## Current Strategy Weights (Ensemble MVO Optimized)

| Strategy | Weight | Method | Notes |
|----------|--------|--------|-------|
| **leverage_inverted** | 33.28% | **Rank-based (top_n/bottom_n)** | Dominant allocation - low correlation diversifier |
| **volatility** | 14.36% | **Rank-based (top_n/bottom_n)** | High Sharpe (1.08), proven performer |
| **turnover** | 10.00% | **Rank-based (top_n/bottom_n)** | Exceptional backtest (Sharpe: 2.17) |
| **breakout** | 9.11% | **Binary trades** | Inverse-vol weighted breakout signals |
| **beta** | 8.25% | **Rank-based (top_n/bottom_n)** | Betting Against Beta factor |
| **mean_reversion** | 5.00% | **Binary trades (long-only)** | CAPPED - high volatility, extreme dips only |
| **carry** | 5.00% | **Rank-based (top_n/bottom_n)** | CAPPED - funding rate factor |
| **kurtosis** | 5.00% | **Rank-based (top_n/bottom_n)** | CAPPED - regime-filtered (bear_only) |
| **adf** | 5.00% | **Rank-based (top_n/bottom_n)** | CAPPED - trend following premium |
| **dilution** | 5.00% | **Rank-based (top_n/bottom_n)** | CAPPED - testing new factor |
| **size** | 0.00% | **Rank-based (top_n/bottom_n)** | Disabled - negative Sharpe |
| **days_from_high** | 0.00% | **Binary trades** | Disabled - negative Sharpe |
| **trendline_breakout** | 0.00% | **Binary trades** | Disabled - not included |

---

## Selection Methods by Strategy

### 1. **Binary Trades** (Signal-Based Selection)
Strategies that generate discrete buy/sell signals and trade all qualifying instruments:

#### **Breakout** (9.11% weight)
- **Method**: Binary buy/sell signals based on 50-day high/low breakouts
- **Selection**: All coins breaking 50d high (LONG) or 50d low (SHORT)
- **Weighting**: Inverse 30-day volatility (risk parity)
- **Rebalance**: Daily (implied by breakout nature)
- **Parameters**:
  - `entry_lookback`: 50 days
  - `exit_lookback`: 70 days

#### **Mean Reversion** (5.00% weight - CAPPED)
- **Method**: Binary signals for extreme dips with high volume
- **Selection**: ALL coins meeting criteria (z-score < -1.5, volume z > 1.0)
- **Direction**: LONG-ONLY (shorting rallies doesn't work)
- **Weighting**: Inverse 30-day volatility
- **Rebalance**: 2-day lookback optimal
- **Parameters**:
  - `zscore_threshold`: 1.5
  - `volume_threshold`: 1.0
  - `period_days`: 2 (lookback)
  - `long_only`: true

#### **Days from High** (0.00% - DISABLED)
- **Method**: Binary selection of coins near 200-day highs
- **Selection**: All coins within `max_days` of 200d high
- **Weighting**: Inverse volatility
- **Status**: Disabled due to negative Sharpe (-0.51)

#### **Trendline Breakout** (0.00% - DISABLED)
- **Method**: Binary signals for trendline momentum continuation
- **Selection**: All coins breaking established trendlines
- **Status**: Not included in current optimization

---

### 2. **Rank-Based (Top N / Bottom N)** Selection
Strategies that rank all coins and select fixed number of top/bottom positions:

#### **Leverage Inverted** (33.28% weight - DOMINANT)
- **Method**: Rank by OI/Market Cap ratio
- **Selection**: 
  - LONG: Bottom 10 (lowest leverage - fundamentals)
  - SHORT: Top 10 (highest leverage - speculation)
- **Weighting**: Risk parity (inverse volatility)
- **Rebalance**: 7 days
- **Performance**: Sharpe 1.19, +53.91% total, -12.10% max DD
- **Parameters**:
  - `top_n`: 10 (high leverage to short)
  - `bottom_n`: 10 (low leverage to long)

#### **Volatility** (14.36% weight)
- **Method**: Rank by 30-day annualized volatility
- **Selection**:
  - LONG: Bottom 10 (lowest volatility - stable)
  - SHORT: Top 10 (highest volatility - unstable)
- **Weighting**: Risk parity (inverse volatility)
- **Rebalance**: 3 days (optimal per backtest)
- **Performance**: Sharpe 1.40, +1,895% total, -38.41% max DD
- **Parameters**:
  - `top_n`: 10
  - `bottom_n`: 10
  - `volatility_window`: 30 days
  - `strategy_type`: "long_low_short_high"

#### **Turnover** (10.00% weight)
- **Method**: Rank by 24h Volume / Market Cap ratio
- **Selection**:
  - LONG: Top 10 (high turnover - liquid)
  - SHORT: Bottom 10 (low turnover - illiquid)
- **Weighting**: Risk parity (inverse volatility)
- **Rebalance**: 30 days
- **Performance**: Sharpe 2.17 (exceptional), +118.61% total, -11.69% max DD
- **Parameters**:
  - `top_n`: 10
  - `bottom_n`: 10
  - `rebalance_days`: 30

#### **Beta** (8.25% weight)
- **Method**: Rank by 90-day beta to BTC
- **Selection**:
  - LONG: Bottom 10 (lowest beta - defensive)
  - SHORT: Top 10 (highest beta - aggressive)
- **Weighting**: Risk parity (inverse volatility)
- **Rebalance**: 5 days (optimal)
- **Performance**: Sharpe 0.71, +261.38% total, -39.27% max DD
- **Parameters**:
  - `top_n`: 10
  - `bottom_n`: 10
  - `beta_window`: 90 days
  - `volatility_window`: 30 days

#### **Carry** (5.00% weight - CAPPED)
- **Method**: Rank by funding rate (aggregated across exchanges)
- **Selection**:
  - LONG: Bottom 10 (most negative funding - receive funding)
  - SHORT: Top 10 (most positive funding - pay funding)
- **Weighting**: Inverse 30-day volatility
- **Rebalance**: 7 days (weekly)
- **Universe**: Filtered to top 150 by market cap
- **Parameters**:
  - `top_n`: 10
  - `bottom_n`: 10
  - `exchange_id`: "hyperliquid"

#### **Kurtosis** (5.00% weight - CAPPED, REGIME-FILTERED)
- **Method**: Rank by 30-day return distribution kurtosis
- **Selection** (Mean Reversion mode):
  - LONG: Bottom 10 (low kurtosis - stable)
  - SHORT: Top 10 (high kurtosis - fat tails)
- **Weighting**: Risk parity (inverse volatility)
- **Rebalance**: 14 days
- **Regime Filter**: **BEAR ONLY** (critical - strategy toxic in bull markets)
  - Bear/Low-Vol: +28% to +50% annualized (Sharpe 1.79)
  - Bull markets: -25% to -90% annualized (INACTIVE)
- **Parameters**:
  - `top_n`: 10
  - `bottom_n`: 10
  - `regime_filter`: "bear_only"
  - `strategy_type`: "mean_reversion"

#### **ADF** (5.00% weight - CAPPED)
- **Method**: Rank by ADF statistic (stationarity test)
- **Selection** (Regime-aware):
  - Trend Following: LONG high ADF (trending), SHORT low ADF (stationary)
  - Mean Reversion: LONG low ADF (stationary), SHORT high ADF (trending)
- **Regime Detection**: Based on BTC 5-day % change
- **Weighting**: Risk parity (inverse volatility)
- **Rebalance**: 7 days
- **Mode**: "blended" (conservative 80/20 allocation)
- **Performance**: Sharpe 0.49, +126.29% total, -50.60% max DD
- **Parameters**:
  - `top_n`: 10
  - `bottom_n`: 10
  - `mode`: "blended"
  - `adf_window`: 60 days

#### **Dilution** (5.00% weight - CAPPED, TESTING)
- **Method**: Rank by dilution velocity (% max supply unlocked per year)
- **Selection**:
  - LONG: Bottom 10 (lowest dilution - conservative unlock)
  - SHORT: Top 10 (highest dilution - aggressive unlock)
- **Weighting**: Risk parity (inverse volatility)
- **Rebalance**: 7 days
- **Performance**: Sharpe 1.07, +2,826% total (monthly rebalance)
- **Parameters**:
  - `top_n`: 10
  - `bottom_n`: 10
  - `lookback_months`: 12

#### **Size** (0.00% - DISABLED)
- **Method**: Rank by market capitalization
- **Selection**:
  - LONG: Bottom 10 (small caps)
  - SHORT: Top 10 (large caps)
- **Status**: Disabled due to negative Sharpe (-0.41)
- **Parameters**:
  - `top_n`: 10
  - `bottom_n`: 10
  - `rebalance_days`: 10

---

### 3. **Percentile-Based Selection** (DEPRECATED)
**Note**: All strategies have migrated from percentile-based to fixed rank-based (top_n/bottom_n) selection.

The following parameters are **DEPRECATED** but remain in config for backward compatibility:
- `long_percentile`: 10
- `short_percentile`: 90
- `num_quintiles`: 10

All strategies now use **`top_n`** and **`bottom_n`** instead of percentiles for more consistent position sizing.

---

## Portfolio Construction Details

### Overall Portfolio Metrics (Expected)
- **Sharpe Ratio**: 1.709
- **Expected Return**: 13.70% annualized
- **Expected Volatility**: 8.02%
- **Expected Max Drawdown**: -38%
- **Optimization Method**: Ensemble (Avg of Regularized MVO + Risk Parity + Max Diversification)
- **Stability**: 30% reduction in turnover vs standard MVO

### Strategy Caps (Safety Limits)
The following strategies are **hard-capped** in `main.py` regardless of optimization results:

1. **Mean Reversion**: 5% max (extreme volatility 76.9%, regime-dependent)
2. **Leverage Inverted**: No cap (testing complete, dominant allocator)
3. **Dilution**: 5% max (testing new strategy, high volatility)
4. **Kurtosis**: 5% max (regime-dependent: bear_only)
5. **Negative Sharpe strategies**: Auto-capped at 5% or excluded

### Capital Reallocation Logic
When strategies return no positions (e.g., regime filter blocks kurtosis):

1. **Fixed Weight Strategies** (maintain allocation):
   - Breakout
   - Days from High (if enabled)

2. **Flexible Weight Strategies** (receive reallocated capital):
   - All other strategies proportionally scale up to absorb inactive capital
   - Example: If kurtosis (5%) is filtered out, that 5% redistributes to other flexible strategies

3. **Regime-Filtered Strategies**:
   - Kurtosis: Inactive in bull markets (capital reallocated)
   - ADF: Adjusts allocation based on regime but always generates positions

---

## Selection Method Summary

| Selection Method | # of Strategies | Weight Total | Description |
|------------------|-----------------|--------------|-------------|
| **Rank-based (top_n/bottom_n)** | 9 active + 1 disabled | 85.89% | Fixed position count (typically 10 long + 10 short) |
| **Binary trades** | 1 active + 2 disabled | 14.11% | All qualifying instruments traded |
| **Percentile-based** | 0 (deprecated) | 0% | Replaced by rank-based |

---

## Key Implementation Notes

### 1. **Lookahead Bias Prevention**
All strategies use `.shift(-1)` for next-day returns in backtesting:
- Signals generated on day T → executed with returns from day T+1
- Rolling calculations exclude current day

### 2. **Risk Parity Weighting**
Most rank-based strategies use **inverse volatility weighting**:
- Position size ∝ 1 / volatility
- Lower vol assets get higher weight (risk equalization)
- Typically 30-day rolling volatility window

### 3. **Rebalance Frequencies** (Optimized per strategy)
- **Daily (1d)**: Trendline Breakout
- **2-3 days**: Mean Reversion (2d), Volatility (3d)
- **5 days**: Beta
- **7 days**: Carry, ADF, Leverage Inverted, Dilution
- **10 days**: Size
- **14 days**: Kurtosis
- **30 days**: Turnover

### 4. **Regime Filters** (Critical for performance)
- **Kurtosis**: `bear_only` - MANDATORY (toxic in bull markets)
- **ADF**: Regime-aware allocation adjustment (not a filter, always active)

### 5. **Data Dependencies**
- **CoinMarketCap API**: Market cap data (Size, Mean Reversion, Carry)
- **Coinalyze API**: Funding rates (Carry), OI data (Leverage Inverted)
- **Historical dilution data**: Token unlock schedules (Dilution)
- Main execution auto-refreshes data for Leverage/Dilution strategies

---

## Configuration File Location

**Primary Config**: `/workspace/execution/all_strategies_config.json`

To modify strategy weights or parameters:
1. Edit `all_strategies_config.json`
2. Weights are automatically normalized to sum to 100%
3. Safety caps applied in `main.py` (Mean Reversion, Dilution at 5%)
4. Run: `python3 execution/main.py --dry-run` to test

---

## Running the Strategies

### Default Execution (uses all_strategies_config.json)
```bash
python3 execution/main.py --dry-run
```

### Custom Config
```bash
python3 execution/main.py --signal-config path/to/custom_config.json --dry-run
```

### CLI Override (equal weights)
```bash
python3 execution/main.py --signals size,beta,volatility --dry-run
```

### Execution Modes
- `--limits` (default): Aggressive limit order execution
- `--market`: Simple market orders
- `--patient [SPREAD]`: Spread offset orders with intelligent splitting

---

## Recent Changes

### 2025-11-06: Percentile → Rank Migration
All strategies migrated from percentile-based to fixed rank-based selection (top_n/bottom_n) for:
- More consistent position sizing
- Easier to understand and backtest
- Better control over portfolio concentration

### 2025-11-02: Ensemble MVO Weights
Portfolio reoptimized using ensemble method (Regularized MVO + Risk Parity + Max Diversification):
- 30% more stable than standard MVO
- Leverage Inverted promoted to 33.28% (dominant allocator)
- Volatility increased to 14.36% (high Sharpe)
- Size, ADF reduced to 5% (negative Sharpe)

### 2025-11-02: Strategy Caps Implemented
Safety caps enforced in main.py:
- Mean Reversion: 5% (extreme volatility)
- Dilution: 5% (testing)
- Kurtosis: 5% (regime-dependent)
- Negative Sharpe strategies: 5% or excluded

---

*Last Updated: 2025-11-07*
*Generated from: execution/main.py and execution/all_strategies_config.json*
