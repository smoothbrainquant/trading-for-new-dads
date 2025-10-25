"""
Tests for Data Collection Functions
Tests: ccxt, coinalyze, and coinmarketcap data collection
"""

import unittest
import sys
import os
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import data collection modules
from data.scripts.ccxt_get_data import ccxt_fetch_hyperliquid_daily_data
from data.scripts.coinalyze_client import CoinalyzeClient
from data.scripts.fetch_coinmarketcap_data import (
    fetch_coinmarketcap_data,
    fetch_mock_marketcap_data,
    map_symbols_to_trading_pairs
)


class TestCCXTDataCollection(unittest.TestCase):
    """Test CCXT data collection functions"""
    
    @patch('ccxt.hyperliquid')
    def test_ccxt_fetch_returns_dataframe(self, mock_exchange_class):
        """Test that ccxt_fetch_hyperliquid_daily_data returns a DataFrame"""
        # Mock the exchange instance
        mock_exchange = MagicMock()
        mock_exchange_class.return_value = mock_exchange
        
        # Mock parse8601 to return a timestamp
        mock_exchange.parse8601.return_value = int((datetime.now() - timedelta(days=5)).timestamp() * 1000)
        
        # Mock OHLCV data
        mock_ohlcv = [
            [int(datetime.now().timestamp() * 1000), 100, 110, 95, 105, 1000],
            [int((datetime.now() + timedelta(days=1)).timestamp() * 1000), 105, 115, 100, 110, 1500],
        ]
        mock_exchange.fetch_ohlcv.return_value = mock_ohlcv
        
        # Call function
        result = ccxt_fetch_hyperliquid_daily_data(symbols=['BTC/USDC:USDC'], days=5)
        
        # Assertions
        self.assertIsInstance(result, pd.DataFrame)
        self.assertIn('date', result.columns)
        self.assertIn('symbol', result.columns)
        self.assertIn('close', result.columns)
        self.assertIn('volume', result.columns)
    
    @patch('ccxt.hyperliquid')
    def test_ccxt_fetch_handles_empty_symbols(self, mock_exchange_class):
        """Test that function handles empty symbol list"""
        mock_exchange = MagicMock()
        mock_exchange_class.return_value = mock_exchange
        mock_exchange.parse8601.return_value = int(datetime.now().timestamp() * 1000)
        
        result = ccxt_fetch_hyperliquid_daily_data(symbols=[], days=5)
        
        # Should return empty DataFrame with correct schema
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 0)
        self.assertIn('date', result.columns)
        self.assertIn('symbol', result.columns)
    
    @patch('ccxt.hyperliquid')
    def test_ccxt_fetch_handles_error(self, mock_exchange_class):
        """Test that function handles API errors gracefully"""
        mock_exchange = MagicMock()
        mock_exchange_class.return_value = mock_exchange
        mock_exchange.parse8601.return_value = int(datetime.now().timestamp() * 1000)
        mock_exchange.fetch_ohlcv.side_effect = Exception("API Error")
        
        # Should not raise exception, but return empty DataFrame
        result = ccxt_fetch_hyperliquid_daily_data(symbols=['BTC/USDC:USDC'], days=5)
        
        self.assertIsInstance(result, pd.DataFrame)


