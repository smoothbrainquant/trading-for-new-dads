# CoinMarketCap API Environment Variable Setup

This guide shows how to properly set and use the `CMC_API` environment variable for fetching historical cryptocurrency data.

## Quick Start

### 1. Get Your API Key
1. Sign up at https://coinmarketcap.com/api/
2. Choose a plan (historical data requires paid plan: Basic $29/mo or higher)
3. Copy your API key from the dashboard

### 2. Set the Environment Variable

#### Option A: Temporary (current session only)
```bash
export CMC_API="your-api-key-here"
```

#### Option B: Permanent (recommended)

**For Bash (~/.bashrc or ~/.bash_profile)**:
```bash
echo 'export CMC_API="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

**For Zsh (~/.zshrc)**:
```bash
echo 'export CMC_API="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

**For Fish (~/.config/fish/config.fish)**:
```bash
echo 'set -x CMC_API "your-api-key-here"' >> ~/.config/fish/config.fish
source ~/.config/fish/config.fish
```

### 3. Verify It's Set
```bash
# Check if set
echo $CMC_API

# Or check with Python
python3 -c "import os; print('CMC_API is set:', bool(os.environ.get('CMC_API')))"
```

### 4. Test API Access
```bash
# Run the test script
python3 test_cmc_api_env.py
```

## Usage Examples

### Method 1: Let Functions Auto-Detect CMC_API (Recommended)

```python
from fetch_coinmarketcap_data import fetch_historical_top100_quarterly

# No api_key parameter needed - will use CMC_API env var
df = fetch_historical_top100_quarterly(
    start_year=2020,
    limit=100
)
```

### Method 2: Command Line (Auto-Detects)

```bash
# Just set the env var and run
export CMC_API="your-api-key"
python3 fetch_coinmarketcap_data.py --historical --start-year 2020
```

### Method 3: Pass Explicitly (Override)

```python
from fetch_coinmarketcap_data import fetch_historical_top100_quarterly

# Explicitly pass API key (overrides CMC_API env var)
df = fetch_historical_top100_quarterly(
    api_key="different-api-key-here",
    start_year=2020
)
```

### Method 4: Read in Python Script

```python
import os

api_key = os.environ.get('CMC_API')
if not api_key:
    raise ValueError("CMC_API environment variable not set!")

# Use the key
from fetch_coinmarketcap_data import fetch_historical_top100_quarterly
df = fetch_historical_top100_quarterly(api_key=api_key)
```

## All Functions Support CMC_API

All CoinMarketCap functions automatically read from `CMC_API` when `api_key=None`:

| Function | Purpose | Requires Paid Plan |
|----------|---------|-------------------|
| `fetch_coinmarketcap_data()` | Current top coins | ❌ No (free tier OK) |
| `fetch_historical_top100_quarterly()` | Historical quarterly snapshots | ✅ Yes (Basic+ plan) |

## Security Best Practices

### ✅ DO:
- Store API key in environment variable (not in code)
- Add `.env` files to `.gitignore`
- Use separate API keys for dev/prod
- Rotate keys periodically

### ❌ DON'T:
- Commit API keys to git repositories
- Share API keys in public channels
- Hardcode keys in source files
- Use production keys for testing

## Using .env File (Optional)

For projects, you can use a `.env` file with python-dotenv:

### 1. Install python-dotenv
```bash
pip install python-dotenv
```

### 2. Create .env file
```bash
# .env
CMC_API=your-api-key-here
```

### 3. Load in Python
```python
from dotenv import load_dotenv
load_dotenv()  # Loads .env variables into environment

# Now CMC_API is available
from fetch_coinmarketcap_data import fetch_historical_top100_quarterly
df = fetch_historical_top100_quarterly()  # Uses CMC_API automatically
```

### 4. Add .env to .gitignore
```bash
echo ".env" >> .gitignore
```

## Troubleshooting

### Issue: "CMC_API environment variable not set"

**Check if set**:
```bash
echo $CMC_API
```

**If empty, set it**:
```bash
export CMC_API="your-api-key"
```

**If still not working after setting in ~/.bashrc**:
```bash
source ~/.bashrc  # Reload bash configuration
```

### Issue: "No data was successfully fetched"

**Possible causes**:
1. Invalid API key
2. Free tier plan (historical data requires paid plan)
3. Rate limit exceeded
4. Network issues

**Verify API key works**:
```bash
# Test with curl
curl -H "X-CMC_PRO_API_KEY: $CMC_API" \
  "https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest?limit=10"
```

### Issue: API key visible in process list

If you pass API key via command line `--api-key`, it may be visible in `ps` output.
Use environment variable instead for better security.

## Example: Full Workflow

```bash
# 1. Set API key (one-time setup)
export CMC_API="your-api-key-from-coinmarketcap"

# 2. Test it works
python3 test_cmc_api_env.py

# 3. Fetch historical data
python3 fetch_coinmarketcap_data.py \
    --historical \
    --start-year 2020 \
    --limit 100 \
    --output historical_top100_2020.csv

# 4. Or use the example script
python3 example_historical_fetch.py

# 5. Use in your own scripts
python3 -c "
from fetch_coinmarketcap_data import fetch_historical_top100_quarterly
df = fetch_historical_top100_quarterly(start_year=2020, limit=100)
print(f'Fetched {len(df)} records')
"
```

## CI/CD Integration

For GitHub Actions, GitLab CI, etc.:

**GitHub Actions**:
```yaml
env:
  CMC_API: ${{ secrets.CMC_API }}

steps:
  - name: Fetch historical data
    run: python3 fetch_coinmarketcap_data.py --historical
```

**GitLab CI**:
```yaml
variables:
  CMC_API: $CMC_API_SECRET

script:
  - python3 fetch_coinmarketcap_data.py --historical
```

Set secrets in your CI/CD platform settings.

## Summary

✅ **Best Practice**: Always use `CMC_API` environment variable
- More secure than hardcoding
- Works automatically with all functions
- Easy to change without code modifications
- Follows 12-factor app principles

```bash
# Set once
export CMC_API="your-api-key"

# Use everywhere
python3 fetch_coinmarketcap_data.py --historical
python3 example_historical_fetch.py
# etc.
```

That's it! The code automatically handles the rest.
