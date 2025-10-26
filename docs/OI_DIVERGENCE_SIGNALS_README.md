# OI Divergence Signals

## Overview

The OI (Open Interest) Divergence signal strategy identifies trading opportunities by analyzing divergences between Open Interest changes and price movements in cryptocurrency perpetual futures markets.

## Strategy Concepts

### Signal Modes

#### 1. **Divergence Mode** (Contrarian/Mean Reversion)
- **LONG**: High OI increases when price is falling → Potential short squeeze
- **SHORT**: High OI increases when price is rising → Potential distribution/reversal
- **Logic**: Contrarian to price movement, validated by OI
- **Use Case**: Mean reversion, identifying overbought/oversold conditions

#### 2. **Trend Mode** (Momentum)
- **LONG**: High OI increases confirming price rise → Strong uptrend
- **SHORT**: High OI decreases confirming price fall → Strong downtrend
- **Logic**: Momentum following, OI confirms price direction
- **Use Case**: Trend following, riding confirmed moves

### How It Works

1. **Calculate Returns**: Compute daily log returns for both price and OI
2. **Z-Score Normalization**: Calculate z-scores over a rolling window (default 30 days)
   - `z_ret` = z-score of price return
   - `z_doi` = z-score of OI change
3. **Compute Scores**:
   - **Trend Score** = `z_doi × sign(ret)` → High when OI change confirms price direction
   - **Divergence Score** = `-Trend Score` → High when OI change contradicts price direction
4. **Rank & Select**: Rank all symbols by score, go LONG top N, SHORT bottom N

## Backtest Performance

Based on comprehensive backtest (Sept 2021 - Oct 2025, 384 symbols, 221K+ data points):

| Metric | Divergence | Trend |
|--------|-----------|-------|
| **Total Return** | +31.93% | -41.80% |
| **Annualized Return** | +6.41% | -11.42% |
| **Sharpe Ratio** | 0.23 | -0.43 |
| **Max Drawdown** | -57.01% | -57.01% |
| **Winner** | ✅ Divergence | ❌ Trend |

**Key Insight**: Divergence mode significantly outperforms, suggesting contrarian positioning based on OI/price divergence provides alpha in crypto markets.

## Usage

### Command Line Interface

#### Generate Current Signals (Latest Date Only)

```bash
# Divergence mode (contrarian)
python3 signals/generate_oi_divergence_signals.py \
  --mode divergence \
  --top-n 10 \
  --bottom-n 10 \
  --current-only

# Trend mode (momentum)
python3 signals/generate_oi_divergence_signals.py \
  --mode trend \
  --top-n 15 \
  --bottom-n 15 \
  --current-only
```

#### Generate Full Historical Signals

```bash
python3 signals/generate_oi_divergence_signals.py \
  --mode divergence \
  --lookback 30 \
  --output signals/oi_divergence_signals_full.csv
```

### Python API

```python
from signals.generate_oi_divergence_signals import (
    get_current_signals,
    get_active_positions,
    load_price_data,
    load_oi_data
)

# Load data
price_df = load_price_data('data/raw/combined_coinbase_coinmarketcap_daily.csv')
oi_df = load_oi_data('data/raw/historical_open_interest_all_perps_since2020_20251026_115907.csv')

# Get current signals
signals = get_current_signals(
    price_data=price_df,
    oi_data=oi_df,
    mode='divergence',
    lookback=30,
    top_n=10,
    bottom_n=10
)

print(signals[['symbol', 'rank', 'signal', 'score_value', 'z_ret', 'z_doi']])

# Get active positions
positions = get_active_positions(
    price_data=price_df,
    oi_data=oi_df,
    mode='divergence',
    top_n=10,
    bottom_n=10
)

print(f"LONG: {positions['longs']}")
print(f"SHORT: {positions['shorts']}")
print(f"Date: {positions['date']}")
```

### Integration with Execution System

```python
# In execution/main.py or similar
from signals.generate_oi_divergence_signals import get_active_positions, load_price_data, load_oi_data

# Load data
price_df = load_price_data('data/raw/combined_coinbase_coinmarketcap_daily.csv')
oi_df = load_oi_data('data/raw/historical_open_interest_all_perps_since2020_20251026_115907.csv')

# Get signals
positions = get_active_positions(
    price_data=price_df,
    oi_data=oi_df,
    mode='divergence',
    top_n=10,
    bottom_n=10
)

# Execute trades
for symbol in positions['longs']:
    place_long_order(symbol, size=calculate_position_size(symbol))

for symbol in positions['shorts']:
    place_short_order(symbol, size=calculate_position_size(symbol))
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--mode` | divergence | Strategy mode: 'divergence' or 'trend' |
| `--lookback` | 30 | Rolling window for z-score calculation (days) |
| `--top-n` | 10 | Number of LONG positions (highest scores) |
| `--bottom-n` | 10 | Number of SHORT positions (lowest scores) |
| `--price-data` | data/raw/combined_coinbase_coinmarketcap_daily.csv | Path to price data CSV |
| `--oi-data` | data/raw/historical_open_interest_all_perps_since2020_*.csv | Path to OI data CSV |
| `--output` | signals/oi_divergence_signals.csv | Output file path |
| `--current-only` | False | Only generate current signals (latest date) |

## Output Format

### Current Signals CSV

