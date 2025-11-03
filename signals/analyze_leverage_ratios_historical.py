#!/usr/bin/env python3
"""
Historical Leverage Analysis - Track Leverage Ratios Since 2021

This script calculates OI/Market Cap ratios over time to show:
- How leverage has evolved historically
- Which coins have consistently high/low leverage
- Leverage regime changes and trends
- Market-wide leverage cycles
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['figure.figsize'] = (16, 10)


def find_latest_file(pattern):
    """Find the most recent file matching a pattern."""
    from glob import glob
    files = sorted(glob(pattern), reverse=True)
    if files:
        return files[0]
    return None


def load_historical_oi_data():
    """Load historical open interest data (automatically finds latest file)"""
    print("Loading historical Open Interest data...")
    
    # Try multiple patterns for OI data files
    oi_patterns = [
        "data/raw/historical_open_interest_all_perps_since2020_*.csv",
        "data/raw/historical_open_interest_top50_*.csv",
        "data/raw/historical_open_interest_top50_ALL_HISTORY_*.csv"
    ]
    
    oi_file = None
    for pattern in oi_patterns:
        oi_file = find_latest_file(pattern)
        if oi_file:
            print(f"  Using OI data: {oi_file}")
            break
    
    if not oi_file:
        raise FileNotFoundError(
            "No Open Interest data found. Run:\n"
            "  python3 data/scripts/refresh_oi_data.py"
        )
    
    df = pd.read_csv(oi_file)
    df["date"] = pd.to_datetime(df["date"])
    print(f"  ? {len(df)} OI records from {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"  ? {df['coin_symbol'].nunique()} unique coins")
    return df


def load_historical_funding_rates():
    """Load historical funding rates data (automatically finds latest file)"""
    print("Loading historical Funding Rates data...")
    
    # Try to find latest funding rates file (exclude summary files)
    fr_patterns = [
        "data/raw/historical_funding_rates_top50_ALL_HISTORY_*.csv",
        "data/raw/historical_funding_rates_top50_*.csv"
    ]
    
    fr_file = None
    for pattern in fr_patterns:
        from glob import glob
        files = sorted(glob(pattern), reverse=True)
        # Filter out summary files
        files = [f for f in files if "summary" not in f.lower()]
        if files:
            fr_file = files[0]
            print(f"  Using Funding Rates data: {fr_file}")
            break
    
    if not fr_file:
        raise FileNotFoundError(
            "No Funding Rates data found. Run:\n"
            "  python3 data/scripts/fetch_historical_funding_rates_top50.py"
        )
    
    df = pd.read_csv(fr_file)
    df["date"] = pd.to_datetime(df["date"])
    print(f"  ? {len(df)} funding records from {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"  ? {df['coin_symbol'].nunique()} unique coins")
    return df


def load_historical_market_cap():
    """Load historical market cap data (monthly snapshots)"""
    print("Loading historical Market Cap data...")
    
    # Try to find the monthly snapshots file
    mcap_file = "data/raw/coinmarketcap_monthly_all_snapshots.csv"
    if not Path(mcap_file).exists():
        raise FileNotFoundError(
            f"Historical Market Cap data not found: {mcap_file}\n"
            "This file contains monthly snapshots needed for historical analysis."
        )
    
    df = pd.read_csv(mcap_file)
    
    # Parse snapshot_date
    df["date"] = pd.to_datetime(df["snapshot_date"], format='%Y%m%d')
    
    # Rename columns for consistency
    df = df.rename(columns={
        "Symbol": "coin_symbol",
        "Name": "coin_name",
        "Market Cap": "market_cap",
        "Rank": "rank"
    })
    
    # Select relevant columns
    df = df[["date", "coin_symbol", "coin_name", "market_cap", "rank"]].copy()
    
    # Remove any rows with missing market cap
    df = df.dropna(subset=["market_cap"])
    
    print(f"  ? {len(df)} market cap records from {df['date'].min().date()} to {df['date'].max().date()}")
    print(f"  ? {df['coin_symbol'].nunique()} unique coins")
    
    return df


def interpolate_market_cap(mcap_monthly_df, oi_df):
    """
    Interpolate daily market cap values from monthly snapshots
    
    We'll use forward-fill approach: use the most recent snapshot value
    until the next snapshot is available
    """
    print("\nInterpolating daily market cap values from monthly snapshots...")
    
    # Get unique dates from OI data (these are the dates we need market cap for)
    oi_dates = sorted(oi_df["date"].unique())
    oi_symbols = set(oi_df["coin_symbol"].unique())
    
    # Get market cap data only for symbols that exist in OI data
    mcap_df = mcap_monthly_df[mcap_monthly_df["coin_symbol"].isin(oi_symbols)].copy()
    
    # Create a complete date range
    date_range = pd.date_range(start=min(oi_dates), end=max(oi_dates), freq='D')
    
    # For each coin, create a time series with forward-filled market cap
    interpolated_data = []
    
    for symbol in mcap_df["coin_symbol"].unique():
        symbol_mcap = mcap_df[mcap_df["coin_symbol"] == symbol].copy()
        symbol_mcap = symbol_mcap.sort_values("date")
        
        # Create full date range for this symbol
        symbol_ts = pd.DataFrame({"date": date_range})
        
        # Merge with existing data
        symbol_ts = symbol_ts.merge(
            symbol_mcap[["date", "market_cap", "coin_name", "rank"]], 
            on="date", 
            how="left"
        )
        
        # Forward fill market cap values
        symbol_ts["market_cap"] = symbol_ts["market_cap"].ffill()
        symbol_ts["rank"] = symbol_ts["rank"].ffill()
        
        # Get the most common name (for consistency)
        most_common_name = symbol_mcap["coin_name"].mode()[0] if not symbol_mcap["coin_name"].empty else symbol
        symbol_ts["coin_name"] = symbol_ts["coin_name"].fillna(most_common_name)
        
        # Add symbol
        symbol_ts["coin_symbol"] = symbol
        
        # Remove rows without market cap (before first snapshot)
        symbol_ts = symbol_ts.dropna(subset=["market_cap"])
        
        interpolated_data.append(symbol_ts)
    
    # Combine all
    result = pd.concat(interpolated_data, ignore_index=True)
    
    print(f"  ? Interpolated {len(result)} daily market cap records")
    print(f"  ? Coverage: {result['coin_symbol'].nunique()} coins")
    
    return result


def calculate_historical_leverage(oi_df, mcap_df, funding_df):
    """
    Calculate historical leverage ratios by merging OI with market cap data
    """
    print("\nCalculating historical leverage ratios...")
    
    # Merge OI with market cap
    df = oi_df.merge(
        mcap_df[["date", "coin_symbol", "market_cap", "rank"]], 
        on=["date", "coin_symbol"], 
        how="inner"
    )
    
    print(f"  ? After merge: {len(df)} records")
    
    # Add funding rates (optional, daily average)
    funding_daily = funding_df.groupby(["date", "coin_symbol"], as_index=False).agg({
        "funding_rate_pct": "mean"
    })
    
    df = df.merge(
        funding_daily,
        on=["date", "coin_symbol"],
        how="left"
    )
    
    # Calculate OI/Market Cap ratio
    df["oi_to_mcap_ratio"] = (df["oi_close"] / df["market_cap"]) * 100
    
    # Calculate rolling metrics (30-day windows)
    df = df.sort_values(["coin_symbol", "date"])
    
    df["oi_to_mcap_ma30"] = df.groupby("coin_symbol")["oi_to_mcap_ratio"].transform(
        lambda x: x.rolling(window=30, min_periods=1).mean()
    )
    
    df["oi_to_mcap_std30"] = df.groupby("coin_symbol")["oi_to_mcap_ratio"].transform(
        lambda x: x.rolling(window=30, min_periods=1).std()
    )
    
    print(f"  ? Calculated leverage ratios for {df['coin_symbol'].nunique()} coins")
    print(f"  ? Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    
    return df


def analyze_aggregate_leverage(df):
    """
    Analyze market-wide leverage trends
    """
    print("\n" + "="*80)
    print("MARKET-WIDE LEVERAGE TRENDS")
    print("="*80)
    
    # Calculate aggregate metrics by date
    daily_agg = df.groupby("date").agg({
        "oi_close": "sum",
        "market_cap": "sum",
        "oi_to_mcap_ratio": "mean",
        "coin_symbol": "count"
    }).reset_index()
    
    daily_agg.columns = ["date", "total_oi", "total_mcap", "avg_oi_mcap_ratio", "num_coins"]
    daily_agg["aggregate_oi_mcap_ratio"] = (daily_agg["total_oi"] / daily_agg["total_mcap"]) * 100
    
    # Calculate 30-day moving average
    daily_agg["oi_mcap_ma30"] = daily_agg["aggregate_oi_mcap_ratio"].rolling(30, min_periods=1).mean()
    
    # Find peaks and troughs
    daily_agg["oi_mcap_ma30_smooth"] = daily_agg["aggregate_oi_mcap_ratio"].rolling(90, min_periods=1).mean()
    
    max_leverage = daily_agg.loc[daily_agg["aggregate_oi_mcap_ratio"].idxmax()]
    min_leverage = daily_agg.loc[daily_agg["aggregate_oi_mcap_ratio"].idxmin()]
    latest = daily_agg.iloc[-1]
    
    print(f"\nAggregate Leverage Statistics:")
    print(f"  Current Leverage (latest):  {latest['aggregate_oi_mcap_ratio']:.3f}%")
    print(f"  Average (all-time):         {daily_agg['aggregate_oi_mcap_ratio'].mean():.3f}%")
    print(f"  Peak Leverage:              {max_leverage['aggregate_oi_mcap_ratio']:.3f}% on {max_leverage['date'].date()}")
    print(f"  Minimum Leverage:           {min_leverage['aggregate_oi_mcap_ratio']:.3f}% on {min_leverage['date'].date()}")
    
    # Year-over-year comparison
    print(f"\nYear-by-Year Average Leverage:")
    yearly = df.copy()
    yearly["year"] = yearly["date"].dt.year
    yearly_avg = yearly.groupby("year")["oi_to_mcap_ratio"].mean()
    
    for year, avg_ratio in yearly_avg.items():
        print(f"  {year}: {avg_ratio:.3f}%")
    
    return daily_agg


def identify_top_leveraged_coins_over_time(df, top_n=10):
    """
    Identify which coins have consistently high leverage
    """
    print("\n" + "="*80)
    print(f"TOP {top_n} MOST LEVERAGED COINS (Historical Average)")
    print("="*80)
    
    # Calculate average leverage per coin over entire history
    coin_avg = df.groupby("coin_symbol").agg({
        "oi_to_mcap_ratio": ["mean", "median", "std", "max"],
        "coin_name": "first",
        "oi_close": "mean"
    }).reset_index()
    
    coin_avg.columns = ["coin_symbol", "avg_oi_mcap", "median_oi_mcap", 
                        "std_oi_mcap", "max_oi_mcap", "coin_name", "avg_oi"]
    
    coin_avg = coin_avg.sort_values("avg_oi_mcap", ascending=False)
    
    print(f"\nTop {top_n} by Historical Average OI/MCap Ratio:")
    for idx, row in coin_avg.head(top_n).iterrows():
        print(f"\n{row['coin_symbol']:<10} {row['coin_name']:<30}")
        print(f"  Average:  {row['avg_oi_mcap']:>8.2f}%")
        print(f"  Median:   {row['median_oi_mcap']:>8.2f}%")
        print(f"  Max:      {row['max_oi_mcap']:>8.2f}%")
        print(f"  Std Dev:  {row['std_oi_mcap']:>8.2f}%")
    
    return coin_avg


def create_time_series_visualizations(df, daily_agg, coin_avg, output_dir="signals"):
    """
    Create comprehensive time series visualizations
    """
    print("\n" + "="*80)
    print("GENERATING TIME SERIES VISUALIZATIONS")
    print("="*80)
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # ========================================================================
    # CHART 1: Market-wide aggregate leverage over time
    # ========================================================================
    fig, axes = plt.subplots(3, 1, figsize=(16, 12))
    
    # Plot 1: Aggregate OI/MCap ratio
    ax1 = axes[0]
    ax1.plot(daily_agg["date"], daily_agg["aggregate_oi_mcap_ratio"], 
            alpha=0.3, color='blue', label='Daily')
    ax1.plot(daily_agg["date"], daily_agg["oi_mcap_ma30"], 
            color='red', linewidth=2, label='30-day MA')
    ax1.fill_between(daily_agg["date"], 0, daily_agg["oi_mcap_ma30"], alpha=0.2, color='red')
    ax1.set_ylabel("Aggregate OI/MCap Ratio (%)", fontweight='bold')
    ax1.set_title("Market-Wide Leverage Ratio Over Time (2021-Present)", 
                 fontsize=14, fontweight='bold')
    ax1.legend()
    ax1.grid(alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    
    # Plot 2: Total Open Interest
    ax2 = axes[1]
    ax2.plot(daily_agg["date"], daily_agg["total_oi"] / 1e9, color='green', linewidth=2)
    ax2.fill_between(daily_agg["date"], 0, daily_agg["total_oi"] / 1e9, alpha=0.3, color='green')
    ax2.set_ylabel("Total Open Interest (Billions USD)", fontweight='bold')
    ax2.set_title("Total Open Interest Over Time", fontsize=12, fontweight='bold')
    ax2.grid(alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    
    # Plot 3: Number of coins tracked
    ax3 = axes[2]
    ax3.plot(daily_agg["date"], daily_agg["num_coins"], color='purple', linewidth=2)
    ax3.fill_between(daily_agg["date"], 0, daily_agg["num_coins"], alpha=0.3, color='purple')
    ax3.set_ylabel("Number of Coins", fontweight='bold')
    ax3.set_xlabel("Date", fontweight='bold')
    ax3.set_title("Number of Coins with OI Data", fontsize=12, fontweight='bold')
    ax3.grid(alpha=0.3)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    
    plt.tight_layout()
    
    file1 = output_path / f"historical_leverage_aggregate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(file1, dpi=300, bbox_inches='tight')
    print(f"  ? Saved: {file1}")
    plt.close()
    
    # ========================================================================
    # CHART 2: Top 10 most leveraged coins over time
    # ========================================================================
    fig, axes = plt.subplots(2, 1, figsize=(16, 10))
    
    # Get top 10 coins by average leverage
    top_10_coins = coin_avg.head(10)["coin_symbol"].tolist()
    
    # Plot each coin's leverage over time
    ax1 = axes[0]
    for symbol in top_10_coins:
        coin_data = df[df["coin_symbol"] == symbol].sort_values("date")
        if len(coin_data) > 0:
            ax1.plot(coin_data["date"], coin_data["oi_to_mcap_ma30"], 
                    label=symbol, linewidth=2, alpha=0.8)
    
    ax1.set_ylabel("OI/MCap Ratio (%) - 30d MA", fontweight='bold')
    ax1.set_title("Top 10 Most Leveraged Coins - Historical Trends", 
                 fontsize=14, fontweight='bold')
    ax1.legend(loc='upper left', ncol=2)
    ax1.grid(alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    
    # Plot: Major coins (BTC, ETH, SOL, BNB)
    ax2 = axes[1]
    major_coins = ["BTC", "ETH", "SOL", "BNB"]
    colors = ['#F7931A', '#627EEA', '#14F195', '#F3BA2F']
    
    for symbol, color in zip(major_coins, colors):
        coin_data = df[df["coin_symbol"] == symbol].sort_values("date")
        if len(coin_data) > 0:
            ax2.plot(coin_data["date"], coin_data["oi_to_mcap_ma30"], 
                    label=symbol, linewidth=2.5, alpha=0.9, color=color)
    
    ax2.set_ylabel("OI/MCap Ratio (%) - 30d MA", fontweight='bold')
    ax2.set_xlabel("Date", fontweight='bold')
    ax2.set_title("Major Coins Leverage Trends", fontsize=12, fontweight='bold')
    ax2.legend(loc='upper left')
    ax2.grid(alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    
    plt.tight_layout()
    
    file2 = output_path / f"historical_leverage_by_coin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(file2, dpi=300, bbox_inches='tight')
    print(f"  ? Saved: {file2}")
    plt.close()
    
    # ========================================================================
    # CHART 3: Heatmap of leverage over time (top coins)
    # ========================================================================
    fig, ax = plt.subplots(figsize=(16, 10))
    
    # Get top 20 coins and create pivot table
    top_20_coins = coin_avg.head(20)["coin_symbol"].tolist()
    heatmap_data = df[df["coin_symbol"].isin(top_20_coins)].copy()
    
    # Resample to monthly for cleaner visualization
    heatmap_data["month"] = heatmap_data["date"].dt.to_period("M")
    heatmap_monthly = heatmap_data.groupby(["month", "coin_symbol"])["oi_to_mcap_ratio"].mean().reset_index()
    heatmap_monthly["month"] = heatmap_monthly["month"].dt.to_timestamp()
    
    # Create pivot table
    pivot = heatmap_monthly.pivot(index="coin_symbol", columns="month", values="oi_to_mcap_ratio")
    
    # Plot heatmap
    try:
        import seaborn as sns
        sns.heatmap(pivot, cmap="RdYlGn_r", ax=ax, cbar_kws={'label': 'OI/MCap Ratio (%)'}, 
                    vmin=0, vmax=pivot.max().max(), linewidths=0.5)
    except ImportError:
        im = ax.imshow(pivot.values, cmap='RdYlGn_r', aspect='auto', vmin=0, vmax=pivot.max().max())
        ax.set_xticks(range(len(pivot.columns)))
        ax.set_yticks(range(len(pivot.index)))
        ax.set_xticklabels(pivot.columns, rotation=45, ha='right')
        ax.set_yticklabels(pivot.index)
        plt.colorbar(im, ax=ax, label='OI/MCap Ratio (%)')
    
    ax.set_xlabel("Date", fontweight='bold')
    ax.set_ylabel("Coin Symbol", fontweight='bold')
    ax.set_title("Leverage Heatmap - Top 20 Coins Over Time", fontsize=14, fontweight='bold')
    
    # Format x-axis dates
    xticks = ax.get_xticks()
    if len(xticks) > 12:  # Show fewer labels if too many
        step = len(xticks) // 12
        ax.set_xticks(xticks[::step])
    
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    
    file3 = output_path / f"historical_leverage_heatmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(file3, dpi=300, bbox_inches='tight')
    print(f"  ? Saved: {file3}")
    plt.close()
    
    # ========================================================================
    # CHART 4: Distribution evolution over time
    # ========================================================================
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    
    # Select specific periods for comparison
    recent_data = df[df["date"] >= df["date"].max() - pd.Timedelta(days=90)]
    year_ago_data = df[(df["date"] >= df["date"].max() - pd.Timedelta(days=455)) & 
                       (df["date"] <= df["date"].max() - pd.Timedelta(days=365))]
    
    # Get data for 2021 and 2023
    data_2021 = df[df["date"].dt.year == 2021]
    data_2023 = df[df["date"].dt.year == 2023]
    
    # Plot distributions
    ax1 = axes[0, 0]
    ax1.hist(data_2021["oi_to_mcap_ratio"], bins=50, alpha=0.7, color='blue', edgecolor='black')
    ax1.set_xlabel("OI/MCap Ratio (%)")
    ax1.set_ylabel("Frequency")
    ax1.set_title("2021 Distribution", fontweight='bold')
    ax1.axvline(data_2021["oi_to_mcap_ratio"].median(), color='red', 
                linestyle='--', linewidth=2, label=f'Median: {data_2021["oi_to_mcap_ratio"].median():.2f}%')
    ax1.legend()
    ax1.grid(alpha=0.3)
    
    ax2 = axes[0, 1]
    ax2.hist(data_2023["oi_to_mcap_ratio"], bins=50, alpha=0.7, color='green', edgecolor='black')
    ax2.set_xlabel("OI/MCap Ratio (%)")
    ax2.set_ylabel("Frequency")
    ax2.set_title("2023 Distribution", fontweight='bold')
    ax2.axvline(data_2023["oi_to_mcap_ratio"].median(), color='red', 
                linestyle='--', linewidth=2, label=f'Median: {data_2023["oi_to_mcap_ratio"].median():.2f}%')
    ax2.legend()
    ax2.grid(alpha=0.3)
    
    ax3 = axes[1, 0]
    ax3.hist(year_ago_data["oi_to_mcap_ratio"], bins=50, alpha=0.7, color='orange', edgecolor='black')
    ax3.set_xlabel("OI/MCap Ratio (%)")
    ax3.set_ylabel("Frequency")
    ax3.set_title("~1 Year Ago Distribution", fontweight='bold')
    ax3.axvline(year_ago_data["oi_to_mcap_ratio"].median(), color='red', 
                linestyle='--', linewidth=2, label=f'Median: {year_ago_data["oi_to_mcap_ratio"].median():.2f}%')
    ax3.legend()
    ax3.grid(alpha=0.3)
    
    ax4 = axes[1, 1]
    ax4.hist(recent_data["oi_to_mcap_ratio"], bins=50, alpha=0.7, color='purple', edgecolor='black')
    ax4.set_xlabel("OI/MCap Ratio (%)")
    ax4.set_ylabel("Frequency")
    ax4.set_title("Last 90 Days Distribution", fontweight='bold')
    ax4.axvline(recent_data["oi_to_mcap_ratio"].median(), color='red', 
                linestyle='--', linewidth=2, label=f'Median: {recent_data["oi_to_mcap_ratio"].median():.2f}%')
    ax4.legend()
    ax4.grid(alpha=0.3)
    
    plt.suptitle("Leverage Distribution Evolution", fontsize=14, fontweight='bold', y=1.00)
    plt.tight_layout()
    
    file4 = output_path / f"historical_leverage_distributions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(file4, dpi=300, bbox_inches='tight')
    print(f"  ? Saved: {file4}")
    plt.close()


def export_historical_data(df, daily_agg, coin_avg, output_dir="signals"):
    """
    Export historical leverage data to CSV
    """
    print("\n" + "="*80)
    print("EXPORTING HISTORICAL DATA")
    print("="*80)
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 1. Full historical data (sampled weekly to reduce size)
    df_weekly = df[df["date"].dt.dayofweek == 0].copy()  # Monday samples
    df_weekly = df_weekly[[
        "date", "coin_symbol", "coin_name", "oi_close", "market_cap", 
        "oi_to_mcap_ratio", "oi_to_mcap_ma30", "funding_rate_pct"
    ]].sort_values(["date", "coin_symbol"])
    
    file1 = output_path / f"historical_leverage_weekly_{timestamp}.csv"
    df_weekly.to_csv(file1, index=False)
    print(f"  ? Weekly historical data: {file1}")
    
    # 2. Daily aggregate
    file2 = output_path / f"historical_leverage_daily_aggregate_{timestamp}.csv"
    daily_agg.to_csv(file2, index=False)
    print(f"  ? Daily aggregate data: {file2}")
    
    # 3. Coin averages
    file3 = output_path / f"historical_leverage_coin_averages_{timestamp}.csv"
    coin_avg.to_csv(file3, index=False)
    print(f"  ? Coin averages: {file3}")
    
    return file1, file2, file3


def main():
    """Main execution"""
    
    print("\n" + "="*80)
    print("HISTORICAL LEVERAGE ANALYSIS (2021-Present)")
    print("="*80)
    print(f"\nStarting analysis at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Load data
    oi_df = load_historical_oi_data()
    funding_df = load_historical_funding_rates()
    mcap_monthly_df = load_historical_market_cap()
    
    # Interpolate daily market cap from monthly snapshots
    mcap_daily_df = interpolate_market_cap(mcap_monthly_df, oi_df)
    
    # Calculate historical leverage
    leverage_df = calculate_historical_leverage(oi_df, mcap_daily_df, funding_df)
    
    # Analyze aggregate trends
    daily_agg = analyze_aggregate_leverage(leverage_df)
    
    # Identify top leveraged coins
    coin_avg = identify_top_leveraged_coins_over_time(leverage_df, top_n=15)
    
    # Create visualizations
    create_time_series_visualizations(leverage_df, daily_agg, coin_avg)
    
    # Export data
    export_historical_data(leverage_df, daily_agg, coin_avg)
    
    print("\n" + "="*80)
    print("? HISTORICAL ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nFinished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nKey Findings:")
    print(f"  ? Analyzed {len(leverage_df)} daily observations")
    print(f"  ? Covered {leverage_df['coin_symbol'].nunique()} unique coins")
    print(f"  ? Date range: {leverage_df['date'].min().date()} to {leverage_df['date'].max().date()}")
    print(f"  ? Current aggregate leverage: {daily_agg.iloc[-1]['aggregate_oi_mcap_ratio']:.3f}%")
    print(f"  ? Historical average: {daily_agg['aggregate_oi_mcap_ratio'].mean():.3f}%")


if __name__ == "__main__":
    main()
