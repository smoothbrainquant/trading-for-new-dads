#!/usr/bin/env python3
"""
Master Data Update Script

This script updates all data sources in the correct order:
1. Market Cap data (CoinMarketCap)
2. Price data (Coinbase spot)
3. Open Interest data (Coinalyze)
4. Funding Rates/Carry data (Coinalyze)

Usage:
    python3 update_all_data.py [--skip-price] [--skip-marketcap] [--skip-oi] [--skip-funding]

Environment Variables Required:
    - CMC_API: CoinMarketCap API key (for market cap data)
    - COINALYZE_API: Coinalyze API key (for OI and funding rate data)
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"{title}")
    print("="*80 + "\n")

def check_environment():
    """Check that required environment variables are set"""
    print_section("CHECKING ENVIRONMENT")
    
    missing = []
    
    if not os.environ.get('CMC_API'):
        print("⚠ CMC_API not set - market cap data will use mock data")
    else:
        print("✓ CMC_API is set")
    
    if not os.environ.get('COINALYZE_API'):
        print("✗ COINALYZE_API not set - OI and funding rate data will fail")
        missing.append('COINALYZE_API')
    else:
        print("✓ COINALYZE_API is set")
    
    if missing:
        print(f"\n⚠ WARNING: Missing required environment variables: {', '.join(missing)}")
        print("Some data updates will fail. Continue anyway? (y/n): ", end='')
        response = input().lower()
        if response != 'y':
            print("Exiting...")
            sys.exit(1)
    
    return True

def update_market_cap(output_dir):
    """Update market cap data from CoinMarketCap"""
    print_section("1/4: UPDATING MARKET CAP DATA")
    
    try:
        from fetch_coinmarketcap_data import fetch_coinmarketcap_data, save_marketcap_data, map_symbols_to_trading_pairs
        
        # Fetch data
        df = fetch_coinmarketcap_data(limit=100)
        
        # Add trading symbol mapping
        df = map_symbols_to_trading_pairs(df)
        
        # Save to file
        output_file = output_dir / 'crypto_marketcap_latest.csv'
        save_marketcap_data(df, str(output_file))
        
        print(f"✓ Market cap data updated: {output_file}")
        return True
        
    except Exception as e:
        print(f"✗ Error updating market cap data: {e}")
        return False

def update_price_data(output_dir):
    """Update price data from Coinbase spot"""
    print_section("2/4: UPDATING PRICE DATA (COINBASE SPOT)")
    
    try:
        import ccxt
        from datetime import datetime, timedelta
        import pandas as pd
        import time
        
        # Initialize Coinbase
        exchange = ccxt.coinbase({'enableRateLimit': True})
        
        # Get top 50 volume pairs
        tickers = exchange.fetch_tickers()
        volume_data = []
        
        for symbol, ticker in tickers.items():
            if ('/USD' in symbol or '/USDT' in symbol or '/USDC' in symbol) and ':' not in symbol:
                volume_data.append({
                    'symbol': symbol,
                    'volume': ticker.get('quoteVolume', 0) or ticker.get('baseVolume', 0) or 0
                })
        
        volume_df = pd.DataFrame(volume_data)
        volume_df = volume_df.sort_values('volume', ascending=False)
        top_pairs = volume_df.head(50)['symbol'].tolist()
        
        print(f"Fetching data for {len(top_pairs)} top volume pairs...")
        
        # Fetch 100 days of data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=100)
        since = exchange.parse8601(start_date.isoformat())
        
        all_data = []
        
        for idx, symbol in enumerate(top_pairs, 1):
            try:
                print(f"  [{idx}/{len(top_pairs)}] {symbol}...", end=' ')
                
                ohlcv = exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe='1d',
                    since=since,
                    limit=100
                )
                
                if ohlcv:
                    df = pd.DataFrame(
                        ohlcv,
                        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                    )
                    df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
                    df['symbol'] = symbol
                    df = df[['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
                    all_data.append(df)
                    print(f"✓ {len(df)} days")
                else:
                    print("✗ No data")
                
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                print(f"✗ Error: {e}")
        
        # Combine and save
        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df = combined_df.sort_values(['date', 'symbol']).reset_index(drop=True)
            
            output_file = output_dir / 'coinbase_spot_latest.csv'
            combined_df.to_csv(output_file, index=False)
            
            print(f"\n✓ Price data updated: {output_file}")
            print(f"  Total records: {len(combined_df):,}")
            print(f"  Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
            return True
        else:
            print("\n✗ No price data was downloaded")
            return False
            
    except Exception as e:
        print(f"✗ Error updating price data: {e}")
        return False

def update_open_interest(output_dir):
    """Update open interest data from Coinalyze"""
    print_section("3/4: UPDATING OPEN INTEREST DATA")
    
    try:
        import subprocess
        
        # Change to output directory and run the OI fetch script
        result = subprocess.run(
            ['python3', '../scripts/fetch_all_historical_open_interest_max.py'],
            cwd=str(output_dir),
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode == 0:
            print("✓ Open interest data updated")
            return True
        else:
            print(f"✗ Error updating open interest data")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"✗ Error updating open interest data: {e}")
        return False

def update_funding_rates(output_dir):
    """Update funding rates data from Coinalyze"""
    print_section("4/4: UPDATING FUNDING RATES (CARRY) DATA")
    
    try:
        import subprocess
        
        # Change to output directory and run the funding rates fetch script
        result = subprocess.run(
            ['python3', '../scripts/fetch_all_historical_funding_rates_max.py'],
            cwd=str(output_dir),
            capture_output=True,
            text=True,
            timeout=600
        )
        
        if result.returncode == 0:
            print("✓ Funding rates data updated")
            return True
        else:
            print(f"✗ Error updating funding rates data")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"✗ Error updating funding rates data: {e}")
        return False

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description='Update all data sources (market cap, price, OI, funding rates)',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--skip-marketcap', action='store_true', help='Skip market cap update')
    parser.add_argument('--skip-price', action='store_true', help='Skip price data update')
    parser.add_argument('--skip-oi', action='store_true', help='Skip open interest update')
    parser.add_argument('--skip-funding', action='store_true', help='Skip funding rates update')
    parser.add_argument('--output-dir', type=str, default=None, help='Output directory (defaults to data/raw)')
    
    args = parser.parse_args()
    
    print_section("DATA UPDATE MASTER SCRIPT")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Determine output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        # Try to find data/raw directory
        current_dir = Path(__file__).parent
        possible_paths = [
            current_dir.parent / 'raw',
            Path('/workspace/data/raw'),
            Path.cwd() / 'data' / 'raw',
        ]
        
        output_dir = None
        for path in possible_paths:
            if path.exists() and path.is_dir():
                output_dir = path
                break
        
        if not output_dir:
            print("✗ Could not find data/raw directory. Please specify --output-dir")
            sys.exit(1)
    
    print(f"Output directory: {output_dir}")
    
    # Check environment
    check_environment()
    
    # Track results
    results = {}
    start_time = datetime.now()
    
    # Run updates in order
    if not args.skip_marketcap:
        results['market_cap'] = update_market_cap(output_dir)
    else:
        print("\nSkipping market cap update (--skip-marketcap)")
    
    if not args.skip_price:
        results['price'] = update_price_data(output_dir)
    else:
        print("\nSkipping price data update (--skip-price)")
    
    if not args.skip_oi:
        results['open_interest'] = update_open_interest(output_dir)
    else:
        print("\nSkipping open interest update (--skip-oi)")
    
    if not args.skip_funding:
        results['funding_rates'] = update_funding_rates(output_dir)
    else:
        print("\nSkipping funding rates update (--skip-funding)")
    
    # Print final summary
    elapsed = datetime.now() - start_time
    
    print_section("UPDATE SUMMARY")
    
    for data_type, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        print(f"{data_type.replace('_', ' ').title()}: {status}")
    
    print(f"\nTotal execution time: {elapsed.total_seconds() / 60:.1f} minutes")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Exit with error code if any updates failed
    if not all(results.values()):
        print("\n⚠ Some data updates failed. Please check the errors above.")
        sys.exit(1)
    else:
        print("\n✅ All data updates completed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main()
