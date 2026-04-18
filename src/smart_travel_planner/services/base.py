"""Base service class for Smart Travel Planner services."""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from ..config import get_settings
from ..utils.http_client import HTTPClient
from ..utils.cache import get_cache


class BaseService(ABC):
    """Base class for all services."""
    
    def __init__(self, name: str):
        self.name = name
        self.settings = get_settings()
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.cache = get_cache()
        self.http_client: Optional[HTTPClient] = None
    
    def _init_http_client(self, base_url: Optional[str] = None, timeout: Optional[int] = None) -> HTTPClient:
        """Initialize HTTP client for the service."""
        if self.http_client is None:
            client_timeout = timeout or self.settings.request_timeout
            self.http_client = HTTPClient(base_url=base_url, timeout=client_timeout)
        return self.http_client
    
    def _log_api_call(self, endpoint: str, params: Optional[Dict[str, Any]] = None):
        """Log API call with masked sensitive data."""
        from ..utils.security import mask_sensitive_info
        
        masked_params = None
        if params:
            masked_params = mask_sensitive_info(str(params))
        
        self.logger.info(f"API call: {endpoint}", extra={
            "service": self.name,
            "endpoint": endpoint,
            "params": masked_params
        })
    
    def _handle_api_error(self, error: Exception, endpoint: str, context: Optional[str] = None):
        """Handle API errors consistently."""
        error_msg = f"{self.name} API error on {endpoint}"
        if context:
            error_msg += f" ({context})"
        
        self.logger.error(f"{error_msg}: {error}", exc_info=True)
        
        # Re-raise with context
        if hasattr(error, 'to_dict'):
            raise error
        else:
            from ..exceptions import APIError
            raise APIError(f"{error_msg}: {error}")
    
    def _get_cache_key(self, method: str, **kwargs) -> str:
        """Generate cache key for method call."""
        key_parts = [self.name, method]
        
        for k, v in sorted(kwargs.items()):
            if v is not None:
                key_parts.append(f"{k}={v}")
        
        return ":".join(key_parts)
    
    def _cache_get(self, method: str, **kwargs) -> Optional[Any]:
        """Get cached result for method."""
        if not self.settings.cache.enabled:
            return None
        
        cache_key = self._get_cache_key(method, **kwargs)
        return self.cache.get(cache_key)
    
    def _cache_set(self, method: str, result: Any, ttl: Optional[int] = None, **kwargs):
        """Cache result for method."""
        if not self.settings.cache.enabled:
            return
        
        cache_key = self._get_cache_key(method, **kwargs)
        cache_ttl = ttl or self.settings.cache.ttl
        self.cache.set(cache_key, result, ttl=cache_ttl)
    
    @abstractmethod
    def health_check(self) -> bool:
        """Check if the service is healthy."""
        pass
    
    def close(self):
        """Clean up resources."""
        if self.http_client:
            self.http_client.close()
            self.http_client = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
