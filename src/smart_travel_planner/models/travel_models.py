"""Travel data models for Smart Travel Planner."""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum


class TransportMode(Enum):
    """Transportation modes for emissions calculation."""
    CAR_GASOLINE = "car_gasoline"
    CAR_ELECTRIC = "car_electric"
    TRAIN = "train"
    BUS = "bus"
    FLIGHT = "flight"
    WALKING = "walking"
    CYCLING = "cycling"


class PriceLevel(Enum):
    """Restaurant price levels."""
    CHEAP = "1"
    MODERATE = "2"
    EXPENSIVE = "3"
    VERY_EXPENSIVE = "4"


@dataclass
class Location:
    """Location information."""
    name: str
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    iata_code: Optional[str] = None  # For airports
    
    def __str__(self) -> str:
        return f"{self.name}" + (f", {self.country}" if self.country else "")


@dataclass
class Flight:
    """Flight information."""
    airline: str
    flight_number: str
    departure_airport: str
    arrival_airport: str
    departure_time: datetime
    arrival_time: datetime
    duration_minutes: int
    stops: int
    price: float
    currency: str = "USD"
    aircraft_type: Optional[str] = None
    
    @property
    def duration_hours(self) -> float:
        """Duration in hours."""
        return self.duration_minutes / 60
    
    @property
    def is_direct(self) -> bool:
        """Check if flight is direct."""
        return self.stops == 0


@dataclass
class Hotel:
    """Hotel information."""
    name: str
    address: str
    stars: Optional[int] = None
    price_per_night: Optional[float] = None
    currency: str = "USD"
    rating: Optional[float] = None
    distance_km: Optional[float] = None
    amenities: List[str] = field(default_factory=list)
    hotel_id: Optional[str] = None  # Amadeus hotel ID
    check_in_date: Optional[date] = None
    check_out_date: Optional[date] = None
    
    @property
    def price_range_display(self) -> str:
        """Display price range based on stars if price not available."""
        if self.price_per_night:
            return f"${self.price_per_night:.2f} {self.currency}/night"
        
        if not self.stars:
            return "Price not available"
        
        # Heuristic price ranges based on stars
        price_ranges = {
            1: "$20-50",
            2: "$50-100", 
            3: "$100-200",
            4: "$200-400",
            5: "$400+"
        }
        return price_ranges.get(self.stars, "Price not available")


@dataclass
class Restaurant:
    """Restaurant information."""
    name: str
    address: str
    cuisine_type: Optional[str] = None
    rating: Optional[float] = None
    price_level: Optional[PriceLevel] = None
    review_count: Optional[int] = None
    is_open_now: Optional[bool] = None
    distance_km: Optional[float] = None
    place_id: Optional[str] = None
    
    @property
    def price_display(self) -> str:
        """Display price level as symbols."""
        if not self.price_level:
            return "Price not available"
        
        symbols = {
            PriceLevel.CHEAP: "¢",
            PriceLevel.MODERATE: "$",
            PriceLevel.EXPENSIVE: "$$",
            PriceLevel.VERY_EXPENSIVE: "$$$"
        }
        return symbols[self.price_level]
    
    @property
    def rating_display(self) -> str:
        """Display rating with review count."""
        if not self.rating:
            return "No rating"
        
        base = f"{self.rating:.1f} stars"
        if self.review_count:
            base += f" ({self.review_count} reviews)"
        return base


@dataclass
class WeatherInfo:
    """Weather information."""
    temperature_celsius: float
    humidity_percent: int
    description: str
    wind_speed_kmh: float
    pressure_hpa: float
    visibility_km: Optional[float] = None
    uv_index: Optional[float] = None
    timestamp: Optional[datetime] = None
    
    @property
    def temperature_fahrenheit(self) -> float:
        """Temperature in Fahrenheit."""
        return (self.temperature_celsius * 9/5) + 32
    
    @property
    def feels_like_celsius(self) -> float:
        """Simple feels-like calculation (wind chill)."""
        if self.temperature_celsius <= 10 and self.wind_speed_kmh > 5:
            # Wind chill formula
            return 13.12 + 0.6215 * self.temperature_celsius - 11.37 * (self.wind_speed_kmh ** 0.16) + 0.3965 * self.temperature_celsius * (self.wind_speed_kmh ** 0.16)
        return self.temperature_celsius


