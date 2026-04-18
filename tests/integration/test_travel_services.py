"""Integration tests for travel services."""

import pytest
from unittest.mock import patch, Mock
from datetime import date, timedelta

from src.smart_travel_planner.services.weather import WeatherService
from src.smart_travel_planner.services.flights import FlightService
from src.smart_travel_planner.services.hotels import HotelService
from src.smart_travel_planner.services.restaurants import RestaurantService
from src.smart_travel_planner.services.emissions import EmissionsService
from src.smart_travel_planner.models.travel_models import Location, Flight, Hotel, Restaurant


class TestWeatherServiceIntegration:
    """Integration tests for WeatherService."""
    
    @patch('src.smart_travel_planner.services.weather.openmeteo_requests')
    def test_get_weather_data_success(self, mock_openmeteo, sample_weather_data):
        """Test successful weather data retrieval."""
        # Setup mock
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "current": {
                "temperature_2m": sample_weather_data["temperature_celsius"],
                "relative_humidity_2m": sample_weather_data["humidity_percent"],
                "weather_code": 1001,  # Partly cloudy
                "wind_speed_10m": sample_weather_data["wind_speed_kmh"],
                "pressure_msl": sample_weather_data["pressure_hpa"],
                "visibility": sample_weather_data["visibility_km"] * 1000,  # Convert to meters
                "uv_index": sample_weather_data["uv_index"]
            }
        }
        mock_session.get.return_value = mock_response
        mock_openmeteo.WeatherSession.return_value = mock_session
        
        # Test service
        with WeatherService() as service:
            weather = service.get_weather("San Francisco")
            
            assert weather.temperature_celsius == sample_weather_data["temperature_celsius"]
            assert weather.humidity_percent == sample_weather_data["humidity_percent"]
            assert weather.wind_speed_kmh == sample_weather_data["wind_speed_kmh"]
            assert weather.pressure_hpa == sample_weather_data["pressure_hpa"]
    
    @patch('src.smart_travel_planner.services.weather.openmeteo_requests')
    def test_get_weather_data_fallback(self, mock_openmeteo):
        """Test weather data fallback when Open-Meteo is unavailable."""
        mock_openmeteo.WeatherSession.side_effect = ImportError("Open-Meteo not available")
        
        with patch('src.smart_travel_planner.services.weather.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "main": {
                    "temp": 22.5,
                    "humidity": 65,
                    "pressure": 1013.25
                },
                "weather": [{"description": "partly cloudy"}],
                "wind": {"speed": 4.2},  # m/s to km/h conversion
                "visibility": 10000  # meters
            }
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            with WeatherService() as service:
                weather = service.get_weather("San Francisco")
                
                assert weather.temperature_celsius == 22.5
                assert weather.humidity_percent == 65


class TestFlightServiceIntegration:
    """Integration tests for FlightService."""
    
    @patch('src.smart_travel_planner.services.flights.Amadeus')
    def test_search_flights_success(self, mock_amadeus, sample_flight_data):
        """Test successful flight search."""
        # Setup mock
        mock_client = Mock()
        mock_amadeus.Client.return_value = mock_client
        
        # Mock location lookup
        mock_client.reference_data.locations.get.return_value = {
            "data": [
                {"iataCode": "SFO", "name": "San Francisco"},
                {"iataCode": "LAX", "name": "Los Angeles"}
            ]
        }
        
        # Mock flight offers
        mock_flight_offers = Mock()
        mock_flight_offers.get.return_value = {
            "data": [
                {
                    "id": "flight1",
                    "itineraries": [
                        {
                            "segments": [
                                {
                                    "departure": {
                                        "iataCode": sample_flight_data["departure_airport"],
                                        "at": sample_flight_data["departure_time"]
                                    },
                                    "arrival": {
                                        "iataCode": sample_flight_data["arrival_airport"],
                                        "at": sample_flight_data["arrival_time"]
                                    },
                                    "carrierCode": "TA",
                                    "flightNumber": sample_flight_data["flight_number"],
                                    "duration": f"PT{sample_flight_data['duration_minutes']}M"
                                }
                            ]
                        }
                    ],
                    "price": {
                        "total": str(sample_flight_data["price"]),
                        "currency": sample_flight_data["currency"]
                    }
                }
            ]
        }
        mock_client.shopping.flight_offers = mock_flight_offers
        
        with FlightService() as service:
            flights = service.search_flights(
                origin="San Francisco",
                destination="Los Angeles", 
                departure_date="2024-12-01"
            )
            
            assert len(flights) == 1
            flight = flights[0]
            assert flight.airline == sample_flight_data["airline"]
            assert flight.flight_number == sample_flight_data["flight_number"]
            assert flight.price == sample_flight_data["price"]
    
    @patch('src.smart_travel_planner.services.flights.Amadeus')
    def test_search_flights_no_credentials(self, mock_amadeus):
        """Test flight search without Amadeus credentials."""
        mock_amadeus.Client.side_effect = Exception("No API credentials")
        
        with FlightService() as service:
            flights = service.search_flights(
                origin="San Francisco",
                destination="Los Angeles",
                departure_date="2024-12-01"
            )
            
            # Should return empty list when no credentials
            assert flights == []


