#!/usr/bin/env python3
"""
Analyze Breakout Strategy by Market Cap and Funding Buckets

- Computes breakout signals (configurable entry/exit windows)
- Computes next-day forward returns per symbol (to avoid lookahead bias)
- Applies position sign (LONG=+1, SHORT=-1) to forward returns
- Bins cross-section daily by market cap and funding rate into quantiles
- Aggregates performance by buckets and saves CSV summaries

Inputs:
  --price-file: combined price + market cap CSV (e.g., data/raw/combined_coinbase_coinmarketcap_daily.csv)
  --funding-file: historical funding rates CSV (e.g., data/raw/historical_funding_rates_top100_20251025_124832.csv)

Outputs:
  backtests/results/breakout_<entry>_<exit>_<lev>x_cluster_by_marketcap.csv
  backtests/results/breakout_<entry>_<exit>_<lev>x_cluster_by_funding.csv
  backtests/results/breakout_<entry>_<exit>_<lev>x_cluster_2d.csv
"""
import argparse
import os
from typing import Optional

import numpy as np
import pandas as pd

# Local imports: allow running from repo root or script directory
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "signals"))

from calc_breakout_signals import calculate_breakout_signals_param  # type: ignore


def normalize_base_symbol(symbol: str) -> str:
    """Extract base coin symbol from trading pair like 'BTC/USD' or 'BTC/USDC:USDC'."""
    if not isinstance(symbol, str):
        return symbol
    base = symbol.split("/")[0]
    return base.upper()


def compute_signed_forward_returns(price_df: pd.DataFrame,
                                   entry_window: int,
                                   exit_window: int) -> pd.DataFrame:
    """Compute signed next-day returns based on breakout position state."""
    # Compute signals with configurable windows
    signals = calculate_breakout_signals_param(price_df, entry_window=entry_window, exit_window=exit_window)

    # Merge position state back to price rows
    merged = price_df.merge(
        signals[['date', 'symbol', 'position']],
        on=['date', 'symbol'], how='left'
    )

    # Compute forward 1d log return per symbol
    merged = merged.sort_values(['symbol', 'date']).reset_index(drop=True)
    merged['forward_log_return'] = merged.groupby('symbol')['close'].transform(lambda x: np.log(x.shift(-1) / x))

    # Map position to sign
    pos_to_sign = {'LONG': 1.0, 'SHORT': -1.0}
    merged['position_sign'] = merged['position'].map(pos_to_sign).fillna(0.0)
    merged['signed_forward_log_return'] = merged['position_sign'] * merged['forward_log_return']

    return merged


def assign_daily_quantile_buckets(series: pd.Series, q: int) -> pd.Series:
    """Assign cross-sectional quantile buckets per date; expects series indexed by row with 'date' available in parent df.
    This function is meant to be used via groupby(['date']).apply within a DataFrame.
    """
    try:
        return pd.qcut(series, q=q, labels=[str(i) for i in range(1, q + 1)])
    except Exception:
        # If not enough unique values, fall back to NaN buckets
        return pd.Series([np.nan] * len(series), index=series.index)


