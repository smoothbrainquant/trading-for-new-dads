"""
Trendline Breakout Strategy Implementation

Implements a momentum continuation strategy based on trendline analysis:
- Calculates rolling linear regression on closing prices (trendline)
- Detects when price breaks out strongly from a clean, statistically significant trendline
- Long breakouts above uptrend, short breakouts below downtrend
- Uses signal strength for position weighting

Based on backtesting results (2020-2025):
- Total Return: +93.44%
- Sharpe Ratio: 0.36
- Optimal Holding Period: 5 days
- Optimal R²: ≥ 0.5
- Optimal Z-score: ≥ 1.5σ
"""

import pandas as pd
import numpy as np
from typing import Dict
from datetime import datetime, timedelta


def strategy_trendline_breakout(
    historical_data: Dict[str, pd.DataFrame],
    strategy_notional: float,
    trendline_window: int = 30,
    volatility_window: int = 30,
    breakout_threshold: float = 1.5,
    min_r2: float = 0.5,
    max_pvalue: float = 0.05,
    max_positions: int = 10,
    rebalance_days: int = 1,
    weighting_method: str = "equal_weight",
    long_allocation: float = 0.5,
    short_allocation: float = 0.5,
) -> Dict[str, float]:
    """
    Trendline breakout strategy (momentum continuation).
    
    Args:
        historical_data (dict): Dictionary mapping symbols to DataFrames with OHLCV data
        strategy_notional (float): Total notional to allocate
        trendline_window (int): Window for trendline calculation (default: 30 days)
        volatility_window (int): Window for volatility calculation (default: 30 days)
        breakout_threshold (float): Z-score threshold for breakout (default: 1.5σ)
        min_r2 (float): Minimum R² for clean trendline (default: 0.5)
        max_pvalue (float): Maximum p-value for significant trendline (default: 0.05)
        max_positions (int): Maximum positions per side (default: 10)
        rebalance_days (int): Rebalancing frequency in days (default: 1 = daily)
        weighting_method (str): Weighting method ('equal_weight' or 'signal_weighted')
        long_allocation (float): Allocation to long side (default: 0.5)
        short_allocation (float): Allocation to short side (default: 0.5)
    
    Returns:
        dict: Dictionary mapping symbols to notional positions (positive = long, negative = short)
    """
    print("\n" + "-" * 80)
    print("TRENDLINE BREAKOUT STRATEGY (Momentum Continuation)")
    print("-" * 80)
    print(f"  Trendline window: {trendline_window} days")
    print(f"  Breakout threshold: {breakout_threshold}σ")
    print(f"  Min R²: {min_r2}")
    print(f"  Max P-value: {max_pvalue}")
    print(f"  Max positions: {max_positions} per side")
    print(f"  Rebalance frequency: {rebalance_days} days")
    print(f"  Weighting: {weighting_method}")
    print(f"  Long allocation: {long_allocation*100:.1f}%")
    print(f"  Short allocation: {short_allocation*100:.1f}%")
    
    try:
        from signals.calc_trendline_breakout_signals import (
            calculate_rolling_trendline,
            calculate_breakout_metrics,
            detect_breakout_signals,
        )
        
        # Step 1: Combine all historical data into a single DataFrame
        all_data = []
        for symbol, df in historical_data.items():
            if df is None or df.empty:
                continue
            
            symbol_df = df.copy()
            symbol_df["symbol"] = symbol
            
            # Ensure required columns exist
            required_cols = ["timestamp", "close"]
            if not all(col in symbol_df.columns for col in required_cols):
                continue
            
            # Rename timestamp to date for consistency
            symbol_df["date"] = pd.to_datetime(symbol_df["timestamp"])
            symbol_df = symbol_df[["date", "symbol", "close"]]
            
            all_data.append(symbol_df)
        
        if not all_data:
            print("  ⚠️  No valid historical data available")
            return {}
        
        # Combine all data
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df = combined_df.sort_values(["symbol", "date"]).reset_index(drop=True)
        
        print(f"\n  Processing {len(combined_df)} data points for {combined_df['symbol'].nunique()} symbols")
        
        # Step 2: Calculate trendline metrics
        trendline_data = calculate_rolling_trendline(combined_df, window=trendline_window)
        
        # Step 3: Calculate breakout metrics
        trendline_data = calculate_breakout_metrics(trendline_data, window=volatility_window)
        
        # Step 4: Detect breakout signals
        trendline_data = detect_breakout_signals(
            trendline_data,
            breakout_threshold=breakout_threshold,
            min_r2=min_r2,
            max_pvalue=max_pvalue,
            slope_direction='any'
        )
        
        # Step 5: Get most recent signals (within last rebalance_days)
        latest_date = trendline_data["date"].max()
        recent_cutoff = latest_date - pd.Timedelta(days=rebalance_days)
        
        recent_signals = trendline_data[
            (trendline_data["date"] >= recent_cutoff) &
            (trendline_data["signal"] != "NEUTRAL")
        ].copy()
        
        if recent_signals.empty:
            print("  ⚠️  No recent signals found")
            return {}
        
        # Get most recent signal per symbol
        current_signals = recent_signals.sort_values("date").groupby("symbol").tail(1)
        
        # Step 6: Rank by signal strength and select top positions
        long_signals = current_signals[current_signals["signal"] == "LONG"].copy()
        short_signals = current_signals[current_signals["signal"] == "SHORT"].copy()
        
        # Sort by signal strength
        long_signals = long_signals.sort_values("signal_strength", ascending=False).head(max_positions)
        short_signals = short_signals.sort_values("signal_strength", ascending=False).head(max_positions)
        
        print(f"\n  Found {len(long_signals)} LONG signals (top {max_positions})")
        print(f"  Found {len(short_signals)} SHORT signals (top {max_positions})")
        
        if len(long_signals) == 0 and len(short_signals) == 0:
            print("  ⚠️  No signals after filtering")
            return {}
        
        # Step 7: Calculate position weights
        positions = {}
        
        # Long positions
        if len(long_signals) > 0:
            long_notional = strategy_notional * long_allocation
            
            if weighting_method == "equal_weight":
                weight_per_position = long_notional / len(long_signals)
                for _, row in long_signals.iterrows():
                    positions[row["symbol"]] = weight_per_position
            
            elif weighting_method == "signal_weighted":
                # Weight by signal strength
                total_strength = long_signals["signal_strength"].sum()
                for _, row in long_signals.iterrows():
                    weight = (row["signal_strength"] / total_strength) * long_notional
                    positions[row["symbol"]] = weight
            
            else:
                # Default to equal weight
                weight_per_position = long_notional / len(long_signals)
                for _, row in long_signals.iterrows():
                    positions[row["symbol"]] = weight_per_position
            
            print(f"\n  Long positions (total: ${long_notional:,.2f}):")
            for _, row in long_signals.iterrows():
                symbol = row["symbol"]
                notional = positions[symbol]
                print(f"    {symbol}: ${notional:,.2f} "
                      f"(strength: {row['signal_strength']:.2f}, "
                      f"R²: {row['r_squared']:.3f}, "
                      f"Z-score: {row['breakout_z_score']:.2f}σ)")
        
        # Short positions
        if len(short_signals) > 0:
            short_notional = strategy_notional * short_allocation
            
            if weighting_method == "equal_weight":
                weight_per_position = short_notional / len(short_signals)
                for _, row in short_signals.iterrows():
                    positions[row["symbol"]] = -weight_per_position  # Negative for short
            
            elif weighting_method == "signal_weighted":
                # Weight by signal strength
                total_strength = short_signals["signal_strength"].sum()
                for _, row in short_signals.iterrows():
                    weight = (row["signal_strength"] / total_strength) * short_notional
                    positions[row["symbol"]] = -weight  # Negative for short
            
            else:
                # Default to equal weight
                weight_per_position = short_notional / len(short_signals)
                for _, row in short_signals.iterrows():
                    positions[row["symbol"]] = -weight_per_position  # Negative for short
            
            print(f"\n  Short positions (total: ${short_notional:,.2f}):")
            for _, row in short_signals.iterrows():
                symbol = row["symbol"]
                notional = abs(positions[symbol])
                print(f"    {symbol}: ${notional:,.2f} "
                      f"(strength: {row['signal_strength']:.2f}, "
                      f"R²: {row['r_squared']:.3f}, "
                      f"Z-score: {row['breakout_z_score']:.2f}σ)")
        
        print(f"\n  Total positions: {len(positions)}")
        print(f"  Total allocated: ${sum(abs(v) for v in positions.values()):,.2f}")
        
        return positions
    
    except Exception as e:
        print(f"\n  ❌ Error in trendline breakout strategy: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}
