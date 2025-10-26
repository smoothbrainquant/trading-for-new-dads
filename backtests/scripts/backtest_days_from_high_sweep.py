"""
Backtest sweep for Days-From-High signal across thresholds and sides.

- Selects instruments within N days of their rolling 200-day high
- Allocates using inverse-volatility weights (risk parity)
- Tests both LONG and SHORT variants (shorting near highs)
- Rebalances daily
- Aggregates metrics across parameter combinations

Notes:
- Uses next-day returns implicitly by applying today's returns to yesterday's weights
- Avoids lookahead bias in volatility and selection (based on data up to current day)
"""

from __future__ import annotations

import os
import sys
import argparse
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

# Ensure repo root on path so we can import from `signals`
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(THIS_DIR, "..", ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# Local imports
from signals.calc_days_from_high import calculate_days_since_200d_high
from signals.calc_weights import calculate_weights


def load_data(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    return df


def calculate_rolling_volatility(data: pd.DataFrame, window: int = 30) -> pd.DataFrame:
    df = data.copy()
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)

    df['daily_return'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )

    df['volatility'] = df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=window, min_periods=window).std() * np.sqrt(365)
    )

    return df[['date', 'symbol', 'close', 'daily_return', 'volatility']]


def calc_portfolio_return(weights: Dict[str, float], returns_df: pd.DataFrame) -> float:
    if not weights or returns_df.empty:
        return 0.0
    port_ret = 0.0
    for symbol, weight in weights.items():
        vals = returns_df.loc[returns_df['symbol'] == symbol, 'daily_return'].values
        if len(vals) > 0 and not np.isnan(vals[0]):
            port_ret += weight * vals[0]
    return port_ret


def compute_metrics(portfolio_df: pd.DataFrame, initial_capital: float) -> Dict[str, float]:
    df = portfolio_df.copy()
    df['daily_return'] = df['portfolio_value'].pct_change()
    df['log_return'] = np.log(df['portfolio_value'] / df['portfolio_value'].shift(1))

    final_value = float(df['portfolio_value'].iloc[-1])
    total_return = (final_value - initial_capital) / initial_capital

    num_days = len(df)
    years = num_days / 365.25 if num_days > 0 else 0
    annualized_return = (final_value / initial_capital) ** (1 / years) - 1 if years > 0 else 0.0

    daily_vol = df['log_return'].dropna().std()
    annualized_vol = float(daily_vol * np.sqrt(365)) if not np.isnan(daily_vol) else 0.0
    sharpe_ratio = (annualized_return / annualized_vol) if annualized_vol > 0 else 0.0

    cumulative = (1 + df['daily_return'].fillna(0)).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_drawdown = float(drawdown.min()) if not drawdown.empty else 0.0

    daily_log = df['log_return'].dropna()
    win_rate = float((daily_log > 0).sum() / len(daily_log)) if len(daily_log) > 0 else 0.0

    avg_positions = float(df['num_positions'].mean()) if 'num_positions' in df.columns else 0.0

    return {
        'initial_capital': float(initial_capital),
        'final_value': float(final_value),
        'total_return': float(total_return),
        'annualized_return': float(annualized_return),
        'annualized_volatility': float(annualized_vol),
        'sharpe_ratio': float(sharpe_ratio),
        'max_drawdown': float(max_drawdown),
        'win_rate': float(win_rate),
        'avg_positions': float(avg_positions),
        'num_days': int(num_days),
    }


