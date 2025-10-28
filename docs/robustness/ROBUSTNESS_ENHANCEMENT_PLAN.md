# Repository Robustness & Antifragility Enhancement Plan

## Executive Summary

This document outlines a comprehensive plan to transform the crypto trading system from a functional codebase into a **robust** (resilient to failures) and **antifragile** (improving from failures) system.

**Current State Assessment:**
- ✅ Basic testing infrastructure (pytest)
- ✅ Documentation exists
- ✅ Configuration examples
- ⚠️ Limited error handling
- ❌ No CI/CD pipeline
- ❌ No type safety
- ❌ Minimal logging
- ❌ No monitoring/alerting
- ❌ No systematic validation

**Target State:**
A system that not only withstands failures but learns from them, with multiple layers of defense, comprehensive observability, and automated quality gates.

---

## 1. Foundation: Code Quality & Type Safety

### 1.1 Type Hints & Static Analysis
**Problem:** No type checking leads to runtime errors and unclear interfaces.

**Solution:**
```python
# Add type hints to all functions
def calculate_weights(
    volatilities: Dict[str, float], 
    min_vol: float = 0.0001
) -> Dict[str, float]:
    """Calculate inverse-volatility weights."""
    ...

# Use strict mypy configuration
# .mypy.ini
[mypy]
python_version = 3.10
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
disallow_untyped_calls = True
```

**Files to Create:**
- `.mypy.ini` - MyPy configuration
- `pyproject.toml` - Tool configuration hub

**Action Items:**
1. Add mypy to requirements.txt
2. Create mypy configuration
3. Add type hints to all public functions (start with signals/, execution/, data/scripts/)
4. Run `mypy --strict` and fix issues progressively

---

### 1.2 Code Formatting & Linting
**Problem:** Inconsistent code style reduces readability and increases bugs.

**Solution:**
```bash
# Add to requirements.txt
black>=23.0.0
ruff>=0.1.0  # Fast Python linter
isort>=5.12.0

# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py310']

[tool.ruff]
line-length = 100
select = [
    "E",  # pycodestyle errors
    "W",  # pycodestyle warnings
    "F",  # pyflakes
    "I",  # isort
    "B",  # flake8-bugbear
    "C4", # flake8-comprehensions
    "UP", # pyupgrade
]
ignore = ["E501"]  # line too long (handled by black)

[tool.isort]
profile = "black"
line_length = 100
```

**Action Items:**
1. Add formatting/linting tools to requirements
2. Create pyproject.toml with configurations
3. Format entire codebase: `black .`
4. Fix linting issues: `ruff check . --fix`
5. Sort imports: `isort .`

---

### 1.3 Pre-commit Hooks
**Problem:** Quality checks happen too late (after commit/push).

**Solution:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
      - id: check-merge-conflict
      - id: detect-private-key
  
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
  
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]
  
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [pandas-stubs, types-requests]
```

**Action Items:**
1. Install: `pip install pre-commit`
2. Create `.pre-commit-config.yaml`
3. Install hooks: `pre-commit install`
4. Test: `pre-commit run --all-files`

---

## 2. Defensive Programming: Error Handling & Validation

### 2.1 Custom Exception Hierarchy
**Problem:** Generic exceptions make debugging difficult and error handling imprecise.

**Solution:**
```python
# common/exceptions.py
class TradingSystemError(Exception):
    """Base exception for trading system."""
    pass

class DataError(TradingSystemError):
    """Data-related errors (missing, invalid, stale)."""
    pass

class DataMissingError(DataError):
    """Required data not found."""
    pass

class DataValidationError(DataError):
    """Data failed validation checks."""
    pass

class DataStaleError(DataError):
    """Data is too old to be usable."""
    def __init__(self, data_timestamp, current_timestamp, max_age_hours):
        self.data_timestamp = data_timestamp
        self.current_timestamp = current_timestamp
        self.max_age_hours = max_age_hours
        super().__init__(
            f"Data is stale: {data_timestamp} vs {current_timestamp} "
            f"(max age: {max_age_hours}h)"
        )

class SignalError(TradingSystemError):
    """Signal calculation errors."""
    pass

class ExecutionError(TradingSystemError):
    """Trade execution errors."""
    pass

class APIError(TradingSystemError):
    """External API errors."""
    pass

class ConfigurationError(TradingSystemError):
    """Invalid configuration."""
    pass

class RiskLimitError(TradingSystemError):
    """Risk limit exceeded."""
    def __init__(self, limit_type, current_value, max_value):
        self.limit_type = limit_type
        self.current_value = current_value
        self.max_value = max_value
        super().__init__(
            f"{limit_type} limit exceeded: {current_value} > {max_value}"
        )
```

**Action Items:**
1. Create `common/exceptions.py`
2. Replace all generic `Exception` with specific types
3. Add context to exceptions (timestamps, values, limits)

---

### 2.2 Input Validation Layer
**Problem:** Invalid inputs cause failures deep in the stack.

**Solution:**
```python
# common/validators.py
from typing import Optional, List, Union
from datetime import datetime
import pandas as pd
from .exceptions import DataValidationError

