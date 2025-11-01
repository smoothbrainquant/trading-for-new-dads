#!/bin/bash
#
# Example script to run Hurst exponent factor backtests
#
# This script demonstrates how to run different variants of the Hurst exponent strategy
#

echo "Running Hurst Exponent Factor Backtests..."
echo "==========================================="
echo ""

# Navigate to workspace root
cd /workspace

# 1. Long Mean-Reverting, Short Trending (Primary Strategy)
echo "1. Running Long Mean-Reverting Strategy..."
python3 backtests/scripts/backtest_hurst_exponent_factor.py \
  --strategy long_mean_reverting \
  --hurst-window 90 \
  --rebalance-days 7 \
  --weighting-method equal_weight \
  --start-date 2020-01-01 \
  --output-prefix backtests/results/hurst_mean_reverting

echo ""
echo "2. Running Long Mean-Reverting with Risk Parity..."
python3 backtests/scripts/backtest_hurst_exponent_factor.py \
  --strategy long_mean_reverting \
  --hurst-window 90 \
  --rebalance-days 7 \
  --weighting-method risk_parity \
  --start-date 2020-01-01 \
  --output-prefix backtests/results/hurst_mean_reverting_risk_parity

echo ""
echo "3. Running Long Trending Strategy..."
python3 backtests/scripts/backtest_hurst_exponent_factor.py \
  --strategy long_trending \
  --hurst-window 90 \
  --rebalance-days 7 \
  --weighting-method equal_weight \
  --start-date 2020-01-01 \
  --output-prefix backtests/results/hurst_trending

echo ""
echo "4. Running Long Low Hurst Only (Defensive)..."
python3 backtests/scripts/backtest_hurst_exponent_factor.py \
  --strategy long_low_hurst \
  --hurst-window 90 \
  --rebalance-days 7 \
  --weighting-method equal_weight \
  --start-date 2020-01-01 \
  --output-prefix backtests/results/hurst_low_only

echo ""
echo "5. Running Long High Hurst Only (Momentum)..."
python3 backtests/scripts/backtest_hurst_exponent_factor.py \
  --strategy long_high_hurst \
  --hurst-window 90 \
  --rebalance-days 7 \
  --weighting-method equal_weight \
  --start-date 2020-01-01 \
  --output-prefix backtests/results/hurst_high_only

echo ""
echo "==========================================="
echo "All backtests complete!"
echo "Results saved to: backtests/results/"
echo ""
echo "Compare results:"
echo "  - hurst_mean_reverting_*      : Long mean-reverting, short trending"
echo "  - hurst_trending_*            : Long trending, short mean-reverting"
echo "  - hurst_low_only_*            : Long low Hurst only"
echo "  - hurst_high_only_*           : Long high Hurst only"
