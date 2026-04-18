"""Configuration settings management for Smart Travel Planner."""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv


@dataclass
class APIConfig:
    """API configuration settings."""
    google_api_key: Optional[str] = None
    google_maps_api_key: Optional[str] = None
    google_places_api_key: Optional[str] = None
    weather_api_key: Optional[str] = None
    openaq_api_key: Optional[str] = None
    amadeus_api_key: Optional[str] = None
    amadeus_api_secret: Optional[str] = None


@dataclass
class AmadeusConfig:
    """Amadeus-specific configuration."""
    checkin_offset_days: int = 7
    stay_nights: int = 1
    base_url: str = "https://test.api.amadeus.com"
    timeout: int = 30


@dataclass
class GoogleConfig:
    """Google services configuration."""
    gemini_model: str = "gemini-1.5-flash"
    maps_timeout: int = 30
    places_timeout: int = 30


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class SecurityConfig:
    """Security configuration."""
    requests_ca_bundle: Optional[str] = None
    ssl_verify: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 3600  # 1 hour


@dataclass
class CacheConfig:
    """Caching configuration."""
    enabled: bool = True
    ttl: int = 3600  # 1 hour
    max_size: int = 1000


@dataclass
class Settings:
    """Main application settings."""
    
    # API configurations
    api: APIConfig = field(default_factory=APIConfig)
    amadeus: AmadeusConfig = field(default_factory=AmadeusConfig)
    google: GoogleConfig = field(default_factory=GoogleConfig)
    
    # System configurations
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    
    # Application settings
    debug: bool = False
    environment: str = "development"
    max_retries: int = 3
    request_timeout: int = 30
    
    # Data paths
    data_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "data")
    emission_factors_file: str = "emission_factors.csv"
    
    def __post_init__(self):
        """Post-initialization setup."""
        # Load environment variables
        self._load_env_vars()
        
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Set debug mode based on environment
        self.debug = self.environment.lower() in ("development", "dev", "debug")
    
    def _load_env_vars(self) -> None:
        """Load configuration from environment variables."""
        # API keys
        self.api.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.api.google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
        self.api.google_places_api_key = os.getenv("GOOGLE_PLACES_API_KEY")
        self.api.weather_api_key = os.getenv("WEATHER_API_KEY")
        self.api.openaq_api_key = os.getenv("OPENAQ_API_KEY")
        self.api.amadeus_api_key = os.getenv("AMADEUS_API_KEY")
        self.api.amadeus_api_secret = os.getenv("AMADEUS_API_SECRET")
        
        # Amadeus settings
        if os.getenv("AMADEUS_CHECKIN_OFFSET_DAYS"):
            self.amadeus.checkin_offset_days = int(os.getenv("AMADEUS_CHECKIN_OFFSET_DAYS"))
        if os.getenv("AMADEUS_STAY_NIGHTS"):
            self.amadeus.stay_nights = int(os.getenv("AMADEUS_STAY_NIGHTS"))
        
        # Security settings
        self.security.requests_ca_bundle = os.getenv("REQUESTS_CA_BUNDLE")
        if os.getenv("SSL_VERIFY"):
            self.security.ssl_verify = os.getenv("SSL_VERIFY").lower() != "false"
        
        # Logging settings
        if os.getenv("LOG_LEVEL"):
            self.logging.level = os.getenv("LOG_LEVEL").upper()
        if os.getenv("LOG_FILE"):
            self.logging.file_path = os.getenv("LOG_FILE")
        
        # Environment
        self.environment = os.getenv("ENVIRONMENT", "development")
    
    def validate(self) -> Dict[str, Any]:
        """Validate configuration and return any issues."""
        issues = {}
        
        # Check required API keys for core functionality
        if not self.api.google_api_key:
            issues["google_api_key"] = "Required for itinerary generation"
        
        # Check optional but recommended API keys
        optional_keys = {
            "google_maps_api_key": "Route planning and enhanced features",
            "google_places_api_key": "Restaurant recommendations",
            "amadeus_api_key": "Real-time flight and hotel pricing",
        }
        
        for key, description in optional_keys.items():
            if not getattr(self.api, key):
                issues[key] = f"Optional: {description}"
        
        # Validate Amadeus configuration
        if self.api.amadeus_api_key and not self.api.amadeus_api_secret:
            issues["amadeus_api_secret"] = "Required when amadeus_api_key is provided"
        
        # Validate numeric settings
        if self.amadeus.checkin_offset_days < 0:
            issues["amadeus_checkin_offset_days"] = "Must be non-negative"
        
        if self.amadeus.stay_nights < 1:
            issues["amadeus_stay_nights"] = "Must be at least 1"
        
        return issues
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary (excluding sensitive data)."""
        return {
            "environment": self.environment,
            "debug": self.debug,
            "amadeus": {
                "checkin_offset_days": self.amadeus.checkin_offset_days,
                "stay_nights": self.amadeus.stay_nights,
            },
            "google": {
                "gemini_model": self.google.gemini_model,
            },
            "logging": {
                "level": self.logging.level,
                "file_path": self.logging.file_path,
            },
            "security": {
                "ssl_verify": self.security.ssl_verify,
                "rate_limit_requests": self.security.rate_limit_requests,
            },
            "cache": {
                "enabled": self.cache.enabled,
                "ttl": self.cache.ttl,
            },
        }


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        # Load .env file if it exists
        env_path = Path(__file__).parent.parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        
        _settings = Settings()
        
        # Validate and log any configuration issues
        issues = _settings.validate()
        if issues:
            import logging
            logger = logging.getLogger(__name__)
            for key, message in issues.items():
                if "Required" in message:
                    logger.error(f"Configuration issue: {key} - {message}")
                else:
                    logger.warning(f"Configuration note: {key} - {message}")
    
    return _settings


def reload_settings() -> Settings:
    """Reload settings from environment variables."""
    global _settings
    _settings = None
    return get_settings()