class DataValidator:
    """Validates data integrity and structure."""
    
    @staticmethod
    def validate_ohlcv_dataframe(
        df: pd.DataFrame,
        required_columns: Optional[List[str]] = None
    ) -> None:
        """Validate OHLCV dataframe structure and content."""
        if required_columns is None:
            required_columns = ['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']
        
        # Check structure
        if df.empty:
            raise DataValidationError("DataFrame is empty")
        
        missing_cols = set(required_columns) - set(df.columns)
        if missing_cols:
            raise DataValidationError(f"Missing columns: {missing_cols}")
        
        # Check OHLC consistency
        if not (df['high'] >= df['low']).all():
            invalid_rows = df[df['high'] < df['low']]
            raise DataValidationError(
                f"High < Low in {len(invalid_rows)} rows: {invalid_rows.head()}"
            )
        
        if not (df['high'] >= df['close']).all():
            raise DataValidationError("High < Close in some rows")
        
        if not (df['low'] <= df['close']).all():
            raise DataValidationError("Low > Close in some rows")
        
        # Check for nulls in critical columns
        critical_nulls = df[required_columns].isnull().sum()
        if critical_nulls.any():
            raise DataValidationError(
                f"Null values in critical columns: {critical_nulls[critical_nulls > 0]}"
            )
        
        # Check for negative prices
        price_cols = ['open', 'high', 'low', 'close']
        for col in price_cols:
            if (df[col] <= 0).any():
                raise DataValidationError(f"Non-positive values in {col}")
    
    @staticmethod
    def validate_date_range(
        df: pd.DataFrame,
        max_age_hours: int = 48,
        date_column: str = 'date'
    ) -> None:
        """Validate data freshness."""
        if df.empty:
            raise DataValidationError("Cannot validate date range on empty DataFrame")
        
        latest_date = pd.to_datetime(df[date_column]).max()
        current_time = pd.Timestamp.now(tz='UTC')
        
        if latest_date.tz is None:
            latest_date = latest_date.tz_localize('UTC')
        
        age_hours = (current_time - latest_date).total_seconds() / 3600
        
        if age_hours > max_age_hours:
            from .exceptions import DataStaleError
            raise DataStaleError(latest_date, current_time, max_age_hours)
    
    @staticmethod
    def validate_weights(weights: dict, tolerance: float = 1e-6) -> None:
        """Validate portfolio weights sum to 1.0."""
        if not weights:
            raise DataValidationError("Weights dictionary is empty")
        
        total = sum(weights.values())
        if abs(total - 1.0) > tolerance:
            raise DataValidationError(
                f"Weights sum to {total:.6f}, expected 1.0 (±{tolerance})"
            )
        
        # Check for negative weights
        negative = {k: v for k, v in weights.items() if v < 0}
        if negative:
            raise DataValidationError(f"Negative weights found: {negative}")
    
    @staticmethod
    def validate_signals(signals: dict) -> None:
        """Validate signal dictionary structure."""
        required_keys = ['longs', 'shorts']
        missing = set(required_keys) - set(signals.keys())
        if missing:
            raise DataValidationError(f"Signal dict missing keys: {missing}")
        
        # Ensure lists
        if not isinstance(signals['longs'], list):
            raise DataValidationError("'longs' must be a list")
        if not isinstance(signals['shorts'], list):
            raise DataValidationError("'shorts' must be a list")
        
        # Check for overlap
        overlap = set(signals['longs']) & set(signals['shorts'])
        if overlap:
            raise DataValidationError(f"Symbols in both longs and shorts: {overlap}")
```

**Action Items:**
1. Create `common/validators.py`
2. Add validation calls at all data ingestion points
3. Add validation before signal calculation
4. Add validation before order execution

---

### 2.3 Comprehensive Error Handling
**Problem:** Bare `except:` clauses hide errors; no retry logic.

**Solution:**
```python
# common/retry.py
import time
import functools
from typing import Callable, Type, Tuple
import logging

logger = logging.getLogger(__name__)

def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """Retry decorator with exponential backoff."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    attempt += 1
                    if attempt >= max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                        f"Retrying in {current_delay}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
            
        return wrapper
    return decorator


# Usage example in data fetching
from common.retry import retry
from common.exceptions import APIError

@retry(max_attempts=3, delay=2.0, exceptions=(APIError, ConnectionError))
def fetch_market_data(symbol: str) -> pd.DataFrame:
    """Fetch market data with automatic retry."""
    try:
        data = api.get_ohlcv(symbol)
        if data is None:
            raise APIError(f"No data returned for {symbol}")
        return data
    except requests.RequestException as e:
        raise APIError(f"API request failed: {e}") from e
```

**Action Items:**
1. Create `common/retry.py`
2. Replace bare `except:` with specific exception types
3. Add retry logic to all external API calls
4. Add retry to database/file operations

---

## 3. Observability: Logging, Monitoring & Alerting

### 3.1 Structured Logging
**Problem:** Minimal logging makes debugging production issues impossible.

**Solution:**
```python
# common/logging_config.py
import logging
import logging.handlers
import json
from datetime import datetime
from typing import Any, Dict

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for easy parsing."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)

def setup_logging(
    log_level: str = "INFO",
    log_file: str = "logs/trading_system.log",
    enable_json: bool = False
) -> None:
    """Configure logging for the entire application."""
    
    # Create logs directory
    import os
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Console handler (human-readable)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    
    # File handler (JSON for production)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=50 * 1024 * 1024,  # 50MB
        backupCount=10
    )
    file_handler.setLevel(logging.DEBUG)
    
    if enable_json:
        file_handler.setFormatter(JSONFormatter())
    else:
        file_handler.setFormatter(console_format)
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('ccxt').setLevel(logging.WARNING)

class ContextLogger:
    """Logger with context fields for better tracing."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs):
        """Add context fields to all logs."""
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear all context."""
        self.context = {}
    
    def _log(self, level: int, msg: str, **kwargs):
        """Internal logging with context."""
        extra = {'extra_fields': {**self.context, **kwargs}}
        self.logger.log(level, msg, extra=extra)
    
    def debug(self, msg: str, **kwargs):
        self._log(logging.DEBUG, msg, **kwargs)
    
    def info(self, msg: str, **kwargs):
        self._log(logging.INFO, msg, **kwargs)
    
    def warning(self, msg: str, **kwargs):
        self._log(logging.WARNING, msg, **kwargs)
    
    def error(self, msg: str, **kwargs):
        self._log(logging.ERROR, msg, **kwargs)
    
    def critical(self, msg: str, **kwargs):
        self._log(logging.CRITICAL, msg, **kwargs)


# Usage in main.py
from common.logging_config import setup_logging, ContextLogger
import logging

setup_logging(log_level="INFO", enable_json=True)
logger = ContextLogger(logging.getLogger(__name__))

# Set context for all logs in this execution
logger.set_context(
    run_id="backtest_20251028",
    strategy="mean_reversion",
    environment="production"
)

logger.info("Starting backtest", symbols=["BTC", "ETH"], start_date="2024-01-01")
```

**Action Items:**
1. Create `common/logging_config.py`
2. Create `logs/` directory with `.gitignore`
3. Add logging to all critical functions
4. Log at decision points (signal generation, order placement, risk checks)
5. Add performance logging (timing, memory usage)

---

### 3.2 Metrics & Monitoring
**Problem:** No visibility into system health and performance.

**Solution:**
```python
# common/metrics.py
from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime
import json

@dataclass
class SystemMetrics:
    """Track system health metrics."""
    
    # Data metrics
    data_fetch_count: int = 0
    data_fetch_errors: int = 0
    data_staleness_warnings: int = 0
    
    # Signal metrics
    signals_generated: int = 0
    signal_errors: int = 0
    long_signals: int = 0
    short_signals: int = 0
    
    # Execution metrics
    orders_placed: int = 0
    orders_filled: int = 0
    orders_failed: int = 0
    total_notional: float = 0.0
    
    # Performance metrics
    avg_api_latency_ms: float = 0.0
    max_memory_mb: float = 0.0
    
    # Risk metrics
    risk_limit_breaches: int = 0
    
    # Timing
    start_time: datetime = field(default_factory=datetime.utcnow)
    last_update: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'data': {
                'fetch_count': self.data_fetch_count,
                'fetch_errors': self.data_fetch_errors,
                'staleness_warnings': self.data_staleness_warnings,
            },
            'signals': {
                'generated': self.signals_generated,
                'errors': self.signal_errors,
                'long': self.long_signals,
                'short': self.short_signals,
            },
            'execution': {
                'orders_placed': self.orders_placed,
                'orders_filled': self.orders_filled,
                'orders_failed': self.orders_failed,
                'total_notional': self.total_notional,
            },
            'performance': {
                'avg_api_latency_ms': self.avg_api_latency_ms,
                'max_memory_mb': self.max_memory_mb,
            },
            'risk': {
                'limit_breaches': self.risk_limit_breaches,
            },
            'timing': {
                'start_time': self.start_time.isoformat(),
                'last_update': self.last_update.isoformat(),
                'uptime_seconds': (datetime.utcnow() - self.start_time).total_seconds(),
            }
        }
    
    def save_to_file(self, filepath: str):
        """Save metrics to file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    def increment_data_fetch(self, success: bool = True):
        """Increment data fetch counter."""
        self.data_fetch_count += 1
        if not success:
            self.data_fetch_errors += 1
        self.last_update = datetime.utcnow()


