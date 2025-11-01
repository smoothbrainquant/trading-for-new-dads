"""
Backtest Days from High Strategy with Different Rebalance Periods

This script backtests a momentum trading strategy that:
1. Selects instruments within 20 days of their 200-day high
2. Calculates 30-day rolling volatility for selected instruments
3. Allocates weights using risk parity (inverse volatility)
4. Tests different rebalance periods: [1, 2, 3, 5, 7, 10, 30] days
5. Compares performance across all rebalance periods

Key difference from standard backtest:
- Rebalance period determines how many trading days to hold positions before rebalancing
- Tests various holding periods to find optimal rebalance frequency
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import sys
import os

# Add parent directory to path for imports
workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, workspace_root)

from signals.calc_days_from_high import calculate_days_since_200d_high
from signals.calc_vola import calculate_rolling_30d_volatility
from signals.calc_weights import calculate_weights


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
    data,
    days_threshold=20,
    lookback_window=200,
    rebalance_period=1,  # Changed to use integer days instead of string frequency
    start_date=None,
    end_date=None,
    initial_capital=10000,
    volatility_window=30,
):
    """
    Run backtest for the days from high system with specific rebalance period.

    Args:
        data (pd.DataFrame): Historical OHLCV data
        days_threshold (int): Maximum days from 200d high to select instruments
        lookback_window (int): Lookback window for calculating high (default 200)
        volatility_window (int): Window for volatility calculation (default 30)
        rebalance_period (int): Number of trading days between rebalances
        start_date (str): Start date for backtest (format: 'YYYY-MM-DD')
        end_date (str): End date for backtest (format: 'YYYY-MM-DD')
        initial_capital (float): Initial portfolio capital

    Returns:
        dict: Dictionary containing:
            - portfolio_values: DataFrame with date and portfolio value
            - trades: DataFrame with rebalancing history
            - metrics: Dictionary of performance metrics
    """
    # Filter data by date range if specified
    if start_date:
        data = data[data["date"] >= pd.to_datetime(start_date)]
    if end_date:
        data = data[data["date"] <= pd.to_datetime(end_date)]

    # Get unique dates for rebalancing
    all_dates = sorted(data["date"].unique())

    # Adjust lookback and volatility windows if we don't have enough data
    min_required_days = lookback_window + volatility_window

    if len(all_dates) < min_required_days:
        # Adjust to use smaller windows that fit the available data
        target_backtest_days = min(20, len(all_dates) // 4)
        available_for_setup = len(all_dates) - target_backtest_days

        # Use 70% for lookback window, 30% for volatility window
        adjusted_lookback = max(30, int(available_for_setup * 0.7))
        adjusted_volatility = max(10, int(available_for_setup * 0.3))

        print(
            f"WARNING: Insufficient data for {lookback_window}d lookback + {volatility_window}d volatility."
        )
        print(f"         Available days: {len(all_dates)}")
        print(
            f"         Adjusting to {adjusted_lookback}d lookback + {adjusted_volatility}d volatility"
        )
        print(f"         Target backtest period: ~{target_backtest_days} days")

        lookback_window = adjusted_lookback
        volatility_window = adjusted_volatility
        min_required_days = lookback_window + volatility_window

    if len(all_dates) < min_required_days:
        raise ValueError(
            f"Insufficient data. Need at least {min_required_days} days, have {len(all_dates)}"
        )

    # Start backtest after minimum required period
    backtest_start_idx = min_required_days
    backtest_dates = all_dates[backtest_start_idx:]

    if len(backtest_dates) == 0:
        print(f"WARNING: No backtesting days available after setup period")
        print(f"         Using last available day only")
        backtest_dates = [all_dates[-1]]

    print(f"\nBacktest Configuration:")
    print(f"  Period: {backtest_dates[0].date()} to {backtest_dates[-1].date()}")
    print(f"  Trading days: {len(backtest_dates)}")
    print(f"  Lookback window: {lookback_window}d")
    print(f"  Volatility window: {volatility_window}d")
    print(f"  Days threshold: {days_threshold}")
    print(f"  Initial capital: ${initial_capital:,.2f}")
    print(f"  Rebalance period: {rebalance_period} trading days")
    print("=" * 80)

    # Initialize tracking variables
    portfolio_values = []
    trades_history = []
    current_weights = {}
    current_capital = initial_capital
    days_since_last_rebalance = 0

    # Calculate daily returns for all data
    data_with_returns = data.copy()
    data_with_returns["daily_return"] = data_with_returns.groupby("symbol")["close"].transform(
        lambda x: np.log(x / x.shift(1))
    )

    # Main backtest loop
    for i, current_date in enumerate(backtest_dates):
        # Get data up to current date
        historical_data = data[data["date"] <= current_date].copy()

        # Determine if we should rebalance today
        should_rebalance = (i == 0) or (days_since_last_rebalance >= rebalance_period)

        # Step 1: Calculate portfolio return based on previous weights (always do this)
        if i > 0 and current_weights:
            # Get returns for current date
            current_returns = data_with_returns[data_with_returns["date"] == current_date]
            portfolio_return = calculate_portfolio_returns(current_weights, current_returns)

            # Update capital
            current_capital = current_capital * np.exp(portfolio_return)

        # Step 2: Rebalance if needed
        if should_rebalance:
            # Calculate days since 200d high
            try:
                days_from_high_df = calculate_days_since_200d_high(historical_data)
                latest_days_from_high = days_from_high_df[days_from_high_df["date"] == current_date]
            except Exception as e:
                print(f"Error calculating days from high on {current_date}: {e}")
                # Keep existing weights if calculation fails
                portfolio_values.append(
                    {
                        "date": current_date,
                        "portfolio_value": current_capital,
                        "num_positions": len(current_weights),
                        "positions": ", ".join(current_weights.keys()) if current_weights else "None",
                        "rebalanced": False,
                    }
                )
                days_since_last_rebalance += 1
                continue

            # Select instruments within threshold
            selected_instruments = latest_days_from_high[
                latest_days_from_high["days_since_200d_high"] <= days_threshold
            ]

            selected_symbols = selected_instruments["symbol"].tolist()

            # Calculate volatility for selected instruments
            if len(selected_symbols) > 0:
                selected_data = historical_data[historical_data["symbol"].isin(selected_symbols)]

                try:
                    volatility_df = calculate_rolling_volatility_custom(
                        selected_data, window=volatility_window
                    )
                    latest_volatility = volatility_df[volatility_df["date"] == current_date]

                    # Create volatility dictionary
                    volatilities = {}
                    for _, row in latest_volatility.iterrows():
                        if not pd.isna(row["volatility_30d"]) and row["volatility_30d"] > 0:
                            volatilities[row["symbol"]] = row["volatility_30d"]

                except Exception as e:
                    print(f"Error calculating volatility on {current_date}: {e}")
                    volatilities = {}
            else:
                volatilities = {}

            # Calculate weights using risk parity
            new_weights = calculate_weights(volatilities) if volatilities else {}

            # Record trades (when weights change)
            if new_weights != current_weights:
                all_symbols = set(new_weights.keys()) | set(current_weights.keys())
                for symbol in all_symbols:
                    old_weight = current_weights.get(symbol, 0)
                    new_weight = new_weights.get(symbol, 0)
                    if abs(new_weight - old_weight) > 0.0001:  # Only record significant changes
                        trades_history.append(
                            {
                                "date": current_date,
                                "symbol": symbol,
                                "old_weight": old_weight,
                                "new_weight": new_weight,
                                "weight_change": new_weight - old_weight,
                            }
                        )

            # Update current weights
            current_weights = new_weights.copy()
            days_since_last_rebalance = 0
        else:
            # Not rebalancing, just track days
            days_since_last_rebalance += 1

        # Record portfolio value
        portfolio_values.append(
            {
                "date": current_date,
                "portfolio_value": current_capital,
                "num_positions": len(current_weights),
                "positions": ", ".join(current_weights.keys()) if current_weights else "None",
                "rebalanced": should_rebalance,
            }
        )

        # Progress update
        if (i + 1) % 50 == 0 or i == len(backtest_dates) - 1:
            print(
                f"Progress: {i+1}/{len(backtest_dates)} days | "
                f"Date: {current_date.date()} | "
                f"Value: ${current_capital:,.2f} | "
                f"Positions: {len(current_weights)}"
            )

    # Convert to DataFrames
    portfolio_df = pd.DataFrame(portfolio_values)
    trades_df = pd.DataFrame(trades_history)

    # Calculate performance metrics
    metrics = calculate_performance_metrics(portfolio_df, initial_capital, rebalance_period)

    return {"portfolio_values": portfolio_df, "trades": trades_df, "metrics": metrics}


def calculate_performance_metrics(portfolio_df, initial_capital, rebalance_period):
    """
    Calculate performance metrics for the backtest.

    Args:
        portfolio_df (pd.DataFrame): DataFrame with portfolio values over time
        initial_capital (float): Initial portfolio capital
        rebalance_period (int): Rebalance period in trading days

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

    # Average number of positions
    avg_positions = portfolio_df["num_positions"].mean()

    # Count actual rebalances
    num_rebalances = portfolio_df["rebalanced"].sum() if "rebalanced" in portfolio_df.columns else 0

    metrics = {
        "rebalance_period": rebalance_period,
        "initial_capital": initial_capital,
        "final_value": final_value,
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_vol,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "total_trades": len(portfolio_df),
        "avg_positions": avg_positions,
        "num_days": num_days,
        "num_rebalances": num_rebalances,
    }

    return metrics


