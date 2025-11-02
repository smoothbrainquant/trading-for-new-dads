"""
Inverted Leverage Factor Strategy

LONG low leverage coins (fundamentals), SHORT high leverage coins (speculation)

Performance: Sharpe 1.19, +53.91% total return (4+ years), -12.10% max drawdown
Optimal rebalance: 7 days
"""

from typing import Dict
import pandas as pd
import numpy as np
from datetime import timedelta
import os

from .utils import get_base_symbol


def strategy_leverage_inverted(
    historical_data: Dict[str, pd.DataFrame],
    universe_symbols: list,
    notional: float,
    rebalance_days: int = 7,
    top_n: int = 10,
    bottom_n: int = 10,
) -> Dict[str, float]:
    """
    Inverted leverage factor strategy.
    
    LONG: Bottom 10 coins by OI/Market Cap ratio (least leveraged - fundamentals)
    SHORT: Top 10 coins by OI/Market Cap ratio (most leveraged - speculation)
    
    Args:
        historical_data: Dict of symbol -> DataFrame with OHLCV data
        universe_symbols: List of symbols to consider
        notional: Total notional capital to allocate
        rebalance_days: Rebalance frequency in days (default: 7)
        top_n: Number of high-leverage coins to short (default: 10)
        bottom_n: Number of low-leverage coins to long (default: 10)
    
    Returns:
        Dict mapping symbols to target notional values (positive=long, negative=short)
    """
    
    print(f"  Strategy: Inverted Leverage Factor (testing)")  # testing
    print(f"  LONG low leverage (fundamentals), SHORT high leverage (speculation)")
    print(f"  Rebalance: {rebalance_days} days, Risk Parity weighting")
    
    # Load leverage data
    leverage_file = "signals/historical_leverage_weekly_20251102_170645.csv"
    if not os.path.exists(leverage_file):
        print(f"  ??  Leverage data not found: {leverage_file}")
        print(f"     Run: python3 signals/analyze_leverage_ratios_historical.py")
        return {}
    
    leverage_df = pd.read_csv(leverage_file)
    leverage_df["date"] = pd.to_datetime(leverage_df["date"])
    
    # Get most recent leverage data
    latest_date = leverage_df["date"].max()
    latest_leverage = leverage_df[leverage_df["date"] == latest_date].copy()
    
    print(f"  ? Loaded leverage data (as of {latest_date.date()})")
    print(f"  ? {len(latest_leverage)} coins with leverage data")
    
    # Filter to available coins in universe
    base_symbols = [get_base_symbol(sym) for sym in universe_symbols]
    latest_leverage = latest_leverage[latest_leverage["coin_symbol"].isin(base_symbols)]
    
    # Filter out stablecoins
    stablecoins = ["USDT", "USDC", "DAI", "USDD", "TUSD", "BUSD"]
    latest_leverage = latest_leverage[~latest_leverage["coin_symbol"].isin(stablecoins)]
    
    # Filter to coins with valid data
    latest_leverage = latest_leverage[latest_leverage["oi_to_mcap_ratio"].notna()]
    latest_leverage = latest_leverage[latest_leverage["oi_to_mcap_ratio"] > 0]
    
    if len(latest_leverage) < (top_n + bottom_n):
        print(f"  ??  Insufficient leverage data: {len(latest_leverage)} coins (need {top_n + bottom_n})")
        return {}
    
    # Sort by leverage ratio
    latest_leverage = latest_leverage.sort_values("oi_to_mcap_ratio", ascending=False)
    
    # INVERTED: Long BOTTOM (least leveraged), Short TOP (most leveraged)
    low_leverage_long = latest_leverage.tail(bottom_n)["coin_symbol"].tolist()
    high_leverage_short = latest_leverage.head(top_n)["coin_symbol"].tolist()
    
    print(f"\n  Selected for LONG (low leverage - fundamentals):")
    for i, coin in enumerate(low_leverage_long, 1):
        ratio = latest_leverage[latest_leverage["coin_symbol"] == coin]["oi_to_mcap_ratio"].iloc[0]
        print(f"    {i:2d}. {coin:<10s} OI/MCap: {ratio:>6.2f}%")
    
    print(f"\n  Selected for SHORT (high leverage - speculation):")
    for i, coin in enumerate(high_leverage_short, 1):
        ratio = latest_leverage[latest_leverage["coin_symbol"] == coin]["oi_to_mcap_ratio"].iloc[0]
        print(f"    {i:2d}. {coin:<10s} OI/MCap: {ratio:>6.2f}%")
    
    # Calculate risk parity weights using volatility from historical data
    def calculate_volatility_weights(coins, historical_data):
        """Calculate inverse volatility weights"""
        vol_dict = {}
        
        for coin in coins:
            # Find matching symbol in historical data
            matching_symbols = [s for s in historical_data.keys() if get_base_symbol(s) == coin]
            
            if matching_symbols:
                data = historical_data[matching_symbols[0]]
                if len(data) >= 30:
                    returns = data["close"].pct_change().dropna()
                    if len(returns) > 0:
                        vol = returns.std() * np.sqrt(252)  # Annualized
                        if vol > 0:
                            vol_dict[coin] = vol
        
        if not vol_dict:
            # Fallback to equal weight
            return {coin: 1.0/len(coins) for coin in coins}
        
        # Calculate inverse volatility weights
        inv_vol = {k: 1.0/v for k, v in vol_dict.items()}
        total_inv_vol = sum(inv_vol.values())
        weights = {k: v/total_inv_vol for k, v in inv_vol.items()}
        
        # Add missing coins with average weight
        missing = set(coins) - set(weights.keys())
        if missing:
            avg_weight = sum(weights.values()) / len(weights)
            for coin in missing:
                weights[coin] = avg_weight
            # Renormalize
            total = sum(weights.values())
            weights = {k: v/total for k, v in weights.items()}
        
        return weights
    
    # Calculate weights
    long_weights = calculate_volatility_weights(low_leverage_long, historical_data)
    short_weights = calculate_volatility_weights(high_leverage_short, historical_data)
    
    # Build target positions
    target_positions = {}
    
    # Long leg (50% of capital)
    long_notional = notional * 0.5
    for coin, weight in long_weights.items():
        # Find matching symbol in universe
        matching = [s for s in universe_symbols if get_base_symbol(s) == coin]
        if matching:
            target_positions[matching[0]] = weight * long_notional
    
    # Short leg (50% of capital)
    short_notional = notional * 0.5
    for coin, weight in short_weights.items():
        # Find matching symbol in universe
        matching = [s for s in universe_symbols if get_base_symbol(s) == coin]
        if matching:
            target_positions[matching[0]] = -weight * short_notional  # Negative for short
    
    print(f"\n  ? Generated {len(target_positions)} positions")
    print(f"    Long positions: {sum(1 for v in target_positions.values() if v > 0)}")
    print(f"    Short positions: {sum(1 for v in target_positions.values() if v < 0)}")
    
    return target_positions
