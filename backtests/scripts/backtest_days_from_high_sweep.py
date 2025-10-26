"""
Backtest sweep for Days-from-High/Low strategy (LONG and SHORT).

Strategy:
- LONG side: select symbols within X days of their 200-day high
- SHORT side: select symbols within X days of their 200-day low
- Risk parity (inverse volatility) weighting per side
- Combine long and short weights (short weights negative)
- Rebalance daily

Outputs:
- Summary CSV of metrics per threshold
- Optional per-threshold detailed CSVs (portfolio values, trades, metrics)
"""

import argparse
import os
import sys
from typing import Dict, List

import numpy as np
import pandas as pd

# Ensure we can import helper modules from the signals package directory
CURRENT_DIR = os.path.dirname(__file__)
SIGNALS_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '..', '..', 'signals'))
if SIGNALS_DIR not in sys.path:
    sys.path.insert(0, SIGNALS_DIR)

from calc_days_from_high import (
    calculate_days_since_200d_high,
    calculate_days_since_200d_low,
)
from calc_weights import calculate_weights


def load_data(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    return df


def calculate_rolling_volatility_custom(data: pd.DataFrame, window: int = 30) -> pd.DataFrame:
    df = data.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)

    df['daily_return'] = df.groupby('symbol')['close'].transform(lambda x: np.log(x / x.shift(1)))
    df['volatility_30d'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=window, min_periods=window).std() * np.sqrt(365)
    )
    return df[['date', 'symbol', 'close', 'daily_return', 'volatility_30d']]


def calculate_portfolio_returns(weights: Dict[str, float], returns_df: pd.DataFrame) -> float:
    if not weights or returns_df.empty:
        return 0.0
    portfolio_return = 0.0
    for symbol, weight in weights.items():
        symbol_return = returns_df[returns_df['symbol'] == symbol]['daily_return'].values
        if len(symbol_return) > 0 and not np.isnan(symbol_return[0]):
            portfolio_return += weight * symbol_return[0]
    return portfolio_return


def calculate_performance_metrics(portfolio_df: pd.DataFrame, initial_capital: float) -> Dict[str, float]:
    portfolio_df = portfolio_df.copy()
    portfolio_df['daily_return'] = portfolio_df['portfolio_value'].pct_change()
    portfolio_df['log_return'] = np.log(portfolio_df['portfolio_value'] / portfolio_df['portfolio_value'].shift(1))

    final_value = float(portfolio_df['portfolio_value'].iloc[-1])
    total_return = (final_value - initial_capital) / initial_capital

    num_days = len(portfolio_df)
    years = num_days / 365.25
    annualized_return = (final_value / initial_capital) ** (1 / years) - 1 if years > 0 else 0.0

    daily_returns = portfolio_df['log_return'].dropna()
    daily_vol = daily_returns.std()
    annualized_vol = float(daily_vol * np.sqrt(365)) if not np.isnan(daily_vol) else 0.0
    sharpe_ratio = (annualized_return / annualized_vol) if annualized_vol > 0 else 0.0

    cumulative_returns = (1 + portfolio_df['daily_return'].fillna(0)).cumprod()
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max
    max_drawdown = float(drawdown.min()) if len(drawdown) else 0.0

    positive_days = (daily_returns > 0).sum()
    total_trading_days = len(daily_returns)
    win_rate = float(positive_days / total_trading_days) if total_trading_days > 0 else 0.0

    avg_long_positions = float(portfolio_df['num_long_positions'].mean()) if 'num_long_positions' in portfolio_df.columns else np.nan
    avg_short_positions = float(portfolio_df['num_short_positions'].mean()) if 'num_short_positions' in portfolio_df.columns else np.nan
    avg_total_positions = float(avg_long_positions + avg_short_positions) if not np.isnan(avg_long_positions) and not np.isnan(avg_short_positions) else np.nan

    avg_long_exposure = float(portfolio_df['long_exposure'].mean()) if 'long_exposure' in portfolio_df.columns else np.nan
    avg_short_exposure = float(portfolio_df['short_exposure'].mean()) if 'short_exposure' in portfolio_df.columns else np.nan
    avg_net_exposure = float(portfolio_df['net_exposure'].mean()) if 'net_exposure' in portfolio_df.columns else np.nan
    avg_gross_exposure = float(portfolio_df['gross_exposure'].mean()) if 'gross_exposure' in portfolio_df.columns else np.nan

    return {
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'annualized_return': annualized_return,
        'annualized_volatility': annualized_vol,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'num_days': num_days,
        'avg_long_positions': avg_long_positions,
        'avg_short_positions': avg_short_positions,
        'avg_total_positions': avg_total_positions,
        'avg_long_exposure': avg_long_exposure,
        'avg_short_exposure': avg_short_exposure,
        'avg_net_exposure': avg_net_exposure,
        'avg_gross_exposure': avg_gross_exposure,
    }


