#!/usr/bin/env python3
"""
Fill Price Data Gaps - Systematic Gap Analysis and Backfilling

This script:
1. Analyzes gaps in combined_coinbase_coinmarketcap_daily.csv
2. Prioritizes high market cap coins
3. Fetches missing data from multiple sources
4. Backfills systematically
5. Updates the combined file

Usage:
    python3 fill_price_data_gaps.py --dry-run  # Analyze only
    python3 fill_price_data_gaps.py --fill     # Actually fill gaps
    python3 fill_price_data_gaps.py --fill --limit 10  # Fill top 10 coins only
"""

import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime, timedelta
import argparse
import time
import requests
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

class GapAnalyzer:
    """Analyze gaps in price data."""
    
    def __init__(self, data_file: str):
        """Initialize with data file path."""
        self.data_file = data_file
        self.df = None
        self.gaps = []
        
    def load_data(self):
        """Load price data."""
        print(f"Loading data from {self.data_file}...")
        self.df = pd.read_csv(self.data_file)
        self.df['date'] = pd.to_datetime(self.df['date'])
        print(f"  Loaded {len(self.df):,} rows, {self.df['base'].nunique()} symbols")
        
    def analyze_gaps(self) -> pd.DataFrame:
        """
        Analyze gaps for each symbol.
        
        Returns:
            DataFrame with gap analysis per symbol
        """
        print("\nAnalyzing gaps...")
        
        gap_data = []
        symbols = sorted(self.df['base'].unique())
        
        for i, symbol in enumerate(symbols, 1):
            if i % 20 == 0:
                print(f"  Progress: {i}/{len(symbols)}")
            
            symbol_data = self.df[self.df['base'] == symbol].sort_values('date')
            
            if len(symbol_data) == 0:
                continue
            
            # Get date range
            first_date = symbol_data['date'].min()
            last_date = symbol_data['date'].max()
            days_span = (last_date - first_date).days
            actual_days = len(symbol_data)
            
            # Expected vs actual (assuming daily data)
            expected_days = days_span + 1
            missing_days = expected_days - actual_days
            coverage_pct = actual_days / expected_days * 100 if expected_days > 0 else 0
            
            # Check if current (has recent data)
            days_since_last = (pd.Timestamp.now() - last_date).days
            is_current = days_since_last <= 7  # Within last week
            
            # Get latest market cap (for prioritization)
            latest_data = symbol_data.iloc[-1]
            market_cap = latest_data.get('market_cap', 0)
            rank = latest_data.get('cmc_rank', 999)
            
            # Identify specific gaps
            gaps = self._find_date_gaps(symbol_data)
            
            gap_data.append({
                'symbol': symbol,
                'first_date': first_date,
                'last_date': last_date,
                'days_span': days_span,
                'actual_days': actual_days,
                'expected_days': expected_days,
                'missing_days': missing_days,
                'coverage_pct': coverage_pct,
                'is_current': is_current,
                'days_since_last': days_since_last,
                'market_cap': market_cap,
                'rank': rank if pd.notna(rank) else 999,
                'num_gaps': len(gaps),
                'largest_gap_days': max([g['days'] for g in gaps]) if gaps else 0,
                'gaps': gaps
            })
        
        gap_df = pd.DataFrame(gap_data)
        
        # Sort by market cap (highest first)
        gap_df = gap_df.sort_values('market_cap', ascending=False)
        
        return gap_df
    
    def _find_date_gaps(self, symbol_data: pd.DataFrame) -> List[Dict]:
        """Find specific date gaps in symbol data."""
        if len(symbol_data) < 2:
            return []
        
        symbol_data = symbol_data.sort_values('date')
        dates = symbol_data['date'].tolist()
        
        gaps = []
        for i in range(len(dates) - 1):
            current = dates[i]
            next_date = dates[i + 1]
            expected_next = current + timedelta(days=1)
            
            if next_date > expected_next:
                gap_days = (next_date - expected_next).days
                gaps.append({
                    'start': expected_next,
                    'end': next_date - timedelta(days=1),
                    'days': gap_days
                })
        
        # Check gap from last date to today (if not current)
        last_date = dates[-1]
        today = pd.Timestamp.now().normalize()
        if last_date < today - timedelta(days=1):
            gap_days = (today - last_date).days - 1
            if gap_days > 0:
                gaps.append({
                    'start': last_date + timedelta(days=1),
                    'end': today - timedelta(days=1),
                    'days': gap_days
                })
        
        return gaps


