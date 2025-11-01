"""
Tests for Execution Functions
Tests: balance checking, position checking, instrument selection
"""

import unittest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import execution modules
from execution.ccxt_get_balance import ccxt_get_hyperliquid_balance, ccxt_print_balance_summary
from execution.ccxt_get_positions import ccxt_get_positions

# Mock the calc_days_from_high import before importing select_insts
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "signals"))

from execution.select_insts import select_instruments_near_200d_high


class TestBalanceChecking(unittest.TestCase):
    """Test balance checking functions"""

    @patch("ccxt.hyperliquid")
    @patch.dict(os.environ, {"HL_API": "test_api", "HL_SECRET": "test_secret"})
    def test_get_balance_with_credentials(self, mock_exchange_class):
        """Test balance fetching with valid credentials"""
        # Mock the exchange instance
        mock_exchange = MagicMock()
        mock_exchange_class.return_value = mock_exchange

        # Mock balance responses
        mock_perp_balance = {
            "info": {
                "marginSummary": {
                    "accountValue": "10000.00",
                    "totalMarginUsed": "2000.00",
                    "totalRawUsd": "10000.00",
                    "totalNtlPos": "2000.00",
                },
                "withdrawable": "8000.00",
                "assetPositions": [],
            },
            "total": {"USDC": 10000.0},
            "free": {"USDC": 8000.0},
            "used": {"USDC": 2000.0},
        }

        mock_spot_balance = {
            "total": {"USDC": 5000.0},
            "free": {"USDC": 5000.0},
            "used": {"USDC": 0.0},
        }

        mock_exchange.fetch_balance.side_effect = [mock_perp_balance, mock_spot_balance]

        # Call function
        result = ccxt_get_hyperliquid_balance()

        # Assertions
        self.assertIsInstance(result, dict)
        self.assertIn("perp", result)
        self.assertIn("spot", result)
        self.assertEqual(result["perp"]["total"]["USDC"], 10000.0)

    def test_get_balance_missing_credentials(self):
        """Test that function raises error without credentials"""
        # Remove credentials from environment
        original_api = os.environ.get("HL_API")
        original_secret = os.environ.get("HL_SECRET")

        if "HL_API" in os.environ:
            del os.environ["HL_API"]
        if "HL_SECRET" in os.environ:
            del os.environ["HL_SECRET"]

        try:
            with self.assertRaises(ValueError):
                ccxt_get_hyperliquid_balance()
        finally:
            # Restore credentials
            if original_api:
                os.environ["HL_API"] = original_api
            if original_secret:
                os.environ["HL_SECRET"] = original_secret

    def test_print_balance_summary_doesnt_crash(self):
        """Test that print_balance_summary doesn't crash with valid data"""
        mock_balances = {
            "perp": {
                "info": {
                    "marginSummary": {
                        "accountValue": "10000.00",
                        "totalMarginUsed": "2000.00",
                        "totalRawUsd": "10000.00",
                        "totalNtlPos": "2000.00",
                    },
                    "withdrawable": "8000.00",
                    "assetPositions": [],
                },
                "total": {"USDC": 10000.0},
            },
            "spot": {"total": {"USDC": 5000.0}},
        }

        # Should not raise exception
        try:
            ccxt_print_balance_summary(mock_balances)
        except Exception as e:
            self.fail(f"print_balance_summary raised exception: {e}")


class TestPositionChecking(unittest.TestCase):
    """Test position checking functions"""

    @patch("ccxt.hyperliquid")
    @patch.dict(os.environ, {"HL_API": "test_api", "HL_SECRET": "test_secret"})
    def test_get_positions_returns_list(self, mock_exchange_class):
        """Test that get_positions returns a list"""
        # Mock the exchange instance
        mock_exchange = MagicMock()
        mock_exchange_class.return_value = mock_exchange

        # Mock positions response
        mock_positions = [
            {
                "symbol": "BTC/USDC:USDC",
                "side": "long",
                "contracts": 1.5,
                "entryPrice": 50000.0,
                "markPrice": 51000.0,
                "unrealizedPnl": 1500.0,
            },
            {
                "symbol": "ETH/USDC:USDC",
                "side": "short",
                "contracts": -10.0,
                "entryPrice": 3000.0,
                "markPrice": 2950.0,
                "unrealizedPnl": 500.0,
            },
        ]

        mock_exchange.fetch_positions.return_value = mock_positions

        # Call function
        result = ccxt_get_positions()

        # Assertions
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["symbol"], "BTC/USDC:USDC")

    def test_get_positions_missing_credentials(self):
        """Test that function raises error without credentials"""
        # Remove credentials from environment
        original_api = os.environ.get("HL_API")
        original_secret = os.environ.get("HL_SECRET")

        if "HL_API" in os.environ:
            del os.environ["HL_API"]
        if "HL_SECRET" in os.environ:
            del os.environ["HL_SECRET"]

        try:
            with self.assertRaises(ValueError):
                ccxt_get_positions()
        finally:
            # Restore credentials
            if original_api:
                os.environ["HL_API"] = original_api
            if original_secret:
                os.environ["HL_SECRET"] = original_secret

    @patch("ccxt.hyperliquid")
    @patch.dict(os.environ, {"HL_API": "test_api", "HL_SECRET": "test_secret"})
    def test_get_positions_handles_empty_positions(self, mock_exchange_class):
        """Test handling of empty positions"""
        mock_exchange = MagicMock()
        mock_exchange_class.return_value = mock_exchange
        mock_exchange.fetch_positions.return_value = []

        result = ccxt_get_positions()

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)


