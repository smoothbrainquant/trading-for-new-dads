"""
Volatility Factor Strategy Implementation

Implements the low volatility anomaly strategy for crypto:
- Calculates rolling volatility for all cryptocurrencies
- Long low volatility coins (stable), short high volatility coins (volatile)
- Uses equal-weight or risk parity weighting
- Rebalances periodically (3 days optimal based on backtesting)

This is a market-neutral strategy that captures the low-volatility anomaly.
Based on VOLATILITY_REBALANCE_PERIOD_ANALYSIS.md showing 3-day rebalancing
achieves the highest Sharpe ratio (1.407) and annualized return (41.77%).
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def strategy_volatility(
    historical_data,
    symbols,
    strategy_notional,
    volatility_window=30,
    rebalance_days=3,
    top_n=10,
    bottom_n=10,
    strategy_type="long_low_short_high",
    weighting_method="equal_weight",
    long_allocation=0.5,
    short_allocation=0.5,
):
    """
    Volatility factor strategy (Low Volatility Anomaly).
    
    Args:
        historical_data (dict): Dictionary mapping symbols to DataFrames with OHLCV data
        symbols (list): List of symbols to consider
        strategy_notional (float): Total notional to allocate
        volatility_window (int): Window for volatility calculation (default: 30 days)
        rebalance_days (int): Rebalancing frequency in days (default: 3, optimal per backtest)
        top_n (int): Number of positions for long side (default: 10)
        bottom_n (int): Number of positions for short side (default: 10)
        strategy_type (str): Strategy type ('long_low_short_high', 'long_low_vol', 'long_high_vol')
        weighting_method (str): Weighting method ('equal_weight' or 'risk_parity')
        long_allocation (float): Allocation to long side (default: 0.5)
        short_allocation (float): Allocation to short side (default: 0.5)
    
    Returns:
        dict: Dictionary mapping symbols to notional positions (positive = long, negative = short)
    """
    print("\n" + "-" * 80)
    print("VOLATILITY FACTOR STRATEGY (Low Volatility Anomaly)")
    print("-" * 80)
    print(f"  Volatility window: {volatility_window} days")
    print(f"  Rebalance frequency: {rebalance_days} days (optimal per backtest)")
    print(f"  Strategy type: {strategy_type}")
    print(f"  Top N (long): {top_n} positions")
    print(f"  Bottom N (short): {bottom_n} positions")
    print(f"  Weighting: {weighting_method}")
    print(f"  Long allocation: {long_allocation*100:.1f}%")
    print(f"  Short allocation: {short_allocation*100:.1f}%")
    
    try:
        # Step 1: Calculate volatility for all symbols
        volatility_results = []
        
        for symbol in symbols:
            if symbol not in historical_data:
                continue
            
            df = historical_data[symbol].copy()
            if len(df) < volatility_window:
                continue
            
            # Sort by date
            df = df.sort_values("date").reset_index(drop=True)
            
            # Calculate daily log returns
            df["daily_return"] = np.log(df["close"] / df["close"].shift(1))
            
            # Calculate rolling volatility (annualized)
            if len(df) >= volatility_window:
                # Use most recent window
                recent_data = df.tail(volatility_window).copy()
                
                # Calculate volatility
                volatility = recent_data["daily_return"].std() * np.sqrt(365)
                
                if not np.isnan(volatility) and volatility > 0:
                    # Get latest price for reference
                    latest_price = df["close"].iloc[-1]
                    
                    volatility_results.append({
                        "symbol": symbol,
                        "volatility": volatility,
                        "price": latest_price,
                    })
        
        if not volatility_results:
            print("  ⚠️  No symbols with valid volatility calculations")
            return {}
        
        # Convert to DataFrame for easier ranking
        vol_df = pd.DataFrame(volatility_results)
        
        print(f"\n  Calculated volatility for {len(vol_df)} symbols")
        print(f"  Volatility range: [{vol_df['volatility'].min()*100:.1f}%, {vol_df['volatility'].max()*100:.1f}%]")
        print(f"  Volatility mean: {vol_df['volatility'].mean()*100:.1f}%")
        print(f"  Volatility median: {vol_df['volatility'].median()*100:.1f}%")
        
        # Step 2: Sort by volatility (ascending: low to high)
        vol_df = vol_df.sort_values("volatility")
        
        # Step 3: Select top N and bottom N based on strategy type
        if strategy_type == "long_low_short_high":
            # Long: Bottom N (lowest volatility)
            long_df = vol_df.head(top_n).copy()
            # Short: Top N (highest volatility)
            short_df = vol_df.tail(bottom_n).copy()
        
        elif strategy_type == "long_low_vol":
            # Long: Bottom N (lowest volatility) only
            long_df = vol_df.head(top_n).copy()
            short_df = pd.DataFrame()
        
        elif strategy_type == "long_high_vol":
            # Long: Top N (highest volatility) only
            long_df = vol_df.tail(top_n).copy()
            short_df = pd.DataFrame()
        
        elif strategy_type == "long_high_short_low":
            # Long: Top N (highest volatility), Short: Bottom N (lowest volatility) - contrarian
            long_df = vol_df.tail(top_n).copy()
            short_df = vol_df.head(bottom_n).copy()
        
        else:
            print(f"  ⚠️  Unknown strategy type: {strategy_type}")
            return {}
        
        print(f"\n  Selected {len(long_df)} long positions ({strategy_type.split('_')[1]} volatility)")
        print(f"  Selected {len(short_df)} short positions ({strategy_type.split('_')[-1] if len(strategy_type.split('_')) > 2 else 'N/A'} volatility)" if len(short_df) > 0 else "  No short positions")
        
        if len(long_df) == 0 and len(short_df) == 0:
            print("  ⚠️  No positions selected")
            return {}
        
        # Step 4: Calculate weights
        positions = {}
        
        # Long positions
        if len(long_df) > 0:
            long_notional = strategy_notional * long_allocation
            
            if weighting_method == "equal_weight":
                weight_per_position = long_notional / len(long_df)
                for _, row in long_df.iterrows():
                    positions[row["symbol"]] = weight_per_position
            
            elif weighting_method == "risk_parity":
                # Weight inversely to volatility (lower vol gets higher weight)
                long_df["inv_vol"] = 1 / long_df["volatility"]
                total_inv_vol = long_df["inv_vol"].sum()
                for _, row in long_df.iterrows():
                    weight = (row["inv_vol"] / total_inv_vol) * long_notional
                    positions[row["symbol"]] = weight
            
            print(f"\n  Long positions (total: ${long_notional:,.2f}):")
            for symbol, notional in sorted(positions.items(), key=lambda x: x[1], reverse=True)[:10]:
                vol_val = vol_df[vol_df["symbol"] == symbol]["volatility"].iloc[0]
                print(f"    {symbol}: ${notional:,.2f} (vol: {vol_val*100:.1f}%)")
            if len(positions) > 10:
                print(f"    ... and {len([p for p in positions.values() if p > 0]) - 10} more")
        
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
            
            short_positions = [(s, p) for s, p in positions.items() if p < 0]
            if short_positions:
                print(f"\n  Short positions (total: ${short_notional:,.2f}):")
                for symbol, notional in sorted(short_positions, key=lambda x: abs(x[1]), reverse=True)[:10]:
                    vol_val = vol_df[vol_df["symbol"] == symbol]["volatility"].iloc[0]
                    print(f"    {symbol}: ${abs(notional):,.2f} (vol: {vol_val*100:.1f}%)")
                if len(short_positions) > 10:
                    print(f"    ... and {len(short_positions) - 10} more")
        
        # Calculate portfolio volatility
        portfolio_vol = 0
        total_weight = 0
        for symbol, notional in positions.items():
            vol_val = vol_df[vol_df["symbol"] == symbol]["volatility"].iloc[0]
            weight = abs(notional) / strategy_notional
            portfolio_vol += weight * vol_val
            total_weight += weight
        
        if total_weight > 0:
            avg_portfolio_vol = portfolio_vol / total_weight
            print(f"\n  Average portfolio volatility: {avg_portfolio_vol*100:.1f}%")
        print(f"  Total positions: {len(positions)}")
        
        return positions
    
    except Exception as e:
        print(f"\n  ❌ Error in volatility strategy: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}
