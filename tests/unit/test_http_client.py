"""Unit tests for HTTP client utilities."""

import pytest
import requests
from unittest.mock import Mock, patch, MagicMock

from src.smart_travel_planner.utils.http_client import HTTPClient, RateLimiter
from src.smart_travel_planner.exceptions import APIError, RateLimitError, ServiceUnavailableError


class TestRateLimiter:
    """Test cases for RateLimiter class."""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initialization."""
        limiter = RateLimiter(max_requests=10, time_window=60)
        assert limiter.max_requests == 10
        assert limiter.time_window == 60
        assert len(limiter.requests) == 0
    
    def test_rate_limiter_allowed_requests(self):
        """Test allowed requests within limits."""
        limiter = RateLimiter(max_requests=3, time_window=60)
        
        # First request should be allowed
        assert limiter.is_allowed() is True
        assert len(limiter.requests) == 1
        
        # Second request should be allowed
        assert limiter.is_allowed() is True
        assert len(limiter.requests) == 2
        
        # Third request should be allowed
        assert limiter.is_allowed() is True
        assert len(limiter.requests) == 3
    
    def test_rate_limiter_blocked_requests(self):
        """Test blocked requests when limit exceeded."""
        limiter = RateLimiter(max_requests=2, time_window=60)
        
        # Fill the limit
        limiter.is_allowed()
        limiter.is_allowed()
        
        # Next request should be blocked
        assert limiter.is_allowed() is False
        assert len(limiter.requests) == 2
    
    def test_rate_limiter_time_window_reset(self):
        """Test rate limiter reset after time window."""
        limiter = RateLimiter(max_requests=2, time_window=1)
        
        # Fill the limit
        limiter.is_allowed()
        limiter.is_allowed()
        
        # Should be blocked
        assert limiter.is_allowed() is False
        
        # Wait for time window to pass
        import time
        time.sleep(1.1)
        
        # Should be allowed again
        assert limiter.is_allowed() is True
    
    def test_wait_time_calculation(self):
        """Test wait time calculation."""
        limiter = RateLimiter(max_requests=2, time_window=60)
        
        # Fill the limit
        limiter.is_allowed()
        limiter.is_allowed()
        
        # Wait time should be positive
        wait_time = limiter.wait_time()
        assert wait_time > 0
        assert wait_time <= 60
        
        # When allowed, wait time should be 0
        limiter.requests = []  # Clear requests
        assert limiter.wait_time() == 0


class TestHTTPClient:
    """Test cases for HTTPClient class."""
    
    def test_client_initialization(self):
        """Test HTTP client initialization."""
        client = HTTPClient(base_url="https://api.example.com", timeout=15)
        
        assert client.base_url == "https://api.example.com"
        assert client.timeout == 15
        assert client.session is not None
        assert client.rate_limiter is not None
    
    def test_full_url_construction(self):
        """Test full URL construction."""
        client = HTTPClient(base_url="https://api.example.com")
        
        assert client._get_full_url("users") == "https://api.example.com/users"
        assert client._get_full_url("/users") == "https://api.example.com/users"
        assert client._get_full_url("users/123") == "https://api.example.com/users/123"
        
        # Without base URL
        client_no_base = HTTPClient()
        assert client_no_base._get_full_url("https://other.com/api") == "https://other.com/api"
    
    @patch('src.smart_travel_planner.utils.http_client.requests.Session.request')
    def test_successful_request(self, mock_request):
        """Test successful HTTP request."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response
        
        client = HTTPClient(base_url="https://api.example.com")
        result = client.get("/test")
        
        assert result == {"status": "success"}
        mock_request.assert_called_once()
    
    @patch('src.smart_travel_planner.utils.http_client.requests.Session.request')
    def test_request_with_rate_limiting(self, mock_request):
        """Test request with rate limiting."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "success"}
        mock_response.raise_for_status.return_value = None
        mock_request.return_value = mock_response
        
        # Create client with very restrictive rate limit
        client = HTTPClient(base_url="https://api.example.com")
        client.rate_limiter.max_requests = 1
        client.rate_limiter.time_window = 60
        
        # First request should work
        result1 = client.get("/test1")
        assert result1 == {"status": "success"}
        
        # Second request should trigger rate limit wait
        # Since we can't actually wait in tests, we'll mock the wait_time
        client.rate_limiter.wait_time = Mock(return_value=0)
        
        result2 = client.get("/test2")
        assert result2 == {"status": "success"}
    
    @patch('src.smart_travel_planner.utils.http_client.requests.Session.request')
    def test_authentication_error(self, mock_request):
        """Test authentication error handling."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.raise_for_status.side_effect = requests.HTTPError()
        mock_request.return_value = mock_response
        
        client = HTTPClient()
        
        with pytest.raises(APIError) as exc_info:
            client.get("/test")
        
        assert exc_info.value.status_code == 401
        assert "Authentication failed" in str(exc_info.value)
    
    @patch('src.smart_travel_planner.utils.http_client.requests.Session.request')
    def test_rate_limit_error(self, mock_request):
        """Test rate limit error handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}
        mock_response.text = "Rate limit exceeded"
        mock_response.raise_for_status.side_effect = requests.HTTPError()
        mock_request.return_value = mock_response
        
        client = HTTPClient()
        
        with pytest.raises(RateLimitError) as exc_info:
            client.get("/test")
        
        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 60
    
    @patch('src.smart_travel_planner.utils.http_client.requests.Session.request')
    def test_service_unavailable_error(self, mock_request):
        """Test service unavailable error handling."""
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.text = "Service unavailable"
        mock_response.raise_for_status.side_effect = requests.HTTPError()
        mock_request.return_value = mock_response
        
        client = HTTPClient()
        
        with pytest.raises(ServiceUnavailableError) as exc_info:
            client.get("/test")
        
        assert exc_info.value.status_code == 503
        assert "Service unavailable" in str(exc_info.value)
    
    @patch('src.smart_travel_planner.utils.http_client.requests.Session.request')
    def test_timeout_error(self, mock_request):
        """Test timeout error handling."""
        mock_request.side_effect = requests.Timeout()
        
        client = HTTPClient()
        
        with pytest.raises(APIError) as exc_info:
            client.get("/test")
        
        assert "timeout" in str(exc_info.value).lower()
    
    @patch('src.smart_travel_planner.utils.http_client.requests.Session.request')
    def test_ssl_error(self, mock_request):
        """Test SSL error handling."""
        mock_request.side_effect = requests.exceptions.SSLError("SSL verification failed")
        
        client = HTTPClient()
        
        with pytest.raises(APIError) as exc_info:
            client.get("/test")
        
        assert "SSL error" in str(exc_info.value)
    
    @patch('src.smart_travel_planner.utils.http_client.requests.Session.request')
    def test_json_decode_error(self, mock_request):
        """Test JSON decode error handling."""
        mock_response = Mock()
        mock_response.json.side_effect = requests.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status.return_value = None
        mock_response.text = "Plain text response"
        mock_request.return_value = mock_response
        
        client = HTTPClient()
        result = client.get("/test")
        
        assert result == {"text": "Plain text response"}
    
    def test_post_request(self):
        """Test POST request."""
        with patch.object(HTTPClient, 'request') as mock_request:
            mock_request.return_value = {"status": "success"}
            
            client = HTTPClient()
            result = client.post("/test", json={"data": "value"})
            
            mock_request.assert_called_once_with(
                "POST", "/test", json={"data": "value"}, data=None, headers=None, params=None
            )
            assert result == {"status": "success"}
    
    def test_put_request(self):
        """Test PUT request."""
        with patch.object(HTTPClient, 'request') as mock_request:
            mock_request.return_value = {"status": "success"}
            
            client = HTTPClient()
            result = client.put("/test", data={"data": "value"})
            
            mock_request.assert_called_once_with(
                "PUT", "/test", json=None, data={"data": "value"}, headers=None, params=None
            )
            assert result == {"status": "success"}
    
    def test_delete_request(self):
        """Test DELETE request."""
        with patch.object(HTTPClient, 'request') as mock_request:
            mock_request.return_value = {"status": "success"}
            
            client = HTTPClient()
            result = client.delete("/test")
            
            mock_request.assert_called_once_with(
                "DELETE", "/test", json=None, data=None, headers=None, params=None
            )
            assert result == {"status": "success"}
    
    def test_context_manager(self):
        """Test HTTP client as context manager."""
        with HTTPClient() as client:
            assert client.session is not None
        
        # Session should be closed after context exit
        # Note: We can't easily test this without mocking more deeply
    
    def test_close_method(self):
        """Test close method."""
        client = HTTPClient()
        mock_session = Mock()
        client.session = mock_session
        
        client.close()
        
        mock_session.close.assert_called_once()
        assert client.session is None