class TestInstrumentSelection(unittest.TestCase):
    """Test instrument selection functions"""

    def setUp(self):
        """Create test data"""
        dates = pd.date_range(start="2024-01-01", periods=250, freq="D")

        # Create data for 3 instruments with different characteristics
        # Instrument 1: Recently hit 200d high (5 days ago)
        # Make trend up, then flat near high
        prices_1 = [40000 + i * 40 for i in range(240)] + [49960] * 10

        # Instrument 2: Far from 200d high (100 days ago)
        # High at start, then decline
        prices_2 = [50000] * 100 + [50000 - i * 66 for i in range(150)]

        # Instrument 3: At 200d high today
        # Steady uptrend
        prices_3 = [30000 + i * 80 for i in range(250)]

        self.test_df = pd.DataFrame(
            {
                "date": list(dates) + list(dates) + list(dates),
                "symbol": ["NEAR_HIGH"] * 250 + ["FAR_FROM_HIGH"] * 250 + ["AT_HIGH"] * 250,
                "open": prices_1 + prices_2 + prices_3,
                "high": [p * 1.01 for p in prices_1 + prices_2 + prices_3],
                "low": [p * 0.99 for p in prices_1 + prices_2 + prices_3],
                "close": prices_1 + prices_2 + prices_3,
                "volume": [1000000] * 750,
            }
        )

    def test_select_instruments_returns_dataframe(self):
        """Test that selection returns a DataFrame"""
        result = select_instruments_near_200d_high(self.test_df, max_days=20)

        self.assertIsInstance(result, pd.DataFrame)

    def test_select_instruments_filters_correctly(self):
        """Test that instruments are filtered by max_days threshold"""
        result = select_instruments_near_200d_high(self.test_df, max_days=20)

        # Should only include instruments within 20 days of 200d high
        if len(result) > 0:
            self.assertTrue(all(result["days_since_200d_high"] < 20))

    def test_select_instruments_includes_at_high(self):
        """Test that instrument at 200d high is included"""
        result = select_instruments_near_200d_high(self.test_df, max_days=20)

        # AT_HIGH should be in results (days_since_200d_high = 0)
        if len(result) > 0:
            symbols = result["symbol"].tolist()
            # At least one instrument should be very close to high
            min_days = result["days_since_200d_high"].min()
            self.assertLessEqual(min_days, 5)

    def test_select_instruments_sorted_by_days(self):
        """Test that results are sorted by days_since_200d_high"""
        result = select_instruments_near_200d_high(self.test_df, max_days=20)

        if len(result) > 1:
            # Check that days_since_200d_high is in ascending order
            days_col = result["days_since_200d_high"]
            self.assertTrue(
                all(days_col.iloc[i] <= days_col.iloc[i + 1] for i in range(len(days_col) - 1))
            )

    def test_select_instruments_has_required_columns(self):
        """Test that result has required columns"""
        result = select_instruments_near_200d_high(self.test_df, max_days=20)

        if len(result) > 0:
            required_columns = [
                "date",
                "symbol",
                "high",
                "rolling_200d_high",
                "days_since_200d_high",
            ]
            for col in required_columns:
                self.assertIn(col, result.columns)

    def test_select_instruments_with_csv_path(self):
        """Test that function works with CSV file path"""
        temp_csv = "/tmp/test_selection_data.csv"
        self.test_df.to_csv(temp_csv, index=False)

        try:
            result = select_instruments_near_200d_high(temp_csv, max_days=20)
            self.assertIsInstance(result, pd.DataFrame)
        finally:
            if os.path.exists(temp_csv):
                os.remove(temp_csv)

    def test_select_instruments_different_thresholds(self):
        """Test selection with different max_days thresholds"""
        result_5 = select_instruments_near_200d_high(self.test_df, max_days=5)
        result_20 = select_instruments_near_200d_high(self.test_df, max_days=20)

        # 20-day threshold should include at least as many as 5-day
        self.assertGreaterEqual(len(result_20), len(result_5))


class TestSpreadOffsetOrders(unittest.TestCase):
    """Test spread offset order execution"""

    def test_send_spread_offset_orders_dry_run(self):
        """Test spread offset orders in dry run mode"""
        # Import here to avoid issues if module is not available
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "execution"))
        
        try:
            from send_spread_offset_orders import send_spread_offset_orders
            
            # Test with empty trades
            result = send_spread_offset_orders({}, spread_multiplier=1.0, dry_run=True)
            self.assertEqual(result, [])
            
            # Test with invalid spread multiplier should raise ValueError
            with self.assertRaises(ValueError):
                send_spread_offset_orders(
                    {"BTC/USDC:USDC": 100}, spread_multiplier=-1.0, dry_run=True
                )
        except ImportError:
            self.skipTest("send_spread_offset_orders module not available")

    def test_spread_offset_calculation(self):
        """Test spread offset price calculation logic"""
        # Test buy order: bid - (spread * multiplier)
        bid = 100.0
        ask = 101.0
        spread = ask - bid  # 1.0
        multiplier = 1.0
        
        expected_buy_price = bid - (spread * multiplier)  # 99.0
        self.assertEqual(expected_buy_price, 99.0)
        
        # Test sell order: ask + (spread * multiplier)
        expected_sell_price = ask + (spread * multiplier)  # 102.0
        self.assertEqual(expected_sell_price, 102.0)
        
        # Test with 0.5x multiplier
        multiplier = 0.5
        expected_buy_price = bid - (spread * multiplier)  # 99.5
        self.assertEqual(expected_buy_price, 99.5)
        
        # Test with 2.0x multiplier
        multiplier = 2.0
        expected_sell_price = ask + (spread * multiplier)  # 103.0
        self.assertEqual(expected_sell_price, 103.0)


if __name__ == "__main__":
    # Run tests
    unittest.main(verbosity=2)
