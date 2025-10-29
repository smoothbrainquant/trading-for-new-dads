import ccxt
import pandas as pd
from datetime import datetime
from pprint import pprint
from typing import List, Dict, Tuple

try:
    # Lazy import; only needed when using Coinalyze
    from data.scripts.coinalyze_client import CoinalyzeClient  # type: ignore
except Exception:
    # We will import inside functions to avoid hard failure on import
    CoinalyzeClient = None  # type: ignore


def fetch_binance_funding_rates(symbols=None, exchange_id="binance"):
    """
    DEPRECATED: Use fetch_coinalyze_aggregated_funding_rates() or
    fetch_coinalyze_funding_rates_for_universe() instead.

    This function is kept for backward compatibility but should not be used
    as it creates a dependency on Binance which may be geo-restricted.

    Fetch current funding rates from Binance for perpetual futures.

    Args:
        symbols: List of trading pairs (e.g., ['BTC/USDT:USDT', 'ETH/USDT:USDT'])
                 If None, fetches all available funding rates
        exchange_id: Exchange to use ('binance' or 'binanceus')

    Returns:
        DataFrame with columns: symbol, funding_rate, funding_time, next_funding_time

    Note:
        - Binance may be geo-restricted in some locations
        - Use exchange_id='binanceus' if you're in the US
        - Funding occurs every 8 hours (00:00, 08:00, 16:00 UTC)
        - Positive funding rate = longs pay shorts
        - Negative funding rate = shorts pay longs
    """
    # Initialize Binance exchange
    exchange_class = getattr(ccxt, exchange_id)
    exchange = exchange_class(
        {
            "enableRateLimit": True,
            "options": {
                "defaultType": "future",  # Use futures market
            },
        }
    )

    try:
        if symbols:
            # Fetch funding rates for specific symbols
            funding_data = []
            for symbol in symbols:
                try:
                    print(f"Fetching funding rate for {symbol}...")
                    funding_rate = exchange.fetch_funding_rate(symbol)
                    funding_data.append(funding_rate)
                except Exception as e:
                    print(f"Error fetching funding rate for {symbol}: {str(e)}")
        else:
            # Fetch all funding rates
            print("Fetching all funding rates from Binance...")
            funding_rates = exchange.fetch_funding_rates()
            funding_data = list(funding_rates.values())

        # Convert to DataFrame
        if funding_data:
            df_data = []
            for item in funding_data:
                df_data.append(
                    {
                        "symbol": item.get("symbol"),
                        "funding_rate": item.get("fundingRate"),
                        "funding_rate_pct": item.get("fundingRate", 0)
                        * 100,  # Convert to percentage
                        "funding_timestamp": item.get("fundingTimestamp"),
                        "funding_time": (
                            pd.to_datetime(item.get("fundingTimestamp"), unit="ms")
                            if item.get("fundingTimestamp")
                            else None
                        ),
                        "next_funding_time": (
                            pd.to_datetime(item.get("nextFundingTime"), unit="ms")
                            if item.get("nextFundingTime")
                            else None
                        ),
                        "mark_price": item.get("markPrice"),
                        "index_price": item.get("indexPrice"),
                    }
                )

            df = pd.DataFrame(df_data)
            df = df.sort_values("funding_rate", ascending=False).reset_index(drop=True)
            return df
        else:
            return pd.DataFrame(
                columns=[
                    "symbol",
                    "funding_rate",
                    "funding_rate_pct",
                    "funding_timestamp",
                    "funding_time",
                    "next_funding_time",
                    "mark_price",
                    "index_price",
                ]
            )

    except Exception as e:
        print(f"Error fetching funding rates: {str(e)}")
        raise


def fetch_binance_funding_history(symbol, limit=100):
    """
    DEPRECATED: This function creates a dependency on Binance which may be geo-restricted.

    This function is kept for backward compatibility but should not be used.
    Consider using Coinalyze historical funding rate endpoints instead.

    Fetch historical funding rates for a specific symbol.

    Args:
        symbol: Trading pair (e.g., 'BTC/USDT:USDT')
        limit: Number of historical records to fetch (default 100)

    Returns:
        DataFrame with historical funding rates
    """
    exchange = ccxt.binance(
        {
            "enableRateLimit": True,
            "options": {
                "defaultType": "future",
            },
        }
    )

    try:
        print(f"\nFetching funding rate history for {symbol}...")
        history = exchange.fetch_funding_rate_history(symbol, limit=limit)

        if history:
            df = pd.DataFrame(history)
            df["funding_time"] = pd.to_datetime(df["timestamp"], unit="ms")
            df["funding_rate_pct"] = df["fundingRate"] * 100
            df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)
            return df
        else:
            return pd.DataFrame()

    except Exception as e:
        print(f"Error fetching funding history for {symbol}: {str(e)}")
        raise


