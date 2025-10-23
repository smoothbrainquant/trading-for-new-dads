# Size Factor Backtest Strategy

## Overview

The Size Factor backtest implements a quantitative trading strategy based on market capitalization, testing the hypothesis that smaller cap cryptocurrencies may exhibit different return characteristics compared to large cap cryptocurrencies. This is analogous to the well-documented "size premium" or "small cap effect" observed in traditional equity markets.

## Strategy Description

### Core Concept

The size factor strategy ranks cryptocurrencies by market capitalization and constructs portfolios based on size buckets:

- **Large Cap**: Top quintile by market cap (Bucket 1)
- **Mid Cap**: Middle quintiles (Buckets 2-4)
- **Small Cap**: Bottom quintile by market cap (Bucket 5)

### Strategy Variants

1. **Long Small Cap Only (`long_small`)**
   - Long position in smallest quintile only
   - 50% exposure (default)
   - Market neutral not applicable

2. **Long Small, Short Large (`long_small_short_large`)**
   - Long position in smallest quintile
   - Short position in largest quintile
   - Market neutral strategy
   - 50% long exposure + 50% short exposure (default)

3. **Long Bottom 2 Quintiles (`long_small_2_quintiles`)**
   - Long position in bottom 2 quintiles (40% of market)
   - More diversified small cap exposure
   - 50% exposure (default)

### Portfolio Construction

Within each size bucket, the strategy uses **risk parity weighting**:
- Calculate 30-day rolling volatility for each asset
- Assign weights inversely proportional to volatility
- Higher volatility → Lower weight
- Lower volatility → Higher weight

This ensures that each position contributes equally to portfolio risk.

## Files

### Main Scripts

1. **`fetch_coinmarketcap_data.py`**
   - Fetches real-time market cap data from CoinMarketCap API
   - Falls back to mock data if API key not available
   - Generates realistic market cap distribution

2. **`backtest_size_factor.py`**
   - Main backtest engine for size factor strategies
   - Supports multiple strategy variants
   - Calculates comprehensive performance metrics

### Output Files

Each backtest run generates 4 CSV files:

1. **`backtest_size_factor_portfolio_values.csv`**
   - Daily portfolio values
   - Position counts (long/short)
   - Exposure metrics (long/short/net/gross)

2. **`backtest_size_factor_trades.csv`**
   - Complete trade history
   - Rebalancing details
   - Weight changes over time

3. **`backtest_size_factor_metrics.csv`**
   - Performance metrics summary
   - Risk-adjusted returns
   - Drawdown statistics

4. **`backtest_size_factor_strategy_info.csv`**
   - Strategy configuration
   - Selected symbols for long/short
   - Size bucket assignments

## Usage

### Basic Usage

```bash
# Long small cap only (default)
python3 backtest_size_factor.py \
  --price-data top10_markets_100d_daily_data.csv \
  --strategy long_small

# Long small, short large (market neutral)
python3 backtest_size_factor.py \
  --price-data top10_markets_100d_daily_data.csv \
  --strategy long_small_short_large

# Long bottom 2 quintiles
python3 backtest_size_factor.py \
  --price-data top10_markets_100d_daily_data.csv \
  --strategy long_small_2_quintiles
```

### Advanced Configuration

```bash
python3 backtest_size_factor.py \
  --price-data top10_markets_100d_daily_data.csv \
  --marketcap-file crypto_marketcap.csv \
  --strategy long_small_short_large \
  --num-buckets 5 \
  --volatility-window 30 \
  --rebalance-days 7 \
  --initial-capital 10000 \
  --leverage 1.0 \
  --long-allocation 0.5 \
  --short-allocation 0.5 \
  --start-date 2025-07-01 \
  --end-date 2025-10-07 \
  --output-prefix backtest_size_factor_custom
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--price-data` | `top10_markets_100d_daily_data.csv` | Historical OHLCV price data |
| `--marketcap-file` | None | Market cap CSV file (fetches if not provided) |
| `--cmc-api-key` | None | CoinMarketCap API key (or set CMC_API_KEY env var) |
| `--strategy` | `long_small_short_large` | Strategy variant |
| `--num-buckets` | 5 | Number of size buckets (quintiles) |
| `--volatility-window` | 30 | Volatility calculation window (days) |
| `--rebalance-days` | 7 | Rebalance frequency (days) |
| `--initial-capital` | 10000 | Starting capital in USD |
| `--leverage` | 1.0 | Leverage multiplier |
| `--long-allocation` | 0.5 | Long side allocation (50%) |
| `--short-allocation` | 0.5 | Short side allocation (50%) |
| `--start-date` | None | Backtest start date (YYYY-MM-DD) |
| `--end-date` | None | Backtest end date (YYYY-MM-DD) |
| `--output-prefix` | `backtest_size_factor` | Output file prefix |

## Performance Metrics

The backtest calculates comprehensive performance metrics:

### Return Metrics
- **Total Return**: Cumulative return over backtest period
- **Annualized Return**: Geometric mean annual return
- **Win Rate**: Percentage of positive daily returns

### Risk Metrics
- **Annualized Volatility**: Standard deviation of returns (annualized)
- **Sharpe Ratio**: Risk-adjusted return (assuming 0% risk-free rate)
- **Maximum Drawdown**: Largest peak-to-trough decline

