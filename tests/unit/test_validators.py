"""Unit tests for input validation utilities."""

import pytest
from datetime import date, datetime, timedelta

from src.smart_travel_planner.utils.validators import (
    validate_location,
    validate_date_range,
    validate_email,
    validate_phone_number,
    validate_travelers,
    validate_budget,
    validate_price_level,
    validate_rating,
    validate_coordinates,
    validate_iata_code,
    sanitize_string,
    validate_list_items
)
from src.smart_travel_planner.exceptions import ValidationError


class TestLocationValidation:
    """Test cases for location validation."""
    
    def test_valid_location(self):
        """Test valid location inputs."""
        assert validate_location("San Francisco") == "San Francisco"
        assert validate_location("New York, USA") == "New York, USA"
        assert validate_location("Paris") == "Paris"
        assert validate_location("  London  ") == "London"
    
    def test_invalid_location(self):
        """Test invalid location inputs."""
        with pytest.raises(ValidationError) as exc_info:
            validate_location("")
        assert "non-empty string" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_location("A")
        assert "at least 2 characters" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_location("A" * 101)
        assert "too long" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_location("San Francisco123")
        assert "invalid characters" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_location(None)
        assert "non-empty string" in str(exc_info.value)


class TestDateRangeValidation:
    """Test cases for date range validation."""
    
    def test_valid_date_range(self):
        """Test valid date ranges."""
        today = date.today()
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)
        
        # Date objects
        assert validate_date_range(tomorrow, next_week) == (tomorrow, next_week)
        
        # String dates
        future_date = today + timedelta(days=10)
        future_date_str = future_date.strftime("%Y-%m-%d")
        future_date_plus_5 = today + timedelta(days=15)
        future_date_plus_5_str = future_date_plus_5.strftime("%Y-%m-%d")
        
        result = validate_date_range(future_date_str, future_date_plus_5_str)
        assert result == (future_date, future_date_plus_5)
    
    def test_invalid_date_range(self):
        """Test invalid date ranges."""
        today = date.today()
        yesterday = today - timedelta(days=1)
        tomorrow = today + timedelta(days=1)
        
        # Past start date
        with pytest.raises(ValidationError) as exc_info:
            validate_date_range(yesterday, tomorrow)
        assert "cannot be in the past" in str(exc_info.value)
        
        # Start after end
        with pytest.raises(ValidationError) as exc_info:
            validate_date_range(tomorrow, today)
        assert "must be before end date" in str(exc_info.value)
        
        # Invalid format
        with pytest.raises(ValidationError) as exc_info:
            validate_date_range("2024-13-01", "2024-12-01")
        assert "YYYY-MM-DD format" in str(exc_info.value)
        
        # Too far in future
        far_future = today + timedelta(days=400)
        with pytest.raises(ValidationError) as exc_info:
            validate_date_range(far_future, far_future + timedelta(days=1))
        assert "too far in future" in str(exc_info.value)
        
        # Trip too long
        long_trip_end = today + timedelta(days=35)
        with pytest.raises(ValidationError) as exc_info:
            validate_date_range(tomorrow, long_trip_end)
        assert "too long" in str(exc_info.value)


class TestEmailValidation:
    """Test cases for email validation."""
    
    def test_valid_email(self):
        """Test valid email addresses."""
        assert validate_email("test@example.com") == "test@example.com"
        assert validate_email("user.name@domain.co.uk") == "user.name@domain.co.uk"
        assert validate_email("  TEST@EXAMPLE.COM  ") == "test@example.com"
    
    def test_invalid_email(self):
        """Test invalid email addresses."""
        with pytest.raises(ValidationError) as exc_info:
            validate_email("")
        assert "non-empty string" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_email("invalid-email")
        assert "Invalid email format" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_email("@example.com")
        assert "Invalid email format" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_email("test@")
        assert "Invalid email format" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_email("a" * 255 + "@example.com")
        assert "too long" in str(exc_info.value)


class TestPhoneValidation:
    """Test cases for phone number validation."""
    
    def test_valid_phone(self):
        """Test valid phone numbers."""
        assert validate_phone_number("1234567890") == "1234567890"
        assert validate_phone_number("123-456-7890") == "1234567890"
        assert validate_phone_number("(123) 456-7890") == "1234567890"
        assert validate_phone_number("+1 123 456 7890") == "1234567890"
    
    def test_invalid_phone(self):
        """Test invalid phone numbers."""
        with pytest.raises(ValidationError) as exc_info:
            validate_phone_number("")
        assert "non-empty string" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_phone_number("12345")
        assert "10-15 digits" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_phone_number("1234567890123456")
        assert "10-15 digits" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_phone_number("abc-123-4567")
        assert "only digits" in str(exc_info.value)


class TestTravelersValidation:
    """Test cases for travelers validation."""
    
    def test_valid_travelers(self):
        """Test valid number of travelers."""
        assert validate_travelers(1) == 1
        assert validate_travelers(5) == 5
        assert validate_travelers(20) == 20
    
    def test_invalid_travelers(self):
        """Test invalid number of travelers."""
        with pytest.raises(ValidationError) as exc_info:
            validate_travelers(0)
        assert "at least 1" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_travelers(-1)
        assert "at least 1" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_travelers(21)
        assert "too many" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_travelers("5")
        assert "must be an integer" in str(exc_info.value)


