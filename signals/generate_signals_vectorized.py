#!/usr/bin/env python3
"""
Vectorized Signal Generation Module

This module provides vectorized implementations of common ranking-based factor signals.
Instead of looping through dates one at a time, these functions compute signals for
ALL dates simultaneously using pandas vectorized operations.

Performance: 10-100x faster than loop-based approaches.

Supported factors:
- Volatility (low vol anomaly)
- Beta (betting against beta)
- Carry (funding rate arbitrage)
- Size (market cap factor)
- Generic ranking (customizable)
"""

import pandas as pd
import numpy as np
from typing import Union, Literal


def assign_quintiles_vectorized(
    data: pd.DataFrame,
    factor_column: str,
    num_quintiles: int = 5,
    ascending: bool = True
) -> pd.DataFrame:
    """
    Assign quintiles for ALL dates at once using vectorized operations.
    
    This is the core vectorization pattern that can be used for any ranking-based factor.
    
    Args:
        data: DataFrame with 'date', 'symbol', and factor columns
        factor_column: Name of column to rank on (e.g., 'volatility_30d', 'beta', 'market_cap')
        num_quintiles: Number of quintiles/buckets (default 5)
        ascending: True if lower values get quintile 1, False otherwise
    
    Returns:
        DataFrame with 'quintile' and 'rank' columns added
    
    Example:
        >>> volatility_df = calculate_rolling_30d_volatility(price_data)
        >>> ranked_df = assign_quintiles_vectorized(
        ...     volatility_df,
        ...     factor_column='volatility_30d',
        ...     num_quintiles=5,
        ...     ascending=True  # Low vol = quintile 1
        ... )
    """
    df = data.copy()
    
    # Drop NaN values in factor column
    df = df.dropna(subset=[factor_column])
    
    # Vectorized: compute ranks for ALL dates at once
    # groupby('date') ensures ranking is done within each date
    df['rank'] = df.groupby('date')[factor_column].rank(
        method='first',
        ascending=ascending
    )
    
    # Count of symbols per date (for percentile calculation)
    df['count_per_date'] = df.groupby('date')[factor_column].transform('count')
    
    # Calculate percentile
    df['percentile'] = (df['rank'] / df['count_per_date']) * 100
    
    # Assign quintiles using rank-based approach (more stable than qcut)
    df['quintile'] = df.groupby('date')['rank'].transform(
        lambda x: pd.cut(
            x,
            bins=num_quintiles,
            labels=range(1, num_quintiles + 1),
            include_lowest=True
        ) if len(x) >= num_quintiles else None
    )
    
    # Convert quintile to int
    df['quintile'] = df['quintile'].astype('Int64')
    
    return df


def generate_long_short_signals_vectorized(
    ranked_df: pd.DataFrame,
    long_condition: str,
    short_condition: str = None
) -> pd.DataFrame:
    """
    Generate long/short signals based on quintile or percentile conditions.
    
    Args:
        ranked_df: DataFrame from assign_quintiles_vectorized()
        long_condition: Condition for long signals (e.g., 'quintile == 1', 'percentile <= 20')
        short_condition: Condition for short signals (e.g., 'quintile == 5', 'percentile >= 80')
                        If None, no short positions
    
    Returns:
        DataFrame with 'signal' column added (-1, 0, or 1)
    
    Example:
        >>> signals_df = generate_long_short_signals_vectorized(
        ...     ranked_df,
        ...     long_condition='quintile == 1',      # Long lowest vol
        ...     short_condition='quintile == 5'      # Short highest vol
        ... )
    """
    df = ranked_df.copy()
    
    # Initialize signals to 0 (no position)
    df['signal'] = 0
    
    # Apply long condition (vectorized)
    df.loc[df.eval(long_condition), 'signal'] = 1
    
    # Apply short condition if provided (vectorized)
    if short_condition:
        df.loc[df.eval(short_condition), 'signal'] = -1
    
    return df


