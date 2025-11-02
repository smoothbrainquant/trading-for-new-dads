"""
Orderbook Imbalance Signal Generator

This script generates trading signals based on orderbook imbalance.
The theory is that orderbook imbalance can predict short-term price movements:
- Positive imbalance (more bids) -> bullish signal
- Negative imbalance (more asks) -> bearish signal

Multiple imbalance metrics are calculated:
1. Value-weighted imbalance (total bid/ask liquidity)
2. Top-of-book imbalance (best bid/ask sizes)
3. Multi-level imbalance (weighted by distance from mid)
4. Imbalance momentum (change in imbalance over time)
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Optional, Dict
import time


def calculate_orderbook_imbalance_signals(
    symbols: List[str],
    exchange_name: str = "hyperliquid",
    orderbook_depth: int = 10,
    imbalance_threshold: float = 0.2,
    use_decay_weights: bool = True
) -> pd.DataFrame:
    """
    Generate trading signals based on orderbook imbalance.
    
    Args:
        symbols: List of trading pairs
        exchange_name: Exchange to fetch data from
        orderbook_depth: Number of order book levels to analyze
        imbalance_threshold: Threshold for signal generation (0-1)
        use_decay_weights: Use exponentially decaying weights by depth
    
    Returns:
        DataFrame with imbalance metrics and signals
    """
    # Initialize exchange
    if exchange_name == "hyperliquid":
        exchange = ccxt.hyperliquid({"enableRateLimit": True})
    else:
        exchange_class = getattr(ccxt, exchange_name)
        exchange = exchange_class({"enableRateLimit": True})
    
    exchange.load_markets()
    
    signals_list = []
    
    print(f"\n{'='*120}")
    print(f"ORDERBOOK IMBALANCE SIGNAL GENERATOR")
    print(f"{'='*120}\n")
    print(f"Depth: {orderbook_depth} levels | Threshold: ?{imbalance_threshold} | Decay weights: {use_decay_weights}\n")
    
    for symbol in symbols:
        try:
            # Fetch order book
            orderbook = exchange.fetch_order_book(symbol, limit=orderbook_depth)
            ticker = exchange.fetch_ticker(symbol)
            
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            if not bids or not asks:
                print(f"{symbol:20s} | No order book data")
                continue
            
            # Calculate imbalance metrics
            signals = calculate_imbalance_metrics(
                symbol=symbol,
                bids=bids,
                asks=asks,
                ticker=ticker,
                use_decay_weights=use_decay_weights,
                imbalance_threshold=imbalance_threshold
            )
            
            signals_list.append(signals)
            
            # Print signal
            signal_str = {1: "LONG", 0: "NEUTRAL", -1: "SHORT"}[signals['signal']]
            print(f"{symbol:20s} | Imbalance: {signals['imbalance_weighted']:>7.3f} | "
                  f"TOB: {signals['top_of_book_imbalance']:>7.3f} | "
                  f"Signal: {signal_str:>7s} | "
                  f"Strength: {signals['signal_strength']:.3f}")
            
        except Exception as e:
            print(f"{symbol:20s} | Error: {str(e)}")
            continue
        
        time.sleep(0.1)
    
    if not signals_list:
        return pd.DataFrame()
    
    df = pd.DataFrame(signals_list)
    return df


def calculate_imbalance_metrics(
    symbol: str,
    bids: List[List[float]],
    asks: List[List[float]],
    ticker: Dict,
    use_decay_weights: bool = True,
    imbalance_threshold: float = 0.2
) -> Dict:
    """
    Calculate orderbook imbalance metrics and generate signal.
    
    Args:
        symbol: Trading pair
        bids: Order book bid levels
        asks: Order book ask levels
        ticker: Ticker data
        use_decay_weights: Apply exponential decay weights by depth
        imbalance_threshold: Signal threshold
    
    Returns:
        Dictionary with imbalance metrics and signals
    """
    best_bid = bids[0][0]
    best_ask = asks[0][0]
    mid_price = (best_bid + best_ask) / 2
    
    # 1. SIMPLE VALUE-WEIGHTED IMBALANCE
    # Total value on each side
    total_bid_value = sum(price * size for price, size in bids)
    total_ask_value = sum(price * size for price, size in asks)
    
    # Imbalance ratio: -1 (all asks) to +1 (all bids)
    imbalance_simple = (total_bid_value - total_ask_value) / (total_bid_value + total_ask_value)
    
    # 2. TOP-OF-BOOK IMBALANCE
    # Just the best bid/ask sizes
    best_bid_size = bids[0][1]
    best_ask_size = asks[0][1]
    top_of_book_imbalance = (best_bid_size - best_ask_size) / (best_bid_size + best_ask_size)
    
    # 3. DEPTH-WEIGHTED IMBALANCE
    # Levels closer to mid price get higher weight
    if use_decay_weights:
        weighted_bid_value = 0
        weighted_ask_value = 0
        
        for i, (price, size) in enumerate(bids):
            # Exponential decay: level 0 gets weight 1, level 1 gets 0.9, etc.
            weight = np.exp(-i * 0.1)
            weighted_bid_value += price * size * weight
        
        for i, (price, size) in enumerate(asks):
            weight = np.exp(-i * 0.1)
            weighted_ask_value += price * size * weight
        
        imbalance_weighted = (weighted_bid_value - weighted_ask_value) / (weighted_bid_value + weighted_ask_value)
    else:
        imbalance_weighted = imbalance_simple
    
    # 4. PRICE-DISTANCE WEIGHTED IMBALANCE
    # Weight by distance from mid price
    bid_pd_weighted = 0
    ask_pd_weighted = 0
    
    for price, size in bids:
        distance_pct = abs(price - mid_price) / mid_price
        weight = 1 / (1 + distance_pct * 100)  # Closer = higher weight
        bid_pd_weighted += price * size * weight
    
    for price, size in asks:
        distance_pct = abs(price - mid_price) / mid_price
        weight = 1 / (1 + distance_pct * 100)
        ask_pd_weighted += price * size * weight
    
    imbalance_price_distance = (bid_pd_weighted - ask_pd_weighted) / (bid_pd_weighted + ask_pd_weighted)
    
    # 5. SIZE-ONLY IMBALANCE (ignoring price)
    total_bid_size = sum(size for _, size in bids)
    total_ask_size = sum(size for _, size in asks)
    imbalance_size = (total_bid_size - total_ask_size) / (total_bid_size + total_ask_size)
    
    # 6. COMPOSITE IMBALANCE SCORE
    # Average of different imbalance measures
    composite_imbalance = np.mean([
        imbalance_weighted,
        top_of_book_imbalance,
        imbalance_price_distance,
        imbalance_size
    ])
    
    # 7. GENERATE SIGNAL
    # Primary signal based on weighted imbalance
    if imbalance_weighted > imbalance_threshold:
        signal = 1  # LONG (more bids than asks)
    elif imbalance_weighted < -imbalance_threshold:
        signal = -1  # SHORT (more asks than bids)
    else:
        signal = 0  # NEUTRAL
    
    # Signal strength (0-1)
    signal_strength = abs(imbalance_weighted)
    
    # 8. CONFIDENCE METRICS
    # How aligned are different imbalance measures?
    imbalance_values = [imbalance_weighted, top_of_book_imbalance, imbalance_price_distance, imbalance_size]
    imbalance_signs = [np.sign(x) for x in imbalance_values]
    
    # Agreement: percentage of measures with same sign as primary signal
    if signal != 0:
        agreement = sum(1 for s in imbalance_signs if s == signal) / len(imbalance_signs)
    else:
        agreement = 0.5  # Neutral
    
    # Consistency: standard deviation of imbalance measures (lower = more consistent)
    consistency = 1 - np.std(imbalance_values)  # Normalize so higher is better
    
    # 9. LIQUIDITY QUALITY
    # Average of bid/ask available liquidity
    avg_liquidity = (total_bid_value + total_ask_value) / 2
    
    # Spread
    spread_pct = (best_ask - best_bid) / mid_price * 100
    
    return {
        'symbol': symbol,
        'timestamp': datetime.now(),
        'mid_price': mid_price,
        
        # Imbalance metrics (range: -1 to +1)
        'imbalance_simple': imbalance_simple,
        'imbalance_weighted': imbalance_weighted,  # PRIMARY SIGNAL
        'imbalance_price_distance': imbalance_price_distance,
        'imbalance_size': imbalance_size,
        'top_of_book_imbalance': top_of_book_imbalance,
        'composite_imbalance': composite_imbalance,
        
        # Signal
        'signal': signal,  # -1, 0, or 1
        'signal_strength': signal_strength,  # 0 to 1
        'signal_agreement': agreement,  # 0 to 1
        'signal_consistency': consistency,  # 0 to 1
        
        # Context
        'total_bid_value': total_bid_value,
        'total_ask_value': total_ask_value,
        'avg_liquidity': avg_liquidity,
        'spread_pct': spread_pct,
        
        # Sizes
        'best_bid_size': best_bid_size,
        'best_ask_size': best_ask_size,
        'total_bid_size': total_bid_size,
        'total_ask_size': total_ask_size,
    }


def generate_portfolio_signals(
    df: pd.DataFrame,
    min_signal_strength: float = 0.3,
    min_liquidity: float = 10000
) -> pd.DataFrame:
    """
    Filter signals for portfolio construction.
    
    Args:
        df: DataFrame with imbalance signals
        min_signal_strength: Minimum signal strength to include
        min_liquidity: Minimum average liquidity (USD)
    
    Returns:
        Filtered DataFrame with tradeable signals
    """
    filtered = df[
        (df['signal'] != 0) &
        (df['signal_strength'] >= min_signal_strength) &
        (df['avg_liquidity'] >= min_liquidity)
    ].copy()
    
    return filtered


def display_signals_summary(df: pd.DataFrame):
    """Display summary of orderbook imbalance signals."""
    if df is None or df.empty:
        print("\nNo signals to display.")
        return
    
    print(f"\n{'='*120}")
    print("ORDERBOOK IMBALANCE SIGNALS SUMMARY")
    print(f"{'='*120}\n")
    
    print(f"Total Instruments: {len(df)}")
    
    # Signal distribution
    print(f"\nSignal Distribution:")
    signal_counts = df['signal'].value_counts().sort_index()
    signal_labels = {-1: 'SHORT', 0: 'NEUTRAL', 1: 'LONG'}
    for signal, count in signal_counts.items():
        label = signal_labels.get(signal, str(signal))
        pct = count / len(df) * 100
        print(f"  {label:>7s}: {count:>3d} ({pct:>5.1f}%)")
    
    # Average metrics by signal
    print(f"\nAverage Metrics by Signal:")
    signal_stats = df.groupby('signal').agg({
        'imbalance_weighted': 'mean',
        'signal_strength': 'mean',
        'signal_agreement': 'mean',
        'avg_liquidity': 'mean',
        'spread_pct': 'mean'
    }).round(4)
    print(signal_stats)
    
    # Strongest signals
    if (df['signal'] != 0).any():
        print(f"\nStrongest LONG Signals (top 5):")
        long_signals = df[df['signal'] == 1].nlargest(5, 'signal_strength')
        if not long_signals.empty:
            cols = ['symbol', 'imbalance_weighted', 'signal_strength', 'signal_agreement', 'spread_pct']
            print(long_signals[cols].to_string(index=False))
        
        print(f"\nStrongest SHORT Signals (top 5):")
        short_signals = df[df['signal'] == -1].nlargest(5, 'signal_strength')
        if not short_signals.empty:
            cols = ['symbol', 'imbalance_weighted', 'signal_strength', 'signal_agreement', 'spread_pct']
            print(short_signals[cols].to_string(index=False))
    
    # Imbalance distribution
    print(f"\nImbalance Distribution:")
    print(f"  Mean:   {df['imbalance_weighted'].mean():>7.3f}")
    print(f"  Median: {df['imbalance_weighted'].median():>7.3f}")
    print(f"  Std:    {df['imbalance_weighted'].std():>7.3f}")
    print(f"  Min:    {df['imbalance_weighted'].min():>7.3f}")
    print(f"  Max:    {df['imbalance_weighted'].max():>7.3f}")
    
    print(f"\n{'='*120}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Generate trading signals from orderbook imbalance",
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
        default=10,
        help="Order book depth levels"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.2,
        help="Imbalance threshold for signal generation"
    )
    parser.add_argument(
        "--no-decay-weights",
        action="store_true",
        help="Don't use exponential decay weights"
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="Save results to CSV"
    )
    parser.add_argument(
        "--portfolio-csv",
        type=str,
        help="Save filtered portfolio signals to CSV"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch for top 30 active markets"
    )
    
    args = parser.parse_args()
    
    print(f"{'='*120}")
    print(f"ORDERBOOK IMBALANCE SIGNAL GENERATOR")
    print(f"{'='*120}")
    
    # Determine symbols
    if args.all:
        exchange = ccxt.hyperliquid({"enableRateLimit": True})
        markets = exchange.load_markets()
        symbols = [
            symbol for symbol, market in markets.items()
            if market.get("active") and market.get("type") == "swap"
        ][:30]
        print(f"\nFetching signals for top {len(symbols)} active markets")
    elif args.symbols:
        symbols = args.symbols
    else:
        symbols = [
            "BTC/USDC:USDC",
            "ETH/USDC:USDC",
            "SOL/USDC:USDC",
            "AVAX/USDC:USDC",
            "MATIC/USDC:USDC",
        ]
        print(f"\nUsing default symbols: {', '.join(symbols)}")
    
    # Generate signals
    df = calculate_orderbook_imbalance_signals(
        symbols=symbols,
        exchange_name=args.exchange,
        orderbook_depth=args.depth,
        imbalance_threshold=args.threshold,
        use_decay_weights=not args.no_decay_weights
    )
    
    if df.empty:
        print("\nNo signals generated. Exiting.")
        exit(1)
    
    # Display summary
    display_signals_summary(df)
    
    # Generate portfolio signals
    portfolio_df = generate_portfolio_signals(df)
    
    if not portfolio_df.empty:
        print(f"Portfolio Signals (filtered for min strength & liquidity):")
        print(f"  Total tradeable signals: {len(portfolio_df)}")
        print(f"  LONG:  {(portfolio_df['signal'] == 1).sum()}")
        print(f"  SHORT: {(portfolio_df['signal'] == -1).sum()}")
    
    # Save results
    if args.csv:
        df.to_csv(args.csv, index=False)
        print(f"\n? All signals saved to {args.csv}")
    
    if args.portfolio_csv and not portfolio_df.empty:
        portfolio_df.to_csv(args.portfolio_csv, index=False)
        print(f"? Portfolio signals saved to {args.portfolio_csv}")
    
    print("\nDone!")
