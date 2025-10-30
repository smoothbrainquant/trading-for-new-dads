"""
Automated Trading Strategy Execution

This script now supports blending multiple signals with configurable weights.

Supported signals (handlers implemented or stubbed):
- days_from_high: Long-only instruments near 200d highs (inverse-vol weighted)
- breakout: Long/short based on 50d breakout with 70d exits (inverse-vol weighted)
- carry: Long negative-funding symbols, short positive-funding symbols (basic)
- mean_reversion: Long-only extreme dips with high volume (2d lookback, optimal per backtest)
- size: Placeholder (prints notice if selected but not implemented)

Weights can be provided via an external JSON config file so the backtesting suite
can update them without code changes. Example config structure:

{
  "strategy_weights": {
    "days_from_high": 0.2,
    "breakout": 0.4,
    "mean_reversion": 0.2,
    "size": 0.1,
    "carry": 0.1
  },
  "params": {
    "days_from_high": {"max_days": 20},
    "breakout": {"entry_lookback": 50, "exit_lookback": 70},
    "mean_reversion": {"zscore_threshold": 1.5, "volume_threshold": 1.0, "period_days": 2},
    "size": {"top_n": 10, "bottom_n": 10},
    "carry": {"exchange_id": "hyperliquid"}
  }
}

By default, the script uses weights from all_strategies_config.json. You can override
this by providing a custom --signal-config path, or pass --signals to use equal weights
across listed signals, or pass --signal-config="" to use the legacy 50/50 blend.
"""

import argparse
import json
import os
import sys
from collections import defaultdict
import pandas as pd

# Add workspace root and necessary directories to Python path
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)
EXECUTION_DIR = os.path.join(WORKSPACE_ROOT, "execution")
if EXECUTION_DIR not in sys.path:
    sys.path.insert(0, EXECUTION_DIR)
DATA_SCRIPTS_DIR = os.path.join(WORKSPACE_ROOT, "data", "scripts")
if DATA_SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, DATA_SCRIPTS_DIR)

from ccxt_get_markets_by_volume import ccxt_get_markets_by_volume
from ccxt_get_data import ccxt_fetch_hyperliquid_daily_data
from ccxt_get_balance import ccxt_get_hyperliquid_balance
from ccxt_get_positions import ccxt_get_positions
from check_positions import check_positions, get_position_weights
from data.scripts.fetch_coinmarketcap_data import (
    fetch_coinmarketcap_data,
    map_symbols_to_trading_pairs,
)
from aggressive_order_execution import aggressive_execute_orders

# Import strategies from dedicated package
from execution.strategies import (
    strategy_days_from_high,
    strategy_breakout,
    strategy_carry,
    strategy_mean_reversion,
    strategy_size,
    # strategy_oi_divergence,  # Removed: OI data not used
)

# Import shared strategy utilities for legacy path
from execution.strategies.utils import (
    calculate_days_from_200d_high,
    calculate_rolling_30d_volatility,
    calc_weights,
    calculate_breakout_signals_from_data,
)

# Import cache management
try:
    from data.scripts.coinalyze_cache import CoinalyzeCache
except ImportError:
    CoinalyzeCache = None

# Import reporting module
from execution.reporting import (
    export_portfolio_weights_multisignal,
    export_portfolio_weights_legacy,
    generate_trade_allocation_breakdown,
)


# Strategy Registry: Maps strategy names to their implementation functions
STRATEGY_REGISTRY = {
    "days_from_high": strategy_days_from_high,
    "breakout": strategy_breakout,
    "carry": strategy_carry,
    "mean_reversion": strategy_mean_reversion,
    "size": strategy_size,
    # "oi_divergence": strategy_oi_divergence,  # Removed: OI data not used
}


def _build_strategy_params(
    strategy_name: str,
    historical_data: dict,
    strategy_notional: float,
    params: dict,
    cli_args,
) -> tuple:
    """
    Build parameters for a strategy based on its name.

    Returns:
        Tuple of (args, kwargs) to pass to the strategy function
    """
    p = params.get(strategy_name, {}) if isinstance(params, dict) else {}

    if strategy_name == "days_from_high":
        max_days = (
            int(p.get("max_days", cli_args.days_since_high)) if p else cli_args.days_since_high
        )
        return (historical_data, strategy_notional), {"max_days": max_days}

    elif strategy_name == "breakout":
        return (historical_data, strategy_notional), {}

    elif strategy_name == "carry":
        exchange_id = p.get("exchange_id", "hyperliquid") if isinstance(p, dict) else "hyperliquid"
        top_n = int(p.get("top_n", 10)) if isinstance(p, dict) else 10
        bottom_n = int(p.get("bottom_n", 10)) if isinstance(p, dict) else 10
        return (historical_data, list(historical_data.keys()), strategy_notional), {
            "exchange_id": exchange_id,
            "top_n": top_n,
            "bottom_n": bottom_n,
        }

    elif strategy_name == "mean_reversion":
        zscore_threshold = float(p.get("zscore_threshold", 1.5)) if isinstance(p, dict) else 1.5
        volume_threshold = float(p.get("volume_threshold", 1.0)) if isinstance(p, dict) else 1.0
        lookback_window = int(p.get("lookback_window", 30)) if isinstance(p, dict) else 30
        period_days = int(p.get("period_days", 2)) if isinstance(p, dict) else 2
        limit = int(p.get("limit", 100)) if isinstance(p, dict) else 100
        long_only = bool(p.get("long_only", True)) if isinstance(p, dict) else True
        return (historical_data, strategy_notional), {
            "zscore_threshold": zscore_threshold,
            "volume_threshold": volume_threshold,
            "lookback_window": lookback_window,
            "period_days": period_days,
            "limit": limit,
            "long_only": long_only,
        }

    # elif strategy_name == "oi_divergence":  # Removed: OI data not used
    #     mode = p.get("mode", "trend") if isinstance(p, dict) else "trend"
    #     lookback = int(p.get("lookback", 30)) if isinstance(p, dict) else 30
    #     top_n = int(p.get("top_n", 10)) if isinstance(p, dict) else 10
    #     bottom_n = int(p.get("bottom_n", 10)) if isinstance(p, dict) else 10
    #     exchange_code = p.get("exchange_code", "A") if isinstance(p, dict) else "A"
    #     return (historical_data, strategy_notional), {
    #         "mode": mode,
    #         "lookback": lookback,
    #         "top_n": top_n,
    #         "bottom_n": bottom_n,
    #         "exchange_code": exchange_code,
    #     }

    elif strategy_name == "size":
        top_n = int(p.get("top_n", 10)) if isinstance(p, dict) else 10
        bottom_n = int(p.get("bottom_n", 10)) if isinstance(p, dict) else 10
        limit = int(p.get("limit", 100)) if isinstance(p, dict) else 100
        rebalance_days = int(p.get("rebalance_days", 10)) if isinstance(p, dict) else 10
        return (historical_data, list(historical_data.keys()), strategy_notional), {
            "top_n": top_n,
            "bottom_n": bottom_n,
            "limit": limit,
            "rebalance_days": rebalance_days,
        }

    else:
        # Default: just pass historical_data and notional
        return (historical_data, strategy_notional), {}


