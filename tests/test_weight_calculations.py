"""
Test Weight Calculations for Mean Reversion and Other Strategies

This test suite verifies that weight calculations in both backtest and live
trading implementations are mathematically correct.

Coverage:
- Risk parity weight calculation
- Equal weight calculation  
- Allocation scaling
- Weight summation
"""

import pytest
import pandas as pd
import numpy as np
import sys
import os

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'signals'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from signals.calc_weights import calculate_weights
from signals.generate_signals_vectorized import calculate_weights_vectorized


class TestRiskParityWeights:
    """Test risk parity weight calculation."""

    def test_weights_sum_to_one(self):
        """Verify that risk parity weights sum to exactly 1.0."""
        volatilities = {
            'BTC/USD': 0.05,
            'ETH/USD': 0.08,
            'SOL/USD': 0.10,
        }
        
        weights = calculate_weights(volatilities)
        
        assert weights is not None
        assert len(weights) == 3
        assert abs(sum(weights.values()) - 1.0) < 1e-10, "Weights must sum to 1.0"

    def test_inverse_volatility_logic(self):
        """Verify that lower volatility assets get higher weights."""
        volatilities = {
            'LOW_VOL': 0.05,   # Should get highest weight
            'MED_VOL': 0.10,   # Should get medium weight
            'HIGH_VOL': 0.20,  # Should get lowest weight
        }
        
        weights = calculate_weights(volatilities)
        
        assert weights['LOW_VOL'] > weights['MED_VOL']
        assert weights['MED_VOL'] > weights['HIGH_VOL']
        assert weights['LOW_VOL'] > weights['HIGH_VOL']

    def test_empty_volatilities(self):
        """Verify handling of empty volatilities dict."""
        weights = calculate_weights({})
        assert weights == {}

    def test_single_asset(self):
        """Verify that single asset gets 100% weight."""
        volatilities = {'BTC/USD': 0.05}
        weights = calculate_weights(volatilities)
        
        assert len(weights) == 1
        assert abs(weights['BTC/USD'] - 1.0) < 1e-10

    def test_zero_volatility_filtered(self):
        """Verify that zero volatility assets are filtered out."""
        volatilities = {
            'BTC/USD': 0.05,
            'STABLECOIN': 0.0,  # Should be filtered
        }
        
        weights = calculate_weights(volatilities)
        
        assert len(weights) == 1
        assert 'STABLECOIN' not in weights
        assert abs(weights['BTC/USD'] - 1.0) < 1e-10

    def test_negative_volatility_filtered(self):
        """Verify that negative volatility assets are filtered out."""
        volatilities = {
            'BTC/USD': 0.05,
            'INVALID': -0.01,  # Should be filtered
        }
        
        weights = calculate_weights(volatilities)
        
        assert len(weights) == 1
        assert 'INVALID' not in weights


class TestEqualWeightVectorized:
    """Test equal weight calculation in vectorized backtest."""

    def test_equal_weight_long_only(self):
        """Test equal weighting with long-only positions."""
        # Create test data: 3 longs on same date
        df = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01'] * 3),
            'symbol': ['BTC', 'ETH', 'SOL'],
            'signal': [1, 1, 1],
        })
        
        weights_df = calculate_weights_vectorized(
            df,
            weighting_method='equal_weight',
            long_allocation=1.0,
            short_allocation=0.0,
        )
        
        # Each position should get 1/3 of allocation
        assert len(weights_df) == 3
        assert all(abs(weights_df['weight'] - 1.0/3) < 1e-10)
        assert abs(weights_df['weight'].sum() - 1.0) < 1e-10

    def test_equal_weight_long_short(self):
        """Test equal weighting with both long and short positions."""
        # Create test data: 3 longs, 2 shorts
        df = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01'] * 5),
            'symbol': ['BTC', 'ETH', 'SOL', 'AVAX', 'LINK'],
            'signal': [1, 1, 1, -1, -1],
        })
        
        weights_df = calculate_weights_vectorized(
            df,
            weighting_method='equal_weight',
            long_allocation=0.5,
            short_allocation=0.5,
        )
        
        # Verify long weights: each gets 0.5 / 3 = 0.1667
        long_weights = weights_df[weights_df['signal'] == 1]['weight']
        assert len(long_weights) == 3
        assert all(abs(long_weights - 0.5/3) < 1e-10)
        assert abs(long_weights.sum() - 0.5) < 1e-10
        
        # Verify short weights: each gets -0.5 / 2 = -0.25
        short_weights = weights_df[weights_df['signal'] == -1]['weight']
        assert len(short_weights) == 2
        assert all(abs(short_weights + 0.5/2) < 1e-10)
        assert abs(short_weights.sum() + 0.5) < 1e-10
        
        # Verify gross exposure
        assert abs(weights_df['weight'].abs().sum() - 1.0) < 1e-10

    def test_equal_weight_multiple_dates(self):
        """Test equal weighting with multiple rebalance dates."""
        # Create test data: different positions per date
        df = pd.DataFrame({
            'date': pd.to_datetime([
                '2024-01-01', '2024-01-01', '2024-01-01',  # 3 longs
                '2024-01-02', '2024-01-02',                 # 2 longs
            ]),
            'symbol': ['BTC', 'ETH', 'SOL', 'BTC', 'ETH'],
            'signal': [1, 1, 1, 1, 1],
        })
        
        weights_df = calculate_weights_vectorized(
            df,
            weighting_method='equal_weight',
            long_allocation=1.0,
            short_allocation=0.0,
        )
        
        # Date 1: 3 positions, each should get 1/3
        date1 = weights_df[weights_df['date'] == '2024-01-01']
        assert len(date1) == 3
        assert all(abs(date1['weight'] - 1.0/3) < 1e-10)
        
        # Date 2: 2 positions, each should get 1/2
        date2 = weights_df[weights_df['date'] == '2024-01-02']
        assert len(date2) == 2
        assert all(abs(date2['weight'] - 1.0/2) < 1e-10)


