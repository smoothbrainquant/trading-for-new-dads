"""
Analyze Breakout Strategy by Side (Long vs Short)

Breaks down performance to show:
- Long-only performance
- Short-only performance
- Combined long/short performance
"""

import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "signals"))

from calc_breakout_signals import calculate_breakout_signals
from calc_vola import calculate_rolling_30d_volatility
from calc_weights import calculate_weights


def calculate_rolling_volatility_custom(data, window=30):
    """Calculate rolling volatility with custom window size."""
    df = data.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    df["daily_return"] = df.groupby("symbol")["close"].transform(lambda x: np.log(x / x.shift(1)))
    df["volatility_30d"] = df.groupby("symbol")["daily_return"].transform(
        lambda x: x.rolling(window=window, min_periods=window).std() * np.sqrt(365)
    )
    return df[["date", "symbol", "close", "daily_return", "volatility_30d"]]


def calculate_portfolio_returns(weights, returns_df):
    """Calculate portfolio returns based on weights and individual asset returns."""
    if not weights or returns_df.empty:
        return 0.0
    
    portfolio_return = 0.0
    for symbol, weight in weights.items():
        symbol_return = returns_df[returns_df["symbol"] == symbol]["daily_return"].values
        if len(symbol_return) > 0 and not np.isnan(symbol_return[0]):
            portfolio_return += weight * symbol_return[0]
    
    return portfolio_return


