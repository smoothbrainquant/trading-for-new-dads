#!/usr/bin/env python3
"""
Coinalyze API Client
Simple Python client for interacting with Coinalyze API
"""
import os
import requests
import time
from typing import Optional, List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CoinalyzeClient:
    """Client for Coinalyze API"""
    
    BASE_URL = "https://api.coinalyze.net/v1"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Coinalyze API client
        
        Args:
            api_key: API key for authentication. If None, will try to get from COINALYZE_API env var
        """
        self.api_key = api_key or os.environ.get('COINALYZE_API')
        if not self.api_key:
            raise ValueError("API key required. Set COINALYZE_API env var or pass api_key parameter")
        
        self.session = requests.Session()
        self.session.headers.update({'api_key': self.api_key})
        
        self._last_request_time = 0
        self._min_request_interval = 1.5  # seconds between requests to avoid rate limiting
    
    def _rate_limit(self):
        """Implement rate limiting between requests"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def _request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> tuple[bool, Any]:
        """
        Make API request with rate limiting and error handling
        
        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters
            
        Returns:
            Tuple of (success: bool, data: Any)
        """
        self._rate_limit()
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                return True, response.json()
            elif response.status_code == 429:
                logger.warning("Rate limited by API. Consider increasing delay between requests.")
                return False, {"error": "rate_limited", "message": response.text}
            elif response.status_code == 400:
                logger.error(f"Bad request: {response.text}")
                return False, {"error": "bad_request", "message": response.text}
            elif response.status_code == 404:
                logger.error(f"Endpoint not found: {endpoint}")
                return False, {"error": "not_found", "message": "Endpoint not found"}
            else:
                logger.error(f"API error {response.status_code}: {response.text}")
                return False, {"error": f"http_{response.status_code}", "message": response.text}
                
        except requests.exceptions.Timeout:
            logger.error("Request timeout")
            return False, {"error": "timeout", "message": "Request timeout"}
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return False, {"error": "request_failed", "message": str(e)}
    
    def get_exchanges(self) -> Optional[List[Dict[str, str]]]:
        """
        Get list of all supported exchanges
        
        Returns:
            List of exchanges with 'code' and 'name' fields, or None on error
            
        Example:
            [
                {'code': 'A', 'name': 'Binance'},
                {'code': '6', 'name': 'Bybit'},
                ...
            ]
        """
        success, data = self._request("exchanges")
        return data if success else None
    
    def get_open_interest(self, symbols: str) -> Optional[List[Dict]]:
        """
        Get open interest data for specified symbols
        
        Args:
            symbols: Comma-separated list of symbols
            
        Returns:
            List of open interest data, or None on error
            
        Note:
            The correct symbol format is currently unknown.
            Tested formats (BTCUSDT, A_BTCUSDT, BTC) return empty arrays.
        """
        success, data = self._request("open-interest", params={'symbols': symbols})
        return data if success else None
    
    def get_funding_rate(self, symbols: str) -> Optional[List[Dict]]:
        """
        Get funding rate data for specified symbols
        
        Args:
            symbols: Comma-separated list of symbols
            
        Returns:
            List of funding rate data, or None on error
            
        Note:
            The correct symbol format is currently unknown.
            Tested formats (BTCUSDT, A_BTCUSDT, BTC) return empty arrays.
        """
        success, data = self._request("funding-rate", params={'symbols': symbols})
        return data if success else None
    
    def print_exchanges(self):
        """Print all supported exchanges in a formatted way"""
        exchanges = self.get_exchanges()
        
        if exchanges:
            print(f"\n{'='*60}")
            print(f"COINALYZE SUPPORTED EXCHANGES ({len(exchanges)} total)")
            print(f"{'='*60}")
            print(f"{'Code':<6} {'Name':<30}")
            print(f"{'-'*60}")
            
            for ex in exchanges:
                print(f"{ex['code']:<6} {ex['name']:<30}")
            
            print(f"{'='*60}\n")
        else:
            print("Failed to retrieve exchanges")


def main():
    """Example usage"""
    
    # Initialize client
    client = CoinalyzeClient()
    
    # Get and print exchanges
    print("\n1. Getting exchanges...")
    client.print_exchanges()
    
    # Try to get open interest (will likely return empty)
    print("\n2. Testing open interest endpoint...")
    oi_data = client.get_open_interest("BTCUSDT")
    print(f"Open interest data: {oi_data}")
    if not oi_data:
        print("   Note: Empty result - symbol format may be incorrect")
    
    # Try to get funding rate (will likely return empty)
    print("\n3. Testing funding rate endpoint...")
    fr_data = client.get_funding_rate("BTCUSDT")
    print(f"Funding rate data: {fr_data}")
    if not fr_data:
        print("   Note: Empty result - symbol format may be incorrect")
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print("Working endpoints:")
    print("  ✓ /exchanges - Returns list of 26 supported exchanges")
    print("\nPartially working (endpoint exists but returns empty data):")
    print("  ⚠ /open-interest - Requires correct symbol format")
    print("  ⚠ /funding-rate - Requires correct symbol format")
    print("\nNext steps:")
    print("  - Check Coinalyze documentation for correct symbol format")
    print("  - Verify API key permissions")
    print("  - Contact Coinalyze support for complete API documentation")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
