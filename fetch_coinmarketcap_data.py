"""
Fetch Market Cap Data from CoinMarketCap

This script fetches current market cap data for cryptocurrencies from CoinMarketCap API.
Market cap is used for size factor analysis where smaller cap coins may exhibit
different return characteristics compared to large cap coins.
"""

import requests
import pandas as pd
import json
import os
import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


def fetch_coinmarketcap_data(api_key=None, limit=100, convert='USD'):
    """
    Fetch cryptocurrency market cap data from CoinMarketCap.
    
    Args:
        api_key (str): CoinMarketCap API key. If None, tries to read from CMC_API env var
        limit (int): Number of cryptocurrencies to fetch (max 5000)
        convert (str): Currency for conversion (default USD)
        
    Returns:
        pd.DataFrame: DataFrame with symbol, name, market_cap, price, volume_24h, etc.
    """
    # Get API key from environment if not provided
    if api_key is None:
        api_key = os.environ.get('CMC_API')
        if not api_key:
            print("WARNING: No CoinMarketCap API key found.")
            print("Please set CMC_API environment variable or use demo mode.")
            print("Using demo/mock data instead...")
            return fetch_mock_marketcap_data(limit)
    
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
    
    parameters = {
        'start': '1',
        'limit': str(limit),
        'convert': convert,
        'sort': 'market_cap',
        'sort_dir': 'desc'
    }
    
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': api_key,
    }
    
    try:
        print(f"Fetching top {limit} cryptocurrencies from CoinMarketCap...")
        response = requests.get(url, headers=headers, params=parameters)
        response.raise_for_status()
        
        data = response.json()
        
        if 'data' not in data:
            print(f"ERROR: Unexpected API response structure")
            return fetch_mock_marketcap_data(limit)
        
        # Parse the data
        coins_data = []
        for coin in data['data']:
            quote = coin['quote'][convert]
            coins_data.append({
                'symbol': coin['symbol'],
                'name': coin['name'],
                'cmc_rank': coin['cmc_rank'],
                'market_cap': quote['market_cap'],
                'price': quote['price'],
                'volume_24h': quote['volume_24h'],
                'percent_change_24h': quote['percent_change_24h'],
                'percent_change_7d': quote['percent_change_7d'],
                'market_cap_dominance': quote['market_cap_dominance'],
                'timestamp': datetime.now().isoformat()
            })
        
        df = pd.DataFrame(coins_data)
        print(f"Successfully fetched {len(df)} cryptocurrencies")
        return df
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR fetching from CoinMarketCap: {e}")
        print("Using mock data instead...")
        return fetch_mock_marketcap_data(limit)