class TestHotelServiceIntegration:
    """Integration tests for HotelService."""
    
    @patch('src.smart_travel_planner.services.hotels.requests.get')
    def test_search_hotels_osm_success(self, mock_get, sample_hotel_data):
        """Test hotel search using OpenStreetMap."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "elements": [
                {
                    "tags": {
                        "name": sample_hotel_data["name"],
                        "tourism": "hotel",
                        "stars": str(sample_hotel_data["stars"]),
                        "addr:full": sample_hotel_data["address"]
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with HotelService() as service:
            hotels = service.search_hotels("San Francisco", radius_km=5)
            
            assert len(hotels) == 1
            hotel = hotels[0]
            assert hotel.name == sample_hotel_data["name"]
            assert hotel.stars == sample_hotel_data["stars"]
    
    @patch('src.smart_travel_planner.services.hotels.Amadeus')
    def test_search_hotels_amadeus_success(self, mock_amadeus, sample_hotel_data):
        """Test hotel search using Amadeus API."""
        mock_client = Mock()
        mock_amadeus.Client.return_value = mock_client
        
        # Mock hotel discovery
        mock_client.reference_data.locations.hotels.by_geocode.get.return_value = {
            "data": [
                {"hotelId": "hotel1"}
            ]
        }
        
        # Mock hotel offers
        mock_client.shopping.hotel_offers.get.return_value = {
            "data": [
                {
                    "hotel": {
                        "name": sample_hotel_data["name"],
                        "address": {"line1": sample_hotel_data["address"]},
                        "rating": sample_hotel_data["rating"]
                    },
                    "offers": [
                        {
                            "price": {
                                "total": str(sample_hotel_data["price_per_night"]),
                                "currency": sample_hotel_data["currency"]
                            }
                        }
                    ]
                }
            ]
        }
        
        with HotelService() as service:
            hotels = service.search_hotels("San Francisco", use_amadeus=True)
            
            assert len(hotels) == 1
            hotel = hotels[0]
            assert hotel.name == sample_hotel_data["name"]
            assert hotel.price_per_night == sample_hotel_data["price_per_night"]


class TestRestaurantServiceIntegration:
    """Integration tests for RestaurantService."""
    
    @patch('src.smart_travel_planner.services.restaurants.requests.get')
    def test_search_restaurants_success(self, mock_get, sample_restaurant_data):
        """Test restaurant search using Google Places API."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "name": sample_restaurant_data["name"],
                    "vicinity": sample_restaurant_data["address"],
                    "rating": sample_restaurant_data["rating"],
                    "price_level": sample_restaurant_data["price_level"],
                    "user_ratings_total": sample_restaurant_data["review_count"],
                    "opening_hours": {"open_now": sample_restaurant_data["is_open_now"]},
                    "place_id": "test_place_id"
                }
            ],
            "status": "OK"
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with RestaurantService() as service:
            restaurants = service.search_restaurants(
                location="San Francisco",
                cuisine="Italian",
                min_rating=4.0
            )
            
            assert len(restaurants) == 1
            restaurant = restaurants[0]
            assert restaurant.name == sample_restaurant_data["name"]
            assert restaurant.rating == sample_restaurant_data["rating"]
    
    @patch('src.smart_travel_planner.services.restaurants.requests.get')
    def test_search_restaurants_no_api_key(self, mock_get):
        """Test restaurant search without API key."""
        mock_get.side_effect = Exception("API key required")
        
        with RestaurantService() as service:
            restaurants = service.search_restaurants("San Francisco")
            
            # Should return empty list when no API key
            assert restaurants == []