# Global metrics instance
_metrics = SystemMetrics()

def get_metrics() -> SystemMetrics:
    """Get global metrics instance."""
    return _metrics
```

**Action Items:**
1. Create `common/metrics.py`
2. Add metric collection to all key operations
3. Export metrics to file after each run
4. Create dashboard script to visualize metrics

---

### 3.3 Health Checks
**Problem:** No systematic way to verify system health.

**Solution:**
```python
# common/health_checks.py
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, timedelta
import pandas as pd
from .exceptions import DataStaleError

@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    passed: bool
    message: str
    timestamp: datetime = datetime.utcnow()
    severity: str = "INFO"  # INFO, WARNING, CRITICAL

class HealthChecker:
    """Perform system health checks."""
    
    def __init__(self):
        self.results: List[HealthCheckResult] = []
    
    def check_data_freshness(
        self,
        df: pd.DataFrame,
        max_age_hours: int = 24,
        date_column: str = 'date'
    ) -> HealthCheckResult:
        """Check if data is fresh enough."""
        try:
            latest_date = pd.to_datetime(df[date_column]).max()
            age_hours = (datetime.utcnow() - latest_date.replace(tzinfo=None)).total_seconds() / 3600
            
            if age_hours > max_age_hours:
                result = HealthCheckResult(
                    name="data_freshness",
                    passed=False,
                    message=f"Data is {age_hours:.1f}h old (max: {max_age_hours}h)",
                    severity="CRITICAL"
                )
            else:
                result = HealthCheckResult(
                    name="data_freshness",
                    passed=True,
                    message=f"Data is {age_hours:.1f}h old (within limit)"
                )
            
            self.results.append(result)
            return result
        
        except Exception as e:
            result = HealthCheckResult(
                name="data_freshness",
                passed=False,
                message=f"Error checking data freshness: {e}",
                severity="CRITICAL"
            )
            self.results.append(result)
            return result
    
    def check_data_completeness(
        self,
        df: pd.DataFrame,
        expected_symbols: List[str],
        date_column: str = 'date'
    ) -> HealthCheckResult:
        """Check if all expected symbols have data."""
        try:
            available_symbols = set(df['symbol'].unique())
            expected_set = set(expected_symbols)
            missing = expected_set - available_symbols
            
            if missing:
                result = HealthCheckResult(
                    name="data_completeness",
                    passed=False,
                    message=f"Missing data for {len(missing)} symbols: {list(missing)[:5]}...",
                    severity="WARNING"
                )
            else:
                result = HealthCheckResult(
                    name="data_completeness",
                    passed=True,
                    message=f"All {len(expected_symbols)} symbols have data"
                )
            
            self.results.append(result)
            return result
        
        except Exception as e:
            result = HealthCheckResult(
                name="data_completeness",
                passed=False,
                message=f"Error checking data completeness: {e}",
                severity="CRITICAL"
            )
            self.results.append(result)
            return result
    
    def check_api_connectivity(self) -> HealthCheckResult:
        """Check if external APIs are reachable."""
        # TODO: Implement API ping
        pass
    
    def check_disk_space(self, min_gb: float = 1.0) -> HealthCheckResult:
        """Check available disk space."""
        import shutil
        try:
            usage = shutil.disk_usage('/')
            free_gb = usage.free / (1024**3)
            
            if free_gb < min_gb:
                result = HealthCheckResult(
                    name="disk_space",
                    passed=False,
                    message=f"Low disk space: {free_gb:.2f}GB (min: {min_gb}GB)",
                    severity="CRITICAL"
                )
            else:
                result = HealthCheckResult(
                    name="disk_space",
                    passed=True,
                    message=f"Disk space OK: {free_gb:.2f}GB available"
                )
            
            self.results.append(result)
            return result
        
        except Exception as e:
            result = HealthCheckResult(
                name="disk_space",
                passed=False,
                message=f"Error checking disk space: {e}",
                severity="WARNING"
            )
            self.results.append(result)
            return result
    
    def get_summary(self) -> dict:
        """Get summary of all health checks."""
        return {
            'total_checks': len(self.results),
            'passed': sum(1 for r in self.results if r.passed),
            'failed': sum(1 for r in self.results if not r.passed),
            'critical_failures': sum(
                1 for r in self.results if not r.passed and r.severity == "CRITICAL"
            ),
            'checks': [
                {
                    'name': r.name,
                    'passed': r.passed,
                    'message': r.message,
                    'severity': r.severity,
                    'timestamp': r.timestamp.isoformat()
                }
                for r in self.results
            ]
        }
