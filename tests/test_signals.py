"""
Tests for Signal Calculation Functions
Tests: breakout signals, volatility calculation, weight calculation
"""

import unittest
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import signal calculation modules
from signals.calc_breakout_signals import (
    calculate_breakout_signals,
    get_current_signals,
    get_active_signals
)
from signals.calc_vola import (
    calculate_rolling_30d_volatility,
    calculate_rolling_30d_volatility_simple
)
from signals.calc_weights import calculate_weights


class TestBreakoutSignals(unittest.TestCase):
    """Test breakout signal calculation functions"""
    
    def setUp(self):
        """Create test data"""
        # Create sample price data
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        
        # Create uptrend data for BTC
        btc_prices = np.linspace(40000, 50000, 100) + np.random.randn(100) * 500
        
        # Create downtrend data for ETH
        eth_prices = np.linspace(3000, 2500, 100) + np.random.randn(100) * 50
        
        self.test_df = pd.DataFrame({
            'date': list(dates) + list(dates),
            'symbol': ['BTC/USDC:USDC'] * 100 + ['ETH/USDC:USDC'] * 100,
            'open': list(btc_prices * 0.99) + list(eth_prices * 0.99),
            'high': list(btc_prices * 1.01) + list(eth_prices * 1.01),
            'low': list(btc_prices * 0.98) + list(eth_prices * 0.98),
            'close': list(btc_prices) + list(eth_prices),
            'volume': [1000000] * 200
        })
    
    def test_calculate_breakout_signals_returns_dataframe(self):
        """Test that calculate_breakout_signals returns a DataFrame"""
        result = calculate_breakout_signals(self.test_df)
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)
    
    def test_calculate_breakout_signals_has_required_columns(self):
        """Test that result has all required columns"""
        result = calculate_breakout_signals(self.test_df)
        
        required_columns = [
            'date', 'symbol', 'close',
            'rolling_50d_high', 'rolling_50d_low',
            'rolling_70d_high', 'rolling_70d_low',
            'signal', 'position'
        ]
        
        for col in required_columns:
            self.assertIn(col, result.columns)
    
    def test_calculate_breakout_signals_valid_signals(self):
        """Test that signals are valid values"""
        result = calculate_breakout_signals(self.test_df)
        
        valid_signals = ['LONG', 'SHORT', 'EXIT_LONG', 'EXIT_SHORT', 
                        'HOLD_LONG', 'HOLD_SHORT', 'NEUTRAL']
        
        # All signals should be valid
        self.assertTrue(all(result['signal'].isin(valid_signals)))
    
    def test_calculate_breakout_signals_valid_positions(self):
        """Test that positions are valid values"""
        result = calculate_breakout_signals(self.test_df)
        
        valid_positions = ['LONG', 'SHORT', 'FLAT']
        
        # All positions should be valid
        self.assertTrue(all(result['position'].isin(valid_positions)))
    
    def test_get_current_signals_returns_latest(self):
        """Test that get_current_signals returns only the latest date"""
        result = get_current_signals(self.test_df)
        
        # Should have one row per symbol
        self.assertEqual(len(result), self.test_df['symbol'].nunique())
        
        # All dates should be the same (latest)
        self.assertEqual(result['date'].nunique(), 1)
        latest_date = result['date'].iloc[0]
        self.assertEqual(latest_date, self.test_df['date'].max())
    
    def test_get_active_signals_structure(self):
        """Test that get_active_signals returns correct structure"""
        result = get_active_signals(self.test_df)
        
        # Check result structure
        self.assertIsInstance(result, dict)
        self.assertIn('longs', result)
        self.assertIn('shorts', result)
        self.assertIn('signals_df', result)
        
        # Check data types
        self.assertIsInstance(result['longs'], list)
        self.assertIsInstance(result['shorts'], list)
        self.assertIsInstance(result['signals_df'], pd.DataFrame)
    
    def test_breakout_signals_with_csv_path(self):
        """Test that function works with CSV file path"""
        # Save test data to temp CSV
        temp_csv = '/tmp/test_breakout_data.csv'
        self.test_df.to_csv(temp_csv, index=False)
        
        try:
            result = calculate_breakout_signals(temp_csv)
            self.assertIsInstance(result, pd.DataFrame)
            self.assertGreater(len(result), 0)
        finally:
            if os.path.exists(temp_csv):
                os.remove(temp_csv)