def update_market_data():
    """
    Update market cap data from CoinMarketCap.

    This function fetches the latest market cap data and saves it to the data/raw directory.
    It runs automatically at the start of each execution to ensure fresh data.

    Returns:
        pd.DataFrame: Latest market cap data or None if failed
    """
    print("\n" + "=" * 80)
    print("UPDATING MARKET DATA")
    print("=" * 80)

    try:
        # Fetch latest market cap data
        print("\nFetching latest market cap data from CoinMarketCap...")
        df_marketcap = fetch_coinmarketcap_data(limit=300)

        if df_marketcap is not None and not df_marketcap.empty:
            # Save to data/raw directory
            out_dir = os.path.join(WORKSPACE_ROOT, "data", "raw")
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, "crypto_marketcap_latest.csv")
            df_marketcap.to_csv(out_path, index=False)
            print(f"✓ Saved {len(df_marketcap)} market cap records to: {out_path}")
            return df_marketcap
        else:
            print("⚠️  No market cap data available (using mock data)")
            return None
    except Exception as e:
        print(f"⚠️  Error updating market cap data: {e}")
        return None


# def check_and_refresh_oi_data_if_needed():  # Removed: OI data not used
#     """
#     Check OI data freshness and automatically refresh if stale.
#
#     Triggers automatic download if:
#     - OI data is 1+ days behind current date
#     - OI data file is >8 hours old
#
#     Returns:
#         dict: OI data status information after check/refresh
#     """
#     try:
#         from data.scripts.refresh_oi_data import check_and_refresh_oi_data
#
#         # Check and auto-refresh if needed
#         result = check_and_refresh_oi_data(force=False, start_year=2020)
#
#         return result
#
#     except Exception as e:
#         print(f"\n⚠️  Error in OI data check/refresh: {e}")
#         import traceback
#
#         traceback.print_exc()
#         return {"status": "error", "error": str(e), "refreshed": False}


def check_cache_freshness():
    """
    Check the freshness of cached OI and carry (funding rate) data.

    This function inspects the Coinalyze cache directory and reports on the age
    and validity of cached data files. It helps identify when data needs to be refreshed.

    Returns:
        dict: Cache status information
    """
    print("\n" + "=" * 80)
    print("CHECKING CACHE FRESHNESS (Funding Rates)")
    print("=" * 80)

    if CoinalyzeCache is None:
        print("⚠️  CoinalyzeCache not available - skipping cache check")
        return {"status": "unavailable"}

    try:
        # Initialize cache with default TTL (1 hour for funding rates)
        cache = CoinalyzeCache(ttl_hours=1)

        # Get cache info
        info = cache.get_cache_info()

        print(f"\nCache directory: {info['cache_dir']}")
        print(f"Cache TTL: {info['ttl_hours']} hour(s)")

        if not info["files"]:
            print("\n⚠️  No cached data found")
            print("   Coinalyze data will be fetched from API when needed")
            return {"status": "empty", "files": []}

        print(f"\nCached files: {len(info['files'])}")
        print("\nCache Status:")
        print("-" * 80)

        valid_count = 0
        expired_count = 0

        for f in info["files"]:
            status = "✓ VALID" if f["is_valid"] else "✗ EXPIRED"
            age_str = f"{f['age_hours']:.2f}h"
            size_kb = f["size"] / 1024

            # Show validation reason for expired caches
            reason_str = ""
            if not f["is_valid"] and "validation_reason" in f:
                reason = f["validation_reason"]
                if reason == "date_changed":
                    reason_str = " (date changed)"
                elif reason == "ttl_expired":
                    reason_str = " (TTL expired)"

            print(
                f"  {status:10s} {f['name']:40s} age={age_str:8s} size={size_kb:.1f}KB{reason_str}"
            )

            if f["is_valid"]:
                valid_count += 1
            else:
                expired_count += 1

        print("-" * 80)
        print(f"\nSummary: {valid_count} valid, {expired_count} expired")

        if expired_count > 0:
            print("\n⚠️  Some cached data is expired and will be refreshed from API when needed")
        else:
            print("\n✓ All cached data is fresh and will be used")

        return {
            "status": "ok",
            "total_files": len(info["files"]),
            "valid_count": valid_count,
            "expired_count": expired_count,
            "files": info["files"],
        }

    except Exception as e:
        print(f"\n⚠️  Error checking cache: {e}")
        return {"status": "error", "error": str(e)}


def request_markets_by_volume(min_volume=100000):
    """
    Request markets by volume, filtered by minimum daily volume.

    Fetches a list of markets sorted by trading volume to identify
    the most liquid trading instruments.

    Args:
        min_volume (float): Minimum 24h notional volume in USD (default: $100,000)

    Returns:
        list: List of market symbols sorted by volume (filtered by min_volume)
    """
    df = ccxt_get_markets_by_volume()

    if df is not None and not df.empty:
        # Filter by minimum volume
        df_filtered = df[df["notional_volume_24h"] >= min_volume]
        print(f"\nFiltered to {len(df_filtered)} markets with volume >= ${min_volume:,.0f}")

        # Return list of symbols sorted by volume
        return df_filtered["symbol"].tolist()

    return []