# -----------------------------
# Coinalyze integration
# -----------------------------


def _parse_trading_symbol(symbol: str) -> Tuple[str, str]:
    """
    Parse a trading symbol like 'BTC/USDC:USDC' into base and quote (e.g., ('BTC', 'USDC')).
    """
    if not isinstance(symbol, str) or "/" not in symbol:
        return symbol, ""
    base, rhs = symbol.split("/", 1)
    quote = rhs.split(":", 1)[0] if ":" in rhs else rhs
    return base, quote


def _build_coinalyze_symbol(base: str, quote: str, exchange_code: str) -> str:
    """
    Build Coinalyze futures-perpetual symbol given components.
    Format varies by exchange:
    - Hyperliquid (H): {BASE}.H  (e.g., BTC.H)
    - Binance (A): {BASE}{QUOTE}_PERP.A (e.g., BTCUSDT_PERP.A)
    """
    if exchange_code == "H":
        # Hyperliquid uses simple format: BTC.H
        return f"{base}.{exchange_code}"
    else:
        # Other exchanges like Binance use full format: BTCUSDT_PERP.A
        return f"{base}{quote}_PERP.{exchange_code}"


def fetch_coinalyze_aggregated_funding_rates(
    universe_symbols: List[str],
) -> pd.DataFrame:
    """
    Fetch AGGREGATED funding rates from Coinalyze using .A suffix.

    This uses Coinalyze's built-in aggregation across ALL major exchanges,
    providing market-wide funding rate signals (not exchange-specific).

    Format: [SYMBOL]USDT_PERP.A (e.g., BTCUSDT_PERP.A)
    The .A suffix indicates aggregated data across all exchanges on Coinalyze.

    Args:
        universe_symbols: List of trading symbols, e.g., ['BTC/USDC:USDC', 'ETH/USDC:USDC']

    Returns:
        DataFrame with columns: base, quote, funding_rate, funding_rate_pct, coinalyze_symbol
    """
    from data.scripts.coinalyze_client import CoinalyzeClient

    if not universe_symbols:
        return pd.DataFrame(
            columns=["base", "quote", "funding_rate", "funding_rate_pct", "coinalyze_symbol"]
        )

    client = CoinalyzeClient()

    # Build base symbols from universe
    base_symbols = set()
    for sym in universe_symbols:
        base, _ = _parse_trading_symbol(sym)
        if base:
            base_symbols.add(base)

    # Build aggregated symbols using .A suffix
    # Format: BTCUSDT_PERP.A for aggregated funding across all exchanges
    symbols_to_fetch = []
    base_to_symbol_map = {}
    for base in base_symbols:
        c_symbol = f"{base}USDT_PERP.A"
        symbols_to_fetch.append(c_symbol)
        base_to_symbol_map[c_symbol] = base

    # Fetch in chunks of 20 (Coinalyze API limit)
    all_rates = []
    chunk_size = 20
    for i in range(0, len(symbols_to_fetch), chunk_size):
        chunk = symbols_to_fetch[i : i + chunk_size]
        symbols_param = ",".join(chunk)

        try:
            data = client.get_funding_rate(symbols_param)
            if data:
                for item in data:
                    c_sym = item.get("symbol")
                    value = item.get("value")
                    if c_sym and value is not None:
                        base = base_to_symbol_map.get(c_sym)
                        if base:
                            all_rates.append(
                                {
                                    "base": base,
                                    "quote": "USDT",
                                    "coinalyze_symbol": c_sym,
                                    "funding_rate": float(value),
                                    "funding_rate_pct": float(value) * 100.0,
                                }
                            )
        except Exception as e:
            # Continue on error
            pass

    if not all_rates:
        return pd.DataFrame(
            columns=["base", "quote", "funding_rate", "funding_rate_pct", "coinalyze_symbol"]
        )

    df = pd.DataFrame(all_rates)

    # Sort by funding rate descending
    df = df.sort_values("funding_rate", ascending=False).reset_index(drop=True)

    return df


