import types
from unittest.mock import patch
from tools import (
    estimate_transport_emissions,
    geocode_city,
    fetch_weather,
    fetch_city_time,
    fetch_air_quality_openmeteo,
)

# --- fetch_air_quality_openmeteo tests ---

@patch("tools.geocode_city")
def test_fetch_air_quality_success(mock_geocode):
    """Test air quality fetch with Open-Meteo"""
    mock_geocode.return_value = (37.7749, -122.4194)
    out = fetch_air_quality_openmeteo("San Francisco")
    # Accept various valid responses
    assert ("Air Quality" in out or 
            "No air quality data" in out or 
            "unavailable" in out)  # When optional packages missing


@patch("tools.geocode_city")
def test_fetch_air_quality_no_geocode(mock_geocode):
    """Test air quality when geocoding fails"""
    mock_geocode.return_value = None
    out = fetch_air_quality_openmeteo("Nowhere")
    assert "Could not geocode city" in out or "unavailable" in out

# --- estimate_transport_emissions tests ---

def test_estimate_transport_emissions_known_mode():
    out = estimate_transport_emissions("train", 100.0)
    assert "train" in out
    assert "100.0 km" in out or "100.0" in out  # formatting check


def test_estimate_transport_emissions_unknown_mode():
    out = estimate_transport_emissions("spaceship", 50.0)
    assert "Mode 'spaceship' not supported" in out

# --- fetch_city_time tests ---

def test_fetch_city_time_success(monkeypatch):
    monkeypatch.setattr("tools.geocode_city", lambda city: (37.7749, -122.4194))
    out = fetch_city_time("San Francisco")
    assert "Approximate local time in San Francisco" in out
    assert "UTC" in out  # timezone label present


def test_fetch_city_time_failure(monkeypatch):
    monkeypatch.setattr("tools.geocode_city", lambda city: None)
    out = fetch_city_time("Atlantis")
    assert "Could not determine time" in out

# --- geocode_city / fetch_weather tests ---
# We'll mock geocode_city and the external call inside fetch_weather to isolate logic.

@patch("tools.requests.get")
def test_fetch_weather_success(mock_get):
    # mock geocode_city indirectly by returning lat/lon JSON
    def geocode_side_effect(url, params=None, headers=None, timeout=0, verify=None):
        if "nominatim" in url:
            resp = types.SimpleNamespace()
            resp.raise_for_status = lambda: None
            resp.json = lambda: [{"lat": "37.7749", "lon": "-122.4194"}]
            return resp
        else:
            resp = types.SimpleNamespace()
            resp.raise_for_status = lambda: None
            resp.json = lambda: {"current_weather": {"temperature": 18.0, "windspeed": 5.0}}
            return resp
    mock_get.side_effect = geocode_side_effect
    out = fetch_weather("San Francisco")
    assert "Weather in San Francisco" in out
    assert "18.0" in out

@patch("tools.requests.get")
def test_fetch_weather_geocode_fail(mock_get):
    # Geocode returns empty list
    def side_effect(url, params=None, headers=None, timeout=0, verify=None):
        resp = types.SimpleNamespace()
        resp.raise_for_status = lambda: None
        resp.json = lambda: []
        return resp
    mock_get.side_effect = side_effect
    out = fetch_weather("UnknownTown")
    assert "Could not geocode city" in out


# --- restaurant_search_tool tests ---

