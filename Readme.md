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

## Usage

The script fetches daily OHLCV (Open, High, Low, Close, Volume) data from Hyperliquid for BTC, ETH, and SOL.

```bash
python get_data.py
```

This will fetch and display the last 5 days of trading data for:
- BTC/USDC:USDC
- ETH/USDC:USDC
- SOL/USDC:USDC

### Output

The script displays:
- Daily OHLCV data for each symbol
- Date and time of each candle
- Price range summary
- Average trading volume
