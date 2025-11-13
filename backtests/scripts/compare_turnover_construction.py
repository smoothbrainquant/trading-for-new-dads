#!/usr/bin/env python3
"""
Compare Turnover Factor Portfolio Construction Methods

Compares:
1. Top/Bottom 10 coins each side (fixed count)
2. Top/Bottom deciles (top 10% and bottom 10% by percentile)
"""

import pandas as pd
import numpy as np
import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "signals"))

from signals.generate_signals_vectorized import (
    generate_turnover_signals_vectorized,
    calculate_weights_vectorized,
    calculate_portfolio_returns_vectorized,
    calculate_cumulative_returns_vectorized,
    assign_top_bottom_n_vectorized,
    assign_percentiles_vectorized,
)


def load_data():
    """Load price and market cap data"""
    print("\n" + "=" * 80)
    print("LOADING DATA")
    print("=" * 80)
    
    # Load price data
    price_file = "data/raw/combined_coinbase_coinmarketcap_daily.csv"
    print(f"\nLoading price data from {price_file}...")
    price_df = pd.read_csv(price_file)
    price_df["date"] = pd.to_datetime(price_df["date"])
    
    # Deduplicate symbols: filter to keep only symbols with ":" suffix
    if len(price_df) > 0 and ":" in str(price_df["symbol"].iloc[0]):
        price_df = price_df[price_df["symbol"].str.contains(":")].copy()
    
    price_df = price_df.sort_values(["symbol", "date"]).reset_index(drop=True)
    print(f"  ✓ Loaded {len(price_df)} rows, {price_df['symbol'].nunique()} symbols")
    
    # Load market cap data
    mcap_file = "data/raw/coinmarketcap_monthly_all_snapshots.csv"
    print(f"\nLoading market cap data from {mcap_file}...")
    mcap_df = pd.read_csv(mcap_file)
    
    # Handle snapshot_date column
    if "snapshot_date" in mcap_df.columns:
        mcap_df["date"] = pd.to_datetime(mcap_df["snapshot_date"], format='%Y%m%d')
        mcap_df = mcap_df.drop(columns=["snapshot_date"])
    elif "date" in mcap_df.columns:
        mcap_df["date"] = pd.to_datetime(mcap_df["date"])
    
    # Normalize column names
    rename_dict = {}
    if "Market Cap" in mcap_df.columns:
        rename_dict["Market Cap"] = "market_cap"
    if "Symbol" in mcap_df.columns:
        rename_dict["Symbol"] = "symbol"
    if rename_dict:
        mcap_df = mcap_df.rename(columns=rename_dict)
    
    print(f"  ✓ Loaded {len(mcap_df)} rows, {len(mcap_df['date'].unique())} unique dates")
    
    return price_df, mcap_df


def generate_signals_top_bottom_n(price_data, marketcap_data, top_n=10, bottom_n=10, rebalance_days=30):
    """Generate signals using top/bottom N approach"""
    # Normalize symbols
    price_df = price_data[['date', 'symbol', 'volume']].copy()
    price_df['base_symbol'] = price_df['symbol'].apply(lambda x: x.split('/')[0] if '/' in str(x) else x)
    
    mcap_df = marketcap_data[['date', 'symbol', 'market_cap']].copy()
    mcap_df['base_symbol'] = mcap_df['symbol'].apply(lambda x: x.split('/')[0] if '/' in str(x) else x)
    
    # Merge
    df = pd.merge(
        price_df[['date', 'symbol', 'base_symbol', 'volume']],
        mcap_df[['date', 'base_symbol', 'market_cap']],
        on=['date', 'base_symbol'],
        how='inner'
    )
    
    # Calculate turnover
    df['turnover_pct'] = (df['volume'] / df['market_cap'] * 100).replace([np.inf, -np.inf], np.nan)
    df = df[df['turnover_pct'].notna()]
    df = df[(df['turnover_pct'] > 0) & (df['turnover_pct'] < 100)]
    
    # Apply rebalancing
    df = df.sort_values('date')
    unique_dates = df['date'].unique()
    rebalance_dates = unique_dates[::rebalance_days]
    df = df[df['date'].isin(rebalance_dates)]
    
    # Assign top/bottom N
    df = assign_top_bottom_n_vectorized(
        df,
        factor_column='turnover_pct',
        top_n=top_n,
        bottom_n=bottom_n,
        ascending=False  # High turnover is better (so top_n gets highest values)
    )
    
    # Generate signals based on selection column
    df['signal'] = 0
    df.loc[df['selection'] == 'top', 'signal'] = 1   # Top N = high turnover = long
    df.loc[df['selection'] == 'bottom', 'signal'] = -1  # Bottom N = low turnover = short
    
    return df[['date', 'symbol', 'turnover_pct', 'signal']]


