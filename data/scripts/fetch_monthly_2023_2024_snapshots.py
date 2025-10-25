"""
Fetch Monthly CoinMarketCap Historical Snapshots for 2023-2024

This script downloads monthly historical snapshot data from CoinMarketCap
for 2023 (Jan-Dec) and 2024 (Jan-Oct).
"""

import requests
import pandas as pd
import json
import re
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta


def fetch_historical_snapshot(date_str):
    """
    Fetch historical cryptocurrency data from CoinMarketCap snapshot page.
    
    Args:
        date_str (str): Date string in format YYYYMMDD (e.g., '20241101')
        
    Returns:
        pd.DataFrame: DataFrame with historical crypto data
    """
    url = f"https://coinmarketcap.com/historical/{date_str}/"
    
    print(f"\nFetching data from: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        html_content = response.text
        
        # Extract JSON data from __NEXT_DATA__ script tag
        match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html_content, re.DOTALL)
        
        if not match:
            print(f"ERROR: Could not find __NEXT_DATA__ in page")
            return None
        
        json_str = match.group(1)
        data = json.loads(json_str)
        
        # Navigate through the JSON structure to find the crypto data
        # Structure: props -> initialState (JSON string) -> cryptocurrency -> listingHistorical -> data
        try:
            # initialState is a JSON-encoded string, need to parse it
            initial_state_str = data['props']['initialState']
            initial_state = json.loads(initial_state_str)
            crypto_list = initial_state['cryptocurrency']['listingHistorical']['data']
        except (KeyError, json.JSONDecodeError) as e:
            print(f"ERROR: Could not find crypto data in JSON structure: {e}")
            print(f"Available keys: {data.keys()}")
            if 'props' in data:
                print(f"Props keys: {data['props'].keys()}")
            return None
        
        if not crypto_list:
            print(f"ERROR: No crypto data found")
            return None
        
        # Extract relevant fields from each cryptocurrency
        rows = []
        for crypto in crypto_list:
            # Get USD quote data
            usd_quote = crypto.get('quote', {}).get('USD', {})
            
            row = {
                'Rank': crypto.get('rank', crypto.get('cmcRank', '')),
                'Name': crypto.get('name', ''),
                'Symbol': crypto.get('symbol', ''),
                'Market Cap': usd_quote.get('marketCap', usd_quote.get('market_cap', 0)),
                'Price': usd_quote.get('price', 0),
                'Circulating Supply': crypto.get('circulatingSupply', crypto.get('circulating_supply', 0)),
                'Volume (24h)': usd_quote.get('volume24h', usd_quote.get('volume_24h', 0)),
                '% 1h': usd_quote.get('percentChange1h', usd_quote.get('percent_change_1h', 0)),
                '% 24h': usd_quote.get('percentChange24h', usd_quote.get('percent_change_24h', 0)),
                '% 7d': usd_quote.get('percentChange7d', usd_quote.get('percent_change_7d', 0)),
                'snapshot_date': date_str
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        print(f"Successfully fetched {len(df)} cryptocurrencies from {date_str}")
        
        return df
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR fetching data: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"ERROR parsing JSON: {e}")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


def save_snapshot_to_csv(df, date_str, output_dir='.'):
    """
    Save snapshot data to CSV file.
    
    Args:
        df (pd.DataFrame): Snapshot data
        date_str (str): Date string for filename
        output_dir (str): Output directory
    """
    if df is None or df.empty:
        print(f"No data to save for {date_str}")
        return
    
    filepath = f"{output_dir}/coinmarketcap_monthly_{date_str}.csv"
    df.to_csv(filepath, index=False)
    print(f"Saved to: {filepath}")
    print(f"  Rows: {len(df)}")
    print(f"  Columns: {', '.join(df.columns.tolist())}")
    print(f"  Top 5 by Market Cap:")
    for idx, row in df.head(5).iterrows():
        print(f"    {row['Rank']}. {row['Name']} ({row['Symbol']}) - ${row['Market Cap']:,.0f}")


def generate_monthly_dates_for_period(start_year, start_month, end_year, end_month):
    """
    Generate list of monthly snapshot dates for a specific period.
    
    Args:
        start_year (int): Starting year
        start_month (int): Starting month (1-12)
        end_year (int): Ending year
        end_month (int): Ending month (1-12)
        
    Returns:
        list: List of date strings in YYYYMMDD format
    """
    dates = []
    current_date = datetime(start_year, start_month, 1)
    end_date = datetime(end_year, end_month, 1)
    
    while current_date <= end_date:
        # Use the 1st of each month for consistency
        date_str = current_date.strftime('%Y%m01')
        dates.append(date_str)
        
        # Move to next month
        current_date = current_date + relativedelta(months=1)
    
    return dates


