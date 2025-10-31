# Daily Returns Output Feature

## Summary

Modified `run_all_backtests.py` to output daily returns from all strategies into a single CSV file for later analysis.

## Changes Made

### 1. Modified Backtest Functions

Updated all strategy backtest functions to include daily returns in their output:
- `run_breakout_backtest()`
- `run_mean_reversion_backtest()`
- `run_size_factor_backtest()`
- `run_carry_factor_backtest()`
- `run_days_from_high_backtest()`
- `run_volatility_factor_backtest()`
- `run_kurtosis_factor_backtest()`
- `run_beta_factor_backtest()`
- `run_adf_factor_backtest()`

Each function now:
- Calculates daily returns from portfolio values: `portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()`
- Returns a `daily_returns` DataFrame with columns: `["date", "Strategy Name"]`
- Includes this DataFrame in the results dictionary

### 2. Added combine_daily_returns() Function

New function that:
- Takes a list of backtest results
- Extracts the `daily_returns` DataFrame from each result
- Merges all daily returns on the `date` column using an outer join
- Handles strategies with different date ranges (fills missing values with NaN)
- Returns a single DataFrame with:
  - `date` column
  - One column per strategy containing its daily returns

### 3. Updated main() Function

Modified to:
- Call `combine_daily_returns(all_results)` after all backtests complete
- Save the combined daily returns to a CSV file
- Generate the output filename by replacing `_summary.csv` with `_daily_returns.csv`
- Print summary information about the saved file

## Output File

### Location
By default: `backtests/results/all_backtests_daily_returns.csv`

Can be customized via `--output-file` parameter (the daily returns file will use the same path with `_daily_returns.csv` suffix)

### Format
```csv
date,Breakout Signal,Mean Reversion,Size Factor,Carry Factor,Days from High,Volatility Factor,Kurtosis Factor,Beta Factor (BAB),ADF Factor (trend_following_premium)
2024-01-01,0.0123,-0.0045,0.0067,0.0089,0.0034,0.0056,0.0078,0.0012,0.0045
2024-01-02,-0.0023,0.0067,-0.0012,0.0034,0.0089,0.0045,0.0023,0.0067,0.0012
...
```

### Columns
- **date**: Trading date
- **Strategy columns**: One column per strategy with its daily percentage return

### Missing Values
Strategies with different date ranges will have NaN values for dates where they don't have data.

## Usage

### Run All Backtests with Daily Returns

```bash
cd /workspace
python3 backtests/scripts/run_all_backtests.py
```

This will generate three output files:
1. `backtests/results/all_backtests_summary.csv` - Performance metrics summary
2. `backtests/results/all_backtests_sharpe_weights.csv` - Portfolio weights
3. `backtests/results/all_backtests_daily_returns.csv` - **NEW: Daily returns for all strategies**

### Custom Date Range

```bash
python3 backtests/scripts/run_all_backtests.py \
    --start-date 2023-01-01 \
    --end-date 2024-12-31 \
    --output-file backtests/results/custom_backtests_summary.csv
```

This will create:
- `backtests/results/custom_backtests_summary.csv`
- `backtests/results/custom_backtests_sharpe_weights.csv`
- `backtests/results/custom_backtests_daily_returns.csv` (NEW)

## Use Cases for Daily Returns

The daily returns CSV can be used for:

1. **Correlation Analysis**: Calculate correlations between strategies
   ```python
   df = pd.read_csv('backtests/results/all_backtests_daily_returns.csv')
   correlations = df.drop('date', axis=1).corr()
   ```

2. **Portfolio Construction**: Optimize portfolio weights using historical returns
   ```python
   returns = df.drop('date', axis=1)
   cov_matrix = returns.cov()
   # Use for mean-variance optimization
   ```

3. **Risk Analysis**: Calculate Value at Risk (VaR) and other risk metrics
   ```python
   returns = df.drop('date', axis=1)
   var_95 = returns.quantile(0.05)
   ```

4. **Time Series Analysis**: Analyze return patterns over time
   ```python
   df['date'] = pd.to_datetime(df['date'])
   df.set_index('date', inplace=True)
   df.plot(figsize=(15, 8))
   ```

5. **Strategy Combination**: Test different portfolio allocations
   ```python
   # Equal weight portfolio
   portfolio_return = df.drop('date', axis=1).mean(axis=1)
   ```

## Technical Details

- Daily returns are calculated as: `pct_change()` on portfolio values
- The first row will have NaN values (no previous day to compare)
- Returns are in decimal format (0.01 = 1% return)
- Date format: YYYY-MM-DD
- All strategies use the same initial capital for comparability

## Testing

The implementation has been tested with:
- Multiple strategies with different date ranges
- Proper handling of missing values
- Correct merging on date column
- Valid CSV output format

## Notes

- This feature does not change any backtest logic
- It only adds an additional output file for analysis
- All existing outputs remain unchanged
- The daily returns are at the strategy level (portfolio level for each strategy)
