#!/usr/bin/env python3
"""
Backtest ADF Factor with Regime-Switching

Switches between Trend Following and Mean Reversion based on 
5-day BTC percent change:
- Strong moves (>10%) → Trend Following
- Moderate moves (0-10%) → Mean Reversion
"""

import pandas as pd
import numpy as np
import sys
import os

def load_data(price_data_file):
    """Load price data"""
    df = pd.read_csv(price_data_file)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    return df

def load_portfolio_data(strategy_files):
    """Load portfolio values from both strategies"""
    portfolios = {}
    
    for name, filepath in strategy_files.items():
        df = pd.read_csv(filepath)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        portfolios[name] = df
    
    return portfolios

def detect_regime(btc_5d_pct_change):
    """Detect market regime based on 5-day BTC % change"""
    if pd.isna(btc_5d_pct_change):
        return 'Unknown'
    elif btc_5d_pct_change > 10:
        return 'Strong Up'
    elif btc_5d_pct_change > 0:
        return 'Moderate Up'
    elif btc_5d_pct_change > -10:
        return 'Down'
    else:
        return 'Strong Down'

def get_optimal_strategy(regime):
    """Return optimal strategy for given regime"""
    if regime in ['Strong Up', 'Down']:
        return 'trend_following'
    elif regime in ['Moderate Up', 'Strong Down']:
        return 'mean_reversion'
    else:
        return 'trend_following'  # default

def simulate_regime_switching(portfolios, btc_data, initial_capital=10000, 
                              switching_mode='optimal'):
    """
    Simulate regime-switching strategy
    
    Args:
        portfolios: Dict with 'trend_following' and 'mean_reversion' DataFrames
        btc_data: DataFrame with BTC prices and 5d % change
        initial_capital: Starting capital
        switching_mode: 'optimal' (switch to best), 'blended' (weight by regime)
    """
    # Merge all data on date
    tf_df = portfolios['trend_following'].copy()
    mr_df = portfolios['mean_reversion'].copy()
    
    # Calculate daily returns for each strategy
    tf_df['tf_daily_return'] = tf_df['portfolio_value'].pct_change()
    mr_df['mr_daily_return'] = mr_df['portfolio_value'].pct_change()
    
    # Merge with BTC data
    combined = tf_df[['date', 'tf_daily_return']].merge(
        mr_df[['date', 'mr_daily_return']], on='date', how='inner'
    )
    combined = combined.merge(btc_data[['date', 'btc_5d_pct_change']], on='date', how='left')
    
    # Detect regime
    combined['regime'] = combined['btc_5d_pct_change'].apply(detect_regime)
    combined['optimal_strategy'] = combined['regime'].apply(get_optimal_strategy)
    
    # Simulate portfolio
    portfolio_value = initial_capital
    portfolio_values = []
    
    for idx, row in combined.iterrows():
        if switching_mode == 'optimal':
            # Use return from optimal strategy
            if row['optimal_strategy'] == 'trend_following':
                daily_return = row['tf_daily_return']
                active_strategy = 'Trend Following'
                tf_weight = 1.0
                mr_weight = 0.0
            else:
                daily_return = row['mr_daily_return']
                active_strategy = 'Mean Reversion'
                tf_weight = 0.0
                mr_weight = 1.0
        
        elif switching_mode == 'blended':
            # Blend both strategies based on regime
            if row['regime'] in ['Strong Up', 'Down']:
                tf_weight = 0.8
                mr_weight = 0.2
            elif row['regime'] in ['Moderate Up', 'Strong Down']:
                tf_weight = 0.2
                mr_weight = 0.8
            else:  # Unknown
                tf_weight = 0.5
                mr_weight = 0.5
            
            daily_return = (tf_weight * row['tf_daily_return'] + 
                           mr_weight * row['mr_daily_return'])
            active_strategy = f"Blend (TF:{tf_weight:.0%}, MR:{mr_weight:.0%})"
        
        # Update portfolio value
        if not pd.isna(daily_return):
            portfolio_value = portfolio_value * (1 + daily_return)
        
        portfolio_values.append({
            'date': row['date'],
            'portfolio_value': portfolio_value,
            'daily_return': daily_return,
            'regime': row['regime'],
            'active_strategy': active_strategy,
            'tf_weight': tf_weight,
            'mr_weight': mr_weight,
            'btc_5d_pct_change': row['btc_5d_pct_change']
        })
    
    return pd.DataFrame(portfolio_values)

