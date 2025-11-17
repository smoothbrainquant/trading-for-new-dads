"""
Backtest Size Factor Strategy on Monthly CoinMarketCap Data

This script backtests a size factor strategy using monthly/annual CoinMarketCap snapshots.
It filters out stablecoins and suspicious tokens, then constructs a long/short portfolio
based on market cap.

Strategy:
- Long: Small cap coins (bottom quintile by market cap)
- Short: Large cap coins (top quintile by market cap)
- Risk parity weighting within each bucket
- Rebalance monthly (at each snapshot)
"""

import pandas as pd
import numpy as np
from datetime import datetime
import argparse


def load_cmc_snapshots(filepath):
    """
    Load CoinMarketCap historical snapshots.
    
    Args:
        filepath (str): Path to CSV with snapshot data
        
    Returns:
        pd.DataFrame: Snapshot data with date parsed
    """
    df = pd.read_csv(filepath)
    
    # Convert snapshot_date to datetime
    df['snapshot_date'] = pd.to_datetime(df['snapshot_date'], format='%Y%m%d')
    
    # Clean up column names
    df.columns = [col.strip() for col in df.columns]
    
    # Sort by date and rank
    df = df.sort_values(['snapshot_date', 'Rank']).reset_index(drop=True)
    
    return df


def filter_stablecoins_and_weird(df):
    """
    Filter out stablecoins and suspicious/weird tokens.
    
    Args:
        df (pd.DataFrame): CoinMarketCap snapshot data
        
    Returns:
        pd.DataFrame: Filtered data
    """
    # Known stablecoins (common ones)
    stablecoin_symbols = [
        'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP', 'USDD', 'GUSD', 'FRAX',
        'USDK', 'PAX', 'HUSD', 'SUSD', 'USDS', 'LUSD', 'USDX', 'UST', 'OUSD',
        'USDN', 'FEI', 'EUROC', 'EURS', 'EURT', 'XAUT', 'PAXG', 'USDE', 'sUSD',
        'MAI', 'MIM', 'USTC', 'USDJ', 'CUSD', 'RSV', 'DUSD', 'USDQ', 'QCAD'
    ]
    
    stablecoin_names = [
        'Tether', 'USD Coin', 'Binance USD', 'Dai', 'TrueUSD', 'Paxos', 
        'Gemini Dollar', 'First Digital USD', 'PayPal USD', 'TerraUSD'
    ]
    
    # Filter out stablecoins
    print(f"\nOriginal data: {len(df)} rows")
    df = df[~df['Symbol'].isin(stablecoin_symbols)]
    df = df[~df['Name'].str.contains('USD', case=False, na=False) | 
            ~df['Name'].str.contains('Dollar', case=False, na=False)]
    print(f"After stablecoin filter: {len(df)} rows")
    
    # Filter out suspicious tokens (very short names, numbers, etc.)
    # Remove tokens with purely numeric symbols
    df = df[~df['Symbol'].str.match(r'^\d+$')]
    
    # Remove tokens with very short names that might be test tokens
    df = df[df['Symbol'].str.len() >= 2]
    
    # Filter out tokens with very low volume (might be dead or fake)
    # Keep only tokens with volume > $100
    df = df[df['Volume (24h)'] > 100]
    
    # Remove wrapped tokens (though some are legitimate)
    # df = df[~df['Symbol'].str.startswith('W')]
    
    # Remove tokens with suspicious names
    suspicious_patterns = ['Test', 'Wrapped', 'Pegged']
    for pattern in suspicious_patterns:
        df = df[~df['Name'].str.contains(pattern, case=False, na=False)]
    
    print(f"After weird token filter: {len(df)} rows")
    
    return df


