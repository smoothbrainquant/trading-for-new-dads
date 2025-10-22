# Breakout Signal Trading Strategy

## Overview

This strategy implements a trend-following system based on price breakouts with asymmetric entry and exit levels. The strategy can take both LONG and SHORT positions based on 50-day high/low breakouts, and uses 70-day levels for exits.

## Signal Rules

### Entry Signals
- **LONG Entry**: Close price crosses above the 50-day high → Go long
- **SHORT Entry**: Close price crosses below the 50-day low → Go short

### Exit Signals
- **LONG Exit**: Close price crosses below the 70-day low → Exit long position
- **SHORT Exit**: Close price crosses above the 70-day high → Exit short position

## Key Features

1. **Asymmetric Entry/Exit**: The strategy uses different lookback periods for entry (50 days) and exit (70 days), allowing positions to run while avoiding whipsaws
2. **Both Long and Short**: Can take positions in both directions based on market trends
3. **Risk Parity Weighting**: Positions are sized based on inverse volatility (lower volatility = higher weight)
4. **Liquid Markets Only**: Only trades markets with >$100k daily volume

## Files

### Core Strategy Files
- `calc_breakout_signals.py` - Calculates breakout signals and position states
- `select_insts_breakout.py` - Selects instruments based on breakout signals
- `main_breakout.py` - Main execution script for the breakout strategy

### Supporting Files
- `calc_vola.py` - Calculates 30-day rolling volatility
- `calc_weights.py` - Calculates risk parity weights
- `ccxt_get_data.py` - Fetches historical price data
- `ccxt_get_markets_by_volume.py` - Gets markets by volume
- `ccxt_make_order.py` - Places orders on the exchange
- `check_positions.py` - Checks current positions

## Usage

### Running the Strategy (Dry Run)
```bash
python3 main_breakout.py --dry-run
```

### Running the Strategy (Live Trading)
```bash
python3 main_breakout.py
```

### Command Line Arguments
- `--rebalance-threshold`: Rebalance threshold as decimal (default: 0.05 for 5%)
- `--leverage`: Leverage multiplier (default: 1.5 for 1.5x)
- `--dry-run`: Run in dry-run mode without placing actual orders

### Examples
```bash
# Dry run with 2x leverage and 3% rebalance threshold
python3 main_breakout.py --dry-run --leverage 2.0 --rebalance-threshold 0.03

# Live trading with 1.5x leverage and 5% rebalance threshold
python3 main_breakout.py --leverage 1.5 --rebalance-threshold 0.05
```

## Strategy Workflow

1. **Market Selection**: Fetches markets with >$100k daily volume
2. **Data Collection**: Retrieves 200 days of historical daily data
3. **Signal Calculation**: Calculates breakout signals for all symbols
4. **Signal Separation**: Separates symbols into LONG and SHORT groups
5. **Volatility Calculation**: Calculates 30-day rolling volatility for each group
6. **Weight Calculation**: Calculates risk parity weights separately for longs/shorts
7. **Account Value**: Gets current account notional value
8. **Target Positions**: Calculates target positions (positive for longs, negative for shorts)
9. **Current Positions**: Retrieves current open positions
10. **Trade Calculation**: Calculates required trades to reach target positions
11. **Order Execution**: Places orders to rebalance portfolio

## Position Management

### Long Positions
- Positive notional values
- Entered when close > 50-day high
- Exited when close < 70-day low

### Short Positions
- Negative notional values
- Entered when close < 50-day low
- Exited when close > 70-day high

## Risk Management

1. **Risk Parity Weighting**: Equalizes risk contribution across positions
2. **Rebalance Threshold**: Only trades when position difference exceeds threshold
3. **Leverage Control**: Configurable leverage multiplier
4. **Automatic Neutralization**: Closes positions that are no longer in signal set

## Testing the Strategy

### Test Signal Calculation
```bash
python3 calc_breakout_signals.py
```

### Test Instrument Selection
```bash
python3 select_insts_breakout.py
```

### Test Full Strategy (Dry Run)
```bash
python3 main_breakout.py --dry-run
```

## Output Files

- `breakout_signals_results.csv` - Full historical breakout signals
- `selected_longs_breakout.csv` - Current LONG positions
- `selected_shorts_breakout.csv` - Current SHORT positions

## Requirements

See `requirements.txt` for Python dependencies:
```bash
pip install -r requirements.txt
```

## Environment Variables

For live trading, set the following environment variables:
- `HL_API` - Hyperliquid wallet address
- `HL_SECRET` - Hyperliquid private key

## Comparison with Original Strategy

### Original Strategy (main.py)
- **Signal**: Instruments within 20 days of 200-day high
- **Direction**: Long only
- **Selection**: Time-based (days from high)

### Breakout Strategy (main_breakout.py)
- **Signal**: Price breakouts above 50d high / below 50d low
- **Direction**: Both long and short
- **Selection**: Price-based (breakout confirmation)
- **Exit**: Separate 70-day exit levels for better risk management

## Notes

- The strategy requires at least 70 days of historical data for signal calculation
- Positions are automatically closed if they no longer have active signals
- The strategy uses market orders for execution
- All positions are sized based on risk parity principles