def generate_volatility_signals_vectorized(
    volatility_df: pd.DataFrame,
    strategy: Literal[
        'long_low_short_high',
        'long_low_vol',
        'long_high_vol',
        'long_high_short_low'
    ] = 'long_low_short_high',
    num_quintiles: int = 5,
    vol_column: str = 'volatility_30d'
) -> pd.DataFrame:
    """
    Generate volatility factor signals for ALL dates at once (vectorized).
    
    Low volatility anomaly: Low vol assets tend to outperform high vol assets
    on a risk-adjusted basis.
    
    Args:
        volatility_df: DataFrame with 'date', 'symbol', and volatility column
        strategy: Trading strategy:
            - 'long_low_short_high': Long low vol, short high vol (classic anomaly)
            - 'long_low_vol': Long low vol only
            - 'long_high_vol': Long high vol only  
            - 'long_high_short_low': Long high vol, short low vol (contrarian)
        num_quintiles: Number of volatility buckets
        vol_column: Name of volatility column
    
    Returns:
        DataFrame with signals for each date/symbol
    
    Example:
        >>> from signals.calc_vola import calculate_rolling_30d_volatility
        >>> volatility_df = calculate_rolling_30d_volatility(price_data)
        >>> signals_df = generate_volatility_signals_vectorized(
        ...     volatility_df,
        ...     strategy='long_low_short_high',
        ...     num_quintiles=5
        ... )
        >>> # signals_df now has signals for ALL dates - instant lookup!
        >>> today_signals = signals_df[signals_df['date'] == '2024-01-15']
    """
    # Assign quintiles (vectorized for all dates)
    ranked_df = assign_quintiles_vectorized(
        volatility_df,
        factor_column=vol_column,
        num_quintiles=num_quintiles,
        ascending=True  # Low vol = quintile 1
    )
    
    # Generate signals based on strategy (vectorized)
    if strategy == 'long_low_short_high':
        signals_df = generate_long_short_signals_vectorized(
            ranked_df,
            long_condition='quintile == 1',
            short_condition=f'quintile == {num_quintiles}'
        )
    
    elif strategy == 'long_low_vol':
        signals_df = generate_long_short_signals_vectorized(
            ranked_df,
            long_condition='quintile == 1',
            short_condition=None
        )
    
    elif strategy == 'long_high_vol':
        signals_df = generate_long_short_signals_vectorized(
            ranked_df,
            long_condition=f'quintile == {num_quintiles}',
            short_condition=None
        )
    
    elif strategy == 'long_high_short_low':
        signals_df = generate_long_short_signals_vectorized(
            ranked_df,
            long_condition=f'quintile == {num_quintiles}',
            short_condition='quintile == 1'
        )
    
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
    
    return signals_df[['date', 'symbol', vol_column, 'quintile', 'percentile', 'signal']]


def generate_beta_signals_vectorized(
    beta_df: pd.DataFrame,
    strategy: Literal[
        'betting_against_beta',
        'traditional_risk_premium',
        'long_low_beta',
        'long_high_beta'
    ] = 'betting_against_beta',
    num_quintiles: int = 5,
    long_percentile: float = 20,
    short_percentile: float = 80
) -> pd.DataFrame:
    """
    Generate beta factor signals for ALL dates at once (vectorized).
    
    Betting Against Beta: Low beta assets tend to outperform high beta assets
    on a risk-adjusted basis (BAB factor).
    
    Args:
        beta_df: DataFrame with 'date', 'symbol', 'beta' columns
        strategy: Trading strategy:
            - 'betting_against_beta': Long low beta, short high beta (BAB)
            - 'traditional_risk_premium': Long high beta, short low beta
            - 'long_low_beta': Long low beta only (defensive)
            - 'long_high_beta': Long high beta only (aggressive)
        num_quintiles: Number of beta buckets
        long_percentile: Percentile threshold for longs (e.g., 20 = bottom 20%)
        short_percentile: Percentile threshold for shorts (e.g., 80 = top 20%)
    
    Returns:
        DataFrame with signals for each date/symbol
    
    Example:
        >>> signals_df = generate_beta_signals_vectorized(
        ...     beta_df,
        ...     strategy='betting_against_beta',
        ...     long_percentile=20,
        ...     short_percentile=80
        ... )
    """
    # Assign quintiles (vectorized for all dates)
    ranked_df = assign_quintiles_vectorized(
        beta_df,
        factor_column='beta',
        num_quintiles=num_quintiles,
        ascending=True  # Low beta = quintile 1
    )
    
    # Generate signals based on strategy (vectorized)
    if strategy == 'betting_against_beta':
        signals_df = generate_long_short_signals_vectorized(
            ranked_df,
            long_condition=f'percentile <= {long_percentile}',
            short_condition=f'percentile >= {short_percentile}'
        )
    
    elif strategy == 'traditional_risk_premium':
        signals_df = generate_long_short_signals_vectorized(
            ranked_df,
            long_condition=f'percentile >= {short_percentile}',
            short_condition=f'percentile <= {long_percentile}'
        )
    
    elif strategy == 'long_low_beta':
        signals_df = generate_long_short_signals_vectorized(
            ranked_df,
            long_condition=f'percentile <= {long_percentile}',
            short_condition=None
        )
    
    elif strategy == 'long_high_beta':
        signals_df = generate_long_short_signals_vectorized(
            ranked_df,
            long_condition=f'percentile >= {short_percentile}',
            short_condition=None
        )
    
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
    
    return signals_df[['date', 'symbol', 'beta', 'quintile', 'percentile', 'signal']]


