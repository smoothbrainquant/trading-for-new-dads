#!/bin/bash
#
# Demo script for Kurtosis Strategy with Regime Filter
#
# This script demonstrates the regime-filtered kurtosis strategy in dry-run mode.
# It will show:
# 1. Current market regime (bull or bear based on BTC 50MA vs 200MA)
# 2. Whether the kurtosis strategy activates or remains inactive
# 3. Positions generated (if active) or confirmation of no positions (if inactive)
#

echo "================================================================================"
echo "KURTOSIS REGIME FILTER DEMO"
echo "================================================================================"
echo ""
echo "This demo runs the kurtosis mean reversion strategy with regime filtering."
echo "The strategy will ONLY activate if we're in a BEAR MARKET (50MA < 200MA on BTC)."
echo ""
echo "Expected behavior:"
echo "  - BULL MARKET: Strategy inactive, 0 positions, capital stays in other strategies"
echo "  - BEAR MARKET: Strategy active, generates long/short positions"
echo ""
echo "Press Ctrl+C to cancel, or press Enter to continue..."
read

echo ""
echo "================================================================================"
echo "Running main.py with kurtosis strategy (dry-run mode)..."
echo "================================================================================"
echo ""

cd /workspace

# Run with just kurtosis strategy to clearly see the regime filter in action
python3 execution/main.py \
    --signals kurtosis \
    --dry-run \
    --threshold 0.03

echo ""
echo "================================================================================"
echo "DEMO COMPLETE"
echo "================================================================================"
echo ""
echo "Review the output above to see:"
echo "  1. Market Regime Detection section (BULL or BEAR)"
echo "  2. Kurtosis strategy status (ACTIVE or INACTIVE)"
echo "  3. Positions generated (if active) or 'No positions' (if inactive)"
echo ""
echo "To run live (when ready):"
echo "  python3 execution/main.py --signals kurtosis"
echo ""
echo "To run with multiple strategies:"
echo "  python3 execution/main.py --dry-run  # Uses config file weights"
echo ""
