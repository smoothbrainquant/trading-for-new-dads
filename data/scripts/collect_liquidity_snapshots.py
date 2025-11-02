"""
Collect Historical Liquidity Snapshots

This script periodically collects orderbook liquidity data and saves snapshots
for historical analysis. This allows backtesting of liquidity-based factors
and orderbook imbalance signals.

Usage:
1. One-time snapshot: python collect_liquidity_snapshots.py --symbols BTC/USDC:USDC ETH/USDC:USDC
2. Continuous collection: python collect_liquidity_snapshots.py --interval 300 --duration 3600
3. Append to existing data: python collect_liquidity_snapshots.py --append

The collected data can be used to:
- Analyze liquid vs illiquid coins performance
- Backtest orderbook imbalance signals
- Study liquidity dynamics over time
- Calculate time-series of liquidity metrics
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional
import time
import os
import sys

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from signals.calc_liquidity_metrics import calculate_single_asset_metrics
from signals.calc_orderbook_imbalance_signals import calculate_imbalance_metrics


def collect_single_snapshot(
    symbols: List[str],
    exchange_name: str = "hyperliquid",
    orderbook_depth: int = 20,
    include_imbalance: bool = True,
    volatilities: Optional[dict] = None
) -> pd.DataFrame:
    """
    Collect a single snapshot of liquidity data for all symbols.
    
    Args:
        symbols: List of trading pairs
        exchange_name: Exchange to use
        orderbook_depth: Order book depth levels
        include_imbalance: Include orderbook imbalance metrics
        volatilities: Optional dict of symbol -> volatility
    
    Returns:
        DataFrame with liquidity metrics for this snapshot
    """
    # Initialize exchange
    if exchange_name == "hyperliquid":
        exchange = ccxt.hyperliquid({"enableRateLimit": True})
    else:
        exchange_class = getattr(ccxt, exchange_name)
        exchange = exchange_class({"enableRateLimit": True})
    
    exchange.load_markets()
    
    snapshot_data = []
    snapshot_time = datetime.now()
    
    for symbol in symbols:
        try:
            # Fetch order book and ticker
            orderbook = exchange.fetch_order_book(symbol, limit=orderbook_depth)
            ticker = exchange.fetch_ticker(symbol)
            
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                continue
            
            # Get volatility if available
            base_symbol = symbol.split('/')[0]
            volatility = volatilities.get(base_symbol, np.nan) if volatilities else np.nan
            
            # Calculate liquidity metrics
            metrics = calculate_single_asset_metrics(
                symbol=symbol,
                bids=bids,
                asks=asks,
                ticker=ticker,
                volatility=volatility,
                orderbook_depth=orderbook_depth
            )
            
            # Add imbalance metrics if requested
            if include_imbalance:
                imbalance = calculate_imbalance_metrics(
                    symbol=symbol,
                    bids=bids,
                    asks=asks,
                    ticker=ticker,
                    use_decay_weights=True,
                    imbalance_threshold=0.2
                )
                
                # Merge imbalance metrics (avoid duplicates)
                for key, value in imbalance.items():
                    if key not in metrics and key != 'symbol':
                        metrics[key] = value
            
            # Override timestamp with snapshot time for consistency
            metrics['timestamp'] = snapshot_time
            
            snapshot_data.append(metrics)
            
        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            continue
        
        # Small delay for rate limiting
        time.sleep(0.05)
    
    if not snapshot_data:
        return pd.DataFrame()
    
    df = pd.DataFrame(snapshot_data)
    return df


def collect_continuous_snapshots(
    symbols: List[str],
    exchange_name: str = "hyperliquid",
    interval_seconds: int = 300,
    duration_seconds: Optional[int] = None,
    output_file: str = "data/raw/liquidity_snapshots.csv",
    append: bool = True,
    orderbook_depth: int = 20,
    price_data_file: Optional[str] = None
) -> pd.DataFrame:
    """
    Collect liquidity snapshots at regular intervals.
    
    Args:
        symbols: List of trading pairs
        exchange_name: Exchange to use
        interval_seconds: Seconds between snapshots
        duration_seconds: Total duration to collect (None = run once)
        output_file: Where to save snapshots
        append: Append to existing file or overwrite
        orderbook_depth: Order book depth
        price_data_file: Optional price data for volatility calculation
    
    Returns:
        DataFrame with all collected snapshots
    """
    # Load volatilities if price data provided
    volatilities = None
    if price_data_file and os.path.exists(price_data_file):
        print(f"Loading price data from {price_data_file}...")
        from signals.calc_liquidity_metrics import calculate_realized_volatilities
        price_data = pd.read_csv(price_data_file)
        volatilities = calculate_realized_volatilities(price_data, window=30)
        print(f"Calculated volatilities for {len(volatilities)} symbols")
    
    # Load existing data if appending
    all_data = []
    if append and os.path.exists(output_file):
        print(f"Loading existing data from {output_file}...")
        existing_df = pd.read_csv(output_file)
        all_data.append(existing_df)
        print(f"Loaded {len(existing_df)} existing records")
    
    # Calculate number of iterations
    if duration_seconds:
        num_iterations = max(1, duration_seconds // interval_seconds)
    else:
        num_iterations = 1
    
    print(f"\n{'='*120}")
    print(f"LIQUIDITY SNAPSHOT COLLECTION")
    print(f"{'='*120}")
    print(f"Symbols: {len(symbols)}")
    print(f"Interval: {interval_seconds}s")
    print(f"Duration: {duration_seconds if duration_seconds else 'Single snapshot'}s")
    print(f"Output: {output_file}")
    print(f"{'='*120}\n")
    
    start_time = time.time()
    
    for iteration in range(num_iterations):
        iteration_start = time.time()
        
        print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Collecting snapshot {iteration + 1}/{num_iterations}...")
        
        # Collect snapshot
        snapshot_df = collect_single_snapshot(
            symbols=symbols,
            exchange_name=exchange_name,
            orderbook_depth=orderbook_depth,
            include_imbalance=True,
            volatilities=volatilities
        )
        
        if not snapshot_df.empty:
            all_data.append(snapshot_df)
            print(f"? Collected {len(snapshot_df)} records")
            
            # Save incrementally
            combined_df = pd.concat(all_data, ignore_index=True)
            combined_df.to_csv(output_file, index=False)
            print(f"? Saved to {output_file} (total: {len(combined_df)} records)")
        else:
            print("? No data collected in this snapshot")
        
        # Wait for next interval (if not last iteration)
        if iteration < num_iterations - 1:
            iteration_elapsed = time.time() - iteration_start
            sleep_time = max(0, interval_seconds - iteration_elapsed)
            
            if sleep_time > 0:
                print(f"Waiting {sleep_time:.1f}s until next snapshot...")
                time.sleep(sleep_time)
    
    total_elapsed = time.time() - start_time
    
    print(f"\n{'='*120}")
    print(f"COLLECTION COMPLETE")
    print(f"{'='*120}")
    print(f"Total snapshots: {num_iterations}")
    print(f"Total time: {total_elapsed:.1f}s")
    print(f"Records collected: {sum(len(df) for df in all_data if not df.empty)}")
    print(f"Output file: {output_file}")
    print(f"{'='*120}\n")
    
    if all_data:
        return pd.concat(all_data, ignore_index=True)
    else:
        return pd.DataFrame()


def analyze_snapshot_history(
    snapshot_file: str = "data/raw/liquidity_snapshots.csv"
) -> None:
    """
    Analyze historical liquidity snapshots.
    
    Args:
        snapshot_file: Path to snapshot data CSV
    """
    if not os.path.exists(snapshot_file):
        print(f"Snapshot file not found: {snapshot_file}")
        return
    
    print(f"Loading snapshot data from {snapshot_file}...")
    df = pd.read_csv(snapshot_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print(f"\n{'='*120}")
    print(f"LIQUIDITY SNAPSHOT ANALYSIS")
    print(f"{'='*120}\n")
    
    print(f"Total records: {len(df)}")
    print(f"Unique symbols: {df['symbol'].nunique()}")
    print(f"Unique timestamps: {df['timestamp'].nunique()}")
    print(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Duration: {df['timestamp'].max() - df['timestamp'].min()}")
    
    # Snapshot frequency
    timestamps = df['timestamp'].unique()
    if len(timestamps) > 1:
        timestamps_sorted = sorted(timestamps)
        intervals = [(timestamps_sorted[i+1] - timestamps_sorted[i]).total_seconds() 
                    for i in range(len(timestamps_sorted)-1)]
        avg_interval = np.mean(intervals)
        print(f"Average snapshot interval: {avg_interval:.1f}s")
    
    # Metrics availability
    print(f"\nMetrics Coverage:")
    key_metrics = ['spread_pct', 'orderbook_imbalance', 'depth_impact_1000', 
                   'spread_vol_adj', 'liquidity_score']
    for metric in key_metrics:
        if metric in df.columns:
            coverage = df[metric].notna().sum() / len(df) * 100
            print(f"  {metric:25s}: {coverage:>5.1f}%")
    
    # Top symbols by snapshot count
    print(f"\nTop 10 Symbols by Snapshot Count:")
    top_symbols = df['symbol'].value_counts().head(10)
    for symbol, count in top_symbols.items():
        print(f"  {symbol:20s}: {count:>4d} snapshots")
    
    # Liquidity statistics over time
    if 'spread_pct' in df.columns:
        print(f"\nSpread Statistics (all snapshots):")
        print(f"  Mean:   {df['spread_pct'].mean():.4f}%")
        print(f"  Median: {df['spread_pct'].median():.4f}%")
        print(f"  Std:    {df['spread_pct'].std():.4f}%")
    
    if 'orderbook_imbalance' in df.columns:
        print(f"\nOrderbook Imbalance Statistics:")
        print(f"  Mean:   {df['orderbook_imbalance'].mean():.4f}")
        print(f"  Median: {df['orderbook_imbalance'].median():.4f}")
        print(f"  Std:    {df['orderbook_imbalance'].std():.4f}")
    
    print(f"\n{'='*120}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Collect liquidity snapshots for historical analysis",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        help="List of symbols to track"
    )
    parser.add_argument(
        "--exchange",
        type=str,
        default="hyperliquid",
        help="Exchange name"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Seconds between snapshots (default: 5 minutes)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        help="Total duration in seconds (None = single snapshot)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/raw/liquidity_snapshots.csv",
        help="Output CSV file"
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing file instead of overwriting"
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=20,
        help="Order book depth levels"
    )
    parser.add_argument(
        "--price-data",
        type=str,
        help="Historical price data for volatility calculation"
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze existing snapshot data"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Track top 30 active markets"
    )
    
    args = parser.parse_args()
    
    # Analysis mode
    if args.analyze:
        analyze_snapshot_history(args.output)
        exit(0)
    
    # Determine symbols
    if args.all:
        exchange = ccxt.hyperliquid({"enableRateLimit": True})
        markets = exchange.load_markets()
        symbols = [
            symbol for symbol, market in markets.items()
            if market.get("active") and market.get("type") == "swap"
        ][:30]
        print(f"Tracking top {len(symbols)} active markets")
    elif args.symbols:
        symbols = args.symbols
    else:
        # Default to top coins
        symbols = [
            "BTC/USDC:USDC",
            "ETH/USDC:USDC",
            "SOL/USDC:USDC",
            "AVAX/USDC:USDC",
            "MATIC/USDC:USDC",
            "ARB/USDC:USDC",
            "OP/USDC:USDC",
            "DOGE/USDC:USDC",
            "XRP/USDC:USDC",
            "ADA/USDC:USDC",
        ]
        print(f"Using default symbols (top 10)")
    
    # Collect snapshots
    df = collect_continuous_snapshots(
        symbols=symbols,
        exchange_name=args.exchange,
        interval_seconds=args.interval,
        duration_seconds=args.duration,
        output_file=args.output,
        append=args.append,
        orderbook_depth=args.depth,
        price_data_file=args.price_data
    )
    
    if not df.empty:
        print(f"\n? Collection complete!")
        print(f"  Records: {len(df)}")
        print(f"  Symbols: {df['symbol'].nunique()}")
        print(f"  Snapshots: {df['timestamp'].nunique()}")
    else:
        print(f"\n? No data collected")
    
    print("\nDone!")
