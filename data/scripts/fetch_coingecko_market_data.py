#!/usr/bin/env python3
"""
Fetch Market Cap and FDV data from CoinGecko API

CoinGecko Free API:
- 50 calls/minute
- No authentication required
- Comprehensive crypto data
"""

import requests
import pandas as pd
import time
from datetime import datetime
from typing import Dict, List, Optional
import re

class CoinGeckoClient:
    """Client for CoinGecko API"""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self, rate_limit_delay: float = 1.5):
        """
        Initialize client
        
        Args:
            rate_limit_delay: Delay between requests (1.5s = ~40 calls/min)
        """
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        
    def _get(self, endpoint: str, params: Dict = None, timeout: int = 10) -> Optional[Dict]:
        """Make GET request with error handling and rate limiting"""
        try:
            time.sleep(self.rate_limit_delay)
            url = f"{self.BASE_URL}/{endpoint}"
            response = self.session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {endpoint}: {e}")
            return None
    
    def search_coin(self, symbol: str) -> Optional[str]:
        """
        Search for coin ID by symbol
        
        Args:
            symbol: Token symbol (e.g., 'BTC', 'ETH')
            
        Returns:
            CoinGecko coin ID or None
        """
        data = self._get("search", params={"query": symbol})
        if not data or 'coins' not in data:
            return None
        
        # Find exact symbol match (case-insensitive)
        symbol_upper = symbol.upper()
        for coin in data['coins']:
            if coin.get('symbol', '').upper() == symbol_upper:
                return coin['id']
        
        # If no exact match, return first result
        if data['coins']:
            return data['coins'][0]['id']
        
        return None
    
    def get_coin_data(self, coin_id: str) -> Optional[Dict]:
        """
        Get detailed coin data including market cap and FDV
        
        Args:
            coin_id: CoinGecko coin ID
            
        Returns:
            Dict with coin data
        """
        return self._get(
            f"coins/{coin_id}",
            params={
                'localization': 'false',
                'tickers': 'false',
                'market_data': 'true',
                'community_data': 'false',
                'developer_data': 'false',
                'sparkline': 'false'
            }
        )
    
    def get_markets_data(self, coin_ids: List[str]) -> Optional[List[Dict]]:
        """
        Get market data for multiple coins at once (more efficient)
        
        Args:
            coin_ids: List of CoinGecko coin IDs (max 250 per call)
            
        Returns:
            List of coin market data
        """
        ids_str = ','.join(coin_ids[:250])  # API limit
        return self._get(
            "coins/markets",
            params={
                'vs_currency': 'usd',
                'ids': ids_str,
                'order': 'market_cap_desc',
                'sparkline': 'false',
                'price_change_percentage': '24h'
            }
        )