class TestBudgetValidation:
    """Test cases for budget validation."""
    
    def test_valid_budget(self):
        """Test valid budget values."""
        assert validate_budget(None) is None
        assert validate_budget(0) == 0.0
        assert validate_budget(100) == 100.0
        assert validate_budget(999.99) == 999.99
    
    def test_invalid_budget(self):
        """Test invalid budget values."""
        with pytest.raises(ValidationError) as exc_info:
            validate_budget(-100)
        assert "cannot be negative" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_budget("100")
        assert "must be a number" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_budget(1000001)
        assert "too high" in str(exc_info.value)


class TestPriceLevelValidation:
    """Test cases for price level validation."""
    
    def test_valid_price_level(self):
        """Test valid price levels."""
        assert validate_price_level("1") == "1"
        assert validate_price_level("2") == "2"
        assert validate_price_level("3") == "3"
        assert validate_price_level("4") == "4"
        assert validate_price_level("cheap") == "1"
        assert validate_price_level("moderate") == "2"
        assert validate_price_level("expensive") == "3"
        assert validate_price_level("very_expensive") == "4"
        assert validate_price_level("  CHEAP  ") == "1"
    
    def test_invalid_price_level(self):
        """Test invalid price levels."""
        with pytest.raises(ValidationError) as exc_info:
            validate_price_level("5")
        assert "must be one of" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_price_level("invalid")
        assert "must be one of" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_price_level(1)
        assert "must be a string" in str(exc_info.value)


class TestRatingValidation:
    """Test cases for rating validation."""
    
    def test_valid_rating(self):
        """Test valid rating values."""
        assert validate_rating(None) is None
        assert validate_rating(0) == 0.0
        assert validate_rating(2.5) == 2.5
        assert validate_rating(5.0) == 5.0
        assert validate_rating("4.2") == 4.2
    
    def test_invalid_rating(self):
        """Test invalid rating values."""
        with pytest.raises(ValidationError) as exc_info:
            validate_rating(-0.1)
        assert "between 0 and 5" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_rating(5.1)
        assert "between 0 and 5" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_rating("invalid")
        assert "must be a number" in str(exc_info.value)


class TestCoordinatesValidation:
    """Test cases for coordinates validation."""
    
    def test_valid_coordinates(self):
        """Test valid coordinates."""
        assert validate_coordinates(37.7749, -122.4194) == (37.7749, -122.4194)
        assert validate_coordinates(0, 0) == (0.0, 0.0)
        assert validate_coordinates(90, 180) == (90.0, 180.0)
        assert validate_coordinates(-90, -180) == (-90.0, -180.0)
    
    def test_invalid_coordinates(self):
        """Test invalid coordinates."""
        with pytest.raises(ValidationError) as exc_info:
            validate_coordinates(91, 0)
        assert "Latitude must be between" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_coordinates(0, 181)
        assert "Longitude must be between" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_coordinates("37.7749", -122.4194)
        assert "must be numbers" in str(exc_info.value)


class TestIataCodeValidation:
    """Test cases for IATA code validation."""
    
    def test_valid_iata_code(self):
        """Test valid IATA codes."""
        assert validate_iata_code("SFO") == "SFO"
        assert validate_iata_code("LAX") == "LAX"
        assert validate_iata_code("JFK") == "JFK"
        assert validate_iata_code("sfo") == "SFO"
        assert validate_iata_code("  lax  ") == "LAX"
    
    def test_invalid_iata_code(self):
        """Test invalid IATA codes."""
        with pytest.raises(ValidationError) as exc_info:
            validate_iata_code("SF")
        assert "exactly 3 characters" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_iata_code("SFO1")
        assert "only letters" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            validate_iata_code(123)
        assert "must be a string" in str(exc_info.value)


class TestStringSanitization:
    """Test cases for string sanitization."""
    
    def test_sanitize_string(self):
        """Test string sanitization."""
        assert sanitize_string("Hello World") == "Hello World"
        assert sanitize_string("  Hello World  ") == "Hello World"
        assert sanitize_string("Hello<script>alert('xss')</script>World") == "HelloalertxssWorld"
        assert sanitize_string("Hello\"quote'and&semicolon;test") == "Helloquoteandsemicolontest"
        
        # Test truncation
        long_string = "A" * 300
        assert len(sanitize_string(long_string)) == 255
    
    def test_sanitize_string_invalid_input(self):
        """Test sanitization with invalid input."""
        with pytest.raises(ValidationError):
            sanitize_string(123)


class TestListValidation:
    """Test cases for list validation."""
    
    def test_valid_list(self):
        """Test valid list inputs."""
        result = validate_list_items(["item1", "item2", "item3"], "test_list")
        assert result == ["item1", "item2", "item3"]
        
        # Test with empty strings (should be filtered out)
        result = validate_list_items(["item1", "", "item2"], "test_list")
        assert result == ["item1", "item2"]
        
        # Test with whitespace (should be trimmed)
        result = validate_list_items(["  item1  ", "item2"], "test_list")
        assert result == ["item1", "item2"]
    
    def test_invalid_list(self):
        """Test invalid list inputs."""
        with pytest.raises(ValidationError) as exc_info:
            validate_list_items("not a list", "test_list")
        assert "must be a list" in str(exc_info.value)
        
        # Too many items
        with pytest.raises(ValidationError) as exc_info:
            validate_list_items([f"item{i}" for i in range(11)], "test_list")
        assert "too many items" in str(exc_info.value)
        
        # Invalid item type
        with pytest.raises(ValidationError) as exc_info:
            validate_list_items([1, 2, 3], "test_list")
        assert "must be a string" in str(exc_info.value)
