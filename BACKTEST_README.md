# Backtest for 20d from 200d High Trading System

## Overview

This backtest evaluates a momentum trading strategy that:
1. Selects instruments within **20 days** (configurable) of their **200-day high**
2. Calculates rolling volatility for selected instruments
3. Allocates portfolio weights using **risk parity** (inverse volatility weighting)
4. Rebalances daily based on the selection criteria
5. Tracks portfolio performance over time

## Files Created

- **`backtest_20d_from_200d_high.py`** - Main backtest script
- **`backtest_20d_200d_high_portfolio_values.csv`** - Daily portfolio values and positions
- **`backtest_20d_200d_high_trades.csv`** - Rebalancing trade history
- **`backtest_20d_200d_high_metrics.csv`** - Performance metrics summary

## Usage

### Basic Usage

```bash
python3 backtest_20d_from_200d_high.py
```

This runs the backtest with default parameters:
- Data file: `top10_markets_100d_daily_data.csv`
- Days threshold: 20 days from 200d high
- Initial capital: $10,000
- Date range: Full data range available

### Custom Parameters

```bash
python3 backtest_20d_from_200d_high.py \
    --data-file your_data.csv \
    --days-threshold 15 \
    --initial-capital 50000 \
    --start-date 2025-08-01 \
    --end-date 2025-10-01 \
    --output-prefix my_backtest
```

### Available Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `--data-file` | Path to historical OHLCV CSV file | `top10_markets_100d_daily_data.csv` |
| `--days-threshold` | Max days from 200d high to select instruments | 20 |
| `--initial-capital` | Initial portfolio capital in USD | 10000 |
| `--start-date` | Backtest start date (YYYY-MM-DD) | First available |
| `--end-date` | Backtest end date (YYYY-MM-DD) | Last available |
| `--output-prefix` | Prefix for output CSV files | `backtest_20d_200d_high` |

## Data Requirements

The input CSV file should have the following columns:
- `date` - Trading date (YYYY-MM-DD format)
- `symbol` - Instrument symbol (e.g., BTC/USDC:USDC)
- `open` - Opening price
- `high` - Highest price
- `low` - Lowest price
- `close` - Closing price
- `volume` - Trading volume

## Adaptive Parameters

The backtest automatically adapts to available data:
- If insufficient data for 200-day lookback, it adjusts to a shorter period
- Volatility calculation window adjusts proportionally
- Ensures at least 20 trading days for meaningful backtest results

## Output Files

### 1. Portfolio Values (`*_portfolio_values.csv`)

Daily portfolio performance with columns:
- `date` - Trading date
- `portfolio_value` - Total portfolio value
- `num_positions` - Number of positions held
- `positions` - List of symbols held
- `daily_return` - Daily percentage return
- `log_return` - Daily log return

### 2. Trades History (`*_trades.csv`)

Rebalancing activity with columns:
- `date` - Trade date
- `symbol` - Instrument symbol
- `old_weight` - Previous portfolio weight
- `new_weight` - New portfolio weight
- `weight_change` - Change in weight

### 3. Performance Metrics (`*_metrics.csv`)

Summary statistics:
- `initial_capital` - Starting capital
- `final_value` - Ending portfolio value
- `total_return` - Total return percentage
- `annualized_return` - Annualized return percentage
- `annualized_volatility` - Annualized volatility
- `sharpe_ratio` - Risk-adjusted return metric
- `max_drawdown` - Maximum peak-to-trough decline
- `win_rate` - Percentage of profitable days
- `total_trades` - Number of trading days
- `avg_positions` - Average number of positions held

## Example Results

Recent backtest on 100 days of data (Sep-Oct 2025):

```
Portfolio Performance:
  Initial Capital:        $      10,000.00
  Final Value:            $       8,672.89
  Total Return:                   -13.27%
  Annualized Return:              -92.57%

Risk Metrics:
  Annualized Volatility:           84.84%
  Sharpe Ratio:                     -1.09
  Maximum Drawdown:               -26.24%

Trading Statistics:
  Win Rate:                        36.84%
  Trading Days:                        20
  Avg Positions:                      4.1
  Total Rebalances:                    76
```

## Strategy Logic

### 1. Instrument Selection
For each trading day:
- Calculate rolling 200-day (or adjusted) high for each instrument
- Determine days since last 200-day high
- Select instruments within threshold (default: 20 days)

### 2. Volatility Calculation
For selected instruments:
- Calculate daily log returns
- Compute rolling 30-day (or adjusted) volatility
- Annualize volatility by multiplying by √365

### 3. Risk Parity Weighting
Portfolio weights are calculated as:
```
weight_i = (1 / volatility_i) / Σ(1 / volatility_j)
```

This ensures:
- Lower volatility assets get higher weights
- Higher volatility assets get lower weights
- All assets contribute equally to portfolio risk
- Weights sum to 100%

### 4. Rebalancing
- Daily rebalancing to maintain target weights
- Positions added/removed as instruments enter/exit selection criteria
- No transaction costs or slippage modeled (ideal execution)

## Interpreting Results

### Positive Indicators
- Positive total return
- Sharpe ratio > 1.0
- Maximum drawdown < 20%
- Win rate > 50%

### Risk Considerations
- High volatility periods may show negative returns
- Strategy is momentum-based (trend-following)
- Performance depends on market regime
- Small sample sizes can be misleading

## Extending the Backtest

The backtest can be extended by:
1. Adding transaction costs/slippage
2. Implementing position sizing limits
3. Adding leverage constraints
4. Testing different lookback windows
5. Incorporating other selection criteria
6. Adding stop-loss/take-profit rules

## Dependencies

Required Python packages:
- `pandas>=2.0.0` - Data manipulation
- `numpy>=1.26.0` - Numerical calculations

## Notes

- The backtest assumes ideal execution (no slippage or transaction costs)
- Results are for educational/research purposes only
- Past performance does not guarantee future results
- Always validate strategies with out-of-sample data before live trading
