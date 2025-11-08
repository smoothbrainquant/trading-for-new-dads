"""
Emission Yield Factor Strategy

Strategy: Short coins with highest emission yield, long coins with lowest emission yield
Emission Yield: Annual token emissions / Market Cap (%)

IMPORTANT: High emission yield = HIGH DILUTION = BAD for holders
- This factor represents COST, not benefit
- High emission = shorting candidate (value being diluted away)
- Low/zero emission = longing candidate (no dilution)

Top diluters (Nov 2025):
- PENDLE: 15.08% (emitting tokens worth 15% of market cap annually!)
- AAVE: 1.85%

Key Insight: Protocols with aggressive token emissions dilute holders.
Strategy inverted: SHORT high emitters, LONG low/no emitters.
"""

import pandas as pd
import numpy as np
import os


def strategy_defi_emission_yield(
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
    DeFi Emission Yield factor strategy - SHORT high emissions, LONG low emissions.
    
    INVERTED LOGIC: High emission yield is BAD (dilution), so we short it.
    
    Args:
        historical_data (dict): Dictionary of symbol -> DataFrame with OHLCV data
        symbols (list): List of tradeable symbols
        notional (float): Total notional to allocate
        rebalance_days (int): Rebalancing frequency in days (default: 7)
        top_n (int): Number of short positions (high emissions = bad)
        bottom_n (int): Number of long positions (low emissions = good)
        volatility_window (int): Days for volatility calculation (default: 30)
        long_allocation (float): Allocation to long side (default: 0.5)
        short_allocation (float): Allocation to short side (default: 0.5)
        weighting_method (str): 'risk_parity' or 'equal_weight' (default: risk_parity)
    
    Returns:
        dict: Dictionary mapping symbols to target notional values (positive=long, negative=short)
    """
    print("\n" + "=" * 80)
    print("DEFI EMISSION YIELD FACTOR STRATEGY")
    print("=" * 80)
    print(f"Parameters: top_n={top_n}, bottom_n={bottom_n}, rebalance={rebalance_days}d, weighting={weighting_method}")
    print("⚠️ INVERTED: SHORT high emitters (dilution), LONG low emitters (no dilution)")
    
    # Load latest emission yield signals
    signal_file = '/workspace/signals/defi_factor_emission_yield_signals.csv'
    if not os.path.exists(signal_file):
        print(f"\n⚠️ Emission yield signals not found: {signal_file}")
        print("  Run: python3 signals/calc_comprehensive_defi_factors.py")
        return {}
    
    try:
        signals_df = pd.read_csv(signal_file)
    except Exception as e:
        print(f"\n⚠️ Error loading emission yield signals: {e}")
        return {}
    
    print(f"\nLoaded {len(signals_df)} coins with emission yield data")
    print(f"Date: {signals_df['date'].iloc[0] if 'date' in signals_df.columns else 'unknown'}")
    
    # Filter for valid data
    signals_df = signals_df[signals_df['emission_yield_pct'].notna()].copy()
    
    # Map trading symbols (e.g., BTC/USD -> BTC)
    symbol_map = {}
    for sym in symbols:
        base = sym.split('/')[0] if '/' in sym else sym
        symbol_map[base] = sym
    
    # Filter to tradeable symbols
    signals_df['trading_symbol'] = signals_df['symbol'].map(symbol_map)
    signals_df = signals_df[signals_df['trading_symbol'].notna()].copy()
    
    print(f"Found {len(signals_df)} tradeable coins with emission yield data")
    
    if len(signals_df) < (top_n + bottom_n):
        print(f"⚠️ Not enough coins ({len(signals_df)}) for top_{top_n} + bottom_{bottom_n}")
        return {}
    
    # Sort by emission yield (DESCENDING: highest emissions first)
    signals_df = signals_df.sort_values('emission_yield_pct', ascending=False)
    
    # INVERTED: Top emissions = SHORT, Bottom emissions = LONG
    top_emitters = signals_df.head(top_n).copy()  # High emissions -> SHORT
    low_emitters = signals_df.tail(bottom_n).copy()  # Low emissions -> LONG
    
    print(f"\nTop {top_n} Emitters (SHORT - high dilution):")
    for idx, row in top_emitters.iterrows():
        print(f"  {row['symbol']:10s} -> {row['trading_symbol']:12s}: {row['emission_yield_pct']:.4f}% dilution")
    
    print(f"\nBottom {bottom_n} Emitters (LONG - low/no dilution):")
    for idx, row in low_emitters.iterrows():
        print(f"  {row['symbol']:10s} -> {row['trading_symbol']:12s}: {row['emission_yield_pct']:.4f}% dilution")
    
    # Calculate volatilities for risk parity weighting
    volatilities = {}
    for symbol in list(top_emitters['trading_symbol']) + list(low_emitters['trading_symbol']):
        if symbol in historical_data:
            df = historical_data[symbol]
            if len(df) >= volatility_window and 'close' in df.columns:
                returns = df['close'].pct_change().dropna()
                if len(returns) >= volatility_window:
                    vol = returns.tail(volatility_window).std()
                    volatilities[symbol] = vol if vol > 0 else 0.01
    
    # Allocate capital
    positions = {}
    
    # Long positions (LOW emissions = good, no dilution)
    long_notional = notional * long_allocation
    if weighting_method == "risk_parity" and volatilities:
        # Risk parity: inverse volatility weighting
        long_symbols = list(low_emitters['trading_symbol'])
        long_inv_vols = {sym: 1.0 / volatilities.get(sym, 0.01) for sym in long_symbols if sym in volatilities}
        
        if long_inv_vols:
            total_inv_vol = sum(long_inv_vols.values())
            for sym, inv_vol in long_inv_vols.items():
                weight = inv_vol / total_inv_vol
                positions[sym] = long_notional * weight
                print(f"  LONG {sym}: ${positions[sym]:,.2f} (risk parity weight: {weight:.4f})")
    else:
        # Equal weight
        long_symbols = list(low_emitters['trading_symbol'])
        for sym in long_symbols:
            positions[sym] = long_notional / len(long_symbols)
            print(f"  LONG {sym}: ${positions[sym]:,.2f} (equal weight)")
    
    # Short positions (HIGH emissions = bad, high dilution)
    short_notional = notional * short_allocation
    if weighting_method == "risk_parity" and volatilities:
        # Risk parity: inverse volatility weighting
        short_symbols = list(top_emitters['trading_symbol'])
        short_inv_vols = {sym: 1.0 / volatilities.get(sym, 0.01) for sym in short_symbols if sym in volatilities}
        
        if short_inv_vols:
            total_inv_vol = sum(short_inv_vols.values())
            for sym, inv_vol in short_inv_vols.items():
                weight = inv_vol / total_inv_vol
                positions[sym] = -1 * short_notional * weight  # Negative for short
                print(f"  SHORT {sym}: ${abs(positions[sym]):,.2f} (risk parity weight: {weight:.4f})")
    else:
        # Equal weight
        short_symbols = list(top_emitters['trading_symbol'])
        for sym in short_symbols:
            positions[sym] = -1 * short_notional / len(short_symbols)  # Negative for short
            print(f"  SHORT {sym}: ${abs(positions[sym]):,.2f} (equal weight)")
    
    print(f"\n✅ Generated {len(positions)} positions (Long: {len([p for p in positions.values() if p > 0])}, Short: {len([p for p in positions.values() if p < 0])})")
    print("=" * 80)
    
    return positions
