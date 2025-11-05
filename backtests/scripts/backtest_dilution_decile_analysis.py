#!/usr/bin/env python3
"""
Dilution Factor Decile Analysis Backtest

This script runs comprehensive dilution factor backtests with:
1. Individual top 10 and bottom 10 coin performance
2. Decile portfolio performance (10 portfolios sorted by dilution)
3. Detailed comparison of extreme deciles

Strategy:
- Universe: Top 150 coins by market cap with dilution data
- Sort by dilution velocity (12-month rolling)
- Create 10 equal-weighted decile portfolios
- Monthly rebalancing
- Compare performance across deciles
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os


def load_historical_price_data():
    """Load historical price data."""
    possible_paths = [
        'data/raw/combined_coinbase_coinmarketcap_daily.csv',
        '/workspace/data/raw/combined_coinbase_coinmarketcap_daily.csv',
        'data/raw/coinbase_spot_daily_data_20200101_20251024_110130.csv',
        '/workspace/data/raw/coinbase_spot_daily_data_20200101_20251024_110130.csv'
    ]
    
    df = None
    for path in possible_paths:
        if os.path.exists(path):
            print(f"Loading price data from: {path}")
            df = pd.read_csv(path)
            break
    
    if df is None:
        raise FileNotFoundError("Could not find price data file")
    
    df['date'] = pd.to_datetime(df['date'])
    df = df[df['date'] >= '2021-01-01'].copy()
    
    # Calculate returns
    df = df.sort_values(['base', 'date'])
    df['return'] = df.groupby('base')['close'].pct_change()
    df['return_next'] = df.groupby('base')['return'].shift(-1)
    
    print(f"Loaded price data: {len(df)} records, {df['base'].nunique()} coins")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    
    return df


def load_historical_dilution_snapshots():
    """Load historical dilution snapshots."""
    hist_file = 'crypto_dilution_historical_2021_2025.csv'
    if not os.path.exists(hist_file):
        hist_file = '/workspace/crypto_dilution_historical_2021_2025.csv'
    
    df = pd.read_csv(hist_file)
    df['date'] = pd.to_datetime(df['date'])
    
    print(f"Loaded historical dilution: {len(df)} records, {df['Symbol'].nunique()} coins")
    
    return df


def calculate_rolling_dilution_signal(historical_dilution_df, lookback_months=12):
    """Calculate rolling dilution velocity signals."""
    signals = []
    rebalance_dates = sorted(historical_dilution_df['date'].unique())
    
    for rebal_date in rebalance_dates:
        lookback_start = rebal_date - pd.DateOffset(months=lookback_months)
        
        window_data = historical_dilution_df[
            (historical_dilution_df['date'] >= lookback_start) &
            (historical_dilution_df['date'] <= rebal_date)
        ].copy()
        
        for symbol in window_data['Symbol'].unique():
            coin_data = window_data[window_data['Symbol'] == symbol].sort_values('date')
            
            if len(coin_data) < 2:
                continue
            
            first = coin_data.iloc[0]
            last = coin_data.iloc[-1]
            
            days_elapsed = (last['date'] - first['date']).days
            if days_elapsed == 0:
                continue
            
            years_elapsed = days_elapsed / 365.25
            circ_pct_change = last['circulating_pct'] - first['circulating_pct']
            dilution_velocity = circ_pct_change / years_elapsed if years_elapsed > 0 else 0
            
            signals.append({
                'date': rebal_date,
                'symbol': symbol,
                'dilution_velocity': dilution_velocity,
                'market_cap': last['Market Cap'],
                'rank': last['Rank'],
                'price': last['Price'],
                'circulating_pct': last['circulating_pct']
            })
    
    signals_df = pd.DataFrame(signals)
    print(f"Calculated rolling dilution signals: {len(signals_df)} records")
    
    return signals_df


def backtest_decile_portfolios(signals_df, price_df, n_deciles=10):
    """
    Backtest portfolios sorted into deciles by dilution velocity.
    
    Returns:
        dict: Results for each decile including individual coin performance
    """
    rebalance_dates = sorted(signals_df['date'].unique())
    
    # Initialize results storage
    decile_results = {i: {
        'portfolio_values': [],
        'holdings': [],
        'returns': []
    } for i in range(1, n_deciles + 1)}
    
    # Track individual coin performance across all periods
    individual_coin_returns = []
    
    # Initial portfolio values
    decile_portfolio_values = {i: 1.0 for i in range(1, n_deciles + 1)}
    
    for idx, rebal_date in enumerate(rebalance_dates):
        print(f"Rebalancing {idx+1}/{len(rebalance_dates)}: {rebal_date.date()}")
        
        # Get signals for this date
        date_signals = signals_df[signals_df['date'] == rebal_date].copy()
        
        # Filter to top 150 by market cap and valid dilution
        date_signals = date_signals[date_signals['dilution_velocity'].notna()]
        date_signals = date_signals.nsmallest(150, 'rank')
        
        # Filter to coins with price data
        available_coins = price_df['base'].unique()
        date_signals = date_signals[date_signals['symbol'].isin(available_coins)]
        
        if len(date_signals) < 20:
            print(f"  Warning: Only {len(date_signals)} coins available, skipping")
            continue
        
        # Sort by dilution velocity and assign to deciles
        date_signals = date_signals.sort_values('dilution_velocity').reset_index(drop=True)
        
        # Use rank-based assignment to handle duplicates
        # This ensures we always get deciles even with duplicate values
        date_signals['rank_pct'] = date_signals.index / (len(date_signals) - 1) if len(date_signals) > 1 else 0.5
        date_signals['decile'] = (date_signals['rank_pct'] * n_deciles).astype(int) + 1
        date_signals['decile'] = date_signals['decile'].clip(1, n_deciles)
        
        # Determine holding period
        if idx < len(rebalance_dates) - 1:
            next_rebal = rebalance_dates[idx + 1]
        else:
            next_rebal = price_df['date'].max()
        
        # Get returns for holding period
        holding_period_returns = price_df[
            (price_df['date'] > rebal_date) &
            (price_df['date'] <= next_rebal)
        ].copy()
        
        # Calculate returns for each decile portfolio
        for decile in range(1, n_deciles + 1):
            decile_coins = date_signals[date_signals['decile'] == decile]
            
            if len(decile_coins) == 0:
                continue
            
            # Store holdings for this period
            for _, coin in decile_coins.iterrows():
                decile_results[decile]['holdings'].append({
                    'date': rebal_date,
                    'symbol': coin['symbol'],
                    'dilution_velocity': coin['dilution_velocity'],
                    'rank': coin['rank']
                })
            
            # Calculate equal-weighted portfolio returns for each day
            for date in sorted(holding_period_returns['date'].unique()):
                daily_data = holding_period_returns[holding_period_returns['date'] == date]
                
                # Get returns for coins in this decile
                decile_returns = []
                for symbol in decile_coins['symbol'].values:
                    coin_return = daily_data[daily_data['base'] == symbol]['return'].values
                    if len(coin_return) > 0 and not np.isnan(coin_return[0]):
                        decile_returns.append(coin_return[0])
                
                # Equal weighted average
                if len(decile_returns) > 0:
                    portfolio_return = np.mean(decile_returns)
                    decile_portfolio_values[decile] *= (1 + portfolio_return)
                    
                    decile_results[decile]['portfolio_values'].append({
                        'date': date,
                        'portfolio_value': decile_portfolio_values[decile],
                        'return': portfolio_return,
                        'n_coins': len(decile_returns)
                    })
                    decile_results[decile]['returns'].append(portfolio_return)
        
        # Track individual coin returns for this rebalance period
        for _, coin in date_signals.iterrows():
            coin_symbol = coin['symbol']
            coin_decile = coin['decile']
            
            # Calculate total return for this coin over the holding period
            coin_period_data = holding_period_returns[
                holding_period_returns['base'] == coin_symbol
            ]['return'].values
            
            if len(coin_period_data) > 0:
                # Cumulative return over period
                period_return = (1 + pd.Series(coin_period_data)).prod() - 1
                
                individual_coin_returns.append({
                    'rebalance_date': rebal_date,
                    'symbol': coin_symbol,
                    'decile': coin_decile,
                    'dilution_velocity': coin['dilution_velocity'],
                    'rank': coin['rank'],
                    'period_return': period_return,
                    'n_days': len(coin_period_data)
                })
    
    # Convert to DataFrames
    for decile in range(1, n_deciles + 1):
        decile_results[decile]['portfolio_values'] = pd.DataFrame(
            decile_results[decile]['portfolio_values']
        )
        decile_results[decile]['holdings'] = pd.DataFrame(
            decile_results[decile]['holdings']
        )
    
    individual_returns_df = pd.DataFrame(individual_coin_returns)
    
    return decile_results, individual_returns_df


def calculate_decile_metrics(decile_results):
    """Calculate performance metrics for each decile."""
    metrics = {}
    
    for decile, results in decile_results.items():
        portfolio_df = results['portfolio_values']
        
        if len(portfolio_df) == 0:
            continue
        
        # Total return
        total_return = (portfolio_df['portfolio_value'].iloc[-1] / 
                       portfolio_df['portfolio_value'].iloc[0] - 1) * 100
        
        # Annualized return
        days = (portfolio_df['date'].max() - portfolio_df['date'].min()).days
        years = days / 365.25
        annualized_return = ((portfolio_df['portfolio_value'].iloc[-1] / 
                             portfolio_df['portfolio_value'].iloc[0]) ** (1/years) - 1) * 100
        
        # Volatility
        returns = pd.Series(results['returns'])
        volatility = returns.std() * np.sqrt(365) * 100
        
        # Sharpe ratio
        sharpe = annualized_return / volatility if volatility > 0 else 0
        
        # Max drawdown
        cumulative = portfolio_df['portfolio_value']
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max * 100
        max_drawdown = drawdown.min()
        
        metrics[decile] = {
            'decile': decile,
            'total_return_pct': total_return,
            'annualized_return_pct': annualized_return,
            'volatility_pct': volatility,
            'sharpe_ratio': sharpe,
            'max_drawdown_pct': max_drawdown,
            'n_days': len(portfolio_df)
        }
    
    return pd.DataFrame(list(metrics.values()))


def analyze_top_bottom_names(individual_returns_df, n=10):
    """
    Analyze the top and bottom N individual coins by average returns.
    
    Returns:
        tuple: (top_names_df, bottom_names_df)
    """
    # Calculate average return per coin across all rebalance periods
    coin_avg_returns = individual_returns_df.groupby('symbol').agg({
        'period_return': 'mean',
        'dilution_velocity': 'mean',
        'rank': 'mean',
        'decile': lambda x: x.mode().iloc[0] if len(x) > 0 else np.nan,
        'rebalance_date': 'count'
    }).reset_index()
    
    coin_avg_returns.columns = ['symbol', 'avg_period_return', 'avg_dilution_velocity', 
                                 'avg_rank', 'typical_decile', 'n_periods']
    
    # Sort by return
    coin_avg_returns = coin_avg_returns.sort_values('avg_period_return', ascending=False)
    
    # Get top and bottom N
    top_n = coin_avg_returns.head(n).copy()
    bottom_n = coin_avg_returns.tail(n).copy()
    
    top_n['category'] = 'Top ' + str(n)
    bottom_n['category'] = 'Bottom ' + str(n)
    
    return top_n, bottom_n


def plot_decile_comparison(decile_results, metrics_df, output_file='dilution_decile_comparison.png'):
    """Plot comprehensive decile comparison."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # Plot 1: Cumulative returns by decile
    ax1 = axes[0, 0]
    for decile in sorted(decile_results.keys()):
        portfolio_df = decile_results[decile]['portfolio_values']
        if len(portfolio_df) > 0:
            label = f'D{decile} (Low)' if decile == 1 else f'D{decile} (High)' if decile == 10 else f'D{decile}'
            ax1.plot(portfolio_df['date'], portfolio_df['portfolio_value'], 
                    label=label, linewidth=2 if decile in [1, 10] else 1,
                    alpha=1.0 if decile in [1, 10] else 0.5)
    
    ax1.set_ylabel('Portfolio Value ($)', fontsize=11)
    ax1.set_title('Decile Portfolio Performance (Equal-Weighted)', fontsize=12, fontweight='bold')
    ax1.legend(fontsize=9, ncol=2)
    ax1.grid(True, alpha=0.3)
    
    # Plot 2: Annualized returns by decile
    ax2 = axes[0, 1]
    colors = ['darkgreen' if i == 1 else 'darkred' if i == 10 else 'gray' 
              for i in metrics_df['decile']]
    bars = ax2.bar(metrics_df['decile'], metrics_df['annualized_return_pct'], color=colors, alpha=0.7)
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax2.set_xlabel('Decile (1=Low Dilution, 10=High Dilution)', fontsize=11)
    ax2.set_ylabel('Annualized Return (%)', fontsize=11)
    ax2.set_title('Annualized Returns by Dilution Decile', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%', ha='center', va='bottom' if height > 0 else 'top', fontsize=9)
    
    # Plot 3: Sharpe ratios by decile
    ax3 = axes[1, 0]
    colors = ['darkgreen' if i == 1 else 'darkred' if i == 10 else 'gray' 
              for i in metrics_df['decile']]
    bars = ax3.bar(metrics_df['decile'], metrics_df['sharpe_ratio'], color=colors, alpha=0.7)
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=1)
    ax3.set_xlabel('Decile (1=Low Dilution, 10=High Dilution)', fontsize=11)
    ax3.set_ylabel('Sharpe Ratio', fontsize=11)
    ax3.set_title('Sharpe Ratio by Dilution Decile', fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')
    
    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.2f}', ha='center', va='bottom' if height > 0 else 'top', fontsize=9)
    
    # Plot 4: Max drawdown by decile
    ax4 = axes[1, 1]
    colors = ['darkgreen' if i == 1 else 'darkred' if i == 10 else 'gray' 
              for i in metrics_df['decile']]
    bars = ax4.bar(metrics_df['decile'], metrics_df['max_drawdown_pct'], color=colors, alpha=0.7)
    ax4.set_xlabel('Decile (1=Low Dilution, 10=High Dilution)', fontsize=11)
    ax4.set_ylabel('Max Drawdown (%)', fontsize=11)
    ax4.set_title('Maximum Drawdown by Dilution Decile', fontsize=12, fontweight='bold')
    ax4.grid(True, alpha=0.3, axis='y')
    
    # Add value labels
    for bar in bars:
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                f'{height:.1f}%', ha='center', va='top', fontsize=9)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"? Saved: {output_file}")
    plt.close()


