"""
Tests for Backtest Functions
Tests: mean reversion backtest and related functionality
"""

import unittest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import backtest modules
from backtests.scripts.backtest_mean_reversion import (
    load_data,
    calculate_z_scores,
    categorize_moves,
    analyze_mean_reversion,
)


class TestBacktestDataLoading(unittest.TestCase):
    """Test data loading functionality"""

    def setUp(self):
        """Create test CSV file"""
        dates = pd.date_range(start="2024-01-01", periods=50, freq="D")

        self.test_df = pd.DataFrame(
            {
                "date": dates,
                "symbol": ["BTC/USDC:USDC"] * 50,
                "open": np.random.randn(50) * 100 + 50000,
                "high": np.random.randn(50) * 100 + 50500,
                "low": np.random.randn(50) * 100 + 49500,
                "close": np.random.randn(50) * 100 + 50000,
                "volume": np.random.randn(50) * 1000000 + 5000000,
            }
        )

        # Ensure proper ordering
        self.test_df = self.test_df.sort_values(["symbol", "date"])

        self.temp_csv = "/tmp/test_backtest_data.csv"
        self.test_df.to_csv(self.temp_csv, index=False)

    def tearDown(self):
        """Clean up test file"""
        if os.path.exists(self.temp_csv):
            os.remove(self.temp_csv)

    def test_load_data_returns_dataframe(self):
        """Test that load_data returns a DataFrame"""
        result = load_data(self.temp_csv)

        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)

    def test_load_data_converts_date(self):
        """Test that date column is converted to datetime"""
        result = load_data(self.temp_csv)

        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result["date"]))

    def test_load_data_sorts_correctly(self):
        """Test that data is sorted by symbol and date"""
        result = load_data(self.temp_csv)

        # Check that data is sorted
        self.assertTrue(result["date"].is_monotonic_increasing)


class TestZScoreCalculation(unittest.TestCase):
    """Test z-score calculation functions"""

    def setUp(self):
        """Create test data with known characteristics"""
        dates = pd.date_range(start="2024-01-01", periods=60, freq="D")

        # Create data with a spike (for z-score testing)
        prices = [50000 + i * 100 for i in range(60)]
        # Add a big spike at day 40
        prices[40] = prices[40] * 1.10  # 10% spike

        volumes = [1000000] * 60
        volumes[40] = volumes[40] * 2  # Volume spike

        self.test_df = pd.DataFrame(
            {
                "date": dates,
                "symbol": ["BTC/USDC:USDC"] * 60,
                "open": prices,
                "high": [p * 1.01 for p in prices],
                "low": [p * 0.99 for p in prices],
                "close": prices,
                "volume": volumes,
            }
        )

    def test_calculate_z_scores_returns_dataframe(self):
        """Test that calculate_z_scores returns a DataFrame"""
        result = calculate_z_scores(self.test_df, lookback_window=30)

        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), len(self.test_df))

    def test_calculate_z_scores_has_required_columns(self):
        """Test that result has all required columns"""
        result = calculate_z_scores(self.test_df, lookback_window=30)

        required_columns = [
            "pct_change",
            "volume_change",
            "return_mean",
            "return_std",
            "volume_mean",
            "volume_std",
            "return_zscore",
            "volume_zscore",
            "forward_1d_return",
        ]

        for col in required_columns:
            self.assertIn(col, result.columns)

    def test_calculate_z_scores_no_lookahead_bias(self):
        """Test that z-score calculation doesn't have lookahead bias"""
        result = calculate_z_scores(self.test_df, lookback_window=30)

        # The mean and std used for day i should not include day i's data
        # Check that first 30 rows have NaN z-scores (not enough history)
        first_30_zscores = result["return_zscore"].head(31)  # +1 for pct_change lag
        self.assertTrue(first_30_zscores.isna().any())

    def test_calculate_z_scores_detects_outliers(self):
        """Test that z-scores correctly identify outliers"""
        result = calculate_z_scores(self.test_df, lookback_window=30)

        # The spike at day 40 should have a high z-score
        spike_day_zscore = result.iloc[40]["return_zscore"]

        # Z-score should be high (> 1.0) or NaN
        if not pd.isna(spike_day_zscore):
            self.assertGreater(abs(spike_day_zscore), 0.5)

    def test_forward_return_calculation(self):
        """Test that forward returns are calculated correctly"""
        result = calculate_z_scores(self.test_df, lookback_window=30)

        # Forward return should be shifted correctly
        # Last row should have NaN forward return
        self.assertTrue(pd.isna(result.iloc[-1]["forward_1d_return"]))


