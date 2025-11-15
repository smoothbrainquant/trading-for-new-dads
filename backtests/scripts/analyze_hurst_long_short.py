#!/usr/bin/env python3
"""
Hurst Exponent Long/Short Strategy Analysis

Analyzes performance of:
- Long High HE (trending coins)
- Short Low HE (fade mean-reverting coins)
- Combined long/short portfolio

Breaks down by market direction.
"""

import pandas as pd
import numpy as np
import sys
import os

def main():
    print("=" * 80)
    print("HURST EXPONENT LONG/SHORT STRATEGY")
    print("=" * 80)
    
    # Load the detailed data from previous analysis
    data_file = 'backtests/results/hurst_direction_top100_2023_detailed_data.csv'
    
    if not os.path.exists(data_file):
        print(f"\nERROR: Data file not found: {data_file}")
        print("Please run analyze_hurst_by_direction.py first.")
        return
    
    print(f"\nLoading data from: {data_file}")
    df = pd.read_csv(data_file)
    df['date'] = pd.to_datetime(df['date'])
    
    print(f"Loaded {len(df):,} observations")
    print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
    
    # Calculate returns for each side
    print("\n" + "-" * 80)
    print("Calculating Strategy Returns...")
    
    # Long High HE returns
    high_he_data = df[df['hurst_class'] == 'High HE'].copy()
    long_returns = high_he_data.groupby('date')['forward_return'].mean()
    
    # Short Low HE returns (inverted)
    low_he_data = df[df['hurst_class'] == 'Low HE'].copy()
    short_returns = -low_he_data.groupby('date')['forward_return'].mean()  # Negative for short
    
    # Combine into long/short portfolio (50/50 allocation) - use merge for proper alignment
    combined_df = pd.DataFrame({
        'date': long_returns.index,
        'long_return': long_returns.values
    })
    
    short_df = pd.DataFrame({
        'date': short_returns.index,
        'short_return': short_returns.values
    })
    
    combined_df = combined_df.merge(short_df, on='date', how='inner')
    combined_df['long_short_return'] = (combined_df['long_return'] + combined_df['short_return']) / 2
    
    # Merge with direction classification
    # Get direction for each date from original data
    direction_by_date = df.groupby('date')['direction_class'].first()
    combined_df = combined_df.merge(
        direction_by_date.reset_index(),
        on='date',
        how='left'
    )
    
    # Overall statistics
    print("\n" + "=" * 80)
    print("OVERALL PERFORMANCE (2023-2025)")
    print("=" * 80)
    
    def calc_metrics(returns, label, periods_per_year=252/5):
        """Calculate performance metrics"""
        mean_ret = returns.mean()
        std_ret = returns.std()
        ann_ret = (1 + mean_ret) ** periods_per_year - 1
        ann_vol = std_ret * np.sqrt(periods_per_year)
        sharpe = (mean_ret / std_ret) * np.sqrt(periods_per_year) if std_ret > 0 else 0
        win_rate = (returns > 0).sum() / len(returns)
        
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_dd = drawdown.min()
        
        print(f"\n{label}:")
        print(f"  Mean 5d Return:     {mean_ret:>9.2%}")
        print(f"  Annualized Return:  {ann_ret:>9.1%}")
        print(f"  Annualized Vol:     {ann_vol:>9.1%}")
        print(f"  Sharpe Ratio:       {sharpe:>9.2f}")
        print(f"  Win Rate:           {win_rate:>9.1%}")
        print(f"  Max Drawdown:       {max_dd:>9.1%}")
        print(f"  Observations:       {len(returns):>9,}")
        
        return {
            'mean_return': mean_ret,
            'annualized_return': ann_ret,
            'annualized_vol': ann_vol,
            'sharpe_ratio': sharpe,
            'win_rate': win_rate,
            'max_drawdown': max_dd,
            'count': len(returns)
        }
    
    # Overall metrics
    long_metrics = calc_metrics(combined_df['long_return'], "LONG High HE Only")
    short_metrics = calc_metrics(combined_df['short_return'], "SHORT Low HE Only")
    ls_metrics = calc_metrics(combined_df['long_short_return'], "LONG/SHORT Combined (50/50)")
    
    # Performance by direction
    print("\n" + "=" * 80)
    print("PERFORMANCE BY MARKET DIRECTION")
    print("=" * 80)
    
    for direction in ['Up', 'Down']:
        print(f"\n{direction.upper()} MARKETS:")
        print("-" * 80)
        
        dir_data = combined_df[combined_df['direction_class'] == direction]
        
        if len(dir_data) > 0:
            calc_metrics(dir_data['long_return'], f"  Long High HE")
            calc_metrics(dir_data['short_return'], f"  Short Low HE")
            calc_metrics(dir_data['long_short_return'], f"  Long/Short Combined")
    
    # Summary table
    print("\n" + "=" * 80)
    print("SUMMARY TABLE: LONG/SHORT VS COMPONENTS")
    print("=" * 80)
    
    print(f"\n{'Strategy':<25} {'Ann Return':>12} {'Sharpe':>8} {'Win Rate':>10} {'Max DD':>10}")
    print("-" * 75)
    
    strategies = [
        ('Long High HE Only', long_metrics),
        ('Short Low HE Only', short_metrics),
        ('Long/Short (50/50)', ls_metrics)
    ]
    
    for name, metrics in strategies:
        print(f"{name:<25} {metrics['annualized_return']:>11.1%} {metrics['sharpe_ratio']:>8.2f} "
              f"{metrics['win_rate']:>9.1%} {metrics['max_drawdown']:>9.1%}")
    
    # Breakdown by direction - summary table
    print("\n" + "=" * 80)
    print("DIRECTION BREAKDOWN: LONG/SHORT RETURNS")
    print("=" * 80)
    
    summary_data = []
    
    for direction in ['Up', 'Down']:
        dir_data = combined_df[combined_df['direction_class'] == direction]
        
        if len(dir_data) > 0:
            long_ret = (1 + dir_data['long_return'].mean()) ** (252/5) - 1
            short_ret = (1 + dir_data['short_return'].mean()) ** (252/5) - 1
            ls_ret = (1 + dir_data['long_short_return'].mean()) ** (252/5) - 1
            
            summary_data.append({
                'direction': direction,
                'long_high_he': long_ret,
                'short_low_he': short_ret,
                'long_short': ls_ret,
                'observations': len(dir_data)
            })
    
    summary_df = pd.DataFrame(summary_data)
    
    print(f"\n{'Direction':<12} {'Long High HE':>14} {'Short Low HE':>14} {'Long/Short':>14} {'Obs':>8}")
    print("-" * 72)
    
    for _, row in summary_df.iterrows():
        print(f"{row['direction']:<12} {row['long_high_he']:>13.1%} {row['short_low_he']:>13.1%} "
              f"{row['long_short']:>13.1%} {row['observations']:>8,}")
    
    # Calculate spread
    print("\n" + "=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)
    
    print(f"\n1. Overall Long/Short Performance:")
    print(f"   Annualized Return: {ls_metrics['annualized_return']:.1%}")
    print(f"   Sharpe Ratio: {ls_metrics['sharpe_ratio']:.2f}")
    print(f"   Win Rate: {ls_metrics['win_rate']:.1%}")
    
    print(f"\n2. Component Contribution:")
    print(f"   Long High HE:  {long_metrics['annualized_return']:>7.1%} (Sharpe: {long_metrics['sharpe_ratio']:.2f})")
    print(f"   Short Low HE:  {short_metrics['annualized_return']:>7.1%} (Sharpe: {short_metrics['sharpe_ratio']:.2f})")
    print(f"   Combined L/S:  {ls_metrics['annualized_return']:>7.1%} (Sharpe: {ls_metrics['sharpe_ratio']:.2f})")
    
    long_short_boost = ls_metrics['annualized_return'] - long_metrics['annualized_return']
    print(f"\n   Short adds: {long_short_boost:+.1%} to returns")
    
    print(f"\n3. Best Regime for Long/Short:")
    up_ls = summary_df[summary_df['direction'] == 'Up']['long_short'].values[0]
    down_ls = summary_df[summary_df['direction'] == 'Down']['long_short'].values[0]
    
    if down_ls > up_ls:
        print(f"   DOWN markets: {down_ls:.1%} annualized ⭐")
        print(f"   UP markets:   {up_ls:.1%} annualized")
        print(f"   → Long/Short excels in DOWN markets (+{down_ls - up_ls:.1%})")
    else:
        print(f"   UP markets:   {up_ls:.1%} annualized ⭐")
        print(f"   DOWN markets: {down_ls:.1%} annualized")
        print(f"   → Long/Short excels in UP markets (+{up_ls - down_ls:.1%})")
    
    print(f"\n4. Why Long/Short Works:")
    print(f"   - Captures High HE upside: {long_metrics['annualized_return']:.1%}")
    print(f"   - Profits from Low HE decline: {short_metrics['annualized_return']:.1%}")
    print(f"   - Market neutral: reduces market beta")
    print(f"   - Diversified alpha: two sources of return")
    
    # Save results
    print("\n" + "-" * 80)
    print("Saving results...")
    
    output_dir = 'backtests/results'
    
    # Save time series
    ts_file = f'{output_dir}/hurst_long_short_timeseries.csv'
    combined_df.to_csv(ts_file, index=False)
    print(f"✓ Saved time series to: {ts_file}")
    
    # Save summary
    summary_file = f'{output_dir}/hurst_long_short_summary.csv'
    summary_df.to_csv(summary_file, index=False)
    print(f"✓ Saved summary to: {summary_file}")
    
    # Save metrics
    metrics_data = pd.DataFrame([
        {'strategy': 'Long High HE', **long_metrics},
        {'strategy': 'Short Low HE', **short_metrics},
        {'strategy': 'Long/Short 50/50', **ls_metrics}
    ])
    metrics_file = f'{output_dir}/hurst_long_short_metrics.csv'
    metrics_data.to_csv(metrics_file, index=False)
    print(f"✓ Saved metrics to: {metrics_file}")
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    
    # Create visualization
    print("\n" + "-" * 80)
    print("Creating visualizations...")
    
    try:
        import matplotlib.pyplot as plt
        
        # Create figure with subplots
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Long/Short Strategy Performance (2023-2025)\nLong High HE + Short Low HE', 
                     fontsize=16, fontweight='bold')
        
        # 1. Cumulative returns
        ax1 = axes[0, 0]
        cum_long = (1 + combined_df['long_return']).cumprod()
        cum_short = (1 + combined_df['short_return']).cumprod()
        cum_ls = (1 + combined_df['long_short_return']).cumprod()
        
        ax1.plot(combined_df['date'], cum_long, label='Long High HE', linewidth=2, alpha=0.8)
        ax1.plot(combined_df['date'], cum_short, label='Short Low HE', linewidth=2, alpha=0.8)
        ax1.plot(combined_df['date'], cum_ls, label='Long/Short 50/50', linewidth=2.5, alpha=0.9, color='purple')
        ax1.set_ylabel('Cumulative Return', fontweight='bold')
        ax1.set_title('Cumulative Returns Over Time', fontweight='bold')
        ax1.legend(loc='best')
        ax1.grid(alpha=0.3)
        ax1.axhline(y=1, color='black', linestyle='--', linewidth=0.5)
        
        # 2. Returns by direction
        ax2 = axes[0, 1]
        direction_data = []
        for direction in ['Up', 'Down']:
            dir_data = combined_df[combined_df['direction_class'] == direction]
            if len(dir_data) > 0:
                direction_data.append({
                    'Direction': direction,
                    'Long': (1 + dir_data['long_return'].mean()) ** (252/5) - 1,
                    'Short': (1 + dir_data['short_return'].mean()) ** (252/5) - 1,
                    'L/S': (1 + dir_data['long_short_return'].mean()) ** (252/5) - 1
                })
        
        dir_df = pd.DataFrame(direction_data)
        x = np.arange(len(dir_df))
        width = 0.25
        
        ax2.bar(x - width, dir_df['Long'], width, label='Long High HE', alpha=0.8)
        ax2.bar(x, dir_df['Short'], width, label='Short Low HE', alpha=0.8)
        ax2.bar(x + width, dir_df['L/S'], width, label='Long/Short', alpha=0.8, color='purple')
        
        ax2.set_xticks(x)
        ax2.set_xticklabels(dir_df['Direction'])
        ax2.set_ylabel('Annualized Return (%)', fontweight='bold')
        ax2.set_title('Returns by Market Direction', fontweight='bold')
        ax2.legend()
        ax2.grid(axis='y', alpha=0.3)
        ax2.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
        
        # Format as percentages
        for container in ax2.containers:
            ax2.bar_label(container, fmt='%.0f%%')
        
        # 3. Rolling Sharpe ratio
        ax3 = axes[1, 0]
        window = 50  # 50 observations (~250 days)
        
        rolling_sharpe_ls = (combined_df['long_short_return'].rolling(window).mean() / 
                            combined_df['long_short_return'].rolling(window).std() * 
                            np.sqrt(252/5))
        
        ax3.plot(combined_df['date'], rolling_sharpe_ls, linewidth=2, color='purple', alpha=0.8)
        ax3.set_ylabel('Sharpe Ratio', fontweight='bold')
        ax3.set_title(f'Rolling {window}-Period Sharpe (Long/Short)', fontweight='bold')
        ax3.axhline(y=0, color='black', linestyle='--', linewidth=0.5)
        ax3.axhline(y=1, color='green', linestyle='--', linewidth=0.5, alpha=0.5, label='Sharpe = 1')
        ax3.grid(alpha=0.3)
        ax3.legend()
        
        # 4. Drawdown
        ax4 = axes[1, 1]
        running_max = cum_ls.expanding().max()
        drawdown = (cum_ls - running_max) / running_max
        
        ax4.fill_between(combined_df['date'], 0, drawdown, alpha=0.5, color='red')
        ax4.plot(combined_df['date'], drawdown, linewidth=1.5, color='darkred')
        ax4.set_ylabel('Drawdown', fontweight='bold')
        ax4.set_title('Long/Short Strategy Drawdown', fontweight='bold')
        ax4.grid(alpha=0.3)
        ax4.set_ylim([drawdown.min() * 1.1, 0.05])
        
        plt.tight_layout()
        chart_file = f'{output_dir}/hurst_long_short_performance.png'
        plt.savefig(chart_file, dpi=300, bbox_inches='tight')
        print(f"✓ Saved chart to: {chart_file}")
        
    except Exception as e:
        print(f"Warning: Could not create visualization: {e}")
    
    print("\n" + "=" * 80)
    print("DONE!")
    print("=" * 80)


if __name__ == '__main__':
    main()
