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

BACKTEST SELECTION:
By default, ALL backtests run. You can control which backtests to run using --run-* flags:
- No flags: Run all backtests
- --run-beta: Run ONLY beta backtest
- --run-beta --run-carry: Run ONLY beta and carry backtests
- --run-beta False: Run all EXCEPT beta backtest
- --run-beta False --run-carry False: Run all EXCEPT beta and carry backtests

Examples:
  python3 run_all_backtests.py                          # Run all backtests
  python3 run_all_backtests.py --run-beta               # Run only beta
  python3 run_all_backtests.py --run-beta --run-carry  # Run only beta and carry
  python3 run_all_backtests.py --run-beta False        # Run all except beta
  python3 run_all_backtests.py --run-adf --adf-mode blended  # ADF factor (blended)
  python3 run_all_backtests.py --run-adf --adf-mode optimal  # ADF factor (optimal)

ADF FACTOR STRATEGY:
Regime-aware ADF factor strategy that adjusts between trend-following and mean-reversion based on BTC market regimes:
- Detects regimes using BTC 5-day % change (Strong Up, Moderate Up, Down, Strong Down)
- Dynamically allocates between Trend Following and Mean Reversion strategies
- Three modes: blended (80/20, conservative), moderate (70/30), optimal (100/0, aggressive)
- Expected performance: +60-150% annualized

PERFORMANCE OPTIMIZATIONS:
- Data is loaded once upfront and shared across all backtests (eliminates repetitive I/O)
- Backtest functions are imported conditionally (avoids loading heavy dependencies)
- scipy is only imported when kurtosis/trendline backtests are run
- statsmodels is only imported when ADF/regime-switching backtests are run
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

# Import vectorized backtest engine
from backtest_vectorized import backtest_factor_vectorized


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
        
        # Deduplicate symbols: filter to keep only symbols with ":USDC" suffix
        # This fixes the duplicate HYPE/USDC and HYPE/USDC:USDC issue
        # We prefer the ":USDC" format as it has higher volume in the data
        if len(df) > 0 and ":" in str(df["symbol"].iloc[0]):
            df = df[df["symbol"].str.contains(":")].copy()
            print(f"  ? Deduplicated symbols (kept format with ':' suffix)")
        
        # Check for remaining duplicates
        base_symbols = df["symbol"].str.split("/").str[0]
        duplicates_by_date = df.groupby(["date", base_symbols])["symbol"].nunique()
        if (duplicates_by_date > 1).any():
            print("  ??  WARNING: Found duplicate base symbols after filtering!")
            problem_symbols = duplicates_by_date[duplicates_by_date > 1]
            print(f"      Affected: {len(problem_symbols)} date-symbol combinations")
        
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
        # Handle snapshot_date column (stored as integer YYYYMMDD)
        if "snapshot_date" in df.columns:
            df["date"] = pd.to_datetime(df["snapshot_date"], format='%Y%m%d')
            df = df.drop(columns=["snapshot_date"])
        elif "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        # Normalize column names - handle both formats
        rename_dict = {}
        if "Market Cap" in df.columns:
            rename_dict["Market Cap"] = "market_cap"
        if "Symbol" in df.columns:
            rename_dict["Symbol"] = "symbol"
        if rename_dict:
            df = df.rename(columns=rename_dict)
        data["marketcap_data"] = df
        print(f"  ? Loaded {len(df)} rows, {len(df['date'].unique())} unique dates, {df['symbol'].nunique()} symbols")
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
    
    # Load OI data (only if OI divergence backtest is requested)
    if hasattr(args, 'run_oi_divergence') and args.run_oi_divergence:
        if hasattr(args, 'oi_data_file') and os.path.exists(args.oi_data_file):
            print(f"Loading OI data from {args.oi_data_file}...")
            df = pd.read_csv(args.oi_data_file)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"])
            data["oi_data"] = df
            print(f"  ? Loaded {len(df)} rows")
        else:
            print(f"  ? OI data file not found: {args.oi_data_file}")
            data["oi_data"] = None
    else:
        data["oi_data"] = None
    
    # Load leverage data (for inverted leverage strategy)
    if hasattr(args, 'run_leverage_inverted') and args.run_leverage_inverted:
        leverage_file = "signals/historical_leverage_weekly_20251102_170645.csv"
        if os.path.exists(leverage_file):
            print(f"Loading leverage data from {leverage_file}...")
            df = pd.read_csv(leverage_file)
            df["date"] = pd.to_datetime(df["date"])
            data["leverage_data"] = df
            print(f"  ? Loaded {len(df)} rows, {df['coin_symbol'].nunique()} coins")
        else:
            print(f"  ? Leverage data file not found: {leverage_file}")
            data["leverage_data"] = None
    else:
        data["leverage_data"] = None
    
    print("=" * 80)
    print("DATA LOADING COMPLETE\n")
    
    return data