def get_200d_daily_data(symbols):
    """
    Get 200 days of daily data.

    Retrieves historical daily OHLCV data for the past 200 days
    for the specified symbols.

    Args:
        symbols (list): List of market symbols

    Returns:
        dict: Dictionary mapping symbols to their historical data
    """
    df = ccxt_fetch_hyperliquid_daily_data(symbols=symbols, days=200)

    if df is not None and not df.empty:
        # Group by symbol and return as dictionary
        result = {}
        for symbol in df["symbol"].unique():
            symbol_data = df[df["symbol"] == symbol].copy()
            result[symbol] = symbol_data
        return result

    return {}


def calculate_days_from_200d_high(data):
    """Deprecated shim; use execution.strategies.utils.calculate_days_from_200d_high instead."""
    from execution.strategies.utils import calculate_days_from_200d_high as _impl

    return _impl(data)


def calculate_200d_ma(data):
    """Placeholder for 200d MA calculation (unused)."""
    pass


def select_instruments_by_days_from_high(data_source, threshold):
    """Deprecated; selection is handled within strategies modules."""
    from execution.strategies.utils import select_instruments_by_days_from_high as _impl

    return _impl(data_source, threshold)


def calculate_rolling_30d_volatility(data, selected_symbols):
    """Deprecated shim; use execution.strategies.utils.calculate_rolling_30d_volatility instead."""
    from execution.strategies.utils import calculate_rolling_30d_volatility as _impl

    return _impl(data, selected_symbols)


def calc_weights(volatilities):
    """Deprecated shim; use execution.strategies.utils.calc_weights instead."""
    from execution.strategies.utils import calc_weights as _impl

    return _impl(volatilities)


def get_current_positions():
    """
    Get current positions.

    Retrieves all current open positions from the exchange account.

    Returns:
        dict: Dictionary mapping symbols to position information
    """
    return check_positions()


def get_balance():
    """
    Get balance.

    Retrieves the current account balance and available funds.

    Returns:
        dict: Account balance information
    """
    return ccxt_get_hyperliquid_balance()


def calculate_difference_weights_positions(target_weights, current_positions):
    """
    Calculate difference between weights and current positions.

    Computes the difference between target portfolio weights and
    actual current position weights.

    Args:
        target_weights (dict): Dictionary of symbols to target weights
        current_positions (dict): Dictionary of current position information

    Returns:
        dict: Dictionary mapping symbols to weight differences
    """
    # Get current position weights
    current_weights = get_position_weights(current_positions)

    # Calculate differences
    differences = {}

    # Check all target symbols
    all_symbols = set(target_weights.keys()) | set(current_weights.keys())

    for symbol in all_symbols:
        target_weight = target_weights.get(symbol, 0)
        current_weight = current_weights.get(symbol, 0)
        differences[symbol] = target_weight - current_weight

    return differences


def get_account_notional_value():
    """
    Get account notional value from balance + positions.

    Calculates total account value including both free balance and
    the notional value of all open positions.

    Returns:
        float: Total account notional value in USD
    """
    # Get balance
    balance = get_balance()

    # Get positions
    positions_data = get_current_positions()

    # Extract account value from balance (perp account)
    perp_balance = balance.get("perp", {})
    perp_info = perp_balance.get("info", {})
    margin_summary = perp_info.get("marginSummary", {})
    account_value = float(margin_summary.get("accountValue", 0))

    print(f"\nAccount notional value: ${account_value:,.2f}")

    return account_value


def calculate_target_positions(weights, notional_value):
    """
    Calculate target positions based on weights and notional value.

    Args:
        weights (dict): Dictionary of symbols to portfolio weights
        notional_value (float): Total account notional value

    Returns:
        dict: Dictionary of symbols to target notional position sizes
    """
    target_positions = {}

    for symbol, weight in weights.items():
        target_notional = weight * notional_value
        target_positions[symbol] = target_notional
        print(f"  {symbol}: weight={weight:.4f}, target=${target_notional:,.2f}")

    return target_positions


