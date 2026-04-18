"""Itinerary generation service for Smart Travel Planner."""

import logging
from typing import Dict, List, Any, Optional
from datetime import date, timedelta

try:
    import google.generativeai as genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from ..config import get_settings
from ..models.travel_models import TravelRequest, Itinerary, ItineraryDay, Location, Hotel, Restaurant, Flight, WeatherInfo, EmissionsData
from ..services.base import BaseService
from ..exceptions import ItineraryGenerationError, ConfigurationError


class ItineraryService(BaseService):
    """Service for generating travel itineraries using AI."""
    
    def __init__(self):
        super().__init__("itinerary")
        self.settings = get_settings()
        self._model = None
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the generative AI model."""
        if not GENAI_AVAILABLE:
            self.logger.warning("Google Generative AI not available")
            return
        
        if not self.settings.api.google_api_key:
            self.logger.warning("Google API key not configured")
            return
        
        try:
            genai.configure(api_key=self.settings.api.google_api_key)
            self._model = genai.GenerativeModel(self.settings.google.gemini_model)
            self.logger.info(f"Initialized Gemini model: {self.settings.google.gemini_model}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Gemini model: {e}")
            raise ConfigurationError(f"Failed to initialize AI model: {e}")
    
    def health_check(self) -> bool:
        """Check if the service is healthy."""
        return self._model is not None
    
    async def generate_itinerary(
        self,
        travel_request: TravelRequest,
        context: Optional[Dict[str, Any]] = None
    ) -> Itinerary:
        """Generate a complete travel itinerary."""
        if not self._model:
            raise ItineraryGenerationError("AI model not available")
        
        try:
            self.logger.info(f"Generating itinerary for {travel_request.duration_days} days")
            
            # Create prompt
            prompt = self._create_prompt(travel_request, context)
            
            # Generate itinerary content
            response = self._model.generate_content(prompt)
            itinerary_text = response.text
            
            # Parse the response into structured data
            itinerary = self._parse_itinerary(itinerary_text, travel_request, context)
            
            self.logger.info(f"Generated {len(itinerary.days)}-day itinerary")
            return itinerary
            
        except Exception as e:
            self.logger.error(f"Error generating itinerary: {e}", exc_info=True)
            raise ItineraryGenerationError(f"Failed to generate itinerary: {e}")
    
    def _create_prompt(
        self,
        travel_request: TravelRequest,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a comprehensive prompt for itinerary generation."""
        
        # Basic trip information
        prompt = f"""
Generate a sustainable travel itinerary for a {travel_request.duration_days}-day trip from {travel_request.origin} to {travel_request.destination}.
Trip dates: {travel_request.start_date} to {travel_request.end_date}
Number of travelers: {travel_request.travelers}
Sustainability preference: {travel_request.sustainability_preference}
"""
        
        # Add budget information
        if travel_request.budget_usd:
            prompt += f"Budget: ${travel_request.budget_usd:.2f}\n"
        
        # Add preferences
        if travel_request.cuisine_preferences:
            prompt += f"Cuisine preferences: {', '.join(travel_request.cuisine_preferences)}\n"
        
        if travel_request.activity_preferences:
            prompt += f"Activity preferences: {', '.join(travel_request.activity_preferences)}\n"
        
        # Add context data
        if context:
            prompt += "\nContext Information:\n"
            
            if "weather" in context:
                weather = context["weather"]
                prompt += f"Weather: {weather.description}, {weather.temperature_celsius:.1f}°C\n"
            
            if "flights" in context:
                flights = context["flights"]
                prompt += f"Flight options: {len(flights)} available, starting from ${min(f.price for f in flights):.2f}\n"
            
            if "hotels" in context:
                hotels = context["hotels"]
                prompt += f"Hotel options: {len(hotels)} available, starting from ${min(h.price_per_night for h in hotels if h.price_per_night):.2f}\n"
            
            if "restaurants" in context:
                restaurants = context["restaurants"]
                prompt += f"Restaurant options: {len(restaurants)} available, average rating {sum(r.rating for r in restaurants if r.rating) / len([r for r in restaurants if r.rating]):.1f}\n"
            
            if "emissions" in context:
                emissions = context["emissions"]
                prompt += f"Estimated transport emissions: {emissions.co2_kg:.2f} kg CO2\n"
        
        # Add sustainability focus
        prompt += f"""

Sustainability Guidelines:
- Prioritize low-carbon transportation options
- Recommend eco-friendly accommodations
- Suggest sustainable activities and dining
- Include environmental impact considerations
- Balance sustainability with traveler comfort and budget

Please provide a day-by-day itinerary with the following format for each day:
Day X - [Date]
Morning: [Activity description]
Afternoon: [Activity description]  
Evening: [Activity description]
Dining: [Restaurant recommendation]
Accommodation: [Hotel recommendation]
Transportation: [How to get around]
Sustainability tip: [Eco-friendly suggestion]

Make the itinerary practical, enjoyable, and environmentally conscious.
"""
        
        return prompt
    
    def _parse_itinerary(
        self,
        itinerary_text: str,
        travel_request: TravelRequest,
        context: Optional[Dict[str, Any]] = None
    ) -> Itinerary:
        """Parse the generated text into a structured itinerary."""
        
        # Create location objects
        origin = Location(name=travel_request.origin)
        destination = Location(name=travel_request.destination)
        
        # Parse days from the text
        days = []
        current_date = travel_request.start_date
        
        # Simple parsing logic - in production, this would be more sophisticated
        day_sections = self._extract_day_sections(itinerary_text)
        
        for i, day_text in enumerate(day_sections):
            day_date = current_date + timedelta(days=i)
            
            # Parse activities from day text
            activities = self._extract_activities(day_text)
            
            # Create itinerary day
            itinerary_day = ItineraryDay(
                day=i + 1,
                date=day_date,
                activities=activities,
                notes=day_text.strip()
            )
            
            days.append(itinerary_day)
        
        # Calculate total emissions if available
        total_emissions = None
        if context and "emissions" in context:
            total_emissions = context["emissions"].co2_kg
        
        # Determine sustainability rating
        sustainability_rating = self._calculate_sustainability_rating(total_emissions, travel_request)
        
        return Itinerary(
            origin=origin,
            destination=destination,
            start_date=travel_request.start_date,
            end_date=travel_request.end_date,
            days=days,
            total_emissions_kg_co2=total_emissions,
            sustainability_rating=sustainability_rating
        )
    
    def _extract_day_sections(self, itinerary_text: str) -> List[str]:
        """Extract individual day sections from the itinerary text."""
        days = []
        
        # Split by "Day X" pattern
        import re
        day_pattern = r'Day \d+.*?(?=Day \d+|$)'
        matches = re.findall(day_pattern, itinerary_text, re.DOTALL | re.IGNORECASE)
        
        if matches:
            days = matches
        else:
            # Fallback: split by simple pattern
            lines = itinerary_text.split('\n')
            current_day = []
            for line in lines:
                if line.strip().lower().startswith('day') and current_day:
                    days.append('\n'.join(current_day))
                    current_day = [line]
                else:
                    current_day.append(line)
            
            if current_day:
                days.append('\n'.join(current_day))
        
        return days
    
    def _extract_activities(self, day_text: str) -> List[str]:
        """Extract activities from day text."""
        activities = []
        
        lines = day_text.split('\n')
        for line in lines:
            line = line.strip()
            if line and any(keyword in line.lower() for keyword in ['morning:', 'afternoon:', 'evening:', 'activity:']):
                # Clean up the activity description
                activity = line.split(':', 1)[1].strip() if ':' in line else line
                if activity:
                    activities.append(activity)
        
        return activities
    
    def _calculate_sustainability_rating(
        self,
        total_emissions_kg: Optional[float],
        travel_request: TravelRequest
    ) -> str:
        """Calculate sustainability rating based on emissions and preferences."""
        if total_emissions_kg is None:
            return "Unknown"
        
        # Simple rating based on emissions per day
        emissions_per_day = total_emissions_kg / travel_request.duration_days
        
        if emissions_per_day <= 10:
            return "Excellent"
        elif emissions_per_day <= 25:
            return "Good"
        elif emissions_per_day <= 50:
            return "Moderate"
        elif emissions_per_day <= 100:
            return "Poor"
        else:
            return "Very Poor"
    
    async def generate_fallback_itinerary(self, travel_request: TravelRequest) -> Itinerary:
        """Generate a basic fallback itinerary when AI is not available."""
        self.logger.warning("Using fallback itinerary generation")
        
        # Create location objects
        origin = Location(name=travel_request.origin)
        destination = Location(name=travel_request.destination)
        
        # Create basic day structure
        days = []
        current_date = travel_request.start_date
        
        for i in range(travel_request.duration_days):
            day_date = current_date + timedelta(days=i)
            
            # Basic activities
            activities = [
                "Explore local attractions",
                "Visit cultural sites",
                "Enjoy local cuisine",
                "Relax and recharge"
            ]
            
            itinerary_day = ItineraryDay(
                day=i + 1,
                date=day_date,
                activities=activities,
                notes="Basic itinerary - AI generation not available"
            )
            
            days.append(itinerary_day)
        
        return Itinerary(
            origin=origin,
            destination=destination,
            start_date=travel_request.start_date,
            end_date=travel_request.end_date,
            days=days,
            sustainability_rating="Unknown"
        )
