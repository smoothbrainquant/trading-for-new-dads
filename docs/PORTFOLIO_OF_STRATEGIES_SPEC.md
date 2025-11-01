# Portfolio of Strategies Backtest Specification
## Enhanced Risk Parity with Correlation

**Version:** 1.0  
**Date:** 2025-10-26  
**Status:** Draft for Implementation  

---

## 1. Executive Summary

### Objective
Build a meta-strategy backtest that combines **6 individual strategies** (Carry, Breakout, Mean Reversion, Days-from-High, Size Factor, OI Divergence) using **Enhanced Risk Parity** weighting that accounts for correlation structure. This approach aims to maximize risk-adjusted returns through intelligent diversification across uncorrelated return streams spanning multiple market regimes and signal types.

### Key Innovation
Unlike simple risk parity (inverse volatility) which treats strategies independently, Enhanced Risk Parity explicitly accounts for correlation to:
- Reduce over-allocation to correlated strategies
- Increase allocation to diversifying strategies
- Optimize portfolio-level risk contribution

### Expected Outcomes
- Sharpe ratio improvement of 20-50% vs equal-weight or simple risk parity
- Lower maximum drawdown through better diversification
- More stable returns across different market regimes
- Clear performance attribution across constituent strategies
- Reduced correlation to BTC through multi-factor diversification

---

## 2. Strategy Universe

### 2.1 Constituent Strategies

| Strategy | Signal Logic | Expected Return Driver | Typical Volatility | Market Regime |
|----------|--------------|------------------------|-------------------|---------------|
| **Carry Factor** | Long low FR, Short high FR | Funding rate mean reversion | Medium | Range-bound |
| **Breakout** | Long 50d high, Short 50d low | Trend continuation | High | Trending |
| **Mean Reversion** | Long oversold, Short overbought | Price mean reversion | Medium-High | Range-bound |
| **Days-from-High** | Long coins near 200d high | Momentum | Medium | Trending |
| **Size Factor** | Long small-cap, Short large-cap | Small cap premium | High | Bull markets |
| **OI Divergence** | Contrarian OI/price signals | Mean reversion via OI | Medium-High | Volatile markets |

**Notes:**
- **Size Factor**: Long bottom quintile (small caps), short top quintile (large caps). Exploits size premium similar to equity markets.
- **OI Divergence**: Uses "divergence mode" (contrarian) which historically outperforms trend mode. Signals based on open interest vs price divergence.

**Why 6 Strategies?**
This portfolio spans multiple dimensions of crypto market inefficiencies:
1. **Time-series factors**: Breakout, Mean Reversion (technical price patterns)
2. **Cross-sectional factors**: Days-from-High, Size (relative ranking)
3. **Market microstructure**: Carry (funding rates), OI Divergence (positioning)
4. **Regime diversity**: 3 trend-following + 3 mean-reverting strategies for balance

The diversity across signal types, data sources, and market regimes provides robust diversification beyond simple correlation analysis.

### 2.2 Strategy Correlation Expectations

Expected correlation structure (6×6):
```
                Carry    Breakout   MeanRev   Days-High   Size    OI-Div
Carry            1.00      -0.20      0.30     -0.15      0.10     0.25
Breakout        -0.20       1.00     -0.40      0.60      0.30    -0.30
MeanRev          0.30      -0.40      1.00     -0.30      0.10     0.35
Days-High       -0.15       0.60     -0.30      1.00      0.40    -0.20
Size             0.10       0.30      0.10      0.40      1.00     0.15
OI-Div           0.25      -0.30      0.35     -0.20      0.15     1.00
```

**Strategy Clusters:**
- **Mean Reversion Cluster**: Carry, Mean Reversion, OI Divergence (positive correlations)
- **Momentum Cluster**: Breakout, Days-from-High, Size (positive correlations)
- **Cross-Cluster**: Negative correlations provide diversification benefit

**Note:** Actual correlations will be computed from realized returns and will vary over time. These expectations help inform initial portfolio construction.

### 2.3 Strategy Diversification Map

```
Portfolio Structure:

┌─────────────────────────────────────────────────────────────┐
│                    MEAN REVERSION CLUSTER                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │    CARRY     │──│ MEAN REVERT  │──│ OI DIVERGENCE│     │
│  │ (Funding FR) │  │ (Price Mean) │  │  (OI/Price)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│   Range-bound       Range-bound       Volatile markets     │
└─────────────────────────────────────────────────────────────┘
                              │
                    NEGATIVE CORRELATION
                              │
┌─────────────────────────────────────────────────────────────┐
│                     MOMENTUM CLUSTER                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  BREAKOUT    │──│ DAYS-FROM-   │──│  SIZE FACTOR │     │
│  │ (50d high/low│  │   HIGH       │  │ (Small-cap)  │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│   Trending          Trending          Bull markets         │
└─────────────────────────────────────────────────────────────┘

Legend:
  ── Positive correlation (cluster members)
  │  Negative correlation (across clusters)
  
Expected Behavior:
- Mean Reversion cluster outperforms in choppy/ranging markets
- Momentum cluster outperforms in trending/bull markets
- Enhanced RP automatically shifts allocation based on regime
- Cross-cluster negative correlations provide drawdown protection
```

