"""
Market Regime Detection for Strategy Filtering

This module provides regime detection capabilities to enable/disable strategies
based on market conditions. Primary use case: Only activate bear market strategies
during confirmed bear regimes.

Regime Definition:
- Bull Market: 50-day MA > 200-day MA on BTC
- Bear Market: 50-day MA < 200-day MA on BTC
"""

import pandas as pd
import numpy as np
from datetime import datetime


def detect_market_regime(historical_data, reference_symbol="BTC/USD"):
    """
    Detect current market regime based on moving average crossover.
    
    Uses the 50-day vs 200-day moving average on BTC as the primary regime indicator.
    This is a widely-used trend identification method in traditional finance.
    
    Args:
        historical_data (dict): Dictionary mapping symbols to DataFrames with OHLCV data
        reference_symbol (str): Symbol to use for regime detection (default: "BTC/USD")
    
    Returns:
        dict: Regime information containing:
            - regime (str): "bull" or "bear"
            - ma_50 (float): Current 50-day moving average
            - ma_200 (float): Current 200-day moving average
            - price (float): Current price
            - confidence (str): "high" or "low" based on MA separation
            - days_in_regime (int): Number of days since last regime change
    """
    print("\n" + "=" * 80)
    print("MARKET REGIME DETECTION")
    print("=" * 80)
    
    # Get BTC data
    if reference_symbol not in historical_data:
        print(f"  ??  Warning: {reference_symbol} not found in historical data")
        print(f"  Available symbols: {', '.join(list(historical_data.keys())[:5])}...")
        
        # Fallback: try variations
        for alt_symbol in ["BTC-USD", "BTCUSD", "BTC"]:
            if alt_symbol in historical_data:
                print(f"  Using alternative symbol: {alt_symbol}")
                reference_symbol = alt_symbol
                break
        else:
            print(f"  ??  Could not find BTC data - defaulting to BEAR regime (safe mode)")
            return {
                "regime": "bear",
                "ma_50": None,
                "ma_200": None,
                "price": None,
                "confidence": "low",
                "days_in_regime": 0,
                "error": "Reference symbol not found"
            }
    
    btc_data = historical_data[reference_symbol].copy()
    
    # Ensure data is sorted by date
    btc_data = btc_data.sort_values("date").reset_index(drop=True)
    
    # Check if we have enough data
    if len(btc_data) < 200:
        print(f"  ??  Warning: Only {len(btc_data)} days of BTC data (need 200 for 200-day MA)")
        print(f"  Defaulting to BEAR regime (safe mode)")
        return {
            "regime": "bear",
            "ma_50": None,
            "ma_200": None,
            "price": None,
            "confidence": "low",
            "days_in_regime": 0,
            "error": "Insufficient data"
        }
    
    # Calculate moving averages
    btc_data["ma_50"] = btc_data["close"].rolling(window=50).mean()
    btc_data["ma_200"] = btc_data["close"].rolling(window=200).mean()
    
    # Get latest values
    latest = btc_data.iloc[-1]
    price = latest["close"]
    ma_50 = latest["ma_50"]
    ma_200 = latest["ma_200"]
    
    if pd.isna(ma_50) or pd.isna(ma_200):
        print(f"  ??  Warning: Moving averages could not be calculated")
        print(f"  Defaulting to BEAR regime (safe mode)")
        return {
            "regime": "bear",
            "ma_50": None,
            "ma_200": None,
            "price": price,
            "confidence": "low",
            "days_in_regime": 0,
            "error": "MA calculation failed"
        }
    
    # Determine regime: bull if 50-day MA > 200-day MA
    regime = "bull" if ma_50 > ma_200 else "bear"
    
    # Calculate confidence based on MA separation
    # High confidence = MAs are well-separated (>5% apart)
    # Low confidence = MAs are close together (<5% apart)
    ma_diff_pct = abs(ma_50 - ma_200) / ma_200 * 100
    confidence = "high" if ma_diff_pct > 5 else "low"
    
    # Calculate days in current regime
    # Look backwards for last crossover
    btc_data["regime_bull"] = btc_data["ma_50"] > btc_data["ma_200"]
    current_regime_bool = btc_data["regime_bull"].iloc[-1]
    
    days_in_regime = 0
    for i in range(len(btc_data) - 1, -1, -1):
        if pd.notna(btc_data["regime_bull"].iloc[i]):
            if btc_data["regime_bull"].iloc[i] == current_regime_bool:
                days_in_regime += 1
            else:
                break
        else:
            break
    
    # Print regime information
    print(f"\nReference Symbol: {reference_symbol}")
    print(f"  Date: {latest['date'].strftime('%Y-%m-%d')}")
    print(f"  Price: ${price:,.2f}")
    print(f"  50-day MA: ${ma_50:,.2f}")
    print(f"  200-day MA: ${ma_200:,.2f}")
    print(f"  MA Separation: {ma_diff_pct:.2f}%")
    print(f"\n  ?? REGIME: {regime.upper()}")
    print(f"  Confidence: {confidence.upper()}")
    print(f"  Days in regime: {days_in_regime}")
    
    if confidence == "low":
        print(f"\n  ??  Low confidence: MAs are close together ({ma_diff_pct:.2f}%)")
        print(f"      Regime may be transitioning")
    
    print("=" * 80)
    
    return {
        "regime": regime,
        "ma_50": ma_50,
        "ma_200": ma_200,
        "price": price,
        "confidence": confidence,
        "days_in_regime": days_in_regime,
        "ma_diff_pct": ma_diff_pct,
        "reference_symbol": reference_symbol,
        "date": latest["date"]
    }


