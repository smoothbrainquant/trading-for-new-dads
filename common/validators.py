"""
Input validation utilities.

Provides validation functions for data integrity, signal validity,
and risk parameter checks. Raises specific exceptions on validation failure.
"""

from typing import Optional, List, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime

from .exceptions import (
    DataValidationError,
    DataStaleError,
    SignalValidationError,
    RiskLimitError
)


class DataValidator:
    """Validates data integrity and structure."""
    
    @staticmethod
    def validate_ohlcv_dataframe(
        df: pd.DataFrame,
        required_columns: Optional[List[str]] = None
    ) -> None:
        """Validate OHLCV dataframe structure and content.
        
        Args:
            df: DataFrame to validate
            required_columns: List of required columns (default: standard OHLCV)
            
        Raises:
            DataValidationError: If validation fails
        """
        if required_columns is None:
            required_columns = ['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']
        
        # Check if empty
        if df.empty:
            raise DataValidationError("DataFrame is empty")
        
        # Check for missing columns
        missing_cols = set(required_columns) - set(df.columns)
        if missing_cols:
            raise DataValidationError(f"Missing required columns: {missing_cols}")
        
        # Check OHLC consistency: high >= low
        if not (df['high'] >= df['low']).all():
            invalid_rows = df[df['high'] < df['low']]
            raise DataValidationError(
                f"High < Low in {len(invalid_rows)} rows. "
                f"First invalid row: {invalid_rows.iloc[0].to_dict()}"
            )
        
        # Check OHLC consistency: high >= close
        if not (df['high'] >= df['close']).all():
            invalid_count = (df['high'] < df['close']).sum()
            raise DataValidationError(
                f"High < Close in {invalid_count} rows"
            )
        
        # Check OHLC consistency: low <= close
        if not (df['low'] <= df['close']).all():
            invalid_count = (df['low'] > df['close']).sum()
            raise DataValidationError(
                f"Low > Close in {invalid_count} rows"
            )
        
        # Check for nulls in critical columns
        critical_nulls = df[required_columns].isnull().sum()
        if critical_nulls.any():
            null_cols = critical_nulls[critical_nulls > 0]
            raise DataValidationError(
                f"Null values in critical columns: {null_cols.to_dict()}"
            )
        
        # Check for non-positive prices
        price_cols = [col for col in ['open', 'high', 'low', 'close'] if col in df.columns]
        for col in price_cols:
            if (df[col] <= 0).any():
                invalid_count = (df[col] <= 0).sum()
                raise DataValidationError(
                    f"Non-positive values in {col}: {invalid_count} rows"
                )
        
        # Check for infinite values
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if np.isinf(df[col]).any():
                invalid_count = np.isinf(df[col]).sum()
                raise DataValidationError(
                    f"Infinite values in {col}: {invalid_count} rows"
                )
    
    @staticmethod
    def validate_date_range(
        df: pd.DataFrame,
        max_age_hours: int = 48,
        date_column: str = 'date'
    ) -> None:
        """Validate that data is fresh enough.
        
        Args:
            df: DataFrame with date column
            max_age_hours: Maximum allowed age in hours
            date_column: Name of the date column
            
        Raises:
            DataValidationError: If DataFrame is empty
            DataStaleError: If data is too old
        """
        if df.empty:
            raise DataValidationError("Cannot validate date range on empty DataFrame")
        
        if date_column not in df.columns:
            raise DataValidationError(f"Date column '{date_column}' not found")
        
        # Get latest date
        latest_date = pd.to_datetime(df[date_column]).max()
        current_time = pd.Timestamp.now(tz='UTC')
        
        # Ensure both timestamps have timezone info
        if latest_date.tz is None:
            latest_date = latest_date.tz_localize('UTC')
        
        # Calculate age
        age_hours = (current_time - latest_date).total_seconds() / 3600
        
        if age_hours > max_age_hours:
            raise DataStaleError(latest_date, current_time, max_age_hours)
    
    @staticmethod
    def validate_symbols_present(
        df: pd.DataFrame,
        required_symbols: List[str],
        symbol_column: str = 'symbol'
    ) -> None:
        """Validate that all required symbols are present.
        
        Args:
            df: DataFrame with symbol column
            required_symbols: List of required symbol identifiers
            symbol_column: Name of the symbol column
            
        Raises:
            DataValidationError: If symbols are missing
        """
        if symbol_column not in df.columns:
            raise DataValidationError(f"Symbol column '{symbol_column}' not found")
        
        available_symbols = set(df[symbol_column].unique())
        required_set = set(required_symbols)
        missing_symbols = required_set - available_symbols
        
        if missing_symbols:
            raise DataValidationError(
                f"Missing data for {len(missing_symbols)} required symbols: "
                f"{sorted(list(missing_symbols))[:10]}"  # Show first 10
            )


