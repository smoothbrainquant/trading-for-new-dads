#!/usr/bin/env python3
"""
Backtest for Durbin-Watson Factor Strategy with Directional Regime Filtering

This script backtests a Durbin-Watson (DW) factor strategy that:
1. Calculates rolling DW statistic for all cryptocurrencies (measures autocorrelation)
2. Classifies market regime using 5-day BTC percent change
3. Ranks cryptocurrencies by DW values (momentum vs mean reversion)
4. Creates long/short portfolios based on DW rankings and current regime:
   - Regime-Adaptive: Switches between momentum/mean reversion based on regime
   - Momentum Premium: Long low DW (momentum), Short high DW (mean reversion)
   - Mean Reversion Premium: Long high DW (mean reversion), Short low DW (momentum)
5. Uses equal-weight or risk parity weighting within each bucket
6. Rebalances periodically (weekly by default)
7. Tracks portfolio performance over time

DW interpretation:
- DW < 2: Positive autocorrelation (momentum/trending behavior)
- DW ~ 2: No autocorrelation (random walk)
- DW > 2: Negative autocorrelation (mean reversion/oscillating behavior)
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


def calculate_rolling_dw(data, window=60):
    """
    Calculate rolling Durbin-Watson statistic for each cryptocurrency.

    The Durbin-Watson statistic measures autocorrelation in returns:
    DW = Σ(r_t - r_{t-1})² / Σ(r_t)²

    Interpretation:
    - DW ~ 2: No autocorrelation (random walk)
    - DW < 2: Positive autocorrelation (momentum)
    - DW > 2: Negative autocorrelation (mean reversion)
    - DW ≈ 2(1 - ρ) where ρ is first-order autocorrelation

    Args:
        data (pd.DataFrame): DataFrame with date, symbol, close columns
        window (int): Rolling window size for DW calculation (default: 60 days)

    Returns:
        pd.DataFrame: DataFrame with dw_stat and supporting columns
    """
    df = data.copy()
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

    # Calculate daily log returns
    df["daily_return"] = df.groupby("symbol")["close"].transform(lambda x: np.log(x / x.shift(1)))

    # Calculate rolling DW statistic
    def calculate_dw_for_group(group):
        """Calculate rolling DW for a single coin"""
        dw_stats = []
        autocorr_lag1 = []

        for i in range(len(group)):
            if i < window:
                dw_stats.append(np.nan)
                autocorr_lag1.append(np.nan)
                continue

            # Extract window of returns
            window_returns = group["daily_return"].iloc[i - window : i].values

            # Remove NaN values
            clean_returns = window_returns[~np.isnan(window_returns)]

            # Require at least 70% data availability
            if len(clean_returns) < window * 0.7:
                dw_stats.append(np.nan)
                autocorr_lag1.append(np.nan)
                continue

            try:
                # Calculate DW statistic
                # DW = Σ(r_t - r_{t-1})² / Σ(r_t)²
                numerator = np.sum(np.diff(clean_returns) ** 2)
                denominator = np.sum(clean_returns**2)

                if denominator == 0 or np.isnan(denominator):
                    dw_stats.append(np.nan)
                    autocorr_lag1.append(np.nan)
                    continue

                dw = numerator / denominator

                # Sanity check: DW should be between 0 and 4
                if dw < 0:
                    dw = 0
                elif dw > 4:
                    dw = 4

                dw_stats.append(dw)

                # Also calculate first-order autocorrelation for analysis
                # ρ = (2 - DW) / 2
                rho = (2 - dw) / 2
                autocorr_lag1.append(rho)

            except Exception as e:
                # If calculation fails, return NaN
                dw_stats.append(np.nan)
                autocorr_lag1.append(np.nan)

        return pd.Series(dw_stats), pd.Series(autocorr_lag1)

    # Apply DW calculation to each symbol
    print("  Calculating Durbin-Watson statistics for each coin...")
    dw_results = []

    for symbol in df["symbol"].unique():
        symbol_data = df[df["symbol"] == symbol].copy().reset_index(drop=True)

        if len(symbol_data) < window:
            continue

        dw_stats, autocorr = calculate_dw_for_group(symbol_data)
        symbol_data["dw_stat"] = dw_stats
        symbol_data["autocorr_lag1"] = autocorr

        # Classify behavior
        # DW < 1.5: Strong momentum
        # 1.5 <= DW < 2.0: Weak momentum
        # DW ~ 2.0: Random walk
        # 2.0 < DW <= 2.5: Weak mean reversion
        # DW > 2.5: Strong mean reversion
        symbol_data["behavior"] = "random_walk"
        symbol_data.loc[symbol_data["dw_stat"] < 1.5, "behavior"] = "strong_momentum"
        symbol_data.loc[
            (symbol_data["dw_stat"] >= 1.5) & (symbol_data["dw_stat"] < 2.0), "behavior"
        ] = "weak_momentum"
        symbol_data.loc[
            (symbol_data["dw_stat"] > 2.0) & (symbol_data["dw_stat"] <= 2.5), "behavior"
        ] = "weak_mean_reversion"
        symbol_data.loc[symbol_data["dw_stat"] > 2.5, "behavior"] = "strong_mean_reversion"

        dw_results.append(symbol_data)

    df_with_dw = pd.concat(dw_results, ignore_index=True)

    # Calculate additional statistics for analysis
    df_with_dw["returns_mean_60d"] = df_with_dw.groupby("symbol")["daily_return"].transform(
        lambda x: x.rolling(window=window, min_periods=int(window * 0.8)).mean()
    )

    df_with_dw["returns_std_60d"] = df_with_dw.groupby("symbol")["daily_return"].transform(
        lambda x: x.rolling(window=window, min_periods=int(window * 0.8)).std()
    )

    return df_with_dw


def classify_regime(data, btc_symbol="BTC", directional_window=5, directional_threshold=10):
    """
    Classify market regime based on BTC directional change.

    Regimes:
    - Strong Up: BTC 5d % change > +10%
    - Moderate Up: BTC 5d % change 0% to +10%
    - Down: BTC 5d % change 0% to -10%
    - Strong Down: BTC 5d % change < -10%

    Args:
        data (pd.DataFrame): DataFrame with date, symbol, close
        btc_symbol (str): BTC symbol name
        directional_window (int): Days for % change calculation (default: 5)
        directional_threshold (float): Threshold for strong moves (default: 10)

    Returns:
        pd.DataFrame: DataFrame with regime and btc_Nd_pct columns
    """
    df = data.copy()

    # Get BTC prices
    btc_data = df[df["symbol"] == btc_symbol][["date", "close"]].copy()
    btc_data = btc_data.rename(columns={"close": "btc_close"})
    btc_data = btc_data.sort_values("date")

    # Calculate N-day percent change
    btc_data[f"btc_{directional_window}d_pct"] = (
        btc_data["btc_close"] / btc_data["btc_close"].shift(directional_window) - 1
    ) * 100

    # Classify regime
    def get_regime(pct_change):
        if pd.isna(pct_change):
            return "unknown"
        elif pct_change > directional_threshold:
            return "Strong Up"
        elif pct_change > 0:
            return "Moderate Up"
        elif pct_change > -directional_threshold:
            return "Down"
        else:
            return "Strong Down"

    btc_data["regime"] = btc_data[f"btc_{directional_window}d_pct"].apply(get_regime)

    # Merge regime info back to main dataframe
    df = df.merge(btc_data[["date", f"btc_{directional_window}d_pct", "regime"]], on="date", how="left")

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


def rank_by_dw(data, date, num_quintiles=5):
    """
    Rank cryptocurrencies by DW statistic on a specific date.

    Args:
        data (pd.DataFrame): DataFrame with dw_stat column
        date (pd.Timestamp): Date to rank on
        num_quintiles (int): Number of quintiles

    Returns:
        pd.DataFrame: DataFrame with quintile and rank information
    """
    # Get data for this specific date
    date_data = data[data["date"] == date].copy()

    if date_data.empty:
        return pd.DataFrame()

    # Remove NaN DW statistics
    date_data = date_data.dropna(subset=["dw_stat"])

    if len(date_data) < num_quintiles:
        return pd.DataFrame()

    # Rank by DW (ascending: low to high)
    # Lower DW = more momentum (positive autocorrelation) = Rank 1
    # Higher DW = more mean reversion (negative autocorrelation) = Rank N
    date_data["dw_rank"] = date_data["dw_stat"].rank(method="first", ascending=True)
    date_data["percentile"] = date_data["dw_rank"] / len(date_data) * 100

    # Assign quintiles (1 = lowest DW, num_quintiles = highest DW)
    try:
        date_data["quintile"] = pd.qcut(
            date_data["dw_stat"],
            q=num_quintiles,
            labels=range(1, num_quintiles + 1),
            duplicates="drop",
        )
    except ValueError:
        # If qcut fails, use rank-based approach
        date_data["quintile"] = pd.cut(
            date_data["dw_rank"], bins=num_quintiles, labels=range(1, num_quintiles + 1)
        )

    return date_data


def select_symbols_by_dw(
    data,
    date,
    strategy="regime_adaptive",
    num_quintiles=5,
    long_percentile=20,
    short_percentile=80,
):
    """
    Select symbols based on DW factor strategy and current regime.

    Args:
        data (pd.DataFrame): Data with dw_stat and regime columns
        date (pd.Timestamp): Date to select on
        strategy (str): Strategy type:
            - 'regime_adaptive': Switch based on market regime
            - 'momentum_premium': Long low DW (momentum), short high DW (mean reversion)
            - 'mean_reversion_premium': Long high DW (mean reversion), short low DW (momentum)
            - 'long_momentum': Long low DW (momentum) only
            - 'long_mean_reversion': Long high DW (mean reversion) only
        num_quintiles (int): Number of quintiles
        long_percentile (int): Percentile threshold for long positions
        short_percentile (int): Percentile threshold for short positions

    Returns:
        dict: Dictionary with 'long' and 'short' DataFrames
    """
    # Rank by DW
    ranked_df = rank_by_dw(data, date, num_quintiles)

    if ranked_df.empty:
        return {"long": pd.DataFrame(), "short": pd.DataFrame()}

    # Get current regime
    current_regime = ranked_df["regime"].iloc[0] if "regime" in ranked_df.columns else "unknown"

    if strategy == "regime_adaptive":
        # Switch strategy based on market regime
        # Strong moves (Strong Up, Down) → Favor MOMENTUM (low DW)
        # Moderate moves (Moderate Up, Strong Down) → Favor MEAN REVERSION (high DW)

        if current_regime in ["Strong Up", "Down"]:
            # Favor momentum in strong directional moves
            # Long low DW (momentum), Short high DW (mean reversion)
            long_df = ranked_df[ranked_df["percentile"] <= long_percentile]
            short_df = ranked_df[ranked_df["percentile"] >= short_percentile]

        elif current_regime in ["Moderate Up", "Strong Down"]:
            # Favor mean reversion in moderate/choppy moves
            # Long high DW (mean reversion), Short low DW (momentum)
            long_df = ranked_df[ranked_df["percentile"] >= short_percentile]
            short_df = ranked_df[ranked_df["percentile"] <= long_percentile]

        else:
            # Unknown regime: default to momentum
            long_df = ranked_df[ranked_df["percentile"] <= long_percentile]
            short_df = ranked_df[ranked_df["percentile"] >= short_percentile]

    elif strategy == "momentum_premium":
        # Always long low DW (momentum), short high DW (mean reversion)
        long_df = ranked_df[ranked_df["percentile"] <= long_percentile]
        short_df = ranked_df[ranked_df["percentile"] >= short_percentile]

    elif strategy == "mean_reversion_premium":
        # Always long high DW (mean reversion), short low DW (momentum)
        long_df = ranked_df[ranked_df["percentile"] >= short_percentile]
        short_df = ranked_df[ranked_df["percentile"] <= long_percentile]

    elif strategy == "long_momentum":
        # Long only low DW (momentum)
        long_df = ranked_df[ranked_df["percentile"] <= long_percentile]
        short_df = pd.DataFrame()

    elif strategy == "long_mean_reversion":
        # Long only high DW (mean reversion)
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
    strategy="regime_adaptive",
    dw_window=60,
    directional_window=5,
    directional_threshold=10,
    volatility_window=30,
    rebalance_days=7,
    num_quintiles=5,
    long_percentile=20,
    short_percentile=80,
    weighting_method="equal_weight",
    initial_capital=10000,
    leverage=1.0,
    long_allocation=0.5,
    short_allocation=0.5,
    min_volume=5_000_000,
    min_market_cap=50_000_000,
    start_date=None,
    end_date=None,
):
    """
    Run the DW factor backtest.

    Args:
        data (pd.DataFrame): Historical OHLCV data
        strategy (str): Strategy type
        dw_window (int): DW calculation window
        directional_window (int): Days for directional % change
        directional_threshold (float): Threshold for strong moves (%)
        volatility_window (int): Volatility calculation window for risk parity
        rebalance_days (int): Rebalance frequency in days
        num_quintiles (int): Number of quintiles
        long_percentile (int): Percentile threshold for longs
        short_percentile (int): Percentile threshold for shorts
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
        dict: Dictionary with backtest results
    """
    print("\n" + "=" * 80)
    print(f"DURBIN-WATSON FACTOR BACKTEST - {strategy.upper()}")
    print("=" * 80)
    print(f"Strategy: {strategy}")
    print(f"DW Window: {dw_window} days")
    print(f"Directional Window: {directional_window} days")
    print(f"Directional Threshold: ±{directional_threshold}%")
    print(f"Rebalance: Every {rebalance_days} days")
    print(f"Weighting: {weighting_method}")
    print(f"Initial Capital: ${initial_capital:,.2f}")
    print(f"Long/Short Allocation: {long_allocation*100:.0f}% / {short_allocation*100:.0f}%")
    print("=" * 80 + "\n")

    # Step 1: Calculate DW statistics
    print("[1/7] Calculating Durbin-Watson statistics...")
    df = calculate_rolling_dw(data, window=dw_window)

    # Step 2: Classify market regime
    print("[2/7] Classifying market regimes...")
    df = classify_regime(
        df,
        btc_symbol="BTC",
        directional_window=directional_window,
        directional_threshold=directional_threshold,
    )

    # Step 3: Calculate volatility (for risk parity)
    print("[3/7] Calculating volatility...")
    df = calculate_volatility(df, window=volatility_window)

    # Step 4: Filter universe
    print("[4/7] Filtering universe...")
    df = filter_universe(df, min_volume=min_volume, min_market_cap=min_market_cap)

    # Step 5: Prepare date range
    print("[5/7] Preparing backtest dates...")
    all_dates = sorted(df["date"].unique())

    if start_date:
        all_dates = [d for d in all_dates if d >= pd.to_datetime(start_date)]
    if end_date:
        all_dates = [d for d in all_dates if d <= pd.to_datetime(end_date)]

    # Filter to only dates with sufficient history
    min_start_date = df["date"].min() + timedelta(days=dw_window + directional_window)
    all_dates = [d for d in all_dates if d >= min_start_date]

    print(f"  Backtest period: {all_dates[0].date()} to {all_dates[-1].date()}")
    print(f"  Total days: {len(all_dates)}")

    # Step 6: Run backtest
    print("[6/7] Running backtest...")

    # Initialize portfolio tracking
    portfolio_values = []
    trades_log = []
    current_positions = {}  # {symbol: weight}
    portfolio_value = initial_capital
    cash = 0

    # Rebalance dates
    rebalance_dates = all_dates[::rebalance_days]

    print(f"  Number of rebalances: {len(rebalance_dates)}")

    for i, date in enumerate(all_dates):
        # Check if it's a rebalance date
        is_rebalance_date = date in rebalance_dates

        if is_rebalance_date:
            # Select new positions based on DW and regime
            selected = select_symbols_by_dw(
                df,
                date,
                strategy=strategy,
                num_quintiles=num_quintiles,
                long_percentile=long_percentile,
                short_percentile=short_percentile,
            )

            long_positions = calculate_position_weights(
                selected["long"], weighting_method, long_allocation * leverage
            )
            short_positions = calculate_position_weights(
                selected["short"], weighting_method, short_allocation * leverage
            )

            # Record new positions
            new_positions = {}

            for _, row in long_positions.iterrows():
                new_positions[row["symbol"]] = row["weight"]
                trades_log.append(
                    {
                        "date": date,
                        "symbol": row["symbol"],
                        "signal": "LONG",
                        "dw_stat": row.get("dw_stat", np.nan),
                        "dw_rank": row.get("dw_rank", np.nan),
                        "percentile": row.get("percentile", np.nan),
                        "weight": row["weight"],
                        "position_size": portfolio_value * row["weight"],
                        "regime": row.get("regime", "unknown"),
                        "behavior": row.get("behavior", "unknown"),
                    }
                )

            for _, row in short_positions.iterrows():
                new_positions[row["symbol"]] = -row["weight"]
                trades_log.append(
                    {
                        "date": date,
                        "symbol": row["symbol"],
                        "signal": "SHORT",
                        "dw_stat": row.get("dw_stat", np.nan),
                        "dw_rank": row.get("dw_rank", np.nan),
                        "percentile": row.get("percentile", np.nan),
                        "weight": -row["weight"],
                        "position_size": portfolio_value * row["weight"],
                        "regime": row.get("regime", "unknown"),
                        "behavior": row.get("behavior", "unknown"),
                    }
                )

            current_positions = new_positions

        # Calculate daily P&L (use NEXT day's returns to avoid lookahead bias)
        if i < len(all_dates) - 1:
            next_date = all_dates[i + 1]

            # Get returns for next day
            daily_returns = {}
            for symbol in current_positions.keys():
                symbol_data = df[(df["symbol"] == symbol) & (df["date"] == next_date)]
                if not symbol_data.empty:
                    daily_returns[symbol] = symbol_data["daily_return"].iloc[0]

            # Calculate portfolio return
            portfolio_return = 0
            for symbol, weight in current_positions.items():
                if symbol in daily_returns and not np.isnan(daily_returns[symbol]):
                    portfolio_return += weight * daily_returns[symbol]

            # Update portfolio value
            portfolio_value = portfolio_value * (1 + portfolio_return)

        # Record portfolio value
        long_exposure = sum([w * portfolio_value for w in current_positions.values() if w > 0])
        short_exposure = sum([w * portfolio_value for w in current_positions.values() if w < 0])

        # Get current regime
        date_data = df[df["date"] == date]
        current_regime = date_data["regime"].iloc[0] if not date_data.empty and "regime" in date_data.columns else "unknown"
        btc_pct = date_data[f"btc_{directional_window}d_pct"].iloc[0] if not date_data.empty else np.nan

        # Calculate average DW for long/short
        long_symbols = [s for s, w in current_positions.items() if w > 0]
        short_symbols = [s for s, w in current_positions.items() if w < 0]

        avg_dw_long = np.nan
        avg_dw_short = np.nan

        if long_symbols:
            long_dw_data = df[(df["date"] == date) & (df["symbol"].isin(long_symbols))]
            if not long_dw_data.empty:
                avg_dw_long = long_dw_data["dw_stat"].mean()

        if short_symbols:
            short_dw_data = df[(df["date"] == date) & (df["symbol"].isin(short_symbols))]
            if not short_dw_data.empty:
                avg_dw_short = short_dw_data["dw_stat"].mean()

        portfolio_values.append(
            {
                "date": date,
                "portfolio_value": portfolio_value,
                "cash": cash,
                "long_exposure": long_exposure,
                "short_exposure": short_exposure,
                "net_exposure": long_exposure + short_exposure,
                "gross_exposure": abs(long_exposure) + abs(short_exposure),
                "num_longs": len(long_symbols),
                "num_shorts": len(short_symbols),
                "avg_dw_long": avg_dw_long,
                "avg_dw_short": avg_dw_short,
                f"btc_{directional_window}d_pct": btc_pct,
                "regime": current_regime,
            }
        )

        # Progress update
        if (i + 1) % 100 == 0:
            print(f"  Processed {i+1}/{len(all_dates)} days ({(i+1)/len(all_dates)*100:.1f}%)")

    # Step 7: Calculate performance metrics
    print("[7/7] Calculating performance metrics...")

    portfolio_df = pd.DataFrame(portfolio_values)
    trades_df = pd.DataFrame(trades_log)

    # Calculate returns
    portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()

    # Calculate metrics
    total_return = (portfolio_df["portfolio_value"].iloc[-1] / initial_capital) - 1
    num_days = len(portfolio_df)
    annualized_return = (1 + total_return) ** (365 / num_days) - 1

    daily_returns = portfolio_df["daily_return"].dropna()
    annualized_volatility = daily_returns.std() * np.sqrt(365)
    sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility > 0 else 0

    # Downside deviation (for Sortino)
    downside_returns = daily_returns[daily_returns < 0]
    downside_volatility = downside_returns.std() * np.sqrt(365) if len(downside_returns) > 0 else 0
    sortino_ratio = annualized_return / downside_volatility if downside_volatility > 0 else 0

    # Maximum drawdown
    cumulative = (1 + daily_returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = drawdown.min()

    calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0

    # Win rate
    win_rate = (daily_returns > 0).sum() / len(daily_returns) if len(daily_returns) > 0 else 0

    # Regime statistics
    regime_stats = {}
    for regime in ["Strong Up", "Moderate Up", "Down", "Strong Down"]:
        regime_data = portfolio_df[portfolio_df["regime"] == regime]
        if len(regime_data) > 1:
            regime_returns = regime_data["daily_return"].dropna()
            if len(regime_returns) > 0:
                regime_total_return = (regime_data["portfolio_value"].iloc[-1] / regime_data["portfolio_value"].iloc[0]) - 1
                regime_ann_return = (1 + regime_total_return) ** (365 / len(regime_data)) - 1
                regime_vol = regime_returns.std() * np.sqrt(365)
                regime_sharpe = regime_ann_return / regime_vol if regime_vol > 0 else 0

                regime_cumulative = (1 + regime_returns).cumprod()
                regime_running_max = regime_cumulative.expanding().max()
                regime_drawdown = (regime_cumulative - regime_running_max) / regime_running_max
                regime_max_dd = regime_drawdown.min()

                regime_stats[regime] = {
                    "num_days": len(regime_data),
                    "pct_time": len(regime_data) / len(portfolio_df) * 100,
                    "total_return": regime_total_return,
                    "annualized_return": regime_ann_return,
                    "annualized_volatility": regime_vol,
                    "sharpe_ratio": regime_sharpe,
                    "max_drawdown": regime_max_dd,
                    "win_rate": (regime_returns > 0).sum() / len(regime_returns),
                }

    metrics = {
        "initial_capital": initial_capital,
        "final_value": portfolio_df["portfolio_value"].iloc[-1],
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_volatility,
        "sharpe_ratio": sharpe_ratio,
        "sortino_ratio": sortino_ratio,
        "max_drawdown": max_drawdown,
        "calmar_ratio": calmar_ratio,
        "win_rate": win_rate,
        "num_days": num_days,
        "num_rebalances": len(rebalance_dates),
        "avg_long_positions": portfolio_df["num_longs"].mean(),
        "avg_short_positions": portfolio_df["num_shorts"].mean(),
        "avg_dw_long": portfolio_df["avg_dw_long"].mean(),
        "avg_dw_short": portfolio_df["avg_dw_short"].mean(),
    }

    # Print summary
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)
    print(f"Initial Capital:        ${metrics['initial_capital']:,.2f}")
    print(f"Final Value:            ${metrics['final_value']:,.2f}")
    print(f"Total Return:           {metrics['total_return']*100:,.2f}%")
    print(f"Annualized Return:      {metrics['annualized_return']*100:,.2f}%")
    print(f"Annualized Volatility:  {metrics['annualized_volatility']*100:,.2f}%")
    print(f"Sharpe Ratio:           {metrics['sharpe_ratio']:.2f}")
    print(f"Sortino Ratio:          {metrics['sortino_ratio']:.2f}")
    print(f"Maximum Drawdown:       {metrics['max_drawdown']*100:,.2f}%")
    print(f"Calmar Ratio:           {metrics['calmar_ratio']:.2f}")
    print(f"Win Rate:               {metrics['win_rate']*100:,.2f}%")
    print(f"Avg Long Positions:     {metrics['avg_long_positions']:.1f}")
    print(f"Avg Short Positions:    {metrics['avg_short_positions']:.1f}")
    print(f"Avg DW Long:            {metrics['avg_dw_long']:.2f}")
    print(f"Avg DW Short:           {metrics['avg_dw_short']:.2f}")
    print("=" * 80 + "\n")

    if regime_stats:
        print("PERFORMANCE BY REGIME:")
        print("-" * 80)
        for regime, stats in regime_stats.items():
            print(f"\n{regime}:")
            print(f"  Days: {stats['num_days']} ({stats['pct_time']:.1f}% of time)")
            print(f"  Annualized Return: {stats['annualized_return']*100:.2f}%")
            print(f"  Sharpe Ratio: {stats['sharpe_ratio']:.2f}")
            print(f"  Max Drawdown: {stats['max_drawdown']*100:.2f}%")
            print(f"  Win Rate: {stats['win_rate']*100:.2f}%")
        print("-" * 80 + "\n")

    return {
        "portfolio_values": portfolio_df,
        "trades": trades_df,
        "metrics": metrics,
        "regime_stats": regime_stats,
    }


def save_results(results, output_prefix):
    """
    Save backtest results to CSV files.

    Args:
        results (dict): Backtest results dictionary
        output_prefix (str): Prefix for output files
    """
    output_dir = os.path.join(os.path.dirname(__file__), "../results")
    os.makedirs(output_dir, exist_ok=True)

    # Save portfolio values
    portfolio_file = os.path.join(output_dir, f"{output_prefix}_portfolio_values.csv")
    results["portfolio_values"].to_csv(portfolio_file, index=False)
    print(f"✓ Saved portfolio values to: {portfolio_file}")

    # Save trades
    trades_file = os.path.join(output_dir, f"{output_prefix}_trades.csv")
    results["trades"].to_csv(trades_file, index=False)
    print(f"✓ Saved trades to: {trades_file}")

    # Save metrics
    metrics_file = os.path.join(output_dir, f"{output_prefix}_metrics.csv")
    metrics_df = pd.DataFrame([results["metrics"]])
    metrics_df.to_csv(metrics_file, index=False)
    print(f"✓ Saved metrics to: {metrics_file}")

    # Save regime performance
    if results.get("regime_stats"):
        regime_file = os.path.join(output_dir, f"{output_prefix}_regime_performance.csv")
        regime_df = pd.DataFrame(results["regime_stats"]).T
        regime_df.to_csv(regime_file)
        print(f"✓ Saved regime performance to: {regime_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Backtest Durbin-Watson Factor Strategy with Directional Regime Filtering"
    )

    # Data parameters
    parser.add_argument(
        "--price-data",
        type=str,
        default="data/raw/combined_coinbase_coinmarketcap_daily.csv",
        help="Path to historical price data CSV",
    )

    # Strategy parameters
    parser.add_argument(
        "--strategy",
        type=str,
        default="regime_adaptive",
        choices=["regime_adaptive", "momentum_premium", "mean_reversion_premium", "long_momentum", "long_mean_reversion"],
        help="Strategy variant",
    )

    parser.add_argument("--dw-window", type=int, default=60, help="DW calculation window (days)")

    parser.add_argument(
        "--directional-window", type=int, default=5, help="Days for BTC directional % change"
    )

    parser.add_argument(
        "--directional-threshold", type=float, default=10, help="Threshold for strong moves (%%)"
    )

    parser.add_argument(
        "--volatility-window", type=int, default=30, help="Volatility window for risk parity (days)"
    )

    parser.add_argument(
        "--rebalance-days", type=int, default=7, help="Rebalance frequency (days)"
    )

    parser.add_argument("--num-quintiles", type=int, default=5, help="Number of DW quintiles")

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

    # Capital and allocation
    parser.add_argument(
        "--initial-capital", type=float, default=10000, help="Initial capital (USD)"
    )

    parser.add_argument("--leverage", type=float, default=1.0, help="Leverage multiplier")

    parser.add_argument(
        "--long-allocation", type=float, default=0.5, help="Allocation to long side (0-1)"
    )

    parser.add_argument(
        "--short-allocation", type=float, default=0.5, help="Allocation to short side (0-1)"
    )

    # Filters
    parser.add_argument(
        "--min-volume", type=float, default=5_000_000, help="Minimum 30d avg volume (USD)"
    )

    parser.add_argument(
        "--min-market-cap", type=float, default=50_000_000, help="Minimum market cap (USD)"
    )

    # Date range
    parser.add_argument("--start-date", type=str, default=None, help="Backtest start date (YYYY-MM-DD)")

    parser.add_argument("--end-date", type=str, default=None, help="Backtest end date (YYYY-MM-DD)")

    # Output
    parser.add_argument(
        "--output-prefix",
        type=str,
        default="backtest_dw_factor",
        help="Prefix for output files",
    )

    args = parser.parse_args()

    # Load data
    print(f"\nLoading data from: {args.price_data}")
    data = load_data(args.price_data)
    print(f"✓ Loaded {len(data)} rows, {data['symbol'].nunique()} unique symbols")

    # Run backtest
    results = run_backtest(
        data=data,
        strategy=args.strategy,
        dw_window=args.dw_window,
        directional_window=args.directional_window,
        directional_threshold=args.directional_threshold,
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
    )

    # Save results
    print("\nSaving results...")
    save_results(results, args.output_prefix)

    print("\n✓ Backtest complete!\n")


if __name__ == "__main__":
    main()
