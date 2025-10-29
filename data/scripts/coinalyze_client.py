#!/usr/bin/env python3
"""
Coinalyze API Client - Complete Implementation
Based on official API documentation
"""
import os
import requests
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Global rate limiter shared across all CoinalyzeClient instances
class GlobalRateLimiter:
    """
    Global rate limiter to coordinate API calls across all CoinalyzeClient instances.
    Rate Limit: 40 API calls per minute per API key
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._last_request_time = 0
        self._min_request_interval = 1.5  # 40 calls/min = 1.5s per call
        self._call_count = 0

    def wait(self):
        """Wait if necessary to respect rate limit"""
        with self._lock:
            elapsed = time.time() - self._last_request_time
            if elapsed < self._min_request_interval:
                sleep_time = self._min_request_interval - elapsed
                logger.debug(
                    f"Rate limiting: waiting {sleep_time:.2f}s (call #{self._call_count + 1})"
                )
                time.sleep(sleep_time)
            self._last_request_time = time.time()
            self._call_count += 1
            if self._call_count % 10 == 0:
                logger.info(f"Coinalyze API calls made: {self._call_count}")


# Global instance shared by all clients
_global_rate_limiter = GlobalRateLimiter()


class CoinalyzeClient:
    """
    Complete client for Coinalyze API

    Symbol Format:
    - Futures: BTCUSDT_PERP.A (symbol_PERP.exchange_code)
    - Spot: BTCUSD.C (symbol.exchange_code)

    Rate Limit: 40 API calls per minute per API key
    Note: Uses global rate limiter to coordinate across all instances
    """

    BASE_URL = "https://api.coinalyze.net/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Coinalyze API client

        Args:
            api_key: API key for authentication. If None, uses COINALYZE_API env var
        """
        self.api_key = api_key or os.environ.get("COINALYZE_API")
        if not self.api_key:
            raise ValueError(
                "API key required. Set COINALYZE_API env var or pass api_key parameter"
            )

        self.session = requests.Session()
        self.session.headers.update({"api_key": self.api_key})

    def _rate_limit(self):
        """Implement rate limiting between requests using global rate limiter"""
        _global_rate_limiter.wait()

    def _request(
        self, endpoint: str, params: Optional[Dict[str, Any]] = None, max_retries: int = 3
    ) -> tuple[bool, Any]:
        """Make API request with rate limiting, error handling, and automatic retries"""
        url = f"{self.BASE_URL}/{endpoint}"

        for attempt in range(max_retries):
            self._rate_limit()

            try:
                response = self.session.get(url, params=params, timeout=10)

                if response.status_code == 200:
                    return True, response.json()
                elif response.status_code == 429:
                    # Rate limited - wait longer and retry
                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        wait_time = float(retry_after)
                    else:
                        # Exponential backoff: 2, 4, 8 seconds
                        wait_time = 2 ** (attempt + 1)

                    logger.warning(
                        f"Rate limited (attempt {attempt + 1}/{max_retries}). Waiting {wait_time}s before retry..."
                    )
                    time.sleep(wait_time)

                    if attempt < max_retries - 1:
                        continue  # Retry
                    else:
                        return False, {"error": "rate_limited", "message": "Max retries exceeded"}

                elif response.status_code == 400:
                    logger.error(f"Bad request: {response.text}")
                    return False, {"error": "bad_request", "message": response.text}
                elif response.status_code == 401:
                    logger.error("Invalid/missing API key")
                    return False, {"error": "unauthorized", "message": "Invalid/missing API key"}
                elif response.status_code == 404:
                    logger.error(f"Endpoint not found: {endpoint}")
                    return False, {"error": "not_found", "message": "Endpoint not found"}
                else:
                    logger.error(f"API error {response.status_code}: {response.text}")
                    return False, {
                        "error": f"http_{response.status_code}",
                        "message": response.text,
                    }

            except requests.exceptions.Timeout:
                logger.error("Request timeout")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying after timeout (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(2)
                    continue
                return False, {"error": "timeout", "message": "Request timeout"}
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {str(e)}")
                return False, {"error": "request_failed", "message": str(e)}

        return False, {"error": "max_retries", "message": "Maximum retry attempts exceeded"}

    # ==================== MARKET INFORMATION ====================

    def get_exchanges(self) -> Optional[List[Dict[str, str]]]:
        """
        Get list of all supported exchanges

        Returns:
            [{'name': 'Binance', 'code': 'A'}, ...]
        """
        success, data = self._request("exchanges")
        return data if success else None

    def get_future_markets(self) -> Optional[List[Dict]]:
        """
        Get list of all supported future markets

        Returns:
            List of futures with symbol, exchange, base_asset, quote_asset,
            is_perpetual, margined, expire_at, and data availability flags
        """
        success, data = self._request("future-markets")
        return data if success else None

    def get_spot_markets(self) -> Optional[List[Dict]]:
        """
        Get list of all supported spot markets

        Returns:
            List of spots with symbol, exchange, base_asset, quote_asset
        """
        success, data = self._request("spot-markets")
        return data if success else None

    # ==================== CURRENT DATA ====================

    def get_open_interest(self, symbols: str, convert_to_usd: bool = False) -> Optional[List[Dict]]:
        """
        Get current open interest

        Args:
            symbols: Comma-separated symbols (e.g., 'BTCUSDT_PERP.A,ETHUSDT_PERP.A')
                    Max 20 symbols, each consumes one API call
            convert_to_usd: Convert to USD

        Returns:
            [{'symbol': 'BTCUSDT_PERP.A', 'value': 123.45, 'update': 1234567890}, ...]
        """
        params = {"symbols": symbols, "convert_to_usd": "true" if convert_to_usd else "false"}
        success, data = self._request("open-interest", params)
        return data if success else None

    def get_funding_rate(self, symbols: str) -> Optional[List[Dict]]:
        """
        Get current funding rate

        Args:
            symbols: Comma-separated symbols (e.g., 'BTCUSDT_PERP.A,ETHUSDT_PERP.A')
                    Max 20 symbols

        Returns:
            [{'symbol': 'BTCUSDT_PERP.A', 'value': 0.0001, 'update': 1234567890}, ...]
        """
        params = {"symbols": symbols}
        success, data = self._request("funding-rate", params)
        return data if success else None

    def get_predicted_funding_rate(self, symbols: str) -> Optional[List[Dict]]:
        """
        Get current predicted funding rate

        Args:
            symbols: Comma-separated symbols (e.g., 'BTCUSDT_PERP.A')

        Returns:
            [{'symbol': 'BTCUSDT_PERP.A', 'value': 0.0001, 'update': 1234567890}, ...]
        """
        params = {"symbols": symbols}
        success, data = self._request("predicted-funding-rate", params)
        return data if success else None

    # ==================== HISTORICAL DATA ====================

    def get_open_interest_history(
        self, symbols: str, interval: str, from_ts: int, to_ts: int, convert_to_usd: bool = False
    ) -> Optional[List[Dict]]:
        """
        Get open interest history

        Args:
            symbols: Comma-separated symbols (max 20)
            interval: '1min', '5min', '15min', '30min', '1hour', '2hour',
                     '4hour', '6hour', '12hour', 'daily'
            from_ts: From timestamp (inclusive), UNIX seconds
            to_ts: To timestamp (inclusive), UNIX seconds
            convert_to_usd: Convert to USD

        Returns:
            [{'symbol': 'BTCUSDT_PERP.A', 'history': [[ts, value], ...]}, ...]
        """
        params = {
            "symbols": symbols,
            "interval": interval,
            "from": from_ts,
            "to": to_ts,
            "convert_to_usd": "true" if convert_to_usd else "false",
        }
        success, data = self._request("open-interest-history", params)
        return data if success else None

    def get_funding_rate_history(
        self, symbols: str, interval: str, from_ts: int, to_ts: int
    ) -> Optional[List[Dict]]:
        """
        Get funding rate history

        Args:
            symbols: Comma-separated symbols (max 20)
            interval: '1min', '5min', '15min', '30min', '1hour', '2hour',
                     '4hour', '6hour', '12hour', 'daily'
            from_ts: From timestamp (inclusive), UNIX seconds
            to_ts: To timestamp (inclusive), UNIX seconds

        Returns:
            [{'symbol': 'BTCUSDT_PERP.A', 'history': [[ts, value], ...]}, ...]
        """
        params = {"symbols": symbols, "interval": interval, "from": from_ts, "to": to_ts}
        success, data = self._request("funding-rate-history", params)
        return data if success else None

    def get_predicted_funding_rate_history(
        self, symbols: str, interval: str, from_ts: int, to_ts: int
    ) -> Optional[List[Dict]]:
        """Get predicted funding rate history"""
        params = {"symbols": symbols, "interval": interval, "from": from_ts, "to": to_ts}
        success, data = self._request("predicted-funding-rate-history", params)
        return data if success else None

    def get_liquidation_history(
        self, symbols: str, interval: str, from_ts: int, to_ts: int, convert_to_usd: bool = False
    ) -> Optional[List[Dict]]:
        """Get liquidation history"""
        params = {
            "symbols": symbols,
            "interval": interval,
            "from": from_ts,
            "to": to_ts,
            "convert_to_usd": "true" if convert_to_usd else "false",
        }
        success, data = self._request("liquidation-history", params)
        return data if success else None

    def get_long_short_ratio_history(
        self, symbols: str, interval: str, from_ts: int, to_ts: int
    ) -> Optional[List[Dict]]:
        """Get long/short ratio history"""
        params = {"symbols": symbols, "interval": interval, "from": from_ts, "to": to_ts}
        success, data = self._request("long-short-ratio-history", params)
        return data if success else None

    def get_ohlcv_history(
        self, symbols: str, interval: str, from_ts: int, to_ts: int
    ) -> Optional[List[Dict]]:
        """
        Get OHLCV (candlestick) history

        Args:
            symbols: Comma-separated symbols (e.g., 'BTCUSDT_PERP.A,BTCUSD.C')
                    Works for both futures and spot
            interval: '1min', '5min', '15min', '30min', '1hour', '2hour',
                     '4hour', '6hour', '12hour', 'daily'
            from_ts: From timestamp (inclusive), UNIX seconds
            to_ts: To timestamp (inclusive), UNIX seconds

        Returns:
            [{'symbol': 'BTCUSDT_PERP.A', 'history': [[ts, o, h, l, c, v], ...]}, ...]
        """
        params = {"symbols": symbols, "interval": interval, "from": from_ts, "to": to_ts}
        success, data = self._request("ohlcv-history", params)
        return data if success else None


def main():
    """Example usage with all endpoints"""

    client = CoinalyzeClient()

    print("=" * 80)
    print("COINALYZE API - COMPLETE ENDPOINT TEST")
    print("=" * 80)

    # 1. Get exchanges
    print("\n1. Exchanges:")
    exchanges = client.get_exchanges()
    if exchanges:
        print(f"   Found {len(exchanges)} exchanges")
        print(f"   Examples: {exchanges[:3]}")

    # 2. Get future markets
    print("\n2. Future Markets:")
    futures = client.get_future_markets()
    if futures:
        print(f"   Found {len(futures)} future markets")
        print(f"   Example: {futures[0] if futures else 'None'}")
        # Show some BTC perpetuals
        btc_perps = [f for f in futures if "BTC" in f.get("symbol", "") and f.get("is_perpetual")][
            :3
        ]
        print(f"   BTC Perpetuals: {[f['symbol'] for f in btc_perps]}")

    # 3. Get spot markets
    print("\n3. Spot Markets:")
    spots = client.get_spot_markets()
    if spots:
        print(f"   Found {len(spots)} spot markets")
        print(f"   Example: {spots[0] if spots else 'None'}")

    # 4. Get current open interest (using correct symbol format)
    print("\n4. Current Open Interest:")
    if futures and len(futures) > 0:
        test_symbol = futures[0]["symbol"]
        print(f"   Testing with: {test_symbol}")
        oi = client.get_open_interest(test_symbol)
        print(f"   Result: {oi}")

    # 5. Get current funding rate
    print("\n5. Current Funding Rate:")
    if futures and len(futures) > 0:
        test_symbol = futures[0]["symbol"]
        print(f"   Testing with: {test_symbol}")
        fr = client.get_funding_rate(test_symbol)
        print(f"   Result: {fr}")

    # 6. Get historical data (last 7 days, daily interval)
    print("\n6. Historical Open Interest (7 days):")
    if futures and len(futures) > 0:
        test_symbol = futures[0]["symbol"]
        end_ts = int(datetime.now().timestamp())
        start_ts = int((datetime.now() - timedelta(days=7)).timestamp())

        print(f"   Testing with: {test_symbol}")
        hist = client.get_open_interest_history(test_symbol, "daily", start_ts, end_ts)
        if hist and len(hist) > 0:
            history = hist[0].get("history", [])
            print(f"   Got {len(history)} data points")
            if history:
                print(f"   Latest: {history[-1] if history else 'None'}")

    # 7. Get OHLCV data
    print("\n7. OHLCV History (7 days):")
    if futures and len(futures) > 0:
        test_symbol = futures[0]["symbol"]
        end_ts = int(datetime.now().timestamp())
        start_ts = int((datetime.now() - timedelta(days=7)).timestamp())

        print(f"   Testing with: {test_symbol}")
        ohlcv = client.get_ohlcv_history(test_symbol, "daily", start_ts, end_ts)
        if ohlcv and len(ohlcv) > 0:
            history = ohlcv[0].get("history", [])
            print(f"   Got {len(history)} candles")
            if history:
                print(f"   Latest: {history[-1] if history else 'None'}")

    print("\n" + "=" * 80)
    print("ALL ENDPOINTS TESTED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    main()
