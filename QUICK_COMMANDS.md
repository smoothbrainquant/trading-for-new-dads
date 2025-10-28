# Quick Commands Reference

Copy-paste these commands to get started immediately.

---

## 🚀 Getting Started (5 minutes)

```bash
# 1. Install development tools
cd /workspace
pip3 install -r requirements-dev.txt

# 2. Setup pre-commit hooks
pre-commit install

# 3. Run initial formatting (will modify files)
black .

# 4. Check what needs fixing
ruff check .

# 5. Run existing tests
python3 run_tests.py

# 6. Commit the foundation
git add common/ tests/test_validators.py requirements-dev.txt .pre-commit-config.yaml pyproject.toml
git add ROBUSTNESS*.md QUICK_START_ROBUSTNESS.md IMPLEMENTATION_GUIDE.md QUICK_COMMANDS.md
git commit -m "Add robustness foundation: validators, exceptions, retry, dev tools"
```

---

## 📝 Daily Commands

### Format & Lint
```bash
# Format code
black .

# Fix linting issues
ruff check . --fix

# Sort imports
isort .

# Check types (after adding type hints)
mypy signals/ --ignore-missing-imports
```

### Testing
```bash
# Run all tests
python3 run_tests.py

# Run specific test file
python3 run_tests.py tests/test_validators.py

# Run with coverage
python3 -m pytest tests/ --cov=signals --cov=backtests --cov=execution --cov=common --cov-report=term-missing

# Run with coverage HTML report
python3 -m pytest tests/ --cov=signals --cov=backtests --cov=execution --cov=common --cov-report=html
# Then open htmlcov/index.html
```

### Pre-commit
```bash
# Run all pre-commit hooks manually
pre-commit run --all-files

# Run on specific files
pre-commit run --files signals/calc_weights.py

# Update hook versions
pre-commit autoupdate
```

---

## 🔧 Adding Validation (Copy-Paste Templates)

### Template 1: Add to Backtest Script

```python
# Add to imports at top
import sys
import os
workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from common.validators import DataValidator
from common.exceptions import DataValidationError
import logging

logger = logging.getLogger(__name__)

# Add after loading data (df = pd.read_csv(...))
try:
    DataValidator.validate_ohlcv_dataframe(df)
    logger.info(f"✓ Data validation passed: {len(df)} rows")
except DataValidationError as e:
    logger.error(f"✗ Data validation failed: {e}")
    sys.exit(1)
```

### Template 2: Add to Signal Generation

```python
# Add to imports
from common.validators import SignalValidator
from common.exceptions import SignalValidationError
import logging

logger = logging.getLogger(__name__)

# Add before returning signals
try:
    SignalValidator.validate_signals({'longs': longs, 'shorts': shorts})
    logger.debug("✓ Signals validated")
except SignalValidationError as e:
    logger.error(f"✗ Signal validation failed: {e}")
    return {'longs': [], 'shorts': []}

# Add before returning weights
try:
    SignalValidator.validate_weights(weights)
    logger.debug(f"✓ Weights validated: {len(weights)} assets")
except SignalValidationError as e:
    logger.error(f"✗ Weight validation failed: {e}")
    return {}
```

### Template 3: Add to Execution Script

```python
# Add to imports
from common.validators import RiskValidator
from common.exceptions import RiskLimitError
import logging

logger = logging.getLogger(__name__)

# Add before placing orders
try:
    # Check total exposure
    total_exposure = sum(abs(notional) for notional in positions.values())
    RiskValidator.validate_total_exposure(
        total_exposure=total_exposure,
        max_exposure=100000  # Your max
    )
    
    # Check each position
    for symbol, notional in positions.items():
        RiskValidator.validate_position_size(
            notional=abs(notional),
            max_notional=10000,  # Your max per asset
            symbol=symbol
        )
    
    logger.info(f"✓ Risk checks passed: {len(positions)} positions, ${total_exposure:,.2f} total")

except RiskLimitError as e:
    logger.error(f"✗ Risk limit exceeded: {e}")
    # Handle: reduce positions, abort, etc.
```

### Template 4: Add Retry to API Function

```python
# Add to imports
from common.retry import retry
from common.exceptions import APIError
import requests

# Add decorator to API function
@retry(max_attempts=3, delay=2.0, backoff=2.0, exceptions=(APIError, requests.RequestException))
def fetch_api_data(symbol: str):
    """Fetch data with automatic retry."""
    try:
        response = api.get_data(symbol)
        if response is None:
            raise APIError(f"No data for {symbol}")
        return response
    except requests.Timeout as e:
        raise APIError(f"Timeout: {e}") from e
    except requests.RequestException as e:
        raise APIError(f"Request failed: {e}") from e
```

---

## 📊 Testing Your Changes

### After Adding Validation
```bash
# Test the script still runs
python3 backtests/scripts/backtest_mean_reversion.py

# Test with intentionally bad data to see validation work
python3 -c "
import pandas as pd
from common.validators import DataValidator
from common.exceptions import DataValidationError

# Create invalid data (high < low)
df = pd.DataFrame({
    'date': pd.date_range('2024-01-01', periods=5),
    'symbol': ['BTC'] * 5,
    'open': [100, 101, 102, 103, 104],
    'high': [90, 91, 92, 93, 94],  # Invalid!
    'low': [95, 96, 97, 98, 99],
    'close': [100, 101, 102, 103, 104],
    'volume': [1000] * 5
})

try:
    DataValidator.validate_ohlcv_dataframe(df)
except DataValidationError as e:
    print(f'✓ Validation caught error: {e}')
"
```

