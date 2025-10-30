# Kurtosis Rebalance Periods Backtest Summary

## Overview

Backtested the kurtosis factor strategy with multiple rebalance periods to determine optimal rebalancing frequency. The kurtosis factor strategy trades based on the tail-fatness of return distributions, going long high-kurtosis (volatile) coins and short low-kurtosis (stable) coins in the momentum variant.

## Implementation

### New Scripts Created

1. **`backtests/scripts/backtest_kurtosis_rebalance_periods.py`**
   - Runs kurtosis factor backtest with multiple rebalance periods
   - Tests periods: [1, 2, 3, 5, 7, 10, 30] days
   - Generates comprehensive comparison summary
   - Saves individual results for each rebalance period

### Integration with Run All Backtests

Updated **`backtests/scripts/run_all_backtests.py`** to:
- Accept multiple kurtosis rebalance periods via `--kurtosis-rebalance-periods` argument
- Default periods: [1, 2, 3, 5, 7, 10, 30] days
- Run separate backtests for each period
- Include all results in comprehensive comparison table

## Backtest Results

### Configuration
- **Strategy**: Momentum (long high kurtosis, short low kurtosis)
- **Kurtosis Window**: 30 days
- **Volatility Window**: 30 days
- **Period**: 2020-02-19 to 2025-10-24 (2,075 days)
- **Initial Capital**: $10,000
- **Leverage**: 1.0x
- **Long/Short Allocation**: 50%/50%

### Performance by Rebalance Period

| Rebalance Days | Total Return | Annual Return | Sharpe Ratio | Max Drawdown | Win Rate | Total Trades |
|----------------|--------------|---------------|--------------|--------------|----------|--------------|
| **1 day**      | **603.33%**  | **40.97%**    | **0.85**     | -69.64%      | 52.84%   | 5,922        |
| **2 days**     | 215.22%      | 22.40%        | 0.47         | -78.55%      | 52.22%   | 3,321        |
| **3 days**     | 201.42%      | 21.44%        | 0.47         | **-63.47%**  | 51.59%   | 2,384        |
| **5 days**     | 27.11%       | 4.31%         | 0.09         | -83.32%      | 51.93%   | 1,588        |
| **7 days**     | 42.33%       | 6.41%         | 0.14         | -67.74%      | 51.11%   | 1,195        |
| **10 days**    | -22.66%      | -4.42%        | -0.10        | -77.29%      | 52.31%   | 889          |
| **30 days**    | -9.96%       | -1.83%        | -0.04        | -71.75%      | 50.72%   | 364          |

### Key Findings

1. **Optimal Rebalancing**: 1-day rebalancing significantly outperforms all other periods
   - Nearly 2x the returns of 2-day rebalancing
   - 0.85 Sharpe ratio (highest among all periods)
   - 603% total return over ~5.7 years

2. **Performance Degradation**: Returns drop sharply with less frequent rebalancing
   - 1-3 day periods show positive risk-adjusted returns
   - 5-7 day periods show marginal returns
   - 10+ day periods show negative returns

3. **Strategy Characteristics**:
   - The kurtosis momentum strategy benefits from frequent position adjustments
   - More rebalancing captures short-term volatility signals more effectively
   - Longer holding periods miss optimal entry/exit timing

4. **Risk Metrics**:
   - Best max drawdown: 3-day rebalancing (-63.47%)
   - Win rates remain relatively stable across all periods (50-53%)
   - Sharpe ratios decline significantly with less frequent rebalancing

## Usage

### Run Rebalance Period Comparison

```bash
cd /workspace
python3 backtests/scripts/backtest_kurtosis_rebalance_periods.py \
    --rebalance-periods 1 2 3 5 7 10 30 \
    --strategy momentum
```

### Include in Run All Backtests

```bash
cd /workspace
python3 backtests/scripts/run_all_backtests.py \
    --kurtosis-rebalance-periods 1 2 3 5 7 10 30 \
    --kurtosis-strategy momentum
```

### Customize Rebalance Periods

```bash
python3 backtests/scripts/run_all_backtests.py \
    --kurtosis-rebalance-periods 1 3 7 14 \
    --kurtosis-strategy momentum
```

## Files Generated

All results saved to `/workspace/backtests/results/`:

### Individual Results per Period
- `kurtosis_momentum_{N}d_rebal_portfolio_values.csv` - Portfolio value timeseries
- `kurtosis_momentum_{N}d_rebal_trades.csv` - All trades executed
- `kurtosis_momentum_{N}d_rebal_kurtosis_timeseries.csv` - Kurtosis values over time
- `kurtosis_momentum_{N}d_rebal_metrics.csv` - Performance metrics
- `kurtosis_momentum_{N}d_rebal_strategy_info.csv` - Strategy configuration

### Comparison Summary
- `kurtosis_momentum_rebalance_comparison_summary.csv` - Metrics comparison across all periods

## Conclusions

1. **Recommended Rebalancing**: 1-day rebalancing for optimal performance
   - Highest returns and best risk-adjusted performance
   - Captures short-term volatility dynamics effectively

2. **Backup Options**: 2-3 day rebalancing as alternatives
   - Still show strong positive returns
   - Reduce trading costs while maintaining decent performance

3. **Avoid**: 10+ day rebalancing periods
   - Negative returns indicate strategy doesn't work at longer horizons
   - Kurtosis signals decay quickly and need frequent updates

## Next Steps

Consider testing:
1. Mean reversion strategy with different rebalance periods
2. Transaction cost analysis to determine optimal rebalancing with fees
3. Different kurtosis calculation windows (currently 30 days)
4. Alternative volatility-based signals combined with kurtosis

---
**Generated**: 2025-10-30
**Data Period**: 2020-02-19 to 2025-10-24 (2,075 days)
