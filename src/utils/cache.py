#!/usr/bin/env python3
"""
Simple Caching System
=====================

Cache expensive operations to speed up repeated queries.
"""

import pickle
import time
import os
from typing import Any, Optional
from functools import wraps


class SimpleCache:
    """Simple time-based cache."""
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize cache.
        
        Args:
            ttl_seconds: Time to live in seconds (default 5 minutes)
        """
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                # Expired, remove
                del self.cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Set value in cache with current timestamp."""
        self.cache[key] = (value, time.time())
    
    def clear(self):
        """Clear all cached values."""
        self.cache = {}
    
    def size(self) -> int:
        """Return number of cached items."""
        return len(self.cache)


class FileCache:
    """Persistent file-based cache."""
    
    def __init__(self, cache_dir: str = 'data/cache', ttl_seconds: int = 3600):
        """
        Initialize file cache.
        
        Args:
            cache_dir: Directory to store cache files
            ttl_seconds: Time to live in seconds (default 1 hour)
        """
        self.cache_dir = cache_dir
        self.ttl = ttl_seconds
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_filepath(self, key: str) -> str:
        """Get filepath for cache key."""
        # Sanitize key for filename
        safe_key = key.replace('/', '_').replace('\\', '_')
        return os.path.join(self.cache_dir, f"{safe_key}.pkl")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from file cache if not expired."""
        filepath = self._get_filepath(key)
        
        if not os.path.exists(filepath):
            return None
        
        # Check if expired
        file_age = time.time() - os.path.getmtime(filepath)
        if file_age > self.ttl:
            os.remove(filepath)
            return None
        
        # Load from file
        try:
            with open(filepath, 'rb') as f:
                return pickle.load(f)
        except Exception:
            return None
    
    def set(self, key: str, value: Any):
        """Set value in file cache."""
        filepath = self._get_filepath(key)
        try:
            with open(filepath, 'wb') as f:
                pickle.dump(value, f)
        except Exception:
            pass
    
    def clear(self):
        """Clear all cached files."""
        for filename in os.listdir(self.cache_dir):
            filepath = os.path.join(self.cache_dir, filename)
            if os.path.isfile(filepath):
                os.remove(filepath)


def cached(ttl_seconds: int = 300):
    """
    Decorator to cache function results.
    
    Usage:
        @cached(ttl_seconds=300)
        def expensive_function(ticker):
            # ... expensive operation
            return result
    """
    cache = SimpleCache(ttl_seconds=ttl_seconds)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key = f"{func.__name__}_{str(args)}_{str(kwargs)}"
            
            # Check cache
            result = cache.get(key)
            if result is not None:
                return result
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Cache result
            cache.set(key, result)
            
            return result
        return wrapper
    return decorator


# Global caches for common use
YFINANCE_CACHE = FileCache(cache_dir='data/cache/yfinance', ttl_seconds=300)  # 5 min
LEAPS_CACHE = FileCache(cache_dir='data/cache/leaps', ttl_seconds=3600)  # 1 hour
SCANNER_CACHE = SimpleCache(ttl_seconds=900)  # 15 min in memory


def cache_yfinance_ticker(ticker: str, data: Any):
    """Cache yfinance ticker data."""
    YFINANCE_CACHE.set(f'ticker_{ticker}', data)


def get_cached_yfinance_ticker(ticker: str) -> Optional[Any]:
    """Get cached yfinance ticker data."""
    return YFINANCE_CACHE.get(f'ticker_{ticker}')


def cache_leaps_analysis(ticker: str, result: dict):
    """Cache LEAPS analysis result."""
    LEAPS_CACHE.set(f'leaps_{ticker}', result)


def get_cached_leaps_analysis(ticker: str) -> Optional[dict]:
    """Get cached LEAPS analysis."""
    return LEAPS_CACHE.get(f'leaps_{ticker}')