@dataclass
class AirQualityInfo:
    """Air quality information."""
    aqi: Optional[int] = None  # Air Quality Index
    pm25: Optional[float] = None  # PM2.5 concentration
    pm10: Optional[float] = None  # PM10 concentration
    o3: Optional[float] = None  # Ozone concentration
    no2: Optional[float] = None  # Nitrogen dioxide
    so2: Optional[float] = None  # Sulfur dioxide
    co: Optional[float] = None  # Carbon monoxide
    
    @property
    def aqi_level(self) -> str:
        """Get AQI level description."""
        if not self.aqi:
            return "Unknown"
        
        if self.aqi <= 50:
            return "Good"
        elif self.aqi <= 100:
            return "Moderate"
        elif self.aqi <= 150:
            return "Unhealthy for Sensitive Groups"
        elif self.aqi <= 200:
            return "Unhealthy"
        elif self.aqi <= 300:
            return "Very Unhealthy"
        else:
            return "Hazardous"


@dataclass
class EmissionsData:
    """Transport emissions data."""
    mode: TransportMode
    distance_km: float
    co2_kg: float
    co2_per_km: float
    
    @property
    def co2_lb(self) -> float:
        """CO2 emissions in pounds."""
        return self.co2_kg * 2.20462
    
    @property
    def sustainability_score(self) -> str:
        """Get sustainability rating based on emissions."""
        if self.co2_per_km <= 0.05:
            return "Excellent"
        elif self.co2_per_km <= 0.1:
            return "Good"
        elif self.co2_per_km <= 0.2:
            return "Moderate"
        elif self.co2_per_km <= 0.3:
            return "Poor"
        else:
            return "Very Poor"


@dataclass
class ItineraryDay:
    """Single day of itinerary."""
    day: int
    date: date
    activities: List[str] = field(default_factory=list)
    accommodation: Optional[Hotel] = None
    transportation: Optional[str] = None
    meals: List[Restaurant] = field(default_factory=list)
    estimated_emissions: Optional[EmissionsData] = None
    notes: Optional[str] = None


@dataclass
class Itinerary:
    """Complete travel itinerary."""
    origin: Location
    destination: Location
    start_date: date
    end_date: date
    days: List[ItineraryDay] = field(default_factory=list)
    total_cost_usd: Optional[float] = None
    total_emissions_kg_co2: Optional[float] = None
    sustainability_rating: Optional[str] = None
    
    @property
    def duration_days(self) -> int:
        """Trip duration in days."""
        return (self.end_date - self.start_date).days + 1
    
    @property
    def total_emissions_lb_co2(self) -> Optional[float]:
        """Total emissions in pounds."""
        if self.total_emissions_kg_co2:
            return self.total_emissions_kg_co2 * 2.20462
        return None


@dataclass
class TravelRequest:
    """Travel planning request."""
    origin: str
    destination: str
    start_date: date
    end_date: date
    travelers: int = 1
    budget_usd: Optional[float] = None
    preferred_transport_modes: List[TransportMode] = field(default_factory=list)
    sustainability_preference: str = "moderate"  # low, moderate, high
    accommodation_preference: Optional[str] = None
    cuisine_preferences: List[str] = field(default_factory=list)
    activity_preferences: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Post-initialization validation."""
        if self.start_date > self.end_date:
            raise ValueError("Start date must be before end date")
        
        if self.travelers < 1:
            raise ValueError("Number of travelers must be at least 1")
        
        if self.budget_usd is not None and self.budget_usd < 0:
            raise ValueError("Budget cannot be negative")
