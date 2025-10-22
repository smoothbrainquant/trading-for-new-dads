"""
Automated Trading Strategy Execution
Main script for executing trading strategy based on 200d high and volatility.
"""

import argparse
from ccxt_get_markets_by_volume import ccxt_get_markets_by_volume
from ccxt_get_data import ccxt_fetch_hyperliquid_daily_data
from ccxt_get_balance import ccxt_get_hyperliquid_balance
from ccxt_get_positions import ccxt_get_positions
from select_insts import select_instruments_near_200d_high
from calc_vola import calculate_rolling_30d_volatility as calc_vola_func
from calc_weights import calculate_weights
from check_positions import check_positions, get_position_weights
from aggressive_order_execution import aggressive_execute_orders
import pandas as pd


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
    """
    Calculate days from 200d high.
    
    Computes the number of days since each instrument reached
    its 200-day high price.
    
    Args:
        data (dict): Historical price data for each symbol
        
    Returns:
        dict: Dictionary mapping symbols to days since 200d high
    """
    from calc_days_from_high import get_current_days_since_high
    
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
    
    # Calculate days since 200d high
    result_df = get_current_days_since_high(df)
    
    # Convert to dictionary
    result = {}
    for _, row in result_df.iterrows():
        result[row['symbol']] = int(row['days_since_200d_high'])
    
    return result


def calculate_200d_ma(data):
    """
    Calculate 200d MA (Moving Average).
    
    Computes the 200-day moving average for each instrument.
    
    Args:
        data (dict): Historical price data for each symbol
        
    Returns:
        dict: Dictionary mapping symbols to their 200d MA values
    """
    pass


def select_instruments_by_days_from_high(data_source, threshold):
    """
    Select instruments based on days from 200d high.
    
    Filters instruments based on how many days have passed since
    their 200-day high, using a specified threshold.
    
    Args:
        data_source (str or pd.DataFrame): Either a path to a CSV file or a pandas DataFrame
        threshold (int): Maximum number of days from high to include
        
    Returns:
        pd.DataFrame: DataFrame of selected instruments with their days since 200d high
    """
    # Use the imported function from select_insts.py
    return select_instruments_near_200d_high(data_source, max_days=threshold)