def print_results(results):
    """
    Print backtest results in a formatted manner.

    Args:
        results (dict): Dictionary containing backtest results
    """
    metrics = results["metrics"]

    print("\n" + "=" * 80)
    print(f"BACKTEST RESULTS - Rebalance Period: {metrics['rebalance_period']} days")
    print("=" * 80)
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
    print(f"  Avg Positions:          {metrics['avg_positions']:>15.1f}")
    print(f"  Number of Rebalances:   {metrics['num_rebalances']:>15,.0f}")
    print(f"  Total Weight Changes:   {len(results['trades']):>15,.0f}")

    print("\n" + "=" * 80)


def save_results(results, output_prefix="backtest", rebalance_period=1):
    """
    Save backtest results to CSV files.

    Args:
        results (dict): Dictionary containing backtest results
        output_prefix (str): Prefix for output filenames
        rebalance_period (int): Rebalance period in days
    """
    # Create output filename with rebalance period
    output_dir = "backtests/results"
    os.makedirs(output_dir, exist_ok=True)

    # Save portfolio values
    portfolio_file = f"{output_dir}/{output_prefix}_rebalance_{rebalance_period}d_portfolio.csv"
    results["portfolio_values"].to_csv(portfolio_file, index=False)
    print(f"\nPortfolio values saved to: {portfolio_file}")

    # Save trades
    if not results["trades"].empty:
        trades_file = f"{output_dir}/{output_prefix}_rebalance_{rebalance_period}d_trades.csv"
        results["trades"].to_csv(trades_file, index=False)
        print(f"Trades history saved to: {trades_file}")

    # Save metrics
    metrics_file = f"{output_dir}/{output_prefix}_rebalance_{rebalance_period}d_metrics.csv"
    metrics_df = pd.DataFrame([results["metrics"]])
    metrics_df.to_csv(metrics_file, index=False)
    print(f"Performance metrics saved to: {metrics_file}")