def backtest_once(
    data: pd.DataFrame,
    days_threshold: int,
    lookback_window: int = 200,
    volatility_window: int = 30,
    initial_capital: float = 10000.0,
    side: str = 'long',  # 'long' or 'short'
) -> Dict[str, object]:
    # Dates
    all_dates = sorted(data['date'].unique())

    min_required_days = lookback_window + volatility_window
    if len(all_dates) < min_required_days:
        raise ValueError(
            f"Insufficient data. Need at least {min_required_days} days, have {len(all_dates)}"
        )

    start_idx = min_required_days
    backtest_dates = all_dates[start_idx:]
    if len(backtest_dates) == 0:
        backtest_dates = [all_dates[-1]]

    # Precompute daily returns for application of previous weights
    data_with_returns = data.copy()
    data_with_returns['daily_return'] = data_with_returns.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )

    portfolio_values: List[Dict[str, object]] = []
    trades_history: List[Dict[str, object]] = []

    current_weights: Dict[str, float] = {}
    current_capital = float(initial_capital)

    for i, current_date in enumerate(backtest_dates):
        # Historical window up to and including current_date
        historical = data[data['date'] <= current_date].copy()

        # 1) Days since 200d high (vectorized per symbol)
        try:
            days_df = calculate_days_since_200d_high(historical)
            latest_days = days_df[days_df['date'] == current_date]
        except Exception as e:
            print(f"Error calculating days_from_high on {current_date}: {e}")
            continue

        # 2) Select symbols within threshold
        selected_symbols = latest_days.loc[
            latest_days['days_since_200d_high'] <= days_threshold, 'symbol'
        ].tolist()

        # 3) Volatility for selected symbols
        if selected_symbols:
            selected_hist = historical[historical['symbol'].isin(selected_symbols)]
            vola_df = calculate_rolling_volatility(selected_hist, window=volatility_window)
            latest_vola = vola_df[vola_df['date'] == current_date]
            vol_map: Dict[str, float] = {}
            for _, row in latest_vola.iterrows():
                v = row['volatility']
                if pd.notna(v) and v > 0:
                    vol_map[str(row['symbol'])] = float(v)
        else:
            vol_map = {}

        # 4) Risk-parity weights
        base_weights = calculate_weights(vol_map) if vol_map else {}
        if side.lower() == 'short':
            new_weights = {sym: -w for sym, w in base_weights.items()}
        else:
            new_weights = base_weights

        # 5) Apply daily return to previous weights
        if i > 0 and current_weights:
            todays_returns = data_with_returns[data_with_returns['date'] == current_date]
            port_ret = calc_portfolio_return(current_weights, todays_returns)
            current_capital *= float(np.exp(port_ret))

        # Record portfolio value
        portfolio_values.append({
            'date': current_date,
            'portfolio_value': current_capital,
            'num_positions': len(new_weights),
            'positions': ', '.join(new_weights.keys()) if new_weights else 'None',
        })

        # Record trades on weight changes
        if new_weights != current_weights:
            all_syms = set(new_weights.keys()) | set(current_weights.keys())
            for sym in all_syms:
                old_w = current_weights.get(sym, 0.0)
                new_w = new_weights.get(sym, 0.0)
                if abs(new_w - old_w) > 1e-6:
                    trades_history.append({
                        'date': current_date,
                        'symbol': sym,
                        'old_weight': old_w,
                        'new_weight': new_w,
                        'weight_change': new_w - old_w,
                    })

        current_weights = new_weights.copy()

        if (i + 1) % 50 == 0 or i == len(backtest_dates) - 1:
            print(
                f"Progress: {i+1}/{len(backtest_dates)} | Date: {pd.to_datetime(current_date).date()} | "
                f"Value: ${current_capital:,.2f} | Positions: {len(new_weights)}"
            )

    portfolio_df = pd.DataFrame(portfolio_values)
    trades_df = pd.DataFrame(trades_history)
    metrics = compute_metrics(portfolio_df, initial_capital)

    return {
        'portfolio_values': portfolio_df,
        'trades': trades_df,
        'metrics': metrics,
        'start_date': pd.to_datetime(backtest_dates[0]).date() if backtest_dates else None,
        'end_date': pd.to_datetime(backtest_dates[-1]).date() if backtest_dates else None,
    }