def should_activate_strategy(regime_info, strategy_type="bear_only"):
    """
    Determine if a strategy should be activated based on regime.
    
    Args:
        regime_info (dict): Regime information from detect_market_regime()
        strategy_type (str): Strategy activation type:
            - "bear_only": Only activate in bear markets
            - "bull_only": Only activate in bull markets
            - "always": Always activate (no filter)
    
    Returns:
        tuple: (should_activate (bool), reason (str))
    """
    if strategy_type == "always":
        return True, "No regime filter applied"
    
    regime = regime_info.get("regime", "bear")  # Default to bear (safe mode)
    confidence = regime_info.get("confidence", "low")
    days_in_regime = regime_info.get("days_in_regime", 0)
    
    if strategy_type == "bear_only":
        if regime == "bear":
            # Activate in bear markets
            if confidence == "high" and days_in_regime >= 5:
                return True, f"Bear market confirmed ({days_in_regime} days, high confidence)"
            elif confidence == "high":
                return True, f"Bear market confirmed (high confidence, but only {days_in_regime} days)"
            else:
                return True, f"Bear market (low confidence: MAs close together)"
        else:
            return False, f"Bull market detected - strategy inactive (kurtosis mean reversion is bear-market only)"
    
    elif strategy_type == "bull_only":
        if regime == "bull":
            if confidence == "high" and days_in_regime >= 5:
                return True, f"Bull market confirmed ({days_in_regime} days, high confidence)"
            elif confidence == "high":
                return True, f"Bull market confirmed (high confidence, but only {days_in_regime} days)"
            else:
                return True, f"Bull market (low confidence: MAs close together)"
        else:
            return False, f"Bear market detected - strategy inactive (bull-market only)"
    
    return False, f"Unknown strategy type: {strategy_type}"


def get_volatility_regime(historical_data, reference_symbol="BTC/USD", window=30):
    """
    Detect volatility regime (high vs low).
    
    Args:
        historical_data (dict): Dictionary mapping symbols to DataFrames with OHLCV data
        reference_symbol (str): Symbol to use for regime detection (default: "BTC/USD")
        window (int): Rolling window for volatility calculation (default: 30 days)
    
    Returns:
        dict: Volatility regime information
    """
    if reference_symbol not in historical_data:
        return {
            "vol_regime": "unknown",
            "volatility": None,
            "vol_percentile": None,
            "error": "Reference symbol not found"
        }
    
    btc_data = historical_data[reference_symbol].copy()
    btc_data = btc_data.sort_values("date").reset_index(drop=True)
    
    # Calculate returns
    btc_data["daily_return"] = btc_data["close"].pct_change()
    
    # Calculate rolling volatility (annualized)
    btc_data["volatility"] = btc_data["daily_return"].rolling(window=window).std() * np.sqrt(365)
    
    # Get current volatility
    current_vol = btc_data["volatility"].iloc[-1]
    
    if pd.isna(current_vol):
        return {
            "vol_regime": "unknown",
            "volatility": None,
            "vol_percentile": None,
            "error": "Volatility calculation failed"
        }
    
    # Calculate historical percentile
    vol_percentile = (btc_data["volatility"].dropna() < current_vol).mean() * 100
    
    # Define regime: high if above 60th percentile, low if below
    vol_regime = "high" if vol_percentile > 60 else "low"
    
    return {
        "vol_regime": vol_regime,
        "volatility": current_vol,
        "vol_percentile": vol_percentile,
        "window": window
    }
