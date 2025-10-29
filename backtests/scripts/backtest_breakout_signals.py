"""
Backtest for Breakout Signal Trading System

This script backtests a trend-following strategy that:
1. Generates LONG signals when price breaks above 50-day high
2. Generates SHORT signals when price breaks below 50-day low
3. Exits LONG when price breaks below 70-day low
4. Exits SHORT when price breaks above 70-day high
5. Uses risk parity weighting (inverse volatility) separately for longs and shorts
6. Rebalances daily based on position state changes
7. Tracks portfolio performance over time with both long and short positions
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse
from calc_breakout_signals import calculate_breakout_signals
from calc_vola import calculate_rolling_30d_volatility
from calc_weights import calculate_weights


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
    data,
    entry_window=50,
    exit_window=70,
    volatility_window=30,
    start_date=None,
    end_date=None,
    initial_capital=10000,
    leverage=1.0,
    long_allocation=0.5,
    short_allocation=0.5,
):
    """
    Run backtest for the breakout signal system.

    Args:
        data (pd.DataFrame): Historical OHLCV data
        entry_window (int): Window for entry signals (50d high/low)
        exit_window (int): Window for exit signals (70d high/low)
        volatility_window (int): Window for volatility calculation (default 30)
        start_date (str): Start date for backtest (format: 'YYYY-MM-DD')
        end_date (str): End date for backtest (format: 'YYYY-MM-DD')
        initial_capital (float): Initial portfolio capital
        leverage (float): Leverage multiplier (default 1.0 for no leverage)
        long_allocation (float): Allocation to long side (default 0.5 = 50%)
        short_allocation (float): Allocation to short side (default 0.5 = 50%)

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

    # Need at least exit_window + volatility_window days for calculations
    min_required_days = exit_window + volatility_window

    if len(all_dates) < min_required_days:
        raise ValueError(
            f"Insufficient data. Need at least {min_required_days} days, have {len(all_dates)}"
        )

    # Start backtest after minimum required period
    backtest_start_idx = min_required_days
    backtest_dates = all_dates[backtest_start_idx:]

    if len(backtest_dates) == 0:
        backtest_dates = [all_dates[-1]]

    print(f"\nBacktest Configuration:")
    print(f"  Period: {backtest_dates[0].date()} to {backtest_dates[-1].date()}")
    print(f"  Trading days: {len(backtest_dates)}")
    print(f"  Entry window: {entry_window}d")
    print(f"  Exit window: {exit_window}d")
    print(f"  Volatility window: {volatility_window}d")
    print(f"  Initial capital: ${initial_capital:,.2f}")
    print(f"  Leverage: {leverage}x")
    print(f"  Long allocation: {long_allocation:.1%}")
    print(f"  Short allocation: {short_allocation:.1%}")
    print("=" * 80)

    # Initialize tracking variables
    portfolio_values = []
    trades_history = []
    current_weights = {}  # Combined weights (positive for long, negative for short)
    current_capital = initial_capital

    # Calculate daily returns for all data
    data_with_returns = data.copy()
    data_with_returns["daily_return"] = data_with_returns.groupby("symbol")["close"].transform(
        lambda x: np.log(x / x.shift(1))
    )

    # Main backtest loop
    for i, current_date in enumerate(backtest_dates):
        # Get data up to current date
        historical_data = data[data["date"] <= current_date].copy()

        # Step 1: Calculate breakout signals
        try:
            signals_df = calculate_breakout_signals(historical_data)
            current_signals = signals_df[signals_df["date"] == current_date]
        except Exception as e:
            print(f"Error calculating signals on {current_date}: {e}")
            continue

        # Step 2: Separate into LONG and SHORT positions
        long_symbols = current_signals[current_signals["position"] == "LONG"]["symbol"].tolist()
        short_symbols = current_signals[current_signals["position"] == "SHORT"]["symbol"].tolist()

        # Step 3: Calculate volatility for all active positions
        all_active_symbols = long_symbols + short_symbols

        new_weights = {}

        if len(all_active_symbols) > 0:
            active_data = historical_data[historical_data["symbol"].isin(all_active_symbols)]

            try:
                volatility_df = calculate_rolling_volatility_custom(
                    active_data, window=volatility_window
                )
                latest_volatility = volatility_df[volatility_df["date"] == current_date]

                # Separate volatilities for longs and shorts
                long_volatilities = {}
                short_volatilities = {}

                for _, row in latest_volatility.iterrows():
                    if not pd.isna(row["volatility_30d"]) and row["volatility_30d"] > 0:
                        if row["symbol"] in long_symbols:
                            long_volatilities[row["symbol"]] = row["volatility_30d"]
                        elif row["symbol"] in short_symbols:
                            short_volatilities[row["symbol"]] = row["volatility_30d"]

                # Step 4: Calculate risk parity weights separately for longs and shorts
                long_weights = calculate_weights(long_volatilities) if long_volatilities else {}
                short_weights = calculate_weights(short_volatilities) if short_volatilities else {}

                # Step 5: Apply leverage and allocation to each side
                # Scale long weights by long_allocation and leverage
                for symbol, weight in long_weights.items():
                    new_weights[symbol] = weight * long_allocation * leverage

                # Scale short weights by short_allocation and leverage (negative for shorts)
                for symbol, weight in short_weights.items():
                    new_weights[symbol] = -weight * short_allocation * leverage

            except Exception as e:
                print(f"Error calculating volatility/weights on {current_date}: {e}")

        # Step 6: Calculate portfolio return based on previous weights
        if i > 0 and current_weights:
            # Get returns for current date
            current_returns = data_with_returns[data_with_returns["date"] == current_date]
            portfolio_return = calculate_portfolio_returns(current_weights, current_returns)

            # Update capital
            current_capital = current_capital * np.exp(portfolio_return)

        # Step 7: Record portfolio value
        long_exposure = sum(w for w in new_weights.values() if w > 0)
        short_exposure = abs(sum(w for w in new_weights.values() if w < 0))
        net_exposure = sum(new_weights.values())

        portfolio_values.append(
            {
                "date": current_date,
                "portfolio_value": current_capital,
                "num_long_positions": len([w for w in new_weights.values() if w > 0]),
                "num_short_positions": len([w for w in new_weights.values() if w < 0]),
                "long_exposure": long_exposure,
                "short_exposure": short_exposure,
                "net_exposure": net_exposure,
                "gross_exposure": long_exposure + short_exposure,
                "long_positions": ", ".join([s for s, w in new_weights.items() if w > 0]) or "None",
                "short_positions": ", ".join([s for s, w in new_weights.items() if w < 0])
                or "None",
            }
        )

        # Step 8: Record trades (when weights change)
        if new_weights != current_weights:
            all_symbols = set(new_weights.keys()) | set(current_weights.keys())
            for symbol in all_symbols:
                old_weight = current_weights.get(symbol, 0)
                new_weight = new_weights.get(symbol, 0)
                if abs(new_weight - old_weight) > 0.0001:  # Only record significant changes
                    # Determine trade type
                    if old_weight == 0 and new_weight > 0:
                        trade_type = "ENTER_LONG"
                    elif old_weight == 0 and new_weight < 0:
                        trade_type = "ENTER_SHORT"
                    elif old_weight > 0 and new_weight == 0:
                        trade_type = "EXIT_LONG"
                    elif old_weight < 0 and new_weight == 0:
                        trade_type = "EXIT_SHORT"
                    elif old_weight > 0 and new_weight > 0:
                        trade_type = "REBALANCE_LONG"
                    elif old_weight < 0 and new_weight < 0:
                        trade_type = "REBALANCE_SHORT"
                    elif old_weight > 0 and new_weight < 0:
                        trade_type = "FLIP_LONG_TO_SHORT"
                    elif old_weight < 0 and new_weight > 0:
                        trade_type = "FLIP_SHORT_TO_LONG"
                    else:
                        trade_type = "OTHER"

                    trades_history.append(
                        {
                            "date": current_date,
                            "symbol": symbol,
                            "trade_type": trade_type,
                            "old_weight": old_weight,
                            "new_weight": new_weight,
                            "weight_change": new_weight - old_weight,
                        }
                    )

        # Update current weights
        current_weights = new_weights.copy()

        # Progress update
        if (i + 1) % 50 == 0 or i == len(backtest_dates) - 1:
            print(
                f"Progress: {i+1}/{len(backtest_dates)} days | "
                f"Date: {current_date.date()} | "
                f"Value: ${current_capital:,.2f} | "
                f"Long: {len([w for w in new_weights.values() if w > 0])} | "
                f"Short: {len([w for w in new_weights.values() if w < 0])}"
            )

    # Convert to DataFrames
    portfolio_df = pd.DataFrame(portfolio_values)
    trades_df = pd.DataFrame(trades_history)

    # Calculate performance metrics
    metrics = calculate_performance_metrics(portfolio_df, initial_capital)

    return {"portfolio_values": portfolio_df, "trades": trades_df, "metrics": metrics}


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

    print("\n" + "=" * 80)
    print("BACKTEST RESULTS")
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
    print(f"  Avg Long Positions:     {metrics['avg_long_positions']:>15.1f}")
    print(f"  Avg Short Positions:    {metrics['avg_short_positions']:>15.1f}")
    print(f"  Avg Total Positions:    {metrics['avg_total_positions']:>15.1f}")

    print(f"\nExposure Statistics:")
    print(f"  Avg Long Exposure:      {metrics['avg_long_exposure']:>15.2%}")
    print(f"  Avg Short Exposure:     {metrics['avg_short_exposure']:>15.2%}")
    print(f"  Avg Net Exposure:       {metrics['avg_net_exposure']:>15.2%}")
    print(f"  Avg Gross Exposure:     {metrics['avg_gross_exposure']:>15.2%}")

    if not results["trades"].empty:
        print(f"  Total Trades:           {len(results['trades']):>15,.0f}")

        # Trade type breakdown
        trade_types = results["trades"]["trade_type"].value_counts()
        print(f"\n  Trade Type Breakdown:")
        for trade_type, count in trade_types.items():
            print(f"    {trade_type:20s}: {count:>10,.0f}")

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

    # Show some recent trades
    if not results["trades"].empty:
        print("\n" + "=" * 80)
        print("Recent Trades (last 20):")
        print(results["trades"].tail(20).to_string(index=False))