def run_multi_period_backtest(data, rebalance_periods, **kwargs):
    """
    Run backtest across multiple rebalance periods and compare results.

    Args:
        data (pd.DataFrame): Historical OHLCV data
        rebalance_periods (list): List of rebalance periods to test
        **kwargs: Additional arguments to pass to backtest function

    Returns:
        dict: Dictionary mapping rebalance periods to results
    """
    all_results = {}

    print("\n" + "=" * 80)
    print("MULTI-PERIOD BACKTEST STARTING")
    print("=" * 80)
    print(f"\nTesting rebalance periods: {rebalance_periods}")
    print("=" * 80)

    for period in rebalance_periods:
        print(f"\n\n{'='*80}")
        print(f"Testing Rebalance Period: {period} days")
        print("=" * 80)

        results = backtest(data, rebalance_period=period, **kwargs)
        all_results[period] = results

        print_results(results)

        # Save individual results
        save_results(results, output_prefix="days_from_high", rebalance_period=period)

    return all_results


def create_comparison_report(all_results, output_file="backtests/results/rebalance_period_comparison.csv"):
    """
    Create a comparison report of all rebalance periods.

    Args:
        all_results (dict): Dictionary mapping rebalance periods to results
        output_file (str): Path to save comparison report
    """
    comparison_data = []

    for period, results in sorted(all_results.items()):
        metrics = results["metrics"]
        comparison_data.append(
            {
                "rebalance_period": period,
                "final_value": metrics["final_value"],
                "total_return": metrics["total_return"],
                "annualized_return": metrics["annualized_return"],
                "annualized_volatility": metrics["annualized_volatility"],
                "sharpe_ratio": metrics["sharpe_ratio"],
                "max_drawdown": metrics["max_drawdown"],
                "win_rate": metrics["win_rate"],
                "num_rebalances": metrics["num_rebalances"],
                "avg_positions": metrics["avg_positions"],
            }
        )

    comparison_df = pd.DataFrame(comparison_data)
    comparison_df.to_csv(output_file, index=False)

    print("\n\n" + "=" * 80)
    print("COMPARISON REPORT - ALL REBALANCE PERIODS")
    print("=" * 80)
    print(f"\n{comparison_df.to_string(index=False)}")
    print("\n" + "=" * 80)
    print(f"\nComparison report saved to: {output_file}")
    print("=" * 80)

    # Find best performing period by Sharpe ratio
    best_sharpe_idx = comparison_df["sharpe_ratio"].idxmax()
    best_sharpe_period = comparison_df.loc[best_sharpe_idx, "rebalance_period"]
    best_sharpe = comparison_df.loc[best_sharpe_idx, "sharpe_ratio"]

    # Find best performing period by total return
    best_return_idx = comparison_df["total_return"].idxmax()
    best_return_period = comparison_df.loc[best_return_idx, "rebalance_period"]
    best_return = comparison_df.loc[best_return_idx, "total_return"]

    print(f"\n📊 KEY INSIGHTS:")
    print(f"  Best Sharpe Ratio:      {best_sharpe_period} days (Sharpe: {best_sharpe:.2f})")
    print(f"  Best Total Return:      {best_return_period} days (Return: {best_return:.2%})")
    print("=" * 80)

    return comparison_df


