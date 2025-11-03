#!/usr/bin/env python3
"""
Fetch comprehensive DeFi metrics from DefiLlama API.

Fetches:
- TVL (Total Value Locked) by protocol
- Daily fees and revenue (for utility yield calculation)
- On-chain yields (staking, lending APYs)
- DEX liquidity and volume

Data can be used for:
- Utility yield = Daily fees / Market cap (or TVL)
- Net yield gap analysis
- On-chain yield vs risk-free rate comparison
- Liquidity / Market cap ratios
"""

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import time
import json

class DefiLlamaClient:
    """Client for fetching data from DefiLlama API"""
    
    BASE_URL = "https://api.llama.fi"
    COINS_URL = "https://coins.llama.fi"
    YIELDS_URL = "https://yields.llama.fi"
    STABLECOINS_URL = "https://stablecoins.llama.fi"
    
    def __init__(self, rate_limit_delay: float = 0.5):
        """
        Initialize client
        
        Args:
            rate_limit_delay: Delay between requests in seconds
        """
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        
    def _get(self, url: str, timeout: int = 10) -> Optional[Dict]:
        """Make GET request with error handling and rate limiting"""
        try:
            time.sleep(self.rate_limit_delay)
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def get_protocols(self) -> Optional[List[Dict]]:
        """Get all protocols with TVL data"""
        return self._get(f"{self.BASE_URL}/protocols")
    
    def get_protocol_details(self, protocol_slug: str) -> Optional[Dict]:
        """Get detailed data for a specific protocol"""
        return self._get(f"{self.BASE_URL}/protocol/{protocol_slug}")
    
    def get_fees_revenue(self) -> Optional[Dict]:
        """Get fees and revenue data across protocols"""
        return self._get(f"{self.BASE_URL}/overview/fees")
    
    def get_yields(self) -> Optional[Dict]:
        """Get yield data for various pools"""
        return self._get(f"{self.YIELDS_URL}/pools")
    
    def get_dexs(self) -> Optional[Dict]:
        """Get DEX volume and liquidity data"""
        return self._get(f"{self.BASE_URL}/overview/dexs")
    
    def get_coin_prices(self, coin_ids: List[str]) -> Optional[Dict]:
        """
        Get current prices for specified coins
        
        Args:
            coin_ids: List of coin IDs in format "coingecko:bitcoin"
        """
        coins_str = ",".join(coin_ids)
        return self._get(f"{self.COINS_URL}/prices/current/{coins_str}")
    
    def get_historical_tvl(self, protocol_slug: str) -> Optional[Dict]:
        """Get historical TVL for a protocol"""
        return self._get(f"{self.BASE_URL}/protocol/{protocol_slug}")


def fetch_utility_yield_data(client: DefiLlamaClient) -> pd.DataFrame:
    """
    Fetch data for calculating utility yield (fees / TVL or market cap)
    
    Returns:
        DataFrame with columns: protocol, tvl, daily_fees, daily_revenue, utility_yield
    """
    print("Fetching utility yield data...")
    
    # Get protocols with TVL
    protocols = client.get_protocols()
    if not protocols:
        return pd.DataFrame()
    
    tvl_data = {p['slug']: {
        'name': p['name'],
        'symbol': p.get('symbol', ''),
        'tvl': p.get('tvl', 0),
        'category': p.get('category', ''),
        'chain': p.get('chain', 'Multi-Chain'),
    } for p in protocols}
    
    # Get fees and revenue
    fees_data = client.get_fees_revenue()
    if not fees_data or 'protocols' not in fees_data:
        return pd.DataFrame()
    
    results = []
    for protocol in fees_data['protocols']:
        name = protocol.get('name', '')
        slug = protocol.get('defillamaId', name.lower().replace(' ', '-'))
        
        # Try multiple matching strategies
        matching_slug = None
        if slug in tvl_data:
            matching_slug = slug
        else:
            # Try direct name match
            name_lower = name.lower()
            for tvl_slug, tvl_info in tvl_data.items():
                if tvl_info['name'].lower() == name_lower:
                    matching_slug = tvl_slug
                    break
        
        if matching_slug:
            daily_fees = protocol.get('total24h', 0) or 0
            daily_revenue = protocol.get('revenue24h', 0) or 0
            tvl = tvl_data[matching_slug]['tvl'] or 0
            
            # Calculate utility yield (annualized)
            utility_yield = (daily_fees * 365 / tvl * 100) if tvl > 0 else 0
            
            results.append({
                'protocol': tvl_data[matching_slug]['name'],
                'symbol': tvl_data[matching_slug]['symbol'],
                'category': tvl_data[matching_slug]['category'],
                'chain': tvl_data[matching_slug]['chain'],
                'tvl': tvl,
                'daily_fees': daily_fees,
                'daily_revenue': daily_revenue,
                'utility_yield_pct': utility_yield,
                'timestamp': datetime.now().isoformat(),
            })
    
    df = pd.DataFrame(results)
    print(f"✓ Fetched utility yield data for {len(df)} protocols")
    return df