def calculate_returns(df):
    """
    Calculate returns between snapshots for each symbol.
    
    Args:
        df (pd.DataFrame): Snapshot data with Price column
        
    Returns:
        pd.DataFrame: Data with returns calculated
    """
    df = df.sort_values(['Symbol', 'snapshot_date'])
    
    # Calculate price return between snapshots
    df['price_return'] = df.groupby('Symbol')['Price'].pct_change()
    df['log_return'] = df.groupby('Symbol')['Price'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    # Calculate market cap return
    df['mcap_return'] = df.groupby('Symbol')['Market Cap'].pct_change()
    
    return df


def assign_size_quintiles(df_snapshot, num_buckets=5):
    """
    Assign size quintiles based on market cap for a single snapshot.
    
    Args:
        df_snapshot (pd.DataFrame): Data for a single snapshot date
        num_buckets (int): Number of size buckets (default 5 for quintiles)
        
    Returns:
        pd.DataFrame: Data with size_bucket column added (1=largest, 5=smallest)
    """
    df = df_snapshot.copy()
    
    # Sort by market cap descending
    df = df.sort_values('Market Cap', ascending=False)
    
    # Assign quintiles (1 = largest cap, 5 = smallest cap)
    try:
        df['size_bucket'] = pd.qcut(
            df['Market Cap'], 
            q=num_buckets, 
            labels=range(1, num_buckets + 1),
            duplicates='drop'
        )
    except ValueError:
        # If we can't create quintiles (not enough unique values), use rank
        df['size_bucket'] = pd.cut(
            df['Market Cap'].rank(method='first'),
            bins=num_buckets,
            labels=range(1, num_buckets + 1)
        )
    
    return df


def calculate_portfolio_weights(symbols_list, volatility_dict=None):
    """
    Calculate portfolio weights for a list of symbols.
    If volatility data is provided, use risk parity weighting.
    Otherwise, use equal weighting.
    
    Args:
        symbols_list (list): List of symbols
        volatility_dict (dict): Optional dictionary of symbol -> volatility
        
    Returns:
        dict: Dictionary of symbol -> weight
    """
    if not symbols_list:
        return {}
    
    if volatility_dict:
        # Risk parity weighting (inverse volatility)
        weights = {}
        valid_symbols = [s for s in symbols_list if s in volatility_dict and volatility_dict[s] > 0]
        
        if not valid_symbols:
            # Fall back to equal weighting
            return {s: 1.0 / len(symbols_list) for s in symbols_list}
        
        inv_vol_sum = sum(1.0 / volatility_dict[s] for s in valid_symbols)
        
        for symbol in valid_symbols:
            weights[symbol] = (1.0 / volatility_dict[symbol]) / inv_vol_sum
        
        return weights
    else:
        # Equal weighting
        weight = 1.0 / len(symbols_list)
        return {s: weight for s in symbols_list}


def backtest_size_factor(
    df,
    strategy='long_small_short_large',
    num_buckets=5,
    long_allocation=0.5,
    short_allocation=0.5,
    initial_capital=10000
):
    """
    Run backtest for size factor strategy.
    
    Args:
        df (pd.DataFrame): CoinMarketCap snapshot data
        strategy (str): Strategy type
        num_buckets (int): Number of size buckets
        long_allocation (float): Allocation to long side
        short_allocation (float): Allocation to short side
        initial_capital (float): Initial portfolio value
        
    Returns:
        dict: Backtest results
    """
    # Get unique dates
    dates = sorted(df['snapshot_date'].unique())
    
    print(f"\n{'='*80}")
    print(f"BACKTEST CONFIGURATION")
    print(f"{'='*80}")
    print(f"Strategy: {strategy}")
    print(f"Size buckets: {num_buckets}")
    print(f"Long allocation: {long_allocation:.1%}")
    print(f"Short allocation: {short_allocation:.1%}")
    print(f"Initial capital: ${initial_capital:,.2f}")
    print(f"Rebalance dates: {len(dates)}")
    print(f"Period: {dates[0].date()} to {dates[-1].date()}")
    print(f"{'='*80}\n")
    
    # Initialize tracking
    portfolio_values = []
    trades_history = []
    holdings_history = []
    current_capital = initial_capital
    current_long_holdings = {}
    current_short_holdings = {}
    
    # Need at least 2 dates to calculate returns
    if len(dates) < 2:
        raise ValueError("Need at least 2 snapshot dates to run backtest")
    
    # Start from first date (no returns yet)
    for date_idx, current_date in enumerate(dates):
        print(f"\n--- Date: {current_date.date()} (Snapshot {date_idx + 1}/{len(dates)}) ---")
        
        # Get data for current snapshot
        snapshot = df[df['snapshot_date'] == current_date].copy()
        
        # Assign size buckets
        snapshot = assign_size_quintiles(snapshot, num_buckets=num_buckets)
        
        # Select symbols based on strategy
        if strategy == 'long_small_short_large':
            long_symbols = snapshot[snapshot['size_bucket'] == num_buckets]['Symbol'].tolist()
            short_symbols = snapshot[snapshot['size_bucket'] == 1]['Symbol'].tolist()
        elif strategy == 'long_small':
            long_symbols = snapshot[snapshot['size_bucket'] == num_buckets]['Symbol'].tolist()
            short_symbols = []
        elif strategy == 'long_small_2_quintiles':
            long_symbols = snapshot[
                snapshot['size_bucket'].isin([num_buckets, num_buckets - 1])
            ]['Symbol'].tolist()
            short_symbols = []
        else:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        print(f"Long symbols: {len(long_symbols)}")
        print(f"Short symbols: {len(short_symbols)}")
        
        # If not first period, calculate returns and update portfolio value
        if date_idx > 0:
            prev_date = dates[date_idx - 1]
            prev_snapshot = df[df['snapshot_date'] == prev_date]
            
            # Calculate returns for holdings
            portfolio_return_dollars = 0.0
            
            # Long holdings
            for symbol, num_shares in current_long_holdings.items():
                prev_price = prev_snapshot[prev_snapshot['Symbol'] == symbol]['Price'].values
                curr_price = snapshot[snapshot['Symbol'] == symbol]['Price'].values
                
                if len(prev_price) > 0 and len(curr_price) > 0:
                    price_return = (curr_price[0] - prev_price[0]) / prev_price[0]
                    position_value = num_shares * prev_price[0]
                    position_return_dollars = position_value * price_return
                    portfolio_return_dollars += position_return_dollars
                    
                    print(f"  LONG {symbol}: {price_return:+.2%} (${position_return_dollars:+,.2f})")
            
            # Short holdings
            for symbol, num_shares in current_short_holdings.items():
                prev_price = prev_snapshot[prev_snapshot['Symbol'] == symbol]['Price'].values
                curr_price = snapshot[snapshot['Symbol'] == symbol]['Price'].values
                
                if len(prev_price) > 0 and len(curr_price) > 0:
                    price_return = (curr_price[0] - prev_price[0]) / prev_price[0]
                    position_value = num_shares * prev_price[0]
                    # Short returns are negative of price returns
                    position_return_dollars = -position_value * price_return
                    portfolio_return_dollars += position_return_dollars
                    
                    print(f"  SHORT {symbol}: {-price_return:+.2%} (${position_return_dollars:+,.2f})")
            
            # Update capital
            current_capital += portfolio_return_dollars
            
            print(f"\nPortfolio return: ${portfolio_return_dollars:+,.2f}")
            print(f"New portfolio value: ${current_capital:,.2f}")
        
        # Calculate new weights (equal weight for simplicity)
        long_weights = calculate_portfolio_weights(long_symbols)
        short_weights = calculate_portfolio_weights(short_symbols)
        
        # Calculate new holdings
        new_long_holdings = {}
        new_short_holdings = {}
        
        # Long positions
        long_capital = current_capital * long_allocation
        for symbol, weight in long_weights.items():
            symbol_capital = long_capital * weight
            price = snapshot[snapshot['Symbol'] == symbol]['Price'].values[0]
            num_shares = symbol_capital / price
            new_long_holdings[symbol] = num_shares
            
            trades_history.append({
                'date': current_date,
                'symbol': symbol,
                'side': 'LONG',
                'weight': weight * long_allocation,
                'capital': symbol_capital,
                'price': price,
                'shares': num_shares
            })
        
        # Short positions
        short_capital = current_capital * short_allocation
        for symbol, weight in short_weights.items():
            symbol_capital = short_capital * weight
            price = snapshot[snapshot['Symbol'] == symbol]['Price'].values[0]
            num_shares = symbol_capital / price
            new_short_holdings[symbol] = num_shares
            
            trades_history.append({
                'date': current_date,
                'symbol': symbol,
                'side': 'SHORT',
                'weight': -weight * short_allocation,
                'capital': symbol_capital,
                'price': price,
                'shares': num_shares
            })
        
        # Update holdings
        current_long_holdings = new_long_holdings
        current_short_holdings = new_short_holdings
        
        # Calculate exposures
        long_exposure = sum(
            holdings * snapshot[snapshot['Symbol'] == symbol]['Price'].values[0]
            for symbol, holdings in current_long_holdings.items()
        )
        short_exposure = sum(
            holdings * snapshot[snapshot['Symbol'] == symbol]['Price'].values[0]
            for symbol, holdings in current_short_holdings.items()
        )
        
        # Record portfolio value
        portfolio_values.append({
            'date': current_date,
            'portfolio_value': current_capital,
            'num_long_positions': len(current_long_holdings),
            'num_short_positions': len(current_short_holdings),
            'long_exposure': long_exposure,
            'short_exposure': short_exposure,
            'net_exposure': long_exposure - short_exposure,
            'gross_exposure': long_exposure + short_exposure
        })
        
        print(f"Long exposure: ${long_exposure:,.2f} ({long_exposure/current_capital:.1%})")
        print(f"Short exposure: ${short_exposure:,.2f} ({short_exposure/current_capital:.1%})")
    
    # Convert to DataFrames
    portfolio_df = pd.DataFrame(portfolio_values)
    trades_df = pd.DataFrame(trades_history)
    
    # Calculate performance metrics
    metrics = calculate_performance_metrics(portfolio_df, initial_capital)
    
    return {
        'portfolio_values': portfolio_df,
        'trades': trades_df,
        'metrics': metrics
    }


def calculate_performance_metrics(portfolio_df, initial_capital):
    """
    Calculate performance metrics.
    
    Args:
        portfolio_df (pd.DataFrame): Portfolio values over time
        initial_capital (float): Initial capital
        
    Returns:
        dict: Performance metrics
    """
    # Calculate returns
    portfolio_df = portfolio_df.copy()
    portfolio_df['return'] = portfolio_df['portfolio_value'].pct_change()
    portfolio_df['log_return'] = np.log(
        portfolio_df['portfolio_value'] / portfolio_df['portfolio_value'].shift(1)
    )
    
    # Total return
    final_value = portfolio_df['portfolio_value'].iloc[-1]
    total_return = (final_value - initial_capital) / initial_capital
    
    # Calculate time period
    first_date = portfolio_df['date'].iloc[0]
    last_date = portfolio_df['date'].iloc[-1]
    days = (last_date - first_date).days
    years = days / 365.25
    
    # Annualized return (CAGR)
    annualized_return = (final_value / initial_capital) ** (1 / years) - 1 if years > 0 else 0
    
    # Volatility (annualized)
    returns = portfolio_df['return'].dropna()
    if len(returns) > 1:
        # Estimate annualization factor based on number of periods
        periods_per_year = len(returns) / years if years > 0 else 1
        period_vol = returns.std()
        annualized_vol = period_vol * np.sqrt(periods_per_year)
    else:
        annualized_vol = 0
    
    # Sharpe ratio (assuming 0% risk-free rate)
    sharpe_ratio = annualized_return / annualized_vol if annualized_vol > 0 else 0
    
    # Maximum drawdown
    cumulative_returns = (1 + portfolio_df['return'].fillna(0)).cumprod()
    running_max = cumulative_returns.expanding().max()
    drawdown = (cumulative_returns - running_max) / running_max
    max_drawdown = drawdown.min()
    
    # Win rate
    positive_periods = (returns > 0).sum()
    total_periods = len(returns)
    win_rate = positive_periods / total_periods if total_periods > 0 else 0
    
    # Average exposures
    avg_long_exposure = portfolio_df['long_exposure'].mean()
    avg_short_exposure = portfolio_df['short_exposure'].mean()
    avg_net_exposure = portfolio_df['net_exposure'].mean()
    avg_gross_exposure = portfolio_df['gross_exposure'].mean()
    
    return {
        'initial_capital': initial_capital,
        'final_value': final_value,
        'total_return': total_return,
        'annualized_return': annualized_return,
        'annualized_volatility': annualized_vol,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'num_periods': len(portfolio_df),
        'days': days,
        'years': years,
        'avg_long_positions': portfolio_df['num_long_positions'].mean(),
        'avg_short_positions': portfolio_df['num_short_positions'].mean(),
        'avg_long_exposure': avg_long_exposure,
        'avg_short_exposure': avg_short_exposure,
        'avg_net_exposure': avg_net_exposure,
        'avg_gross_exposure': avg_gross_exposure
    }


def print_results(results):
    """Print backtest results."""
    metrics = results['metrics']
    
    print(f"\n{'='*80}")
    print("SIZE FACTOR BACKTEST RESULTS")
    print(f"{'='*80}")
    
    print(f"\nPortfolio Performance:")
    print(f"  Initial Capital:        ${metrics['initial_capital']:>15,.2f}")
    print(f"  Final Value:            ${metrics['final_value']:>15,.2f}")
    print(f"  Total Return:           {metrics['total_return']:>15.2%}")
    print(f"  Annualized Return:      {metrics['annualized_return']:>15.2%}")
    
    print(f"\nRisk Metrics:")
    print(f"  Annualized Volatility:  {metrics['annualized_volatility']:>15.2%}")
    print(f"  Sharpe Ratio:           {metrics['sharpe_ratio']:>15.2f}")
    print(f"  Maximum Drawdown:       {metrics['max_drawdown']:>15.2%}")
    
    print(f"\nTrading Statistics:")
    print(f"  Win Rate:               {metrics['win_rate']:>15.2%}")
    print(f"  Trading Periods:        {metrics['num_periods']:>15.0f}")
    print(f"  Days:                   {metrics['days']:>15.0f}")
    print(f"  Years:                  {metrics['years']:>15.2f}")
    print(f"  Avg Long Positions:     {metrics['avg_long_positions']:>15.1f}")
    print(f"  Avg Short Positions:    {metrics['avg_short_positions']:>15.1f}")
    
    print(f"\nExposure Statistics:")
    print(f"  Avg Long Exposure:      ${metrics['avg_long_exposure']:>14,.2f}")
    print(f"  Avg Short Exposure:     ${metrics['avg_short_exposure']:>14,.2f}")
    print(f"  Avg Net Exposure:       ${metrics['avg_net_exposure']:>14,.2f}")
    print(f"  Avg Gross Exposure:     ${metrics['avg_gross_exposure']:>14,.2f}")
    
    print(f"\n{'='*80}")
    
    # Show portfolio value over time
    print("\nPortfolio Value Over Time:")
    print(results['portfolio_values'].to_string(index=False))


def save_results(results, output_prefix='backtest_cmc_size_factor_monthly'):
    """Save results to CSV files."""
    # Portfolio values
    portfolio_file = f"{output_prefix}_portfolio_values.csv"
    results['portfolio_values'].to_csv(portfolio_file, index=False)
    print(f"\nPortfolio values saved to: {portfolio_file}")
    
    # Trades
    trades_file = f"{output_prefix}_trades.csv"
    results['trades'].to_csv(trades_file, index=False)
    print(f"Trades history saved to: {trades_file}")
    
    # Metrics
    metrics_file = f"{output_prefix}_metrics.csv"
    metrics_df = pd.DataFrame([results['metrics']])
    metrics_df.to_csv(metrics_file, index=False)
    print(f"Performance metrics saved to: {metrics_file}")


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(
        description='Backtest Size Factor Strategy on Monthly CoinMarketCap Data',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        '--data',
        type=str,
        default='coinmarketcap_historical_all_snapshots.csv',
        help='Path to CoinMarketCap snapshots CSV file'
    )
    parser.add_argument(
        '--strategy',
        type=str,
        default='long_small_short_large',
        choices=['long_small_short_large', 'long_small', 'long_small_2_quintiles'],
        help='Size factor strategy type'
    )
    parser.add_argument(
        '--num-buckets',
        type=int,
        default=5,
        help='Number of size buckets (quintiles)'
    )
    parser.add_argument(
        '--long-allocation',
        type=float,
        default=0.5,
        help='Allocation to long side (0.5 = 50%%)'
    )
    parser.add_argument(
        '--short-allocation',
        type=float,
        default=0.5,
        help='Allocation to short side (0.5 = 50%%)'
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
        default='backtest_cmc_size_factor_monthly',
        help='Prefix for output CSV files'
    )
    parser.add_argument(
        '--no-filter',
        action='store_true',
        help='Skip filtering stablecoins and weird tokens'
    )
    
    args = parser.parse_args()
    
    print("="*80)
    print("SIZE FACTOR BACKTEST - COINMARKETCAP MONTHLY DATA")
    print("="*80)
    
    # Load data
    print(f"\nLoading data from {args.data}...")
    df = load_cmc_snapshots(args.data)
    print(f"Loaded {len(df)} rows")
    print(f"Snapshots: {sorted(df['snapshot_date'].unique())}")
    print(f"Unique symbols: {df['Symbol'].nunique()}")
    
    # Filter data
    if not args.no_filter:
        print("\nFiltering stablecoins and weird tokens...")
        df = filter_stablecoins_and_weird(df)
    
    # Run backtest
    print("\nRunning backtest...")
    results = backtest_size_factor(
        df=df,
        strategy=args.strategy,
        num_buckets=args.num_buckets,
        long_allocation=args.long_allocation,
        short_allocation=args.short_allocation,
        initial_capital=args.initial_capital
    )
    
    # Print results
    print_results(results)
    
    # Save results
    save_results(results, output_prefix=args.output_prefix)
    
    print(f"\n{'='*80}")
    print("BACKTEST COMPLETE")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
