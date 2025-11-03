#!/usr/bin/env python3
"""
Fill Price Data Gaps V2 - Focus on extending stale coins to present

This version prioritizes:
1. Extending coins that stopped updating (e.g., Oct 2021 batch)
2. High market cap coins first
3. Filling to present day

Usage:
    python3 fill_price_data_gaps_v2.py --analyze  # Analyze only
    python3 fill_price_data_gaps_v2.py --fill --limit 10  # Fill top 10 stale coins
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta
import argparse
import time
import requests
from typing import Dict, List, Optional
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class StaleDataAnalyzer:
    """Analyze stale/outdated price data."""
    
    def __init__(self, data_file: str):
        self.data_file = data_file
        self.df = None
        self.today = pd.Timestamp.now().normalize()
        
    def load_data(self):
        """Load price data."""
        print(f"Loading data from {self.data_file}...")
        self.df = pd.read_csv(self.data_file)
        self.df['date'] = pd.to_datetime(self.df['date'])
        print(f"  ✓ Loaded {len(self.df):,} rows, {self.df['base'].nunique()} symbols")
        
    def analyze(self) -> pd.DataFrame:
        """
        Analyze stale data - focus on coins not updated to present.
        
        Returns:
            DataFrame with analysis
        """
        print(f"\nAnalyzing staleness (today = {self.today.date()})...")
        
        results = []
        symbols = sorted(self.df['base'].unique())
        
        for i, symbol in enumerate(symbols, 1):
            if i % 30 == 0:
                print(f"  Progress: {i}/{len(symbols)}")
            
            symbol_data = self.df[self.df['base'] == symbol].sort_values('date')
            
            if len(symbol_data) == 0:
                continue
            
            first_date = symbol_data['date'].min()
            last_date = symbol_data['date'].max()
            days_of_data = len(symbol_data)
            
            # Calculate staleness
            days_stale = (self.today - last_date).days
            is_current = days_stale <= 7
            
            # Get market cap for prioritization
            latest = symbol_data.iloc[-1]
            market_cap = latest.get('market_cap', 0)
            rank = latest.get('cmc_rank', 999)
            
            # Priority score (higher = more important to fix)
            # Based on: market cap (high), days stale (many), recency (old = bad)
            if market_cap > 0 and days_stale > 0:
                priority = (market_cap / 1e9) * min(days_stale / 100, 10)  # Cap staleness multiplier
            else:
                priority = 0
            
            results.append({
                'symbol': symbol,
                'first_date': first_date,
                'last_date': last_date,
                'days_of_data': days_of_data,
                'days_stale': days_stale,
                'is_current': is_current,
                'needs_backfill': days_stale > 7,
                'market_cap': market_cap,
                'rank': rank if pd.notna(rank) else 999,
                'priority_score': priority,
                'backfill_start': last_date + timedelta(days=1) if days_stale > 0 else None,
                'backfill_end': self.today - timedelta(days=1)
            })
        
        df = pd.DataFrame(results)
        
        # Sort by priority (highest first)
        df = df.sort_values('priority_score', ascending=False)
        
        return df


class CoinGeckoFetcher:
    """Fetch data from CoinGecko API."""
    
    def __init__(self, api_key=None):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.rate_limit = 3.0  # seconds between calls (increased for stability)
        self.api_key = api_key or os.environ.get('COINGECKO_API_KEY')
        self.symbol_map = self._build_symbol_map()
        
    def _build_symbol_map(self) -> Dict[str, str]:
        """Map symbols to CoinGecko IDs."""
        return {
            'BTC': 'bitcoin',
            'ETH': 'ethereum',
            'SOL': 'solana',
            'XRP': 'ripple',
            'ADA': 'cardano',
            'DOGE': 'dogecoin',
            'DOT': 'polkadot',
            'AVAX': 'avalanche-2',
            'SHIB': 'shiba-inu',
            'LINK': 'chainlink',
            'UNI': 'uniswap',
            'LTC': 'litecoin',
            'BCH': 'bitcoin-cash',
            'NEAR': 'near',
            'APT': 'aptos',
            'ARB': 'arbitrum',
            'OP': 'optimism',
            'ICP': 'internet-computer',
            'POL': 'polygon-ecosystem-token',
            'MATIC': 'matic-network',
            'ATOM': 'cosmos',
            'XLM': 'stellar',
            'HBAR': 'hedera-hashgraph',
            'VET': 'vechain',
            'DAI': 'dai',
            'USDC': 'usd-coin',
            'USDT': 'tether',
            'BNB': 'binancecoin',
            'TRX': 'tron',
            'XMR': 'monero',
            'ETC': 'ethereum-classic',
            'FIL': 'filecoin',
            'AAVE': 'aave',
            'MKR': 'maker',
            'SNX': 'synthetix-network-token',
            'CRV': 'curve-dao-token',
            'COMP': 'compound-governance-token',
            'SUSHI': 'sushi',
            'YFI': 'yearn-finance',
            'GRT': 'the-graph',
            'SAND': 'the-sandbox',
            'MANA': 'decentraland',
            'AXS': 'axie-infinity',
            'ENS': 'ethereum-name-service',
            'LDO': 'lido-dao',
            'IMX': 'immutable-x',
            'RENDER': 'render-token',
            'INJ': 'injective-protocol',
            'SEI': 'sei-network',
            'SUI': 'sui',
            'STX': 'blockstack',
            'TIA': 'celestia',
            'PENDLE': 'pendle',
            'WLD': 'worldcoin-wld',
            'PEPE': 'pepe',
            'BONK': 'bonk',
            'FLOKI': 'floki',
            'WIF': 'dogwifcoin',
            'ALGO': 'algorand',
            'FLOW': 'flow',
            'ROSE': 'oasis-network',
            'KSM': 'kusama',
            'FTM': 'fantom',
            'EGLD': 'elrond-erd-2',
            'ZEC': 'zcash',
            'DASH': 'dash',
            'ENJ': 'enjincoin',
            'CHZ': 'chiliz',
            'THETA': 'theta-token',
            'ZRX': '0x',
            'MINA': 'mina-protocol',
            'CELO': 'celo',
            'KAVA': 'kava',
            'OSMO': 'osmosis',
        }
    
    def fetch(self, symbol: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data for symbol.
        
        Args:
            symbol: Coin symbol
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with OHLCV data or None
        """
        coin_id = self.symbol_map.get(symbol.upper())
        
        if not coin_id:
            print(f"    ⚠ No CoinGecko mapping for {symbol}")
            return None
        
        try:
            # CoinGecko API
            url = f"{self.base_url}/coins/{coin_id}/market_chart/range"
            params = {
                'vs_currency': 'usd',
                'from': int(start_date.timestamp()),
                'to': int(end_date.timestamp())
            }
            
            headers = {}
            if self.api_key:
                headers['x-cg-demo-api-key'] = self.api_key
            
            print(f"    Fetching {symbol} ({start_date.date()} to {end_date.date()})...")
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            time.sleep(self.rate_limit)
            
            if response.status_code != 200:
                print(f"    ✗ API error {response.status_code}")
                return None
            
            data = response.json()
            
            if 'prices' not in data or len(data['prices']) == 0:
                print(f"    ✗ No data returned")
                return None
            
            # Parse response
            rows = []
            prices = data['prices']
            volumes = data.get('total_volumes', [])
            
            for i, (ts, price) in enumerate(prices):
                date = pd.to_datetime(ts, unit='ms').normalize()
                volume = volumes[i][1] if i < len(volumes) else 0
                
                rows.append({
                    'date': date,
                    'symbol': f'{symbol}/USD',
                    'base': symbol,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': volume
                })
            
            df = pd.DataFrame(rows)
            
            # Aggregate to daily
            df = df.groupby(['date', 'symbol', 'base']).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).reset_index()
            
            print(f"    ✓ Fetched {len(df)} days")
            return df
            
        except Exception as e:
            print(f"    ✗ Error: {e}")
            return None


