#!/bin/bash
# Comprehensive DeFi Factor Pipeline
# Runs all data fetching and factor calculations

set -e  # Exit on error

echo "========================================================================"
echo "Comprehensive DeFi Factor Pipeline"
echo "========================================================================"
echo ""

# Step 1: DefiLlama data
echo "[1/4] Fetching DefiLlama data (fees, TVL, yields)..."
python3 data/scripts/fetch_defillama_data.py
echo ""

echo "[2/4] Mapping DefiLlama data to tradeable universe..."
python3 data/scripts/map_defillama_to_universe.py
echo ""

# Step 2: CoinGecko data
echo "[3/4] Fetching CoinGecko data (FDV, market cap, volume)..."
echo "Note: This takes ~2 minutes due to rate limiting..."
python3 data/scripts/fetch_coingecko_market_data.py
echo ""

# Step 3: Calculate factors
echo "[4/4] Calculating comprehensive factors and generating signals..."
python3 signals/calc_comprehensive_defi_factors.py
echo ""

echo "========================================================================"
echo "✅ Pipeline complete!"
echo "========================================================================"
echo ""
echo "Output files:"
echo "  - signals/defi_factor_combined_signals.csv (USE THIS FOR TRADING)"
echo "  - data/raw/comprehensive_defi_factors_$(date +%Y%m%d).csv"
echo ""
echo "View signals:"
echo "  cat signals/defi_factor_combined_signals.csv | column -t -s, | less -S"
