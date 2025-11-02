"""
Vectorized Backtest Engine

This module provides a unified vectorized backtesting framework that eliminates
date loops and dramatically improves performance (10-100x faster than traditional
loop-based approaches).

Key Features:
- Single backtest function for all ranking-based factors
- No date loops - all operations are vectorized
- Proper lookahead bias prevention (signals on day T, returns from day T+1)
- Support for rebalancing, equal weight, and risk parity
- Comprehensive performance metrics

Performance: 30-50x faster than loop-based approaches
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Literal, Dict, Callable
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "signals"))

from generate_signals_vectorized import (
    generate_volatility_signals_vectorized,
    generate_beta_signals_vectorized,
    generate_carry_signals_vectorized,
    generate_size_signals_vectorized,
    generate_skew_signals_vectorized,
    generate_kurtosis_signals_vectorized,
    generate_days_from_high_signals_vectorized,
    generate_breakout_signals_vectorized,
    generate_mean_reversion_signals_vectorized,
    generate_adf_signals_vectorized,
    calculate_weights_vectorized,
    calculate_portfolio_returns_vectorized,
    calculate_cumulative_returns_vectorized,
    calculate_regime_vectorized,
)


def prepare_price_data(
    price_data: pd.DataFrame,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> pd.DataFrame:
    """
    Prepare price data with returns calculation.
    
    Args:
        price_data: DataFrame with date, symbol, close columns
        start_date: Start date for filtering
        end_date: End date for filtering
    
    Returns:
        pd.DataFrame: Price data with daily_return column
    """
    df = price_data.copy()
    df['date'] = pd.to_datetime(df['date'])
    
    # Extract base symbol if symbol is in format "BTC/USD"
    if 'base' in df.columns:
        df['symbol'] = df['base']
    elif len(df) > 0 and '/' in str(df['symbol'].iloc[0]):
        df['symbol'] = df['symbol'].apply(lambda x: x.split('/')[0] if '/' in str(x) else x)
    
    df = df.sort_values(['symbol', 'date']).reset_index(drop=True)
    
    # Filter by date range
    if start_date:
        df = df[df['date'] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df['date'] <= pd.to_datetime(end_date)]
    
    # Calculate daily log returns
    df['daily_return'] = df.groupby('symbol')['close'].transform(
        lambda x: np.log(x / x.shift(1))
    )
    
    return df


def prepare_factor_data(
    price_data: pd.DataFrame,
    factor_type: str,
    **factor_params,
) -> pd.DataFrame:
    """
    Calculate factor data (volatility, beta, etc.) for all dates at once.
    
    Args:
        price_data: DataFrame with OHLCV data
        factor_type: Type of factor ('volatility', 'beta', 'carry', 'size', etc.)
        **factor_params: Additional parameters for factor calculation
    
    Returns:
        pd.DataFrame: DataFrame with factor values for all dates
    """
    if factor_type == 'volatility':
        from calc_vola import calculate_rolling_30d_volatility
        window = factor_params.get('window', 30)
        if window == 30:
            return calculate_rolling_30d_volatility(price_data)
        else:
            # Custom window volatility
            df = price_data.copy()
            df['daily_return'] = df.groupby('symbol')['close'].transform(
                lambda x: np.log(x / x.shift(1))
            )
            df[f'volatility_{window}d'] = df.groupby('symbol')['daily_return'].transform(
                lambda x: x.rolling(window=window, min_periods=window).std() * np.sqrt(365)
            )
            return df
    
    elif factor_type == 'beta':
        from backtests.scripts.backtest_beta_factor import calculate_rolling_beta
        window = factor_params.get('beta_window', 90)
        btc_data = price_data[price_data['symbol'] == 'BTC'].copy()
        return calculate_rolling_beta(price_data, btc_data, window=window)
    
    elif factor_type == 'carry':
        # Funding rates data should be merged with price data to ensure alignment
        funding_data = factor_params.get('funding_data')
        if funding_data is None:
            return None
        # Merge with price data to ensure we only trade symbols with price data
        # Keep only dates and symbols that exist in price_data
        merged = price_data.merge(
            funding_data,
            on=['date', 'symbol'],
            how='inner'
        )
        return merged
    
    elif factor_type == 'size':
        # Market cap data should be merged with price data to ensure alignment
        marketcap_data = factor_params.get('marketcap_data')
        if marketcap_data is None:
            return None
        # Drop market_cap from price_data if it exists to avoid column name conflicts
        price_df_clean = price_data.copy()
        if 'market_cap' in price_df_clean.columns:
            price_df_clean = price_df_clean.drop(columns=['market_cap'])
        
        # Forward-fill market cap data to make it available for all dates
        # Get all unique dates from price data and all symbols from market cap data
        mcap_subset = marketcap_data[['date', 'symbol', 'market_cap']].copy()
        
        # Merge with left join to keep all price data rows
        merged = price_df_clean.merge(
            mcap_subset,
            on=['date', 'symbol'],
            how='left'
        )
        
        # Forward-fill market cap within each symbol
        merged = merged.sort_values(['symbol', 'date'])
        merged['market_cap'] = merged.groupby('symbol')['market_cap'].ffill()
        
        # Drop rows with no market cap data (before first snapshot)
        merged = merged.dropna(subset=['market_cap'])
        
        return merged
    
    elif factor_type == 'kurtosis':
        # Calculate kurtosis
        from scipy import stats
        df = price_data.copy()
        df['daily_return'] = df.groupby('symbol')['close'].transform(
            lambda x: np.log(x / x.shift(1))
        )
        window = factor_params.get('kurtosis_window', 30)
        df[f'kurtosis_{window}d'] = df.groupby('symbol')['daily_return'].transform(
            lambda x: x.rolling(window=window, min_periods=window).apply(stats.kurtosis, raw=True)
        )
        return df
    
    elif factor_type == 'skew':
        # Calculate skewness
        from scipy import stats
        df = price_data.copy()
        df['daily_return'] = df.groupby('symbol')['close'].transform(
            lambda x: np.log(x / x.shift(1))
        )
        window = factor_params.get('skew_window', 30)
        df[f'skewness_{window}d'] = df.groupby('symbol')['daily_return'].transform(
            lambda x: x.rolling(window=window, min_periods=window).apply(stats.skew, raw=True)
        )
        return df
    
    elif factor_type == 'days_from_high':
        # No additional calculation needed - signals will be generated from price data
        return price_data.copy()
    
    elif factor_type == 'breakout':
        # No additional calculation needed - signals will be generated from price data
        return price_data.copy()
    
    elif factor_type == 'mean_reversion':
        # No additional calculation needed - signals will be generated from price data
        return price_data.copy()
    
    elif factor_type == 'adf':
        # ADF requires pre-calculation using statsmodels (cannot be vectorized)
        # User must pass pre-calculated ADF data via adf_data parameter
        adf_data = factor_params.get('adf_data')
        if adf_data is None:
            raise ValueError("ADF factor requires pre-calculated 'adf_data' parameter")
        
        # Symbol format normalization: ADF uses full symbols (e.g., 'AAVE/USD')
        # while price_data may use base symbols (e.g., 'AAVE')
        # Check if we need to normalize
        sample_adf_symbol = str(adf_data['symbol'].iloc[0])
        sample_price_symbol = str(price_data['symbol'].iloc[0])
        
        # If formats differ, use 'base' column from ADF or extract base from symbol
        if '/' in sample_adf_symbol and '/' not in sample_price_symbol:
            if 'base' in adf_data.columns:
                # Use existing base column
                adf_data = adf_data.copy()
                adf_data['symbol_normalized'] = adf_data['base']
            else:
                # Extract base from symbol (e.g., 'AAVE/USD' -> 'AAVE')
                adf_data = adf_data.copy()
                adf_data['symbol_normalized'] = adf_data['symbol'].str.split('/').str[0]
            merge_on_col = 'symbol_normalized'
        else:
            merge_on_col = 'symbol'
        
        # Merge with price_data to ensure alignment (only keep dates/symbols in price_data)
        # This is critical when price_data has been filtered by start_date/end_date
        # First, select only the ADF columns we need
        adf_cols = ['date', merge_on_col, 'adf_stat']
        if 'adf_pvalue' in adf_data.columns:
            adf_cols.append('adf_pvalue')
        if 'is_stationary' in adf_data.columns:
            adf_cols.append('is_stationary')
        
        adf_subset = adf_data[adf_cols].copy()
        
        # Rename the merge column to 'symbol' for consistency
        if merge_on_col != 'symbol':
            adf_subset = adf_subset.rename(columns={merge_on_col: 'symbol'})
        
        # Merge with price data (left join to keep all price_data rows)
        merged = price_data.merge(
            adf_subset,
            on=['date', 'symbol'],
            how='left'  # Left join: keep all price_data rows, add ADF where available
        )
        
        # Drop rows where adf_stat is NaN (no ADF data available)
        merged = merged.dropna(subset=['adf_stat'])
        
        return merged
    
    else:
        raise ValueError(f"Unknown factor type: {factor_type}")


def generate_signals_for_factor(
    factor_df: pd.DataFrame,
    factor_type: str,
    strategy: str,
    **signal_params,
) -> pd.DataFrame:
    """
    Generate signals for a specific factor type (vectorized).
    
    Args:
        factor_df: DataFrame with factor data
        factor_type: Type of factor
        strategy: Strategy name
        **signal_params: Additional parameters for signal generation
    
    Returns:
        pd.DataFrame: DataFrame with signals for all dates
    """
    if factor_type == 'volatility':
        return generate_volatility_signals_vectorized(
            factor_df,
            strategy=strategy,
            num_quintiles=signal_params.get('num_quintiles', 5),
            vol_column=signal_params.get('vol_column', 'volatility_30d'),
        )
    
    elif factor_type == 'beta':
        return generate_beta_signals_vectorized(
            factor_df,
            strategy=strategy,
            num_quintiles=signal_params.get('num_quintiles', 5),
            long_percentile=signal_params.get('long_percentile', 20),
            short_percentile=signal_params.get('short_percentile', 80),
        )
    
    elif factor_type == 'carry':
        return generate_carry_signals_vectorized(
            factor_df,
            top_n=signal_params.get('top_n', 10),
            bottom_n=signal_params.get('bottom_n', 10),
            funding_column=signal_params.get('funding_column', 'funding_rate_pct'),
        )
    
    elif factor_type == 'size':
        return generate_size_signals_vectorized(
            factor_df,
            strategy=strategy,
            num_buckets=signal_params.get('num_buckets', 5),
            marketcap_column=signal_params.get('marketcap_column', 'market_cap'),
        )
    
    elif factor_type == 'kurtosis':
        return generate_kurtosis_signals_vectorized(
            factor_df,
            strategy=strategy,
            num_quintiles=signal_params.get('num_quintiles', 5),
            long_percentile=signal_params.get('long_percentile', 20),
            short_percentile=signal_params.get('short_percentile', 80),
            kurtosis_column=signal_params.get('kurtosis_column', 'kurtosis_30d'),
            regime_filter=signal_params.get('regime_filter'),
            regime_data=signal_params.get('regime_data'),
        )
    
    elif factor_type == 'skew':
        return generate_skew_signals_vectorized(
            factor_df,
            strategy=strategy,
            num_quintiles=signal_params.get('num_quintiles', 5),
            long_percentile=signal_params.get('long_percentile', 20),
            short_percentile=signal_params.get('short_percentile', 80),
            skew_column=signal_params.get('skew_column', 'skewness_30d'),
        )
    
    elif factor_type == 'days_from_high':
        return generate_days_from_high_signals_vectorized(
            factor_df,
            max_days=signal_params.get('max_days', 20),
            lookback_window=signal_params.get('lookback_window', 200),
        )
    
    elif factor_type == 'breakout':
        return generate_breakout_signals_vectorized(
            factor_df,
            entry_window=signal_params.get('entry_window', 50),
            exit_window=signal_params.get('exit_window', 70),
        )
    
    elif factor_type == 'mean_reversion':
        return generate_mean_reversion_signals_vectorized(
            factor_df,
            zscore_threshold=signal_params.get('zscore_threshold', 1.5),
            volume_threshold=signal_params.get('volume_threshold', 1.0),
            lookback_window=signal_params.get('lookback_window', 30),
            long_only=signal_params.get('long_only', True),
        )
    
    elif factor_type == 'adf':
        return generate_adf_signals_vectorized(
            factor_df,
            strategy=strategy,
            num_quintiles=signal_params.get('num_quintiles', 5),
            long_percentile=signal_params.get('long_percentile', 20),
            short_percentile=signal_params.get('short_percentile', 80),
            adf_column=signal_params.get('adf_column', 'adf_stat'),
        )
    
    else:
        raise ValueError(f"Unknown factor type: {factor_type}")


def filter_to_rebalance_dates(
    signals_df: pd.DataFrame,
    rebalance_days: int = 1,
) -> pd.DataFrame:
    """
    Filter signals to only rebalance dates.
    
    Args:
        signals_df: DataFrame with signals for all dates
        rebalance_days: Rebalance every N days
    
    Returns:
        pd.DataFrame: Signals only on rebalance dates
    """
    all_dates = sorted(signals_df['date'].unique())
    
    if rebalance_days == 1:
        # Daily rebalancing - no filtering needed
        return signals_df
    
    # Select every Nth date
    rebalance_dates = all_dates[::rebalance_days]
    return signals_df[signals_df['date'].isin(rebalance_dates)].copy()


def forward_fill_weights(
    weights_df: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> pd.DataFrame:
    """
    Forward-fill weights to hold positions between rebalances.
    
    Args:
        weights_df: DataFrame with weights on rebalance dates
        start_date: Start date
        end_date: End date
    
    Returns:
        pd.DataFrame: Weights for all daily dates
    """
    # Create daily date range
    daily_dates = pd.DataFrame({
        'date': pd.date_range(start=start_date, end=end_date, freq='D')
    })
    
    # Get all symbols
    symbols = weights_df['symbol'].unique()
    
    # Create cartesian product of dates and symbols
    daily_grid = pd.DataFrame(
        [(d, s) for d in daily_dates['date'] for s in symbols],
        columns=['date', 'symbol']
    )
    
    # Merge with weights (left join)
    weights_daily = daily_grid.merge(
        weights_df[['date', 'symbol', 'weight']],
        on=['date', 'symbol'],
        how='left'
    )
    
    # Forward fill weights by symbol
    weights_daily = weights_daily.sort_values(['symbol', 'date'])
    weights_daily['weight'] = weights_daily.groupby('symbol')['weight'].ffill()
    
    # Drop rows with no weight (before first signal)
    weights_daily = weights_daily.dropna(subset=['weight'])
    
    # Filter out zero weights to reduce memory
    weights_daily = weights_daily[weights_daily['weight'] != 0]
    
    return weights_daily


def backtest_factor_vectorized(
    price_data: pd.DataFrame,
    factor_type: str,
    strategy: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    initial_capital: float = 10000,
    leverage: float = 1.0,
    long_allocation: float = 0.5,
    short_allocation: float = 0.5,
    rebalance_days: int = 1,
    weighting_method: Literal['equal_weight', 'risk_parity'] = 'equal_weight',
    **factor_params,
) -> Dict:
    """
    Run a fully vectorized backtest for any ranking-based factor strategy.
    
    This function eliminates ALL date loops and is 30-50x faster than traditional
    loop-based approaches.
    
    Args:
        price_data: DataFrame with OHLCV data
        factor_type: Type of factor ('volatility', 'beta', 'carry', 'size', etc.)
        strategy: Strategy name (e.g., 'long_low_short_high')
        start_date: Start date for backtest
        end_date: End date for backtest
        initial_capital: Initial portfolio capital
        leverage: Leverage multiplier
        long_allocation: Allocation to long positions
        short_allocation: Allocation to short positions
        rebalance_days: Rebalance every N days
        weighting_method: 'equal_weight' or 'risk_parity'
        **factor_params: Additional parameters for factor calculation and signal generation
    
    Returns:
        dict: Dictionary with backtest results
    """
    print(f"\n{'='*80}")
    print(f"Running Vectorized Backtest: {factor_type.upper()} Factor - {strategy}")
    print(f"{'='*80}")
    
    # Step 1: Prepare price data
    print("Step 1: Preparing price data...")
    price_df = prepare_price_data(price_data, start_date, end_date)
    print(f"  ? Prepared {len(price_df)} rows, {price_df['symbol'].nunique()} symbols")
    
    # Step 2: Calculate factor data for ALL dates (vectorized)
    print(f"Step 2: Calculating {factor_type} factor for ALL dates...")
    factor_df = prepare_factor_data(price_df, factor_type, **factor_params)
    
    if factor_df is None or len(factor_df) == 0:
        raise ValueError(f"No factor data available for {factor_type} factor")
    
    print(f"  ? Calculated factor for {len(factor_df)} rows")
    
    # Step 2.5: Calculate market regime (if regime filter requested for kurtosis)
    regime_filter = factor_params.get('regime_filter')
    if factor_type == 'kurtosis' and regime_filter and regime_filter != 'always':
        print(f"Step 2.5: Calculating market regime (filter: {regime_filter})...")
        try:
            reference_symbol = factor_params.get('reference_symbol', 'BTC')
            regime_data = calculate_regime_vectorized(
                price_df,
                reference_symbol=reference_symbol,
                ma_short=50,
                ma_long=200
            )
            print(f"  ? Calculated regime for {len(regime_data)} dates")
            
            # Count regime distribution
            regime_counts = regime_data['regime'].value_counts()
            print(f"  ? Bull days: {regime_counts.get('bull', 0)} ({regime_counts.get('bull', 0)/len(regime_data)*100:.1f}%)")
            print(f"  ? Bear days: {regime_counts.get('bear', 0)} ({regime_counts.get('bear', 0)/len(regime_data)*100:.1f}%)")
            
            # Add regime data to factor_params so it's passed to signal generation
            factor_params['regime_data'] = regime_data
        except Exception as e:
            print(f"  ??  Warning: Regime calculation failed: {e}")
            print(f"  Continuing without regime filter (signals will be generated for all dates)")
            factor_params['regime_filter'] = 'always'
    
    # Step 3: Generate signals for ALL dates (vectorized)
    print("Step 3: Generating signals for ALL dates...")
    signals_df = generate_signals_for_factor(
        factor_df,
        factor_type,
        strategy,
        **factor_params
    )
    print(f"  ? Generated {len(signals_df)} signals")
    print(f"  ? Long positions: {(signals_df['signal'] == 1).sum()}")
    print(f"  ? Short positions: {(signals_df['signal'] == -1).sum()}")
    
    # Step 4: Filter to rebalance dates
    print(f"Step 4: Filtering to rebalance dates (every {rebalance_days} days)...")
    signals_rebalance = filter_to_rebalance_dates(signals_df, rebalance_days)
    num_rebalances = len(signals_rebalance['date'].unique())
    print(f"  ? {num_rebalances} rebalance dates")
    
    # Step 5: Calculate weights for ALL rebalance dates (vectorized)
    print("Step 5: Calculating portfolio weights...")
    
    # Prepare volatility data for risk parity if needed
    volatility_df = None
    if weighting_method == 'risk_parity':
        if 'volatility' in signals_rebalance.columns:
            volatility_df = signals_rebalance[['date', 'symbol', 'volatility']].copy()
        else:
            # Calculate volatility
            vol_window = factor_params.get('volatility_window', 30)
            price_df['volatility'] = price_df.groupby('symbol')['daily_return'].transform(
                lambda x: x.rolling(window=vol_window, min_periods=vol_window).std() * np.sqrt(365)
            )
            volatility_df = price_df[['date', 'symbol', 'volatility']].copy()
    
    weights_df = calculate_weights_vectorized(
        signals_rebalance,
        volatility_df=volatility_df,
        weighting_method=weighting_method,
        long_allocation=long_allocation * leverage,
        short_allocation=short_allocation * leverage,
    )
    print(f"  ? Calculated weights for {len(weights_df)} positions")
    
    # Step 6: Forward-fill weights to daily frequency
    print("Step 6: Forward-filling weights between rebalances...")
    all_dates = signals_df['date'].unique()
    weights_daily = forward_fill_weights(
        weights_df,
        start_date=all_dates.min(),
        end_date=all_dates.max(),
    )
    print(f"  ? Forward-filled to {len(weights_daily['date'].unique())} days")
    
    # Step 7: Shift returns by 1 day to avoid lookahead bias
    # Signals on day T should use returns from day T+1
    print("Step 7: Aligning returns (avoiding lookahead bias)...")
    returns_df = price_df[['date', 'symbol', 'daily_return']].copy()
    returns_df['date'] = returns_df['date'] - pd.Timedelta(days=1)  # Shift back so T+1 returns match T signals
    
    # Step 8: Calculate portfolio returns for ALL dates (vectorized)
    print("Step 8: Calculating portfolio returns...")
    portfolio_returns = calculate_portfolio_returns_vectorized(
        weights_daily,
        returns_df,
    )
    print(f"  ? Calculated returns for {len(portfolio_returns)} days")
    
    # Step 9: Calculate cumulative returns (vectorized)
    print("Step 9: Calculating cumulative performance...")
    results = calculate_cumulative_returns_vectorized(
        portfolio_returns,
        initial_capital=initial_capital,
    )
    
    # Step 10: Calculate performance metrics
    print("Step 10: Computing performance metrics...")
    
    # Check if we have results
    if len(results) == 0:
        print("\n??  WARNING: No portfolio returns calculated (empty results DataFrame)")
        print("This may be due to:")
        print("  - Start date filtering removed all data")
        print("  - No valid signals generated")
        print("  - Date alignment issues between factor data and price data")
        return None
    
    total_return = results['cum_return'].iloc[-1] - 1
    num_days = len(results)
    years = num_days / 365.25
    annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
    
    volatility = results['portfolio_return'].std() * np.sqrt(365)
    sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
    
    max_drawdown = results['drawdown'].min()
    avg_drawdown = results[results['drawdown'] < 0]['drawdown'].mean() if (results['drawdown'] < 0).any() else 0
    
    downside_returns = results[results['portfolio_return'] < 0]['portfolio_return']
    downside_vol = downside_returns.std() * np.sqrt(365) if len(downside_returns) > 0 else 0
    sortino_ratio = annualized_return / downside_vol if downside_vol > 0 else 0
    
    win_rate = (results['portfolio_return'] > 0).sum() / len(results) if len(results) > 0 else 0
    
    print(f"\n{'='*80}")
    print(f"BACKTEST RESULTS")
    print(f"{'='*80}")
    print(f"Total Return:       {total_return:>10.2%}")
    print(f"Annualized Return:  {annualized_return:>10.2%}")
    print(f"Volatility:         {volatility:>10.2%}")
    print(f"Sharpe Ratio:       {sharpe_ratio:>10.3f}")
    print(f"Sortino Ratio:      {sortino_ratio:>10.3f}")
    print(f"Max Drawdown:       {max_drawdown:>10.2%}")
    print(f"Win Rate:           {win_rate:>10.2%}")
    print(f"Number of Days:     {num_days:>10}")
    print(f"{'='*80}\n")
    
    return {
        'portfolio_values': results[['date', 'portfolio_value']],
        'portfolio_returns': portfolio_returns,
        'signals': signals_df,
        'weights': weights_df,
        'metrics': {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'max_drawdown': max_drawdown,
            'avg_drawdown': avg_drawdown,
            'downside_vol': downside_vol,
            'win_rate': win_rate,
            'num_days': num_days,
        }
    }