### After Adding Logging
```bash
# Run and check log file created
python3 backtests/scripts/backtest_mean_reversion.py
ls -lh logs/

# View the log
tail -f logs/backtest_*.log
```

### After Adding Tests
```bash
# Run new tests
python3 run_tests.py tests/test_your_new_file.py

# Check coverage increased
python3 -m pytest tests/ --cov=signals --cov-report=term-missing | grep "TOTAL"
```

---

## 🐛 Debugging Common Issues

### Issue: Import Error
```bash
# Problem: ModuleNotFoundError: No module named 'common'

# Solution 1: Add to Python path in script
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Solution 2: Install package in development mode
pip3 install -e .

# Solution 3: Run from workspace root
cd /workspace
python3 backtests/scripts/backtest_mean_reversion.py
```

### Issue: Pre-commit Hook Fails
```bash
# Problem: Pre-commit hook failing on commit

# Solution: Run manually to see details
pre-commit run --all-files

# Fix the issues, then commit
git add -A
git commit -m "Fix pre-commit issues"
```

### Issue: Tests Fail After Changes
```bash
# Problem: Tests failing after adding validation

# Solution: Check what changed
git diff

# Run tests with verbose output
python3 -m pytest tests/test_signals.py -v

# If validation is too strict, adjust parameters
DataValidator.validate_date_range(df, max_age_hours=8760)  # 1 year for backtests
```

---

## 📈 Checking Progress

### Coverage Report
```bash
# Generate HTML coverage report
python3 -m pytest tests/ \
  --cov=signals \
  --cov=backtests \
  --cov=execution \
  --cov=common \
  --cov-report=html

# Open in browser
open htmlcov/index.html  # Mac
xdg-open htmlcov/index.html  # Linux
```

### Code Quality Metrics
```bash
# Check formatting
black --check .

# Check linting
ruff check . | wc -l  # Count of issues

# Check type coverage
mypy signals/ --ignore-missing-imports 2>&1 | grep "Found"
```

### Test Metrics
```bash
# Count test files
ls tests/test_*.py | wc -l

# Count test functions
grep -r "def test_" tests/ | wc -l

# Run tests with summary
python3 run_tests.py 2>&1 | tail -20
```

---

## 🎯 Your First Day - Step by Step

```bash
# === STEP 1: Setup (5 min) ===
cd /workspace
pip3 install -r requirements-dev.txt
pre-commit install
black .

# === STEP 2: Pick one file to enhance (30 min) ===
# Let's start with: backtests/scripts/backtest_mean_reversion.py

# Open the file and add:
# 1. Import validators (use Template 1 above)
# 2. Add validation after data loading
# 3. Test it

python3 backtests/scripts/backtest_mean_reversion.py

# === STEP 3: Commit (2 min) ===
git add backtests/scripts/backtest_mean_reversion.py
git commit -m "Add data validation to mean_reversion backtest"

# === STEP 4: Do it again (30 min) ===
# Pick another file: backtests/scripts/backtest_breakout_signals.py
# Repeat steps above

# === STEP 5: Add to execution (1 hour) ===
# Open: execution/main.py
# Add: Risk validation (use Template 3 above)
# Test in dry-run mode

python3 execution/main.py --dry-run

# Commit
git add execution/main.py
git commit -m "Add risk validation to execution"

# === STEP 6: Celebrate! ===
echo "✅ Day 1 complete! You've made the system more robust!"
```

---

## 📚 Quick Reference Links

- **Full Plan**: `ROBUSTNESS_ENHANCEMENT_PLAN.md`
- **Quick Start**: `QUICK_START_ROBUSTNESS.md`
- **Implementation Guide**: `IMPLEMENTATION_GUIDE.md`
- **This File**: `QUICK_COMMANDS.md`

---

## 💡 Pro Tips

### Tip 1: Commit Often
```bash
# After each working change
git add -A
git commit -m "Add validation to X"
```

### Tip 2: Test in Dry-Run Mode
```bash
# Always test execution changes in dry-run
python3 execution/main.py --dry-run
```

### Tip 3: Keep a Log of Changes
```bash
# Create a changelog
echo "$(date): Added validation to backtest_mean_reversion.py" >> CHANGES.log
```

### Tip 4: Use Aliases
```bash
# Add to ~/.bashrc or ~/.zshrc
alias fmt='black . && ruff check . --fix && isort .'
alias test='python3 run_tests.py'
alias cov='python3 -m pytest tests/ --cov=signals --cov=backtests --cov=execution --cov=common --cov-report=html'

# Then just run:
fmt
test
cov
```

### Tip 5: Run Pre-commit Before Push
```bash
# Before pushing
pre-commit run --all-files
python3 run_tests.py
git push
```

---

## 🎉 You're Ready!

Everything you need is now in place. Start with:

```bash
pip3 install -r requirements-dev.txt && pre-commit install && black .
```

Then pick ONE file and enhance it. Repeat. You've got this! 💪