class TestVolatilityCalculation(unittest.TestCase):
    """Test volatility calculation functions"""
    
    def setUp(self):
        """Create test data with known volatility characteristics"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        
        # Create stable asset (low volatility)
        stable_prices = [100 + np.random.randn() * 1 for _ in range(100)]
        
        # Create volatile asset (high volatility)
        volatile_prices = [100 + np.random.randn() * 10 for _ in range(100)]
        
        self.test_df = pd.DataFrame({
            'date': list(dates) + list(dates),
            'symbol': ['STABLE'] * 100 + ['VOLATILE'] * 100,
            'open': stable_prices + volatile_prices,
            'high': [p * 1.01 for p in stable_prices] + [p * 1.05 for p in volatile_prices],
            'low': [p * 0.99 for p in stable_prices] + [p * 0.95 for p in volatile_prices],
            'close': stable_prices + volatile_prices,
            'volume': [1000000] * 200
        })
    
    def test_calculate_rolling_volatility_returns_dataframe(self):
        """Test that function returns a DataFrame"""
        result = calculate_rolling_30d_volatility(self.test_df)
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertGreater(len(result), 0)
    
    def test_calculate_rolling_volatility_has_required_columns(self):
        """Test that result has required columns"""
        result = calculate_rolling_30d_volatility(self.test_df)
        
        required_columns = ['date', 'symbol', 'close', 'daily_return', 'volatility_30d']
        for col in required_columns:
            self.assertIn(col, result.columns)
    
    def test_volatility_requires_minimum_periods(self):
        """Test that volatility is NaN for periods < 30 days"""
        result = calculate_rolling_30d_volatility(self.test_df)
        
        # First 30 rows should have NaN volatility
        symbol_data = result[result['symbol'] == 'STABLE'].head(30)
        self.assertTrue(symbol_data['volatility_30d'].isna().any())
    
    def test_volatility_is_positive(self):
        """Test that calculated volatility is positive"""
        result = calculate_rolling_30d_volatility(self.test_df)
        
        # Remove NaN values
        valid_vola = result['volatility_30d'].dropna()
        
        # All volatility values should be >= 0
        self.assertTrue(all(valid_vola >= 0))
    
    def test_volatile_asset_has_higher_volatility(self):
        """Test that more volatile asset has higher calculated volatility"""
        result = calculate_rolling_30d_volatility(self.test_df)
        
        # Get average volatility for each symbol (excluding NaN)
        stable_vola = result[result['symbol'] == 'STABLE']['volatility_30d'].mean()
        volatile_vola = result[result['symbol'] == 'VOLATILE']['volatility_30d'].mean()
        
        # Volatile asset should have higher volatility
        self.assertGreater(volatile_vola, stable_vola)
    
    def test_calculate_rolling_volatility_simple(self):
        """Test non-annualized volatility calculation"""
        result = calculate_rolling_30d_volatility_simple(self.test_df)
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertIn('volatility_30d', result.columns)
        
        # Simple volatility should be lower than annualized
        # (annualized = simple * sqrt(365))
        valid_vola = result['volatility_30d'].dropna()
        self.assertTrue(all(valid_vola >= 0))
    
    def test_volatility_with_csv_path(self):
        """Test that function works with CSV file path"""
        temp_csv = '/tmp/test_vola_data.csv'
        self.test_df.to_csv(temp_csv, index=False)
        
        try:
            result = calculate_rolling_30d_volatility(temp_csv)
            self.assertIsInstance(result, pd.DataFrame)
        finally:
            if os.path.exists(temp_csv):
                os.remove(temp_csv)


class TestWeightCalculation(unittest.TestCase):
    """Test portfolio weight calculation functions"""
    
    def test_calculate_weights_basic(self):
        """Test basic weight calculation"""
        volatilities = {
            'BTC/USDC:USDC': 0.05,
            'ETH/USDC:USDC': 0.08,
            'SOL/USDC:USDC': 0.12
        }
        
        weights = calculate_weights(volatilities)
        
        # Check that weights sum to 1.0
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)
        
        # Check that all weights are positive
        self.assertTrue(all(w > 0 for w in weights.values()))
    
    def test_calculate_weights_inverse_relationship(self):
        """Test that weights are inversely proportional to volatility"""
        volatilities = {
            'LOW_VOL': 0.05,
            'HIGH_VOL': 0.10
        }
        
        weights = calculate_weights(volatilities)
        
        # Lower volatility should get higher weight
        self.assertGreater(weights['LOW_VOL'], weights['HIGH_VOL'])
    
    def test_calculate_weights_equal_volatility(self):
        """Test that equal volatilities produce equal weights"""
        volatilities = {
            'ASSET_A': 0.10,
            'ASSET_B': 0.10,
            'ASSET_C': 0.10
        }
        
        weights = calculate_weights(volatilities)
        
        # All weights should be approximately equal
        expected_weight = 1.0 / 3.0
        for weight in weights.values():
            self.assertAlmostEqual(weight, expected_weight, places=6)
    
    def test_calculate_weights_handles_empty_input(self):
        """Test that function handles empty input"""
        weights = calculate_weights({})
        
        self.assertEqual(weights, {})
    
    def test_calculate_weights_filters_invalid_volatilities(self):
        """Test that function filters out invalid volatilities"""
        volatilities = {
            'VALID': 0.05,
            'ZERO': 0.0,
            'NEGATIVE': -0.05,
            'NONE': None
        }
        
        weights = calculate_weights(volatilities)
        
        # Only valid volatility should have weight
        self.assertIn('VALID', weights)
        self.assertNotIn('ZERO', weights)
        self.assertNotIn('NEGATIVE', weights)
        self.assertNotIn('NONE', weights)
        
        # Weight should sum to 1.0
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)
    
    def test_calculate_weights_all_invalid_returns_empty(self):
        """Test that all invalid volatilities returns empty dict"""
        volatilities = {
            'ZERO': 0.0,
            'NEGATIVE': -0.05,
            'NONE': None
        }
        
        weights = calculate_weights(volatilities)
        
        self.assertEqual(weights, {})


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
