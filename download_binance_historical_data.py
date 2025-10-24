"""
Download historical daily OHLCV data from Binance using ccxt.

This script fetches daily candle data for specified trading pairs from Binance
and saves them to CSV files for backtesting and analysis.
"""

import ccxt
from datetime import datetime, timedelta
import pandas as pd
import time
import os


def download_binance_daily_data(
    symbols=None,
    days=500,
    market_type='spot',
    output_file=None,
    rate_limit_pause=0.5,
    exchange_name='bybit'
):
    """
    Download historical daily OHLCV data from exchange.
    
    Args:
        symbols (list): List of trading pairs to fetch (e.g., ['BTC/USDT', 'ETH/USDT'])
                       If None, fetches top volume pairs
        days (int): Number of days of historical data to retrieve (default: 500)
        market_type (str): 'spot' or 'futures' (default: 'spot')
        output_file (str): Path to save CSV file. If None, auto-generates filename
        rate_limit_pause (float): Seconds to pause between requests (default: 0.5)
        exchange_name (str): Exchange to use ('binance', 'bybit', etc.)
    
    Returns:
        pd.DataFrame: DataFrame with columns: date, symbol, open, high, low, close, volume
    """
    
    # Initialize exchange
    if exchange_name == 'bybit':
        if market_type == 'futures':
            exchange = ccxt.bybit({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'linear',  # Use USDT perpetuals
                }
            })
            print("Connecting to Bybit Linear Futures...")
        else:
            exchange = ccxt.bybit({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                }
            })
            print("Connecting to Bybit Spot...")
    else:  # binance
        if market_type == 'futures':
            exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',  # Use perpetual futures
                }
            })
            print("Connecting to Binance Futures...")
        else:
            exchange = ccxt.binance({
                'enableRateLimit': True,
            })
            print("Connecting to Binance Spot...")
    
    # If no symbols provided, get top volume pairs
    if symbols is None:
        print("\nFetching top volume pairs...")
        symbols = get_top_binance_pairs(exchange, market_type=market_type, limit=20, exchange_name=exchange_name)
        print(f"Selected {len(symbols)} top volume pairs")
    
    # Calculate start timestamp
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    since = exchange.parse8601(start_date.isoformat())
    
    print(f"\nFetching data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    print(f"Total symbols: {len(symbols)}")
    print("=" * 80)
    
    all_data = []
    failed_symbols = []
    
    for idx, symbol in enumerate(symbols, 1):
        try:
            print(f"\n[{idx}/{len(symbols)}] Fetching {symbol}...")
            
            # Fetch OHLCV data in batches (Binance limit is 1000 candles per request)
            all_ohlcv = []
            current_since = since
            batch_count = 0
            
            while True:
                batch_count += 1
                ohlcv = exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe='1d',
                    since=current_since,
                    limit=1000  # Binance max limit
                )
                
                if not ohlcv:
                    break
                
                all_ohlcv.extend(ohlcv)
                
                # Check if we've reached the end
                last_timestamp = ohlcv[-1][0]
                if last_timestamp >= exchange.milliseconds() or len(ohlcv) < 1000:
                    break
                
                # Update since for next batch
                current_since = last_timestamp + 1
                
                # Rate limiting
                time.sleep(rate_limit_pause)
            
            if not all_ohlcv:
                print(f"  ⚠ No data available for {symbol}")
                failed_symbols.append(symbol)
                continue
            
            # Convert to DataFrame
            df = pd.DataFrame(
                all_ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # Convert timestamp to readable date
            df['date'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['symbol'] = symbol
            
            # Filter to requested date range
            df = df[df['date'] >= start_date]
            df = df[['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']]
            
            # Remove duplicates (keep last)
            df = df.drop_duplicates(subset=['date', 'symbol'], keep='last')
            
            all_data.append(df)
            
            print(f"  ✓ Downloaded {len(df)} days (fetched in {batch_count} batch(es))")
            print(f"    Date range: {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}")
            print(f"    Price range: ${df['low'].min():.2f} - ${df['high'].max():.2f}")
            print(f"    Avg volume: {df['volume'].mean():,.0f}")
            
        except Exception as e:
            print(f"  ✗ Error fetching {symbol}: {str(e)}")
            failed_symbols.append(symbol)
        
        # Rate limiting between symbols
        time.sleep(rate_limit_pause)
    
    # Combine all data
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        combined_df = combined_df.sort_values(['date', 'symbol']).reset_index(drop=True)
        
        # Save to CSV
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"{exchange_name}_{market_type}_daily_data_{days}d_{timestamp}.csv"
        
        combined_df.to_csv(output_file, index=False)
        
        print("\n" + "=" * 80)
        print("DOWNLOAD COMPLETE")
        print("=" * 80)
        print(f"\nSuccessfully downloaded data for {len(symbols) - len(failed_symbols)}/{len(symbols)} symbols")
        print(f"Total records: {len(combined_df):,}")
        print(f"Date range: {combined_df['date'].min()} to {combined_df['date'].max()}")
        print(f"Saved to: {output_file}")
        
        if failed_symbols:
            print(f"\n⚠ Failed symbols ({len(failed_symbols)}):")
            for symbol in failed_symbols:
                print(f"  - {symbol}")
        
        return combined_df
    else:
        print("\n" + "=" * 80)
        print("ERROR: No data was downloaded")
        print("=" * 80)
        return pd.DataFrame(columns=['date', 'symbol', 'open', 'high', 'low', 'close', 'volume'])


def get_top_binance_pairs(exchange, market_type='spot', limit=20, exchange_name='bybit'):
    """
    Get top trading pairs by volume from exchange.
    
    Args:
        exchange: ccxt exchange instance
        market_type (str): 'spot' or 'futures'
        limit (int): Number of top pairs to return
        exchange_name (str): Exchange name for filtering
    
    Returns:
        list: List of trading pair symbols
    """
    try:
        # Load markets
        exchange.load_markets()
        
        # Get tickers with 24h volume
        tickers = exchange.fetch_tickers()
        
        # Filter and sort by volume
        volume_data = []
        for symbol, ticker in tickers.items():
            # Filter based on market type and exchange
            if exchange_name == 'bybit':
                if market_type == 'spot':
                    # Bybit spot: filter for USDT pairs
                    if '/USDT' in symbol and ':' not in symbol:
                        volume_data.append({
                            'symbol': symbol,
                            'volume': ticker.get('quoteVolume', 0) or 0
                        })
                else:  # futures
                    # Bybit linear perpetuals: /USDT:USDT format
                    if '/USDT:USDT' in symbol:
                        volume_data.append({
                            'symbol': symbol,
                            'volume': ticker.get('quoteVolume', 0) or 0
                        })
            else:  # binance
                if market_type == 'spot':
                    # Spot markets: filter for USDT pairs, exclude futures
                    if '/USDT' in symbol and ':' not in symbol:
                        volume_data.append({
                            'symbol': symbol,
                            'volume': ticker.get('quoteVolume', 0) or 0
                        })
                else:  # futures
                    # Futures markets: filter for perpetual futures with USDT
                    if '/USDT:USDT' in symbol:
                        volume_data.append({
                            'symbol': symbol,
                            'volume': ticker.get('quoteVolume', 0) or 0
                        })
        
        # Sort by volume and get top pairs
        volume_df = pd.DataFrame(volume_data)
        volume_df = volume_df.sort_values('volume', ascending=False)
        top_pairs = volume_df.head(limit)['symbol'].tolist()
        
        return top_pairs
        
    except Exception as e:
        print(f"Error fetching top pairs: {str(e)}")
        # Return default pairs if error
        if market_type == 'futures':
            return ['BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT']
        else:
            return ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']


def download_specific_symbols(symbols, days=500, market_type='spot', output_file=None, exchange_name='bybit'):
    """
    Convenience function to download data for specific symbols.
    
    Args:
        symbols (list): List of trading pairs
        days (int): Number of days to download
        market_type (str): 'spot' or 'futures'
        output_file (str): Output CSV filename
        exchange_name (str): Exchange to use
    
    Returns:
        pd.DataFrame: Downloaded data
    """
    return download_binance_daily_data(
        symbols=symbols,
        days=days,
        market_type=market_type,
        output_file=output_file,
        exchange_name=exchange_name
    )


def download_top_volume_pairs(limit=20, days=500, market_type='spot', output_file=None, exchange_name='bybit'):
    """
    Convenience function to download top volume pairs.
    
    Args:
        limit (int): Number of top pairs to download
        days (int): Number of days to download
        market_type (str): 'spot' or 'futures'
        output_file (str): Output CSV filename
        exchange_name (str): Exchange to use
    
    Returns:
        pd.DataFrame: Downloaded data
    """
    # Fetch top pairs first to pass the limit
    exchange_cls = getattr(ccxt, exchange_name)
    if market_type == 'futures':
        exchange = exchange_cls({
            'enableRateLimit': True,
            'options': {'defaultType': 'linear' if exchange_name == 'bybit' else 'future'}
        })
    else:
        exchange = exchange_cls({'enableRateLimit': True})
    
    symbols = get_top_binance_pairs(exchange, market_type=market_type, limit=limit, exchange_name=exchange_name)
    
    return download_binance_daily_data(
        symbols=symbols,
        days=days,
        market_type=market_type,
        output_file=output_file,
        exchange_name=exchange_name
    )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Download historical daily data from crypto exchange',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--symbols',
        nargs='+',
        help='Specific symbols to download (e.g., BTC/USDT ETH/USDT). If not provided, downloads top volume pairs'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=500,
        help='Number of days of historical data to download'
    )
    parser.add_argument(
        '--market-type',
        choices=['spot', 'futures'],
        default='spot',
        help='Market type: spot or futures'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=20,
        help='Number of top volume pairs to download (only used if --symbols not provided)'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Output CSV filename (auto-generated if not provided)'
    )
    parser.add_argument(
        '--exchange',
        type=str,
        default='bybit',
        choices=['binance', 'bybit'],
        help='Exchange to use (default: bybit)'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print(f"{args.exchange.upper()} HISTORICAL DATA DOWNLOADER")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Exchange: {args.exchange}")
    print(f"  Market type: {args.market_type}")
    print(f"  Days: {args.days}")
    
    if args.symbols:
        print(f"  Symbols: {', '.join(args.symbols)}")
        df = download_specific_symbols(
            symbols=args.symbols,
            days=args.days,
            market_type=args.market_type,
            output_file=args.output,
            exchange_name=args.exchange
        )
    else:
        print(f"  Mode: Top {args.limit} volume pairs")
        df = download_top_volume_pairs(
            limit=args.limit,
            days=args.days,
            market_type=args.market_type,
            output_file=args.output,
            exchange_name=args.exchange
        )
    
    if not df.empty:
        print("\n" + "=" * 80)
        print("Sample of downloaded data:")
        print("=" * 80)
        print(df.head(10).to_string(index=False))
        print("\n" + df.tail(10).to_string(index=False))