def backtest_strategy(signals_df, price_data, initial_capital=10000, weighting_method='risk_parity'):
    """Run backtest with given signals"""
    # Prepare returns data
    price_df = price_data.copy()
    price_df = price_df.sort_values(['symbol', 'date'])
    price_df['daily_return'] = price_df.groupby('symbol')['close'].pct_change()
    returns_df = price_df[['date', 'symbol', 'daily_return']].dropna()
    
    # Calculate volatility for risk parity weighting
    price_df['volatility'] = price_df.groupby('symbol')['daily_return'].transform(
        lambda x: x.rolling(window=30, min_periods=10).std()
    )
    volatility_df = price_df[['date', 'symbol', 'volatility']].dropna()
    
    # Calculate weights
    weights_df = calculate_weights_vectorized(
        signals_df,
        volatility_df=volatility_df if weighting_method == 'risk_parity' else None,
        weighting_method=weighting_method,
        long_allocation=0.5,
        short_allocation=0.5,
    )
    
    # Calculate portfolio returns
    portfolio_returns_df = calculate_portfolio_returns_vectorized(
        weights_df,
        returns_df,
    )
    
    # Calculate cumulative returns
    results = calculate_cumulative_returns_vectorized(
        portfolio_returns_df,
        initial_capital=initial_capital,
    )
    
    return results, signals_df


def calculate_metrics(results_df, initial_capital):
    """Calculate performance metrics"""
    portfolio_df = results_df.copy()
    portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()
    
    daily_returns = portfolio_df["daily_return"].dropna()
    if len(daily_returns) == 0:
        return None
    
    final_value = portfolio_df["portfolio_value"].iloc[-1]
    total_return = (final_value - initial_capital) / initial_capital
    
    num_days = len(portfolio_df)
    years = num_days / 365.25
    annualized_return = (final_value / initial_capital) ** (1 / years) - 1 if years > 0 else 0
    
    # Volatility
    daily_vol = daily_returns.std()
    annualized_vol = daily_vol * np.sqrt(365)
    
    # Sharpe ratio
    sharpe_ratio = annualized_return / annualized_vol if annualized_vol > 0 else 0
    
    # Max drawdown
    cumulative_returns = (1 + daily_returns.fillna(0)).cumprod()
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # Win rate
    win_rate = (daily_returns > 0).sum() / len(daily_returns)
    
    # Calmar ratio
    calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
    
    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_vol": annualized_vol,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "calmar_ratio": calmar_ratio,
        "num_days": num_days,
        "final_value": final_value,
    }


