"""
Modified Kurtosis Factor Backtest with Position Size Cap

This is a modified version that caps individual position sizes at a maximum percentage.
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

# Import functions from the original backtest module
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from backtest_kurtosis_factor import (
    load_data,
    calculate_rolling_kurtosis,
    calculate_volatility,
    filter_universe,
    rank_by_kurtosis,
    select_symbols_by_kurtosis,
    calculate_portfolio_returns,
)

def calculate_metrics(portfolio_df, initial_capital):
    """Calculate performance metrics."""
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
    print(f"  Max position size: {strategy_info['max_position_pct']:.1%}")

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

def backtest_with_cap(
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
    max_position_pct=0.05,  # NEW: Maximum position size as percentage of portfolio
):
    """
    Run backtest with position size cap.
    """
    print("\nStep 1: Calculating returns and kurtosis...")
    data_with_kurtosis = calculate_rolling_kurtosis(price_data, window=kurtosis_window)

    print("Step 2: Calculating volatility...")
    data_with_volatility = calculate_volatility(data_with_kurtosis, window=volatility_window)

    print("Step 3: Filtering universe by liquidity and market cap...")
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

    all_dates = sorted(filtered_data["date"].unique())
    min_required_days = max(kurtosis_window, volatility_window) + 10

    if len(all_dates) < min_required_days:
        raise ValueError(
            f"Insufficient data. Need at least {min_required_days} days, have {len(all_dates)}"
        )

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
    print(f"  Max position size: {max_position_pct:.1%}")
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

    daily_tracking_dates = all_dates[backtest_start_idx:]

    for date_idx, current_date in enumerate(daily_tracking_dates):
        is_rebalance_day = (
            last_rebalance_date is None
            or current_date in backtest_dates
            or (current_date - last_rebalance_date).days >= rebalance_days
        )

        if is_rebalance_day:
            historical_data = filtered_data[filtered_data["date"] <= current_date].copy()
            ranked_data = rank_by_kurtosis(historical_data, current_date)

            if not ranked_data.empty:
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

                # Save kurtosis data
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

                    long_weights = calculate_weights(long_vols) if long_vols else {}
                    short_weights = calculate_weights(short_vols) if short_vols else {}

                    # Apply allocation and leverage
                    for symbol, weight in long_weights.items():
                        new_weights[symbol] = weight * long_allocation * leverage

                    for symbol, weight in short_weights.items():
                        new_weights[symbol] = -weight * short_allocation * leverage

                elif weighting == "equal_weight":
                    if long_symbols:
                        long_weight = (long_allocation * leverage) / len(long_symbols)
                        for symbol in long_symbols:
                            new_weights[symbol] = long_weight

                    if short_symbols:
                        short_weight = (short_allocation * leverage) / len(short_symbols)
                        for symbol in short_symbols:
                            new_weights[symbol] = -short_weight

                # APPLY POSITION SIZE CAP
                capped_weights = {}
                for symbol, weight in new_weights.items():
                    # Cap absolute weight at max_position_pct
                    if abs(weight) > max_position_pct:
                        capped_weights[symbol] = np.sign(weight) * max_position_pct
                    else:
                        capped_weights[symbol] = weight
                
                new_weights = capped_weights

                # Record trades
                if new_weights != current_weights:
                    all_symbols = set(new_weights.keys()) | set(current_weights.keys())
                    for symbol in all_symbols:
                        old_weight = current_weights.get(symbol, 0)
                        new_weight = new_weights.get(symbol, 0)
                        if abs(new_weight - old_weight) > 0.0001:
                            kurt = ranked_data[ranked_data["symbol"] == symbol]["kurtosis"].values
                            kurt_val = kurt[0] if len(kurt) > 0 else np.nan

                            trades_history.append(
                                {
                                    "date": current_date,
                                    "symbol": symbol,
                                    "old_weight": old_weight,
                                    "new_weight": new_weight,
                                    "trade": "BUY" if new_weight > old_weight else "SELL",
                                    "signal": "LONG" if new_weight > 0 else "SHORT" if new_weight < 0 else "FLAT",
                                    "kurtosis": kurt_val,
                                    "portfolio_value": current_capital,
                                }
                            )

                current_weights = new_weights.copy()
                last_rebalance_date = current_date

        # Calculate daily returns
        next_day_data = filtered_data[filtered_data["date"] == current_date]
        if not next_day_data.empty and current_weights:
            daily_return = calculate_portfolio_returns(current_weights, next_day_data)
            current_capital *= 1 + daily_return
        
        # Track portfolio metrics
        long_exposure = sum([w for w in current_weights.values() if w > 0])
        short_exposure = abs(sum([w for w in current_weights.values() if w < 0]))
        net_exposure = sum(current_weights.values())
        gross_exposure = long_exposure + short_exposure
        num_longs = sum(1 for w in current_weights.values() if w > 0)
        num_shorts = sum(1 for w in current_weights.values() if w < 0)

        portfolio_values.append(
            {
                "date": current_date,
                "portfolio_value": current_capital,
                "long_exposure": long_exposure,
                "short_exposure": short_exposure,
                "net_exposure": net_exposure,
                "gross_exposure": gross_exposure,
                "num_long_positions": num_longs,
                "num_short_positions": num_shorts,
            }
        )

        # Progress reporting
        if (date_idx + 1) % 50 == 0 or date_idx == len(daily_tracking_dates) - 1:
            print(
                f"Progress: {date_idx + 1}/{len(daily_tracking_dates)} days | "
                f"Date: {current_date.date()} | "
                f"Value: ${current_capital:,.2f} | "
                f"Long: {num_longs} | Short: {num_shorts}"
            )

    # Convert to DataFrames
    portfolio_df = pd.DataFrame(portfolio_values)
    trades_df = pd.DataFrame(trades_history)
    kurtosis_df = pd.DataFrame(kurtosis_timeseries)

    # Calculate metrics
    metrics = calculate_metrics(portfolio_df, initial_capital)

    strategy_info = {
        "strategy": strategy,
        "kurtosis_window": kurtosis_window,
        "volatility_window": volatility_window,
        "rebalance_days": rebalance_days,
        "long_percentile": long_percentile,
        "short_percentile": short_percentile,
        "max_positions": max_positions,
        "weighting": weighting,
        "max_position_pct": max_position_pct,
        "leverage": leverage,
        "long_allocation": long_allocation,
        "short_allocation": short_allocation,
    }

    return {
        "portfolio_values": portfolio_df,
        "trades": trades_df,
        "kurtosis_timeseries": kurtosis_df,
        "metrics": metrics,
        "strategy_info": strategy_info,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Backtest Kurtosis Factor with Position Cap",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--price-data",
        type=str,
        default="data/raw/combined_coinbase_coinmarketcap_daily.csv",
        help="Path to price data",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="momentum",
        choices=["mean_reversion", "momentum"],
        help="Strategy type",
    )
    parser.add_argument("--kurtosis-window", type=int, default=30)
    parser.add_argument("--volatility-window", type=int, default=30)
    parser.add_argument("--rebalance-days", type=int, default=14)
    parser.add_argument("--long-percentile", type=float, default=20)
    parser.add_argument("--short-percentile", type=float, default=80)
    parser.add_argument("--max-positions", type=int, default=10)
    parser.add_argument("--weighting", type=str, default="risk_parity", choices=["risk_parity", "equal_weight"])
    parser.add_argument("--initial-capital", type=float, default=10000)
    parser.add_argument("--leverage", type=float, default=1.0)
    parser.add_argument("--long-allocation", type=float, default=0.5)
    parser.add_argument("--short-allocation", type=float, default=0.5)
    parser.add_argument("--min-volume", type=float, default=5_000_000)
    parser.add_argument("--min-market-cap", type=float, default=50_000_000)
    parser.add_argument("--max-position-pct", type=float, default=0.05, help="Max position size (0.05 = 5%%)")
    parser.add_argument("--start-date", type=str, default=None)
    parser.add_argument("--end-date", type=str, default=None)
    parser.add_argument("--output-prefix", type=str, default="backtests/results/kurtosis_capped")

    args = parser.parse_args()

    # Load data
    print("=" * 80)
    print("KURTOSIS FACTOR BACKTEST WITH POSITION CAP")
    print("=" * 80)
    print(f"\nLoading price data from {args.price_data}...")
    data = load_data(args.price_data)
    print(f"Loaded {len(data)} rows for {data['symbol'].nunique()} symbols")
    print(f"Date range: {data['date'].min().date()} to {data['date'].max().date()}")
    print("\nRunning backtest...")

    # Run backtest
    results = backtest_with_cap(
        data,
        strategy=args.strategy,
        kurtosis_window=args.kurtosis_window,
        volatility_window=args.volatility_window,
        rebalance_days=args.rebalance_days,
        long_percentile=args.long_percentile,
        short_percentile=args.short_percentile,
        max_positions=args.max_positions,
        weighting=args.weighting,
        start_date=args.start_date,
        end_date=args.end_date,
        initial_capital=args.initial_capital,
        leverage=args.leverage,
        long_allocation=args.long_allocation,
        short_allocation=args.short_allocation,
        min_volume=args.min_volume,
        min_market_cap=args.min_market_cap,
        max_position_pct=args.max_position_pct,
    )

    # Print and save results
    print_results(results)
    save_results(results, args.output_prefix)

    print("\n" + "=" * 80)
    print("BACKTEST COMPLETE")
    print("=" * 80)
