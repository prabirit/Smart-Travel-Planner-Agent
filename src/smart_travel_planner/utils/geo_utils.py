"""Geographic utilities for Smart Travel Planner."""

import math
from typing import Optional, Tuple
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderUnavailable, GeocoderServiceError

from ..config import get_settings
from ..exceptions import ValidationError, APIError
from .validators import validate_coordinates


def calculate_distance(
    lat1: float, lon1: float, lat2: float, lon2: float, unit: str = "km"
) -> float:
    """Calculate distance between two geographic points."""
    # Validate coordinates
    validate_coordinates(lat1, lon1)
    validate_coordinates(lat2, lon2)
    
    try:
        # Use geopy for accurate distance calculation
        distance = geodesic((lat1, lon1), (lat2, lon2))
        
        if unit.lower() == "km":
            return distance.kilometers
        elif unit.lower() == "mi":
            return distance.miles
        elif unit.lower() == "m":
            return distance.meters
        else:
            raise ValueError(f"Unsupported unit: {unit}")
            
    except Exception as e:
        raise APIError(f"Distance calculation failed: {e}")


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance using Haversine formula (fallback method)."""
    validate_coordinates(lat1, lon1)
    validate_coordinates(lat2, lon2)
    
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    # Earth's radius in kilometers
    r = 6371
    return c * r


def geocode_location(location: str) -> Tuple[float, float]:
    """Geocode a location string to coordinates."""
    if not isinstance(location, str):
        raise ValidationError("Location must be a string")
    
    try:
        # Use Nominatim (free, no API key required)
        geolocator = Nominatim(user_agent="smart-travel-planner")
        location_data = geolocator.geocode(location)
        
        if not location_data:
            raise ValidationError(f"Location not found: {location}")
        
        return location_data.latitude, location_data.longitude
        
    except GeocoderUnavailable:
        raise APIError("Geocoding service temporarily unavailable")
    except GeocoderServiceError as e:
        raise APIError(f"Geocoding service error: {e}")
    except Exception as e:
        raise APIError(f"Geocoding failed: {e}")


def reverse_geocode(lat: float, lon: float) -> Optional[str]:
    """Reverse geocode coordinates to location name."""
    validate_coordinates(lat, lon)
    
    try:
        geolocator = Nominatim(user_agent="smart-travel-planner")
        location_data = geolocator.reverse((lat, lon))
        
        if location_data:
            return location_data.address
        
        return None
        
    except Exception:
        # Silently fail reverse geocoding as it's not critical
        return None


def approximate_local_time(latitude: float, longitude: float) -> str:
    """Approximate local time based on longitude."""
    validate_coordinates(latitude, longitude)
    
    # Rough timezone calculation based on longitude
    # Each 15 degrees of longitude is approximately 1 hour
    timezone_offset = round(longitude / 15)
    
    from datetime import datetime, timedelta
    import pytz
    
    try:
        # Get current UTC time
        utc_time = datetime.utcnow()
        
        # Apply timezone offset
        local_time = utc_time + timedelta(hours=timezone_offset)
        
        return local_time.strftime("%Y-%m-%d %H:%M:%S (UTC%+d)" % timezone_offset)
        
    except Exception:
        # Fallback to UTC time
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S (UTC)")


def is_within_radius(
    center_lat: float, center_lon: float,
    point_lat: float, point_lon: float,
    radius_km: float
) -> bool:
    """Check if a point is within a specified radius of a center point."""
    distance = calculate_distance(center_lat, center_lon, point_lat, point_lon)
    return distance <= radius_km


def find_points_within_radius(
    center_lat: float, center_lon: float,
    points: list[Tuple[float, float]],
    radius_km: float
) -> list[Tuple[float, float, float]]:
    """Find all points within a radius, returning (lat, lon, distance)."""
    results = []
    
    for point_lat, point_lon in points:
        try:
            distance = calculate_distance(center_lat, center_lon, point_lat, point_lon)
            if distance <= radius_km:
                results.append((point_lat, point_lon, distance))
        except Exception:
            # Skip invalid points
            continue
    
    # Sort by distance
    results.sort(key=lambda x: x[2])
    return results


def bounding_box(
    center_lat: float, center_lon: float,
    radius_km: float
) -> Tuple[float, float, float, float]:
    """Calculate bounding box for a center point and radius."""
    validate_coordinates(center_lat, center_lon)
    
    # Approximate conversion: 1 degree latitude = 111 km
    # 1 degree longitude = 111 km * cos(latitude)
    lat_delta = radius_km / 111.0
    lon_delta = radius_km / (111.0 * math.cos(math.radians(center_lat)))
    
    min_lat = center_lat - lat_delta
    max_lat = center_lat + lat_delta
    min_lon = center_lon - lon_delta
    max_lon = center_lon + lon_delta
    
    return min_lat, min_lon, max_lat, max_lon


def extract_country_from_location(location: str) -> Optional[str]:
    """Extract country name from location string."""
    if not isinstance(location, str):
        return None
    
    # Common country indicators
    country_indicators = [
        "USA", "United States", "America",
        "UK", "United Kingdom", "Britain", "England",
        "Canada", "Australia", "France", "Germany",
        "Italy", "Spain", "Japan", "China", "India",
        "Brazil", "Mexico", "Argentina", "Russia"
    ]
    
    location_upper = location.upper()
    
    for country in country_indicators:
        if country.upper() in location_upper:
            return country
    
    return None


def normalize_location_name(location: str) -> str:
    """Normalize location name for consistent processing."""
    if not isinstance(location, str):
        return ""
    
    # Remove extra whitespace and standardize
    normalized = " ".join(location.strip().split())
    
    # Common abbreviations
    abbreviations = {
        "USA": "United States",
        "UK": "United Kingdom",
        "US": "United States",
        "U.S.A.": "United States",
        "U.K.": "United Kingdom",
    }
    
    for abbr, full in abbreviations.items():
        if normalized.upper() == abbr.upper():
            normalized = full
    
    return normalized


def validate_location_coordinates(location: str) -> Tuple[float, float]:
    """Validate and geocode a location, returning coordinates."""
    try:
        lat, lon = geocode_location(location)
        validate_coordinates(lat, lon)
        return lat, lon
    except Exception as e:
        raise ValidationError(f"Invalid location: {location}. {str(e)}")
