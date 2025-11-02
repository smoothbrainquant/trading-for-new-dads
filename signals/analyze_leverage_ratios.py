#!/usr/bin/env python3
"""
Quantify Leveraged Positions Across Top 50 Coins

This script calculates multiple leverage metrics to identify which coins have the
most/least leveraged positions:

1. OI/Market Cap Ratio - Primary leverage indicator
2. Funding Rate (7d avg) - Indicates long/short demand and cost of leverage
3. OI Growth (30d) - Shows increasing/decreasing leverage trends
4. OI Volatility - Stability of leveraged positions

Methodology:
- Higher OI/Market Cap = More leveraged relative to spot market size
- Positive funding = Longs paying shorts (bullish leverage)
- Negative funding = Shorts paying longs (bearish leverage)
- High OI growth = Rapidly increasing leverage
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 10)


def load_market_cap_data():
    """Load latest market cap data"""
    df = pd.read_csv("data/raw/crypto_marketcap_latest.csv")
    df = df[["symbol", "name", "cmc_rank", "market_cap", "price", "volume_24h"]]
    df.columns = ["coin_symbol", "coin_name", "rank", "market_cap", "price", "volume_24h"]
    return df


def load_open_interest_data():
    """Load historical open interest data"""
    df = pd.read_csv("data/raw/historical_open_interest_top50_ALL_HISTORY_20251027_101817.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_funding_rates_data():
    """Load historical funding rates data"""
    df = pd.read_csv("data/raw/historical_funding_rates_top50_ALL_HISTORY_20251027_102154.csv")
    df["date"] = pd.to_datetime(df["date"])
    return df


def calculate_oi_metrics(oi_df, lookback_days=30):
    """
    Calculate Open Interest metrics for each coin
    
    Returns:
    - latest_oi: Most recent OI value (USD)
    - oi_growth_30d: % change in OI over 30 days
    - oi_volatility: Std dev of daily OI changes (30d)
    """
    metrics = []
    
    for symbol in oi_df["coin_symbol"].unique():
        symbol_data = oi_df[oi_df["coin_symbol"] == symbol].sort_values("date")
        
        if len(symbol_data) < 2:
            continue
            
        # Latest OI
        latest_oi = symbol_data["oi_close"].iloc[-1]
        
        # OI growth over lookback period
        if len(symbol_data) >= lookback_days:
            oi_30d_ago = symbol_data["oi_close"].iloc[-lookback_days]
            oi_growth_30d = ((latest_oi - oi_30d_ago) / oi_30d_ago) * 100
        else:
            oi_growth_30d = np.nan
        
        # OI volatility (std of daily % changes)
        symbol_data["oi_pct_change"] = symbol_data["oi_close"].pct_change() * 100
        oi_volatility = symbol_data["oi_pct_change"].tail(lookback_days).std()
        
        # Average OI over last 7 days for stability
        avg_oi_7d = symbol_data["oi_close"].tail(7).mean()
        
        metrics.append({
            "coin_symbol": symbol,
            "latest_oi": latest_oi,
            "avg_oi_7d": avg_oi_7d,
            "oi_growth_30d": oi_growth_30d,
            "oi_volatility_30d": oi_volatility,
            "oi_data_points": len(symbol_data)
        })
    
    return pd.DataFrame(metrics)


def calculate_funding_rate_metrics(fr_df, lookback_days=7):
    """
    Calculate Funding Rate metrics for each coin
    
    Returns:
    - avg_funding_7d: Average funding rate over last 7 days (%)
    - avg_funding_30d: Average funding rate over last 30 days (%)
    - funding_volatility: Std dev of funding rates
    """
    metrics = []
    
    for symbol in fr_df["coin_symbol"].unique():
        symbol_data = fr_df[fr_df["coin_symbol"] == symbol].sort_values("date")
        
        if len(symbol_data) < 2:
            continue
        
        # Recent funding rates
        avg_funding_7d = symbol_data["funding_rate_pct"].tail(7).mean()
        avg_funding_30d = symbol_data["funding_rate_pct"].tail(30).mean()
        
        # Funding rate volatility
        funding_volatility = symbol_data["funding_rate_pct"].tail(30).std()
        
        # Positive funding days (longs paying shorts)
        positive_pct = (symbol_data["funding_rate_pct"].tail(30) > 0).sum() / min(30, len(symbol_data.tail(30))) * 100
        
        metrics.append({
            "coin_symbol": symbol,
            "avg_funding_7d": avg_funding_7d,
            "avg_funding_30d": avg_funding_30d,
            "funding_volatility_30d": funding_volatility,
            "positive_funding_pct": positive_pct,
            "fr_data_points": len(symbol_data)
        })
    
    return pd.DataFrame(metrics)


def calculate_leverage_scores(df):
    """
    Calculate composite leverage scores
    
    Primary metric: OI/Market Cap ratio (%)
    Secondary: Funding rates, OI growth
    """
    # OI to Market Cap ratio (primary leverage indicator)
    df["oi_to_mcap_ratio"] = (df["latest_oi"] / df["market_cap"]) * 100
    
    # OI to Volume ratio (how much is locked vs traded)
    df["oi_to_volume_ratio"] = (df["avg_oi_7d"] / df["volume_24h"]) * 100
    
    # Composite leverage score (normalized)
    # Higher OI/MCap + Higher funding (absolute) = More leveraged
    df["leverage_score"] = (
        df["oi_to_mcap_ratio"].rank(pct=True) * 0.6 +  # Primary weight
        df["avg_funding_7d"].abs().rank(pct=True) * 0.2 +
        df["oi_growth_30d"].rank(pct=True) * 0.2
    ) * 100
    
    return df


def generate_summary_report(df):
    """Generate text summary of leverage analysis"""
    
    print("\n" + "="*80)
    print("CRYPTOCURRENCY LEVERAGE ANALYSIS - TOP 50 COINS")
    print("="*80)
    
    print(f"\nAnalysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Coins Analyzed: {len(df)}")
    print(f"Total Open Interest: ${df['latest_oi'].sum():,.0f}")
    print(f"Total Market Cap: ${df['market_cap'].sum():,.0f}")
    print(f"Overall OI/MCap Ratio: {(df['latest_oi'].sum() / df['market_cap'].sum() * 100):.2f}%")
    
    print("\n" + "="*80)
    print("KEY LEVERAGE METRICS - EXPLANATION")
    print("="*80)
    print("""