### 2.4 Expected Benefits of 6-Strategy Diversification

| Benefit | Description | Expected Impact |
|---------|-------------|-----------------|
| **Regime Coverage** | 3 strategies per regime type | ±30% Sharpe improvement |
| **Signal Diversity** | Price, FR, OI, Size data sources | Lower correlation to BTC |
| **Drawdown Protection** | Negative cross-cluster correlation | 20-30% DD reduction |
| **Capacity** | Spread across 6 different universes | Higher AUM capacity |
| **Robustness** | No single strategy dominates | Stable through market cycles |

---

## 3. Weighting Methodology: Enhanced Risk Parity

### 3.1 Conceptual Framework

**Simple Risk Parity** (current implementation):
- Weight each strategy inversely to its volatility
- Assumes strategies are uncorrelated
- Formula: `w_i = (1/σ_i) / Σ(1/σ_j)`

**Enhanced Risk Parity** (proposed):
- Weight strategies to equalize risk contribution accounting for correlations
- Risk contribution of strategy i: `RC_i = w_i × (Σw)_i` where Σ is covariance matrix
- Target: `RC_1 = RC_2 = ... = RC_n = Portfolio Risk / n`

### 3.2 Mathematical Formulation

Given:
- **μ** = vector of expected returns (optional, can use historical)
- **Σ** = n×n covariance matrix of strategy returns
- **w** = vector of portfolio weights
- **σ_p** = portfolio volatility = √(w^T Σ w)

Objective:
```
Find w such that:
  RC_i = w_i × (Σw)_i / σ_p = 1/n  for all i

Subject to:
  Σw_i = 1            (fully invested)
  w_i ≥ w_min         (minimum allocation, e.g., 5%)
  w_i ≤ w_max         (maximum allocation, e.g., 50%)
```

This is solved via numerical optimization (scipy.optimize).

### 3.3 Implementation Algorithm

```python
def calculate_enhanced_rp_weights(strategy_returns_df, 
                                  lookback_days=60,
                                  min_weight=0.05,
                                  max_weight=0.50,
                                  shrinkage_factor=0.3):
    """
    Step 1: Compute covariance matrix from strategy returns
      - Use rolling window (default 60 days)
      - Apply shrinkage toward diagonal (reduce estimation error)
    
    Step 2: Solve optimization problem
      - Objective: Minimize difference in risk contributions
      - Constraints: weights sum to 1, bounds on individual weights
    
    Step 3: Return weights vector
    """
    # Covariance estimation with shrinkage
    sample_cov = strategy_returns_df.cov()
    target_cov = np.diag(np.diag(sample_cov))  # Diagonal matrix
    shrunk_cov = (1 - shrinkage_factor) * sample_cov + shrinkage_factor * target_cov
    
    # Optimization
    weights = solve_risk_parity_optimization(
        cov_matrix=shrunk_cov,
        min_weight=min_weight,
        max_weight=max_weight
    )
    
    return weights
```

### 3.4 Covariance Estimation Details

**Lookback Window:**
- Primary: 60 trading days (~2 months)
- Rationale: Balance between stability and adaptation
- Alternative: 90 days for more stable estimates

**Shrinkage:**
- Ledoit-Wolf shrinkage toward diagonal matrix
- Shrinkage intensity: 0.2 - 0.4
- Purpose: Reduce estimation error in off-diagonal correlations
- Formula: `Σ_shrunk = (1-λ) × Σ_sample + λ × Σ_diagonal`

**Handling Missing Data:**
- Require minimum 30 days of overlapping returns
- If strategy lacks sufficient history, exclude temporarily
- Redistribute weights among available strategies

### 3.5 Special Considerations for 6-Strategy Portfolio

**Higher Dimensional Covariance:**
- 6×6 covariance matrix = 21 unique correlations to estimate
- Shrinkage becomes more important with higher dimensions
- Consider increasing shrinkage intensity (0.30-0.40) vs 4-strategy portfolio

**Weight Concentration Risk:**
- With `min_weight=0.05`, `max_weight=0.50`, theoretical range is 5-50% per strategy
- In practice, expect 10-25% per strategy with ERP
- Monitor for excessive concentration (>40% in any single strategy)

**Cluster Analysis:**
- Mean Reversion cluster (3 strategies): May receive 40-50% combined weight in range-bound markets
- Momentum cluster (3 strategies): May receive 40-50% combined weight in trending markets
- Enhanced RP naturally adjusts allocation based on regime

**Optimization Stability:**
- 6 strategies more sensitive to estimation error than 4
- Use longer lookback (60-90 days) for more stable estimates
- Consider monthly rebalancing to reduce turnover

**Computation:**
- 6×6 optimization still very fast (<1ms per rebalance)
- Memory and runtime not a concern

---

## 4. Backtest Design