def fetch_historical_top100_quarterly(api_key=None, start_year=2020, end_date=None, limit=100, convert='USD', delay_seconds=1):
    """
    Fetch historical top 100 cryptocurrencies by market cap, once per quarter.
    
    This fetches snapshots of the top cryptocurrencies at the end of each quarter
    (March 31, June 30, September 30, December 31) from the start year to present.
    
    Args:
        api_key (str): CoinMarketCap API key. If None, tries to read from CMC_API env var
        start_year (int): Starting year for historical data (default 2020)
        end_date (datetime): End date for data collection (default today)
        limit (int): Number of cryptocurrencies to fetch per quarter (default 100)
        convert (str): Currency for conversion (default USD)
        delay_seconds (float): Delay between API calls to respect rate limits (default 1 second)
        
    Returns:
        pd.DataFrame: DataFrame with all quarterly snapshots, includes 'snapshot_date' column
    """
    # Get API key from environment if not provided
    if api_key is None:
        api_key = os.environ.get('CMC_API')
        if not api_key:
            print("ERROR: No CoinMarketCap API key found.")
            print("Historical data requires a paid CoinMarketCap API plan.")
            print("Please set CMC_API environment variable with a valid API key.")
            return None
    
    if end_date is None:
        end_date = datetime.now()
    
    # Generate quarterly dates (end of each quarter)
    quarterly_dates = []
    current_date = datetime(start_year, 3, 31)  # Q1 end: March 31
    
    while current_date <= end_date:
        quarterly_dates.append(current_date)
        # Move to next quarter end
        if current_date.month == 3:
            current_date = datetime(current_date.year, 6, 30)
        elif current_date.month == 6:
            current_date = datetime(current_date.year, 9, 30)
        elif current_date.month == 9:
            current_date = datetime(current_date.year, 12, 31)
        else:  # December
            current_date = datetime(current_date.year + 1, 3, 31)
    
    print(f"Fetching historical data for {len(quarterly_dates)} quarters")
    print(f"Date range: {quarterly_dates[0].strftime('%Y-%m-%d')} to {quarterly_dates[-1].strftime('%Y-%m-%d')}")
    print(f"This will make {len(quarterly_dates)} API calls with {delay_seconds}s delays")
    print(f"Estimated time: ~{len(quarterly_dates) * delay_seconds / 60:.1f} minutes\n")
    
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/historical'
    
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': api_key,
    }
    
    all_data = []
    failed_dates = []
    
    for i, snapshot_date in enumerate(quarterly_dates, 1):
        date_str = snapshot_date.strftime('%Y-%m-%d')
        
        parameters = {
            'date': date_str,
            'limit': str(limit),
            'convert': convert,
            'sort': 'market_cap',
            'sort_dir': 'desc'
        }
        
        try:
            print(f"[{i}/{len(quarterly_dates)}] Fetching {date_str}...", end=' ')
            response = requests.get(url, headers=headers, params=parameters)
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' not in data:
                print(f"❌ No data in response")
                failed_dates.append(date_str)
                continue
            
            # Parse the data for this quarter
            for coin in data['data']:
                quote = coin['quote'][convert]
                all_data.append({
                    'snapshot_date': date_str,
                    'quarter': f"{snapshot_date.year}-Q{(snapshot_date.month-1)//3 + 1}",
                    'symbol': coin['symbol'],
                    'name': coin['name'],
                    'cmc_rank': coin['cmc_rank'],
                    'market_cap': quote['market_cap'],
                    'price': quote['price'],
                    'volume_24h': quote['volume_24h'],
                    'percent_change_24h': quote.get('percent_change_24h'),
                    'percent_change_7d': quote.get('percent_change_7d'),
                    'market_cap_dominance': quote.get('market_cap_dominance'),
                    'circulating_supply': coin.get('circulating_supply'),
                    'total_supply': coin.get('total_supply'),
                    'max_supply': coin.get('max_supply'),
                })
            
            print(f"✓ {len(data['data'])} coins")
            
            # Respect rate limits
            if i < len(quarterly_dates):
                time.sleep(delay_seconds)
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error: {e}")
            failed_dates.append(date_str)
            # Continue with other dates even if one fails
            time.sleep(delay_seconds)
    
    if not all_data:
        print("\n❌ No data was successfully fetched!")
        print("This could be due to:")
        print("  1. Invalid or expired API key")
        print("  2. API plan doesn't include historical data access")
        print("  3. Network connectivity issues")
        return None
    
    df = pd.DataFrame(all_data)
    
    print(f"\n{'='*80}")
    print(f"✓ Successfully fetched {len(df)} records across {len(quarterly_dates) - len(failed_dates)} quarters")
    print(f"  Unique coins: {df['symbol'].nunique()}")
    print(f"  Date range: {df['snapshot_date'].min()} to {df['snapshot_date'].max()}")
    
    if failed_dates:
        print(f"\n⚠️  Failed dates ({len(failed_dates)}): {', '.join(failed_dates)}")
    
    # Summary by quarter
    print(f"\nRecords per quarter:")
    quarter_counts = df.groupby('quarter').size()
    for quarter, count in quarter_counts.items():
        print(f"  {quarter}: {count} coins")
    
    print(f"{'='*80}\n")
    
    return df


def fetch_mock_marketcap_data(limit=100):
    """
    Generate mock market cap data for testing when API key is not available.
    This uses approximate values based on typical crypto market structure.
    
    Args:
        limit (int): Number of cryptocurrencies to generate
        
    Returns:
        pd.DataFrame: Mock market cap data
    """
    import numpy as np
    
    # Common crypto symbols (top cryptocurrencies)
    common_symbols = [
        'BTC', 'ETH', 'BNB', 'SOL', 'XRP', 'ADA', 'AVAX', 'DOGE', 'DOT', 'MATIC',
        'LTC', 'LINK', 'UNI', 'ATOM', 'ARB', 'OP', 'APT', 'SUI', 'INJ', 'TIA',
        'SEI', 'STX', 'FET', 'NEAR', 'GRT', 'RUNE', 'AAVE', 'MKR', 'SNX', 'CRV',
        'COMP', 'YFI', 'SUSHI', 'BAL', '1INCH', 'ENJ', 'SAND', 'MANA', 'AXS', 'IMX',
        'BLUR', 'LDO', 'RPL', 'FXS', 'CVX', 'DYDX', 'GMX', 'GNS', 'PERP', 'JOE'
    ]
    
    coins_data = []
    
    # Generate market caps following power law distribution (Zipf's law)
    # Large caps dominate, then exponential decline
    base_market_cap = 1_000_000_000_000  # $1T for #1 (BTC-like)
    
    for i in range(min(limit, len(common_symbols) * 2)):
        rank = i + 1
        
        # Power law for market cap
        market_cap = base_market_cap / (rank ** 1.5)
        
        # Add some randomness
        market_cap *= np.random.uniform(0.8, 1.2)
        
        # Price and volume correlated with market cap
        price = market_cap / np.random.uniform(100_000_000, 1_000_000_000)
        volume_24h = market_cap * np.random.uniform(0.05, 0.3)
        
        symbol = common_symbols[i] if i < len(common_symbols) else f"COIN{i+1}"
        
        coins_data.append({
            'symbol': symbol,
            'name': f"{symbol} Token",
            'cmc_rank': rank,
            'market_cap': market_cap,
            'price': price,
            'volume_24h': volume_24h,
            'percent_change_24h': np.random.uniform(-10, 10),
            'percent_change_7d': np.random.uniform(-20, 20),
            'market_cap_dominance': (market_cap / base_market_cap) * 100,
            'timestamp': datetime.now().isoformat()
        })
    
    df = pd.DataFrame(coins_data)
    print(f"Generated mock data for {len(df)} cryptocurrencies")
    return df


