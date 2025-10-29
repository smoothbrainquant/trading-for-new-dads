# Trendline Breakout Signals - Quick Start Guide

## Overview

The trendline breakout signal identifies **momentum continuation opportunities** by detecting when price breaks out strongly from a clean trendline.

### Signal Types
- **LONG**: Price breaks ABOVE a clean uptrend (uptrend continuation)
- **SHORT**: Price breaks BELOW a clean downtrend (downtrend continuation)

### Performance (2020-2025 Backtest)
- **Total Return**: +93.44% (12.31% annualized)
- **Sharpe Ratio**: 0.36
- **Max Drawdown**: -40.27%
- **Win Rate**: 8.5% of days (captures large moves, not daily wins)
- **Trades**: 129 over 5 years (selective, ~26/year)

## Signal Quality Filters

The strategy only generates signals when:
1. **R² ≥ 0.5**: Trendline is clean (explains ≥50% of price variance)
2. **P-value ≤ 0.05**: Trendline is statistically significant
3. **Z-score ≥ 1.5σ**: Breakout is strong (≥1.5 standard deviations from trendline)

These filters ensure we only trade high-quality setups with proven trends.

## Quick Start

### 1. Generate Signals

```bash
# Generate signals with default parameters (recommended)
python3 signals/calc_trendline_breakout_signals.py

# Use stricter filters for higher quality (fewer signals)
python3 signals/calc_trendline_breakout_signals.py --min-r2 0.7 --breakout-threshold 2.0

# Only uptrend breakouts (long only)
python3 signals/calc_trendline_breakout_signals.py --slope-direction positive
```

### 2. View Current Signals

Signals are saved to two files:
- `signals/trendline_breakout_signals_full.csv` - All historical signals
- `signals/trendline_breakout_signals_current.csv` - Recent signals (last 5 days)

### 3. Understand Signal Columns

| Column | Description |
|--------|-------------|
| `date` | Signal date |
| `symbol` | Cryptocurrency symbol |
| `close` | Current price |
| `signal` | LONG, SHORT, or NEUTRAL |
| `signal_strength` | Quality score (higher = better) |
| `r_squared` | Trendline quality (0-1, higher = cleaner) |
| `norm_slope` | Trendline slope (% per year) |
| `breakout_z_score` | Breakout strength (standard deviations) |
| `distance_from_trendline` | How far price is from trendline (%) |
| `volatility` | Annualized volatility |
| `p_value` | Statistical significance (lower = better) |

## Signal Interpretation

### LONG Signal Example
```
Symbol: BTC/USD
Signal: LONG
Signal Strength: 2.50
R²: 0.68
Norm Slope: +250%/year
Breakout Z-score: +2.3σ
Distance: +5.2% above trendline

Interpretation:
✓ Clean uptrend (R² = 0.68)
✓ Strong upward momentum (+250%/year)
✓ Price breaking out above trendline (+2.3σ)
→ Continuation signal: Uptrend likely to continue
```

### SHORT Signal Example
```
Symbol: ETH/USD
Signal: SHORT
Signal Strength: 1.85
R²: 0.62
Norm Slope: -180%/year
Breakout Z-score: -1.9σ
Distance: -3.8% below trendline

Interpretation:
✓ Clean downtrend (R² = 0.62)
✓ Strong downward momentum (-180%/year)
✓ Price breaking below trendline (-1.9σ)
→ Continuation signal: Downtrend likely to continue
```

## Usage in Python

```python
import pandas as pd

# Load signals
signals = pd.read_csv('signals/trendline_breakout_signals_full.csv')
signals['date'] = pd.to_datetime(signals['date'])

# Get current signals (last 5 days)
latest_date = signals['date'].max()
recent_cutoff = latest_date - pd.Timedelta(days=5)
current = signals[
    (signals['date'] >= recent_cutoff) &
    (signals['signal'] != 'NEUTRAL')
]

# Get top 10 long signals by signal strength
top_longs = current[current['signal'] == 'LONG'].nlargest(10, 'signal_strength')

# Get top 10 short signals by signal strength
top_shorts = current[current['signal'] == 'SHORT'].nlargest(10, 'signal_strength')

# Filter by R² quality
high_quality = current[current['r_squared'] >= 0.7]

# Filter by breakout strength
strong_breakouts = current[current['breakout_z_score'].abs() >= 2.0]
```

## Recommended Strategy

### Entry Rules
1. **Signal appears** with R² ≥ 0.5, Z-score ≥ 1.5σ
2. **Rank by signal strength** (higher = better)
3. **Enter top 10 signals per side** (long/short)
4. **Equal weight** or weight by signal strength

### Position Sizing
- **Long allocation**: 50% of capital (5% per position if 10 longs)
- **Short allocation**: 50% of capital (5% per position if 10 shorts)
- **Max positions**: 10 long + 10 short (20 total)

### Exit Rules
- **Fixed holding period**: 5 days (optimal from backtest)
- **Or**: Exit when signal flips (e.g., uptrend breaks down)

### Risk Management
- **Stop loss**: Optional, -10% per position
- **Portfolio stop**: Exit all positions if drawdown > 30%
- **Rebalance**: Daily check for new signals

## Parameters Explained

