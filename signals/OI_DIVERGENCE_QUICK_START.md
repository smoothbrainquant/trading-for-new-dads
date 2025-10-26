# OI Divergence Signal - Quick Start

## 🚀 Quick Commands

### Get Current Signals (Divergence Mode)
```bash
cd /workspace
PYTHONPATH=/workspace python3 signals/generate_oi_divergence_signals.py \
  --mode divergence \
  --top-n 10 \
  --bottom-n 10 \
  --current-only
```

### Get Current Signals (Trend Mode)
```bash
PYTHONPATH=/workspace python3 signals/generate_oi_divergence_signals.py \
  --mode trend \
  --top-n 10 \
  --bottom-n 10 \
  --current-only
```

### Generate Full Historical Signals
```bash
PYTHONPATH=/workspace python3 signals/generate_oi_divergence_signals.py \
  --mode divergence \
  --lookback 30 \
  --top-n 15 \
  --bottom-n 15 \
  --output signals/oi_divergence_historical.csv
```

## 📊 Run Examples
```bash
PYTHONPATH=/workspace python3 signals/example_oi_divergence_usage.py
```

## 💻 Python Usage

```python
from signals.generate_oi_divergence_signals import get_active_positions, load_price_data, load_oi_data

# Load data
price_df = load_price_data('data/raw/combined_coinbase_coinmarketcap_daily.csv')
oi_df = load_oi_data('data/raw/historical_open_interest_all_perps_since2020_20251026_115907.csv')

# Get signals
positions = get_active_positions(
    price_data=price_df,
    oi_data=oi_df,
    mode='divergence',  # or 'trend'
    top_n=10,
    bottom_n=10
)

print(f"LONG: {positions['longs']}")
print(f"SHORT: {positions['shorts']}")
```

## 📈 Current Signals (as of 2025-10-24)

### Divergence Mode (✅ Recommended - +32% historical return)
- **LONG**: BNT, POWR, MORPHO, ZEC, BIO, ATH, AAVE, FLOKI, API3, SNX
- **SHORT**: POPCAT, ALGO, BONK, JTO, ENA, BCH, BTC, LA, WIF, MOG

### Trend Mode (⚠️ Caution - -42% historical return)
- **LONG**: MOG, WIF, LA, BTC, BCH, ENA, JTO, BONK, ALGO, POPCAT
- **SHORT**: BNT, POWR, MORPHO, ZEC, BIO, ATH, AAVE, FLOKI, API3, SNX

## 🎯 Strategy Summary

| Aspect | Divergence Mode | Trend Mode |
|--------|----------------|------------|
| **Philosophy** | Contrarian / Mean Reversion | Momentum / Trend Following |
| **LONG Signal** | OI ↑ + Price ↓ (Short squeeze) | OI ↑ + Price ↑ (Confirmed trend) |
| **SHORT Signal** | OI ↑ + Price ↑ (Distribution) | OI ↓ + Price ↓ (Confirmed downtrend) |
| **Backtest Return** | +31.93% (4.5 years) | -41.80% (4.5 years) |
| **Sharpe Ratio** | 0.23 | -0.43 |
| **Best For** | Crypto volatile markets | Strong trending markets |

## 📁 Key Files

- **Signal Generator**: `signals/generate_oi_divergence_signals.py`
- **Core Logic**: `signals/calc_open_interest_divergence.py`
- **Examples**: `signals/example_oi_divergence_usage.py`
- **Documentation**: `docs/OI_DIVERGENCE_SIGNALS_README.md`
- **Backtest Script**: `backtests/scripts/backtest_open_interest_divergence.py`
- **Execution Strategy**: `execution/strategies/open_interest_divergence.py`

## ⚙️ Key Parameters

- `--mode`: 'divergence' (contrarian) or 'trend' (momentum)
- `--lookback`: Rolling window for z-scores (default: 30 days)
- `--top-n`: Number of LONG positions (default: 10)
- `--bottom-n`: Number of SHORT positions (default: 10)

## 🎓 Understanding the Signals

### Score Interpretation

**High Divergence Score** (e.g., +1.15):
- Price rising + OI falling → Shorts covering → **LONG signal**
- Price falling + OI rising → Potential short squeeze → **LONG signal**

**Low Divergence Score** (e.g., -1.28):
- Price rising + OI rising → New longs at top → **SHORT signal**
- Price falling + OI falling → Weak hands exiting → **SHORT signal**

### Example Signal

```
BNT: Score: 1.146, z_ret: 0.43, z_doi: -1.15
→ Price up slightly (+0.43 σ) but OI down significantly (-1.15 σ)
→ Interpretation: Shorts covering, potential squeeze
→ Signal: LONG
```

## 🔧 Troubleshooting

**No signals generated?**
- Check data files exist in `data/raw/`
- Verify date alignment between price and OI data
- Ensure sufficient historical data (need 30+ days for lookback)

**Fewer symbols than expected?**
- Only symbols present in BOTH price and OI datasets are used
- Current overlap: 90 symbols
- Check `--min-data-points` parameter if using advanced options

**Different results than backtest?**
- Backtest uses full historical data
- Current signals use latest data only
- Signal composition changes daily as markets evolve

## 📚 Learn More

See complete documentation: `docs/OI_DIVERGENCE_SIGNALS_README.md`