def calculate_trade_amounts(target_positions, current_positions, notional_value, threshold=0.05):
    """
    Calculate trade amounts where target positions are > threshold difference from current.

    Important: If a position exists but is NOT in target_positions, it will ALWAYS be
    neutralized (closed) regardless of the threshold. This ensures that off-target
    positions are removed from the portfolio.

    This function correctly handles SHORT positions by:
    - Tracking position side (long vs short) based on contract sign
    - Using signed notional values (negative for short, positive for long)
    - Calculating correct trade amounts: target - current
      * Short position (current=-1000, target=0): diff = +1000 (BUY to close)
      * Long position (current=+1000, target=0): diff = -1000 (SELL to close)

    Args:
        target_positions (dict): Dictionary of symbols to target notional values (always positive/long)
        current_positions (dict): Dictionary of current position information from exchange
        notional_value (float): Total account notional value
        threshold (float): Minimum difference as fraction of notional to trigger trade (default 0.05)

    Returns:
        dict: Dictionary of symbols to trade amounts (positive = buy, negative = sell)
    """
    import ccxt
    import os

    trades = {}

    # Initialize exchange to fetch current prices if needed
    api_key = os.getenv("HL_API")
    api_secret = os.getenv("HL_SECRET")
    exchange = None
    if api_key and api_secret:
        exchange = ccxt.hyperliquid(
            {
                "privateKey": api_secret,
                "walletAddress": api_key,
                "enableRateLimit": True,
            }
        )

    # Get current position notional values with proper sign handling
    # For SHORT positions: notional should be negative
    # For LONG positions: notional should be positive
    # This allows correct trade amount calculation
    current_notional = {}
    position_sides = {}  # Track if position is long (positive) or short (negative)

    for pos in current_positions.get("positions", []):
        symbol = pos.get("symbol")
        contracts = pos.get("contracts", 0)

        # Skip if no contracts
        if contracts == 0:
            continue

        # Get price - try markPrice, then entryPrice, then fetch current price
        mark_price = pos.get("markPrice")
        if mark_price is None or mark_price == 0:
            mark_price = pos.get("entryPrice")
            if mark_price is None or mark_price == 0:
                # Fetch current price from exchange
                if exchange:
                    try:
                        ticker = exchange.fetch_ticker(symbol)
                        mark_price = ticker["last"]
                        print(f"  Fetched current price for {symbol}: ${mark_price:,.2f}")
                    except:
                        mark_price = 0
                else:
                    mark_price = 0

        # IMPORTANT: Hyperliquid returns POSITIVE contracts for BOTH long and short
        # The 'side' field indicates whether it's long or short, not the sign of contracts
        side = pos.get("side", "long")
        position_sides[symbol] = side

        # Store the signed notional value (negative for short, positive for long)
        # This ensures correct trade calculation: target - current
        if side == "short":
            notional = -1 * abs(contracts) * mark_price
        else:
            notional = abs(contracts) * mark_price
        current_notional[symbol] = notional

    # Calculate all symbols to consider
    all_symbols = set(target_positions.keys()) | set(current_notional.keys())

    print(
        f"\nCalculating trade amounts (threshold: {threshold*100:.0f}% of notional = ${notional_value * threshold:,.2f})"
    )
    print("=" * 80)

    for symbol in all_symbols:
        target = target_positions.get(symbol, 0)
        current = current_notional.get(
            symbol, 0
        )  # Now signed: negative for short, positive for long
        side = position_sides.get(symbol, "long")  # Default to 'long' if not tracked

        # Calculate difference: positive means BUY, negative means SELL
        # This works correctly now because current is signed:
        # - Short position (current=-1000, target=0): diff = 0-(-1000) = +1000 (BUY to close)
        # - Long position (current=+1000, target=0): diff = 0-(+1000) = -1000 (SELL to close)
        difference = target - current

        # Calculate percentage difference relative to total notional value
        pct_difference = abs(difference) / notional_value if notional_value > 0 else 0

        print(f"\n{symbol}:")
        print(f"  Current: ${abs(current):,.2f} ({side.upper()})")
        print(f"  Target:  ${target:,.2f} (LONG)")
        print(f"  Diff:    ${difference:,.2f} ({pct_difference*100:.2f}% of notional)")

        # If position exists but is NOT in target weights, always neutralize it
        if symbol not in target_positions and abs(current) > 0:
            # The difference calculation now handles both short and long correctly:
            # - Short: difference will be positive (need to BUY)
            # - Long: difference will be negative (need to SELL)
            trades[symbol] = difference
            if side == "short":
                print(
                    f"  ✓ NEUTRALIZE SHORT: Position not in target weights (BUY ${abs(difference):,.2f} to close short)"
                )
            else:
                print(
                    f"  ✓ NEUTRALIZE LONG: Position not in target weights (SELL ${abs(difference):,.2f})"
                )
        # Only trade if difference exceeds threshold
        elif pct_difference > threshold:
            trades[symbol] = difference
            print(
                f"  ✓ Trade needed: ${abs(difference):,.2f} ({'BUY' if difference > 0 else 'SELL'})"
            )
        else:
            print(f"  ✗ No trade needed (below {threshold*100:.0f}% threshold)")

    return trades


def calculate_breakout_signals_from_data(data):
    """Deprecated shim; use execution.strategies.utils.calculate_breakout_signals_from_data instead."""
    from execution.strategies.utils import calculate_breakout_signals_from_data as _impl

    return _impl(data)


def _normalize_weights(weights_dict):
    """Normalize a dict of strategy weights so they sum to 1.0 (if possible)."""
    if not weights_dict:
        return {}
    total = sum(v for v in weights_dict.values() if v is not None and v >= 0)
    if total <= 0:
        return {}
    return {k: (v / total if v is not None and v >= 0 else 0.0) for k, v in weights_dict.items()}


def load_signal_config(config_path):
    """Load strategy weights and params from a JSON config file if present."""
    if not config_path:
        return None
    try:
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                cfg = json.load(f)
            weights = cfg.get("strategy_weights", {}) or {}
            params = cfg.get("params", {}) or {}
            weights = _normalize_weights(weights)
            print(f"\nLoaded signal blend config from: {config_path}")
            print("Strategy weights:")
            for name, w in weights.items():
                print(f"  {name}: {w:.4f} ({w*100:.2f}%)")
            return {"strategy_weights": weights, "params": params}
        else:
            print(f"\nSignal config not found at: {config_path}. Using CLI/defaults.")
            return None
    except Exception as e:
        print(f"\nError loading signal config '{config_path}': {e}. Using CLI/defaults.")
        return None


def get_base_symbol(symbol):
    """Deprecated shim; use execution.strategies.utils.get_base_symbol instead."""
    from execution.strategies.utils import get_base_symbol as _impl

    return _impl(symbol)


# Note: Strategy functions are now imported from execution.strategies package


def send_orders_if_difference_exceeds_threshold(trades, dry_run=True, aggressive=False):
    """
    Send orders to adjust positions based on calculated trade amounts.

    Places buy/sell orders to rebalance the portfolio when the difference
    between target and actual positions exceeds the specified threshold.

    Args:
        trades (dict): Dictionary of symbols to trade amounts (positive = buy, negative = sell)
        dry_run (bool): If True, only prints orders without executing (default: True)
        aggressive (bool): If True, uses aggressive execution strategy (default: False)

    Returns:
        list: List of order results (empty if dry_run=True) or dict for aggressive execution
    """
    from ccxt_make_order import ccxt_make_order

    if not trades:
        print("\nNo trades to execute.")
        return []

    # Use aggressive execution if enabled
    if aggressive:
        print("\nUsing AGGRESSIVE ORDER EXECUTION strategy (tick-based)...")
        result = aggressive_execute_orders(
            trades=trades,
            tick_interval=2.0,  # Poll every 2 seconds
            max_time=60,  # Run for max 60 seconds
            cross_spread_after=True,  # Cross spread if not filled after max_time
            dry_run=dry_run,
        )
        return result

    # Default execution (simple market orders)
    print(f"\n{'='*80}")
    print(f"ORDER EXECUTION {'(DRY RUN)' if dry_run else '(LIVE)'}")
    print(f"{'='*80}")

    orders = []

    for symbol, amount in trades.items():
        side = "buy" if amount > 0 else "sell"
        notional = abs(amount)

        print(f"\n{symbol}: {side.upper()} ${notional:,.2f}")

        if dry_run:
            print(f"  [DRY RUN] Would place {side} order for ${notional:,.2f}")
        else:
            try:
                order = ccxt_make_order(
                    symbol=symbol, notional_amount=notional, side=side, order_type="market"
                )
                orders.append(order)
                print(f"  ✓ Order placed successfully")
            except Exception as e:
                print(f"  ✗ Error placing order: {str(e)}")

    return orders