class TestAllocationScaling:
    """Test that allocations are scaled correctly."""

    def test_allocation_with_leverage(self):
        """Test that leverage scales allocations correctly."""
        df = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01'] * 2),
            'symbol': ['BTC', 'ETH'],
            'signal': [1, 1],
        })
        
        leverage = 2.0
        long_allocation = 0.5 * leverage  # 1.0 with 2x leverage
        
        weights_df = calculate_weights_vectorized(
            df,
            weighting_method='equal_weight',
            long_allocation=long_allocation,
            short_allocation=0.0,
        )
        
        # Each position gets 1.0 / 2 = 0.5 (50% each with 2x leverage)
        assert all(abs(weights_df['weight'] - 0.5) < 1e-10)
        assert abs(weights_df['weight'].sum() - 1.0) < 1e-10

    def test_partial_allocation(self):
        """Test that partial allocation works correctly."""
        df = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01'] * 3),
            'symbol': ['BTC', 'ETH', 'SOL'],
            'signal': [1, 1, 1],
        })
        
        # Only allocate 30% to longs
        weights_df = calculate_weights_vectorized(
            df,
            weighting_method='equal_weight',
            long_allocation=0.3,
            short_allocation=0.0,
        )
        
        # Each position gets 0.3 / 3 = 0.1 (10% each)
        assert all(abs(weights_df['weight'] - 0.1) < 1e-10)
        assert abs(weights_df['weight'].sum() - 0.3) < 1e-10


class TestRiskParityVectorized:
    """Test risk parity weighting in vectorized backtest."""

    def test_risk_parity_with_volatility(self):
        """Test risk parity weighting with volatility data."""
        # Create test data with volatility
        df = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01'] * 3),
            'symbol': ['BTC', 'ETH', 'SOL'],
            'signal': [1, 1, 1],
        })
        
        volatility_df = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01'] * 3),
            'symbol': ['BTC', 'ETH', 'SOL'],
            'volatility': [0.05, 0.08, 0.10],  # BTC lowest vol
        })
        
        weights_df = calculate_weights_vectorized(
            df,
            volatility_df=volatility_df,
            weighting_method='risk_parity',
            long_allocation=1.0,
            short_allocation=0.0,
        )
        
        # BTC (lowest vol) should have highest weight
        btc_weight = weights_df[weights_df['symbol'] == 'BTC']['weight'].values[0]
        eth_weight = weights_df[weights_df['symbol'] == 'ETH']['weight'].values[0]
        sol_weight = weights_df[weights_df['symbol'] == 'SOL']['weight'].values[0]
        
        assert btc_weight > eth_weight
        assert eth_weight > sol_weight
        
        # Weights should sum to allocation
        assert abs(weights_df['weight'].sum() - 1.0) < 1e-10


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_no_signals(self):
        """Test handling of dates with no signals."""
        df = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01'] * 3),
            'symbol': ['BTC', 'ETH', 'SOL'],
            'signal': [0, 0, 0],  # No positions
        })
        
        weights_df = calculate_weights_vectorized(
            df,
            weighting_method='equal_weight',
            long_allocation=1.0,
            short_allocation=0.0,
        )
        
        # All weights should be zero
        assert all(weights_df['weight'] == 0.0)

    def test_single_position(self):
        """Test handling of single position."""
        df = pd.DataFrame({
            'date': pd.to_datetime(['2024-01-01']),
            'symbol': ['BTC'],
            'signal': [1],
        })
        
        weights_df = calculate_weights_vectorized(
            df,
            weighting_method='equal_weight',
            long_allocation=1.0,
            short_allocation=0.0,
        )
        
        # Single position gets 100% weight
        assert len(weights_df) == 1
        assert abs(weights_df['weight'].values[0] - 1.0) < 1e-10


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