def fetch_coinalyze_funding_rates_for_universe(
    universe_symbols: List[str],
    exchange_code: str = "H",
) -> pd.DataFrame:
    """
    Fetch current funding rates from Coinalyze for a SPECIFIC exchange.

    Args:
        universe_symbols: List of trading symbols, e.g., ['BTC/USDC:USDC', 'ETH/USDC:USDC']
        exchange_code: Coinalyze exchange code (e.g., 'H' Hyperliquid, 'A' Binance)

    Returns:
        DataFrame with at least columns: base, quote, funding_rate, funding_rate_pct,
        update_timestamp, update_time, coinalyze_symbol
    """
    # Import here to avoid hard dependency when not used
    from data.scripts.coinalyze_client import CoinalyzeClient  # type: ignore

    if not universe_symbols:
        return pd.DataFrame(
            columns=[
                "base",
                "quote",
                "funding_rate",
                "funding_rate_pct",
                "update_timestamp",
                "update_time",
                "coinalyze_symbol",
            ]
        )

    # Build unique Coinalyze symbols for the provided universe
    pairs: Dict[str, Tuple[str, str]] = {}
    for sym in universe_symbols:
        base, quote = _parse_trading_symbol(sym)
        # Default to USDC if quote missing
        quote = quote or "USDC"
        c_symbol = _build_coinalyze_symbol(base, quote, exchange_code)
        pairs[c_symbol] = (base, quote)

    symbols_list = list(pairs.keys())
    client = CoinalyzeClient()

    # Coinalyze allows up to 20 symbols per request
    chunk_size = 20
    all_rows = []
    for i in range(0, len(symbols_list), chunk_size):
        chunk = symbols_list[i : i + chunk_size]
        symbols_param = ",".join(chunk)
        data = client.get_funding_rate(symbols_param)
        if not data:
            continue
        for item in data:
            c_sym = item.get("symbol")
            value = item.get("value")  # decimal per-period rate
            update = item.get("update")  # epoch ms
            if c_sym is None or value is None:
                continue
            base, quote = pairs.get(c_sym, ("", ""))
            all_rows.append(
                {
                    "coinalyze_symbol": c_sym,
                    "base": base,
                    "quote": quote,
                    "funding_rate": float(value),
                    "funding_rate_pct": float(value) * 100.0,
                    "update_timestamp": int(update) if update is not None else None,
                    "update_time": (
                        pd.to_datetime(int(update), unit="ms") if update is not None else None
                    ),
                }
            )

    df = pd.DataFrame(all_rows)
    # Sort similar to Binance helper for consistency (descending by rate)
    if not df.empty and "funding_rate" in df.columns:
        df = df.sort_values("funding_rate", ascending=False).reset_index(drop=True)

    # Warn if we got no data
    if df.empty:
        print(
            f"WARNING: Coinalyze returned no funding rate data for {len(symbols_list)} symbols (exchange={exchange_code})"
        )
        print(
            f"  Symbols requested: {symbols_list[:5]}..."
            if len(symbols_list) > 5
            else f"  Symbols requested: {symbols_list}"
        )

    return df