### 4.1 Data Requirements

**Input Data:**
1. **Individual Strategy Returns**
   - Pre-computed daily returns for each strategy
   - Source: Run individual backtests first (all 6 strategies)
   - Format: CSV with columns `[date, strategy_name, daily_return, positions, exposure]`

2. **Price Data** (for performance verification)
   - Historical OHLCV data for constituent instruments
   - Used to verify strategy returns and calculate actual portfolio P&L

**Data Structure:**
```
backtests/results/
  ├── backtest_carry_factor_portfolio_values.csv
  ├── backtest_breakout_signals_portfolio_values.csv
  ├── backtest_mean_reversion_portfolio_values.csv
  ├── backtest_20d_200d_high_portfolio_values.csv
  ├── backtest_size_factor_portfolio_values.csv
  └── backtest_open_interest_divergence_portfolio_values.csv

Format of each file (standard backtest output):
date,portfolio_value,daily_return,num_long_positions,num_short_positions,...
2025-01-01,10123.45,0.0123,5,5,...
2025-01-02,10078.32,-0.0045,5,5,...
...
```

**Strategy Naming Convention:**
- `carry` - Carry Factor (funding rate arbitrage)
- `breakout` - Breakout Signals (trend following)
- `mean_reversion` - Mean Reversion (contrarian price)
- `days_from_high` - Days from 200d High (momentum)
- `size` - Size Factor (small cap premium)
- `oi_divergence` - OI Divergence (contrarian OI/price)

### 4.2 Backtest Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `initial_capital` | $100,000 | $10k-$1M | Starting portfolio value |
| `cov_lookback_days` | 60 | 30-120 | Days for covariance estimation |
| `rebalance_frequency` | Weekly | Daily/Weekly/Monthly | Weight recomputation frequency |
| `min_weight` | 0.05 | 0.0-0.15 | Minimum allocation per strategy |
| `max_weight` | 0.50 | 0.30-0.70 | Maximum allocation per strategy |
| `shrinkage_intensity` | 0.30 | 0.0-0.5 | Covariance shrinkage factor |
| `start_date` | Auto | - | First date with sufficient data |
| `end_date` | Auto | - | Last available date |

### 4.3 Rebalancing Logic

**Frequency:** Weekly (every Monday)
- Rationale: Balance between adaptation and transaction costs
- Alternative: Daily for high-frequency strategies, Monthly for cost-sensitive

**Rebalancing Workflow:**
```python
For each rebalancing date:
  1. Collect returns for all strategies from [date-lookback, date-1]
  2. Validate minimum data requirements (>30 days overlap)
  3. Compute covariance matrix with shrinkage
  4. Solve enhanced RP optimization for target weights
  5. Calculate weight changes from current positions
  6. Record trades and update positions
```

**Transaction Cost Modeling:**
- Basic: 0% (frictionless, for initial analysis)
- Enhanced: 0.1% per side (0.2% round-trip)
- Apply to absolute weight changes: `cost = 0.001 × Σ|Δw_i|`

### 4.4 Risk Management

**Position Limits:**
- Maximum 50% in any single strategy (diversification)
- Minimum 5% if strategy is included (avoid dust positions)
- Option to exclude poorly performing strategies (Sharpe < 0 over last 90d)

**Portfolio Constraints:**
- Target gross exposure: 100% (can be levered to 150% if desired)
- Net exposure: No explicit constraint (depends on strategy mix)
- Maximum portfolio volatility: Optional 40% annualized cap

**Fallback Mechanisms:**
- If optimization fails: Fall back to simple risk parity
- If covariance matrix is singular: Add small ridge regularization
- If all strategies have negative returns: Equal weight allocation

---

## 5. Performance Metrics

### 5.1 Portfolio-Level Metrics

**Return Metrics:**
- Total Return (%)
- Annualized Return (%)
- Daily/Weekly/Monthly Returns Distribution
- Cumulative Returns Chart

**Risk Metrics:**
- Annualized Volatility (%)
- Maximum Drawdown (%)
- Drawdown Duration (days)
- Value at Risk (VaR 95%, 99%)
- Conditional Value at Risk (CVaR)

**Risk-Adjusted Metrics:**
- Sharpe Ratio (assuming 0% risk-free rate)
- Sortino Ratio (downside deviation)
- Calmar Ratio (Return / Max Drawdown)
- Information Ratio (vs equal-weight benchmark)

**Other Statistics:**
- Win Rate (% profitable days)
- Average Win / Average Loss
- Longest Winning/Losing Streak
- Correlation to BTC (market beta)

### 5.2 Strategy Attribution

**Weight Analysis:**
- Time series of strategy weights
- Average weight per strategy
- Weight volatility (how much rebalancing)
- Time in min/max bound

**Return Attribution:**
- Contribution to portfolio return by strategy
- Strategy-level Sharpe ratios
- Correlation matrix (realized vs expected)
- Best/worst performing strategy by period

