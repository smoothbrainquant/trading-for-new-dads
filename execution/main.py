"""
Automated Trading Strategy Execution

This script now supports blending multiple signals with configurable weights.

Supported signals (handlers implemented or stubbed):
- days_from_high: Long-only instruments near 200d highs (inverse-vol weighted)
- breakout: Long/short based on 50d breakout with 70d exits (inverse-vol weighted)
- carry: Long negative-funding symbols, short positive-funding symbols (basic)
- mean_reversion: Placeholder (prints notice if selected but not implemented)
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
    "mean_reversion": {"quantile": 0.2},
    "size": {"top_n": 10, "bottom_n": 10},
    "carry": {"exchange_id": "binance"}
  }
}

If no config is provided, you can pass a list of signals via --signals and the
script will assign equal weights across them. If neither is provided, it falls
back to the original 50/50 blend of days_from_high and breakout.
"""

import argparse
import json
import os
from collections import defaultdict
from ccxt_get_markets_by_volume import ccxt_get_markets_by_volume
from ccxt_get_data import ccxt_fetch_hyperliquid_daily_data
from ccxt_get_balance import ccxt_get_hyperliquid_balance
from ccxt_get_positions import ccxt_get_positions
from check_positions import check_positions, get_position_weights
from aggressive_order_execution import aggressive_execute_orders

# Import strategies from dedicated package
from execution.strategies import (
    strategy_days_from_high,
    strategy_breakout,
    strategy_carry,
    strategy_mean_reversion,
    strategy_size,
)

# Import shared strategy utilities for legacy path
from execution.strategies.utils import (
    calculate_days_from_200d_high,
    calculate_rolling_30d_volatility,
    calc_weights,
    calculate_breakout_signals_from_data,
)


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
        df_filtered = df[df['notional_volume_24h'] >= min_volume]
        print(f"\nFiltered to {len(df_filtered)} markets with volume >= ${min_volume:,.0f}")
        
        # Return list of symbols sorted by volume
        return df_filtered['symbol'].tolist()
    
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
        for symbol in df['symbol'].unique():
            symbol_data = df[df['symbol'] == symbol].copy()
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
    perp_balance = balance.get('perp', {})
    perp_info = perp_balance.get('info', {})
    margin_summary = perp_info.get('marginSummary', {})
    account_value = float(margin_summary.get('accountValue', 0))
    
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
    api_key = os.getenv('HL_API')
    api_secret = os.getenv('HL_SECRET')
    exchange = None
    if api_key and api_secret:
        exchange = ccxt.hyperliquid({
            'privateKey': api_secret,
            'walletAddress': api_key,
            'enableRateLimit': True,
        })
    
    # Get current position notional values with proper sign handling
    # For SHORT positions: notional should be negative
    # For LONG positions: notional should be positive
    # This allows correct trade amount calculation
    current_notional = {}
    position_sides = {}  # Track if position is long (positive) or short (negative)
    
    for pos in current_positions.get('positions', []):
        symbol = pos.get('symbol')
        contracts = pos.get('contracts', 0)
        
        # Skip if no contracts
        if contracts == 0:
            continue
            
        # Get price - try markPrice, then entryPrice, then fetch current price
        mark_price = pos.get('markPrice')
        if mark_price is None or mark_price == 0:
            mark_price = pos.get('entryPrice')
            if mark_price is None or mark_price == 0:
                # Fetch current price from exchange
                if exchange:
                    try:
                        ticker = exchange.fetch_ticker(symbol)
                        mark_price = ticker['last']
                        print(f"  Fetched current price for {symbol}: ${mark_price:,.2f}")
                    except:
                        mark_price = 0
                else:
                    mark_price = 0
        
        # IMPORTANT: Hyperliquid returns POSITIVE contracts for BOTH long and short
        # The 'side' field indicates whether it's long or short, not the sign of contracts
        side = pos.get('side', 'long')
        position_sides[symbol] = side
        
        # Store the signed notional value (negative for short, positive for long)
        # This ensures correct trade calculation: target - current
        if side == 'short':
            notional = -1 * abs(contracts) * mark_price
        else:
            notional = abs(contracts) * mark_price
        current_notional[symbol] = notional
    
    # Calculate all symbols to consider
    all_symbols = set(target_positions.keys()) | set(current_notional.keys())
    
    print(f"\nCalculating trade amounts (threshold: {threshold*100:.0f}% of notional = ${notional_value * threshold:,.2f})")
    print("=" * 80)
    
    for symbol in all_symbols:
        target = target_positions.get(symbol, 0)
        current = current_notional.get(symbol, 0)  # Now signed: negative for short, positive for long
        side = position_sides.get(symbol, 'long')  # Default to 'long' if not tracked
        
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
            if side == 'short':
                print(f"  ✓ NEUTRALIZE SHORT: Position not in target weights (BUY ${abs(difference):,.2f} to close short)")
            else:
                print(f"  ✓ NEUTRALIZE LONG: Position not in target weights (SELL ${abs(difference):,.2f})")
        # Only trade if difference exceeds threshold
        elif pct_difference > threshold:
            trades[symbol] = difference
            print(f"  ✓ Trade needed: ${abs(difference):,.2f} ({'BUY' if difference > 0 else 'SELL'})")
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
            with open(config_path, 'r') as f:
                cfg = json.load(f)
            weights = cfg.get('strategy_weights', {}) or {}
            params = cfg.get('params', {}) or {}
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
            dry_run=dry_run
        )
        return result
    
    # Default execution (simple market orders)
    print(f"\n{'='*80}")
    print(f"ORDER EXECUTION {'(DRY RUN)' if dry_run else '(LIVE)'}")
    print(f"{'='*80}")
    
    orders = []
    
    for symbol, amount in trades.items():
        side = 'buy' if amount > 0 else 'sell'
        notional = abs(amount)
        
        print(f"\n{symbol}: {side.upper()} ${notional:,.2f}")
        
        if dry_run:
            print(f"  [DRY RUN] Would place {side} order for ${notional:,.2f}")
        else:
            try:
                order = ccxt_make_order(
                    symbol=symbol,
                    notional_amount=notional,
                    side=side,
                    order_type='market'
                )
                orders.append(order)
                print(f"  ✓ Order placed successfully")
            except Exception as e:
                print(f"  ✗ Error placing order: {str(e)}")
    
    return orders


