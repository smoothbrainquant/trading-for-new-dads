#!/usr/bin/env python3
"""
Coinalyze Data Cache
Caches funding rates and open interest data to avoid repeated API calls
"""
import os
import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CoinalyzeCache:
    """Cache manager for Coinalyze API data"""
    
    def __init__(self, cache_dir: Optional[str] = None, ttl_hours: int = 1):
        """
        Initialize cache manager
        
        Args:
            cache_dir: Directory to store cache files. Defaults to workspace/data/.cache/coinalyze
            ttl_hours: Time-to-live in hours before cache is considered stale (default: 1 hour)
        """
        if cache_dir is None:
            workspace_root = Path(__file__).parent.parent.parent
            cache_dir = workspace_root / 'data' / '.cache' / 'coinalyze'
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl_hours = ttl_hours
        
        logger.info(f"Coinalyze cache initialized at: {self.cache_dir}")
        logger.info(f"Cache TTL: {ttl_hours} hours")
    
    def _get_cache_path(self, data_type: str, exchange_code: str = 'all') -> Path:
        """Get cache file path for a given data type"""
        return self.cache_dir / f"{data_type}_{exchange_code}.json"
    
    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if cache file exists and is not stale"""
        if not cache_path.exists():
            return False
        
        # Check file modification time
        mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age = datetime.now() - mtime
        
        if age > timedelta(hours=self.ttl_hours):
            logger.info(f"Cache expired: {cache_path.name} (age: {age})")
            return False
        
        logger.info(f"Cache valid: {cache_path.name} (age: {age})")
        return True
    
    def save_funding_rates(self, data: pd.DataFrame, exchange_code: str = 'all'):
        """Save funding rates to cache"""
        cache_path = self._get_cache_path('funding_rates', exchange_code)
        
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'exchange_code': exchange_code,
            'data': data.to_dict(orient='records')
        }
        
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        logger.info(f"Saved funding rates to cache: {cache_path.name} ({len(data)} records)")
    
    def load_funding_rates(self, exchange_code: str = 'all') -> Optional[pd.DataFrame]:
        """Load funding rates from cache if valid"""
        cache_path = self._get_cache_path('funding_rates', exchange_code)
        
        if not self._is_cache_valid(cache_path):
            return None
        
        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            
            df = pd.DataFrame(cache_data['data'])
            logger.info(f"Loaded funding rates from cache: {cache_path.name} ({len(df)} records)")
            return df
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return None
    
    def save_oi_history(self, data: pd.DataFrame, exchange_code: str, days: int):
        """Save open interest history to cache"""
        cache_key = f"{exchange_code}_days{days}"
        cache_path = self._get_cache_path('oi_history', cache_key)
        
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'exchange_code': exchange_code,
            'days': days,
            'data': data.to_dict(orient='records')
        }
        
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f, indent=2)
        
        logger.info(f"Saved OI history to cache: {cache_path.name} ({len(data)} records)")
    
    def load_oi_history(self, exchange_code: str, days: int) -> Optional[pd.DataFrame]:
        """Load open interest history from cache if valid"""
        cache_key = f"{exchange_code}_days{days}"
        cache_path = self._get_cache_path('oi_history', cache_key)
        
        if not self._is_cache_valid(cache_path):
            return None
        
        try:
            with open(cache_path, 'r') as f:
                cache_data = json.load(f)
            
            df = pd.DataFrame(cache_data['data'])
            # Convert date column to datetime if present
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            
            logger.info(f"Loaded OI history from cache: {cache_path.name} ({len(df)} records)")
            return df
        except Exception as e:
            logger.error(f"Error loading cache: {e}")
            return None
    
    def clear_cache(self, data_type: Optional[str] = None):
        """Clear cache files"""
        if data_type:
            pattern = f"{data_type}_*.json"
            files = list(self.cache_dir.glob(pattern))
        else:
            files = list(self.cache_dir.glob("*.json"))
        
        for f in files:
            f.unlink()
            logger.info(f"Deleted cache file: {f.name}")
        
        logger.info(f"Cleared {len(files)} cache files")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about cached files"""
        info = {
            'cache_dir': str(self.cache_dir),
            'ttl_hours': self.ttl_hours,
            'files': []
        }
        
        for cache_file in self.cache_dir.glob("*.json"):
            mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
            age = datetime.now() - mtime
            is_valid = age <= timedelta(hours=self.ttl_hours)
            
            info['files'].append({
                'name': cache_file.name,
                'size': cache_file.stat().st_size,
                'modified': mtime.isoformat(),
                'age_hours': age.total_seconds() / 3600,
                'is_valid': is_valid
            })
        
        return info


