#!/usr/bin/env python3
"""
Calculate Comprehensive DeFi Factors

Factors calculated:
1. Fee Yield = annualized fees ÷ FDV (or MC)
2. Emission/Incentive Yield = annualized incentives ÷ FDV (or MC)  
3. Net Yield = Fee Yield − Emission Yield
4. Revenue Productivity = annualized fees ÷ TVL
5. Turnover (Liquidity/Velocity proxy) = 24h spot volume ÷ FDV

Data sources:
- DefiLlama: fees, TVL, reward APYs
- CoinGecko: FDV, market cap, 24h volume
"""

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Optional


def load_defillama_data(date: str = None) -> pd.DataFrame:
    """Load DefiLlama factors (fees, TVL, yields)"""
    if date is None:
        date = datetime.now().strftime("%Y%m%d")
    
    filepath = Path(f"/workspace/data/raw/defillama_factors_{date}.csv")
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    print(f"Loading DefiLlama data: {filepath.name}")
    df = pd.read_csv(filepath)
    return df


def load_coingecko_data(date: str = None) -> pd.DataFrame:
    """Load CoinGecko market data (FDV, MC, volume)"""
    if date is None:
        date = datetime.now().strftime("%Y%m%d")
    
    filepath = Path(f"/workspace/data/raw/coingecko_market_data_{date}.csv")
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    print(f"Loading CoinGecko data: {filepath.name}")
    df = pd.read_csv(filepath)
    
    # Standardize column names
    df = df.rename(columns={
        'fully_diluted_valuation': 'fdv',
        'total_volume': 'volume_24h',
    })
    
    return df