def fetch_yield_data(client: DefiLlamaClient) -> pd.DataFrame:
    """
    Fetch on-chain yield data (staking, lending, LP yields)
    
    Returns:
        DataFrame with columns: pool_id, symbol, apy, tvl, chain, project
    """
    print("Fetching yield data...")
    
    yields_data = client.get_yields()
    if not yields_data or 'data' not in yields_data:
        return pd.DataFrame()
    
    results = []
    for pool in yields_data['data']:
        results.append({
            'pool_id': pool.get('pool', ''),
            'symbol': pool.get('symbol', ''),
            'project': pool.get('project', ''),
            'chain': pool.get('chain', ''),
            'apy': pool.get('apy', 0),
            'apy_base': pool.get('apyBase', 0),
            'apy_reward': pool.get('apyReward', 0),
            'tvl': pool.get('tvlUsd', 0),
            'il_risk': pool.get('ilRisk', 'unknown'),
            'exposure': pool.get('exposure', 'single'),
            'timestamp': datetime.now().isoformat(),
        })
    
    df = pd.DataFrame(results)
    print(f"✓ Fetched yield data for {len(df)} pools")
    return df


def fetch_dex_liquidity_data(client: DefiLlamaClient) -> pd.DataFrame:
    """
    Fetch DEX liquidity and volume data
    
    Returns:
        DataFrame with columns: dex, volume_24h, fees_24h, chain
    """
    print("Fetching DEX liquidity data...")
    
    dexs_data = client.get_dexs()
    if not dexs_data or 'protocols' not in dexs_data:
        return pd.DataFrame()
    
    results = []
    for dex in dexs_data['protocols']:
        results.append({
            'dex': dex.get('name', ''),
            'defi_llama_id': dex.get('defillamaId', ''),
            'volume_24h': dex.get('total24h', 0),
            'volume_7d': dex.get('total7d', 0),
            'change_1d': dex.get('change_1d', 0),
            'chains': ','.join(dex.get('chains', [])),
            'timestamp': datetime.now().isoformat(),
        })
    
    df = pd.DataFrame(results)
    print(f"✓ Fetched DEX data for {len(df)} exchanges")
    return df


def fetch_protocol_tvls(client: DefiLlamaClient, top_n: int = 100) -> pd.DataFrame:
    """
    Fetch TVL data for top protocols
    
    Args:
        top_n: Number of top protocols by TVL to include
        
    Returns:
        DataFrame with protocol TVL data
    """
    print(f"Fetching TVL data for top {top_n} protocols...")
    
    protocols = client.get_protocols()
    if not protocols:
        return pd.DataFrame()
    
    # Sort by TVL and take top N
    sorted_protocols = sorted(
        [p for p in protocols if p.get('tvl') is not None and p.get('tvl', 0) > 0],
        key=lambda x: x.get('tvl', 0),
        reverse=True
    )[:top_n]
    
    results = []
    for protocol in sorted_protocols:
        results.append({
            'protocol': protocol.get('name', ''),
            'slug': protocol.get('slug', ''),
            'symbol': protocol.get('symbol', ''),
            'category': protocol.get('category', ''),
            'chains': ','.join(protocol.get('chains', [])),
            'tvl': protocol.get('tvl', 0),
            'change_1h': protocol.get('change_1h', 0),
            'change_1d': protocol.get('change_1d', 0),
            'change_7d': protocol.get('change_7d', 0),
            'mcap': protocol.get('mcap', 0),
            'timestamp': datetime.now().isoformat(),
        })
    
    df = pd.DataFrame(results)
    print(f"✓ Fetched TVL data for {len(df)} protocols")
    return df


def main():
    """Fetch all DeFi data from DefiLlama"""
    print("=" * 60)
    print("DefiLlama Data Fetcher")
    print("=" * 60)
    print()
    
    client = DefiLlamaClient(rate_limit_delay=0.3)
    
    # Fetch all datasets
    utility_yield_df = fetch_utility_yield_data(client)
    yield_df = fetch_yield_data(client)
    dex_df = fetch_dex_liquidity_data(client)
    tvl_df = fetch_protocol_tvls(client, top_n=200)
    
    # Save to CSV files
    timestamp = datetime.now().strftime("%Y%m%d")
    
    if not utility_yield_df.empty:
        filepath = f"/workspace/data/raw/defillama_utility_yields_{timestamp}.csv"
        utility_yield_df.to_csv(filepath, index=False)
        print(f"\n✓ Saved utility yield data: {filepath}")
        print(f"  Top 5 by utility yield:")
        top_5 = utility_yield_df.nlargest(5, 'utility_yield_pct')[['protocol', 'utility_yield_pct', 'tvl']]
        for _, row in top_5.iterrows():
            print(f"    {row['protocol']}: {row['utility_yield_pct']:.2f}% (TVL: ${row['tvl']:,.0f})")
    
    if not yield_df.empty:
        filepath = f"/workspace/data/raw/defillama_yields_{timestamp}.csv"
        yield_df.to_csv(filepath, index=False)
        print(f"\n✓ Saved yield data: {filepath}")
        print(f"  Top 5 by APY (>$1M TVL):")
        high_tvl = yield_df[yield_df['tvl'] > 1_000_000]
        top_5 = high_tvl.nlargest(5, 'apy')[['symbol', 'project', 'apy', 'tvl']]
        for _, row in top_5.iterrows():
            print(f"    {row['symbol']} ({row['project']}): {row['apy']:.2f}% APY (TVL: ${row['tvl']:,.0f})")
    
    if not dex_df.empty:
        filepath = f"/workspace/data/raw/defillama_dex_data_{timestamp}.csv"
        dex_df.to_csv(filepath, index=False)
        print(f"\n✓ Saved DEX data: {filepath}")
        print(f"  Top 5 by volume:")
        top_5 = dex_df.nlargest(5, 'volume_24h')[['dex', 'volume_24h']]
        for _, row in top_5.iterrows():
            print(f"    {row['dex']}: ${row['volume_24h']:,.0f}")
    
    if not tvl_df.empty:
        filepath = f"/workspace/data/raw/defillama_tvl_{timestamp}.csv"
        tvl_df.to_csv(filepath, index=False)
        print(f"\n✓ Saved TVL data: {filepath}")
        print(f"  Top 5 by TVL:")
        top_5 = tvl_df.nlargest(5, 'tvl')[['protocol', 'tvl', 'category']]
        for _, row in top_5.iterrows():
            print(f"    {row['protocol']}: ${row['tvl']:,.0f} ({row['category']})")
    
    print("\n" + "=" * 60)
    print("✅ Data fetch complete!")
    print("=" * 60)
    
    # Summary
    print(f"\nSummary:")
    print(f"  - {len(utility_yield_df)} protocols with fee data")
    print(f"  - {len(yield_df)} yield pools")
    print(f"  - {len(dex_df)} DEXs")
    print(f"  - {len(tvl_df)} protocols with TVL data")
    print(f"\nNext steps:")
    print(f"  1. Map protocol symbols to your trading universe")
    print(f"  2. Calculate utility yield = daily_fees * 365 / market_cap")
    print(f"  3. Compare on-chain yields vs risk-free rate")
    print(f"  4. Analyze liquidity / market cap ratios")


if __name__ == "__main__":
    main()