**Risk Attribution:**
- Risk contribution by strategy (RC_i)
- Marginal contribution to risk (MCR)
- Diversification ratio: `Σw_i×σ_i / σ_portfolio`

### 5.3 Comparative Analysis

**Benchmarks:**
1. **Equal Weight:** ~16.67% allocation to each of 6 strategies
2. **Simple Risk Parity:** Inverse volatility, no correlation
3. **Best Single Strategy:** Performance of top individual strategy
4. **60/40 BTC/Stablecoin:** Traditional crypto allocation
5. **Momentum-Only Portfolio:** Equal weight of Breakout + Days-from-High + Size
6. **Mean Reversion Portfolio:** Equal weight of Carry + Mean Reversion + OI Divergence

**Comparison Dimensions:**
- Sharpe Ratio improvement
- Drawdown reduction
- Correlation to BTC
- Turnover/rebalancing frequency

---

## 6. Implementation Specification

### 6.1 Code Structure

```
backtests/scripts/
  ├── backtest_portfolio_of_strategies.py         # Main script
  ├── enhanced_risk_parity.py                     # ERP weighting module
  └── portfolio_utils.py                          # Shared utilities

signals/
  └── calc_weights.py                             # Extended with ERP function

backtests/results/
  └── portfolio_of_strategies/
      ├── portfolio_values.csv                    # Daily performance
      ├── strategy_weights.csv                    # Weight time series
      ├── rebalancing_trades.csv                  # Rebalancing log
      ├── performance_metrics.csv                 # Summary statistics
      ├── strategy_attribution.csv                # Attribution analysis
      ├── correlation_matrix.csv                  # Realized correlations
      ├── portfolio_equity_curve.png              # Visualization
      └── weights_over_time.png                   # Weight evolution
```

### 6.2 Module: `enhanced_risk_parity.py`