def calculate_comprehensive_factors(
    defillama_df: pd.DataFrame,
    coingecko_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Calculate all comprehensive DeFi factors
    
    Args:
        defillama_df: DataFrame with DefiLlama data
        coingecko_df: DataFrame with CoinGecko data
        
    Returns:
        DataFrame with all calculated factors
    """
    # Merge datasets on symbol
    df = pd.merge(
        defillama_df,
        coingecko_df[['symbol', 'market_cap', 'fdv', 'volume_24h', 'current_price']],
        on='symbol',
        how='inner'
    )
    
    print(f"\nMerged data for {len(df)} tokens\n")
    
    # Use FDV if available, otherwise market_cap
    df['valuation'] = df['fdv'].fillna(df['market_cap'])
    
    # Handle missing values
    df['daily_fees'] = df['daily_fees'].fillna(0)
    df['daily_revenue'] = df['daily_revenue'].fillna(0)
    df['tvl'] = df['tvl'].fillna(0)
    df['total_tvl'] = df['total_tvl'].fillna(0)
    df['weighted_apy_reward'] = df['weighted_apy_reward'].fillna(0)
    df['volume_24h'] = df['volume_24h'].fillna(0)
    
    # Combined TVL (from both protocol and pools)
    df['combined_tvl'] = df['tvl'] + df['total_tvl']
    
    # ========================================================================
    # FACTOR 1: Fee Yield = annualized fees ÷ FDV
    # ========================================================================
    df['fee_yield_pct'] = (df['daily_fees'] * 365 / df['valuation'] * 100).replace([np.inf, -np.inf], np.nan)
    
    # ========================================================================
    # FACTOR 2: Emission/Incentive Yield = annualized incentives ÷ FDV
    # ========================================================================
    # Reward APY from DefiLlama is already annualized
    # But we need to convert APY to absolute dollar amount, then back to yield on FDV
    # Simplified: use reward APY directly as proxy (it's yield on staked amount)
    # For more accurate calculation, we'd need: incentives_annual = TVL * reward_apy / 100
    df['emission_value_annual'] = df['combined_tvl'] * df['weighted_apy_reward'] / 100
    df['emission_yield_pct'] = (df['emission_value_annual'] / df['valuation'] * 100).replace([np.inf, -np.inf], np.nan)
    
    # ========================================================================
    # FACTOR 3: Net Yield = Fee Yield − Emission Yield
    # ========================================================================
    df['net_yield_pct'] = df['fee_yield_pct'] - df['emission_yield_pct']
    
    # ========================================================================
    # FACTOR 4: Revenue Productivity = annualized fees ÷ TVL
    # ========================================================================
    df['revenue_productivity_pct'] = (df['daily_fees'] * 365 / df['combined_tvl'] * 100).replace([np.inf, -np.inf], np.nan)
    
    # ========================================================================
    # FACTOR 5: Turnover = 24h spot volume ÷ FDV
    # ========================================================================
    df['turnover_ratio'] = (df['volume_24h'] / df['valuation']).replace([np.inf, -np.inf], np.nan)
    df['turnover_pct'] = df['turnover_ratio'] * 100
    
    # Additional useful metrics
    df['tvl_to_fdv'] = (df['combined_tvl'] / df['valuation']).replace([np.inf, -np.inf], np.nan)
    df['volume_to_tvl'] = (df['volume_24h'] / df['combined_tvl']).replace([np.inf, -np.inf], np.nan)
    
    return df


def generate_factor_signals(
    df: pd.DataFrame,
    factor_name: str,
    long_threshold: float = 80,
    short_threshold: float = 20,
    min_fdv: float = 10_000_000,  # Min $10M FDV
    ascending: bool = False
) -> pd.DataFrame:
    """
    Generate signals for a specific factor
    
    Args:
        df: DataFrame with factors
        factor_name: Column name of the factor
        long_threshold: Percentile for long signals
        short_threshold: Percentile for short signals
        min_fdv: Minimum FDV to include
        ascending: If True, lower values are better (e.g., emission yield)
        
    Returns:
        DataFrame with signals
    """
    df_filtered = df[
        (df['valuation'] >= min_fdv) &
        (df[factor_name].notna())
    ].copy()
    
    if df_filtered.empty:
        return df_filtered
    
    # Calculate percentiles
    df_filtered['percentile'] = df_filtered[factor_name].rank(
        ascending=ascending,
        pct=True
    ) * 100
    
    # Generate signals
    df_filtered['signal'] = 'neutral'
    df_filtered.loc[df_filtered['percentile'] >= long_threshold, 'signal'] = 'long'
    df_filtered.loc[df_filtered['percentile'] <= short_threshold, 'signal'] = 'short'
    
    # Calculate weights
    long_count = (df_filtered['signal'] == 'long').sum()
    short_count = (df_filtered['signal'] == 'short').sum()
    
    df_filtered['weight'] = 0.0
    if long_count > 0:
        df_filtered.loc[df_filtered['signal'] == 'long', 'weight'] = 1.0 / long_count
    if short_count > 0:
        df_filtered.loc[df_filtered['signal'] == 'short', 'weight'] = -1.0 / short_count
    
    return df_filtered


def print_factor_summary(df: pd.DataFrame, factor_name: str, description: str):
    """Print summary statistics for a factor"""
    print(f"\n{description}")
    print("=" * 80)
    
    factor_data = df[df[factor_name].notna()]
    if factor_data.empty:
        print("No data available")
        return
    
    print(f"Tokens with data: {len(factor_data)}")
    print(f"Mean: {factor_data[factor_name].mean():.2f}")
    print(f"Median: {factor_data[factor_name].median():.2f}")
    print(f"Std Dev: {factor_data[factor_name].std():.2f}")
    
    # Top 5
    print(f"\nTop 5 (highest {factor_name}):")
    top_5 = factor_data.nlargest(5, factor_name)
    for _, row in top_5.iterrows():
        print(f"  {row['symbol']:8s}: {row[factor_name]:8.2f} "
              f"(FDV: ${row['valuation']:,.0f})")
    
    # Bottom 5
    print(f"\nBottom 5 (lowest {factor_name}):")
    bottom_5 = factor_data.nsmallest(5, factor_name)
    for _, row in bottom_5.iterrows():
        print(f"  {row['symbol']:8s}: {row[factor_name]:8.2f} "
              f"(FDV: ${row['valuation']:,.0f})")


def main():
    """Calculate comprehensive DeFi factors"""
    print("=" * 80)
    print("Comprehensive DeFi Factor Calculator")
    print("=" * 80)
    print()
    
    # Load data
    try:
        defillama_df = load_defillama_data()
        coingecko_df = load_coingecko_data()
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nPlease run data fetch scripts first:")
        print("  1. python3 data/scripts/fetch_defillama_data.py")
        print("  2. python3 data/scripts/map_defillama_to_universe.py")
        print("  3. python3 data/scripts/fetch_coingecko_market_data.py")
        return
    
    # Calculate factors
    df = calculate_comprehensive_factors(defillama_df, coingecko_df)
    
    # Save comprehensive dataset
    date = datetime.now().strftime("%Y%m%d")
    output_file = f"/workspace/data/raw/comprehensive_defi_factors_{date}.csv"
    df.to_csv(output_file, index=False)
    print(f"✓ Saved comprehensive factors: {output_file}\n")
    
    # Print summaries for each factor
    factors = [
        ('fee_yield_pct', 'Factor 1: Fee Yield %'),
        ('emission_yield_pct', 'Factor 2: Emission Yield %'),
        ('net_yield_pct', 'Factor 3: Net Yield %'),
        ('revenue_productivity_pct', 'Factor 4: Revenue Productivity %'),
        ('turnover_pct', 'Factor 5: Turnover %'),
    ]
    
    for factor_col, description in factors:
        print_factor_summary(df, factor_col, description)
    
    # Generate signals for each factor
    print("\n" + "=" * 80)
    print("Generating Factor Signals")
    print("=" * 80)
    
    signals_dir = Path("/workspace/signals")
    
    factor_configs = [
        ('fee_yield_pct', 'fee_yield', False, 'High fee yield = strong revenue'),
        ('emission_yield_pct', 'emission_yield', True, 'Low emission = less dilution'),
        ('net_yield_pct', 'net_yield', False, 'Positive net yield = sustainable'),
        ('revenue_productivity_pct', 'revenue_productivity', False, 'Efficient TVL usage'),
        ('turnover_pct', 'turnover', False, 'High velocity/liquidity'),
    ]
    
    for factor_col, factor_name, ascending, desc in factor_configs:
        print(f"\n{factor_name.replace('_', ' ').title()}: {desc}")
        
        df_signals = generate_factor_signals(
            df,
            factor_col,
            long_threshold=80,
            short_threshold=20,
            min_fdv=10_000_000,
            ascending=ascending
        )
        
        if not df_signals.empty:
            long_count = (df_signals['signal'] == 'long').sum()
            short_count = (df_signals['signal'] == 'short').sum()
            print(f"  Long: {long_count} tokens, Short: {short_count} tokens")
            
            # Save signals
            filepath = signals_dir / f"defi_factor_{factor_name}_signals.csv"
            df_signals.to_csv(filepath, index=False)
            print(f"  ✓ Saved: {filepath.name}")
            
            # Show top longs
            if long_count > 0:
                print(f"\n  Top 5 Long Signals:")
                longs = df_signals[df_signals['signal'] == 'long'].nlargest(5, factor_col)
                for _, row in longs.iterrows():
                    print(f"    {row['symbol']:8s}: {row[factor_col]:8.2f}")
    
    # Create combined factor signal
    print("\n" + "=" * 80)
    print("Combined Multi-Factor Signal")
    print("=" * 80)
    
    # Calculate composite score (equal weight)
    df['composite_score'] = (
        df['fee_yield_pct'].fillna(0) * 0.25 +
        -df['emission_yield_pct'].fillna(0) * 0.15 +  # Negative because low is better
        df['net_yield_pct'].fillna(0) * 0.30 +
        df['revenue_productivity_pct'].fillna(0) * 0.20 +
        df['turnover_pct'].fillna(0) * 0.10
    )
    
    combined_signals = generate_factor_signals(
        df,
        'composite_score',
        long_threshold=80,
        short_threshold=20,
        min_fdv=10_000_000,
        ascending=False
    )
    
    if not combined_signals.empty:
        long_count = (combined_signals['signal'] == 'long').sum()
        short_count = (combined_signals['signal'] == 'short').sum()
        
        print(f"\nCombined signals:")
        print(f"  Long: {long_count} tokens")
        print(f"  Short: {short_count} tokens")
        
        # Save
        filepath = signals_dir / f"defi_factor_combined_signals.csv"
        combined_signals.to_csv(filepath, index=False)
        print(f"\n✓ Saved: {filepath.name}")
        
        # Show top longs
        print(f"\nTop 10 Long Signals:")
        longs = combined_signals[combined_signals['signal'] == 'long'].nlargest(10, 'composite_score')
        print(f"\n{'Symbol':<8} {'Composite':<10} {'Fee Yield':<10} {'Net Yield':<10} {'Rev Prod':<10} {'FDV ($M)':<12}")
        print("-" * 70)
        for _, row in longs.iterrows():
            print(f"{row['symbol']:<8} "
                  f"{row['composite_score']:>9.2f} "
                  f"{row['fee_yield_pct']:>9.2f} "
                  f"{row['net_yield_pct']:>9.2f} "
                  f"{row['revenue_productivity_pct']:>9.2f} "
                  f"${row['valuation']/1e6:>10.1f}")
    
    print("\n" + "=" * 80)
    print("✅ Factor calculation complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