### Exposure Metrics
- **Long Exposure**: Average long position exposure
- **Short Exposure**: Average short position exposure
- **Net Exposure**: Average net market exposure (long - short)
- **Gross Exposure**: Average total exposure (long + short)

### Trading Statistics
- **Avg Long Positions**: Average number of long positions
- **Avg Short Positions**: Average number of short positions
- **Total Rebalances**: Number of rebalancing events
- **Trading Days**: Number of days in backtest

## Example Results

### Long Small Cap Strategy

```
Strategy Information:
  Strategy: long_small
  Long symbols (5): BTC, ETH, SOL, XRP, DOGE
  
Portfolio Performance:
  Initial Capital:        $      10,000.00
  Final Value:            $      10,621.28
  Total Return:                     6.21%
  Annualized Return:               36.96%

Risk Metrics:
  Annualized Volatility:           26.02%
  Sharpe Ratio:                      1.42
  Maximum Drawdown:                -7.08%

Trading Statistics:
  Win Rate:                        56.52%
  Trading Days:                        70
  Avg Long Positions:                 5.0
```

## Market Cap Data

### Using CoinMarketCap API

To use real market cap data:

1. Get a free API key from [CoinMarketCap](https://coinmarketcap.com/api/)
2. Set environment variable:
   ```bash
   export CMC_API_KEY="your-api-key-here"
   ```
3. Or pass directly:
   ```bash
   python3 backtest_size_factor.py --cmc-api-key "your-api-key"
   ```

### Fetching Market Cap Data

```bash
# Fetch and save market cap data
python3 fetch_coinmarketcap_data.py \
  --api-key "your-api-key" \
  --limit 100 \
  --output crypto_marketcap.csv

# Use saved data in backtest
python3 backtest_size_factor.py \
  --marketcap-file crypto_marketcap.csv
```

### Mock Data

If no API key is provided, the system generates realistic mock data:
- Follows power law distribution (Zipf's law)
- BTC-like market cap for largest coin (~$1T)
- Exponential decay for smaller coins
- Realistic price/volume relationships

## Strategy Hypothesis

### Academic Background

The size factor is well-documented in traditional finance:
- **Fama-French Three-Factor Model**: Includes size as a risk factor
- **Small Cap Premium**: Historically, small cap stocks outperformed large caps
- **Risk Compensation**: Higher volatility justifies higher expected returns

### Crypto Market Application

In cryptocurrency markets:
- **Growth Potential**: Smaller projects may have more room to grow
- **Liquidity Premium**: Lower liquidity may command higher returns
- **Risk Characteristics**: Higher beta and volatility
- **Market Inefficiency**: Less analyst coverage, more mispricings

### Considerations

- **Survival Bias**: Many small caps fail completely
- **Liquidity Risk**: Harder to exit large positions
- **Higher Volatility**: Requires robust risk management
- **Market Conditions**: May perform differently in bull vs bear markets

## Risk Management

The strategy incorporates several risk management techniques:

1. **Risk Parity Weighting**: Equal risk contribution from each position
2. **Volatility Targeting**: Inverse volatility weighting
3. **Regular Rebalancing**: Weekly rebalancing (default)
4. **Position Limits**: Controlled through allocation parameters
5. **Leverage Control**: Configurable leverage parameter

## Dependencies

```
ccxt>=4.0.0
pandas>=2.0.0
numpy>=1.24.0
requests>=2.28.0
```

Install with:
```bash
pip install -r requirements.txt
```

## Integration with Existing System

This size factor backtest integrates with the existing trading system:

- Uses same data format as other backtests
- Leverages `calc_vola.py` for volatility calculations
- Uses `calc_weights.py` for risk parity weighting
- Compatible with CCXT data fetching infrastructure

## Limitations and Future Enhancements

### Current Limitations

1. **Static Market Cap**: Uses single snapshot of market cap data
2. **Limited Universe**: Constrained by available trading data
3. **No Transaction Costs**: Assumes frictionless trading
4. **No Slippage**: Assumes execution at close prices

### Future Enhancements

1. **Dynamic Market Cap**: Update market caps over time
2. **Transaction Costs**: Include realistic trading fees
3. **Slippage Model**: Account for market impact
4. **Multi-Factor Model**: Combine size with momentum, value, etc.
5. **Machine Learning**: Predict optimal size allocations
6. **Regime Detection**: Adjust strategy based on market conditions

## References

- Fama, E. F., & French, K. R. (1993). Common risk factors in the returns on stocks and bonds.
- Banz, R. W. (1981). The relationship between return and market value of common stocks.
- Liu, Y., Tsyvinski, A., & Wu, X. (2022). Common risk factors in cryptocurrency.

## Support and Contribution

For questions or contributions:
1. Review existing backtest documentation in `BACKTEST_README.md`
2. Check strategy docs in `BREAKOUT_SIGNAL_STRATEGY.md`
3. Follow code patterns in `backtest_breakout_signals.py` and `backtest_20d_from_200d_high.py`

## License

This code is part of a cryptocurrency trading system. Use at your own risk.

---

**Disclaimer**: This backtest is for educational and research purposes only. Past performance does not guarantee future results. Cryptocurrency trading involves substantial risk of loss. Always conduct your own research and consult with financial advisors before trading.