```python
"""
Enhanced Risk Parity Weight Calculation Module

Implements correlation-aware risk parity optimization for portfolio allocation.
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import Dict, Tuple, Optional


def calculate_covariance_matrix(
    returns_df: pd.DataFrame,
    shrinkage_intensity: float = 0.3,
    min_periods: int = 30
) -> Tuple[np.ndarray, list]:
    """
    Calculate shrunk covariance matrix from strategy returns.
    
    Args:
        returns_df: DataFrame with strategy returns (columns = strategies)
        shrinkage_intensity: Ledoit-Wolf shrinkage factor (0=sample, 1=diagonal)
        min_periods: Minimum overlapping observations required
        
    Returns:
        Tuple of (covariance_matrix, strategy_names)
    """
    # Remove strategies with insufficient data
    valid_strategies = returns_df.columns[returns_df.count() >= min_periods]
    returns_clean = returns_df[valid_strategies].dropna()
    
    if len(returns_clean) < min_periods:
        raise ValueError(f"Insufficient data: need {min_periods}, have {len(returns_clean)}")
    
    # Sample covariance
    sample_cov = returns_clean.cov().values
    
    # Target: diagonal matrix (assumes independence)
    target_cov = np.diag(np.diag(sample_cov))
    
    # Shrinkage
    shrunk_cov = (1 - shrinkage_intensity) * sample_cov + shrinkage_intensity * target_cov
    
    return shrunk_cov, list(valid_strategies)


def calculate_risk_contributions(
    weights: np.ndarray,
    cov_matrix: np.ndarray
) -> np.ndarray:
    """
    Calculate risk contribution of each asset.
    
    Risk Contribution_i = w_i × (Σw)_i / σ_portfolio
    
    Args:
        weights: Array of portfolio weights
        cov_matrix: Covariance matrix
        
    Returns:
        Array of risk contributions (sum to 1.0)
    """
    portfolio_variance = weights @ cov_matrix @ weights
    portfolio_vol = np.sqrt(portfolio_variance)
    
    # Marginal contribution to risk
    marginal_contrib = cov_matrix @ weights
    
    # Risk contribution
    risk_contrib = weights * marginal_contrib / portfolio_vol
    
    # Normalize to sum to 1
    risk_contrib_pct = risk_contrib / risk_contrib.sum()
    
    return risk_contrib_pct


def risk_parity_objective(
    weights: np.ndarray,
    cov_matrix: np.ndarray
) -> float:
    """
    Objective function: minimize variance of risk contributions.
    
    Target: all risk contributions equal (1/n for n assets)
    """
    n = len(weights)
    target_rc = 1.0 / n
    
    risk_contribs = calculate_risk_contributions(weights, cov_matrix)
    
    # Sum of squared deviations from target
    objective = np.sum((risk_contribs - target_rc) ** 2)
    
    return objective


def solve_enhanced_risk_parity(
    cov_matrix: np.ndarray,
    min_weight: float = 0.05,
    max_weight: float = 0.50,
    initial_weights: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Solve for Enhanced Risk Parity weights using numerical optimization.
    
    Args:
        cov_matrix: n×n covariance matrix of strategy returns
        min_weight: Minimum allocation per strategy (e.g., 0.05 = 5%)
        max_weight: Maximum allocation per strategy (e.g., 0.50 = 50%)
        initial_weights: Starting point for optimization (default: equal weight)
        
    Returns:
        Array of optimal weights (sum to 1.0)
    """
    n = len(cov_matrix)
    
    # Initial guess: equal weight
    if initial_weights is None:
        x0 = np.ones(n) / n
    else:
        x0 = initial_weights
    
    # Constraints
    constraints = [
        {'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0}  # Weights sum to 1
    ]
    
    # Bounds
    bounds = tuple((min_weight, max_weight) for _ in range(n))
    
    # Optimize
    result = minimize(
        fun=risk_parity_objective,
        x0=x0,
        args=(cov_matrix,),
        method='SLSQP',
        bounds=bounds,
        constraints=constraints,
        options={'maxiter': 1000, 'ftol': 1e-9}
    )
    
    if not result.success:
        print(f"Warning: Optimization did not converge: {result.message}")
        # Fall back to simple risk parity
        return solve_simple_risk_parity_from_cov(cov_matrix, min_weight, max_weight)
    
    return result.x


def solve_simple_risk_parity_from_cov(
    cov_matrix: np.ndarray,
    min_weight: float = 0.05,
    max_weight: float = 0.50
) -> np.ndarray:
    """
    Fallback: simple risk parity ignoring correlations.
    
    Weight inversely proportional to volatility.
    """
    vols = np.sqrt(np.diag(cov_matrix))
    inv_vols = 1.0 / vols
    weights = inv_vols / inv_vols.sum()
    
    # Apply bounds (clip and renormalize)
    weights = np.clip(weights, min_weight, max_weight)
    weights = weights / weights.sum()
    
    return weights


def calculate_enhanced_rp_weights(
    strategy_returns_df: pd.DataFrame,
    lookback_days: int = 60,
    min_weight: float = 0.05,
    max_weight: float = 0.50,
    shrinkage_intensity: float = 0.30
) -> Dict[str, float]:
    """
    Main entry point: Calculate Enhanced Risk Parity weights for strategies.
    
    Args:
        strategy_returns_df: DataFrame with columns = strategy names, values = daily returns
        lookback_days: Number of days for covariance estimation
        min_weight: Minimum allocation per strategy
        max_weight: Maximum allocation per strategy
        shrinkage_intensity: Covariance shrinkage factor
        
    Returns:
        Dictionary mapping strategy names to weights (sum to 1.0)
    """
    # Use last N days
    recent_returns = strategy_returns_df.tail(lookback_days)
    
    # Compute covariance matrix
    cov_matrix, strategy_names = calculate_covariance_matrix(
        recent_returns,
        shrinkage_intensity=shrinkage_intensity,
        min_periods=min(30, lookback_days // 2)
    )
    
    # Solve for optimal weights
    weights_array = solve_enhanced_risk_parity(
        cov_matrix,
        min_weight=min_weight,
        max_weight=max_weight
    )
    
    # Convert to dictionary
    weights_dict = {
        strategy_names[i]: weights_array[i]
        for i in range(len(strategy_names))
    }
    
    return weights_dict


# Additional utility functions

def calculate_diversification_ratio(
    weights: Dict[str, float],
    strategy_vols: Dict[str, float],
    portfolio_vol: float
) -> float:
    """
    Diversification Ratio = (Weighted Avg Vol) / (Portfolio Vol)
    
    DR > 1 indicates diversification benefit.
    DR = 1 means no diversification (perfect correlation).
    """
    weighted_avg_vol = sum(weights[s] * strategy_vols[s] for s in weights)
    return weighted_avg_vol / portfolio_vol


def calculate_correlation_matrix(
    strategy_returns_df: pd.DataFrame,
    lookback_days: int = 60
) -> pd.DataFrame:
    """
    Calculate rolling correlation matrix of strategy returns.
    """
    recent_returns = strategy_returns_df.tail(lookback_days)
    return recent_returns.corr()
```

### 6.3 Main Backtest Script: `backtest_portfolio_of_strategies.py`