class SignalValidator:
    """Validates signal integrity and structure."""
    
    @staticmethod
    def validate_signals(signals: Dict[str, List[str]]) -> None:
        """Validate signal dictionary structure.
        
        Args:
            signals: Dictionary with 'longs' and 'shorts' keys
            
        Raises:
            SignalValidationError: If validation fails
        """
        # Check required keys
        required_keys = ['longs', 'shorts']
        missing_keys = set(required_keys) - set(signals.keys())
        if missing_keys:
            raise SignalValidationError(
                f"Signal dictionary missing required keys: {missing_keys}"
            )
        
        # Check types
        if not isinstance(signals['longs'], list):
            raise SignalValidationError(
                f"'longs' must be a list, got {type(signals['longs'])}"
            )
        
        if not isinstance(signals['shorts'], list):
            raise SignalValidationError(
                f"'shorts' must be a list, got {type(signals['shorts'])}"
            )
        
        # Check for overlap
        longs_set = set(signals['longs'])
        shorts_set = set(signals['shorts'])
        overlap = longs_set & shorts_set
        
        if overlap:
            raise SignalValidationError(
                f"Symbols appear in both longs and shorts: {overlap}"
            )
    
    @staticmethod
    def validate_weights(
        weights: Dict[str, float],
        tolerance: float = 1e-6
    ) -> None:
        """Validate that portfolio weights are valid and sum to 1.0.
        
        Args:
            weights: Dictionary mapping symbols to weights
            tolerance: Acceptable deviation from sum=1.0
            
        Raises:
            SignalValidationError: If validation fails
        """
        if not weights:
            raise SignalValidationError("Weights dictionary is empty")
        
        # Check sum
        total = sum(weights.values())
        if abs(total - 1.0) > tolerance:
            raise SignalValidationError(
                f"Weights sum to {total:.6f}, expected 1.0 (±{tolerance})"
            )
        
        # Check for negative weights
        negative_weights = {k: v for k, v in weights.items() if v < 0}
        if negative_weights:
            raise SignalValidationError(
                f"Negative weights found: {negative_weights}"
            )
        
        # Check for NaN or infinite weights
        for symbol, weight in weights.items():
            if np.isnan(weight):
                raise SignalValidationError(f"NaN weight for {symbol}")
            if np.isinf(weight):
                raise SignalValidationError(f"Infinite weight for {symbol}")


class RiskValidator:
    """Validates risk parameters and limits."""
    
    @staticmethod
    def validate_position_size(
        notional: float,
        max_notional: float,
        symbol: str = "position"
    ) -> None:
        """Validate that position size is within limits.
        
        Args:
            notional: Position notional value
            max_notional: Maximum allowed notional
            symbol: Symbol identifier for error message
            
        Raises:
            RiskLimitError: If position size exceeds limit
        """
        if notional > max_notional:
            raise RiskLimitError(
                limit_type=f"position_size_{symbol}",
                current_value=notional,
                max_value=max_notional
            )
    
    @staticmethod
    def validate_total_exposure(
        total_exposure: float,
        max_exposure: float
    ) -> None:
        """Validate that total portfolio exposure is within limits.
        
        Args:
            total_exposure: Total portfolio exposure
            max_exposure: Maximum allowed exposure
            
        Raises:
            RiskLimitError: If total exposure exceeds limit
        """
        if total_exposure > max_exposure:
            raise RiskLimitError(
                limit_type="total_exposure",
                current_value=total_exposure,
                max_value=max_exposure
            )
    
    @staticmethod
    def validate_leverage(
        leverage: float,
        max_leverage: float
    ) -> None:
        """Validate that leverage is within limits.
        
        Args:
            leverage: Current leverage
            max_leverage: Maximum allowed leverage
            
        Raises:
            RiskLimitError: If leverage exceeds limit
        """
        if leverage > max_leverage:
            raise RiskLimitError(
                limit_type="leverage",
                current_value=leverage,
                max_value=max_leverage
            )
