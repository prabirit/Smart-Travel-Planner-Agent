"""Custom exceptions for Smart Travel Planner."""

from .base import (
    SmartTravelPlannerError,
    ConfigurationError,
    APIError,
    ValidationError,
    AuthenticationError,
    RateLimitError,
    ServiceUnavailableError,
)
from .travel_exceptions import (
    FlightSearchError,
    HotelSearchError,
    WeatherError,
    RestaurantSearchError,
    EmissionsCalculationError,
    ItineraryGenerationError,
)

__all__ = [
    # Base exceptions
    "SmartTravelPlannerError",
    "ConfigurationError", 
    "APIError",
    "ValidationError",
    "AuthenticationError",
    "RateLimitError",
    "ServiceUnavailableError",
    # Travel-specific exceptions
    "FlightSearchError",
    "HotelSearchError", 
    "WeatherError",
    "RestaurantSearchError",
    "EmissionsCalculationError",
    "ItineraryGenerationError",
]
