"""
Backtest for Kurtosis Factor Strategy

This script backtests a kurtosis factor strategy that:
1. Calculates rolling kurtosis of daily returns for each cryptocurrency
2. Ranks cryptocurrencies by kurtosis values
3. Creates long/short portfolios based on kurtosis rankings:
   - Mean Reversion: Long low kurtosis (stable), Short high kurtosis (unstable)
   - Momentum: Long high kurtosis (volatile), Short low kurtosis (stable)
4. Uses risk parity weighting within each bucket
5. Rebalances periodically (daily, weekly, or monthly)
6. Tracks portfolio performance over time

Kurtosis hypothesis: Kurtosis measures tail-fatness of return distributions.
High kurtosis = fat tails, prone to extreme moves
Low kurtosis = thin tails, more stable returns
"""

import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../signals"))
from calc_vola import calculate_rolling_30d_volatility
from calc_weights import calculate_weights


def load_data(filepath):
    """
    Load historical OHLCV data from CSV file.

    Args:
        filepath (str): Path to CSV file with OHLCV data

    Returns:
        pd.DataFrame: DataFrame with date, symbol, close, volume, market_cap
    """
    df = pd.read_csv(filepath)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

    # Keep only relevant columns
    required_cols = ["date", "symbol", "close"]
    optional_cols = ["volume", "market_cap"]

    cols_to_keep = required_cols.copy()
    for col in optional_cols:
        if col in df.columns:
            cols_to_keep.append(col)

    df = df[cols_to_keep]
    return df


def calculate_rolling_kurtosis(data, window=30):
    """
    Calculate rolling kurtosis of daily returns.
    Uses Fisher's definition (excess kurtosis where normal distribution = 0).

    Args:
        data (pd.DataFrame): DataFrame with date, symbol, close columns
        window (int): Rolling window size for kurtosis calculation

    Returns:
        pd.DataFrame: DataFrame with kurtosis and supporting columns
    """
    df = data.copy()
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

    # Calculate daily log returns
    df["daily_return"] = df.groupby("symbol")["close"].transform(lambda x: np.log(x / x.shift(1)))

    # Calculate rolling kurtosis using scipy.stats.kurtosis (Fisher=True for excess kurtosis)
    def rolling_kurt(x):
        if len(x) < window or x.isna().all():
            return np.nan
        try:
            # Fisher=True: excess kurtosis (normal = 0, leptokurtic > 0, platykurtic < 0)
            # nan_policy='omit' to handle any NaN values
            return stats.kurtosis(x.dropna(), fisher=True, nan_policy="omit")
        except:
            return np.nan

    df["kurtosis"] = df.groupby("symbol")["daily_return"].transform(
        lambda x: x.rolling(window=window, min_periods=window).apply(rolling_kurt, raw=False)
    )

    # Also calculate mean and std of returns in window for context
    df["returns_mean_30d"] = df.groupby("symbol")["daily_return"].transform(
        lambda x: x.rolling(window=window, min_periods=window).mean()
    )

    df["returns_std_30d"] = df.groupby("symbol")["daily_return"].transform(
        lambda x: x.rolling(window=window, min_periods=window).std()
    )

    return df


def calculate_volatility(data, window=30):
    """
    Calculate rolling volatility (annualized).

    Args:
        data (pd.DataFrame): DataFrame with daily_return column
        window (int): Rolling window size

    Returns:
        pd.DataFrame: DataFrame with volatility column
    """
    df = data.copy()

    # Calculate annualized volatility
    df["volatility"] = df.groupby("symbol")["daily_return"].transform(
        lambda x: x.rolling(window=window, min_periods=window).std() * np.sqrt(365)
    )

    return df


def filter_universe(data, min_volume=5_000_000, min_market_cap=50_000_000):
    """
    Filter cryptocurrency universe by liquidity and market cap.

    Args:
        data (pd.DataFrame): DataFrame with volume and market_cap columns
        min_volume (float): Minimum 30-day average daily volume
        min_market_cap (float): Minimum market cap

    Returns:
        pd.DataFrame: Filtered data
    """
    df = data.copy()

    # Calculate 30-day rolling average volume
    if "volume" in df.columns:
        df["volume_30d_avg"] = df.groupby("symbol")["volume"].transform(
            lambda x: x.rolling(window=30, min_periods=20).mean()
        )
        df = df[df["volume_30d_avg"] >= min_volume]

    # Filter by market cap
    if "market_cap" in df.columns:
        df = df[df["market_cap"] >= min_market_cap]

    return df


