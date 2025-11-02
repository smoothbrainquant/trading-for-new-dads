"""
Analyze Kurtosis Backtest by Regime - Breaking down Long/Short Returns

This script analyzes the kurtosis factor backtest results by different market regimes
and breaks down returns into long and short components.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 10)

def load_kurtosis_data():
    """Load kurtosis backtest data."""
    portfolio = pd.read_csv('backtests/results/kurtosis_factor_portfolio_values.csv')
    portfolio['date'] = pd.to_datetime(portfolio['date'])
    
    kurtosis_ts = pd.read_csv('backtests/results/kurtosis_factor_kurtosis_timeseries.csv')
    kurtosis_ts['date'] = pd.to_datetime(kurtosis_ts['date'])
    
    # Load price data for market regime identification
    price_data = pd.read_csv('data/raw/combined_coinbase_coinmarketcap_daily.csv')
    price_data['date'] = pd.to_datetime(price_data['date'])
    
    return portfolio, kurtosis_ts, price_data

def calculate_daily_returns(portfolio):
    """Calculate daily returns for the portfolio."""
    portfolio = portfolio.copy()
    portfolio['daily_return'] = portfolio['portfolio_value'].pct_change()
    portfolio['log_return'] = np.log(portfolio['portfolio_value'] / portfolio['portfolio_value'].shift(1))
    return portfolio

def identify_market_regimes(price_data):
    """
    Identify different market regimes based on:
    1. Market trend (bull/bear)
    2. Volatility regime (high/low)
    3. Time periods
    """
    # Calculate BTC price as market proxy
    btc_data = price_data[price_data['symbol'] == 'BTC/USD'].copy()
    btc_data = btc_data.sort_values('date')
    
    # Calculate rolling metrics
    btc_data['ma_50'] = btc_data['close'].rolling(50).mean()
    btc_data['ma_200'] = btc_data['close'].rolling(200).mean()
    btc_data['daily_return'] = btc_data['close'].pct_change()
    btc_data['volatility_30d'] = btc_data['daily_return'].rolling(30).std() * np.sqrt(365)
    
    # Define trend regime: bull (50 > 200) vs bear (50 < 200)
    btc_data['trend_regime'] = np.where(btc_data['ma_50'] > btc_data['ma_200'], 'Bull', 'Bear')
    
    # Define volatility regime based on historical percentiles
    vol_median = btc_data['volatility_30d'].median()
    btc_data['vol_regime'] = np.where(btc_data['volatility_30d'] > vol_median, 'High Vol', 'Low Vol')
    
    # Combined regime
    btc_data['regime'] = btc_data['trend_regime'] + ' / ' + btc_data['vol_regime']
    
    return btc_data[['date', 'trend_regime', 'vol_regime', 'regime', 'volatility_30d']]

def calculate_position_returns(portfolio, kurtosis_ts, price_data):
    """
    Calculate returns broken down by long/short positions.
    """
    portfolio = portfolio.copy()
    
    # Calculate returns
    portfolio['daily_return'] = portfolio['portfolio_value'].pct_change()
    portfolio['log_return'] = np.log(portfolio['portfolio_value'] / portfolio['portfolio_value'].shift(1))
    
    # For each date, calculate the contribution from long and short positions
    # We can approximate this using the exposure data
    portfolio['long_return_contrib'] = 0.0
    portfolio['short_return_contrib'] = 0.0
    
    for idx in range(1, len(portfolio)):
        date = portfolio.iloc[idx]['date']
        prev_date = portfolio.iloc[idx-1]['date']
        
        # Get previous exposures
        long_exp = portfolio.iloc[idx-1]['long_exposure']
        short_exp = portfolio.iloc[idx-1]['short_exposure']
        gross_exp = portfolio.iloc[idx-1]['gross_exposure']
        
        total_return = portfolio.iloc[idx]['log_return']
        
        if gross_exp > 0 and not np.isnan(total_return):
            # Approximate long/short contributions based on exposure weights
            # This is an approximation assuming proportional contribution
            long_weight = long_exp / gross_exp if gross_exp > 0 else 0
            short_weight = short_exp / gross_exp if gross_exp > 0 else 0
            
            # Allocate return to long/short
            portfolio.loc[portfolio.index[idx], 'long_return_contrib'] = total_return * long_weight
            portfolio.loc[portfolio.index[idx], 'short_return_contrib'] = total_return * short_weight
    
    return portfolio

def analyze_by_regime(portfolio_with_returns, regimes):
    """Analyze returns broken down by regime and long/short."""
    # Merge regimes
    analysis_df = portfolio_with_returns.merge(regimes, on='date', how='left')
    analysis_df = analysis_df.dropna(subset=['regime'])
    
    # Group by regime
    regime_stats = []
    
    for regime in analysis_df['regime'].unique():
        regime_data = analysis_df[analysis_df['regime'] == regime].copy()
        
        if len(regime_data) < 5:  # Skip regimes with too few observations
            continue
        
        # Total returns
        total_return = (regime_data['portfolio_value'].iloc[-1] / regime_data['portfolio_value'].iloc[0] - 1)
        
        # Long/short contributions
        long_contrib = regime_data['long_return_contrib'].sum()
        short_contrib = regime_data['short_return_contrib'].sum()
        
        # Statistics
        stats = {
            'regime': regime,
            'trend': regime_data['trend_regime'].iloc[0],
            'vol': regime_data['vol_regime'].iloc[0],
            'num_days': len(regime_data),
            'total_return': total_return,
            'annualized_return': (1 + total_return) ** (365 / len(regime_data)) - 1,
            'long_contribution': long_contrib,
            'short_contribution': short_contrib,
            'long_annualized': (np.exp(long_contrib) ** (365 / len(regime_data))) - 1,
            'short_annualized': (np.exp(short_contrib) ** (365 / len(regime_data))) - 1,
            'sharpe': regime_data['log_return'].mean() / regime_data['log_return'].std() * np.sqrt(365) if regime_data['log_return'].std() > 0 else 0,
            'win_rate': (regime_data['log_return'] > 0).sum() / len(regime_data),
            'avg_long_positions': regime_data['num_long_positions'].mean(),
            'avg_short_positions': regime_data['num_short_positions'].mean(),
            'avg_long_exposure': regime_data['long_exposure'].mean(),
            'avg_short_exposure': regime_data['short_exposure'].mean(),
        }
        
        regime_stats.append(stats)
    
    return pd.DataFrame(regime_stats)

def analyze_by_time_period(portfolio_with_returns):
    """Analyze returns by time period."""
    portfolio_with_returns['year'] = portfolio_with_returns['date'].dt.year
    
    yearly_stats = []
    
    for year in sorted(portfolio_with_returns['year'].unique()):
        year_data = portfolio_with_returns[portfolio_with_returns['year'] == year].copy()
        
        if len(year_data) < 5:
            continue
        
        # Calculate stats
        total_return = (year_data['portfolio_value'].iloc[-1] / year_data['portfolio_value'].iloc[0] - 1)
        long_contrib = year_data['long_return_contrib'].sum()
        short_contrib = year_data['short_return_contrib'].sum()
        
        stats = {
            'year': int(year),
            'num_days': len(year_data),
            'total_return': total_return,
            'long_contribution': long_contrib,
            'short_contribution': short_contrib,
            'long_annualized': (np.exp(long_contrib) ** (365 / len(year_data))) - 1,
            'short_annualized': (np.exp(short_contrib) ** (365 / len(year_data))) - 1,
            'sharpe': year_data['log_return'].mean() / year_data['log_return'].std() * np.sqrt(365) if year_data['log_return'].std() > 0 else 0,
            'win_rate': (year_data['log_return'] > 0).sum() / len(year_data),
            'avg_long_positions': year_data['num_long_positions'].mean(),
            'avg_short_positions': year_data['num_short_positions'].mean(),
        }
        
        yearly_stats.append(stats)
    
    return pd.DataFrame(yearly_stats)

def plot_regime_analysis(regime_stats):
    """Create visualizations for regime analysis."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Returns by regime
    ax = axes[0, 0]
    x = np.arange(len(regime_stats))
    width = 0.35
    
    ax.bar(x - width/2, regime_stats['long_annualized'] * 100, width, label='Long', alpha=0.8)
    ax.bar(x + width/2, regime_stats['short_annualized'] * 100, width, label='Short', alpha=0.8)
    ax.set_xlabel('Regime')
    ax.set_ylabel('Annualized Return (%)')
    ax.set_title('Long vs Short Returns by Regime')
    ax.set_xticks(x)
    ax.set_xticklabels(regime_stats['regime'], rotation=45, ha='right')
    ax.legend()
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.grid(True, alpha=0.3)
    
    # 2. Sharpe ratio by regime
    ax = axes[0, 1]
    colors = ['green' if x > 0 else 'red' for x in regime_stats['sharpe']]
    ax.barh(regime_stats['regime'], regime_stats['sharpe'], color=colors, alpha=0.7)
    ax.set_xlabel('Sharpe Ratio')
    ax.set_title('Sharpe Ratio by Regime')
    ax.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
    ax.grid(True, alpha=0.3)
    
    # 3. Win rate by regime
    ax = axes[1, 0]
    ax.barh(regime_stats['regime'], regime_stats['win_rate'] * 100, alpha=0.7)
    ax.set_xlabel('Win Rate (%)')
    ax.set_title('Win Rate by Regime')
    ax.axvline(x=50, color='red', linestyle='--', linewidth=1)
    ax.grid(True, alpha=0.3)
    
    # 4. Total contribution by regime
    ax = axes[1, 1]
    regime_stats['long_total'] = regime_stats['long_contribution']
    regime_stats['short_total'] = regime_stats['short_contribution']
    
    x = np.arange(len(regime_stats))
    ax.bar(x - width/2, regime_stats['long_total'], width, label='Long Contribution', alpha=0.8)
    ax.bar(x + width/2, regime_stats['short_total'], width, label='Short Contribution', alpha=0.8)
    ax.set_xlabel('Regime')
    ax.set_ylabel('Cumulative Log Return Contribution')
    ax.set_title('Long vs Short Contribution by Regime')
    ax.set_xticks(x)
    ax.set_xticklabels(regime_stats['regime'], rotation=45, ha='right')
    ax.legend()
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('backtests/results/kurtosis_regime_analysis.png', dpi=300, bbox_inches='tight')
    print("\nSaved plot to: backtests/results/kurtosis_regime_analysis.png")
    plt.close()

