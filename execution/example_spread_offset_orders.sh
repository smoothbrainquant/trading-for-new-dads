#!/bin/bash
# Example usage of send_spread_offset_orders.py
# This script demonstrates various ways to use the spread offset execution method

echo "=========================================="
echo "Spread Offset Order Execution Examples"
echo "=========================================="
echo ""

# Example 1: Basic usage with default 1.0x spread multiplier
echo "Example 1: Basic usage (1.0x spread multiplier)"
echo "Buy \$100 BTC at bid - 1x spread, sell \$50 ETH at ask + 1x spread"
python3 send_spread_offset_orders.py \
  --trades "BTC/USDC:USDC:100" "ETH/USDC:USDC:-50"
echo ""
read -p "Press Enter to continue..."
echo ""

# Example 2: Conservative orders close to best prices (0.5x spread)
echo "Example 2: Conservative orders (0.5x spread multiplier)"
echo "Buy \$200 SOL closer to best bid"
python3 send_spread_offset_orders.py \
  --trades "SOL/USDC:USDC:200" \
  --spread-multiplier 0.5
echo ""
read -p "Press Enter to continue..."
echo ""

# Example 3: Aggressive passive orders (2.0x spread)
echo "Example 3: Aggressive passive orders (2.0x spread multiplier)"
echo "Multiple trades farther from best prices for better pricing"
python3 send_spread_offset_orders.py \
  --trades \
    "BTC/USDC:USDC:100" \
    "ETH/USDC:USDC:-50" \
    "SOL/USDC:USDC:75" \
    "ARB/USDC:USDC:-25" \
  --spread-multiplier 2.0
echo ""
read -p "Press Enter to continue..."
echo ""

# Example 4: Very conservative (0.25x spread)
echo "Example 4: Very conservative orders (0.25x spread multiplier)"
echo "Orders very close to best prices, higher probability of fill"
python3 send_spread_offset_orders.py \
  --trades "BTC/USDC:USDC:1000" \
  --spread-multiplier 0.25
echo ""
read -p "Press Enter to continue..."
echo ""

# Example 5: At best bid/ask (0.0x spread - equivalent to send_limit_orders.py)
echo "Example 5: Exactly at best bid/ask (0.0x spread multiplier)"
echo "Equivalent to send_limit_orders.py behavior"
python3 send_spread_offset_orders.py \
  --trades "ETH/USDC:USDC:-100" \
  --spread-multiplier 0.0
echo ""
read -p "Press Enter to continue..."
echo ""

echo "=========================================="
echo "All examples completed!"
echo ""
echo "To execute LIVE trades, add the --live flag:"
echo "  python3 send_spread_offset_orders.py --trades \"BTC/USDC:USDC:100\" --spread-multiplier 1.0 --live"
echo ""
echo "Make sure to set environment variables:"
echo "  export HL_API='your_wallet_address'"
echo "  export HL_SECRET='your_secret_key'"
echo "=========================================="
