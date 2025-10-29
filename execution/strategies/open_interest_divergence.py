from __future__ import annotations

from typing import Dict, List, Tuple
from datetime import datetime, timedelta

import pandas as pd

from .utils import get_base_symbol


def _parse_trading_symbol(symbol: str) -> Tuple[str, str]:
    if not isinstance(symbol, str) or "/" not in symbol:
        return symbol, ""
    base, rhs = symbol.split("/", 1)
    quote = rhs.split(":", 1)[0] if ":" in rhs else rhs
    return base, quote


def _build_coinalyze_symbol(base: str, quote: str = "USDT", exchange_code: str = "A") -> str:
    """
    Build Coinalyze symbol. Default format uses aggregate data across all exchanges.

    Formats by exchange:
    - Aggregate (A): {BASE}USDT_PERP.A (e.g., BTCUSDT_PERP.A) - RECOMMENDED for robust signals
    - Hyperliquid (H): {BASE}.H  (e.g., BTC.H)
    - Binance (default): {BASE}{QUOTE}_PERP (e.g., BTCUSDT_PERP)

    Default is aggregate ('A') which provides OI data summed across all exchanges.
    This gives more robust signals than single-exchange data.
    """
    if exchange_code == "A":
        # Aggregate format: always use USDT
        return f"{base}USDT_PERP.A"
    elif exchange_code == "H":
        # Hyperliquid format
        return f"{base}.{exchange_code}"
    else:
        # Other exchanges (e.g., Binance)
        return f"{base}{quote}_PERP.{exchange_code}"


