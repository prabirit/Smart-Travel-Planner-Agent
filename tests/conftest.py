"""Pytest configuration and fixtures for Smart Travel Planner tests."""

import pytest
from unittest.mock import Mock, patch
from pathlib import Path
import tempfile
import os

from src.smart_travel_planner.config.settings import Settings


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    settings = Settings()
    settings.environment = "test"
    settings.debug = True
    settings.cache.enabled = False  # Disable caching in tests
    settings.security.ssl_verify = False
    settings.api.google_api_key = "test-google-key"
    settings.api.amadeus_api_key = "test-amadeus-key"
    settings.api.amadeus_api_secret = "test-amadeus-secret"
    return settings


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("AMADEUS_API_KEY", "test-amadeus-key")
    monkeypatch.setenv("AMADEUS_API_SECRET", "test-amadeus-secret")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")


@pytest.fixture
def sample_weather_data():
    """Sample weather data for testing."""
    return {
        "temperature_celsius": 22.5,
        "humidity_percent": 65,
        "description": "Partly cloudy",
        "wind_speed_kmh": 15.2,
        "pressure_hpa": 1013.25,
        "visibility_km": 10.0,
        "uv_index": 5.0
    }


@pytest.fixture
def sample_flight_data():
    """Sample flight data for testing."""
    return {
        "airline": "Test Airlines",
        "flight_number": "TA123",
        "departure_airport": "SFO",
        "arrival_airport": "LAX",
        "departure_time": "2024-12-01T10:00:00",
        "arrival_time": "2024-12-01T12:30:00",
        "duration_minutes": 150,
        "stops": 0,
        "price": 299.99,
        "currency": "USD"
    }


@pytest.fixture
def sample_hotel_data():
    """Sample hotel data for testing."""
    return {
        "name": "Test Hotel",
        "address": "123 Test St, Test City",
        "stars": 4,
        "price_per_night": 150.0,
        "currency": "USD",
        "rating": 4.2,
        "distance_km": 2.5,
        "amenities": ["WiFi", "Pool", "Gym"]
    }


@pytest.fixture
def sample_restaurant_data():
    """Sample restaurant data for testing."""
    return {
        "name": "Test Restaurant",
        "address": "456 Food Ave, Test City",
        "cuisine_type": "Italian",
        "rating": 4.5,
        "price_level": "2",
        "review_count": 128,
        "is_open_now": True,
        "distance_km": 1.2
    }


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for testing."""
    client = Mock()
    client.get.return_value = {"status": "success"}
    client.post.return_value = {"status": "success"}
    client.request.return_value = {"status": "success"}
    return client


@pytest.fixture(autouse=True)
def setup_test_environment(mock_env_vars, mock_settings):
    """Setup test environment for all tests."""
    with patch('src.smart_travel_planner.config.settings.get_settings', return_value=mock_settings):
        yield


@pytest.fixture
def mock_cache():
    """Mock cache manager for testing."""
    cache = Mock()
    cache.get.return_value = None
    cache.set.return_value = None
    cache.delete.return_value = True
    cache.clear.return_value = None
    cache.size.return_value = 0
    return cache


@pytest.fixture
def mock_geopy():
    """Mock geopy for testing."""
    with patch('src.smart_travel_planner.utils.geo_utils.geodesic') as mock_geodesic:
        mock_distance = Mock()
        mock_distance.kilometers = 100.0
        mock_distance.miles = 62.14
        mock_distance.meters = 100000.0
        mock_geodesic.return_value = mock_distance
        yield mock_geodesic


@pytest.fixture
def mock_nominatim():
    """Mock Nominatim geocoder for testing."""
    with patch('src.smart_travel_planner.utils.geo_utils.Nominatim') as mock_nominatim_class:
        mock_geolocator = Mock()
        mock_location = Mock()
        mock_location.latitude = 37.7749
        mock_location.longitude = -122.4194
        mock_location.address = "San Francisco, CA, USA"
        
        mock_geolocator.geocode.return_value = mock_location
        mock_geolocator.reverse.return_value = mock_location
        mock_nominatim_class.return_value = mock_geolocator
        
        yield mock_geolocator


@pytest.fixture
def sample_emissions_data():
    """Sample emissions data for testing."""
    return {
        "mode": "car_gasoline",
        "distance_km": 100.0,
        "co2_kg": 20.5,
        "co2_per_km": 0.205
    }


@pytest.fixture
def mock_openmeteo():
    """Mock Open-Meteo API for testing."""
    with patch('src.smart_travel_planner.services.weather.openmeteo_requests') as mock_openmeteo:
        mock_session = Mock()
        mock_response = Mock()
        mock_response.json.return_value = {
            "current": {
                "temperature_2m": 22.5,
                "relative_humidity_2m": 65,
                "weather_code": 1001,
                "wind_speed_10m": 15.2,
                "pressure_msl": 1013.25,
                "visibility": 10000,
                "uv_index": 5.0
            }
        }
        mock_session.get.return_value = mock_response
        mock_openmeteo.WeatherSession.return_value = mock_session
        yield mock_openmeteo


@pytest.fixture
def mock_amadeus_client():
    """Mock Amadeus API client for testing."""
    with patch('src.smart_travel_planner.services.flights.Amadeus') as mock_amadeus:
        mock_client = Mock()
        mock_amadeus.Client.return_value = mock_client
        
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
                                        "iataCode": "SFO",
                                        "at": "2024-12-01T10:00:00"
                                    },
                                    "arrival": {
                                        "iataCode": "LAX", 
                                        "at": "2024-12-01T12:30:00"
                                    },
                                    "carrierCode": "TA",
                                    "flightNumber": "123"
                                }
                            ]
                        }
                    ],
                    "price": {
                        "total": "299.99",
                        "currency": "USD"
                    }
                }
            ]
        }
        
        mock_client.reference_data.locations.get.return_value = {
            "data": [
                {"iataCode": "SFO", "name": "San Francisco"},
                {"iataCode": "LAX", "name": "Los Angeles"}
            ]
        }
        
        mock_client.shopping.flight_offers.get.return_value = mock_flight_offers.get.return_value
        mock_client.shopping.hotel_offers.get.return_value = {
            "data": [
                {
                    "hotel": {
                        "name": "Test Hotel",
                        "address": {"line1": "123 Test St"},
                        "rating": 4.2
                    },
                    "offers": [
                        {
                            "price": {
                                "total": "150.00",
                                "currency": "USD"
                            }
                        }
                    ]
                }
            ]
        }
        
        yield mock_client


@pytest.fixture
def mock_google_places():
    """Mock Google Places API for testing."""
    with patch('src.smart_travel_planner.services.restaurants.requests.get') as mock_get:
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [
                {
                    "name": "Test Restaurant",
                    "vicinity": "456 Food Ave, Test City",
                    "rating": 4.5,
                    "price_level": 2,
                    "user_ratings_total": 128,
                    "opening_hours": {"open_now": True},
                    "place_id": "test_place_id"
                }
            ],
            "status": "OK"
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        yield mock_get


@pytest.fixture
def mock_gemini():
    """Mock Google Gemini API for testing."""
    with patch('src.smart_travel_planner.services.itinerary.genai') as mock_genai:
        mock_model = Mock()
        mock_response = Mock()
        mock_response.text = """
        Day 1: Arrive in San Francisco, check into hotel, explore Fisherman's Wharf
        Day 2: Visit Golden Gate Bridge, Alcatraz tour, dinner at Italian restaurant
        Day 3: Day trip to Napa Valley, wine tasting, return to city
        """
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        yield mock_genai
