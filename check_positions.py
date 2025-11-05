#!/usr/bin/env python3
"""
Check Positions Script

Compares current positions (in notional) to desired positions (in notional).
This script helps identify rebalancing needs by showing the difference between
target portfolio allocation and actual positions.
"""

import pandas as pd
from ccxt_get_positions import ccxt_get_positions
from ccxt_get_balance import ccxt_get_hyperliquid_balance


def get_current_positions_notional():
    """
    Get current positions with notional values.
    
    Returns:
        dict: Dictionary mapping symbols to their notional position values
              Positive values = long positions, Negative values = short positions
    """
    positions = ccxt_get_positions()
    
    current_notional = {}
    
    for pos in positions:
        contracts = pos.get('contracts', 0)
        if contracts != 0:  # Only include non-zero positions
            symbol = pos.get('symbol')
            mark_price = pos.get('markPrice', 0)
            
            # Calculate notional value
            # Positive for long, negative for short
            notional = contracts * mark_price
            current_notional[symbol] = notional
    
    return current_notional


def get_desired_positions_notional(weights, account_value):
    """
    Get desired positions with notional values based on target weights.
    
    Args:
        weights (dict): Dictionary mapping symbols to their target weights (0-1)
        account_value (float): Total account value in USD
    
    Returns:
        dict: Dictionary mapping symbols to their desired notional position values
    """
    desired_notional = {}
    
    for symbol, weight in weights.items():
        # Calculate desired notional = account_value * weight
        desired_notional[symbol] = account_value * weight
    
    return desired_notional


def compare_positions(current_notional, desired_notional):
    """
    Compare current positions to desired positions.
    
    Args:
        current_notional (dict): Current positions in notional values
        desired_notional (dict): Desired positions in notional values
    
    Returns:
        pd.DataFrame: Comparison dataframe with columns:
                     - symbol: instrument symbol
                     - current_notional: current position size in USD
                     - desired_notional: target position size in USD
                     - difference: difference in USD (desired - current)
                     - pct_difference: percentage difference relative to desired
    """
    # Get all unique symbols from both dictionaries
    all_symbols = set(list(current_notional.keys()) + list(desired_notional.keys()))
    
    comparison_data = []
    
    for symbol in all_symbols:
        current = current_notional.get(symbol, 0.0)
        desired = desired_notional.get(symbol, 0.0)
        difference = desired - current
        
        # Calculate percentage difference relative to desired position
        # If desired is 0, use absolute difference
        if desired != 0:
            pct_difference = (difference / abs(desired)) * 100
        else:
            pct_difference = 100.0 if current != 0 else 0.0
        
        comparison_data.append({
            'symbol': symbol,
            'current_notional': current,
            'desired_notional': desired,
            'difference': difference,
            'pct_difference': pct_difference
        })
    
    # Create DataFrame and sort by absolute difference (descending)
    df = pd.DataFrame(comparison_data)
    df = df.sort_values('difference', key=abs, ascending=False).reset_index(drop=True)
    
    return df