1. OI/Market Cap Ratio: Open Interest divided by Market Capitalization
   - Measures leverage intensity relative to spot market size
   - Higher ratio = More leveraged positions relative to market
   - Typical range: 0.5% - 5% (varies by coin)

2. Average Funding Rate (7d): Cost of holding leveraged positions
   - Positive = Longs paying shorts (bullish leverage demand)
   - Negative = Shorts paying longs (bearish leverage demand)
   - Higher absolute value = More extreme leverage demand

3. OI Growth (30d): Change in open interest over 30 days
   - Positive = Growing leverage
   - Negative = Declining leverage (deleveraging)

4. OI/Volume Ratio: Open interest divided by 24h trading volume
   - Measures how much is locked in positions vs actively traded
   - Higher = More locked leverage relative to liquidity
    """)
    
    print("\n" + "="*80)
    print("TOP 10 MOST LEVERAGED COINS (by OI/Market Cap Ratio)")
    print("="*80)
    
    top_10 = df.nlargest(10, "oi_to_mcap_ratio")[
        ["rank", "coin_name", "coin_symbol", "oi_to_mcap_ratio", "latest_oi", 
         "market_cap", "avg_funding_7d", "oi_growth_30d"]
    ]
    
    for idx, row in top_10.iterrows():
        print(f"\n{int(row['rank'])}. {row['coin_name']} ({row['coin_symbol']})")
        print(f"   OI/MCap Ratio:    {row['oi_to_mcap_ratio']:>8.2f}%")
        print(f"   Open Interest:    ${row['latest_oi']:>15,.0f}")
        print(f"   Market Cap:       ${row['market_cap']:>15,.0f}")
        print(f"   Avg Funding (7d): {row['avg_funding_7d']:>8.3f}%")
        print(f"   OI Growth (30d):  {row['oi_growth_30d']:>8.1f}%")
    
    print("\n" + "="*80)
    print("TOP 10 LEAST LEVERAGED COINS (by OI/Market Cap Ratio)")
    print("="*80)
    
    bottom_10 = df.nsmallest(10, "oi_to_mcap_ratio")[
        ["rank", "coin_name", "coin_symbol", "oi_to_mcap_ratio", "latest_oi", 
         "market_cap", "avg_funding_7d", "oi_growth_30d"]
    ]
    
    for idx, row in bottom_10.iterrows():
        print(f"\n{int(row['rank'])}. {row['coin_name']} ({row['coin_symbol']})")
        print(f"   OI/MCap Ratio:    {row['oi_to_mcap_ratio']:>8.2f}%")
        print(f"   Open Interest:    ${row['latest_oi']:>15,.0f}")
        print(f"   Market Cap:       ${row['market_cap']:>15,.0f}")
        print(f"   Avg Funding (7d): {row['avg_funding_7d']:>8.3f}%")
        print(f"   OI Growth (30d):  {row['oi_growth_30d']:>8.1f}%")
    
    print("\n" + "="*80)
    print("HIGHEST POSITIVE FUNDING RATES (Expensive Long Leverage)")
    print("="*80)
    
    high_funding = df.nlargest(10, "avg_funding_7d")[
        ["coin_name", "coin_symbol", "avg_funding_7d", "oi_to_mcap_ratio"]
    ]
    
    for idx, row in high_funding.iterrows():
        print(f"{row['coin_symbol']:<10} {row['coin_name']:<25} "
              f"Funding: {row['avg_funding_7d']:>7.3f}%  "
              f"OI/MCap: {row['oi_to_mcap_ratio']:>6.2f}%")
    
    print("\n" + "="*80)
    print("HIGHEST NEGATIVE FUNDING RATES (Expensive Short Leverage)")
    print("="*80)
    
    low_funding = df.nsmallest(10, "avg_funding_7d")[
        ["coin_name", "coin_symbol", "avg_funding_7d", "oi_to_mcap_ratio"]
    ]
    
    for idx, row in low_funding.iterrows():
        print(f"{row['coin_symbol']:<10} {row['coin_name']:<25} "
              f"Funding: {row['avg_funding_7d']:>7.3f}%  "
              f"OI/MCap: {row['oi_to_mcap_ratio']:>6.2f}%")
    
    print("\n" + "="*80)
    print("FASTEST GROWING LEVERAGE (OI Growth 30d)")
    print("="*80)
    
    growth = df.nlargest(10, "oi_growth_30d")[
        ["coin_name", "coin_symbol", "oi_growth_30d", "oi_to_mcap_ratio", "latest_oi"]
    ]
    
    for idx, row in growth.iterrows():
        print(f"{row['coin_symbol']:<10} {row['coin_name']:<25} "
              f"Growth: {row['oi_growth_30d']:>7.1f}%  "
              f"OI/MCap: {row['oi_to_mcap_ratio']:>6.2f}%")


def create_visualizations(df, output_dir="signals"):
    """Create visualization charts"""
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Create 2x2 subplot
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Top 20 by OI/MCap Ratio
    ax1 = axes[0, 0]
    top_20_oi = df.nlargest(20, "oi_to_mcap_ratio").sort_values("oi_to_mcap_ratio")
    colors = ['red' if x > 2 else 'orange' if x > 1 else 'green' 
              for x in top_20_oi["oi_to_mcap_ratio"]]
    ax1.barh(top_20_oi["coin_symbol"], top_20_oi["oi_to_mcap_ratio"], color=colors)
    ax1.set_xlabel("OI/Market Cap Ratio (%)")
    ax1.set_title("Top 20 Most Leveraged Coins (OI/MCap %)", fontsize=12, fontweight='bold')
    ax1.grid(axis='x', alpha=0.3)
    
    # 2. Funding Rates vs OI/MCap
    ax2 = axes[0, 1]
    scatter = ax2.scatter(df["oi_to_mcap_ratio"], df["avg_funding_7d"], 
                         s=df["latest_oi"]/1e6, alpha=0.6, c=df["rank"], 
                         cmap='viridis_r')
    ax2.set_xlabel("OI/Market Cap Ratio (%)")
    ax2.set_ylabel("Avg Funding Rate 7d (%)")
    ax2.set_title("Leverage vs Funding Rate (bubble size = OI)", 
                  fontsize=12, fontweight='bold')
    ax2.axhline(y=0, color='black', linestyle='--', alpha=0.3)
    ax2.grid(alpha=0.3)
    
    # Add labels for extreme points
    for _, row in df.nlargest(5, "oi_to_mcap_ratio").iterrows():
        ax2.annotate(row["coin_symbol"], 
                    (row["oi_to_mcap_ratio"], row["avg_funding_7d"]),
                    fontsize=8, alpha=0.7)
    
    # 3. OI Growth distribution
    ax3 = axes[1, 0]
    oi_growth_sorted = df.sort_values("oi_growth_30d", ascending=False).head(20)
    colors_growth = ['green' if x > 0 else 'red' for x in oi_growth_sorted["oi_growth_30d"]]
    ax3.barh(oi_growth_sorted["coin_symbol"], oi_growth_sorted["oi_growth_30d"], 
            color=colors_growth, alpha=0.7)
    ax3.set_xlabel("OI Growth 30d (%)")
    ax3.set_title("Top 20 OI Growth/Decline (30 days)", fontsize=12, fontweight='bold')
    ax3.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    ax3.grid(axis='x', alpha=0.3)
    
    # 4. Market Cap vs Open Interest
    ax4 = axes[1, 1]
    # Only show top 30 for clarity
    top_30 = df.nlargest(30, "market_cap")
    x = np.arange(len(top_30))
    width = 0.35
    
    # Normalize to billions for readability
    mcap_billions = top_30["market_cap"] / 1e9
    oi_billions = top_30["latest_oi"] / 1e9
    
    ax4.bar(x - width/2, mcap_billions, width, label='Market Cap', alpha=0.8, color='blue')
    ax4.bar(x + width/2, oi_billions, width, label='Open Interest', alpha=0.8, color='orange')
    ax4.set_ylabel("Value (Billions USD)")
    ax4.set_title("Market Cap vs Open Interest (Top 30)", fontsize=12, fontweight='bold')
    ax4.set_xticks(x)
    ax4.set_xticklabels(top_30["coin_symbol"], rotation=45, ha='right')
    ax4.legend()
    ax4.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    
    output_file = output_path / f"leverage_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n?? Visualization saved to: {output_file}")
    plt.close()
    
    # Create second chart: Detailed leverage metrics
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. OI/Volume ratio
    ax1 = axes[0, 0]
    top_20_vol = df.nlargest(20, "oi_to_volume_ratio").sort_values("oi_to_volume_ratio")
    ax1.barh(top_20_vol["coin_symbol"], top_20_vol["oi_to_volume_ratio"], 
            color='purple', alpha=0.7)
    ax1.set_xlabel("OI/Volume Ratio (%)")
    ax1.set_title("Highest OI/Volume Ratios (Locked Leverage)", 
                  fontsize=12, fontweight='bold')
    ax1.grid(axis='x', alpha=0.3)
    
    # 2. Funding rate volatility
    ax2 = axes[0, 1]
    top_20_fvol = df.nlargest(20, "funding_volatility_30d").sort_values("funding_volatility_30d")
    ax2.barh(top_20_fvol["coin_symbol"], top_20_fvol["funding_volatility_30d"], 
            color='red', alpha=0.7)
    ax2.set_xlabel("Funding Rate Volatility (Std Dev %)")
    ax2.set_title("Most Volatile Funding Rates (30d)", fontsize=12, fontweight='bold')
    ax2.grid(axis='x', alpha=0.3)
    
    # 3. OI volatility
    ax3 = axes[1, 0]
    top_20_oivol = df.nlargest(20, "oi_volatility_30d").sort_values("oi_volatility_30d")
    ax3.barh(top_20_oivol["coin_symbol"], top_20_oivol["oi_volatility_30d"], 
            color='orange', alpha=0.7)
    ax3.set_xlabel("OI Volatility (Std Dev %)")
    ax3.set_title("Most Volatile Open Interest (30d)", fontsize=12, fontweight='bold')
    ax3.grid(axis='x', alpha=0.3)
    
    # 4. Composite leverage score
    ax4 = axes[1, 1]
    top_20_score = df.nlargest(20, "leverage_score").sort_values("leverage_score")
    colors_score = plt.cm.RdYlGn_r(top_20_score["leverage_score"]/100)
    ax4.barh(top_20_score["coin_symbol"], top_20_score["leverage_score"], 
            color=colors_score, alpha=0.8)
    ax4.set_xlabel("Composite Leverage Score (0-100)")
    ax4.set_title("Highest Composite Leverage Scores", fontsize=12, fontweight='bold')
    ax4.grid(axis='x', alpha=0.3)
    
    plt.tight_layout()
    
    output_file2 = output_path / f"leverage_metrics_detailed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    plt.savefig(output_file2, dpi=300, bbox_inches='tight')
    print(f"?? Detailed metrics saved to: {output_file2}")
    plt.close()


def export_results(df, output_dir="signals"):
    """Export full results to CSV"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Sort by OI/MCap ratio
    df_sorted = df.sort_values("oi_to_mcap_ratio", ascending=False)
    
    # Select key columns for export
    export_cols = [
        "rank", "coin_name", "coin_symbol",
        "oi_to_mcap_ratio", "leverage_score",
        "latest_oi", "market_cap", "volume_24h",
        "avg_funding_7d", "avg_funding_30d",
        "oi_growth_30d", "oi_volatility_30d",
        "oi_to_volume_ratio", "funding_volatility_30d",
        "positive_funding_pct"
    ]
    
    df_export = df_sorted[export_cols].copy()
    
    # Round for readability
    df_export["oi_to_mcap_ratio"] = df_export["oi_to_mcap_ratio"].round(2)
    df_export["leverage_score"] = df_export["leverage_score"].round(1)
    df_export["avg_funding_7d"] = df_export["avg_funding_7d"].round(4)
    df_export["avg_funding_30d"] = df_export["avg_funding_30d"].round(4)
    df_export["oi_growth_30d"] = df_export["oi_growth_30d"].round(2)
    df_export["oi_volatility_30d"] = df_export["oi_volatility_30d"].round(2)
    df_export["oi_to_volume_ratio"] = df_export["oi_to_volume_ratio"].round(2)
    df_export["funding_volatility_30d"] = df_export["funding_volatility_30d"].round(2)
    df_export["positive_funding_pct"] = df_export["positive_funding_pct"].round(1)
    
    output_file = output_path / f"leverage_ratios_top50_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df_export.to_csv(output_file, index=False)
    print(f"\n?? Full results exported to: {output_file}")
    
    return output_file