def plot_top_bottom_names(top_names, bottom_names, output_file='dilution_top_bottom_names.png'):
    """Plot top and bottom individual coin performance."""
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    
    # Plot 1: Top performers
    ax1 = axes[0]
    top_sorted = top_names.sort_values('avg_period_return', ascending=True)
    colors = plt.cm.Greens(np.linspace(0.4, 0.8, len(top_sorted)))
    bars = ax1.barh(range(len(top_sorted)), top_sorted['avg_period_return'] * 100, color=colors)
    ax1.set_yticks(range(len(top_sorted)))
    ax1.set_yticklabels(top_sorted['symbol'])
    ax1.set_xlabel('Average Period Return (%)', fontsize=11)
    ax1.set_title(f'Top {len(top_names)} Performing Coins', fontsize=12, fontweight='bold')
    ax1.grid(True, alpha=0.3, axis='x')
    
    # Add dilution velocity annotations
    for i, (idx, row) in enumerate(top_sorted.iterrows()):
        ax1.text(row['avg_period_return'] * 100, i, 
                f" (D{int(row['typical_decile'])}, {row['avg_dilution_velocity']:.1f}%/yr)",
                va='center', fontsize=8, color='darkgreen')
    
    # Plot 2: Bottom performers
    ax2 = axes[1]
    bottom_sorted = bottom_names.sort_values('avg_period_return', ascending=True)
    colors = plt.cm.Reds(np.linspace(0.4, 0.8, len(bottom_sorted)))
    bars = ax2.barh(range(len(bottom_sorted)), bottom_sorted['avg_period_return'] * 100, color=colors)
    ax2.set_yticks(range(len(bottom_sorted)))
    ax2.set_yticklabels(bottom_sorted['symbol'])
    ax2.set_xlabel('Average Period Return (%)', fontsize=11)
    ax2.set_title(f'Bottom {len(bottom_names)} Performing Coins', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='x')
    
    # Add dilution velocity annotations
    for i, (idx, row) in enumerate(bottom_sorted.iterrows()):
        ax2.text(row['avg_period_return'] * 100, i,
                f" (D{int(row['typical_decile'])}, {row['avg_dilution_velocity']:.1f}%/yr)",
                va='center', fontsize=8, color='darkred')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"? Saved: {output_file}")
    plt.close()


