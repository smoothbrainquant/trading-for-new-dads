#!/usr/bin/env python3
"""
Fetch ALL Historical Funding Rates - Maximum Available Data
Fetches daily funding rates from 2019 to present for top 50 coins
"""
import pandas as pd
import os
from datetime import datetime, timedelta
from coinalyze_client import CoinalyzeClient
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_top_50_coins():
    """Load top 50 coins from latest CoinMarketCap snapshot"""
    logger.info("Loading CoinMarketCap data...")
    
    df = pd.read_csv('coinmarketcap_historical_all_snapshots.csv')
    latest_date = df['snapshot_date'].max()
    logger.info(f"Latest snapshot: {latest_date}")
    
    latest = df[df['snapshot_date'] == latest_date].copy()
    latest = latest.sort_values('Rank').head(50)
    
    logger.info(f"Found {len(latest)} coins in top 50")
    
    return latest[['Rank', 'Name', 'Symbol', 'Market Cap']].to_dict('records')


def find_perpetual_symbols(client, coin_symbols):
    """Map coin symbols to Coinalyze perpetual symbols"""
    logger.info("Fetching available perpetual markets from Coinalyze...")
    
    futures = client.get_future_markets()
    if not futures:
        logger.error("Failed to fetch futures markets")
        return {}
    
    logger.info(f"Found {len(futures)} perpetual markets")
    
    symbol_map = {}
    preferred_exchanges = ['A', '6', '3', '0', '2']  # Binance, Bybit, OKX, BitMEX, Deribit
    
    for coin_symbol in coin_symbols:
        matches = []
        
        for future in futures:
            if (future['base_asset'] == coin_symbol and 
                future['is_perpetual'] and
                future['quote_asset'] in ['USDT', 'USD', 'USDC']):
                matches.append(future)
        
        if matches:
            matches_sorted = sorted(
                matches,
                key=lambda x: (
                    preferred_exchanges.index(x['exchange']) 
                    if x['exchange'] in preferred_exchanges 
                    else 999
                )
            )
            
            best_match = matches_sorted[0]['symbol']
            symbol_map[coin_symbol] = best_match
            logger.info(f"  {coin_symbol} -> {best_match}")
        else:
            logger.warning(f"  {coin_symbol} -> No perpetual found")
    
    return symbol_map


def fetch_max_history_for_symbol(client, symbol, start_year=2019):
    """
    Fetch maximum available history for a single symbol
    Daily data is retained indefinitely, so we can go back to when perps started
    
    Args:
        client: CoinalyzeClient instance
        symbol: Coinalyze symbol (e.g., 'BTCUSDT_PERP.A')
        start_year: Year to start fetching from (default 2019 when most perps launched)
    
    Returns:
        List of data dictionaries
    """
    # Set date range: from start_year to present
    start_ts = int(datetime(start_year, 1, 1).timestamp())
    end_ts = int(datetime.now().timestamp())
    
    logger.info(f"  Fetching {symbol} from {datetime.fromtimestamp(start_ts).date()} to {datetime.fromtimestamp(end_ts).date()}")
    
    data_points = []
    
    try:
        result = client.get_funding_rate_history(
            symbols=symbol,
            interval='daily',  # Daily data has unlimited retention
            from_ts=start_ts,
            to_ts=end_ts
        )
        
        if result and len(result) > 0:
            history = result[0].get('history', [])
            
            if history:
                logger.info(f"  ✓ {symbol}: {len(history)} days of data")
                
                # Find actual date range
                first_date = datetime.fromtimestamp(history[0]['t']).date()
                last_date = datetime.fromtimestamp(history[-1]['t']).date()
                logger.info(f"    Data range: {first_date} to {last_date}")
                
                # Convert to our format
                for point in history:
                    data_points.append({
                        'symbol': symbol,
                        'timestamp': point['t'],
                        'date': datetime.fromtimestamp(point['t']).strftime('%Y-%m-%d'),
                        'funding_rate': point['c'],
                        'funding_rate_pct': point['c'] * 100,
                        'fr_open': point.get('o'),
                        'fr_high': point.get('h'),
                        'fr_low': point.get('l'),
                    })
            else:
                logger.warning(f"  ⚠ {symbol}: No data returned")
        else:
            logger.warning(f"  ⚠ {symbol}: Failed to fetch data")
            
    except Exception as e:
        logger.error(f"  ✗ {symbol}: Error - {e}")
    
    return data_points