def main():
    """Main execution function"""
    
    print("\n" + "="*80)
    print("CRYPTOCURRENCY LEVERAGE ANALYSIS")
    print("="*80)
    print("\nLoading data...")
    
    # Load data
    mcap_df = load_market_cap_data()
    oi_df = load_open_interest_data()
    fr_df = load_funding_rates_data()
    
    print(f"? Market Cap: {len(mcap_df)} coins")
    print(f"? Open Interest: {len(oi_df)} records for {oi_df['coin_symbol'].nunique()} coins")
    print(f"? Funding Rates: {len(fr_df)} records for {fr_df['coin_symbol'].nunique()} coins")
    
    print("\nCalculating metrics...")
    
    # Calculate OI metrics
    oi_metrics = calculate_oi_metrics(oi_df, lookback_days=30)
    print(f"? OI metrics calculated for {len(oi_metrics)} coins")
    
    # Calculate funding rate metrics
    fr_metrics = calculate_funding_rate_metrics(fr_df, lookback_days=7)
    print(f"? Funding rate metrics calculated for {len(fr_metrics)} coins")
    
    # Merge all data
    df = mcap_df.merge(oi_metrics, on="coin_symbol", how="inner")
    df = df.merge(fr_metrics, on="coin_symbol", how="inner")
    
    print(f"? Combined data: {len(df)} coins with complete data")
    
    # Calculate leverage scores
    df = calculate_leverage_scores(df)
    print(f"? Leverage scores calculated")
    
    # Generate reports
    generate_summary_report(df)
    
    # Create visualizations
    print("\n" + "="*80)
    print("Generating visualizations...")
    create_visualizations(df)
    
    # Export results
    print("\n" + "="*80)
    print("Exporting results...")
    output_file = export_results(df)
    
    print("\n" + "="*80)
    print("? ANALYSIS COMPLETE")
    print("="*80)
    print(f"\nResults saved to: {output_file}")
    print("\nSUMMARY:")
    print(f"  ? Most Leveraged: {df.nlargest(1, 'oi_to_mcap_ratio')['coin_name'].values[0]} "
          f"({df.nlargest(1, 'oi_to_mcap_ratio')['oi_to_mcap_ratio'].values[0]:.2f}% OI/MCap)")
    print(f"  ? Least Leveraged: {df.nsmallest(1, 'oi_to_mcap_ratio')['coin_name'].values[0]} "
          f"({df.nsmallest(1, 'oi_to_mcap_ratio')['oi_to_mcap_ratio'].values[0]:.2f}% OI/MCap)")
    print(f"  ? Average OI/MCap: {df['oi_to_mcap_ratio'].mean():.2f}%")
    print(f"  ? Median OI/MCap: {df['oi_to_mcap_ratio'].median():.2f}%")
    

if __name__ == "__main__":
    main()