def fetch_coinalyze_funding_rates_cached(
    universe_symbols: List[str],
    exchange_code: str = 'H',
    cache_ttl_hours: int = 1,
) -> Optional[pd.DataFrame]:
    """
    Fetch funding rates with caching
    
    Args:
        universe_symbols: List of trading symbols
        exchange_code: Coinalyze exchange code ('H' for Hyperliquid, 'A' for Binance)
        cache_ttl_hours: Cache time-to-live in hours
    
    Returns:
        DataFrame with funding rates or None
    """
    cache = CoinalyzeCache(ttl_hours=cache_ttl_hours)
    
    # Try to load from cache
    df_cached = cache.load_funding_rates(exchange_code)
    if df_cached is not None:
        logger.info(f"Using cached funding rates for exchange {exchange_code}")
        return df_cached
    
    # Cache miss - fetch from API
    logger.info(f"Cache miss - fetching funding rates from Coinalyze API...")
    try:
        from execution.get_carry import fetch_coinalyze_funding_rates_for_universe
        
        df = fetch_coinalyze_funding_rates_for_universe(
            universe_symbols=universe_symbols,
            exchange_code=exchange_code
        )
        
        if df is not None and not df.empty:
            # Save to cache
            cache.save_funding_rates(df, exchange_code)
            logger.info(f"Fetched and cached {len(df)} funding rates")
            return df
        else:
            logger.warning("No funding rate data returned from API")
            return None
    except Exception as e:
        logger.error(f"Error fetching funding rates: {e}")
        return None


def fetch_coinalyze_aggregated_funding_cached(
    universe_symbols: List[str],
    aggregation: str = 'mean',
    cache_ttl_hours: int = 1,
) -> Optional[pd.DataFrame]:
    """
    Fetch aggregated funding rates with caching
    
    Args:
        universe_symbols: List of trading symbols
        aggregation: Aggregation method ('mean', 'median', 'binance_primary')
        cache_ttl_hours: Cache time-to-live in hours
    
    Returns:
        DataFrame with aggregated funding rates or None
    """
    cache = CoinalyzeCache(ttl_hours=cache_ttl_hours)
    
    # Try to load from cache
    df_cached = cache.load_funding_rates('aggregated')
    if df_cached is not None:
        logger.info(f"Using cached aggregated funding rates")
        return df_cached
    
    # Cache miss - fetch from API
    logger.info(f"Cache miss - fetching aggregated funding rates from Coinalyze API...")
    try:
        from execution.get_carry import fetch_coinalyze_aggregated_funding_rates
        
        df = fetch_coinalyze_aggregated_funding_rates(
            universe_symbols=universe_symbols,
            aggregation=aggregation
        )
        
        if df is not None and not df.empty:
            # Save to cache
            cache.save_funding_rates(df, 'aggregated')
            logger.info(f"Fetched and cached {len(df)} aggregated funding rates")
            return df
        else:
            logger.warning("No aggregated funding rate data returned from API")
            return None
    except Exception as e:
        logger.error(f"Error fetching aggregated funding rates: {e}")
        return None


def fetch_oi_history_cached(
    universe_symbols: List[str],
    exchange_code: str = 'H',
    days: int = 200,
    cache_ttl_hours: int = 8,
) -> Optional[pd.DataFrame]:
    """
    Fetch OI history with caching
    
    Note: Historical data has longer TTL (8 hours) since it changes less frequently
    
    Args:
        universe_symbols: List of trading symbols
        exchange_code: Coinalyze exchange code
        days: Number of days of history
        cache_ttl_hours: Cache time-to-live in hours (default 8 for historical data)
    
    Returns:
        DataFrame with OI history or None
    """
    cache = CoinalyzeCache(ttl_hours=cache_ttl_hours)
    
    # Try to load from cache
    df_cached = cache.load_oi_history(exchange_code, days)
    if df_cached is not None:
        logger.info(f"Using cached OI history for exchange {exchange_code} ({days} days)")
        return df_cached
    
    # Cache miss - fetch from API
    logger.info(f"Cache miss - fetching OI history from Coinalyze API...")
    
    # Import the internal fetch function from the strategy module
    try:
        import sys
        from pathlib import Path
        
        # Add strategies module to path if not already
        strategies_path = Path(__file__).parent.parent.parent / 'execution' / 'strategies'
        if str(strategies_path) not in sys.path:
            sys.path.insert(0, str(strategies_path))
        
        from open_interest_divergence import _fetch_oi_history_for_universe
        
        df = _fetch_oi_history_for_universe(
            universe_symbols=universe_symbols,
            exchange_code=exchange_code,
            days=days
        )
        
        if df is not None and not df.empty:
            # Save to cache
            cache.save_oi_history(df, exchange_code, days)
            logger.info(f"Fetched and cached {len(df)} OI history records")
            return df
        else:
            logger.warning("No OI history data returned from API")
            return None
    except Exception as e:
        logger.error(f"Error fetching OI history: {e}")
        return None


if __name__ == "__main__":
    """Test the cache"""
    cache = CoinalyzeCache(ttl_hours=1)
    
    print("="*80)
    print("COINALYZE CACHE TEST")
    print("="*80)
    
    # Show cache info
    info = cache.get_cache_info()
    print(f"\nCache directory: {info['cache_dir']}")
    print(f"TTL: {info['ttl_hours']} hours")
    print(f"\nCached files: {len(info['files'])}")
    
    for f in info['files']:
        status = "✓ VALID" if f['is_valid'] else "✗ EXPIRED"
        print(f"  {status} {f['name']}: {f['size']} bytes, age={f['age_hours']:.2f}h")
    
    print("\n" + "="*80)
