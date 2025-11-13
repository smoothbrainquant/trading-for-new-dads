#!/usr/bin/env python3
"""
Run Dilution Factor Backtest with Relaxed Parameters

Changes from original:
- top_n = 5 (instead of 10)
- bottom_n = 5 (instead of 10)
- volatility_lookback = 30 days (instead of 90)
- min_data_points = 10 (instead of 20)
"""

import pandas as pd
import numpy as np
import sys
sys.path.append('/workspace/backtests/scripts')

def calculate_rolling_dilution_signal(historical_dilution_df, lookback_months=12):
    """Calculate rolling dilution velocity."""
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
    
    return pd.DataFrame(signals)


def calculate_volatility_relaxed(price_df, symbol, end_date, lookback_days=30, min_points=10):
    """Calculate historical volatility with relaxed minimum data requirement."""
    lookback_start = end_date - pd.DateOffset(days=lookback_days)
    coin_data = price_df[
        (price_df['base'] == symbol) &
        (price_df['date'] >= lookback_start) &
        (price_df['date'] <= end_date)
    ].copy()
    
    if len(coin_data) < min_points:
        return np.nan
    
    returns = coin_data['return'].dropna()
    if len(returns) < min_points:
        return np.nan
    
    volatility = returns.std() * np.sqrt(365)
    return volatility


def construct_portfolio_relaxed(signals, price_df, rebal_date, top_n=5, vol_lookback=30, min_data_points=10):
    """Construct risk parity weighted long/short portfolio with relaxed requirements."""
    valid_signals = signals[signals['dilution_velocity'].notna()].copy()
    valid_signals = valid_signals.nsmallest(150, 'rank')
    
    if len(valid_signals) < top_n * 2:
        return {}
    
    valid_signals = valid_signals.sort_values('dilution_velocity')
    long_candidates = valid_signals.head(top_n).copy()
    short_candidates = valid_signals.tail(top_n).copy()
    
    # Calculate volatility with relaxed requirements
    long_candidates['volatility'] = long_candidates['symbol'].apply(
        lambda s: calculate_volatility_relaxed(price_df, s, rebal_date, 
                                               lookback_days=vol_lookback, 
                                               min_points=min_data_points)
    )
    short_candidates['volatility'] = short_candidates['symbol'].apply(
        lambda s: calculate_volatility_relaxed(price_df, s, rebal_date,
                                               lookback_days=vol_lookback,
                                               min_points=min_data_points)
    )
    
    long_candidates = long_candidates[long_candidates['volatility'].notna()]
    short_candidates = short_candidates[short_candidates['volatility'].notna()]
    
    if len(long_candidates) == 0 or len(short_candidates) == 0:
        return {}
    
    long_candidates['inv_vol'] = 1.0 / long_candidates['volatility']
    short_candidates['inv_vol'] = 1.0 / short_candidates['volatility']
    
    long_total_inv_vol = long_candidates['inv_vol'].sum()
    short_total_inv_vol = short_candidates['inv_vol'].sum()
    
    long_candidates['weight'] = long_candidates['inv_vol'] / long_total_inv_vol
    short_candidates['weight'] = -short_candidates['inv_vol'] / short_total_inv_vol
    
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


