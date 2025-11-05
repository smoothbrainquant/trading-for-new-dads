# Risk Parity Usage Audit Report

**Date**: 2025-11-04  
**Audit Scope**: All backtest scripts and main.py (execution pipeline)  
**Purpose**: Verify consistent use of risk parity weighting across factor/long-short strategies

---

## Executive Summary

✅ **MOST strategies are using risk parity** for long/short factor strategies  
⚠️ **SOME strategies default to equal_weight** but support risk_parity as an option  
📊 **Mixed approach** based on strategy type and historical decisions

---

## 1. Main Execution Pipeline (execution/main.py)

### Overall Finding: ✅ **MOSTLY RISK PARITY**

The main execution pipeline (`execution/main.py`) uses **different defaults** for different strategies based on their configuration:

### Strategies Using Risk Parity (Default):

1. **Kurtosis Factor** (Line 259)
   - Default: `weighting_method = "risk_parity"`
   - Config: Uses risk parity by default

2. **ADF Factor** (Line 306)
   - Default: `weighting_method = "risk_parity"`
   - Config: Uses risk parity by default

### Strategies Using Equal Weight (Default):

1. **Beta Factor (BAB)** (Line 214)
   - Default: `weighting_method = "equal_weight"`
   - Config supports: Can be overridden to risk_parity

2. **Trendline Breakout** (Line 236)
   - Default: `weighting_method = "equal_weight"`
   - Config supports: Can be overridden to risk_parity

3. **Volatility Factor** (Line 285)
   - Default: `weighting_method = "equal_weight"`
   - Config supports: Can be overridden to risk_parity

### Strategy Config (all_strategies_config.json):

**Beta** (Line 184): `"weighting_method": "equal_weight"`
**Trendline Breakout** (Line 197): `"weighting_method": "equal_weight"`
**Volatility** (Line 206): `"weighting_method": "equal_weight"`
**Kurtosis** (Line 216): `"weighting_method": "risk_parity"` ✅
**ADF** (Line 233): `"weighting_method": "risk_parity"` ✅
**Turnover** (Line 278): `"weighting_method": "equal_weight"`

---

## 2. Backtest Scripts (backtests/scripts/)

### run_all_backtests.py

This is the **master backtest orchestrator**. Here's what each strategy uses:

#### ✅ Using Risk Parity (Hardcoded):

1. **Breakout Signals** (Line 327)
   ```python
   weighting_method='risk_parity',  # Inverse volatility weighting
   ```

2. **Mean Reversion** (Line 379)
   ```python
   weighting_method='risk_parity',  # Risk parity weighting
   ```

3. **Size Factor** (Line 452)
   ```python
   weighting_method='risk_parity',  # Inverse volatility weighting (matches live trading)
   ```

4. **Days from High** (Line 523)
   ```python
   weighting_method='risk_parity',
   ```

5. **Carry Factor** (Line 655)
   ```python
   weighting_method='risk_parity',  # Inverse volatility weighting
   ```

6. **Kurtosis Factor** (Line 832)
   ```python
   weighting_method=kwargs.get("weighting", "risk_parity"),
   ```

7. **ADF Factor** (Line 1224)
   ```python
   weighting_method='risk_parity',
   ```

8. **Dilution Factor** (Line 1244)
   ```python
   weighting_method='risk_parity',
   ```

#### ⚠️ Using Equal Weight or Configurable:

1. **Volatility Factor** (Line 751)
   ```python
   weighting_method=kwargs.get("weighting_method", "equal_weight"),
   ```

2. **Beta Factor** (Line 886)
   ```python
   weighting_method=kwargs.get("weighting_method", "risk_parity"),
   ```
   - **Note**: Defaults to risk_parity in backtest, but config sets it to equal_weight

3. **Trendline Factor** (Line 582)
   ```python
   method=kwargs.get('weighting_method', 'equal_weight'),
   ```

4. **Beta Rebalance Periods** (Line 2043)
   ```python
   weighting_method="equal_weight",
   ```

5. **Beta 5-day Rebalance** (Line 2145)
   ```python
   weighting_method="equal_weight",
   ```

### Individual Backtest Scripts:

#### ✅ Risk Parity (Primary):

