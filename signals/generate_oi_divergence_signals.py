#!/usr/bin/env python3
"""
OI Divergence Signal Generator

Generates trading signals based on Open Interest (OI) divergence from price action.
This module computes z-scored OI changes vs price returns to identify:
- DIVERGENCE mode: Contrarian signals (buy OI rise + price fall, short OI rise + price rise)
- TREND mode: Momentum signals (buy OI rise + price rise, short OI fall + price fall)

Signal Rules:
- LONG: High divergence/trend score (top N symbols)
- SHORT: Low divergence/trend score (bottom N symbols)
- NEUTRAL: Symbols not in top/bottom N
"""

import argparse
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from signals.calc_open_interest_divergence import (
    compute_oi_divergence_scores,
    prepare_oi_data,
    prepare_price_data,
)


def generate_oi_divergence_signals(
    price_data: pd.DataFrame,
    oi_data: pd.DataFrame,
    mode: str = 'divergence',
    lookback: int = 30,
    top_n: int = 10,
    bottom_n: int = 10,
    min_data_points: int = 30,
) -> pd.DataFrame:
    """
    Generate OI divergence signals for all symbols over time.
    
    Parameters:
    -----------
    price_data : pd.DataFrame
        Price data with columns: date, symbol/base, close
    oi_data : pd.DataFrame
        OI data with columns: date, symbol/coin_symbol, oi_close/oi
    mode : str
        'divergence' (contrarian) or 'trend' (momentum)
    lookback : int
        Rolling window for z-score calculation
    top_n : int
        Number of symbols to go LONG (highest scores)
    bottom_n : int
        Number of symbols to go SHORT (lowest scores)
    min_data_points : int
        Minimum number of data points required per symbol
    
    Returns:
    --------
    pd.DataFrame
        Signals with columns: date, symbol, score, rank, signal, position_side, score_value
    """
    # Compute divergence scores
    scores_df = compute_oi_divergence_scores(oi_data, price_data, lookback=lookback)
    
    if scores_df.empty:
        print("Warning: No scores computed. Check data alignment.")
        return pd.DataFrame()
    
    # Select score column based on mode
    score_col = 'score_trend' if mode == 'trend' else 'score_divergence'
    
    # Remove rows with insufficient data
    scores_df = scores_df.dropna(subset=[score_col])
    
    # Generate signals for each date
    all_signals = []
    
    for date in scores_df['date'].unique():
        day_data = scores_df[scores_df['date'] == date].copy()
        
        if day_data.empty:
            continue
        
        # Sort by score (descending for divergence/trend)
        day_data = day_data.sort_values(score_col, ascending=False)
        
        # Remove duplicates, keep highest score per symbol
        day_data = day_data.drop_duplicates(subset=['symbol'], keep='first')
        
        # Assign ranks
        day_data['rank'] = range(1, len(day_data) + 1)
        day_data['score_value'] = day_data[score_col]
        
        # Assign signals
        day_data['signal'] = 'NEUTRAL'
        day_data['position_side'] = 'FLAT'
        
        # Top N = LONG
        if len(day_data) >= top_n:
            long_indices = day_data.head(top_n).index
            day_data.loc[long_indices, 'signal'] = 'LONG'
            day_data.loc[long_indices, 'position_side'] = 'LONG'
        
        # Bottom N = SHORT
        if len(day_data) >= bottom_n:
            short_indices = day_data.tail(bottom_n).index
            day_data.loc[short_indices, 'signal'] = 'SHORT'
            day_data.loc[short_indices, 'position_side'] = 'SHORT'
        
        # Keep relevant columns
        signals = day_data[[
            'date', 'symbol', 'rank', 'signal', 'position_side', 'score_value',
            'ret', 'd_oi', 'z_ret', 'z_doi'
        ]].copy()
        
        all_signals.append(signals)
    
    if not all_signals:
        return pd.DataFrame()
    
    result_df = pd.concat(all_signals, ignore_index=True)
    result_df = result_df.sort_values(['date', 'rank']).reset_index(drop=True)
    
    return result_df


