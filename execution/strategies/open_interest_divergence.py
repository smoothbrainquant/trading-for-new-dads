from __future__ import annotations

from typing import Dict, List, Tuple
from datetime import datetime, timedelta

import pandas as pd

from .utils import get_base_symbol


def _parse_trading_symbol(symbol: str) -> Tuple[str, str]:
    if not isinstance(symbol, str) or '/' not in symbol:
        return symbol, ''
    base, rhs = symbol.split('/', 1)
    quote = rhs.split(':', 1)[0] if ':' in rhs else rhs
    return base, quote


def _build_coinalyze_symbol(base: str, quote: str, exchange_code: str) -> str:
    """
    Build Coinalyze symbol. Format varies by exchange:
    - Hyperliquid (H): {BASE}.H  (e.g., BTC.H)
    - Binance (A): {BASE}{QUOTE}_PERP.A (e.g., BTCUSDT_PERP.A)
    """
    if exchange_code == 'H':
        return f"{base}.{exchange_code}"
    else:
        return f"{base}{quote}_PERP.{exchange_code}"


def _prepare_price_df(historical_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: List[pd.DataFrame] = []
    for sym, df in historical_data.items():
        d = df.copy()
        if 'symbol' not in d.columns:
            d['symbol'] = sym
        d['base_symbol'] = d['symbol'].astype(str).apply(get_base_symbol)
        rows.append(d[['date', 'close', 'symbol', 'base_symbol']])
    if not rows:
        return pd.DataFrame(columns=['date', 'close', 'symbol', 'base_symbol'])
    out = pd.concat(rows, ignore_index=True)
    out['date'] = pd.to_datetime(out['date'])
    out = out.sort_values(['base_symbol', 'date']).reset_index(drop=True)
    return out


def _load_aggregated_oi_from_file(
    universe_symbols: List[str],
    days: int = 200,
) -> pd.DataFrame:
    """Load aggregated OI data from local file.
    
    Uses pre-downloaded aggregated OI data across all exchanges.
    This avoids exchange-specific API calls and provides more robust signals.
    
    Returns columns: ['coin_symbol','coinalyze_symbol','date','oi_close']
    """
    import os
    from glob import glob
    
    # Find the most recent aggregated OI file
    workspace_root = os.getenv('WORKSPACE_ROOT', '/workspace')
    oi_data_dir = os.path.join(workspace_root, 'data', 'raw')
    
    # Look for aggregated OI files
    pattern = os.path.join(oi_data_dir, 'historical_open_interest_all_perps_since2020_*.csv')
    oi_files = sorted(glob(pattern), reverse=True)
    
    if not oi_files:
        print(f"    No aggregated OI data file found at: {pattern}")
        return pd.DataFrame()
    
    oi_file = oi_files[0]
    print(f"    Loading aggregated OI data from: {os.path.basename(oi_file)}")
    
    try:
        df = pd.read_csv(oi_file)
        df['date'] = pd.to_datetime(df['date'])
        
        # Filter to recent data (last N days)
        cutoff_date = datetime.now() - timedelta(days=days)
        df = df[df['date'] >= cutoff_date]
        
        # Extract base symbols from universe
        base_symbols = set()
        for tsym in universe_symbols:
            base = get_base_symbol(tsym)
            base_symbols.add(base)
        
        # Filter to universe base symbols
        df = df[df['coin_symbol'].isin(base_symbols)]
        
        if df.empty:
            print(f"    No OI data found for universe symbols")
            return pd.DataFrame()
        
        # Rename columns to match expected format
        df = df.rename(columns={'symbol': 'coinalyze_symbol'})
        
        # If coinalyze_symbol column doesn't exist, create it from coin_symbol
        if 'coinalyze_symbol' not in df.columns:
            df['coinalyze_symbol'] = df['coin_symbol']
        
        print(f"    Loaded {len(df)} OI records for {df['coin_symbol'].nunique()} symbols")
        print(f"    Date range: {df['date'].min().date()} to {df['date'].max().date()}")
        
        return df[['coin_symbol', 'coinalyze_symbol', 'date', 'oi_close']].sort_values(['coin_symbol', 'date']).reset_index(drop=True)
        
    except Exception as e:
        print(f"    Error loading aggregated OI data: {e}")
        return pd.DataFrame()


def _fetch_oi_history_for_universe(
    universe_symbols: List[str],
    exchange_code: str = 'H',
    days: int = 200,
) -> pd.DataFrame:
    """Fetch daily OI USD history for given trading symbols' bases.

    Returns columns: ['coin_symbol','coinalyze_symbol','date','oi_close']
    """
    try:
        from data.scripts.coinalyze_client import CoinalyzeClient  # type: ignore
    except Exception:
        return pd.DataFrame()

    client = CoinalyzeClient()

    # Map base -> coinalyze symbol (choose quote from trading symbol or default USDC)
    base_to_csym: Dict[str, str] = {}
    for tsym in universe_symbols:
        base, quote = _parse_trading_symbol(tsym)
        if not base:
            continue
        if not quote:
            quote = 'USDC'
        c_sym = _build_coinalyze_symbol(base, quote, exchange_code)
        base_to_csym.setdefault(base, c_sym)

    if not base_to_csym:
        print(f"    No base_to_csym mapping created from universe")
        return pd.DataFrame()

    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=days)).timestamp())
    
    print(f"    Fetching OI for {len(base_to_csym)} symbols (exchange={exchange_code}, days={days})")
    print(f"    Sample mappings: {list(base_to_csym.items())[:3]}")

    rows: List[dict] = []
    # Coinalyze allows up to 20 symbols per request
    items = list(base_to_csym.items())
    chunk = 20
    num_chunks = (len(items) + chunk - 1) // chunk
    estimated_time = num_chunks * 1.5
    print(f"    Rate limited to 40 calls/min: {num_chunks} API calls required (~{estimated_time:.0f}s total)")
    
    for i in range(0, len(items), chunk):
        batch = items[i:i+chunk]
        symbols_param = ','.join(cs for _, cs in batch)
        try:
            data = client.get_open_interest_history(
                symbols=symbols_param,
                interval='daily',
                from_ts=start_ts,
                to_ts=end_ts,
                convert_to_usd=True,
            )
            if data:
                print(f"      Batch {i//chunk + 1}: Got data for {len(data)} symbols")
            else:
                print(f"      Batch {i//chunk + 1}: No data returned")
        except Exception as e:
            print(f"    Error fetching OI history: {e}")
            data = None
        if not data:
            continue
        # Reverse map coinalyze_symbol -> base
        csym_to_base = {cs: b for b, cs in batch}
        for item in data:
            csym = item.get('symbol')
            hist = item.get('history', [])
            base = csym_to_base.get(csym)
            if not base:
                continue
            for pt in hist:
                rows.append({
                    'coin_symbol': base,
                    'coinalyze_symbol': csym,
                    'date': datetime.fromtimestamp(pt['t']).strftime('%Y-%m-%d'),
                    'oi_close': pt.get('c'),
                })
    if not rows:
        print(f"    No OI history rows collected")
        return pd.DataFrame()

    print(f"    Collected {len(rows)} OI history rows")
    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['coin_symbol', 'date']).reset_index(drop=True)
    return df[['coin_symbol', 'coinalyze_symbol', 'date', 'oi_close']]