```

**Action Items:**
1. Create `common/health_checks.py`
2. Run health checks at startup
3. Run periodic health checks during execution
4. Block execution if critical checks fail

---

## 4. Testing: Comprehensive Coverage

### 4.1 Expand Unit Tests
**Current:** ~315 lines of tests for signals only
**Target:** 80%+ code coverage across all modules

```python
# tests/test_validators.py
import pytest
import pandas as pd
from common.validators import DataValidator
from common.exceptions import DataValidationError

class TestDataValidator:
    
    def test_validate_ohlcv_valid_data(self):
        """Test validation passes for valid OHLCV data."""
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'symbol': ['BTC'] * 10,
            'open': [100.0] * 10,
            'high': [105.0] * 10,
            'low': [95.0] * 10,
            'close': [102.0] * 10,
            'volume': [1000.0] * 10,
        })
        
        # Should not raise
        DataValidator.validate_ohlcv_dataframe(df)
    
    def test_validate_ohlcv_high_less_than_low(self):
        """Test validation fails when high < low."""
        df = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=10),
            'symbol': ['BTC'] * 10,
            'open': [100.0] * 10,
            'high': [95.0] * 10,  # High < Low!
            'low': [100.0] * 10,
            'close': [102.0] * 10,
            'volume': [1000.0] * 10,
        })
        
        with pytest.raises(DataValidationError, match="High < Low"):
            DataValidator.validate_ohlcv_dataframe(df)
    
    def test_validate_weights_sum_not_one(self):
        """Test validation fails when weights don't sum to 1.0."""
        weights = {'BTC': 0.6, 'ETH': 0.3}  # Sum = 0.9
        
        with pytest.raises(DataValidationError, match="Weights sum"):
            DataValidator.validate_weights(weights)
    
    def test_validate_weights_negative(self):
        """Test validation fails for negative weights."""
        weights = {'BTC': 0.7, 'ETH': 0.5, 'SOL': -0.2}
        
        with pytest.raises(DataValidationError, match="Negative weights"):
            DataValidator.validate_weights(weights)


# tests/test_retry.py
import pytest
from common.retry import retry
from common.exceptions import APIError

class TestRetryDecorator:
    
    def test_retry_succeeds_first_attempt(self):
        """Test that successful call on first attempt works."""
        call_count = 0
        
        @retry(max_attempts=3)
        def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_func()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_succeeds_after_failures(self):
        """Test that retry works after initial failures."""
        call_count = 0
        
        @retry(max_attempts=3, delay=0.01)
        def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise APIError("Temporary failure")
            return "success"
        
        result = flaky_func()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_exhausts_attempts(self):
        """Test that retry raises after max attempts."""
        call_count = 0
        
        @retry(max_attempts=3, delay=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise APIError("Permanent failure")
        
        with pytest.raises(APIError, match="Permanent failure"):
            always_fails()
        
        assert call_count == 3
```

**Action Items:**
1. Add tests for all validators
2. Add tests for retry logic
3. Add tests for custom exceptions
4. Add integration tests for end-to-end workflows
5. Add property-based tests using hypothesis
6. Target 80% code coverage minimum

---

### 4.2 Integration Tests
**Problem:** Unit tests don't catch integration issues.

```python
# tests/integration/test_full_workflow.py
import pytest
import pandas as pd
from datetime import datetime, timedelta

class TestFullWorkflow:
    """Test complete workflows end-to-end."""
    
    def test_data_to_signals_to_weights(self, sample_market_data):
        """Test full pipeline from data to portfolio weights."""
        # 1. Load data
        from data.scripts.ccxt_get_data import load_data
        df = load_data(sample_market_data)
        
        # 2. Validate data
        from common.validators import DataValidator
        DataValidator.validate_ohlcv_dataframe(df)
        
        # 3. Calculate signals
        from signals.calc_breakout_signals import calculate_breakout_signals
        signals_df = calculate_breakout_signals(df)
        
        # 4. Calculate volatilities
        from signals.calc_vola import calculate_rolling_30d_volatility
        vola_df = calculate_rolling_30d_volatility(df)
        
        # 5. Calculate weights
        from signals.calc_weights import calculate_weights
        latest_vola = vola_df.groupby('symbol')['volatility_30d'].last()
        weights = calculate_weights(latest_vola.to_dict())
        
        # 6. Validate weights
        DataValidator.validate_weights(weights)
        
        # Assert final state
        assert len(weights) > 0
        assert abs(sum(weights.values()) - 1.0) < 1e-6
    
    def test_backtest_execution(self):
        """Test that backtest runs without errors."""
        from backtests.scripts.backtest_mean_reversion import run_backtest
        
        # Run with minimal data
        results = run_backtest(
            start_date='2024-01-01',
            end_date='2024-01-31',
            symbols=['BTC/USDC:USDC', 'ETH/USDC:USDC']
        )
        
        # Check results structure
        assert 'sharpe_ratio' in results
        assert 'total_return' in results
        assert 'metrics' in results
```

**Action Items:**
1. Create `tests/integration/` directory
2. Add end-to-end workflow tests
3. Add backtest execution tests
4. Add data pipeline tests

---

### 4.3 Property-Based Testing
**Problem:** Edge cases are missed by example-based tests.

```python
# tests/test_properties.py
import hypothesis
from hypothesis import given, strategies as st
import pandas as pd
from signals.calc_weights import calculate_weights

class TestPropertiesWeights:
    
    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=10),
        values=st.floats(min_value=0.01, max_value=10.0),
        min_size=1,
        max_size=20
    ))
    def test_weights_always_sum_to_one(self, volatilities):
        """Property: weights should always sum to 1.0."""
        weights = calculate_weights(volatilities)
        
        if weights:  # Not empty
            total = sum(weights.values())
            assert abs(total - 1.0) < 1e-6, f"Weights sum to {total}"
    
    @given(st.dictionaries(
        keys=st.text(min_size=1, max_size=10),
        values=st.floats(min_value=0.01, max_value=10.0),
        min_size=1,
        max_size=20
    ))
    def test_weights_are_positive(self, volatilities):
        """Property: all weights should be positive."""
        weights = calculate_weights(volatilities)
        
        for symbol, weight in weights.items():
            assert weight > 0, f"Weight for {symbol} is not positive: {weight}"
    
    @given(st.floats(min_value=0.01, max_value=1.0))
    def test_single_asset_gets_full_weight(self, volatility):
        """Property: single asset should get 100% weight."""
        weights = calculate_weights({'ASSET': volatility})
        
        assert len(weights) == 1
        assert abs(weights['ASSET'] - 1.0) < 1e-6