def _prepare_price_df(historical_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: List[pd.DataFrame] = []
    for sym, df in historical_data.items():
        d = df.copy()
        if "symbol" not in d.columns:
            d["symbol"] = sym
        d["base_symbol"] = d["symbol"].astype(str).apply(get_base_symbol)
        rows.append(d[["date", "close", "symbol", "base_symbol"]])
    if not rows:
        return pd.DataFrame(columns=["date", "close", "symbol", "base_symbol"])
    out = pd.concat(rows, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"])
    out = out.sort_values(["base_symbol", "date"]).reset_index(drop=True)
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
    workspace_root = os.getenv("WORKSPACE_ROOT", "/workspace")
    oi_data_dir = os.path.join(workspace_root, "data", "raw")

    # Look for aggregated OI files
    pattern = os.path.join(oi_data_dir, "historical_open_interest_all_perps_since2020_*.csv")
    oi_files = sorted(glob(pattern), reverse=True)

    if not oi_files:
        print(f"    ⚠️  No aggregated OI data file found at: {pattern}")
        print(
            f"    Expected format: historical_open_interest_all_perps_since2020_YYYYMMDD_HHMMSS.csv"
        )
        return pd.DataFrame()

    oi_file = oi_files[0]
    print(f"    Loading aggregated OI data from: {os.path.basename(oi_file)}")

    try:
        df = pd.read_csv(oi_file)

        # Validate required columns
        required_cols = ["coin_symbol", "date", "oi_close"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"    ❌ Missing required columns: {missing_cols}")
            print(f"    Available columns: {list(df.columns)}")
            return pd.DataFrame()

        # Parse dates with error handling
        try:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            # Remove rows with invalid dates
            invalid_dates = df["date"].isna().sum()
            if invalid_dates > 0:
                print(f"    ⚠️  Removed {invalid_dates} rows with invalid dates")
                df = df.dropna(subset=["date"])
        except Exception as e:
            print(f"    ❌ Error parsing dates: {e}")
            return pd.DataFrame()

        # Check data freshness - strict same-day check
        if not df.empty:
            max_date = df["date"].max()
            today = pd.Timestamp(datetime.now().date())
            days_stale = (today - max_date).days

            if days_stale == 0:
                print(f"    ✓ OI data is current (today: {today.date()})")
            elif days_stale == 1:
                print(f"    ⚠️  WARNING: OI data is from YESTERDAY ({max_date.date()})")
                print(f"    Using most recent available data")
                print(f"    Consider refreshing OI data for today's trading signals")
            elif days_stale > 1:
                print(
                    f"    ⚠️  WARNING: OI data is {days_stale} days old (last update: {max_date.date()})"
                )
                print(f"    Today: {today.date()}")
                print(f"    Using most recent available data, but signals may be stale")
                print(f"    RECOMMENDATION: Refresh OI data before trading")
            elif days_stale < 0:
                print(
                    f"    ⚠️  WARNING: OI data has FUTURE dates (max: {max_date.date()}, today: {today.date()})"
                )
                print(f"    This indicates a data quality issue - check data collection")
                print(f"    Using data anyway, but verify results carefully")

        # Filter to recent data (last N days)
        cutoff_date = datetime.now() - timedelta(days=days)
        df_filtered = df[df["date"] >= cutoff_date]

        if df_filtered.empty:
            print(f"    ⚠️  No OI data within last {days} days (cutoff: {cutoff_date.date()})")
            print(f"    Data range: {df['date'].min().date()} to {df['date'].max().date()}")
            # Return all data instead of empty dataframe
            print(f"    Using all available data instead")
            df_filtered = df

        # Extract base symbols from universe
        base_symbols = set()
        for tsym in universe_symbols:
            try:
                base = get_base_symbol(tsym)
                base_symbols.add(base)
            except Exception as e:
                print(f"    ⚠️  Could not extract base symbol from {tsym}: {e}")
                continue

        if not base_symbols:
            print(f"    ❌ No valid base symbols extracted from universe")
            return pd.DataFrame()

        # Filter to universe base symbols
        df_filtered = df_filtered[df_filtered["coin_symbol"].isin(base_symbols)]

        if df_filtered.empty:
            print(f"    ⚠️  No OI data found for universe symbols")
            print(f"    Universe symbols: {sorted(list(base_symbols))[:10]} (showing first 10)")
            print(
                f"    Available symbols: {sorted(df['coin_symbol'].unique()[:10].tolist())} (showing first 10)"
            )
            return pd.DataFrame()

        # Rename columns to match expected format
        df_filtered = df_filtered.rename(columns={"symbol": "coinalyze_symbol"})

        # If coinalyze_symbol column doesn't exist, create it from coin_symbol
        if "coinalyze_symbol" not in df_filtered.columns:
            df_filtered["coinalyze_symbol"] = df_filtered["coin_symbol"]

        # Validate data quality
        null_oi = df_filtered["oi_close"].isna().sum()
        if null_oi > 0:
            print(f"    ⚠️  Found {null_oi} rows with null OI values (will be filtered later)")

        print(
            f"    ✓ Loaded {len(df_filtered)} OI records for {df_filtered['coin_symbol'].nunique()} symbols"
        )
        print(
            f"    Date range: {df_filtered['date'].min().date()} to {df_filtered['date'].max().date()}"
        )

        result = (
            df_filtered[["coin_symbol", "coinalyze_symbol", "date", "oi_close"]]
            .sort_values(["coin_symbol", "date"])
            .reset_index(drop=True)
        )

        return result

    except Exception as e:
        print(f"    ❌ Error loading aggregated OI data: {e}")
        import traceback

        traceback.print_exc()
        return pd.DataFrame()


def _fetch_oi_history_for_universe(
    universe_symbols: List[str],
    exchange_code: str = "A",
    days: int = 200,
) -> pd.DataFrame:
    """Fetch daily OI USD history for given trading symbols' bases.

    Args:
        universe_symbols: List of trading symbols (e.g., ['BTC/USDC:USDC', 'ETH/USDC:USDC'])
        exchange_code: Exchange code - use 'A' for aggregate (default, recommended)
        days: Number of days of history to fetch

    Default exchange_code='A' fetches aggregate OI across all exchanges using format:
    BTCUSDT_PERP.A, ETHUSDT_PERP.A, etc.

    Returns columns: ['coin_symbol','coinalyze_symbol','date','oi_close']
    """
    try:
        from data.scripts.coinalyze_client import CoinalyzeClient  # type: ignore
    except Exception:
        return pd.DataFrame()

    client = CoinalyzeClient()

    # Map base -> coinalyze symbol
    # For aggregate (A), always use USDT format regardless of trading pair quote
    base_to_csym: Dict[str, str] = {}
    for tsym in universe_symbols:
        base, quote = _parse_trading_symbol(tsym)
        if not base:
            continue
        # Use aggregate format by default for robust cross-exchange signals
        c_sym = _build_coinalyze_symbol(base, quote="USDT", exchange_code=exchange_code)
        base_to_csym.setdefault(base, c_sym)

    if not base_to_csym:
        print(f"    No base_to_csym mapping created from universe")
        return pd.DataFrame()

    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=days)).timestamp())

    exchange_label = (
        "aggregate (all exchanges)" if exchange_code == "A" else f"exchange {exchange_code}"
    )
    print(f"    Fetching OI for {len(base_to_csym)} symbols ({exchange_label}, days={days})")
    print(f"    Using 'daily' interval with convert_to_usd=true")
    print(f"    Sample mappings: {list(base_to_csym.items())[:3]}")

    rows: List[dict] = []
    # Coinalyze allows up to 20 symbols per request
    items = list(base_to_csym.items())
    chunk = 20
    num_chunks = (len(items) + chunk - 1) // chunk
    estimated_time = num_chunks * 1.5
    print(
        f"    Rate limited to 40 calls/min: {num_chunks} API calls required (~{estimated_time:.0f}s total)"
    )

    for i in range(0, len(items), chunk):
        batch = items[i : i + chunk]
        symbols_param = ",".join(cs for _, cs in batch)
        try:
            data = client.get_open_interest_history(
                symbols=symbols_param,
                interval="daily",  # Use 'daily' as specified
                from_ts=start_ts,
                to_ts=end_ts,
                convert_to_usd=True,  # Always convert to USD
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
            csym = item.get("symbol")
            hist = item.get("history", [])
            base = csym_to_base.get(csym)
            if not base:
                continue
            for pt in hist:
                rows.append(
                    {
                        "coin_symbol": base,
                        "coinalyze_symbol": csym,
                        "date": datetime.fromtimestamp(pt["t"]).strftime("%Y-%m-%d"),
                        "oi_close": pt.get("c"),
                    }
                )
    if not rows:
        print(f"    No OI history rows collected")
        return pd.DataFrame()

    print(f"    Collected {len(rows)} OI history rows")
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["coin_symbol", "date"]).reset_index(drop=True)
    return df[["coin_symbol", "coinalyze_symbol", "date", "oi_close"]]