def main():
    """
    Main execution function supporting multi-signal blending with external weights.

    Modes (evaluated in order):
    - By default, uses weights from all_strategies_config.json
    - If custom --signal-config provided and found, use weights from that config
    - If --signals provided, use equal weights across listed signals
    - If --signal-config="" (empty), fallback to legacy 50/50 (days_from_high + breakout)
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Automated Trading Strategy Execution",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--days-since-high",
        type=int,
        default=20,
        help="Maximum days since 200d high for instrument selection",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.05,
        help="Rebalance threshold as decimal (e.g., 0.05 for 5%%)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Run in dry-run mode (no actual orders placed)",
    )
    parser.add_argument(
        "--leverage",
        type=float,
        default=1.5,
        help="Leverage multiplier for notional value (e.g., 2.0 for 2x leverage)",
    )
    parser.add_argument(
        "--aggressive",
        action="store_true",
        default=False,
        help="Use aggressive order execution strategy (tick-based: continuously move limit orders to best bid/ask)",
    )
    parser.add_argument(
        "--signals",
        type=str,
        default=None,
        help="Comma-separated list of signals to blend (e.g., days_from_high,breakout,mean_reversion,size,carry)",
    )
    parser.add_argument(
        "--signal-config",
        type=str,
        default=os.path.join(EXECUTION_DIR, "all_strategies_config.json"),
        help="Path to JSON config file with strategy_weights and optional params (default: all_strategies_config.json)",
    )
    args = parser.parse_args()

    # Decide blending mode
    config = load_signal_config(args.signal_config) if args.signal_config else None
    configured_weights = (config or {}).get("strategy_weights") if config else None
    params = (config or {}).get("params", {}) if config else {}

    if configured_weights:
        blend_weights = configured_weights
        selected_signals = list(blend_weights.keys())
        title = "MULTI-SIGNAL BLEND (config-driven)"
    else:
        selected_signals = []
        if args.signals:
            selected_signals = [s.strip() for s in args.signals.split(",") if s.strip()]
        blend_weights = (
            _normalize_weights({s: 1.0 for s in selected_signals}) if selected_signals else None
        )
        title = "MULTI-SIGNAL BLEND (CLI)" if blend_weights else "COMBINED 50/50 (legacy)"

    print("=" * 80)
    print(f"AUTOMATED TRADING STRATEGY EXECUTION - {title}")
    print("=" * 80)

    # Update market data and check cache freshness
    print("\n[Pre-flight checks]")
    update_market_data()

    # # Check and auto-refresh OI data if OI strategy is being used  # Removed: OI data not used
    # if (
    #     blend_weights
    #     and "oi_divergence" in blend_weights
    #     and blend_weights.get("oi_divergence", 0) > 0
    # ):
    #     print("\n[OI Data Check] OI Divergence strategy active - checking data freshness...")
    #     oi_result = check_and_refresh_oi_data_if_needed()
    #
    #     # Check result
    #     if oi_result.get("refreshed"):
    #         print("\n" + "✓" * 80)
    #         print("✓ OI DATA AUTOMATICALLY REFRESHED")
    #         print(f"✓ Fresh data downloaded and ready for trading")
    #         print("✓" * 80)
    #     elif oi_result.get("status") == "current":
    #         print("\n✓ OI data is current - no refresh needed")
    #     elif oi_result.get("status") in ["refresh_failed", "error"]:
    #         # Refresh failed - issue strong warning
    #         print("\n" + "!" * 80)
    #         print("⚠️  CRITICAL: OI DATA REFRESH FAILED")
    #         print(f"   Strategy weight: {blend_weights.get('oi_divergence', 0)*100:.1f}%")
    #         print("   Impact: Will use existing data (potentially stale)")
    #         print("   Recommendation: Check COINALYZE_API credentials and network")
    #         if oi_result.get("error"):
    #             print(f"   Error: {oi_result.get('error')}")
    #         print("!" * 80)
    #     else:
    #         # Unknown status - warn but continue
    #         print(f"\n⚠️  Warning: Unexpected OI data status: {oi_result.get('status')}")

    check_cache_freshness()

    print(f"\nParameters:")
    print(f"  Days since high (Strategy 1 default): {args.days_since_high}")
    print(f"  Rebalance threshold: {args.threshold*100:.1f}%")
    print(f"  Leverage: {args.leverage}x")
    print(f"  Aggressive execution: {args.aggressive}")
    print(f"  Dry run: {args.dry_run}")
    if blend_weights:
        print("\nSelected signals and weights:")
        for name, w in blend_weights.items():
            print(f"  {name}: {w:.4f} ({w*100:.2f}%)")
    else:
        print("\nSelected signals: days_from_high + breakout (50/50 legacy)")
    print("=" * 80)

    # Step 1: Request markets by volume
    print("\n[1/7] Requesting markets by volume (>$100k/day)...")
    symbols = request_markets_by_volume(min_volume=100000)
    print(f"Selected {len(symbols)} markets")

    if not symbols:
        print("No markets found. Exiting.")
        return

    # Step 2: Get 200d daily data
    print("\n[2/7] Fetching 200 days of daily data...")
    historical_data = get_200d_daily_data(symbols)
    print(f"Retrieved data for {len(historical_data)} symbols")

    if not historical_data:
        print("No historical data available. Exiting.")
        return

    # Step 3: Get account notional and apply leverage
    print("\n[3/7] Getting account notional and applying leverage...")
    try:
        base_notional_value = get_account_notional_value()
    except Exception as e:
        # Check if error is due to missing credentials
        missing_creds = "HL_API" in str(e) or "HL_SECRET" in str(e) or "must be set" in str(e)
        if missing_creds:
            print(
                f"Could not fetch account value (credentials missing). Using mock $100,000 for DRY RUN."
            )
            base_notional_value = 100000.0
        else:
            # For other errors, still raise if not in dry-run
            if args.dry_run:
                print(f"Could not fetch account value ({e}). Using mock $100,000 for DRY RUN.")
                base_notional_value = 100000.0
            else:
                raise
    notional_value = base_notional_value * args.leverage
    if args.leverage != 1.0:
        print(
            f"Applying {args.leverage}x leverage: ${base_notional_value:,.2f} → ${notional_value:,.2f}"
        )

    # Step 4: Build target positions either via blend or legacy 50/50
    print("\n[4/7] Building target positions from selected signals...")
    target_positions = defaultdict(float)
    # Track per-signal contributions for allocation breakdown
    per_signal_contribs: dict[str, dict[str, float]] = {}
    signal_names: list[str] = []

    if blend_weights:
        # Use multi-signal blend
        signal_names = list(blend_weights.keys())

        # First pass: Call all strategies with their initial weights
        initial_contributions = {}
        initial_contributions_original = {}  # Store unscaled contributions for comparison
        for strategy_name, weight in blend_weights.items():
            if weight <= 0:
                continue

            strategy_notional = notional_value * weight
            print("\n" + "-" * 80)
            print(
                f"Strategy: {strategy_name} | Allocation: ${strategy_notional:,.2f} ({weight*100:.2f}%)"
            )

            # Look up strategy function in registry
            strategy_fn = STRATEGY_REGISTRY.get(strategy_name)
            if not strategy_fn:
                print(f"  WARNING: Unknown strategy '{strategy_name}' not in registry, skipping.")
                contrib = {}
            else:
                # Build parameters for this strategy
                strategy_args, strategy_kwargs = _build_strategy_params(
                    strategy_name=strategy_name,
                    historical_data=historical_data,
                    strategy_notional=strategy_notional,
                    params=params,
                    cli_args=args,
                )

                # Execute strategy
                try:
                    contrib = strategy_fn(*strategy_args, **strategy_kwargs)
                except Exception as e:
                    print(f"  ERROR executing strategy '{strategy_name}': {e}")
                    contrib = {}

            # Store initial contributions (both original and working copy)
            initial_contributions[strategy_name] = dict(contrib)
            initial_contributions_original[strategy_name] = dict(contrib)

        # Print BEFORE reallocation weights
        print("\n" + "=" * 80)
        print("PORTFOLIO WEIGHTS BEFORE CAPITAL REALLOCATION")
        print("=" * 80)
        temp_positions_before = defaultdict(float)
        for strategy_name, contrib in initial_contributions.items():
            for sym, ntl in contrib.items():
                temp_positions_before[sym] += ntl

        if temp_positions_before:
            # Convert to weights
            weights_before = {}
            for symbol, notional in temp_positions_before.items():
                weight = notional / notional_value if notional_value > 0 else 0.0
                weights_before[symbol] = weight

            # Sort by absolute weight
            sorted_weights = sorted(weights_before.items(), key=lambda x: abs(x[1]), reverse=True)

            print(f"\nTop 20 positions:")
            for i, (symbol, weight) in enumerate(sorted_weights[:20], 1):
                side = "LONG" if weight > 0 else ("SHORT" if weight < 0 else "FLAT")
                print(f"  {i:2d}. {symbol:20s}: {weight:>8.3f} ({weight*100:>6.2f}%) {side:>5s}")

            total_weight = sum(abs(w) for w in weights_before.values())
            total_long = sum(w for w in weights_before.values() if w > 0)
            total_short = sum(abs(w) for w in weights_before.values() if w < 0)
            print(f"\nTotal positions: {len(weights_before)}")
            print(f"Total weight (abs): {total_weight:.3f}")
            print(f"Long weight: {total_long:.3f}")
            print(f"Short weight: {total_short:.3f}")
        else:
            print("\nNo positions before reallocation.")
        print("=" * 80)

        # Check which strategies returned no positions and rebalance
        # Fixed weight strategies that should maintain their allocation
        FIXED_WEIGHT_STRATEGIES = {"breakout", "days_from_high"}

        active_strategies = {
            name: weight
            for name, weight in blend_weights.items()
            if initial_contributions.get(name, {})
        }
        inactive_strategies = {
            name: weight
            for name, weight in blend_weights.items()
            if not initial_contributions.get(name, {})
        }

        if inactive_strategies:
            print("\n" + "=" * 80)
            print("CAPITAL REALLOCATION: Some strategies returned no positions")
            print("=" * 80)
            for name, orig_weight in inactive_strategies.items():
                print(f"  ❌ {name}: No positions found (original weight: {orig_weight*100:.2f}%)")

            if active_strategies:
                # Separate fixed and flexible strategies
                fixed_active = {
                    name: weight
                    for name, weight in active_strategies.items()
                    if name in FIXED_WEIGHT_STRATEGIES
                }
                flexible_active = {
                    name: weight
                    for name, weight in active_strategies.items()
                    if name not in FIXED_WEIGHT_STRATEGIES
                }

                # Calculate capital to redistribute (from inactive strategies + inactive fixed strategies)
                inactive_flexible = {
                    name: weight
                    for name, weight in inactive_strategies.items()
                    if name not in FIXED_WEIGHT_STRATEGIES
                }
                capital_to_redistribute = sum(inactive_flexible.values())

                print(f"\n  Fixed allocations (maintaining original weights):")
                for name, weight in fixed_active.items():
                    print(f"    {name}: {weight*100:.2f}% (fixed)")

                if flexible_active and capital_to_redistribute > 0:
                    # Renormalize only flexible strategies with the additional capital
                    # New weight = original weight * (1 + capital_to_redistribute / sum(original flexible weights))
                    original_flexible_total = sum(flexible_active.values())
                    scale_factor = (
                        original_flexible_total + capital_to_redistribute
                    ) / original_flexible_total

                    print(
                        f"\n  Reallocating {capital_to_redistribute*100:.2f}% capital among flexible strategies:"
                    )

                    rebalanced_weights = {}
                    # Keep fixed weights unchanged
                    for name, weight in fixed_active.items():
                        rebalanced_weights[name] = weight

                    # Scale up flexible weights proportionally
                    for name, weight in flexible_active.items():
                        new_weight = weight * scale_factor
                        rebalanced_weights[name] = new_weight
                        print(
                            f"    {name}: {weight*100:.2f}% → {new_weight*100:.2f}% "
                            f"(+{(new_weight - weight)*100:.2f}pp)"
                        )

                    # Verify total sums to 1.0
                    total_weight = sum(rebalanced_weights.values())
                    if abs(total_weight - 1.0) > 0.0001:
                        print(
                            f"\n  ⚠️  WARNING: Total weight = {total_weight*100:.2f}% (expected 100%)"
                        )

                    # Recalculate positions with new weights
                    print("\n  Recalculating positions with adjusted weights...")
                    print("-" * 80)

                    for strategy_name, new_weight in rebalanced_weights.items():
                        old_weight = blend_weights[strategy_name]
                        old_notional = notional_value * old_weight
                        new_notional = notional_value * new_weight

                        if strategy_name in FIXED_WEIGHT_STRATEGIES:
                            print(f"\n  Strategy: {strategy_name} (FIXED)")
                            print(f"    Allocation: ${old_notional:,.2f} (unchanged)")
                        else:
                            print(f"\n  Strategy: {strategy_name}")
                            print(f"    Allocation: ${old_notional:,.2f} → ${new_notional:,.2f}")

                            # Scale the initial contributions by the weight ratio
                            ratio = new_weight / old_weight if old_weight > 0 else 0
                            old_contrib = initial_contributions[strategy_name]
                            new_contrib = {
                                sym: notional * ratio for sym, notional in old_contrib.items()
                            }

                            initial_contributions[strategy_name] = new_contrib
                            print(f"    Positions scaled by {ratio:.4f}x")

                    # Update blend_weights to reflect rebalancing
                    blend_weights = rebalanced_weights
                    print("=" * 80)
                elif not flexible_active:
                    print(
                        f"\n  All active strategies have fixed weights (no flexible strategies to rebalance)"
                    )
                    # Keep the fixed strategies at their original weights
                    rebalanced_weights = fixed_active
                    blend_weights = rebalanced_weights
                    print("=" * 80)
                else:
                    print(f"\n  No capital to redistribute (all inactive strategies are fixed)")
                    print("=" * 80)
            else:
                print("\n  ⚠️  WARNING: No strategies returned any positions!")
                print("=" * 80)

        # Build target positions from (potentially rebalanced) contributions
        for strategy_name, contrib in initial_contributions.items():
            per_signal_contribs[strategy_name] = dict(contrib)
            for sym, ntl in contrib.items():
                target_positions[sym] += ntl

        # Print AFTER reallocation weights
        print("\n" + "=" * 80)
        print("PORTFOLIO WEIGHTS AFTER CAPITAL REALLOCATION")
        print("=" * 80)

        if target_positions:
            # Convert to weights
            weights_after = {}
            for symbol, notional in target_positions.items():
                weight = notional / notional_value if notional_value > 0 else 0.0
                weights_after[symbol] = weight

            # Sort by absolute weight
            sorted_weights = sorted(weights_after.items(), key=lambda x: abs(x[1]), reverse=True)

            print(f"\nTop 20 positions:")
            for i, (symbol, weight) in enumerate(sorted_weights[:20], 1):
                side = "LONG" if weight > 0 else ("SHORT" if weight < 0 else "FLAT")
                print(f"  {i:2d}. {symbol:20s}: {weight:>8.3f} ({weight*100:>6.2f}%) {side:>5s}")

            total_weight = sum(abs(w) for w in weights_after.values())
            total_long = sum(w for w in weights_after.values() if w > 0)
            total_short = sum(abs(w) for w in weights_after.values() if w < 0)
            print(f"\nTotal positions: {len(weights_after)}")
            print(f"Total weight (abs): {total_weight:.3f}")
            print(f"Long weight: {total_long:.3f}")
            print(f"Short weight: {total_short:.3f}")
        else:
            print("\nNo positions after reallocation.")
        print("=" * 80)

        # Print combined positions
        if target_positions:
            print("\nCombined Target Positions (from multi-signal blend):")
            print("=" * 80)
            for symbol, target in sorted(target_positions.items()):
                side = "LONG" if target > 0 else ("SHORT" if target < 0 else "FLAT")
                print(f"  {symbol}: {side} ${abs(target):,.2f}")
        else:
            print("\nNo target positions generated from selected signals.")

        # CRITICAL WARNING: Check capital utilization
        total_allocated = sum(abs(v) for v in target_positions.values())
        utilization_pct = (total_allocated / notional_value * 100) if notional_value > 0 else 0
        print(f"\n{'='*80}")
        print(
            f"CAPITAL UTILIZATION: ${total_allocated:,.2f} / ${notional_value:,.2f} ({utilization_pct:.1f}%)"
        )
        print(f"{'='*80}")

        # Warn if severely underallocated
        if utilization_pct < 50:
            print(f"\n⚠️  WARNING: LOW CAPITAL UTILIZATION ({utilization_pct:.1f}%)")
            print(
                f"    Expected ~100% utilization with leverage, but only {utilization_pct:.1f}% is allocated."
            )
            print(f"    This means most strategies are NOT finding signals:")
            for strategy_name, weight in blend_weights.items():
                expected_alloc = weight * notional_value
                actual_alloc = sum(
                    abs(per_signal_contribs.get(strategy_name, {}).get(sym, 0.0))
                    for sym in target_positions.keys()
                )
                strat_util = (actual_alloc / expected_alloc * 100) if expected_alloc > 0 else 0
                status = "✓" if strat_util > 80 else "⚠️" if strat_util > 20 else "❌"
                print(
                    f"      {status} {strategy_name:20s}: {strat_util:>5.1f}% (${actual_alloc:>12,.2f} / ${expected_alloc:>12,.2f})"
                )
            print(f"\n    Possible causes:")
            print(f"      1. Strategies require external data (Coinalyze API for carry/OI)")
            print(f"      2. Current market conditions don't meet strategy criteria")
            print(f"      3. Strategy parameters are too conservative")
            print(f"{'='*80}\n")

        # Export portfolio weights to file after handling reallocation
        export_portfolio_weights_multisignal(
            target_positions=target_positions,
            initial_contributions_original=initial_contributions_original,
            per_signal_contribs=per_signal_contribs,
            signal_names=signal_names,
            notional_value=notional_value,
            workspace_root=WORKSPACE_ROOT,
        )

    else:
        # Legacy 50/50 pipeline (days_from_high + breakout)
        print("\nUsing legacy 50/50 blend: days_from_high + breakout")
        initial_contributions_original = {}  # Initialize for legacy path

        # Days from high path
        days_from_high = calculate_days_from_200d_high(historical_data)
        selected_symbols_20d = [
            symbol for symbol, days in days_from_high.items() if days <= args.days_since_high
        ]
        volatilities_20d = (
            calculate_rolling_30d_volatility(historical_data, selected_symbols_20d)
            if selected_symbols_20d
            else {}
        )
        weights_20d = calc_weights(volatilities_20d) if volatilities_20d else {}

        # Breakout path
        breakout_signals = calculate_breakout_signals_from_data(historical_data)
        longs_breakout = [
            symbol for symbol, direction in breakout_signals.items() if direction == 1
        ]
        shorts_breakout = [
            symbol for symbol, direction in breakout_signals.items() if direction == -1
        ]
        vol_long = (
            calculate_rolling_30d_volatility(historical_data, longs_breakout)
            if longs_breakout
            else {}
        )
        vol_short = (
            calculate_rolling_30d_volatility(historical_data, shorts_breakout)
            if shorts_breakout
            else {}
        )
        w_long = calc_weights(vol_long) if vol_long else {}
        w_short = calc_weights(vol_short) if vol_short else {}

        # Combine as before
        strat1_notional = notional_value * 0.5
        strat2_notional = notional_value * 0.5

        # Per-signal contributions
        signal_names = ["days_from_high", "breakout"]
        contrib_days = {sym: w * strat1_notional for sym, w in (weights_20d or {}).items()}
        contrib_breakout: dict[str, float] = {}
        for sym, w in (w_long or {}).items():
            contrib_breakout[sym] = contrib_breakout.get(sym, 0.0) + w * strat2_notional
        for sym, w in (w_short or {}).items():
            contrib_breakout[sym] = contrib_breakout.get(sym, 0.0) - w * strat2_notional
        per_signal_contribs["days_from_high"] = contrib_days
        per_signal_contribs["breakout"] = contrib_breakout
        initial_contributions_original["days_from_high"] = dict(contrib_days)
        initial_contributions_original["breakout"] = dict(contrib_breakout)

        # Combined target positions
        for sym, amt in contrib_days.items():
            target_positions[sym] += amt
        for sym, amt in contrib_breakout.items():
            target_positions[sym] += amt

        if target_positions:
            print("\nCombined Target Positions (legacy 50/50):")
            print("=" * 80)
            for symbol, target in sorted(target_positions.items()):
                side = "LONG" if target > 0 else ("SHORT" if target < 0 else "FLAT")
                print(f"  {symbol}: {side} ${abs(target):,.2f}")

        # Export portfolio weights to file for legacy mode
        export_portfolio_weights_legacy(
            target_positions=target_positions,
            per_signal_contribs=per_signal_contribs,
            signal_names=signal_names,
            notional_value=notional_value,
            workspace_root=WORKSPACE_ROOT,
        )

    # Step 5: Get current positions
    print("\n[5/7] Getting current positions...")
    try:
        current_positions = get_current_positions()
    except Exception as e:
        # Auto-enable dry-run if credentials missing, to avoid hard failure in normal runs
        missing_creds = "HL_API" in str(e) or "HL_SECRET" in str(e) or "must be set" in str(e)
        if args.dry_run or missing_creds:
            if missing_creds and not args.dry_run:
                print("Credentials missing; switching to DRY RUN for this session.")
                args.dry_run = True  # type: ignore
            print(f"Could not fetch positions ({e}). Assuming flat portfolio for DRY RUN.")
            current_positions = {
                "total_positions": 0,
                "total_unrealized_pnl": 0.0,
                "positions": [],
                "symbols": [],
            }
        else:
            raise
    print(f"Currently holding {current_positions['total_positions']} positions")
    print(f"Total unrealized PnL: ${current_positions['total_unrealized_pnl']:,.2f}")

    # Step 6: Calculate trade amounts
    print(f"\n[6/7] Calculating trade amounts (>{args.threshold*100:.0f}% threshold)...")
    trades = calculate_trade_amounts(
        target_positions, current_positions, notional_value, threshold=args.threshold
    )

    # Build and print allocation breakdown by trade before executing orders
    generate_trade_allocation_breakdown(
        trades=trades,
        target_positions=target_positions,
        per_signal_contribs=per_signal_contribs,
        signal_names=signal_names,
        notional_value=notional_value,
        historical_data=historical_data,
        workspace_root=WORKSPACE_ROOT,
        exchange_id="hyperliquid",
    )

    # Step 7: Execute orders (dry run by default)
    print("\n" + "=" * 80)
    print("TRADE EXECUTION")
    print("=" * 80)

    if trades:
        print(f"\n{len(trades)} trade(s) to execute:")
        for symbol, amount in trades.items():
            side = "BUY" if amount > 0 else "SELL"
            print(f"  {symbol}: {side} ${abs(amount):,.2f}")

        # Execute orders
        send_orders_if_difference_exceeds_threshold(
            trades, dry_run=args.dry_run, aggressive=args.aggressive
        )

        if args.dry_run:
            print("\n" + "=" * 80)
            print("NOTE: Running in DRY RUN mode. No actual orders were placed.")
            print("To execute live orders, run without --dry-run flag")
            print("=" * 80)
    else:
        print("\nNo trades needed. Portfolio is within rebalancing threshold.")

    print("\n" + "=" * 80)
    print("STRATEGY EXECUTION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