class DataFetcher:
    """Fetch missing data from multiple sources."""
    
    def __init__(self):
        """Initialize data fetcher."""
        self.coingecko_base = "https://api.coingecko.com/api/v3"
        self.rate_limit_delay = 1.2  # CoinGecko free tier: 50 calls/minute
        
    def fetch_coingecko(self, symbol: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """
        Fetch data from CoinGecko.
        
        Args:
            symbol: Coin symbol (e.g., 'BTC')
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with OHLCV data or None if failed
        """
        try:
            # Map common symbols to CoinGecko IDs
            symbol_to_id = self._get_symbol_mapping()
            coin_id = symbol_to_id.get(symbol.upper())
            
            if not coin_id:
                print(f"    ⚠ No CoinGecko mapping for {symbol}")
                return None
            
            # Convert dates to timestamps
            start_ts = int(start_date.timestamp())
            end_ts = int(end_date.timestamp())
            
            url = f"{self.coingecko_base}/coins/{coin_id}/market_chart/range"
            params = {
                'vs_currency': 'usd',
                'from': start_ts,
                'to': end_ts
            }
            
            print(f"    Fetching {symbol} from CoinGecko ({start_date.date()} to {end_date.date()})...")
            
            response = requests.get(url, params=params, timeout=30)
            time.sleep(self.rate_limit_delay)  # Rate limiting
            
            if response.status_code != 200:
                print(f"    ✗ CoinGecko API error: {response.status_code}")
                return None
            
            data = response.json()
            
            if 'prices' not in data or len(data['prices']) == 0:
                print(f"    ✗ No data returned")
                return None
            
            # Parse data
            prices = data['prices']
            volumes = data.get('total_volumes', [])
            
            df_data = []
            for i, (ts, price) in enumerate(prices):
                date = pd.to_datetime(ts, unit='ms').normalize()
                volume = volumes[i][1] if i < len(volumes) else 0
                
                df_data.append({
                    'date': date,
                    'symbol': f'{symbol}/USD',
                    'base': symbol,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                    'volume': volume
                })
            
            df = pd.DataFrame(df_data)
            
            # Aggregate to daily (CoinGecko returns hourly for some ranges)
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
            print(f"    ✗ Error fetching from CoinGecko: {e}")
            return None
    
    def _get_symbol_mapping(self) -> Dict[str, str]:
        """
        Map common symbols to CoinGecko IDs.
        
        Returns:
            Dict mapping symbol to CoinGecko ID
        """
        # Common mappings (expand as needed)
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
            'TURBO': 'turbo',
            'WIF': 'dogwifcoin',
        }