```

**Action Items:**
1. Add hypothesis to requirements.txt
2. Add property-based tests for critical functions
3. Run property tests with high example counts in CI

---

## 5. CI/CD: Automated Quality Gates

### 5.1 GitHub Actions Workflow
**Problem:** No automated testing on commits.

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [ main, develop, cursor/* ]
  pull_request:
    branches: [ main, develop ]

jobs:
  quality:
    name: Code Quality
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Check formatting (black)
        run: black --check .
      
      - name: Lint (ruff)
        run: ruff check .
      
      - name: Type check (mypy)
        run: mypy . --ignore-missing-imports
        continue-on-error: true  # Initially allow failures
      
      - name: Security check (bandit)
        run: bandit -r . -x ./tests
  
  test:
    name: Tests
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11']
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run tests with coverage
        run: |
          python3 run_tests.py
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: false
  
  integration:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: [quality, test]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Run integration tests
        run: |
          pytest tests/integration/ -v
  
  security:
    name: Security Scan
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'
```

**Action Items:**
1. Create `.github/workflows/ci.yml`
2. Add branch protection rules requiring checks to pass
3. Enable CodeCov for coverage tracking
4. Add security scanning

---

### 5.2 Continuous Deployment
**Problem:** Manual deployment is error-prone.

```yaml
# .github/workflows/cd.yml
name: CD

on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  release:
    name: Create Release
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Run full test suite
        run: |
          pip install -r requirements.txt
          python3 run_tests.py
      
      - name: Build distribution
        run: |
          pip install build
          python -m build
      
      - name: Create GitHub Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          draft: false
          prerelease: false
      
      - name: Archive backtest results
        run: |
          tar -czf backtest-results-${{ github.ref_name }}.tar.gz backtests/results/
      
      - name: Upload release assets
        uses: actions/upload-release-asset@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          upload_url: ${{ steps.create_release.outputs.upload_url }}
          asset_path: ./backtest-results-${{ github.ref_name }}.tar.gz
          asset_name: backtest-results-${{ github.ref_name }}.tar.gz
          asset_content_type: application/gzip
```

**Action Items:**
1. Create `.github/workflows/cd.yml`
2. Set up semantic versioning
3. Automate backtest result archiving
4. Create deployment checklist

---

## 6. Infrastructure: Resilience & Scalability

### 6.1 Circuit Breaker Pattern
**Problem:** Cascading failures when external services are down.

```python
# common/circuit_breaker.py
from enum import Enum
from datetime import datetime, timedelta
from typing import Callable, Optional
import functools

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered

class CircuitBreaker:
    """Circuit breaker to prevent cascading failures."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function through circuit breaker."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception(f"Circuit breaker OPEN for {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        
        except self.expected_exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to try recovery."""
        if self.last_failure_time is None:
            return False
        
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60
):
    """Decorator to add circuit breaker to function."""
    breaker = CircuitBreaker(failure_threshold, recovery_timeout)
    
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator


# Usage
from common.circuit_breaker import circuit_breaker

@circuit_breaker(failure_threshold=3, recovery_timeout=30)
def fetch_external_data(symbol: str):
    """Fetch data from external API with circuit breaker."""
    return api.get_data(symbol)
```

**Action Items:**
1. Create `common/circuit_breaker.py`
2. Add circuit breakers to all external API calls
3. Add circuit breaker monitoring/alerting

---

### 6.2 Rate Limiting
**Problem:** API rate limits cause execution failures.

```python
# common/rate_limiter.py
import time
from collections import deque
from datetime import datetime, timedelta
from threading import Lock

class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(
        self,
        max_requests: int,
        time_window: int,
        name: str = "default"
    ):
        self.max_requests = max_requests
        self.time_window = time_window  # seconds
        self.name = name
        self.requests = deque()
        self.lock = Lock()
    
    def acquire(self, blocking: bool = True) -> bool:
        """Acquire permission to make a request."""
        with self.lock:
            now = time.time()
            
            # Remove old requests outside time window
            while self.requests and self.requests[0] < now - self.time_window:
                self.requests.popleft()
            
            # Check if we can make request
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            
            if not blocking:
                return False
            
            # Wait until oldest request expires
            sleep_time = self.time_window - (now - self.requests[0]) + 0.1
            
        time.sleep(sleep_time)
        return self.acquire(blocking=True)
    
    def __enter__(self):
        """Context manager entry."""
        self.acquire()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass


# Global rate limiters for different APIs
API_RATE_LIMITERS = {
    'coinalyze': RateLimiter(max_requests=10, time_window=60, name='coinalyze'),
    'coinmarketcap': RateLimiter(max_requests=30, time_window=60, name='coinmarketcap'),
    'ccxt': RateLimiter(max_requests=1, time_window=1, name='ccxt'),  # 1 req/sec
}


# Usage
from common.rate_limiter import API_RATE_LIMITERS

def fetch_coinalyze_data(symbol: str):
    """Fetch data with rate limiting."""
    with API_RATE_LIMITERS['coinalyze']:
        return coinalyze_api.get_funding_rates(symbol)
```

**Action Items:**
1. Create `common/rate_limiter.py`
2. Add rate limiting to all API calls
3. Make rate limits configurable
4. Log rate limit hits

---

### 6.3 Caching Layer
**Problem:** Repeated API calls waste time and hit rate limits.