def generate_carry_signals_vectorized(
    funding_df: pd.DataFrame,
    top_n: int = 10,
    bottom_n: int = 10,
    column: str = 'funding_rate_pct'
) -> pd.DataFrame:
    """
    Generate carry trade signals for ALL dates at once (vectorized).
    
    Carry strategy: Long coins with lowest funding rates (we receive funding),
    short coins with highest funding rates (we receive funding).
    
    Args:
        funding_df: DataFrame with 'date', 'symbol', and funding rate column
        top_n: Number of highest funding rate coins to short
        bottom_n: Number of lowest funding rate coins to long
        column: Name of funding rate column
    
    Returns:
        DataFrame with signals for each date/symbol
    
    Example:
        >>> signals_df = generate_carry_signals_vectorized(
        ...     funding_df,
        ...     top_n=10,    # Short top 10 highest funding
        ...     bottom_n=10  # Long bottom 10 lowest funding
        ... )
    """
    df = funding_df.copy()
    df = df.dropna(subset=[column])
    
    # Vectorized: rank within each date
    df['funding_rank'] = df.groupby('date')[column].rank(
        method='first',
        ascending=True  # Lower funding rate = lower rank
    )
    
    # Count of coins per date
    df['count_per_date'] = df.groupby('date')[column].transform('count')
    
    # Generate signals (vectorized conditionals)
    df['signal'] = 0
    
    # Long: bottom_n lowest funding rates (rank <= bottom_n)
    df.loc[df['funding_rank'] <= bottom_n, 'signal'] = 1
    
    # Short: top_n highest funding rates (rank > count - top_n)
    df.loc[df['funding_rank'] > (df['count_per_date'] - top_n), 'signal'] = -1
    
    return df[['date', 'symbol', column, 'funding_rank', 'signal']]


def generate_size_signals_vectorized(
    market_cap_df: pd.DataFrame,
    strategy: Literal[
        'small_minus_big',
        'long_small_cap',
        'long_large_cap',
        'big_minus_small'
    ] = 'small_minus_big',
    num_quintiles: int = 5
) -> pd.DataFrame:
    """
    Generate size factor signals for ALL dates at once (vectorized).
    
    Size premium: Small cap assets tend to outperform large cap assets
    over long time periods (SMB factor).
    
    Args:
        market_cap_df: DataFrame with 'date', 'symbol', 'market_cap' columns
        strategy: Trading strategy:
            - 'small_minus_big': Long small cap, short large cap (classic SMB)
            - 'long_small_cap': Long small cap only
            - 'long_large_cap': Long large cap only (quality/safety)
            - 'big_minus_small': Long large cap, short small cap (contrarian)
        num_quintiles: Number of size buckets
    
    Returns:
        DataFrame with signals for each date/symbol
    
    Example:
        >>> signals_df = generate_size_signals_vectorized(
        ...     market_cap_df,
        ...     strategy='small_minus_big',
        ...     num_quintiles=5
        ... )
    """
    # Assign quintiles (vectorized for all dates)
    # ascending=True means small cap = quintile 1
    ranked_df = assign_quintiles_vectorized(
        market_cap_df,
        factor_column='market_cap',
        num_quintiles=num_quintiles,
        ascending=True  # Small cap = quintile 1
    )
    
    # Generate signals based on strategy (vectorized)
    if strategy == 'small_minus_big':
        signals_df = generate_long_short_signals_vectorized(
            ranked_df,
            long_condition='quintile == 1',  # Long small cap
            short_condition=f'quintile == {num_quintiles}'  # Short large cap
        )
    
    elif strategy == 'long_small_cap':
        signals_df = generate_long_short_signals_vectorized(
            ranked_df,
            long_condition='quintile == 1',
            short_condition=None
        )
    
    elif strategy == 'long_large_cap':
        signals_df = generate_long_short_signals_vectorized(
            ranked_df,
            long_condition=f'quintile == {num_quintiles}',
            short_condition=None
        )
    
    elif strategy == 'big_minus_small':
        signals_df = generate_long_short_signals_vectorized(
            ranked_df,
            long_condition=f'quintile == {num_quintiles}',
            short_condition='quintile == 1'
        )
    
    else:
        raise ValueError(f"Unknown strategy: {strategy}")
    
    return signals_df[['date', 'symbol', 'market_cap', 'quintile', 'percentile', 'signal']]


