#!/usr/bin/env python3
"""
Backtest for ADF Factor Strategy

This script backtests an ADF (Augmented Dickey-Fuller) factor strategy that:
1. Calculates rolling ADF test statistic for all cryptocurrencies
2. Ranks cryptocurrencies by ADF values (stationarity/mean reversion)
3. Creates long/short portfolios based on ADF rankings:
   - Mean Reversion Premium: Long low ADF (stationary), Short high ADF (trending)
   - Trend Following Premium: Long high ADF (trending), Short low ADF (stationary)
4. Uses equal-weight or risk parity weighting within each bucket
5. Rebalances periodically (weekly by default)
6. Tracks portfolio performance over time

ADF hypothesis: Tests whether mean-reverting coins (low ADF) outperform trending coins (high ADF)
or vice versa.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../signals"))

# Import statsmodels for ADF test
try:
    from statsmodels.tsa.stattools import adfuller
except ImportError:
    print("ERROR: statsmodels package not found. Please install it:")
    print("  pip install statsmodels")
    sys.exit(1)


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
    optional_cols = ["volume", "market_cap", "open", "high", "low"]

    cols_to_keep = required_cols.copy()
    for col in optional_cols:
        if col in df.columns:
            cols_to_keep.append(col)

    df = df[cols_to_keep]
    return df


def calculate_rolling_adf(data, window=60, regression="ct", maxlag=4, cache_file=None):
    """
    Calculate rolling ADF test statistic for each cryptocurrency.

    ADF test determines stationarity (mean reversion) of a time series.
    - More negative ADF = more stationary/mean-reverting
    - Less negative ADF = less stationary/more trending

    Args:
        data (pd.DataFrame): DataFrame with date, symbol, close columns
        window (int): Rolling window size for ADF calculation (default: 60 days)
        regression (str): Regression type for ADF test (default: 'ct')
            - 'c': constant only
            - 'ct': constant + trend (recommended for crypto)
            - 'ctt': constant + linear/quadratic trend
            - 'n': no constant, no trend
        maxlag (int): Maximum lag for ADF test (default: 4)
            - Use fixed maxlag for speed (2-3x faster than autolag="AIC")
            - 4-5 lags is typically sufficient for daily crypto data
            - Set to None to use autolag="AIC" (slower but more optimal)
        cache_file (str): Path to cache file for ADF results (optional)
            - If file exists, load cached results instead of recalculating
            - If None, no caching is used

    Returns:
        pd.DataFrame: DataFrame with adf_stat and supporting columns
    """
    # Check cache first
    if cache_file and os.path.exists(cache_file):
        print(f"  Loading ADF statistics from cache: {cache_file}")
        df_cached = pd.read_csv(cache_file, parse_dates=['date'])
        print(f"  Loaded {len(df_cached):,} rows from cache")
        return df_cached
    
    df = data.copy()
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

    # Calculate daily log returns for supporting analysis
    df["daily_return"] = df.groupby("symbol")["close"].transform(lambda x: np.log(x / x.shift(1)))

    # Calculate rolling ADF test statistic
    def calculate_adf_for_group(group):
        """Calculate rolling ADF for a single coin"""
        adf_stats = []
        adf_pvalues = []

        for i in range(len(group)):
            if i < window:
                adf_stats.append(np.nan)
                adf_pvalues.append(np.nan)
                continue

            # Extract window of PRICE LEVELS (not returns!)
            window_prices = group["close"].iloc[i - window : i].values

            # Run ADF test
            try:
                if maxlag is None:
                    # Use autolag="AIC" (slower but more optimal)
                    result = adfuller(window_prices, regression=regression, autolag="AIC")
                else:
                    # Use fixed maxlag (faster)
                    result = adfuller(window_prices, regression=regression, maxlag=maxlag)
                adf_statistic = result[0]  # ADF test statistic
                adf_pvalue = result[1]  # p-value

                # Sanity check: cap extreme values
                if adf_statistic < -20:
                    adf_statistic = -20
                elif adf_statistic > 0:
                    adf_statistic = 0

                adf_stats.append(adf_statistic)
                adf_pvalues.append(adf_pvalue)

            except Exception as e:
                # If ADF test fails, return NaN
                adf_stats.append(np.nan)
                adf_pvalues.append(np.nan)

        return pd.Series(adf_stats), pd.Series(adf_pvalues)

    # Apply ADF calculation to each symbol
    print("  Calculating ADF statistics for each coin...")
    adf_results = []

    for symbol in df["symbol"].unique():
        symbol_data = df[df["symbol"] == symbol].copy().reset_index(drop=True)

        if len(symbol_data) < window:
            continue

        adf_stats, adf_pvalues = calculate_adf_for_group(symbol_data)
        symbol_data["adf_stat"] = adf_stats
        symbol_data["adf_pvalue"] = adf_pvalues

        # Mark as stationary if p-value < 0.05 (95% confidence)
        symbol_data["is_stationary"] = symbol_data["adf_pvalue"] < 0.05

        adf_results.append(symbol_data)

    df_with_adf = pd.concat(adf_results, ignore_index=True)

    # Calculate additional statistics for analysis
    df_with_adf["returns_mean_60d"] = df_with_adf.groupby("symbol")["daily_return"].transform(
        lambda x: x.rolling(window=window, min_periods=int(window * 0.8)).mean()
    )

    df_with_adf["returns_std_60d"] = df_with_adf.groupby("symbol")["daily_return"].transform(
        lambda x: x.rolling(window=window, min_periods=int(window * 0.8)).std()
    )

    # Save to cache if requested
    if cache_file:
        print(f"  Saving ADF statistics to cache: {cache_file}")
        df_with_adf.to_csv(cache_file, index=False)
        print(f"  Saved {len(df_with_adf):,} rows to cache")

    return df_with_adf


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
        lambda x: x.rolling(window=window, min_periods=int(window * 0.7)).std() * np.sqrt(365)
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


def rank_by_adf(data, date, num_quintiles=5):
    """
    Rank cryptocurrencies by ADF statistic on a specific date.

    Args:
        data (pd.DataFrame): DataFrame with adf_stat column
        date (pd.Timestamp): Date to rank on
        num_quintiles (int): Number of quintiles

    Returns:
        pd.DataFrame: DataFrame with quintile and rank information
    """
    # Get data for this specific date
    date_data = data[data["date"] == date].copy()

    if date_data.empty:
        return pd.DataFrame()

    # Remove NaN ADF statistics
    date_data = date_data.dropna(subset=["adf_stat"])

    if len(date_data) < num_quintiles:
        return pd.DataFrame()

    # Rank by ADF (ascending: low/negative to high/less negative)
    # Lower ADF = more mean-reverting/stationary = Rank 1
    # Higher ADF = more trending/non-stationary = Rank N
    date_data["adf_rank"] = date_data["adf_stat"].rank(method="first", ascending=True)
    date_data["percentile"] = date_data["adf_rank"] / len(date_data) * 100

    # Assign quintiles (1 = lowest ADF, num_quintiles = highest ADF)
    try:
        date_data["quintile"] = pd.qcut(
            date_data["adf_stat"],
            q=num_quintiles,
            labels=range(1, num_quintiles + 1),
            duplicates="drop",
        )
    except ValueError:
        # If qcut fails, use rank-based approach
        date_data["quintile"] = pd.cut(
            date_data["adf_rank"], bins=num_quintiles, labels=range(1, num_quintiles + 1)
        )

    return date_data


def select_symbols_by_adf(
    data,
    date,
    strategy="mean_reversion_premium",
    num_quintiles=5,
    long_percentile=20,
    short_percentile=80,
):
    """
    Select symbols based on ADF factor strategy.

    Args:
        data (pd.DataFrame): Data with adf_stat column
        date (pd.Timestamp): Date to select on
        strategy (str): Strategy type:
            - 'mean_reversion_premium': Long low ADF (stationary), short high ADF (trending)
            - 'trend_following_premium': Long high ADF (trending), short low ADF (stationary)
            - 'long_stationary': Long low ADF (stationary) only
            - 'long_trending': Long high ADF (trending) only
        num_quintiles (int): Number of quintiles
        long_percentile (int): Percentile threshold for long positions
        short_percentile (int): Percentile threshold for short positions

    Returns:
        dict: Dictionary with 'long' and 'short' DataFrames
    """
    # Rank by ADF
    ranked_df = rank_by_adf(data, date, num_quintiles)

    if ranked_df.empty:
        return {"long": pd.DataFrame(), "short": pd.DataFrame()}

    if strategy == "mean_reversion_premium":
        # Long lowest ADF (most stationary/mean-reverting)
        # Short highest ADF (most trending/non-stationary)
        long_df = ranked_df[ranked_df["percentile"] <= long_percentile]
        short_df = ranked_df[ranked_df["percentile"] >= short_percentile]

    elif strategy == "trend_following_premium":
        # Long highest ADF (most trending/non-stationary)
        # Short lowest ADF (most stationary/mean-reverting)
        long_df = ranked_df[ranked_df["percentile"] >= short_percentile]
        short_df = ranked_df[ranked_df["percentile"] <= long_percentile]

    elif strategy == "long_stationary":
        # Long only low ADF (stationary)
        long_df = ranked_df[ranked_df["percentile"] <= long_percentile]
        short_df = pd.DataFrame()

    elif strategy == "long_trending":
        # Long only high ADF (trending)
        long_df = ranked_df[ranked_df["percentile"] >= short_percentile]
        short_df = pd.DataFrame()

    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    return {"long": long_df, "short": short_df}


def calculate_position_weights(positions_df, weighting_method="equal_weight", total_allocation=0.5):
    """
    Calculate position weights for a bucket of positions.

    Args:
        positions_df (pd.DataFrame): DataFrame with positions and volatility
        weighting_method (str): Weighting method ('equal_weight' or 'risk_parity')
        total_allocation (float): Total allocation to this bucket (e.g., 0.5 = 50%)

    Returns:
        pd.DataFrame: DataFrame with weights column added
    """
    df = positions_df.copy()

    if df.empty:
        return df

    if weighting_method == "equal_weight":
        # Equal weight across all positions
        df["weight"] = total_allocation / len(df)

    elif weighting_method == "risk_parity":
        # Weight inversely proportional to volatility
        if "volatility" not in df.columns or df["volatility"].isna().all():
            # Fall back to equal weight if no volatility data
            df["weight"] = total_allocation / len(df)
        else:
            # Handle missing volatility
            df["volatility_clean"] = df["volatility"].fillna(df["volatility"].median())

            # Inverse volatility weights
            df["inv_vol"] = 1 / df["volatility_clean"]
            df["weight"] = (df["inv_vol"] / df["inv_vol"].sum()) * total_allocation

    else:
        raise ValueError(f"Unknown weighting method: {weighting_method}")

    return df


def run_backtest(
    data,
    strategy="mean_reversion_premium",
    adf_window=60,
    volatility_window=30,
    rebalance_days=7,
    num_quintiles=5,
    long_percentile=20,
    short_percentile=80,
    regression="ct",
    maxlag=4,
    weighting_method="equal_weight",
    initial_capital=10000,
    leverage=1.0,
    long_allocation=0.5,
    short_allocation=0.5,
    min_volume=5_000_000,
    min_market_cap=50_000_000,
    start_date=None,
    end_date=None,
    cache_file=None,
):
    """
    Run the ADF factor backtest.

    Args:
        data (pd.DataFrame): Historical OHLCV data
        strategy (str): Strategy type
        adf_window (int): ADF calculation window
        volatility_window (int): Volatility calculation window for risk parity
        rebalance_days (int): Rebalance frequency in days
        num_quintiles (int): Number of quintiles
        long_percentile (int): Percentile threshold for longs
        short_percentile (int): Percentile threshold for shorts
        regression (str): ADF regression type ('c', 'ct', 'ctt', 'n')
        maxlag (int): Maximum lag for ADF test (default: 4, None for autolag="AIC")
        cache_file (str): Path to cache file for ADF results (optional)
        weighting_method (str): Position weighting method
        initial_capital (float): Starting capital
        leverage (float): Leverage multiplier
        long_allocation (float): Allocation to long side
        short_allocation (float): Allocation to short side
        min_volume (float): Minimum volume filter
        min_market_cap (float): Minimum market cap filter
        start_date (str): Backtest start date
        end_date (str): Backtest end date

    Returns:
        dict: Dictionary with portfolio_values, trades, metrics, and strategy_info
    """
    print("=" * 80)
    print("ADF FACTOR BACKTEST")
    print("=" * 80)
    print(f"\nStrategy: {strategy}")
    print(f"ADF Window: {adf_window} days")
    print(f"ADF Regression Type: {regression}")
    if maxlag is None:
        print(f"ADF Maxlag: autolag='AIC' (slower, more optimal)")
    else:
        print(f"ADF Maxlag: {maxlag} (faster)")
    print(f"Volatility Window: {volatility_window} days")
    print(f"Rebalance Frequency: {rebalance_days} days")
    print(f"Weighting Method: {weighting_method}")
    print(f"Long Allocation: {long_allocation*100:.1f}%")
    print(f"Short Allocation: {short_allocation*100:.1f}%")
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print(f"Leverage: {leverage}x")
    print(f"Min Volume: ${min_volume:,.0f}")
    print(f"Min Market Cap: ${min_market_cap:,.0f}")

    # Step 1: Calculate ADF statistics
    print("\n" + "-" * 80)
    print("Step 1: Calculating rolling ADF statistics...")
    adf_data = calculate_rolling_adf(
        data, 
        window=adf_window, 
        regression=regression, 
        maxlag=maxlag,
        cache_file=cache_file
    )
    print(f"  Total data points with ADF: {adf_data['adf_stat'].notna().sum()}")
    print(f"  ADF range: [{adf_data['adf_stat'].min():.2f}, {adf_data['adf_stat'].max():.2f}]")
    print(f"  ADF mean: {adf_data['adf_stat'].mean():.2f}")
    print(f"  ADF median: {adf_data['adf_stat'].median():.2f}")
    print(
        f"  Stationary coins (p<0.05): {adf_data['is_stationary'].sum()} / {len(adf_data)} ({adf_data['is_stationary'].mean()*100:.1f}%)"
    )

    # Step 2: Calculate volatility (for risk parity weighting)
    print("\n" + "-" * 80)
    print("Step 2: Calculating volatility...")
    adf_data = calculate_volatility(adf_data, window=volatility_window)

    # Step 3: Filter universe
    print("\n" + "-" * 80)
    print("Step 3: Filtering universe...")
    print(f"  Coins before filtering: {adf_data['symbol'].nunique()}")
    adf_data = filter_universe(adf_data, min_volume=min_volume, min_market_cap=min_market_cap)
    print(f"  Coins after filtering: {adf_data['symbol'].nunique()}")

    # Step 4: Filter by date range
    if start_date:
        adf_data = adf_data[adf_data["date"] >= pd.to_datetime(start_date)]
    if end_date:
        adf_data = adf_data[adf_data["date"] <= pd.to_datetime(end_date)]

    # Step 5: Run backtest
    print("\n" + "-" * 80)
    print("Step 4: Running backtest...")

    # Get trading dates
    trading_dates = sorted(adf_data["date"].unique())

    if len(trading_dates) < adf_window + rebalance_days:
        raise ValueError(f"Insufficient data. Need at least {adf_window + rebalance_days} days.")

    # Start after warmup period
    start_idx = adf_window
    trading_dates = trading_dates[start_idx:]

    print(f"  Trading period: {trading_dates[0].date()} to {trading_dates[-1].date()}")
    print(f"  Total trading days: {len(trading_dates)}")

    # Initialize portfolio tracking
    portfolio_values = []
    trades = []
    current_positions = {}  # {symbol: weight}
    portfolio_value = initial_capital * leverage
    cash = 0  # Market neutral, fully invested

    # Rebalancing loop
    rebalance_dates = trading_dates[::rebalance_days]
    print(f"  Number of rebalances: {len(rebalance_dates)}")

    for date_idx, current_date in enumerate(trading_dates):
        # Check if rebalance day
        if current_date in rebalance_dates:
            # Select positions based on ADF
            selected = select_symbols_by_adf(
                adf_data,
                current_date,
                strategy=strategy,
                num_quintiles=num_quintiles,
                long_percentile=long_percentile,
                short_percentile=short_percentile,
            )

            # Calculate weights
            long_positions = calculate_position_weights(
                selected["long"], weighting_method, long_allocation
            )
            short_positions = calculate_position_weights(
                selected["short"], weighting_method, short_allocation
            )

            # Record trades
            for _, row in long_positions.iterrows():
                trades.append(
                    {
                        "date": current_date,
                        "symbol": row["symbol"],
                        "signal": "LONG",
                        "adf_stat": row["adf_stat"],
                        "adf_pvalue": row.get("adf_pvalue", np.nan),
                        "is_stationary": row.get("is_stationary", False),
                        "adf_rank": row.get("adf_rank", np.nan),
                        "percentile": row.get("percentile", np.nan),
                        "weight": row["weight"],
                        "volatility": row.get("volatility", np.nan),
                        "market_cap": row.get("market_cap", np.nan),
                        "volume_30d_avg": row.get("volume_30d_avg", np.nan),
                    }
                )

            for _, row in short_positions.iterrows():
                trades.append(
                    {
                        "date": current_date,
                        "symbol": row["symbol"],
                        "signal": "SHORT",
                        "adf_stat": row["adf_stat"],
                        "adf_pvalue": row.get("adf_pvalue", np.nan),
                        "is_stationary": row.get("is_stationary", False),
                        "adf_rank": row.get("adf_rank", np.nan),
                        "percentile": row.get("percentile", np.nan),
                        "weight": -row["weight"],  # Negative for short
                        "volatility": row.get("volatility", np.nan),
                        "market_cap": row.get("market_cap", np.nan),
                        "volume_30d_avg": row.get("volume_30d_avg", np.nan),
                    }
                )

            # Update current positions
            current_positions = {}
            for _, row in long_positions.iterrows():
                current_positions[row["symbol"]] = row["weight"]
            for _, row in short_positions.iterrows():
                current_positions[row["symbol"]] = -row["weight"]

        # Calculate daily P&L using next day's returns (avoid lookahead bias)
        if date_idx < len(trading_dates) - 1:
            next_date = trading_dates[date_idx + 1]

            # Get returns for next day
            next_day_data = adf_data[adf_data["date"] == next_date]

            daily_pnl = 0
            for symbol, weight in current_positions.items():
                symbol_data = next_day_data[next_day_data["symbol"] == symbol]
                if not symbol_data.empty:
                    daily_return = symbol_data.iloc[0]["daily_return"]
                    if not np.isnan(daily_return):
                        daily_pnl += weight * daily_return

            # Update portfolio value
            portfolio_value = portfolio_value * (1 + daily_pnl)

        # Calculate exposures
        long_exposure = sum([w for w in current_positions.values() if w > 0])
        short_exposure = sum([w for w in current_positions.values() if w < 0])
        net_exposure = long_exposure + short_exposure
        gross_exposure = long_exposure + abs(short_exposure)

        # Calculate average ADF of positions
        avg_adf_long = 0
        avg_adf_short = 0
        num_longs = sum([1 for w in current_positions.values() if w > 0])
        num_shorts = sum([1 for w in current_positions.values() if w < 0])

        for symbol, weight in current_positions.items():
            symbol_adf_data = adf_data[
                (adf_data["date"] == current_date) & (adf_data["symbol"] == symbol)
            ]
            if not symbol_adf_data.empty:
                adf_val = symbol_adf_data.iloc[0]["adf_stat"]
                if not np.isnan(adf_val):
                    if weight > 0:
                        avg_adf_long += adf_val
                    else:
                        avg_adf_short += adf_val

        if num_longs > 0:
            avg_adf_long = avg_adf_long / num_longs
        if num_shorts > 0:
            avg_adf_short = avg_adf_short / num_shorts

        # Record portfolio value
        portfolio_values.append(
            {
                "date": current_date,
                "portfolio_value": portfolio_value,
                "cash": cash,
                "long_exposure": long_exposure * portfolio_value,
                "short_exposure": short_exposure * portfolio_value,
                "net_exposure": net_exposure * portfolio_value,
                "gross_exposure": gross_exposure * portfolio_value,
                "num_longs": num_longs,
                "num_shorts": num_shorts,
                "avg_adf_long": avg_adf_long,
                "avg_adf_short": avg_adf_short,
            }
        )

    # Convert to DataFrames
    portfolio_df = pd.DataFrame(portfolio_values)
    trades_df = pd.DataFrame(trades)

    # Calculate metrics
    print("\n" + "-" * 80)
    print("Step 5: Calculating performance metrics...")
    metrics = calculate_metrics(portfolio_df, initial_capital, leverage)

    # Calculate strategy info
    strategy_info = {
        "strategy": strategy,
        "adf_window": adf_window,
        "regression": regression,
        "volatility_window": volatility_window,
        "rebalance_days": rebalance_days,
        "num_quintiles": num_quintiles,
        "long_percentile": long_percentile,
        "short_percentile": short_percentile,
        "weighting_method": weighting_method,
        "initial_capital": initial_capital,
        "leverage": leverage,
        "long_allocation": long_allocation,
        "short_allocation": short_allocation,
        "avg_adf_long": (
            trades_df[trades_df["signal"] == "LONG"]["adf_stat"].mean()
            if not trades_df.empty
            else np.nan
        ),
        "avg_adf_short": (
            trades_df[trades_df["signal"] == "SHORT"]["adf_stat"].mean()
            if not trades_df.empty
            else np.nan
        ),
        "long_symbols": (
            ",".join(sorted(trades_df[trades_df["signal"] == "LONG"]["symbol"].unique()))
            if not trades_df.empty
            else ""
        ),
        "short_symbols": (
            ",".join(sorted(trades_df[trades_df["signal"] == "SHORT"]["symbol"].unique()))
            if not trades_df.empty
            else ""
        ),
    }

    return {
        "portfolio_values": portfolio_df,
        "trades": trades_df,
        "metrics": metrics,
        "strategy_info": strategy_info,
    }


def calculate_metrics(portfolio_df, initial_capital, leverage):
    """
    Calculate performance metrics from portfolio values.

    Args:
        portfolio_df (pd.DataFrame): Portfolio values over time
        initial_capital (float): Starting capital
        leverage (float): Leverage multiplier

    Returns:
        dict: Dictionary of performance metrics
    """
    if portfolio_df.empty:
        return {}

    # Calculate returns
    portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()

    # Total return
    final_value = portfolio_df["portfolio_value"].iloc[-1]
    initial_value = initial_capital * leverage
    total_return = (final_value - initial_value) / initial_value

    # Annualized return
    num_days = len(portfolio_df)
    annualized_return = (1 + total_return) ** (365 / num_days) - 1

    # Volatility
    annualized_volatility = portfolio_df["daily_return"].std() * np.sqrt(365)

    # Sharpe ratio (assuming 0% risk-free rate)
    sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility > 0 else 0

    # Sortino ratio (downside deviation)
    downside_returns = portfolio_df["daily_return"][portfolio_df["daily_return"] < 0]
    downside_volatility = downside_returns.std() * np.sqrt(365) if len(downside_returns) > 0 else 0
    sortino_ratio = annualized_return / downside_volatility if downside_volatility > 0 else 0

    # Maximum drawdown
    cumulative_returns = (1 + portfolio_df["daily_return"]).cumprod()
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max
    max_drawdown = drawdown.min()

    # Calmar ratio
    calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0

    # Win rate
    win_rate = (portfolio_df["daily_return"] > 0).sum() / len(portfolio_df)

    # Average exposures
    avg_long_exposure = portfolio_df["long_exposure"].mean()
    avg_short_exposure = portfolio_df["short_exposure"].mean()
    avg_net_exposure = portfolio_df["net_exposure"].mean()
    avg_gross_exposure = portfolio_df["gross_exposure"].mean()

    # Average positions
    avg_long_positions = portfolio_df["num_longs"].mean()
    avg_short_positions = portfolio_df["num_shorts"].mean()

    # Average ADF
    avg_adf_long = portfolio_df["avg_adf_long"].mean()
    avg_adf_short = portfolio_df["avg_adf_short"].mean()

    metrics = {
        "initial_capital": initial_capital,
        "leverage": leverage,
        "final_value": final_value,
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "sharpe_ratio": sharpe_ratio,
        "sortino_ratio": sortino_ratio,
        "max_drawdown": max_drawdown,
        "calmar_ratio": calmar_ratio,
        "win_rate": win_rate,
        "trading_days": num_days,
        "avg_long_exposure": avg_long_exposure,
        "avg_short_exposure": avg_short_exposure,
        "avg_net_exposure": avg_net_exposure,
        "avg_gross_exposure": avg_gross_exposure,
        "avg_long_positions": avg_long_positions,
        "avg_short_positions": avg_short_positions,
        "avg_adf_long": avg_adf_long,
        "avg_adf_short": avg_adf_short,
    }

    return metrics


def print_results(results):
    """
    Print backtest results in a formatted way.

    Args:
        results (dict): Backtest results dictionary
    """
    metrics = results["metrics"]
    strategy_info = results["strategy_info"]

    print("\n" + "=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)

    print("\nStrategy Configuration:")
    print(f"  Strategy:               {strategy_info['strategy']}")
    print(f"  ADF Window:             {strategy_info['adf_window']} days")
    print(f"  ADF Regression:         {strategy_info['regression']}")
    print(f"  Rebalance Frequency:    {strategy_info['rebalance_days']} days")
    print(f"  Weighting Method:       {strategy_info['weighting_method']}")
    print(f"  Long Allocation:        {strategy_info['long_allocation']*100:.1f}%")
    print(f"  Short Allocation:       {strategy_info['short_allocation']*100:.1f}%")

    print("\nPortfolio Performance:")
    print(f"  Initial Capital:        $ {metrics['initial_capital']:>12,.2f}")
    print(f"  Final Value:            $ {metrics['final_value']:>12,.2f}")
    print(f"  Total Return:           {metrics['total_return']:>14.2%}")
    print(f"  Annualized Return:      {metrics['annualized_return']:>14.2%}")

    print("\nRisk Metrics:")
    print(f"  Annualized Volatility:  {metrics['annualized_volatility']:>14.2%}")
    print(f"  Sharpe Ratio:           {metrics['sharpe_ratio']:>14.2f}")
    print(f"  Sortino Ratio:          {metrics['sortino_ratio']:>14.2f}")
    print(f"  Maximum Drawdown:       {metrics['max_drawdown']:>14.2%}")
    print(f"  Calmar Ratio:           {metrics['calmar_ratio']:>14.2f}")

    print("\nTrading Statistics:")
    print(f"  Win Rate:               {metrics['win_rate']:>14.2%}")
    print(f"  Trading Days:           {metrics['trading_days']:>14.0f}")
    print(f"  Avg Long Positions:     {metrics['avg_long_positions']:>14.1f}")
    print(f"  Avg Short Positions:    {metrics['avg_short_positions']:>14.1f}")

    print("\nExposure Metrics:")
    print(f"  Avg Long Exposure:      $ {metrics['avg_long_exposure']:>12,.2f}")
    print(f"  Avg Short Exposure:     $ {metrics['avg_short_exposure']:>12,.2f}")
    print(f"  Avg Net Exposure:       $ {metrics['avg_net_exposure']:>12,.2f}")
    print(f"  Avg Gross Exposure:     $ {metrics['avg_gross_exposure']:>12,.2f}")

    print("\nADF Analysis:")
    print(f"  Avg Long ADF:           {metrics['avg_adf_long']:>14.2f}")
    print(f"  Avg Short ADF:          {metrics['avg_adf_short']:>14.2f}")
    print(f"  ADF Spread:             {metrics['avg_adf_short'] - metrics['avg_adf_long']:>14.2f}")

    print("\n" + "=" * 80)


def save_results(results, output_prefix):
    """
    Save backtest results to CSV files.

    Args:
        results (dict): Backtest results dictionary
        output_prefix (str): Prefix for output files
    """
    output_dir = os.path.dirname(output_prefix) or "."
    os.makedirs(output_dir, exist_ok=True)

    # Save portfolio values
    portfolio_file = f"{output_prefix}_portfolio_values.csv"
    results["portfolio_values"].to_csv(portfolio_file, index=False)
    print(f"\n✓ Saved portfolio values to: {portfolio_file}")

    # Save trades
    trades_file = f"{output_prefix}_trades.csv"
    results["trades"].to_csv(trades_file, index=False)
    print(f"✓ Saved trades to: {trades_file}")

    # Save metrics
    metrics_file = f"{output_prefix}_metrics.csv"
    metrics_df = pd.DataFrame([results["metrics"]]).T
    metrics_df.columns = ["value"]
    metrics_df.to_csv(metrics_file)
    print(f"✓ Saved metrics to: {metrics_file}")

    # Save strategy info
    strategy_file = f"{output_prefix}_strategy_info.csv"
    strategy_df = pd.DataFrame([results["strategy_info"]])
    strategy_df.to_csv(strategy_file, index=False)
    print(f"✓ Saved strategy info to: {strategy_file}")


def main():
    """Main function to run ADF factor backtest."""
    parser = argparse.ArgumentParser(description="Backtest ADF factor strategy")

    # Data parameters
    parser.add_argument(
        "--price-data",
        type=str,
        default="data/raw/combined_coinbase_coinmarketcap_daily.csv",
        help="Path to historical OHLCV CSV file",
    )

    # Strategy parameters
    parser.add_argument(
        "--strategy",
        type=str,
        default="mean_reversion_premium",
        choices=[
            "mean_reversion_premium",
            "trend_following_premium",
            "long_stationary",
            "long_trending",
        ],
        help="Strategy variant",
    )

    # ADF calculation parameters
    parser.add_argument("--adf-window", type=int, default=60, help="ADF calculation window in days")
    parser.add_argument(
        "--regression",
        type=str,
        default="ct",
        choices=["c", "ct", "ctt", "n"],
        help="ADF regression type (c=constant, ct=constant+trend)",
    )
    parser.add_argument(
        "--maxlag",
        type=int,
        default=4,
        help="Maximum lag for ADF test (default: 4 for speed, use 0 for autolag='AIC')",
    )
    parser.add_argument(
        "--cache-file",
        type=str,
        default=None,
        help="Path to cache file for ADF results (speeds up repeated runs)",
    )
    parser.add_argument(
        "--volatility-window", type=int, default=30, help="Volatility calculation window in days"
    )

    # Portfolio construction parameters
    parser.add_argument("--rebalance-days", type=int, default=7, help="Rebalance frequency in days")
    parser.add_argument("--num-quintiles", type=int, default=5, help="Number of ADF quintiles")
    parser.add_argument(
        "--long-percentile", type=int, default=20, help="Percentile threshold for long positions"
    )
    parser.add_argument(
        "--short-percentile", type=int, default=80, help="Percentile threshold for short positions"
    )
    parser.add_argument(
        "--weighting-method",
        type=str,
        default="equal_weight",
        choices=["equal_weight", "risk_parity"],
        help="Position weighting method",
    )

    # Capital and leverage
    parser.add_argument(
        "--initial-capital", type=float, default=10000, help="Initial capital in USD"
    )
    parser.add_argument("--leverage", type=float, default=1.0, help="Leverage multiplier")
    parser.add_argument(
        "--long-allocation", type=float, default=0.5, help="Allocation to long side (0-1)"
    )
    parser.add_argument(
        "--short-allocation", type=float, default=0.5, help="Allocation to short side (0-1)"
    )

    # Universe filters
    parser.add_argument(
        "--min-volume", type=float, default=5_000_000, help="Minimum 30-day average volume in USD"
    )
    parser.add_argument(
        "--min-market-cap", type=float, default=50_000_000, help="Minimum market cap in USD"
    )

    # Date range
    parser.add_argument(
        "--start-date", type=str, default=None, help="Backtest start date (YYYY-MM-DD)"
    )
    parser.add_argument("--end-date", type=str, default=None, help="Backtest end date (YYYY-MM-DD)")

    # Output
    parser.add_argument(
        "--output-prefix",
        type=str,
        default="backtests/results/backtest_adf_factor",
        help="Prefix for output files",
    )

    args = parser.parse_args()

    # Load data
    print(f"\nLoading data from: {args.price_data}")
    data = load_data(args.price_data)
    print(f"Loaded {len(data)} data points for {data['symbol'].nunique()} symbols")
    print(f"Date range: {data['date'].min().date()} to {data['date'].max().date()}")

    # Convert maxlag=0 to None (for autolag="AIC")
    maxlag = None if args.maxlag == 0 else args.maxlag
    
    # Run backtest
    results = run_backtest(
        data=data,
        strategy=args.strategy,
        adf_window=args.adf_window,
        regression=args.regression,
        maxlag=maxlag,
        volatility_window=args.volatility_window,
        rebalance_days=args.rebalance_days,
        num_quintiles=args.num_quintiles,
        long_percentile=args.long_percentile,
        short_percentile=args.short_percentile,
        weighting_method=args.weighting_method,
        initial_capital=args.initial_capital,
        leverage=args.leverage,
        long_allocation=args.long_allocation,
        short_allocation=args.short_allocation,
        min_volume=args.min_volume,
        min_market_cap=args.min_market_cap,
        start_date=args.start_date,
        end_date=args.end_date,
        cache_file=args.cache_file,
    )

    # Print results
    print_results(results)

    # Save results
    save_results(results, args.output_prefix)

    print("\n" + "=" * 80)
    print("BACKTEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