def backtest_dilution_relaxed(price_df, hist_df, top_n=5, vol_lookback=30, 
                               min_data_points=10, rebalance_days=7, 
                               transaction_cost=0.001, initial_capital=10000):
    """Run dilution backtest with relaxed parameters."""
    
    # Calculate signals
    print('Calculating dilution signals...')
    signals_df = calculate_rolling_dilution_signal(hist_df, lookback_months=12)
    
    # Create rebalance dates
    start_date = price_df['date'].min()
    end_date = price_df['date'].max()
    
    rebalance_dates = []
    current_date = start_date
    while current_date <= end_date:
        nearest_signal = signals_df[signals_df['date'] >= current_date]['date'].min()
        if pd.notna(nearest_signal):
            rebalance_dates.append(nearest_signal)
        current_date += pd.Timedelta(days=rebalance_days)
    
    rebalance_dates = sorted(list(set(rebalance_dates)))
    
    print(f'Rebalance dates: {len(rebalance_dates)}')
    print(f'Date range: {rebalance_dates[0].date()} to {rebalance_dates[-1].date()}')
    
    # Run backtest
    portfolio_history = []
    position_history = []
    current_portfolio = {}
    portfolio_value = initial_capital
    
    for i, rebal_date in enumerate(rebalance_dates):
        date_signals = signals_df[signals_df['date'] == rebal_date].copy()
        new_portfolio = construct_portfolio_relaxed(
            date_signals, price_df, rebal_date, 
            top_n=top_n, vol_lookback=vol_lookback, min_data_points=min_data_points
        )
        
        # Track position counts
        long_positions = sum(1 for p in new_portfolio.values() if p['side'] == 'long')
        short_positions = sum(1 for p in new_portfolio.values() if p['side'] == 'short')
        position_history.append({
            'date': rebal_date,
            'long': long_positions,
            'short': short_positions,
            'total': len(new_portfolio)
        })
        
        if len(new_portfolio) == 0:
            continue
        
        # Calculate turnover and apply transaction costs
        turnover = 0.0
        all_symbols = set(list(current_portfolio.keys()) + list(new_portfolio.keys()))
        for symbol in all_symbols:
            old_weight = current_portfolio.get(symbol, {}).get('weight', 0)
            new_weight = new_portfolio.get(symbol, {}).get('weight', 0)
            turnover += abs(new_weight - old_weight)
        
        transaction_cost_impact = turnover * transaction_cost
        portfolio_value *= (1 - transaction_cost_impact)
        
        # Calculate returns until next rebalance
        if i < len(rebalance_dates) - 1:
            next_rebal = rebalance_dates[i + 1]
        else:
            next_rebal = price_df['date'].max()
        
        holding_period = price_df[
            (price_df['date'] > rebal_date) &
            (price_df['date'] <= next_rebal)
        ].copy()
        
        for date in sorted(holding_period['date'].unique()):
            daily_returns = holding_period[holding_period['date'] == date]
            portfolio_return = 0.0
            valid_positions = 0
            
            # Calculate daily return for each position
            for symbol, position in new_portfolio.items():
                base_symbol = symbol
                symbol_data = daily_returns[daily_returns['base'] == base_symbol]
                
                if len(symbol_data) == 0:
                    continue
                
                if 'return' in symbol_data.columns:
                    symbol_return = symbol_data['return'].values[0]
                else:
                    continue
                
                if not np.isnan(symbol_return):
                    portfolio_return += position['weight'] * symbol_return
                    valid_positions += 1
            
            if valid_positions > 0:
                portfolio_value *= (1 + portfolio_return)
                portfolio_history.append({
                    'date': date,
                    'portfolio_value': portfolio_value,
                    'return': portfolio_return
                })
        
        current_portfolio = new_portfolio
        
        if i % 10 == 0:
            print(f'  {i+1}/{len(rebalance_dates)}: {rebal_date.date()} - {long_positions} long + {short_positions} short = {len(new_portfolio)} total, PV: ${portfolio_value:,.2f}')
    
    portfolio_df = pd.DataFrame(portfolio_history)
    positions_df = pd.DataFrame(position_history)
    
    return portfolio_df, positions_df


