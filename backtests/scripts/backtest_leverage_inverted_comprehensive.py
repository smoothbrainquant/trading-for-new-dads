#!/usr/bin/env python3
"""
INVERTED Leverage Strategy with Risk Parity - Comprehensive Backtest

Strategy:
- LONG: Bottom 10 coins by leverage ratio (LEAST leveraged) - inverted!
- SHORT: Top 10 coins by leverage ratio (MOST leveraged) - inverted!
- Weighting: Risk Parity (inverse volatility)
- Test multiple rebalance frequencies: 1d, 3d, 5d, 7d, 30d
- Test two ranking metrics: OI/Market Cap and OI/Volume

Hypothesis:
Low leverage coins (better fundamentals, less speculation) outperform
high leverage coins (prone to liquidations, excessive speculation).
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (16, 10)


def load_historical_leverage_data():
    """Load the historical leverage data"""
    print("Loading historical leverage data...")
    
    df = pd.read_csv("signals/historical_leverage_weekly_20251102_170645.csv")
    df["date"] = pd.to_datetime(df["date"])
    
    # Calculate OI/Volume ratio if not present
    # We'll need to reload from the daily aggregate to get volume data
    # For now, use a proxy calculation
    
    print(f"  ? Loaded {len(df)} records")
    print(f"  ? Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    
    return df


def load_price_data():
    """Load daily price data"""
    print("Loading price data...")
    
    df = pd.read_csv("data/raw/combined_coinbase_coinmarketcap_daily.csv")
    df["date"] = pd.to_datetime(df["date"])
    
    if "base" in df.columns:
        df["coin_symbol"] = df["base"]
    elif "symbol" in df.columns:
        df["coin_symbol"] = df["symbol"].str.replace("/USD", "").str.replace("-USD", "")
    
    df = df.sort_values(["coin_symbol", "date"])
    df["return"] = df.groupby("coin_symbol")["close"].pct_change()
    
    # Calculate rolling volatility for risk parity
    df["volatility_30d"] = df.groupby("coin_symbol")["return"].transform(
        lambda x: x.rolling(30, min_periods=10).std() * np.sqrt(252)
    )
    
    df = df[["date", "coin_symbol", "close", "return", "volatility_30d", "volume"]].copy()
    
    print(f"  ? Loaded {len(df)} price records")
    
    return df


def calculate_oi_volume_ratio(leverage_df, price_df):
    """Calculate OI/Volume ratio by merging with price data"""
    print("Calculating OI/Volume ratios...")
    
    # Merge to get volume and close data
    merged = leverage_df.merge(
        price_df[["date", "coin_symbol", "volume", "close"]],
        on=["date", "coin_symbol"],
        how="left"
    )
    
    # Calculate OI/Volume ratio (OI in USD / Daily Volume in USD)
    # volume * close = volume in USD
    merged["oi_to_volume_ratio"] = (merged["oi_close"] / (merged["volume"] * merged["close"] + 1e-9)) * 100
    
    # Fill NaN with a large value (so they rank low)
    merged["oi_to_volume_ratio"] = merged["oi_to_volume_ratio"].fillna(999)
    
    print(f"  ? Calculated OI/Volume ratios")
    
    return merged


def rank_coins_inverted(leverage_df, as_of_date, ranking_metric="oi_to_mcap_ratio"):
    """
    INVERTED ranking: Long LOW leverage, Short HIGH leverage
    
    Returns: (bottom_10_long, top_10_short)
    """
    df = leverage_df[leverage_df["date"] <= as_of_date].copy()
    
    if df.empty:
        return [], []
    
    latest = df.sort_values("date").groupby("coin_symbol").tail(1)
    latest = latest[latest[ranking_metric].notna()]
    latest = latest[latest[ranking_metric] > 0]
    
    # Filter out stablecoins
    stablecoins = ["USDT", "USDC", "DAI", "USDD", "TUSD", "BUSD"]
    latest = latest[~latest["coin_symbol"].isin(stablecoins)]
    
    if len(latest) < 20:
        return [], []
    
    # Sort by leverage ratio
    latest = latest.sort_values(ranking_metric, ascending=False)
    
    # INVERTED: Long BOTTOM 10 (least leveraged), Short TOP 10 (most leveraged)
    bottom_10_long = latest.tail(10)["coin_symbol"].tolist()
    top_10_short = latest.head(10)["coin_symbol"].tolist()
    
    return bottom_10_long, top_10_short


def calculate_risk_parity_weights(coins, price_df, as_of_date, lookback=30):
    """
    Calculate risk parity weights (inverse volatility weighting)
    """
    if not coins:
        return {}
    
    # Get recent volatility data
    recent_data = price_df[
        (price_df["date"] <= as_of_date) & 
        (price_df["date"] > as_of_date - timedelta(days=lookback*2))
    ]
    
    # Get latest volatility for each coin
    latest_vol = recent_data.groupby("coin_symbol")["volatility_30d"].last()
    
    weights = {}
    total_inv_vol = 0
    
    for coin in coins:
        if coin in latest_vol.index and not pd.isna(latest_vol[coin]) and latest_vol[coin] > 0:
            inv_vol = 1.0 / latest_vol[coin]
            weights[coin] = inv_vol
            total_inv_vol += inv_vol
        else:
            # Use equal weight for coins without volatility data
            weights[coin] = 1.0
            total_inv_vol += 1.0
    
    # Normalize to sum to 1
    if total_inv_vol > 0:
        weights = {k: v/total_inv_vol for k, v in weights.items()}
    
    return weights


def backtest_inverted_strategy(
    leverage_df,
    price_df,
    rebalance_days=30,
    ranking_metric="oi_to_mcap_ratio",
    use_risk_parity=True,
    transaction_cost=0.001
):
    """
    Backtest the INVERTED leverage strategy with risk parity weighting
    """
    
    start_date = max(leverage_df["date"].min(), price_df["date"].min())
    end_date = min(leverage_df["date"].max(), price_df["date"].max())
    
    # Create rebalance dates
    all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
    rebalance_dates = all_dates[::rebalance_days].tolist()
    
    # Initialize tracking
    portfolio_values = []
    portfolio_value = 1.0
    current_longs = []
    current_shorts = []
    current_long_weights = {}
    current_short_weights = {}
    
    for date in all_dates:
        is_rebalance = date in rebalance_dates
        
        if is_rebalance:
            # Rank coins (INVERTED)
            new_longs, new_shorts = rank_coins_inverted(leverage_df, date, ranking_metric)
            
            if not new_longs or not new_shorts:
                portfolio_values.append({
                    "date": date,
                    "portfolio_value": portfolio_value,
                    "num_longs": len(current_longs),
                    "num_shorts": len(current_shorts)
                })
                continue
            
            # Calculate risk parity weights
            if use_risk_parity:
                new_long_weights = calculate_risk_parity_weights(new_longs, price_df, date)
                new_short_weights = calculate_risk_parity_weights(new_shorts, price_df, date)
            else:
                # Equal weight
                new_long_weights = {coin: 1.0/len(new_longs) for coin in new_longs}
                new_short_weights = {coin: 1.0/len(new_shorts) for coin in new_shorts}
            
            # Calculate turnover
            total_trades = (
                len(set(new_longs) - set(current_longs)) +
                len(set(current_longs) - set(new_longs)) +
                len(set(new_shorts) - set(current_shorts)) +
                len(set(current_shorts) - set(new_shorts))
            )
            
            if total_trades > 0:
                turnover_ratio = total_trades / (len(new_longs) + len(new_shorts))
                cost = portfolio_value * turnover_ratio * transaction_cost
                portfolio_value -= cost
            
            current_longs = new_longs
            current_shorts = new_shorts
            current_long_weights = new_long_weights
            current_short_weights = new_short_weights
        
        # Calculate daily returns
        if current_longs or current_shorts:
            date_prices = price_df[price_df["date"] == date]
            
            # Long portfolio return (weighted)
            long_return = 0.0
            if current_longs and current_long_weights:
                for coin, weight in current_long_weights.items():
                    coin_return = date_prices[date_prices["coin_symbol"] == coin]["return"]
                    if len(coin_return) > 0 and not pd.isna(coin_return.iloc[0]):
                        long_return += weight * coin_return.iloc[0]
            
            # Short portfolio return (weighted, negative)
            short_return = 0.0
            if current_shorts and current_short_weights:
                for coin, weight in current_short_weights.items():
                    coin_return = date_prices[date_prices["coin_symbol"] == coin]["return"]
                    if len(coin_return) > 0 and not pd.isna(coin_return.iloc[0]):
                        short_return += weight * (-coin_return.iloc[0])  # Negative for short
            
            # Combined return (50% long, 50% short)
            if current_longs and current_shorts:
                daily_return = 0.5 * long_return + 0.5 * short_return
            elif current_longs:
                daily_return = long_return
            elif current_shorts:
                daily_return = short_return
            else:
                daily_return = 0.0
            
            portfolio_value *= (1 + daily_return)
        
        portfolio_values.append({
            "date": date,
            "portfolio_value": portfolio_value,
            "num_longs": len(current_longs),
            "num_shorts": len(current_shorts)
        })
    
    return pd.DataFrame(portfolio_values)


def calculate_metrics(portfolio_df):
    """Calculate performance metrics"""
    
    portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()
    
    total_return = (portfolio_df["portfolio_value"].iloc[-1] / portfolio_df["portfolio_value"].iloc[0] - 1) * 100
    
    days = (portfolio_df["date"].iloc[-1] - portfolio_df["date"].iloc[0]).days
    years = days / 365.25
    annualized_return = ((portfolio_df["portfolio_value"].iloc[-1] / portfolio_df["portfolio_value"].iloc[0]) ** (1/years) - 1) * 100
    
    daily_vol = portfolio_df["daily_return"].std()
    annualized_vol = daily_vol * np.sqrt(252) * 100
    
    sharpe_ratio = (annualized_return / annualized_vol) if annualized_vol > 0 else 0
    
    cumulative = portfolio_df["portfolio_value"]
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max * 100
    max_drawdown = drawdown.min()
    
    calmar_ratio = (annualized_return / abs(max_drawdown)) if max_drawdown != 0 else 0
    
    win_rate = (portfolio_df["daily_return"] > 0).sum() / len(portfolio_df["daily_return"].dropna()) * 100
    
    return {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_vol,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "calmar_ratio": calmar_ratio,
        "win_rate": win_rate,
        "final_value": portfolio_df["portfolio_value"].iloc[-1]
    }


def run_comprehensive_backtest(leverage_df, price_df):
    """
    Run backtests across all combinations:
    - Rebalance periods: 1d, 3d, 5d, 7d, 30d
    - Ranking metrics: OI/MCap, OI/Volume
    """
    
    print("\n" + "="*80)
    print("COMPREHENSIVE BACKTEST - INVERTED STRATEGY WITH RISK PARITY")
    print("="*80)
    
    # Calculate OI/Volume ratios
    leverage_with_volume = calculate_oi_volume_ratio(leverage_df, price_df)
    
    rebalance_periods = [1, 3, 5, 7, 30]
    ranking_metrics = ["oi_to_mcap_ratio", "oi_to_volume_ratio"]
    
    results = []
    all_portfolio_dfs = {}
    
    total_tests = len(rebalance_periods) * len(ranking_metrics)
    test_num = 0
    
    for ranking_metric in ranking_metrics:
        metric_name = "OI/MCap" if ranking_metric == "oi_to_mcap_ratio" else "OI/Volume"
        
        for rebal_days in rebalance_periods:
            test_num += 1
            print(f"\n[{test_num}/{total_tests}] Testing: {metric_name}, {rebal_days}-day rebalance")
            
            # Use appropriate dataframe
            lev_df = leverage_df if ranking_metric == "oi_to_mcap_ratio" else leverage_with_volume
            
            portfolio_df = backtest_inverted_strategy(
                lev_df,
                price_df,
                rebalance_days=rebal_days,
                ranking_metric=ranking_metric,
                use_risk_parity=True
            )
            
            metrics = calculate_metrics(portfolio_df)
            
            result = {
                "ranking_metric": metric_name,
                "rebalance_days": rebal_days,
                **metrics
            }
            
            results.append(result)
            
            # Store portfolio for later visualization
            key = f"{metric_name}_{rebal_days}d"
            all_portfolio_dfs[key] = portfolio_df
            
            print(f"  ? Total Return: {metrics['total_return']:.2f}%")
            print(f"  ? Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            print(f"  ? Max Drawdown: {metrics['max_drawdown']:.2f}%")
    
    results_df = pd.DataFrame(results)
    
    return results_df, all_portfolio_dfs


def print_results_summary(results_df):
    """Print formatted results summary"""
    
    print("\n" + "="*80)
    print("RESULTS SUMMARY - ALL COMBINATIONS")
    print("="*80)
    
    # Sort by Sharpe Ratio
    results_sorted = results_df.sort_values("sharpe_ratio", ascending=False)
    
    print("\n" + "-"*80)
    print("RANKED BY SHARPE RATIO (Best to Worst)")
    print("-"*80)
    print(f"{'Rank':<6}{'Metric':<12}{'Rebal':<8}{'Total Ret':<12}{'Ann. Ret':<12}{'Sharpe':<10}{'Max DD':<10}{'Win Rate':<10}")
    print("-"*80)
    
    for idx, row in results_sorted.iterrows():
        print(f"{idx+1:<6}{row['ranking_metric']:<12}{row['rebalance_days']:>3}d    "
              f"{row['total_return']:>8.2f}%   {row['annualized_return']:>8.2f}%   "
              f"{row['sharpe_ratio']:>6.2f}    {row['max_drawdown']:>8.2f}%  {row['win_rate']:>6.2f}%")
    
    # Best by each metric
    print("\n" + "-"*80)
    print("BEST PERFORMERS BY METRIC")
    print("-"*80)
    
    best_sharpe = results_df.loc[results_df['sharpe_ratio'].idxmax()]
    print(f"\nBest Sharpe Ratio: {best_sharpe['sharpe_ratio']:.2f}")
    print(f"  ? {best_sharpe['ranking_metric']}, {best_sharpe['rebalance_days']}-day rebalance")
    print(f"  ? Total Return: {best_sharpe['total_return']:.2f}%, Max DD: {best_sharpe['max_drawdown']:.2f}%")
    
    best_return = results_df.loc[results_df['total_return'].idxmax()]
    print(f"\nBest Total Return: {best_return['total_return']:.2f}%")
    print(f"  ? {best_return['ranking_metric']}, {best_return['rebalance_days']}-day rebalance")
    print(f"  ? Sharpe: {best_return['sharpe_ratio']:.2f}, Max DD: {best_return['max_drawdown']:.2f}%")
    
    best_dd = results_df.loc[results_df['max_drawdown'].idxmax()]  # Highest (least negative)
    print(f"\nBest Max Drawdown: {best_dd['max_drawdown']:.2f}%")
    print(f"  ? {best_dd['ranking_metric']}, {best_dd['rebalance_days']}-day rebalance")
    print(f"  ? Total Return: {best_dd['total_return']:.2f}%, Sharpe: {best_dd['sharpe_ratio']:.2f}")
    
    # Average by ranking metric
    print("\n" + "-"*80)
    print("AVERAGE PERFORMANCE BY RANKING METRIC")
    print("-"*80)
    
    for metric in results_df['ranking_metric'].unique():
        metric_results = results_df[results_df['ranking_metric'] == metric]
        print(f"\n{metric}:")
        print(f"  Avg Total Return:    {metric_results['total_return'].mean():>8.2f}%")
        print(f"  Avg Sharpe Ratio:    {metric_results['sharpe_ratio'].mean():>8.2f}")
        print(f"  Avg Max Drawdown:    {metric_results['max_drawdown'].mean():>8.2f}%")
    
    # Average by rebalance period
    print("\n" + "-"*80)
    print("AVERAGE PERFORMANCE BY REBALANCE PERIOD")
    print("-"*80)
    
    for days in sorted(results_df['rebalance_days'].unique()):
        days_results = results_df[results_df['rebalance_days'] == days]
        print(f"\n{days}-day rebalance:")
        print(f"  Avg Total Return:    {days_results['total_return'].mean():>8.2f}%")
        print(f"  Avg Sharpe Ratio:    {days_results['sharpe_ratio'].mean():>8.2f}")
        print(f"  Avg Max Drawdown:    {days_results['max_drawdown'].mean():>8.2f}%")


def create_comparison_visualizations(results_df, all_portfolio_dfs, output_dir="backtests/results"):
    """Create comprehensive comparison visualizations"""
    
    print("\n" + "="*80)
    print("GENERATING COMPARISON VISUALIZATIONS")
    print("="*80)
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # ========================================================================
    # CHART 1: Performance comparison - all strategies
    # ========================================================================
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    
    # Plot 1: Portfolio values over time (OI/MCap)
    ax1 = axes[0, 0]
    for key, df in all_portfolio_dfs.items():
        if "OI/MCap" in key:
            label = key.replace("OI/MCap_", "").replace("d", "-day")
            ax1.plot(df["date"], df["portfolio_value"], label=label, linewidth=2, alpha=0.8)
    
    ax1.axhline(y=1, color='black', linestyle='--', alpha=0.5)
    ax1.set_ylabel("Portfolio Value", fontweight='bold')
    ax1.set_title("Portfolio Performance - OI/Market Cap Ranking", fontsize=12, fontweight='bold')
    ax1.legend(loc='best', fontsize=9)
    ax1.grid(alpha=0.3)
    
    # Plot 2: Portfolio values over time (OI/Volume)
    ax2 = axes[0, 1]
    for key, df in all_portfolio_dfs.items():
        if "OI/Volume" in key:
            label = key.replace("OI/Volume_", "").replace("d", "-day")
            ax2.plot(df["date"], df["portfolio_value"], label=label, linewidth=2, alpha=0.8)
    
    ax2.axhline(y=1, color='black', linestyle='--', alpha=0.5)
    ax2.set_ylabel("Portfolio Value", fontweight='bold')
    ax2.set_title("Portfolio Performance - OI/Volume Ranking", fontsize=12, fontweight='bold')
    ax2.legend(loc='best', fontsize=9)
    ax2.grid(alpha=0.3)
    
    # Plot 3: Sharpe Ratio comparison
    ax3 = axes[1, 0]
    pivot_sharpe = results_df.pivot(index='rebalance_days', columns='ranking_metric', values='sharpe_ratio')
    pivot_sharpe.plot(kind='bar', ax=ax3, width=0.8)
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax3.set_xlabel("Rebalance Period (days)", fontweight='bold')
    ax3.set_ylabel("Sharpe Ratio", fontweight='bold')
    ax3.set_title("Sharpe Ratio by Rebalance Period", fontsize=12, fontweight='bold')
    ax3.legend(title="Ranking Metric")
    ax3.grid(alpha=0.3, axis='y')
    plt.setp(ax3.xaxis.get_majorticklabels(), rotation=0)
    
    # Plot 4: Total Return comparison
    ax4 = axes[1, 1]
    pivot_return = results_df.pivot(index='rebalance_days', columns='ranking_metric', values='total_return')
    pivot_return.plot(kind='bar', ax=ax4, width=0.8)
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax4.set_xlabel("Rebalance Period (days)", fontweight='bold')
    ax4.set_ylabel("Total Return (%)", fontweight='bold')
    ax4.set_title("Total Return by Rebalance Period", fontsize=12, fontweight='bold')
    ax4.legend(title="Ranking Metric")
    ax4.grid(alpha=0.3, axis='y')
    plt.setp(ax4.xaxis.get_majorticklabels(), rotation=0)
    
    plt.suptitle("INVERTED Leverage Strategy - Comprehensive Comparison", 
                fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    
    file1 = output_path / f"leverage_inverted_comparison_{timestamp}.png"
    plt.savefig(file1, dpi=300, bbox_inches='tight')
    print(f"  ? Saved: {file1}")
    plt.close()
    
    # ========================================================================
    # CHART 2: Detailed metrics comparison
    # ========================================================================
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    
    # Heatmap 1: Sharpe Ratio
    ax1 = axes[0, 0]
    pivot = results_df.pivot(index='ranking_metric', columns='rebalance_days', values='sharpe_ratio')
    sns.heatmap(pivot, annot=True, fmt='.2f', cmap='RdYlGn', center=0, ax=ax1,
               cbar_kws={'label': 'Sharpe Ratio'})
    ax1.set_xlabel("Rebalance Period (days)", fontweight='bold')
    ax1.set_ylabel("Ranking Metric", fontweight='bold')
    ax1.set_title("Sharpe Ratio Heatmap", fontweight='bold')
    
    # Heatmap 2: Total Return
    ax2 = axes[0, 1]
    pivot = results_df.pivot(index='ranking_metric', columns='rebalance_days', values='total_return')
    sns.heatmap(pivot, annot=True, fmt='.1f', cmap='RdYlGn', center=0, ax=ax2,
               cbar_kws={'label': 'Total Return (%)'})
    ax2.set_xlabel("Rebalance Period (days)", fontweight='bold')
    ax2.set_ylabel("Ranking Metric", fontweight='bold')
    ax2.set_title("Total Return Heatmap (%)", fontweight='bold')
    
    # Heatmap 3: Max Drawdown
    ax3 = axes[1, 0]
    pivot = results_df.pivot(index='ranking_metric', columns='rebalance_days', values='max_drawdown')
    sns.heatmap(pivot, annot=True, fmt='.1f', cmap='RdYlGn_r', center=-25, ax=ax3,
               cbar_kws={'label': 'Max Drawdown (%)'})
    ax3.set_xlabel("Rebalance Period (days)", fontweight='bold')
    ax3.set_ylabel("Ranking Metric", fontweight='bold')
    ax3.set_title("Max Drawdown Heatmap (%)", fontweight='bold')
    
    # Scatter: Risk vs Return
    ax4 = axes[1, 1]
    for metric in results_df['ranking_metric'].unique():
        metric_data = results_df[results_df['ranking_metric'] == metric]
        ax4.scatter(metric_data['max_drawdown'].abs(), metric_data['total_return'],
                   s=200, alpha=0.7, label=metric)
        
        # Add labels for rebalance periods
        for _, row in metric_data.iterrows():
            ax4.annotate(f"{row['rebalance_days']}d", 
                        (abs(row['max_drawdown']), row['total_return']),
                        fontsize=8, ha='center', va='center')
    
    ax4.axhline(y=0, color='black', linestyle='--', alpha=0.3)
    ax4.set_xlabel("Max Drawdown (%) [absolute]", fontweight='bold')
    ax4.set_ylabel("Total Return (%)", fontweight='bold')
    ax4.set_title("Risk vs Return", fontweight='bold')
    ax4.legend()
    ax4.grid(alpha=0.3)
    
    plt.tight_layout()
    
    file2 = output_path / f"leverage_inverted_metrics_{timestamp}.png"
    plt.savefig(file2, dpi=300, bbox_inches='tight')
    print(f"  ? Saved: {file2}")
    plt.close()
    
    # ========================================================================
    # CHART 3: Best strategy detailed view
    # ========================================================================
    best_idx = results_df['sharpe_ratio'].idxmax()
    best_result = results_df.loc[best_idx]
    best_key = f"{best_result['ranking_metric']}_{int(best_result['rebalance_days'])}d"
    best_portfolio = all_portfolio_dfs[best_key]
    
    fig, axes = plt.subplots(3, 1, figsize=(16, 12))
    
    # Portfolio value
    ax1 = axes[0]
    ax1.plot(best_portfolio["date"], best_portfolio["portfolio_value"], 
            linewidth=2, color='blue')
    ax1.fill_between(best_portfolio["date"], 1, best_portfolio["portfolio_value"], 
                     alpha=0.3, color='blue')
    ax1.axhline(y=1, color='black', linestyle='--', alpha=0.5)
    ax1.set_ylabel("Portfolio Value", fontweight='bold')
    ax1.set_title(f"BEST STRATEGY: {best_result['ranking_metric']}, {int(best_result['rebalance_days'])}-day rebalance",
                 fontsize=14, fontweight='bold')
    ax1.grid(alpha=0.3)
    
    metrics_text = f"Total Return: {best_result['total_return']:.2f}%\n"
    metrics_text += f"Sharpe Ratio: {best_result['sharpe_ratio']:.2f}\n"
    metrics_text += f"Max DD: {best_result['max_drawdown']:.2f}%"
    ax1.text(0.02, 0.98, metrics_text, transform=ax1.transAxes,
            verticalalignment='top', fontsize=11,
            bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7))
    
    # Drawdown
    ax2 = axes[1]
    cumulative = best_portfolio["portfolio_value"]
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max * 100
    ax2.fill_between(best_portfolio["date"], 0, drawdown, color='red', alpha=0.5)
    ax2.plot(best_portfolio["date"], drawdown, color='darkred', linewidth=1.5)
    ax2.set_ylabel("Drawdown (%)", fontweight='bold')
    ax2.grid(alpha=0.3)
    
    # Rolling returns
    ax3 = axes[2]
    best_portfolio["rolling_30d"] = best_portfolio["portfolio_value"].pct_change(30) * 100
    ax3.plot(best_portfolio["date"], best_portfolio["rolling_30d"], color='green', linewidth=1.5)
    ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax3.fill_between(best_portfolio["date"], 0, best_portfolio["rolling_30d"],
                     where=best_portfolio["rolling_30d"] >= 0, color='green', alpha=0.3)
    ax3.fill_between(best_portfolio["date"], 0, best_portfolio["rolling_30d"],
                     where=best_portfolio["rolling_30d"] < 0, color='red', alpha=0.3)
    ax3.set_ylabel("30-Day Return (%)", fontweight='bold')
    ax3.set_xlabel("Date", fontweight='bold')
    ax3.grid(alpha=0.3)
    
    plt.tight_layout()
    
    file3 = output_path / f"leverage_inverted_best_strategy_{timestamp}.png"
    plt.savefig(file3, dpi=300, bbox_inches='tight')
    print(f"  ? Saved: {file3}")
    plt.close()


def export_results(results_df, all_portfolio_dfs, output_dir="backtests/results"):
    """Export all results to CSV"""
    
    print("\n" + "="*80)
    print("EXPORTING RESULTS")
    print("="*80)
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Summary results
    file1 = output_path / f"leverage_inverted_summary_{timestamp}.csv"
    results_df.to_csv(file1, index=False)
    print(f"  ? Summary results: {file1}")
    
    # Best strategy portfolio values
    best_idx = results_df['sharpe_ratio'].idxmax()
    best_result = results_df.loc[best_idx]
    best_key = f"{best_result['ranking_metric']}_{int(best_result['rebalance_days'])}d"
    best_portfolio = all_portfolio_dfs[best_key]
    
    file2 = output_path / f"leverage_inverted_best_portfolio_{timestamp}.csv"
    best_portfolio.to_csv(file2, index=False)
    print(f"  ? Best strategy portfolio: {file2}")
    
    return file1, file2


def main():
    """Main execution"""
    
    print("\n" + "="*100)
    print(" "*30 + "INVERTED LEVERAGE STRATEGY")
    print(" "*25 + "Comprehensive Backtest Analysis")
    print("="*100)
    print("\nStrategy: LONG low leverage (fundamentals), SHORT high leverage (speculation)")
    print("Weighting: Risk Parity (inverse volatility)")
    print("Tests: 5 rebalance periods ? 2 ranking metrics = 10 total combinations")
    print("="*100)
    
    # Load data
    leverage_df = load_historical_leverage_data()
    price_df = load_price_data()
    
    # Run comprehensive backtest
    results_df, all_portfolio_dfs = run_comprehensive_backtest(leverage_df, price_df)
    
    # Print summary
    print_results_summary(results_df)
    
    # Create visualizations
    create_comparison_visualizations(results_df, all_portfolio_dfs)
    
    # Export results
    export_results(results_df, all_portfolio_dfs)
    
    print("\n" + "="*100)
    print("? COMPREHENSIVE BACKTEST COMPLETE")
    print("="*100)


if __name__ == "__main__":
    main()