def save_results(results, output_prefix="backtest_breakout"):
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


def main():
    """Main execution function for backtest."""
    parser = argparse.ArgumentParser(
        description="Backtest Breakout Signal Trading System",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--data-file",
        type=str,
        default="top10_markets_100d_daily_data.csv",
        help="Path to historical OHLCV data CSV file",
    )
    parser.add_argument(
        "--entry-window",
        type=int,
        default=50,
        help="Entry signal window (50d high/low for breakouts)",
    )
    parser.add_argument(
        "--exit-window", type=int, default=70, help="Exit signal window (70d high/low for exits)"
    )
    parser.add_argument(
        "--volatility-window", type=int, default=30, help="Volatility calculation window"
    )
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
        "--output-prefix", type=str, default="backtest_breakout", help="Prefix for output CSV files"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("BACKTEST: Breakout Signal Trading System")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Data file: {args.data_file}")
    print(f"  Entry window: {args.entry_window}d")
    print(f"  Exit window: {args.exit_window}d")
    print(f"  Volatility window: {args.volatility_window}d")
    print(f"  Initial capital: ${args.initial_capital:,.2f}")
    print(f"  Leverage: {args.leverage}x")
    print(f"  Long allocation: {args.long_allocation:.1%}")
    print(f"  Short allocation: {args.short_allocation:.1%}")
    print(f"  Start date: {args.start_date or 'First available'}")
    print(f"  End date: {args.end_date or 'Last available'}")
    print("=" * 80)

    # Load data
    print("\nLoading data...")
    data = load_data(args.data_file)
    print(f"Loaded {len(data)} rows for {data['symbol'].nunique()} symbols")
    print(f"Date range: {data['date'].min().date()} to {data['date'].max().date()}")

    # Run backtest
    print("\nRunning backtest...")
    results = backtest(
        data=data,
        entry_window=args.entry_window,
        exit_window=args.exit_window,
        volatility_window=args.volatility_window,
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