def main():
    """Main execution function."""
    print("=" * 80)
    print("COINMARKETCAP MONTHLY HISTORICAL SNAPSHOTS DOWNLOAD (2023-2024)")
    print("=" * 80)
    
    # Generate monthly dates for 2023 (Jan-Dec) and 2024 (Jan-Oct)
    print("\nGenerating monthly snapshots for:")
    print("  - 2023: January - December (12 months)")
    print("  - 2024: January - October (10 months)")
    
    snapshot_dates_2023 = generate_monthly_dates_for_period(2023, 1, 2023, 12)
    snapshot_dates_2024 = generate_monthly_dates_for_period(2024, 1, 2024, 10)
    
    snapshot_dates = snapshot_dates_2023 + snapshot_dates_2024
    
    print(f"\nTotal snapshot dates to fetch: {len(snapshot_dates)}")
    print("\n2023 Dates:")
    for date in snapshot_dates_2023:
        year = date[:4]
        month = date[4:6]
        dt = datetime.strptime(f"{year}{month}01", '%Y%m%d')
        print(f"  - {dt.strftime('%B %Y')} ({date})")
    
    print("\n2024 Dates:")
    for date in snapshot_dates_2024:
        year = date[:4]
        month = date[4:6]
        dt = datetime.strptime(f"{year}{month}01", '%Y%m%d')
        print(f"  - {dt.strftime('%B %Y')} ({date})")
    
    all_snapshots = []
    successful_dates = []
    failed_dates = []
    
    for date_str in snapshot_dates:
        # Fetch data
        df = fetch_historical_snapshot(date_str)
        
        if df is not None:
            # Save individual snapshot
            save_snapshot_to_csv(df, date_str)
            all_snapshots.append(df)
            successful_dates.append(date_str)
        else:
            failed_dates.append(date_str)
        
        # Be polite to the server - wait between requests
        print("Waiting 3 seconds before next request...")
        time.sleep(3)
    
    # Combine all snapshots into one file
    if all_snapshots:
        print("\n" + "=" * 80)
        print("COMBINING ALL MONTHLY SNAPSHOTS")
        print("=" * 80)
        
        combined_df = pd.concat(all_snapshots, ignore_index=True)
        combined_filepath = "coinmarketcap_monthly_2023_2024_snapshots.csv"
        combined_df.to_csv(combined_filepath, index=False)
        print(f"\nCombined data saved to: {combined_filepath}")
        print(f"  Total rows: {len(combined_df)}")
        print(f"  Snapshots: {len(all_snapshots)}")
        
        # Print summary by date
        print("\nSummary by snapshot date:")
        for date_str in successful_dates:
            date_df = combined_df[combined_df['snapshot_date'] == date_str]
            count = len(date_df)
            avg_mcap = date_df['Market Cap'].mean()
            total_mcap = date_df['Market Cap'].sum()
            
            # Parse date for display
            year = date_str[:4]
            month = date_str[4:6]
            dt = datetime.strptime(f"{year}{month}01", '%Y%m%d')
            
            print(f"  {dt.strftime('%B %Y'):15} ({date_str}): {count:4} cryptos, "
                  f"Total Market Cap: ${total_mcap/1e9:,.0f}B, "
                  f"Avg: ${avg_mcap/1e6:,.0f}M")
    
    # Report failures if any
    if failed_dates:
        print("\n" + "=" * 80)
        print("FAILED DOWNLOADS")
        print("=" * 80)
        print(f"The following {len(failed_dates)} snapshots could not be downloaded:")
        for date_str in failed_dates:
            year = date_str[:4]
            month = date_str[4:6]
            dt = datetime.strptime(f"{year}{month}01", '%Y%m%d')
            print(f"  - {dt.strftime('%B %Y')} ({date_str})")
    
    print("\n" + "=" * 80)
    print("DOWNLOAD COMPLETE")
    print("=" * 80)
    print(f"Successfully downloaded: {len(successful_dates)} of {len(snapshot_dates)} snapshots")
    print(f"\nIndividual monthly files are saved as: coinmarketcap_monthly_YYYYMM01.csv")
    print(f"Combined file saved as: coinmarketcap_monthly_2023_2024_snapshots.csv")


if __name__ == "__main__":
    main()
