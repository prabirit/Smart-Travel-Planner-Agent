"""Travel-specific exceptions for Smart Travel Planner."""

from .base import SmartTravelPlannerError


class FlightSearchError(SmartTravelPlannerError):
    """Raised when flight search fails."""
    pass


class HotelSearchError(SmartTravelPlannerError):
    """Raised when hotel search fails."""
    pass


class WeatherError(SmartTravelPlannerError):
    """Raised when weather data retrieval fails."""
    pass


class RestaurantSearchError(SmartTravelPlannerError):
    """Raised when restaurant search fails."""
    pass


class EmissionsCalculationError(SmartTravelPlannerError):
    """Raised when emissions calculation fails."""
    pass


class ItineraryGenerationError(SmartTravelPlannerError):
    """Raised when itinerary generation fails."""
    pass
