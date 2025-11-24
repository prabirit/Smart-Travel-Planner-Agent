import types
from unittest.mock import patch
from tools import (
    Weather,
    AirQuality,
    fetch_air_quality,
    estimate_transport_emissions,
    geocode_city,
    fetch_weather,
    fetch_city_time,
)

# --- Dataclass tests ---

def test_weather_dataclass():
    w = Weather(temperature_c=22.5, wind_speed_ms=3.1, humidity=None, description="Sunny")
    assert w.temperature_c == 22.5
    assert w.wind_speed_ms == 3.1
    assert w.humidity is None
    assert w.description == "Sunny"


def test_airquality_dataclass():
    aq = AirQuality(pm25=12.3, pm10=25.0, source="OpenAQ")
    assert aq.pm25 == 12.3
    assert aq.pm10 == 25.0
    assert aq.source == "OpenAQ"

# --- fetch_air_quality tests ---

@patch("requests.get")
def test_fetch_air_quality_success(mock_get):
    mock_resp = types.SimpleNamespace()
    mock_resp.raise_for_status = lambda: None
    mock_resp.json = lambda: {
        "data": [
            {
                "measurements": [
                    {"parameter": "pm25", "value": 10.0},
                    {"parameter": "pm10", "value": 20.0},
                ]
            }
        ]
    }
    mock_get.return_value = mock_resp
    out = fetch_air_quality("TestCity")
    assert "PM2.5: 10.0" in out
    assert "PM10: 20.0" in out

@patch("requests.get")
def test_fetch_air_quality_no_results(mock_get):
    mock_resp = types.SimpleNamespace()
    mock_resp.raise_for_status = lambda: None
    mock_resp.json = lambda: {"data": []}
    mock_get.return_value = mock_resp
    out = fetch_air_quality("Nowhere")
    assert out.startswith("No air quality data")

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