def plot_yearly_analysis(yearly_stats):
    """Create visualizations for yearly analysis."""
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    # 1. Annual returns breakdown
    ax = axes[0, 0]
    x = yearly_stats['year']
    width = 0.35
    
    ax.bar(x - width/2, yearly_stats['long_annualized'] * 100, width, label='Long', alpha=0.8)
    ax.bar(x + width/2, yearly_stats['short_annualized'] * 100, width, label='Short', alpha=0.8)
    ax.set_xlabel('Year')
    ax.set_ylabel('Annualized Return (%)')
    ax.set_title('Long vs Short Returns by Year')
    ax.legend()
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.grid(True, alpha=0.3)
    
    # 2. Total returns by year
    ax = axes[0, 1]
    colors = ['green' if x > 0 else 'red' for x in yearly_stats['total_return']]
    ax.bar(yearly_stats['year'], yearly_stats['total_return'] * 100, color=colors, alpha=0.7)
    ax.set_xlabel('Year')
    ax.set_ylabel('Total Return (%)')
    ax.set_title('Total Annual Returns')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.grid(True, alpha=0.3)
    
    # 3. Sharpe ratio by year
    ax = axes[1, 0]
    colors = ['green' if x > 0 else 'red' for x in yearly_stats['sharpe']]
    ax.bar(yearly_stats['year'], yearly_stats['sharpe'], color=colors, alpha=0.7)
    ax.set_xlabel('Year')
    ax.set_ylabel('Sharpe Ratio')
    ax.set_title('Sharpe Ratio by Year')
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax.grid(True, alpha=0.3)
    
    # 4. Win rate by year
    ax = axes[1, 1]
    ax.bar(yearly_stats['year'], yearly_stats['win_rate'] * 100, alpha=0.7)
    ax.set_xlabel('Year')
    ax.set_ylabel('Win Rate (%)')
    ax.set_title('Win Rate by Year')
    ax.axhline(y=50, color='red', linestyle='--', linewidth=1)
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('backtests/results/kurtosis_yearly_analysis.png', dpi=300, bbox_inches='tight')
    print("Saved plot to: backtests/results/kurtosis_yearly_analysis.png")
    plt.close()