def calculate_weights_vectorized(
    signals_df: pd.DataFrame,
    weighting_method: Literal['equal_weight', 'risk_parity'] = 'equal_weight',
    long_allocation: float = 0.5,
    short_allocation: float = 0.5,
    volatility_column: str = None
) -> pd.DataFrame:
    """
    Calculate portfolio weights for ALL dates at once (vectorized).
    
    Args:
        signals_df: DataFrame with 'date', 'symbol', 'signal' columns
        weighting_method: 'equal_weight' or 'risk_parity'
        long_allocation: Total allocation to long positions (e.g., 0.5 = 50%)
        short_allocation: Total allocation to short positions (e.g., 0.5 = 50%)
        volatility_column: Required for risk_parity method
    
    Returns:
        DataFrame with 'weight' column added
    
    Example:
        >>> weights_df = calculate_weights_vectorized(
        ...     signals_df,
        ...     weighting_method='equal_weight',
        ...     long_allocation=0.5,
        ...     short_allocation=0.5
        ... )
    """
    df = signals_df.copy()
    
    if weighting_method == 'equal_weight':
        # Count positions per side per date (vectorized)
        df['long_count'] = df[df['signal'] == 1].groupby('date')['signal'].transform('count')
        df['short_count'] = df[df['signal'] == -1].groupby('date')['signal'].transform('count')
        
        # Vectorized weight calculation
        df['weight'] = 0.0
        
        # Long positions: equal weight
        long_mask = df['signal'] == 1
        df.loc[long_mask, 'weight'] = long_allocation / df.loc[long_mask, 'long_count']
        
        # Short positions: equal weight (negative)
        short_mask = df['signal'] == -1
        df.loc[short_mask, 'weight'] = -short_allocation / df.loc[short_mask, 'short_count']
    
    elif weighting_method == 'risk_parity':
        if volatility_column is None or volatility_column not in df.columns:
            raise ValueError("risk_parity requires volatility_column to be specified and present in data")
        
        def calc_risk_parity_weights(group):
            """Calculate risk parity weights within a group (date/side)"""
            if group['signal'].iloc[0] == 0:
                group['weight'] = 0.0
                return group
            
            # Use volatility if available, otherwise equal weight
            if volatility_column in group.columns and not group[volatility_column].isna().all():
                valid_vol = group[volatility_column].fillna(group[volatility_column].mean())
                valid_vol = valid_vol.clip(lower=0.0001)  # Avoid division by zero
                inv_vol = 1.0 / valid_vol
                group['rp_weight'] = inv_vol / inv_vol.sum()
            else:
                # Fall back to equal weight
                group['rp_weight'] = 1.0 / len(group)
            
            return group
        
        # Apply risk parity separately for longs and shorts on each date
        df['weight'] = 0.0
        
        # Process longs
        longs = df[df['signal'] == 1].copy()
        if len(longs) > 0:
            longs = longs.groupby('date', group_keys=False).apply(calc_risk_parity_weights)
            longs['weight'] = longs['rp_weight'] * long_allocation
            df.loc[df['signal'] == 1, 'weight'] = longs['weight'].values
        
        # Process shorts
        shorts = df[df['signal'] == -1].copy()
        if len(shorts) > 0:
            shorts = shorts.groupby('date', group_keys=False).apply(calc_risk_parity_weights)
            shorts['weight'] = shorts['rp_weight'] * -short_allocation
            df.loc[df['signal'] == -1, 'weight'] = shorts['weight'].values
    
    else:
        raise ValueError(f"Unknown weighting method: {weighting_method}")
    
    # Remove helper columns
    df = df.drop(columns=['long_count', 'short_count'], errors='ignore')
    
    return df