def print_funding_summary(df, top_n=20):
    """
    Print a formatted summary of funding rates.

    Args:
        df: DataFrame with funding rate data
        top_n: Number of top positive and negative rates to display
    """
    print("\n" + "=" * 100)
    print("PERPETUAL FUTURES FUNDING RATES")
    print("=" * 100)

    if df.empty:
        print("\nNo funding rate data available.")
        return

    print(f"\nTotal symbols: {len(df)}")
    print(f"Data fetched at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if "next_funding_time" in df.columns and not df["next_funding_time"].isna().all():
        next_funding = df["next_funding_time"].iloc[0]
        print(f"Next funding time: {next_funding}")

    # Summary statistics
    print(f"\nFunding Rate Statistics:")
    print(f"  Mean:   {df['funding_rate_pct'].mean():.4f}%")
    print(f"  Median: {df['funding_rate_pct'].median():.4f}%")
    print(f"  Min:    {df['funding_rate_pct'].min():.4f}%")
    print(f"  Max:    {df['funding_rate_pct'].max():.4f}%")

    # Top positive funding rates (long pays short)
    print(f"\n{'-' * 100}")
    print(f"TOP {top_n} HIGHEST FUNDING RATES (Long pays Short - expensive to be long)")
    print(f"{'-' * 100}")
    print(f"{'Symbol':<20} {'Funding Rate':<15} {'Annual Rate':<15} {'Mark Price':<15}")
    print(f"{'-' * 100}")

    top_positive = df.nlargest(top_n, "funding_rate_pct")
    for _, row in top_positive.iterrows():
        symbol = row["symbol"]
        funding_pct = row["funding_rate_pct"]
        # Funding occurs every 8 hours on Binance (3 times per day)
        annual_rate = funding_pct * 3 * 365
        mark_price = row.get("mark_price", "N/A")
        mark_price_str = (
            f"${mark_price:,.2f}" if isinstance(mark_price, (int, float)) else str(mark_price)
        )
        print(f"{symbol:<20} {funding_pct:>13.4f}%  {annual_rate:>13.2f}%  {mark_price_str:<15}")

    # Top negative funding rates (short pays long)
    print(f"\n{'-' * 100}")
    print(f"TOP {top_n} LOWEST FUNDING RATES (Short pays Long - expensive to be short)")
    print(f"{'-' * 100}")
    print(f"{'Symbol':<20} {'Funding Rate':<15} {'Annual Rate':<15} {'Mark Price':<15}")
    print(f"{'-' * 100}")

    top_negative = df.nsmallest(top_n, "funding_rate_pct")
    for _, row in top_negative.iterrows():
        symbol = row["symbol"]
        funding_pct = row["funding_rate_pct"]
        annual_rate = funding_pct * 3 * 365
        mark_price = row.get("mark_price", "N/A")
        mark_price_str = (
            f"${mark_price:,.2f}" if isinstance(mark_price, (int, float)) else str(mark_price)
        )
        print(f"{symbol:<20} {funding_pct:>13.4f}%  {annual_rate:>13.2f}%  {mark_price_str:<15}")

    print("=" * 100)


if __name__ == "__main__":
    print("Fetching funding rates via Coinalyze...")
    print("=" * 100)

    try:
        # Example universe of symbols to fetch funding rates for
        universe = [
            "BTC/USDC:USDC",
            "ETH/USDC:USDC",
            "SOL/USDC:USDC",
            "AVAX/USDC:USDC",
            "MATIC/USDC:USDC",
            "LINK/USDC:USDC",
            "UNI/USDC:USDC",
            "ATOM/USDC:USDC",
        ]

        # Option 1: Fetch aggregated funding rates (recommended)
        # Uses .A suffix: BTCUSDT_PERP.A for aggregated data across all exchanges
        print("\n1. Fetching AGGREGATED funding rates (market-wide signal using .A suffix)...")
        print("-" * 100)
        print("Format: [SYMBOL]USDT_PERP.A (e.g., BTCUSDT_PERP.A)")
        print("This uses Coinalyze's built-in aggregation across all exchanges\n")

        df_aggregated = fetch_coinalyze_aggregated_funding_rates(universe_symbols=universe)

        if not df_aggregated.empty:
            print(f"\nAggregated Funding Rates ({len(df_aggregated)} symbols):")
            print(df_aggregated.to_string(index=False))

            # Save to CSV
            output_file = "aggregated_funding_rates.csv"
            df_aggregated.to_csv(output_file, index=False)
            print(f"\n✓ Aggregated funding rates saved to {output_file}")
        else:
            print("⚠️  No aggregated funding data returned")

        # Option 2: Fetch exchange-specific funding rates (Hyperliquid example)
        print("\n\n2. Fetching HYPERLIQUID funding rates (exchange-specific)...")
        print("-" * 100)
        df_hyperliquid = fetch_coinalyze_funding_rates_for_universe(
            universe_symbols=universe, exchange_code="H"  # H=Hyperliquid
        )

        if not df_hyperliquid.empty:
            print(f"\nHyperliquid Funding Rates:")
            print(
                df_hyperliquid[["base", "funding_rate_pct", "update_time"]].to_string(index=False)
            )

            # Save to CSV
            output_file = "hyperliquid_funding_rates.csv"
            df_hyperliquid.to_csv(output_file, index=False)
            print(f"\n✓ Hyperliquid funding rates saved to {output_file}")
        else:
            print("⚠️  No Hyperliquid funding data returned")

        # Option 3: Fetch exchange-specific funding rates (Bybit example)
        print("\n\n3. Fetching BYBIT funding rates (exchange-specific)...")
        print("-" * 100)
        df_bybit = fetch_coinalyze_funding_rates_for_universe(
            universe_symbols=universe, exchange_code="D"  # D=Bybit
        )

        if not df_bybit.empty:
            print(f"\nBybit Funding Rates:")
            print(df_bybit[["base", "funding_rate_pct", "update_time"]].to_string(index=False))

            # Save to CSV
            output_file = "bybit_funding_rates.csv"
            df_bybit.to_csv(output_file, index=False)
            print(f"\n✓ Bybit funding rates saved to {output_file}")
        else:
            print("⚠️  No Bybit funding data returned")

        print("\n" + "=" * 100)
        print("✓ All funding rates fetched successfully via Coinalyze")
        print("=" * 100)
        print("\nNOTE: This script uses Coinalyze API exclusively (no Binance dependency)")
        print("      Aggregated rates use .A suffix (e.g., BTCUSDT_PERP.A)")
        print("      Set COINALYZE_API environment variable to use this functionality")

    except Exception as e:
        print(f"\n⚠️  Error fetching funding rates: {str(e)}")
        print("\nTroubleshooting:")
        print("  1. Ensure COINALYZE_API environment variable is set")
        print("  2. Check your Coinalyze API subscription and rate limits")
        print("  3. Verify the symbols exist on Coinalyze")
        raise
