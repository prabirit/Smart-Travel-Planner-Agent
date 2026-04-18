"""Input validation utilities for Smart Travel Planner."""

import re
from datetime import datetime, date
from typing import Optional, List, Union

from ..exceptions import ValidationError


def validate_location(location: str) -> str:
    """Validate location string."""
    if not location or not isinstance(location, str):
        raise ValidationError("Location must be a non-empty string", field="location", value=location)
    
    location = location.strip()
    if len(location) < 2:
        raise ValidationError("Location name must be at least 2 characters", field="location", value=location)
    
    if len(location) > 100:
        raise ValidationError("Location name too long (max 100 characters)", field="location", value=location)
    
    # Check for valid characters (letters, spaces, hyphens, apostrophes, commas)
    if not re.match(r"^[a-zA-Z\s\-\',]+$", location):
        raise ValidationError("Location contains invalid characters", field="location", value=location)
    
    return location


def validate_date_range(start_date: Union[str, date], end_date: Union[str, date]) -> tuple[date, date]:
    """Validate date range."""
    # Convert string dates to date objects
    if isinstance(start_date, str):
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("Start date must be in YYYY-MM-DD format", field="start_date", value=start_date)
    
    if isinstance(end_date, str):
        try:
            end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("End date must be in YYYY-MM-DD format", field="end_date", value=end_date)
    
    # Validate dates
    today = date.today()
    if start_date < today:
        raise ValidationError("Start date cannot be in the past", field="start_date", value=start_date)
    
    if start_date > end_date:
        raise ValidationError("Start date must be before end date", field="start_date", value=start_date)
    
    # Check for reasonable date range (max 1 year in advance)
    max_future_date = today.replace(year=today.year + 1)
    if start_date > max_future_date:
        raise ValidationError("Start date too far in future (max 1 year)", field="start_date", value=start_date)
    
    # Check trip duration (max 30 days)
    trip_duration = (end_date - start_date).days
    if trip_duration > 30:
        raise ValidationError("Trip duration too long (max 30 days)", field="end_date", value=end_date)
    
    return start_date, end_date


def validate_email(email: str) -> str:
    """Validate email address."""
    if not email or not isinstance(email, str):
        raise ValidationError("Email must be a non-empty string", field="email", value=email)
    
    email = email.strip().lower()
    
    # Basic email regex
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, email):
        raise ValidationError("Invalid email format", field="email", value=email)
    
    if len(email) > 254:  # RFC 5321 limit
        raise ValidationError("Email address too long", field="email", value=email)
    
    return email


def validate_phone_number(phone: str) -> str:
    """Validate phone number (basic validation)."""
    if not phone or not isinstance(phone, str):
        raise ValidationError("Phone number must be a non-empty string", field="phone", value=phone)
    
    # Remove common formatting characters
    phone_clean = re.sub(r'[\s\-\(\)\+]', '', phone)
    
    # Check if phone contains only digits
    if not phone_clean.isdigit():
        raise ValidationError("Phone number must contain only digits", field="phone", value=phone)
    
    # Check length (10-15 digits for international numbers)
    if len(phone_clean) < 10 or len(phone_clean) > 15:
        raise ValidationError("Phone number must be 10-15 digits", field="phone", value=phone)
    
    return phone


def validate_travelers(travelers: int) -> int:
    """Validate number of travelers."""
    if not isinstance(travelers, int):
        raise ValidationError("Number of travelers must be an integer", field="travelers", value=travelers)
    
    if travelers < 1:
        raise ValidationError("Number of travelers must be at least 1", field="travelers", value=travelers)
    
    if travelers > 20:
        raise ValidationError("Number of travelers too many (max 20)", field="travelers", value=travelers)
    
    return travelers


def validate_budget(budget: Optional[float]) -> Optional[float]:
    """Validate budget amount."""
    if budget is None:
        return None
    
    if not isinstance(budget, (int, float)):
        raise ValidationError("Budget must be a number", field="budget", value=budget)
    
    if budget < 0:
        raise ValidationError("Budget cannot be negative", field="budget", value=budget)
    
    if budget > 1000000:  # Reasonable upper limit
        raise ValidationError("Budget amount too high", field="budget", value=budget)
    
    return float(budget)


def validate_price_level(price_level: str) -> str:
    """Validate restaurant price level."""
    valid_levels = ["1", "2", "3", "4", "cheap", "moderate", "expensive", "very_expensive"]
    
    if not isinstance(price_level, str):
        raise ValidationError("Price level must be a string", field="price_level", value=price_level)
    
    price_level = price_level.lower().strip()
    
    if price_level not in valid_levels:
        raise ValidationError(f"Price level must be one of: {', '.join(valid_levels)}", field="price_level", value=price_level)
    
    # Map text values to numeric
    level_mapping = {
        "cheap": "1",
        "moderate": "2", 
        "expensive": "3",
        "very_expensive": "4"
    }
    
    return level_mapping.get(price_level, price_level)


def validate_rating(rating: Optional[float]) -> Optional[float]:
    """Validate rating value."""
    if rating is None:
        return None
    
    if not isinstance(rating, (int, float)):
        raise ValidationError("Rating must be a number", field="rating", value=rating)
    
    rating = float(rating)
    
    if rating < 0 or rating > 5:
        raise ValidationError("Rating must be between 0 and 5", field="rating", value=rating)
    
    return rating


def validate_coordinates(latitude: float, longitude: float) -> tuple[float, float]:
    """Validate geographic coordinates."""
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        raise ValidationError("Coordinates must be numbers", field="coordinates")
    
    if latitude < -90 or latitude > 90:
        raise ValidationError("Latitude must be between -90 and 90", field="latitude", value=latitude)
    
    if longitude < -180 or longitude > 180:
        raise ValidationError("Longitude must be between -180 and 180", field="longitude", value=longitude)
    
    return float(latitude), float(longitude)


def validate_iata_code(code: str) -> str:
    """Validate IATA airport code."""
    if not isinstance(code, str):
        raise ValidationError("IATA code must be a string", field="iata_code", value=code)
    
    code = code.upper().strip()
    
    if len(code) != 3:
        raise ValidationError("IATA code must be exactly 3 characters", field="iata_code", value=code)
    
    if not code.isalpha():
        raise ValidationError("IATA code must contain only letters", field="iata_code", value=code)
    
    return code


def sanitize_string(input_string: str, max_length: int = 255) -> str:
    """Sanitize string input."""
    if not isinstance(input_string, str):
        raise ValidationError("Input must be a string")
    
    # Remove potentially harmful characters
    sanitized = re.sub(r'[<>"\']', '', input_string.strip())
    
    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized


def validate_list_items(items: List[str], field_name: str, max_items: int = 10, max_item_length: int = 50) -> List[str]:
    """Validate list of string items."""
    if not isinstance(items, list):
        raise ValidationError(f"{field_name} must be a list", field=field_name)
    
    if len(items) > max_items:
        raise ValidationError(f"{field_name} has too many items (max {max_items})", field=field_name)
    
    validated_items = []
    for i, item in enumerate(items):
        if not isinstance(item, str):
            raise ValidationError(f"{field_name}[{i}] must be a string", field=field_name)
        
        item = sanitize_string(item, max_item_length)
        if item:  # Only add non-empty items
            validated_items.append(item)
    
    return validated_items
