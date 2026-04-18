"""Caching utilities for Smart Travel Planner."""

import time
import json
import hashlib
from typing import Any, Optional, Dict, Union
from pathlib import Path

from ..config import get_settings


class CacheManager:
    """Simple in-memory cache with optional file persistence."""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600, persist_file: Optional[str] = None):
        self.max_size = max_size
        self.ttl = ttl
        self.persist_file = Path(persist_file) if persist_file else None
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        # Load from file if persistence is enabled
        if self.persist_file and self.persist_file.exists():
            self._load_from_file()
    
    def _generate_key(self, key: Union[str, Dict[str, Any]]) -> str:
        """Generate cache key from input."""
        if isinstance(key, str):
            return key
        
        # Convert dict to JSON string for consistent key generation
        if isinstance(key, dict):
            # Sort keys for consistent hashing
            key_str = json.dumps(key, sort_keys=True, separators=(',', ':'))
            return hashlib.md5(key_str.encode()).hexdigest()
        
        # Convert other types to string
        return str(key)
    
    def _is_expired(self, entry: Dict[str, Any]) -> bool:
        """Check if cache entry is expired."""
        if self.ttl <= 0:  # No expiration
            return False
        return time.time() - entry['timestamp'] > self.ttl
    
    def _evict_if_needed(self):
        """Evict oldest entries if cache is full."""
        if len(self._cache) <= self.max_size:
            return
        
        # Sort by timestamp and remove oldest entries
        sorted_items = sorted(self._cache.items(), key=lambda x: x[1]['timestamp'])
        items_to_remove = len(self._cache) - self.max_size + 1
        
        for key, _ in sorted_items[:items_to_remove]:
            del self._cache[key]
    
    def _save_to_file(self):
        """Save cache to file."""
        if not self.persist_file:
            return
        
        try:
            self.persist_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.persist_file, 'w') as f:
                json.dump(self._cache, f)
        except Exception:
            # Silently fail file operations to avoid breaking the application
            pass
    
    def _load_from_file(self):
        """Load cache from file."""
        if not self.persist_file or not self.persist_file.exists():
            return
        
        try:
            with open(self.persist_file, 'r') as f:
                self._cache = json.load(f)
        except Exception:
            # Silently fail file operations
            self._cache = {}
    
    def get(self, key: Union[str, Dict[str, Any]]) -> Optional[Any]:
        """Get value from cache."""
        cache_key = self._generate_key(key)
        
        if cache_key not in self._cache:
            return None
        
        entry = self._cache[cache_key]
        
        # Check if expired
        if self._is_expired(entry):
            del self._cache[cache_key]
            return None
        
        # Update access time
        entry['access_time'] = time.time()
        return entry['value']
    
    def set(self, key: Union[str, Dict[str, Any]], value: Any, ttl: Optional[int] = None):
        """Set value in cache."""
        cache_key = self._generate_key(key)
        current_time = time.time()
        
        # Use custom TTL or default
        entry_ttl = ttl if ttl is not None else self.ttl
        
        self._cache[cache_key] = {
            'value': value,
            'timestamp': current_time,
            'access_time': current_time,
            'ttl': entry_ttl,
        }
        
        # Evict if needed
        self._evict_if_needed()
        
        # Save to file if persistence is enabled
        if self.persist_file:
            self._save_to_file()
    
    def delete(self, key: Union[str, Dict[str, Any]]) -> bool:
        """Delete entry from cache."""
        cache_key = self._generate_key(key)
        
        if cache_key in self._cache:
            del self._cache[cache_key]
            
            # Save to file if persistence is enabled
            if self.persist_file:
                self._save_to_file()
            return True
        
        return False
    
    def clear(self):
        """Clear all cache entries."""
        self._cache.clear()
        
        # Save to file if persistence is enabled
        if self.persist_file:
            self._save_to_file()
    
    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)
    
    def cleanup_expired(self):
        """Remove expired entries from cache."""
        expired_keys = []
        
        for key, entry in self._cache.items():
            if self._is_expired(entry):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        # Save to file if entries were removed
        if expired_keys and self.persist_file:
            self._save_to_file()
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self._cache)
        expired_count = sum(1 for entry in self._cache.values() if self._is_expired(entry))
        
        return {
            'total_entries': total_entries,
            'expired_entries': expired_count,
            'valid_entries': total_entries - expired_count,
            'max_size': self.max_size,
            'ttl': self.ttl,
            'utilization': total_entries / self.max_size if self.max_size > 0 else 0,
        }


# Global cache instance
_cache_manager: Optional[CacheManager] = None


def get_cache() -> CacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    
    if _cache_manager is None:
        settings = get_settings()
        
        if settings.cache.enabled:
            persist_file = settings.data_dir / "cache.json"
            _cache_manager = CacheManager(
                max_size=settings.cache.max_size,
                ttl=settings.cache.ttl,
                persist_file=str(persist_file)
            )
        else:
            # Disabled cache - use a no-op cache
            _cache_manager = CacheManager(max_size=0, ttl=0)
    
    return _cache_manager


def cache_key(*args, **kwargs) -> str:
    """Generate a cache key from function arguments."""
    key_data = {
        'args': args,
        'kwargs': sorted(kwargs.items())
    }
    return hashlib.md5(json.dumps(key_data, sort_keys=True).encode()).hexdigest()


def cached(ttl: Optional[int] = None, key_func: Optional[callable] = None):
    """Decorator for caching function results."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache = get_cache()
            
            # Generate cache key
            if key_func:
                cache_key_data = key_func(*args, **kwargs)
            else:
                cache_key_data = cache_key(func.__name__, *args, **kwargs)
            
            # Try to get from cache
            result = cache.get(cache_key_data)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key_data, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator
