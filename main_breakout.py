"""
Automated Trading Strategy Execution - Breakout Signal Strategy
Main script for executing trading strategy based on 50d high/low breakouts with 70d exits.

Signal Rules:
- LONG: Close above 50-day high → Go long
- EXIT LONG: Close below 70-day low → Exit long
- SHORT: Close below 50-day low → Go short
- EXIT SHORT: Close above 70-day high → Exit short
"""

import argparse
from ccxt_get_markets_by_volume import ccxt_get_markets_by_volume
from ccxt_get_data import ccxt_fetch_hyperliquid_daily_data
from ccxt_get_balance import ccxt_get_hyperliquid_balance
from ccxt_get_positions import ccxt_get_positions
from select_insts_breakout import select_instruments_by_breakout_signals, get_target_positions_from_signals
from calc_vola import calculate_rolling_30d_volatility as calc_vola_func
from calc_weights import calculate_weights
from check_positions import check_positions, get_position_weights
import pandas as pd


def request_markets_by_volume(min_volume=100000):
    """
    Request markets by volume, filtered by minimum daily volume.
    
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


def get_historical_daily_data(symbols, days=200):
    """
    Get historical days of daily data.
    
    Args:
        symbols (list): List of market symbols
        days (int): Number of days of historical data
        
    Returns:
        dict: Dictionary mapping symbols to their historical data
    """
    df = ccxt_fetch_hyperliquid_daily_data(symbols=symbols, days=days)
    
    if df is not None and not df.empty:
        # Group by symbol and return as dictionary
        result = {}
        for symbol in df['symbol'].unique():
            symbol_data = df[df['symbol'] == symbol].copy()
            result[symbol] = symbol_data
        return result
    
    return {}


def calculate_breakout_signals_from_data(data):
    """
    Calculate breakout signals from historical data.
    
    Args:
        data (dict): Historical price data for each symbol
        
    Returns:
        dict: Dictionary mapping symbols to their target direction (1=long, -1=short, 0=flat)
    """
    from calc_breakout_signals import get_current_signals
    
    # Combine all data into a single DataFrame
    combined_data = []
    for symbol, symbol_df in data.items():
        df_copy = symbol_df.copy()
        if 'symbol' not in df_copy.columns:
            df_copy['symbol'] = symbol
        combined_data.append(df_copy)
    
    if not combined_data:
        return {}
    
    df = pd.concat(combined_data, ignore_index=True)
    
    # Get current signals
    signals_df = get_current_signals(df)
    
    # Convert to target positions dictionary
    target_positions = {}
    for _, row in signals_df.iterrows():
        symbol = row['symbol']
        position = row['position']
        
        if position == 'LONG':
            target_positions[symbol] = 1
        elif position == 'SHORT':
            target_positions[symbol] = -1
        else:
            target_positions[symbol] = 0
    
    return target_positions


def get_symbols_with_signals(target_positions):
    """
    Get lists of symbols with LONG and SHORT signals.
    
    Args:
        target_positions (dict): Dictionary mapping symbols to direction (1=long, -1=short, 0=flat)
        
    Returns:
        dict: Dictionary with 'longs' and 'shorts' lists
    """
    longs = [symbol for symbol, direction in target_positions.items() if direction == 1]
    shorts = [symbol for symbol, direction in target_positions.items() if direction == -1]
    
    return {
        'longs': longs,
        'shorts': shorts
    }


def calculate_rolling_30d_volatility(data, selected_symbols):
    """
    Calculate rolling 30d volatility.
    
    Args:
        data (dict): Historical price data for each symbol
        selected_symbols (list): List of selected instrument symbols
        
    Returns:
        dict: Dictionary mapping symbols to their 30d volatility
    """
    # Combine data for selected symbols into a single DataFrame
    combined_data = []
    for symbol in selected_symbols:
        if symbol in data:
            symbol_df = data[symbol].copy()
            if 'symbol' not in symbol_df.columns:
                symbol_df['symbol'] = symbol
            combined_data.append(symbol_df)
    
    if not combined_data:
        return {}
    
    # Concatenate all data into one DataFrame
    df = pd.concat(combined_data, ignore_index=True)
    
    # Calculate rolling volatility using the imported function
    volatility_df = calc_vola_func(df)
    
    # Extract the most recent volatility for each symbol
    result = {}
    for symbol in selected_symbols:
        symbol_data = volatility_df[volatility_df['symbol'] == symbol]
        if not symbol_data.empty:
            # Get the most recent non-null volatility value
            latest_volatility = symbol_data['volatility_30d'].dropna().iloc[-1] if not symbol_data['volatility_30d'].dropna().empty else None
            if latest_volatility is not None:
                result[symbol] = latest_volatility
    
    return result


def calc_weights(volatilities):
    """
    Calculate portfolio weights based on risk parity (inverse volatility).
    
    Args:
        volatilities (dict): Dictionary mapping symbols to their rolling volatility values
        
    Returns:
        dict: Dictionary mapping symbols to their risk parity weights (summing to 1.0)
    """
    return calculate_weights(volatilities)


def get_current_positions():
    """
    Get current positions.
    
    Returns:
        dict: Dictionary mapping symbols to position information
    """
    return check_positions()


def get_balance():
    """
    Get balance.
    
    Returns:
        dict: Account balance information
    """
    return ccxt_get_hyperliquid_balance()


def get_account_notional_value():
    """
    Get account notional value from balance + positions.
    
    Returns:
        float: Total account notional value in USD
    """
    # Get balance
    balance = get_balance()
    
    # Extract account value from balance (perp account)
    perp_balance = balance.get('perp', {})
    perp_info = perp_balance.get('info', {})
    margin_summary = perp_info.get('marginSummary', {})
    account_value = float(margin_summary.get('accountValue', 0))
    
    print(f"\nAccount notional value: ${account_value:,.2f}")
    
    return account_value


def calculate_target_positions_with_direction(weights_long, weights_short, notional_value):
    """
    Calculate target positions based on weights and direction (long/short).
    
    Args:
        weights_long (dict): Dictionary of symbols to portfolio weights for LONG positions
        weights_short (dict): Dictionary of symbols to portfolio weights for SHORT positions
        notional_value (float): Total account notional value
        
    Returns:
        dict: Dictionary of symbols to target notional position sizes (positive=long, negative=short)
    """
    target_positions = {}
    
    # Calculate long positions (positive notional)
    for symbol, weight in weights_long.items():
        target_notional = weight * notional_value
        target_positions[symbol] = target_notional
        print(f"  {symbol}: LONG weight={weight:.4f}, target=${target_notional:,.2f}")
    
    # Calculate short positions (negative notional)
    for symbol, weight in weights_short.items():
        target_notional = -1 * weight * notional_value
        target_positions[symbol] = target_notional
        print(f"  {symbol}: SHORT weight={weight:.4f}, target=-${abs(target_notional):,.2f}")
    
    return target_positions


def calculate_trade_amounts(target_positions, current_positions, notional_value, threshold=0.05):
    """
    Calculate trade amounts where target positions are > threshold difference from current.
    
    This function correctly handles BOTH LONG and SHORT positions by:
    - Tracking position side (long vs short) based on contract sign
    - Using signed notional values (negative for short, positive for long)
    - Calculating correct trade amounts: target - current
    
    Args:
        target_positions (dict): Dictionary of symbols to target notional values (positive=long, negative=short)
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
    current_notional = {}
    position_sides = {}
    
    for pos in current_positions.get('positions', []):
        symbol = pos.get('symbol')
        contracts = pos.get('contracts', 0)
        
        # Skip if no contracts
        if contracts == 0:
            continue
            
        # Get price
        mark_price = pos.get('markPrice')
        if mark_price is None or mark_price == 0:
            mark_price = pos.get('entryPrice')
            if mark_price is None or mark_price == 0:
                if exchange:
                    try:
                        ticker = exchange.fetch_ticker(symbol)
                        mark_price = ticker['last']
                        print(f"  Fetched current price for {symbol}: ${mark_price:,.2f}")
                    except:
                        mark_price = 0
                else:
                    mark_price = 0
        
        side = pos.get('side', 'long')
        position_sides[symbol] = side
        
        # Store the signed notional value
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
        current = current_notional.get(symbol, 0)
        side = position_sides.get(symbol, 'long')
        
        # Calculate difference
        difference = target - current
        
        # Calculate percentage difference relative to total notional value
        pct_difference = abs(difference) / notional_value if notional_value > 0 else 0
        
        # Determine target side
        target_side = "LONG" if target > 0 else ("SHORT" if target < 0 else "FLAT")
        
        print(f"\n{symbol}:")
        print(f"  Current: ${abs(current):,.2f} ({side.upper()})")
        print(f"  Target:  ${abs(target):,.2f} ({target_side})")
        print(f"  Diff:    ${difference:,.2f} ({pct_difference*100:.2f}% of notional)")
        
        # If position exists but is NOT in target weights, always neutralize it
        if symbol not in target_positions and abs(current) > 0:
            trades[symbol] = difference
            if side == 'short':
                print(f"  ✓ NEUTRALIZE SHORT: Position not in target (BUY ${abs(difference):,.2f} to close)")
            else:
                print(f"  ✓ NEUTRALIZE LONG: Position not in target (SELL ${abs(difference):,.2f})")
        # Only trade if difference exceeds threshold
        elif pct_difference > threshold:
            trades[symbol] = difference
            action = 'BUY' if difference > 0 else 'SELL'
            print(f"  ✓ Trade needed: {action} ${abs(difference):,.2f}")
        else:
            print(f"  ✗ No trade needed (below {threshold*100:.0f}% threshold)")
    
    return trades


def send_orders_if_difference_exceeds_threshold(trades, dry_run=True):
    """
    Send orders to adjust positions based on calculated trade amounts.
    
    Args:
        trades (dict): Dictionary of symbols to trade amounts (positive = buy, negative = sell)
        dry_run (bool): If True, only prints orders without executing (default: True)
        
    Returns:
        list: List of order results (empty if dry_run=True)
    """
    from ccxt_make_order import ccxt_make_order
    
    if not trades:
        print("\nNo trades to execute.")
        return []
    
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
    Main execution function for breakout signal strategy.
    
    Workflow:
    1. Request markets by volume (>$100k/day)
    2. Get 200d daily data (need enough history for 70d calculations)
    3. Calculate breakout signals (50d high/low entry, 70d exit levels)
    4. Separate LONG and SHORT signals
    5. Calculate rolling 30d volatility for each group
    6. Calculate weights based on inverse volatility (separately for longs/shorts)
    7. Get account notional value
    8. Calculate target positions (positive for longs, negative for shorts)
    9. Get current positions
    10. Calculate trade amounts where difference > threshold
    11. Execute orders
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description='Automated Trading Strategy Execution - Breakout Signals',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
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
    args = parser.parse_args()
    
    print("="*80)
    print("AUTOMATED TRADING STRATEGY EXECUTION - BREAKOUT SIGNALS")
    print("="*80)
    print("\nSignal Rules:")
    print("  LONG:        Close above 50-day high")
    print("  EXIT LONG:   Close below 70-day low")
    print("  SHORT:       Close below 50-day low")
    print("  EXIT SHORT:  Close above 70-day high")
    print("\nParameters:")
    print(f"  Rebalance threshold: {args.rebalance_threshold*100:.1f}%")
    print(f"  Leverage: {args.leverage}x")
    print(f"  Dry run: {args.dry_run}")
    print("="*80)
    
    # Step 1: Request markets by volume
    print("\n[1/11] Requesting markets by volume (>$100k/day)...")
    symbols = request_markets_by_volume(min_volume=100000)
    print(f"Selected {len(symbols)} markets")
    
    if not symbols:
        print("No markets found. Exiting.")
        return
    
    # Step 2: Get 200d daily data (need history for 70d calculations)
    print("\n[2/11] Fetching 200 days of daily data...")
    historical_data = get_historical_daily_data(symbols, days=200)
    print(f"Retrieved data for {len(historical_data)} symbols")
    
    if not historical_data:
        print("No historical data available. Exiting.")
        return
    
    # Step 3: Calculate breakout signals
    print("\n[3/11] Calculating breakout signals...")
    target_positions_signals = calculate_breakout_signals_from_data(historical_data)
    signals_summary = get_symbols_with_signals(target_positions_signals)
    
    longs_list = signals_summary['longs']
    shorts_list = signals_summary['shorts']
    
    print(f"LONG signals: {len(longs_list)} symbols")
    for symbol in longs_list:
        print(f"  {symbol}")
    
    print(f"\nSHORT signals: {len(shorts_list)} symbols")
    for symbol in shorts_list:
        print(f"  {symbol}")
    
    if not longs_list and not shorts_list:
        print("\nNo signals found. Exiting.")
        return
    
    # Step 4: Calculate rolling 30d volatility for LONG signals
    print("\n[4/11] Calculating rolling 30d volatility for LONG signals...")
    volatilities_long = {}
    if longs_list:
        volatilities_long = calculate_rolling_30d_volatility(historical_data, longs_list)
        print(f"Calculated volatility for {len(volatilities_long)} LONG symbols:")
        for symbol, vol in volatilities_long.items():
            print(f"  {symbol}: {vol:.6f}")
    
    # Step 5: Calculate rolling 30d volatility for SHORT signals
    print("\n[5/11] Calculating rolling 30d volatility for SHORT signals...")
    volatilities_short = {}
    if shorts_list:
        volatilities_short = calculate_rolling_30d_volatility(historical_data, shorts_list)
        print(f"Calculated volatility for {len(volatilities_short)} SHORT symbols:")
        for symbol, vol in volatilities_short.items():
            print(f"  {symbol}: {vol:.6f}")
    
    # Step 6: Calculate weights for LONG positions
    print("\n[6/11] Calculating weights for LONG positions...")
    weights_long = {}
    if volatilities_long:
        weights_long = calc_weights(volatilities_long)
        print(f"Calculated weights for {len(weights_long)} LONG symbols:")
        for symbol, weight in weights_long.items():
            print(f"  {symbol}: {weight:.4f} ({weight*100:.2f}%)")
    
    # Step 7: Calculate weights for SHORT positions
    print("\n[7/11] Calculating weights for SHORT positions...")
    weights_short = {}
    if volatilities_short:
        weights_short = calc_weights(volatilities_short)
        print(f"Calculated weights for {len(weights_short)} SHORT symbols:")
        for symbol, weight in weights_short.items():
            print(f"  {symbol}: {weight:.4f} ({weight*100:.2f}%)")
    
    # Step 8: Get account notional value
    print("\n[8/11] Getting account notional value...")
    base_notional_value = get_account_notional_value()
    
    # Apply leverage multiplier
    notional_value = base_notional_value * args.leverage
    if args.leverage != 1.0:
        print(f"Applying {args.leverage}x leverage: ${base_notional_value:,.2f} → ${notional_value:,.2f}")
    
    # Step 9: Calculate target positions (with direction)
    print("\n[9/11] Calculating target positions...")
    target_positions = calculate_target_positions_with_direction(weights_long, weights_short, notional_value)
    
    # Step 10: Get current positions
    print("\n[10/11] Getting current positions...")
    current_positions = get_current_positions()
    print(f"Currently holding {current_positions['total_positions']} positions")
    print(f"Total unrealized PnL: ${current_positions['total_unrealized_pnl']:,.2f}")
    
    # Step 11: Calculate trade amounts
    print(f"\n[11/11] Calculating trade amounts (>{args.rebalance_threshold*100:.0f}% threshold)...")
    trades = calculate_trade_amounts(
        target_positions, 
        current_positions, 
        notional_value, 
        threshold=args.rebalance_threshold
    )
    
    # Execute orders
    print("\n" + "="*80)
    print("TRADE EXECUTION")
    print("="*80)
    
    if trades:
        print(f"\n{len(trades)} trade(s) to execute:")
        for symbol, amount in trades.items():
            side = 'BUY' if amount > 0 else 'SELL'
            print(f"  {symbol}: {side} ${abs(amount):,.2f}")
        
        # Execute orders
        send_orders_if_difference_exceeds_threshold(trades, dry_run=args.dry_run)
        
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