```csv
date,symbol,rank,signal,position_side,score_value,ret,d_oi,z_ret,z_doi
2025-10-24,BNT,1,LONG,LONG,1.146,0.012,0.015,0.43,-1.15
2025-10-24,MOG,34,SHORT,SHORT,-1.276,0.008,0.025,0.42,1.28
```

### Signal Types

- **LONG**: Top N symbols (highest scores) → Go long
- **SHORT**: Bottom N symbols (lowest scores) → Go short
- **NEUTRAL**: All other symbols → No position

### Key Metrics in Output

- `score_value`: The divergence/trend score (higher = more bullish in respective mode)
- `z_ret`: Z-scored price return (standardized)
- `z_doi`: Z-scored OI change (standardized)
- `ret`: Raw log return
- `d_oi`: Raw log OI change
- `rank`: Ranking by score (1 = highest)

## Data Requirements

### Price Data
- **Format**: CSV with columns: `date`, `symbol`/`base`, `close`
- **Frequency**: Daily
- **Source**: Coinbase spot + CoinMarketCap historical
- **File**: `data/raw/combined_coinbase_coinmarketcap_daily.csv`

### OI Data
- **Format**: CSV with columns: `date`, `coin_symbol`/`symbol`, `oi_close`/`oi`
- **Frequency**: Daily
- **Source**: Coinalyze API (perpetual futures)
- **File**: `data/raw/historical_open_interest_all_perps_since2020_*.csv`
- **Coverage**: 384 symbols, 221K+ data points, Sept 2021 - Oct 2025

## Example Output

```
================================================================================
OI DIVERGENCE SIGNAL GENERATOR
================================================================================
Mode: DIVERGENCE
Lookback: 30 days
Portfolio: 10 longs + 10 shorts
================================================================================

Signals as of 2025-10-24:
Total symbols evaluated: 34

================================================================================
LONG POSITIONS (10):
================================================================================
   1. BNT         Score:   1.146  z_ret:   0.43  z_doi:  -1.15
   2. POWR        Score:   0.368  z_ret:   0.11  z_doi:   0.37
   3. MORPHO      Score:   0.257  z_ret:   0.51  z_doi:  -0.26
   ...

================================================================================
SHORT POSITIONS (10):
================================================================================
  34. MOG         Score:  -1.276  z_ret:   0.42  z_doi:   1.28
  33. WIF         Score:  -1.175  z_ret:   0.28  z_doi:   1.17
  32. LA          Score:  -1.112  z_ret:   0.22  z_doi:   1.11
   ...
```

## Strategy Interpretation

### Divergence Mode Examples

**LONG Signal: BNT (Score: 1.146)**
- `z_ret: 0.43` → Price rising modestly
- `z_doi: -1.15` → OI falling significantly (shorts covering)
- **Interpretation**: Short squeeze potential, contrarian long

**SHORT Signal: MOG (Score: -1.276)**
- `z_ret: 0.42` → Price rising
- `z_doi: 1.28` → OI rising significantly (new longs entering at top)
- **Interpretation**: Potential distribution/reversal, contrarian short

### Trend Mode Examples

**LONG Signal: BTC (Score: 0.778)**
- `z_ret: 0.43` → Price rising
- `z_doi: 0.78` → OI rising (conviction in uptrend)
- **Interpretation**: Confirmed uptrend, momentum long

**SHORT Signal: BNT (Score: -1.146)**
- `z_ret: 0.43` → Price rising
- `z_doi: -1.15` → OI falling (weak hands exiting)
- **Interpretation**: Weak momentum, potential reversal

## Risk Management

1. **Market Neutral**: Strategy is typically ~50% long / 50% short exposure
2. **Risk Parity**: Use inverse volatility weighting within each side
3. **Rebalancing**: Weekly rebalancing recommended (tested at 7-day intervals)
4. **Position Sizing**: Limit individual positions to 5-10% of portfolio
5. **Stop Loss**: Max drawdown historically -57%, set stops accordingly

## Performance Tips

1. **Mode Selection**: 
   - Divergence mode historically outperforms (+31.93% vs -41.80%)
   - Use divergence in range-bound/volatile markets
   - Use trend in strong trending markets (with caution)

2. **Parameter Tuning**:
   - Shorter lookback (20d) → More reactive, higher turnover
   - Longer lookback (45d) → Smoother signals, lower turnover
   - More positions (20/20) → Better diversification, lower concentration risk

3. **Market Conditions**:
   - Strategy performs best during moderate volatility
   - Extreme drawdowns occur during major market crashes
   - Consider reducing exposure during high VIX periods

## Related Files

- **Signal Generator**: `signals/generate_oi_divergence_signals.py`
- **Core Logic**: `signals/calc_open_interest_divergence.py`
- **Backtest Script**: `backtests/scripts/backtest_open_interest_divergence.py`
- **Execution Strategy**: `execution/strategies/open_interest_divergence.py`
- **Test Suite**: `tests/test_signals.py`

## References

- Backtest Summary: `backtests/results/backtest_open_interest_*_metrics.csv`
- OI Data Coverage: See `data/raw/historical_open_interest_*_summary_*.csv`
- Complete dataset: 384 symbols, 221,330 data points, 4+ years of history

## Support

For issues or questions:
1. Check data files exist in `data/raw/`
2. Ensure dependencies installed: `pip install -r requirements.txt`
3. Verify data alignment: price and OI symbols must overlap
4. Review backtest results for expected performance characteristics
