#!/usr/bin/env python3
"""
Analyze ADF Factor Performance by Market Directionality

Uses 5-day BTC percent change to categorize market regimes:
- Strong Up (>10%)
- Up (0% to 10%)
- Down (0% to -10%)
- Strong Down (<-10%)

Analyzes strategy performance in each regime.
"""

import pandas as pd
import numpy as np
import sys

def load_portfolio_and_btc_data(portfolio_file, price_data_file):
    """Load portfolio values and BTC price data"""
    portfolio = pd.read_csv(portfolio_file)
    portfolio['date'] = pd.to_datetime(portfolio['date'])
    
    prices = pd.read_csv(price_data_file)
    prices['date'] = pd.to_datetime(prices['date'])
    
    # Get BTC data
    btc = prices[prices['symbol'].isin(['BTC', 'BTC/USD'])][['date', 'close']].copy()
    btc = btc.sort_values('date').drop_duplicates('date')
    btc.columns = ['date', 'btc_close']
    
    return portfolio, btc

def calculate_btc_5d_change(btc):
    """Calculate 5-day percent change for BTC"""
    btc = btc.sort_values('date').copy()
    btc['btc_5d_pct_change'] = btc['btc_close'].pct_change(periods=5) * 100
    return btc

def categorize_regime(pct_change):
    """Categorize market regime based on 5d % change"""
    if pd.isna(pct_change):
        return 'Unknown'
    elif pct_change > 10:
        return 'Strong Up (>10%)'
    elif pct_change > 0:
        return 'Up (0-10%)'
    elif pct_change > -10:
        return 'Down (0 to -10%)'
    else:
        return 'Strong Down (<-10%)'

def analyze_by_regime(portfolio_df, strategy_name):
    """Analyze strategy performance by market regime"""
    
    # Calculate daily returns
    portfolio_df['daily_return'] = portfolio_df['portfolio_value'].pct_change()
    
    # Group by regime
    regime_stats = []
    
    for regime in ['Strong Up (>10%)', 'Up (0-10%)', 'Down (0 to -10%)', 'Strong Down (<-10%)']:
        regime_data = portfolio_df[portfolio_df['regime'] == regime]
        
        if len(regime_data) == 0:
            continue
        
        # Calculate metrics
        num_days = len(regime_data)
        daily_returns = regime_data['daily_return'].dropna()
        
        if len(daily_returns) == 0:
            continue
        
        total_return = (regime_data['portfolio_value'].iloc[-1] / regime_data['portfolio_value'].iloc[0] - 1) * 100
        avg_daily_return = daily_returns.mean() * 100
        win_rate = (daily_returns > 0).sum() / len(daily_returns) * 100
        
        # Annualized metrics
        ann_return = ((1 + daily_returns.mean()) ** 365 - 1) * 100
        ann_vol = daily_returns.std() * np.sqrt(365) * 100
        sharpe = ann_return / ann_vol if ann_vol > 0 else 0
        
        # Max drawdown in this regime
        cum_returns = (1 + daily_returns).cumprod()
        running_max = cum_returns.expanding().max()
        drawdown = (cum_returns - running_max) / running_max
        max_dd = drawdown.min() * 100
        
        regime_stats.append({
            'Strategy': strategy_name,
            'Regime': regime,
            'Days': num_days,
            'Pct_of_Total': num_days / len(portfolio_df) * 100,
            'Total_Return': total_return,
            'Avg_Daily_Return': avg_daily_return,
            'Ann_Return': ann_return,
            'Ann_Volatility': ann_vol,
            'Sharpe': sharpe,
            'Max_DD': max_dd,
            'Win_Rate': win_rate,
            'Avg_BTC_5d_Change': regime_data['btc_5d_pct_change'].mean()
        })
    
    return pd.DataFrame(regime_stats)

def main():
    """Main analysis function"""
    
    print("=" * 80)
    print("ADF FACTOR: DIRECTIONAL ANALYSIS (5-Day % Change)")
    print("=" * 80)
    
    # Define strategies to analyze
    strategies = {
        'Trend Following (EW)': 'backtests/results/adf_trend_following_2021_top100_portfolio_values.csv',
        'Mean Reversion (EW)': 'backtests/results/adf_mean_reversion_2021_top100_portfolio_values.csv',
        'Trend Following (RP)': 'backtests/results/adf_trend_riskparity_2021_top100_portfolio_values.csv'
    }
    
    price_data_file = 'data/raw/combined_coinbase_coinmarketcap_daily.csv'
    
    all_results = []
    
    for strategy_name, portfolio_file in strategies.items():
        print(f"\n{'-' * 80}")
        print(f"Analyzing: {strategy_name}")
        print('-' * 80)
        
        # Load data
        portfolio, btc = load_portfolio_and_btc_data(portfolio_file, price_data_file)
        
        # Calculate BTC 5-day change
        btc = calculate_btc_5d_change(btc)
        
        # Merge with portfolio
        portfolio = portfolio.merge(btc, on='date', how='left')
        
        # Categorize regime
        portfolio['regime'] = portfolio['btc_5d_pct_change'].apply(categorize_regime)
        
        # Analyze by regime
        regime_analysis = analyze_by_regime(portfolio, strategy_name)
        all_results.append(regime_analysis)
        
        # Print results
        print("\nPerformance by Market Regime:")
        print(regime_analysis.to_string(index=False))
        
        # Regime distribution
        print("\nRegime Distribution:")
        regime_dist = portfolio['regime'].value_counts()
        for regime, count in regime_dist.items():
            pct = count / len(portfolio) * 100
            print(f"  {regime:25s}: {count:4d} days ({pct:5.1f}%)")
    
    # Combine all results
    all_results_df = pd.concat(all_results, ignore_index=True)
    
    # Save results
    output_file = 'backtests/results/adf_directional_analysis.csv'
    all_results_df.to_csv(output_file, index=False)
    print(f"\n✓ Saved directional analysis to: {output_file}")
    
    # Comparative analysis
    print("\n" + "=" * 80)
    print("COMPARATIVE ANALYSIS")
    print("=" * 80)
    
    # Compare strategies by regime
    for regime in ['Strong Up (>10%)', 'Up (0-10%)', 'Down (0 to -10%)', 'Strong Down (<-10%)']:
        regime_data = all_results_df[all_results_df['Regime'] == regime]
        if len(regime_data) > 0:
            print(f"\n{regime}:")
            print(regime_data[['Strategy', 'Ann_Return', 'Sharpe', 'Win_Rate']].to_string(index=False))
    
    # Best/worst regimes per strategy
    print("\n" + "=" * 80)
    print("BEST & WORST REGIMES PER STRATEGY")
    print("=" * 80)
    
    for strategy_name in strategies.keys():
        strategy_data = all_results_df[all_results_df['Strategy'] == strategy_name].copy()
        if len(strategy_data) > 0:
            strategy_data = strategy_data.sort_values('Ann_Return', ascending=False)
            print(f"\n{strategy_name}:")
            print(f"  Best:  {strategy_data.iloc[0]['Regime']:25s} ({strategy_data.iloc[0]['Ann_Return']:+7.2f}% ann. return)")
            print(f"  Worst: {strategy_data.iloc[-1]['Regime']:25s} ({strategy_data.iloc[-1]['Ann_Return']:+7.2f}% ann. return)")

if __name__ == '__main__':
    main()
