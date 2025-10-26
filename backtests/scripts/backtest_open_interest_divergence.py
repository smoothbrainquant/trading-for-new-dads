#!/usr/bin/env python3
"""
Backtest for Open Interest (OI) Divergence / Trend Strategy

- Uses daily price data (e.g., combined coinbase/CMC) and OI data (Coinalyze daily OI USD)
- Computes z-scored OI change and price return over a rolling window
- Two modes:
  1) trend: long where OI confirms price, short where it contradicts
  2) divergence: contrarian to price-validated by OI (long where OI rises but price down, etc.)
- Risk parity within each side using 30d volatility
- Rebalance every N days; apply next-day returns to avoid look-ahead bias
"""

from dataclasses import dataclass
import argparse
from typing import Tuple

import numpy as np
import pandas as pd

from signals.calc_open_interest_divergence import (
    compute_oi_divergence_scores,
    build_equal_or_risk_parity_weights,
)


@dataclass
class BacktestConfig:
    lookback: int = 30
    volatility_window: int = 30
    rebalance_days: int = 7
    top_n: int = 10
    bottom_n: int = 10
    mode: str = "trend"  # or "divergence"
    initial_capital: float = 10000.0


def load_price_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'])
    if 'base' in df.columns and 'symbol' not in df.columns:
        df['symbol'] = df['base']
    df = df[['date','symbol','close']].dropna().sort_values(['symbol','date']).reset_index(drop=True)
    return df


def load_oi_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'])
    # prefer coin_symbol if present to align bases; else derive from symbol
    if 'coin_symbol' in df.columns:
        sym_col = 'coin_symbol'
    else:
        sym_col = 'symbol'
        if '/' in str(df[sym_col].iloc[0]):
            df['coin_symbol'] = df[sym_col].astype(str).str.extract(r'^([^/]+)')[0]
            sym_col = 'coin_symbol'
    keep = ['date', sym_col]
    if 'oi_close' in df.columns:
        keep.append('oi_close')
    else:
        # Coinalyze scripts save columns with oi_close, ensure fallback
        if 'oi' in df.columns:
            df = df.rename(columns={'oi': 'oi_close'})
            keep.append('oi_close')
        else:
            raise ValueError("OI CSV must contain 'oi_close' or 'oi' column")
    df = df[keep].rename(columns={sym_col: 'symbol'})
    df = df.dropna().sort_values(['symbol','date']).reset_index(drop=True)
    return df


def calculate_portfolio_returns(weights: dict, returns_df: pd.DataFrame) -> float:
    if not weights or returns_df.empty:
        return 0.0
    ret = 0.0
    for sym, w in weights.items():
        vals = returns_df[returns_df['symbol'] == sym]['log_return'].values
        if len(vals) > 0 and not np.isnan(vals[0]):
            ret += w * vals[0]
    return ret


def backtest(price_df: pd.DataFrame, oi_df: pd.DataFrame, cfg: BacktestConfig):
    # Overlap dates
    dates_price = set(price_df['date'].unique())
    dates_oi = set(oi_df['date'].unique())
    common_dates = sorted(list(dates_price.intersection(dates_oi)))
    if len(common_dates) < (cfg.lookback + 10):
        raise ValueError("Insufficient overlapping history for backtest")

    # Precompute scores
    scores = compute_oi_divergence_scores(oi_df, price_df, lookback=cfg.lookback)

    # Precompute daily log returns for next-day application
    p = price_df.copy()
    p['log_return'] = p.groupby('symbol')['close'].transform(lambda x: np.log(x) - np.log(x.shift(1)))

    start_idx = cfg.lookback
    tracking_dates = common_dates[start_idx:]
    rebalance_dates = tracking_dates[::cfg.rebalance_days]
    if not rebalance_dates:
        rebalance_dates = [tracking_dates[-1]]

    weights = {}
    portfolio_values = []
    capital = cfg.initial_capital
    last_rebalance = None

    for i, dt in enumerate(tracking_dates):
        # Rebalance if needed
        if (last_rebalance is None) or (dt in rebalance_dates):
            # Select portfolio
            df_day = scores[scores['date'] == dt]
            if df_day.empty:
                longs, shorts = [], []
            else:
                col = 'score_trend' if cfg.mode == 'trend' else 'score_divergence'
                sel = df_day[['symbol', col]].dropna().sort_values(col, ascending=False)
                longs = sel.head(cfg.top_n)['symbol'].tolist()
                shorts = sel.tail(cfg.bottom_n)['symbol'].tolist()

            # Build weights (risk parity within sides)
            weights = build_equal_or_risk_parity_weights(
                price_df=price_df, long_symbols=longs, short_symbols=shorts,
                notional=1.0, volatility_window=cfg.volatility_window, use_risk_parity=True
            )
            last_rebalance = dt

        # Apply NEXT day's returns
        if i < len(tracking_dates) - 1 and weights:
            next_dt = tracking_dates[i+1]
            ret_df = p[p['date'] == next_dt]
            port_log_ret = calculate_portfolio_returns(weights, ret_df)
            capital = capital * np.exp(port_log_ret)

        long_exposure = sum(w for w in weights.values() if w > 0)
        short_exposure = abs(sum(w for w in weights.values() if w < 0))
        portfolio_values.append({
            'date': dt,
            'portfolio_value': capital,
            'long_exposure': long_exposure,
            'short_exposure': short_exposure,
            'net_exposure': long_exposure - short_exposure,
            'gross_exposure': long_exposure + short_exposure,
        })

    pv = pd.DataFrame(portfolio_values)
    metrics = _metrics(pv, cfg.initial_capital)
    return {'portfolio_values': pv, 'metrics': metrics}