def main():
    """Main analysis function."""
    print("=" * 80)
    print("KURTOSIS FACTOR BACKTEST - REGIME ANALYSIS")
    print("=" * 80)
    
    # Load data
    print("\nLoading data...")
    portfolio, kurtosis_ts, price_data = load_kurtosis_data()
    print(f"Portfolio data: {len(portfolio)} days")
    print(f"Date range: {portfolio['date'].min().date()} to {portfolio['date'].max().date()}")
    
    # Identify regimes
    print("\nIdentifying market regimes...")
    regimes = identify_market_regimes(price_data)
    print(f"Regime definitions: {regimes['regime'].nunique()} unique regimes")
    
    # Calculate position returns
    print("\nCalculating long/short contributions...")
    portfolio_with_returns = calculate_position_returns(portfolio, kurtosis_ts, price_data)
    
    # Analyze by regime
    print("\nAnalyzing by regime...")
    regime_stats = analyze_by_regime(portfolio_with_returns, regimes)
    
    print("\n" + "=" * 80)
    print("REGIME ANALYSIS SUMMARY")
    print("=" * 80)
    print(regime_stats.to_string(index=False))
    
    # Save regime stats
    regime_stats.to_csv('backtests/results/kurtosis_regime_stats.csv', index=False)
    print("\nSaved regime stats to: backtests/results/kurtosis_regime_stats.csv")
    
    # Analyze by year
    print("\n" + "=" * 80)
    print("YEARLY ANALYSIS")
    print("=" * 80)
    yearly_stats = analyze_by_time_period(portfolio_with_returns)
    print(yearly_stats.to_string(index=False))
    
    # Save yearly stats
    yearly_stats.to_csv('backtests/results/kurtosis_yearly_stats.csv', index=False)
    print("\nSaved yearly stats to: backtests/results/kurtosis_yearly_stats.csv")
    
    # Create visualizations
    print("\nCreating visualizations...")
    plot_regime_analysis(regime_stats)
    plot_yearly_analysis(yearly_stats)
    
    # Summary insights
    print("\n" + "=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)
    
    # Best/worst regimes
    best_regime = regime_stats.loc[regime_stats['annualized_return'].idxmax()]
    worst_regime = regime_stats.loc[regime_stats['annualized_return'].idxmin()]
    
    print(f"\nBest Regime: {best_regime['regime']}")
    print(f"  - Annualized Return: {best_regime['annualized_return']:.2%}")
    print(f"  - Long Contribution: {best_regime['long_annualized']:.2%}")
    print(f"  - Short Contribution: {best_regime['short_annualized']:.2%}")
    print(f"  - Sharpe Ratio: {best_regime['sharpe']:.2f}")
    
    print(f"\nWorst Regime: {worst_regime['regime']}")
    print(f"  - Annualized Return: {worst_regime['annualized_return']:.2%}")
    print(f"  - Long Contribution: {worst_regime['long_annualized']:.2%}")
    print(f"  - Short Contribution: {worst_regime['short_annualized']:.2%}")
    print(f"  - Sharpe Ratio: {worst_regime['sharpe']:.2f}")
    
    # Long vs Short performance
    total_long = regime_stats['long_contribution'].sum()
    total_short = regime_stats['short_contribution'].sum()
    
    print(f"\n\nOverall Long/Short Performance:")
    print(f"  - Total Long Contribution: {total_long:.4f} ({np.exp(total_long)-1:.2%} cumulative)")
    print(f"  - Total Short Contribution: {total_short:.4f} ({np.exp(total_short)-1:.2%} cumulative)")
    print(f"  - Long/Short Ratio: {total_long/total_short:.2f}" if total_short != 0 else "  - Long/Short Ratio: N/A")
    
    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()
