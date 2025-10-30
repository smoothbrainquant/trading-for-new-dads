from typing import Dict, List
import os
import json
from datetime import datetime, timedelta

import pandas as pd

from .utils import calculate_rolling_30d_volatility, calc_weights


def strategy_size(
    historical_data: Dict[str, pd.DataFrame],
    universe_symbols: List[str],
    notional: float,
    top_n: int = 10,
    bottom_n: int = 10,
    limit: int = 100,
    rebalance_days: int = 10,
) -> Dict[str, float]:
    """Size factor via market capitalization (CoinMarketCap).

    - Fetch current market caps for top `limit` coins from CMC (uses mock if no API key)
    - LONG bottom `bottom_n` (smallest caps)
    - SHORT top `top_n` (largest caps)
    - Intersect with tradable `universe_symbols`
    - Weight by inverse 30d volatility
    - Caches results and only recalculates every `rebalance_days` days
    
    Args:
        historical_data: Dictionary of symbol -> DataFrame with OHLCV data
        universe_symbols: List of tradable symbols
        notional: Total notional to allocate
        top_n: Number of large caps to short
        bottom_n: Number of small caps to long
        limit: Number of coins to fetch from CMC
        rebalance_days: Days between rebalancing (default: 10, optimal per backtest)
    
    Returns:
        Dictionary of symbol -> target notional (positive=long, negative=short)
    """
    try:
        from data.scripts.fetch_coinmarketcap_data import (
            fetch_coinmarketcap_data,
            map_symbols_to_trading_pairs,
        )
    except Exception as e:
        print(f"  Size handler unavailable (CMC import error): {e}")
        return {}
    
    # Check cache and skip recalculation if within rebalance period
    workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cache_dir = os.path.join(workspace_root, "execution", ".cache")
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "size_strategy_cache.json")
    
    # Try to load cached weights
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cache_data = json.load(f)
            
            last_calc_date = datetime.fromisoformat(cache_data.get('last_calculation_date', '2000-01-01'))
            days_since_calc = (datetime.now() - last_calc_date).days
            cached_weights = cache_data.get('weights', {})
            cached_notional = cache_data.get('notional', 0)
            
            if days_since_calc < rebalance_days and cached_weights:
                # Use cached weights, but scale to current notional
                print(f"  ⚡ Using cached SIZE weights (calculated {days_since_calc} days ago)")
                print(f"     Next recalculation in {rebalance_days - days_since_calc} days")
                
                # Scale cached weights to current notional
                scale_factor = notional / cached_notional if cached_notional > 0 else 1.0
                scaled_weights = {sym: weight * scale_factor for sym, weight in cached_weights.items()}
                
                # Filter to only symbols in current universe
                filtered_weights = {sym: weight for sym, weight in scaled_weights.items() 
                                   if sym in universe_symbols}
                
                print(f"     Using {len(filtered_weights)} cached positions (scaled to ${notional:,.2f})")
                return filtered_weights
            else:
                print(f"  🔄 Cache expired ({days_since_calc} days old) - recalculating SIZE weights")
        except Exception as e:
            print(f"  ⚠️  Error loading cache: {e} - recalculating")
    else:
        print(f"  🔄 No cache found - calculating SIZE weights (will cache for {rebalance_days} days)")

    try:
        df_mc = fetch_coinmarketcap_data(limit=limit)
    except Exception as e:
        print(f"  Error fetching market caps from CMC: {e}")
        return {}

    if df_mc is None or df_mc.empty:
        print("  No market cap data available for size factor.")
        return {}

    # Ensure required columns and map to trading symbols used in our data/exchange
    df_mc = df_mc.dropna(subset=["market_cap", "symbol"]).copy()
    df_mc = map_symbols_to_trading_pairs(df_mc, trading_suffix="/USDC:USDC")

    # Keep only assets that exist in our tradable universe
    df_mc = df_mc[df_mc["trading_symbol"].isin(universe_symbols)]
    if df_mc.empty:
        print("  CMC symbols did not match our tradable universe for size factor.")
        return {}

    # Sort by market cap (desc). Top = large caps; Bottom = small caps
    df_sorted = df_mc.sort_values("market_cap", ascending=False)
    top_large = df_sorted.head(max(0, int(top_n)))
    bottom_small = df_sorted.tail(max(0, int(bottom_n)))

    short_symbols = top_large["trading_symbol"].tolist()  # short large caps
    long_symbols = bottom_small["trading_symbol"].tolist()  # long small caps

    target_positions: Dict[str, float] = {}

    if long_symbols:
        vola_long = calculate_rolling_30d_volatility(historical_data, long_symbols)
        w_long = calc_weights(vola_long) if vola_long else {}
        for symbol, w in w_long.items():
            target_positions[symbol] = target_positions.get(symbol, 0.0) + w * notional
        print(
            f"  Allocated ${notional:,.2f} to SIZE LONGS (bottom {bottom_n} market caps) across {len(w_long)} symbols"
        )
    else:
        print("  No SIZE LONG candidates (small caps).")

    if short_symbols:
        vola_short = calculate_rolling_30d_volatility(historical_data, short_symbols)
        w_short = calc_weights(vola_short) if vola_short else {}
        for symbol, w in w_short.items():
            target_positions[symbol] = target_positions.get(symbol, 0.0) - w * notional
        print(
            f"  Allocated ${notional:,.2f} to SIZE SHORTS (top {top_n} market caps) across {len(w_short)} symbols"
        )
    else:
        print("  No SIZE SHORT candidates (large caps).")

    # Save to cache for future runs
    try:
        cache_data = {
            'last_calculation_date': datetime.now().isoformat(),
            'weights': target_positions,
            'notional': notional,
            'rebalance_days': rebalance_days,
            'params': {
                'top_n': top_n,
                'bottom_n': bottom_n,
                'limit': limit
            }
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        print(f"  💾 Cached SIZE weights (valid for {rebalance_days} days)")
    except Exception as e:
        print(f"  ⚠️  Warning: Could not save cache: {e}")

    return target_positions