class TestEmissionsServiceIntegration:
    """Integration tests for EmissionsService."""
    
    def test_calculate_emissions_success(self, sample_emissions_data):
        """Test emissions calculation."""
        with EmissionsService() as service:
            emissions = service.calculate_emissions(
                mode="car_gasoline",
                distance_km=100.0
            )
            
            assert emissions.mode.value == "car_gasoline"
            assert emissions.distance_km == 100.0
            assert emissions.co2_kg > 0
            assert emissions.co2_per_km > 0
    
    def test_calculate_emissions_invalid_mode(self):
        """Test emissions calculation with invalid mode."""
        with EmissionsService() as service:
            with pytest.raises(Exception):
                service.calculate_emissions(mode="invalid_mode", distance_km=100.0)


class TestServiceHealthChecks:
    """Integration tests for service health checks."""
    
    def test_weather_service_health_check(self):
        """Test WeatherService health check."""
        with WeatherService() as service:
            health = service.health_check()
            assert isinstance(health, bool)
    
    def test_flight_service_health_check(self):
        """Test FlightService health check."""
        with FlightService() as service:
            health = service.health_check()
            assert isinstance(health, bool)
    
    def test_hotel_service_health_check(self):
        """Test HotelService health check."""
        with HotelService() as service:
            health = service.health_check()
            assert isinstance(health, bool)
    
    def test_restaurant_service_health_check(self):
        """Test RestaurantService health check."""
        with RestaurantService() as service:
            health = service.health_check()
            assert isinstance(health, bool)
    
    def test_emissions_service_health_check(self):
        """Test EmissionsService health check."""
        with EmissionsService() as service:
            health = service.health_check()
            assert isinstance(health, bool)


class TestServiceIntegration:
    """Integration tests for service interactions."""
    
    @patch('src.smart_travel_planner.services.weather.openmeteo_requests')
    @patch('src.smart_travel_planner.services.flights.Amadeus')
    @patch('src.smart_travel_planner.services.hotels.Amadeus')
    @patch('src.smart_travel_planner.services.restaurants.requests.get')
    def test_complete_travel_planning(self, mock_restaurants, mock_amadeus_hotels, 
                                     mock_amadeus_flights, mock_openmeteo):
        """Test complete travel planning workflow."""
        # Setup all mocks
        mock_openmeteo.WeatherSession.return_value.get.return_value.json.return_value = {
            "current": {"temperature_2m": 22.5, "relative_humidity_2m": 65}
        }
        
        mock_amadeus_flights.Client.return_value.shopping.flight_offers.get.return_value = {
            "data": [{"id": "flight1", "price": {"total": "299.99"}}]
        }
        
        mock_amadeus_hotels.Client.return_value.shopping.hotel_offers.get.return_value = {
            "data": [{"hotel": {"name": "Test Hotel"}}]
        }
        
        mock_restaurants.return_value.json.return_value = {
            "results": [{"name": "Test Restaurant"}], "status": "OK"
        }
        
        # Test complete workflow
        with WeatherService() as weather_service, \
             FlightService() as flight_service, \
             HotelService() as hotel_service, \
             RestaurantService() as restaurant_service:
            
            # Get weather
            weather = weather_service.get_weather("San Francisco")
            assert weather.temperature_celsius == 22.5
            
            # Search flights
            flights = flight_service.search_flights("SFO", "LAX", "2024-12-01")
            assert len(flights) > 0
            
            # Search hotels
            hotels = hotel_service.search_hotels("San Francisco", use_amadeus=True)
            assert len(hotels) > 0
            
            # Search restaurants
            restaurants = restaurant_service.search_restaurants("San Francisco")
            assert len(restaurants) > 0
