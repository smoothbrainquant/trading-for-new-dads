"""
Run All Backtests and Calculate Performance Metrics

This script runs all available backtest strategies and calculates comprehensive
performance metrics including:
- Average return
- Average drawdown
- Standard deviation of returns
- Standard deviation of downside returns
- Sharpe ratio
- Sortino ratio
- Information coefficient

The results are compiled into a summary table for easy comparison.

PERFORMANCE OPTIMIZATIONS:
- Data is loaded once upfront and shared across all backtests (eliminates repetitive I/O)
- Backtest functions are imported conditionally (avoids loading heavy dependencies)
- scipy is only imported when kurtosis/trendline backtests are run
- statsmodels is only imported when ADF backtests are run
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime
import argparse

# Add parent directories to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "signals"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "data", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backtests", "scripts"))

# NOTE: Backtest functions are imported conditionally in main() to avoid
# loading heavy dependencies (scipy, statsmodels) unless needed


def calculate_comprehensive_metrics(portfolio_df, initial_capital, benchmark_returns=None):
    """
    Calculate comprehensive performance metrics.

    Args:
        portfolio_df (pd.DataFrame): DataFrame with portfolio values over time
        initial_capital (float): Initial portfolio capital
        benchmark_returns (pd.Series): Benchmark returns for IC calculation (optional)

    Returns:
        dict: Dictionary of comprehensive performance metrics
    """
    # Calculate returns
    portfolio_df = portfolio_df.copy()
    portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()
    portfolio_df["log_return"] = np.log(
        portfolio_df["portfolio_value"] / portfolio_df["portfolio_value"].shift(1)
    )

    # Filter out NaN values
    daily_returns = portfolio_df["daily_return"].dropna()
    log_returns = portfolio_df["log_return"].dropna()

    if len(daily_returns) == 0:
        return None

    # --- Basic Return Metrics ---
    final_value = portfolio_df["portfolio_value"].iloc[-1]
    total_return = (final_value - initial_capital) / initial_capital

    num_days = len(portfolio_df)
    years = num_days / 365.25
    annualized_return = (final_value / initial_capital) ** (1 / years) - 1 if years > 0 else 0

    # Average daily return (annualized)
    avg_daily_return = daily_returns.mean()
    avg_annual_return = (1 + avg_daily_return) ** 365 - 1

    # --- Volatility Metrics ---
    # Standard deviation of returns (annualized)
    daily_vol = log_returns.std()
    annualized_vol = daily_vol * np.sqrt(365)

    # Downside deviation (annualized) - only negative returns
    downside_returns = log_returns[log_returns < 0]
    downside_vol = downside_returns.std() if len(downside_returns) > 0 else 0
    annualized_downside_vol = downside_vol * np.sqrt(365)

    # --- Drawdown Metrics ---
    # Calculate running drawdown
    cumulative_returns = (1 + daily_returns.fillna(0)).cumprod()
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max

    # Maximum drawdown
    max_drawdown = drawdown.min()

    # Average drawdown (average of all drawdown periods)
    # A drawdown period is when portfolio is below previous peak
    in_drawdown = drawdown < 0
    avg_drawdown = drawdown[in_drawdown].mean() if in_drawdown.any() else 0

    # --- Risk-Adjusted Return Metrics ---
    # Sharpe ratio (assuming 0% risk-free rate)
    sharpe_ratio = annualized_return / annualized_vol if annualized_vol > 0 else 0

    # Sortino ratio (using downside deviation)
    sortino_ratio = (
        annualized_return / annualized_downside_vol if annualized_downside_vol > 0 else 0
    )

    # --- Information Coefficient ---
    # IC measures correlation between predicted and actual returns
    # For strategies, we can calculate autocorrelation of returns as a signal quality measure
    # Alternatively, if we have benchmark returns, we can calculate tracking error
    information_coefficient = None
    if benchmark_returns is not None:
        # Calculate IC as correlation between strategy returns and benchmark
        try:
            # Align returns
            aligned_returns = pd.concat([daily_returns, benchmark_returns], axis=1, join="inner")
            if len(aligned_returns) > 1:
                information_coefficient = aligned_returns.corr().iloc[0, 1]
        except:
            pass

    # If no benchmark, calculate return predictability using autocorrelation
    if information_coefficient is None:
        # Use 1-day autocorrelation as a measure of signal quality
        if len(daily_returns) > 1:
            information_coefficient = daily_returns.autocorr(lag=1)

    # --- Additional Metrics ---
    # Win rate
    positive_days = (daily_returns > 0).sum()
    win_rate = positive_days / len(daily_returns) if len(daily_returns) > 0 else 0

    # Calmar ratio (annualized return / max drawdown)
    calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0

    metrics = {
        "avg_return": avg_annual_return,
        "avg_drawdown": avg_drawdown,
        "stdev_return": annualized_vol,
        "stdev_downside_return": annualized_downside_vol,
        "sharpe_ratio": sharpe_ratio,
        "sortino_ratio": sortino_ratio,
        "information_coefficient": (
            information_coefficient if information_coefficient is not None else 0
        ),
        # Additional useful metrics
        "total_return": total_return,
        "annualized_return": annualized_return,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "calmar_ratio": calmar_ratio,
        "num_days": num_days,
        "final_value": final_value,
    }

    return metrics


def load_all_data(args):
    """
    Load all data files once to avoid repetitive I/O.
    
    Args:
        args: Command line arguments with file paths
        
    Returns:
        dict: Dictionary with all loaded data
    """
    print("\n" + "=" * 80)
    print("LOADING DATA (ONE-TIME LOAD)")
    print("=" * 80)
    
    data = {}
    
    # Load price data
    if os.path.exists(args.data_file):
        print(f"Loading price data from {args.data_file}...")
        df = pd.read_csv(args.data_file)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
        data["price_data"] = df
        print(f"  ? Loaded {len(df)} rows, {df['symbol'].nunique()} symbols")
    else:
        print(f"  ? Price data file not found: {args.data_file}")
        data["price_data"] = None
    
    # Load market cap data
    if os.path.exists(args.marketcap_file):
        print(f"Loading market cap data from {args.marketcap_file}...")
        df = pd.read_csv(args.marketcap_file)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        # Normalize column names
        if "Market Cap" in df.columns:
            df = df.rename(columns={"Market Cap": "market_cap", "Symbol": "symbol"})
        if "symbol" not in df.columns and "Symbol" in df.columns:
            df = df.rename(columns={"Symbol": "symbol"})
        data["marketcap_data"] = df
        print(f"  ? Loaded {len(df)} rows")
    else:
        print(f"  ? Market cap file not found: {args.marketcap_file}")
        data["marketcap_data"] = None
    
    # Load funding rates data
    if os.path.exists(args.funding_rates_file):
        print(f"Loading funding rates from {args.funding_rates_file}...")
        df = pd.read_csv(args.funding_rates_file)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        elif "timestamp" in df.columns:
            df["date"] = pd.to_datetime(df["timestamp"])
        data["funding_data"] = df
        print(f"  ? Loaded {len(df)} rows")
    else:
        print(f"  ? Funding rates file not found: {args.funding_rates_file}")
        data["funding_data"] = None
    
    # Load OI data (if needed)
    if hasattr(args, 'oi_data_file') and os.path.exists(args.oi_data_file):
        print(f"Loading OI data from {args.oi_data_file}...")
        df = pd.read_csv(args.oi_data_file)
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        data["oi_data"] = df
        print(f"  ? Loaded {len(df)} rows")
    else:
        data["oi_data"] = None
    
    print("=" * 80)
    print("DATA LOADING COMPLETE\n")
    
    return data


def run_breakout_backtest(price_data, **kwargs):
    """Run breakout signal backtest."""
    print("\n" + "=" * 80)
    print("Running Breakout Signal Backtest")
    print("=" * 80)

    try:
        # Import backtest function
        from backtests.scripts.backtest_breakout_signals import backtest as backtest_breakout
        
        results = backtest_breakout(
            data=price_data,
            entry_window=kwargs.get("entry_window", 50),
            exit_window=kwargs.get("exit_window", 70),
            volatility_window=kwargs.get("volatility_window", 30),
            initial_capital=kwargs.get("initial_capital", 10000),
            leverage=kwargs.get("leverage", 1.0),
            long_allocation=kwargs.get("long_allocation", 0.5),
            short_allocation=kwargs.get("short_allocation", 0.5),
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
        )

        # Calculate comprehensive metrics
        metrics = calculate_comprehensive_metrics(
            results["portfolio_values"], kwargs.get("initial_capital", 10000)
        )
        
        # Extract daily returns
        portfolio_df = results["portfolio_values"].copy()
        portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()
        daily_returns = portfolio_df[["date", "daily_return"]].copy()
        daily_returns.columns = ["date", "Breakout Signal"]

        return {
            "strategy": "Breakout Signal",
            "description": f"Entry: {kwargs.get('entry_window', 50)}d, Exit: {kwargs.get('exit_window', 70)}d",
            "metrics": metrics,
            "results": results,
            "daily_returns": daily_returns,
        }
    except Exception as e:
        print(f"Error in Breakout backtest: {e}")
        import traceback

        traceback.print_exc()
        return None


def run_mean_reversion_backtest(price_data, **kwargs):
    """Run mean reversion backtest."""
    print("\n" + "=" * 80)
    print("Running Mean Reversion Backtest")
    print("=" * 80)

    try:
        # Import backtest functions
        from backtests.scripts.backtest_mean_reversion import (
            calculate_z_scores,
            categorize_moves,
            analyze_mean_reversion,
        )
        
        data = price_data

        # Calculate z-scores
        data_with_zscores = calculate_z_scores(
            data, lookback_window=kwargs.get("lookback_window", 30)
        )

        # Categorize moves
        data_categorized = categorize_moves(
            data_with_zscores,
            return_threshold=kwargs.get("return_threshold", 1.0),
            volume_threshold=kwargs.get("volume_threshold", 1.0),
        )

        # Analyze mean reversion
        results = analyze_mean_reversion(data_categorized)

        # Create a synthetic portfolio based on mean reversion signals
        # We'll use the directional category with best performance
        directional_stats = results["by_directional_category"]

        if not directional_stats.empty:
            best_strategy = directional_stats.loc[directional_stats["mean_forward_return"].idxmax()]

            # Create portfolio from detailed data
            detailed_data = results["detailed_data"]

            # Filter for best strategy category
            strategy_data = detailed_data[
                detailed_data["category_directional"] == best_strategy["category"]
            ].copy()

            if len(strategy_data) > 0:
                # Create cumulative portfolio value
                initial_capital = kwargs.get("initial_capital", 10000)
                strategy_data = strategy_data.sort_values("date")
                strategy_data["cumulative_return"] = (
                    1 + strategy_data["forward_1d_return"].fillna(0)
                ).cumprod()
                strategy_data["portfolio_value"] = (
                    initial_capital * strategy_data["cumulative_return"]
                )

                # Calculate metrics
                portfolio_df = strategy_data[["date", "portfolio_value"]].copy()
                metrics = calculate_comprehensive_metrics(portfolio_df, initial_capital)
                
                # Extract daily returns
                portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()
                daily_returns = portfolio_df[["date", "daily_return"]].copy()
                daily_returns.columns = ["date", "Mean Reversion"]

                return {
                    "strategy": "Mean Reversion",
                    "description": f"Best category: {best_strategy['category']}",
                    "metrics": metrics,
                    "results": results,
                    "daily_returns": daily_returns,
                }

        print("Insufficient data for mean reversion backtest")
        return None

    except Exception as e:
        print(f"Error in Mean Reversion backtest: {e}")
        import traceback

        traceback.print_exc()
        return None


def run_size_factor_backtest(price_data, marketcap_data, **kwargs):
    """Run size factor backtest."""
    print("\n" + "=" * 80)
    print("Running Size Factor Backtest")
    print("=" * 80)

    try:
        # Import backtest function
        from backtests.scripts.backtest_size_factor import backtest as backtest_size
        
        if marketcap_data is None or len(marketcap_data) == 0:
            print("No market cap data available")
            return None

        results = backtest_size(
            price_data=price_data,
            marketcap_data=marketcap_data,
            strategy=kwargs.get("strategy", "long_small_short_large"),
            num_buckets=kwargs.get("num_buckets", 5),
            volatility_window=kwargs.get("volatility_window", 30),
            rebalance_days=kwargs.get("rebalance_days", 7),
            initial_capital=kwargs.get("initial_capital", 10000),
            leverage=kwargs.get("leverage", 1.0),
            long_allocation=kwargs.get("long_allocation", 0.5),
            short_allocation=kwargs.get("short_allocation", 0.5),
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
        )

        # Calculate comprehensive metrics
        metrics = calculate_comprehensive_metrics(
            results["portfolio_values"], kwargs.get("initial_capital", 10000)
        )
        
        # Extract daily returns
        portfolio_df = results["portfolio_values"].copy()
        portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()
        daily_returns = portfolio_df[["date", "daily_return"]].copy()
        daily_returns.columns = ["date", "Size Factor"]

        return {
            "strategy": "Size Factor",
            "description": f"Strategy: {kwargs.get('strategy', 'long_small_short_large')}",
            "metrics": metrics,
            "results": results,
            "daily_returns": daily_returns,
        }
    except Exception as e:
        print(f"Error in Size Factor backtest: {e}")
        import traceback

        traceback.print_exc()
        return None


def run_carry_factor_backtest(price_data, funding_data, **kwargs):
    """Run carry factor backtest."""
    print("\n" + "=" * 80)
    print("Running Carry Factor Backtest")
    print("=" * 80)

    try:
        # Import backtest function
        from backtests.scripts.backtest_carry_factor import backtest as backtest_carry

        if funding_data is None or len(funding_data) == 0:
            print("No funding rates data available")
            return None

        results = backtest_carry(
            price_data=price_data,
            funding_data=funding_data,
            top_n=kwargs.get("top_n", 10),
            bottom_n=kwargs.get("bottom_n", 10),
            volatility_window=kwargs.get("volatility_window", 30),
            rebalance_days=kwargs.get("rebalance_days", 7),
            initial_capital=kwargs.get("initial_capital", 10000),
            leverage=kwargs.get("leverage", 1.0),
            long_allocation=kwargs.get("long_allocation", 0.5),
            short_allocation=kwargs.get("short_allocation", 0.5),
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
        )

        # Calculate comprehensive metrics
        metrics = calculate_comprehensive_metrics(
            results["portfolio_values"], kwargs.get("initial_capital", 10000)
        )
        
        # Extract daily returns
        portfolio_df = results["portfolio_values"].copy()
        portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()
        daily_returns = portfolio_df[["date", "daily_return"]].copy()
        daily_returns.columns = ["date", "Carry Factor"]

        return {
            "strategy": "Carry Factor",
            "description": f"Top {kwargs.get('top_n', 10)} short, Bottom {kwargs.get('bottom_n', 10)} long",
            "metrics": metrics,
            "results": results,
            "daily_returns": daily_returns,
        }
    except Exception as e:
        print(f"Error in Carry Factor backtest: {e}")
        import traceback

        traceback.print_exc()
        return None


def run_days_from_high_backtest(price_data, **kwargs):
    """Run days from high backtest."""
    print("\n" + "=" * 80)
    print("Running Days from High Backtest")
    print("=" * 80)

    try:
        # Import backtest function
        from backtests.scripts.backtest_20d_from_200d_high import backtest as backtest_days_from_high
        
        results = backtest_days_from_high(
            data=price_data,
            days_threshold=kwargs.get("days_threshold", 20),
            volatility_window=kwargs.get("volatility_window", 30),
            initial_capital=kwargs.get("initial_capital", 10000),
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
        )

        # Calculate comprehensive metrics
        metrics = calculate_comprehensive_metrics(
            results["portfolio_values"], kwargs.get("initial_capital", 10000)
        )
        
        # Extract daily returns
        portfolio_df = results["portfolio_values"].copy()
        portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()
        daily_returns = portfolio_df[["date", "daily_return"]].copy()
        daily_returns.columns = ["date", "Days from High"]

        return {
            "strategy": "Days from High",
            "description": f"Max {kwargs.get('days_threshold', 20)} days from 200d high",
            "metrics": metrics,
            "results": results,
            "daily_returns": daily_returns,
        }
    except Exception as e:
        print(f"Error in Days from High backtest: {e}")
        import traceback

        traceback.print_exc()
        return None


# def run_oi_divergence_backtest(data_file, oi_data_file, **kwargs):  # Removed: OI data not used
#     """Run OI divergence backtest."""
#     print("\n" + "=" * 80)
#     print("Running OI Divergence Backtest")
#     print("=" * 80)
#
#     try:
#         price_data = load_oi_price_data(data_file)
#         oi_data = load_oi_data(oi_data_file)
#
#         if oi_data is None or len(oi_data) == 0:
#             print("No OI data available")
#             return None
#
#         mode = kwargs.get("oi_mode", "divergence")
#         cfg = OIBacktestConfig(
#             lookback=kwargs.get("lookback", 30),
#             volatility_window=kwargs.get("volatility_window", 30),
#             rebalance_days=kwargs.get("rebalance_days", 7),
#             top_n=kwargs.get("top_n", 10),
#             bottom_n=kwargs.get("bottom_n", 10),
#             mode=mode,
#             initial_capital=kwargs.get("initial_capital", 10000),
#         )
#
#         results = backtest_oi_divergence(price_df=price_data, oi_df=oi_data, cfg=cfg)
#
#         # Calculate comprehensive metrics
#         metrics = calculate_comprehensive_metrics(
#             results["portfolio_values"], kwargs.get("initial_capital", 10000)
#         )
#
#         return {
#             "strategy": f"OI Divergence ({mode})",
#             "description": f"Mode: {mode}, Top {kwargs.get('top_n', 10)}, Bottom {kwargs.get('bottom_n', 10)}",
#             "metrics": metrics,
#             "results": results,
#         }
#     except Exception as e:
#         print(f"Error in OI Divergence backtest: {e}")
#         import traceback
#
#         traceback.print_exc()
#         return None


def run_volatility_factor_backtest(price_data, **kwargs):
    """Run volatility factor backtest."""
    print("\n" + "=" * 80)
    print("Running Volatility Factor Backtest")
    print("=" * 80)

    try:
        # Import backtest function
        from backtests.scripts.backtest_volatility_factor import backtest as backtest_volatility

        results = backtest_volatility(
            price_data=price_data,
            strategy=kwargs.get("strategy", "long_low_short_high"),
            num_quintiles=kwargs.get("num_quintiles", 5),
            volatility_window=kwargs.get("volatility_window", 30),
            rebalance_days=kwargs.get("rebalance_days", 7),
            initial_capital=kwargs.get("initial_capital", 10000),
            leverage=kwargs.get("leverage", 1.0),
            long_allocation=kwargs.get("long_allocation", 0.5),
            short_allocation=kwargs.get("short_allocation", 0.5),
            weighting_method=kwargs.get("weighting_method", "equal"),
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
        )

        # Calculate comprehensive metrics
        metrics = calculate_comprehensive_metrics(
            results["portfolio_values"], kwargs.get("initial_capital", 10000)
        )
        
        # Extract daily returns
        portfolio_df = results["portfolio_values"].copy()
        portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()
        daily_returns = portfolio_df[["date", "daily_return"]].copy()
        daily_returns.columns = ["date", "Volatility Factor"]

        return {
            "strategy": "Volatility Factor",
            "description": f"Strategy: {kwargs.get('strategy', 'long_low_short_high')}",
            "metrics": metrics,
            "results": results,
            "daily_returns": daily_returns,
        }
    except Exception as e:
        print(f"Error in Volatility Factor backtest: {e}")
        import traceback

        traceback.print_exc()
        return None


def run_kurtosis_factor_backtest(price_data, **kwargs):
    """Run kurtosis factor backtest."""
    print("\n" + "=" * 80)
    print("Running Kurtosis Factor Backtest")
    print("=" * 80)

    try:
        # Import backtest function (requires scipy)
        from backtests.scripts.backtest_kurtosis_factor import backtest as backtest_kurtosis

        results = backtest_kurtosis(
            price_data=price_data,
            strategy=kwargs.get("strategy", "momentum"),
            kurtosis_window=kwargs.get("kurtosis_window", 30),
            volatility_window=kwargs.get("volatility_window", 30),
            rebalance_days=kwargs.get("rebalance_days", 14),
            initial_capital=kwargs.get("initial_capital", 10000),
            leverage=kwargs.get("leverage", 1.0),
            long_allocation=kwargs.get("long_allocation", 0.5),
            short_allocation=kwargs.get("short_allocation", 0.5),
            weighting=kwargs.get("weighting", "risk_parity"),
            long_percentile=kwargs.get("long_percentile", 20),
            short_percentile=kwargs.get("short_percentile", 80),
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
        )

        # Calculate comprehensive metrics
        metrics = calculate_comprehensive_metrics(
            results["portfolio_values"], kwargs.get("initial_capital", 10000)
        )
        
        # Extract daily returns
        portfolio_df = results["portfolio_values"].copy()
        portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()
        daily_returns = portfolio_df[["date", "daily_return"]].copy()
        daily_returns.columns = ["date", "Kurtosis Factor"]

        return {
            "strategy": "Kurtosis Factor",
            "description": f"Strategy: {kwargs.get('strategy', 'momentum')}, Rebal: {kwargs.get('rebalance_days', 14)}d",
            "metrics": metrics,
            "results": results,
            "daily_returns": daily_returns,
        }
    except Exception as e:
        print(f"Error in Kurtosis Factor backtest: {e}")
        import traceback

        traceback.print_exc()
        return None


def run_beta_factor_backtest(price_data, **kwargs):
    """Run beta factor backtest."""
    print("\n" + "=" * 80)
    print("Running Beta Factor Backtest")
    print("=" * 80)

    try:
        # Import backtest function
        from backtests.scripts.backtest_beta_factor import run_backtest as backtest_beta

        results = backtest_beta(
            data=price_data,
            strategy=kwargs.get("strategy", "betting_against_beta"),
            beta_window=kwargs.get("beta_window", 90),
            volatility_window=kwargs.get("volatility_window", 30),
            rebalance_days=kwargs.get("rebalance_days", 1),
            num_quintiles=kwargs.get("num_quintiles", 5),
            long_percentile=kwargs.get("long_percentile", 20),
            short_percentile=kwargs.get("short_percentile", 80),
            weighting_method=kwargs.get("weighting_method", "risk_parity"),
            initial_capital=kwargs.get("initial_capital", 10000),
            leverage=kwargs.get("leverage", 1.0),
            long_allocation=kwargs.get("long_allocation", 0.5),
            short_allocation=kwargs.get("short_allocation", 0.5),
            min_volume=kwargs.get("min_volume", 5000000),
            min_market_cap=kwargs.get("min_market_cap", 50000000),
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
        )

        # Calculate comprehensive metrics
        metrics = calculate_comprehensive_metrics(
            results["portfolio_values"], kwargs.get("initial_capital", 10000)
        )
        
        # Extract daily returns
        portfolio_df = results["portfolio_values"].copy()
        portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()
        daily_returns = portfolio_df[["date", "daily_return"]].copy()
        daily_returns.columns = ["date", "Beta Factor (BAB)"]

        return {
            "strategy": "Beta Factor (BAB)",
            "description": f"Strategy: BAB, Weighting: {kwargs.get('weighting_method', 'risk_parity')}, Rebal: {kwargs.get('rebalance_days', 1)}d",
            "metrics": metrics,
            "results": results,
            "daily_returns": daily_returns,
        }
    except Exception as e:
        print(f"Error in Beta Factor backtest: {e}")
        import traceback

        traceback.print_exc()
        return None


# def run_adf_factor_backtest(data_file, **kwargs):
#     """Run ADF factor backtest."""
#     print("\n" + "=" * 80)
#     print(f"Running ADF Factor Backtest - {kwargs.get('strategy', 'mean_reversion_premium')}")
#     print("=" * 80)
#
#     try:
#         price_data = load_data(data_file)
#
#         results = run_adf_backtest(
#             data=price_data,
#             strategy=kwargs.get("strategy", "mean_reversion_premium"),
#             adf_window=kwargs.get("adf_window", 60),
#             regression=kwargs.get("regression", "ct"),
#             volatility_window=kwargs.get("volatility_window", 30),
#             rebalance_days=kwargs.get("rebalance_days", 7),
#             num_quintiles=kwargs.get("num_quintiles", 5),
#             long_percentile=kwargs.get("long_percentile", 20),
#             short_percentile=kwargs.get("short_percentile", 80),
#             weighting_method=kwargs.get("weighting_method", "equal_weight"),
#             initial_capital=kwargs.get("initial_capital", 10000),
#             leverage=kwargs.get("leverage", 1.0),
#             long_allocation=kwargs.get("long_allocation", 0.5),
#             short_allocation=kwargs.get("short_allocation", 0.5),
#             min_volume=kwargs.get("min_volume", 5_000_000),
#             min_market_cap=kwargs.get("min_market_cap", 50_000_000),
#             start_date=kwargs.get("start_date"),
#             end_date=kwargs.get("end_date"),
#         )
#
#         # Calculate comprehensive metrics
#         metrics = calculate_comprehensive_metrics(
#             results["portfolio_values"], kwargs.get("initial_capital", 10000)
#         )
#         
#         # Extract daily returns
#         portfolio_df = results["portfolio_values"].copy()
#         portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()
#         daily_returns = portfolio_df[["date", "daily_return"]].copy()
#         strategy_name = f'ADF Factor ({kwargs.get("strategy", "mean_reversion_premium")})'
#         daily_returns.columns = ["date", strategy_name]
#
#         return {
#             "strategy": strategy_name,
#             "description": f"ADF window: {kwargs.get('adf_window', 60)}d, Rebal: {kwargs.get('rebalance_days', 7)}d",
#             "metrics": metrics,
#             "results": results,
#             "daily_returns": daily_returns,
#         }
#     except Exception as e:
#         print(f"Error in ADF Factor backtest: {e}")
#         import traceback
#
#         traceback.print_exc()
#         return None


def combine_daily_returns(all_results):
    """
    Combine daily returns from all strategies into a single DataFrame.

    Args:
        all_results (list): List of dictionaries with backtest results

    Returns:
        pd.DataFrame: DataFrame with date column and one column per strategy
    """
    if not all_results:
        return pd.DataFrame()

    # Collect all daily returns DataFrames
    daily_returns_list = []
    for result in all_results:
        if result is None or "daily_returns" not in result:
            continue
        daily_returns_list.append(result["daily_returns"])

    if not daily_returns_list:
        return pd.DataFrame()

    # Merge all daily returns on date
    combined_df = daily_returns_list[0].copy()
    for df in daily_returns_list[1:]:
        combined_df = pd.merge(combined_df, df, on="date", how="outer")

    # Sort by date
    combined_df = combined_df.sort_values("date").reset_index(drop=True)

    return combined_df


def create_summary_table(all_results):
    """
    Create summary table with all metrics.

    Args:
        all_results (list): List of dictionaries with backtest results

    Returns:
        pd.DataFrame: Summary table with all metrics
    """
    summary_data = []

    for result in all_results:
        if result is None or result["metrics"] is None:
            continue

        metrics = result["metrics"]

        summary_data.append(
            {
                "Strategy": result["strategy"],
                "Description": result["description"],
                "Avg Return": metrics["avg_return"],
                "Avg Drawdown": metrics["avg_drawdown"],
                "Stdev Return": metrics["stdev_return"],
                "Stdev Downside Return": metrics["stdev_downside_return"],
                "Sharpe Ratio": metrics["sharpe_ratio"],
                "Sortino Ratio": metrics["sortino_ratio"],
                "Information Coefficient": metrics["information_coefficient"],
                "Max Drawdown": metrics["max_drawdown"],
                "Win Rate": metrics["win_rate"],
                "Calmar Ratio": metrics["calmar_ratio"],
                "Total Return": metrics["total_return"],
                "Final Value": metrics["final_value"],
                "Num Days": metrics["num_days"],
            }
        )

    summary_df = pd.DataFrame(summary_data)
    return summary_df


def calculate_sharpe_weights_with_floor(summary_df, min_weight=0.05):
    """
    Calculate portfolio weights based on Sharpe ratios with a minimum weight floor.
    ALL strategies receive at least min_weight allocation (including negative Sharpe).

    Args:
        summary_df (pd.DataFrame): Summary DataFrame with backtest results
        min_weight (float): Minimum weight per strategy (default 5%)

    Returns:
        pd.DataFrame: DataFrame with strategies and their weights
    """
    if summary_df.empty:
        return None

    # Include ALL strategies (both positive and negative Sharpe)
    all_strategies = summary_df.copy()

    # Separate positive and negative Sharpe strategies
    positive_sharpe = all_strategies[all_strategies["Sharpe Ratio"] > 0].copy()
    negative_sharpe = all_strategies[all_strategies["Sharpe Ratio"] <= 0].copy()

    # Calculate initial weights for positive Sharpe strategies
    if len(positive_sharpe) > 0:
        total_sharpe = positive_sharpe["Sharpe Ratio"].sum()
        positive_sharpe["Initial_Weight"] = positive_sharpe["Sharpe Ratio"] / total_sharpe

        # Scale positive weights to leave room for negative strategies
        # Reserve min_weight for each negative strategy
        reserved_weight = len(negative_sharpe) * min_weight
        available_weight = 1.0 - reserved_weight
        positive_sharpe["Initial_Weight"] = positive_sharpe["Initial_Weight"] * available_weight
    else:
        # If no positive Sharpe strategies, distribute equally
        positive_sharpe["Initial_Weight"] = 0

    # Assign min_weight to negative Sharpe strategies
    negative_sharpe["Initial_Weight"] = min_weight

    # Combine both groups
    all_weights = pd.concat([positive_sharpe, negative_sharpe])

    # Apply floor to all strategies
    all_weights["Weight"] = all_weights["Initial_Weight"].apply(lambda x: max(x, min_weight))

    # Renormalize to sum to 1.0
    weight_sum = all_weights["Weight"].sum()
    all_weights["Weight"] = all_weights["Weight"] / weight_sum

    # Create output DataFrame
    weights_df = all_weights[["Strategy", "Description", "Sharpe Ratio", "Weight"]].copy()
    weights_df["Weight_Pct"] = weights_df["Weight"] * 100

    # Sort by weight descending
    weights_df = weights_df.sort_values("Weight", ascending=False)

    return weights_df


def print_sharpe_weights(weights_df, summary_df, min_weight=0.05):
    """Print formatted Sharpe-based weights table."""
    print("\n" + "=" * 120)
    print("SHARPE-BASED PORTFOLIO WEIGHTS")
    print("=" * 120)

    if weights_df is None or weights_df.empty:
        print("\nNo weights to display")
        return

    weight_sum = weights_df["Weight"].sum()

    print(f"\nWeighting Method: All strategies with {min_weight*100:.0f}% minimum floor")
    print(f"Strategies included: {len(weights_df)} (ALL strategies)")
    print(f"Total weight: {weight_sum:.6f} (should be 1.0)")

    # Count positive and negative Sharpe strategies
    positive_count = (weights_df["Sharpe Ratio"] > 0).sum()
    negative_count = (weights_df["Sharpe Ratio"] <= 0).sum()
    print(f"  - Positive Sharpe: {positive_count} strategies")
    print(f"  - Negative Sharpe: {negative_count} strategies (minimum {min_weight*100:.0f}% each)")

    print("\nPortfolio Allocation:")
    print("-" * 120)
    for idx, row in weights_df.iterrows():
        sharpe_indicator = "?" if row["Sharpe Ratio"] > 0 else "?"
        print(
            f"  {sharpe_indicator} {row['Strategy']:<18} | Sharpe: {row['Sharpe Ratio']:>8.3f} | Weight: {row['Weight']:>8.4f} ({row['Weight_Pct']:>6.2f}%)"
        )

    print("\n" + "-" * 120)
    print(f"  {'TOTAL':<20} | {'':>8} | Weight: {weight_sum:>8.4f} ({weight_sum*100:>6.2f}%)")

    # Calculate expected portfolio metrics (weighted average)
    merged = summary_df.merge(weights_df[["Strategy", "Weight"]], on="Strategy", how="inner")

    expected_return = (merged["Avg Return"] * merged["Weight"]).sum()
    expected_sharpe = (merged["Sharpe Ratio"] * merged["Weight"]).sum()
    expected_sortino = (merged["Sortino Ratio"] * merged["Weight"]).sum()
    expected_max_dd = (merged["Max Drawdown"] * merged["Weight"]).sum()

    print("\nExpected Portfolio Metrics (Weighted Average):")
    print("-" * 120)
    print(f"  Expected Return:        {expected_return:>8.2%}")
    print(f"  Expected Sharpe Ratio:  {expected_sharpe:>8.3f}")
    print(f"  Expected Sortino Ratio: {expected_sortino:>8.3f}")
    print(f"  Expected Max Drawdown:  {expected_max_dd:>8.2%}")
    print("=" * 120)


def print_summary_table(summary_df):
    """Print formatted summary table."""
    print("\n" + "=" * 120)
    print("BACKTEST PERFORMANCE SUMMARY")
    print("=" * 120)

    if summary_df.empty:
        print("No results to display")
        return

    # Format the display
    display_df = summary_df.copy()

    # Format percentage columns
    pct_cols = [
        "Avg Return",
        "Avg Drawdown",
        "Stdev Return",
        "Stdev Downside Return",
        "Max Drawdown",
        "Win Rate",
        "Total Return",
    ]
    for col in pct_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"{x:.2%}")

    # Format ratio columns
    ratio_cols = ["Sharpe Ratio", "Sortino Ratio", "Calmar Ratio", "Information Coefficient"]
    for col in ratio_cols:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"{x:.3f}")

    # Format value columns
    if "Final Value" in display_df.columns:
        display_df["Final Value"] = display_df["Final Value"].apply(lambda x: f"${x:,.2f}")

    # Print main metrics table
    main_metrics = [
        "Strategy",
        "Description",
        "Avg Return",
        "Avg Drawdown",
        "Stdev Return",
        "Stdev Downside Return",
        "Sharpe Ratio",
        "Sortino Ratio",
        "Information Coefficient",
    ]

    print("\nCore Performance Metrics:")
    print(display_df[main_metrics].to_string(index=False))

    # Print additional metrics
    print("\n" + "=" * 120)
    print("Additional Metrics:")
    additional_metrics = [
        "Strategy",
        "Max Drawdown",
        "Win Rate",
        "Calmar Ratio",
        "Total Return",
        "Final Value",
        "Num Days",
    ]
    print(display_df[additional_metrics].to_string(index=False))

    print("\n" + "=" * 120)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Run all backtests and generate comprehensive performance metrics",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--data-file",
        type=str,
        default="data/raw/combined_coinbase_coinmarketcap_daily.csv",
        help="Path to historical OHLCV data CSV file",
    )
    parser.add_argument(
        "--marketcap-file",
        type=str,
        default="data/raw/coinmarketcap_historical_all_snapshots.csv",
        help="Path to market cap data CSV file",
    )
    parser.add_argument(
        "--funding-rates-file",
        type=str,
        default="data/raw/historical_funding_rates_top100_ALL_HISTORY_20251028_002456.csv",
        help="Path to funding rates data CSV file (top 100 coins, 2020-present)",
    )
    parser.add_argument(
        "--oi-data-file",
        type=str,
        default="data/raw/historical_open_interest_all_perps_since2020_20251027_042634.csv",
        help="Path to open interest data CSV file",
    )
    parser.add_argument(
        "--initial-capital", type=float, default=10000, help="Initial portfolio capital in USD"
    )
    parser.add_argument(
        "--start-date", type=str, default="2023-01-01", help="Start date for backtest (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date", type=str, default=None, help="End date for backtest (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="backtests/results/all_backtests_summary.csv",
        help="Output file for summary table",
    )
    parser.add_argument(
        "--run-breakout", action="store_true", default=True, help="Run breakout signal backtest"
    )
    parser.add_argument(
        "--run-mean-reversion",
        action="store_true",
        default=True,
        help="Run mean reversion backtest",
    )
    parser.add_argument(
        "--run-size", action="store_true", default=True, help="Run size factor backtest"
    )
    parser.add_argument(
        "--run-carry", action="store_true", default=True, help="Run carry factor backtest"
    )
    parser.add_argument(
        "--run-days-from-high",
        action="store_true",
        default=True,
        help="Run days from high backtest",
    )
    parser.add_argument(
        "--run-oi-divergence", action="store_true", default=True, help="Run OI divergence backtest"
    )
    parser.add_argument(
        "--oi-mode",
        type=str,
        default="divergence",
        choices=["divergence", "trend"],
        help="OI divergence mode: divergence (contrarian) or trend (momentum)",
    )
    parser.add_argument(
        "--run-volatility", action="store_true", default=True, help="Run volatility factor backtest"
    )
    parser.add_argument(
        "--volatility-strategy",
        type=str,
        default="long_low_short_high",
        choices=["long_low_short_high", "long_low_vol", "long_high_vol", "long_high_short_low"],
        help="Volatility factor strategy type",
    )
    parser.add_argument(
        "--run-kurtosis", action="store_true", default=True, help="Run kurtosis factor backtest"
    )
    parser.add_argument(
        "--kurtosis-strategy",
        type=str,
        default="momentum",
        choices=["mean_reversion", "momentum"],
        help="Kurtosis factor strategy type",
    )
    parser.add_argument(
        "--kurtosis-rebalance-days",
        type=int,
        default=1,
        help="Kurtosis rebalance frequency in days",
    )
    parser.add_argument(
        "--run-beta", action="store_true", default=True, help="Run beta factor backtest"
    )
    parser.add_argument(
        "--beta-strategy",
        type=str,
        default="betting_against_beta",
        choices=[
            "betting_against_beta",
            "traditional_risk_premium",
            "long_low_beta",
            "long_high_beta",
        ],
        help="Beta factor strategy type",
    )
    parser.add_argument(
        "--beta-weighting",
        type=str,
        default="equal_weight",
        choices=["equal_weight", "risk_parity", "beta_weighted"],
        help="Beta factor weighting method",
    )
    parser.add_argument(
        "--beta-rebalance-days", type=int, default=5, help="Beta rebalance frequency in days (optimal: 5 days, Sharpe: 0.68)"
    )
    # parser.add_argument(
    #     "--run-adf", action="store_true", default=True, help="Run ADF factor backtest"
    # )
    # parser.add_argument(
    #     "--adf-strategy",
    #     type=str,
    #     default="trend_following_premium",
    #     choices=[
    #         "mean_reversion_premium",
    #         "trend_following_premium",
    #         "long_stationary",
    #         "long_trending",
    #     ],
    #     help="ADF factor strategy type",
    # )
    # parser.add_argument("--adf-window", type=int, default=60, help="ADF calculation window in days")

    args = parser.parse_args()

    print("=" * 120)
    print("RUNNING ALL BACKTESTS")
    print("=" * 120)
    print(f"\nConfiguration:")
    print(f"  Data file: {args.data_file}")
    print(f"  Market cap file: {args.marketcap_file}")
    print(f"  Funding rates file: {args.funding_rates_file}")
    print(f"  OI data file: {args.oi_data_file}")
    print(f"  Initial capital: ${args.initial_capital:,.2f}")
    print(f"  Start date: {args.start_date or 'First available'}")
    print(f"  End date: {args.end_date or 'Last available'}")
    print(f"  Output file: {args.output_file}")
    print(f"  OI mode: {args.oi_mode}")
    print("=" * 120)

    # Load all data once (eliminates repetitive I/O)
    loaded_data = load_all_data(args)
    
    # Common parameters
    common_params = {
        "initial_capital": args.initial_capital,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "leverage": 1.0,
        "long_allocation": 0.5,
        "short_allocation": 0.5,
        "volatility_window": 30,
    }

    # Run all backtests
    all_results = []

    # 1. Breakout Signal
    if args.run_breakout:
        if loaded_data["price_data"] is not None:
            result = run_breakout_backtest(
                loaded_data["price_data"], entry_window=50, exit_window=70, **common_params
            )
            if result:
                all_results.append(result)
        else:
            print("? Skipping Breakout backtest: price data not available")

    # 2. Mean Reversion
    if args.run_mean_reversion:
        if loaded_data["price_data"] is not None:
            result = run_mean_reversion_backtest(
                loaded_data["price_data"],
                lookback_window=30,
                return_threshold=1.0,
                volume_threshold=1.0,
                **common_params,
            )
            if result:
                all_results.append(result)
        else:
            print("? Skipping Mean Reversion backtest: price data not available")

    # 3. Size Factor
    if args.run_size:
        if loaded_data["price_data"] is not None and loaded_data["marketcap_data"] is not None:
            result = run_size_factor_backtest(
                loaded_data["price_data"],
                loaded_data["marketcap_data"],
                strategy="long_small_short_large",
                num_buckets=5,
                rebalance_days=10,  # Optimal: 10 days (Sharpe: 0.39)
                **common_params,
            )
            if result:
                all_results.append(result)
        else:
            print("? Skipping Size Factor backtest: price or marketcap data not available")

    # 4. Carry Factor
    if args.run_carry:
        if loaded_data["price_data"] is not None and loaded_data["funding_data"] is not None:
            result = run_carry_factor_backtest(
                loaded_data["price_data"],
                loaded_data["funding_data"],
                top_n=10,
                bottom_n=10,
                rebalance_days=7,
                **common_params,
            )
            if result:
                all_results.append(result)
        else:
            print("? Skipping Carry Factor backtest: price or funding data not available")

    # 5. Days from High
    if args.run_days_from_high:
        if loaded_data["price_data"] is not None:
            result = run_days_from_high_backtest(
                loaded_data["price_data"], days_threshold=20, **common_params
            )
            if result:
                all_results.append(result)
        else:
            print("? Skipping Days from High backtest: price data not available")

    # # 6. OI Divergence  # Removed: OI data not used
    # if args.run_oi_divergence:
    #     if loaded_data["price_data"] is not None and loaded_data["oi_data"] is not None:
    #         result = run_oi_divergence_backtest(
    #             loaded_data["price_data"],
    #             loaded_data["oi_data"],
    #             oi_mode=args.oi_mode,
    #             lookback=30,
    #             top_n=10,
    #             bottom_n=10,
    #             rebalance_days=7,
    #             **common_params,
    #         )
    #         if result:
    #             all_results.append(result)
    #     else:
    #         print("? Skipping OI Divergence backtest: price or OI data not available")

    # 7. Volatility Factor
    if args.run_volatility:
        if loaded_data["price_data"] is not None:
            result = run_volatility_factor_backtest(
                loaded_data["price_data"],
                strategy=args.volatility_strategy,
                num_quintiles=5,
                rebalance_days=3,  # Optimal: 3 days (Sharpe: 1.41)
                weighting_method="equal",
                **common_params,
            )
            if result:
                all_results.append(result)
        else:
            print("? Skipping Volatility Factor backtest: price data not available")

    # 8. Kurtosis Factor (requires scipy)
    if args.run_kurtosis:
        if loaded_data["price_data"] is not None:
            result = run_kurtosis_factor_backtest(
                loaded_data["price_data"],
                strategy=args.kurtosis_strategy,
                kurtosis_window=30,
                rebalance_days=args.kurtosis_rebalance_days,
                weighting="risk_parity",
                long_percentile=20,
                short_percentile=80,
                **common_params,
            )
            if result:
                all_results.append(result)
        else:
            print("? Skipping Kurtosis Factor backtest: price data not available")

    # 9. Beta Factor (BAB with Equal Weight, 5-day Rebalancing)
    if args.run_beta:
        if loaded_data["price_data"] is not None:
            result = run_beta_factor_backtest(
                loaded_data["price_data"],
                strategy=args.beta_strategy,
                beta_window=90,
                rebalance_days=args.beta_rebalance_days,
                weighting_method=args.beta_weighting,
                long_percentile=20,
                short_percentile=80,
                **common_params,
            )
            if result:
                all_results.append(result)
        else:
            print("? Skipping Beta Factor backtest: price data not available")

    # 10. ADF Factor (Trend Following) - COMMENTED OUT
    # if args.run_adf:
    #     result = run_adf_factor_backtest(
    #         args.data_file,
    #         strategy=args.adf_strategy,
    #         adf_window=args.adf_window,
    #         regression="ct",
    #         rebalance_days=7,
    #         weighting_method="equal_weight",
    #         long_percentile=20,
    #         short_percentile=80,
    #         min_volume=5_000_000,
    #         min_market_cap=50_000_000,
    #         **common_params,
    #     )
    #     if result:
    #         all_results.append(result)

    # Create and display summary table
    summary_df = create_summary_table(all_results)
    print_summary_table(summary_df)

    # Save results
    if not summary_df.empty:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(args.output_file), exist_ok=True)

        # Save with original numeric values (not formatted)
        summary_df.to_csv(args.output_file, index=False)
        print(f"\nSummary table saved to: {args.output_file}")

        # Generate and save Sharpe-based weights with 5% floor
        weights_df = calculate_sharpe_weights_with_floor(summary_df, min_weight=0.05)

        if weights_df is not None and not weights_df.empty:
            # Print weights table
            print_sharpe_weights(weights_df, summary_df, min_weight=0.05)

            # Save weights to CSV
            weights_file = args.output_file.replace("_summary.csv", "_sharpe_weights.csv")
            if weights_file == args.output_file:
                weights_file = args.output_file.replace(".csv", "_sharpe_weights.csv")

            weights_df.to_csv(weights_file, index=False)
            print(f"\nSharpe-based weights saved to: {weights_file}")

    # Combine and save daily returns from all strategies
    daily_returns_df = combine_daily_returns(all_results)
    if not daily_returns_df.empty:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(args.output_file), exist_ok=True)

        # Generate daily returns filename
        daily_returns_file = args.output_file.replace("_summary.csv", "_daily_returns.csv")
        if daily_returns_file == args.output_file:
            daily_returns_file = args.output_file.replace(".csv", "_daily_returns.csv")

        # Save daily returns
        daily_returns_df.to_csv(daily_returns_file, index=False)
        print(f"\n{'=' * 120}")
        print(f"Daily returns for all strategies saved to: {daily_returns_file}")
        print(f"Shape: {daily_returns_df.shape[0]} days x {daily_returns_df.shape[1]-1} strategies")
        print(f"Date range: {daily_returns_df['date'].min()} to {daily_returns_df['date'].max()}")
        print(f"{'=' * 120}")

    print("\n" + "=" * 120)
    print("ALL BACKTESTS COMPLETE")
    print("=" * 120)


if __name__ == "__main__":
    main()