- `backtest_dilution_factor.py` - Uses custom risk_parity implementation
- `backtest_dilution_factor_outlier_filtered.py` - Uses custom risk_parity implementation
- `backtest_leverage_inverted.py` - Uses custom risk_parity implementation
- `backtest_leverage_inverted_comprehensive.py` - Uses custom risk_parity implementation
- `backtest_20d_from_200d_high.py` - Uses risk parity (line 248)
- `backtest_carry_factor.py` - Uses risk parity via calc_weights
- `backtest_size_factor.py` - Uses risk parity via calc_weights

#### ⚠️ Equal Weight (Primary):

- `backtest_skew_factor.py` - Equal weight within quintiles
- `backtest_leverage_long_short.py` - Equal weight within legs
- `backtest_turnover_factor.py` - Equal weight (basket strategy)

#### 🔀 Configurable (Supports Both):

- `backtest_vectorized.py` - Default: `equal_weight`, supports `risk_parity`
- `backtest_adf_factor.py` - Default: `equal_weight`, supports `risk_parity`
- `backtest_beta_factor.py` - Default: `equal_weight`, supports `risk_parity`
- `backtest_trendline_factor.py` - Default: `equal_weight`, supports `risk_parity`
- `backtest_trendline_breakout.py` - Default: `equal_weight`, supports `risk_parity`
- `backtest_trendline_reversal.py` - Default: `equal_weight`, supports `risk_parity`
- `backtest_volatility_factor.py` - Supports both equal_weight and risk_parity
- `backtest_iqr_spread_factor.py` - Default: `equal_weight`, supports `risk_parity`
- `backtest_basket_pairs_trading.py` - Default: `equal_weight`, supports z_score_weight

---

## 3. Risk Parity Implementation

### Core Implementation: `signals/calc_weights.py`

The canonical risk parity implementation:

```python
def calculate_weights(volatilities):
    """
    Calculate portfolio weights based on risk parity using inverse volatility.
    
    Methodology:
    1. Calculate inverse volatility for each asset (1 / volatility)
    2. Sum all inverse volatilities
    3. Normalize by dividing each inverse volatility by the sum
    
    Mathematical formula:
        weight_i = (1 / vol_i) / sum(1 / vol_j for all j)
    """
```

**Key Properties**:
- Lower volatility assets receive higher weights
- Higher volatility assets receive lower weights
- All assets contribute equally to portfolio risk
- Weights sum to exactly 1.0 (100% of portfolio)

### Vectorized Implementation: `signals/generate_signals_vectorized.py`

Lines 564-597 implement risk parity for long/short portfolios:

```python
if weighting_method == 'risk_parity':
    # Calculate risk parity weights separately for longs and shorts
    def calc_risk_parity_weights(group):
        # Weight inversely proportional to volatility
        inv_vol = 1.0 / group['volatility']
        weights = inv_vol / inv_vol.sum()
        return weights
    
    # Apply separately for longs and shorts
    longs = df[df['signal'] == 1].groupby('date').apply(calc_risk_parity_weights)
    shorts = df[df['signal'] == -1].groupby('date').apply(calc_risk_parity_weights)
```

---

## 4. Summary by Strategy Type

| Strategy | Backtest Default | Main.py Default | Config Setting | Status |
|----------|-----------------|----------------|----------------|--------|
| **Kurtosis** | risk_parity | risk_parity | risk_parity | ✅ Consistent |
| **ADF** | risk_parity | risk_parity | risk_parity | ✅ Consistent |
| **Size** | risk_parity | N/A | N/A | ✅ Risk Parity |
| **Carry** | risk_parity | N/A | N/A | ✅ Risk Parity |
| **Breakout** | risk_parity | N/A | N/A | ✅ Risk Parity |
| **Mean Reversion** | risk_parity | N/A | N/A | ✅ Risk Parity |
| **Days from High** | risk_parity | N/A | N/A | ✅ Risk Parity |
| **Dilution** | risk_parity | N/A | N/A | ✅ Risk Parity |
| **Leverage Inverted** | risk_parity | N/A | N/A | ✅ Risk Parity |
| **Beta (BAB)** | risk_parity | equal_weight | equal_weight | ⚠️ **INCONSISTENT** |
| **Volatility** | equal_weight | equal_weight | equal_weight | ⚠️ Equal Weight |
| **Trendline Breakout** | equal_weight | equal_weight | equal_weight | ⚠️ Equal Weight |
| **Turnover** | N/A | N/A | equal_weight | ⚠️ Equal Weight |
| **Skew** | equal_weight | N/A | N/A | ⚠️ Equal Weight |

---

## 5. Issues Found

### ⚠️ Issue #1: Beta Factor Inconsistency

