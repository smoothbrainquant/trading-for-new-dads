#!/usr/bin/env python3
"""
Dilution Factor Strategy Backtest

Strategy:
- Long top 10 coins with LOWEST dilution (most deflationary/stable supply)
- Short top 10 coins with HIGHEST dilution (most aggressive unlocks)
- Risk parity weighting: equal risk contribution from each position
- Monthly rebalancing based on rolling dilution velocity
- Universe: Top 150 coins by market cap

Hypothesis: Coins with low dilution outperform high dilution coins
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os


def load_historical_price_data():
    """
    Load historical price data from coinbase/coinmarketcap combined data.
    
    Returns:
        pd.DataFrame: Historical price data with returns
    """
    # Try multiple possible file locations
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
    
    # Parse date
    df['date'] = pd.to_datetime(df['date'])
    
    # Filter to 2021 onwards
    df = df[df['date'] >= '2021-01-01'].copy()
    
    # Calculate daily returns (next day for proper lag)
    df = df.sort_values(['base', 'date'])
    df['return'] = df.groupby('base')['close'].pct_change()
    df['return_next'] = df.groupby('base')['return'].shift(-1)  # Next day return
    
    print(f"Loaded price data: {len(df)} records, {df['base'].nunique()} coins")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    
    return df


def load_dilution_velocity_data():
    """
    Load dilution velocity data calculated from historical analysis.
    
    Returns:
        pd.DataFrame: Dilution velocity by coin
    """
    velocity_file = 'crypto_dilution_velocity_2021_2025.csv'
    if not os.path.exists(velocity_file):
        velocity_file = '/workspace/crypto_dilution_velocity_2021_2025.csv'
    
    df = pd.read_csv(velocity_file)
    print(f"Loaded dilution velocity for {len(df)} coins")
    
    return df


def load_historical_dilution_snapshots():
    """
    Load historical monthly dilution snapshots to calculate rolling dilution.
    
    Returns:
        pd.DataFrame: Historical dilution metrics by date
    """
    hist_file = 'crypto_dilution_historical_2021_2025.csv'
    if not os.path.exists(hist_file):
        hist_file = '/workspace/crypto_dilution_historical_2021_2025.csv'
    
    df = pd.read_csv(hist_file)
    df['date'] = pd.to_datetime(df['date'])
    
    print(f"Loaded historical dilution: {len(df)} records, {df['Symbol'].nunique()} coins")
    
    return df


def calculate_rolling_dilution_signal(historical_dilution_df, lookback_months=12):
    """
    Calculate rolling dilution velocity for each coin at each rebalance date.
    
    Args:
        historical_dilution_df (pd.DataFrame): Historical dilution snapshots
        lookback_months (int): Lookback period for calculating velocity
        
    Returns:
        pd.DataFrame: Rolling dilution signals by date and symbol
    """
    signals = []
    
    # Get unique rebalance dates (monthly snapshots)
    rebalance_dates = sorted(historical_dilution_df['date'].unique())
    
    for rebal_date in rebalance_dates:
        # Get lookback window
        lookback_start = rebal_date - pd.DateOffset(months=lookback_months)
        
        # Get data in window
        window_data = historical_dilution_df[
            (historical_dilution_df['date'] >= lookback_start) &
            (historical_dilution_df['date'] <= rebal_date)
        ].copy()
        
        # Calculate velocity for each coin
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
            
            # Calculate circulation % change
            circ_pct_change = last['circulating_pct'] - first['circulating_pct']
            dilution_velocity = circ_pct_change / years_elapsed if years_elapsed > 0 else 0
            
            # Get market cap and rank
            market_cap = last['Market Cap']
            rank = last['Rank']
            price = last['Price']
            
            signals.append({
                'date': rebal_date,
                'symbol': symbol,
                'dilution_velocity': dilution_velocity,
                'market_cap': market_cap,
                'rank': rank,
                'price': price,
                'circulating_pct': last['circulating_pct']
            })
    
    signals_df = pd.DataFrame(signals)
    print(f"Calculated rolling dilution signals: {len(signals_df)} records")
    
    return signals_df


def calculate_volatility(price_df, symbol, end_date, lookback_days=90):
    """
    Calculate historical volatility for a symbol.
    
    Args:
        price_df (pd.DataFrame): Price data
        symbol (str): Coin symbol
        end_date (pd.Timestamp): End date for calculation
        lookback_days (int): Lookback period
        
    Returns:
        float: Annualized volatility
    """
    lookback_start = end_date - pd.DateOffset(days=lookback_days)
    
    coin_data = price_df[
        (price_df['base'] == symbol) &
        (price_df['date'] >= lookback_start) &
        (price_df['date'] <= end_date)
    ].copy()
    
    if len(coin_data) < 20:  # Need minimum data
        return np.nan
    
    # Calculate annualized volatility
    returns = coin_data['return'].dropna()
    volatility = returns.std() * np.sqrt(365)  # Annualize daily volatility
    
    return volatility


def construct_risk_parity_portfolio(signals, price_df, rebal_date, top_n=10):
    """
    Construct risk parity weighted long/short portfolio.
    
    Args:
        signals (pd.DataFrame): Dilution signals for the date
        price_df (pd.DataFrame): Price data for volatility calculation
        rebal_date (pd.Timestamp): Rebalancing date
        top_n (int): Number of long and short positions
        
    Returns:
        dict: Portfolio weights by symbol
    """
    # Filter to coins with valid dilution data
    valid_signals = signals[signals['dilution_velocity'].notna()].copy()
    
    # Filter to top 150 by market cap
    valid_signals = valid_signals.nsmallest(150, 'rank')
    
    if len(valid_signals) < top_n * 2:
        return {}
    
    # *** FIX: Filter to coins with price data BEFORE selecting top/bottom ***
    # Get list of coins with sufficient price data
    available_coins = price_df['base'].unique()
    valid_signals = valid_signals[valid_signals['symbol'].isin(available_coins)]
    
    # Pre-calculate volatility for all candidates
    valid_signals['volatility'] = valid_signals['symbol'].apply(
        lambda s: calculate_volatility(price_df, s, rebal_date)
    )
    
    # Keep only coins with valid volatility (sufficient price history)
    valid_signals = valid_signals[valid_signals['volatility'].notna()]
    
    # Dynamically adjust position count based on available coins
    # Need at least 4 coins total (2 long + 2 short minimum)
    if len(valid_signals) < 4:
        print(f"  Warning: Only {len(valid_signals)} coins with valid data (need minimum 4)")
        return {}
    
    # Adjust top_n if we don't have enough coins
    # Each side needs at least 1, ideally top_n
    adjusted_top_n = min(top_n, len(valid_signals) // 2)
    
    if adjusted_top_n < top_n:
        print(f"  Note: Adjusted to {adjusted_top_n} positions per side (have {len(valid_signals)} valid coins)")
    
    # Sort by dilution velocity
    valid_signals = valid_signals.sort_values('dilution_velocity')
    
    # Select long (lowest dilution) and short (highest dilution)
    long_candidates = valid_signals.head(adjusted_top_n).copy()
    short_candidates = valid_signals.tail(adjusted_top_n).copy()
    
    if len(long_candidates) == 0 or len(short_candidates) == 0:
        return {}
    
    # Risk parity: weight inversely proportional to volatility
    # Each position gets equal risk contribution
    
    # Calculate inverse volatility weights (volatility already calculated)
    long_candidates['inv_vol'] = 1.0 / long_candidates['volatility']
    short_candidates['inv_vol'] = 1.0 / short_candidates['volatility']
    
    # Normalize to sum to 1 for long and -1 for short
    long_total_inv_vol = long_candidates['inv_vol'].sum()
    short_total_inv_vol = short_candidates['inv_vol'].sum()
    
    long_candidates['weight'] = long_candidates['inv_vol'] / long_total_inv_vol
    short_candidates['weight'] = -short_candidates['inv_vol'] / short_total_inv_vol
    
    # Combine into portfolio
    portfolio = {}
    
    for _, row in long_candidates.iterrows():
        portfolio[row['symbol']] = {
            'weight': row['weight'],
            'side': 'long',
            'dilution_velocity': row['dilution_velocity'],
            'volatility': row['volatility']
        }
    
    for _, row in short_candidates.iterrows():
        portfolio[row['symbol']] = {
            'weight': row['weight'],
            'side': 'short',
            'dilution_velocity': row['dilution_velocity'],
            'volatility': row['volatility']
        }
    
    return portfolio


def backtest_dilution_factor(signals_df, price_df, rebalance_freq='M', top_n=10):
    """
    Backtest the dilution factor strategy.
    
    Args:
        signals_df (pd.DataFrame): Rolling dilution signals
        price_df (pd.DataFrame): Price data with returns
        rebalance_freq (str): Rebalancing frequency ('M' for monthly)
        top_n (int): Number of long and short positions
        
    Returns:
        tuple: (portfolio_values, trades, metrics)
    """
    # Get rebalance dates
    rebalance_dates = sorted(signals_df['date'].unique())
    
    portfolio_history = []
    trades = []
    
    current_portfolio = {}
    portfolio_value = 1.0  # Start with $1
    
    for i, rebal_date in enumerate(rebalance_dates):
        print(f"Rebalancing {i+1}/{len(rebalance_dates)}: {rebal_date.date()}")
        
        # Get signals for this date
        date_signals = signals_df[signals_df['date'] == rebal_date].copy()
        
        # Construct new portfolio
        new_portfolio = construct_risk_parity_portfolio(
            date_signals, price_df, rebal_date, top_n=top_n
        )
        
        if len(new_portfolio) == 0:
            print(f"  Warning: No valid portfolio for {rebal_date.date()}")
            continue
        
        # Record trades
        all_symbols = set(list(current_portfolio.keys()) + list(new_portfolio.keys()))
        for symbol in all_symbols:
            old_weight = current_portfolio.get(symbol, {}).get('weight', 0)
            new_weight = new_portfolio.get(symbol, {}).get('weight', 0)
            
            if abs(new_weight - old_weight) > 0.001:  # Significant change
                trades.append({
                    'date': rebal_date,
                    'symbol': symbol,
                    'old_weight': old_weight,
                    'new_weight': new_weight,
                    'trade': new_weight - old_weight
                })
        
        # Calculate returns until next rebalance
        if i < len(rebalance_dates) - 1:
            next_rebal = rebalance_dates[i + 1]
        else:
            next_rebal = price_df['date'].max()
        
        # Get daily returns for holding period
        holding_period = price_df[
            (price_df['date'] > rebal_date) &
            (price_df['date'] <= next_rebal)
        ].copy()
        
        # Calculate portfolio returns for each day
        for date in sorted(holding_period['date'].unique()):
            daily_returns = holding_period[holding_period['date'] == date]
            
            # Calculate portfolio return for this day
            portfolio_return = 0.0
            valid_positions = 0
            
            for symbol, position in new_portfolio.items():
                symbol_return = daily_returns[daily_returns['base'] == symbol]['return'].values
                
                if len(symbol_return) > 0 and not np.isnan(symbol_return[0]):
                    portfolio_return += position['weight'] * symbol_return[0]
                    valid_positions += 1
            
            # Only update if we have valid returns
            if valid_positions > 0:
                portfolio_value *= (1 + portfolio_return)
                
                portfolio_history.append({
                    'date': date,
                    'portfolio_value': portfolio_value,
                    'return': portfolio_return,
                    'n_positions': len(new_portfolio),
                    'n_long': sum(1 for p in new_portfolio.values() if p['side'] == 'long'),
                    'n_short': sum(1 for p in new_portfolio.values() if p['side'] == 'short')
                })
        
        current_portfolio = new_portfolio
    
    portfolio_df = pd.DataFrame(portfolio_history)
    trades_df = pd.DataFrame(trades)
    
    # Calculate metrics
    if len(portfolio_df) > 0:
        metrics = calculate_performance_metrics(portfolio_df)
    else:
        metrics = {}
    
    return portfolio_df, trades_df, metrics


def calculate_performance_metrics(portfolio_df):
    """
    Calculate performance metrics for the strategy.
    
    Args:
        portfolio_df (pd.DataFrame): Portfolio values over time
        
    Returns:
        dict: Performance metrics
    """
    if len(portfolio_df) == 0:
        return {}
    
    # Total return
    total_return = (portfolio_df['portfolio_value'].iloc[-1] / portfolio_df['portfolio_value'].iloc[0] - 1) * 100
    
    # Annualized return
    days = (portfolio_df['date'].max() - portfolio_df['date'].min()).days
    years = days / 365.25
    annualized_return = ((portfolio_df['portfolio_value'].iloc[-1] / portfolio_df['portfolio_value'].iloc[0]) ** (1/years) - 1) * 100
    
    # Volatility
    daily_returns = portfolio_df['return'].dropna()
    volatility = daily_returns.std() * np.sqrt(365) * 100
    
    # Sharpe ratio (assuming 0% risk-free rate)
    sharpe = annualized_return / volatility if volatility > 0 else 0
    
    # Max drawdown
    cumulative = portfolio_df['portfolio_value']
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max * 100
    max_drawdown = drawdown.min()
    
    # Win rate
    win_rate = (daily_returns > 0).sum() / len(daily_returns) * 100 if len(daily_returns) > 0 else 0
    
    metrics = {
        'total_return_pct': total_return,
        'annualized_return_pct': annualized_return,
        'volatility_pct': volatility,
        'sharpe_ratio': sharpe,
        'max_drawdown_pct': max_drawdown,
        'win_rate_pct': win_rate,
        'n_days': len(portfolio_df),
        'start_date': portfolio_df['date'].min(),
        'end_date': portfolio_df['date'].max()
    }
    
    return metrics


def plot_backtest_results(portfolio_df, metrics, trades_df):
    """
    Plot backtest results.
    
    Args:
        portfolio_df (pd.DataFrame): Portfolio values
        metrics (dict): Performance metrics
        trades_df (pd.DataFrame): Trade history
    """
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))
    
    # Plot 1: Portfolio value
    ax1 = axes[0]
    ax1.plot(portfolio_df['date'], portfolio_df['portfolio_value'], 
            linewidth=2, color='blue', label='Dilution Factor Strategy')
    ax1.set_ylabel('Portfolio Value ($)', fontsize=12)
    ax1.set_title('Dilution Factor Long/Short Strategy - Risk Parity Weighted', 
                 fontsize=14, fontweight='bold')
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=10)
    
    # Add metrics text
    metrics_text = f"""Total Return: {metrics['total_return_pct']:.1f}%
