"""
Backtest for Size Factor Strategy

This script backtests a size factor strategy that:
1. Fetches market cap data from CoinMarketCap
2. Ranks cryptocurrencies by market cap
3. Creates long/short portfolios based on size:
   - Long position: Small cap coins (bottom quintile)
   - Short position: Large cap coins (top quintile)
   - Or long-only small caps
4. Uses risk parity weighting within each size bucket
5. Rebalances periodically (daily, weekly, or monthly)
6. Tracks portfolio performance over time

Size factor hypothesis: Smaller cap coins may outperform larger caps due to higher growth potential,
though with higher volatility. This is analogous to the "small cap premium" in equity markets.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from signals.calc_vola import calculate_rolling_30d_volatility
from signals.calc_weights import calculate_weights
from data.scripts.fetch_coinmarketcap_data import fetch_coinmarketcap_data, fetch_mock_marketcap_data


def calculate_rolling_volatility_custom(data, window=30):
    """
    Calculate rolling volatility with custom window size.

    Args:
        data (pd.DataFrame): DataFrame with date, symbol, close columns
        window (int): Window size for volatility calculation

    Returns:
        pd.DataFrame: DataFrame with volatility_30d column
    """
    df = data.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

    # Calculate daily log returns
    df["daily_return"] = df.groupby("symbol")["close"].transform(lambda x: np.log(x / x.shift(1)))

    # Calculate rolling volatility (annualized)
    df["volatility_30d"] = df.groupby("symbol")["daily_return"].transform(
        lambda x: x.rolling(window=window, min_periods=window).std() * np.sqrt(365)
    )

    return df[["date", "symbol", "close", "daily_return", "volatility_30d"]]


def load_data(filepath):
    """
    Load historical OHLCV data from CSV file.

    Args:
        filepath (str): Path to CSV file with OHLCV data

    Returns:
        pd.DataFrame: DataFrame with date, symbol, open, high, low, close, volume
    """
    df = pd.read_csv(filepath)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    return df


def load_marketcap_data(filepath=None, api_key=None, limit=100):
    """
    Load or fetch market cap data.

    Args:
        filepath (str): Path to saved market cap CSV file (if available)
        api_key (str): CoinMarketCap API key (if fetching fresh data)
        limit (int): Number of cryptocurrencies to fetch

    Returns:
        pd.DataFrame: Market cap data with symbol, market_cap columns
    """
    if filepath:
        try:
            print(f"Loading market cap data from {filepath}...")
            df = pd.read_csv(filepath)
            print(f"Loaded market cap data for {len(df)} cryptocurrencies")
            return df
        except Exception as e:
            print(f"Error loading file: {e}")

    # Fetch fresh data if file not available
    print("Fetching fresh market cap data from CoinMarketCap...")
    df = fetch_coinmarketcap_data(api_key=api_key, limit=limit)
    return df


def normalize_symbol(symbol):
    """
    Normalize trading symbol to match market cap symbol.
    E.g., 'BTC/USDC:USDC' -> 'BTC'

    Args:
        symbol (str): Trading symbol

    Returns:
        str: Normalized symbol
    """
    # Extract base symbol (before '/')
    if "/" in symbol:
        return symbol.split("/")[0]
    return symbol


def assign_size_buckets(marketcap_df, num_buckets=5):
    """
    Assign cryptocurrencies to size buckets based on market cap.

    Args:
        marketcap_df (pd.DataFrame): Market cap data with 'symbol' and 'market_cap' columns
        num_buckets (int): Number of size buckets (default 5 for quintiles)

    Returns:
        pd.DataFrame: Market cap data with additional 'size_bucket' column (1=largest, num_buckets=smallest)
    """
    df = marketcap_df.copy()

    # Sort by market cap descending
    df = df.sort_values("market_cap", ascending=False).reset_index(drop=True)

    # Assign buckets (1 = largest cap, 5 = smallest cap)
    df["size_bucket"] = pd.qcut(
        df["market_cap"], q=num_buckets, labels=range(1, num_buckets + 1), duplicates="drop"
    )

    return df


def select_symbols_by_size(marketcap_df, strategy="long_small_short_large", available_symbols=None):
    """
    Select symbols based on size factor strategy.

    Args:
        marketcap_df (pd.DataFrame): Market cap data with size_bucket column
        strategy (str): Strategy type:
            - 'long_small_short_large': Long smallest quintile, short largest quintile
            - 'long_small': Long smallest quintile only
            - 'long_small_2_quintiles': Long bottom 2 quintiles
        available_symbols (list): List of symbols available for trading (filters selection)

    Returns:
        dict: Dictionary with 'long' and 'short' lists of symbols
    """
    if available_symbols:
        # Filter to only available symbols
        marketcap_df = marketcap_df[marketcap_df["symbol"].isin(available_symbols)]

    num_buckets = marketcap_df["size_bucket"].max()

    if strategy == "long_small_short_large":
        # Long smallest quintile (highest number), short largest quintile (1)
        long_symbols = marketcap_df[marketcap_df["size_bucket"] == num_buckets]["symbol"].tolist()
        short_symbols = marketcap_df[marketcap_df["size_bucket"] == 1]["symbol"].tolist()

    elif strategy == "long_small":
        # Long smallest quintile only
        long_symbols = marketcap_df[marketcap_df["size_bucket"] == num_buckets]["symbol"].tolist()
        short_symbols = []

    elif strategy == "long_small_2_quintiles":
        # Long bottom 2 quintiles
        long_symbols = marketcap_df[
            marketcap_df["size_bucket"].isin([num_buckets, num_buckets - 1])
        ]["symbol"].tolist()
        short_symbols = []

    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    return {"long": long_symbols, "short": short_symbols}


def calculate_portfolio_returns(weights, returns_df):
    """
    Calculate portfolio returns based on weights and individual asset returns.
    Handles both positive (long) and negative (short) weights.

    Args:
        weights (dict): Dictionary mapping symbols to portfolio weights (can be negative for shorts)
        returns_df (pd.DataFrame): DataFrame with symbol and daily_return columns

    Returns:
        float: Portfolio return for the period
    """
    if not weights or returns_df.empty:
        return 0.0

    portfolio_return = 0.0
    for symbol, weight in weights.items():
        symbol_return = returns_df[returns_df["symbol"] == symbol]["daily_return"].values
        if len(symbol_return) > 0 and not np.isnan(symbol_return[0]):
            portfolio_return += weight * symbol_return[0]

    return portfolio_return


def backtest(
    price_data,
    marketcap_data,
    strategy="long_small_short_large",
    num_buckets=5,
    volatility_window=30,
    rebalance_days=7,
    start_date=None,
    end_date=None,
    initial_capital=10000,
    leverage=1.0,
    long_allocation=0.5,
    short_allocation=0.5,
):
    """
    Run backtest for the size factor strategy.

    Args:
        price_data (pd.DataFrame): Historical OHLCV data
        marketcap_data (pd.DataFrame): Market cap data with symbol and market_cap columns
        strategy (str): Size factor strategy type
        num_buckets (int): Number of size buckets for ranking
        volatility_window (int): Window for volatility calculation
        rebalance_days (int): Rebalance every N days
        start_date (str): Start date for backtest (format: 'YYYY-MM-DD')
        end_date (str): End date for backtest (format: 'YYYY-MM-DD')
        initial_capital (float): Initial portfolio capital
        leverage (float): Leverage multiplier (default 1.0 for no leverage)
        long_allocation (float): Allocation to long side (default 0.5 = 50%)
        short_allocation (float): Allocation to short side (default 0.5 = 50%)

    Returns:
        dict: Dictionary containing backtest results
    """
    # Filter data by date range if specified
    if start_date:
        price_data = price_data[price_data["date"] >= pd.to_datetime(start_date)]
    if end_date:
        price_data = price_data[price_data["date"] <= pd.to_datetime(end_date)]

    # Normalize trading symbols to match market cap symbols
    price_data["base_symbol"] = price_data["symbol"].apply(normalize_symbol)

    # Get available trading symbols
    available_symbols = price_data["base_symbol"].unique().tolist()

    # Assign size buckets
    marketcap_with_buckets = assign_size_buckets(marketcap_data, num_buckets=num_buckets)

    print(f"\nSize Bucket Distribution:")
    for bucket in range(1, num_buckets + 1):
        bucket_df = marketcap_with_buckets[marketcap_with_buckets["size_bucket"] == bucket]
        if len(bucket_df) > 0:
            print(
                f"  Bucket {bucket} ({'Large' if bucket == 1 else 'Small' if bucket == num_buckets else 'Mid'}): "
                f"{len(bucket_df)} coins, "
                f"Market cap range: ${bucket_df['market_cap'].min():,.0f} - ${bucket_df['market_cap'].max():,.0f}"
            )

    # Select symbols based on strategy
    selected = select_symbols_by_size(marketcap_with_buckets, strategy, available_symbols)
    long_symbols_base = selected["long"]
    short_symbols_base = selected["short"]

    print(f"\nStrategy: {strategy}")
    print(f"  Long positions: {len(long_symbols_base)} coins")
    print(f"  Short positions: {len(short_symbols_base)} coins")

    # Get unique dates for rebalancing
    all_dates = sorted(price_data["date"].unique())

    # Need enough data for volatility calculation
    min_required_days = volatility_window + 10

    if len(all_dates) < min_required_days:
        raise ValueError(
            f"Insufficient data. Need at least {min_required_days} days, have {len(all_dates)}"
        )

    # Start backtest after minimum required period
    backtest_start_idx = volatility_window
    backtest_dates = all_dates[backtest_start_idx::rebalance_days]  # Rebalance every N days

    if len(backtest_dates) == 0:
        backtest_dates = [all_dates[-1]]

    print(f"\nBacktest Configuration:")
    print(f"  Period: {backtest_dates[0].date()} to {backtest_dates[-1].date()}")
    print(f"  Trading days: {len(backtest_dates)}")
    print(f"  Rebalance frequency: Every {rebalance_days} days")
    print(f"  Volatility window: {volatility_window}d")
    print(f"  Initial capital: ${initial_capital:,.2f}")
    print(f"  Leverage: {leverage}x")
    print(f"  Long allocation: {long_allocation:.1%}")
    print(f"  Short allocation: {short_allocation:.1%}")
    print("=" * 80)

    # Initialize tracking variables
    portfolio_values = []
    trades_history = []
    current_weights = {}
    current_capital = initial_capital
    last_rebalance_date = None

    # Calculate daily returns for all data
    data_with_returns = price_data.copy()
    data_with_returns["daily_return"] = data_with_returns.groupby("symbol")["close"].transform(
        lambda x: np.log(x / x.shift(1))
    )

    # Track daily (not just rebalance days) for portfolio value
    daily_tracking_dates = all_dates[backtest_start_idx:]

    for date_idx, current_date in enumerate(daily_tracking_dates):
        # Check if it's a rebalancing day
        is_rebalance_day = (
            last_rebalance_date is None
            or current_date in backtest_dates
            or (current_date - last_rebalance_date).days >= rebalance_days
        )

        if is_rebalance_day:
            # Get data up to current date
            historical_data = price_data[price_data["date"] <= current_date].copy()

            # Map trading symbols to base symbols for long/short selection
            long_symbols_trading = (
                historical_data[historical_data["base_symbol"].isin(long_symbols_base)]["symbol"]
                .unique()
                .tolist()
            )

            short_symbols_trading = (
                historical_data[historical_data["base_symbol"].isin(short_symbols_base)]["symbol"]
                .unique()
                .tolist()
            )

            all_active_symbols = long_symbols_trading + short_symbols_trading

            new_weights = {}

            if len(all_active_symbols) > 0:
                active_data = historical_data[historical_data["symbol"].isin(all_active_symbols)]

                try:
                    # Calculate volatility
                    volatility_df = calculate_rolling_volatility_custom(
                        active_data, window=volatility_window
                    )
                    latest_volatility = volatility_df[volatility_df["date"] == current_date]

                    # Separate volatilities for longs and shorts
                    long_volatilities = {}
                    short_volatilities = {}

                    for _, row in latest_volatility.iterrows():
                        if not pd.isna(row["volatility_30d"]) and row["volatility_30d"] > 0:
                            if row["symbol"] in long_symbols_trading:
                                long_volatilities[row["symbol"]] = row["volatility_30d"]
                            elif row["symbol"] in short_symbols_trading:
                                short_volatilities[row["symbol"]] = row["volatility_30d"]

                    # Calculate risk parity weights separately for longs and shorts
                    long_weights = calculate_weights(long_volatilities) if long_volatilities else {}
                    short_weights = (
                        calculate_weights(short_volatilities) if short_volatilities else {}
                    )

                    # Apply leverage and allocation
                    for symbol, weight in long_weights.items():
                        new_weights[symbol] = weight * long_allocation * leverage

                    for symbol, weight in short_weights.items():
                        new_weights[symbol] = -weight * short_allocation * leverage

                except Exception as e:
                    print(f"Error calculating volatility/weights on {current_date}: {e}")
                    new_weights = current_weights.copy()

            # Record trades when weights change
            if new_weights != current_weights:
                all_symbols = set(new_weights.keys()) | set(current_weights.keys())
                for symbol in all_symbols:
                    old_weight = current_weights.get(symbol, 0)
                    new_weight = new_weights.get(symbol, 0)
                    if abs(new_weight - old_weight) > 0.0001:
                        trades_history.append(
                            {
                                "date": current_date,
                                "symbol": symbol,
                                "old_weight": old_weight,
                                "new_weight": new_weight,
                                "weight_change": new_weight - old_weight,
                            }
                        )

            current_weights = new_weights.copy()
            last_rebalance_date = current_date

        # Calculate daily portfolio return based on current weights
        if date_idx > 0 and current_weights:
            current_returns = data_with_returns[data_with_returns["date"] == current_date]
            portfolio_return = calculate_portfolio_returns(current_weights, current_returns)
            current_capital = current_capital * np.exp(portfolio_return)

        # Record portfolio value daily
        long_exposure = sum(w for w in current_weights.values() if w > 0)
        short_exposure = abs(sum(w for w in current_weights.values() if w < 0))
        net_exposure = sum(current_weights.values())

        portfolio_values.append(
            {
                "date": current_date,
                "portfolio_value": current_capital,
                "num_long_positions": len([w for w in current_weights.values() if w > 0]),
                "num_short_positions": len([w for w in current_weights.values() if w < 0]),
                "long_exposure": long_exposure,
                "short_exposure": short_exposure,
                "net_exposure": net_exposure,
                "gross_exposure": long_exposure + short_exposure,
            }
        )

        # Progress update
        if (date_idx + 1) % 50 == 0 or date_idx == len(daily_tracking_dates) - 1:
            print(
                f"Progress: {date_idx+1}/{len(daily_tracking_dates)} days | "
                f"Date: {current_date.date()} | "
                f"Value: ${current_capital:,.2f} | "
                f"Long: {len([w for w in current_weights.values() if w > 0])} | "
                f"Short: {len([w for w in current_weights.values() if w < 0])}"
            )

    # Convert to DataFrames
    portfolio_df = pd.DataFrame(portfolio_values)
    trades_df = pd.DataFrame(trades_history)

    # Calculate performance metrics
    metrics = calculate_performance_metrics(portfolio_df, initial_capital)

    return {
        "portfolio_values": portfolio_df,
        "trades": trades_df,
        "metrics": metrics,
        "strategy_info": {
            "strategy": strategy,
            "num_buckets": num_buckets,
            "long_symbols": long_symbols_base,
            "short_symbols": short_symbols_base,
        },
    }


def calculate_performance_metrics(portfolio_df, initial_capital):
    """
    Calculate performance metrics for the backtest.

    Args:
        portfolio_df (pd.DataFrame): DataFrame with portfolio values over time
        initial_capital (float): Initial portfolio capital

    Returns:
        dict: Dictionary of performance metrics
    """
    # Calculate returns
    portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()
    portfolio_df["log_return"] = np.log(
        portfolio_df["portfolio_value"] / portfolio_df["portfolio_value"].shift(1)
    )

    # Total return
    final_value = portfolio_df["portfolio_value"].iloc[-1]
    total_return = (final_value - initial_capital) / initial_capital

    # Annualized return (assuming 365 trading days per year)
    num_days = len(portfolio_df)
    years = num_days / 365.25
    annualized_return = (final_value / initial_capital) ** (1 / years) - 1 if years > 0 else 0

    # Volatility (annualized)
    daily_returns = portfolio_df["log_return"].dropna()
    daily_vol = daily_returns.std()
    annualized_vol = daily_vol * np.sqrt(365)

    # Sharpe ratio (assuming 0% risk-free rate)
    sharpe_ratio = annualized_return / annualized_vol if annualized_vol > 0 else 0

    # Maximum drawdown
    cumulative_returns = (1 + portfolio_df["daily_return"].fillna(0)).cumprod()
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max
    max_drawdown = drawdown.min()

    # Win rate (percentage of positive days)
    positive_days = (daily_returns > 0).sum()
    total_trading_days = len(daily_returns)
    win_rate = positive_days / total_trading_days if total_trading_days > 0 else 0

    # Average positions
    avg_long_positions = portfolio_df["num_long_positions"].mean()
    avg_short_positions = portfolio_df["num_short_positions"].mean()
    avg_total_positions = avg_long_positions + avg_short_positions

    # Average exposures
    avg_long_exposure = portfolio_df["long_exposure"].mean()
    avg_short_exposure = portfolio_df["short_exposure"].mean()
    avg_net_exposure = portfolio_df["net_exposure"].mean()
    avg_gross_exposure = portfolio_df["gross_exposure"].mean()

    metrics = {
        "initial_capital": initial_capital,
        "final_value": final_value,
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_vol,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "num_days": num_days,
        "avg_long_positions": avg_long_positions,
        "avg_short_positions": avg_short_positions,
        "avg_total_positions": avg_total_positions,
        "avg_long_exposure": avg_long_exposure,
        "avg_short_exposure": avg_short_exposure,
        "avg_net_exposure": avg_net_exposure,
        "avg_gross_exposure": avg_gross_exposure,
    }

    return metrics


def print_results(results):
    """
    Print backtest results in a formatted manner.

    Args:
        results (dict): Dictionary containing backtest results
    """
    metrics = results["metrics"]
    strategy_info = results["strategy_info"]

    print("\n" + "=" * 80)
    print("SIZE FACTOR BACKTEST RESULTS")
    print("=" * 80)

    print(f"\nStrategy Information:")
    print(f"  Strategy: {strategy_info['strategy']}")
    print(f"  Size buckets: {strategy_info['num_buckets']}")
    print(
        f"  Long symbols ({len(strategy_info['long_symbols'])}): {', '.join(strategy_info['long_symbols'][:10])}"
        + (
            f" ... (+{len(strategy_info['long_symbols'])-10} more)"
            if len(strategy_info["long_symbols"]) > 10
            else ""
        )
    )
    print(
        f"  Short symbols ({len(strategy_info['short_symbols'])}): {', '.join(strategy_info['short_symbols'][:10])}"
        + (
            f" ... (+{len(strategy_info['short_symbols'])-10} more)"
            if len(strategy_info["short_symbols"]) > 10
            else ""
        )
    )

    print(f"\nPortfolio Performance:")
    print(f"  Initial Capital:        ${metrics['initial_capital']:>15,.2f}")
    print(f"  Final Value:            ${metrics['final_value']:>15,.2f}")
    print(f"  Total Return:           {metrics['total_return']:>15.2%}")
    print(f"  Annualized Return:      {metrics['annualized_return']:>15.2%}")

    print(f"\nRisk Metrics:")
    print(f"  Annualized Volatility:  {metrics['annualized_volatility']:>15.2%}")
    print(f"  Sharpe Ratio:           {metrics['sharpe_ratio']:>15.2f}")
    print(f"  Maximum Drawdown:       {metrics['max_drawdown']:>15.2%}")

    print(f"\nTrading Statistics:")
    print(f"  Win Rate:               {metrics['win_rate']:>15.2%}")
    print(f"  Trading Days:           {metrics['num_days']:>15,.0f}")
    print(f"  Avg Long Positions:     {metrics['avg_long_positions']:>15.1f}")
    print(f"  Avg Short Positions:    {metrics['avg_short_positions']:>15.1f}")
    print(f"  Avg Total Positions:    {metrics['avg_total_positions']:>15.1f}")

    print(f"\nExposure Statistics:")
    print(f"  Avg Long Exposure:      {metrics['avg_long_exposure']:>15.2%}")
    print(f"  Avg Short Exposure:     {metrics['avg_short_exposure']:>15.2%}")
    print(f"  Avg Net Exposure:       {metrics['avg_net_exposure']:>15.2%}")
    print(f"  Avg Gross Exposure:     {metrics['avg_gross_exposure']:>15.2%}")

    if not results["trades"].empty:
        print(f"  Total Rebalances:       {len(results['trades']):>15,.0f}")

    print("\n" + "=" * 80)

    # Show portfolio value over time (sample)
    portfolio_df = results["portfolio_values"]
    print("\nPortfolio Value Sample (first 10 days):")
    display_cols = [
        "date",
        "portfolio_value",
        "num_long_positions",
        "num_short_positions",
        "long_exposure",
        "short_exposure",
        "net_exposure",
    ]
    print(portfolio_df[display_cols].head(10).to_string(index=False))

    print("\nPortfolio Value Sample (last 10 days):")
    print(portfolio_df[display_cols].tail(10).to_string(index=False))


def save_results(results, output_prefix="backtest_size_factor"):
    """
    Save backtest results to CSV files.

    Args:
        results (dict): Dictionary containing backtest results
        output_prefix (str): Prefix for output filenames
    """
    # Save portfolio values
    portfolio_file = f"{output_prefix}_portfolio_values.csv"
    results["portfolio_values"].to_csv(portfolio_file, index=False)
    print(f"\nPortfolio values saved to: {portfolio_file}")

    # Save trades
    if not results["trades"].empty:
        trades_file = f"{output_prefix}_trades.csv"
        results["trades"].to_csv(trades_file, index=False)
        print(f"Trades history saved to: {trades_file}")

    # Save metrics
    metrics_file = f"{output_prefix}_metrics.csv"
    metrics_df = pd.DataFrame([results["metrics"]])
    metrics_df.to_csv(metrics_file, index=False)
    print(f"Performance metrics saved to: {metrics_file}")

    # Save strategy info
    strategy_file = f"{output_prefix}_strategy_info.csv"
    strategy_df = pd.DataFrame([results["strategy_info"]])
    strategy_df.to_csv(strategy_file, index=False)
    print(f"Strategy info saved to: {strategy_file}")


def main():
    """Main execution function for backtest."""
    parser = argparse.ArgumentParser(
        description="Backtest Size Factor Trading Strategy",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--price-data",
        type=str,
        default="top10_markets_100d_daily_data.csv",
        help="Path to historical OHLCV price data CSV file",
    )
    parser.add_argument(
        "--marketcap-file",
        type=str,
        default=None,
        help="Path to market cap data CSV file (if not provided, will fetch from API)",
    )
    parser.add_argument(
        "--cmc-api-key",
        type=str,
        default=None,
        help="CoinMarketCap API key (or set CMC_API env var)",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="long_small_short_large",
        choices=["long_small_short_large", "long_small", "long_small_2_quintiles"],
        help="Size factor strategy type",
    )
    parser.add_argument(
        "--num-buckets", type=int, default=5, help="Number of size buckets for ranking (quintiles)"
    )
    parser.add_argument(
        "--volatility-window", type=int, default=30, help="Volatility calculation window in days"
    )
    parser.add_argument("--rebalance-days", type=int, default=7, help="Rebalance every N days")
    parser.add_argument(
        "--initial-capital", type=float, default=10000, help="Initial portfolio capital in USD"
    )
    parser.add_argument(
        "--leverage", type=float, default=1.0, help="Leverage multiplier (1.0 = no leverage)"
    )
    parser.add_argument(
        "--long-allocation", type=float, default=0.5, help="Allocation to long side (0.5 = 50%%)"
    )
    parser.add_argument(
        "--short-allocation", type=float, default=0.5, help="Allocation to short side (0.5 = 50%%)"
    )
    parser.add_argument(
        "--start-date", type=str, default=None, help="Start date for backtest (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date", type=str, default=None, help="End date for backtest (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default="backtest_size_factor",
        help="Prefix for output CSV files",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("SIZE FACTOR BACKTEST")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Price data file: {args.price_data}")
    print(f"  Market cap file: {args.marketcap_file or 'Fetch from API'}")
    print(f"  Strategy: {args.strategy}")
    print(f"  Size buckets: {args.num_buckets}")
    print(f"  Volatility window: {args.volatility_window}d")
    print(f"  Rebalance frequency: Every {args.rebalance_days} days")
    print(f"  Initial capital: ${args.initial_capital:,.2f}")
    print(f"  Leverage: {args.leverage}x")
    print(f"  Long allocation: {args.long_allocation:.1%}")
    print(f"  Short allocation: {args.short_allocation:.1%}")
    print(f"  Start date: {args.start_date or 'First available'}")
    print(f"  End date: {args.end_date or 'Last available'}")
    print("=" * 80)

    # Load price data
    print("\nLoading price data...")
    price_data = load_data(args.price_data)
    print(f"Loaded {len(price_data)} rows for {price_data['symbol'].nunique()} symbols")
    print(f"Date range: {price_data['date'].min().date()} to {price_data['date'].max().date()}")

    # Load or fetch market cap data
    print("\nLoading market cap data...")
    marketcap_data = load_marketcap_data(
        filepath=args.marketcap_file, api_key=args.cmc_api_key, limit=100
    )
    print(f"Market cap data for {len(marketcap_data)} cryptocurrencies")

    # Run backtest
    print("\nRunning backtest...")
    results = backtest(
        price_data=price_data,
        marketcap_data=marketcap_data,
        strategy=args.strategy,
        num_buckets=args.num_buckets,
        volatility_window=args.volatility_window,
        rebalance_days=args.rebalance_days,
        initial_capital=args.initial_capital,
        leverage=args.leverage,
        long_allocation=args.long_allocation,
        short_allocation=args.short_allocation,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    # Print results
    print_results(results)

    # Save results
    save_results(results, output_prefix=args.output_prefix)

    print("\n" + "=" * 80)
    print("BACKTEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
