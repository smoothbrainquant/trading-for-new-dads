#!/usr/bin/env python3
"""
Backtest VC-Backed Premium Strategy

Test whether coins with strong VC backing outperform coins with weak/no VC backing.

Hypothesis: Coins backed by top-tier VCs have:
- Better fundamentals
- More resources
- Higher survival rates
- Stronger network effects
? Should outperform over time

Strategy:
- Long: Coins with 5+ VCs (VC-backed premium)
- Short: Coins with 0-2 VCs (weak backing) OR equal-weight benchmark
- Rebalance: Monthly or quarterly
"""

import pandas as pd
import numpy as np
import glob
import os
from datetime import datetime
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')


def find_latest_file(pattern):
    """Find most recent file matching pattern."""
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getctime)


def load_vc_data():
    """Load VC portfolio data."""
    vc_file = find_latest_file("data/raw/cmc_vc_portfolios_*.csv")
    if not vc_file:
        raise FileNotFoundError("VC portfolio file not found")
    
    print(f"Loading VC data from: {vc_file}")
    return pd.read_csv(vc_file)


def load_price_data():
    """Load historical price data."""
    price_file = "data/raw/combined_coinbase_coinmarketcap_daily.csv"
    
    print(f"Loading price data from: {price_file}")
    df = pd.read_csv(price_file)
    df['date'] = pd.to_datetime(df['date'])
    
    # Sort by date
    df = df.sort_values(['symbol', 'date'])
    
    return df


def create_vc_tiers(vc_df):
    """
    Categorize coins into VC tiers.
    
    Tiers:
    - Tier 1 (Elite): 8+ VCs (top quartile)
    - Tier 2 (Strong): 5-7 VCs
    - Tier 3 (Moderate): 3-4 VCs
    - Tier 4 (Weak): 1-2 VCs
    - Tier 5 (None): 0 VCs
    """
    vc_df = vc_df.copy()
    
    vc_df['vc_tier'] = pd.cut(
        vc_df['total_vc_portfolios'],
        bins=[-1, 0, 2, 4, 7, 100],
        labels=['No VC', 'Weak (1-2)', 'Moderate (3-4)', 'Strong (5-7)', 'Elite (8+)']
    )
    
    return vc_df


def calculate_portfolio_returns(price_df, universe, rebalance_days=30, start_date=None, end_date=None):
    """
    Calculate returns for a portfolio of coins (equal-weighted, rebalanced).
    
    Args:
        price_df: Price data
        universe: List of symbols (from 'base' column)
        rebalance_days: Days between rebalances
        start_date: Start date for backtest
        end_date: End date for backtest
    
    Returns:
        Series of portfolio values over time
    """
    # Filter to universe (use 'base' column which is the coin symbol)
    df = price_df[price_df['base'].isin(universe)].copy()
    
    if start_date:
        df = df[df['date'] >= start_date]
    if end_date:
        df = df[df['date'] <= end_date]
    
    if len(df) == 0:
        return pd.Series(dtype=float)
    
    # Calculate daily returns
    df['return'] = df.groupby('base')['close'].pct_change()
    
    # Get all dates
    dates = sorted(df['date'].unique())
    
    if len(dates) == 0:
        return pd.Series(dtype=float)
    
    # Initialize portfolio
    portfolio_values = []
    portfolio_dates = []
    current_value = 100.0  # Start with $100
    
    # Rebalance dates
    rebalance_dates = [dates[i] for i in range(0, len(dates), rebalance_days)]
    
    current_holdings = {}
    last_rebalance = None
    
    for date in dates:
        # Check if rebalance day
        if date in rebalance_dates:
            # Get active symbols (have data on this date)
            active_symbols = df[df['date'] == date]['base'].tolist()
            
            if len(active_symbols) > 0:
                # Equal weight rebalance
                weight_per_coin = current_value / len(active_symbols)
                current_holdings = {sym: weight_per_coin for sym in active_symbols}
                last_rebalance = date
        
        # Apply daily returns to holdings
        if current_holdings:
            day_returns = df[df['date'] == date].set_index('base')['return']
            
            new_holdings = {}
            for sym, value in current_holdings.items():
                if sym in day_returns.index and pd.notna(day_returns[sym]):
                    new_value = value * (1 + day_returns[sym])
                    new_holdings[sym] = new_value
                else:
                    # No data for this day, maintain value
                    new_holdings[sym] = value
            
            current_holdings = new_holdings
            current_value = sum(current_holdings.values())
        
        portfolio_values.append(current_value)
        portfolio_dates.append(date)
    
    return pd.Series(portfolio_values, index=portfolio_dates)