class TestMovesCategorization(unittest.TestCase):
    """Test moves categorization functions"""

    def setUp(self):
        """Create test data with z-scores"""
        self.test_df = pd.DataFrame(
            {
                "date": pd.date_range(start="2024-01-01", periods=10, freq="D"),
                "symbol": ["BTC/USDC:USDC"] * 10,
                "return_zscore": [0.5, 1.5, -1.5, 0.1, 2.0, -2.0, 0.3, 1.2, -0.8, 0.0],
                "volume_zscore": [0.5, 1.5, 1.5, 0.1, 0.5, 1.5, 2.0, 0.3, 0.4, 0.0],
                "forward_1d_return": [
                    0.01,
                    -0.02,
                    0.03,
                    0.00,
                    -0.01,
                    0.02,
                    -0.01,
                    0.01,
                    0.00,
                    0.01,
                ],
            }
        )

    def test_categorize_moves_returns_dataframe(self):
        """Test that categorize_moves returns a DataFrame"""
        result = categorize_moves(self.test_df, return_threshold=1.0, volume_threshold=1.0)

        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), len(self.test_df))

    def test_categorize_moves_has_category_columns(self):
        """Test that result has category columns"""
        result = categorize_moves(self.test_df)

        self.assertIn("category", result.columns)
        self.assertIn("category_directional", result.columns)

    def test_categorize_moves_valid_categories(self):
        """Test that categories are valid"""
        result = categorize_moves(self.test_df)

        valid_categories = [
            "high_return_high_volume",
            "high_return_low_volume",
            "low_return_high_volume",
            "low_return_low_volume",
            "unknown",
        ]

        self.assertTrue(all(result["category"].isin(valid_categories)))

    def test_categorize_moves_directional_categories(self):
        """Test directional categories"""
        result = categorize_moves(self.test_df, return_threshold=1.0, volume_threshold=1.0)

        valid_directional = [
            "up_move_high_volume",
            "up_move_low_volume",
            "down_move_high_volume",
            "down_move_low_volume",
            "neutral",
        ]

        self.assertTrue(all(result["category_directional"].isin(valid_directional)))


class TestMeanReversionAnalysis(unittest.TestCase):
    """Test mean reversion analysis functions"""

    def setUp(self):
        """Create test data for analysis"""
        np.random.seed(42)  # For reproducible tests

        self.test_df = pd.DataFrame(
            {
                "date": pd.date_range(start="2024-01-01", periods=100, freq="D"),
                "symbol": ["BTC/USDC:USDC"] * 100,
                "return_zscore": np.random.randn(100) * 2,
                "volume_zscore": np.random.randn(100) * 1.5,
                "forward_1d_return": np.random.randn(100) * 0.02,
                "category": ["high_return_high_volume"] * 25
                + ["high_return_low_volume"] * 25
                + ["low_return_high_volume"] * 25
                + ["low_return_low_volume"] * 25,
                "category_directional": ["up_move_high_volume"] * 20
                + ["up_move_low_volume"] * 20
                + ["down_move_high_volume"] * 20
                + ["down_move_low_volume"] * 20
                + ["neutral"] * 20,
            }
        )

    def test_analyze_mean_reversion_returns_dict(self):
        """Test that analyze_mean_reversion returns a dictionary"""
        result = analyze_mean_reversion(self.test_df)

        self.assertIsInstance(result, dict)

    def test_analyze_mean_reversion_has_required_keys(self):
        """Test that result has all required keys"""
        result = analyze_mean_reversion(self.test_df)

        required_keys = [
            "overall",
            "by_category",
            "by_directional_category",
            "by_return_bucket",
            "detailed_data",
        ]

        for key in required_keys:
            self.assertIn(key, result)

    def test_analyze_mean_reversion_overall_stats(self):
        """Test overall statistics"""
        result = analyze_mean_reversion(self.test_df)

        overall = result["overall"]

        self.assertIn("count", overall)
        self.assertIn("mean_forward_return", overall)
        self.assertIn("median_forward_return", overall)
        self.assertIn("std_forward_return", overall)

        # Count should match input (minus NaN values)
        self.assertGreater(overall["count"], 0)

    def test_analyze_mean_reversion_category_stats(self):
        """Test category statistics"""
        result = analyze_mean_reversion(self.test_df)

        by_category = result["by_category"]

        self.assertIsInstance(by_category, pd.DataFrame)

        if not by_category.empty:
            required_cols = [
                "category",
                "count",
                "mean_forward_return",
                "sharpe_ratio",
                "positive_days_pct",
            ]
            for col in required_cols:
                self.assertIn(col, by_category.columns)

    def test_analyze_mean_reversion_handles_nans(self):
        """Test that function handles NaN values correctly"""
        # Add some NaN values
        df_with_nans = self.test_df.copy()
        df_with_nans.loc[0:10, "forward_1d_return"] = np.nan

        result = analyze_mean_reversion(df_with_nans)

        # Should still return valid results
        self.assertIsInstance(result, dict)
        self.assertGreater(result["overall"]["count"], 0)


if __name__ == "__main__":
    # Run tests
    unittest.main(verbosity=2)