def print_position_comparison(comparison_df, threshold_pct=5.0):
    """
    Print a formatted comparison of positions.
    
    Args:
        comparison_df (pd.DataFrame): Comparison dataframe from compare_positions()
        threshold_pct (float): Percentage threshold to highlight (default 5%)
    """
    print("\n" + "=" * 100)
    print("POSITION COMPARISON: CURRENT vs DESIRED (NOTIONAL)")
    print("=" * 100)
    
    # Summary statistics
    total_current = comparison_df['current_notional'].sum()
    total_desired = comparison_df['desired_notional'].sum()
    total_difference = comparison_df['difference'].sum()
    
    print(f"\nSummary:")
    print(f"  Total Current Notional:  ${total_current:,.2f}")
    print(f"  Total Desired Notional:  ${total_desired:,.2f}")
    print(f"  Total Difference:        ${total_difference:,.2f}")
    
    # Positions requiring rebalancing (exceeding threshold)
    needs_rebalancing = comparison_df[abs(comparison_df['pct_difference']) > threshold_pct]
    
    if not needs_rebalancing.empty:
        print(f"\n" + "-" * 100)
        print(f"POSITIONS REQUIRING REBALANCING (>{threshold_pct}% difference)")
        print("-" * 100)
        print(f"{'Symbol':<20} {'Current':>15} {'Desired':>15} {'Difference':>15} {'% Diff':>10}")
        print("-" * 100)
        
        for _, row in needs_rebalancing.iterrows():
            symbol = row['symbol']
            current = row['current_notional']
            desired = row['desired_notional']
            diff = row['difference']
            pct_diff = row['pct_difference']
            
            print(f"{symbol:<20} ${current:>14,.2f} ${desired:>14,.2f} ${diff:>14,.2f} {pct_diff:>9.1f}%")
    else:
        print(f"\n✓ No positions require rebalancing (all within {threshold_pct}% threshold)")
    
    # All positions summary
    print(f"\n" + "-" * 100)
    print("ALL POSITIONS")
    print("-" * 100)
    print(f"{'Symbol':<20} {'Current':>15} {'Desired':>15} {'Difference':>15} {'% Diff':>10}")
    print("-" * 100)
    
    for _, row in comparison_df.iterrows():
        symbol = row['symbol']
        current = row['current_notional']
        desired = row['desired_notional']
        diff = row['difference']
        pct_diff = row['pct_difference']
        
        # Highlight rows that need rebalancing
        marker = "⚠" if abs(pct_diff) > threshold_pct else " "
        print(f"{marker} {symbol:<18} ${current:>14,.2f} ${desired:>14,.2f} ${diff:>14,.2f} {pct_diff:>9.1f}%")
    
    print("=" * 100)


def check_positions(weights, threshold_pct=5.0):
    """
    Main function to check and compare positions.
    
    Args:
        weights (dict): Dictionary mapping symbols to target weights
        threshold_pct (float): Percentage threshold for highlighting differences
    
    Returns:
        pd.DataFrame: Comparison dataframe
    """
    # Get current positions
    print("Fetching current positions...")
    current_notional = get_current_positions_notional()
    
    # Get account value
    print("Fetching account balance...")
    balance = ccxt_get_hyperliquid_balance()
    
    # Extract account value from perp margin summary
    perp_info = balance.get('perp', {}).get('info', {})
    margin_summary = perp_info.get('marginSummary', {})
    account_value = float(margin_summary.get('accountValue', 0))
    
    if account_value == 0:
        print("Warning: Account value is 0. Cannot calculate desired positions.")
        return None
    
    print(f"Account Value: ${account_value:,.2f}")
    
    # Get desired positions
    print("Calculating desired positions...")
    desired_notional = get_desired_positions_notional(weights, account_value)
    
    # Compare positions
    print("Comparing positions...")
    comparison_df = compare_positions(current_notional, desired_notional)
    
    # Print comparison
    print_position_comparison(comparison_df, threshold_pct)
    
    return comparison_df


if __name__ == "__main__":
    # Example usage with sample weights
    # In practice, these weights would come from calc_weights() function
    example_weights = {
        'BTC/USD:USD': 0.30,
        'ETH/USD:USD': 0.25,
        'SOL/USD:USD': 0.20,
        'MATIC/USD:USD': 0.15,
        'AVAX/USD:USD': 0.10,
    }
    
    print("Example: Checking positions with sample weights")
    print("=" * 100)
    print("\nTarget Weights:")
    for symbol, weight in example_weights.items():
        print(f"  {symbol}: {weight:.1%}")
    
    try:
        comparison = check_positions(example_weights, threshold_pct=5.0)
        
        if comparison is not None:
            # Save to CSV
            output_file = "position_comparison.csv"
            comparison.to_csv(output_file, index=False)
            print(f"\n✓ Comparison saved to: {output_file}")
            
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
