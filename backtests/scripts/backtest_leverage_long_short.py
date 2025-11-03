#!/usr/bin/env python3
"""
Leverage Long/Short Backtest

Strategy:
- Long top 10 coins by OI/Market Cap ratio (most leveraged)
- Short bottom 10 coins by OI/Market Cap ratio (least leveraged)
- Rebalance monthly
- Equal weight within each leg

Hypothesis:
High leverage may indicate strong trader conviction and momentum,
potentially leading to outperformance. This tests whether leverage ratios
have predictive power for future returns.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from pathlib import Path

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (16, 10)


def load_historical_leverage_data():
    """Load the historical leverage data we just created"""
    print("Loading historical leverage data...")
    
    # Load weekly data
    df = pd.read_csv("signals/historical_leverage_weekly_20251102_170645.csv")
    df["date"] = pd.to_datetime(df["date"])
    
    print(f"  ? Loaded {len(df)} records")
    print(f"  ? Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"  ? Coins: {df['coin_symbol'].nunique()}")
    
    return df


def load_price_data():
    """Load daily price data"""
    print("Loading price data...")
    
    df = pd.read_csv("data/raw/combined_coinbase_coinmarketcap_daily.csv")
    df["date"] = pd.to_datetime(df["date"])
    
    # Use 'base' column for symbol (matches our leverage data better)
    if "base" in df.columns:
        df["coin_symbol"] = df["base"]
    elif "symbol" in df.columns:
        df["coin_symbol"] = df["symbol"].str.replace("/USD", "").str.replace("-USD", "")
    
    # Calculate daily returns
    df = df.sort_values(["coin_symbol", "date"])
    df["return"] = df.groupby("coin_symbol")["close"].pct_change()
    
    # Keep only relevant columns
    df = df[["date", "coin_symbol", "close", "return"]].copy()
    
    print(f"  ? Loaded {len(df)} price records")
    print(f"  ? Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"  ? Coins: {df['coin_symbol'].nunique()}")
    
    return df


def create_monthly_rebalance_dates(start_date, end_date):
    """Create monthly rebalance dates (first Monday of each month)"""
    dates = []
    current = start_date
    
    while current <= end_date:
        # Find first Monday of the month
        first_day = current.replace(day=1)
        days_until_monday = (7 - first_day.weekday()) % 7
        if days_until_monday == 0 and first_day.weekday() == 0:
            first_monday = first_day
        else:
            first_monday = first_day + timedelta(days=days_until_monday)
        
        if first_monday >= start_date and first_monday <= end_date:
            dates.append(first_monday)
        
        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1, day=1)
        else:
            current = current.replace(month=current.month + 1, day=1)
    
    return dates


def rank_coins_by_leverage(leverage_df, as_of_date, min_data_points=4):
    """
    Rank coins by OI/MCap ratio as of a specific date
    
    Returns: (top_10_long, bottom_10_short)
    """
    # Get data for the most recent date at or before as_of_date
    df = leverage_df[leverage_df["date"] <= as_of_date].copy()
    
    if df.empty:
        return [], []
    
    # Get most recent observation for each coin
    latest = df.sort_values("date").groupby("coin_symbol").tail(1)
    
    # Filter out coins with insufficient data or missing values
    latest = latest[latest["oi_to_mcap_ratio"].notna()]
    latest = latest[latest["oi_to_mcap_ratio"] > 0]  # Must have positive OI
    
    # Filter out stablecoins
    stablecoins = ["USDT", "USDC", "DAI", "USDD", "TUSD", "BUSD"]
    latest = latest[~latest["coin_symbol"].isin(stablecoins)]
    
    if len(latest) < 20:  # Need at least 20 coins to form portfolios
        return [], []
    
    # Sort by leverage ratio
    latest = latest.sort_values("oi_to_mcap_ratio", ascending=False)
    
    # Top 10 for long
    top_10 = latest.head(10)["coin_symbol"].tolist()
    
    # Bottom 10 for short
    bottom_10 = latest.tail(10)["coin_symbol"].tolist()
    
    return top_10, bottom_10


def backtest_leverage_strategy(
    leverage_df,
    price_df,
    rebalance_freq="monthly",
    top_n=10,
    bottom_n=10,
    transaction_cost=0.001  # 10bps per trade
):
    """
    Backtest the leverage long/short strategy
    """
    print("\n" + "="*80)
    print("RUNNING BACKTEST")
    print("="*80)
    
    # Determine rebalance dates
    start_date = max(leverage_df["date"].min(), price_df["date"].min())
    end_date = min(leverage_df["date"].max(), price_df["date"].max())
    
    print(f"\nBacktest Period: {start_date.date()} to {end_date.date()}")
    
    if rebalance_freq == "monthly":
        rebalance_dates = create_monthly_rebalance_dates(start_date, end_date)
    else:
        # Weekly rebalancing
        rebalance_dates = pd.date_range(start=start_date, end=end_date, freq='W-MON').tolist()
    
    print(f"Rebalance Frequency: {rebalance_freq}")
    print(f"Number of Rebalances: {len(rebalance_dates)}")
    
    # Initialize tracking
    portfolio_values = []
    holdings = {"longs": [], "shorts": []}
    trade_log = []
    
    # Initialize portfolio value
    portfolio_value = 1.0
    current_longs = []
    current_shorts = []
    
    # Get all daily dates for tracking
    all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    print(f"\nProcessing {len(all_dates)} days...")
    
    for date in all_dates:
        # Check if it's a rebalance date
        is_rebalance = date in rebalance_dates
        
        if is_rebalance:
            # Rank coins by leverage
            new_longs, new_shorts = rank_coins_by_leverage(leverage_df, date)
            
            if not new_longs or not new_shorts:
                # Skip if we can't form portfolios
                portfolio_values.append({
                    "date": date,
                    "portfolio_value": portfolio_value,
                    "long_value": portfolio_value / 2,
                    "short_value": portfolio_value / 2,
                    "num_longs": len(current_longs),
                    "num_shorts": len(current_shorts)
                })
                continue
            
            # Calculate turnover and transaction costs
            longs_added = set(new_longs) - set(current_longs)
            longs_removed = set(current_longs) - set(new_longs)
            shorts_added = set(new_shorts) - set(current_shorts)
            shorts_removed = set(current_shorts) - set(new_shorts)
            
            total_trades = len(longs_added) + len(longs_removed) + len(shorts_added) + len(shorts_removed)
            
            if total_trades > 0:
                # Apply transaction costs
                turnover_ratio = total_trades / (len(new_longs) + len(new_shorts))
                cost = portfolio_value * turnover_ratio * transaction_cost
                portfolio_value -= cost
                
                trade_log.append({
                    "date": date,
                    "longs_added": len(longs_added),
                    "longs_removed": len(longs_removed),
                    "shorts_added": len(shorts_added),
                    "shorts_removed": len(shorts_removed),
                    "transaction_cost": cost,
                    "portfolio_value": portfolio_value
                })
            
            # Update holdings
            current_longs = new_longs
            current_shorts = new_shorts
            
            holdings["longs"].append({
                "date": date,
                "coins": current_longs.copy()
            })
            holdings["shorts"].append({
                "date": date,
                "coins": current_shorts.copy()
            })
        
        # Calculate daily returns for current holdings
        if current_longs or current_shorts:
            date_prices = price_df[price_df["date"] == date]
            
            # Long portfolio return
            long_return = 0.0
            if current_longs:
                long_returns = date_prices[date_prices["coin_symbol"].isin(current_longs)]["return"]
                if len(long_returns) > 0:
                    long_return = long_returns.mean()  # Equal weight
            
            # Short portfolio return (negative of returns)
            short_return = 0.0
            if current_shorts:
                short_returns = date_prices[date_prices["coin_symbol"].isin(current_shorts)]["return"]
                if len(short_returns) > 0:
                    short_return = -short_returns.mean()  # Negative for short
            
            # Combined portfolio return (50% long, 50% short)
            if current_longs and current_shorts:
                daily_return = 0.5 * long_return + 0.5 * short_return
            elif current_longs:
                daily_return = long_return
            elif current_shorts:
                daily_return = short_return
            else:
                daily_return = 0.0
            
            # Update portfolio value
            portfolio_value *= (1 + daily_return)
        
        # Record portfolio value
        portfolio_values.append({
            "date": date,
            "portfolio_value": portfolio_value,
            "long_value": portfolio_value / 2,
            "short_value": portfolio_value / 2,
            "num_longs": len(current_longs),
            "num_shorts": len(current_shorts)
        })
    
    print(f"  ? Backtest complete")
    print(f"  ? Final portfolio value: {portfolio_value:.4f}")
    print(f"  ? Total return: {(portfolio_value - 1) * 100:.2f}%")
    
    return pd.DataFrame(portfolio_values), holdings, pd.DataFrame(trade_log)


def calculate_performance_metrics(portfolio_df):
    """Calculate comprehensive performance metrics"""
    
    print("\n" + "="*80)
    print("PERFORMANCE METRICS")
    print("="*80)
    
    # Calculate returns
    portfolio_df["daily_return"] = portfolio_df["portfolio_value"].pct_change()
    
    # Total return
    total_return = (portfolio_df["portfolio_value"].iloc[-1] / portfolio_df["portfolio_value"].iloc[0] - 1) * 100
    
    # Annualized return
    days = (portfolio_df["date"].iloc[-1] - portfolio_df["date"].iloc[0]).days
    years = days / 365.25
    annualized_return = ((portfolio_df["portfolio_value"].iloc[-1] / portfolio_df["portfolio_value"].iloc[0]) ** (1/years) - 1) * 100
    
    # Volatility (annualized)
    daily_vol = portfolio_df["daily_return"].std()
    annualized_vol = daily_vol * np.sqrt(252) * 100
    
    # Sharpe Ratio (assuming 0% risk-free rate)
    sharpe_ratio = (annualized_return / annualized_vol) if annualized_vol > 0 else 0
    
    # Maximum Drawdown
    cumulative = portfolio_df["portfolio_value"]
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max * 100
    max_drawdown = drawdown.min()
    
    # Calmar Ratio
    calmar_ratio = (annualized_return / abs(max_drawdown)) if max_drawdown != 0 else 0
    
    # Win Rate
    win_rate = (portfolio_df["daily_return"] > 0).sum() / len(portfolio_df["daily_return"].dropna()) * 100
    
    # Best/Worst days
    best_day = portfolio_df["daily_return"].max() * 100
    worst_day = portfolio_df["daily_return"].min() * 100
    
    print(f"\nTotal Return:        {total_return:>10.2f}%")
    print(f"Annualized Return:   {annualized_return:>10.2f}%")
    print(f"Annualized Volatility: {annualized_vol:>8.2f}%")
    print(f"Sharpe Ratio:        {sharpe_ratio:>10.2f}")
    print(f"Maximum Drawdown:    {max_drawdown:>10.2f}%")
    print(f"Calmar Ratio:        {calmar_ratio:>10.2f}")
    print(f"Win Rate:            {win_rate:>10.2f}%")
    print(f"Best Day:            {best_day:>10.2f}%")
    print(f"Worst Day:           {worst_day:>10.2f}%")
    
    # Monthly returns
    portfolio_df["year_month"] = portfolio_df["date"].dt.to_period("M")
    monthly_returns = portfolio_df.groupby("year_month")["daily_return"].apply(
        lambda x: (1 + x).prod() - 1
    ) * 100
    
    print(f"\nMonthly Statistics:")
    print(f"  Average Monthly Return: {monthly_returns.mean():>8.2f}%")
    print(f"  Positive Months:        {(monthly_returns > 0).sum():>8} ({(monthly_returns > 0).sum() / len(monthly_returns) * 100:.1f}%)")
    print(f"  Negative Months:        {(monthly_returns < 0).sum():>8} ({(monthly_returns < 0).sum() / len(monthly_returns) * 100:.1f}%)")
    print(f"  Best Month:             {monthly_returns.max():>8.2f}%")
    print(f"  Worst Month:            {monthly_returns.min():>8.2f}%")
    
    metrics = {
        "total_return": total_return,
        "annualized_return": annualized_return,
        "annualized_volatility": annualized_vol,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "calmar_ratio": calmar_ratio,
        "win_rate": win_rate,
        "best_day": best_day,
        "worst_day": worst_day,
        "monthly_returns": monthly_returns
    }
    
    return metrics


def analyze_holdings(holdings):
    """Analyze most frequently held coins"""
    
    print("\n" + "="*80)
    print("HOLDINGS ANALYSIS")
    print("="*80)
    
    # Count frequency of longs
    long_counter = {}
    for h in holdings["longs"]:
        for coin in h["coins"]:
            long_counter[coin] = long_counter.get(coin, 0) + 1
    
    # Count frequency of shorts
    short_counter = {}
    for h in holdings["shorts"]:
        for coin in h["coins"]:
            short_counter[coin] = short_counter.get(coin, 0) + 1
    
    total_rebalances = len(holdings["longs"])
    
    print(f"\nTotal Rebalances: {total_rebalances}")
    
    print(f"\nMost Frequently LONG (Top 10):")
    long_sorted = sorted(long_counter.items(), key=lambda x: x[1], reverse=True)[:10]
    for coin, count in long_sorted:
        pct = (count / total_rebalances) * 100
        print(f"  {coin:<10} {count:>3} times ({pct:>5.1f}%)")
    
    print(f"\nMost Frequently SHORT (Top 10):")
    short_sorted = sorted(short_counter.items(), key=lambda x: x[1], reverse=True)[:10]
    for coin, count in short_sorted:
        pct = (count / total_rebalances) * 100
        print(f"  {coin:<10} {count:>3} times ({pct:>5.1f}%)")
    
    return long_counter, short_counter


def create_visualizations(portfolio_df, metrics, holdings, output_dir="backtests/results"):
    """Create comprehensive visualization charts"""
    
    print("\n" + "="*80)
    print("GENERATING VISUALIZATIONS")
    print("="*80)
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # ========================================================================
    # CHART 1: Portfolio performance over time
    # ========================================================================
    fig, axes = plt.subplots(3, 1, figsize=(16, 12))
    
    # Plot 1: Portfolio value
    ax1 = axes[0]
    ax1.plot(portfolio_df["date"], portfolio_df["portfolio_value"], 
            linewidth=2, color='blue', label='Portfolio Value')
    ax1.fill_between(portfolio_df["date"], 1, portfolio_df["portfolio_value"], 
                     alpha=0.3, color='blue')
    ax1.axhline(y=1, color='black', linestyle='--', alpha=0.5)
    ax1.set_ylabel("Portfolio Value", fontweight='bold', fontsize=12)
    ax1.set_title("Leverage Long/Short Strategy - Portfolio Performance", 
                 fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left')
    ax1.grid(alpha=0.3)
    
    # Add metrics text
    metrics_text = f"Total Return: {metrics['total_return']:.2f}%\n"
    metrics_text += f"Ann. Return: {metrics['annualized_return']:.2f}%\n"
    metrics_text += f"Sharpe: {metrics['sharpe_ratio']:.2f}\n"
    metrics_text += f"Max DD: {metrics['max_drawdown']:.2f}%"
    ax1.text(0.02, 0.98, metrics_text, transform=ax1.transAxes,
            verticalalignment='top', fontsize=10,
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    # Plot 2: Drawdown
    ax2 = axes[1]
    cumulative = portfolio_df["portfolio_value"]
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max * 100
    
    ax2.fill_between(portfolio_df["date"], 0, drawdown, 
                     color='red', alpha=0.5)
    ax2.plot(portfolio_df["date"], drawdown, color='darkred', linewidth=1.5)
    ax2.set_ylabel("Drawdown (%)", fontweight='bold', fontsize=12)
    ax2.set_title("Drawdown Over Time", fontsize=12, fontweight='bold')
    ax2.grid(alpha=0.3)
    
    # Plot 3: Rolling 30-day return
    ax3 = axes[2]
    portfolio_df["rolling_return_30d"] = portfolio_df["portfolio_value"].pct_change(30) * 100
    ax3.plot(portfolio_df["date"], portfolio_df["rolling_return_30d"], 
            color='green', linewidth=1.5)
    ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    ax3.fill_between(portfolio_df["date"], 0, portfolio_df["rolling_return_30d"],
                     where=portfolio_df["rolling_return_30d"] >= 0, 
                     color='green', alpha=0.3)
    ax3.fill_between(portfolio_df["date"], 0, portfolio_df["rolling_return_30d"],
                     where=portfolio_df["rolling_return_30d"] < 0, 
                     color='red', alpha=0.3)
    ax3.set_ylabel("30-Day Return (%)", fontweight='bold', fontsize=12)
    ax3.set_xlabel("Date", fontweight='bold', fontsize=12)
    ax3.set_title("Rolling 30-Day Returns", fontsize=12, fontweight='bold')
    ax3.grid(alpha=0.3)
    
    plt.tight_layout()
    
    file1 = output_path / f"leverage_longshor_performance_{timestamp}.png"
    plt.savefig(file1, dpi=300, bbox_inches='tight')
    print(f"  ? Saved: {file1}")
    plt.close()
    
    # ========================================================================
    # CHART 2: Monthly returns heatmap
    # ========================================================================
    fig, ax = plt.subplots(figsize=(16, 8))
    
    monthly_returns = metrics["monthly_returns"]
    
    # Create pivot table for heatmap
    monthly_data = monthly_returns.reset_index()
    monthly_data["year"] = monthly_data["year_month"].dt.year
    monthly_data["month"] = monthly_data["year_month"].dt.month
    
    pivot = monthly_data.pivot(index="year", columns="month", values="year_month")
    pivot = pivot.applymap(lambda x: monthly_returns[x] if pd.notna(x) else np.nan)
    
    # Plot heatmap
    try:
        import seaborn as sns
        sns.heatmap(pivot, annot=True, fmt='.1f', cmap='RdYlGn', center=0,
                   ax=ax, cbar_kws={'label': 'Monthly Return (%)'}, 
                   linewidths=0.5, vmin=-20, vmax=20)
    except ImportError:
        im = ax.imshow(pivot.values, cmap='RdYlGn', aspect='auto', vmin=-20, vmax=20)
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_yticks(range(len(pivot.index)))
        ax.set_xticklabels(pivot.columns)
        ax.set_yticklabels(pivot.index)
        plt.colorbar(im, ax=ax, label='Monthly Return (%)')
    
    ax.set_xlabel("Month", fontweight='bold', fontsize=12)
    ax.set_ylabel("Year", fontweight='bold', fontsize=12)
    ax.set_title("Monthly Returns Heatmap (%)", fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    
    file2 = output_path / f"leverage_longshort_monthly_returns_{timestamp}.png"
    plt.savefig(file2, dpi=300, bbox_inches='tight')
    print(f"  ? Saved: {file2}")
    plt.close()
    
    # ========================================================================
    # CHART 3: Return distribution
    # ========================================================================
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    
    # Daily returns distribution
    ax1 = axes[0, 0]
    daily_returns = portfolio_df["daily_return"].dropna() * 100
    ax1.hist(daily_returns, bins=50, alpha=0.7, color='blue', edgecolor='black')
    ax1.axvline(x=daily_returns.mean(), color='red', linestyle='--', 
               linewidth=2, label=f'Mean: {daily_returns.mean():.2f}%')
    ax1.axvline(x=0, color='black', linestyle='-', linewidth=1, alpha=0.5)
    ax1.set_xlabel("Daily Return (%)")
    ax1.set_ylabel("Frequency")
    ax1.set_title("Daily Returns Distribution", fontweight='bold')
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    # Monthly returns distribution
    ax2 = axes[0, 1]
    ax2.hist(monthly_returns, bins=30, alpha=0.7, color='green', edgecolor='black')
    ax2.axvline(x=monthly_returns.mean(), color='red', linestyle='--', 
               linewidth=2, label=f'Mean: {monthly_returns.mean():.2f}%')
    ax2.axvline(x=0, color='black', linestyle='-', linewidth=1, alpha=0.5)
    ax2.set_xlabel("Monthly Return (%)")
    ax2.set_ylabel("Frequency")
    ax2.set_title("Monthly Returns Distribution", fontweight='bold')
    ax2.legend()
    ax2.grid(alpha=0.3)
    
    # Rolling Sharpe Ratio (90-day)
    ax3 = axes[1, 0]
    portfolio_df["rolling_sharpe_90d"] = (
        portfolio_df["daily_return"].rolling(90).mean() / 
        portfolio_df["daily_return"].rolling(90).std() * np.sqrt(252)
    )
    ax3.plot(portfolio_df["date"], portfolio_df["rolling_sharpe_90d"], 
            color='purple', linewidth=2)
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.5)
    ax3.axhline(y=1, color='green', linestyle='--', linewidth=1, alpha=0.5, label='Sharpe = 1')
    ax3.set_ylabel("90-Day Rolling Sharpe Ratio")
    ax3.set_xlabel("Date")
    ax3.set_title("Rolling Sharpe Ratio", fontweight='bold')
    ax3.legend()
    ax3.grid(alpha=0.3)
    
    # Cumulative return by year
    ax4 = axes[1, 1]
    portfolio_df["year"] = portfolio_df["date"].dt.year
    yearly_returns = portfolio_df.groupby("year")["daily_return"].apply(
        lambda x: ((1 + x).prod() - 1) * 100
    )
    colors = ['green' if x > 0 else 'red' for x in yearly_returns]
    ax4.bar(yearly_returns.index, yearly_returns, color=colors, alpha=0.7, edgecolor='black')
    ax4.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax4.set_ylabel("Annual Return (%)")
    ax4.set_xlabel("Year")
    ax4.set_title("Annual Returns", fontweight='bold')
    ax4.grid(alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    file3 = output_path / f"leverage_longshort_distributions_{timestamp}.png"
    plt.savefig(file3, dpi=300, bbox_inches='tight')
    print(f"  ? Saved: {file3}")
    plt.close()


def export_results(portfolio_df, metrics, holdings, trade_log, output_dir="backtests/results"):
    """Export results to CSV files"""
    
    print("\n" + "="*80)
    print("EXPORTING RESULTS")
    print("="*80)
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 1. Portfolio values
    file1 = output_path / f"leverage_longshort_portfolio_values_{timestamp}.csv"
    portfolio_df.to_csv(file1, index=False)
    print(f"  ? Portfolio values: {file1}")
    
    # 2. Trade log
    if not trade_log.empty:
        file2 = output_path / f"leverage_longshort_trades_{timestamp}.csv"
        trade_log.to_csv(file2, index=False)
        print(f"  ? Trade log: {file2}")
    
    # 3. Metrics summary
    metrics_df = pd.DataFrame([{
        "metric": k,
        "value": v
    } for k, v in metrics.items() if not isinstance(v, pd.Series)])
    
    file3 = output_path / f"leverage_longshort_metrics_{timestamp}.csv"
    metrics_df.to_csv(file3, index=False)
    print(f"  ? Metrics: {file3}")
    
    # 4. Strategy info
    strategy_info = {
        "strategy_name": "Leverage Long/Short",
        "description": "Long top 10 leveraged coins, Short bottom 10 least leveraged",
        "rebalance_frequency": "Monthly",
        "start_date": portfolio_df["date"].min(),
        "end_date": portfolio_df["date"].max(),
        "total_return_pct": metrics["total_return"],
        "annualized_return_pct": metrics["annualized_return"],
        "sharpe_ratio": metrics["sharpe_ratio"],
        "max_drawdown_pct": metrics["max_drawdown"],
        "win_rate_pct": metrics["win_rate"]
    }
    
    strategy_df = pd.DataFrame([strategy_info])
    file4 = output_path / f"leverage_longshort_strategy_info_{timestamp}.csv"
    strategy_df.to_csv(file4, index=False)
    print(f"  ? Strategy info: {file4}")
    
    return file1, file2, file3, file4


def main():
    """Main execution"""
    
    print("\n" + "="*80)
    print("LEVERAGE LONG/SHORT BACKTEST")
    print("="*80)
    print("\nStrategy:")
    print("  ? LONG: Top 10 coins by OI/Market Cap ratio (most leveraged)")
    print("  ? SHORT: Bottom 10 coins by OI/Market Cap ratio (least leveraged)")
    print("  ? Rebalance: Monthly (first Monday)")
    print("  ? Weighting: Equal weight within each leg")
    print("  ? Transaction costs: 10 bps per trade")
    print("\n" + "="*80)
    
    # Load data
    leverage_df = load_historical_leverage_data()
    price_df = load_price_data()
    
    # Run backtest
    portfolio_df, holdings, trade_log = backtest_leverage_strategy(
        leverage_df,
        price_df,
        rebalance_freq="monthly",
        top_n=10,
        bottom_n=10
    )
    
    # Calculate metrics
    metrics = calculate_performance_metrics(portfolio_df)
    
    # Analyze holdings
    long_counter, short_counter = analyze_holdings(holdings)
    
    # Create visualizations
    create_visualizations(portfolio_df, metrics, holdings)
    
    # Export results
    export_results(portfolio_df, metrics, holdings, trade_log)
    
    print("\n" + "="*80)
    print("? BACKTEST COMPLETE")
    print("="*80)
    print(f"\nFinal Results:")
    print(f"  ? Total Return:      {metrics['total_return']:>10.2f}%")
    print(f"  ? Annualized Return: {metrics['annualized_return']:>10.2f}%")
    print(f"  ? Sharpe Ratio:      {metrics['sharpe_ratio']:>10.2f}")
    print(f"  ? Max Drawdown:      {metrics['max_drawdown']:>10.2f}%")
    

if __name__ == "__main__":
    main()