```python
# common/cache.py
import pickle
import hashlib
import os
from datetime import datetime, timedelta
from typing import Any, Optional, Callable
import functools

class FileCache:
    """Simple file-based cache with TTL."""
    
    def __init__(self, cache_dir: str = ".cache", default_ttl: int = 3600):
        self.cache_dir = cache_dir
        self.default_ttl = default_ttl
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Generate cache key from function name and arguments."""
        key_data = f"{func_name}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _get_cache_path(self, cache_key: str) -> str:
        """Get filesystem path for cache key."""
        return os.path.join(self.cache_dir, f"{cache_key}.pkl")
    
    def get(self, cache_key: str) -> Optional[Any]:
        """Get value from cache."""
        cache_path = self._get_cache_path(cache_key)
        
        if not os.path.exists(cache_path):
            return None
        
        # Check if expired
        mtime = datetime.fromtimestamp(os.path.getmtime(cache_path))
        if datetime.now() - mtime > timedelta(seconds=self.default_ttl):
            os.remove(cache_path)
            return None
        
        with open(cache_path, 'rb') as f:
            return pickle.load(f)
    
    def set(self, cache_key: str, value: Any):
        """Set value in cache."""
        cache_path = self._get_cache_path(cache_key)
        with open(cache_path, 'wb') as f:
            pickle.dump(value, f)
    
    def clear(self):
        """Clear all cache."""
        for filename in os.listdir(self.cache_dir):
            os.remove(os.path.join(self.cache_dir, filename))


def cached(ttl: int = 3600):
    """Decorator to cache function results."""
    cache = FileCache(default_ttl=ttl)
    
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = cache._get_cache_key(func.__name__, args, kwargs)
            
            # Try cache first
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Compute and cache
            result = func(*args, **kwargs)
            cache.set(cache_key, result)
            return result
        
        return wrapper
    return decorator


# Usage
from common.cache import cached

@cached(ttl=3600)  # Cache for 1 hour
def fetch_market_cap_data():
    """Fetch market cap data (expensive operation)."""
    return api.get_market_caps()
```

**Action Items:**
1. Create `common/cache.py`
2. Add caching to expensive operations
3. Add cache warming at startup
4. Add cache invalidation logic

---

## 7. Configuration Management

### 7.1 Environment-Specific Configs
**Problem:** Single config doesn't work for dev/staging/prod.

```python
# common/config.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import yaml
import os
from enum import Enum

class Environment(Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

@dataclass
class RiskConfig:
    leverage: float = 1.5
    max_notional_usd: float = 100000
    per_asset_max_notional_usd: float = 10000
    rebalance_threshold: float = 0.05

@dataclass
class ExecutionConfig:
    dry_run: bool = True
    aggressive: bool = True
    tick_wait_seconds: int = 10
    cross_spread_on_timeout: bool = True

@dataclass
class MonitoringConfig:
    enable_logging: bool = True
    log_level: str = "INFO"
    enable_metrics: bool = True
    metrics_export_interval: int = 60
    health_check_interval: int = 300

@dataclass
class Config:
    environment: Environment
    risk: RiskConfig
    execution: ExecutionConfig
    monitoring: MonitoringConfig
    api_keys: Dict[str, str] = field(default_factory=dict)
    
    @classmethod
    def from_yaml(cls, filepath: str) -> 'Config':
        """Load config from YAML file."""
        with open(filepath, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls(
            environment=Environment(data.get('environment', 'development')),
            risk=RiskConfig(**data.get('risk', {})),
            execution=ExecutionConfig(**data.get('execution', {})),
            monitoring=MonitoringConfig(**data.get('monitoring', {})),
            api_keys=data.get('api_keys', {})
        )
    
    @classmethod
    def from_env(cls) -> 'Config':
        """Load config from environment variables."""
        env = os.getenv('TRADING_ENV', 'development')
        config_path = f"configs/config.{env}.yaml"
        
        if os.path.exists(config_path):
            return cls.from_yaml(config_path)
        
        # Fallback to default
        return cls(
            environment=Environment(env),
            risk=RiskConfig(),
            execution=ExecutionConfig(),
            monitoring=MonitoringConfig()
        )

# Global config instance
_config: Optional[Config] = None

def get_config() -> Config:
    """Get global config instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config

def set_config(config: Config):
    """Set global config instance."""
    global _config
    _config = config
```

**Action Items:**
1. Create `common/config.py`
2. Create environment-specific config files:
   - `configs/config.development.yaml`
   - `configs/config.staging.yaml`
   - `configs/config.production.yaml`
3. Use config throughout codebase
4. Add config validation

---

## 8. Antifragility: Learning from Failures

### 8.1 Failure Database
**Problem:** Same errors occur repeatedly without learning.