class TestCoinalyzeClient(unittest.TestCase):
    """Test Coinalyze API client functions"""
    
    def test_client_requires_api_key(self):
        """Test that CoinalyzeClient requires an API key"""
        # Remove any existing API key from environment
        original_key = os.environ.get('COINALYZE_API')
        if 'COINALYZE_API' in os.environ:
            del os.environ['COINALYZE_API']
        
        try:
            # Should raise ValueError if no API key provided
            with self.assertRaises(ValueError):
                CoinalyzeClient(api_key=None)
        finally:
            # Restore original API key
            if original_key:
                os.environ['COINALYZE_API'] = original_key
    
    def test_client_accepts_api_key(self):
        """Test that CoinalyzeClient accepts an API key"""
        # Should not raise exception
        client = CoinalyzeClient(api_key='test_key')
        self.assertEqual(client.api_key, 'test_key')
        self.assertIsNotNone(client.session)
    
    @patch('requests.Session.get')
    def test_get_exchanges_returns_data(self, mock_get):
        """Test that get_exchanges returns exchange data"""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {'name': 'Binance', 'code': 'A'},
            {'name': 'Coinbase', 'code': 'C'}
        ]
        mock_get.return_value = mock_response
        
        client = CoinalyzeClient(api_key='test_key')
        result = client.get_exchanges()
        
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        self.assertIn('name', result[0])
        self.assertIn('code', result[0])
    
    @patch('requests.Session.get')
    def test_get_funding_rate_history_format(self, mock_get):
        """Test that get_funding_rate_history returns correct format"""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                'symbol': 'BTCUSDT_PERP.A',
                'history': [[1609459200, 0.0001], [1609545600, 0.00015]]
            }
        ]
        mock_get.return_value = mock_response
        
        client = CoinalyzeClient(api_key='test_key')
        
        now = int(datetime.now().timestamp())
        week_ago = int((datetime.now() - timedelta(days=7)).timestamp())
        
        result = client.get_funding_rate_history(
            symbols='BTCUSDT_PERP.A',
            interval='daily',
            from_ts=week_ago,
            to_ts=now
        )
        
        self.assertIsInstance(result, list)
        if result:
            self.assertIn('symbol', result[0])
            self.assertIn('history', result[0])


class TestCoinMarketCapDataCollection(unittest.TestCase):
    """Test CoinMarketCap data collection functions"""
    
    def test_fetch_mock_marketcap_data(self):
        """Test that fetch_mock_marketcap_data generates valid data"""
        df = fetch_mock_marketcap_data(limit=10)
        
        # Check DataFrame properties
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 10)
        
        # Check required columns
        required_columns = ['symbol', 'name', 'cmc_rank', 'market_cap', 
                          'price', 'volume_24h', 'timestamp']
        for col in required_columns:
            self.assertIn(col, df.columns)
        
        # Check data validity
        self.assertEqual(df['cmc_rank'].iloc[0], 1)
        self.assertTrue(all(df['market_cap'] > 0))
        self.assertTrue(all(df['price'] > 0))
    
    def test_fetch_mock_marketcap_follows_power_law(self):
        """Test that mock data follows power law distribution"""
        df = fetch_mock_marketcap_data(limit=50)
        
        # First rank should have much higher market cap than 50th
        first_mc = df[df['cmc_rank'] == 1]['market_cap'].iloc[0]
        last_mc = df[df['cmc_rank'] == 50]['market_cap'].iloc[0]
        
        self.assertGreater(first_mc, last_mc * 10)
    
    @patch('requests.get')
    def test_fetch_coinmarketcap_data_with_api(self, mock_get):
        """Test fetch_coinmarketcap_data with mocked API response"""
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [
                {
                    'symbol': 'BTC',
                    'name': 'Bitcoin',
                    'cmc_rank': 1,
                    'quote': {
                        'USD': {
                            'market_cap': 1000000000000,
                            'price': 50000,
                            'volume_24h': 30000000000,
                            'percent_change_24h': 2.5,
                            'percent_change_7d': 5.0,
                            'market_cap_dominance': 45.0
                        }
                    }
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        df = fetch_coinmarketcap_data(api_key='test_key', limit=1)
        
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 1)
        self.assertEqual(df['symbol'].iloc[0], 'BTC')
        self.assertEqual(df['cmc_rank'].iloc[0], 1)
    
    @patch('requests.get')
    def test_fetch_coinmarketcap_falls_back_to_mock(self, mock_get):
        """Test that function falls back to mock data on API error"""
        # Mock API error with RequestException
        import requests
        mock_get.side_effect = requests.exceptions.RequestException("API Error")
        
        # Should not raise exception, should return mock data
        df = fetch_coinmarketcap_data(api_key='test_key', limit=10)
        
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 10)
    
    def test_map_symbols_to_trading_pairs(self):
        """Test symbol to trading pair mapping"""
        df = pd.DataFrame({
            'symbol': ['BTC', 'ETH', 'SOL'],
            'market_cap': [1000, 500, 100]
        })
        
        result = map_symbols_to_trading_pairs(df, trading_suffix='/USDC:USDC')
        
        self.assertIn('trading_symbol', result.columns)
        self.assertEqual(result['trading_symbol'].iloc[0], 'BTC/USDC:USDC')
        self.assertEqual(result['trading_symbol'].iloc[1], 'ETH/USDC:USDC')


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
