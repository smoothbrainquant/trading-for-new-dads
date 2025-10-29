"""
Tests for validation utilities.

Tests input validation for data integrity, signal structure,
and risk parameter checks.
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from common.validators import DataValidator, SignalValidator, RiskValidator
from common.exceptions import (
    DataValidationError,
    DataStaleError,
    SignalValidationError,
    RiskLimitError,
)


class TestDataValidator(unittest.TestCase):
    """Test data validation functions."""

    def setUp(self):
        """Create test data."""
        self.valid_df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=10),
                "symbol": ["BTC/USDC:USDC"] * 10,
                "open": [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0],
                "high": [105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0],
                "low": [95.0, 96.0, 97.0, 98.0, 99.0, 100.0, 101.0, 102.0, 103.0, 104.0],
                "close": [102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0],
                "volume": [1000.0] * 10,
            }
        )

    def test_validate_ohlcv_valid_data(self):
        """Test that validation passes for valid OHLCV data."""
        # Should not raise any exception
        DataValidator.validate_ohlcv_dataframe(self.valid_df)

    def test_validate_ohlcv_empty_dataframe(self):
        """Test that validation fails for empty DataFrame."""
        empty_df = pd.DataFrame()

        with self.assertRaises(DataValidationError) as context:
            DataValidator.validate_ohlcv_dataframe(empty_df)

        self.assertIn("empty", str(context.exception).lower())

    def test_validate_ohlcv_missing_columns(self):
        """Test that validation fails when columns are missing."""
        incomplete_df = self.valid_df.drop(columns=["volume"])

        with self.assertRaises(DataValidationError) as context:
            DataValidator.validate_ohlcv_dataframe(incomplete_df)

        self.assertIn("volume", str(context.exception).lower())

    def test_validate_ohlcv_high_less_than_low(self):
        """Test that validation fails when high < low."""
        invalid_df = self.valid_df.copy()
        invalid_df.loc[0, "high"] = 90.0  # Below low of 95.0

        with self.assertRaises(DataValidationError) as context:
            DataValidator.validate_ohlcv_dataframe(invalid_df)

        self.assertIn("high", str(context.exception).lower())
        self.assertIn("low", str(context.exception).lower())

    def test_validate_ohlcv_negative_prices(self):
        """Test that validation fails for negative prices."""
        invalid_df = self.valid_df.copy()
        invalid_df.loc[0, "close"] = -100.0

        with self.assertRaises(DataValidationError) as context:
            DataValidator.validate_ohlcv_dataframe(invalid_df)

        self.assertIn("non-positive", str(context.exception).lower())

    def test_validate_ohlcv_null_values(self):
        """Test that validation fails when nulls are present."""
        invalid_df = self.valid_df.copy()
        invalid_df.loc[0, "close"] = np.nan

        with self.assertRaises(DataValidationError) as context:
            DataValidator.validate_ohlcv_dataframe(invalid_df)

        self.assertIn("null", str(context.exception).lower())

    def test_validate_date_range_fresh_data(self):
        """Test that validation passes for fresh data."""
        fresh_df = self.valid_df.copy()
        fresh_df["date"] = pd.date_range(end=datetime.now(), periods=10)

        # Should not raise
        DataValidator.validate_date_range(fresh_df, max_age_hours=48)

    def test_validate_date_range_stale_data(self):
        """Test that validation fails for stale data."""
        stale_df = self.valid_df.copy()
        # Data from 100 hours ago
        stale_df["date"] = pd.date_range(end=datetime.now() - timedelta(hours=100), periods=10)

        with self.assertRaises(DataStaleError):
            DataValidator.validate_date_range(stale_df, max_age_hours=48)

    def test_validate_symbols_present_all_found(self):
        """Test that validation passes when all symbols are present."""
        # Should not raise
        DataValidator.validate_symbols_present(self.valid_df, required_symbols=["BTC/USDC:USDC"])

    def test_validate_symbols_present_missing_symbols(self):
        """Test that validation fails when symbols are missing."""
        with self.assertRaises(DataValidationError) as context:
            DataValidator.validate_symbols_present(
                self.valid_df, required_symbols=["BTC/USDC:USDC", "ETH/USDC:USDC", "SOL/USDC:USDC"]
            )

        self.assertIn("missing", str(context.exception).lower())


class TestSignalValidator(unittest.TestCase):
    """Test signal validation functions."""

    def test_validate_signals_valid_structure(self):
        """Test that validation passes for valid signals."""
        valid_signals = {"longs": ["BTC", "ETH"], "shorts": ["SOL", "ADA"]}

        # Should not raise
        SignalValidator.validate_signals(valid_signals)

    def test_validate_signals_missing_keys(self):
        """Test that validation fails when keys are missing."""
        invalid_signals = {"longs": ["BTC"]}  # Missing 'shorts'

        with self.assertRaises(SignalValidationError) as context:
            SignalValidator.validate_signals(invalid_signals)

        self.assertIn("missing", str(context.exception).lower())

    def test_validate_signals_wrong_type(self):
        """Test that validation fails for wrong data types."""
        invalid_signals = {"longs": "BTC", "shorts": []}  # Should be list, not string

        with self.assertRaises(SignalValidationError):
            SignalValidator.validate_signals(invalid_signals)

    def test_validate_signals_overlap(self):
        """Test that validation fails when symbols overlap."""
        invalid_signals = {"longs": ["BTC", "ETH"], "shorts": ["ETH", "SOL"]}  # ETH in both

        with self.assertRaises(SignalValidationError) as context:
            SignalValidator.validate_signals(invalid_signals)

        self.assertIn("overlap", str(context.exception).lower())
        self.assertIn("ETH", str(context.exception))

    def test_validate_weights_valid(self):
        """Test that validation passes for valid weights."""
        valid_weights = {"BTC": 0.4, "ETH": 0.35, "SOL": 0.25}

        # Should not raise
        SignalValidator.validate_weights(valid_weights)

    def test_validate_weights_sum_not_one(self):
        """Test that validation fails when weights don't sum to 1.0."""
        invalid_weights = {"BTC": 0.5, "ETH": 0.3}  # Sum = 0.8

        with self.assertRaises(SignalValidationError) as context:
            SignalValidator.validate_weights(invalid_weights)

        self.assertIn("sum", str(context.exception).lower())

    def test_validate_weights_negative(self):
        """Test that validation fails for negative weights."""
        invalid_weights = {"BTC": 0.6, "ETH": 0.5, "SOL": -0.1}

        with self.assertRaises(SignalValidationError) as context:
            SignalValidator.validate_weights(invalid_weights)

        self.assertIn("negative", str(context.exception).lower())

    def test_validate_weights_empty(self):
        """Test that validation fails for empty weights."""
        with self.assertRaises(SignalValidationError):
            SignalValidator.validate_weights({})


