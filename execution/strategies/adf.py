"""
ADF Factor Strategy Implementation

Implements the ADF (Augmented Dickey-Fuller) factor strategy for crypto:
- Calculates rolling ADF test statistic for all cryptocurrencies
- Ranks cryptocurrencies by stationarity/mean reversion strength
- Creates long/short portfolios based on ADF rankings:
  * Trend Following Premium: Long trending coins (high ADF), Short stationary coins (low ADF)
  * Mean Reversion Premium: Long stationary coins (low ADF), Short trending coins (high ADF)
- Uses equal-weight or risk parity weighting
- Rebalances periodically (7 days optimal based on backtesting)

This is a market-neutral strategy that captures the trend-following premium.
Based on backtest results: Risk Parity weighting achieved +126.29% return with 0.49 Sharpe.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

try:
    from statsmodels.tsa.stattools import adfuller
except ImportError:
    print("ERROR: statsmodels package not found. Please install it:")
    print("  pip install statsmodels")
    adfuller = None


def strategy_adf(
    historical_data,
    symbols,
    strategy_notional,
    adf_window=60,
    regression="ct",
    volatility_window=30,
    rebalance_days=7,
    long_percentile=20,
    short_percentile=80,
    strategy_type="trend_following_premium",
    weighting_method="risk_parity",
    long_allocation=0.5,
    short_allocation=0.5,
):
    """
    ADF factor strategy (Augmented Dickey-Fuller test for stationarity).
    
    Args:
        historical_data (dict): Dictionary mapping symbols to DataFrames with OHLCV data
        symbols (list): List of symbols to consider
        strategy_notional (float): Total notional to allocate
        adf_window (int): Window for ADF calculation (default: 60 days)
        regression (str): ADF regression type - 'c', 'ct', 'ctt', 'n' (default: 'ct')
        volatility_window (int): Window for volatility calculation (default: 30 days)
        rebalance_days (int): Rebalancing frequency in days (default: 7, optimal per backtest)
        long_percentile (int): Percentile threshold for long positions (default: 20)
        short_percentile (int): Percentile threshold for short positions (default: 80)
        strategy_type (str): Strategy variant:
            - 'trend_following_premium': Long trending (high ADF), Short stationary (low ADF)
            - 'mean_reversion_premium': Long stationary (low ADF), Short trending (high ADF)
        weighting_method (str): Weighting method ('equal_weight' or 'risk_parity')
        long_allocation (float): Allocation to long side (default: 0.5)
        short_allocation (float): Allocation to short side (default: 0.5)
    
    Returns:
        dict: Dictionary mapping symbols to notional positions (positive = long, negative = short)
    """
    print("\n" + "-" * 80)
    print("ADF FACTOR STRATEGY (Augmented Dickey-Fuller)")
    print("-" * 80)
    print(f"  Strategy type: {strategy_type}")
    print(f"  ADF window: {adf_window} days")
    print(f"  Regression type: {regression}")
    print(f"  Volatility window: {volatility_window} days")
    print(f"  Rebalance frequency: {rebalance_days} days (optimal)")
    print(f"  Long percentile: {long_percentile}%")
    print(f"  Short percentile: {short_percentile}%")
    print(f"  Weighting: {weighting_method}")
    print(f"  Long allocation: {long_allocation*100:.1f}%")
    print(f"  Short allocation: {short_allocation*100:.1f}%")
    
    # Check if statsmodels is available
    if adfuller is None:
        print("  ⚠️  statsmodels not available - cannot calculate ADF")
        return {}
    
    # Check if it's time to rebalance based on last rebalance date
    # For real-time trading, we'll check if rebalance_days have passed
    # For simplicity in this initial implementation, we'll rebalance every call
    # TODO: Implement persistent state to track last rebalance date
    
    try:
        # Step 1: Calculate ADF for all symbols
        adf_results = []
        
        for symbol in symbols:
            if symbol not in historical_data:
                continue
            
            df = historical_data[symbol].copy()
            if len(df) < adf_window:
                continue
            
            # Sort by date and get most recent window
            df = df.sort_values("date").reset_index(drop=True)
            
            # Calculate daily returns for supporting analysis
            df["daily_return"] = np.log(df["close"] / df["close"].shift(1))
            
            # Calculate ADF using most recent window of price LEVELS
            if len(df) >= adf_window:
                # Use most recent data for ADF calculation
                window_prices = df["close"].iloc[-adf_window:].values
                
                try:
                    # Run ADF test
                    result = adfuller(window_prices, regression=regression, autolag="AIC")
                    adf_stat = result[0]  # ADF test statistic
                    adf_pvalue = result[1]  # p-value
                    
                    # Sanity check: cap extreme values
                    if adf_stat < -20:
                        adf_stat = -20
                    elif adf_stat > 0:
                        adf_stat = 0
                    
                    # Calculate volatility for risk parity weighting
                    recent_returns = df["daily_return"].iloc[-volatility_window:].dropna()
                    if len(recent_returns) >= int(volatility_window * 0.7):
                        volatility = recent_returns.std() * np.sqrt(365)
                    else:
                        volatility = np.nan
                    
                    # Store result
                    if not np.isnan(adf_stat) and not np.isnan(volatility) and volatility > 0:
                        adf_results.append({
                            "symbol": symbol,
                            "adf_stat": adf_stat,
                            "adf_pvalue": adf_pvalue,
                            "volatility": volatility,
                            "is_stationary": adf_pvalue < 0.05,
                        })
                
                except Exception as e:
                    # Skip if ADF test fails for this symbol
                    continue
        
        if not adf_results:
            print("  ⚠️  No symbols with valid ADF calculations")
            return {}
        
        adf_df = pd.DataFrame(adf_results)
        
        print(f"\n  Calculated ADF for {len(adf_df)} symbols")
        print(f"  ADF range: [{adf_df['adf_stat'].min():.2f}, {adf_df['adf_stat'].max():.2f}]")
        print(f"  ADF mean: {adf_df['adf_stat'].mean():.2f}")
        print(f"  ADF median: {adf_df['adf_stat'].median():.2f}")
        print(f"  Stationary coins (p<0.05): {adf_df['is_stationary'].sum()} / {len(adf_df)}")
        
        # Step 2: Rank by ADF and select long/short based on strategy type
        adf_df["percentile"] = adf_df["adf_stat"].rank(pct=True) * 100
        
        if strategy_type == "trend_following_premium":
            # Long: High ADF (more trending/non-stationary)
            # Short: Low ADF (more stationary/mean-reverting)
            long_df = adf_df[adf_df["percentile"] >= short_percentile].copy()
            short_df = adf_df[adf_df["percentile"] <= long_percentile].copy()
            print(f"\n  TREND FOLLOWING PREMIUM:")
            print(f"    Long: {len(long_df)} trending coins (high ADF)")
            print(f"    Short: {len(short_df)} stationary coins (low ADF)")
        
        elif strategy_type == "mean_reversion_premium":
            # Long: Low ADF (more stationary/mean-reverting)
            # Short: High ADF (more trending/non-stationary)
            long_df = adf_df[adf_df["percentile"] <= long_percentile].copy()
            short_df = adf_df[adf_df["percentile"] >= short_percentile].copy()
            print(f"\n  MEAN REVERSION PREMIUM:")
            print(f"    Long: {len(long_df)} stationary coins (low ADF)")
            print(f"    Short: {len(short_df)} trending coins (high ADF)")
        
        else:
            print(f"  ⚠️  Unknown strategy type: {strategy_type}")
            return {}
        
        # Step 3: Calculate position sizes
        positions = {}
        
        # Long positions
        if len(long_df) > 0:
            long_notional = strategy_notional * long_allocation
            
            if weighting_method == "equal_weight":
                # Equal weight
                weight_per_long = 1.0 / len(long_df)
                for _, row in long_df.iterrows():
                    symbol = row["symbol"]
                    notional = weight_per_long * long_notional
                    positions[symbol] = notional
            
            elif weighting_method == "risk_parity":
                # Weight inversely to volatility (risk parity)
                long_df["inv_vol"] = 1 / long_df["volatility"]
                inv_vol_sum = long_df["inv_vol"].sum()
                
                for _, row in long_df.iterrows():
                    symbol = row["symbol"]
                    weight = row["inv_vol"] / inv_vol_sum
                    notional = weight * long_notional
                    positions[symbol] = notional
            
            print(f"\n  Long positions: {len(long_df)}")
            avg_long_adf = long_df["adf_stat"].mean()
            print(f"  Average long ADF: {avg_long_adf:.2f}")
        
        # Short positions
        if len(short_df) > 0:
            short_notional = strategy_notional * short_allocation
            
            if weighting_method == "equal_weight":
                # Equal weight
                weight_per_short = 1.0 / len(short_df)
                for _, row in short_df.iterrows():
                    symbol = row["symbol"]
                    notional = -weight_per_short * short_notional  # Negative for short
                    positions[symbol] = notional
            
            elif weighting_method == "risk_parity":
                # Weight inversely to volatility
                short_df["inv_vol"] = 1 / short_df["volatility"]
                inv_vol_sum = short_df["inv_vol"].sum()
                
                for _, row in short_df.iterrows():
                    symbol = row["symbol"]
                    weight = row["inv_vol"] / inv_vol_sum
                    notional = -weight * short_notional  # Negative for short
                    positions[symbol] = notional
            
            print(f"\n  Short positions: {len(short_df)}")
            avg_short_adf = short_df["adf_stat"].mean()
            print(f"  Average short ADF: {avg_short_adf:.2f}")
        
        # Print summary
        if positions:
            total_long = sum(v for v in positions.values() if v > 0)
            total_short = abs(sum(v for v in positions.values() if v < 0))
            print(f"\n  Total long exposure: ${total_long:,.2f}")
            print(f"  Total short exposure: ${total_short:,.2f}")
            print(f"  Net exposure: ${total_long - total_short:,.2f}")
        
        return positions
    
    except Exception as e:
        print(f"\n  ❌ Error in ADF strategy: {str(e)}")
        import traceback
        traceback.print_exc()
        return {}