Annualized: {metrics['annualized_return_pct']:.1f}%
Sharpe: {metrics['sharpe_ratio']:.2f}
Max DD: {metrics['max_drawdown_pct']:.1f}%
Volatility: {metrics['volatility_pct']:.1f}%"""
    
    ax1.text(0.02, 0.98, metrics_text, transform=ax1.transAxes,
            fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    # Plot 2: Drawdown
    ax2 = axes[1]
    cumulative = portfolio_df['portfolio_value']
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max * 100
    
    ax2.fill_between(portfolio_df['date'], drawdown, 0, alpha=0.3, color='red')
    ax2.plot(portfolio_df['date'], drawdown, linewidth=1, color='darkred')
    ax2.set_ylabel('Drawdown (%)', fontsize=12)
    ax2.set_title('Strategy Drawdown', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    
    # Plot 3: Rolling returns
    ax3 = axes[2]
    portfolio_df['rolling_return_30d'] = portfolio_df['return'].rolling(30).sum() * 100
    ax3.plot(portfolio_df['date'], portfolio_df['rolling_return_30d'], 
            linewidth=1.5, color='green', alpha=0.7)
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=1, alpha=0.3)
    ax3.set_ylabel('30-Day Rolling Return (%)', fontsize=12)
    ax3.set_xlabel('Date', fontsize=12)
    ax3.set_title('Rolling 30-Day Returns', fontsize=12, fontweight='bold')
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('dilution_factor_backtest_results.png', dpi=300, bbox_inches='tight')
    print(f"? Saved: dilution_factor_backtest_results.png")
    plt.close()


def save_backtest_results(portfolio_df, trades_df, metrics):
    """
    Save backtest results to CSV files.
    
    Args:
        portfolio_df (pd.DataFrame): Portfolio values
        trades_df (pd.DataFrame): Trade history
        metrics (dict): Performance metrics
    """
    # Save portfolio values
    portfolio_df.to_csv('dilution_factor_portfolio_values.csv', index=False)
    print(f"? Saved: dilution_factor_portfolio_values.csv")
    
    # Save trades
    if len(trades_df) > 0:
        trades_df.to_csv('dilution_factor_trades.csv', index=False)
        print(f"? Saved: dilution_factor_trades.csv")
    
    # Save metrics
    metrics_df = pd.DataFrame([metrics])
    metrics_df.to_csv('dilution_factor_metrics.csv', index=False)
    print(f"? Saved: dilution_factor_metrics.csv")


def main():
    """Main execution function."""
    print("=" * 80)
    print("DILUTION FACTOR STRATEGY BACKTEST")
    print("=" * 80)
    print("\nStrategy:")
    print("  - Long top 10 coins with LOWEST dilution")
    print("  - Short top 10 coins with HIGHEST dilution")
    print("  - Risk parity weighting (inverse volatility)")
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
    
    # Run backtest
    print("\n" + "-" * 80)
    print("RUNNING BACKTEST")
    print("-" * 80)
    
    portfolio_df, trades_df, metrics = backtest_dilution_factor(
        signals_df, price_df, rebalance_freq='M', top_n=10
    )
    
    # Print results
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS")
    print("=" * 80)
    
    if len(metrics) > 0:
        print(f"\nPeriod: {metrics['start_date'].date()} to {metrics['end_date'].date()}")
        print(f"Trading days: {metrics['n_days']}")
        print(f"\nPerformance:")
        print(f"  Total Return:       {metrics['total_return_pct']:>8.2f}%")
        print(f"  Annualized Return:  {metrics['annualized_return_pct']:>8.2f}%")
        print(f"  Volatility:         {metrics['volatility_pct']:>8.2f}%")
        print(f"  Sharpe Ratio:       {metrics['sharpe_ratio']:>8.2f}")
        print(f"  Max Drawdown:       {metrics['max_drawdown_pct']:>8.2f}%")
        print(f"  Win Rate:           {metrics['win_rate_pct']:>8.2f}%")
        
        print(f"\nTotal trades: {len(trades_df)}")
    else:
        print("ERROR: No results generated")
        return
    
    # Plot results
    print("\n" + "-" * 80)
    print("GENERATING VISUALIZATIONS")
    print("-" * 80)
    
    plot_backtest_results(portfolio_df, metrics, trades_df)
    
    # Save results
    print("\n" + "-" * 80)
    print("SAVING RESULTS")
    print("-" * 80)
    
    save_backtest_results(portfolio_df, trades_df, metrics)
    
    print("\n" + "=" * 80)
    print("BACKTEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
