"""
Custom exception hierarchy for the trading system.

Provides specific exception types for different failure modes,
making error handling more precise and debugging easier.
"""


class TradingSystemError(Exception):
    """Base exception for all trading system errors."""

    pass


# === Data-related Errors ===


class DataError(TradingSystemError):
    """Base class for data-related errors."""

    pass


class DataMissingError(DataError):
    """Required data is missing or not found."""

    pass


class DataValidationError(DataError):
    """Data failed validation checks (e.g., OHLC inconsistencies)."""

    pass


class DataStaleError(DataError):
    """Data is too old to be safely used.

    Attributes:
        data_timestamp: When the data was last updated
        current_timestamp: Current system time
        max_age_hours: Maximum allowed data age
    """

    def __init__(self, data_timestamp, current_timestamp, max_age_hours):
        self.data_timestamp = data_timestamp
        self.current_timestamp = current_timestamp
        self.max_age_hours = max_age_hours

        message = (
            f"Data is stale: last update {data_timestamp}, "
            f"current time {current_timestamp}, "
            f"max age {max_age_hours}h"
        )
        super().__init__(message)


# === Signal Calculation Errors ===


class SignalError(TradingSystemError):
    """Base class for signal calculation errors."""

    pass


class SignalCalculationError(SignalError):
    """Error during signal calculation (e.g., insufficient data)."""

    pass


class SignalValidationError(SignalError):
    """Calculated signal failed validation."""

    pass


# === Execution Errors ===


class ExecutionError(TradingSystemError):
    """Base class for trade execution errors."""

    pass


class OrderPlacementError(ExecutionError):
    """Failed to place an order."""

    pass


class OrderFillError(ExecutionError):
    """Order was not filled as expected."""

    pass


class PositionError(ExecutionError):
    """Error related to position management."""

    pass


# === External API Errors ===


class APIError(TradingSystemError):
    """Base class for external API errors."""

    pass


class APIConnectionError(APIError):
    """Failed to connect to external API."""

    pass


class APIRateLimitError(APIError):
    """Hit API rate limit."""

    def __init__(self, api_name, retry_after=None):
        self.api_name = api_name
        self.retry_after = retry_after

        message = f"Rate limit exceeded for {api_name}"
        if retry_after:
            message += f", retry after {retry_after}s"
        super().__init__(message)


class APIResponseError(APIError):
    """API returned an error response."""

    pass


# === Configuration Errors ===


class ConfigurationError(TradingSystemError):
    """Base class for configuration errors."""

    pass


class InvalidConfigError(ConfigurationError):
    """Configuration is invalid or malformed."""

    pass


class MissingConfigError(ConfigurationError):
    """Required configuration is missing."""

    pass


# === Risk Management Errors ===


class RiskError(TradingSystemError):
    """Base class for risk management errors."""

    pass


class RiskLimitError(RiskError):
    """Risk limit was exceeded.

    Attributes:
        limit_type: Type of limit that was exceeded
        current_value: Current value
        max_value: Maximum allowed value
    """

    def __init__(self, limit_type, current_value, max_value):
        self.limit_type = limit_type
        self.current_value = current_value
        self.max_value = max_value

        message = f"{limit_type} limit exceeded: " f"{current_value:.2f} > {max_value:.2f}"
        super().__init__(message)


class InsufficientCapitalError(RiskError):
    """Insufficient capital to execute trade."""

    pass
