# HyperLiquid Data Fetching

This project pulls data from HyperLiquid in Python using the ccxt library.

## Overview

This project uses [ccxt](https://github.com/ccxt/ccxt) (CryptoCurrency eXchange Trading Library) to fetch trading data from HyperLiquid, a decentralized perpetual futures exchange.

## Requirements

- Python 3.x
- ccxt library
- pandas library

## Installation

```bash
pip install -r requirements.txt
```

## Environment Variables

The following environment variables can be configured for API access:

| Variable | Description | Required |
|----------|-------------|----------|
| `CMC_API` | CoinMarketCap API key for fetching historical cryptocurrency market data | Optional (required for CoinMarketCap data fetching) |
| `HL_API` | HyperLiquid API key for exchange access | Optional (required for HyperLiquid trading) |
| `HL_SECRET` | HyperLiquid API secret for authentication | Optional (required for HyperLiquid trading) |
| `COINALYZE_API` | Coinalyze API key for market analytics data | Optional (required for Coinalyze data fetching) |

Set these variables in your shell environment:

```bash
export CMC_API="your_coinmarketcap_api_key"
export HL_API="your_hyperliquid_api_key"
export HL_SECRET="your_hyperliquid_secret"
export COINALYZE_API="your_coinalyze_api_key"
```

Or create a `.env` file in the project root:

```
CMC_API=your_coinmarketcap_api_key
HL_API=your_hyperliquid_api_key
HL_SECRET=your_hyperliquid_secret
COINALYZE_API=your_coinalyze_api_key
```

## Usage

### Data Fetching

The script fetches daily OHLCV (Open, High, Low, Close, Volume) data from Hyperliquid for BTC, ETH, and SOL.

```bash
python get_data.py
```

This will fetch and display the last 5 days of trading data for:
- BTC/USDC:USDC
- ETH/USDC:USDC
- SOL/USDC:USDC

### Automated Trading Strategy

The `main.py` script implements an automated trading strategy based on 200-day high and volatility calculations.

#### Basic Usage

```bash
# Dry run mode (default - no actual orders placed)
python3 main.py --dry-run

# Live trading (places actual orders)
python3 main.py
```

#### Command-Line Options

- `--days-since-high DAYS`: Maximum days since 200d high for instrument selection (default: 20)
- `--rebalance-threshold THRESHOLD`: Rebalance threshold as decimal, e.g., 0.05 for 5% (default: 0.05)
- `--leverage LEVERAGE`: Leverage multiplier for notional value, e.g., 2.0 for 2x leverage (default: 1.5)
- `--dry-run`: Run in dry-run mode (no actual orders placed)
- `--aggressive`: Use aggressive order execution strategy (limit orders first, then incrementally move towards market)

#### Aggressive Order Execution

The `--aggressive` flag enables a sophisticated order execution strategy that:
1. Sends limit orders at best bid/ask prices first
2. Waits for fills (default: 10 seconds)
3. Incrementally moves unfilled orders closer to crossing the spread
4. Finally crosses the spread with market orders for any remaining unfilled orders

This strategy balances between getting better prices (via limit orders) and ensuring fills (via market orders).

**Examples:**

```bash
# Dry run with aggressive execution
python3 main.py --dry-run --aggressive

# Live trading with aggressive execution and custom parameters
python3 main.py --aggressive --leverage 2.0 --rebalance-threshold 0.03

# Conservative strategy with high rebalancing threshold
python3 main.py --dry-run --rebalance-threshold 0.10 --days-since-high 10
```

### Output

The script displays:
- Daily OHLCV data for each symbol
- Date and time of each candle
- Price range summary
- Average trading volume