def rank_by_kurtosis(data, current_date):
    """
    Rank symbols by kurtosis on a given date.

    Args:
        data (pd.DataFrame): DataFrame with kurtosis values
        current_date (pd.Timestamp): Date to rank on

    Returns:
        pd.DataFrame: Ranked data for the date
    """
    date_data = data[data["date"] == current_date].copy()

    # Remove rows with missing kurtosis
    date_data = date_data.dropna(subset=["kurtosis"])

    if len(date_data) == 0:
        return pd.DataFrame()

    # Rank by kurtosis (1 = lowest kurtosis, N = highest kurtosis)
    date_data["kurtosis_rank"] = date_data["kurtosis"].rank(method="average")
    date_data["kurtosis_percentile"] = date_data["kurtosis_rank"] / len(date_data) * 100

    return date_data


def select_symbols_by_kurtosis(
    ranked_data,
    strategy="mean_reversion",
    long_percentile=20,
    short_percentile=80,
    max_positions=10,
):
    """
    Select symbols for long/short based on kurtosis rankings.

    Args:
        ranked_data (pd.DataFrame): Ranked data with kurtosis_percentile column
        strategy (str): Strategy type:
            - 'mean_reversion': Long low kurtosis, Short high kurtosis
            - 'momentum': Long high kurtosis, Short low kurtosis
            - 'long_only_stable': Long low kurtosis only
            - 'long_only_volatile': Long high kurtosis only
        long_percentile (float): Percentile threshold for long positions
        short_percentile (float): Percentile threshold for short positions
        max_positions (int): Maximum positions per side

    Returns:
        dict: Dictionary with 'long' and 'short' DataFrames
    """
    if ranked_data.empty:
        return {"long": pd.DataFrame(), "short": pd.DataFrame()}

    if strategy == "mean_reversion":
        # Long: Low kurtosis (stable coins)
        long_data = ranked_data[ranked_data["kurtosis_percentile"] <= long_percentile]
        # Short: High kurtosis (volatile coins)
        short_data = ranked_data[ranked_data["kurtosis_percentile"] >= short_percentile]

    elif strategy == "momentum":
        # Long: High kurtosis (volatile coins)
        long_data = ranked_data[ranked_data["kurtosis_percentile"] >= short_percentile]
        # Short: Low kurtosis (stable coins)
        short_data = ranked_data[ranked_data["kurtosis_percentile"] <= long_percentile]

    elif strategy == "long_only_stable":
        # Long: Low kurtosis only
        long_data = ranked_data[ranked_data["kurtosis_percentile"] <= long_percentile]
        short_data = pd.DataFrame()

    elif strategy == "long_only_volatile":
        # Long: High kurtosis only
        long_data = ranked_data[ranked_data["kurtosis_percentile"] >= short_percentile]
        short_data = pd.DataFrame()

    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    # Limit number of positions
    if len(long_data) > max_positions:
        # For mean reversion: take lowest kurtosis
        # For momentum: take highest kurtosis
        if strategy in ["mean_reversion", "long_only_stable"]:
            long_data = long_data.nsmallest(max_positions, "kurtosis")
        else:
            long_data = long_data.nlargest(max_positions, "kurtosis")

    if len(short_data) > max_positions:
        # For mean reversion: take highest kurtosis
        # For momentum: take lowest kurtosis
        if strategy == "mean_reversion":
            short_data = short_data.nlargest(max_positions, "kurtosis")
        else:
            short_data = short_data.nsmallest(max_positions, "kurtosis")

    return {"long": long_data, "short": short_data}


