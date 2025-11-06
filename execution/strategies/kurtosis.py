"""
Kurtosis Factor Strategy Implementation with Regime Filter

Implements a kurtosis factor strategy for crypto:
- Calculates rolling kurtosis of daily returns for all cryptocurrencies
- Ranks cryptocurrencies by kurtosis values
- Creates long/short portfolios based on kurtosis rankings:
  * Mean Reversion: Long low kurtosis (stable), Short high kurtosis (unstable)
  * Momentum: Long high kurtosis (volatile), Short low kurtosis (stable)
- Uses equal-weight or risk parity weighting
- Rebalances periodically
- **REGIME FILTER**: Can be configured to only activate in specific market regimes

Kurtosis hypothesis: Kurtosis measures tail-fatness of return distributions.
High kurtosis = fat tails, prone to extreme moves
Low kurtosis = thin tails, more stable returns

**IMPORTANT**: Mean Reversion mode excels in BEAR MARKETS only:
- Bear/Low-Vol: +28% to +50% annualized (Sharpe 1.79)
- Bull markets: -25% to -90% annualized (Sharpe -2.01 to -1.22)
- Regime filter is STRONGLY RECOMMENDED for mean reversion mode
"""

import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta

# Import regime detection
try:
    from execution.strategies.regime_filter import detect_market_regime, should_activate_strategy
except ImportError:
    # Fallback if module not found
    def detect_market_regime(historical_data, reference_symbol="BTC/USD"):
        return {"regime": "bear", "confidence": "low", "days_in_regime": 0, "error": "regime_filter module not found"}
    
    def should_activate_strategy(regime_info, strategy_type="bear_only"):
        return True, "Regime filter not available - defaulting to active"