def backtest_long_short(
    data: pd.DataFrame,
    days_threshold: int = 20,
    lookback_window: int = 200,
    volatility_window: int = 30,
    start_date: str | None = None,
    end_date: str | None = None,
    initial_capital: float = 10000.0,
    leverage: float = 1.0,
    long_allocation: float = 0.5,
    short_allocation: float = 0.5,
) -> Dict[str, pd.DataFrame | Dict[str, float]]:
    # Filter data by date range if specified
    if start_date:
        data = data[data['date'] >= pd.to_datetime(start_date)]
    if end_date:
        data = data[data['date'] <= pd.to_datetime(end_date)]

    all_dates = sorted(data['date'].unique())
    min_required_days = lookback_window + volatility_window
    if len(all_dates) < min_required_days:
        raise ValueError(f"Insufficient data. Need at least {min_required_days} days, have {len(all_dates)}")

    backtest_start_idx = min_required_days
    backtest_dates = all_dates[backtest_start_idx:]
    if len(backtest_dates) == 0:
        backtest_dates = [all_dates[-1]]

    # Precompute returns for all data
    data_with_returns = data.copy()
    data_with_returns['daily_return'] = data_with_returns.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )

    portfolio_values: List[Dict] = []
    trades_history: List[Dict] = []
    current_weights: Dict[str, float] = {}
    current_capital: float = initial_capital

    for i, current_date in enumerate(backtest_dates):
        historical_data = data[data['date'] <= current_date].copy()

        # Days since highs and lows at current date
        try:
            days_from_high_df = calculate_days_since_200d_high(historical_data)
            latest_high = days_from_high_df[days_from_high_df['date'] == current_date]
        except Exception as e:
            print(f"Error calculating days_from_high on {current_date}: {e}")
            continue

        try:
            days_from_low_df = calculate_days_since_200d_low(historical_data)
            latest_low = days_from_low_df[days_from_low_df['date'] == current_date]
        except Exception as e:
            print(f"Error calculating days_from_low on {current_date}: {e}")
            continue

        # Select symbols
        long_symbols = latest_high[latest_high['days_since_200d_high'] <= days_threshold]['symbol'].tolist()
        short_symbols = latest_low[latest_low['days_since_200d_low'] <= days_threshold]['symbol'].tolist()

        all_active_symbols = list(set(long_symbols + short_symbols))
        new_weights: Dict[str, float] = {}

        if len(all_active_symbols) > 0:
            active_data = historical_data[historical_data['symbol'].isin(all_active_symbols)]
            try:
                volatility_df = calculate_rolling_volatility_custom(active_data, window=volatility_window)
                latest_volatility = volatility_df[volatility_df['date'] == current_date]

                long_vols: Dict[str, float] = {}
                short_vols: Dict[str, float] = {}
                for _, row in latest_volatility.iterrows():
                    vol = row['volatility_30d']
                    if pd.notna(vol) and vol > 0:
                        sym = row['symbol']
                        if sym in long_symbols:
                            long_vols[sym] = float(vol)
                        if sym in short_symbols:
                            short_vols[sym] = float(vol)

                long_weights = calculate_weights(long_vols) if long_vols else {}
                short_weights = calculate_weights(short_vols) if short_vols else {}

                for sym, w in long_weights.items():
                    new_weights[sym] = w * long_allocation * leverage
                for sym, w in short_weights.items():
                    new_weights[sym] = -w * short_allocation * leverage
            except Exception as e:
                print(f"Error calculating volatility/weights on {current_date}: {e}")

        # Apply previous-day weights to today's returns
        if i > 0 and current_weights:
            current_returns = data_with_returns[data_with_returns['date'] == current_date]
            portfolio_return = calculate_portfolio_returns(current_weights, current_returns)
            current_capital = current_capital * np.exp(portfolio_return)

        long_exposure = sum(w for w in new_weights.values() if w > 0)
        short_exposure = abs(sum(w for w in new_weights.values() if w < 0))
        net_exposure = sum(new_weights.values())

        portfolio_values.append({
            'date': current_date,
            'portfolio_value': current_capital,
            'num_long_positions': len([w for w in new_weights.values() if w > 0]),
            'num_short_positions': len([w for w in new_weights.values() if w < 0]),
            'long_exposure': long_exposure,
            'short_exposure': short_exposure,
            'net_exposure': net_exposure,
            'gross_exposure': long_exposure + short_exposure,
            'long_positions': ', '.join([s for s, w in new_weights.items() if w > 0]) or 'None',
            'short_positions': ', '.join([s for s, w in new_weights.items() if w < 0]) or 'None',
        })

        if new_weights != current_weights:
            all_syms = set(new_weights.keys()) | set(current_weights.keys())
            for sym in all_syms:
                old_w = current_weights.get(sym, 0.0)
                new_w = new_weights.get(sym, 0.0)
                if abs(new_w - old_w) > 0.0001:
                    if old_w == 0 and new_w > 0:
                        trade_type = 'ENTER_LONG'
                    elif old_w == 0 and new_w < 0:
                        trade_type = 'ENTER_SHORT'
                    elif old_w > 0 and new_w == 0:
                        trade_type = 'EXIT_LONG'
                    elif old_w < 0 and new_w == 0:
                        trade_type = 'EXIT_SHORT'
                    elif old_w > 0 and new_w > 0:
                        trade_type = 'REBALANCE_LONG'
                    elif old_w < 0 and new_w < 0:
                        trade_type = 'REBALANCE_SHORT'
                    elif old_w > 0 and new_w < 0:
                        trade_type = 'FLIP_LONG_TO_SHORT'
                    elif old_w < 0 and new_w > 0:
                        trade_type = 'FLIP_SHORT_TO_LONG'
                    else:
                        trade_type = 'OTHER'

                    trades_history.append({
                        'date': current_date,
                        'symbol': sym,
                        'trade_type': trade_type,
                        'old_weight': old_w,
                        'new_weight': new_w,
                        'weight_change': new_w - old_w,
                    })

        current_weights = new_weights.copy()

        if (i + 1) % 50 == 0 or i == len(backtest_dates) - 1:
            print(
                f"Progress: {i+1}/{len(backtest_dates)} days | Date: {current_date.date()} | "
                f"Value: ${current_capital:,.2f} | Long: {len([w for w in new_weights.values() if w > 0])} | "
                f"Short: {len([w for w in new_weights.values() if w < 0])}"
            )

    portfolio_df = pd.DataFrame(portfolio_values)
    trades_df = pd.DataFrame(trades_history)
    metrics = calculate_performance_metrics(portfolio_df, initial_capital)
    return {
        'portfolio_values': portfolio_df,
        'trades': trades_df,
        'metrics': metrics,
    }


