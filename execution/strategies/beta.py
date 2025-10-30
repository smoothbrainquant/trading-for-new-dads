"""
Beta Factor Strategy Implementation

Implements the Betting Against Beta (BAB) strategy for crypto:
- Calculates rolling beta to BTC for all cryptocurrencies
- Long low beta coins (defensive), short high beta coins (aggressive)
- Uses equal-weight or risk parity weighting
- Rebalances periodically (5 days optimal based on backtesting)

This is a market-neutral strategy that captures the low-beta anomaly.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def strategy_beta(
    historical_data,
    symbols,
    strategy_notional,
    beta_window=90,
    volatility_window=30,
    rebalance_days=5,
    long_percentile=20,
    short_percentile=80,
    weighting_method="equal_weight",
    long_allocation=0.5,
    short_allocation=0.5,
):
    """
    Beta factor strategy (Betting Against Beta).
    
    Args:
        historical_data (dict): Dictionary mapping symbols to DataFrames with OHLCV data
        symbols (list): List of symbols to consider
        strategy_notional (float): Total notional to allocate
        beta_window (int): Window for beta calculation (default: 90 days)
        volatility_window (int): Window for volatility calculation (default: 30 days)
        rebalance_days (int): Rebalancing frequency in days (default: 5, optimal per backtest)
        long_percentile (int): Percentile threshold for long positions (default: 20)
        short_percentile (int): Percentile threshold for short positions (default: 80)
        weighting_method (str): Weighting method ('equal_weight' or 'risk_parity')
        long_allocation (float): Allocation to long side (default: 0.5)
        short_allocation (float): Allocation to short side (default: 0.5)
    
    Returns:
        dict: Dictionary mapping symbols to notional positions (positive = long, negative = short)
    """
    print("\n" + "-" * 80)
    print("BETA FACTOR STRATEGY (Betting Against Beta)")
    print("-" * 80)
    print(f"  Beta window: {beta_window} days")
    print(f"  Volatility window: {volatility_window} days")
    print(f"  Rebalance frequency: {rebalance_days} days (optimal)")
    print(f"  Long percentile: {long_percentile}%")
    print(f"  Short percentile: {short_percentile}%")
    print(f"  Weighting: {weighting_method}")
    print(f"  Long allocation: {long_allocation*100:.1f}%")
    print(f"  Short allocation: {short_allocation*100:.1f}%")
    
    # Check if it's time to rebalance based on last rebalance date
    # For real-time trading, we'll check if rebalance_days have passed
    # For simplicity in this initial implementation, we'll rebalance every call
    # TODO: Implement persistent state to track last rebalance date
    
    try:
        # Step 1: Extract BTC data
        btc_symbol = None
        for sym in symbols:
            if "BTC" in sym and sym in historical_data:
                btc_symbol = sym
                break
        
        if not btc_symbol:
            print("  ⚠️  BTC data not found - cannot calculate beta")
            return {}
        
        btc_data = historical_data[btc_symbol].copy()
        if len(btc_data) < beta_window:
            print(f"  ⚠️  Insufficient BTC data ({len(btc_data)} < {beta_window} days)")
            return {}
        
        print(f"  Using {btc_symbol} as benchmark")
        
        # Calculate BTC returns
        btc_data = btc_data.sort_values("timestamp").reset_index(drop=True)
        btc_data["btc_return"] = np.log(btc_data["close"] / btc_data["close"].shift(1))
        
        # Step 2: Calculate beta for all symbols
        beta_results = []
        
        for symbol in symbols:
            if symbol not in historical_data or symbol == btc_symbol:
                continue
            
            df = historical_data[symbol].copy()
            if len(df) < beta_window:
                continue
            
            # Sort by timestamp
            df = df.sort_values("timestamp").reset_index(drop=True)
            
            # Calculate returns
            df["daily_return"] = np.log(df["close"] / df["close"].shift(1))
            
            # Merge with BTC returns
            df = df.merge(
                btc_data[["timestamp", "btc_return"]],
                on="timestamp",
                how="left"
            )
            
            # Calculate rolling beta
            if len(df) >= beta_window:
                # Use most recent window
                recent_data = df.tail(beta_window).copy()
                
                # Calculate covariance and variance
                cov = recent_data["daily_return"].cov(recent_data["btc_return"])
                var = recent_data["btc_return"].var()
                
                if var > 0 and not np.isnan(cov):
                    beta = cov / var
                    
                    # Cap extreme betas
                    beta = np.clip(beta, -5, 10)
                    
                    # Calculate volatility for risk parity weighting
                    volatility = recent_data["daily_return"].std() * np.sqrt(365)
                    
                    # Get latest price for reference
                    latest_price = df["close"].iloc[-1]
                    
                    beta_results.append({
                        "symbol": symbol,
                        "beta": beta,
                        "volatility": volatility,
                        "price": latest_price,
                    })
        
        if not beta_results:
            print("  ⚠️  No symbols with valid beta calculations")
            return {}
        
        # Convert to DataFrame for easier ranking
        beta_df = pd.DataFrame(beta_results)
        
        print(f"\n  Calculated beta for {len(beta_df)} symbols")
        print(f"  Beta range: [{beta_df['beta'].min():.2f}, {beta_df['beta'].max():.2f}]")
        print(f"  Beta mean: {beta_df['beta'].mean():.2f}")
        print(f"  Beta median: {beta_df['beta'].median():.2f}")
        
        # Step 3: Rank by beta and select long/short
        beta_df["percentile"] = beta_df["beta"].rank(pct=True) * 100
        
        # Long: Low beta (defensive)
        long_df = beta_df[beta_df["percentile"] <= long_percentile].copy()
        
        # Short: High beta (aggressive)
        short_df = beta_df[beta_df["percentile"] >= short_percentile].copy()
        
        print(f"\n  Selected {len(long_df)} long positions (low beta)")
        print(f"  Selected {len(short_df)} short positions (high beta)")
        
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
                # Weight inversely to volatility
                long_df["inv_vol"] = 1 / long_df["volatility"]
                total_inv_vol = long_df["inv_vol"].sum()
                for _, row in long_df.iterrows():
                    weight = (row["inv_vol"] / total_inv_vol) * long_notional
                    positions[row["symbol"]] = weight
            
            print(f"\n  Long positions (total: ${long_notional:,.2f}):")
            for symbol, notional in sorted(positions.items(), key=lambda x: x[1], reverse=True):
                beta_val = beta_df[beta_df["symbol"] == symbol]["beta"].iloc[0]
                print(f"    {symbol}: ${notional:,.2f} (beta: {beta_val:.2f})")
        
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
            for symbol in sorted(positions.keys()):
                if positions[symbol] < 0:
                    beta_val = beta_df[beta_df["symbol"] == symbol]["beta"].iloc[0]
                    print(f"    {symbol}: ${abs(positions[symbol]):,.2f} (beta: {beta_val:.2f})")
        
        # Calculate portfolio beta
        portfolio_beta = 0
        for symbol, notional in positions.items():
            beta_val = beta_df[beta_df["symbol"] == symbol]["beta"].iloc[0]
            weight = notional / strategy_notional
            portfolio_beta += weight * beta_val
        
        print(f"\n  Portfolio beta: {portfolio_beta:.2f}")
        print(f"  Total positions: {len(positions)}")
        
        return positions
    
    except Exception as e:
        print(f"\n  ❌ Error in beta strategy: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}