def strategy_oi_divergence(
    historical_data: Dict[str, pd.DataFrame],
    notional: float,
    mode: str = 'trend',  # or 'divergence'
    lookback: int = 30,
    top_n: int = 10,
    bottom_n: int = 10,
    exchange_code: str = 'H',  # Ignored - uses aggregated data
) -> Dict[str, float]:
    """Open Interest divergence/trend strategy using aggregated OI history.

    - Uses pre-downloaded aggregated OI data across all exchanges
    - Filters universe to top 50 by market cap to optimize computation
    - Builds OI z-score vs price returns over a rolling window
    - Selects top/bottom by score
    - Allocates risk-parity within each side using recent price volatility
    
    Note: exchange_code parameter is ignored; strategy uses aggregated OI data
    from all exchanges for more robust signals.
    """
    if not historical_data:
        return {}

    # Build price dataframe and universe mappings
    price_df = _prepare_price_df(historical_data)
    if price_df.empty:
        return {}

    # Universe trading symbols and mapping base -> trading symbol
    universe_symbols = list(historical_data.keys())
    base_to_trading: Dict[str, str] = {}
    for tsym in universe_symbols:
        base = get_base_symbol(tsym)
        base_to_trading[base] = tsym
    
    # Filter to top 50 by market cap to reduce Coinalyze API calls
    print(f"    Filtering universe from {len(universe_symbols)} to top 50 by market cap...")
    try:
        from data.scripts.fetch_coinmarketcap_data import (
            fetch_coinmarketcap_data,
            map_symbols_to_trading_pairs,
        )
        df_mc = fetch_coinmarketcap_data(limit=200)
        if df_mc is not None and not df_mc.empty:
            df_mc_mapped = map_symbols_to_trading_pairs(df_mc, trading_suffix='/USDC:USDC')
            # Get trading symbols that are in our universe
            valid_mc_symbols = set(df_mc_mapped['trading_symbol'].dropna().tolist())
            filtered_universe = [s for s in universe_symbols if s in valid_mc_symbols]
            
            # Sort by market cap and take top 50
            df_mc_filtered = df_mc_mapped[df_mc_mapped['trading_symbol'].isin(filtered_universe)]
            df_mc_filtered = df_mc_filtered.sort_values('market_cap', ascending=False).head(50)
            top_50_symbols = df_mc_filtered['trading_symbol'].tolist()
            
            if top_50_symbols:
                print(f"    Filtered to {len(top_50_symbols)} symbols with top market caps")
                universe_symbols = top_50_symbols
                # Update base_to_trading for filtered universe
                base_to_trading = {}
                for tsym in universe_symbols:
                    base = get_base_symbol(tsym)
                    base_to_trading[base] = tsym
            else:
                print(f"    Warning: Market cap filtering produced no symbols, using full universe")
        else:
            print(f"    Warning: Could not fetch market cap data, using full universe")
    except Exception as e:
        print(f"    Warning: Market cap filtering failed ({e}), using full universe")

    # Fetch OI history - use aggregated data from local file
    # This provides a more robust signal across all exchanges and avoids API rate limits
    days_needed = max(lookback * 4, 120)
    print(f"    Using aggregated OI data (exchange-agnostic)")
    oi_df = _load_aggregated_oi_from_file(universe_symbols, days=days_needed)
    
    if oi_df is None or oi_df.empty:
        print("  ⚠️  OI DIVERGENCE STRATEGY: No aggregated OI data available!")
        print(f"       Aggregated OI data provides signals across all exchanges")
        print(f"       Make sure aggregated OI data file exists in data/raw/")
        print(f"       File pattern: historical_open_interest_all_perps_since2020_*.csv")
        return {}

    # Compute scores
    from signals.calc_open_interest_divergence import (
        compute_oi_divergence_scores,
        build_equal_or_risk_parity_weights,
    )

    scores = compute_oi_divergence_scores(oi_df, price_df, lookback=lookback)
    if scores.empty:
        return {}

    # Pick on latest date present across both
    latest_date = min(price_df['date'].max(), oi_df['date'].max())
    day_scores = scores[scores['date'] == latest_date]
    if day_scores.empty:
        # fallback to last available in scores
        latest_date = scores['date'].max()
        day_scores = scores[scores['date'] == latest_date]
    col = 'score_trend' if mode == 'trend' else 'score_divergence'
    day_scores = day_scores[['symbol', col]].dropna()
    if day_scores.empty:
        return {}

    sel = day_scores.sort_values(col, ascending=False)
    long_bases = sel.head(max(0, int(top_n)))['symbol'].tolist()
    short_bases = sel.tail(max(0, int(bottom_n)))['symbol'].tolist()

    # Build risk-parity weights on base-level price data
    weights_base = build_equal_or_risk_parity_weights(
        price_df=price_df.rename(columns={'base_symbol': 'symbol'})[['date','symbol','close']],
        long_symbols=long_bases,
        short_symbols=short_bases,
        notional=notional,
        volatility_window=30,
        use_risk_parity=True,
    )

    # Map base -> trading symbols used by execution
    weights_trading: Dict[str, float] = {}
    for base, w in weights_base.items():
        tsym = base_to_trading.get(base)
        if tsym:
            weights_trading[tsym] = weights_trading.get(tsym, 0.0) + w

    return weights_trading