```python
#!/usr/bin/env python3
"""
Portfolio of Strategies Backtest using Enhanced Risk Parity

This script combines multiple individual strategies with correlation-aware weighting.

Strategies combined:
  1. Carry Factor (funding rate arbitrage)
  2. Breakout (trend following)
  3. Mean Reversion (contrarian price)
  4. Days-from-High (momentum)
  5. Size Factor (small cap premium)
  6. OI Divergence (contrarian OI/price)

Weighting: Enhanced Risk Parity with correlation adjustment
"""

import pandas as pd
import numpy as np
import argparse
from pathlib import Path
from enhanced_risk_parity import (
    calculate_enhanced_rp_weights,
    calculate_risk_contributions,
    calculate_diversification_ratio,
    calculate_correlation_matrix
)


def load_strategy_returns(strategy_name: str, results_dir: str) -> pd.Series:
    """Load daily returns for a single strategy from backtest results."""
    filepath = Path(results_dir) / f"{strategy_name}_portfolio_values.csv"
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    
    # Calculate daily log returns
    df['daily_return'] = np.log(df['portfolio_value'] / df['portfolio_value'].shift(1))
    
    return df['daily_return'].dropna()


def load_all_strategies(
    strategy_names: list,
    results_dir: str
) -> pd.DataFrame:
    """Load and combine returns for all strategies into single DataFrame."""
    all_returns = {}
    
    for strategy in strategy_names:
        try:
            returns = load_strategy_returns(strategy, results_dir)
            all_returns[strategy] = returns
            print(f"Loaded {strategy}: {len(returns)} days")
        except FileNotFoundError:
            print(f"Warning: Could not find results for {strategy}, skipping")
    
    # Combine into DataFrame (aligned by date)
    returns_df = pd.DataFrame(all_returns)
    returns_df = returns_df.dropna()  # Only dates where all strategies have returns
    
    print(f"\nCombined returns: {len(returns_df)} days with all strategies")
    return returns_df


def calculate_portfolio_return(
    strategy_returns: pd.Series,
    weights: dict
) -> float:
    """Calculate portfolio return given strategy returns and weights."""
    portfolio_return = sum(
        weights.get(strategy, 0) * strategy_returns.get(strategy, 0)
        for strategy in weights
    )
    return portfolio_return


def backtest_portfolio(
    strategy_returns_df: pd.DataFrame,
    initial_capital: float = 100000,
    rebalance_frequency: str = 'weekly',
    cov_lookback_days: int = 60,
    min_weight: float = 0.05,
    max_weight: float = 0.50,
    shrinkage_intensity: float = 0.30,
    transaction_cost_bps: float = 0.0
):
    """
    Run portfolio backtest with Enhanced Risk Parity weighting.
    """
    dates = strategy_returns_df.index
    strategies = list(strategy_returns_df.columns)
    
    # Initialize
    current_capital = initial_capital
    current_weights = {s: 1.0/len(strategies) for s in strategies}  # Start equal weight
    
    # Storage
    portfolio_values = []
    weight_history = []
    rebalance_log = []
    
    # Determine rebalance dates
    if rebalance_frequency == 'daily':
        rebalance_dates = dates
    elif rebalance_frequency == 'weekly':
        rebalance_dates = dates[dates.dayofweek == 0]  # Mondays
    elif rebalance_frequency == 'monthly':
        rebalance_dates = dates[dates.is_month_start]
    else:
        raise ValueError(f"Unknown rebalance frequency: {rebalance_frequency}")
    
    # Main backtest loop
    for i, date in enumerate(dates):
        # Rebalance if it's a rebalance date and we have sufficient history
        if date in rebalance_dates and i >= cov_lookback_days:
            try:
                # Calculate new weights
                lookback_data = strategy_returns_df.iloc[i-cov_lookback_days:i]
                new_weights = calculate_enhanced_rp_weights(
                    lookback_data,
                    lookback_days=cov_lookback_days,
                    min_weight=min_weight,
                    max_weight=max_weight,
                    shrinkage_intensity=shrinkage_intensity
                )
                
                # Calculate transaction costs
                turnover = sum(abs(new_weights.get(s, 0) - current_weights.get(s, 0)) 
                             for s in strategies)
                transaction_costs = turnover * current_capital * (transaction_cost_bps / 10000)
                current_capital -= transaction_costs
                
                # Record rebalance
                rebalance_log.append({
                    'date': date,
                    'turnover': turnover,
                    'transaction_cost': transaction_costs,
                    'old_weights': current_weights.copy(),
                    'new_weights': new_weights.copy()
                })
                
                current_weights = new_weights
                
            except Exception as e:
                print(f"Warning: Could not rebalance on {date}: {e}")
        
        # Calculate portfolio return
        strategy_returns_today = strategy_returns_df.loc[date]
        portfolio_return = calculate_portfolio_return(strategy_returns_today, current_weights)
        
        # Update capital (compound log returns)
        current_capital *= np.exp(portfolio_return)
        
        # Record
        portfolio_values.append({
            'date': date,
            'portfolio_value': current_capital,
            'daily_return': portfolio_return,
            **{f'weight_{s}': current_weights.get(s, 0) for s in strategies}
        })
        
        # Record weights periodically
        if date in rebalance_dates:
            weight_history.append({
                'date': date,
                **current_weights
            })
    
    # Convert to DataFrames
    portfolio_df = pd.DataFrame(portfolio_values)
    weights_df = pd.DataFrame(weight_history)
    
    return {
        'portfolio_values': portfolio_df,
        'weight_history': weights_df,
        'rebalance_log': rebalance_log,
        'final_capital': current_capital,
        'initial_capital': initial_capital
    }


def calculate_performance_metrics(portfolio_df: pd.DataFrame, initial_capital: float):
    """Calculate comprehensive performance metrics."""
    # ... (similar to existing backtest scripts)
    pass


def run_comparative_analysis(
    strategy_returns_df: pd.DataFrame,
    portfolio_results: dict
):
    """Compare Enhanced RP against benchmarks."""
    # Run equal weight benchmark
    # Run simple RP benchmark
    # Run best single strategy benchmark
    # Compare metrics
    pass


def main():
    parser = argparse.ArgumentParser(
        description='Portfolio of Strategies Backtest with Enhanced Risk Parity'
    )
    parser.add_argument('--results-dir', default='../results',
                       help='Directory with individual strategy results')
    parser.add_argument('--strategies', nargs='+',
                       default=['carry', 'breakout', 'mean_reversion', 'days_from_high', 
                                'size', 'oi_divergence'],
                       help='Strategies to combine')
    parser.add_argument('--initial-capital', type=float, default=100000)
    parser.add_argument('--rebalance-frequency', choices=['daily', 'weekly', 'monthly'],
                       default='weekly')
    parser.add_argument('--cov-lookback', type=int, default=60)
    parser.add_argument('--min-weight', type=float, default=0.05)
    parser.add_argument('--max-weight', type=float, default=0.50)
    parser.add_argument('--shrinkage', type=float, default=0.30)
    parser.add_argument('--transaction-cost-bps', type=float, default=10.0)
    parser.add_argument('--output-dir', default='../results/portfolio_of_strategies')
    
    args = parser.parse_args()
    
    # Load strategy returns
    print("Loading strategy returns...")
    strategy_returns_df = load_all_strategies(args.strategies, args.results_dir)
    
    # Run backtest
    print("\nRunning Enhanced Risk Parity backtest...")
    results = backtest_portfolio(
        strategy_returns_df,
        initial_capital=args.initial_capital,
        rebalance_frequency=args.rebalance_frequency,
        cov_lookback_days=args.cov_lookback,
        min_weight=args.min_weight,
        max_weight=args.max_weight,
        shrinkage_intensity=args.shrinkage,
        transaction_cost_bps=args.transaction_cost_bps
    )
    
    # Calculate metrics
    print("\nCalculating performance metrics...")
    metrics = calculate_performance_metrics(results['portfolio_values'], args.initial_capital)
    
    # Save results
    # ...
    
    print("\nBacktest complete!")


if __name__ == '__main__':
    main()
```