def calculate_portfolio_returns(weights, returns_df):
    """
    Calculate portfolio returns based on weights and individual asset returns.

    Args:
        weights (dict): Dictionary mapping symbols to portfolio weights
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
    strategy="mean_reversion",
    kurtosis_window=30,
    volatility_window=30,
    rebalance_days=1,
    long_percentile=20,
    short_percentile=80,
    max_positions=10,
    weighting="risk_parity",
    start_date=None,
    end_date=None,
    initial_capital=10000,
    leverage=1.0,
    long_allocation=0.5,
    short_allocation=0.5,
    min_volume=5_000_000,
    min_market_cap=50_000_000,
):
    """
    Run backtest for the kurtosis factor strategy.

    Args:
        price_data (pd.DataFrame): Historical OHLCV data
        strategy (str): Strategy type ('mean_reversion' or 'momentum')
        kurtosis_window (int): Window for kurtosis calculation
        volatility_window (int): Window for volatility calculation
        rebalance_days (int): Rebalance every N days
        long_percentile (float): Percentile threshold for long positions
        short_percentile (float): Percentile threshold for short positions
        max_positions (int): Maximum positions per side
        weighting (str): Weighting method ('risk_parity' or 'equal_weight')
        start_date (str): Start date for backtest
        end_date (str): End date for backtest
        initial_capital (float): Initial portfolio capital
        leverage (float): Leverage multiplier
        long_allocation (float): Allocation to long side
        short_allocation (float): Allocation to short side
        min_volume (float): Minimum volume filter
        min_market_cap (float): Minimum market cap filter

    Returns:
        dict: Dictionary containing backtest results
    """
    print("\nStep 1: Calculating returns and kurtosis...")
    data_with_kurtosis = calculate_rolling_kurtosis(price_data, window=kurtosis_window)

    print("Step 2: Calculating volatility...")
    data_with_volatility = calculate_volatility(data_with_kurtosis, window=volatility_window)

    print("Step 3: Filtering universe by liquidity and market cap...")
    # Note: Filtering disabled if columns not available
    if "volume" in data_with_volatility.columns or "market_cap" in data_with_volatility.columns:
        filtered_data = filter_universe(data_with_volatility, min_volume, min_market_cap)
        print(
            f"  Filtered from {data_with_volatility['symbol'].nunique()} to {filtered_data['symbol'].nunique()} symbols"
        )
    else:
        filtered_data = data_with_volatility
        print(f"  Skipping filtering (volume/market_cap not available)")

    # Filter by date range
    if start_date:
        filtered_data = filtered_data[filtered_data["date"] >= pd.to_datetime(start_date)]
    if end_date:
        filtered_data = filtered_data[filtered_data["date"] <= pd.to_datetime(end_date)]

    # Get unique dates
    all_dates = sorted(filtered_data["date"].unique())

    # Need enough data for kurtosis calculation
    min_required_days = max(kurtosis_window, volatility_window) + 10

    if len(all_dates) < min_required_days:
        raise ValueError(
            f"Insufficient data. Need at least {min_required_days} days, have {len(all_dates)}"
        )

    # Start backtest after minimum required period
    backtest_start_idx = max(kurtosis_window, volatility_window)
    backtest_dates = all_dates[backtest_start_idx::rebalance_days]

    if len(backtest_dates) == 0:
        backtest_dates = [all_dates[-1]]

    print(f"\nBacktest Configuration:")
    print(f"  Strategy: {strategy}")
    print(f"  Period: {backtest_dates[0].date()} to {backtest_dates[-1].date()}")
    print(f"  Trading days: {len(backtest_dates)}")
    print(f"  Rebalance frequency: Every {rebalance_days} days")
    print(f"  Kurtosis window: {kurtosis_window}d")
    print(f"  Volatility window: {volatility_window}d")
    print(f"  Long percentile: {long_percentile}%")
    print(f"  Short percentile: {short_percentile}%")
    print(f"  Max positions per side: {max_positions}")
    print(f"  Weighting method: {weighting}")
    print(f"  Initial capital: ${initial_capital:,.2f}")
    print(f"  Leverage: {leverage}x")
    print(f"  Long allocation: {long_allocation:.1%}")
    print(f"  Short allocation: {short_allocation:.1%}")
    print("=" * 80)

    # Initialize tracking
    portfolio_values = []
    trades_history = []
    kurtosis_timeseries = []
    current_weights = {}
    current_capital = initial_capital
    last_rebalance_date = None

    # Track daily portfolio value
    daily_tracking_dates = all_dates[backtest_start_idx:]

    for date_idx, current_date in enumerate(daily_tracking_dates):
        # Check if it's a rebalancing day
        is_rebalance_day = (
            last_rebalance_date is None
            or current_date in backtest_dates
            or (current_date - last_rebalance_date).days >= rebalance_days
        )

        if is_rebalance_day:
            # Get data up to current date (no lookahead)
            historical_data = filtered_data[filtered_data["date"] <= current_date].copy()

            # Rank by kurtosis
            ranked_data = rank_by_kurtosis(historical_data, current_date)

            if not ranked_data.empty:
                # Select long/short symbols
                selected = select_symbols_by_kurtosis(
                    ranked_data,
                    strategy=strategy,
                    long_percentile=long_percentile,
                    short_percentile=short_percentile,
                    max_positions=max_positions,
                )

                long_symbols = (
                    selected["long"]["symbol"].tolist() if not selected["long"].empty else []
                )
                short_symbols = (
                    selected["short"]["symbol"].tolist() if not selected["short"].empty else []
                )

                # Save kurtosis data for analysis
                for _, row in selected["long"].iterrows():
                    kurtosis_timeseries.append(
                        {
                            "date": current_date,
                            "symbol": row["symbol"],
                            "signal": "LONG",
                            "kurtosis": row["kurtosis"],
                            "kurtosis_rank": row["kurtosis_rank"],
                            "kurtosis_percentile": row["kurtosis_percentile"],
                            "returns_mean_30d": row.get("returns_mean_30d", np.nan),
                            "returns_std_30d": row.get("returns_std_30d", np.nan),
                        }
                    )

                for _, row in selected["short"].iterrows():
                    kurtosis_timeseries.append(
                        {
                            "date": current_date,
                            "symbol": row["symbol"],
                            "signal": "SHORT",
                            "kurtosis": row["kurtosis"],
                            "kurtosis_rank": row["kurtosis_rank"],
                            "kurtosis_percentile": row["kurtosis_percentile"],
                            "returns_mean_30d": row.get("returns_mean_30d", np.nan),
                            "returns_std_30d": row.get("returns_std_30d", np.nan),
                        }
                    )

                # Calculate weights
                new_weights = {}

                if weighting == "risk_parity" and len(long_symbols + short_symbols) > 0:
                    # Get volatilities for longs and shorts
                    long_vols = {}
                    short_vols = {}

                    for symbol in long_symbols:
                        vol = ranked_data[ranked_data["symbol"] == symbol]["volatility"].values
                        if len(vol) > 0 and not np.isnan(vol[0]) and vol[0] > 0:
                            long_vols[symbol] = vol[0]

                    for symbol in short_symbols:
                        vol = ranked_data[ranked_data["symbol"] == symbol]["volatility"].values
                        if len(vol) > 0 and not np.isnan(vol[0]) and vol[0] > 0:
                            short_vols[symbol] = vol[0]

                    # Calculate risk parity weights
                    long_weights = calculate_weights(long_vols) if long_vols else {}
                    short_weights = calculate_weights(short_vols) if short_vols else {}

                    # Apply allocation and leverage
                    for symbol, weight in long_weights.items():
                        new_weights[symbol] = weight * long_allocation * leverage

                    for symbol, weight in short_weights.items():
                        new_weights[symbol] = -weight * short_allocation * leverage

                elif weighting == "equal_weight":
                    # Equal weight
                    if long_symbols:
                        long_weight = (long_allocation * leverage) / len(long_symbols)
                        for symbol in long_symbols:
                            new_weights[symbol] = long_weight

                    if short_symbols:
                        short_weight = (short_allocation * leverage) / len(short_symbols)
                        for symbol in short_symbols:
                            new_weights[symbol] = -short_weight

                # Record trades
                if new_weights != current_weights:
                    all_symbols = set(new_weights.keys()) | set(current_weights.keys())
                    for symbol in all_symbols:
                        old_weight = current_weights.get(symbol, 0)
                        new_weight = new_weights.get(symbol, 0)
                        if abs(new_weight - old_weight) > 0.0001:
                            # Get kurtosis for this symbol
                            kurt = ranked_data[ranked_data["symbol"] == symbol]["kurtosis"].values
                            kurt_val = kurt[0] if len(kurt) > 0 else np.nan

                            trades_history.append(
                                {
                                    "date": current_date,
                                    "symbol": symbol,
                                    "signal": (
                                        "LONG"
                                        if new_weight > 0
                                        else "SHORT" if new_weight < 0 else "CLOSE"
                                    ),
                                    "old_weight": old_weight,
                                    "new_weight": new_weight,
                                    "weight_change": new_weight - old_weight,
                                    "kurtosis": kurt_val,
                                }
                            )

                current_weights = new_weights.copy()
                last_rebalance_date = current_date

        # Calculate daily portfolio return
        if date_idx > 0 and current_weights:
            current_returns = filtered_data[filtered_data["date"] == current_date]
            portfolio_return = calculate_portfolio_returns(current_weights, current_returns)
            current_capital = current_capital * np.exp(portfolio_return)

        # Record portfolio value
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
    kurtosis_df = pd.DataFrame(kurtosis_timeseries)

    # Calculate performance metrics
    metrics = calculate_performance_metrics(portfolio_df, initial_capital)

    return {
        "portfolio_values": portfolio_df,
        "trades": trades_df,
        "kurtosis_timeseries": kurtosis_df,
        "metrics": metrics,
        "strategy_info": {
            "strategy": strategy,
            "kurtosis_window": kurtosis_window,
            "long_percentile": long_percentile,
            "short_percentile": short_percentile,
            "weighting": weighting,
        },
    }


def calculate_performance_metrics(portfolio_df, initial_capital):
    """Calculate performance metrics for the backtest."""
    portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()
    portfolio_df["log_return"] = np.log(
        portfolio_df["portfolio_value"] / portfolio_df["portfolio_value"].shift(1)
    )

    final_value = portfolio_df["portfolio_value"].iloc[-1]
    total_return = (final_value - initial_capital) / initial_capital

    num_days = len(portfolio_df)
    years = num_days / 365.25
    annualized_return = (final_value / initial_capital) ** (1 / years) - 1 if years > 0 else 0

    daily_returns = portfolio_df["log_return"].dropna()
    daily_vol = daily_returns.std()
    annualized_vol = daily_vol * np.sqrt(365)

    sharpe_ratio = annualized_return / annualized_vol if annualized_vol > 0 else 0

    cumulative_returns = (1 + portfolio_df["daily_return"].fillna(0)).cumprod()
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max
    max_drawdown = drawdown.min()

    positive_days = (daily_returns > 0).sum()
    win_rate = positive_days / len(daily_returns) if len(daily_returns) > 0 else 0

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
        "avg_long_positions": portfolio_df["num_long_positions"].mean(),
        "avg_short_positions": portfolio_df["num_short_positions"].mean(),
        "avg_long_exposure": portfolio_df["long_exposure"].mean(),
        "avg_short_exposure": portfolio_df["short_exposure"].mean(),
        "avg_net_exposure": portfolio_df["net_exposure"].mean(),
        "avg_gross_exposure": portfolio_df["gross_exposure"].mean(),
    }

    return metrics


def print_results(results):
    """Print backtest results."""
    metrics = results["metrics"]
    strategy_info = results["strategy_info"]

    print("\n" + "=" * 80)
    print("KURTOSIS FACTOR BACKTEST RESULTS")
    print("=" * 80)

    print(f"\nStrategy Information:")
    print(f"  Strategy: {strategy_info['strategy']}")
    print(f"  Kurtosis window: {strategy_info['kurtosis_window']}d")
    print(f"  Long percentile: {strategy_info['long_percentile']}%")
    print(f"  Short percentile: {strategy_info['short_percentile']}%")
    print(f"  Weighting: {strategy_info['weighting']}")

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

    print(f"\nExposure Statistics:")
    print(f"  Avg Long Exposure:      {metrics['avg_long_exposure']:>15.2%}")
    print(f"  Avg Short Exposure:     {metrics['avg_short_exposure']:>15.2%}")
    print(f"  Avg Net Exposure:       {metrics['avg_net_exposure']:>15.2%}")
    print(f"  Avg Gross Exposure:     {metrics['avg_gross_exposure']:>15.2%}")

    if not results["trades"].empty:
        print(f"  Total Trades:           {len(results['trades']):>15,.0f}")

    print("\n" + "=" * 80)


def save_results(results, output_prefix="backtests/results/kurtosis_factor"):
    """Save backtest results to CSV files."""
    portfolio_file = f"{output_prefix}_portfolio_values.csv"
    results["portfolio_values"].to_csv(portfolio_file, index=False)
    print(f"\nPortfolio values saved to: {portfolio_file}")

    if not results["trades"].empty:
        trades_file = f"{output_prefix}_trades.csv"
        results["trades"].to_csv(trades_file, index=False)
        print(f"Trades history saved to: {trades_file}")

    if not results["kurtosis_timeseries"].empty:
        kurtosis_file = f"{output_prefix}_kurtosis_timeseries.csv"
        results["kurtosis_timeseries"].to_csv(kurtosis_file, index=False)
        print(f"Kurtosis timeseries saved to: {kurtosis_file}")

    metrics_file = f"{output_prefix}_metrics.csv"
    pd.DataFrame([results["metrics"]]).to_csv(metrics_file, index=False)
    print(f"Performance metrics saved to: {metrics_file}")

    strategy_file = f"{output_prefix}_strategy_info.csv"
    pd.DataFrame([results["strategy_info"]]).to_csv(strategy_file, index=False)
    print(f"Strategy info saved to: {strategy_file}")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Backtest Kurtosis Factor Trading Strategy",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--price-data",
        type=str,
        default="data/raw/combined_coinbase_coinmarketcap_daily.csv",
        help="Path to historical OHLCV price data CSV file",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="mean_reversion",
        choices=["mean_reversion", "momentum", "long_only_stable", "long_only_volatile"],
        help="Strategy type",
    )
    parser.add_argument(
        "--kurtosis-window", type=int, default=30, help="Window for kurtosis calculation in days"
    )
    parser.add_argument(
        "--volatility-window",
        type=int,
        default=30,
        help="Window for volatility calculation in days",
    )
    parser.add_argument("--rebalance-days", type=int, default=1, help="Rebalance every N days")
    parser.add_argument(
        "--long-percentile", type=float, default=20, help="Percentile threshold for long positions"
    )
    parser.add_argument(
        "--short-percentile",
        type=float,
        default=80,
        help="Percentile threshold for short positions",
    )
    parser.add_argument("--max-positions", type=int, default=10, help="Maximum positions per side")
    parser.add_argument(
        "--weighting",
        type=str,
        default="risk_parity",
        choices=["risk_parity", "equal_weight"],
        help="Position weighting method",
    )
    parser.add_argument(
        "--initial-capital", type=float, default=10000, help="Initial portfolio capital in USD"
    )
    parser.add_argument("--leverage", type=float, default=1.0, help="Leverage multiplier")
    parser.add_argument(
        "--long-allocation", type=float, default=0.5, help="Allocation to long side"
    )
    parser.add_argument(
        "--short-allocation", type=float, default=0.5, help="Allocation to short side"
    )
    parser.add_argument(
        "--min-volume", type=float, default=5_000_000, help="Minimum 30d avg daily volume filter"
    )
    parser.add_argument(
        "--min-market-cap", type=float, default=50_000_000, help="Minimum market cap filter"
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
        default="backtests/results/kurtosis_factor",
        help="Prefix for output CSV files",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("KURTOSIS FACTOR BACKTEST")
    print("=" * 80)

    # Load data
    print(f"\nLoading price data from {args.price_data}...")
    price_data = load_data(args.price_data)
    print(f"Loaded {len(price_data)} rows for {price_data['symbol'].nunique()} symbols")
    print(f"Date range: {price_data['date'].min().date()} to {price_data['date'].max().date()}")

    # Run backtest
    print("\nRunning backtest...")
    results = backtest(
        price_data=price_data,
        strategy=args.strategy,
        kurtosis_window=args.kurtosis_window,
        volatility_window=args.volatility_window,
        rebalance_days=args.rebalance_days,
        long_percentile=args.long_percentile,
        short_percentile=args.short_percentile,
        max_positions=args.max_positions,
        weighting=args.weighting,
        initial_capital=args.initial_capital,
        leverage=args.leverage,
        long_allocation=args.long_allocation,
        short_allocation=args.short_allocation,
        min_volume=args.min_volume,
        min_market_cap=args.min_market_cap,
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
