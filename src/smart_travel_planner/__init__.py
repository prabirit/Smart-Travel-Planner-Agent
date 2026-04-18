"""
Smart Travel Planner Agent

A sustainability-focused travel planning system that integrates real-time flight and hotel pricing,
weather and air quality data, emissions estimation, and restaurant recommendations.
"""

__version__ = "1.0.0"
__author__ = "Smart Travel Planner Team"
__email__ = "contact@smarttravelplanner.com"

from .core.agent import TravelPlannerAgent
from .core.itinerary import ItineraryGenerator
from .services.weather import WeatherService
from .services.flights import FlightService
from .services.hotels import HotelService
from .services.restaurants import RestaurantService
from .services.emissions import EmissionsService
from .config.settings import Settings

__all__ = [
    "TravelPlannerAgent",
    "ItineraryGenerator", 
    "WeatherService",
    "FlightService",
    "HotelService",
    "RestaurantService",
    "EmissionsService",
    "Settings",
]