def _metrics(portfolio_df: pd.DataFrame, initial_capital: float):
    out = {}
    portfolio_df = portfolio_df.copy()
    portfolio_df['daily_return'] = portfolio_df['portfolio_value'].pct_change()
    portfolio_df['log_return'] = np.log(portfolio_df['portfolio_value'] / portfolio_df['portfolio_value'].shift(1))

    final_value = portfolio_df['portfolio_value'].iloc[-1]
    out['final_value'] = final_value
    out['total_return'] = final_value / initial_capital - 1.0

    dr = portfolio_df['log_return'].dropna()
    if len(dr) > 2:
        vol = dr.std() * np.sqrt(365)
        years = len(portfolio_df) / 365.25
        ann_return = (final_value / initial_capital) ** (1 / years) - 1 if years > 0 else 0
        out['annualized_return'] = ann_return
        out['annualized_volatility'] = vol
        out['sharpe_ratio'] = ann_return / vol if vol > 0 else 0
    else:
        out['annualized_return'] = 0.0
        out['annualized_volatility'] = 0.0
        out['sharpe_ratio'] = 0.0

    cum = (1 + portfolio_df['daily_return'].fillna(0)).cumprod()
    roll_max = cum.expanding().max()
    dd = (cum - roll_max) / roll_max
    out['max_drawdown'] = float(dd.min())

    return out


def main():
    parser = argparse.ArgumentParser(
        description='Backtest Open Interest Divergence/Trend Strategy',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument('--price-data', type=str, default='data/raw/combined_coinbase_coinmarketcap_daily.csv')
    parser.add_argument('--oi-data', type=str, required=True,
                        help='Path to OI daily CSV with columns including date, coin_symbol/symbol, oi_close')
    parser.add_argument('--mode', type=str, default='trend', choices=['trend','divergence'])
    parser.add_argument('--lookback', type=int, default=30)
    parser.add_argument('--volatility-window', type=int, default=30)
    parser.add_argument('--rebalance-days', type=int, default=7)
    parser.add_argument('--top-n', type=int, default=10)
    parser.add_argument('--bottom-n', type=int, default=10)
    parser.add_argument('--initial-capital', type=float, default=10000.0)
    args = parser.parse_args()

    price_df = load_price_data(args.price_data)
    oi_df = load_oi_data(args.oi_data)

    cfg = BacktestConfig(
        lookback=args.lookback,
        volatility_window=args.volatility_window,
        rebalance_days=args.rebalance_days,
        top_n=args.top_n,
        bottom_n=args.bottom_n,
        mode=args.mode,
        initial_capital=args.initial_capital,
    )

    results = backtest(price_df, oi_df, cfg)

    print("\n" + "="*80)
    print(f"OI {args.mode.upper()} BACKTEST RESULTS")
    print("="*80)
    m = results['metrics']
    print(f"Final Value:         ${m['final_value']:,.2f}")
    print(f"Total Return:        {m['total_return']*100:,.2f}%")
    print(f"Annualized Return:   {m['annualized_return']*100:,.2f}%")
    print(f"Annualized Vol:      {m['annualized_volatility']*100:,.2f}%")
    print(f"Sharpe Ratio:        {m['sharpe_ratio']:.2f}")
    print(f"Max Drawdown:        {m['max_drawdown']*100:,.2f}%")

    # Save outputs
    out_prefix = f"backtest_open_interest_{args.mode}"
    pv = results['portfolio_values']
    pv.to_csv(f"backtests/results/{out_prefix}_portfolio_values.csv", index=False)
    pd.DataFrame([m]).to_csv(f"backtests/results/{out_prefix}_metrics.csv", index=False)
    print(f"Saved results to backtests/results/{out_prefix}_*.csv")


if __name__ == '__main__':
    main()
