"""Main agent class for Smart Travel Planner."""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from ..config import get_settings
from ..models.travel_models import TravelRequest, Itinerary, Flight, Hotel, Restaurant, WeatherInfo, EmissionsData
from ..services.weather import WeatherService
from ..services.flights import FlightService
from ..services.hotels import HotelService
from ..services.restaurants import RestaurantService
from ..services.emissions import EmissionsService
from ..services.itinerary import ItineraryService
from ..exceptions import SmartTravelPlannerError, ConfigurationError


class TravelPlannerAgent:
    """Main travel planner agent that orchestrates all services."""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = logging.getLogger(__name__)
        
        # Initialize services
        self.weather_service = WeatherService()
        self.flight_service = FlightService()
        self.hotel_service = HotelService()
        self.restaurant_service = RestaurantService()
        self.emissions_service = EmissionsService()
        self.itinerary_service = ItineraryService()
        
        self.logger.info("TravelPlannerAgent initialized")
    
    async def process_request(
        self, 
        travel_request: TravelRequest, 
        features: List[str]
    ) -> Dict[str, Any]:
        """Process travel request and return results."""
        results = {}
        
        try:
            # Process each requested feature
            for feature in features:
                self.logger.info(f"Processing feature: {feature}")
                
                if feature == "itinerary":
                    results["itinerary"] = await self.generate_itinerary(travel_request)
                
                elif feature == "flights":
                    results["flights"] = await self.search_flights(travel_request)
                
                elif feature == "hotels":
                    results["hotels"] = await self.search_hotels(travel_request)
                
                elif feature == "restaurants":
                    results["restaurants"] = await self.search_restaurants(travel_request)
                
                elif feature == "weather":
                    results["weather"] = await self.get_weather(travel_request.destination)
                
                elif feature == "emissions":
                    results["emissions"] = await self.calculate_emissions(travel_request)
                
                else:
                    self.logger.warning(f"Unknown feature: {feature}")
            
            self.logger.info(f"Successfully processed {len(results)} features")
            return results
            
        except Exception as e:
            self.logger.error(f"Error processing request: {e}", exc_info=True)
            raise SmartTravelPlannerError(f"Failed to process travel request: {e}")
    
    async def generate_itinerary(self, travel_request: TravelRequest) -> Itinerary:
        """Generate complete travel itinerary."""
        try:
            self.logger.info(f"Generating itinerary for {travel_request.origin} to {travel_request.destination}")
            
            # Collect data for itinerary generation
            context_data = await self._collect_itinerary_context(travel_request)
            
            # Generate itinerary using the service
            itinerary = await self.itinerary_service.generate_itinerary(
                travel_request=travel_request,
                context=context_data
            )
            
            self.logger.info(f"Generated {len(itinerary.days)}-day itinerary")
            return itinerary
            
        except Exception as e:
            self.logger.error(f"Error generating itinerary: {e}", exc_info=True)
            raise
    
    async def search_flights(self, travel_request: TravelRequest) -> List[Flight]:
        """Search for flights between origin and destination."""
        try:
            self.logger.info(f"Searching flights from {travel_request.origin} to {travel_request.destination}")
            
            flights = await self.flight_service.search_flights(
                origin=travel_request.origin,
                destination=travel_request.destination,
                departure_date=travel_request.start_date,
                travelers=travel_request.travelers
            )
            
            self.logger.info(f"Found {len(flights)} flight options")
            return flights
            
        except Exception as e:
            self.logger.error(f"Error searching flights: {e}", exc_info=True)
            return []
    
    async def search_hotels(self, travel_request: TravelRequest) -> List[Hotel]:
        """Search for hotels in destination."""
        try:
            self.logger.info(f"Searching hotels in {travel_request.destination}")
            
            hotels = await self.hotel_service.search_hotels(
                location=travel_request.destination,
                check_in_date=travel_request.start_date,
                check_out_date=travel_request.end_date,
                travelers=travel_request.travelers
            )
            
            self.logger.info(f"Found {len(hotels)} hotel options")
            return hotels
            
        except Exception as e:
            self.logger.error(f"Error searching hotels: {e}", exc_info=True)
            return []
    
    async def search_restaurants(self, travel_request: TravelRequest) -> List[Restaurant]:
        """Search for restaurants in destination."""
        try:
            self.logger.info(f"Searching restaurants in {travel_request.destination}")
            
            restaurants = await self.restaurant_service.search_restaurants(
                location=travel_request.destination,
                cuisine_types=travel_request.cuisine_preferences
            )
            
            self.logger.info(f"Found {len(restaurants)} restaurant options")
            return restaurants
            
        except Exception as e:
            self.logger.error(f"Error searching restaurants: {e}", exc_info=True)
            return []
    
    async def get_weather(self, location: str) -> Optional[WeatherInfo]:
        """Get weather information for location."""
        try:
            self.logger.info(f"Getting weather for {location}")
            
            weather = await self.weather_service.get_weather(location)
            
            self.logger.info(f"Retrieved weather data: {weather.temperature_celsius}°C")
            return weather
            
        except Exception as e:
            self.logger.error(f"Error getting weather: {e}", exc_info=True)
            return None
    
    async def calculate_emissions(self, travel_request: TravelRequest) -> Optional[EmissionsData]:
        """Calculate transport emissions for the trip."""
        try:
            self.logger.info(f"Calculating emissions for {travel_request.origin} to {travel_request.destination}")
            
            emissions = await self.emissions_service.calculate_trip_emissions(travel_request)
            
            self.logger.info(f"Calculated emissions: {emissions.co2_kg:.2f} kg CO2")
            return emissions
            
        except Exception as e:
            self.logger.error(f"Error calculating emissions: {e}", exc_info=True)
            return None
    
    async def _collect_itinerary_context(self, travel_request: TravelRequest) -> Dict[str, Any]:
        """Collect context data for itinerary generation."""
        context = {}
        
        try:
            # Get weather data
            weather = await self.get_weather(travel_request.destination)
            if weather:
                context["weather"] = weather
            
            # Get flight options
            flights = await self.search_flights(travel_request)
            if flights:
                context["flights"] = flights[:3]  # Limit to top 3 options
            
            # Get hotel options
            hotels = await self.search_hotels(travel_request)
            if hotels:
                context["hotels"] = hotels[:5]  # Limit to top 5 options
            
            # Get restaurant options
            restaurants = await self.search_restaurants(travel_request)
            if restaurants:
                context["restaurants"] = restaurants[:5]  # Limit to top 5 options
            
            # Calculate emissions
            emissions = await self.calculate_emissions(travel_request)
            if emissions:
                context["emissions"] = emissions
            
            self.logger.info(f"Collected context data: {list(context.keys())}")
            return context
            
        except Exception as e:
            self.logger.error(f"Error collecting context: {e}", exc_info=True)
            return context
    
    async def health_check(self) -> Dict[str, bool]:
        """Check health of all services."""
        health_status = {}
        
        services = [
            ("weather", self.weather_service),
            ("flights", self.flight_service),
            ("hotels", self.hotel_service),
            ("restaurants", self.restaurant_service),
            ("emissions", self.emissions_service),
            ("itinerary", self.itinerary_service),
        ]
        
        for name, service in services:
            try:
                health_status[name] = service.health_check()
            except Exception as e:
                self.logger.error(f"Health check failed for {name}: {e}")
                health_status[name] = False
        
        return health_status
    
    def close(self):
        """Close all services and clean up resources."""
        try:
            self.weather_service.close()
            self.flight_service.close()
            self.hotel_service.close()
            self.restaurant_service.close()
            self.emissions_service.close()
            self.itinerary_service.close()
            
            self.logger.info("All services closed")
            
        except Exception as e:
            self.logger.error(f"Error closing services: {e}", exc_info=True)
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.close()
