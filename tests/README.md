# Trading System Tests

This directory contains comprehensive tests for the trading system components.

## Test Coverage

### 1. Data Collection Tests (`test_data_collection.py`)
- **CCXT Tests**: Tests for fetching OHLCV data from Hyperliquid via CCXT
- **Coinalyze Tests**: Tests for Coinalyze API client (funding rates, open interest, etc.)
- **CoinMarketCap Tests**: Tests for market cap data fetching (with mock fallback)

### 2. Signal Calculation Tests (`test_signals.py`)
- **Breakout Signals**: Tests for 50d/70d breakout signal calculation
- **Volatility Calculation**: Tests for rolling 30-day volatility calculation
- **Weight Calculation**: Tests for risk parity portfolio weight calculation

### 3. Backtest Tests (`test_backtests.py`)
- **Data Loading**: Tests for CSV data loading
- **Z-Score Calculation**: Tests for return and volume z-score calculation
- **Categorization**: Tests for move categorization (high/low return/volume)
- **Mean Reversion Analysis**: Tests for mean reversion pattern analysis

### 4. Execution Tests (`test_execution.py`)
- **Balance Checking**: Tests for fetching account balances
- **Position Checking**: Tests for fetching open positions
- **Instrument Selection**: Tests for selecting instruments near 200-day highs

## Running Tests

### Run All Tests
```bash
python3 run_tests.py
```

### Run Specific Test File
```bash
python3 run_tests.py tests/test_signals.py
```

### Run Specific Test Class
```bash
python3 run_tests.py tests/test_signals.py::TestBreakoutSignals
```

### Run Specific Test Method
```bash
python3 run_tests.py tests/test_signals.py::TestBreakoutSignals::test_calculate_breakout_signals_returns_dataframe
```

### List All Tests
```bash
python3 run_tests.py --list
```

### Using pytest directly
```bash
# Run all tests with verbose output
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=data --cov=signals --cov=backtests --cov=execution --cov-report=html

# Run specific test
pytest tests/test_signals.py::TestBreakoutSignals -v
```

## Test Requirements

Install test dependencies:
```bash
pip install -r requirements.txt
```

Required packages:
- `pytest>=7.4.0` - Testing framework
- `pytest-cov>=4.1.0` - Coverage reporting

## Test Design

### Mocking Strategy
- External API calls (CCXT, Coinalyze, CoinMarketCap) are mocked to avoid requiring credentials
- Real API credentials can be tested by setting environment variables
- Tests are designed to work without external dependencies

### Test Data
- Tests use synthetic data generated in `setUp()` methods
- Data is designed to test specific edge cases and expected behaviors
- No external data files are required for tests to run

### Coverage
Tests cover:
- ✓ Happy path scenarios
- ✓ Error handling and edge cases
- ✓ Data validation
- ✓ Input/output formats
- ✓ Missing or invalid data handling

## Environment Variables for Real API Testing

If you want to test with real APIs, set these environment variables:

```bash
# For CCXT/Hyperliquid tests
export HL_API='your_api_key'
export HL_SECRET='your_secret_key'

# For Coinalyze tests
export COINALYZE_API='your_api_key'

# For CoinMarketCap tests
export CMC_API='your_api_key'
```

**Note**: Tests will use mock data if these are not set, so they can run without credentials.

## Continuous Integration

These tests are designed to run in CI/CD environments without external API access:
- All external APIs are mocked by default
- Tests create temporary files in `/tmp/` and clean up after themselves
- No persistent state is maintained between test runs

## Adding New Tests

When adding new functionality, follow these patterns:

1. **Create test file**: `tests/test_<module>.py`
2. **Import unittest**: Use Python's unittest framework
3. **Mock external calls**: Use `unittest.mock.patch` for API calls
4. **Create test data**: Generate synthetic data in `setUp()` methods
5. **Test edge cases**: Include tests for error conditions
6. **Document tests**: Add docstrings explaining what each test validates

Example:
```python
import unittest
from unittest.mock import patch, MagicMock

class TestNewFeature(unittest.TestCase):
    def setUp(self):
        """Create test data"""
        self.test_data = ...
    
    def test_feature_returns_expected_type(self):
        """Test that feature returns correct type"""
        result = my_feature(self.test_data)
        self.assertIsInstance(result, ExpectedType)
    
    @patch('external_api.call')
    def test_feature_with_mocked_api(self, mock_api):
        """Test feature with mocked external API"""
        mock_api.return_value = mock_response
        result = my_feature()
        self.assertEqual(result, expected_value)
```

## Test Status

| Component | Test File | Status | Coverage |
|-----------|-----------|--------|----------|
| Data Collection | `test_data_collection.py` | ✓ Complete | High |
| Signals | `test_signals.py` | ✓ Complete | High |
| Backtests | `test_backtests.py` | ✓ Complete | High |
| Execution | `test_execution.py` | ✓ Complete | High |

## Troubleshooting

### Tests fail with "Module not found"
```bash
# Ensure requirements are installed
pip install -r requirements.txt

# Run from project root directory
cd /workspace
python3 run_tests.py
```

### Tests fail with API errors
- Tests are designed to work without API credentials
- Check that mocks are properly configured
- If testing with real APIs, verify environment variables are set

### Coverage report not generated
```bash
# Install coverage tools
pip install pytest-cov

# Run with coverage
pytest tests/ --cov=data --cov=signals --cov=backtests --cov=execution --cov-report=html
```
