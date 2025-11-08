"""
Fee Yield Factor Strategy

Strategy: Long coins with highest fee yield, short coins with lowest fee yield
Fee Yield: Annual fees generated / Market Cap (%)

Top performers (Nov 2025):
- LDO (Lido): 108.91%
- SUSHI: 62.01%
- UNI (Uniswap): 48.03%

Key Insight: Protocols generating high fees relative to market cap provide
better value capture for token holders.
"""

import pandas as pd
import numpy as np
import os


def strategy_defi_fee_yield(
    historical_data,
    symbols,
    notional,
    rebalance_days=7,
    top_n=10,
    bottom_n=10,
    volatility_window=30,
    long_allocation=0.5,
    short_allocation=0.5,
    weighting_method="risk_parity",
):
    """
    DeFi Fee Yield factor strategy - Long high fee yield, Short low fee yield.
    
    Args:
        historical_data (dict): Dictionary of symbol -> DataFrame with OHLCV data
        symbols (list): List of tradeable symbols
        notional (float): Total notional to allocate
        rebalance_days (int): Rebalancing frequency in days (default: 7)
        top_n (int): Number of long positions (default: 10)
        bottom_n (int): Number of short positions (default: 10)
        volatility_window (int): Days for volatility calculation (default: 30)
        long_allocation (float): Allocation to long side (default: 0.5)
        short_allocation (float): Allocation to short side (default: 0.5)
        weighting_method (str): 'risk_parity' or 'equal_weight' (default: risk_parity)
    
    Returns:
        dict: Dictionary mapping symbols to target notional values (positive=long, negative=short)
    """
    print("\n" + "=" * 80)
    print("DEFI FEE YIELD FACTOR STRATEGY")
    print("=" * 80)
    print(f"Parameters: top_n={top_n}, bottom_n={bottom_n}, rebalance={rebalance_days}d, weighting={weighting_method}")
    
    # Load latest fee yield signals
    signal_file = '/workspace/signals/defi_factor_fee_yield_signals.csv'
    if not os.path.exists(signal_file):
        print(f"\n⚠️ Fee yield signals not found: {signal_file}")
        print("  Run: python3 signals/calc_comprehensive_defi_factors.py")
        return {}
    
    try:
        signals_df = pd.read_csv(signal_file)
    except Exception as e:
        print(f"\n⚠️ Error loading fee yield signals: {e}")
        return {}
    
    print(f"\nLoaded {len(signals_df)} coins with fee yield data")
    print(f"Date: {signals_df['date'].iloc[0] if 'date' in signals_df.columns else 'unknown'}")
    
    # Filter for valid data
    signals_df = signals_df[signals_df['fee_yield_pct'].notna()].copy()
    
    # Map trading symbols (e.g., BTC/USD -> BTC)
    symbol_map = {}
    for sym in symbols:
        base = sym.split('/')[0] if '/' in sym else sym
        symbol_map[base] = sym
    
    # Filter to tradeable symbols
    signals_df['trading_symbol'] = signals_df['symbol'].map(symbol_map)
    signals_df = signals_df[signals_df['trading_symbol'].notna()].copy()
    
    print(f"Found {len(signals_df)} tradeable coins with fee yield data")
    
    if len(signals_df) < (top_n + bottom_n):
        print(f"⚠️ Not enough coins ({len(signals_df)}) for top_{top_n} + bottom_{bottom_n}")
        return {}
    
    # Sort by fee yield
    signals_df = signals_df.sort_values('fee_yield_pct', ascending=False)
    
    # Select top and bottom
    top_fee_yield = signals_df.head(top_n).copy()
    bottom_fee_yield = signals_df.tail(bottom_n).copy()
    
    print(f"\nTop {top_n} Fee Yield (LONG):")
    for idx, row in top_fee_yield.iterrows():
        print(f"  {row['symbol']:10s} -> {row['trading_symbol']:12s}: {row['fee_yield_pct']:.2f}%")
    
    print(f"\nBottom {bottom_n} Fee Yield (SHORT):")
    for idx, row in bottom_fee_yield.iterrows():
        print(f"  {row['symbol']:10s} -> {row['trading_symbol']:12s}: {row['fee_yield_pct']:.2f}%")
    
    # Calculate volatilities for risk parity weighting
    volatilities = {}
    for symbol in list(top_fee_yield['trading_symbol']) + list(bottom_fee_yield['trading_symbol']):
        if symbol in historical_data:
            df = historical_data[symbol]
            if len(df) >= volatility_window and 'close' in df.columns:
                returns = df['close'].pct_change().dropna()
                if len(returns) >= volatility_window:
                    vol = returns.tail(volatility_window).std()
                    volatilities[symbol] = vol if vol > 0 else 0.01
    
    # Allocate capital
    positions = {}
    
    # Long positions (high fee yield)
    long_notional = notional * long_allocation
    if weighting_method == "risk_parity" and volatilities:
        # Risk parity: inverse volatility weighting
        long_symbols = list(top_fee_yield['trading_symbol'])
        long_inv_vols = {sym: 1.0 / volatilities.get(sym, 0.01) for sym in long_symbols if sym in volatilities}
        
        if long_inv_vols:
            total_inv_vol = sum(long_inv_vols.values())
            for sym, inv_vol in long_inv_vols.items():
                weight = inv_vol / total_inv_vol
                positions[sym] = long_notional * weight
                print(f"  LONG {sym}: ${positions[sym]:,.2f} (risk parity weight: {weight:.4f})")
    else:
        # Equal weight
        long_symbols = list(top_fee_yield['trading_symbol'])
        for sym in long_symbols:
            positions[sym] = long_notional / len(long_symbols)
            print(f"  LONG {sym}: ${positions[sym]:,.2f} (equal weight)")
    
    # Short positions (low fee yield)
    short_notional = notional * short_allocation
    if weighting_method == "risk_parity" and volatilities:
        # Risk parity: inverse volatility weighting
        short_symbols = list(bottom_fee_yield['trading_symbol'])
        short_inv_vols = {sym: 1.0 / volatilities.get(sym, 0.01) for sym in short_symbols if sym in volatilities}
        
        if short_inv_vols:
            total_inv_vol = sum(short_inv_vols.values())
            for sym, inv_vol in short_inv_vols.items():
                weight = inv_vol / total_inv_vol
                positions[sym] = -1 * short_notional * weight  # Negative for short
                print(f"  SHORT {sym}: ${abs(positions[sym]):,.2f} (risk parity weight: {weight:.4f})")
    else:
        # Equal weight
        short_symbols = list(bottom_fee_yield['trading_symbol'])
        for sym in short_symbols:
            positions[sym] = -1 * short_notional / len(short_symbols)  # Negative for short
            print(f"  SHORT {sym}: ${abs(positions[sym]):,.2f} (equal weight)")
    
    print(f"\n✅ Generated {len(positions)} positions (Long: {len([p for p in positions.values() if p > 0])}, Short: {len([p for p in positions.values() if p < 0])})")
    print("=" * 80)
    
    return positions