```python
# common/failure_tracker.py
import json
import sqlite3
from datetime import datetime
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict

@dataclass
class Failure:
    """Record of a system failure."""
    timestamp: str
    component: str
    error_type: str
    error_message: str
    stack_trace: Optional[str]
    context: Dict
    severity: str
    resolved: bool = False
    resolution: Optional[str] = None

class FailureDatabase:
    """Track and analyze system failures."""
    
    def __init__(self, db_path: str = "failures.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS failures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                component TEXT NOT NULL,
                error_type TEXT NOT NULL,
                error_message TEXT,
                stack_trace TEXT,
                context TEXT,
                severity TEXT,
                resolved BOOLEAN DEFAULT 0,
                resolution TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON failures(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_component ON failures(component)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_error_type ON failures(error_type)
        ''')
        
        conn.commit()
        conn.close()
    
    def record_failure(self, failure: Failure):
        """Record a failure."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO failures 
            (timestamp, component, error_type, error_message, stack_trace, 
             context, severity, resolved, resolution)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            failure.timestamp,
            failure.component,
            failure.error_type,
            failure.error_message,
            failure.stack_trace,
            json.dumps(failure.context),
            failure.severity,
            failure.resolved,
            failure.resolution
        ))
        
        conn.commit()
        conn.close()
    
    def get_recent_failures(self, hours: int = 24) -> List[Failure]:
        """Get failures from last N hours."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM failures 
            WHERE timestamp > datetime('now', '-{} hours')
            ORDER BY timestamp DESC
        '''.format(hours))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [
            Failure(
                timestamp=row['timestamp'],
                component=row['component'],
                error_type=row['error_type'],
                error_message=row['error_message'],
                stack_trace=row['stack_trace'],
                context=json.loads(row['context']),
                severity=row['severity'],
                resolved=bool(row['resolved']),
                resolution=row['resolution']
            )
            for row in rows
        ]
    
    def get_failure_patterns(self) -> Dict[str, int]:
        """Analyze failure patterns."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT error_type, COUNT(*) as count
            FROM failures
            WHERE timestamp > datetime('now', '-7 days')
            GROUP BY error_type
            ORDER BY count DESC
        ''')
        
        patterns = {row[0]: row[1] for row in cursor.fetchall()}
        conn.close()
        
        return patterns
    
    def mark_resolved(self, failure_id: int, resolution: str):
        """Mark a failure as resolved."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE failures
            SET resolved = 1, resolution = ?
            WHERE id = ?
        ''', (resolution, failure_id))
        
        conn.commit()
        conn.close()


# Global failure tracker
_failure_db = FailureDatabase()

def record_failure(
    component: str,
    error: Exception,
    severity: str = "ERROR",
    **context
):
    """Record a failure for analysis."""
    import traceback
    
    failure = Failure(
        timestamp=datetime.utcnow().isoformat(),
        component=component,
        error_type=type(error).__name__,
        error_message=str(error),
        stack_trace=traceback.format_exc(),
        context=context,
        severity=severity
    )
    
    _failure_db.record_failure(failure)
```

**Action Items:**
1. Create `common/failure_tracker.py`
2. Record all failures to database
3. Create weekly failure analysis script
4. Add failure pattern detection
5. Create auto-remediation for common failures

---

### 8.2 Adaptive Risk Management
**Problem:** Fixed risk limits don't adapt to market conditions.

```python
# common/adaptive_risk.py
import pandas as pd
from typing import Dict
from dataclasses import dataclass

@dataclass
class MarketRegime:
    """Market regime classification."""
    volatility: str  # low, medium, high
    trend: str  # up, down, sideways
    liquidity: str  # high, medium, low

class AdaptiveRiskManager:
    """Adjust risk parameters based on market conditions."""
    
    def __init__(self, base_leverage: float = 1.5):
        self.base_leverage = base_leverage
        self.current_regime: MarketRegime = MarketRegime("medium", "sideways", "high")
    
    def detect_regime(self, market_data: pd.DataFrame) -> MarketRegime:
        """Detect current market regime."""
        # Calculate volatility
        returns = market_data['close'].pct_change()
        volatility_30d = returns.rolling(30).std().iloc[-1]
        
        if volatility_30d < 0.02:
            vol_regime = "low"
        elif volatility_30d < 0.05:
            vol_regime = "medium"
        else:
            vol_regime = "high"
        
        # Calculate trend
        sma_50 = market_data['close'].rolling(50).mean().iloc[-1]
        sma_200 = market_data['close'].rolling(200).mean().iloc[-1]
        current_price = market_data['close'].iloc[-1]
        
        if current_price > sma_50 > sma_200:
            trend = "up"
        elif current_price < sma_50 < sma_200:
            trend = "down"
        else:
            trend = "sideways"
        
        # Calculate liquidity (volume-based)
        volume_avg = market_data['volume'].rolling(30).mean().iloc[-1]
        volume_recent = market_data['volume'].iloc[-5:].mean()
        
        if volume_recent > volume_avg * 1.2:
            liquidity = "high"
        elif volume_recent > volume_avg * 0.8:
            liquidity = "medium"
        else:
            liquidity = "low"
        
        self.current_regime = MarketRegime(vol_regime, trend, liquidity)
        return self.current_regime
    
    def get_adjusted_leverage(self) -> float:
        """Get leverage adjusted for current regime."""
        leverage = self.base_leverage
        
        # Reduce leverage in high volatility
        if self.current_regime.volatility == "high":
            leverage *= 0.7
        elif self.current_regime.volatility == "low":
            leverage *= 1.2
        
        # Reduce leverage in low liquidity
        if self.current_regime.liquidity == "low":
            leverage *= 0.8
        
        return min(leverage, self.base_leverage * 1.5)  # Cap at 1.5x base
    
    def get_adjusted_position_size(self, base_size: float) -> float:
        """Get position size adjusted for regime."""
        size = base_size
        
        # Smaller positions in adverse conditions
        if self.current_regime.volatility == "high":
            size *= 0.7
        
        if self.current_regime.liquidity == "low":
            size *= 0.8
        
        return size
```

**Action Items:**
1. Create `common/adaptive_risk.py`
2. Integrate regime detection into execution
3. Log regime changes
4. Backtest adaptive vs fixed risk

---

### 8.3 Self-Healing Mechanisms
**Problem:** System requires manual intervention after failures.

```python
# common/self_healing.py
import logging
from typing import Callable, Dict, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class HealingAction:
    """Self-healing action definition."""
    name: str
    condition: Callable[[], bool]
    action: Callable[[], None]
    cooldown_seconds: int = 300  # Don't repeat too often

class SelfHealingSystem:
    """Automatic remediation of known issues."""
    
    def __init__(self):
        self.actions: List[HealingAction] = []
        self.last_run: Dict[str, float] = {}
    
    def register_action(self, action: HealingAction):
        """Register a self-healing action."""
        self.actions.append(action)
    
    def check_and_heal(self):
        """Check conditions and apply healing actions."""
        import time
        now = time.time()
        
        for action in self.actions:
            # Check cooldown
            if action.name in self.last_run:
                elapsed = now - self.last_run[action.name]
                if elapsed < action.cooldown_seconds:
                    continue
            
            # Check condition
            try:
                if action.condition():
                    logger.info(f"Triggering healing action: {action.name}")
                    action.action()
                    self.last_run[action.name] = now
            
            except Exception as e:
                logger.error(f"Healing action {action.name} failed: {e}")


# Example healing actions
def setup_healing_actions() -> SelfHealingSystem:
    """Setup common healing actions."""
    healer = SelfHealingSystem()
    
    # Clear cache if disk space low
    def check_disk_space() -> bool:
        import shutil
        usage = shutil.disk_usage('/')
        free_gb = usage.free / (1024**3)
        return free_gb < 2.0
    
    def clear_old_cache():
        import os
        import time
        cache_dir = ".cache"
        now = time.time()
        for filename in os.listdir(cache_dir):
            filepath = os.path.join(cache_dir, filename)
            if os.path.getmtime(filepath) < now - 86400:  # Older than 1 day
                os.remove(filepath)
        logger.info("Cleared old cache files")
    
    healer.register_action(HealingAction(
        name="clear_old_cache",
        condition=check_disk_space,
        action=clear_old_cache
    ))
    
    # Restart connection if stale
    def check_connection_stale() -> bool:
        # TODO: Implement connection staleness check
        return False
    
    def restart_connection():
        # TODO: Implement connection restart
        logger.info("Restarted API connection")
    
    healer.register_action(HealingAction(
        name="restart_connection",
        condition=check_connection_stale,
        action=restart_connection,
        cooldown_seconds=60
    ))
    
    return healer
```