---

## 7. Testing & Validation

### 7.1 Unit Tests

```python
# tests/test_enhanced_risk_parity.py

def test_risk_contributions_sum_to_one():
    """Risk contributions should sum to 1.0"""
    pass

def test_weights_respect_bounds():
    """Weights should be within [min_weight, max_weight]"""
    pass

def test_covariance_shrinkage():
    """Shrunk covariance should be between sample and diagonal"""
    pass

def test_optimization_convergence():
    """Optimization should converge for well-conditioned problems"""
    pass

def test_fallback_to_simple_rp():
    """Should gracefully fall back if optimization fails"""
    pass
```

### 7.2 Integration Tests

- Load actual strategy returns from previous backtests
- Run portfolio backtest with Enhanced RP
- Verify metrics are reasonable (Sharpe > 0, weights sum to 1, etc.)
- Compare against equal-weight benchmark

### 7.3 Validation Checks

**Data Quality:**
- [ ] All strategy returns aligned by date
- [ ] No missing values in critical periods
- [ ] Returns are in log space (additive)

**Mathematical Correctness:**
- [ ] Risk contributions sum to 1.0
- [ ] Portfolio variance = w^T Σ w
- [ ] Weights sum to 1.0 ± 1e-6

**Economic Reasonableness:**
- [ ] Sharpe ratio improvement vs equal weight
- [ ] Lower drawdown than worst strategy
- [ ] Diversification ratio > 1.0
- [ ] Weights change smoothly over time (not erratic)

---

## 8. Deliverables

### 8.1 Code Deliverables

- [ ] `enhanced_risk_parity.py` - Core weighting module
- [ ] `backtest_portfolio_of_strategies.py` - Main backtest script
- [ ] Unit tests for ERP module
- [ ] Integration tests for full backtest

### 8.2 Output Files

**Standard Outputs:**
- `portfolio_values.csv` - Daily performance
- `strategy_weights.csv` - Weight evolution
- `rebalancing_trades.csv` - Rebalancing log
- `performance_metrics.csv` - Summary statistics

**Enhanced Outputs:**
- `strategy_attribution.csv` - Return/risk attribution
- `correlation_matrix.csv` - Realized correlations
- `risk_contributions.csv` - Risk contribution over time
- `comparative_analysis.csv` - ERP vs benchmarks

**Visualizations:**
- `equity_curve.png` - Portfolio value over time
- `weights_over_time.png` - Stacked area chart of weights
- `correlation_heatmap.png` - Strategy correlation matrix
- `risk_attribution.png` - Risk contribution pie chart
- `drawdown_chart.png` - Underwater equity curve

### 8.3 Documentation

- [ ] This specification document
- [ ] Implementation notes (decisions, challenges)
- [ ] User guide for running the backtest
- [ ] Performance summary report

---

## 9. Success Criteria

### 9.1 Technical Success