def calculate_metrics(portfolio_df, initial_capital):
    """Calculate performance metrics"""
    if portfolio_df.empty:
        return {}
    
    # Calculate returns
    daily_returns = portfolio_df['daily_return'].dropna()
    
    # Total return
    final_value = portfolio_df['portfolio_value'].iloc[-1]
    total_return = (final_value - initial_capital) / initial_capital
    
    # Annualized return
    num_days = len(portfolio_df)
    annualized_return = (1 + total_return) ** (365 / num_days) - 1
    
    # Volatility
    annualized_volatility = daily_returns.std() * np.sqrt(365)
    
    # Sharpe ratio (assuming 0% risk-free rate)
    sharpe_ratio = annualized_return / annualized_volatility if annualized_volatility > 0 else 0
    
    # Sortino ratio (downside deviation)
    downside_returns = daily_returns[daily_returns < 0]
    downside_volatility = downside_returns.std() * np.sqrt(365) if len(downside_returns) > 0 else 0
    sortino_ratio = annualized_return / downside_volatility if downside_volatility > 0 else 0
    
    # Maximum drawdown
    cumulative_returns = (1 + daily_returns).cumprod()
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # Calmar ratio
    calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
    
    # Win rate
    win_rate = (daily_returns > 0).sum() / len(daily_returns)
    
    metrics = {
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'annualized_return': annualized_return,
        'annualized_volatility': annualized_volatility,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'max_drawdown': max_drawdown,
        'calmar_ratio': calmar_ratio,
        'win_rate': win_rate,
        'trading_days': num_days
    }
    
    return metrics

def print_results(results, mode_name):
    """Print backtest results"""
    metrics = results['metrics']
    
    print("\n" + "=" * 80)
    print(f"REGIME-SWITCHING RESULTS: {mode_name}")
    print("=" * 80)
    
    print("\nPortfolio Performance:")
    print(f"  Initial Capital:        $ {metrics['initial_capital']:>12,.2f}")
    print(f"  Final Value:            $ {metrics['final_value']:>12,.2f}")
    print(f"  Total Return:           {metrics['total_return']:>14.2%}")
    print(f"  Annualized Return:      {metrics['annualized_return']:>14.2%}")
    
    print("\nRisk Metrics:")
    print(f"  Annualized Volatility:  {metrics['annualized_volatility']:>14.2%}")
    print(f"  Sharpe Ratio:           {metrics['sharpe_ratio']:>14.2f}")
    print(f"  Sortino Ratio:          {metrics['sortino_ratio']:>14.2f}")
    print(f"  Maximum Drawdown:       {metrics['max_drawdown']:>14.2%}")
    print(f"  Calmar Ratio:           {metrics['calmar_ratio']:>14.2f}")
    
    print("\nTrading Statistics:")
    print(f"  Win Rate:               {metrics['win_rate']:>14.2%}")
    print(f"  Trading Days:           {metrics['trading_days']:>14.0f}")
    
    # Regime breakdown
    portfolio_df = results['portfolio']
    regime_counts = portfolio_df['regime'].value_counts()
    print("\n  Regime Distribution:")
    for regime, count in regime_counts.items():
        pct = count / len(portfolio_df) * 100
        print(f"    {regime:20s}: {count:4d} days ({pct:5.1f}%)")
    
    # Strategy usage
    if 'active_strategy' in portfolio_df.columns:
        strategy_counts = portfolio_df['active_strategy'].value_counts()
        print("\n  Active Strategy Distribution:")
        for strategy, count in strategy_counts.items():
            pct = count / len(portfolio_df) * 100
            print(f"    {strategy:30s}: {count:4d} days ({pct:5.1f}%)")