def main():
    """Main execution function for multi-period backtest."""
    parser = argparse.ArgumentParser(
        description="Backtest Days from High Strategy with Multiple Rebalance Periods",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--data-file",
        type=str,
        default="data/raw/top10_markets_500d_daily_data.csv",
        help="Path to historical OHLCV data CSV file",
    )
    parser.add_argument(
        "--days-threshold",
        type=int,
        default=20,
        help="Maximum days from 200d high to select instruments",
    )
    parser.add_argument(
        "--initial-capital", type=float, default=10000, help="Initial portfolio capital in USD"
    )
    parser.add_argument(
        "--start-date", type=str, default=None, help="Start date for backtest (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date", type=str, default=None, help="End date for backtest (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--rebalance-periods",
        type=str,
        default="1,2,3,5,7,10,30",
        help="Comma-separated list of rebalance periods in trading days",
    )

    args = parser.parse_args()

    # Parse rebalance periods
    rebalance_periods = [int(x.strip()) for x in args.rebalance_periods.split(",")]

    print("=" * 80)
    print("BACKTEST: Days from High - Multiple Rebalance Periods")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Data file: {args.data_file}")
    print(f"  Days threshold: {args.days_threshold}")
    print(f"  Initial capital: ${args.initial_capital:,.2f}")
    print(f"  Start date: {args.start_date or 'First available'}")
    print(f"  End date: {args.end_date or 'Last available'}")
    print(f"  Rebalance periods: {rebalance_periods}")
    print("=" * 80)

    # Load data
    print("\nLoading data...")
    data = load_data(args.data_file)
    print(f"Loaded {len(data)} rows for {data['symbol'].nunique()} symbols")
    print(f"Date range: {data['date'].min().date()} to {data['date'].max().date()}")

    # Run multi-period backtest
    all_results = run_multi_period_backtest(
        data=data,
        rebalance_periods=rebalance_periods,
        days_threshold=args.days_threshold,
        initial_capital=args.initial_capital,
        start_date=args.start_date,
        end_date=args.end_date,
    )

    # Create comparison report
    create_comparison_report(all_results)

    print("\n" + "=" * 80)
    print("BACKTEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
