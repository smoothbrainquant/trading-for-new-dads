#!/usr/bin/env python3
"""
Test CoinMarketCap API Alternative Data Endpoints

This script tests various CMC API endpoints to explore what additional
alternative data is available beyond basic price/market cap data.

Potential data sources:
1. Social media metrics (Twitter, Reddit, etc.)
2. Developer activity (GitHub commits, etc.)
3. Exchange listings and trading pairs
4. Blockchain-specific metrics
5. Global aggregate metrics
6. Historical OHLCV data
7. Cryptocurrency metadata
"""

import requests
import pandas as pd
import json
import os
from datetime import datetime
import time


class CMCAlternativeDataTester:
    """Test various CoinMarketCap API endpoints for alternative data."""

    def __init__(self, api_key=None):
        """Initialize with API key."""
        self.api_key = api_key or os.environ.get("CMC_API")
        if not self.api_key:
            print("WARNING: No CMC_API key found. Some tests will fail.")
        
        self.base_url = "https://pro-api.coinmarketcap.com"
        self.headers = {
            "Accepts": "application/json",
            "X-CMC_PRO_API_KEY": self.api_key,
        }
        self.results = {}

    def test_endpoint(self, endpoint, params=None, description=""):
        """Test a specific API endpoint."""
        print(f"\n{'='*80}")
        print(f"Testing: {description}")
        print(f"Endpoint: {endpoint}")
        print(f"Params: {params}")
        print(f"{'='*80}")

        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=10)
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"? SUCCESS")
                
                # Show structure
                if "data" in data:
                    print(f"\nData type: {type(data['data'])}")
                    if isinstance(data['data'], list) and len(data['data']) > 0:
                        print(f"Number of items: {len(data['data'])}")
                        print(f"\nFirst item keys: {list(data['data'][0].keys())}")
                        print(f"\nSample data:")
                        print(json.dumps(data['data'][0], indent=2)[:1000])
                    elif isinstance(data['data'], dict):
                        print(f"\nData keys: {list(data['data'].keys())}")
                        print(f"\nSample data:")
                        print(json.dumps(data['data'], indent=2)[:1000])
                else:
                    print(f"\nResponse keys: {list(data.keys())}")
                    print(f"\nSample response:")
                    print(json.dumps(data, indent=2)[:1000])
                
                return {"status": "success", "data": data}
            else:
                print(f"? FAILED")
                try:
                    error_data = response.json()
                    print(f"Error: {error_data}")
                except:
                    print(f"Error: {response.text[:500]}")
                return {"status": "failed", "error": response.text}
        
        except Exception as e:
            print(f"? EXCEPTION: {e}")
            return {"status": "error", "error": str(e)}

    def test_cryptocurrency_info(self):
        """Test cryptocurrency metadata endpoint."""
        result = self.test_endpoint(
            "/v1/cryptocurrency/info",
            params={"symbol": "BTC,ETH,SOL"},
            description="Cryptocurrency Info/Metadata (logos, urls, description, tags)"
        )
        self.results["cryptocurrency_info"] = result
        time.sleep(0.5)

    def test_cryptocurrency_metadata(self):
        """Test cryptocurrency metadata with more details."""
        result = self.test_endpoint(
            "/v2/cryptocurrency/info",
            params={"symbol": "BTC"},
            description="Cryptocurrency Info v2 (enhanced metadata)"
        )
        self.results["cryptocurrency_metadata_v2"] = result
        time.sleep(0.5)

    def test_exchange_listings(self):
        """Test exchange listings endpoint."""
        result = self.test_endpoint(
            "/v1/exchange/listings/latest",
            params={"limit": "10"},
            description="Exchange Listings (exchange volume, rankings)"
        )
        self.results["exchange_listings"] = result
        time.sleep(0.5)

    def test_exchange_info(self):
        """Test exchange metadata."""
        result = self.test_endpoint(
            "/v1/exchange/info",
            params={"slug": "binance"},
            description="Exchange Info (specific exchange details)"
        )
        self.results["exchange_info"] = result
        time.sleep(0.5)

    def test_market_pairs(self):
        """Test market pairs endpoint."""
        result = self.test_endpoint(
            "/v1/cryptocurrency/market-pairs/latest",
            params={"symbol": "BTC", "limit": "5"},
            description="Market Pairs (where coin trades, liquidity by exchange)"
        )
        self.results["market_pairs"] = result
        time.sleep(0.5)

    def test_ohlcv_historical(self):
        """Test historical OHLCV data."""
        result = self.test_endpoint(
            "/v1/cryptocurrency/ohlcv/historical",
            params={"symbol": "BTC", "time_period": "daily", "count": "5"},
            description="Historical OHLCV (candle data)"
        )
        self.results["ohlcv_historical"] = result
        time.sleep(0.5)

    def test_global_metrics(self):
        """Test global cryptocurrency metrics."""
        result = self.test_endpoint(
            "/v1/global-metrics/quotes/latest",
            params={},
            description="Global Metrics (total market cap, BTC dominance, etc.)"
        )
        self.results["global_metrics"] = result
        time.sleep(0.5)

    def test_trending(self):
        """Test trending coins."""
        result = self.test_endpoint(
            "/v1/cryptocurrency/trending/latest",
            params={},
            description="Trending Cryptocurrencies (most visited)"
        )
        self.results["trending"] = result
        time.sleep(0.5)

    def test_gainers_losers(self):
        """Test gainers and losers."""
        result = self.test_endpoint(
            "/v1/cryptocurrency/trending/gainers-losers",
            params={"limit": "10"},
            description="Top Gainers & Losers"
        )
        self.results["gainers_losers"] = result
        time.sleep(0.5)

    def test_most_visited(self):
        """Test most visited coins."""
        result = self.test_endpoint(
            "/v1/cryptocurrency/trending/most-visited",
            params={"limit": "10"},
            description="Most Visited Coins (user interest metric)"
        )
        self.results["most_visited"] = result
        time.sleep(0.5)

    def test_recently_added(self):
        """Test recently added coins."""
        result = self.test_endpoint(
            "/v1/cryptocurrency/listings/new",
            params={"limit": "10"},
            description="Recently Added Coins (new listings)"
        )
        self.results["recently_added"] = result
        time.sleep(0.5)

    def test_price_performance_stats(self):
        """Test price performance statistics."""
        result = self.test_endpoint(
            "/v1/cryptocurrency/price-performance-stats/latest",
            params={"symbol": "BTC,ETH"},
            description="Price Performance Stats (all-time high, periods)"
        )
        self.results["price_performance"] = result
        time.sleep(0.5)

    def test_airdrops(self):
        """Test airdrops endpoint."""
        result = self.test_endpoint(
            "/v1/cryptocurrency/airdrops",
            params={"limit": "5"},
            description="Airdrops (upcoming/recent airdrops)"
        )
        self.results["airdrops"] = result
        time.sleep(0.5)

    def test_fiat_map(self):
        """Test fiat currency map."""
        result = self.test_endpoint(
            "/v1/fiat/map",
            params={},
            description="Fiat Currency Map"
        )
        self.results["fiat_map"] = result
        time.sleep(0.5)

    def run_all_tests(self):
        """Run all endpoint tests."""
        print("\n" + "="*80)
        print("COINMARKETCAP ALTERNATIVE DATA API TESTING")
        print("="*80)
        
        if not self.api_key:
            print("\n??  WARNING: No API key found. Tests will likely fail.")
            print("Set CMC_API environment variable to test real endpoints.\n")
        
        # Core metadata
        self.test_cryptocurrency_info()
        self.test_cryptocurrency_metadata()
        
        # Exchange data
        self.test_exchange_listings()
        self.test_market_pairs()
        
        # Historical data
        self.test_ohlcv_historical()
        
        # Market metrics
        self.test_global_metrics()
        self.test_price_performance_stats()
        
        # Trending/Interest metrics
        self.test_trending()
        self.test_gainers_losers()
        self.test_most_visited()
        self.test_recently_added()
        
        # Other
        self.test_airdrops()
        
        # Summarize results
        self.print_summary()

    def print_summary(self):
        """Print summary of all tests."""
        print("\n" + "="*80)
        print("SUMMARY OF API ENDPOINT TESTS")
        print("="*80)
        
        successful = []
        failed = []
        errors = []
        
        for endpoint, result in self.results.items():
            if result["status"] == "success":
                successful.append(endpoint)
            elif result["status"] == "failed":
                failed.append(endpoint)
            else:
                errors.append(endpoint)
        
        print(f"\n? Successful: {len(successful)}/{len(self.results)}")
        for ep in successful:
            print(f"   - {ep}")
        
        if failed:
            print(f"\n? Failed (API returned error): {len(failed)}")
            for ep in failed:
                print(f"   - {ep}")
        
        if errors:
            print(f"\n??  Errors (connection/exception): {len(errors)}")
            for ep in errors:
                print(f"   - {ep}")
        
        # Save results to file
        self.save_results()

    def save_results(self):
        """Save test results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"data/raw/cmc_api_test_results_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\n?? Full results saved to: {output_file}")

    def generate_data_catalog(self):
        """Generate a catalog of available alternative data."""
        print("\n" + "="*80)
        print("ALTERNATIVE DATA CATALOG")
        print("="*80)
        
        catalog = {
            "Metadata & Fundamentals": [
                "Cryptocurrency descriptions, tags, categories",
                "Website URLs, social media links",
                "Logo images",
                "Launch date, platform info",
            ],
            "Exchange & Liquidity": [
                "Exchange listings and rankings",
                "Market pairs per coin",
                "Liquidity by exchange",
                "Spread and depth data",
            ],
            "Historical Data": [
                "OHLCV candle data",
                "Historical quotes",
                "Price performance stats",
                "All-time high/low data",
            ],
            "Market Sentiment": [
                "Trending coins (most visited)",
                "Top gainers and losers",
                "Recently added coins",
                "Community interest metrics",
            ],
            "Global Metrics": [
                "Total market cap",
                "BTC dominance",
                "Active cryptocurrencies",
                "Active exchanges",
                "DeFi volume",
            ],
            "Events": [
                "Airdrops",
                "Token unlocks",
                "Upcoming events",
            ],
        }
        
        for category, items in catalog.items():
            print(f"\n?? {category}:")
            for item in items:
                print(f"   ? {item}")


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Test CoinMarketCap Alternative Data Endpoints",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="CoinMarketCap API key (or set CMC_API env var)"
    )
    parser.add_argument(
        "--catalog-only",
        action="store_true",
        help="Only show data catalog without API calls"
    )
    
    args = parser.parse_args()
    
    tester = CMCAlternativeDataTester(api_key=args.api_key)
    
    if args.catalog_only:
        tester.generate_data_catalog()
    else:
        tester.run_all_tests()
        tester.generate_data_catalog()
    
    print("\n" + "="*80)
    print("TESTING COMPLETE")
    print("="*80)
    print("\n?? Next steps:")
    print("   1. Review successful endpoints in the summary above")
    print("   2. Check the JSON output file for detailed responses")
    print("   3. Identify which alternative data sources are useful for trading")
    print("   4. Implement data collectors for promising endpoints")
    print("\n")


if __name__ == "__main__":
    main()