def calculate_portfolio_returns_vectorized(
    weights_df: pd.DataFrame,
    returns_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculate portfolio returns for ALL dates at once using vectorized operations.
    
    This is dramatically faster than looping through dates.
    
    Args:
        weights_df: DataFrame with 'date', 'symbol', 'weight' columns
        returns_df: DataFrame with 'date', 'symbol', 'daily_return' columns
    
    Returns:
        DataFrame with 'date' and 'portfolio_return' columns
    
    Example:
        >>> portfolio_returns = calculate_portfolio_returns_vectorized(
        ...     weights_df,
        ...     returns_df
        ... )
    """
    # Merge weights and returns on date and symbol (vectorized)
    merged = pd.merge(
        weights_df[['date', 'symbol', 'weight']],
        returns_df[['date', 'symbol', 'daily_return']],
        on=['date', 'symbol'],
        how='inner'
    )
    
    # Vectorized: multiply weights by returns
    merged['contribution'] = merged['weight'] * merged['daily_return']
    
    # Vectorized: sum contributions by date
    portfolio_returns = merged.groupby('date')['contribution'].sum().reset_index()
    portfolio_returns.columns = ['date', 'portfolio_return']
    
    return portfolio_returns


def calculate_cumulative_returns_vectorized(
    portfolio_returns_df: pd.DataFrame,
    initial_capital: float = 10000
) -> pd.DataFrame:
    """
    Calculate cumulative returns and portfolio metrics over time (vectorized).
    
    Args:
        portfolio_returns_df: DataFrame with 'date' and 'portfolio_return' columns
        initial_capital: Starting capital
    
    Returns:
        DataFrame with cumulative metrics (portfolio_value, drawdown, etc.)
    
    Example:
        >>> results = calculate_cumulative_returns_vectorized(
        ...     portfolio_returns,
        ...     initial_capital=10000
        ... )
    """
    df = portfolio_returns_df.copy()
    
    # Vectorized cumulative product for portfolio value
    df['cum_return'] = (1 + df['portfolio_return']).cumprod()
    df['portfolio_value'] = initial_capital * df['cum_return']
    
    # Vectorized cumulative max for drawdown calculation
    df['cum_max'] = df['portfolio_value'].cummax()
    df['drawdown'] = (df['portfolio_value'] - df['cum_max']) / df['cum_max']
    
    # Vectorized rolling metrics (optional)
    df['rolling_vol_30d'] = df['portfolio_return'].rolling(window=30).std() * np.sqrt(365)
    df['rolling_sharpe_30d'] = (
        df['portfolio_return'].rolling(window=30).mean() * 365 / 
        (df['portfolio_return'].rolling(window=30).std() * np.sqrt(365))
    )
    
    return df


if __name__ == "__main__":
    """
    Example usage showing vectorized signal generation
    """
    print("=" * 80)
    print("Vectorized Signal Generation Example")
    print("=" * 80)
    
    # Create sample data
    dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')
    symbols = [f'COIN{i}' for i in range(1, 11)]
    
    # Generate sample volatility data
    data = []
    for date in dates:
        for symbol in symbols:
            vol = np.random.uniform(0.3, 1.5)
            data.append({
                'date': date,
                'symbol': symbol,
                'volatility_30d': vol,
                'close': 100 * (1 + np.random.randn() * 0.01)
            })
    
    df = pd.DataFrame(data)
    
    print(f"\nGenerated sample data: {len(df)} rows")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")
    print(f"Symbols: {len(df['symbol'].unique())}")
    
    # VECTORIZED: Generate signals for ALL dates at once
    print("\n" + "=" * 80)
    print("Generating signals for ALL dates (vectorized)...")
    print("=" * 80)
    
    import time
    start = time.time()
    
    signals_df = generate_volatility_signals_vectorized(
        df,
        strategy='long_low_short_high',
        num_quintiles=5
    )
    
    elapsed = time.time() - start
    print(f"\n✓ Generated {len(signals_df)} signals in {elapsed:.4f} seconds")
    print(f"  ({len(signals_df) / elapsed:.0f} signals/second)")
    
    # Show sample signals
    print("\n" + "=" * 80)
    print("Sample signals for 2024-06-15:")
    print("=" * 80)
    
    sample_date = pd.Timestamp('2024-06-15')
    sample_signals = signals_df[signals_df['date'] == sample_date].sort_values('volatility_30d')
    print(sample_signals.to_string(index=False))
    
    # Calculate weights
    print("\n" + "=" * 80)
    print("Calculating weights (vectorized)...")
    print("=" * 80)
    
    weights_df = calculate_weights_vectorized(
        signals_df,
        weighting_method='equal_weight',
        long_allocation=0.5,
        short_allocation=0.5
    )
    
    sample_weights = weights_df[weights_df['date'] == sample_date].sort_values('weight', ascending=False)
    print("\nSample weights for 2024-06-15:")
    print(sample_weights[['symbol', 'signal', 'weight', 'volatility_30d']].to_string(index=False))
    
    print("\n" + "=" * 80)
    print("✓ Vectorized signal generation complete!")
    print("=" * 80)
    print("\nSee /workspace/docs/SIGNAL_VECTORIZATION_GUIDE.md for full documentation.")