### Default Parameters (Recommended)
```bash
--trendline-window 30         # 30 days for trendline calculation
--volatility-window 30        # 30 days for volatility normalization
--breakout-threshold 1.5      # 1.5 standard deviations for breakout
--min-r2 0.5                  # Minimum R² of 0.5 for clean trendline
--max-pvalue 0.05             # Maximum p-value of 0.05 for significance
--slope-direction any         # Both uptrend and downtrend breakouts
```

### Conservative Parameters (Higher Quality, Fewer Signals)
```bash
--breakout-threshold 2.0      # Stronger breakouts (2.0σ)
--min-r2 0.7                  # Cleaner trendlines (R² ≥ 0.7)
```

**Trade-off**: Stricter filters reduce signals from 129 to ~23 over 5 years, with lower returns (+12% vs +93%) but also lower drawdowns (-31% vs -40%).

### Aggressive Parameters (More Signals, Lower Quality)
```bash
--breakout-threshold 1.0      # Weaker breakouts (1.0σ)
--min-r2 0.4                  # Less clean trendlines
```

**Trade-off**: More signals but lower quality, not recommended based on backtests.

## Signal Statistics

From 2020-2025 backtest with default parameters:

| Metric | Value |
|--------|-------|
| Total signals | 1,142 |
| LONG signals | 498 (44%) |
| SHORT signals | 644 (56%) |
| Signals after liquidity filter | 129 |
| Average R² | 0.655 |
| Average breakout Z-score | 0.19 |
| Average signal strength | 1.34 |

## Example Workflow

### Daily Signal Check
```bash
# 1. Generate fresh signals
python3 signals/calc_trendline_breakout_signals.py

# 2. View current signals
python3 -c "
import pandas as pd
signals = pd.read_csv('signals/trendline_breakout_signals_current.csv')
print(signals[['symbol', 'signal', 'signal_strength', 'r_squared', 'breakout_z_score']].to_string(index=False))
"

# 3. Filter by quality
python3 -c "
import pandas as pd
signals = pd.read_csv('signals/trendline_breakout_signals_current.csv')
high_quality = signals[signals['r_squared'] >= 0.7]
print(f'High quality signals: {len(high_quality)}')
print(high_quality[['symbol', 'signal', 'signal_strength']].to_string(index=False))
"
```

## Comparison to Other Strategies

### vs. Simple Moving Average Breakout
- **TMA**: Price crosses above/below MA → signal
- **Trendline Breakout**: Price breaks from regression line → signal
- **Advantage**: Considers trend quality (R²) and breakout strength (Z-score)

### vs. Reversal Strategy
- **Reversal**: Trade AGAINST trends (fails, -58% return)
- **Breakout**: Trade WITH trends (works, +93% return)
- **Key difference**: Respect momentum, don't fight it

### vs. Original Trendline Factor
- **Factor**: Continuous ranking by slope × R²
- **Breakout**: Event-driven (breakout detection)
- **Both work**: Factor for sustained trends, Breakout for explosive moves

## Common Questions

### Q: Why so few signals (129 in 5 years)?
**A**: The strategy is highly selective. It only trades:
- Clean trendlines (R² ≥ 0.5)
- Statistically significant (p ≤ 0.05)
- Strong breakouts (Z ≥ 1.5σ)
- Large, liquid coins

This selectivity is a feature, not a bug. Quality > quantity.

### Q: Why is win rate only 8.5%?
**A**: Win rate measures daily P&L. The strategy:
- Holds positions 5 days
- Captures large moves when they occur
- Most days are neutral or small losses
- But winning trades are large

Focus on total return (+93%), not win rate.

### Q: Should I use stricter filters?
**A**: Depends on your goals:
- **More signals**: Use default (R² ≥ 0.5, Z ≥ 1.5σ)
- **Higher quality**: Use strict (R² ≥ 0.7, Z ≥ 2.0σ)
- **Balance**: Default is recommended

### Q: Can I trade only long or only short?
**A**: Yes, use `--slope-direction positive` for long-only or `negative` for short-only. However:
- Long-only performed worse in backtests (-28% return)
- Market-neutral (both) is recommended

## Backtest Summary

See `TRENDLINE_BREAKOUT_SUMMARY.md` for full backtest results.

**Key Results**:
- 5-year total return: +93.44%
- Annualized return: +12.31%
- Sharpe ratio: 0.36
- Max drawdown: -40.27%
- Best holding period: 5 days

## Files

- **Signal Generator**: `signals/calc_trendline_breakout_signals.py`
- **Backtest Script**: `backtests/scripts/backtest_trendline_breakout.py`
- **Full Signals**: `signals/trendline_breakout_signals_full.csv`
- **Current Signals**: `signals/trendline_breakout_signals_current.csv`
- **Backtest Results**: `backtests/results/backtest_trendline_breakout_*`

## Next Steps

1. **Generate signals** with default parameters
2. **Review current signals** in `trendline_breakout_signals_current.csv`
3. **Backtest with your own data** using `backtests/scripts/backtest_trendline_breakout.py`
4. **Paper trade** before going live
5. **Monitor performance** and adjust filters as needed

## Support

For questions or issues:
- Review backtest documentation in `TRENDLINE_BREAKOUT_SUMMARY.md`
- Check comparison analysis in `TRENDLINE_BREAKOUT_VS_REVERSAL.md`
- Run `python3 signals/calc_trendline_breakout_signals.py --help` for CLI options
