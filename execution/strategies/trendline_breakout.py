"""
Trendline Breakout Strategy

This strategy detects breakouts from clean trendlines:
1. Calculates rolling linear regression on closing prices
2. Measures distance from trendline normalized by volatility
3. Detects strong breakouts (>1.5 standard deviations)
4. Only trades when trendlines are clean and significant (R² >= 0.5)
5. Long breakouts above uptrends, short breakouts below downtrends
"""

from typing import Dict
import pandas as pd
import numpy as np
from scipy import stats

from .utils import calculate_rolling_30d_volatility, calc_weights


def calculate_trendline_signals(
    historical_data: Dict[str, pd.DataFrame],
    trendline_window: int = 30,
    volatility_window: int = 30,
    breakout_threshold: float = 1.5,
    min_r2: float = 0.5,
    max_pvalue: float = 0.05,
    slope_direction: str = "any",
) -> Dict[str, int]:
    """
    Calculate trendline breakout signals for all symbols.
    
    Args:
        historical_data: Dictionary mapping symbols to OHLCV DataFrames
        trendline_window: Rolling window for trendline calculation
        volatility_window: Rolling window for volatility calculation
        breakout_threshold: Minimum Z-score for breakout (e.g., 1.5 = 1.5 std devs)
        min_r2: Minimum R² for clean trendline
        max_pvalue: Maximum p-value for significant trendline
        slope_direction: 'positive', 'negative', or 'any'
        
    Returns:
        Dictionary mapping symbols to signals (-1, 0, 1)
    """
    signals = {}
    
    for symbol, df in historical_data.items():
        if df is None or df.empty or len(df) < trendline_window + volatility_window:
            continue
            
        try:
            # Calculate trendline metrics
            prices = df['close'].values[-trendline_window:]
            x = np.arange(len(prices))
            
            # Fit linear regression
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, prices)
            r_squared = r_value ** 2
            predicted_price = slope * (len(prices) - 1) + intercept
            current_price = prices[-1]
            
            # Calculate distance from trendline (percentage)
            distance_from_trendline = (current_price - predicted_price) / predicted_price * 100
            
            # Calculate volatility-adjusted breakout metric
            returns = df['close'].pct_change().dropna().values[-volatility_window:]
            if len(returns) == 0:
                continue
                
            volatility = returns.std()
            
            # Calculate rolling distance statistics
            distances = []
            for i in range(max(0, len(df) - volatility_window), len(df)):
                if i < trendline_window - 1:
                    continue
                window_prices = df['close'].values[max(0, i - trendline_window + 1):i + 1]
                if len(window_prices) < trendline_window:
                    continue
                window_x = np.arange(len(window_prices))
                try:
                    w_slope, w_intercept, _, _, _ = stats.linregress(window_x, window_prices)
                    w_predicted = w_slope * (len(window_prices) - 1) + w_intercept
                    w_distance = (window_prices[-1] - w_predicted) / w_predicted * 100
                    distances.append(w_distance)
                except:
                    continue
            
            if len(distances) < 5:
                continue
                
            # Calculate Z-score of distance
            distance_mean = np.mean(distances)
            distance_std = np.std(distances)
            if distance_std == 0:
                continue
                
            breakout_z_score = (distance_from_trendline - distance_mean) / distance_std
            
            # Normalized slope (percentage per year)
            norm_slope = (slope / current_price) * 100 * 365
            
            # Check if trendline is clean and significant
            if r_squared < min_r2 or p_value > max_pvalue:
                continue
            
            # Detect bullish breakout: price breaking above clean uptrend
            if slope_direction in ['positive', 'any']:
                if (norm_slope > 0 and 
                    breakout_z_score > breakout_threshold and 
                    distance_from_trendline > 0):
                    signals[symbol] = 1
                    continue
            
            # Detect bearish breakout: price breaking below clean downtrend
            if slope_direction in ['negative', 'any']:
                if (norm_slope < 0 and 
                    breakout_z_score < -breakout_threshold and 
                    distance_from_trendline < 0):
                    signals[symbol] = -1
                    continue
                    
        except Exception as e:
            # Silently skip symbols with errors
            continue
    
    return signals


def strategy_trendline_breakout(
    historical_data: Dict[str, pd.DataFrame],
    notional: float,
    trendline_window: int = 30,
    breakout_threshold: float = 1.5,
    min_r2: float = 0.5,
    max_pvalue: float = 0.05,
    slope_direction: str = "any",
    max_positions: int = 10,
) -> Dict[str, float]:
    """
    Trendline breakout strategy implementation for live trading.
    
    Args:
        historical_data: Dictionary mapping symbols to OHLCV DataFrames
        notional: Total notional amount to allocate per side
        trendline_window: Rolling window for trendline calculation
        breakout_threshold: Minimum Z-score for breakout
        min_r2: Minimum R² for clean trendline
        max_pvalue: Maximum p-value for significant trendline
        slope_direction: 'positive', 'negative', or 'any'
        max_positions: Maximum positions per side
        
    Returns:
        Dictionary mapping symbols to position sizes (positive=long, negative=short)
    """
    # Calculate signals
    signals = calculate_trendline_signals(
        historical_data,
        trendline_window=trendline_window,
        breakout_threshold=breakout_threshold,
        min_r2=min_r2,
        max_pvalue=max_pvalue,
        slope_direction=slope_direction,
    )
    
    # Separate long and short signals
    longs = [s for s, d in signals.items() if d == 1]
    shorts = [s for s, d in signals.items() if d == -1]
    
    # Limit positions
    if len(longs) > max_positions:
        longs = longs[:max_positions]
    if len(shorts) > max_positions:
        shorts = shorts[:max_positions]
    
    target_positions: Dict[str, float] = {}
    
    # Allocate to long positions (inverse volatility weighted)
    if longs:
        vola_long = calculate_rolling_30d_volatility(historical_data, longs)
        w_long = calc_weights(vola_long) if vola_long else {}
        for symbol, w in w_long.items():
            target_positions[symbol] = target_positions.get(symbol, 0.0) + w * notional
        print(f"  Allocated ${notional:,.2f} to trendline breakout LONGS across {len(w_long)} symbols")
    else:
        print("  No trendline breakout LONG signals.")
    
    # Allocate to short positions (inverse volatility weighted)
    if shorts:
        vola_short = calculate_rolling_30d_volatility(historical_data, shorts)
        w_short = calc_weights(vola_short) if vola_short else {}
        for symbol, w in w_short.items():
            target_positions[symbol] = target_positions.get(symbol, 0.0) - w * notional
        print(f"  Allocated ${notional:,.2f} to trendline breakout SHORTS across {len(w_short)} symbols")
    else:
        print("  No trendline breakout SHORT signals.")
    
    return target_positions
