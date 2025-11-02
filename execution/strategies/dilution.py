"""
Dilution Factor Strategy

# testing

Strategy: Long coins with lowest dilution velocity, short coins with highest dilution velocity
Dilution Velocity: Rate of token unlock measured as % of max supply unlocked per year

Performance (2021-2025 backtest):
- Monthly rebalancing: +2,826% return, Sharpe 1.07 (optimal)
- Weekly rebalancing: +2,481% return, Sharpe 1.01

Key Insight: Coins with aggressive unlock schedules (high dilution) underperform
"""

import pandas as pd
import numpy as np
import os


def strategy_dilution(
    historical_data,
    symbols,
    notional,
    rebalance_days=7,
    lookback_months=12,
    top_n=10,
    volatility_window=90,
    long_allocation=0.5,
    short_allocation=0.5,
):
    """
    Dilution factor strategy - Long low dilution, Short high dilution.
    
    # testing
    
    Args:
        historical_data (dict): Dictionary of symbol -> DataFrame with OHLCV data
        symbols (list): List of tradeable symbols
        notional (float): Total notional to allocate
        rebalance_days (int): Rebalancing frequency in days (default: 7, optimal per analysis)
        lookback_months (int): Months to lookback for dilution calculation (default: 12)
        top_n (int): Number of long and short positions (default: 10)
        volatility_window (int): Days for volatility calculation (default: 90)
        long_allocation (float): Allocation to long side (default: 0.5)
        short_allocation (float): Allocation to short side (default: 0.5)
    
    Returns:
        dict: Dictionary mapping symbols to target notional values (positive=long, negative=short)
    """
    print("\n" + "=" * 80)
    print("DILUTION FACTOR STRATEGY")
    print("=" * 80)
    print(f"Parameters: top_n={top_n}, lookback={lookback_months}m, rebalance={rebalance_days}d")
    print("# testing new dilution factor")
    
    # Load historical dilution data
    dilution_file = '/workspace/crypto_dilution_historical_2021_2025.csv'
    if not os.path.exists(dilution_file):
        print(f"\n? Dilution data not found: {dilution_file}")
        print("  Run: python3 data/scripts/analyze_historical_dilution.py")
        return {}
    
    try:
        dilution_df = pd.read_csv(dilution_file)
        dilution_df['date'] = pd.to_datetime(dilution_df['date'])
    except Exception as e:
        print(f"\n? Error loading dilution data: {e}")
        return {}
    
    # Get most recent dilution snapshot
    latest_date = dilution_df['date'].max()
    lookback_start = latest_date - pd.DateOffset(months=lookback_months)
    
    print(f"\nCalculating dilution velocity from {lookback_start.date()} to {latest_date.date()}")
    
    # Calculate dilution velocity for each coin
    dilution_velocities = {}
    
    for symbol in dilution_df['Symbol'].unique():
        coin_data = dilution_df[
            (dilution_df['Symbol'] == symbol) &
            (dilution_df['date'] >= lookback_start)
        ].sort_values('date')
        
        if len(coin_data) < 2:
            continue
        
        first = coin_data.iloc[0]
        last = coin_data.iloc[-1]
        
        # Skip if no max supply defined
        if pd.isna(last['max_supply']) or last['max_supply'] == 0:
            continue
        
        # Calculate dilution velocity (% of max supply per year)
        days_elapsed = (last['date'] - first['date']).days
        if days_elapsed == 0:
            continue
        
        years_elapsed = days_elapsed / 365.25
        circ_pct_change = last['circulating_pct'] - first['circulating_pct']
        dilution_velocity = circ_pct_change / years_elapsed if years_elapsed > 0 else 0
        
        dilution_velocities[symbol] = {
            'velocity': dilution_velocity,
            'circ_pct': last['circulating_pct'],
            'market_cap': last.get('Market Cap', 0),
        }
    
    if not dilution_velocities:
        print("\n? No dilution data available for tradeable symbols")
        return {}
    
    print(f"? Calculated dilution velocity for {len(dilution_velocities)} coins")
    
    # Sort by dilution velocity
    sorted_coins = sorted(dilution_velocities.items(), key=lambda x: x[1]['velocity'])
    
    # Select long (low dilution) and short (high dilution) candidates
    long_candidates = sorted_coins[:top_n]
    short_candidates = sorted_coins[-top_n:]
    
    print(f"\n?? TOP {top_n} LOW DILUTION (LONG):")
    for i, (symbol, data) in enumerate(long_candidates[:5], 1):
        print(f"  {i}. {symbol:8s}: {data['velocity']:>6.2f}% per year, {data['circ_pct']:>6.1f}% circulating")
    
    print(f"\n?? TOP {top_n} HIGH DILUTION (SHORT):")
    for i, (symbol, data) in enumerate(reversed(short_candidates[-5:]), 1):
        print(f"  {i}. {symbol:8s}: {data['velocity']:>6.2f}% per year, {data['circ_pct']:>6.1f}% circulating")
    
    # Calculate volatilities for risk parity weighting
    def calculate_volatility(symbol):
        """Calculate annualized volatility for a symbol."""
        # Match symbol format (handle both "BTC" and "BTC/USDC:USDC")
        base_symbol = symbol.split('/')[0] if '/' in symbol else symbol
        
        # Try to find matching data
        for key in historical_data.keys():
            if base_symbol in key or key.split('/')[0] == base_symbol:
                data = historical_data[key]
                if len(data) < volatility_window:
                    continue
                
                returns = data['close'].pct_change().dropna()
                if len(returns) < 20:
                    continue
                
                recent_returns = returns.tail(volatility_window)
                vol = recent_returns.std() * np.sqrt(365)
                return vol
        
        return None
    
    # Calculate weights using inverse volatility (risk parity)
    long_weights = {}
    for symbol, data in long_candidates:
        vol = calculate_volatility(symbol)
        if vol is not None and vol > 0:
            long_weights[symbol] = 1.0 / vol
    
    short_weights = {}
    for symbol, data in short_candidates:
        vol = calculate_volatility(symbol)
        if vol is not None and vol > 0:
            short_weights[symbol] = 1.0 / vol
    
    # Normalize weights
    long_total = sum(long_weights.values())
    short_total = sum(short_weights.values())
    
    if long_total > 0:
        long_weights = {s: w / long_total for s, w in long_weights.items()}
    if short_total > 0:
        short_weights = {s: w / short_total for s, w in short_weights.items()}
    
    # Allocate notional
    long_notional = notional * long_allocation
    short_notional = notional * short_allocation
    
    positions = {}
    
    # Long positions
    for symbol, weight in long_weights.items():
        # Find matching trading symbol
        for trading_symbol in symbols:
            if symbol in trading_symbol or trading_symbol.split('/')[0] == symbol:
                positions[trading_symbol] = weight * long_notional
                break
    
    # Short positions
    for symbol, weight in short_weights.items():
        # Find matching trading symbol
        for trading_symbol in symbols:
            if symbol in trading_symbol or trading_symbol.split('/')[0] == symbol:
                positions[trading_symbol] = -weight * short_notional
                break
    
    print(f"\n? Generated {len(positions)} positions ({len([p for p in positions.values() if p > 0])} long, {len([p for p in positions.values() if p < 0])} short)")
    print(f"  Total allocated: ${sum(abs(p) for p in positions.values()):,.2f} / ${notional:,.2f}")
    print("=" * 80)
    
    return positions
