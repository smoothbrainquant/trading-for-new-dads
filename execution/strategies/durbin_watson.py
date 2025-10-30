from typing import Dict, List

import pandas as pd
import numpy as np

from .utils import calculate_rolling_30d_volatility, calc_weights, get_base_symbol


def calculate_durbin_watson(returns_series: pd.Series) -> float:
    """
    Calculate the Durbin-Watson statistic for a time series of returns.
    
    DW = sum((e_t - e_(t-1))^2) / sum(e_t^2)
    
    where e_t are the residuals (returns in our case).
    
    DW ≈ 2: No autocorrelation (random walk)
    DW < 2: Positive autocorrelation (momentum)
    DW > 2: Negative autocorrelation (mean reversion)
    
    Args:
        returns_series: Time series of returns
        
    Returns:
        float: Durbin-Watson statistic
    """
    returns = returns_series.dropna()
    
    if len(returns) < 2:
        return np.nan
    
    # Calculate differences between consecutive returns
    diff = returns.diff()
    
    # DW statistic
    numerator = (diff ** 2).sum()
    denominator = (returns ** 2).sum()
    
    if denominator == 0:
        return np.nan
    
    dw = numerator / denominator
    
    return dw


def strategy_durbin_watson(
    historical_data: Dict[str, pd.DataFrame],
    universe_symbols: List[str],
    notional: float,
    dw_window: int = 30,
    rebalance_days: int = 7,
    long_percentile: int = 80,
    short_percentile: int = 20,
    top_n_market_cap: int = 100,
) -> Dict[str, float]:
    """
    Durbin-Watson factor strategy (Contrarian).
    
    Long: Coins with high DW (mean-reverting) - will revert UP
    Short: Coins with low DW (momentum) - will exhaust DOWN
    
    Args:
        historical_data: Dict mapping symbols to price DataFrames
        universe_symbols: List of symbols to consider
        notional: Total notional to allocate
        dw_window: Lookback window for DW calculation (default: 30 days)
        rebalance_days: Rebalance frequency (default: 7 days, optimal)
        long_percentile: Percentile threshold for longs (default: 80)
        short_percentile: Percentile threshold for shorts (default: 20)
        top_n_market_cap: Filter to top N coins by market cap (default: 100)
        
    Returns:
        Dict mapping symbols to target notional positions
    """
    # Filter to top N by market cap
    print(f"  Filtering universe from {len(universe_symbols)} to top {top_n_market_cap} by market cap...")
    try:
        from data.scripts.fetch_coinmarketcap_data import (
            fetch_coinmarketcap_data,
            map_symbols_to_trading_pairs,
        )
        df_mc = fetch_coinmarketcap_data(limit=200)
        if df_mc is not None and not df_mc.empty:
            df_mc_mapped = map_symbols_to_trading_pairs(df_mc, trading_suffix='/USDC:USDC')
            valid_mc_symbols = set(df_mc_mapped['trading_symbol'].dropna().tolist())
            filtered_universe = [s for s in universe_symbols if s in valid_mc_symbols]
            
            df_mc_filtered = df_mc_mapped[df_mc_mapped['trading_symbol'].isin(filtered_universe)]
            df_mc_filtered = df_mc_filtered.sort_values('market_cap', ascending=False).head(top_n_market_cap)
            top_symbols = df_mc_filtered['trading_symbol'].tolist()
            
            if top_symbols:
                print(f"  Filtered to {len(top_symbols)} symbols with top market caps")
                universe_symbols = top_symbols
            else:
                print(f"  Warning: Market cap filtering produced no symbols, using full universe")
        else:
            print(f"  Warning: Could not fetch market cap data, using full universe")
    except Exception as e:
        print(f"  Warning: Error in market cap filtering: {e}")
    
    # Calculate DW for each symbol
    dw_scores = {}
    
    for symbol in universe_symbols:
        if symbol not in historical_data:
            continue
            
        df = historical_data[symbol]
        
        if df is None or df.empty or len(df) < dw_window:
            continue
        
        # Get recent window of data
        df_recent = df.tail(dw_window)
        
        # Calculate returns
        if 'close' in df_recent.columns:
            returns = df_recent['close'].pct_change()
        elif 'Close' in df_recent.columns:
            returns = df_recent['Close'].pct_change()
        else:
            continue
        
        # Calculate DW statistic
        dw = calculate_durbin_watson(returns)
        
        if not np.isnan(dw) and 0.5 < dw < 3.5:  # Filter extreme values
            dw_scores[symbol] = dw
    
    if len(dw_scores) < 10:
        print(f"  Warning: Only {len(dw_scores)} symbols with valid DW scores")
        return {}
    
    print(f"  Calculated DW for {len(dw_scores)} symbols")
    
    # Convert to DataFrame for easier manipulation
    dw_df = pd.DataFrame(list(dw_scores.items()), columns=['symbol', 'dw'])
    
    # Calculate percentiles
    dw_df['percentile'] = dw_df['dw'].rank(pct=True) * 100
    
    # Select longs and shorts
    long_symbols = dw_df[dw_df['percentile'] >= long_percentile]['symbol'].tolist()
    short_symbols = dw_df[dw_df['percentile'] <= short_percentile]['symbol'].tolist()
    
    print(f"  Selected {len(long_symbols)} longs (high DW, mean-reverting)")
    print(f"  Selected {len(short_symbols)} shorts (low DW, momentum)")
    
    # Equal weight within each side
    positions = {}
    
    if len(long_symbols) > 0:
        long_weight = (notional * 0.5) / len(long_symbols)
        for symbol in long_symbols:
            positions[symbol] = long_weight
    
    if len(short_symbols) > 0:
        short_weight = (notional * 0.5) / len(short_symbols)
        for symbol in short_symbols:
            positions[symbol] = -short_weight
    
    return positions