def print_analysis(df: pd.DataFrame, top_n: int = 50):
    """Print analysis report."""
    print(f"\n{'=' * 80}")
    print(f"STALE DATA ANALYSIS")
    print(f"{'=' * 80}")
    
    # Overall stats
    total = len(df)
    current = df['is_current'].sum()
    stale = df['needs_backfill'].sum()
    
    print(f"\nOverall:")
    print(f"  Total symbols: {total}")
    print(f"  Current (≤7 days old): {current} ({current/total*100:.1f}%)")
    print(f"  Stale (>7 days old): {stale} ({stale/total*100:.1f}%)")
    
    # By staleness bucket
    buckets = [
        ("0-7 days (current)", 0, 7),
        ("8-30 days", 8, 30),
        ("31-90 days", 31, 90),
        ("91-365 days", 91, 365),
        ("1-2 years", 366, 730),
        ("2+ years", 731, 9999)
    ]
    
    print(f"\nStaleness Distribution:")
    for name, min_days, max_days in buckets:
        count = ((df['days_stale'] >= min_days) & (df['days_stale'] <= max_days)).sum()
        if count > 0:
            print(f"  {name:<20} {count:>4} symbols")
    
    # Top stale coins by market cap
    stale_coins = df[df['needs_backfill']].head(top_n)
    
    print(f"\n{'=' * 80}")
    print(f"TOP {len(stale_coins)} STALE COINS (by priority)")
    print(f"{'=' * 80}")
    
    print(f"\n{'#':<4} {'Symbol':<8} {'Rank':<6} {'MCap':<12} {'Last Date':<12} {'Stale':<10} {'Priority':<10} {'Days Needed':<12}")
    print('-' * 90)
    
    for i, row in stale_coins.iterrows():
        rank = f"{row['rank']:.0f}" if row['rank'] < 999 else "N/A"
        mcap = f"${row['market_cap']/1e9:.1f}B" if row['market_cap'] > 0 else "N/A"
        
        print(f"{i+1:<4} {row['symbol']:<8} {rank:<6} {mcap:<12} "
              f"{row['last_date'].date()!s:<12} {row['days_stale']:<10} "
              f"{row['priority_score']:<10.1f} {row['days_stale']:<12}")
    
    # Save report
    report_file = 'stale_price_data_analysis.csv'
    df.to_csv(report_file, index=False)
    print(f"\n✓ Saved detailed report: {report_file}")