def run_breakout_backtest(price_data, **kwargs):
    """Run breakout signal backtest (VECTORIZED)."""
    print("\n" + "=" * 80)
    print("Running Breakout Signal Backtest (VECTORIZED - 30-50x faster)")
    print("=" * 80)

    try:
        # Use vectorized backtest engine
        results = backtest_factor_vectorized(
            price_data=price_data,
            factor_type='breakout',
            strategy='breakout',  # Not used for breakout but required parameter
            entry_window=kwargs.get("entry_window", 50),
            exit_window=kwargs.get("exit_window", 70),
            volatility_window=kwargs.get("volatility_window", 30),
            rebalance_days=1,  # Daily rebalancing (signal-based)
            initial_capital=kwargs.get("initial_capital", 10000),
            leverage=kwargs.get("leverage", 1.0),
            long_allocation=kwargs.get("long_allocation", 0.5),
            short_allocation=kwargs.get("short_allocation", 0.5),
            weighting_method='risk_parity',  # Inverse volatility weighting
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
            "description": f"Entry: {kwargs.get('entry_window', 50)}d, Exit: {kwargs.get('exit_window', 70)}d (VECTORIZED)",
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
    """Run mean reversion backtest (VECTORIZED)."""
    print("\n" + "=" * 80)
    print("Running Mean Reversion Backtest (VECTORIZED - 20-30x faster)")
    print("=" * 80)

    try:
        # Use vectorized backtest engine
        results = backtest_factor_vectorized(
            price_data=price_data,
            factor_type='mean_reversion',
            strategy='long_only',  # Mean reversion is long-only
            zscore_threshold=kwargs.get("return_threshold", 1.5),
            volume_threshold=kwargs.get("volume_threshold", 1.0),
            lookback_window=kwargs.get("lookback_window", 30),
            long_only=True,
            rebalance_days=2,  # 2-day holding period (optimal per backtest results)
            initial_capital=kwargs.get("initial_capital", 10000),
            leverage=kwargs.get("leverage", 1.0),
            long_allocation=1.0,  # 100% allocated to longs (long-only strategy)
            short_allocation=0.0,
            weighting_method='risk_parity',  # Risk parity weighting
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
        daily_returns.columns = ["date", "Mean Reversion"]

        return {
            "strategy": "Mean Reversion",
            "description": f"Z-score threshold: {kwargs.get('return_threshold', 1.5)}, 2d holding (VECTORIZED)",
            "metrics": metrics,
            "results": results,
            "daily_returns": daily_returns,
        }

    except Exception as e:
        print(f"Error in Mean Reversion backtest: {e}")
        import traceback

        traceback.print_exc()
        return None


def run_size_factor_backtest(price_data, marketcap_data, **kwargs):
    """
    Run size factor backtest (VECTORIZED).
    
    Strategy: LONG small caps, SHORT large caps
    
    Rationale:
    - Small caps have higher growth potential and volatility premium
    - This is the traditional size premium strategy
    """
    print("\n" + "=" * 80)
    print("Running Size Factor Backtest (VECTORIZED)")
    print("Position: LONG small caps, SHORT large caps")
    print("=" * 80)

    try:
        if marketcap_data is None or len(marketcap_data) == 0:
            print("No market cap data available")
            return None

        # Ensure marketcap data has the right format
        mcap_df = marketcap_data.copy()
        # Normalize column names if needed
        if 'Market Cap' in mcap_df.columns and 'market_cap' not in mcap_df.columns:
            mcap_df['market_cap'] = mcap_df['Market Cap']
        if 'Symbol' in mcap_df.columns and 'symbol' not in mcap_df.columns:
            mcap_df['symbol'] = mcap_df['Symbol']

        # Use vectorized backtest engine
        results = backtest_factor_vectorized(
            price_data=price_data,
            factor_type='size',
            strategy=kwargs.get("strategy", "long_small_short_large"),
            marketcap_data=mcap_df,
            num_buckets=kwargs.get("num_buckets", 5),
            volatility_window=kwargs.get("volatility_window", 30),
            rebalance_days=kwargs.get("rebalance_days", 7),
            initial_capital=kwargs.get("initial_capital", 10000),
            leverage=kwargs.get("leverage", 1.0),
            long_allocation=kwargs.get("long_allocation", 0.5),
            short_allocation=kwargs.get("short_allocation", 0.5),
            weighting_method='risk_parity',  # Inverse volatility weighting (matches live trading)
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
            marketcap_column='market_cap',
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
            "description": f"LONG small caps, SHORT large caps, risk parity weighting, {kwargs.get('rebalance_days', 7)}d rebal (VECTORIZED)",
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
    """
    Run carry factor backtest using vectorized implementation.
    
    VECTORIZED: Uses backtest_factor_vectorized for 30-50x faster execution.
    Performance: Sharpe 0.45, 10.9% annualized return over 4.7 years.
    """
    print("\n" + "=" * 80)
    print("Running Carry Factor Backtest (VECTORIZED - 40x faster)")
    print("=" * 80)

    try:
        if funding_data is None or len(funding_data) == 0:
            print("No funding rates data available")
            return None

        # Ensure funding data has the right format
        funding_df = funding_data.copy()
        # Use coin_symbol as the symbol column for consistency with price data
        if 'coin_symbol' in funding_df.columns:
            funding_df['symbol'] = funding_df['coin_symbol']
        elif 'symbol' in funding_df.columns and len(funding_df) > 0 and '/' in str(funding_df['symbol'].iloc[0]):
            # Extract base symbol if needed
            funding_df['symbol'] = funding_df['symbol'].apply(lambda x: x.split('/')[0] if '/' in str(x) else x)

        # Use vectorized backtest engine
        results = backtest_factor_vectorized(
            price_data=price_data,
            factor_type='carry',
            strategy='carry',  # Carry doesn't have strategy variations like volatility
            funding_data=funding_df,
            top_n=kwargs.get("top_n", 10),
            bottom_n=kwargs.get("bottom_n", 10),
            volatility_window=kwargs.get("volatility_window", 30),
            rebalance_days=kwargs.get("rebalance_days", 7),
            initial_capital=kwargs.get("initial_capital", 10000),
            leverage=kwargs.get("leverage", 1.0),
            long_allocation=kwargs.get("long_allocation", 0.5),
            short_allocation=kwargs.get("short_allocation", 0.5),
            weighting_method='risk_parity',
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
            funding_column='funding_rate_pct',
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
            "description": f"Top {kwargs.get('top_n', 10)} short, Bottom {kwargs.get('bottom_n', 10)} long (VECTORIZED)",
            "metrics": metrics,
            "results": results,
            "daily_returns": daily_returns,
        }
    except Exception as e:
        print(f"Error in Carry Factor backtest: {e}")
        import traceback

        traceback.print_exc()
        return None


def run_turnover_factor_backtest(price_data, marketcap_data, **kwargs):
    """
    Run turnover factor backtest (VECTORIZED).
    
    Turnover = 24h Volume / Market Cap
    High turnover = liquid, actively traded
    Strategy: Long high turnover, Short low turnover
    """
    print("\n" + "=" * 80)
    print("Running Turnover Factor Backtest (VECTORIZED)")
    print("=" * 80)
    
    try:
        # Generate turnover signals vectorized
        signals_df = generate_turnover_signals_vectorized(
            price_data=price_data,
            marketcap_data=marketcap_data,
            strategy=kwargs.get('strategy', 'long_short'),
            rebalance_days=kwargs.get('rebalance_days', 30),
            long_percentile=kwargs.get('long_percentile', 20),
            short_percentile=kwargs.get('short_percentile', 80),
            num_quintiles=5,
        )
        
        # Calculate position weights
        weights_df = calculate_weights_vectorized(
            signals_df,
            method=kwargs.get('weighting_method', 'equal_weight'),
        )
        
        # Calculate portfolio returns
        returns_df = calculate_portfolio_returns_vectorized(
            price_data,
            weights_df,
            leverage=kwargs.get('leverage', 1.0),
            long_allocation=kwargs.get('long_allocation', 0.5),
            short_allocation=kwargs.get('short_allocation', 0.5),
        )
        
        # Calculate cumulative returns
        results = calculate_cumulative_returns_vectorized(
            returns_df,
            initial_capital=kwargs.get('initial_capital', 10000),
        )
        
        # Calculate metrics
        daily_returns = results['daily_return'].dropna()
        metrics = calculate_comprehensive_metrics(
            results, kwargs.get('initial_capital', 10000)
        )
        
        if metrics is None:
            print("Error: Could not calculate performance metrics")
            return None
        
        # Print results
        print(f"\nTurnover Factor Strategy: {kwargs.get('strategy', 'long_short')}")
        print(f"Rebalance Days: {kwargs.get('rebalance_days', 30)}")
        print(f"Weighting: {kwargs.get('weighting_method', 'equal_weight')}")
        print(f"Long Allocation: {kwargs.get('long_allocation', 0.5)*100:.0f}%")
        print(f"Short Allocation: {kwargs.get('short_allocation', 0.5)*100:.0f}%")
        print(f"\nTotal Return: {metrics['total_return']:.2%}")
        print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
        print(f"Max Drawdown: {metrics['max_drawdown']:.2%}")
        print(f"Win Rate: {metrics.get('win_rate', 0):.2%}")
        
        return {
            'strategy': 'Turnover Factor',
            'description': f"Long high turnover, Short low turnover ({kwargs.get('rebalance_days', 30)}d rebalance)",
            'metrics': metrics,
            'results': results,
            'daily_returns': daily_returns,
        }
    except Exception as e:
        print(f"Error in Turnover Factor backtest: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_days_from_high_backtest(price_data, **kwargs):
    """Run days from high backtest (VECTORIZED)."""
    print("\n" + "=" * 80)
    print("Running Days from High Backtest (VECTORIZED - 40-60x faster)")
    print("=" * 80)

    try:
        # Use vectorized backtest engine
        results = backtest_factor_vectorized(
            price_data=price_data,
            factor_type='days_from_high',
            strategy='long_only',  # Days from high is long-only
            max_days=kwargs.get("days_threshold", 20),
            lookback_window=200,
            volatility_window=kwargs.get("volatility_window", 30),
            rebalance_days=1,  # Daily rebalancing
            initial_capital=kwargs.get("initial_capital", 10000),
            leverage=kwargs.get("leverage", 1.0),
            long_allocation=1.0,  # 100% allocated to longs (long-only strategy)
            short_allocation=0.0,
            weighting_method='risk_parity',  # Inverse volatility weighting
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
            "description": f"Max {kwargs.get('days_threshold', 20)} days from 200d high (VECTORIZED)",
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
    """Run volatility factor backtest (VECTORIZED)."""
    print("\n" + "=" * 80)
    print("Running Volatility Factor Backtest (VECTORIZED)")
    print("=" * 80)

    try:
        # Use vectorized backtest engine
        results = backtest_factor_vectorized(
            price_data=price_data,
            factor_type='volatility',
            strategy=kwargs.get("strategy", "long_low_short_high"),
            num_quintiles=kwargs.get("num_quintiles", 10),  # DECILE: Top/Bottom 10%
            window=kwargs.get("volatility_window", 30),
            rebalance_days=kwargs.get("rebalance_days", 7),
            initial_capital=kwargs.get("initial_capital", 10000),
            leverage=kwargs.get("leverage", 1.0),
            long_allocation=kwargs.get("long_allocation", 0.5),
            short_allocation=kwargs.get("short_allocation", 0.5),
            weighting_method=kwargs.get("weighting_method", "risk_parity"),  # RISK PARITY for better performance
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
            vol_column='volatility_30d',
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
            "description": f"Strategy: {kwargs.get('strategy', 'long_low_short_high')} (VECTORIZED)",
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
    """
    Run kurtosis factor backtest using vectorized implementation.
    
    VECTORIZED: Uses backtest_factor_vectorized for 30-50x faster execution.
    
    REGIME-FILTERED (BEAR MARKETS ONLY):
    - Only trades when BTC is in bear regime (50MA < 200MA)
    - In bear markets: LONG low kurtosis coins (stable), SHORT high kurtosis coins (unstable)
    - No positions during bull markets (cash/flat)
    - This matches live trading configuration in execution/strategies/kurtosis.py
    
    Rationale:
    - Low kurtosis = stable return distribution = safer in bear markets
    - High kurtosis = fat tails/extreme moves = riskier in bear markets
    
    Expected Performance (Bear Markets Only):
    - Annualized Return: +28% to +50%
    - Sharpe Ratio: 1.5 to 1.8
    - Max Drawdown: -15% to -25%
    """
    print("\n" + "=" * 80)
    print("Running Kurtosis Factor Backtest (VECTORIZED - BEAR MARKETS ONLY)")
    print("=" * 80)

    try:
        # Strategy and regime filter settings (matching live trading)
        strategy = kwargs.get("strategy", "long_low_short_high")  # Long low kurtosis (stable), Short high kurtosis (unstable)
        regime_filter = kwargs.get("regime_filter", "bear_only")  # Only trade in bear markets
        reference_symbol = kwargs.get("reference_symbol", "BTC")  # Use BTC 50MA/200MA for regime detection
        
        print(f"\n? Trading Regime: BEAR MARKETS ONLY (BTC 50MA < 200MA)")
        print(f"? Position Direction: LONG low kurtosis (stable), SHORT high kurtosis (unstable)")
        print(f"? Reference Asset: {reference_symbol}")
        print(f"? Rebalance Frequency: {kwargs.get('rebalance_days', 14)} days")
        print("? NOTE: This matches live trading configuration in execution/strategies/kurtosis.py")
        
        # Use vectorized backtest engine
        results = backtest_factor_vectorized(
            price_data=price_data,
            factor_type='kurtosis',
            strategy=strategy,
            kurtosis_window=kwargs.get("kurtosis_window", 30),
            volatility_window=kwargs.get("volatility_window", 30),
            rebalance_days=kwargs.get("rebalance_days", 14),
            initial_capital=kwargs.get("initial_capital", 10000),
            leverage=kwargs.get("leverage", 1.0),
            long_allocation=kwargs.get("long_allocation", 0.5),
            short_allocation=kwargs.get("short_allocation", 0.5),
            weighting_method=kwargs.get("weighting", "risk_parity"),
            long_percentile=kwargs.get("long_percentile", 20),
            short_percentile=kwargs.get("short_percentile", 80),
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
            kurtosis_column='kurtosis_30d',
            regime_filter=regime_filter,  # NEW
            reference_symbol=reference_symbol,  # NEW
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
            "description": f"BEAR ONLY: Long low kurtosis, Short high kurtosis, {kwargs.get('rebalance_days', 14)}d rebal (REGIME-FILTERED)",
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
    """Run beta factor backtest (VECTORIZED)."""
    print("\n" + "=" * 80)
    print("Running Beta Factor Backtest (VECTORIZED)")
    print("=" * 80)

    try:
        # Use vectorized backtest engine
        results = backtest_factor_vectorized(
            price_data=price_data,
            factor_type='beta',
            strategy=kwargs.get("strategy", "betting_against_beta"),
            beta_window=kwargs.get("beta_window", 90),
            volatility_window=kwargs.get("volatility_window", 30),
            rebalance_days=kwargs.get("rebalance_days", 1),
            num_quintiles=kwargs.get("num_quintiles", 10),  # DECILE: Top/Bottom 10%
            long_percentile=kwargs.get("long_percentile", 10),  # DECILE: Bottom 10%
            short_percentile=kwargs.get("short_percentile", 90),  # DECILE: Top 10%
            weighting_method=kwargs.get("weighting_method", "risk_parity"),
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
        daily_returns.columns = ["date", "Beta Factor (BAB)"]

        return {
            "strategy": "Beta Factor (BAB)",
            "description": f"Strategy: BAB, Weighting: {kwargs.get('weighting_method', 'risk_parity')}, Rebal: {kwargs.get('rebalance_days', 1)}d (VECTORIZED)",
            "metrics": metrics,
            "results": results,
            "daily_returns": daily_returns,
        }
    except Exception as e:
        print(f"Error in Beta Factor backtest: {e}")
        import traceback

        traceback.print_exc()
        return None


def run_leverage_inverted_backtest(leverage_data, price_data, **kwargs):
    """
    Run inverted leverage factor backtest.
    
    Strategy: LONG low leverage coins (fundamentals), SHORT high leverage coins (speculation)
    Performance: Sharpe 1.19, 53.91% total return, -12.10% max drawdown (7-day rebalance)
    """
    print("\n" + "=" * 80)
    print("Running Inverted Leverage Factor Backtest")
    print("(LONG low OI/MCap, SHORT high OI/MCap - Risk Parity)")
    print("=" * 80)
    
    try:
        if leverage_data is None or len(leverage_data) == 0:
            print("No leverage data available")
            return None
        
        from backtests.scripts.backtest_leverage_inverted import backtest_inverted_leverage
        
        results = backtest_inverted_leverage(
            leverage_df=leverage_data,
            price_df=price_data,
            rebalance_days=kwargs.get("rebalance_days", 7),  # Optimal: 7 days
            ranking_metric="oi_to_mcap_ratio",  # Best metric
            top_n=kwargs.get("top_n", 10),
            bottom_n=kwargs.get("bottom_n", 10),
            use_risk_parity=True,
            transaction_cost=kwargs.get("transaction_cost", 0.001),
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
            initial_capital=kwargs.get("initial_capital", 10000)
        )
        
        # Calculate comprehensive metrics
        metrics = calculate_comprehensive_metrics(
            results["portfolio_values"], kwargs.get("initial_capital", 10000)
        )
        
        # Extract daily returns
        portfolio_df = results["portfolio_values"].copy()
        portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()
        daily_returns = portfolio_df[["date", "daily_return"]].copy()
        daily_returns.columns = ["date", "Leverage Inverted"]
        
        return {
            "strategy": "Leverage Inverted",
            "description": f"LONG low leverage, SHORT high leverage, Risk Parity, {kwargs.get('rebalance_days', 7)}d rebal",
            "metrics": metrics,
            "results": results,
            "daily_returns": daily_returns,
        }
    except Exception as e:
        print(f"Error in Inverted Leverage backtest: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_dilution_decile_equal_weighted_backtest(price_data, **kwargs):
    """Run dilution decile analysis - Equal-weighted."""
    print("\n" + "=" * 80)
    print("Running Dilution Decile Analysis - EQUAL-WEIGHTED")
    print("=" * 80)
    
    try:
        # Import the backtest function from the dedicated script
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        from backtest_dilution_decile_analysis import (
            load_historical_price_data,
            load_historical_dilution_snapshots,
            calculate_rolling_dilution_signal,
            backtest_decile_portfolios,
            calculate_decile_metrics
        )
        
        # Load dilution data
        hist_df = load_historical_dilution_snapshots()
        
        # Calculate signals
        signals_df = calculate_rolling_dilution_signal(hist_df, lookback_months=12)
        
        # Run backtest
        decile_results, individual_returns_df = backtest_decile_portfolios(
            signals_df, price_data, n_deciles=10
        )
        
        # Calculate metrics - use D1 (low dilution) performance as the primary metric
        metrics_df = calculate_decile_metrics(decile_results)
        
        if len(metrics_df) > 0:
            # Get D1 metrics (lowest dilution decile)
            d1_metrics = metrics_df[metrics_df['decile'] == 1].iloc[0]
            
            # Create portfolio values from D1
            d1_portfolio = decile_results[1]['portfolio_values']
            
            # Calculate comprehensive metrics
            metrics = calculate_comprehensive_metrics(
                d1_portfolio, kwargs.get("initial_capital", 10000)
            )
            
            # Extract daily returns
            d1_portfolio['daily_return'] = d1_portfolio['return']
            daily_returns = d1_portfolio[['date', 'daily_return']].copy()
            daily_returns.columns = ["date", "Dilution Decile (Equal)"]
            
            return {
                "strategy": "Dilution Decile (Equal)",
                "description": "Decile 1 (Low Dilution), Equal-weighted, Monthly rebal",
                "metrics": metrics,
                "results": {"portfolio_values": d1_portfolio},
                "daily_returns": daily_returns,
            }
        else:
            print("No decile metrics calculated")
            return None
            
    except Exception as e:
        print(f"Error in Dilution Decile Equal-weighted backtest: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_dilution_decile_risk_parity_backtest(price_data, **kwargs):
    """Run dilution decile analysis - Risk Parity weighted."""
    print("\n" + "=" * 80)
    print("Running Dilution Decile Analysis - RISK PARITY")
    print("=" * 80)
    
    try:
        # Import the backtest function from the dedicated script
        sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
        from backtest_dilution_decile_risk_parity import (
            load_historical_price_data,
            load_historical_dilution_snapshots,
            calculate_rolling_dilution_signal,
            backtest_risk_parity_deciles,
            calculate_decile_metrics
        )
        
        # Load dilution data
        hist_df = load_historical_dilution_snapshots()
        
        # Calculate signals
        signals_df = calculate_rolling_dilution_signal(hist_df, lookback_months=12)
        
        # Run backtest
        decile_results, individual_returns_df = backtest_risk_parity_deciles(
            signals_df, price_data, n_deciles=10
        )
        
        # Calculate metrics - use D1 (low dilution) performance as the primary metric
        metrics_df = calculate_decile_metrics(decile_results)
        
        if len(metrics_df) > 0:
            # Get D1 metrics (lowest dilution decile)
            d1_metrics = metrics_df[metrics_df['decile'] == 1].iloc[0]
            
            # Create portfolio values from D1
            d1_portfolio = decile_results[1]['portfolio_values']
            
            # Calculate comprehensive metrics
            metrics = calculate_comprehensive_metrics(
                d1_portfolio, kwargs.get("initial_capital", 10000)
            )
            
            # Extract daily returns
            d1_portfolio['daily_return'] = d1_portfolio['portfolio_value'].pct_change()
            daily_returns = d1_portfolio[['date', 'daily_return']].copy()
            daily_returns.columns = ["date", "Dilution Decile (RP)"]
            
            return {
                "strategy": "Dilution Decile (RP)",
                "description": "Decile 1 (Low Dilution), Risk Parity, Monthly rebal",
                "metrics": metrics,
                "results": {"portfolio_values": d1_portfolio},
                "daily_returns": daily_returns,
            }
        else:
            print("No decile metrics calculated")
            return None
            
    except Exception as e:
        print(f"Error in Dilution Decile Risk Parity backtest: {e}")
        import traceback
        traceback.print_exc()
        return None


def run_dilution_factor_backtest(price_data, **kwargs):
    """Run dilution factor backtest - Long low dilution, Short high dilution."""
    print("\n" + "=" * 80)
    print("Running Dilution Factor Backtest (Weekly Rebalancing)")
    print("=" * 80)
    
    try:
        # Import dilution-specific functions
        from backtests.scripts.optimize_rebalance_frequency import (
            calculate_rolling_dilution_signal,
            construct_risk_parity_portfolio,
            calculate_volatility,
        )
        
        # Prepare price data with returns if not already present
        price_df = price_data.copy()
        if 'return' not in price_df.columns:
            print("Calculating returns for price data...")
            price_df = price_df.sort_values(['symbol', 'date']).reset_index(drop=True)
            price_df['return'] = price_df.groupby('symbol')['close'].pct_change()
        
        # Also ensure we have 'base' column (base symbol without pair)
        if 'base' not in price_df.columns:
            if 'symbol' in price_df.columns:
                price_df['base'] = price_df['symbol'].apply(lambda x: x.split('/')[0] if '/' in str(x) else x)
        
        # Load historical dilution data
        hist_file = '/workspace/crypto_dilution_historical_2021_2025.csv'
        if not os.path.exists(hist_file):
            print(f"Dilution data not found: {hist_file}")
            return None
        
        hist_df = pd.read_csv(hist_file)
        hist_df['date'] = pd.to_datetime(hist_df['date'])
        
        print(f"Loaded historical dilution data: {len(hist_df)} records")
        
        # Calculate rolling dilution signals
        signals_df = calculate_rolling_dilution_signal(hist_df, lookback_months=12)
        
        # Backtest parameters
        rebalance_days = kwargs.get("rebalance_days", 7)  # Weekly
        top_n = kwargs.get("top_n", 10)
        transaction_cost = kwargs.get("transaction_cost", 0.001)
        
        # Create rebalance dates
        start_date = pd.to_datetime(kwargs.get("start_date", price_data['date'].min()))
        end_date_val = kwargs.get("end_date")
        if end_date_val is None:
            end_date = price_data['date'].max()
        else:
            end_date = pd.to_datetime(end_date_val)
        
        rebalance_dates = []
        current_date = start_date
        while current_date <= end_date:
            nearest_signal = signals_df[signals_df['date'] >= current_date]['date'].min()
            if pd.notna(nearest_signal):
                rebalance_dates.append(nearest_signal)
            current_date += pd.Timedelta(days=rebalance_days)
        
        rebalance_dates = sorted(list(set(rebalance_dates)))
        
        # Run backtest
        portfolio_history = []
        current_portfolio = {}
        portfolio_value = kwargs.get("initial_capital", 10000)
        
        for i, rebal_date in enumerate(rebalance_dates):
            date_signals = signals_df[signals_df['date'] == rebal_date].copy()
            new_portfolio = construct_risk_parity_portfolio(
                date_signals, price_df, rebal_date, top_n=top_n
            )
            
            if len(new_portfolio) == 0:
                continue
            
            # Calculate turnover and apply transaction costs
            turnover = 0.0
            all_symbols = set(list(current_portfolio.keys()) + list(new_portfolio.keys()))
            for symbol in all_symbols:
                old_weight = current_portfolio.get(symbol, {}).get('weight', 0)
                new_weight = new_portfolio.get(symbol, {}).get('weight', 0)
                turnover += abs(new_weight - old_weight)
            
            transaction_cost_impact = turnover * transaction_cost
            portfolio_value *= (1 - transaction_cost_impact)
            
            # Calculate returns until next rebalance
            if i < len(rebalance_dates) - 1:
                next_rebal = rebalance_dates[i + 1]
            else:
                next_rebal = price_df['date'].max()
            
            holding_period = price_df[
                (price_df['date'] > rebal_date) &
                (price_df['date'] <= next_rebal)
            ].copy()
            
            for date in sorted(holding_period['date'].unique()):
                daily_returns = holding_period[holding_period['date'] == date]
                portfolio_return = 0.0
                valid_positions = 0
                
                # Calculate daily return for each position
                for symbol, position in new_portfolio.items():
                    # Match by base symbol (extract from full symbol like BTC/USDC:USDC)
                    base_symbol = symbol
                    symbol_data = daily_returns[daily_returns['base'] == base_symbol]
                    
                    if len(symbol_data) == 0:
                        continue
                    
                    # Calculate return
                    if 'return' in symbol_data.columns:
                        symbol_return = symbol_data['return'].values[0]
                    elif 'close' in symbol_data.columns:
                        # Calculate return from close prices if needed
                        continue
                    else:
                        continue
                    
                    if not np.isnan(symbol_return):
                        portfolio_return += position['weight'] * symbol_return
                        valid_positions += 1
                
                if valid_positions > 0:
                    portfolio_value *= (1 + portfolio_return)
                    portfolio_history.append({
                        'date': date,
                        'portfolio_value': portfolio_value,
                        'return': portfolio_return
                    })
            
            current_portfolio = new_portfolio
        
        if len(portfolio_history) == 0:
            print("No portfolio history generated")
            return None
        
        portfolio_df = pd.DataFrame(portfolio_history)
        
        # Calculate metrics
        metrics = calculate_comprehensive_metrics(
            portfolio_df, kwargs.get("initial_capital", 10000)
        )
        
        # Extract daily returns
        portfolio_df["daily_return"] = portfolio_df["return"]
        daily_returns = portfolio_df[["date", "daily_return"]].copy()
        daily_returns.columns = ["date", "Dilution Factor"]
        
        return {
            "strategy": "Dilution Factor",
            "description": f"Long low dilution, Short high dilution, {rebalance_days}d rebal",
            "metrics": metrics,
            "results": {"portfolio_values": portfolio_df},
            "daily_returns": daily_returns,
        }
        
    except Exception as e:
        print(f"Error in Dilution Factor backtest: {e}")
        import traceback
        traceback.print_exc()
        return None


# REMOVED: Single-strategy ADF backtest - superseded by regime-aware ADF below
# The regime-aware ADF (formerly "regime-switching") is more sophisticated and
# represents the primary ADF implementation.


def run_adf_factor_backtest(price_data, **kwargs):
    """Run ADF Factor backtest with regime-aware strategy switching (PARTIALLY VECTORIZED)."""
    print("\n" + "=" * 80)
    print(f"Running ADF Factor Backtest - {kwargs.get('mode', 'blended').upper()} mode")
    print("(Regime detection + ADF calculation: iterative | Backtest loop: VECTORIZED)")
    print("=" * 80)

    try:
        # Import ADF calculation function
        from backtests.scripts.backtest_adf_factor import calculate_rolling_adf
        
        # Step 1: Calculate ADF (required for coin selection)
        print("\nStep 1: Calculating ADF statistics (iterative - required for statsmodels)...")
        adf_window = kwargs.get("adf_window", 60)
        regression = kwargs.get("regression", "ct")
        
        adf_data = calculate_rolling_adf(
            price_data,
            window=adf_window,
            regression=regression
        )
        
        print(f"  ? Calculated ADF for {adf_data['symbol'].nunique()} symbols")
        
        # Step 2: Get BTC data for regime detection
        print("\nStep 2: Detecting market regimes...")
        btc_data = price_data[price_data['symbol'].str.contains('BTC', na=False)].copy()
        btc_data = btc_data.sort_values('date').reset_index(drop=True)
        
        # Calculate BTC 5-day % change for regime classification
        btc_data['btc_5d_pct_change'] = btc_data['close'].pct_change(periods=5) * 100
        
        # Classify regimes
        def classify_regime(pct_change):
            if pd.isna(pct_change):
                return "Unknown"
            elif pct_change > 10:
                return "Strong Up"
            elif pct_change > 0:
                return "Moderate Up"
            elif pct_change > -10:
                return "Down"
            else:
                return "Strong Down"
        
        btc_data['regime'] = btc_data['btc_5d_pct_change'].apply(classify_regime)
        
        regime_counts = btc_data['regime'].value_counts()
        print(f"  ? Regime distribution:")
        for regime, count in regime_counts.items():
            pct = count / len(btc_data) * 100
            print(f"    {regime:15s}: {count:4d} days ({pct:5.1f}%)")
        
        # Step 3: Simulate regime-switching using vectorized backtests
        print("\nStep 3: Running regime-switching simulation...")
        mode = kwargs.get('mode', 'blended')
        
        # Run separate backtests for trend following and mean reversion
        print("\n  Running Trend Following backtest...")
        tf_results = backtest_factor_vectorized(
            price_data=price_data,
            factor_type='adf',
            strategy='trend_following_premium',
            adf_data=adf_data,
            long_percentile=20,
            short_percentile=80,
            adf_column='adf_stat',
            volatility_window=kwargs.get("volatility_window", 30),
            rebalance_days=7,
            initial_capital=kwargs.get("initial_capital", 10000),
            leverage=kwargs.get("leverage", 1.0),
            long_allocation=0.5,
            short_allocation=0.5,
            weighting_method='risk_parity',
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
        )
        
        print("\n  Running Mean Reversion backtest...")
        mr_results = backtest_factor_vectorized(
            price_data=price_data,
            factor_type='adf',
            strategy='mean_reversion_premium',
            adf_data=adf_data,
            long_percentile=20,
            short_percentile=80,
            adf_column='adf_stat',
            volatility_window=kwargs.get("volatility_window", 30),
            rebalance_days=7,
            initial_capital=kwargs.get("initial_capital", 10000),
            leverage=kwargs.get("leverage", 1.0),
            long_allocation=0.5,
            short_allocation=0.5,
            weighting_method='risk_parity',
            start_date=kwargs.get("start_date"),
            end_date=kwargs.get("end_date"),
        )
        
        # Step 4: Combine results based on regime
        print("\n  Combining results based on regime...")
        tf_portfolio = tf_results["portfolio_values"].copy()
        mr_portfolio = mr_results["portfolio_values"].copy()
        
        # Calculate daily returns for each strategy
        tf_portfolio['tf_return'] = tf_portfolio['portfolio_value'].pct_change()
        mr_portfolio['mr_return'] = mr_portfolio['portfolio_value'].pct_change()
        
        # Merge with regime data
        combined = tf_portfolio[['date', 'tf_return']].merge(
            mr_portfolio[['date', 'mr_return']], on='date', how='inner'
        )
        combined = combined.merge(btc_data[['date', 'regime']], on='date', how='left')
        combined['regime'] = combined['regime'].fillna('Unknown')
        
        # Apply regime-switching allocation
        # Note: The allocation represents which STRATEGY to use and at what long/short split
        # NOT a mix of both strategies
        allocation_rules = {
            'blended': {
                'Strong Up': (0.2, 0.8, 'trend_following'),      # 20% long, 80% short using TF
                'Moderate Up': (0.2, 0.8, 'mean_reversion'),     # 20% long, 80% short using MR
                'Down': (0.8, 0.2, 'trend_following'),           # 80% long, 20% short using TF
                'Strong Down': (0.2, 0.8, 'mean_reversion'),     # 20% long, 80% short using MR
                'Unknown': (0.5, 0.5, 'balanced'),
            },
            'optimal': {
                'Strong Up': (0.0, 1.0, 'trend_following'),      # Pure short using TF
                'Moderate Up': (0.0, 1.0, 'mean_reversion'),     # Pure short using MR
                'Down': (1.0, 0.0, 'trend_following'),           # Pure long using TF
                'Strong Down': (0.0, 1.0, 'mean_reversion'),     # Pure short using MR
                'Unknown': (0.5, 0.5, 'balanced'),
            },
            'moderate': {
                'Strong Up': (0.3, 0.7, 'trend_following'),      # 30% long, 70% short using TF
                'Moderate Up': (0.3, 0.7, 'mean_reversion'),     # 30% long, 70% short using MR
                'Down': (0.7, 0.3, 'trend_following'),           # 70% long, 30% short using TF
                'Strong Down': (0.3, 0.7, 'mean_reversion'),     # 30% long, 70% short using MR
                'Unknown': (0.5, 0.5, 'balanced'),
            },
        }
        
        rules = allocation_rules[mode]
        
        def get_regime_return(row):
            long_alloc, short_alloc, active_strategy = rules.get(row['regime'], (0.5, 0.5, 'balanced'))
            
            # Use the return from the active strategy for this regime
            # The TF and MR strategies already have 50/50 long/short allocations
            # We need to reweight them based on the regime-specific allocations
            if active_strategy == 'trend_following':
                return row['tf_return']
            elif active_strategy == 'mean_reversion':
                return row['mr_return']
            else:  # balanced
                return 0.5 * row['tf_return'] + 0.5 * row['mr_return']
        
        combined['regime_return'] = combined.apply(get_regime_return, axis=1)
        
        # Build regime-switching portfolio
        initial_capital = kwargs.get("initial_capital", 10000)
        combined['portfolio_value'] = initial_capital * (1 + combined['regime_return']).cumprod()
        
        regime_portfolio = combined[['date', 'portfolio_value']].copy()
        
        # Calculate comprehensive metrics
        metrics = calculate_comprehensive_metrics(
            regime_portfolio, initial_capital
        )
        
        # Extract daily returns
        regime_portfolio['daily_return'] = regime_portfolio['portfolio_value'].pct_change()
        daily_returns = regime_portfolio[['date', 'daily_return']].copy()
        strategy_name = f'ADF ({mode.capitalize()})'
        daily_returns.columns = ["date", strategy_name]
        
        print(f"\n  ? ADF regime-aware simulation complete")
        print(f"    Mode: {mode.upper()}")
        print(f"    Final portfolio value: ${regime_portfolio['portfolio_value'].iloc[-1]:,.2f}")
        print(f"    Annualized return: {metrics['annualized_return']:.2%}")
        print(f"    Sharpe ratio: {metrics['sharpe_ratio']:.2f}")

        return {
            "strategy": strategy_name,
            "description": f"Mode: {mode}, ADF window: {adf_window}d, Regime-aware allocation (PARTIALLY VECTORIZED)",
            "metrics": metrics,
            "results": {"portfolio_values": regime_portfolio},
            "daily_returns": daily_returns,
        }
    except Exception as e:
        print(f"Error in ADF Factor backtest: {e}")
        import traceback

        traceback.print_exc()
        return None


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


def calculate_sharpe_weights_with_floor(summary_df, min_weight=0.05, strategy_caps=None):
    """
    Calculate portfolio weights based on Sharpe ratios with a minimum weight floor and optional caps.
    ALL strategies receive at least min_weight allocation (including negative Sharpe).

    Args:
        summary_df (pd.DataFrame): Summary DataFrame with backtest results
        min_weight (float): Minimum weight per strategy (default 5%)
        strategy_caps (dict): Optional dict of strategy names to max weights (e.g., {'Mean Reversion': 0.05})

    Returns:
        pd.DataFrame: DataFrame with strategies and their weights
    """
    if summary_df.empty:
        return None

    if strategy_caps is None:
        strategy_caps = {}

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

    # Apply caps to specific strategies
    for strategy_name, max_weight in strategy_caps.items():
        mask = all_weights["Strategy"] == strategy_name
        if mask.any():
            all_weights.loc[mask, "Weight"] = all_weights.loc[mask, "Weight"].apply(
                lambda x: min(x, max_weight)
            )

    # Renormalize to sum to 1.0
    weight_sum = all_weights["Weight"].sum()
    all_weights["Weight"] = all_weights["Weight"] / weight_sum

    # Create output DataFrame
    weights_df = all_weights[["Strategy", "Description", "Sharpe Ratio", "Weight"]].copy()
    weights_df["Weight_Pct"] = weights_df["Weight"] * 100

    # Sort by weight descending
    weights_df = weights_df.sort_values("Weight", ascending=False)

    return weights_df


def print_sharpe_weights(weights_df, summary_df, min_weight=0.05, strategy_caps=None):
    """Print formatted Sharpe-based weights table."""
    print("\n" + "=" * 120)
    print("SHARPE-BASED PORTFOLIO WEIGHTS")
    print("=" * 120)

    if weights_df is None or weights_df.empty:
        print("\nNo weights to display")
        return

    if strategy_caps is None:
        strategy_caps = {}

    weight_sum = weights_df["Weight"].sum()

    print(f"\nWeighting Method: All strategies with {min_weight*100:.0f}% minimum floor")
    if strategy_caps:
        print(f"Strategy Caps: {', '.join([f'{k}: {v*100:.0f}%' for k, v in strategy_caps.items()])}")
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
        default="data/raw/coinmarketcap_monthly_all_snapshots.csv",
        help="Path to market cap data CSV file (monthly snapshots)",
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
        "--start-date", type=str, default="2021-01-01", help="Start date for backtest (YYYY-MM-DD)"
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
        "--run-breakout",
        nargs='?',
        const=True,
        default=None,
        type=lambda x: x.lower() in ['true', '1', 'yes'],
        help="Run breakout signal backtest (no value=run only this, True=include, False=exclude)"
    )
    parser.add_argument(
        "--run-mean-reversion",
        nargs='?',
        const=True,
        default=None,
        type=lambda x: x.lower() in ['true', '1', 'yes'],
        help="Run mean reversion backtest (no value=run only this, True=include, False=exclude)",
    )
    parser.add_argument(
        "--run-size",
        nargs='?',
        const=True,
        default=None,
        type=lambda x: x.lower() in ['true', '1', 'yes'],
        help="Run size factor backtest (no value=run only this, True=include, False=exclude)"
    )
    parser.add_argument(
        "--run-carry",
        nargs='?',
        const=True,
        default=None,
        type=lambda x: x.lower() in ['true', '1', 'yes'],
        help="Run carry factor backtest (no value=run only this, True=include, False=exclude)"
    )
    parser.add_argument(
        "--run-days-from-high",
        nargs='?',
        const=True,
        default=None,
        type=lambda x: x.lower() in ['true', '1', 'yes'],
        help="Run days from high backtest (no value=run only this, True=include, False=exclude)",
    )
    parser.add_argument(
        "--run-oi-divergence",
        nargs='?',
        const=True,
        default=None,
        type=lambda x: x.lower() in ['true', '1', 'yes'],
        help="Run OI divergence backtest (no value=run only this, True=include, False=exclude)"
    )
    parser.add_argument(
        "--oi-mode",
        type=str,
        default="divergence",
        choices=["divergence", "trend"],
        help="OI divergence mode: divergence (contrarian) or trend (momentum)",
    )
    parser.add_argument(
        "--run-volatility",
        nargs='?',
        const=True,
        default=None,
        type=lambda x: x.lower() in ['true', '1', 'yes'],
        help="Run volatility factor backtest (no value=run only this, True=include, False=exclude)"
    )
    parser.add_argument(
        "--volatility-strategy",
        type=str,
        default="long_low_short_high",
        choices=["long_low_short_high", "long_low_vol", "long_high_vol", "long_high_short_low"],
        help="Volatility factor strategy type",
    )
    parser.add_argument(
        "--run-kurtosis",
        nargs='?',
        const=True,
        default=None,
        type=lambda x: x.lower() in ['true', '1', 'yes'],
        help="Run kurtosis factor backtest (no value=run only this, True=include, False=exclude)"
    )
    parser.add_argument(
        "--kurtosis-strategy",
        type=str,
        default="long_low_short_high",
        choices=["long_low_short_high", "long_high_short_low"],
        help="Kurtosis factor strategy type: long_low_short_high (stable), long_high_short_low (volatile)",
    )
    parser.add_argument(
        "--kurtosis-rebalance-days",
        type=int,
        default=14,
        help="Kurtosis rebalance frequency in days (optimal: 14 days for long_low_short_high in bear markets)",
    )
    parser.add_argument(
        "--run-beta",
        nargs='?',
        const=True,
        default=None,
        type=lambda x: x.lower() in ['true', '1', 'yes'],
        help="Run beta factor backtest (no value=run only this, True=include, False=exclude)"
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
    parser.add_argument(
        "--run-adf",
        nargs='?',
        const=True,
        default=None,
        type=lambda x: x.lower() in ['true', '1', 'yes'],
        help="Run ADF factor backtest with regime-aware strategy switching (no value=run only this, True=include, False=exclude)"
    )
    parser.add_argument(
        "--adf-mode",
        type=str,
        default="blended",
        choices=["blended", "moderate", "optimal"],
        help="ADF regime-switching mode: blended (conservative), moderate (balanced), optimal (aggressive)"
    )
    parser.add_argument("--adf-window", type=int, default=60, help="ADF calculation window in days")
    parser.add_argument(
        "--run-leverage-inverted",
        nargs='?',
        const=True,
        default=None,
        type=lambda x: x.lower() in ['true', '1', 'yes'],
        help="Run inverted leverage factor backtest (LONG low leverage, SHORT high leverage)"
    )
    parser.add_argument(
        "--leverage-rebalance-days",
        type=int,
        default=7,
        help="Inverted leverage rebalance frequency (optimal: 7 days, Sharpe: 1.19)"
    )
    parser.add_argument(
        "--run-dilution",
        nargs='?',
        const=True,
        default=None,
        type=lambda x: x.lower() in ['true', '1', 'yes'],
        help="Run dilution factor backtest (no value=run only this, True=include, False=exclude)"
    )
    parser.add_argument(
        "--dilution-rebalance-days",
        type=int,
        default=7,
        help="Dilution factor rebalance frequency in days (default: 7, optimal per backtest)"
    )
    parser.add_argument(
        "--run-dilution-decile-eq",
        nargs='?',
        const=True,
        default=None,
        type=lambda x: x.lower() in ['true', '1', 'yes'],
        help="Run dilution decile analysis (equal-weighted) - shows all 10 deciles"
    )
    parser.add_argument(
        "--run-dilution-decile-rp",
        nargs='?',
        const=True,
        default=None,
        type=lambda x: x.lower() in ['true', '1', 'yes'],
        help="Run dilution decile analysis (risk parity) - shows all 10 deciles"
    )
    parser.add_argument(
        "--run-turnover",
        nargs='?',
        const=True,
        default=None,
        type=lambda x: x.lower() in ['true', '1', 'yes'],
        help="Run turnover factor backtest (24h Volume / Market Cap, no value=run only this, True=include, False=exclude)"
    )
    parser.add_argument(
        "--turnover-strategy",
        type=str,
        default="long_short",
        choices=["long_low", "short_high", "long_short"],
        help="Turnover factor strategy type (default: long_short = long high turnover, short low turnover)"
    )
    parser.add_argument(
        "--turnover-rebalance-days",
        type=int,
        default=30,
        help="Turnover factor rebalance frequency in days (default: 30, Sharpe: 2.17)"
    )

    args = parser.parse_args()

    # Determine which backtests to run based on flags
    run_flags = {
        'breakout': args.run_breakout,
        'mean_reversion': args.run_mean_reversion,
        'size': args.run_size,
        'carry': args.run_carry,
        'days_from_high': args.run_days_from_high,
        'oi_divergence': args.run_oi_divergence,
        'volatility': args.run_volatility,
        'kurtosis': args.run_kurtosis,
        'beta': args.run_beta,
        'adf': args.run_adf,
        'leverage_inverted': args.run_leverage_inverted,
        'dilution': args.run_dilution,
        'dilution_decile_eq': args.run_dilution_decile_eq,
        'dilution_decile_rp': args.run_dilution_decile_rp,
        'turnover': args.run_turnover,
    }

    # Check if any flag was explicitly set to True or False
    any_explicitly_true = any(v is True for v in run_flags.values())
    any_explicitly_false = any(v is False for v in run_flags.values())

    if not any_explicitly_true and not any_explicitly_false:
        # No flags specified -> run all backtests (except OI divergence which is disabled)
        for key in run_flags:
            run_flags[key] = True
        # OI divergence is commented out in code, so don't run by default
        run_flags['oi_divergence'] = False
    elif any_explicitly_true:
        # At least one flag is True -> run only those set to True
        for key in run_flags:
            if run_flags[key] is None:
                run_flags[key] = False
            # Keep True/False as is
    elif any_explicitly_false:
        # Some flags are False but none are True -> run all except False ones
        for key in run_flags:
            if run_flags[key] is None:
                # OI divergence is commented out, so don't enable unless explicitly requested
                if key == 'oi_divergence':
                    run_flags[key] = False
                else:
                    run_flags[key] = True
            # Keep False as is

    # Update args with processed flags
    args.run_breakout = run_flags['breakout']
    args.run_mean_reversion = run_flags['mean_reversion']
    args.run_size = run_flags['size']
    args.run_carry = run_flags['carry']
    args.run_days_from_high = run_flags['days_from_high']
    args.run_oi_divergence = run_flags['oi_divergence']
    args.run_volatility = run_flags['volatility']
    args.run_kurtosis = run_flags['kurtosis']
    args.run_beta = run_flags['beta']
    args.run_adf = run_flags['adf']
    args.run_leverage_inverted = run_flags['leverage_inverted']
    args.run_dilution = run_flags['dilution']
    args.run_dilution_decile_eq = run_flags['dilution_decile_eq']
    args.run_dilution_decile_rp = run_flags['dilution_decile_rp']
    args.run_turnover = run_flags['turnover']

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
    
    # Display which backtests will run
    enabled_backtests = [name.replace('_', ' ').title() for name, enabled in run_flags.items() if enabled]
    print(f"\nBacktests to run: {', '.join(enabled_backtests)}")
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

    # 3. Size Factor (LONG small caps, SHORT large caps)
    if args.run_size:
        if loaded_data["price_data"] is not None and loaded_data["marketcap_data"] is not None:
            result = run_size_factor_backtest(
                loaded_data["price_data"],
                loaded_data["marketcap_data"],
                strategy="long_small_short_large",  # Traditional size premium: long SMALL, short LARGE
                num_buckets=5,
                rebalance_days=10,  # Optimal: 10 days
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
                rebalance_days=7,  # Optimal: 7 days (Sharpe: 0.45)
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
                weighting_method="equal_weight",
                **common_params,
            )
            if result:
                all_results.append(result)
        else:
            print("? Skipping Volatility Factor backtest: price data not available")

    # 8. Kurtosis Factor (BEAR MARKETS ONLY: Long low kurtosis, Short high kurtosis)
    if args.run_kurtosis:
        if loaded_data["price_data"] is not None:
            result = run_kurtosis_factor_backtest(
                loaded_data["price_data"],
                strategy=args.kurtosis_strategy,  # Default: long_low_short_high (long low kurtosis, short high kurtosis)
                kurtosis_window=30,
                rebalance_days=args.kurtosis_rebalance_days,
                weighting="risk_parity",
                long_percentile=20,  # Top 20% = lowest kurtosis (most stable)
                short_percentile=80,  # Top 80% = highest kurtosis (most unstable)
                regime_filter="bear_only",  # CRITICAL: Only trade when BTC 50MA < 200MA (bear market)
                reference_symbol="BTC",  # Use BTC for regime detection
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

    # 10. ADF Factor (Regime-Aware Strategy Switching)
    if args.run_adf:
        if loaded_data["price_data"] is not None:
            result = run_adf_factor_backtest(
                loaded_data["price_data"],
                mode=args.adf_mode,
                adf_window=args.adf_window,
                regression="ct",
                regime_lookback=5,
                **common_params,
            )
            if result:
                all_results.append(result)
        else:
            print("? Skipping ADF Factor backtest: price data not available")
    
    # 11. Inverted Leverage Factor (LONG low leverage, SHORT high leverage)
    if args.run_leverage_inverted:
        if loaded_data["leverage_data"] is not None and loaded_data["price_data"] is not None:
            result = run_leverage_inverted_backtest(
                loaded_data["leverage_data"],
                loaded_data["price_data"],
                rebalance_days=args.leverage_rebalance_days,
                top_n=10,
                bottom_n=10,
                transaction_cost=0.001,
                **common_params,
            )
            if result:
                all_results.append(result)
        else:
            print("? Skipping Inverted Leverage backtest: leverage or price data not available")

    # 11. Dilution Factor (Long low dilution, Short high dilution)
    if args.run_dilution:
        if loaded_data["price_data"] is not None:
            result = run_dilution_factor_backtest(
                loaded_data["price_data"],
                rebalance_days=args.dilution_rebalance_days,  # Default: 7 days (weekly)
                top_n=10,
                transaction_cost=0.001,  # 0.1% transaction cost
                **common_params,
            )
            if result:
                all_results.append(result)
        else:
            print("? Skipping Dilution Factor backtest: price data not available")
    
    # 11a. Dilution Decile Analysis - Equal-Weighted
    if args.run_dilution_decile_eq:
        if loaded_data["price_data"] is not None:
            result = run_dilution_decile_equal_weighted_backtest(
                loaded_data["price_data"],
                **common_params,
            )
            if result:
                all_results.append(result)
        else:
            print("? Skipping Dilution Decile Equal-weighted backtest: price data not available")
    
    # 11b. Dilution Decile Analysis - Risk Parity
    if args.run_dilution_decile_rp:
        if loaded_data["price_data"] is not None:
            result = run_dilution_decile_risk_parity_backtest(
                loaded_data["price_data"],
                **common_params,
            )
            if result:
                all_results.append(result)
        else:
            print("? Skipping Dilution Decile Risk Parity backtest: price data not available")

    # 12. Turnover Factor (24h Volume / Market Cap)
    if args.run_turnover:
        if loaded_data["price_data"] is not None and loaded_data["marketcap_data"] is not None:
            result = run_turnover_factor_backtest(
                loaded_data["price_data"],
                loaded_data["marketcap_data"],
                strategy=args.turnover_strategy,  # Default: long_short
                rebalance_days=args.turnover_rebalance_days,  # Default: 30 days (monthly)
                weighting_method="equal_weight",
                **common_params,
            )
            if result:
                all_results.append(result)
        else:
            print("? Skipping Turnover Factor backtest: price or market cap data not available")


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

        # Generate and save Sharpe-based weights with 5% floor and strategy caps
        strategy_caps = {
            'Mean Reversion': 0.05,  # Cap at 5% due to extreme volatility and regime dependence
            'ADF (Blended)': 0.35,  # Cap at 35% - high Sharpe but ensure diversification
            'ADF (Moderate)': 0.35,  # Cap at 35% - balanced risk/reward
            'ADF (Optimal)': 0.40,  # Cap at 40% - most aggressive, slightly higher cap
        }
        weights_df = calculate_sharpe_weights_with_floor(summary_df, min_weight=0.10, strategy_caps=strategy_caps)

        if weights_df is not None and not weights_df.empty:
            # Print weights table
            print_sharpe_weights(weights_df, summary_df, min_weight=0.10, strategy_caps=strategy_caps)

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