def main():
    parser = argparse.ArgumentParser(description='Cluster breakout results by market cap and funding buckets')
    parser.add_argument('--price-file', type=str, default='data/raw/combined_coinbase_coinmarketcap_daily.csv')
    parser.add_argument('--funding-file', type=str, default='data/raw/historical_funding_rates_top100_20251025_124832.csv')
    parser.add_argument('--entry-window', type=int, default=50)
    parser.add_argument('--exit-window', type=int, default=10)
    parser.add_argument('--leverage', type=float, default=1.5)
    parser.add_argument('--start-date', type=str, default=None)
    parser.add_argument('--end-date', type=str, default=None)
    parser.add_argument('--marketcap-quantiles', type=int, default=5)
    parser.add_argument('--funding-quantiles', type=int, default=5)
    parser.add_argument('--output-dir', type=str, default='backtests/results')
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    # Load combined price + market cap data
    price_df = pd.read_csv(args.price_file)
    price_df['date'] = pd.to_datetime(price_df['date'])
    price_df = price_df.sort_values(['symbol', 'date']).reset_index(drop=True)

    # Optional date filter
    if args.start_date:
        price_df = price_df[price_df['date'] >= pd.to_datetime(args.start_date)]
    if args.end_date:
        price_df = price_df[price_df['date'] <= pd.to_datetime(args.end_date)]

    # Ensure base symbol and numeric market cap
    if 'base' not in price_df.columns:
        price_df['base'] = price_df['symbol'].apply(normalize_base_symbol)
    price_df['market_cap'] = pd.to_numeric(price_df.get('market_cap', np.nan), errors='coerce')

    # Compute signed forward returns using breakout positions
    print("Computing breakout signals and signed forward returns...")
    merged = compute_signed_forward_returns(price_df, args.entry_window, args.exit_window)

    # Load funding data and align by date + base symbol
    print("Loading funding rates and merging...")
    funding_df = pd.read_csv(args.funding_file)
    # Normalize
    if 'date' in funding_df.columns:
        funding_df['date'] = pd.to_datetime(funding_df['date'])
    # Prefer 'coin_symbol' if present, else try to extract from 'symbol'
    if 'coin_symbol' in funding_df.columns:
        funding_df['base'] = funding_df['coin_symbol'].astype(str).str.upper()
    elif 'symbol' in funding_df.columns:
        # e.g., BTCUSD_PERP.A -> BTC
        funding_df['base'] = funding_df['symbol'].astype(str).str.extract(r'^([A-Z]+)')[0]
    else:
        funding_df['base'] = np.nan

    # Funding rate percentage column
    if 'funding_rate_pct' not in funding_df.columns and 'funding_rate' in funding_df.columns:
        # Convert to percentage
        funding_df['funding_rate_pct'] = funding_df['funding_rate'] * 100.0

    funding_cols = ['date', 'base', 'funding_rate_pct']
    funding_df = funding_df[funding_cols].dropna(subset=['date', 'base']).copy()

    # Merge funding onto merged frame
    merged = merged.merge(funding_df, on=['date', 'base'], how='left')

    # Assign cross-sectional buckets per date
    print("Assigning daily market cap and funding quantile buckets...")
    merged['marketcap_bucket'] = (merged
                                  .groupby('date', group_keys=False)['market_cap']
                                  .apply(lambda s: assign_daily_quantile_buckets(s, args.marketcap_quantiles)))

    merged['funding_bucket'] = (merged
                                .groupby('date', group_keys=False)['funding_rate_pct']
                                .apply(lambda s: assign_daily_quantile_buckets(s, args.funding_quantiles)))

    # Keep only rows with an active position and valid forward return
    active = merged[(merged['position_sign'] != 0) & merged['signed_forward_log_return'].notna()].copy()

    # Helper to compute summary stats
    def summarize(group: pd.DataFrame) -> pd.Series:
        r = group['signed_forward_log_return']
        mean = r.mean()
        vol = r.std()
        sharpe = (mean / vol) if vol and vol > 0 else 0.0
        count = len(r)
        return pd.Series({
            'mean_daily_log_return': mean,
            'stdev_daily_log_return': vol,
            'daily_sharpe': sharpe,
            'n': count,
        })

    # By market cap bucket
    mc_summary = (active.dropna(subset=['marketcap_bucket'])
                        .groupby('marketcap_bucket')
                        .apply(summarize)
                        .reset_index()
                        .sort_values('marketcap_bucket'))

    # By funding bucket
    fr_summary = (active.dropna(subset=['funding_bucket'])
                        .groupby('funding_bucket')
                        .apply(summarize)
                        .reset_index()
                        .sort_values('funding_bucket'))

    # 2D cluster
    cluster_2d = (active.dropna(subset=['marketcap_bucket', 'funding_bucket'])
                        .groupby(['marketcap_bucket', 'funding_bucket'])
                        .apply(summarize)
                        .reset_index()
                        .sort_values(['marketcap_bucket', 'funding_bucket']))

    # Save outputs
    tag = f"{args.entry_window}_{args.exit_window}_{args.leverage}x"
    mc_path = os.path.join(args.output_dir, f"breakout_{tag}_cluster_by_marketcap.csv")
    fr_path = os.path.join(args.output_dir, f"breakout_{tag}_cluster_by_funding.csv")
    cl2d_path = os.path.join(args.output_dir, f"breakout_{tag}_cluster_2d.csv")

    mc_summary.to_csv(mc_path, index=False)
    fr_summary.to_csv(fr_path, index=False)
    cluster_2d.to_csv(cl2d_path, index=False)

    print(f"Saved: {mc_path}")
    print(f"Saved: {fr_path}")
    print(f"Saved: {cl2d_path}")


if __name__ == '__main__':
    main()
