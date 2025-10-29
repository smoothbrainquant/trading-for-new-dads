#!/usr/bin/env python3
"""
Coinalyze API Demo - Practical Examples
"""
from coinalyze_client_updated import CoinalyzeClient
from datetime import datetime, timedelta


def main():
    print("=" * 80)
    print("COINALYZE API - PRACTICAL EXAMPLES")
    print("=" * 80)

    client = CoinalyzeClient()

    # Example 1: Find top BTC perpetuals by exchange
    print("\n📊 Example 1: BTC Perpetuals Across Exchanges")
    print("-" * 80)

    futures = client.get_future_markets()
    if futures:
        btc_perps = [
            f
            for f in futures
            if f["base_asset"] == "BTC"
            and f["quote_asset"] in ["USDT", "USD"]
            and f["is_perpetual"]
        ]

        print(f"Found {len(btc_perps)} BTC perpetual contracts\n")
        print(f"{'Symbol':<25} {'Exchange':<15} {'Has OI Data':<15} {'Has L/S Ratio'}")
        print("-" * 80)

        for perp in btc_perps[:10]:
            exch = next(
                (e["name"] for e in client.get_exchanges() if e["code"] == perp["exchange"]),
                "Unknown",
            )
            print(
                f"{perp['symbol']:<25} {exch:<15} {str(perp.get('has_ohlcv_data', False)):<15} {perp.get('has_long_short_ratio_data', False)}"
            )

    # Example 2: Get current funding rates for major pairs
    print("\n\n💰 Example 2: Current Funding Rates (Major Pairs)")
    print("-" * 80)

    # Find symbols for BTC and ETH on Binance
    if futures:
        binance_symbols = [
            f["symbol"]
            for f in futures
            if f["exchange"] == "A"  # Binance
            and f["base_asset"] in ["BTC", "ETH"]
            and f["quote_asset"] == "USDT"
            and f["is_perpetual"]
        ][:2]

        if binance_symbols:
            symbols_str = ",".join(binance_symbols)
            fr_data = client.get_funding_rate(symbols_str)

            if fr_data:
                print(f"{'Symbol':<25} {'Funding Rate':<20} {'Update Time'}")
                print("-" * 80)
                for item in fr_data:
                    fr_pct = item["value"] * 100
                    update_time = datetime.fromtimestamp(item["update"] / 1000).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    print(f"{item['symbol']:<25} {fr_pct:>7.4f}%{' '*12} {update_time}")

    # Example 3: Get current open interest
    print("\n\n📈 Example 3: Current Open Interest (BTC & ETH)")
    print("-" * 80)

    if binance_symbols:
        symbols_str = ",".join(binance_symbols)
        oi_data = client.get_open_interest(symbols_str)

        if oi_data:
            print(f"{'Symbol':<25} {'Open Interest':<20} {'Update Time'}")
            print("-" * 80)
            for item in oi_data:
                update_time = datetime.fromtimestamp(item["update"] / 1000).strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                print(f"{item['symbol']:<25} {item['value']:>15,.2f}{' '*5} {update_time}")

    # Example 4: Get historical data
    print("\n\n📉 Example 4: 7-Day Historical Open Interest (BTC)")
    print("-" * 80)

    if binance_symbols:
        btc_symbol = binance_symbols[0]

        end_ts = int(datetime.now().timestamp())
        start_ts = int((datetime.now() - timedelta(days=7)).timestamp())

        oi_hist = client.get_open_interest_history(
            symbols=btc_symbol, interval="daily", from_ts=start_ts, to_ts=end_ts
        )

        if oi_hist and len(oi_hist) > 0:
            history = oi_hist[0].get("history", [])
            print(f"Symbol: {oi_hist[0]['symbol']}")
            print(f"Data points: {len(history)}\n")

            print(f"{'Date':<15} {'Open':<15} {'High':<15} {'Low':<15} {'Close':<15}")
            print("-" * 80)

            for point in history:
                date = datetime.fromtimestamp(point["t"]).strftime("%Y-%m-%d")
                print(
                    f"{date:<15} {point['o']:>12,.0f}   {point['h']:>12,.0f}   {point['l']:>12,.0f}   {point['c']:>12,.0f}"
                )

    # Example 5: Get OHLCV price data
    print("\n\n🕯️  Example 5: 7-Day OHLCV Price Data (BTC)")
    print("-" * 80)

    if binance_symbols:
        btc_symbol = binance_symbols[0]

        end_ts = int(datetime.now().timestamp())
        start_ts = int((datetime.now() - timedelta(days=7)).timestamp())

        ohlcv = client.get_ohlcv_history(
            symbols=btc_symbol, interval="daily", from_ts=start_ts, to_ts=end_ts
        )

        if ohlcv and len(ohlcv) > 0:
            history = ohlcv[0].get("history", [])
            print(f"Symbol: {ohlcv[0]['symbol']}")
            print(f"Candles: {len(history)}\n")

            print(
                f"{'Date':<15} {'Open':<12} {'High':<12} {'Low':<12} {'Close':<12} {'Volume':<15}"
            )
            print("-" * 80)

            for candle in history[-5:]:  # Last 5 days
                date = datetime.fromtimestamp(candle["t"]).strftime("%Y-%m-%d")
                print(
                    f"{date:<15} {candle['o']:>10.2f}   {candle['h']:>10.2f}   {candle['l']:>10.2f}   {candle['c']:>10.2f}   {candle['v']:>12,.2f}"
                )

    # Example 6: Find all available ETH instruments
    print("\n\n🔍 Example 6: All ETH Perpetuals (First 10)")
    print("-" * 80)

    if futures:
        eth_perps = [f for f in futures if f["base_asset"] == "ETH" and f["is_perpetual"]][:10]

        exchanges = {e["code"]: e["name"] for e in client.get_exchanges()}

        print(f"{'Symbol':<30} {'Exchange':<20} {'Quote Asset':<15}")
        print("-" * 80)

        for perp in eth_perps:
            exch_name = exchanges.get(perp["exchange"], "Unknown")
            print(f"{perp['symbol']:<30} {exch_name:<20} {perp['quote_asset']:<15}")

    print("\n" + "=" * 80)
    print("🎉 Demo Complete! All endpoints working correctly.")
    print("=" * 80)
    print("\nNext steps:")
    print("  • Modify examples for your specific use case")
    print("  • Add your own trading logic")
    print("  • Export data to CSV or database")
    print("  • Build monitoring or alerting systems")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
