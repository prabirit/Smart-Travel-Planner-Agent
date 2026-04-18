"""Data models for Smart Travel Planner."""

from .travel_models import (
    Location,
    Flight,
    Hotel,
    Restaurant,
    WeatherInfo,
    AirQualityInfo,
    EmissionsData,
    Itinerary,
    TravelRequest,
)
from .api_models import (
    APIResponse,
    ErrorResponse,
    SuccessResponse,
)

__all__ = [
    # Travel models
    "Location",
    "Flight", 
    "Hotel",
    "Restaurant",
    "WeatherInfo",
    "AirQualityInfo",
    "EmissionsData",
    "Itinerary",
    "TravelRequest",
    # API models
    "APIResponse",
    "ErrorResponse", 
    "SuccessResponse",
]
