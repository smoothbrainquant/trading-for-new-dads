#!/usr/bin/env python3
"""
Backtest for IQR Spread Factor Strategy

This script backtests an IQR spread-based market regime strategy that:
1. Calculates 30-day returns for top 100 cryptocurrencies by market cap
2. Computes IQR spread = 75th percentile - 25th percentile of returns
3. Classifies market regime based on IQR spread level (low/medium/high)
4. Rotates between majors (top 10) and small caps (rank 51-100) based on regime:
   - Low spread (compressed) = Risk-on → Overweight small caps
   - High spread (dispersed) = Risk-off → Overweight majors
5. Tracks portfolio performance over time

Theory: Low IQR spread indicates broad-based market moves (bullish regime),
while high IQR spread indicates fragmented market (potential rollover).
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../signals"))


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


def calculate_returns(data, lookback=30):
    """
    Calculate N-day percentage returns for each cryptocurrency.

    Args:
        data (pd.DataFrame): DataFrame with date, symbol, close columns
        lookback (int): Number of days for return calculation

    Returns:
        pd.DataFrame: DataFrame with returns_Nd column
    """
    df = data.copy()
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

    # Calculate N-day percentage returns
    df[f"returns_{lookback}d"] = df.groupby("symbol")["close"].transform(
        lambda x: (x / x.shift(lookback) - 1) * 100
    )

    # Also calculate daily returns for portfolio calculations
    df["daily_return"] = df.groupby("symbol")["close"].transform(lambda x: np.log(x / x.shift(1)))

    return df


def calculate_iqr_spread(
    data, date, lookback=30, universe_size=100, min_volume=1_000_000, min_market_cap=10_000_000
):
    """
    Calculate IQR spread for a specific date.

    IQR Spread = 75th percentile - 25th percentile of N-day returns
    across top N cryptocurrencies by market cap.

    Args:
        data (pd.DataFrame): DataFrame with returns and market cap
        date (pd.Timestamp): Date to calculate IQR spread for
        lookback (int): Days for return calculation
        universe_size (int): Number of top coins to include
        min_volume (float): Minimum volume filter
        min_market_cap (float): Minimum market cap filter

    Returns:
        dict: IQR spread statistics
    """
    # Get data for this date
    date_data = data[data["date"] == date].copy()

    if date_data.empty:
        return None

    # Filter by volume and market cap
    if "volume" in date_data.columns:
        date_data = date_data[date_data["volume"] >= min_volume]
    if "market_cap" in date_data.columns:
        date_data = date_data[date_data["market_cap"] >= min_market_cap]

    # Get top N by market cap
    if "market_cap" in date_data.columns:
        date_data = date_data.nlargest(universe_size, "market_cap")

    # Get returns for lookback period
    returns_col = f"returns_{lookback}d"
    if returns_col not in date_data.columns:
        return None

    # Remove NaN returns
    returns = date_data[returns_col].dropna()

    if len(returns) < 20:  # Minimum data requirement
        return None

    # Calculate IQR statistics
    p25 = np.percentile(returns, 25)
    p75 = np.percentile(returns, 75)
    iqr_spread = p75 - p25

    # Additional statistics
    stats = {
        "date": date,
        "iqr_spread": iqr_spread,
        "p25": p25,
        "p75": p75,
        "median": np.median(returns),
        "mean": np.mean(returns),
        "std": np.std(returns),
        "min": np.min(returns),
        "max": np.max(returns),
        "range": np.max(returns) - np.min(returns),
        "num_coins": len(returns),
    }

    return stats


def classify_regime(iqr_spread, iqr_history, low_threshold=20, high_threshold=80):
    """
    Classify market regime based on IQR spread percentile.

    Args:
        iqr_spread (float): Current IQR spread value
        iqr_history (pd.Series): Historical IQR spread values
        low_threshold (int): Percentile threshold for low spread regime
        high_threshold (int): Percentile threshold for high spread regime

    Returns:
        str: Regime classification ('LOW_SPREAD', 'MEDIUM_SPREAD', 'HIGH_SPREAD')
    """
    if iqr_history.empty or len(iqr_history) < 30:
        return "MEDIUM_SPREAD"  # Default to medium if insufficient history

    # Calculate percentile of current spread relative to history
    percentile = (iqr_history < iqr_spread).sum() / len(iqr_history) * 100

    if percentile <= low_threshold:
        return "LOW_SPREAD"
    elif percentile >= high_threshold:
        return "HIGH_SPREAD"
    else:
        return "MEDIUM_SPREAD"


def determine_allocations(regime, allocation_method="fixed"):
    """
    Determine allocation to majors and small caps based on regime.

    Args:
        regime (str): Market regime classification
        allocation_method (str): Allocation method ('fixed', 'continuous', 'threshold')

    Returns:
        dict: Allocation to majors and small caps
    """
    if allocation_method == "fixed":
        # Fixed allocations based on regime
        if regime == "LOW_SPREAD":
            # Risk-on: Favor small caps
            return {"majors": 0.30, "small_caps": 0.70}
        elif regime == "HIGH_SPREAD":
            # Risk-off: Favor majors
            return {"majors": 0.70, "small_caps": 0.30}
        else:
            # Neutral: Balanced
            return {"majors": 0.50, "small_caps": 0.50}

    else:
        # For now, default to fixed
        # Future: implement continuous and threshold methods
        return {"majors": 0.50, "small_caps": 0.50}


def select_baskets(
    data,
    date,
    majors_count=10,
    small_caps_range=(51, 100),
    min_volume=1_000_000,
    min_market_cap=10_000_000,
):
    """
    Select majors and small caps baskets for a specific date.

    Args:
        data (pd.DataFrame): DataFrame with market cap data
        date (pd.Timestamp): Date to select baskets for
        majors_count (int): Number of coins in majors basket
        small_caps_range (tuple): Rank range for small caps (start, end)
        min_volume (float): Minimum volume filter
        min_market_cap (float): Minimum market cap filter

    Returns:
        dict: Dictionary with 'majors' and 'small_caps' DataFrames
    """
    # Get data for this date
    date_data = data[data["date"] == date].copy()

    if date_data.empty:
        return {"majors": pd.DataFrame(), "small_caps": pd.DataFrame()}

    # Filter by volume and market cap
    if "volume" in date_data.columns:
        date_data = date_data[date_data["volume"] >= min_volume]
    if "market_cap" in date_data.columns:
        date_data = date_data[date_data["market_cap"] >= min_market_cap]

    # Sort by market cap
    if "market_cap" not in date_data.columns:
        return {"majors": pd.DataFrame(), "small_caps": pd.DataFrame()}

    date_data = date_data.sort_values("market_cap", ascending=False).reset_index(drop=True)

    # Select majors (top N)
    majors = (
        date_data.iloc[:majors_count].copy() if len(date_data) >= majors_count else pd.DataFrame()
    )

    # Select small caps (rank start to end)
    start_rank = small_caps_range[0] - 1  # Convert to 0-indexed
    end_rank = small_caps_range[1]
    small_caps = (
        date_data.iloc[start_rank:end_rank].copy() if len(date_data) >= end_rank else pd.DataFrame()
    )

    return {"majors": majors, "small_caps": small_caps}


def calculate_basket_weights(basket_df, weighting_method="equal_weight"):
    """
    Calculate weights for coins within a basket.

    Args:
        basket_df (pd.DataFrame): DataFrame with basket coins
        weighting_method (str): Weighting method ('equal_weight', 'market_cap', 'risk_parity')

    Returns:
        pd.DataFrame: DataFrame with weights column added
    """
    df = basket_df.copy()

    if df.empty:
        return df

    if weighting_method == "equal_weight":
        # Equal weight across all coins
        df["weight"] = 1.0 / len(df)

    elif weighting_method == "market_cap":
        # Weight proportional to market cap
        if "market_cap" in df.columns:
            df["weight"] = df["market_cap"] / df["market_cap"].sum()
        else:
            df["weight"] = 1.0 / len(df)

    elif weighting_method == "risk_parity":
        # Weight inversely proportional to volatility
        # Calculate volatility if not present
        if "volatility" not in df.columns:
            # Fallback to equal weight
            df["weight"] = 1.0 / len(df)
        else:
            df["volatility_clean"] = df["volatility"].fillna(df["volatility"].median())
            df["inv_vol"] = 1 / df["volatility_clean"]
            df["weight"] = df["inv_vol"] / df["inv_vol"].sum()

    else:
        df["weight"] = 1.0 / len(df)

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
        lambda x: x.rolling(window=window, min_periods=int(window * 0.7)).std() * np.sqrt(365)
    )

    return df


def run_backtest(
    data,
    strategy="dynamic_rotation",
    lookback_days=30,
    rebalance_days=7,
    iqr_history_window=180,
    majors_count=10,
    small_caps_range=(51, 100),
    low_spread_threshold=20,
    high_spread_threshold=80,
    allocation_method="fixed",
    basket_weighting="equal_weight",
    initial_capital=10000,
    min_volume=1_000_000,
    min_market_cap=10_000_000,
    start_date=None,
    end_date=None,
):
    """
    Run the IQR spread factor backtest.

    Args:
        data (pd.DataFrame): Historical OHLCV data
        strategy (str): Strategy type
        lookback_days (int): Days for return calculation
        rebalance_days (int): Rebalance frequency in days
        iqr_history_window (int): Days of IQR history for regime classification
        majors_count (int): Number of coins in majors basket
        small_caps_range (tuple): Rank range for small caps
        low_spread_threshold (int): Percentile threshold for low spread
        high_spread_threshold (int): Percentile threshold for high spread
        allocation_method (str): Allocation method
        basket_weighting (str): Within-basket weighting method
        initial_capital (float): Starting capital
        min_volume (float): Minimum volume filter
        min_market_cap (float): Minimum market cap filter
        start_date (str): Backtest start date
        end_date (str): Backtest end date

    Returns:
        dict: Dictionary with backtest results
    """
    print("=" * 80)
    print("IQR SPREAD FACTOR BACKTEST")
    print("=" * 80)
    print(f"\nStrategy: {strategy}")
    print(f"Lookback Period: {lookback_days} days")
    print(f"Rebalance Frequency: {rebalance_days} days")
    print(f"IQR History Window: {iqr_history_window} days")
    print(f"Majors: Top {majors_count} coins")
    print(f"Small Caps: Rank {small_caps_range[0]}-{small_caps_range[1]}")
    print(f"Low Spread Threshold: {low_spread_threshold}th percentile")
    print(f"High Spread Threshold: {high_spread_threshold}th percentile")
    print(f"Allocation Method: {allocation_method}")
    print(f"Basket Weighting: {basket_weighting}")
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print(f"Min Volume: ${min_volume:,.0f}")
    print(f"Min Market Cap: ${min_market_cap:,.0f}")

    # Step 1: Calculate returns
    print("\n" + "-" * 80)
    print("Step 1: Calculating returns...")
    data = calculate_returns(data, lookback=lookback_days)
    print(f"  Returns calculated for {data['symbol'].nunique()} symbols")

    # Step 2: Calculate volatility (for risk parity if needed)
    if basket_weighting == "risk_parity":
        print("\n" + "-" * 80)
        print("Step 2: Calculating volatility...")
        data = calculate_volatility(data, window=30)

    # Step 3: Filter by date range
    if start_date:
        data = data[data["date"] >= pd.to_datetime(start_date)]
    if end_date:
        data = data[data["date"] <= pd.to_datetime(end_date)]

    # Step 4: Calculate IQR spread time series
    print("\n" + "-" * 80)
    print("Step 3: Calculating IQR spread time series...")

    trading_dates = sorted(data["date"].unique())

    if len(trading_dates) < lookback_days + rebalance_days:
        raise ValueError(f"Insufficient data. Need at least {lookback_days + rebalance_days} days.")

    # Start after warmup period
    start_idx = lookback_days
    trading_dates = trading_dates[start_idx:]

    print(f"  Trading period: {trading_dates[0].date()} to {trading_dates[-1].date()}")
    print(f"  Total trading days: {len(trading_dates)}")

    # Calculate IQR spread for each date
    iqr_timeseries = []
    for date in trading_dates:
        iqr_stats = calculate_iqr_spread(
            data,
            date,
            lookback=lookback_days,
            universe_size=100,
            min_volume=min_volume,
            min_market_cap=min_market_cap,
        )
        if iqr_stats:
            iqr_timeseries.append(iqr_stats)

    iqr_df = pd.DataFrame(iqr_timeseries)
    print(f"  IQR spread calculated for {len(iqr_df)} dates")
    print(
        f"  IQR spread range: [{iqr_df['iqr_spread'].min():.2f}, {iqr_df['iqr_spread'].max():.2f}]"
    )
    print(f"  IQR spread mean: {iqr_df['iqr_spread'].mean():.2f}")
    print(f"  IQR spread median: {iqr_df['iqr_spread'].median():.2f}")

    # Step 5: Run backtest
    print("\n" + "-" * 80)
    print("Step 4: Running backtest...")

    # Initialize portfolio tracking
    portfolio_values = []
    basket_performance = []
    regime_dates = []
    current_positions = {}  # {symbol: weight}
    portfolio_value = initial_capital
    allocations = {"majors": 0.5, "small_caps": 0.5}  # Default allocations
    baskets = {"majors": pd.DataFrame(), "small_caps": pd.DataFrame()}  # Default empty baskets

    # Rebalancing loop
    rebalance_dates = trading_dates[::rebalance_days]
    print(f"  Number of rebalances: {len(rebalance_dates)}")

    for date_idx, current_date in enumerate(trading_dates):
        # Get IQR spread for current date
        iqr_row = iqr_df[iqr_df["date"] == current_date]
        if iqr_row.empty:
            continue

        current_iqr = iqr_row.iloc[0]["iqr_spread"]

        # Get IQR history for regime classification
        iqr_history = iqr_df[iqr_df["date"] < current_date]["iqr_spread"]
        if len(iqr_history) > iqr_history_window:
            iqr_history = iqr_history.tail(iqr_history_window)

        # Classify regime
        regime = classify_regime(
            current_iqr, iqr_history, low_spread_threshold, high_spread_threshold
        )

        # Calculate IQR percentile for tracking
        if len(iqr_history) > 0:
            iqr_percentile = (iqr_history < current_iqr).sum() / len(iqr_history) * 100
        else:
            iqr_percentile = 50

        # Check if rebalance day
        if current_date in rebalance_dates:
            # Determine allocations based on regime
            allocations = determine_allocations(regime, allocation_method)

            # Select baskets
            baskets = select_baskets(
                data,
                current_date,
                majors_count=majors_count,
                small_caps_range=small_caps_range,
                min_volume=min_volume,
                min_market_cap=min_market_cap,
            )

            # Calculate weights within each basket
            majors_basket = calculate_basket_weights(baskets["majors"], basket_weighting)
            small_caps_basket = calculate_basket_weights(baskets["small_caps"], basket_weighting)

            # Update current positions
            current_positions = {}

            # Add majors positions
            if not majors_basket.empty:
                for _, row in majors_basket.iterrows():
                    current_positions[row["symbol"]] = row["weight"] * allocations["majors"]

            # Add small caps positions
            if not small_caps_basket.empty:
                for _, row in small_caps_basket.iterrows():
                    current_positions[row["symbol"]] = row["weight"] * allocations["small_caps"]

        # Calculate daily P&L using next day's returns (avoid lookahead bias)
        if date_idx < len(trading_dates) - 1:
            next_date = trading_dates[date_idx + 1]

            # Get returns for next day
            next_day_data = data[data["date"] == next_date]

            daily_pnl = 0
            majors_pnl = 0
            small_caps_pnl = 0

            for symbol, weight in current_positions.items():
                symbol_data = next_day_data[next_day_data["symbol"] == symbol]
                if not symbol_data.empty:
                    daily_return = symbol_data.iloc[0]["daily_return"]
                    if not np.isnan(daily_return):
                        position_pnl = weight * daily_return
                        daily_pnl += position_pnl

                        # Track majors vs small caps performance
                        # Check if in majors basket
                        if (
                            not baskets["majors"].empty
                            and symbol in baskets["majors"]["symbol"].values
                        ):
                            majors_pnl += position_pnl
                        elif (
                            not baskets["small_caps"].empty
                            and symbol in baskets["small_caps"]["symbol"].values
                        ):
                            small_caps_pnl += position_pnl

            # Update portfolio value
            portfolio_value = portfolio_value * (1 + daily_pnl)

            # Record basket performance
            basket_performance.append(
                {
                    "date": current_date,
                    "majors_return": majors_pnl if allocations["majors"] > 0 else 0,
                    "small_caps_return": small_caps_pnl if allocations["small_caps"] > 0 else 0,
                    "iqr_spread": current_iqr,
                }
            )

        # Calculate exposures
        majors_exposure = sum(
            [
                w
                for sym, w in current_positions.items()
                if not baskets["majors"].empty and sym in baskets["majors"]["symbol"].values
            ]
        )
        small_caps_exposure = sum(
            [
                w
                for sym, w in current_positions.items()
                if not baskets["small_caps"].empty and sym in baskets["small_caps"]["symbol"].values
            ]
        )

        # Record portfolio value
        portfolio_values.append(
            {
                "date": current_date,
                "portfolio_value": portfolio_value,
                "cash": 0,  # Fully invested
                "majors_exposure": majors_exposure * portfolio_value,
                "small_caps_exposure": small_caps_exposure * portfolio_value,
                "majors_allocation": allocations["majors"],
                "small_caps_allocation": allocations["small_caps"],
                "regime": regime,
                "iqr_spread": current_iqr,
                "iqr_percentile": iqr_percentile,
                "num_positions": len(current_positions),
            }
        )

        # Track regime dates for analysis
        regime_dates.append(
            {
                "date": current_date,
                "regime": regime,
                "iqr_spread": current_iqr,
                "iqr_percentile": iqr_percentile,
            }
        )

    # Convert to DataFrames
    portfolio_df = pd.DataFrame(portfolio_values)
    basket_performance_df = pd.DataFrame(basket_performance)
    regime_dates_df = pd.DataFrame(regime_dates)

    # Merge IQR timeseries with regime info
    iqr_df = iqr_df.merge(
        regime_dates_df[["date", "regime", "iqr_percentile"]], on="date", how="left"
    )

    # Calculate metrics
    print("\n" + "-" * 80)
    print("Step 5: Calculating performance metrics...")
    metrics = calculate_metrics(portfolio_df, initial_capital)

    # Calculate performance by regime
    regime_performance = calculate_regime_performance(portfolio_df, basket_performance_df)

    # Calculate correlations
    correlations = calculate_correlations(iqr_df, basket_performance_df, data)

    # Calculate strategy info
    strategy_info = {
        "strategy": strategy,
        "lookback_days": lookback_days,
        "rebalance_days": rebalance_days,
        "iqr_history_window": iqr_history_window,
        "majors_count": majors_count,
        "small_caps_range": f"{small_caps_range[0]}-{small_caps_range[1]}",
        "low_spread_threshold": low_spread_threshold,
        "high_spread_threshold": high_spread_threshold,
        "allocation_method": allocation_method,
        "basket_weighting": basket_weighting,
        "initial_capital": initial_capital,
    }

    return {
        "portfolio_values": portfolio_df,
        "iqr_timeseries": iqr_df,
        "basket_performance": basket_performance_df,
        "regime_performance": regime_performance,
        "correlations": correlations,
        "metrics": metrics,
        "strategy_info": strategy_info,
    }


def calculate_metrics(portfolio_df, initial_capital):
    """
    Calculate performance metrics from portfolio values.

    Args:
        portfolio_df (pd.DataFrame): Portfolio values over time
        initial_capital (float): Starting capital

    Returns:
        dict: Dictionary of performance metrics
    """
    if portfolio_df.empty:
        return {}

    # Calculate returns
    portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()

    # Total return
    final_value = portfolio_df["portfolio_value"].iloc[-1]
    total_return = (final_value - initial_capital) / initial_capital

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

    # Average allocations
    avg_majors_allocation = portfolio_df["majors_allocation"].mean()
    avg_small_caps_allocation = portfolio_df["small_caps_allocation"].mean()

    # Regime statistics
    regime_counts = portfolio_df["regime"].value_counts()
    days_low_spread = regime_counts.get("LOW_SPREAD", 0)
    days_medium_spread = regime_counts.get("MEDIUM_SPREAD", 0)
    days_high_spread = regime_counts.get("HIGH_SPREAD", 0)

    metrics = {
        "initial_capital": initial_capital,
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
        "avg_majors_allocation": avg_majors_allocation,
        "avg_small_caps_allocation": avg_small_caps_allocation,
        "days_low_spread": days_low_spread,
        "days_medium_spread": days_medium_spread,
        "days_high_spread": days_high_spread,
    }

    return metrics


def calculate_regime_performance(portfolio_df, basket_performance_df):
    """
    Calculate performance metrics by regime.

    Args:
        portfolio_df (pd.DataFrame): Portfolio values with regime
        basket_performance_df (pd.DataFrame): Basket performance data

    Returns:
        pd.DataFrame: Performance metrics by regime
    """
    if portfolio_df.empty:
        return pd.DataFrame()

    # Calculate daily returns by regime
    portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()

    regime_stats = []

    for regime in ["LOW_SPREAD", "MEDIUM_SPREAD", "HIGH_SPREAD"]:
        regime_data = portfolio_df[portfolio_df["regime"] == regime]

        if regime_data.empty:
            continue

        # Portfolio performance in this regime
        avg_return = regime_data["daily_return"].mean() * 365  # Annualized
        volatility = regime_data["daily_return"].std() * np.sqrt(365)
        sharpe = avg_return / volatility if volatility > 0 else 0
        win_rate = (regime_data["daily_return"] > 0).sum() / len(regime_data)

        regime_stats.append(
            {
                "regime": regime,
                "num_days": len(regime_data),
                "avg_return_annualized": avg_return,
                "volatility": volatility,
                "sharpe": sharpe,
                "win_rate": win_rate,
            }
        )

    return pd.DataFrame(regime_stats)


def calculate_correlations(iqr_df, basket_performance_df, data):
    """
    Calculate correlation matrix.

    Args:
        iqr_df (pd.DataFrame): IQR time series
        basket_performance_df (pd.DataFrame): Basket performance
        data (pd.DataFrame): Price data

    Returns:
        pd.DataFrame: Correlation matrix
    """
    # Merge data for correlation analysis
    analysis_df = iqr_df[["date", "iqr_spread", "median"]].copy()

    if not basket_performance_df.empty:
        analysis_df = analysis_df.merge(
            basket_performance_df[["date", "majors_return", "small_caps_return"]],
            on="date",
            how="left",
        )

    # Get BTC returns for comparison
    btc_data = data[data["symbol"].isin(["BTC", "BTC/USD"])][["date", "daily_return"]].copy()
    btc_data = btc_data.rename(columns={"daily_return": "btc_return"})
    btc_data = btc_data.drop_duplicates("date")

    analysis_df = analysis_df.merge(btc_data, on="date", how="left")

    # Calculate correlations
    corr_cols = ["iqr_spread", "median"]
    if "majors_return" in analysis_df.columns:
        corr_cols.extend(["majors_return", "small_caps_return"])
    if "btc_return" in analysis_df.columns:
        corr_cols.append("btc_return")

    corr_matrix = analysis_df[corr_cols].corr()

    return corr_matrix


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
    print(f"  Lookback Period:        {strategy_info['lookback_days']} days")
    print(f"  Rebalance Frequency:    {strategy_info['rebalance_days']} days")
    print(f"  Majors:                 Top {strategy_info['majors_count']}")
    print(f"  Small Caps:             Rank {strategy_info['small_caps_range']}")
    print(f"  Allocation Method:      {strategy_info['allocation_method']}")
    print(f"  Basket Weighting:       {strategy_info['basket_weighting']}")

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

    print("\nAllocation Statistics:")
    print(f"  Avg Majors Allocation:  {metrics['avg_majors_allocation']:>14.2%}")
    print(f"  Avg Small Caps Alloc:   {metrics['avg_small_caps_allocation']:>14.2%}")

    print("\nRegime Statistics:")
    print(f"  Days in Low Spread:     {metrics['days_low_spread']:>14.0f}")
    print(f"  Days in Medium Spread:  {metrics['days_medium_spread']:>14.0f}")
    print(f"  Days in High Spread:    {metrics['days_high_spread']:>14.0f}")

    # Print regime performance
    if not results["regime_performance"].empty:
        print("\nPerformance by Regime:")
        for _, row in results["regime_performance"].iterrows():
            print(f"\n  {row['regime']}:")
            print(f"    Days:                {row['num_days']:>10.0f}")
            print(f"    Avg Return (Ann):    {row['avg_return_annualized']:>10.2%}")
            print(f"    Sharpe Ratio:        {row['sharpe']:>10.2f}")
            print(f"    Win Rate:            {row['win_rate']:>10.2%}")

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

    # Save IQR time series
    iqr_file = f"{output_prefix}_iqr_timeseries.csv"
    results["iqr_timeseries"].to_csv(iqr_file, index=False)
    print(f"✓ Saved IQR time series to: {iqr_file}")

    # Save basket performance
    basket_file = f"{output_prefix}_basket_performance.csv"
    results["basket_performance"].to_csv(basket_file, index=False)
    print(f"✓ Saved basket performance to: {basket_file}")

    # Save regime performance
    regime_file = f"{output_prefix}_regime_performance.csv"
    results["regime_performance"].to_csv(regime_file, index=False)
    print(f"✓ Saved regime performance to: {regime_file}")

    # Save correlations
    corr_file = f"{output_prefix}_correlations.csv"
    results["correlations"].to_csv(corr_file)
    print(f"✓ Saved correlations to: {corr_file}")

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
    """Main function to run IQR spread backtest."""
    parser = argparse.ArgumentParser(description="Backtest IQR spread factor strategy")

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
        default="dynamic_rotation",
        choices=["dynamic_rotation", "long_short", "conditional_smallcap", "spread_mean_reversion"],
        help="Strategy variant",
    )

    # IQR calculation parameters
    parser.add_argument("--lookback-days", type=int, default=30, help="Days for return calculation")
    parser.add_argument(
        "--iqr-history-window",
        type=int,
        default=180,
        help="Days of IQR history for regime classification",
    )

    # Universe parameters
    parser.add_argument(
        "--majors-count", type=int, default=10, help="Number of coins in majors basket"
    )
    parser.add_argument(
        "--small-caps-start", type=int, default=51, help="Starting rank for small caps"
    )
    parser.add_argument(
        "--small-caps-end", type=int, default=100, help="Ending rank for small caps"
    )

    # Regime thresholds
    parser.add_argument(
        "--low-spread-threshold",
        type=int,
        default=20,
        help="Percentile threshold for low spread regime",
    )
    parser.add_argument(
        "--high-spread-threshold",
        type=int,
        default=80,
        help="Percentile threshold for high spread regime",
    )

    # Portfolio construction parameters
    parser.add_argument("--rebalance-days", type=int, default=7, help="Rebalance frequency in days")
    parser.add_argument(
        "--allocation-method",
        type=str,
        default="fixed",
        choices=["fixed", "continuous", "threshold"],
        help="Allocation method",
    )
    parser.add_argument(
        "--basket-weighting",
        type=str,
        default="equal_weight",
        choices=["equal_weight", "market_cap", "risk_parity"],
        help="Within-basket weighting method",
    )

    # Capital
    parser.add_argument(
        "--initial-capital", type=float, default=10000, help="Initial capital in USD"
    )

    # Universe filters
    parser.add_argument(
        "--min-volume", type=float, default=1_000_000, help="Minimum 30-day average volume in USD"
    )
    parser.add_argument(
        "--min-market-cap", type=float, default=10_000_000, help="Minimum market cap in USD"
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
        default="backtests/results/backtest_iqr_spread",
        help="Prefix for output files",
    )

    args = parser.parse_args()

    # Load data
    print(f"\nLoading data from: {args.price_data}")
    data = load_data(args.price_data)
    print(f"Loaded {len(data)} data points for {data['symbol'].nunique()} symbols")
    print(f"Date range: {data['date'].min().date()} to {data['date'].max().date()}")

    # Run backtest
    results = run_backtest(
        data=data,
        strategy=args.strategy,
        lookback_days=args.lookback_days,
        rebalance_days=args.rebalance_days,
        iqr_history_window=args.iqr_history_window,
        majors_count=args.majors_count,
        small_caps_range=(args.small_caps_start, args.small_caps_end),
        low_spread_threshold=args.low_spread_threshold,
        high_spread_threshold=args.high_spread_threshold,
        allocation_method=args.allocation_method,
        basket_weighting=args.basket_weighting,
        initial_capital=args.initial_capital,
        min_volume=args.min_volume,
        min_market_cap=args.min_market_cap,
        start_date=args.start_date,
        end_date=args.end_date,
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