def fetch_all_funding_rates_max_history(client, symbols, start_year=2019, max_retries=3):
    """
    Fetch maximum available history for all symbols
    Uses daily interval which has unlimited data retention
    
    Args:
        client: CoinalyzeClient instance
        symbols: List of Coinalyze symbols
        start_year: Year to start from (when perpetual futures launched)
        max_retries: Maximum retries per symbol
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"FETCHING MAXIMUM AVAILABLE HISTORY")
    logger.info(f"{'='*80}")
    logger.info(f"Start date: {start_year}-01-01")
    logger.info(f"End date: {datetime.now().date()}")
    logger.info(f"Total symbols: {len(symbols)}")
    logger.info(f"{'='*80}\n")
    
    all_data = []
    wait_time = 3  # seconds between requests
    
    for idx, symbol in enumerate(symbols, 1):
        logger.info(f"\n[{idx}/{len(symbols)}] Processing {symbol}")
        
        # Retry logic
        success = False
        retry_count = 0
        
        while not success and retry_count < max_retries:
            try:
                data = fetch_max_history_for_symbol(client, symbol, start_year)
                
                if data:
                    all_data.extend(data)
                    success = True
                else:
                    retry_count += 1
                    if retry_count < max_retries:
                        wait = 10 * retry_count
                        logger.warning(f"  Retrying in {wait}s (attempt {retry_count+1}/{max_retries})...")
                        time.sleep(wait)
                    
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    wait = 10 * retry_count
                    logger.warning(f"  Error: {e}, retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    logger.error(f"  Failed after {max_retries} attempts")
        
        # Rate limiting between symbols
        if idx < len(symbols):
            logger.info(f"  Waiting {wait_time}s before next symbol...")
            time.sleep(wait_time)
    
    return pd.DataFrame(all_data)


def main():
    print("="*80)
    print("FETCH ALL HISTORICAL FUNDING RATES - MAXIMUM AVAILABLE DATA")
    print("="*80)
    print("\nThis will fetch ALL daily funding rates from 2019 to present")
    print("Daily interval data is retained indefinitely by Coinalyze")
    print("="*80 + "\n")
    
    # Check for API key
    if not os.environ.get('COINALYZE_API'):
        logger.error("COINALYZE_API environment variable not set")
        return
    
    # Initialize client
    client = CoinalyzeClient()
    
    # Step 1: Get top 50 coins
    top_50 = get_top_50_coins()
    
    print("\nTop 50 Coins:")
    print("-" * 80)
    for coin in top_50[:10]:
        print(f"  {coin['Rank']:>2}. {coin['Name']:<30} ({coin['Symbol']})")
    print(f"  ... and {len(top_50) - 10} more")
    
    # Step 2: Map to Coinalyze symbols
    coin_symbols = [coin['Symbol'] for coin in top_50]
    symbol_map = find_perpetual_symbols(client, coin_symbols)
    
    print(f"\n{len(symbol_map)}/{len(coin_symbols)} coins have perpetual contracts available")
    
    if not symbol_map:
        logger.error("No symbols found to fetch")
        return
    
    # Step 3: Fetch ALL available history (from 2019)
    print("\n" + "="*80)
    print("Starting to fetch maximum historical data...")
    print("This may take 5-10 minutes depending on API rate limits")
    print("="*80 + "\n")
    
    start_time = time.time()
    
    coinalyze_symbols = list(symbol_map.values())
    funding_df = fetch_all_funding_rates_max_history(
        client, 
        coinalyze_symbols, 
        start_year=2019  # Most perpetuals launched 2019-2020
    )
    
    elapsed_time = time.time() - start_time
    
    if funding_df.empty:
        logger.error("No funding rate data retrieved")
        return
    
    # Step 4: Add coin info to results
    reverse_map = {v: k for k, v in symbol_map.items()}
    coin_info_map = {coin['Symbol']: coin for coin in top_50}
    
    funding_df['coin_symbol'] = funding_df['symbol'].apply(lambda x: reverse_map.get(x, ''))
    funding_df['coin_name'] = funding_df['coin_symbol'].apply(
        lambda x: coin_info_map[x]['Name'] if x in coin_info_map else ''
    )
    funding_df['rank'] = funding_df['coin_symbol'].apply(
        lambda x: coin_info_map[x]['Rank'] if x in coin_info_map else 999
    )
    
    # Reorder columns
    funding_df = funding_df[[
        'rank', 'coin_name', 'coin_symbol', 'symbol', 
        'date', 'timestamp', 'funding_rate', 'funding_rate_pct',
        'fr_open', 'fr_high', 'fr_low'
    ]].sort_values(['rank', 'date'])
    
    # Step 5: Save to CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'historical_funding_rates_top50_ALL_HISTORY_{timestamp}.csv'
    
    funding_df.to_csv(output_file, index=False)
    
    print("\n" + "="*80)
    print("RESULTS - COMPLETE HISTORICAL DATA")
    print("="*80)
    print(f"Execution time: {elapsed_time/60:.1f} minutes")
    print(f"Total data points: {len(funding_df):,}")
    print(f"Unique coins: {funding_df['coin_symbol'].nunique()}")
    print(f"Date range: {funding_df['date'].min()} to {funding_df['date'].max()}")
    print(f"Total days of data: {(pd.to_datetime(funding_df['date'].max()) - pd.to_datetime(funding_df['date'].min())).days}")
    print(f"\nOutput saved to: {output_file}")
    
    # Data availability summary
    print("\n" + "="*80)
    print("DATA AVAILABILITY BY COIN")
    print("="*80)
    
    availability = funding_df.groupby(['rank', 'coin_name', 'coin_symbol']).agg({
        'date': ['count', 'min', 'max']
    })
    
    availability.columns = ['Days', 'First Date', 'Last Date']
    availability = availability.reset_index()
    availability['Years'] = (
        (pd.to_datetime(availability['Last Date']) - pd.to_datetime(availability['First Date'])).dt.days / 365.25
    ).round(2)
    
    print(availability.to_string(index=False))
    
    # Save availability summary
    availability_file = f'funding_rates_data_availability_{timestamp}.csv'
    availability.to_csv(availability_file, index=False)
    print(f"\nAvailability summary saved to: {availability_file}")
    
    # Summary statistics
    print("\n" + "="*80)
    print("SUMMARY STATISTICS (ALL-TIME)")
    print("="*80)
    
    summary = funding_df.groupby(['rank', 'coin_name', 'coin_symbol']).agg({
        'funding_rate_pct': ['count', 'mean', 'std', 'min', 'max']
    }).round(4)
    
    summary.columns = ['_'.join(col).strip() for col in summary.columns.values]
    summary = summary.reset_index()
    summary.columns = ['Rank', 'Coin', 'Symbol', 'Data Points', 'Avg FR %', 'Std FR %', 'Min FR %', 'Max FR %']
    
    print(summary.head(20).to_string(index=False))
    
    # Save summary
    summary_file = f'historical_funding_rates_top50_ALL_HISTORY_summary_{timestamp}.csv'
    summary.to_csv(summary_file, index=False)
    print(f"\nSummary saved to: {summary_file}")
    
    # File size info
    file_size_mb = os.path.getsize(output_file) / (1024 * 1024)
    print(f"\nOutput file size: {file_size_mb:.2f} MB")
    
    print("\n" + "="*80)
    print("✅ COMPLETE - ALL AVAILABLE HISTORICAL DATA FETCHED!")
    print("="*80)
    print(f"\nYou now have {len(funding_df):,} data points spanning")
    print(f"{(pd.to_datetime(funding_df['date'].max()) - pd.to_datetime(funding_df['date'].min())).days} days")
    print(f"across {funding_df['coin_symbol'].nunique()} cryptocurrencies!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()
