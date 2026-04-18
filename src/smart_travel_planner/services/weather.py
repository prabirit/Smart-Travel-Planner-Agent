"""Weather service for Smart Travel Planner."""

import logging
from typing import Optional
from datetime import datetime

from ..services.base import BaseService
from ..models.travel_models import WeatherInfo, AirQualityInfo
from ..utils.geo_utils import geocode_location
from ..exceptions import WeatherError
from ..config import get_settings

# Optional imports for Open-Meteo
try:
    import openmeteo_requests
    import requests_cache
    import pandas as pd
    from retry_requests import retry
    OPENMETEO_AVAILABLE = True
except ImportError:
    OPENMETEO_AVAILABLE = False

# Fallback imports
import requests
from requests.exceptions import RequestException


class WeatherService(BaseService):
    """Service for retrieving weather and air quality data."""
    
    def __init__(self):
        super().__init__("weather")
        self.settings = get_settings()
        self._openmeteo_session = None
        self._initialize_openmeteo()
    
    def _initialize_openmeteo(self):
        """Initialize Open-Meteo session if available."""
        if not OPENMETEO_AVAILABLE:
            self.logger.info("Open-Meteo not available, will use fallback")
            return
        
        try:
            # Setup the Open-Meteo API session with retry and caching
            cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
            retry_session = retry(cache_session, retries=2, backoff_factor=0.5)
            self._openmeteo_session = openmeteo_requests.WeatherSession(retry_session)
            self.logger.info("Open-Meteo session initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize Open-Meteo: {e}")
            self._openmeteo_session = None
    
    def health_check(self) -> bool:
        """Check if the weather service is healthy."""
        return self._openmeteo_session is not None or bool(self.settings.api.weather_api_key)
    
    async def get_weather(self, location: str) -> WeatherInfo:
        """Get current weather information for a location."""
        try:
            self._log_api_call(f"get_weather({location})")
            
            # Check cache first
            cache_key = f"weather:{location}"
            cached_result = self._cache_get("get_weather", location=location)
            if cached_result:
                self.logger.info(f"Retrieved weather from cache: {location}")
                return cached_result
            
            # Get coordinates for location
            lat, lon = geocode_location(location)
            
            # Try Open-Meteo first
            weather = await self._get_openmeteo_weather(lat, lon)
            
            # Cache the result
            self._cache_set("get_weather", weather, location=location)
            
            return weather
            
        except Exception as e:
            self.logger.error(f"Error getting weather for {location}: {e}", exc_info=True)
            raise WeatherError(f"Failed to get weather data: {e}")
    
    async def get_air_quality(self, location: str) -> Optional[AirQualityInfo]:
        """Get air quality information for a location."""
        try:
            self._log_api_call(f"get_air_quality({location})")
            
            # Check cache first
            cache_key = f"air_quality:{location}"
            cached_result = self._cache_get("get_air_quality", location=location)
            if cached_result:
                self.logger.info(f"Retrieved air quality from cache: {location}")
                return cached_result
            
            # Get coordinates for location
            lat, lon = geocode_location(location)
            
            # Try Open-Meteo air quality
            air_quality = await self._get_openmeteo_air_quality(lat, lon)
            
            # Cache the result
            if air_quality:
                self._cache_set("get_air_quality", air_quality, location=location)
            
            return air_quality
            
        except Exception as e:
            self.logger.error(f"Error getting air quality for {location}: {e}", exc_info=True)
            return None
    
    async def _get_openmeteo_weather(self, lat: float, lon: float) -> WeatherInfo:
        """Get weather data from Open-Meteo API."""
        if not self._openmeteo_session:
            return await self._get_fallback_weather(lat, lon)
        
        try:
            # Define the parameters for the weather request
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "weather_code",
                    "wind_speed_10m",
                    "pressure_msl",
                    "visibility",
                    "uv_index"
                ]
            }
            
            # Make the API request
            responses = self._openmeteo_session.weather(params)
            response = responses[0]  # We're only requesting one location
            
            # Extract current weather data
            current = response.Current()
            
            # Convert weather code to description
            weather_description = self._weather_code_to_description(current.Variables(2).Value())
            
            # Create WeatherInfo object
            weather = WeatherInfo(
                temperature_celsius=current.Variables(0).Value(),
                humidity_percent=int(current.Variables(1).Value()),
                description=weather_description,
                wind_speed_kmh=current.Variables(3).Value(),
                pressure_hpa=current.Variables(4).Value(),
                visibility_km=current.Variables(5).Value() / 1000 if current.Variables(5).Value() else None,
                uv_index=current.Variables(6).Value(),
                timestamp=datetime.utcnow()
            )
            
            self.logger.info(f"Retrieved Open-Meteo weather: {weather.temperature_celsius}°C")
            return weather
            
        except Exception as e:
            self.logger.error(f"Open-Meteo weather request failed: {e}")
            return await self._get_fallback_weather(lat, lon)
    
    async def _get_openmeteo_air_quality(self, lat: float, lon: float) -> Optional[AirQualityInfo]:
        """Get air quality data from Open-Meteo API."""
        if not self._openmeteo_session:
            return None
        
        try:
            # Define the parameters for air quality request
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": [
                    "pm2_5",
                    "pm10",
                    "ozone",
                    "nitrogen_dioxide",
                    "sulphur_dioxide",
                    "carbon_monoxide"
                ]
            }
            
            # Make the API request
            responses = self._openmeteo_session.air_quality(params)
            response = responses[0]
            
            # Extract current air quality data
            current = response.Current()
            
            # Create AirQualityInfo object
            air_quality = AirQualityInfo(
                pm25=current.Variables(0).Value(),
                pm10=current.Variables(1).Value(),
                o3=current.Variables(2).Value(),
                no2=current.Variables(3).Value(),
                so2=current.Variables(4).Value(),
                co=current.Variables(5).Value()
            )
            
            self.logger.info(f"Retrieved Open-Meteo air quality: PM2.5 {air_quality.pm25}")
            return air_quality
            
        except Exception as e:
            self.logger.error(f"Open-Meteo air quality request failed: {e}")
            return None
    
    async def _get_fallback_weather(self, lat: float, lon: float) -> WeatherInfo:
        """Get weather data using OpenWeatherMap API as fallback."""
        if not self.settings.api.weather_api_key:
            raise WeatherError("No weather API key available for fallback")
        
        try:
            # Initialize HTTP client
            client = self._init_http_client("https://api.openweathermap.org/data/2.5")
            
            # Make API request
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.settings.api.weather_api_key,
                "units": "metric"
            }
            
            response = client.get("weather", params=params)
            
            # Parse response
            weather = WeatherInfo(
                temperature_celsius=response["main"]["temp"],
                humidity_percent=response["main"]["humidity"],
                description=response["weather"][0]["description"].title(),
                wind_speed_kmh=response["wind"]["speed"] * 3.6,  # Convert m/s to km/h
                pressure_hpa=response["main"]["pressure"],
                visibility_km=response.get("visibility", 0) / 1000 if response.get("visibility") else None,
                timestamp=datetime.utcnow()
            )
            
            self.logger.info(f"Retrieved fallback weather: {weather.temperature_celsius}°C")
            return weather
            
        except Exception as e:
            self.logger.error(f"Fallback weather request failed: {e}")
            raise WeatherError(f"All weather sources failed: {e}")
    
    def _weather_code_to_description(self, weather_code: int) -> str:
        """Convert Open-Meteo weather code to description."""
        # WMO weather code interpretations
        weather_codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Drizzle light",
            53: "Drizzle moderate",
            55: "Drizzle dense",
            56: "Freezing drizzle light",
            57: "Freezing drizzle dense",
            61: "Rain slight",
            63: "Rain moderate",
            65: "Rain heavy",
            66: "Freezing rain light",
            67: "Freezing rain heavy",
            71: "Snow fall slight",
            73: "Snow fall moderate",
            75: "Snow fall heavy",
            77: "Snow grains",
            80: "Rain showers slight",
            81: "Rain showers moderate",
            82: "Rain showers violent",
            85: "Snow showers slight",
            86: "Snow showers heavy",
            95: "Thunderstorm slight",
            96: "Thunderstorm moderate",
            99: "Thunderstorm with heavy hail",
        }
        
        return weather_codes.get(weather_code, "Unknown weather")
    
    async def get_weather_forecast(self, location: str, days: int = 7) -> list[WeatherInfo]:
        """Get weather forecast for multiple days."""
        try:
            self._log_api_call(f"get_weather_forecast({location}, {days} days)")
            
            # Get coordinates
            lat, lon = geocode_location(location)
            
            if not self._openmeteo_session:
                raise WeatherError("Forecast not available without Open-Meteo")
            
            # Define parameters for forecast request
            params = {
                "latitude": lat,
                "longitude": lon,
                "daily": [
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "weather_code",
                    "wind_speed_10m_max",
                    "pressure_msl_max"
                ],
                "timezone": "auto"
            }
            
            # Make API request
            responses = self._openmeteo_session.weather(params)
            response = responses[0]
            
            # Parse daily data
            daily = response.Daily()
            forecast = []
            
            for i in range(min(days, len(daily.Variables(0).Data))):
                weather_code = daily.Variables(2).Data[i]
                description = self._weather_code_to_description(int(weather_code))
                
                weather = WeatherInfo(
                    temperature_celsius=(daily.Variables(0).Data[i] + daily.Variables(1).Data[i]) / 2,  # Average
                    description=description,
                    wind_speed_kmh=daily.Variables(3).Data[i],
                    pressure_hpa=daily.Variables(4).Data[i],
                    timestamp=datetime.utcnow()
                )
                
                forecast.append(weather)
            
            self.logger.info(f"Retrieved {len(forecast)} day forecast")
            return forecast
            
        except Exception as e:
            self.logger.error(f"Error getting forecast for {location}: {e}", exc_info=True)
            raise WeatherError(f"Failed to get weather forecast: {e}")