def main():
    """Main execution function"""
    
    print("=" * 80)
    print("ADF FACTOR: REGIME-SWITCHING BACKTEST")
    print("=" * 80)
    
    # Load price data for BTC
    print("\nLoading data...")
    price_data = load_data('data/raw/combined_coinbase_coinmarketcap_daily.csv')
    
    # Get BTC data
    btc = price_data[price_data['symbol'].isin(['BTC', 'BTC/USD'])][['date', 'close']].copy()
    btc = btc.sort_values('date').drop_duplicates('date').reset_index(drop=True)
    btc.columns = ['date', 'btc_close']
    
    # Calculate 5-day % change
    btc['btc_5d_pct_change'] = btc['btc_close'].pct_change(periods=5) * 100
    
    # Load strategy portfolio values
    strategy_files = {
        'trend_following': 'backtests/results/adf_trend_following_2021_top100_portfolio_values.csv',
        'mean_reversion': 'backtests/results/adf_mean_reversion_2021_top100_portfolio_values.csv'
    }
    
    portfolios = load_portfolio_data(strategy_files)
    
    print(f"Loaded {len(portfolios['trend_following'])} days of data")
    print(f"Date range: {portfolios['trend_following']['date'].min().date()} to {portfolios['trend_following']['date'].max().date()}")
    
    # Run regime-switching simulations
    results = {}
    
    # 1. Optimal switching (100% to best strategy per regime)
    print("\n" + "-" * 80)
    print("Running: Optimal Regime-Switching")
    print("-" * 80)
    optimal_portfolio = simulate_regime_switching(
        portfolios, btc, initial_capital=10000, switching_mode='optimal'
    )
    optimal_metrics = calculate_metrics(optimal_portfolio, 10000)
    results['optimal'] = {
        'portfolio': optimal_portfolio,
        'metrics': optimal_metrics
    }
    print_results(results['optimal'], "Optimal Switching")
    
    # 2. Blended switching (80/20 allocation based on regime)
    print("\n" + "-" * 80)
    print("Running: Blended Regime-Switching (80/20)")
    print("-" * 80)
    blended_portfolio = simulate_regime_switching(
        portfolios, btc, initial_capital=10000, switching_mode='blended'
    )
    blended_metrics = calculate_metrics(blended_portfolio, 10000)
    results['blended'] = {
        'portfolio': blended_portfolio,
        'metrics': blended_metrics
    }
    print_results(results['blended'], "Blended Switching (80/20)")
    
    # Save results
    optimal_portfolio.to_csv('backtests/results/adf_regime_switching_optimal_portfolio.csv', index=False)
    blended_portfolio.to_csv('backtests/results/adf_regime_switching_blended_portfolio.csv', index=False)
    
    print("\n✓ Saved optimal switching to: backtests/results/adf_regime_switching_optimal_portfolio.csv")
    print("✓ Saved blended switching to: backtests/results/adf_regime_switching_blended_portfolio.csv")
    
    # Comparative analysis
    print("\n" + "=" * 80)
    print("COMPARATIVE ANALYSIS")
    print("=" * 80)
    
    # Load static strategy metrics
    tf_metrics = pd.read_csv('backtests/results/adf_trend_following_2021_top100_metrics.csv', index_col=0)
    mr_metrics = pd.read_csv('backtests/results/adf_mean_reversion_2021_top100_metrics.csv', index_col=0)
    
    comparison = pd.DataFrame({
        'Strategy': ['Trend Following (Static)', 'Mean Reversion (Static)', 
                    'Optimal Switching', 'Blended Switching (80/20)'],
        'Total Return': [
            tf_metrics.loc['total_return', 'value'],
            mr_metrics.loc['total_return', 'value'],
            optimal_metrics['total_return'],
            blended_metrics['total_return']
        ],
        'Ann. Return': [
            tf_metrics.loc['annualized_return', 'value'],
            mr_metrics.loc['annualized_return', 'value'],
            optimal_metrics['annualized_return'],
            blended_metrics['annualized_return']
        ],
        'Sharpe': [
            tf_metrics.loc['sharpe_ratio', 'value'],
            mr_metrics.loc['sharpe_ratio', 'value'],
            optimal_metrics['sharpe_ratio'],
            blended_metrics['sharpe_ratio']
        ],
        'Max DD': [
            tf_metrics.loc['max_drawdown', 'value'],
            mr_metrics.loc['max_drawdown', 'value'],
            optimal_metrics['max_drawdown'],
            blended_metrics['max_drawdown']
        ],
        'Final Value': [
            tf_metrics.loc['final_value', 'value'],
            mr_metrics.loc['final_value', 'value'],
            optimal_metrics['final_value'],
            blended_metrics['final_value']
        ]
    })
    
    print("\nAll Strategies Comparison:")
    print(comparison.to_string(index=False))
    
    # Calculate improvements
    print("\n" + "=" * 80)
    print("IMPROVEMENT ANALYSIS")
    print("=" * 80)
    
    tf_return = tf_metrics.loc['annualized_return', 'value']
    
    print(f"\nOptimal Switching vs Best Static (Trend Following):")
    print(f"  Trend Following (Static):    {tf_return:>8.2%}")
    print(f"  Optimal Switching:           {optimal_metrics['annualized_return']:>8.2%}")
    print(f"  Improvement:                 {optimal_metrics['annualized_return'] - tf_return:>+8.2%} (+{(optimal_metrics['annualized_return'] / tf_return - 1)*100:.1f}%)")
    
    print(f"\nBlended Switching vs Best Static (Trend Following):")
    print(f"  Trend Following (Static):    {tf_return:>8.2%}")
    print(f"  Blended Switching:           {blended_metrics['annualized_return']:>8.2%}")
    print(f"  Improvement:                 {blended_metrics['annualized_return'] - tf_return:>+8.2%} (+{(blended_metrics['annualized_return'] / tf_return - 1)*100:.1f}%)")
    
    # Sharpe improvement
    tf_sharpe = tf_metrics.loc['sharpe_ratio', 'value']
    print(f"\nSharpe Ratio Improvement:")
    print(f"  Trend Following (Static):    {tf_sharpe:>8.2f}")
    print(f"  Optimal Switching:           {optimal_metrics['sharpe_ratio']:>8.2f} (+{optimal_metrics['sharpe_ratio'] - tf_sharpe:.2f})")
    print(f"  Blended Switching:           {blended_metrics['sharpe_ratio']:>8.2f} (+{blended_metrics['sharpe_ratio'] - tf_sharpe:.2f})")
    
    # Save comparison
    comparison.to_csv('backtests/results/adf_regime_switching_comparison.csv', index=False)
    print("\n✓ Saved comparison to: backtests/results/adf_regime_switching_comparison.csv")
    
    print("\n" + "=" * 80)
    print("REGIME-SWITCHING BACKTEST COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    main()