**Problem**: Beta factor backtest defaults to `risk_parity` but main.py config uses `equal_weight`

**Location**:
- `backtests/scripts/run_all_backtests.py` Line 886: `weighting_method=kwargs.get("weighting_method", "risk_parity")`
- `execution/all_strategies_config.json` Line 184: `"weighting_method": "equal_weight"`
- `execution/main.py` Line 214: `weighting_method = p.get("weighting_method", "equal_weight")`

**Impact**: Backtest results don't match live trading behavior

**Recommendation**: 
- Option A: Change config to `"weighting_method": "risk_parity"` (align with backtest)
- Option B: Change backtest default to `"equal_weight"` (align with config)
- **Need to rebacktest Beta with the chosen method to ensure consistency**

### ⚠️ Issue #2: Volatility Factor Inconsistency

**Problem**: Different defaults in different contexts

**Location**:
- `backtests/scripts/run_all_backtests.py` Line 751: defaults to `equal_weight`
- `execution/all_strategies_config.json` Line 206: `"weighting_method": "equal_weight"`
- Some individual backtest scripts support both

**Status**: Actually consistent (equal_weight everywhere), but worth noting

### ⚠️ Issue #3: Some Strategies Don't Use Risk Parity

**Strategies using equal_weight by design**:
1. **Skew Factor** - Equal weight within quintiles
2. **Turnover Factor** - Equal weight basket strategy
3. **Trendline Breakout** - Equal weight (configurable)

**Question**: Should these also use risk parity for consistency?

---

## 6. Recommendations

### Immediate Actions Required:

1. **Fix Beta Factor Inconsistency**
   - Decision needed: risk_parity or equal_weight?
   - Update config to match backtest (or vice versa)
   - Rerun backtests to validate performance

2. **Document Design Decisions**
   - Why do some strategies use equal_weight?
   - Is this intentional or historical artifact?
   - Create strategy-specific documentation

3. **Add Validation Tests**
   - Test that backtest weighting matches live config
   - Add unit tests for weight consistency
   - Prevent future divergence

### Long-term Improvements:

1. **Standardize Approach**
   - Consider making risk_parity the default for all long/short factors
   - Only use equal_weight when there's a specific reason

2. **Make Weighting Method More Visible**
   - Add weighting method to strategy descriptions
   - Log weighting method during execution
   - Include in backtest output files

3. **Benchmark Both Methods**
   - Run all strategies with both equal_weight and risk_parity
   - Compare performance metrics
   - Document which method works better for each strategy

---

## 7. Conclusion

**Overall Status**: ✅ **Mostly Using Risk Parity**

- **60-70% of strategies**: Using risk_parity consistently
- **30-40% of strategies**: Using equal_weight or mixed approach
- **1 critical issue**: Beta factor has backtest/config mismatch

**Next Steps**:
1. Fix Beta factor inconsistency
2. Decide on standardization approach
3. Add validation tests
4. Document design decisions

---

## Appendix: Complete File List

### Backtest Scripts Checked (28 files):
- backtest_20d_from_200d_high.py
- backtest_adf_factor.py
- backtest_adf_regime_switching.py
- backtest_basket_pairs_trading.py
- backtest_beta_factor.py
- backtest_beta_rebalance_periods.py
- backtest_breakout_signals.py
- backtest_carry_factor.py
- backtest_dilution_factor.py
- backtest_dilution_factor_comparison.py
- backtest_dilution_factor_outlier_filtered.py
- backtest_iqr_spread_factor.py
- backtest_kurtosis_factor.py
- backtest_leverage_inverted.py
- backtest_leverage_inverted_comprehensive.py
- backtest_leverage_long_short.py
- backtest_mean_reversion.py
- backtest_mean_reversion_periods.py
- backtest_open_interest_divergence.py
- backtest_size_factor.py
- backtest_skew_factor.py
- backtest_trendline_breakout.py
- backtest_trendline_factor.py
- backtest_trendline_reversal.py
- backtest_turnover_factor.py
- backtest_vectorized.py
- backtest_volatility_factor.py
- backtest_volatility_rebalance_periods.py

### Core Implementation Files:
- signals/calc_weights.py (canonical risk parity)
- signals/generate_signals_vectorized.py (vectorized implementation)
- execution/main.py (live trading pipeline)
- execution/all_strategies_config.json (strategy configuration)

---

**Report Generated**: 2025-11-04  
**Audit Completed By**: Cursor Agent (Background Task)
