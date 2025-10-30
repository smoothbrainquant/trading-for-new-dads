from typing import Dict, List
import os
import json
from datetime import datetime

import pandas as pd

from .utils import calculate_rolling_30d_volatility, calc_weights, get_base_symbol


def strategy_carry(
    historical_data: Dict[str, pd.DataFrame],
    universe_symbols: List[str],
    notional: float,
    exchange_id: str = "hyperliquid",
    top_n: int = 10,
    bottom_n: int = 10,
    rebalance_days: int = 7,
) -> Dict[str, float]:
    """
    Carry strategy using AGGREGATED market-wide funding rates from Coinalyze.

    The signal comes from Coinalyze's aggregated funding rates across all exchanges,
    which we then trade on the specified exchange (e.g., Hyperliquid).

    We are trading the funding rate signal (market sentiment), not the actual
    funding payments themselves.
    
    Args:
        historical_data: Dictionary of symbol -> DataFrame with OHLCV data
        universe_symbols: List of tradable symbols
        notional: Total notional to allocate
        exchange_id: Exchange to trade on (default: hyperliquid)
        top_n: Number of high funding rate coins to short
        bottom_n: Number of low funding rate coins to long
        rebalance_days: Days between rebalancing (default: 7, weekly)
    
    Returns:
        Dictionary of symbol -> target notional (positive=long, negative=short)
    """
    # Check cache and skip recalculation if within rebalance period
    workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cache_dir = os.path.join(workspace_root, "execution", ".cache")
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "carry_strategy_cache.json")
    
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
                print(f"  ⚡ Using cached CARRY weights (calculated {days_since_calc} days ago)")
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
                print(f"  🔄 Cache expired ({days_since_calc} days old) - recalculating CARRY weights")
        except Exception as e:
            print(f"  ⚠️  Error loading cache: {e} - recalculating")
    else:
        print(f"  🔄 No cache found - calculating CARRY weights (will cache for {rebalance_days} days)")
    

    # Filter to top 150 by market cap to reduce API calls
    print(f"  Filtering universe from {len(universe_symbols)} to top 150 by market cap...")
    try:
        from data.scripts.fetch_coinmarketcap_data import (
            fetch_coinmarketcap_data,
            map_symbols_to_trading_pairs,
        )

        df_mc = fetch_coinmarketcap_data(limit=200)
        if df_mc is not None and not df_mc.empty:
            df_mc_mapped = map_symbols_to_trading_pairs(df_mc, trading_suffix="/USDC:USDC")
            # Get trading symbols that are in our universe
            valid_mc_symbols = set(df_mc_mapped["trading_symbol"].dropna().tolist())
            filtered_universe = [s for s in universe_symbols if s in valid_mc_symbols]

            # Sort by market cap and take top 150
            df_mc_filtered = df_mc_mapped[df_mc_mapped["trading_symbol"].isin(filtered_universe)]
            df_mc_filtered = df_mc_filtered.sort_values("market_cap", ascending=False).head(150)
            top_150_symbols = df_mc_filtered["trading_symbol"].tolist()

            if top_150_symbols:
                print(f"  Filtered to {len(top_150_symbols)} symbols with top market caps")
                universe_symbols = top_150_symbols
            else:
                print(f"  Warning: Market cap filtering produced no symbols, using full universe")
        else:
            print(f"  Warning: Could not fetch market cap data, using full universe")
    except Exception as e:
        print(f"  Warning: Market cap filtering failed ({e}), using full universe")

    df_rates = None
    # Use Coinalyze to get aggregated market-wide funding rates using .A suffix (with caching)
    try:
        from data.scripts.coinalyze_cache import fetch_coinalyze_aggregated_funding_cached

        num_symbols = len(universe_symbols)
        estimated_time = (num_symbols / 20 + 1) * 1.5  # chunks of 20, 1.5s per call
        print(
            f"  Fetching market-wide funding rates from Coinalyze (using .A aggregated suffix)..."
        )
        print(f"  Format: [SYMBOL]USDT_PERP.A (e.g., BTCUSDT_PERP.A)")
        print(f"  Processing {num_symbols} symbols - checking cache first...")
        print(f"  (If cache miss: Rate limited to 40 calls/min, ~{estimated_time:.0f}s total)")
        df_rates = fetch_coinalyze_aggregated_funding_cached(
            universe_symbols=universe_symbols,
            cache_ttl_hours=8,  # 8 hour cache for funding rates
        )
        if df_rates is not None and not df_rates.empty:
            print(f"  Got funding rates for {len(df_rates)} symbols from aggregated .A data")
            # Normalize expected columns
            df_rates = df_rates.copy()
            if "base" not in df_rates.columns:
                if "symbol" in df_rates.columns:
                    df_rates["base"] = df_rates["symbol"].astype(str).str.split("/").str[0]
            # Coinalyze current helper uses 'funding_rate' already; ensure presence
            if "funding_rate" not in df_rates.columns and "fundingRate" in df_rates.columns:
                df_rates = df_rates.rename(columns={"fundingRate": "funding_rate"})
    except Exception as e:
        print(f"  ⚠️  CARRY STRATEGY: Coinalyze aggregated funding fetch failed ({e})")
        print(f"      Falling back to exchange-specific Coinalyze API...")
        df_rates = None

    # Fallback: Use exchange-specific Coinalyze API
    if df_rates is None or df_rates.empty:
        try:
            from execution.get_carry import fetch_coinalyze_funding_rates_for_universe

            # Map exchange_id to Coinalyze exchange code
            exchange_code_map = {
                "hyperliquid": "H",
                "bybit": "D",
                "okx": "K",
            }
            exchange_code = exchange_code_map.get(
                exchange_id.lower(), "H"
            )  # Default to Hyperliquid
            print(
                f"  Fetching funding rates for {exchange_id} (code: {exchange_code}) via Coinalyze..."
            )
            df_rates = fetch_coinalyze_funding_rates_for_universe(
                universe_symbols=universe_symbols, exchange_code=exchange_code
            )
        except Exception as e:
            print(f"  ⚠️  Error fetching funding rates from Coinalyze for {exchange_id}: {e}")
            return {}
    if df_rates is None or df_rates.empty:
        print("  ⚠️  CARRY STRATEGY: No funding rate data available!")
        print(f"      Check: 1) COINALYZE_API environment variable is set")
        print(f"      Check: 2) Coinalyze API access and rate limits")
        print(f"      Check: 3) Symbols exist on Coinalyze (try different symbols)")
        return {}

    universe_bases = {get_base_symbol(s): s for s in universe_symbols}
    df_rates = df_rates.copy()
    # 'base' may already exist (from Coinalyze). If not, derive from 'symbol'.
    if "base" not in df_rates.columns:
        if "symbol" in df_rates.columns:
            df_rates["base"] = df_rates["symbol"].astype(str).str.split("/").str[0]
    df_rates = df_rates[df_rates["base"].isin(universe_bases.keys())]
    if df_rates.empty:
        print("  No funding symbols matched our universe for carry.")
        return {}

    # Accept either 'funding_rate' or 'funding_rate_pct' (convert pct→rate if needed)
    if "funding_rate" not in df_rates.columns and "funding_rate_pct" in df_rates.columns:
        df_rates = df_rates.copy()
        df_rates["funding_rate"] = df_rates["funding_rate_pct"] / 100.0
    df_rates = df_rates.dropna(subset=["funding_rate"])

    # Select bottom N (most negative) for LONG carry and top N (most positive) for SHORT carry
    df_sorted_asc = df_rates.sort_values("funding_rate", ascending=True)
    df_sorted_desc = df_rates.sort_values("funding_rate", ascending=False)

    selected_long_bases = df_sorted_asc.head(max(0, int(bottom_n)))["base"].tolist()
    selected_short_bases = df_sorted_desc.head(max(0, int(top_n)))["base"].tolist()

    long_symbols = [universe_bases[b] for b in selected_long_bases if b in universe_bases]
    short_symbols = [universe_bases[b] for b in selected_short_bases if b in universe_bases]

    target_positions: Dict[str, float] = {}

    if long_symbols:
        vola_long = calculate_rolling_30d_volatility(historical_data, long_symbols)
        w_long = calc_weights(vola_long) if vola_long else {}
        for symbol, w in w_long.items():
            target_positions[symbol] = target_positions.get(symbol, 0.0) + w * notional
        print(
            f"  Allocated ${notional:,.2f} to carry LONGS across {len(w_long)} symbols (bottom {bottom_n} FR)"
        )
    else:
        print("  No carry LONG candidates (negative funding).")

    if short_symbols:
        vola_short = calculate_rolling_30d_volatility(historical_data, short_symbols)
        w_short = calc_weights(vola_short) if vola_short else {}
        for symbol, w in w_short.items():
            target_positions[symbol] = target_positions.get(symbol, 0.0) - w * notional
        print(
            f"  Allocated ${notional:,.2f} to carry SHORTS across {len(w_short)} symbols (top {top_n} FR)"
        )
    else:
        print("  No carry SHORT candidates (positive funding).")

    # Save to cache for future runs
    try:
        cache_data = {
            'last_calculation_date': datetime.now().isoformat(),
            'weights': target_positions,
            'notional': notional,
            'rebalance_days': rebalance_days,
            'params': {
                'exchange_id': exchange_id,
                'top_n': top_n,
                'bottom_n': bottom_n
            }
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f, indent=2)
        print(f"  💾 Cached CARRY weights (valid for {rebalance_days} days)")
    except Exception as e:
        print(f"  ⚠️  Warning: Could not save cache: {e}")

    return target_positions
