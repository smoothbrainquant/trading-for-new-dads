"""
Kurtosis Factor Strategy Implementation

Implements a kurtosis factor strategy for crypto:
- Calculates rolling kurtosis of daily returns for all cryptocurrencies
- Ranks cryptocurrencies by kurtosis values
- Creates long/short portfolios based on kurtosis rankings:
  * Mean Reversion: Long low kurtosis (stable), Short high kurtosis (unstable)
  * Momentum: Long high kurtosis (volatile), Short low kurtosis (stable)
- Uses equal-weight or risk parity weighting
- Rebalances periodically

Kurtosis hypothesis: Kurtosis measures tail-fatness of return distributions.
High kurtosis = fat tails, prone to extreme moves
Low kurtosis = thin tails, more stable returns
"""

import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta


def strategy_kurtosis(
    historical_data,
    symbols,
    strategy_notional,
    kurtosis_window=30,
    volatility_window=30,
    rebalance_days=14,
    long_percentile=20,
    short_percentile=80,
    strategy_type="momentum",
    weighting_method="risk_parity",
    long_allocation=0.5,
    short_allocation=0.5,
    max_positions=10,
):
    """
    Kurtosis factor strategy.
    
    Args:
        historical_data (dict): Dictionary mapping symbols to DataFrames with OHLCV data
        symbols (list): List of symbols to consider
        strategy_notional (float): Total notional to allocate
        kurtosis_window (int): Window for kurtosis calculation (default: 30 days)
        volatility_window (int): Window for volatility calculation (default: 30 days)
        rebalance_days (int): Rebalancing frequency in days (default: 14, optimal per backtest)
        long_percentile (int): Percentile threshold for long positions (default: 20)
        short_percentile (int): Percentile threshold for short positions (default: 80)
        strategy_type (str): Strategy type ('mean_reversion' or 'momentum', default: 'momentum')
        weighting_method (str): Weighting method ('equal_weight' or 'risk_parity')
        long_allocation (float): Allocation to long side (default: 0.5)
        short_allocation (float): Allocation to short side (default: 0.5)
        max_positions (int): Maximum positions per side (default: 10)
    
    Returns:
        dict: Dictionary mapping symbols to notional positions (positive = long, negative = short)
    """
    print("\n" + "-" * 80)
    print("KURTOSIS FACTOR STRATEGY")
    print("-" * 80)
    print(f"  Strategy type: {strategy_type}")
    print(f"  Kurtosis window: {kurtosis_window} days")
    print(f"  Volatility window: {volatility_window} days")
    print(f"  Rebalance frequency: {rebalance_days} days")
    print(f"  Long percentile: {long_percentile}%")
    print(f"  Short percentile: {short_percentile}%")
    print(f"  Weighting: {weighting_method}")
    print(f"  Long allocation: {long_allocation*100:.1f}%")
    print(f"  Short allocation: {short_allocation*100:.1f}%")
    print(f"  Max positions per side: {max_positions}")
    
    try:
        # Step 1: Calculate kurtosis for all symbols
        kurtosis_results = []
        
        for symbol in symbols:
            if symbol not in historical_data:
                continue
            
            df = historical_data[symbol].copy()
            if len(df) < kurtosis_window + 10:
                continue
            
            # Sort by timestamp
            df = df.sort_values("timestamp").reset_index(drop=True)
            
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
        
        # Step 2: Rank by kurtosis and select long/short
        kurtosis_df["percentile"] = kurtosis_df["kurtosis"].rank(pct=True) * 100
        
        if strategy_type == "mean_reversion":
            # Mean Reversion: Long low kurtosis (stable), Short high kurtosis (unstable)
            long_df = kurtosis_df[kurtosis_df["percentile"] <= long_percentile].copy()
            short_df = kurtosis_df[kurtosis_df["percentile"] >= short_percentile].copy()
            
            # Limit positions - take most extreme
            if len(long_df) > max_positions:
                long_df = long_df.nsmallest(max_positions, "kurtosis")
            if len(short_df) > max_positions:
                short_df = short_df.nlargest(max_positions, "kurtosis")
        
        elif strategy_type == "momentum":
            # Momentum: Long high kurtosis (volatile), Short low kurtosis (stable)
            long_df = kurtosis_df[kurtosis_df["percentile"] >= short_percentile].copy()
            short_df = kurtosis_df[kurtosis_df["percentile"] <= long_percentile].copy()
            
            # Limit positions - take most extreme
            if len(long_df) > max_positions:
                long_df = long_df.nlargest(max_positions, "kurtosis")
            if len(short_df) > max_positions:
                short_df = short_df.nsmallest(max_positions, "kurtosis")
        
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
