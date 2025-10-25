# Run All Backtests Script

## Overview

This script runs comprehensive backtests on all available trading strategies and calculates detailed performance metrics for comparison.

## Metrics Calculated

The script calculates the following performance metrics for each strategy:

1. **Avg Return** - Average annualized return
2. **Avg Drawdown** - Average drawdown during losing periods
3. **Stdev Return** - Standard deviation of returns (annualized volatility)
4. **Stdev Downside Return** - Standard deviation of negative returns only (downside volatility)
5. **Sharpe Ratio** - Risk-adjusted return metric (return / volatility)
6. **Sortino Ratio** - Risk-adjusted return using downside volatility only
7. **Information Coefficient** - Measure of signal quality / return predictability

Additional metrics include:
- Max Drawdown
- Win Rate
- Calmar Ratio (return / max drawdown)
- Total Return
- Final Portfolio Value
- Number of Trading Days

## Strategies Tested

The script runs the following backtests:

1. **Breakout Signal** - Trend-following strategy based on price breakouts
2. **Mean Reversion** - Contrarian strategy betting on price reversals
3. **Size Factor** - Long small-cap / short large-cap strategy
4. **Carry Factor** - Long low funding rate / short high funding rate strategy
5. **20d from 200d High** - Momentum strategy selecting instruments within 20 days of their 200-day high

## Usage

### Basic Usage

Run with default parameters:

```bash
cd /workspace
python3 backtests/scripts/run_all_backtests.py
```

### Custom Parameters

```bash
python3 backtests/scripts/run_all_backtests.py \
    --data-file data/raw/top10_markets_500d_daily_data.csv \
    --marketcap-file data/raw/coinmarketcap_historical_20250105.csv \
    --funding-rates-file data/raw/historical_funding_rates_top100_20251025_124832.csv \
    --initial-capital 10000 \
    --start-date 2024-01-01 \
    --end-date 2025-10-23 \
    --output-file backtests/results/all_backtests_summary.csv
```

### Command Line Arguments

- `--data-file`: Path to historical OHLCV price data CSV file
- `--marketcap-file`: Path to market cap data CSV file
- `--funding-rates-file`: Path to funding rates data CSV file  
- `--initial-capital`: Initial portfolio capital in USD (default: 10000)
- `--start-date`: Start date for backtest (YYYY-MM-DD format, optional)
- `--end-date`: End date for backtest (YYYY-MM-DD format, optional)
- `--output-file`: Output file for summary table (default: backtests/results/all_backtests_summary.csv)
- `--run-breakout`: Run breakout signal backtest (default: True)
- `--run-mean-reversion`: Run mean reversion backtest (default: True)
- `--run-size`: Run size factor backtest (default: True)
- `--run-carry`: Run carry factor backtest (default: True)
- `--run-20d-from-200d-high`: Run 20d from 200d high backtest (default: True)

## Output

The script generates:

1. **Console Output** - Detailed progress and results printed to terminal
2. **CSV Summary File** - Comprehensive metrics table saved to specified output file

Example output structure:

```
Strategy,Description,Avg Return,Avg Drawdown,Stdev Return,Stdev Downside Return,Sharpe Ratio,Sortino Ratio,Information Coefficient,Max Drawdown,Win Rate,Calmar Ratio,Total Return,Final Value,Num Days
Breakout Signal,"Entry: 50d, Exit: 70d",-25.47%,-23.63%,26.77%,19.39%,-1.047,-1.446,0.108,-45.74%,46.62%,-0.613,-30.26%,$6973.87,400
Mean Reversion,Best category: up_move_low_volume,1140.86%,-27.78%,105.40%,52.28%,6.383,12.868,0.140,-64.75%,51.34%,10.390,556.00%,$65600.35,336
Size Factor,Strategy: long_small_short_large,41.17%,-9.63%,32.67%,23.26%,1.034,1.453,0.007,-30.19%,52.88%,1.120,45.45%,$14545.04,470
Carry Factor,"Top 10 short, Bottom 10 long",32.65%,-2.86%,28.99%,18.44%,0.921,1.448,0.178,-6.32%,31.58%,4.226,3.83%,$10383.10,58
20d from 200d High,"Momentum: within 20d of 200d high",15.32%,-8.21%,24.53%,16.78%,0.624,0.912,0.092,-18.45%,48.73%,0.831,18.92%,$11892.47,420
```

## Performance Metrics Explanation

### Core Metrics

- **Avg Return**: Annualized geometric mean return. Higher is better.
- **Avg Drawdown**: Average percentage loss during drawdown periods. Closer to 0 is better.
- **Stdev Return**: Total volatility of returns. Lower indicates more stable returns.
- **Stdev Downside Return**: Volatility during losing periods only. Lower is better.
- **Sharpe Ratio**: Return per unit of total risk. Higher is better (>1 is good, >2 is excellent).
- **Sortino Ratio**: Return per unit of downside risk. Higher is better.
- **Information Coefficient**: Measures signal quality and predictability. Positive values indicate skill.

### Additional Metrics

- **Max Drawdown**: Largest peak-to-trough decline. Smaller (less negative) is better.
- **Win Rate**: Percentage of profitable trading days. Higher is better.
- **Calmar Ratio**: Return divided by max drawdown. Higher is better.

## Requirements

Make sure all dependencies are installed:

```bash
pip install -r requirements.txt
```

Required Python packages:
- pandas>=2.0.0
- numpy>=1.24.0
- ccxt>=4.0.0
- requests>=2.28.0

## Notes

- The script automatically handles missing data and adjusts for look-ahead bias
- All strategies use equal initial capital for fair comparison
- Results may vary based on the data period selected
- Longer backtest periods generally provide more reliable metrics
- Mean reversion results can be highly variable depending on market conditions

## Troubleshooting

If you encounter import errors, make sure you're running from the workspace root directory:

```bash
cd /workspace
python3 backtests/scripts/run_all_backtests.py
```

If specific backtests fail, you can disable them using the command line flags:

```bash
python3 backtests/scripts/run_all_backtests.py --no-run-size --no-run-carry
```