def backtest_by_side(
    data,
    entry_window=50,
    exit_window=70,
    volatility_window=30,
    start_date=None,
    end_date=None,
    initial_capital=10000,
    leverage=1.0,
):
    """
    Run backtest and track long, short, and combined performance separately.
    
    Returns:
        dict with three portfolio series: 'long', 'short', 'combined'
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
    print(f"  Initial capital: ${initial_capital:,.2f}")
    
    # Calculate signals and volatilities once upfront
    print("\nCalculating signals and volatilities...")
    all_signals_df = calculate_breakout_signals(data)
    all_volatilities_df = calculate_rolling_volatility_custom(data, window=volatility_window)
    
    # Initialize tracking variables - separate for long and short
    long_values = []
    short_values = []
    combined_values = []
    
    long_capital = initial_capital / 2
    short_capital = initial_capital / 2
    combined_capital = initial_capital
    
    current_long_weights = {}
    current_short_weights = {}
    current_combined_weights = {}
    
    # Calculate daily returns for all data
    data_with_returns = data.copy()
    data_with_returns["daily_return"] = data_with_returns.groupby("symbol")["close"].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Main backtest loop
    for i, current_date in enumerate(backtest_dates):
        # Get pre-calculated signals for current date
        current_signals = all_signals_df[all_signals_df["date"] == current_date]
        
        # Separate into LONG and SHORT positions
        long_symbols = current_signals[current_signals["position"] == "LONG"]["symbol"].tolist()
        short_symbols = current_signals[current_signals["position"] == "SHORT"]["symbol"].tolist()
        
        # Get pre-calculated volatilities
        new_long_weights = {}
        new_short_weights = {}
        
        # Calculate long weights
        if len(long_symbols) > 0:
            latest_volatility = all_volatilities_df[
                (all_volatilities_df["date"] == current_date) &
                (all_volatilities_df["symbol"].isin(long_symbols))
            ]
            
            long_volatilities = {}
            for _, row in latest_volatility.iterrows():
                if not pd.isna(row["volatility_30d"]) and row["volatility_30d"] > 0:
                    long_volatilities[row["symbol"]] = row["volatility_30d"]
            
            if long_volatilities:
                new_long_weights = calculate_weights(long_volatilities)
                # Scale to use full capital with leverage
                for symbol in new_long_weights:
                    new_long_weights[symbol] = new_long_weights[symbol] * leverage
        
        # Calculate short weights
        if len(short_symbols) > 0:
            latest_volatility = all_volatilities_df[
                (all_volatilities_df["date"] == current_date) &
                (all_volatilities_df["symbol"].isin(short_symbols))
            ]
            
            short_volatilities = {}
            for _, row in latest_volatility.iterrows():
                if not pd.isna(row["volatility_30d"]) and row["volatility_30d"] > 0:
                    short_volatilities[row["symbol"]] = row["volatility_30d"]
            
            if short_volatilities:
                new_short_weights = calculate_weights(short_volatilities)
                # Scale to use full capital with leverage (negative for shorts)
                for symbol in new_short_weights:
                    new_short_weights[symbol] = new_short_weights[symbol] * leverage
        
        # Calculate combined weights (50% long, 50% short allocation)
        new_combined_weights = {}
        for symbol, weight in new_long_weights.items():
            new_combined_weights[symbol] = weight * 0.5  # 50% to longs
        for symbol, weight in new_short_weights.items():
            new_combined_weights[symbol] = -weight * 0.5  # 50% to shorts (negative)
        
        # Calculate returns for each side
        if i > 0:
            current_returns = data_with_returns[data_with_returns["date"] == current_date]
            
            # Long-only return
            if current_long_weights:
                long_return = calculate_portfolio_returns(current_long_weights, current_returns)
                long_capital = long_capital * np.exp(long_return)
            
            # Short-only return (negative weights)
            if current_short_weights:
                short_weights_negative = {s: -w for s, w in current_short_weights.items()}
                short_return = calculate_portfolio_returns(short_weights_negative, current_returns)
                short_capital = short_capital * np.exp(short_return)
            
            # Combined return
            if current_combined_weights:
                combined_return = calculate_portfolio_returns(current_combined_weights, current_returns)
                combined_capital = combined_capital * np.exp(combined_return)
        
        # Record values
        long_values.append({
            "date": current_date,
            "portfolio_value": long_capital,
            "num_positions": len(new_long_weights)
        })
        
        short_values.append({
            "date": current_date,
            "portfolio_value": short_capital,
            "num_positions": len(new_short_weights)
        })
        
        combined_values.append({
            "date": current_date,
            "portfolio_value": combined_capital,
            "num_long_positions": len(new_long_weights),
            "num_short_positions": len(new_short_weights)
        })
        
        # Update weights
        current_long_weights = new_long_weights.copy()
        current_short_weights = new_short_weights.copy()
        current_combined_weights = new_combined_weights.copy()
        
        # Progress update
        if (i + 1) % 100 == 0 or i == len(backtest_dates) - 1:
            print(f"Progress: {i+1}/{len(backtest_dates)} days | " +
                  f"Long: ${long_capital:,.2f} | Short: ${short_capital:,.2f} | " +
                  f"Combined: ${combined_capital:,.2f}")
    
    return {
        "long": pd.DataFrame(long_values),
        "short": pd.DataFrame(short_values),
        "combined": pd.DataFrame(combined_values),
    }


def calculate_metrics(portfolio_df, initial_capital, side_name):
    """Calculate performance metrics for a portfolio side."""
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
    
    return {
        "side": side_name,
        "initial_capital": initial_capital,
        "final_value": final_value,
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_vol,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "num_days": num_days,
    }


def print_side_comparison(metrics_list):
    """Print formatted comparison of long vs short vs combined."""
    print("\n" + "=" * 120)
    print("PERFORMANCE BY SIDE: LONG vs SHORT vs COMBINED")
    print("=" * 120)
    
    df = pd.DataFrame(metrics_list)
    
    # Format for display
    display_df = df.copy()
    
    # Add color indicators
    display_df["Performance"] = display_df["sharpe_ratio"].apply(
        lambda x: "?? Strong" if x > 0.5 else ("?? Moderate" if x > 0.3 else "?? Weak")
    )
    
    print("\nCore Metrics:")
    print("-" * 120)
    for _, row in display_df.iterrows():
        print(f"\n{row['side'].upper()} SIDE {row['Performance']}")
        print(f"  Final Value:         ${row['final_value']:>15,.2f}  (Initial: ${row['initial_capital']:>,.2f})")
        print(f"  Total Return:        {row['total_return']:>15.2%}")
        print(f"  Annualized Return:   {row['annualized_return']:>15.2%}")
        print(f"  Sharpe Ratio:        {row['sharpe_ratio']:>15.3f}")
        print(f"  Volatility:          {row['annualized_volatility']:>15.2%}")
        print(f"  Max Drawdown:        {row['max_drawdown']:>15.2%}")
        print(f"  Win Rate:            {row['win_rate']:>15.2%}")
    
    print("\n" + "=" * 120)
    print("SIDE COMPARISON SUMMARY")
    print("=" * 120)
    
    # Create comparison table
    comparison = pd.DataFrame({
        "Side": df["side"],
        "Total Return": df["total_return"].apply(lambda x: f"{x:.2%}"),
        "Ann. Return": df["annualized_return"].apply(lambda x: f"{x:.2%}"),
        "Sharpe": df["sharpe_ratio"].apply(lambda x: f"{x:.3f}"),
        "Max DD": df["max_drawdown"].apply(lambda x: f"{x:.2%}"),
        "Win Rate": df["win_rate"].apply(lambda x: f"{x:.2%}"),
        "Final Value": df["final_value"].apply(lambda x: f"${x:,.2f}"),
    })
    
    print("\n" + comparison.to_string(index=False))
    print("\n" + "=" * 120)


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Analyze Breakout Strategy by Side",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--data-file",
        type=str,
        default="../../data/raw/combined_coinbase_coinmarketcap_daily.csv",
        help="Path to historical OHLCV data CSV file",
    )
    parser.add_argument(
        "--entry-window", type=int, default=50, help="Entry signal window"
    )
    parser.add_argument(
        "--exit-window", type=int, default=70, help="Exit signal window"
    )
    parser.add_argument(
        "--volatility-window", type=int, default=30, help="Volatility calculation window"
    )
    parser.add_argument(
        "--initial-capital", type=float, default=10000, help="Initial portfolio capital"
    )
    parser.add_argument(
        "--leverage", type=float, default=1.0, help="Leverage multiplier"
    )
    parser.add_argument(
        "--start-date", type=str, default="2023-01-01", help="Start date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date", type=str, default=None, help="End date (YYYY-MM-DD)"
    )
    
    args = parser.parse_args()
    
    print("=" * 120)
    print("BREAKOUT STRATEGY: LONG vs SHORT PERFORMANCE BREAKDOWN")
    print("=" * 120)
    
    # Load data
    print("\nLoading data...")
    df = pd.read_csv(args.data_file)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)
    print(f"Loaded {len(df)} rows for {df['symbol'].nunique()} symbols")
    print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    
    # Run backtest by side
    print("\nRunning backtest with side breakdown...")
    results = backtest_by_side(
        data=df,
        entry_window=args.entry_window,
        exit_window=args.exit_window,
        volatility_window=args.volatility_window,
        initial_capital=args.initial_capital,
        leverage=args.leverage,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    
    # Calculate metrics for each side
    initial_per_side = args.initial_capital / 2
    
    metrics_list = [
        calculate_metrics(results["long"], initial_per_side, "Long Only"),
        calculate_metrics(results["short"], initial_per_side, "Short Only"),
        calculate_metrics(results["combined"], args.initial_capital, "Combined (50/50)"),
    ]
    
    # Print comparison
    print_side_comparison(metrics_list)
    
    # Save detailed results
    output_dir = "backtests/results"
    os.makedirs(output_dir, exist_ok=True)
    
    results["long"].to_csv(f"{output_dir}/breakout_long_only.csv", index=False)
    results["short"].to_csv(f"{output_dir}/breakout_short_only.csv", index=False)
    results["combined"].to_csv(f"{output_dir}/breakout_combined.csv", index=False)
    
    print(f"\nDetailed results saved to {output_dir}/")
    print("  - breakout_long_only.csv")
    print("  - breakout_short_only.csv")
    print("  - breakout_combined.csv")


if __name__ == "__main__":
    main()