def calculate_metrics(returns_series):
    """Calculate performance metrics."""
    if len(returns_series) < 2:
        return {}
    
    # Convert to returns
    portfolio_returns = returns_series.pct_change().dropna()
    
    if len(portfolio_returns) == 0:
        return {}
    
    # Total return
    total_return = (returns_series.iloc[-1] / returns_series.iloc[0] - 1) * 100
    
    # Annualized return (assuming daily data)
    days = len(returns_series)
    years = days / 365.25
    annualized_return = ((returns_series.iloc[-1] / returns_series.iloc[0]) ** (1 / years) - 1) * 100
    
    # Volatility (annualized)
    volatility = portfolio_returns.std() * np.sqrt(252) * 100
    
    # Sharpe ratio (assuming 0 risk-free rate)
    sharpe = (annualized_return / volatility) if volatility > 0 else 0
    
    # Max drawdown
    cummax = returns_series.cummax()
    drawdown = (returns_series - cummax) / cummax * 100
    max_drawdown = drawdown.min()
    
    # Sortino ratio (downside deviation)
    downside_returns = portfolio_returns[portfolio_returns < 0]
    downside_std = downside_returns.std() * np.sqrt(252)
    sortino = (annualized_return / 100) / downside_std if downside_std > 0 and len(downside_returns) > 0 else 0
    
    # Win rate
    win_rate = (portfolio_returns > 0).sum() / len(portfolio_returns) * 100
    
    return {
        'total_return': total_return,
        'annualized_return': annualized_return,
        'volatility': volatility,
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'num_days': days,
    }


