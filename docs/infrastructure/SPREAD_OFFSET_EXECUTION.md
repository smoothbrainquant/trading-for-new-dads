# Spread Offset Limit Order Execution

## Overview

The `send_spread_offset_orders.py` execution method places limit orders at a configurable offset from the best bid/ask based on the market spread. This allows traders to place more passive orders that are less likely to be filled immediately but offer better pricing.

## How It Works

### Order Placement Logic

- **Buy orders (positive amount)**: `price = bid - (spread ? spread_multiplier)`
- **Sell orders (negative amount)**: `price = ask + (spread ? spread_multiplier)`
- All prices are automatically rounded to the nearest valid tick size for each market

### Spread Multiplier Parameter

The `spread_multiplier` parameter controls how far from the best bid/ask to place orders:

| Multiplier | Description | Example (spread = $1) |
|------------|-------------|------------------------|
| `0.0` | Exactly at best bid/ask | Order at bid/ask |
| `0.5` | Half spread away | $0.50 away from best |
| `1.0` | One spread away (default) | $1.00 away from best |
| `2.0` | Two spreads away | $2.00 away from best |

## Usage Examples

### Basic Usage (Dry Run)

```bash
# Buy $100 BTC at bid - 1x spread, sell $50 ETH at ask + 1x spread
python3 send_spread_offset_orders.py \
  --trades "BTC/USDC:USDC:100" "ETH/USDC:USDC:-50"
```

### Custom Spread Multiplier

```bash
# Buy $200 SOL at bid - 0.5x spread (closer to best bid)
python3 send_spread_offset_orders.py \
  --trades "SOL/USDC:USDC:200" \
  --spread-multiplier 0.5

# Multiple trades with 2x spread offset (farther from best prices)
python3 send_spread_offset_orders.py \
  --trades \
    "BTC/USDC:USDC:100" \
    "ETH/USDC:USDC:-50" \
    "SOL/USDC:USDC:75" \
    "ARB/USDC:USDC:-25" \
  --spread-multiplier 2.0
```

### Live Trading

```bash
# Execute live orders with 0.25x spread offset
python3 send_spread_offset_orders.py \
  --trades "BTC/USDC:USDC:1000" \
  --spread-multiplier 0.25 \
  --live
```

## Trade Format

Trades are specified in the format `SYMBOL:AMOUNT`:

- **Positive amount** = BUY at `bid - (spread ? multiplier)`
- **Negative amount** = SELL at `ask + (spread ? multiplier)`

Examples:
- `"BTC/USDC:USDC:100"` ? Buy $100 worth of BTC
- `"ETH/USDC:USDC:-50"` ? Sell $50 worth of ETH

## Key Features

### Automatic Tick Size Rounding

The script automatically rounds all prices to the nearest valid tick size for each market using the exchange's market precision information. This ensures that all orders are valid and comply with exchange requirements.

### Price Validation

The script validates that calculated prices are positive. If a spread multiplier is too large and would result in a negative or zero price, the script will skip that order and display an error.

### Detailed Output

For each order, the script displays:
- Current bid/ask prices
- Spread (absolute and percentage)
- Spread offset applied
- Raw calculated price
- Final price (after tick size rounding)
- Order quantity

## Comparison with Other Execution Methods

| Method | Order Price | Use Case |
|--------|-------------|----------|
| `send_limit_orders.py` | At best bid/ask | Quick fills, cross spread |
| `send_spread_offset_orders.py` | Offset from bid/ask | Passive orders, better pricing |
| `aggressive_order_execution.py` | Price ladder with monitoring | Aggressive fills over time |

## Environment Variables

For live trading, set the following environment variables:

```bash
export HL_API='your_hyperliquid_wallet_address'
export HL_SECRET='your_hyperliquid_secret_key'
```

## Command-Line Arguments

- `--trades TRADES [TRADES ...]` - List of trades in format SYMBOL:AMOUNT (required)
- `--spread-multiplier SPREAD_MULTIPLIER, -m` - Multiplier for spread offset (default: 1.0)
- `--live` - Execute live orders (default is dry-run mode)
- `--verbose, -v` - Show verbose output including full order details

## Example Output

```
================================================================================
LIMIT ORDER SUBMISSION WITH SPREAD OFFSET
================================================================================
Mode: DRY RUN
Spread multiplier: 1.0x
Total trades: 1
================================================================================

BTC/USDC:USDC:
  Side:           BUY
  Notional:       $100.00
  Bid:            $110,110.0000
  Ask:            $110,111.0000
  Spread:         $1.0000 (0.0009%)
  Spread Offset:  $1.0000 (1.0x)
  Raw Price:      $110109.00000000
  Order Price:    $110109.00000000 (BID - 1.0x spread, rounded to tick)
  Order Quantity: 0.000908
  Status:         [DRY RUN] Would place BUY limit order at $110109.0000
```

## Best Practices

1. **Start with dry runs** - Always test with dry runs before executing live orders
2. **Choose appropriate multipliers** - Use lower multipliers (0.25-0.5x) for competitive markets, higher (1.5-2.0x) for better prices
3. **Monitor fills** - Orders farther from best prices may take longer to fill or may not fill at all
4. **Adjust based on spread** - Wide spread markets may benefit from lower multipliers
5. **Consider market conditions** - In volatile markets, orders may be quickly left behind

## Technical Details

### Price Calculation

The price calculation follows this logic:

```python
spread = ask - bid
spread_offset = spread * spread_multiplier

if buying:
    raw_price = bid - spread_offset
else:  # selling
    raw_price = ask + spread_offset

# Round to nearest tick size
final_price = round_to_tick_size(raw_price)
```

### Tick Size Rounding

The script uses CCXT's `price_to_precision()` method to round prices according to each market's tick size requirements. This ensures all orders are valid and comply with exchange rules.

## Error Handling

The script handles several error cases:

- **Negative prices** - If the calculated price is negative or zero, the order is skipped with an error message
- **Missing price data** - If bid/ask data cannot be fetched, the order is skipped
- **Invalid credentials** - Live trading requires valid API credentials

## See Also

- [send_limit_orders.py](../../execution/send_limit_orders.py) - Basic limit order placement at bid/ask
- [aggressive_order_execution.py](../../execution/aggressive_order_execution.py) - Aggressive execution with price ladder
- [get_bid_ask.py](../../execution/get_bid_ask.py) - Fetch current bid/ask prices