- [ ] Code runs without errors on historical data
- [ ] All unit and integration tests pass
- [ ] Optimization converges in >95% of rebalances
- [ ] Results are reproducible

### 9.2 Performance Success

**Minimum Bar:**
- Sharpe ratio > equal-weight benchmark
- Max drawdown < worst individual strategy
- Positive total return over test period

**Stretch Goals:**
- Sharpe ratio improvement of 30%+ vs simple RP
- Drawdown reduction of 20%+ vs equal weight
- Diversification ratio > 1.5 (6 strategies with mixed correlations)
- Correlation to BTC < 0.5
- At least 3 strategies with positive weights at all times

### 9.3 Insights Gained

- Understand which strategies are correlated/uncorrelated
- Identify optimal weight ranges for each strategy
- Determine sensitivity to rebalancing frequency
- Assess impact of transaction costs
- Validate correlation estimates vs realized

---

## 10. Future Extensions

### Phase 2 Enhancements

1. **Dynamic Risk Targeting**
   - Adjust overall leverage to maintain constant portfolio volatility
   - Scale weights when portfolio vol exceeds target

2. **Regime Detection**
   - Use volatility regime, trend regime to adjust weights
   - Different weight bounds in different regimes

3. **Mean-Variance Optimization**
   - Incorporate expected returns (not just risk)
   - Compare ERP vs MVO vs Black-Litterman

4. **Hierarchical Risk Parity**
   - Cluster strategies by correlation
   - Allocate hierarchically within clusters

5. **Online Learning**
   - Adapt shrinkage intensity based on out-of-sample performance
   - Use exponentially weighted covariance

6. **Multi-Asset Extension**
   - Add non-crypto strategies (equity factors, fixed income)
   - International diversification

---

## 11. References & Resources

### Academic Papers
- *"Risk Parity Portfolios"* - Maillard, Roncalli, Teïletche (2008)
- *"Hierarchical Risk Parity"* - López de Prado (2016)
- *"Honey, I Shrunk the Sample Covariance Matrix"* - Ledoit & Wolf (2004)

### Practical Guides
- *"Asset Management"* - Roncalli (2014) - Chapter on Risk Parity
- *"Advances in Portfolio Construction"* - Risk Books (2009)

### Code References
- RiskFolio-Lib (Python portfolio optimization)
- PyPortfolioOpt (Modern portfolio optimization)
- MLFinLab (Advanced financial ML, includes HRP)

---

## Appendix A: Alternative Weighting Schemes

For comparison purposes, implement these alternatives:

### A.1 Equal Weight
```python
weights = {strategy: 1.0/n for strategy in strategies}
```

### A.2 Simple Risk Parity (Current)
```python
vols = {strategy: strategy_vol for strategy in strategies}
inv_vols = {strategy: 1.0/vols[strategy] for strategy in strategies}
sum_inv_vols = sum(inv_vols.values())
weights = {strategy: inv_vols[strategy]/sum_inv_vols for strategy in strategies}
```

### A.3 Minimum Variance
```python
# Minimize: w^T Σ w
# Subject to: Σw = 1
from scipy.optimize import minimize

result = minimize(
    fun=lambda w: w @ cov_matrix @ w,
    x0=np.ones(n)/n,
    constraints=[{'type': 'eq', 'fun': lambda w: w.sum() - 1}],
    bounds=[(0, 1) for _ in range(n)]
)
weights = result.x
```

### A.4 Maximum Sharpe (Mean-Variance)
```python
# Maximize: (w^T μ) / sqrt(w^T Σ w)
# Requires expected returns estimation
```

### A.5 Maximum Diversification
```python
# Maximize: (Σ w_i σ_i) / sqrt(w^T Σ w)
# Explicitly maximizes diversification benefit
```

---

## Appendix B: Example Configuration File

```yaml
# config_portfolio_of_strategies.yaml

portfolio:
  initial_capital: 100000
  strategies:
    - carry
    - breakout  
    - mean_reversion
    - days_from_high
    - size
    - oi_divergence

weighting:
  method: enhanced_risk_parity
  cov_lookback_days: 60
  shrinkage_intensity: 0.30
  min_weight: 0.05
  max_weight: 0.50
  
rebalancing:
  frequency: weekly  # daily, weekly, monthly
  day_of_week: monday  # for weekly
  
risk_management:
  max_portfolio_vol: 0.40  # Optional vol target
  exclude_negative_sharpe: false
  lookback_for_exclusion: 90
  
transaction_costs:
  enabled: true
  bps_per_side: 10  # 0.1%
  
output:
  directory: ../results/portfolio_of_strategies
  save_weights: true
  save_attribution: true
  generate_plots: true
```

---

**End of Specification**

**Approval:**
- [ ] Strategy logic reviewed
- [ ] Mathematical formulation validated  
- [ ] Implementation plan approved
- [ ] Resource allocation confirmed
- [ ] Ready for implementation

**Contact:** For questions or clarifications, refer to TODO #4 in `RESEARCH_TODO.md`