def strategy_kurtosis(
    historical_data,
    symbols,
    strategy_notional,
    kurtosis_window=30,
    volatility_window=30,
    rebalance_days=14,
    top_n=10,
    bottom_n=10,
    strategy_type="mean_reversion",  # Changed default to mean_reversion
    weighting_method="risk_parity",
    long_allocation=0.5,
    short_allocation=0.5,
    regime_filter="bear_only",  # regime filter (bear_only, bull_only, always)
    reference_symbol="BTC/USD",  # symbol for regime detection
):
    """
    Kurtosis factor strategy with regime-based activation.
    
    Args:
        historical_data (dict): Dictionary mapping symbols to DataFrames with OHLCV data
        symbols (list): List of symbols to consider
        strategy_notional (float): Total notional to allocate
        kurtosis_window (int): Window for kurtosis calculation (default: 30 days)
        volatility_window (int): Window for volatility calculation (default: 30 days)
        rebalance_days (int): Rebalancing frequency in days (default: 14, optimal per backtest)
        top_n (int): Number of positions for long side (default: 10)
        bottom_n (int): Number of positions for short side (default: 10)
        strategy_type (str): Strategy type:
            - 'mean_reversion': Long low kurtosis, Short high kurtosis (BEAR MARKET ONLY)
            - 'momentum': Long high kurtosis, Short low kurtosis
        weighting_method (str): Weighting method ('equal_weight' or 'risk_parity')
        long_allocation (float): Allocation to long side (default: 0.5)
        short_allocation (float): Allocation to short side (default: 0.5)
        regime_filter (str): Regime activation filter:
            - 'bear_only': Only activate in bear markets (RECOMMENDED for mean_reversion)
            - 'bull_only': Only activate in bull markets
            - 'always': Always active (no filter)
        reference_symbol (str): Symbol for regime detection (default: "BTC/USD")
    
    Returns:
        dict: Dictionary mapping symbols to notional positions (positive = long, negative = short)
              Returns empty dict {} if regime filter prevents activation
    """
    print("\n" + "-" * 80)
    print("KURTOSIS FACTOR STRATEGY WITH REGIME FILTER")
    print("-" * 80)
    print(f"  Strategy type: {strategy_type}")
    print(f"  Regime filter: {regime_filter}")
    print(f"  Kurtosis window: {kurtosis_window} days")
    print(f"  Volatility window: {volatility_window} days")
    print(f"  Rebalance frequency: {rebalance_days} days")
    print(f"  Top N (long): {top_n} positions")
    print(f"  Bottom N (short): {bottom_n} positions")
    print(f"  Weighting: {weighting_method}")
    print(f"  Long allocation: {long_allocation*100:.1f}%")
    print(f"  Short allocation: {short_allocation*100:.1f}%")
    
    # Warning for risky configurations
    if strategy_type == "mean_reversion" and regime_filter == "always":
        print("\n  ⚠️  WARNING: Mean reversion mode without regime filter!")
        print("  ⚠️  This strategy loses -25% to -90% annualized in bull markets!")
        print("  ⚠️  Strongly recommend setting regime_filter='bear_only'")
    
    try:
        # Step 0: Check market regime
        regime_info = detect_market_regime(historical_data, reference_symbol=reference_symbol)
        should_activate, reason = should_activate_strategy(regime_info, strategy_type=regime_filter)
        
        if not should_activate:
            print("\n" + "=" * 80)
            print("🛑 STRATEGY INACTIVE - REGIME FILTER")
            print("=" * 80)
            print(f"  Reason: {reason}")
            print(f"  Current regime: {regime_info.get('regime', 'unknown').upper()}")
            print(f"  Filter setting: {regime_filter}")
            print("\n  No positions will be generated.")
            print("  Strategy will remain flat (all capital in cash/stables).")
            print("=" * 80)
            return {}
        
        print("\n" + "=" * 80)
        print("✅ STRATEGY ACTIVE - REGIME FILTER PASSED")
        print("=" * 80)
        print(f"  {reason}")
        print(f"  Current regime: {regime_info.get('regime', 'unknown').upper()}")
        print(f"  Proceeding with position generation...")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n  ⚠️  Warning: Regime detection failed ({e})")
        if regime_filter != "always":
            print(f"  Defaulting to INACTIVE (safe mode when regime detection fails)")
            return {}
        else:
            print(f"  Filter set to 'always' - proceeding despite error")
    
    try:
        # Step 1: Calculate kurtosis for all symbols
        kurtosis_results = []
        
        for symbol in symbols:
            if symbol not in historical_data:
                continue
            
            df = historical_data[symbol].copy()
            if len(df) < kurtosis_window + 10:
                continue
            
            # Sort by date
            df = df.sort_values("date").reset_index(drop=True)
            
            # Calculate daily log returns
            df["daily_return"] = np.log(df["close"] / df["close"].shift(1))
            
            # Calculate rolling kurtosis using most recent window
            if len(df) >= kurtosis_window:
                recent_data = df.tail(kurtosis_window).copy()
                returns = recent_data["daily_return"].dropna()
                
                if len(returns) >= kurtosis_window - 5:  # Allow a few missing values
                    try:
                        # Fisher=True: excess kurtosis (normal = 0, leptokurtic > 0, platykurtic < 0)
                        kurt = stats.kurtosis(returns, fisher=True, nan_policy="omit")
                        
                        # Calculate volatility for risk parity weighting
                        volatility = returns.std() * np.sqrt(365)
                        
                        # Get latest price for reference
                        latest_price = df["close"].iloc[-1]
                        
                        kurtosis_results.append({
                            "symbol": symbol,
                            "kurtosis": kurt,
                            "volatility": volatility,
                            "price": latest_price,
                            "returns_mean": returns.mean(),
                            "returns_std": returns.std(),
                        })
                    except Exception as e:
                        # Skip symbols with calculation errors
                        continue
        
        if not kurtosis_results:
            print("  ⚠️  No symbols with valid kurtosis calculations")
            return {}
        
        # Convert to DataFrame for easier ranking
        kurtosis_df = pd.DataFrame(kurtosis_results)
        
        print(f"\n  Calculated kurtosis for {len(kurtosis_df)} symbols")
        print(f"  Kurtosis range: [{kurtosis_df['kurtosis'].min():.2f}, {kurtosis_df['kurtosis'].max():.2f}]")
        print(f"  Kurtosis mean: {kurtosis_df['kurtosis'].mean():.2f}")
        print(f"  Kurtosis median: {kurtosis_df['kurtosis'].median():.2f}")
        
        # Step 2: Sort by kurtosis and select top N and bottom N
        kurtosis_df = kurtosis_df.sort_values("kurtosis")
        
        if strategy_type == "mean_reversion":
            # Mean Reversion: Long bottom N (low kurtosis - stable), Short top N (high kurtosis - unstable)
            long_df = kurtosis_df.head(top_n).copy()
            short_df = kurtosis_df.tail(bottom_n).copy()
        
        elif strategy_type == "momentum":
            # Momentum: Long top N (high kurtosis - volatile), Short bottom N (low kurtosis - stable)
            long_df = kurtosis_df.tail(top_n).copy()
            short_df = kurtosis_df.head(bottom_n).copy()
        
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")
        
        print(f"\n  Selected {len(long_df)} long positions")
        print(f"  Selected {len(short_df)} short positions")
        
        if len(long_df) == 0 and len(short_df) == 0:
            print("  ⚠️  No positions selected")
            return {}
        
        # Step 3: Calculate weights
        positions = {}
        
        # Long positions
        if len(long_df) > 0:
            long_notional = strategy_notional * long_allocation
            
            if weighting_method == "equal_weight":
                weight_per_position = long_notional / len(long_df)
                for _, row in long_df.iterrows():
                    positions[row["symbol"]] = weight_per_position
            
            elif weighting_method == "risk_parity":
                # Weight inversely to volatility
                long_df["inv_vol"] = 1 / long_df["volatility"]
                total_inv_vol = long_df["inv_vol"].sum()
                for _, row in long_df.iterrows():
                    weight = (row["inv_vol"] / total_inv_vol) * long_notional
                    positions[row["symbol"]] = weight
            
            print(f"\n  Long positions (total: ${long_notional:,.2f}):")
            for symbol, notional in sorted(positions.items(), key=lambda x: x[1], reverse=True)[:10]:
                kurt_val = kurtosis_df[kurtosis_df["symbol"] == symbol]["kurtosis"].iloc[0]
                print(f"    {symbol}: ${notional:,.2f} (kurtosis: {kurt_val:.2f})")
            if len(positions) > 10:
                print(f"    ... and {len(positions) - 10} more")
        
        # Short positions
        if len(short_df) > 0:
            short_notional = strategy_notional * short_allocation
            
            if weighting_method == "equal_weight":
                weight_per_position = short_notional / len(short_df)
                for _, row in short_df.iterrows():
                    positions[row["symbol"]] = -weight_per_position  # Negative for short
            
            elif weighting_method == "risk_parity":
                # Weight inversely to volatility
                short_df["inv_vol"] = 1 / short_df["volatility"]
                total_inv_vol = short_df["inv_vol"].sum()
                for _, row in short_df.iterrows():
                    weight = (row["inv_vol"] / total_inv_vol) * short_notional
                    positions[row["symbol"]] = -weight  # Negative for short
            
            print(f"\n  Short positions (total: ${short_notional:,.2f}):")
            short_count = 0
            for symbol in sorted(positions.keys()):
                if positions[symbol] < 0:
                    if short_count < 10:
                        kurt_val = kurtosis_df[kurtosis_df["symbol"] == symbol]["kurtosis"].iloc[0]
                        print(f"    {symbol}: ${abs(positions[symbol]):,.2f} (kurtosis: {kurt_val:.2f})")
                    short_count += 1
            if short_count > 10:
                print(f"    ... and {short_count - 10} more")
        
        print(f"\n  Total positions: {len(positions)}")
        
        return positions
    
    except Exception as e:
        print(f"\n  ❌ Error in kurtosis strategy: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}
