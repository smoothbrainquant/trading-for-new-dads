"""
Backtest for Skew Factor Strategy

This script backtests a skew factor strategy that:
1. Calculates 30-day rolling skewness of returns for all cryptocurrencies
2. Ranks coins by skewness (low to high)
3. Creates long/short portfolios:
   - Long: Bottom quintile (20% with most negative skewness)
   - Short: Top quintile (20% with most positive skewness)
4. Equal weight within each quintile
5. Dollar neutral (100% long, 100% short)
6. Daily rebalancing

Hypothesis: Skewness patterns (extreme negative or positive return distributions)
may predict future returns through mean reversion or risk premium effects.
"""

import pandas as pd
import numpy as np
from scipy.stats import skew
from datetime import datetime
import argparse
import matplotlib.pyplot as plt
import seaborn as sns


def load_data(filepath):
    """
    Load historical OHLCV data from CSV file.
    
    Args:
        filepath (str): Path to CSV file with OHLCV data
        
    Returns:
        pd.DataFrame: DataFrame with date, symbol, open, high, low, close, volume, market_cap
    """
    df = pd.read_csv(filepath)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    return df


def calculate_skewness(data, lookback_window=30, min_volume=5_000_000, min_market_cap=50_000_000):
    """
    Calculate rolling skewness for all cryptocurrencies with filters.
    
    Args:
        data (pd.DataFrame): Historical OHLCV data
        lookback_window (int): Window for calculating skewness (default 30 days)
        min_volume (float): Minimum 30-day average volume in USD
        min_market_cap (float): Minimum market cap in USD
        
    Returns:
        pd.DataFrame: Data with skewness and filters applied
    """
    df = data.copy()
    
    # Calculate daily log returns
    df['returns'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Calculate 30-day rolling skewness (shifted to avoid look-ahead bias)
    df['skewness_30d'] = df.groupby('symbol')['returns'].transform(
        lambda x: x.rolling(window=lookback_window, min_periods=lookback_window)
                   .apply(lambda y: skew(y, nan_policy='omit'), raw=False)
                   .shift(1)  # Shift to avoid look-ahead bias
    )
    
    # Calculate 30-day average volume (shifted)
    df['volume_30d_avg'] = df.groupby('symbol')['volume'].transform(
        lambda x: x.rolling(window=30, min_periods=30).mean().shift(1)
    )
    
    # Shift market cap to avoid look-ahead bias
    df['market_cap_shifted'] = df.groupby('symbol')['market_cap'].shift(1)
    
    # Apply filters
    df['passes_volume_filter'] = df['volume_30d_avg'] >= min_volume
    df['passes_marketcap_filter'] = df['market_cap_shifted'] >= min_market_cap
    df['passes_data_filter'] = df['skewness_30d'].notna()
    
    df['passes_all_filters'] = (
        df['passes_volume_filter'] & 
        df['passes_marketcap_filter'] & 
        df['passes_data_filter']
    )
    
    # Calculate forward returns for analysis (shifted -1 for next-day returns)
    df['forward_return'] = df.groupby('symbol')['returns'].shift(-1)
    
    # Replace inf values with NaN
    df = df.replace([np.inf, -np.inf], np.nan)
    
    return df


def generate_signals(data, num_quintiles=5):
    """
    Generate long/short signals based on skewness quintiles.
    
    Args:
        data (pd.DataFrame): Data with skewness calculated
        num_quintiles (int): Number of quintiles for ranking (default 5)
        
    Returns:
        pd.DataFrame: Data with signals added
    """
    df = data.copy()
    
    # For each date, rank coins by skewness among those passing filters
    def rank_by_skewness(group):
        # Filter to valid coins
        valid = group[group['passes_all_filters']].copy()
        
        if len(valid) < num_quintiles * 2:  # Need at least 2 coins per quintile
            valid['quintile'] = np.nan
            valid['signal'] = 0
        else:
            # Rank by skewness (lowest to highest)
            valid = valid.sort_values('skewness_30d')
            
            # Assign quintiles
            valid['quintile'] = pd.qcut(
                range(len(valid)), 
                q=num_quintiles, 
                labels=range(1, num_quintiles + 1),
                duplicates='drop'
            )
            
            # Generate signals
            # Long: Bottom quintile (most negative skewness)
            # Short: Top quintile (most positive skewness)
            valid['signal'] = 0
            valid.loc[valid['quintile'] == 1, 'signal'] = 1  # Long
            valid.loc[valid['quintile'] == num_quintiles, 'signal'] = -1  # Short
        
        return valid
    
    # Apply ranking by date
    df_with_signals = df.groupby('date', group_keys=False).apply(rank_by_skewness)
    
    return df_with_signals


def calculate_portfolio_weights(signals_df, date):
    """
    Calculate equal-weight portfolio weights for a given date.
    
    Args:
        signals_df (pd.DataFrame): DataFrame with signals
        date (datetime): Date to calculate weights for
        
    Returns:
        dict: Dictionary mapping symbols to weights
    """
    date_data = signals_df[signals_df['date'] == date]
    
    # Get long and short symbols
    long_symbols = date_data[date_data['signal'] == 1]['symbol'].tolist()
    short_symbols = date_data[date_data['signal'] == -1]['symbol'].tolist()
    
    weights = {}
    
    # Equal weight within each side
    if len(long_symbols) > 0:
        long_weight = 1.0 / len(long_symbols)
        for symbol in long_symbols:
            weights[symbol] = long_weight
    
    if len(short_symbols) > 0:
        short_weight = -1.0 / len(short_symbols)
        for symbol in short_symbols:
            weights[symbol] = short_weight
    
    return weights


def backtest_strategy(
    signals_df,
    start_date=None,
    end_date=None,
    initial_capital=10000
):
    """
    Run backtest for the skew factor strategy.
    
    Args:
        signals_df (pd.DataFrame): DataFrame with signals and returns
        start_date (str): Start date for backtest (format: 'YYYY-MM-DD')
        end_date (str): End date for backtest (format: 'YYYY-MM-DD')
        initial_capital (float): Initial portfolio capital
        
    Returns:
        dict: Dictionary containing backtest results
    """
    df = signals_df.copy()
    
    # Filter by date range
    if start_date:
        df = df[df['date'] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df['date'] <= pd.to_datetime(end_date)]
    
    # Get unique dates
    all_dates = sorted(df['date'].unique())
    
    # Need at least 31 days for initial skewness calculation
    if len(all_dates) < 31:
        raise ValueError(f"Insufficient data. Need at least 31 days, have {len(all_dates)}")
    
    print(f"\nBacktest Configuration:")
    print(f"  Period: {all_dates[0].date()} to {all_dates[-1].date()}")
    print(f"  Trading days: {len(all_dates)}")
    print(f"  Initial capital: ${initial_capital:,.2f}")
    print("=" * 80)
    
    # Initialize tracking
    portfolio_history = []
    current_capital = initial_capital
    previous_weights = {}
    
    for i, current_date in enumerate(all_dates):
        # Get today's data
        today_data = df[df['date'] == current_date]
        
        # Calculate portfolio weights
        current_weights = calculate_portfolio_weights(df, current_date)
        
        # Calculate portfolio return using forward returns
        portfolio_return = 0.0
        long_return = 0.0
        short_return = 0.0
        
        if current_weights:
            for symbol, weight in current_weights.items():
                symbol_data = today_data[today_data['symbol'] == symbol]
                
                if not symbol_data.empty:
                    forward_ret = symbol_data['forward_return'].values[0]
                    
                    if not np.isnan(forward_ret):
                        portfolio_return += weight * forward_ret
                        
                        if weight > 0:
                            long_return += weight * forward_ret
                        else:
                            short_return += weight * forward_ret
        
        # Update capital (using log returns)
        if not np.isnan(portfolio_return):
            current_capital = current_capital * np.exp(portfolio_return)
        
        # Calculate turnover
        turnover = 0.0
        if previous_weights:
            all_symbols = set(current_weights.keys()) | set(previous_weights.keys())
            for symbol in all_symbols:
                old_weight = previous_weights.get(symbol, 0)
                new_weight = current_weights.get(symbol, 0)
                turnover += abs(new_weight - old_weight)
            turnover = turnover / 2  # Divide by 2 for one-way turnover
        
        # Calculate exposures
        long_exposure = sum(w for w in current_weights.values() if w > 0)
        short_exposure = abs(sum(w for w in current_weights.values() if w < 0))
        net_exposure = sum(current_weights.values())
        gross_exposure = long_exposure + short_exposure
        
        # Record metrics
        portfolio_history.append({
            'date': current_date,
            'portfolio_value': current_capital,
            'daily_return': portfolio_return,
            'long_return': long_return,
            'short_return': short_return,
            'turnover': turnover,
            'num_long': len([w for w in current_weights.values() if w > 0]),
            'num_short': len([w for w in current_weights.values() if w < 0]),
            'long_exposure': long_exposure,
            'short_exposure': short_exposure,
            'net_exposure': net_exposure,
            'gross_exposure': gross_exposure
        })
        
        previous_weights = current_weights.copy()
        
        # Progress update
        if (i + 1) % 100 == 0 or i == len(all_dates) - 1:
            print(f"Progress: {i+1}/{len(all_dates)} days | "
                  f"Date: {current_date.date()} | "
                  f"Value: ${current_capital:,.2f} | "
                  f"Long: {len([w for w in current_weights.values() if w > 0])} | "
                  f"Short: {len([w for w in current_weights.values() if w < 0])}")
    
    # Convert to DataFrame
    portfolio_df = pd.DataFrame(portfolio_history)
    
    # Calculate performance metrics
    metrics = calculate_performance_metrics(portfolio_df, initial_capital)
    
    return {
        'portfolio_values': portfolio_df,
        'metrics': metrics,
        'signals_df': signals_df
    }


def calculate_performance_metrics(portfolio_df, initial_capital):
    """
    Calculate performance metrics for the backtest.
    
    Args:
        portfolio_df (pd.DataFrame): DataFrame with portfolio values over time
        initial_capital (float): Initial portfolio capital
        
    Returns:
        dict: Dictionary of performance metrics
    """
    # Total return
    final_value = portfolio_df['portfolio_value'].iloc[-1]
    total_return = (final_value - initial_capital) / initial_capital
    
    # Annualized return
    num_days = len(portfolio_df)
    years = num_days / 365.25
    annualized_return = (final_value / initial_capital) ** (1 / years) - 1 if years > 0 else 0
    
    # Volatility (annualized from log returns)
    daily_returns = portfolio_df['daily_return'].dropna()
    daily_vol = daily_returns.std()
    annualized_vol = daily_vol * np.sqrt(365)
    
    # Sharpe ratio (assuming 0% risk-free rate)
    sharpe_ratio = annualized_return / annualized_vol if annualized_vol > 0 else 0
    
    # Sortino ratio (downside deviation)
    negative_returns = daily_returns[daily_returns < 0]
    downside_vol = negative_returns.std() * np.sqrt(365) if len(negative_returns) > 0 else annualized_vol
    sortino_ratio = annualized_return / downside_vol if downside_vol > 0 else 0
    
    # Maximum drawdown
    portfolio_df['cumulative'] = (1 + portfolio_df['daily_return'].fillna(0)).cumprod()
    portfolio_df['running_max'] = portfolio_df['cumulative'].expanding().max()
    portfolio_df['drawdown'] = (portfolio_df['cumulative'] - portfolio_df['running_max']) / portfolio_df['running_max']
    max_drawdown = portfolio_df['drawdown'].min()
    
    # Calmar ratio
    calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
    
    # Win rate
    positive_days = (daily_returns > 0).sum()
    total_trading_days = len(daily_returns)
    win_rate = positive_days / total_trading_days if total_trading_days > 0 else 0
    
    # Average turnover
    avg_turnover = portfolio_df['turnover'].mean()
    
    # Long/Short analysis
    long_returns = portfolio_df['long_return'].dropna()
    short_returns = portfolio_df['short_return'].dropna()
    
    long_total_return = (np.exp(long_returns.sum()) - 1) if len(long_returns) > 0 else 0
    short_total_return = (np.exp(short_returns.sum()) - 1) if len(short_returns) > 0 else 0
    
    long_sharpe = (long_returns.mean() / long_returns.std() * np.sqrt(365)) if len(long_returns) > 0 and long_returns.std() > 0 else 0
    short_sharpe = (short_returns.mean() / short_returns.std() * np.sqrt(365)) if len(short_returns) > 0 and short_returns.std() > 0 else 0
    
    # Average positions and exposures
    avg_long_positions = portfolio_df['num_long'].mean()
    avg_short_positions = portfolio_df['num_short'].mean()
    avg_long_exposure = portfolio_df['long_exposure'].mean()
    avg_short_exposure = portfolio_df['short_exposure'].mean()
    avg_net_exposure = portfolio_df['net_exposure'].mean()
    avg_gross_exposure = portfolio_df['gross_exposure'].mean()
    
    metrics = {
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'annualized_return': annualized_return,
        'annualized_volatility': annualized_vol,
        'sharpe_ratio': sharpe_ratio,
        'sortino_ratio': sortino_ratio,
        'max_drawdown': max_drawdown,
        'calmar_ratio': calmar_ratio,
        'win_rate': win_rate,
        'num_days': num_days,
        'avg_turnover': avg_turnover,
        'long_total_return': long_total_return,
        'short_total_return': short_total_return,
        'long_sharpe': long_sharpe,
        'short_sharpe': short_sharpe,
        'avg_long_positions': avg_long_positions,
        'avg_short_positions': avg_short_positions,
        'avg_long_exposure': avg_long_exposure,
        'avg_short_exposure': avg_short_exposure,
        'avg_net_exposure': avg_net_exposure,
        'avg_gross_exposure': avg_gross_exposure
    }
    
    return metrics


def print_results(results):
    """
    Print backtest results in a formatted manner.
    
    Args:
        results (dict): Dictionary containing backtest results
    """
    metrics = results['metrics']
    
    print("\n" + "=" * 80)
    print("SKEW FACTOR BACKTEST RESULTS")
    print("=" * 80)
    
    print(f"\nPortfolio Performance:")
    print(f"  Initial Capital:        ${metrics['initial_capital']:>15,.2f}")
    print(f"  Final Value:            ${metrics['final_value']:>15,.2f}")
    print(f"  Total Return:           {metrics['total_return']:>15.2%}")
    print(f"  Annualized Return:      {metrics['annualized_return']:>15.2%}")
    
    print(f"\nRisk Metrics:")
    print(f"  Annualized Volatility:  {metrics['annualized_volatility']:>15.2%}")
    print(f"  Sharpe Ratio:           {metrics['sharpe_ratio']:>15.2f}")
    print(f"  Sortino Ratio:          {metrics['sortino_ratio']:>15.2f}")
    print(f"  Maximum Drawdown:       {metrics['max_drawdown']:>15.2%}")
    print(f"  Calmar Ratio:           {metrics['calmar_ratio']:>15.2f}")
    
    print(f"\nTrading Statistics:")
    print(f"  Win Rate:               {metrics['win_rate']:>15.2%}")
    print(f"  Trading Days:           {metrics['num_days']:>15,.0f}")
    print(f"  Avg Turnover:           {metrics['avg_turnover']:>15.2%}")
    print(f"  Avg Long Positions:     {metrics['avg_long_positions']:>15.1f}")
    print(f"  Avg Short Positions:    {metrics['avg_short_positions']:>15.1f}")
    
    print(f"\nLong/Short Analysis:")
    print(f"  Long Total Return:      {metrics['long_total_return']:>15.2%}")
    print(f"  Short Total Return:     {metrics['short_total_return']:>15.2%}")
    print(f"  Long Sharpe Ratio:      {metrics['long_sharpe']:>15.2f}")
    print(f"  Short Sharpe Ratio:     {metrics['short_sharpe']:>15.2f}")
    
    print(f"\nExposure Statistics:")
    print(f"  Avg Long Exposure:      {metrics['avg_long_exposure']:>15.2%}")
    print(f"  Avg Short Exposure:     {metrics['avg_short_exposure']:>15.2%}")
    print(f"  Avg Net Exposure:       {metrics['avg_net_exposure']:>15.2%}")
    print(f"  Avg Gross Exposure:     {metrics['avg_gross_exposure']:>15.2%}")
    
    print("\n" + "=" * 80)


def create_visualizations(results, output_dir='backtests/results'):
    """
    Create visualizations for backtest results.
    
    Args:
        results (dict): Dictionary containing backtest results
        output_dir (str): Directory to save visualizations
    """
    portfolio_df = results['portfolio_values']
    
    # Set style
    sns.set_style('darkgrid')
    
    # 1. Equity Curve
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(portfolio_df['date'], portfolio_df['portfolio_value'], linewidth=2, color='#2E86AB')
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Portfolio Value ($)', fontsize=12)
    ax.set_title('Skew Factor Strategy - Equity Curve', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/skew_factor_equity_curve.png', dpi=300, bbox_inches='tight')
    print(f"\nSaved: {output_dir}/skew_factor_equity_curve.png")
    plt.close()
    
    # 2. Drawdown Chart
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.fill_between(portfolio_df['date'], portfolio_df['drawdown'] * 100, 0, 
                     color='#A23B72', alpha=0.6)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Drawdown (%)', fontsize=12)
    ax.set_title('Skew Factor Strategy - Drawdown', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/skew_factor_drawdown.png', dpi=300, bbox_inches='tight')
    print(f"Saved: {output_dir}/skew_factor_drawdown.png")
    plt.close()
    
    # 3. Long vs Short Returns
    fig, ax = plt.subplots(figsize=(12, 6))
    portfolio_df['long_cumulative'] = (1 + portfolio_df['long_return'].fillna(0)).cumprod()
    portfolio_df['short_cumulative'] = (1 + portfolio_df['short_return'].fillna(0)).cumprod()
    
    ax.plot(portfolio_df['date'], portfolio_df['long_cumulative'], 
            label='Long Portfolio', linewidth=2, color='#06A77D')
    ax.plot(portfolio_df['date'], portfolio_df['short_cumulative'], 
            label='Short Portfolio', linewidth=2, color='#D62246')
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Cumulative Return', fontsize=12)
    ax.set_title('Long vs Short Portfolio Performance', fontsize=14, fontweight='bold')
    ax.legend(loc='best', fontsize=11)
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/skew_factor_long_short_comparison.png', dpi=300, bbox_inches='tight')
    print(f"Saved: {output_dir}/skew_factor_long_short_comparison.png")
    plt.close()
    
    # 4. Skewness Distribution
    signals_df = results['signals_df']
    signals_with_skew = signals_df[signals_df['skewness_30d'].notna()]
    
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.hist(signals_with_skew['skewness_30d'], bins=50, color='#F18F01', 
            alpha=0.7, edgecolor='black')
    ax.set_xlabel('30-Day Skewness', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title('Distribution of 30-Day Return Skewness', fontsize=14, fontweight='bold')
    ax.axvline(x=0, color='red', linestyle='--', linewidth=2, label='Zero Skewness')
    ax.legend(loc='best', fontsize=11)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/skew_factor_skewness_distribution.png', dpi=300, bbox_inches='tight')
    print(f"Saved: {output_dir}/skew_factor_skewness_distribution.png")
    plt.close()
    
    # 5. Turnover Over Time
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(portfolio_df['date'], portfolio_df['turnover'] * 100, 
            linewidth=1.5, color='#5F4BB6', alpha=0.7)
    ax.set_xlabel('Date', fontsize=12)
    ax.set_ylabel('Turnover (%)', fontsize=12)
    ax.set_title('Daily Turnover Over Time', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/skew_factor_turnover.png', dpi=300, bbox_inches='tight')
    print(f"Saved: {output_dir}/skew_factor_turnover.png")
    plt.close()


def save_results(results, output_prefix='backtests/results/skew_factor'):
    """
    Save backtest results to CSV files.
    
    Args:
        results (dict): Dictionary containing backtest results
        output_prefix (str): Prefix for output filenames
    """
    # Save portfolio values
    portfolio_file = f"{output_prefix}_backtest_results.csv"
    results['portfolio_values'].to_csv(portfolio_file, index=False)
    print(f"\nPortfolio results saved to: {portfolio_file}")
    
    # Save performance metrics
    metrics_file = f"{output_prefix}_performance.csv"
    metrics_df = pd.DataFrame([results['metrics']])
    metrics_df.to_csv(metrics_file, index=False)
    print(f"Performance metrics saved to: {metrics_file}")
    
    # Save signals (subset for current date range)
    signals_file = f"{output_prefix}_signals.csv"
    portfolio_dates = results['portfolio_values']['date'].unique()
    signals_subset = results['signals_df'][
        results['signals_df']['date'].isin(portfolio_dates) & 
        (results['signals_df']['signal'] != 0)
    ]
    signals_subset.to_csv(signals_file, index=False)
    print(f"Signals saved to: {signals_file}")


def main():
    """Main execution function for backtest."""
    parser = argparse.ArgumentParser(
        description='Backtest Skew Factor Trading Strategy',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--data-file',
        type=str,
        default='data/raw/combined_coinbase_coinmarketcap_daily.csv',
        help='Path to historical OHLCV data CSV file'
    )
    parser.add_argument(
        '--lookback-window',
        type=int,
        default=30,
        help='Lookback window for calculating skewness (days)'
    )
    parser.add_argument(
        '--min-volume',
        type=float,
        default=5_000_000,
        help='Minimum 30-day average volume in USD'
    )
    parser.add_argument(
        '--min-market-cap',
        type=float,
        default=50_000_000,
        help='Minimum market cap in USD'
    )
    parser.add_argument(
        '--num-quintiles',
        type=int,
        default=5,
        help='Number of quintiles for ranking (5 = quintiles, 10 = deciles)'
    )
    parser.add_argument(
        '--start-date',
        type=str,
        default='2020-03-01',
        help='Start date for backtest (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--end-date',
        type=str,
        default=None,
        help='End date for backtest (YYYY-MM-DD)'
    )
    parser.add_argument(
        '--initial-capital',
        type=float,
        default=10000,
        help='Initial portfolio capital in USD'
    )
    parser.add_argument(
        '--output-prefix',
        type=str,
        default='backtests/results/skew_factor',
        help='Prefix for output files'
    )
    parser.add_argument(
        '--no-plots',
        action='store_true',
        help='Skip generating plots'
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("SKEW FACTOR BACKTEST")
    print("=" * 80)
    print(f"\nConfiguration:")
    print(f"  Data file: {args.data_file}")
    print(f"  Lookback window: {args.lookback_window} days")
    print(f"  Min volume: ${args.min_volume:,.0f}")
    print(f"  Min market cap: ${args.min_market_cap:,.0f}")
    print(f"  Quintiles: {args.num_quintiles}")
    print(f"  Start date: {args.start_date}")
    print(f"  End date: {args.end_date or 'Latest available'}")
    print(f"  Initial capital: ${args.initial_capital:,.2f}")
    print("=" * 80)
    
    # Load data
    print("\nLoading data...")
    data = load_data(args.data_file)
    print(f"Loaded {len(data):,} rows for {data['symbol'].nunique()} symbols")
    print(f"Date range: {data['date'].min().date()} to {data['date'].max().date()}")
    
    # Calculate skewness
    print("\nCalculating skewness and applying filters...")
    data_with_skewness = calculate_skewness(
        data, 
        lookback_window=args.lookback_window,
        min_volume=args.min_volume,
        min_market_cap=args.min_market_cap
    )
    
    valid_data = data_with_skewness[data_with_skewness['passes_all_filters']]
    print(f"Valid observations: {len(valid_data):,}")
    print(f"Coins with valid data: {valid_data['symbol'].nunique()}")
    
    # Generate signals
    print("\nGenerating long/short signals based on skewness quintiles...")
    signals_df = generate_signals(data_with_skewness, num_quintiles=args.num_quintiles)
    
    long_signals = signals_df[signals_df['signal'] == 1]
    short_signals = signals_df[signals_df['signal'] == -1]
    print(f"Long signals: {len(long_signals):,}")
    print(f"Short signals: {len(short_signals):,}")
    
    # Run backtest
    print("\nRunning backtest...")
    results = backtest_strategy(
        signals_df=signals_df,
        start_date=args.start_date,
        end_date=args.end_date,
        initial_capital=args.initial_capital
    )
    
    # Print results
    print_results(results)
    
    # Save results
    save_results(results, output_prefix=args.output_prefix)
    
    # Create visualizations
    if not args.no_plots:
        print("\nGenerating visualizations...")
        create_visualizations(results, output_dir='backtests/results')
    
    print("\n" + "=" * 80)
    print("BACKTEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