**Action Items:**
1. Create `common/self_healing.py`
2. Implement common healing actions
3. Run healing checks periodically
4. Log all healing actions

---

## 9. Documentation & Knowledge Base

### 9.1 Runbook for Common Issues
**Problem:** Same issues require re-investigation.

**Action Items:**
1. Create `docs/RUNBOOK.md` with common issues and solutions
2. Document every production issue and resolution
3. Update runbook after each incident
4. Make runbook searchable

### 9.2 Architecture Decision Records (ADRs)
**Problem:** Don't know why decisions were made.

```markdown
# ADR Template: docs/adr/0001-example.md

# ADR-0001: Use Inverse Volatility Weighting

## Status
Accepted

## Context
Need to determine portfolio allocation across multiple assets with varying risk profiles.

## Decision
Use inverse volatility weighting to allocate capital.

## Consequences
### Positive
- Automatically adjusts for risk
- Simple to implement
- Well-understood in finance

### Negative
- May underweight high-momentum assets
- Sensitive to volatility estimation period

## Alternatives Considered
- Equal weighting
- Market cap weighting
- Risk parity

## References
- Backtest results: `backtests/results/volatility_factor_*.csv`
- Original research: `docs/VOLATILITY_FACTOR_SPEC.md`
```

**Action Items:**
1. Create `docs/adr/` directory
2. Document all major decisions as ADRs
3. Reference ADRs in code comments
4. Review ADRs periodically

---

## 10. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
**Priority: Critical**

- [ ] Add type hints to core modules (signals/, execution/)
- [ ] Create custom exception hierarchy
- [ ] Setup structured logging
- [ ] Create input validators
- [ ] Add mypy configuration
- [ ] Setup pre-commit hooks
- [ ] Create requirements-dev.txt

### Phase 2: Testing & CI (Week 3-4)
**Priority: High**

- [ ] Expand unit tests to 50% coverage
- [ ] Add integration tests
- [ ] Setup GitHub Actions CI
- [ ] Add property-based tests
- [ ] Create test fixtures
- [ ] Add coverage reporting

### Phase 3: Robustness (Week 5-6)
**Priority: High**

- [ ] Add retry logic to API calls
- [ ] Implement circuit breakers
- [ ] Add rate limiting
- [ ] Implement caching layer
- [ ] Add health checks
- [ ] Create failure database

### Phase 4: Observability (Week 7-8)
**Priority: Medium**

- [ ] Enhance logging throughout
- [ ] Add metrics collection
- [ ] Create monitoring dashboard
- [ ] Setup alerting system
- [ ] Add performance profiling
- [ ] Create metrics export

### Phase 5: Antifragility (Week 9-10)
**Priority: Medium**

- [ ] Implement adaptive risk management
- [ ] Add self-healing mechanisms
- [ ] Create failure analysis tools
- [ ] Setup chaos testing
- [ ] Implement learning from failures
- [ ] Add anomaly detection

### Phase 6: Documentation (Week 11-12)
**Priority: Low**

- [ ] Create runbook
- [ ] Write ADRs for key decisions
- [ ] Create architecture diagrams
- [ ] Document all APIs
- [ ] Create troubleshooting guide
- [ ] Write contributor guide

---

## Success Metrics

### Robustness Metrics
- **Test Coverage**: Target 80%+
- **Type Coverage**: Target 100% for public APIs
- **Mean Time To Recovery (MTTR)**: < 5 minutes for common failures
- **Deployment Success Rate**: > 99%

### Antifragility Metrics
- **Failure Pattern Detection**: Identify recurring issues automatically
- **Auto-Remediation Rate**: 50%+ of failures handled automatically
- **Incident Learning Rate**: Document 100% of incidents
- **Adaptive Performance**: System performs better in diverse conditions

### Operational Metrics
- **Uptime**: > 99.9%
- **API Error Rate**: < 0.1%
- **Data Staleness**: < 1 hour
- **Alert Noise**: < 5 false positives per week

---

## Tools & Dependencies

### Add to requirements-dev.txt
```
# Code Quality
mypy>=1.8.0
black>=23.12.0
ruff>=0.1.9
isort>=5.13.0
bandit>=1.7.5

# Testing
pytest>=7.4.0
pytest-cov>=4.1.0
pytest-mock>=3.12.0
pytest-asyncio>=0.21.0
hypothesis>=6.92.0

# Documentation
sphinx>=7.2.0
sphinx-rtd-theme>=2.0.0

# Monitoring
prometheus-client>=0.19.0

# Pre-commit
pre-commit>=3.6.0
```

---

## Conclusion

This plan transforms the repository from functional to **robust** (resilient to failures) and **antifragile** (learning from and improving through failures).

**Key Principles:**
1. **Defense in Depth**: Multiple layers of protection
2. **Fail Fast**: Catch errors early
3. **Observable**: Can't fix what you can't see
4. **Adaptive**: Adjust to changing conditions
5. **Learn**: Every failure makes the system better

**Next Steps:**
1. Review this plan with team
2. Prioritize implementation phases
3. Start with Phase 1 (Foundation)
4. Iterate and improve based on learnings

Remember: **A robust system prevents failures. An antifragile system benefits from them.**