def strategy_oi_divergence(
    historical_data: Dict[str, pd.DataFrame],
    notional: float,
    mode: str = "trend",  # or 'divergence'
    lookback: int = 30,
    top_n: int = 10,
    bottom_n: int = 10,
    exchange_code: str = "A",  # 'A' = aggregate across all exchanges (recommended)
) -> Dict[str, float]:
    """Open Interest divergence/trend strategy using aggregated OI history.

    - Uses pre-downloaded aggregated OI data across all exchanges
    - Default format: [SYMBOL]USDT_PERP.A (e.g., BTCUSDT_PERP.A)
    - Filters universe to top 150 by market cap to optimize computation
    - Builds OI z-score vs price returns over a rolling window
    - Selects top/bottom by score
    - Allocates risk-parity within each side using recent price volatility

    Args:
        historical_data: Dict of symbol -> OHLCV dataframe
        notional: Total notional value to allocate
        mode: 'trend' (follow OI momentum) or 'divergence' (fade OI moves)
        lookback: Rolling window for z-score calculation (default 30 days)
        top_n: Number of long positions
        bottom_n: Number of short positions
        exchange_code: 'A' for aggregate (default), 'H' for Hyperliquid only, etc.

    Note: Recommended to use exchange_code='A' (aggregate) for robust signals
    across all exchanges. Format is [SYMBOL]USDT_PERP.A per Coinalyze docs.
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

    # Filter to top 150 by market cap to reduce Coinalyze API calls
    print(f"    Filtering universe from {len(universe_symbols)} to top 150 by market cap...")
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
                print(f"    Filtered to {len(top_150_symbols)} symbols with top market caps")
                universe_symbols = top_150_symbols
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
    # Format: [SYMBOL]USDT_PERP.A (e.g., BTCUSDT_PERP.A) per Coinalyze docs
    days_needed = max(lookback * 4, 120)
    exchange_label = (
        "aggregate (all exchanges)" if exchange_code == "A" else f"exchange {exchange_code}"
    )
    print(f"    Using aggregated OI data ({exchange_label})")
    print(f"    Format: [SYMBOL]USDT_PERP.A (e.g., BTCUSDT_PERP.A)")
    oi_df = _load_aggregated_oi_from_file(universe_symbols, days=days_needed)

    if oi_df is None or oi_df.empty:
        print("  ⚠️  OI DIVERGENCE STRATEGY: No aggregated OI data available!")
        print(f"       Aggregated OI data provides signals across all exchanges")
        print(f"       Make sure aggregated OI data file exists in data/raw/")
        print(f"       File pattern: historical_open_interest_all_perps_since2020_*.csv")
        return {}

    # Check if OI data is same day as execution
    today = pd.Timestamp(datetime.now().date())
    oi_latest_date = oi_df["date"].max()
    days_behind = (today - oi_latest_date).days

    if days_behind > 0:
        print(f"  ⚠️  OI DIVERGENCE STRATEGY: OI data is {days_behind} day(s) behind")
        print(f"       Today: {today.date()}")
        print(f"       Latest OI data: {oi_latest_date.date()}")
        print(f"       Strategy will use data from {oi_latest_date.date()} for signal generation")
        if days_behind > 2:
            print(f"       🔴 CRITICAL: Data is significantly stale - signals may be unreliable")
            print(f"       Strongly recommend refreshing OI data before trading")
    elif days_behind < 0:
        print(f"  ⚠️  OI DIVERGENCE STRATEGY: OI data has future dates!")
        print(f"       This is unexpected and may indicate data quality issues")

    # Compute scores
    from signals.calc_open_interest_divergence import (
        compute_oi_divergence_scores,
        build_equal_or_risk_parity_weights,
    )

    # Check date overlap before computing scores
    oi_dates = set(oi_df["date"].dt.date)
    price_dates = set(price_df["date"].dt.date)
    overlap_dates = oi_dates & price_dates

    if not overlap_dates:
        print(f"  ⚠️  OI DIVERGENCE STRATEGY: No date overlap between OI and price data!")
        print(f"       OI date range: {oi_df['date'].min().date()} to {oi_df['date'].max().date()}")
        print(
            f"       Price date range: {price_df['date'].min().date()} to {price_df['date'].max().date()}"
        )
        return {}

    print(
        f"    Date overlap: {min(overlap_dates)} to {max(overlap_dates)} ({len(overlap_dates)} days)"
    )

    scores = compute_oi_divergence_scores(oi_df, price_df, lookback=lookback)
    if scores.empty:
        print(f"  ⚠️  OI DIVERGENCE STRATEGY: No scores computed (merge produced empty dataframe)")
        return {}

    # Pick on latest date present across both
    latest_date = min(price_df["date"].max(), oi_df["date"].max())
    today = pd.Timestamp(datetime.now().date())

    # Warn if using historical data instead of today's data
    days_behind = (today - latest_date).days
    if days_behind > 0:
        print(f"    ⚠️  Generating signals from {latest_date.date()} (today is {today.date()})")
        print(f"    Signals are {days_behind} day(s) behind current date")

    day_scores = scores[scores["date"] == latest_date]
    if day_scores.empty:
        # fallback to last available in scores
        print(f"    ⚠️  No scores for latest date {latest_date.date()}, using most recent available")
        latest_date = scores["date"].max()
        day_scores = scores[scores["date"] == latest_date]
        print(f"    Using scores from {latest_date.date()}")

        # Additional warning if falling back to even older data
        days_behind = (today - latest_date).days
        if days_behind > 2:
            print(
                f"    🔴 WARNING: Fallback data is {days_behind} days old - signals highly unreliable"
            )
    col = "score_trend" if mode == "trend" else "score_divergence"
    day_scores = day_scores[["symbol", col]].dropna()
    if day_scores.empty:
        return {}

    sel = day_scores.sort_values(col, ascending=False)
    long_bases = sel.head(max(0, int(top_n)))["symbol"].tolist()
    short_bases = sel.tail(max(0, int(bottom_n)))["symbol"].tolist()

    # Build risk-parity weights on base-level price data
    weights_base = build_equal_or_risk_parity_weights(
        price_df=price_df.rename(columns={"base_symbol": "symbol"})[["date", "symbol", "close"]],
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