# Manual symbol to CoinGecko ID mapping for common tokens
SYMBOL_TO_COINGECKO_ID = {
    '1INCH': '1inch',
    'AAVE': 'aave',
    'ADA': 'cardano',
    'AERO': 'aerodrome-finance',
    'AIOZ': 'aioz-network',
    'AKT': 'akash-network',
    'ALGO': 'algorand',
    'ALICE': 'my-neighbor-alice',
    'AMP': 'amp-token',
    'ANKR': 'ankr',
    'APE': 'apecoin',
    'API3': 'api3',
    'APT': 'aptos',
    'ARB': 'arbitrum',
    'ARKM': 'arkham',
    'ATH': 'aethir',
    'ATOM': 'cosmos',
    'AUDIO': 'audius',
    'AVAX': 'avalanche-2',
    'AXL': 'axelar',
    'AXS': 'axie-infinity',
    'BAL': 'balancer',
    'BAND': 'band-protocol',
    'BAT': 'basic-attention-token',
    'BCH': 'bitcoin-cash',
    'BICO': 'biconomy',
    'BIO': 'bio-protocol',
    'BLUR': 'blur',
    'BNB': 'binancecoin',
    'BNT': 'bancor',
    'BONK': 'bonk',
    'BTC': 'bitcoin',
    'BTRST': 'braintrust',
    'CAKE': 'pancakeswap-token',
    'CELO': 'celo',
    'CELR': 'celer-network',
    'CFG': 'centrifuge',
    'CHZ': 'chiliz',
    'COMP': 'compound-governance-token',
    'COTI': 'coti',
    'CRO': 'crypto-com-chain',
    'CRV': 'curve-dao-token',
    'CTSI': 'cartesi',
    'CVC': 'civic',
    'CVX': 'convex-finance',
    'DAI': 'dai',
    'DASH': 'dash',
    'DIA': 'dia-data',
    'DOGE': 'dogecoin',
    'DOT': 'polkadot',
    'DRIFT': 'drift-protocol',
    'EGLD': 'elrond-erd-2',
    'EIGEN': 'eigenlayer',
    'ENA': 'ethena',
    'ENS': 'ethereum-name-service',
    'EOS': 'eos',
    'ETC': 'ethereum-classic',
    'ETH': 'ethereum',
    'ETHFI': 'ether-fi',
    'FARTCOIN': 'fartcoin',
    'FET': 'fetch-ai',
    'FIL': 'filecoin',
    'FLOKI': 'floki',
    'FLOW': 'flow',
    'FLR': 'flare-networks',
    'GIGA': 'gigachad',
    'GLM': 'golem',
    'GMT': 'stepn',
    'GNO': 'gnosis',
    'GRT': 'the-graph',
    'HBAR': 'hedera-hashgraph',
    'HNT': 'helium',
    'ICP': 'internet-computer',
    'ILV': 'illuvium',
    'IMX': 'immutable-x',
    'INJ': 'injective-protocol',
    'IO': 'io',
    'IOTX': 'iotex',
    'JASMY': 'jasmycoin',
    'JTO': 'jito-governance-token',
    'KAVA': 'kava',
    'KNC': 'kyber-network-crystal',
    'KSM': 'kusama',
    'LDO': 'lido-dao',
    'LINK': 'chainlink',
    'LPT': 'livepeer',
    'LRC': 'loopring',
    'LTC': 'litecoin',
    'MAGIC': 'magic',
    'MANA': 'decentraland',
    'MASK': 'mask-network',
    'ME': 'magic-eden',
    'METIS': 'metis-token',
    'MINA': 'mina-protocol',
    'MKR': 'maker',
    'MLN': 'melon',
    'MOG': 'mog-coin',
    'MORPHO': 'morpho',
    'NEAR': 'near',
    'NKN': 'nkn',
    'NMR': 'numeraire',
    'OCEAN': 'ocean-protocol',
    'OGN': 'origin-protocol',
    'ONDO': 'ondo-finance',
    'OP': 'optimism',
    'OSMO': 'osmosis',
    'OXT': 'orchid-protocol',
    'PAX': 'paxos-standard',
    'PAXG': 'pax-gold',
    'PENDLE': 'pendle',
    'PENGU': 'pengu',
    'PEPE': 'pepe',
    'PERP': 'perpetual-protocol',
    'PNUT': 'peanut-the-squirrel',
    'POL': 'polygon-ecosystem-token',
    'POLS': 'polkastarter',
    'POPCAT': 'popcat',
    'POWR': 'power-ledger',
    'PRIME': 'echelon-prime',
    'PUNDIX': 'pundi-x-2',
    'PYR': 'vulcan-forged',
    'PYTH': 'pyth-network',
    'QNT': 'quant-network',
    'RAD': 'radicle',
    'RENDER': 'render-token',
    'REQ': 'request-network',
    'RLC': 'iexec-rlc',
    'ROSE': 'oasis-network',
    'RPL': 'rocket-pool',
    'RSR': 'reserve-rights-token',
    'SAFE': 'safe',
    'SAND': 'the-sandbox',
    'SEI': 'sei-network',
    'SHIB': 'shiba-inu',
    'SKL': 'skale',
    'SNX': 'havven',
    'SOL': 'solana',
    'SPX': 'spx6900',
    'STORJ': 'storj',
    'STRK': 'starknet',
    'STX': 'blockstack',
    'SUI': 'sui',
    'SUPER': 'superverse',
    'SUSHI': 'sushi',
    'T': 'threshold-network-token',
    'TAO': 'bittensor',
    'TIA': 'celestia',
    'TRAC': 'origintrail',
    'TRB': 'tellor',
    'TURBO': 'turbo',
    'UMA': 'uma',
    'UNI': 'uniswap',
    'USDC': 'usd-coin',
    'USDT': 'tether',
    'VET': 'vechain',
    'VTHO': 'vethor-token',
    'W': 'wormhole',
    'WIF': 'dogwifcoin',
    'WLD': 'worldcoin-wld',
    'XCN': 'chain-2',
    'XLM': 'stellar',
    'XRP': 'ripple',
    'XTZ': 'tezos',
    'XYO': 'xyo-network',
    'YFI': 'yearn-finance',
    'ZEC': 'zcash',
    'ZEN': 'zencash',
    'ZETA': 'zetachain',
    'ZK': 'zksync',
    'ZRO': 'layerzero',
    'ZRX': '0x',
}


