"""Unit tests for configuration management."""

import pytest
import os
from pathlib import Path
from unittest.mock import patch

from src.smart_travel_planner.config.settings import Settings, get_settings, reload_settings
from src.smart_travel_planner.exceptions import ConfigurationError


class TestSettings:
    """Test cases for Settings class."""
    
    def test_default_settings(self):
        """Test default settings initialization."""
        settings = Settings()
        
        assert settings.environment == "development"
        assert settings.debug is True  # Based on environment
        assert settings.max_retries == 3
        assert settings.request_timeout == 30
        assert settings.amadeus.checkin_offset_days == 7
        assert settings.amadeus.stay_nights == 1
    
    def test_environment_variable_loading(self, monkeypatch):
        """Test loading settings from environment variables."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        monkeypatch.setenv("AMADEUS_CHECKIN_OFFSET_DAYS", "14")
        monkeypatch.setenv("AMADEUS_STAY_NIGHTS", "3")
        monkeypatch.setenv("LOG_LEVEL", "ERROR")
        monkeypatch.setenv("SSL_VERIFY", "false")
        
        settings = Settings()
        
        assert settings.environment == "production"
        assert settings.debug is False
        assert settings.api.google_api_key == "test-key"
        assert settings.amadeus.checkin_offset_days == 14
        assert settings.amadeus.stay_nights == 3
        assert settings.logging.level == "ERROR"
        assert settings.security.ssl_verify is False
    
    def test_validation_missing_required_keys(self):
        """Test validation with missing required API keys."""
        settings = Settings()
        settings.api.google_api_key = None
        
        issues = settings.validate()
        
        assert "google_api_key" in issues
        assert "Required" in issues["google_api_key"]
    
    def test_validation_amadeus_keys(self, monkeypatch):
        """Test Amadeus API key validation."""
        monkeypatch.setenv("AMADEUS_API_KEY", "test-key")
        # Missing secret
        settings = Settings()
        
        issues = settings.validate()
        
        assert "amadeus_api_secret" in issues
        assert "Required when amadeus_api_key is provided" in issues["amadeus_api_secret"]
    
    def test_validation_numeric_settings(self, monkeypatch):
        """Test numeric setting validation."""
        monkeypatch.setenv("AMADEUS_CHECKIN_OFFSET_DAYS", "-1")
        monkeypatch.setenv("AMADEUS_STAY_NIGHTS", "0")
        
        settings = Settings()
        issues = settings.validate()
        
        assert "amadeus_checkin_offset_days" in issues
        assert "amadeus_stay_nights" in issues
    
    def test_to_dict_excludes_sensitive_data(self, monkeypatch):
        """Test that to_dict excludes sensitive API keys."""
        monkeypatch.setenv("GOOGLE_API_KEY", "secret-key")
        monkeypatch.setenv("AMADEUS_API_KEY", "secret-amadeus")
        
        settings = Settings()
        result = settings.to_dict()
        
        # Should not contain API keys
        assert "api" not in result
        assert "google_api_key" not in str(result)
        assert "amadeus_api_key" not in str(result)
        
        # Should contain non-sensitive data
        assert "environment" in result
        assert "debug" in result


class TestGlobalSettings:
    """Test cases for global settings management."""
    
    def test_get_settings_singleton(self, monkeypatch):
        """Test that get_settings returns the same instance."""
        monkeypatch.setenv("ENVIRONMENT", "test")
        
        settings1 = get_settings()
        settings2 = get_settings()
        
        assert settings1 is settings2
    
    def test_reload_settings(self, monkeypatch):
        """Test settings reload functionality."""
        monkeypatch.setenv("ENVIRONMENT", "test1")
        settings1 = get_settings()
        
        # Change environment and reload
        monkeypatch.setenv("ENVIRONMENT", "test2")
        reload_settings()
        
        settings2 = get_settings()
        
        assert settings1 is not settings2
        assert settings2.environment == "test2"
    
    def test_env_file_loading(self, temp_dir, monkeypatch):
        """Test loading settings from .env file."""
        env_file = temp_dir / ".env"
        env_file.write_text("""
ENVIRONMENT=test
GOOGLE_API_KEY=env-test-key
LOG_LEVEL=DEBUG
""")
        
        # Mock the .env file path
        with patch('src.smart_travel_planner.config.settings.Path') as mock_path:
            mock_path.return_value.parent.parent.parent.parent / ".env" = env_file
            
            settings = Settings()
            
            assert settings.environment == "test"
            assert settings.api.google_api_key == "env-test-key"
            assert settings.logging.level == "DEBUG"


class TestConfigurationError:
    """Test cases for configuration errors."""
    
    def test_configuration_error_creation(self):
        """Test ConfigurationError creation and properties."""
        error = ConfigurationError(
            "Test error",
            error_code="TEST_ERROR",
            details={"field": "test"}
        )
        
        assert str(error) == "Test error"
        assert error.error_code == "TEST_ERROR"
        assert error.details["field"] == "test"
    
    def test_configuration_error_to_dict(self):
        """Test ConfigurationError to_dict method."""
        error = ConfigurationError(
            "Test error",
            error_code="TEST_ERROR",
            details={"field": "test"}
        )
        
        result = error.to_dict()
        
        assert result["error"] == "ConfigurationError"
        assert result["message"] == "Test error"
        assert result["error_code"] == "TEST_ERROR"
        assert result["details"]["field"] == "test"