def main():
    """
    Main execution function supporting multi-signal blending with external weights.
    
    Modes:
    - If --signal-config provided and found, use weights from config
    - Else if --signals provided, use equal weights across listed signals
    - Else fallback to legacy 50/50 (days_from_high + breakout)
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Automated Trading Strategy Execution',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--days-since-high',
        type=int,
        default=20,
        help='Maximum days since 200d high for instrument selection'
    )
    parser.add_argument(
        '--rebalance-threshold',
        type=float,
        default=0.05,
        help='Rebalance threshold as decimal (e.g., 0.05 for 5%%)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=False,
        help='Run in dry-run mode (no actual orders placed)'
    )
    parser.add_argument(
        '--leverage',
        type=float,
        default=1.5,
        help='Leverage multiplier for notional value (e.g., 2.0 for 2x leverage)'
    )
    parser.add_argument(
        '--aggressive',
        action='store_true',
        default=False,
        help='Use aggressive order execution strategy (tick-based: continuously move limit orders to best bid/ask)'
    )
    parser.add_argument(
        '--signals',
        type=str,
        default=None,
        help='Comma-separated list of signals to blend (e.g., days_from_high,breakout,mean_reversion,size,carry)'
    )
    parser.add_argument(
        '--signal-config',
        type=str,
        default=None,
        help='Path to JSON config file with strategy_weights and optional params'
    )
    args = parser.parse_args()
    
    # Decide blending mode
    config = load_signal_config(args.signal_config) if args.signal_config else None
    configured_weights = (config or {}).get('strategy_weights') if config else None
    params = (config or {}).get('params', {}) if config else {}

    if configured_weights:
        blend_weights = configured_weights
        selected_signals = list(blend_weights.keys())
        title = "MULTI-SIGNAL BLEND (config-driven)"
    else:
        selected_signals = []
        if args.signals:
            selected_signals = [s.strip() for s in args.signals.split(',') if s.strip()]
        blend_weights = _normalize_weights({s: 1.0 for s in selected_signals}) if selected_signals else None
        title = "MULTI-SIGNAL BLEND (CLI)" if blend_weights else "COMBINED 50/50 (legacy)"

    print("="*80)
    print(f"AUTOMATED TRADING STRATEGY EXECUTION - {title}")
    print("="*80)
    print(f"\nParameters:")
    print(f"  Days since high (Strategy 1 default): {args.days_since_high}")
    print(f"  Rebalance threshold: {args.rebalance_threshold*100:.1f}%")
    print(f"  Leverage: {args.leverage}x")
    print(f"  Aggressive execution: {args.aggressive}")
    print(f"  Dry run: {args.dry_run}")
    if blend_weights:
        print("\nSelected signals and weights:")
        for name, w in blend_weights.items():
            print(f"  {name}: {w:.4f} ({w*100:.2f}%)")
    else:
        print("\nSelected signals: days_from_high + breakout (50/50 legacy)")
    print("="*80)

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
    base_notional_value = get_account_notional_value()
    notional_value = base_notional_value * args.leverage
    if args.leverage != 1.0:
        print(f"Applying {args.leverage}x leverage: ${base_notional_value:,.2f} → ${notional_value:,.2f}")

    # Step 4: Build target positions either via blend or legacy 50/50
    print("\n[4/7] Building target positions from selected signals...")
    target_positions = defaultdict(float)

    if blend_weights:
        # Use multi-signal blend
        for strategy_name, weight in blend_weights.items():
            if weight <= 0:
                continue
            strategy_notional = notional_value * weight
            print("\n" + "-"*80)
            print(f"Strategy: {strategy_name} | Allocation: ${strategy_notional:,.2f} ({weight*100:.2f}%)")
            p = params.get(strategy_name, {}) if isinstance(params, dict) else {}

            if strategy_name == 'days_from_high':
                max_days = int(p.get('max_days', args.days_since_high)) if p else args.days_since_high
                contrib = strategy_days_from_high(historical_data, strategy_notional, max_days=max_days)
            elif strategy_name == 'breakout':
                contrib = strategy_breakout(historical_data, strategy_notional)
            elif strategy_name == 'carry':
                exchange_id = p.get('exchange_id', 'binance') if isinstance(p, dict) else 'binance'
                contrib = strategy_carry(historical_data, list(historical_data.keys()), strategy_notional, exchange_id=exchange_id)
            elif strategy_name == 'mean_reversion':
                quantile = float(p.get('quantile', 0.2)) if isinstance(p, dict) else 0.2
                contrib = strategy_mean_reversion(historical_data, strategy_notional, quantile=quantile)
            elif strategy_name == 'size':
                top_n = int(p.get('top_n', 10)) if isinstance(p, dict) else 10
                bottom_n = int(p.get('bottom_n', 10)) if isinstance(p, dict) else 10
                contrib = strategy_size(historical_data, list(historical_data.keys()), strategy_notional, top_n=top_n, bottom_n=bottom_n)
            else:
                print(f"  WARNING: Unknown strategy '{strategy_name}', skipping.")
                contrib = {}

            for sym, ntl in contrib.items():
                target_positions[sym] += ntl

        # Print combined positions
        if target_positions:
            print("\nCombined Target Positions (from multi-signal blend):")
            print("=" * 80)
            for symbol, target in sorted(target_positions.items()):
                side = "LONG" if target > 0 else ("SHORT" if target < 0 else "FLAT")
                print(f"  {symbol}: {side} ${abs(target):,.2f}")
        else:
            print("\nNo target positions generated from selected signals.")

    else:
        # Legacy 50/50 pipeline (days_from_high + breakout)
        print("\nUsing legacy 50/50 blend: days_from_high + breakout")

        # Days from high path
        days_from_high = calculate_days_from_200d_high(historical_data)
        selected_symbols_20d = [symbol for symbol, days in days_from_high.items() if days <= args.days_since_high]
        volatilities_20d = calculate_rolling_30d_volatility(historical_data, selected_symbols_20d) if selected_symbols_20d else {}
        weights_20d = calc_weights(volatilities_20d) if volatilities_20d else {}

        # Breakout path
        breakout_signals = calculate_breakout_signals_from_data(historical_data)
        longs_breakout = [symbol for symbol, direction in breakout_signals.items() if direction == 1]
        shorts_breakout = [symbol for symbol, direction in breakout_signals.items() if direction == -1]
        vol_long = calculate_rolling_30d_volatility(historical_data, longs_breakout) if longs_breakout else {}
        vol_short = calculate_rolling_30d_volatility(historical_data, shorts_breakout) if shorts_breakout else {}
        w_long = calc_weights(vol_long) if vol_long else {}
        w_short = calc_weights(vol_short) if vol_short else {}

        # Combine as before
        strat1_notional = notional_value * 0.5
        strat2_notional = notional_value * 0.5
        for sym, w in weights_20d.items():
            target_positions[sym] += w * strat1_notional
        for sym, w in w_long.items():
            target_positions[sym] += w * strat2_notional
        for sym, w in w_short.items():
            target_positions[sym] -= w * strat2_notional

        if target_positions:
            print("\nCombined Target Positions (legacy 50/50):")
            print("=" * 80)
            for symbol, target in sorted(target_positions.items()):
                side = "LONG" if target > 0 else ("SHORT" if target < 0 else "FLAT")
                print(f"  {symbol}: {side} ${abs(target):,.2f}")

    # Step 5: Get current positions
    print("\n[5/7] Getting current positions...")
    current_positions = get_current_positions()
    print(f"Currently holding {current_positions['total_positions']} positions")
    print(f"Total unrealized PnL: ${current_positions['total_unrealized_pnl']:,.2f}")
    
    # Step 6: Calculate trade amounts
    print(f"\n[6/7] Calculating trade amounts (>{args.rebalance_threshold*100:.0f}% threshold)...")
    trades = calculate_trade_amounts(
        target_positions, 
        current_positions, 
        notional_value, 
        threshold=args.rebalance_threshold
    )
    
    # Step 7: Execute orders (dry run by default)
    print("\n" + "="*80)
    print("TRADE EXECUTION")
    print("="*80)
    
    if trades:
        print(f"\n{len(trades)} trade(s) to execute:")
        for symbol, amount in trades.items():
            side = 'BUY' if amount > 0 else 'SELL'
            print(f"  {symbol}: {side} ${abs(amount):,.2f}")
        
        # Execute orders
        send_orders_if_difference_exceeds_threshold(trades, dry_run=args.dry_run, aggressive=args.aggressive)
        
        if args.dry_run:
            print("\n" + "="*80)
            print("NOTE: Running in DRY RUN mode. No actual orders were placed.")
            print("To execute live orders, run without --dry-run flag")
            print("="*80)
    else:
        print("\nNo trades needed. Portfolio is within rebalancing threshold.")
    
    print("\n" + "="*80)
    print("STRATEGY EXECUTION COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