def calculate_rolling_30d_volatility(data, selected_symbols):
    """
    Calculate rolling 30d volatility.
    
    Computes the 30-day rolling volatility for the selected instruments
    to assess risk and determine position sizing.
    
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
    Calculate portfolio weights based on risk parity.
    
    Risk parity is a portfolio allocation strategy that aims to equalize
    the risk contribution of each asset in the portfolio. Unlike equal
    weighting (which can lead to concentration of risk in volatile assets),
    risk parity assigns weights inversely proportional to asset volatility.
    
    Methodology:
    1. Calculate inverse volatility for each asset (1 / volatility)
    2. Sum all inverse volatilities
    3. Normalize by dividing each inverse volatility by the sum
    
    This ensures that:
    - Lower volatility assets receive higher weights
    - Higher volatility assets receive lower weights
    - All assets contribute equally to portfolio risk
    - Weights sum to 1.0 (100% of portfolio)
    
    Mathematical formula:
        weight_i = (1 / vol_i) / sum(1 / vol_j for all j)
    
    Where:
        vol_i = rolling volatility of asset i
        weight_i = resulting portfolio weight for asset i
    
    Args:
        volatilities (dict): Dictionary mapping symbols to their rolling volatility values.
                           Volatility should be expressed as standard deviation of returns.
                           Example: {'BTC/USD': 0.045, 'ETH/USD': 0.062}
        
    Returns:
        dict: Dictionary mapping symbols to their risk parity weights (summing to 1.0).
              Returns empty dict if volatilities is empty or contains invalid values.
              Example: {'BTC/USD': 0.58, 'ETH/USD': 0.42}
    
    Notes:
        - Assets with zero or negative volatility are excluded from calculation
        - If all assets have zero/invalid volatility, returns empty dict
        - Weights are normalized to sum to exactly 1.0
        - This is a simple equal risk contribution approach; more sophisticated
          implementations might consider correlations between assets
    """
    # Use the imported calculate_weights function from calc_weights module
    return calculate_weights(volatilities)


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
        print("\nUsing AGGRESSIVE ORDER EXECUTION strategy...")
        result = aggressive_execute_orders(
            trades=trades,
            wait_time=10,
            max_iterations=3,
            increment_ticks=5,
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
    Main execution function.
    
    Orchestrates the entire trading strategy workflow:
    1. Request markets by volume (>$100k/day)
    2. Get 200d daily data
    3. Calculate days from 200d high
    4. Select instruments <= 20d from high
    5. Calculate rolling 30d volatility
    6. Calculate weights based on inverse volatility
    7. Get account notional value from balance + positions
    8. Calculate target positions with weights * notional
    9. Get current positions
    10. Calculate difference between target and current positions
    11. Calculate trade amounts where target positions are > 5% difference from notional
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
        help='Use aggressive order execution strategy (limit orders first, then incrementally move towards market)'
    )
    args = parser.parse_args()
    
    print("="*80)
    print("AUTOMATED TRADING STRATEGY EXECUTION")
    print("="*80)
    print(f"\nParameters:")
    print(f"  Days since high: {args.days_since_high}")
    print(f"  Rebalance threshold: {args.rebalance_threshold*100:.1f}%")
    print(f"  Leverage: {args.leverage}x")
    print(f"  Aggressive execution: {args.aggressive}")
    print(f"  Dry run: {args.dry_run}")
    print("="*80)
    
    # Step 1: Request markets by volume, select markets over $100k volume/day
    print("\n[1/11] Requesting markets by volume (>$100k/day)...")
    symbols = request_markets_by_volume(min_volume=100000)
    print(f"Selected {len(symbols)} markets")
    
    if not symbols:
        print("No markets found. Exiting.")
        return
    
    # Step 2: Get 200d daily data
    print("\n[2/11] Fetching 200 days of daily data...")
    historical_data = get_200d_daily_data(symbols)
    print(f"Retrieved data for {len(historical_data)} symbols")
    
    if not historical_data:
        print("No historical data available. Exiting.")
        return
    
    # Step 3: Calculate days from 200d high
    print("\n[3/11] Calculating days from 200d high...")
    days_from_high = calculate_days_from_200d_high(historical_data)
    print(f"Calculated days from high for {len(days_from_high)} symbols")
    
    # Step 4: Select instruments <= days_since_high from high
    print(f"\n[4/11] Selecting instruments <= {args.days_since_high} days from high...")
    # Create a DataFrame for filtering
    selected_symbols = [symbol for symbol, days in days_from_high.items() if days <= args.days_since_high]
    print(f"Selected {len(selected_symbols)} instruments near their 200d high:")
    for symbol in selected_symbols:
        print(f"  {symbol}: {days_from_high[symbol]} days from high")
    
    if not selected_symbols:
        print("No instruments near their 200d high. Exiting.")
        return
    
    # Step 5: Calculate rolling 30d volatility
    print("\n[5/11] Calculating rolling 30d volatility...")
    volatilities = calculate_rolling_30d_volatility(historical_data, selected_symbols)
    print(f"Calculated volatility for {len(volatilities)} symbols:")
    for symbol, vol in volatilities.items():
        print(f"  {symbol}: {vol:.6f}")
    
    if not volatilities:
        print("No volatility data available. Exiting.")
        return
    
    # Step 6: Calculate weights based on inverse volatility
    print("\n[6/11] Calculating weights based on inverse volatility...")
    weights = calc_weights(volatilities)
    print(f"Calculated weights for {len(weights)} symbols:")
    for symbol, weight in weights.items():
        print(f"  {symbol}: {weight:.4f} ({weight*100:.2f}%)")
    
    # Step 7: Get account notional value from balance + positions
    print("\n[7/11] Getting account notional value...")
    base_notional_value = get_account_notional_value()
    
    # Apply leverage multiplier
    notional_value = base_notional_value * args.leverage
    if args.leverage != 1.0:
        print(f"Applying {args.leverage}x leverage: ${base_notional_value:,.2f} → ${notional_value:,.2f}")
    
    # Step 8: Calculate target positions with weights * notional
    print("\n[8/11] Calculating target positions...")
    target_positions = calculate_target_positions(weights, notional_value)
    
    # Step 9: Get current positions
    print("\n[9/11] Getting current positions...")
    current_positions = get_current_positions()
    print(f"Currently holding {current_positions['total_positions']} positions")
    print(f"Total unrealized PnL: ${current_positions['total_unrealized_pnl']:,.2f}")
    
    # Step 10: Calculate difference between target and current positions
    print("\n[10/11] Calculating differences between target and current positions...")
    # This is handled within calculate_trade_amounts
    
    # Step 11: Calculate trade amounts where target positions are > threshold difference from notional
    print(f"\n[11/11] Calculating trade amounts (>{args.rebalance_threshold*100:.0f}% threshold)...")
    trades = calculate_trade_amounts(
        target_positions, 
        current_positions, 
        notional_value, 
        threshold=args.rebalance_threshold
    )
    
    # Execute orders (dry run by default)
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