def save_marketcap_data(df, filepath='crypto_marketcap.csv'):
    """
    Save market cap data to CSV file.
    
    Args:
        df (pd.DataFrame): Market cap data
        filepath (str): Output file path
    """
    df.to_csv(filepath, index=False)
    print(f"\nMarket cap data saved to: {filepath}")
    
    # Print summary statistics
    print("\nMarket Cap Summary:")
    print(f"  Total cryptos: {len(df)}")
    print(f"  Total market cap: ${df['market_cap'].sum():,.0f}")
    
    if 'snapshot_date' not in df.columns:
        # Current snapshot data
        print(f"  Largest market cap: {df.iloc[0]['symbol']} - ${df.iloc[0]['market_cap']:,.0f}")
        print(f"  Smallest market cap: {df.iloc[-1]['symbol']} - ${df.iloc[-1]['market_cap']:,.0f}")
    else:
        # Historical data
        print(f"  Quarters: {df['quarter'].nunique()}")
        print(f"  Unique symbols: {df['symbol'].nunique()}")
        print(f"  Date range: {df['snapshot_date'].min()} to {df['snapshot_date'].max()}")
    
    print(f"  Median market cap: ${df['market_cap'].median():,.0f}")


def map_symbols_to_trading_pairs(marketcap_df, trading_suffix='/USDC:USDC'):
    """
    Map CoinMarketCap symbols to trading pair format used in CCXT.
    
    Args:
        marketcap_df (pd.DataFrame): Market cap data with 'symbol' column
        trading_suffix (str): Suffix to add for trading pairs (default for Hyperliquid)
        
    Returns:
        pd.DataFrame: Market cap data with additional 'trading_symbol' column
    """
    df = marketcap_df.copy()
    df['trading_symbol'] = df['symbol'] + trading_suffix
    return df


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Fetch Market Cap Data from CoinMarketCap',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='CoinMarketCap API key (or set CMC_API env var)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Number of cryptocurrencies to fetch'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='crypto_marketcap.csv',
        help='Output CSV file path'
    )
    parser.add_argument(
        '--historical',
        action='store_true',
        help='Fetch historical quarterly data instead of current snapshot'
    )
    parser.add_argument(
        '--start-year',
        type=int,
        default=2020,
        help='Start year for historical data (only used with --historical)'
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay in seconds between API calls for historical data'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("COINMARKETCAP DATA FETCH")
    print("=" * 80)
    
    if args.historical:
        # Fetch historical quarterly data
        print("\nMode: HISTORICAL QUARTERLY DATA")
        print(f"Fetching top {args.limit} coins per quarter from {args.start_year} onwards")
        print("Note: This requires a paid CoinMarketCap API plan\n")
        
        df = fetch_historical_top100_quarterly(
            api_key=args.api_key,
            start_year=args.start_year,
            limit=args.limit,
            delay_seconds=args.delay
        )
        
        if df is None:
            print("\n❌ Failed to fetch historical data")
            return
        
        # Display sample
        print("\nSample Data (first 20 rows):")
        display_cols = ['snapshot_date', 'quarter', 'cmc_rank', 'symbol', 'name', 'market_cap']
        print(df[display_cols].head(20).to_string(index=False))
        
    else:
        # Fetch current snapshot data
        print("\nMode: CURRENT SNAPSHOT")
        print(f"Fetching top {args.limit} cryptocurrencies by current market cap\n")
        
        df = fetch_coinmarketcap_data(api_key=args.api_key, limit=args.limit)
        
        # Add trading symbol mapping
        df = map_symbols_to_trading_pairs(df)
        
        # Display sample
        print("\nSample Data (first 10 rows):")
        display_cols = ['cmc_rank', 'symbol', 'name', 'market_cap', 'price', 'volume_24h']
        print(df[display_cols].head(10).to_string(index=False))
    
    # Save to file
    save_marketcap_data(df, args.output)
    
    print("\n" + "=" * 80)
    print("DATA FETCH COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