# Main execution
if __name__ == '__main__':
    print('=' * 80)
    print('DILUTION FACTOR BACKTEST - RELAXED PARAMETERS')
    print('=' * 80)
    print('Parameters:')
    print('  - top_n = 5')
    print('  - bottom_n = 5')
    print('  - volatility_lookback = 30 days')
    print('  - min_data_points = 10')
    print('  - rebalance_days = 7')
    print('=' * 80)
    
    # Load data
    print('\nLoading data...')
    price_df = pd.read_csv('data/raw/combined_coinbase_coinmarketcap_daily.csv')
    price_df['date'] = pd.to_datetime(price_df['date'])
    price_df = price_df[price_df['date'] >= '2021-01-01'].copy()
    price_df = price_df.sort_values(['symbol', 'date']).reset_index(drop=True)
    price_df['return'] = price_df.groupby('symbol')['close'].pct_change()
    if 'base' not in price_df.columns:
        price_df['base'] = price_df['symbol'].apply(lambda x: x.split('/')[0] if '/' in str(x) else x)
    
    hist_df = pd.read_csv('crypto_dilution_historical_2021_2025.csv')
    hist_df['date'] = pd.to_datetime(hist_df['date'])
    
    print(f'  Price data: {len(price_df)} rows, {price_df["base"].nunique()} coins')
    print(f'  Dilution data: {len(hist_df)} rows, {hist_df["Symbol"].nunique()} coins')
    
    # Run backtest
    print('\nRunning backtest...\n')
    portfolio_df, positions_df = backtest_dilution_relaxed(
        price_df, hist_df, 
        top_n=5, vol_lookback=30, min_data_points=10,
        rebalance_days=7, transaction_cost=0.001, initial_capital=10000
    )
    
    # Calculate metrics
    print('\n' + '=' * 80)
    print('BACKTEST RESULTS')
    print('=' * 80)
    
    if len(portfolio_df) > 0:
        initial_capital = 10000
        final_value = portfolio_df['portfolio_value'].iloc[-1]
        total_return = (final_value - initial_capital) / initial_capital
        
        portfolio_df['daily_return'] = portfolio_df['portfolio_value'].pct_change()
        daily_returns = portfolio_df['daily_return'].dropna()
        
        num_days = len(portfolio_df)
        years = num_days / 365.25
        annualized_return = (final_value / initial_capital) ** (1 / years) - 1 if years > 0 else 0
        
        daily_vol = daily_returns.std()
        annualized_vol = daily_vol * np.sqrt(365)
        sharpe_ratio = annualized_return / annualized_vol if annualized_vol > 0 else 0
        
        cumulative_returns = (1 + daily_returns.fillna(0)).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - running_max) / running_max
        max_drawdown = drawdown.min()
        
        win_rate = (daily_returns > 0).sum() / len(daily_returns) if len(daily_returns) > 0 else 0
        
        print(f'Total Return:           {total_return:.2%}')
        print(f'Annualized Return:      {annualized_return:.2%}')
        print(f'Volatility:             {annualized_vol:.2%}')
        print(f'Sharpe Ratio:           {sharpe_ratio:.3f}')
        print(f'Max Drawdown:           {max_drawdown:.2%}')
        print(f'Win Rate:               {win_rate:.2%}')
        print(f'Number of Days:         {num_days}')
        print(f'Final Portfolio Value:  ${final_value:,.2f}')
    else:
        print('No portfolio history generated!')
    
    # Position statistics
    print('\n' + '=' * 80)
    print('POSITION COVERAGE STATISTICS')
    print('=' * 80)
    print(f'Total rebalances: {len(positions_df)}')
    print(f'\nPosition Statistics:')
    print(f'  Long  - Min: {positions_df["long"].min():2d}, Max: {positions_df["long"].max():2d}, Mean: {positions_df["long"].mean():5.1f}, Median: {positions_df["long"].median():.0f}')
    print(f'  Short - Min: {positions_df["short"].min():2d}, Max: {positions_df["short"].max():2d}, Mean: {positions_df["short"].mean():5.1f}, Median: {positions_df["short"].median():.0f}')
    print(f'  Total - Min: {positions_df["total"].min():2d}, Max: {positions_df["total"].max():2d}, Mean: {positions_df["total"].mean():5.1f}, Median: {positions_df["total"].median():.0f}')
    
    print(f'\nTarget: 5 long + 5 short = 10 total')
    print(f'Achieved target (10 positions): {(positions_df["total"] == 10).sum()} times ({(positions_df["total"] == 10).sum() / len(positions_df) * 100:.1f}%)')
    print(f'Had 8+ positions: {(positions_df["total"] >= 8).sum()} times ({(positions_df["total"] >= 8).sum() / len(positions_df) * 100:.1f}%)')
    print(f'Had 6+ positions: {(positions_df["total"] >= 6).sum()} times ({(positions_df["total"] >= 6).sum() / len(positions_df) * 100:.1f}%)')
    
    # Save results
    portfolio_df.to_csv('dilution_backtest_relaxed_portfolio.csv', index=False)
    positions_df.to_csv('dilution_backtest_relaxed_positions.csv', index=False)
    print('\nResults saved:')
    print('  - dilution_backtest_relaxed_portfolio.csv')
    print('  - dilution_backtest_relaxed_positions.csv')