def get_current_signals(
    price_data: pd.DataFrame,
    oi_data: pd.DataFrame,
    mode: str = 'divergence',
    lookback: int = 30,
    top_n: int = 10,
    bottom_n: int = 10,
    as_of_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Get the most recent OI divergence signals.
    
    Parameters:
    -----------
    price_data : pd.DataFrame
        Price data with columns: date, symbol/base, close
    oi_data : pd.DataFrame
        OI data with columns: date, symbol/coin_symbol, oi_close/oi
    mode : str
        'divergence' or 'trend'
    lookback : int
        Rolling window for z-score calculation
    top_n : int
        Number of LONG signals
    bottom_n : int
        Number of SHORT signals
    as_of_date : str, optional
        Specific date to get signals for (format: YYYY-MM-DD). If None, uses latest.
    
    Returns:
    --------
    pd.DataFrame
        Current signals for all symbols
    """
    all_signals = generate_oi_divergence_signals(
        price_data=price_data,
        oi_data=oi_data,
        mode=mode,
        lookback=lookback,
        top_n=top_n,
        bottom_n=bottom_n,
    )
    
    if all_signals.empty:
        return pd.DataFrame()
    
    # Get signals for specific date or latest
    if as_of_date:
        target_date = pd.to_datetime(as_of_date)
        current = all_signals[all_signals['date'] == target_date]
    else:
        latest_date = all_signals['date'].max()
        current = all_signals[all_signals['date'] == latest_date]
    
    return current.reset_index(drop=True)


def get_active_positions(
    price_data: pd.DataFrame,
    oi_data: pd.DataFrame,
    mode: str = 'divergence',
    lookback: int = 30,
    top_n: int = 10,
    bottom_n: int = 10,
    as_of_date: Optional[str] = None,
) -> Dict[str, List[str]]:
    """
    Get active LONG and SHORT positions based on current signals.
    
    Parameters:
    -----------
    price_data : pd.DataFrame
        Price data
    oi_data : pd.DataFrame
        OI data
    mode : str
        'divergence' or 'trend'
    lookback : int
        Rolling window
    top_n : int
        Number of LONG positions
    bottom_n : int
        Number of SHORT positions
    as_of_date : str, optional
        Specific date (YYYY-MM-DD)
    
    Returns:
    --------
    dict with keys:
        'longs': List of symbols with LONG signals
        'shorts': List of symbols with SHORT signals
        'signals_df': DataFrame with all current signals
        'date': Date of signals
        'mode': Strategy mode used
    """
    current = get_current_signals(
        price_data=price_data,
        oi_data=oi_data,
        mode=mode,
        lookback=lookback,
        top_n=top_n,
        bottom_n=bottom_n,
        as_of_date=as_of_date,
    )
    
    if current.empty:
        return {
            'longs': [],
            'shorts': [],
            'signals_df': pd.DataFrame(),
            'date': None,
            'mode': mode,
        }
    
    longs = current[current['position_side'] == 'LONG']['symbol'].tolist()
    shorts = current[current['position_side'] == 'SHORT']['symbol'].tolist()
    
    return {
        'longs': longs,
        'shorts': shorts,
        'signals_df': current,
        'date': current['date'].iloc[0] if len(current) > 0 else None,
        'mode': mode,
    }


def load_price_data(path: str) -> pd.DataFrame:
    """Load and prepare price data from CSV."""
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'])
    
    # Handle different column names
    if 'base' in df.columns:
        df['symbol'] = df['base']
    elif 'base_symbol' in df.columns:
        df['symbol'] = df['base_symbol']
    elif 'symbol' in df.columns:
        # Extract base if format is BTC/USD
        if '/' in str(df['symbol'].iloc[0]):
            df['symbol'] = df['symbol'].astype(str).str.split('/').str[0]
    
    # Keep only necessary columns
    df = df[['date', 'symbol', 'close']].dropna()
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    return df


def load_oi_data(path: str) -> pd.DataFrame:
    """Load and prepare OI data from CSV."""
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'])
    
    # Handle different column names for symbol
    if 'coin_symbol' in df.columns:
        df['symbol'] = df['coin_symbol']
    elif 'base_symbol' in df.columns:
        df['symbol'] = df['base_symbol']
    elif 'base' in df.columns:
        df['symbol'] = df['base']
    
    # Handle different column names for OI
    if 'oi_close' in df.columns:
        df['oi'] = df['oi_close']
    elif 'oi_usd' in df.columns:
        df['oi'] = df['oi_usd']
    elif 'open_interest' in df.columns:
        df['oi'] = df['open_interest']
    
    # Keep only necessary columns
    df = df[['date', 'symbol', 'oi']].dropna()
    df = df[df['oi'] > 0]  # Remove invalid OI values
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    return df


def main():
    parser = argparse.ArgumentParser(
        description='Generate OI Divergence Trading Signals',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('--price-data', type=str, 
                        default='data/raw/combined_coinbase_coinmarketcap_daily.csv',
                        help='Path to price data CSV')
    parser.add_argument('--oi-data', type=str, 
                        default='data/raw/historical_open_interest_all_perps_since2020_20251026_115907.csv',
                        help='Path to OI data CSV')
    parser.add_argument('--mode', type=str, default='divergence', 
                        choices=['divergence', 'trend'],
                        help='Signal mode: divergence (contrarian) or trend (momentum)')
    parser.add_argument('--lookback', type=int, default=30,
                        help='Lookback window for z-score calculation')
    parser.add_argument('--top-n', type=int, default=10,
                        help='Number of LONG positions')
    parser.add_argument('--bottom-n', type=int, default=10,
                        help='Number of SHORT positions')
    parser.add_argument('--output', type=str, default='signals/oi_divergence_signals.csv',
                        help='Output file path for signals')
    parser.add_argument('--current-only', action='store_true',
                        help='Only output current signals (latest date)')
    
    args = parser.parse_args()
    
    print("="*80)
    print("OI DIVERGENCE SIGNAL GENERATOR")
    print("="*80)
    print(f"Mode: {args.mode.upper()}")
    print(f"Lookback: {args.lookback} days")
    print(f"Portfolio: {args.top_n} longs + {args.bottom_n} shorts")
    print("="*80)
    
    # Load data
    print("\nLoading data...")
    price_df = load_price_data(args.price_data)
    oi_df = load_oi_data(args.oi_data)
    
    print(f"Price data: {len(price_df):,} rows, {price_df['symbol'].nunique()} symbols")
    print(f"  Date range: {price_df['date'].min().date()} to {price_df['date'].max().date()}")
    print(f"OI data: {len(oi_df):,} rows, {oi_df['symbol'].nunique()} symbols")
    print(f"  Date range: {oi_df['date'].min().date()} to {oi_df['date'].max().date()}")
    
    # Generate signals
    if args.current_only:
        print("\nGenerating current signals...")
        signals = get_current_signals(
            price_data=price_df,
            oi_data=oi_df,
            mode=args.mode,
            lookback=args.lookback,
            top_n=args.top_n,
            bottom_n=args.bottom_n,
        )
        
        if signals.empty:
            print("No signals generated!")
            return
        
        print(f"\nSignals as of {signals['date'].iloc[0].date()}:")
        print(f"Total symbols evaluated: {len(signals)}")
        
        # Get active positions
        active = get_active_positions(
            price_data=price_df,
            oi_data=oi_df,
            mode=args.mode,
            lookback=args.lookback,
            top_n=args.top_n,
            bottom_n=args.bottom_n,
        )
        
        print("\n" + "="*80)
        print(f"LONG POSITIONS ({len(active['longs'])}):")
        print("="*80)
        long_signals = signals[signals['position_side'] == 'LONG'].sort_values('rank')
        for _, row in long_signals.iterrows():
            print(f"  {row['rank']:2d}. {row['symbol']:10s}  Score: {row['score_value']:7.3f}  "
                  f"z_ret: {row['z_ret']:6.2f}  z_doi: {row['z_doi']:6.2f}")
        
        print("\n" + "="*80)
        print(f"SHORT POSITIONS ({len(active['shorts'])}):")
        print("="*80)
        short_signals = signals[signals['position_side'] == 'SHORT'].sort_values('rank', ascending=False)
        for _, row in short_signals.iterrows():
            print(f"  {row['rank']:2d}. {row['symbol']:10s}  Score: {row['score_value']:7.3f}  "
                  f"z_ret: {row['z_ret']:6.2f}  z_doi: {row['z_doi']:6.2f}")
        
        # Save current signals
        output_file = args.output.replace('.csv', '_current.csv')
        signals.to_csv(output_file, index=False)
        print(f"\nCurrent signals saved to: {output_file}")
        
    else:
        print("\nGenerating historical signals...")
        signals = generate_oi_divergence_signals(
            price_data=price_df,
            oi_data=oi_df,
            mode=args.mode,
            lookback=args.lookback,
            top_n=args.top_n,
            bottom_n=args.bottom_n,
        )
        
        if signals.empty:
            print("No signals generated!")
            return
        
        print(f"\nGenerated {len(signals):,} signal records")
        print(f"Date range: {signals['date'].min().date()} to {signals['date'].max().date()}")
        print(f"Unique symbols: {signals['symbol'].nunique()}")
        
        # Summary statistics
        long_count = (signals['position_side'] == 'LONG').sum()
        short_count = (signals['position_side'] == 'SHORT').sum()
        neutral_count = (signals['position_side'] == 'FLAT').sum()
        
        print(f"\nSignal distribution:")
        print(f"  LONG signals:    {long_count:,}")
        print(f"  SHORT signals:   {short_count:,}")
        print(f"  NEUTRAL:         {neutral_count:,}")
        
        # Save all signals
        signals.to_csv(args.output, index=False)
        print(f"\nAll signals saved to: {args.output}")
        
        # Also show current signals
        latest = signals[signals['date'] == signals['date'].max()]
        print(f"\n" + "="*80)
        print(f"Latest signals ({latest['date'].iloc[0].date()}):")
        print("="*80)
        print(f"LONG:  {', '.join(latest[latest['position_side'] == 'LONG']['symbol'].tolist())}")
        print(f"SHORT: {', '.join(latest[latest['position_side'] == 'SHORT']['symbol'].tolist())}")


if __name__ == '__main__':
    main()