def main():
    """Main execution function."""
    print("=" * 80)
    print("DILUTION FACTOR DECILE ANALYSIS")
    print("=" * 80)
    print("\nAnalysis:")
    print("  - Decile portfolios sorted by dilution velocity")
    print("  - Top/bottom 10 individual coin comparison")
    print("  - Equal-weighted portfolios")
    print("  - Monthly rebalancing")
    print()
    
    # Load data
    print("-" * 80)
    print("LOADING DATA")
    print("-" * 80)
    
    price_df = load_historical_price_data()
    historical_dilution = load_historical_dilution_snapshots()
    
    # Calculate rolling dilution signals
    print("\n" + "-" * 80)
    print("CALCULATING ROLLING DILUTION SIGNALS")
    print("-" * 80)
    
    signals_df = calculate_rolling_dilution_signal(historical_dilution, lookback_months=12)
    
    # Run decile backtest
    print("\n" + "-" * 80)
    print("RUNNING DECILE BACKTEST")
    print("-" * 80)
    
    decile_results, individual_returns_df = backtest_decile_portfolios(signals_df, price_df, n_deciles=10)
    
    # Calculate metrics
    print("\n" + "-" * 80)
    print("CALCULATING METRICS")
    print("-" * 80)
    
    metrics_df = calculate_decile_metrics(decile_results)
    
    # Analyze top/bottom names
    print("\n" + "-" * 80)
    print("ANALYZING TOP/BOTTOM INDIVIDUAL COINS")
    print("-" * 80)
    
    top_names, bottom_names = analyze_top_bottom_names(individual_returns_df, n=10)
    
    # Print results
    print("\n" + "=" * 80)
    print("DECILE PERFORMANCE SUMMARY")
    print("=" * 80)
    print()
    print(metrics_df.to_string(index=False))
    
    print("\n" + "=" * 80)
    print("TOP 10 PERFORMING COINS")
    print("=" * 80)
    print()
    print(top_names[['symbol', 'avg_period_return', 'avg_dilution_velocity', 
                     'typical_decile', 'n_periods']].to_string(index=False))
    
    print("\n" + "=" * 80)
    print("BOTTOM 10 PERFORMING COINS")
    print("=" * 80)
    print()
    print(bottom_names[['symbol', 'avg_period_return', 'avg_dilution_velocity',
                        'typical_decile', 'n_periods']].to_string(index=False))
    
    # Long/Short comparison
    if len(metrics_df) >= 2:
        d1 = metrics_df[metrics_df['decile'] == 1].iloc[0]
        d10 = metrics_df[metrics_df['decile'] == 10].iloc[0]
        
        print("\n" + "=" * 80)
        print("DECILE 1 (LOW DILUTION) vs DECILE 10 (HIGH DILUTION)")
        print("=" * 80)
        print(f"\nDecile 1 (Low Dilution):")
        print(f"  Annualized Return:  {d1['annualized_return_pct']:>8.2f}%")
        print(f"  Sharpe Ratio:       {d1['sharpe_ratio']:>8.2f}")
        print(f"  Max Drawdown:       {d1['max_drawdown_pct']:>8.2f}%")
        
        print(f"\nDecile 10 (High Dilution):")
        print(f"  Annualized Return:  {d10['annualized_return_pct']:>8.2f}%")
        print(f"  Sharpe Ratio:       {d10['sharpe_ratio']:>8.2f}")
        print(f"  Max Drawdown:       {d10['max_drawdown_pct']:>8.2f}%")
        
        print(f"\nLong/Short Spread (D1 - D10):")
        print(f"  Return Difference:  {d1['annualized_return_pct'] - d10['annualized_return_pct']:>8.2f}%")
        print(f"  Sharpe Difference:  {d1['sharpe_ratio'] - d10['sharpe_ratio']:>8.2f}")
    
    # Save results
    print("\n" + "-" * 80)
    print("SAVING RESULTS")
    print("-" * 80)
    
    metrics_df.to_csv('dilution_decile_metrics.csv', index=False)
    print("? Saved: dilution_decile_metrics.csv")
    
    top_names.to_csv('dilution_top10_names.csv', index=False)
    print("? Saved: dilution_top10_names.csv")
    
    bottom_names.to_csv('dilution_bottom10_names.csv', index=False)
    print("? Saved: dilution_bottom10_names.csv")
    
    individual_returns_df.to_csv('dilution_individual_coin_returns.csv', index=False)
    print("? Saved: dilution_individual_coin_returns.csv")
    
    # Save decile portfolio values
    for decile, results in decile_results.items():
        if len(results['portfolio_values']) > 0:
            results['portfolio_values'].to_csv(f'dilution_decile{decile}_portfolio.csv', index=False)
    print("? Saved: dilution_decile*_portfolio.csv (10 files)")
    
    # Generate plots
    print("\n" + "-" * 80)
    print("GENERATING VISUALIZATIONS")
    print("-" * 80)
    
    plot_decile_comparison(decile_results, metrics_df)
    plot_top_bottom_names(top_names, bottom_names)
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