def print_comparison(metrics1, metrics2, signals1, signals2, name1, name2):
    """Print comparison table"""
    print("\n" + "=" * 80)
    print("PORTFOLIO CONSTRUCTION COMPARISON")
    print("=" * 80)
    
    # Signal statistics
    print(f"\n{name1}:")
    print(f"  Total signals: {len(signals1)}")
    print(f"  Long positions: {(signals1['signal'] == 1).sum()}")
    print(f"  Short positions: {(signals1['signal'] == -1).sum()}")
    print(f"  Avg longs per rebalance: {(signals1['signal'] == 1).sum() / signals1['date'].nunique():.1f}")
    print(f"  Avg shorts per rebalance: {(signals1['signal'] == -1).sum() / signals1['date'].nunique():.1f}")
    
    print(f"\n{name2}:")
    print(f"  Total signals: {len(signals2)}")
    print(f"  Long positions: {(signals2['signal'] == 1).sum()}")
    print(f"  Short positions: {(signals2['signal'] == -1).sum()}")
    print(f"  Avg longs per rebalance: {(signals2['signal'] == 1).sum() / signals2['date'].nunique():.1f}")
    print(f"  Avg shorts per rebalance: {(signals2['signal'] == -1).sum() / signals2['date'].nunique():.1f}")
    
    # Performance comparison
    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON")
    print("=" * 80)
    
    print(f"\n{'Metric':<30} {name1:>20} {name2:>20} {'Difference':>15}")
    print("-" * 90)
    
    metrics = [
        ("Total Return", "total_return", "%"),
        ("Annualized Return", "annualized_return", "%"),
        ("Annualized Volatility", "annualized_vol", "%"),
        ("Sharpe Ratio", "sharpe_ratio", ""),
        ("Max Drawdown", "max_drawdown", "%"),
        ("Win Rate", "win_rate", "%"),
        ("Calmar Ratio", "calmar_ratio", ""),
        ("Final Portfolio Value", "final_value", "$"),
        ("Number of Days", "num_days", ""),
    ]
    
    for label, key, fmt in metrics:
        val1 = metrics1[key]
        val2 = metrics2[key]
        
        if fmt == "%":
            str1 = f"{val1*100:>19.2f}%"
            str2 = f"{val2*100:>19.2f}%"
            diff = f"{(val2-val1)*100:>14.2f}%"
        elif fmt == "$":
            str1 = f"${val1:>18,.2f}"
            str2 = f"${val2:>18,.2f}"
            diff = f"${val2-val1:>13,.2f}"
        else:
            str1 = f"{val1:>20.3f}"
            str2 = f"{val2:>20.3f}"
            diff = f"{val2-val1:>15.3f}"
        
        print(f"{label:<30} {str1} {str2} {diff}")
    
    print("\n" + "=" * 80)
    
    # Winner
    if metrics2['sharpe_ratio'] > metrics1['sharpe_ratio']:
        winner = name2
        diff = metrics2['sharpe_ratio'] - metrics1['sharpe_ratio']
    else:
        winner = name1
        diff = metrics1['sharpe_ratio'] - metrics2['sharpe_ratio']
    
    print(f"\n🏆 WINNER: {winner} (Sharpe advantage: +{diff:.3f})")
    print("=" * 80)