def save_results(results: Dict, output_prefix: str) -> None:
    portfolio_file = f"{output_prefix}_portfolio_values.csv"
    results['portfolio_values'].to_csv(portfolio_file, index=False)
    print(f"Portfolio values saved to: {portfolio_file}")

    if not results['trades'].empty:
        trades_file = f"{output_prefix}_trades.csv"
        results['trades'].to_csv(trades_file, index=False)
        print(f"Trades history saved to: {trades_file}")

    metrics_file = f"{output_prefix}_metrics.csv"
    pd.DataFrame([results['metrics']]).to_csv(metrics_file, index=False)
    print(f"Performance metrics saved to: {metrics_file}")


def main():
    parser = argparse.ArgumentParser(
        description='Backtest sweep for Days-from-High/Low strategy (LONG and SHORT)',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('--data-file', type=str, default='data/raw/top10_markets_500d_daily_data.csv', help='Path to historical OHLCV data CSV file')
    parser.add_argument('--days-thresholds', type=str, default='5,10,15,20,30', help='Comma-separated list of max days thresholds to test')
    parser.add_argument('--lookback-window', type=int, default=200, help='Lookback window for 200d high/low calculation')
    parser.add_argument('--volatility-window', type=int, default=30, help='Window for volatility calculation')
    parser.add_argument('--initial-capital', type=float, default=10000.0, help='Initial portfolio capital in USD')
    parser.add_argument('--leverage', type=float, default=1.0, help='Leverage multiplier')
    parser.add_argument('--long-allocation', type=float, default=0.5, help='Allocation to long side (0.5 = 50%)')
    parser.add_argument('--short-allocation', type=float, default=0.5, help='Allocation to short side (0.5 = 50%)')
    parser.add_argument('--start-date', type=str, default=None, help='Start date for backtest (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, default=None, help='End date for backtest (YYYY-MM-DD)')
    parser.add_argument('--output-prefix', type=str, default='backtests/results/backtest_days_from_high_sweep', help='Prefix for output CSV files')
    parser.add_argument('--save-detailed', action='store_true', help='Save detailed per-threshold CSVs (portfolio, trades, metrics)')

    args = parser.parse_args()

    thresholds = [int(x.strip()) for x in args.days_thresholds.split(',') if x.strip()]

    print("=" * 100)
    print("BACKTEST: Days-from-High/Low Strategy - Parameter Sweep")
    print("=" * 100)
    print(f"Data file: {args.data_file}")
    print(f"Thresholds: {thresholds}")
    print(f"Lookback window: {args.lookback_window}d | Volatility window: {args.volatility_window}d")
    print(f"Capital: ${args.initial_capital:,.2f} | Leverage: {args.leverage}x | Long alloc: {args.long_allocation:.0%} | Short alloc: {args.short_allocation:.0%}")
    print(f"Start: {args.start_date or 'First available'} | End: {args.end_date or 'Last available'}")
    print("=" * 100)

    print("\nLoading data...")
    data = load_data(args.data_file)
    print(f"Loaded {len(data)} rows for {data['symbol'].nunique()} symbols")
    print(f"Date range: {data['date'].min().date()} to {data['date'].max().date()}")

    summary_rows: List[Dict] = []

    for thr in thresholds:
        print("\n" + "-" * 80)
        print(f"Running backtest for threshold = {thr} days")
        print("-" * 80)

        results = backtest_long_short(
            data=data,
            days_threshold=thr,
            lookback_window=args.lookback_window,
            volatility_window=args.volatility_window,
            start_date=args.start_date,
            end_date=args.end_date,
            initial_capital=args.initial_capital,
            leverage=args.leverage,
            long_allocation=args.long_allocation,
            short_allocation=args.short_allocation,
        )

        metrics = results['metrics'].copy()
        metrics['days_threshold'] = thr
        summary_rows.append(metrics)

        if args.save_detailed:
            prefix = f"{args.output_prefix}_thr{thr}"
            save_results(results, output_prefix=prefix)

    summary_df = pd.DataFrame(summary_rows)
    # Order columns
    col_order = [
        'days_threshold', 'initial_capital', 'final_value', 'total_return', 'annualized_return',
        'annualized_volatility', 'sharpe_ratio', 'max_drawdown', 'win_rate', 'num_days',
        'avg_long_positions', 'avg_short_positions', 'avg_total_positions',
        'avg_long_exposure', 'avg_short_exposure', 'avg_net_exposure', 'avg_gross_exposure',
    ]
    summary_df = summary_df[[c for c in col_order if c in summary_df.columns]]

    summary_file = f"{args.output_prefix}_summary.csv"
    summary_df.to_csv(summary_file, index=False)
    print(f"\nSummary saved to: {summary_file}")


if __name__ == '__main__':
    main()
