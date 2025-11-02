"""
Calculate Liquidity Metrics Normalized by Volatility

This script calculates comprehensive liquidity metrics for cryptocurrencies
and normalizes them by their realized volatility to enable fair comparison
across assets with different price volatilities.

Metrics calculated:
1. Spread-based metrics (absolute, percentage, volatility-adjusted)
2. Depth-based metrics (order book liquidity at various depths)
3. Volume-based metrics (Amihud illiquidity measure)
4. Market impact estimates
5. Orderbook imbalance ratios

All metrics are normalized by 30-day realized volatility to compare
"liquid vs illiquid relative to their own volatility".
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple
import time


def calculate_liquidity_metrics(
    symbols: List[str],
    exchange_name: str = "hyperliquid",
    orderbook_depth: int = 20,
    price_data: Optional[pd.DataFrame] = None,
    volatility_window: int = 30
) -> pd.DataFrame:
    """
    Calculate comprehensive liquidity metrics for given symbols.
    
    Args:
        symbols: List of trading pairs
        exchange_name: Exchange to fetch data from
        orderbook_depth: Number of order book levels to fetch
        price_data: Optional DataFrame with historical prices for volatility calculation
                   Expected columns: date, symbol, close
        volatility_window: Rolling window for volatility calculation (days)
    
    Returns:
        DataFrame with liquidity metrics for each symbol
    """
    # Initialize exchange
    if exchange_name == "hyperliquid":
        exchange = ccxt.hyperliquid({"enableRateLimit": True})
    else:
        exchange_class = getattr(ccxt, exchange_name)
        exchange = exchange_class({"enableRateLimit": True})
    
    exchange.load_markets()
    
    # Calculate volatilities if price data provided
    volatilities = {}
    if price_data is not None:
        volatilities = calculate_realized_volatilities(price_data, window=volatility_window)
    
    metrics_list = []
    
    print(f"\n{'='*120}")
    print(f"CALCULATING LIQUIDITY METRICS (Depth: {orderbook_depth} levels)")
    print(f"{'='*120}\n")
    
    for symbol in symbols:
        try:
            # Fetch order book and ticker
            orderbook = exchange.fetch_order_book(symbol, limit=orderbook_depth)
            ticker = exchange.fetch_ticker(symbol)
            
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                print(f"{symbol:20s} | No order book data")
                continue
            
            # Get volatility for this symbol
            # Convert symbol format if needed (e.g., BTC/USDC:USDC -> BTC)
            base_symbol = symbol.split('/')[0]
            volatility = volatilities.get(base_symbol, np.nan)
            
            # Calculate all metrics
            metrics = calculate_single_asset_metrics(
                symbol=symbol,
                bids=bids,
                asks=asks,
                ticker=ticker,
                volatility=volatility,
                orderbook_depth=orderbook_depth
            )
            
            metrics_list.append(metrics)
            
            # Print summary
            print(f"{symbol:20s} | Spread: {metrics['spread_pct']:.4f}% | "
                  f"Vol-Adj Spread: {metrics['spread_vol_adj']:.4f} | "
                  f"OB Imbalance: {metrics['orderbook_imbalance']:.4f} | "
                  f"Depth $1k: {metrics['depth_impact_1000']:.4f}%")
            
        except Exception as e:
            print(f"{symbol:20s} | Error: {str(e)}")
            continue
        
        # Small delay to respect rate limits
        time.sleep(0.1)
    
    if not metrics_list:
        return pd.DataFrame()
    
    df = pd.DataFrame(metrics_list)
    return df


def calculate_single_asset_metrics(
    symbol: str,
    bids: List[List[float]],
    asks: List[List[float]],
    ticker: Dict,
    volatility: float,
    orderbook_depth: int
) -> Dict:
    """
    Calculate liquidity metrics for a single asset.
    
    Args:
        symbol: Trading pair symbol
        bids: List of [price, size] bid levels
        asks: List of [price, size] ask levels  
        ticker: Ticker data dictionary
        volatility: 30-day realized volatility (daily, not annualized)
        orderbook_depth: Number of levels in order book
    
    Returns:
        Dictionary of liquidity metrics
    """
    # Extract basic order book data
    best_bid_price = bids[0][0]
    best_bid_size = bids[0][1]
    best_ask_price = asks[0][0]
    best_ask_size = asks[0][1]
    
    mid_price = (best_bid_price + best_ask_price) / 2
    
    # 1. SPREAD METRICS
    spread_abs = best_ask_price - best_bid_price
    spread_pct = (spread_abs / mid_price * 100) if mid_price > 0 else np.nan
    
    # Volatility-adjusted spread (spread relative to daily volatility)
    # Higher value = more illiquid relative to volatility
    spread_vol_adj = (spread_pct / volatility) if not np.isnan(volatility) and volatility > 0 else np.nan
    
    # 2. DEPTH METRICS
    # Calculate total liquidity at each side
    total_bid_value = sum(price * size for price, size in bids)
    total_ask_value = sum(price * size for price, size in asks)
    total_bid_size = sum(size for _, size in bids)
    total_ask_size = sum(size for _, size in asks)
    
    # Average price at depth
    avg_bid_price = total_bid_value / total_bid_size if total_bid_size > 0 else 0
    avg_ask_price = total_ask_value / total_ask_size if total_ask_size > 0 else 0
    
    # 3. ORDERBOOK IMBALANCE
    # Positive = more bid liquidity, negative = more ask liquidity
    # Range: -1 to +1
    orderbook_imbalance = (total_bid_value - total_ask_value) / (total_bid_value + total_ask_value)
    
    # Size imbalance at top of book
    top_of_book_imbalance = (best_bid_size - best_ask_size) / (best_bid_size + best_ask_size)
    
    # 4. MARKET IMPACT ESTIMATES
    # Calculate cost to execute orders of different sizes
    depth_impact_100 = calculate_market_impact(bids, asks, mid_price, 100)
    depth_impact_1000 = calculate_market_impact(bids, asks, mid_price, 1000)
    depth_impact_5000 = calculate_market_impact(bids, asks, mid_price, 5000)
    depth_impact_10000 = calculate_market_impact(bids, asks, mid_price, 10000)
    
    # Volatility-adjusted market impact
    depth_impact_1000_vol_adj = (depth_impact_1000 / volatility) if not np.isnan(volatility) and volatility > 0 else np.nan
    
    # 5. LIQUIDITY QUALITY SCORE
    # Composite metric: lower is more liquid
    # Combines spread and depth (vol-adjusted)
    liquidity_score = spread_vol_adj + depth_impact_1000_vol_adj if not np.isnan(spread_vol_adj) and not np.isnan(depth_impact_1000_vol_adj) else np.nan
    
    # 6. RESILIENCE METRICS
    # How much price moves per $1000 of notional
    price_impact_per_1k = depth_impact_1000 * mid_price / 1000 if mid_price > 0 else np.nan
    
    # Depth beyond best bid/ask (% of total liquidity)
    deep_bid_pct = ((total_bid_value - best_bid_price * best_bid_size) / total_bid_value * 100) if total_bid_value > 0 else 0
    deep_ask_pct = ((total_ask_value - best_ask_price * best_ask_size) / total_ask_value * 100) if total_ask_value > 0 else 0
    
    # 7. AMIHUD ILLIQUIDITY (requires volume data)
    volume_24h = ticker.get('quoteVolume', ticker.get('baseVolume', 0))
    daily_return = ticker.get('percentage', 0) / 100  # Convert to decimal
    
    # Amihud illiquidity: |return| / volume (in millions)
    amihud = abs(daily_return) / (volume_24h / 1e6) if volume_24h > 0 else np.nan
    
    return {
        'symbol': symbol,
        'timestamp': datetime.now(),
        
        # Price data
        'mid_price': mid_price,
        'best_bid': best_bid_price,
        'best_ask': best_ask_price,
        'best_bid_size': best_bid_size,
        'best_ask_size': best_ask_size,
        
        # Spread metrics
        'spread_abs': spread_abs,
        'spread_pct': spread_pct,
        'spread_vol_adj': spread_vol_adj,  # KEY METRIC
        
        # Depth metrics
        'total_bid_liquidity': total_bid_value,
        'total_ask_liquidity': total_ask_value,
        'total_bid_size': total_bid_size,
        'total_ask_size': total_ask_size,
        'avg_bid_price': avg_bid_price,
        'avg_ask_price': avg_ask_price,
        
        # Imbalance metrics
        'orderbook_imbalance': orderbook_imbalance,  # KEY METRIC
        'top_of_book_imbalance': top_of_book_imbalance,  # KEY METRIC
        
        # Market impact (slippage %)
        'depth_impact_100': depth_impact_100,
        'depth_impact_1000': depth_impact_1000,
        'depth_impact_5000': depth_impact_5000,
        'depth_impact_10000': depth_impact_10000,
        'depth_impact_1000_vol_adj': depth_impact_1000_vol_adj,  # KEY METRIC
        
        # Composite scores
        'liquidity_score': liquidity_score,  # KEY METRIC (lower = more liquid)
        'price_impact_per_1k': price_impact_per_1k,
        
        # Resilience
        'deep_bid_pct': deep_bid_pct,
        'deep_ask_pct': deep_ask_pct,
        
        # Volume-based
        'volume_24h': volume_24h,
        'amihud_illiquidity': amihud,
        
        # Volatility
        'volatility_30d': volatility,
        
        # Meta
        'orderbook_depth_levels': len(bids),
    }


def calculate_market_impact(
    bids: List[List[float]],
    asks: List[List[float]],
    mid_price: float,
    notional_usd: float
) -> float:
    """
    Calculate market impact (slippage) for executing an order of given size.
    
    Args:
        bids: List of [price, size] bid levels
        asks: List of [price, size] ask levels
        mid_price: Current mid price
        notional_usd: Order size in USD
    
    Returns:
        Market impact as percentage of mid price
    """
    # For buy order, walk through asks
    # For simplicity, assume 50/50 buy/sell and average the impact
    
    buy_impact = calculate_side_impact(asks, mid_price, notional_usd, side='buy')
    sell_impact = calculate_side_impact(bids, mid_price, notional_usd, side='sell')
    
    # Average of both sides
    avg_impact = (buy_impact + sell_impact) / 2
    
    return avg_impact


def calculate_side_impact(
    levels: List[List[float]],
    mid_price: float,
    notional_usd: float,
    side: str
) -> float:
    """
    Calculate market impact for one side of the order book.
    
    Args:
        levels: Order book levels [price, size]
        mid_price: Current mid price
        notional_usd: Order size in USD
        side: 'buy' or 'sell'
    
    Returns:
        Market impact as percentage
    """
    remaining_notional = notional_usd
    total_filled_value = 0
    total_filled_size = 0
    
    for price, size in levels:
        if remaining_notional <= 0:
            break
        
        level_value = price * size
        fill_value = min(level_value, remaining_notional)
        fill_size = fill_value / price
        
        total_filled_value += fill_value
        total_filled_size += fill_size
        remaining_notional -= fill_value
    
    if total_filled_size == 0:
        return np.nan  # Not enough liquidity
    
    # Average execution price
    avg_execution_price = total_filled_value / total_filled_size
    
    # Impact as percentage of mid price
    if side == 'buy':
        impact_pct = (avg_execution_price - mid_price) / mid_price * 100
    else:  # sell
        impact_pct = (mid_price - avg_execution_price) / mid_price * 100
    
    return abs(impact_pct)


def calculate_realized_volatilities(
    price_data: pd.DataFrame,
    window: int = 30
) -> Dict[str, float]:
    """
    Calculate realized volatilities from historical price data.
    
    Args:
        price_data: DataFrame with columns: date, symbol, close
        window: Rolling window for volatility calculation
    
    Returns:
        Dictionary mapping symbol to latest volatility value
    """
    df = price_data.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date'])
    
    # Calculate daily returns
    df['return'] = df.groupby('symbol')['close'].pct_change()
    
    # Calculate rolling volatility (not annualized - daily vol)
    df['volatility'] = df.groupby('symbol')['return'].transform(
        lambda x: x.rolling(window=window, min_periods=window).std() * 100  # Convert to percentage
    )
    
    # Get latest volatility for each symbol
    latest_vol = df.groupby('symbol').tail(1).set_index('symbol')['volatility'].to_dict()
    
    return latest_vol


def classify_liquidity_regime(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classify each asset into liquidity regimes based on metrics.
    
    Args:
        df: DataFrame with liquidity metrics
    
    Returns:
        DataFrame with added liquidity_regime column
    """
    df = df.copy()
    
    # Define thresholds (these can be tuned)
    # Using percentiles for relative classification
    
    if 'liquidity_score' in df.columns and df['liquidity_score'].notna().sum() > 0:
        # Use liquidity score (lower is better)
        percentile_33 = df['liquidity_score'].quantile(0.33)
        percentile_67 = df['liquidity_score'].quantile(0.67)
        
        df['liquidity_regime'] = 'Medium'
        df.loc[df['liquidity_score'] <= percentile_33, 'liquidity_regime'] = 'Liquid'
        df.loc[df['liquidity_score'] >= percentile_67, 'liquidity_regime'] = 'Illiquid'
    else:
        # Fallback to spread-based classification
        percentile_33 = df['spread_pct'].quantile(0.33)
        percentile_67 = df['spread_pct'].quantile(0.67)
        
        df['liquidity_regime'] = 'Medium'
        df.loc[df['spread_pct'] <= percentile_33, 'liquidity_regime'] = 'Liquid'
        df.loc[df['spread_pct'] >= percentile_67, 'liquidity_regime'] = 'Illiquid'
    
    return df


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Calculate liquidity metrics normalized by volatility",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        help="List of symbols (e.g., BTC/USDC:USDC ETH/USDC:USDC)"
    )
    parser.add_argument(
        "--exchange",
        type=str,
        default="hyperliquid",
        help="Exchange name"
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=20,
        help="Order book depth levels to fetch"
    )
    parser.add_argument(
        "--price-data",
        type=str,
        help="Path to historical price data CSV for volatility calculation"
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="Save results to CSV file"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch for top 20 active markets"
    )
    
    args = parser.parse_args()
    
    print(f"{'='*120}")
    print(f"LIQUIDITY METRICS CALCULATOR (Volatility-Adjusted)")
    print(f"{'='*120}")
    
    # Load price data for volatility if provided
    price_data = None
    if args.price_data:
        print(f"\nLoading price data from {args.price_data}...")
        price_data = pd.read_csv(args.price_data)
        print(f"Loaded {len(price_data)} price records for {price_data['symbol'].nunique()} symbols")
    
    # Determine symbols
    if args.all:
        # Get top markets from exchange
        exchange = ccxt.hyperliquid({"enableRateLimit": True})
        markets = exchange.load_markets()
        symbols = [
            symbol for symbol, market in markets.items()
            if market.get("active") and market.get("type") == "swap"
        ][:20]
    elif args.symbols:
        symbols = args.symbols
    else:
        # Default symbols
        symbols = [
            "BTC/USDC:USDC",
            "ETH/USDC:USDC",
            "SOL/USDC:USDC",
            "MATIC/USDC:USDC",
            "DOGE/USDC:USDC",
        ]
        print(f"\nUsing default symbols: {', '.join(symbols)}")
    
    # Calculate metrics
    df = calculate_liquidity_metrics(
        symbols=symbols,
        exchange_name=args.exchange,
        orderbook_depth=args.depth,
        price_data=price_data
    )
    
    if df.empty:
        print("\nNo data collected. Exiting.")
        exit(1)
    
    # Classify liquidity regimes
    df = classify_liquidity_regime(df)
    
    # Print summary
    print(f"\n{'='*120}")
    print("LIQUIDITY SUMMARY")
    print(f"{'='*120}\n")
    
    print(f"Total instruments: {len(df)}")
    print(f"\nLiquidity Regime Distribution:")
    print(df['liquidity_regime'].value_counts())
    
    print(f"\nSpread Statistics:")
    print(f"  Average spread %: {df['spread_pct'].mean():.4f}%")
    print(f"  Median spread %:  {df['spread_pct'].median():.4f}%")
    
    if df['spread_vol_adj'].notna().sum() > 0:
        print(f"\nVolatility-Adjusted Spread:")
        print(f"  Average: {df['spread_vol_adj'].mean():.4f}")
        print(f"  Median:  {df['spread_vol_adj'].median():.4f}")
    
    print(f"\nOrderbook Imbalance:")
    print(f"  Average: {df['orderbook_imbalance'].mean():.4f}")
    print(f"  Median:  {df['orderbook_imbalance'].median():.4f}")
    
    print(f"\nMarket Impact ($1000 order):")
    print(f"  Average: {df['depth_impact_1000'].mean():.4f}%")
    print(f"  Median:  {df['depth_impact_1000'].median():.4f}%")
    
    # Top/bottom by liquidity score
    if df['liquidity_score'].notna().sum() > 0:
        print(f"\nMost Liquid (lowest liquidity score):")
        liquid_cols = ['symbol', 'spread_vol_adj', 'depth_impact_1000_vol_adj', 'liquidity_score', 'orderbook_imbalance']
        print(df.nsmallest(5, 'liquidity_score')[liquid_cols].to_string(index=False))
        
        print(f"\nLeast Liquid (highest liquidity score):")
        print(df.nlargest(5, 'liquidity_score')[liquid_cols].to_string(index=False))
    
    # Save to CSV
    if args.csv:
        df.to_csv(args.csv, index=False)
        print(f"\n? Results saved to {args.csv}")
    
    print("\nDone!")
