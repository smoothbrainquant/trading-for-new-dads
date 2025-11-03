#!/usr/bin/env python3
"""
Map DefiLlama data to tradeable universe.

Creates a mapping between DeFi protocol tokens and tradeable crypto symbols,
then aggregates metrics for factor analysis.
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
import re

# Manual mapping of protocol symbols to tradeable symbols
PROTOCOL_TO_SYMBOL_MAP = {
    'AAVE': 'AAVE',
    'CRV': 'CRV',
    'YFI': 'YFI',
    'COMP': 'COMP',
    'SNX': 'SNX',
    'BAL': 'BAL',
    'SKY': 'MKR',  # Sky was MakerDAO
    'SUSHI': 'SUSHI',
    'KNC': 'KNC',
    'DYDX': 'DRIFT',  # Similar derivatives platforms
    'DODO': 'DODO',  # Not in universe
    'TORN': 'TORN',  # Privacy
    'BNT': 'BNT',
    'LDO': 'LDO',
    'DHT': 'DHT',  # Not in universe
    'CAKE': 'CAKE',
    'SDL': 'SDL',  # Not in universe
    'ALCX': 'ALCX',  # Not in universe
    'XVS': 'XVS',  # Not in universe
    'RAY': 'RAY',  # Not in universe but related to SOL
    'VSP': 'VSP',  # Not in universe
    'CRO': 'CRO',
    'PNG': 'PNG',  # Not in universe
    'SDT': 'SDT',  # Not in universe
    'LQTY': 'LQTY',  # Not in universe
    'HNY': 'HNY',  # Not in universe
    'SWISE': 'SWISE',  # Not in universe
    'RBN': 'RBN',  # Not in universe
    'ORCA': 'ORCA',  # SOL ecosystem
    'QUICK': 'QUICK',  # Not in universe
    'CVX': 'CVX',
    'BIFI': 'BIFI',  # Not in universe
    'GMX': 'GMX',  # Not in universe
    'SPELL': 'SPELL',  # Not in universe
    'GAMMA': 'GAMMA',  # Not in universe
    'FRAX': 'FRAX',  # Not in universe
    'UNI': 'UNI',
    'LINK': 'LINK',
    '1INCH': '1INCH',
    'RUNE': 'RUNE',  # Not in universe but THORChain
    'ALPHA': 'ALPHA',  # Not in universe
    'INJ': 'INJ',
    'PENDLE': 'PENDLE',
    'JUP': 'JUP',  # Jupiter (SOL)
    'PYTH': 'PYTH',
    'EIGEN': 'EIGEN',
    'AERO': 'AERO',
    'ENA': 'ENA',
    'ETHFI': 'ETHFI',
    'ONDO': 'ONDO',
    'SAFE': 'SAFE',
    'MORPHO': 'MORPHO',
    'GNO': 'GNO',
    'RPL': 'RPL',
    'ENS': 'ENS',
}

# Load tradeable universe
def load_tradeable_universe() -> set:
    """Load the tradeable universe symbols"""
    with open('/workspace/tradeable_universe.txt', 'r') as f:
        content = f.read()
    
    # Extract symbols using regex
    symbols = re.findall(r'^\s*\d+\.\s+([A-Z0-9]+)', content, re.MULTILINE)
    return set(symbols)


def map_utility_yields(tradeable_symbols: set, date: str = None) -> pd.DataFrame:
    """
    Map utility yield data to tradeable symbols
    
    Returns:
        DataFrame with utility yield metrics per tradeable symbol
    """
    if date is None:
        date = datetime.now().strftime("%Y%m%d")
    
    filepath = f"/workspace/data/raw/defillama_utility_yields_{date}.csv"
    if not Path(filepath).exists():
        print(f"File not found: {filepath}")
        return pd.DataFrame()
    
    df = pd.read_csv(filepath)
    
    # Map protocol symbols to tradeable symbols
    df['tradeable_symbol'] = df['symbol'].map(PROTOCOL_TO_SYMBOL_MAP)
    
    # Filter to only tradeable symbols
    df_tradeable = df[df['tradeable_symbol'].isin(tradeable_symbols)].copy()
    
    # For protocols with multiple entries, aggregate
    agg_df = df_tradeable.groupby('tradeable_symbol').agg({
        'tvl': 'sum',
        'daily_fees': 'sum',
        'daily_revenue': 'sum',
        'utility_yield_pct': 'mean',  # Average yield across protocols
    }).reset_index()
    
    # Recalculate utility yield with aggregated data
    agg_df['utility_yield_pct'] = (agg_df['daily_fees'] * 365 / agg_df['tvl'] * 100).fillna(0)
    
    return agg_df


def map_yields(tradeable_symbols: set, date: str = None) -> pd.DataFrame:
    """
    Map yield data to tradeable symbols
    
    Aggregates APYs across all pools for each symbol
    """
    if date is None:
        date = datetime.now().strftime("%Y%m%d")
    
    filepath = f"/workspace/data/raw/defillama_yields_{date}.csv"
    if not Path(filepath).exists():
        print(f"File not found: {filepath}")
        return pd.DataFrame()
    
    df = pd.read_csv(filepath)
    
    # Map pool symbols to tradeable symbols (many symbols are directly tradeable)
    # Clean up symbols (remove special prefixes/suffixes)
    df['clean_symbol'] = df['symbol'].str.replace(r'^(W|ST|R|OS|E|CB|M|JITO|BN|JUP|SLIS)', '', regex=True)
    df['clean_symbol'] = df['clean_symbol'].str.replace(r'(USDC|USDT|DAI|ETH|BTC).*', r'\1', regex=True)
    
    # Direct mapping
    symbol_map = {
        'SOL': 'SOL',
        'ETH': 'ETH',
        'BTC': 'BTC',
        'USDT': 'USDT',
        'USDC': 'USDC',
        'DAI': 'DAI',
        'AVAX': 'AVAX',
        'MATIC': 'POL',
        'BNB': 'BNB',
        'ADA': 'ADA',
        'DOT': 'DOT',
        'LINK': 'LINK',
        'UNI': 'UNI',
        'AAVE': 'AAVE',
        'CRV': 'CRV',
        'LDO': 'LDO',
        'RPL': 'RPL',
        'OSMO': 'OSMO',
        'ATOM': 'ATOM',
        'NEAR': 'NEAR',
        'FTM': 'FTM',  # Not in universe
        'ALGO': 'ALGO',
        'XTZ': 'XTZ',
        'TRX': 'TRX',  # Not in universe
        'PENDLE': 'PENDLE',
        'PYTH': 'PYTH',
        'OP': 'OP',
        'ARB': 'ARB',
        'SUI': 'SUI',
    }
    
    df['tradeable_symbol'] = df['clean_symbol'].map(symbol_map)
    
    # Filter to tradeable
    df_tradeable = df[df['tradeable_symbol'].isin(tradeable_symbols)].copy()
    
    # Aggregate by tradeable symbol - use TVL-weighted average for APY
    results = []
    for symbol in df_tradeable['tradeable_symbol'].unique():
        symbol_data = df_tradeable[df_tradeable['tradeable_symbol'] == symbol]
        
        total_tvl = symbol_data['tvl'].sum()
        
        # Calculate weighted averages
        if total_tvl > 0:
            weighted_apy = (symbol_data['apy'] * symbol_data['tvl']).sum() / total_tvl
            weighted_apy_base = (symbol_data['apy_base'] * symbol_data['tvl']).sum() / total_tvl
            weighted_apy_reward = (symbol_data['apy_reward'] * symbol_data['tvl']).sum() / total_tvl
        else:
            weighted_apy = symbol_data['apy'].mean()
            weighted_apy_base = symbol_data['apy_base'].mean()
            weighted_apy_reward = symbol_data['apy_reward'].mean()
        
        results.append({
            'symbol': symbol,
            'total_tvl': total_tvl,
            'weighted_apy': weighted_apy,
            'weighted_apy_base': weighted_apy_base,
            'weighted_apy_reward': weighted_apy_reward,
        })
    
    agg_df = pd.DataFrame(results)
    
    return agg_df


def create_combined_factor_data(tradeable_symbols: set, date: str = None) -> pd.DataFrame:
    """
    Create combined factor data for all tradeable symbols
    
    Combines:
    - Utility yield (fees / TVL)
    - On-chain yield (staking/lending APY)
    """
    if date is None:
        date = datetime.now().strftime("%Y%m%d")
    
    print("Mapping utility yields...")
    utility_df = map_utility_yields(tradeable_symbols, date)
    print(f"  Mapped {len(utility_df)} tokens with utility yield data")
    
    print("Mapping on-chain yields...")
    yield_df = map_yields(tradeable_symbols, date)
    print(f"  Mapped {len(yield_df)} tokens with yield data")
    
    # Merge the data
    combined = pd.merge(
        utility_df,
        yield_df,
        left_on='tradeable_symbol',
        right_on='symbol',
        how='outer',
        suffixes=('_protocol', '_pool')
    )
    
    # Clean up column names
    combined['symbol'] = combined['tradeable_symbol'].fillna(combined['symbol'])
    combined = combined.drop(['tradeable_symbol'], axis=1, errors='ignore')
    
    # Fill missing values
    combined = combined.fillna(0)
    
    # Calculate composite metrics
    combined['total_yield_pct'] = combined['utility_yield_pct'] + combined['weighted_apy']
    combined['date'] = date
    
    return combined


def main():
    """Generate factor data mapped to tradeable universe"""
    print("=" * 60)
    print("DefiLlama Data Mapper")
    print("=" * 60)
    print()
    
    # Load tradeable universe
    tradeable_symbols = load_tradeable_universe()
    print(f"Loaded {len(tradeable_symbols)} tradeable symbols\n")
    
    # Create combined factor data
    date = datetime.now().strftime("%Y%m%d")
    combined_df = create_combined_factor_data(tradeable_symbols, date)
    
    # Save
    output_file = f"/workspace/data/raw/defillama_factors_{date}.csv"
    combined_df.to_csv(output_file, index=False)
    print(f"\n✓ Saved factor data: {output_file}")
    
    # Summary statistics
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"\nTotal tradeable tokens with data: {len(combined_df)}")
    print(f"\nTokens with utility yield > 0: {(combined_df['utility_yield_pct'] > 0).sum()}")
    print(f"Tokens with on-chain yield > 0: {(combined_df['weighted_apy'] > 0).sum()}")
    print(f"Tokens with both: {((combined_df['utility_yield_pct'] > 0) & (combined_df['weighted_apy'] > 0)).sum()}")
    
    # Top tokens by total yield
    print("\n" + "=" * 60)
    print("Top 10 Tokens by Total Yield")
    print("=" * 60)
    top_10 = combined_df.nlargest(10, 'total_yield_pct')[
        ['symbol', 'utility_yield_pct', 'weighted_apy', 'total_yield_pct', 'tvl']
    ]
    for _, row in top_10.iterrows():
        print(f"{row['symbol']:6s}: {row['total_yield_pct']:6.2f}% "
              f"(Utility: {row['utility_yield_pct']:5.2f}% + Yield: {row['weighted_apy']:5.2f}%) "
              f"TVL: ${row['tvl']:,.0f}")
    
    # Export for signal generation
    print("\n✓ Data ready for factor signal generation")
    print(f"  File: {output_file}")


if __name__ == "__main__":
    main()
