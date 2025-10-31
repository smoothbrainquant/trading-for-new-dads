# Comprehensive Backtest Analysis Script

## Overview

I've created a comprehensive script that runs backtests on all available trading signals and outputs detailed performance metrics for comparison.

## Location

**Script:** `/workspace/backtests/scripts/run_all_backtests.py`
**Documentation:** `/workspace/backtests/scripts/README_RUN_ALL_BACKTESTS.md`

## Key Features

### Performance Metrics Calculated

The script calculates all requested metrics plus additional useful metrics:

1. ✅ **Avg Return** - Average annualized return
2. ✅ **Avg Drawdown** - Average drawdown during losing periods  
3. ✅ **Stdev Return** - Standard deviation of returns (volatility)
4. ✅ **Stdev of Downside Return** - Downside volatility only
5. ✅ **Sharpe Ratio** - Risk-adjusted return metric
6. ✅ **Sortino Ratio** - Risk-adjusted return using downside volatility
7. ✅ **Information Coefficient** - Signal quality / predictability measure

**Additional Metrics:**
- Max Drawdown
- Win Rate (% of profitable days)
- Calmar Ratio
- Total Return
- Final Portfolio Value
- Number of Trading Days

### Strategies Tested

The script runs backtests on:

1. **Breakout Signal** - Trend-following based on 50d/70d breakouts
2. **Mean Reversion** - Contrarian strategy on z-score extremes
3. **Size Factor** - Long small-cap / short large-cap
4. **Carry Factor** - Based on funding rate differentials

## Quick Start

### Basic Usage

```bash
cd /workspace
python3 backtests/scripts/run_all_backtests.py
```

### With Custom Parameters

```bash
python3 backtests/scripts/run_all_backtests.py \
    --data-file data/raw/top10_markets_500d_daily_data.csv \
    --initial-capital 10000 \
    --output-file backtests/results/my_backtest_summary.csv
```

## Example Output

```
BACKTEST PERFORMANCE SUMMARY
========================================================================================================================

Core Performance Metrics:
       Strategy                       Description Avg Return Avg Drawdown Stdev Return Stdev Downside Return Sharpe Ratio Sortino Ratio Information Coefficient
Breakout Signal             Entry: 50d, Exit: 70d    -25.47%      -23.63%       26.77%                19.39%       -1.047        -1.446                   0.108
 Mean Reversion Best category: up_move_low_volume   1140.86%      -27.78%      105.40%                52.28%        6.383        12.868                   0.140
    Size Factor  Strategy: long_small_short_large     41.17%       -9.63%       32.67%                23.26%        1.034         1.453                   0.007
   Carry Factor      Top 10 short, Bottom 10 long     32.65%       -2.86%       28.99%                18.44%        0.921         1.448                   0.178

========================================================================================================================
Additional Metrics:
       Strategy Max Drawdown Win Rate Calmar Ratio Total Return Final Value  Num Days
Breakout Signal      -45.74%   46.62%       -0.613      -30.26%   $6,973.87       400
 Mean Reversion      -64.75%   51.34%       10.390      556.00%  $65,600.35       336
    Size Factor      -30.19%   52.88%        1.120       45.45%  $14,545.04       470
   Carry Factor       -6.32%   31.58%        4.226        3.83%  $10,383.10        58
```

## Output Files

The script generates a CSV file with all metrics:

**Output Location:** `backtests/results/all_backtests_summary.csv` (or custom path)

**CSV Format:**
```csv
Strategy,Description,Avg Return,Avg Drawdown,Stdev Return,Stdev Downside Return,Sharpe Ratio,Sortino Ratio,Information Coefficient,Max Drawdown,Win Rate,Calmar Ratio,Total Return,Final Value,Num Days
Breakout Signal,"Entry: 50d, Exit: 70d",-0.255,-0.236,0.268,0.194,-1.047,-1.446,0.108,-0.457,0.466,-0.613,-0.303,6973.87,400
...
```

## Metric Interpretation Guide

### High is Better
- Avg Return
- Sharpe Ratio (>1 is good, >2 is excellent)
- Sortino Ratio
- Win Rate
- Calmar Ratio
- Information Coefficient (positive indicates skill)

### Low is Better (or closer to 0)
- Avg Drawdown (less negative)
- Stdev Return (lower volatility)
- Stdev Downside Return
- Max Drawdown (less negative)

## Key Implementation Details

### Avoiding Look-Ahead Bias
- All signals use data available only up to calculation date
- Returns are shifted forward (signals on day T use returns from day T+1)
- Rolling calculations use properly shifted windows

### Risk-Adjusted Returns
- **Sharpe Ratio** = Annualized Return / Total Volatility
- **Sortino Ratio** = Annualized Return / Downside Volatility
- **Calmar Ratio** = Annualized Return / Max Drawdown

### Information Coefficient
- Measures signal quality and return predictability
- Calculated as autocorrelation of returns
- Positive values indicate persistence/skill

## Example Use Cases

### Compare All Strategies

```bash
python3 backtests/scripts/run_all_backtests.py \
    --data-file data/raw/top10_markets_500d_daily_data.csv
```

### Test Specific Period

```bash
python3 backtests/scripts/run_all_backtests.py \
    --data-file data/raw/top10_markets_500d_daily_data.csv \
    --start-date 2024-01-01 \
    --end-date 2025-10-01
```

### Different Initial Capital

```bash
python3 backtests/scripts/run_all_backtests.py \
    --initial-capital 100000
```

## Files Created

1. **Main Script:** `backtests/scripts/run_all_backtests.py`
   - Comprehensive backtest runner
   - Calculates all requested metrics
   - Outputs formatted summary

2. **Documentation:** `backtests/scripts/README_RUN_ALL_BACKTESTS.md`
   - Detailed usage guide
   - Parameter descriptions
   - Metric explanations

3. **Output:** `backtests/results/all_backtests_summary.csv`
   - CSV file with all metrics
   - Easy to import into Excel/Python for further analysis

## Next Steps

You can now:

1. **Run the script** to get comprehensive performance metrics
2. **Compare strategies** side-by-side using the output table
3. **Analyze results** in Excel or Python using the CSV output
4. **Customize parameters** to test different scenarios
5. **Add new strategies** by extending the script

## Support

For detailed documentation, see:
- `/workspace/backtests/scripts/README_RUN_ALL_BACKTESTS.md`

For questions about specific metrics or strategies, refer to the individual backtest scripts in:
- `/workspace/backtests/scripts/`
