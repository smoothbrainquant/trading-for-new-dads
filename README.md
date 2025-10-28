# Crypto Trading System

A comprehensive cryptocurrency trading system with data collection, signal generation, backtesting, and execution capabilities.

## 🚀 Repository Robustness

This repository includes a comprehensive robustness enhancement plan with working infrastructure:
- **Custom exception hierarchy** - 12+ specific exception types
- **Input validators** - Data, signal, and risk validation
- **Retry logic** - Automatic retry with exponential backoff
- **Development tools** - Pre-commit hooks, linting, formatting
- **Testing infrastructure** - Expanding test coverage

**📖 [See Robustness Documentation](docs/robustness/)** | **⚡ [Quick Start](ROBUSTNESS_QUICKSTART.md)**

## Repository Structure

The repository is organized into the following main directories:

### 📊 `data/`
Contains all data-related scripts and raw data files.

- **`data/scripts/`** - Scripts for fetching market data
  - `ccxt_get_data.py` - Get OHLCV data via CCXT
  - `ccxt_get_markets.py` - Fetch available markets
  - `ccxt_get_markets_by_volume.py` - Get markets sorted by volume
  - `coinalyze_client.py` - Client for Coinalyze API
  - `coinalyze_demo.py` - Demo script for Coinalyze integration
  - `ccxt_api_test.py` - API connection testing

- **`data/raw/`** - Raw CSV data files
  - Historical price data from Coinbase and other sources
  - Market data snapshots

### 🎯 `signals/`
Signal generation and calculation scripts.

- `calc_breakout_signals.py` - Calculate breakout trading signals
- `calc_days_from_high.py` - Calculate days from historical high
- `calc_vola.py` - Volatility calculations
- `calc_weights.py` - Portfolio weight calculations
- `analyze_directional_mean_reversion.py` - Directional mean reversion analysis
- `analyze_funding_rates.py` - Funding rate analysis
- `analyze_mean_reversion_results.py` - Mean reversion results analysis

### 📈 `backtests/`
Backtesting infrastructure and historical test results.

- **`backtests/scripts/`** - Backtesting scripts
  - `backtest_breakout_signals.py` - Backtest breakout strategy
  - `backtest_carry_factor.py` - Backtest carry factor strategy
  - `backtest_size_factor.py` - Backtest size factor strategy
  - `backtest_mean_reversion.py` - Backtest mean reversion strategy
  - `backtest_mean_reversion_periods.py` - Period-based mean reversion backtest
  - `backtest_20d_from_200d_high.py` - Backtest 20d from 200d high strategy

- **`backtests/results/`** - Backtest output files (CSV)
  - Performance metrics
  - Portfolio values
  - Trade logs
  - Strategy-specific statistics

### ⚡ `execution/`
Live trading execution scripts.

- `aggressive_order_execution.py` - Aggressive order execution strategy
- `ccxt_make_order.py` - Place orders via CCXT
- `check_positions.py` - Monitor current positions
- `ccxt_get_positions.py` - Fetch current positions
- `ccxt_get_balance.py` - Check account balance

### 📚 `docs/`
Documentation and strategy descriptions.

- `BACKTEST_README.md` - Backtesting documentation
- `BREAKOUT_SIGNAL_STRATEGY.md` - Breakout signal strategy guide
- `COINALYZE_API_COMPLETE.md` - Complete Coinalyze API documentation
- `COINALYZE_README.md` - Coinalyze integration guide
- `RESEARCH_TODO.md` - Prioritized strategy research TODOs (reappraise after each session)

## Getting Started

### Prerequisites

```bash
pip install -r requirements.txt
```

### Environment Variables

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

### Workflow

1. **Data Collection**: Use scripts in `data/scripts/` to fetch market data
2. **Signal Generation**: Run signal calculations from `signals/` directory
3. **Backtesting**: Test strategies using scripts in `backtests/scripts/`
4. **Live Trading**: Execute trades using scripts in `execution/`

### Important Notes

- Always use `python3` instead of `python`
- Install dependencies before running any script: `pip install -r requirements.txt`
- When backtesting, ensure proper handling of lookahead bias (use next-day returns with `.shift(-1)`)

## Project Principles

- **Reproducibility**: Pin dependencies, record data snapshots/versions, set random seeds, and persist run metadata alongside results.
- **Data contracts**: Define schemas for raw/processed data and validate on ingest with clear failure messages; keep validation summaries in `data/` up to date.
- **Config-driven runs**: Centralize knobs (symbols, weights, limits, dates) in a YAML config. Current scripts use CLI flags; the template at `configs/config.example.yaml` defines the standard fields for future `--config` support.
- **Signal hygiene**: Signals use only information available up to time t and apply `.shift(-1)` for returns to avoid lookahead.
- **Exchange abstraction**: Strategies are exchange-agnostic; adapter layers handle exchange-specific details (symbols, precision, auth).
- **Execution safety**: Enforce notional and per-asset caps, explicit short handling, dry-run defaults, kill switch, and stablecoin/spot filtering for perps.
- **Quality gates**: Lint/format/type-check in CI and require tests with coverage on PRs.
- **Observability**: Emit standardized artifacts (allocation breakdowns, equity curves, metrics) to predictable folders per run.
- **Release discipline**: Tag tested backtest bundles and freeze data versions; use semantic versioning for strategy releases.
- **Docs as contract**: Maintain a top-level contributor guide, environment table, PR checklist, and strategy docs.

### Example configuration (template)

Copy the template and tailor it for your runs:

```bash
mkdir -p configs
cp configs/config.example.yaml configs/config.yaml
```

This repo currently uses CLI flags; treat the YAML as the source of truth for parameters and a foundation for a future `--config` option. See `configs/config.example.yaml` for the full template.

## Strategy Overview

The system implements multiple trading strategies:

- **Breakout Signals**: Identify and trade price breakouts
- **Mean Reversion**: Capture returns from price mean reversion
- **Carry Factor**: Exploit funding rate differentials
- **Size Factor**: Trade based on market capitalization factors

See individual documentation files in `docs/` for detailed strategy explanations.

## Live Trading Execution

### Main Execution Script

The `execution/main.py` script implements an automated trading strategy based on 200-day high and volatility calculations.

#### Basic Usage

```bash
# Dry run mode (default - no actual orders placed)
python3 execution/main.py --dry-run

# Live trading (places actual orders)
python3 execution/main.py
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
3. Incremen­tally moves unfilled orders closer to crossing the spread
4. Finally crosses the spread with market orders for any remaining unfilled orders

This strategy balances between getting better prices (via limit orders) and ensuring fills (via market orders).

**Examples:**

```bash
# Dry run with aggressive execution
python3 execution/main.py --dry-run --aggressive

# Live trading with aggressive execution and custom parameters
python3 execution/main.py --aggressive --leverage 2.0 --rebalance-threshold 0.03

# Conservative strategy with high rebalancing threshold
python3 execution/main.py --dry-run --rebalance-threshold 0.10 --days-since-high 10
```