def main():
    print("="*80)
    print("VC-BACKED PREMIUM STRATEGY BACKTEST")
    print("="*80)
    
    # Load data
    print("\n1. Loading data...")
    vc_df = load_vc_data()
    price_df = load_price_data()
    
    print(f"   ? Loaded {len(vc_df)} coins with VC data")
    print(f"   ? Loaded {len(price_df)} price records")
    
    # Categorize by VC tier
    print("\n2. Categorizing coins by VC backing...")
    vc_df = create_vc_tiers(vc_df)
    
    print("\n   VC Tier Distribution:")
    tier_counts = vc_df['vc_tier'].value_counts().sort_index()
    for tier, count in tier_counts.items():
        coins_sample = vc_df[vc_df['vc_tier'] == tier]['symbol'].tolist()[:5]
        print(f"   {tier:20s}: {count:2d} coins - {', '.join(coins_sample)}")
    
    # Define universes
    elite_vc = vc_df[vc_df['total_vc_portfolios'] >= 8]['symbol'].tolist()
    strong_vc = vc_df[vc_df['total_vc_portfolios'] >= 5]['symbol'].tolist()
    moderate_vc = vc_df[(vc_df['total_vc_portfolios'] >= 3) & (vc_df['total_vc_portfolios'] <= 4)]['symbol'].tolist()
    weak_vc = vc_df[(vc_df['total_vc_portfolios'] >= 1) & (vc_df['total_vc_portfolios'] <= 2)]['symbol'].tolist()
    
    # Market benchmark (all coins with VC data)
    market_universe = vc_df['symbol'].tolist()
    
    print(f"\n   Universe sizes:")
    print(f"   Elite VC (8+):      {len(elite_vc)} coins")
    print(f"   Strong VC (5+):     {len(strong_vc)} coins")
    print(f"   Moderate VC (3-4):  {len(moderate_vc)} coins")
    print(f"   Weak VC (1-2):      {len(weak_vc)} coins")
    print(f"   Market (all):       {len(market_universe)} coins")
    
    # Determine backtest period
    print("\n3. Determining backtest period...")
    
    # Find common date range where we have data for most coins
    date_coverage = price_df.groupby('date')['base'].nunique()
    
    # Start when we have at least 30 coins
    valid_dates = date_coverage[date_coverage >= 30].index
    if len(valid_dates) == 0:
        print("   ? Not enough price data coverage")
        return
    
    start_date = valid_dates.min()
    end_date = valid_dates.max()
    
    print(f"   Start: {start_date.strftime('%Y-%m-%d')}")
    print(f"   End:   {end_date.strftime('%Y-%m-%d')}")
    print(f"   Duration: {(end_date - start_date).days} days")
    
    # Run backtests
    print("\n4. Running backtests...")
    rebalance_days = 30  # Monthly rebalance
    
    print(f"   Rebalance frequency: {rebalance_days} days")
    
    portfolios = {}
    
    print("\n   Backtesting Elite VC (8+)...")
    portfolios['Elite VC (8+)'] = calculate_portfolio_returns(
        price_df, elite_vc, rebalance_days, start_date, end_date
    )
    
    print("   Backtesting Strong VC (5+)...")
    portfolios['Strong VC (5+)'] = calculate_portfolio_returns(
        price_df, strong_vc, rebalance_days, start_date, end_date
    )
    
    print("   Backtesting Moderate VC (3-4)...")
    portfolios['Moderate VC (3-4)'] = calculate_portfolio_returns(
        price_df, moderate_vc, rebalance_days, start_date, end_date
    )
    
    print("   Backtesting Weak VC (1-2)...")
    portfolios['Weak VC (1-2)'] = calculate_portfolio_returns(
        price_df, weak_vc, rebalance_days, start_date, end_date
    )
    
    print("   Backtesting Market Benchmark...")
    portfolios['Market Benchmark'] = calculate_portfolio_returns(
        price_df, market_universe, rebalance_days, start_date, end_date
    )
    
    # Calculate metrics
    print("\n5. Calculating performance metrics...")
    results = []
    
    for name, series in portfolios.items():
        if len(series) > 0:
            print(f"   Processing {name}: {len(series)} days")
            metrics = calculate_metrics(series)
            if metrics:  # Only add if metrics were calculated
                metrics['strategy'] = name
                results.append(metrics)
            else:
                print(f"   ??  Warning: No metrics calculated for {name}")
        else:
            print(f"   ??  Warning: No data for {name}")
    
    if len(results) == 0:
        print("\n? ERROR: No results calculated. Check if portfolios have valid data.")
        return
    
    results_df = pd.DataFrame(results)
    results_df = results_df.set_index('strategy')
    
    # Print results
    print("\n" + "="*80)
    print("BACKTEST RESULTS")
    print("="*80)
    
    if len(results_df) > 0:
        print("\nPerformance Metrics:")
        print(results_df[['total_return', 'annualized_return', 'volatility', 'sharpe_ratio', 
                          'max_drawdown', 'win_rate']].to_string())
        
        # Analysis
        print("\n" + "="*80)
        print("ANALYSIS: DO VC-BACKED COINS OUTPERFORM?")
        print("="*80)
        
        # Compare Elite vs Market
        if 'Elite VC (8+)' in results_df.index and 'Market Benchmark' in results_df.index:
            elite_return = results_df.loc['Elite VC (8+)', 'annualized_return']
            market_return = results_df.loc['Market Benchmark', 'annualized_return']
            elite_sharpe = results_df.loc['Elite VC (8+)', 'sharpe_ratio']
            market_sharpe = results_df.loc['Market Benchmark', 'sharpe_ratio']
            
            print(f"\n?? Elite VC (8+) vs Market:")
            print(f"   Elite Return:    {elite_return:+.2f}% per year")
            print(f"   Market Return:   {market_return:+.2f}% per year")
            print(f"   Outperformance:  {elite_return - market_return:+.2f}% per year")
            print(f"   ")
            print(f"   Elite Sharpe:    {elite_sharpe:.2f}")
            print(f"   Market Sharpe:   {market_sharpe:.2f}")
            
            if elite_return > market_return:
                print(f"\n   ? YES! Elite VC-backed coins OUTPERFORM by {elite_return - market_return:.2f}%/year")
            else:
                print(f"\n   ? NO! Elite VC-backed coins UNDERPERFORM by {market_return - elite_return:.2f}%/year")
        
        # Compare Strong VC vs Weak VC
        if 'Strong VC (5+)' in results_df.index and 'Weak VC (1-2)' in results_df.index:
            strong_return = results_df.loc['Strong VC (5+)', 'annualized_return']
            weak_return = results_df.loc['Weak VC (1-2)', 'annualized_return']
            
            print(f"\n?? Strong VC (5+) vs Weak VC (1-2):")
            print(f"   Strong VC Return: {strong_return:+.2f}% per year")
            print(f"   Weak VC Return:   {weak_return:+.2f}% per year")
            print(f"   Difference:       {strong_return - weak_return:+.2f}% per year")
            
            if strong_return > weak_return:
                print(f"\n   ? Strong VC backing shows {strong_return - weak_return:.2f}% premium")
            else:
                print(f"\n   ??  Weak VC coins actually outperform by {weak_return - strong_return:.2f}%")
        
        # Rank all strategies
        print(f"\n?? Strategy Ranking (by Annualized Return):")
        ranked = results_df.sort_values('annualized_return', ascending=False)
        for i, (name, row) in enumerate(ranked.iterrows(), 1):
            print(f"   {i}. {name:25s} - {row['annualized_return']:+7.2f}% (Sharpe: {row['sharpe_ratio']:.2f})")
        
        # Risk-adjusted ranking
        print(f"\n?? Strategy Ranking (by Sharpe Ratio):")
        ranked_sharpe = results_df.sort_values('sharpe_ratio', ascending=False)
        for i, (name, row) in enumerate(ranked_sharpe.iterrows(), 1):
            print(f"   {i}. {name:25s} - Sharpe: {row['sharpe_ratio']:.2f} (Return: {row['annualized_return']:+.2f}%)")
    
    # Plot results
    print("\n6. Generating performance chart...")
    
    plt.figure(figsize=(14, 8))
    
    for name, series in portfolios.items():
        if len(series) > 0:
            # Normalize to start at 100
            normalized = (series / series.iloc[0]) * 100
            plt.plot(normalized.index, normalized.values, label=name, linewidth=2)
    
    plt.title('VC-Backed Premium Strategy Backtest\nDo VC-Backed Coins Outperform?', 
              fontsize=14, fontweight='bold')
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Portfolio Value (Starting at 100)', fontsize=12)
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    output_file = "backtests/results/vc_backed_premium_performance.png"
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"   ? Chart saved: {output_file}")
    
    # Save results
    print("\n7. Saving results...")
    
    results_file = "backtests/results/vc_backed_premium_results.csv"
    results_df.to_csv(results_file)
    print(f"   ? Results saved: {results_file}")
    
    # Save portfolio time series
    portfolio_df = pd.DataFrame(portfolios)
    portfolio_file = "backtests/results/vc_backed_premium_portfolio_values.csv"
    portfolio_df.to_csv(portfolio_file)
    print(f"   ? Portfolio values saved: {portfolio_file}")
    
    print("\n" + "="*80)
    print("BACKTEST COMPLETE")
    print("="*80)
    
    # Summary conclusions
    print("\n?? KEY TAKEAWAYS:")
    
    if len(results_df) > 0:
        top_strategy = results_df.sort_values('annualized_return', ascending=False).index[0]
        top_return = results_df.loc[top_strategy, 'annualized_return']
        
        print(f"\n1. Best performing strategy: {top_strategy}")
        print(f"   Annualized return: {top_return:+.2f}%")
        
        if 'Elite VC (8+)' in results_df.index and 'Market Benchmark' in results_df.index:
            elite_vs_market = results_df.loc['Elite VC (8+)', 'annualized_return'] - results_df.loc['Market Benchmark', 'annualized_return']
            
            if elite_vs_market > 2:
                print(f"\n2. ? VC-backed premium EXISTS: +{elite_vs_market:.2f}%/year")
                print(f"   ? Top-tier VC backing is a meaningful signal")
            elif elite_vs_market > -2:
                print(f"\n2. ??  VC-backed premium is MARGINAL: {elite_vs_market:+.2f}%/year")
                print(f"   ? VC backing matters less than expected")
            else:
                print(f"\n2. ? VC-backed coins UNDERPERFORM: {elite_vs_market:+.2f}%/year")
                print(f"   ? Avoid overweighting VC-backed coins")
        
        print(f"\n3. Recommendation:")
        if top_strategy.startswith('Elite') or top_strategy.startswith('Strong'):
            print(f"   ? USE VC-backed premium factor in portfolio")
            print(f"   ? Overweight coins with 5+ VCs")
        else:
            print(f"   ? DO NOT use VC-backed premium factor")
            print(f"   ? Other factors more important than VC backing")
    
    print()


if __name__ == "__main__":
    main()