def fill_gaps(df: pd.DataFrame, data_file: str, limit: Optional[int] = None, 
              dry_run: bool = False) -> None:
    """Fill gaps for stale coins."""
    
    # Filter to coins that need backfilling
    to_fill = df[df['needs_backfill']].copy()
    
    if limit:
        to_fill = to_fill.head(limit)
    
    print(f"\n{'=' * 80}")
    print(f"FILLING STALE DATA FOR {len(to_fill)} COINS")
    print(f"{'=' * 80}")
    
    if dry_run:
        print("\n⚠ DRY RUN - Would fetch:")
        for i, row in to_fill.iterrows():
            print(f"  {i+1}. {row['symbol']}: {row['backfill_start'].date()} to {row['backfill_end'].date()} ({row['days_stale']} days)")
        return
    
    # Load existing data
    print(f"\nLoading existing data...")
    df_existing = pd.read_csv(data_file)
    df_existing['date'] = pd.to_datetime(df_existing['date'])
    print(f"  ✓ {len(df_existing):,} rows")
    
    fetcher = CoinGeckoFetcher()
    new_data = []
    stats = {'success': 0, 'failed': 0, 'rows': 0}
    
    for idx, row in to_fill.iterrows():
        print(f"\n[{idx+1}/{len(to_fill)}] {row['symbol']}")
        print(f"  Rank: {row['rank']:.0f}, MCap: ${row['market_cap']/1e9:.1f}B")
        print(f"  Last: {row['last_date'].date()}, Need: {row['days_stale']} days")
        
        # Fetch data
        df_new = fetcher.fetch(
            row['symbol'],
            row['backfill_start'],
            row['backfill_end']
        )
        
        if df_new is not None and len(df_new) > 0:
            new_data.append(df_new)
            stats['rows'] += len(df_new)
            stats['success'] += 1
        else:
            stats['failed'] += 1
    
    # Combine and save
    if len(new_data) > 0:
        print(f"\n{'=' * 80}")
        print("SAVING RESULTS")
        print(f"{'=' * 80}")
        
        df_new = pd.concat(new_data, ignore_index=True)
        print(f"\nNew rows: {len(df_new):,}")
        
        # Merge
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined = df_combined.drop_duplicates(subset=['date', 'base'], keep='last')
        df_combined = df_combined.sort_values(['base', 'date']).reset_index(drop=True)
        
        print(f"Total rows: {len(df_combined):,} (added {len(df_combined) - len(df_existing):,})")
        
        # Backup and save
        backup = data_file.replace('.csv', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
        df_existing.to_csv(backup, index=False)
        print(f"✓ Backup: {backup}")
        
        df_combined.to_csv(data_file, index=False)
        print(f"✓ Saved: {data_file}")
    
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")
    print(f"Processed: {len(to_fill)}")
    print(f"Success: {stats['success']}")
    print(f"Failed: {stats['failed']}")
    print(f"New rows: {stats['rows']:,}")


def main():
    parser = argparse.ArgumentParser(description="Fill stale price data gaps")
    parser.add_argument('--data-file', default='data/raw/combined_coinbase_coinmarketcap_daily.csv')
    parser.add_argument('--analyze', action='store_true', help='Analyze only')
    parser.add_argument('--fill', action='store_true', help='Fill gaps')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (show what would be done)')
    parser.add_argument('--limit', type=int, default=None, help='Limit coins to process')
    parser.add_argument('--top', type=int, default=50, help='Top N to show in report')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("STALE PRICE DATA BACKFILL")
    print("=" * 80)
    print(f"Data: {args.data_file}")
    print(f"Mode: {'ANALYZE' if args.analyze else 'DRY RUN' if args.dry_run else 'FILL'}")
    
    # Analyze
    analyzer = StaleDataAnalyzer(args.data_file)
    analyzer.load_data()
    df = analyzer.analyze()
    
    print_analysis(df, top_n=args.top)
    
    # Fill if requested
    if args.fill or args.dry_run:
        fill_gaps(df, args.data_file, limit=args.limit, dry_run=args.dry_run)
    
    print(f"\n{'=' * 80}")
    print("COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