def main():
    """Main execution"""
    print("=" * 80)
    print("TURNOVER FACTOR: FIXED COUNT vs QUINTILES vs DECILES (RISK PARITY)")
    print("=" * 80)
    
    # Load data
    price_data, mcap_data = load_data()
    
    initial_capital = 10000
    rebalance_days = 30
    
    # Method 1: Top/Bottom 5 coins (most extreme)
    print("\n" + "=" * 80)
    print("METHOD 1: TOP/BOTTOM 5 COINS (MOST EXTREME) - RISK PARITY")
    print("=" * 80)
    
    signals_top5 = generate_signals_top_bottom_n(
        price_data, mcap_data, 
        top_n=5, 
        bottom_n=5, 
        rebalance_days=rebalance_days
    )
    
    print(f"✓ Generated {len(signals_top5)} signals")
    results_top5, signals_top5 = backtest_strategy(
        signals_top5, price_data, initial_capital, weighting_method='risk_parity'
    )
    metrics_top5 = calculate_metrics(results_top5, initial_capital)
    
    # Method 2: Top/Bottom 10 coins
    print("\n" + "=" * 80)
    print("METHOD 2: TOP/BOTTOM 10 COINS (FIXED COUNT) - RISK PARITY")
    print("=" * 80)
    
    signals_top10 = generate_signals_top_bottom_n(
        price_data, mcap_data, 
        top_n=10, 
        bottom_n=10, 
        rebalance_days=rebalance_days
    )
    
    print(f"✓ Generated {len(signals_top10)} signals")
    results_top10, signals_top10 = backtest_strategy(
        signals_top10, price_data, initial_capital, weighting_method='risk_parity'
    )
    metrics_top10 = calculate_metrics(results_top10, initial_capital)
    
    # Method 3: Top/Bottom quintiles (20%)
    print("\n" + "=" * 80)
    print("METHOD 3: TOP/BOTTOM QUINTILES (20% EACH SIDE) - RISK PARITY")
    print("=" * 80)
    
    signals_quintiles = generate_turnover_signals_vectorized(
        price_data,
        mcap_data,
        strategy='long_short',
        rebalance_days=rebalance_days,
        long_percentile=20,  # Bottom 20% = low turnover = short
        short_percentile=80,  # Top 20% = high turnover = long
        num_quintiles=5,  # Use quintiles
    )
    
    print(f"✓ Generated {len(signals_quintiles)} signals")
    results_quintiles, signals_quintiles = backtest_strategy(
        signals_quintiles, price_data, initial_capital, weighting_method='risk_parity'
    )
    metrics_quintiles = calculate_metrics(results_quintiles, initial_capital)
    
    # Method 4: Top/Bottom deciles (10%)
    print("\n" + "=" * 80)
    print("METHOD 4: TOP/BOTTOM DECILES (10% EACH SIDE) - RISK PARITY")
    print("=" * 80)
    
    signals_deciles = generate_turnover_signals_vectorized(
        price_data,
        mcap_data,
        strategy='long_short',
        rebalance_days=rebalance_days,
        long_percentile=10,  # Bottom 10% = low turnover = short
        short_percentile=90,  # Top 10% = high turnover = long
        num_quintiles=10,  # Use deciles
    )
    
    print(f"✓ Generated {len(signals_deciles)} signals")
    results_deciles, signals_deciles = backtest_strategy(
        signals_deciles, price_data, initial_capital, weighting_method='risk_parity'
    )
    metrics_deciles = calculate_metrics(results_deciles, initial_capital)
    
    # Print all comparisons
    print("\n" + "=" * 80)
    print("FOUR-WAY COMPARISON SUMMARY")
    print("=" * 80)
    
    all_metrics = [
        ("Top/Bottom 5", metrics_top5, signals_top5),
        ("Top/Bottom 10", metrics_top10, signals_top10),
        ("Top/Bottom Quintiles (20%)", metrics_quintiles, signals_quintiles),
        ("Top/Bottom Deciles (10%)", metrics_deciles, signals_deciles),
    ]
    
    # Print signal statistics
    for name, metrics, signals in all_metrics:
        print(f"\n{name}:")
        print(f"  Total signals: {len(signals)}")
        print(f"  Long positions: {(signals['signal'] == 1).sum()}")
        print(f"  Short positions: {(signals['signal'] == -1).sum()}")
        print(f"  Avg longs per rebalance: {(signals['signal'] == 1).sum() / signals['date'].nunique():.1f}")
        print(f"  Avg shorts per rebalance: {(signals['signal'] == -1).sum() / signals['date'].nunique():.1f}")
    
    # Print performance table
    print("\n" + "=" * 80)
    print("PERFORMANCE COMPARISON (ALL METHODS)")
    print("=" * 80)
    
    print(f"\n{'Metric':<25} {'Top5':>15} {'Top10':>15} {'Quintiles':>15} {'Deciles':>15}")
    print("-" * 90)
    
    metrics_list = [
        ("Total Return", "total_return", "%"),
        ("Annualized Return", "annualized_return", "%"),
        ("Sharpe Ratio", "sharpe_ratio", ""),
        ("Max Drawdown", "max_drawdown", "%"),
        ("Volatility", "annualized_vol", "%"),
        ("Win Rate", "win_rate", "%"),
        ("Calmar Ratio", "calmar_ratio", ""),
        ("Final Value", "final_value", "$"),
    ]
    
    for label, key, fmt in metrics_list:
        val0 = metrics_top5[key]
        val1 = metrics_top10[key]
        val2 = metrics_quintiles[key]
        val3 = metrics_deciles[key]
        
        if fmt == "%":
            str0 = f"{val0*100:>14.2f}%"
            str1 = f"{val1*100:>14.2f}%"
            str2 = f"{val2*100:>14.2f}%"
            str3 = f"{val3*100:>14.2f}%"
        elif fmt == "$":
            str0 = f"${val0:>13,.2f}"
            str1 = f"${val1:>13,.2f}"
            str2 = f"${val2:>13,.2f}"
            str3 = f"${val3:>13,.2f}"
        else:
            str0 = f"{val0:>15.3f}"
            str1 = f"{val1:>15.3f}"
            str2 = f"{val2:>15.3f}"
            str3 = f"{val3:>15.3f}"
        
        print(f"{label:<25} {str0} {str1} {str2} {str3}")
    
    # Determine winner
    sharpes = [metrics_top5['sharpe_ratio'], metrics_top10['sharpe_ratio'], metrics_quintiles['sharpe_ratio'], metrics_deciles['sharpe_ratio']]
    names = ["Top/Bottom 5", "Top/Bottom 10", "Quintiles (20%)", "Deciles (10%)"]
    winner_idx = sharpes.index(max(sharpes))
    
    print("\n" + "=" * 80)
    print(f"🏆 WINNER: {names[winner_idx]} (Sharpe: {sharpes[winner_idx]:.3f})")
    print("=" * 80)
    
    # Save results
    output_dir = "backtests/results"
    os.makedirs(output_dir, exist_ok=True)
    
    comparison_df = pd.DataFrame([
        {
            "Method": "Top/Bottom 5 Coins (Risk Parity)",
            "Description": "Fixed count: 5 longs, 5 shorts, risk parity weighting (most extreme)",
            **{k: v for k, v in metrics_top5.items()}
        },
        {
            "Method": "Top/Bottom 10 Coins (Risk Parity)",
            "Description": "Fixed count: 10 longs, 10 shorts, risk parity weighting",
            **{k: v for k, v in metrics_top10.items()}
        },
        {
            "Method": "Top/Bottom Quintiles (20%, Risk Parity)",
            "Description": "Top 20% and Bottom 20% by percentile, risk parity weighting",
            **{k: v for k, v in metrics_quintiles.items()}
        },
        {
            "Method": "Top/Bottom Deciles (10%, Risk Parity)",
            "Description": "Top 10% and Bottom 10% by percentile, risk parity weighting",
            **{k: v for k, v in metrics_deciles.items()}
        }
    ])
    
    output_file = f"{output_dir}/turnover_construction_comparison.csv"
    comparison_df.to_csv(output_file, index=False)
    print(f"\n✓ Comparison saved to: {output_file}")
    
    # Save equity curves
    results_top5['method'] = 'Top/Bottom 5'
    results_top10['method'] = 'Top/Bottom 10'
    results_quintiles['method'] = 'Top/Bottom Quintiles (20%)'
    results_deciles['method'] = 'Top/Bottom Deciles (10%)'
    
    equity_curves = pd.concat([
        results_top5[['date', 'portfolio_value', 'method']],
        results_top10[['date', 'portfolio_value', 'method']],
        results_quintiles[['date', 'portfolio_value', 'method']],
        results_deciles[['date', 'portfolio_value', 'method']]
    ])
    
    equity_file = f"{output_dir}/turnover_construction_equity_curves.csv"
    equity_curves.to_csv(equity_file, index=False)
    print(f"✓ Equity curves saved to: {equity_file}")
    
    print("\n" + "=" * 80)
    print("✅ COMPARISON COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