class GapFiller:
    """Fill gaps in price data."""
    
    def __init__(self, data_file: str, output_file: str = None):
        """
        Initialize gap filler.
        
        Args:
            data_file: Input data file
            output_file: Output file (default: overwrite input)
        """
        self.data_file = data_file
        self.output_file = output_file or data_file
        self.fetcher = DataFetcher()
        
    def fill_gaps(self, gap_df: pd.DataFrame, limit: Optional[int] = None, 
                  min_market_cap: float = 0, dry_run: bool = False) -> pd.DataFrame:
        """
        Fill gaps in price data.
        
        Args:
            gap_df: Gap analysis DataFrame
            limit: Limit number of symbols to process
            min_market_cap: Minimum market cap to process
            dry_run: If True, don't actually fetch/save data
            
        Returns:
            Updated gap analysis DataFrame
        """
        # Filter by criteria
        to_fill = gap_df[
            (gap_df['missing_days'] > 0) & 
            (gap_df['market_cap'] >= min_market_cap)
        ].copy()
        
        if limit:
            to_fill = to_fill.head(limit)
        
        print(f"\n{'=' * 80}")
        print(f"FILLING GAPS FOR {len(to_fill)} SYMBOLS")
        print(f"{'=' * 80}")
        
        if dry_run:
            print("\n⚠ DRY RUN MODE - No data will be fetched or saved")
        
        # Load existing data
        print(f"\nLoading existing data from {self.data_file}...")
        df_existing = pd.read_csv(self.data_file)
        df_existing['date'] = pd.to_datetime(df_existing['date'])
        print(f"  Loaded {len(df_existing):,} existing rows")
        
        new_rows = []
        stats = {'success': 0, 'failed': 0, 'skipped': 0, 'new_rows': 0}
        
        for idx, row in to_fill.iterrows():
            symbol = row['symbol']
            gaps = row['gaps']
            market_cap = row['market_cap']
            rank = row['rank']
            
            print(f"\n{idx+1}/{len(to_fill)}: {symbol}")
            print(f"  Market cap: ${market_cap/1e9:.2f}B (Rank: {rank:.0f})")
            print(f"  Missing: {row['missing_days']} days in {row['num_gaps']} gap(s)")
            print(f"  Coverage: {row['coverage_pct']:.1f}%")
            
            if dry_run:
                print(f"  [DRY RUN] Would fill gaps:")
                for i, gap in enumerate(gaps, 1):
                    print(f"    Gap {i}: {gap['start'].date()} to {gap['end'].date()} ({gap['days']} days)")
                stats['skipped'] += 1
                continue
            
            # Fill each gap
            symbol_success = True
            for i, gap in enumerate(gaps, 1):
                print(f"  Gap {i}/{len(gaps)}: {gap['start'].date()} to {gap['end'].date()} ({gap['days']} days)")
                
                # Fetch data for this gap
                gap_data = self.fetcher.fetch_coingecko(
                    symbol, 
                    gap['start'], 
                    gap['end']
                )
                
                if gap_data is not None and len(gap_data) > 0:
                    new_rows.append(gap_data)
                    stats['new_rows'] += len(gap_data)
                    print(f"    ✓ Fetched {len(gap_data)} days")
                else:
                    print(f"    ✗ Failed to fetch data")
                    symbol_success = False
                
                # Rate limiting between gaps
                time.sleep(1)
            
            if symbol_success:
                stats['success'] += 1
            else:
                stats['failed'] += 1
        
        # Combine and save
        if not dry_run and len(new_rows) > 0:
            print(f"\n{'=' * 80}")
            print(f"SAVING RESULTS")
            print(f"{'=' * 80}")
            
            # Combine all new data
            df_new = pd.concat(new_rows, ignore_index=True)
            print(f"\nNew rows fetched: {len(df_new):,}")
            
            # Combine with existing
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            
            # Remove duplicates (prefer new data)
            df_combined = df_combined.sort_values('date').drop_duplicates(
                subset=['date', 'base'], 
                keep='last'
            )
            
            print(f"Total rows after merge: {len(df_combined):,}")
            print(f"Net new rows added: {len(df_combined) - len(df_existing):,}")
            
            # Sort by symbol and date
            df_combined = df_combined.sort_values(['base', 'date']).reset_index(drop=True)
            
            # Save
            print(f"\nSaving to {self.output_file}...")
            df_combined.to_csv(self.output_file, index=False)
            print(f"✓ Saved!")
            
            # Backup original if overwriting
            if self.output_file == self.data_file:
                backup_file = self.data_file.replace('.csv', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
                df_existing.to_csv(backup_file, index=False)
                print(f"✓ Backup saved to: {backup_file}")
        
        # Print summary
        print(f"\n{'=' * 80}")
        print(f"SUMMARY")
        print(f"{'=' * 80}")
        print(f"Symbols processed: {len(to_fill)}")
        print(f"  Success: {stats['success']}")
        print(f"  Failed: {stats['failed']}")
        print(f"  Skipped (dry run): {stats['skipped']}")
        print(f"New rows fetched: {stats['new_rows']:,}")
        
        return gap_df


def print_gap_report(gap_df: pd.DataFrame, top_n: int = 30):
    """Print gap analysis report."""
    print(f"\n{'=' * 80}")
    print(f"GAP ANALYSIS REPORT")
    print(f"{'=' * 80}")
    
    # Overall stats
    total_symbols = len(gap_df)
    symbols_with_gaps = (gap_df['missing_days'] > 0).sum()
    total_missing_days = gap_df['missing_days'].sum()
    avg_coverage = gap_df['coverage_pct'].mean()
    current_symbols = gap_df['is_current'].sum()
    
    print(f"\nOverall Statistics:")
    print(f"  Total symbols: {total_symbols}")
    print(f"  Symbols with gaps: {symbols_with_gaps} ({symbols_with_gaps/total_symbols*100:.1f}%)")
    print(f"  Total missing days: {total_missing_days:,}")
    print(f"  Average coverage: {avg_coverage:.1f}%")
    print(f"  Current symbols (updated within 7 days): {current_symbols}")
    
    # Top gaps by market cap
    print(f"\n{'=' * 80}")
    print(f"TOP {top_n} COINS BY MARKET CAP - GAP STATUS")
    print(f"{'=' * 80}")
    
    top_coins = gap_df.head(top_n)
    
    print(f"\n{'Rank':<6} {'Symbol':<8} {'Market Cap':<12} {'Days':<8} {'Missing':<10} {'Coverage':<10} {'Current':<10} {'Gaps':<8}")
    print('-' * 80)
    
    for _, row in top_coins.iterrows():
        rank = f"{row['rank']:.0f}" if row['rank'] < 999 else "N/A"
        mcap = f"${row['market_cap']/1e9:.1f}B" if row['market_cap'] > 0 else "N/A"
        current = "✓ YES" if row['is_current'] else f"✗ {row['days_since_last']}d ago"
        
        print(f"{rank:<6} {row['symbol']:<8} {mcap:<12} {row['actual_days']:<8} "
              f"{row['missing_days']:<10} {row['coverage_pct']:<9.1f}% {current:<10} {row['num_gaps']:<8}")
    
    # Symbols needing attention
    needs_attention = gap_df[
        (gap_df['missing_days'] > 100) | 
        (~gap_df['is_current'] & (gap_df['market_cap'] > 1e9))
    ].head(20)
    
    if len(needs_attention) > 0:
        print(f"\n{'=' * 80}")
        print(f"SYMBOLS NEEDING IMMEDIATE ATTENTION")
        print(f"{'=' * 80}")
        print(f"(Large gaps or major coins that aren't current)")
        
        for _, row in needs_attention.iterrows():
            print(f"\n{row['symbol']} (Rank {row['rank']:.0f}, ${row['market_cap']/1e9:.1f}B)")
            print(f"  Missing: {row['missing_days']} days ({100-row['coverage_pct']:.1f}% of range)")
            print(f"  Last update: {row['last_date'].date()} ({row['days_since_last']} days ago)")
            print(f"  Gaps: {row['num_gaps']} (largest: {row['largest_gap_days']} days)")
    
    # Save detailed report
    report_file = 'price_data_gap_analysis.csv'
    gap_df_export = gap_df.copy()
    gap_df_export['gaps'] = gap_df_export['gaps'].apply(lambda x: str(x))
    gap_df_export.to_csv(report_file, index=False)
    print(f"\n✓ Detailed report saved to: {report_file}")


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(
        description="Analyze and fill gaps in price data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--data-file',
        type=str,
        default='data/raw/combined_coinbase_coinmarketcap_daily.csv',
        help='Path to price data file'
    )
    parser.add_argument(
        '--output-file',
        type=str,
        default=None,
        help='Output file (default: overwrite input file)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Analyze gaps only, do not fetch data'
    )
    parser.add_argument(
        '--fill',
        action='store_true',
        help='Fill gaps (fetch missing data)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of symbols to process'
    )
    parser.add_argument(
        '--min-market-cap',
        type=float,
        default=1e9,  # $1B
        help='Minimum market cap (in USD) to process (default: 1B)'
    )
    parser.add_argument(
        '--top',
        type=int,
        default=30,
        help='Number of top coins to show in report'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("PRICE DATA GAP ANALYSIS AND FILLING")
    print("=" * 80)
    print(f"\nData file: {args.data_file}")
    print(f"Mode: {'DRY RUN (analysis only)' if args.dry_run else 'FILL GAPS' if args.fill else 'ANALYSIS ONLY'}")
    if args.fill:
        print(f"Limit: {args.limit if args.limit else 'No limit'}")
        print(f"Min market cap: ${args.min_market_cap/1e9:.1f}B")
    
    # Step 1: Analyze gaps
    analyzer = GapAnalyzer(args.data_file)
    analyzer.load_data()
    gap_df = analyzer.analyze_gaps()
    
    # Step 2: Print report
    print_gap_report(gap_df, top_n=args.top)
    
    # Step 3: Fill gaps if requested
    if args.fill or args.dry_run:
        filler = GapFiller(args.data_file, args.output_file)
        gap_df = filler.fill_gaps(
            gap_df, 
            limit=args.limit,
            min_market_cap=args.min_market_cap,
            dry_run=args.dry_run
        )
    
    print(f"\n{'=' * 80}")
    print("COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