class TestRiskValidator(unittest.TestCase):
    """Test risk validation functions."""

    def test_validate_position_size_within_limit(self):
        """Test that validation passes when position is within limit."""
        # Should not raise
        RiskValidator.validate_position_size(notional=5000.0, max_notional=10000.0, symbol="BTC")

    def test_validate_position_size_exceeds_limit(self):
        """Test that validation fails when position exceeds limit."""
        with self.assertRaises(RiskLimitError) as context:
            RiskValidator.validate_position_size(
                notional=15000.0, max_notional=10000.0, symbol="BTC"
            )

        error = context.exception
        self.assertEqual(error.current_value, 15000.0)
        self.assertEqual(error.max_value, 10000.0)

    def test_validate_total_exposure_within_limit(self):
        """Test that validation passes when exposure is within limit."""
        # Should not raise
        RiskValidator.validate_total_exposure(total_exposure=80000.0, max_exposure=100000.0)

    def test_validate_total_exposure_exceeds_limit(self):
        """Test that validation fails when exposure exceeds limit."""
        with self.assertRaises(RiskLimitError):
            RiskValidator.validate_total_exposure(total_exposure=120000.0, max_exposure=100000.0)

    def test_validate_leverage_within_limit(self):
        """Test that validation passes when leverage is within limit."""
        # Should not raise
        RiskValidator.validate_leverage(leverage=1.8, max_leverage=2.0)

    def test_validate_leverage_exceeds_limit(self):
        """Test that validation fails when leverage exceeds limit."""
        with self.assertRaises(RiskLimitError):
            RiskValidator.validate_leverage(leverage=2.5, max_leverage=2.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