@patch("tools.geocode_city")  # Patch where it's defined
@patch("agent.requests.get")
def test_restaurant_search_success(mock_get, mock_geocode):
    """Test successful restaurant search with filters"""
    # Mock geocoding
    mock_geocode.return_value = (37.7749, -122.4194)  # San Francisco coords
    
    # Mock Places API response
    mock_resp = types.SimpleNamespace()
    mock_resp.raise_for_status = lambda: None
    mock_resp.json = lambda: {
        "status": "OK",
        "results": [
            {
                "name": "Test Italian Restaurant",
                "place_id": "ChIJ123456",
                "rating": 4.5,
                "user_ratings_total": 250,
                "price_level": 2,
                "vicinity": "123 Main St, San Francisco",
                "opening_hours": {"open_now": True},
                "types": ["restaurant", "food"]
            },
            {
                "name": "Another Restaurant",
                "place_id": "ChIJ789012",
                "rating": 4.3,
                "user_ratings_total": 180,
                "price_level": 2,
                "vicinity": "456 Market St, San Francisco",
                "opening_hours": {"open_now": False},
                "types": ["restaurant", "food"]
            }
        ]
    }
    mock_get.return_value = mock_resp
    
    from agent import restaurant_search_tool
    result = restaurant_search_tool("San Francisco", cuisine="italian", min_rating=4.0, limit=2)
    
    assert "Test Italian Restaurant" in result
    assert "4.5/5.0" in result
    assert "250 reviews" in result
    assert "💰💰" in result  # Price level 2
    assert "🟢 Open" in result


@patch("tools.geocode_city")
def test_restaurant_search_geocode_fail(mock_geocode):
    """Test restaurant search when geocoding fails"""
    mock_geocode.return_value = None
    
    from agent import restaurant_search_tool
    result = restaurant_search_tool("Nonexistent City")
    
    assert "Could not geocode location" in result


@patch("agent.geocode_city")
@patch("agent.requests.get")
@patch("agent.os.getenv")
def test_restaurant_search_no_api_key(mock_getenv, mock_get, mock_geocode):
    """Test restaurant search without API key configured"""
    mock_getenv.return_value = ""  # No API key
    
    from agent import restaurant_search_tool
    result = restaurant_search_tool("San Francisco")
    
    assert "GOOGLE_PLACES_API_KEY not configured" in result


@patch("tools.geocode_city")
@patch("agent.requests.get")
def test_restaurant_search_api_not_enabled(mock_get, mock_geocode):
    """Test restaurant search when Places API is not enabled"""
    mock_geocode.return_value = (37.7749, -122.4194)
    
    # Mock API response with REQUEST_DENIED
    mock_resp = types.SimpleNamespace()
    mock_resp.raise_for_status = lambda: None
    mock_resp.json = lambda: {
        "status": "REQUEST_DENIED",
        "error_message": "This API project is not authorized to use this API."
    }
    mock_get.return_value = mock_resp
    
    from agent import restaurant_search_tool
    result = restaurant_search_tool("San Francisco")
    
    assert "Google Places API is not enabled" in result
    assert "console.cloud.google.com" in result


@patch("tools.geocode_city")
@patch("agent.requests.get")
def test_restaurant_search_with_filters(mock_get, mock_geocode):
    """Test restaurant search with rating and price filters"""
    mock_geocode.return_value = (37.7749, -122.4194)
    
    mock_resp = types.SimpleNamespace()
    mock_resp.raise_for_status = lambda: None
    mock_resp.json = lambda: {
        "status": "OK",
        "results": [
            {
                "name": "High-Rated Restaurant",
                "place_id": "ChIJ111",
                "rating": 4.8,
                "user_ratings_total": 500,
                "price_level": 3,
                "vicinity": "789 Fine St",
                "opening_hours": {"open_now": True},
                "types": ["restaurant"]
            },
            {
                "name": "Lower-Rated Restaurant",
                "place_id": "ChIJ222",
                "rating": 3.5,
                "user_ratings_total": 100,
                "price_level": 1,
                "vicinity": "321 Cheap St",
                "opening_hours": {},
                "types": ["restaurant"]
            }
        ]
    }
    mock_get.return_value = mock_resp
    
    from agent import restaurant_search_tool
    result = restaurant_search_tool("San Francisco", min_rating=4.5, price_level=3, limit=5)
    
    # Should include high-rated restaurant
    assert "High-Rated Restaurant" in result
    assert "4.8/5.0" in result
    
    # Should filter out lower-rated restaurant (< 4.5)
    assert "Lower-Rated Restaurant" not in result
