"""HTTP client with rate limiting and retry logic for Smart Travel Planner."""

import time
import requests
from typing import Optional, Dict, Any, Callable
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.exceptions import RequestException, Timeout, SSLError

from ..config import get_settings
from ..exceptions import APIError, RateLimitError, ServiceUnavailableError


class RateLimiter:
    """Simple rate limiter for API requests."""
    
    def __init__(self, max_requests: int, time_window: int):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = []
    
    def is_allowed(self) -> bool:
        """Check if request is allowed under rate limit."""
        now = time.time()
        # Remove old requests outside the time window
        self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
        
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        
        return False
    
    def wait_time(self) -> float:
        """Get time to wait until next request is allowed."""
        if self.is_allowed():
            return 0
        
        oldest_request = min(self.requests) if self.requests else 0
        wait_time = self.time_window - (time.time() - oldest_request)
        return max(0, wait_time)


class HTTPClient:
    """Enhanced HTTP client with retry logic, rate limiting, and security."""
    
    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        self.base_url = base_url.rstrip('/') if base_url else None
        self.timeout = timeout
        self.settings = get_settings()
        
        # Setup rate limiter
        self.rate_limiter = RateLimiter(
            max_requests=self.settings.security.rate_limit_requests,
            time_window=self.settings.security.rate_limit_window
        )
        
        # Setup session with retry strategy
        self.session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.settings.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set SSL verification
        self.session.verify = self.settings.security.ssl_verify
        
        # Set CA bundle if specified
        if self.settings.security.requests_ca_bundle:
            self.session.verify = self.settings.security.requests_ca_bundle
    
    def _get_full_url(self, endpoint: str) -> str:
        """Get full URL from endpoint."""
        if self.base_url:
            return f"{self.base_url}/{endpoint.lstrip('/')}"
        return endpoint
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle HTTP response and errors."""
        try:
            response.raise_for_status()
            return response.json()
        except requests.JSONDecodeError:
            return {"text": response.text}
        except requests.HTTPError as e:
            if response.status_code == 401:
                raise APIError(
                    "Authentication failed",
                    status_code=response.status_code,
                    response_text=response.text
                )
            elif response.status_code == 429:
                retry_after = response.headers.get('Retry-After')
                raise RateLimitError(
                    "Rate limit exceeded",
                    retry_after=int(retry_after) if retry_after else None,
                    response_text=response.text
                )
            elif response.status_code >= 500:
                raise ServiceUnavailableError(
                    f"Service unavailable: {e}",
                    status_code=response.status_code,
                    response_text=response.text
                )
            else:
                raise APIError(
                    f"HTTP error: {e}",
                    status_code=response.status_code,
                    response_text=response.text
                )
        except RequestException as e:
            raise APIError(f"Request failed: {e}")
    
    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request with rate limiting and error handling."""
        
        # Check rate limit
        wait_time = self.rate_limiter.wait_time()
        if wait_time > 0:
            time.sleep(wait_time)
        
        url = self._get_full_url(endpoint)
        
        try:
            response = self.session.request(
                method=method.upper(),
                url=url,
                params=params,
                data=data,
                json=json,
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )
            return self._handle_response(response)
            
        except Timeout:
            raise APIError(f"Request timeout after {self.timeout} seconds")
        except SSLError as e:
            raise APIError(f"SSL error: {e}")
        except RequestException as e:
            raise APIError(f"Request failed: {e}")
    
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make GET request."""
        return self.request("GET", endpoint, params=params, **kwargs)
    
    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make POST request."""
        return self.request("POST", endpoint, data=data, json=json, **kwargs)
    
    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make PUT request."""
        return self.request("PUT", endpoint, data=data, json=json, **kwargs)
    
    def delete(
        self,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make DELETE request."""
        return self.request("DELETE", endpoint, **kwargs)
    
    def close(self):
        """Close the HTTP session."""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