def load_tradeable_universe() -> List[str]:
    """Load tradeable universe symbols"""
    with open('/workspace/tradeable_universe.txt', 'r') as f:
        content = f.read()
    symbols = re.findall(r'^\s*\d+\.\s+([A-Z0-9]+)', content, re.MULTILINE)
    return symbols


def fetch_market_caps(symbols: List[str]) -> pd.DataFrame:
    """
    Fetch market cap and FDV for list of symbols
    
    Args:
        symbols: List of token symbols
        
    Returns:
        DataFrame with market data
    """
    client = CoinGeckoClient(rate_limit_delay=2.0)  # Increased delay
    
    # Map symbols to CoinGecko IDs (only use manual mappings)
    print("Mapping symbols to CoinGecko IDs...")
    symbol_to_id = {}
    missing = []
    for symbol in symbols:
        if symbol in SYMBOL_TO_COINGECKO_ID:
            symbol_to_id[symbol] = SYMBOL_TO_COINGECKO_ID[symbol]
        else:
            missing.append(symbol)
    
    print(f"Mapped {len(symbol_to_id)}/{len(symbols)} symbols")
    if missing:
        print(f"Missing mappings for: {', '.join(missing[:10])}{' ...' if len(missing) > 10 else ''}")
    
    # Fetch market data in batches
    print("\nFetching market data...")
    results = []
    coin_ids = list(symbol_to_id.values())
    
    # Batch requests (50 coins per request to be safe)
    batch_size = 50
    for i in range(0, len(coin_ids), batch_size):
        batch_ids = coin_ids[i:i+batch_size]
        batch_num = i//batch_size + 1
        total_batches = (len(coin_ids) + batch_size - 1) // batch_size
        print(f"  Fetching batch {batch_num}/{total_batches} ({len(batch_ids)} coins)...")
        
        market_data = client.get_markets_data(batch_ids)
        if market_data:
            results.extend(market_data)
            print(f"    ? Received {len(market_data)} coins")
        else:
            print(f"    ? Failed to fetch batch")
        
        # Extra delay between batches
        if batch_num < total_batches:
            print(f"    Waiting 3s before next batch...")
            time.sleep(3)
    
    # Convert to DataFrame
    if not results:
        return pd.DataFrame()
    
    df = pd.DataFrame(results)
    
    # Reverse mapping (ID to symbol)
    id_to_symbol = {v: k for k, v in symbol_to_id.items()}
    df['symbol'] = df['id'].map(id_to_symbol)
    
    # Select relevant columns
    columns = [
        'symbol', 'id', 'name',
        'current_price',
        'market_cap',
        'fully_diluted_valuation',
        'total_volume',
        'circulating_supply',
        'total_supply',
        'max_supply',
        'price_change_percentage_24h'
    ]
    
    df = df[[c for c in columns if c in df.columns]]
    df['timestamp'] = datetime.now().isoformat()
    
    return df


def main():
    """Fetch market cap data for tradeable universe"""
    print("=" * 60)
    print("CoinGecko Market Data Fetcher")
    print("=" * 60)
    print()
    
    # Load tradeable universe
    symbols = load_tradeable_universe()
    print(f"Loaded {len(symbols)} tradeable symbols\n")
    
    # Fetch market data
    df = fetch_market_caps(symbols)
    
    if df.empty:
        print("No data fetched. Check API connectivity.")
        return
    
    print(f"\n? Fetched data for {len(df)} tokens")
    
    # Save
    date = datetime.now().strftime("%Y%m%d")
    filepath = f"/workspace/data/raw/coingecko_market_data_{date}.csv"
    df.to_csv(filepath, index=False)
    print(f"\n? Saved: {filepath}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Market Data Summary")
    print("=" * 60)
    
    df_sorted = df.sort_values('market_cap', ascending=False)
    print(f"\nTop 10 by Market Cap:")
    for _, row in df_sorted.head(10).iterrows():
        mc = row.get('market_cap', 0) or 0
        fdv = row.get('fully_diluted_valuation', 0) or 0
        vol = row.get('total_volume', 0) or 0
        print(f"  {row['symbol']:6s}: MC=${mc:,.0f}, FDV=${fdv:,.0f}, Vol=${vol:,.0f}")
    
    # Statistics
    print(f"\nStatistics:")
    print(f"  Tokens with Market Cap: {df['market_cap'].notna().sum()}")
    print(f"  Tokens with FDV: {df['fully_diluted_valuation'].notna().sum()}")
    print(f"  Tokens with Volume: {df['total_volume'].notna().sum()}")
    print(f"  Total Market Cap: ${df['market_cap'].sum():,.0f}")


if __name__ == "__main__":
    main()
