#!/usr/bin/env python3
"""
Analyze yearly performance breakdown for DW strategies.
"""

import pandas as pd
import numpy as np

# Load portfolio values for all strategies
strategies = {
    'Contrarian (30d)': 'backtests/results/dw_2021_2025_top100_contrarian_portfolio_values.csv',
    'Risk Parity (60d)': 'backtests/results/dw_2021_2025_top100_risk_parity_portfolio_values.csv',
    'Momentum Continuation': 'backtests/results/dw_2021_2025_top100_momentum_portfolio_values.csv',
}

print("=" * 100)
print("DURBIN-WATSON STRATEGIES - YEARLY PERFORMANCE BREAKDOWN (2021-2025, Top 100 Market Cap)")
print("=" * 100)

for strategy_name, filepath in strategies.items():
    print(f"\n{'='*100}")
    print(f"Strategy: {strategy_name}")
    print("=" * 100)
    
    try:
        df = pd.read_csv(filepath)
        df['date'] = pd.to_datetime(df['date'])
        df['year'] = df['date'].dt.year
        df['daily_return'] = df['portfolio_value'].pct_change()
        
        # Calculate yearly metrics
        yearly_stats = []
        for year in sorted(df['year'].unique()):
            year_data = df[df['year'] == year]
            
            if len(year_data) < 2:
                continue
            
            start_value = year_data['portfolio_value'].iloc[0]
            end_value = year_data['portfolio_value'].iloc[-1]
            year_return = (end_value - start_value) / start_value
            
            year_vol = year_data['daily_return'].std() * np.sqrt(252)
            year_sharpe = (year_return / (len(year_data)/252)) / year_vol if year_vol > 0 else 0
            
            # Max drawdown for the year
            cumulative = (1 + year_data['daily_return'].fillna(0)).cumprod()
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            max_dd = drawdown.min()
            
            win_rate = (year_data['daily_return'] > 0).sum() / len(year_data)
            
            yearly_stats.append({
                'Year': int(year),
                'Return': year_return * 100,
                'Volatility': year_vol * 100,
                'Sharpe': year_sharpe,
                'Max DD': max_dd * 100,
                'Win Rate': win_rate * 100,
                'Days': len(year_data),
                'Start': start_value,
                'End': end_value
            })
        
        # Print yearly table
        print(f"\n{'Year':<8} {'Return':<12} {'Volatility':<12} {'Sharpe':<10} {'Max DD':<12} {'Win Rate':<12} {'Days':<8}")
        print("-" * 100)
        
        for stat in yearly_stats:
            print(f"{stat['Year']:<8} {stat['Return']:>10.2f}% {stat['Volatility']:>10.2f}% {stat['Sharpe']:>9.2f} {stat['Max DD']:>10.2f}% {stat['Win Rate']:>10.1f}% {stat['Days']:>8}")
        
        # Overall stats
        overall_return = (df['portfolio_value'].iloc[-1] - df['portfolio_value'].iloc[0]) / df['portfolio_value'].iloc[0]
        overall_vol = df['daily_return'].std() * np.sqrt(252)
        days = len(df)
        years = days / 252
        ann_return = (1 + overall_return) ** (1 / years) - 1
        overall_sharpe = ann_return / overall_vol if overall_vol > 0 else 0
        
        cumulative = (1 + df['daily_return'].fillna(0)).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        overall_max_dd = drawdown.min()
        
        print("-" * 100)
        print(f"{'TOTAL':<8} {overall_return*100:>10.2f}% {overall_vol*100:>10.2f}% {overall_sharpe:>9.2f} {overall_max_dd*100:>10.2f}% {(df['daily_return']>0).sum()/len(df)*100:>10.1f}% {days:>8}")
        print(f"         Ann: {ann_return*100:>6.2f}%")
        
    except Exception as e:
        print(f"Error loading {strategy_name}: {e}")

print("\n" + "=" * 100)
print("ANALYSIS COMPLETE")
print("=" * 100)