def run_sweep(
    data: pd.DataFrame,
    thresholds: List[int],
    sides: List[str],
    lookback_window: int,
    volatility_window: int,
    initial_capital: float,
    output_dir: str,
    output_prefix: str,
    save_per_run: bool = False,
) -> pd.DataFrame:
    summary_rows: List[Dict[str, object]] = []

    os.makedirs(output_dir, exist_ok=True)

    for side in sides:
        for thr in thresholds:
            print("=" * 100)
            print(f"Running backtest: side={side.upper()} | days_threshold={thr}")
            print("=" * 100)
            res = backtest_once(
                data=data,
                days_threshold=int(thr),
                lookback_window=lookback_window,
                volatility_window=volatility_window,
                initial_capital=initial_capital,
                side=side,
            )

            m = res['metrics']
            row = {
                'side': side,
                'days_threshold': int(thr),
                'lookback_window': int(lookback_window),
                'volatility_window': int(volatility_window),
                'start_date': str(res['start_date']),
                'end_date': str(res['end_date']),
                **m,
            }
            summary_rows.append(row)

            if save_per_run:
                base = f"{output_prefix}_side-{side}_thr-{thr}"
                port_path = os.path.join(output_dir, f"{base}_portfolio.csv")
                trades_path = os.path.join(output_dir, f"{base}_trades.csv")
                metrics_path = os.path.join(output_dir, f"{base}_metrics.csv")
                res['portfolio_values'].to_csv(port_path, index=False)
                res['trades'].to_csv(trades_path, index=False)
                pd.DataFrame([m]).to_csv(metrics_path, index=False)
                print(f"Saved: {port_path} | {trades_path} | {metrics_path}")

    summary_df = pd.DataFrame(summary_rows)
    out_summary = os.path.join(output_dir, f"{output_prefix}_summary.csv")
    summary_df.to_csv(out_summary, index=False)
    print(f"\nSummary saved to: {out_summary}")
    return summary_df


def parse_list_of_ints(s: str) -> List[int]:
    return [int(x.strip()) for x in s.split(',') if x.strip()]


def parse_list_of_strs(s: str) -> List[str]:
    return [x.strip().lower() for x in s.split(',') if x.strip()]


def main():
    parser = argparse.ArgumentParser(
        description='Backtest sweep for Days-From-High thresholds and sides',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        '--data-file',
        type=str,
        required=True,
        help='Path to historical OHLCV data CSV file',
    )
    parser.add_argument(
        '--thresholds',
        type=str,
        default='5,10,20,30,60',
        help='Comma-separated list of days-from-high thresholds',
    )
    parser.add_argument(
        '--sides',
        type=str,
        default='long,short',
        help='Comma-separated sides to test: long, short',
    )
    parser.add_argument(
        '--lookback-window',
        type=int,
        default=200,
        help='Lookback window for rolling high (days)',
    )
    parser.add_argument(
        '--volatility-window',
        type=int,
        default=30,
        help='Window for rolling volatility (days)',
    )
    parser.add_argument(
        '--initial-capital',
        type=float,
        default=10000.0,
        help='Initial capital (USD)',
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=os.path.join(REPO_ROOT, 'backtests', 'results'),
        help='Directory to save outputs',
    )
    parser.add_argument(
        '--output-prefix',
        type=str,
        default='days_from_high_sweep',
        help='Prefix for output files',
    )
    parser.add_argument(
        '--save-per-run',
        action='store_true',
        help='Save portfolio/trades/metrics CSVs for each run',
    )

    args = parser.parse_args()

    print("=" * 100)
    print("BACKTEST SWEEP: Days-From-High")
    print("=" * 100)
    print(f"Data file: {args.data_file}")
    print(f"Thresholds: {args.thresholds}")
    print(f"Sides: {args.sides}")
    print(f"Lookback window: {args.lookback_window}d | Volatility window: {args.volatility_window}d")
    print(f"Initial capital: ${args.initial_capital:,.2f}")
    print(f"Output dir: {args.output_dir}")

    data = load_data(args.data_file)
    print(f"Loaded {len(data):,} rows | Symbols: {data['symbol'].nunique()} | Range: {data['date'].min().date()} -> {data['date'].max().date()}")

    thresholds = parse_list_of_ints(args.thresholds)
    sides = parse_list_of_strs(args.sides)

    run_sweep(
        data=data,
        thresholds=thresholds,
        sides=sides,
        lookback_window=args.lookback_window,
        volatility_window=args.volatility_window,
        initial_capital=args.initial_capital,
        output_dir=args.output_dir,
        output_prefix=args.output_prefix,
        save_per_run=args.save_per_run,
    )


if __name__ == '__main__':
    main()
