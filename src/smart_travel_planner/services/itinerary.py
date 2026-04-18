"""Itinerary service for Smart Travel Planner."""

import logging
from typing import Dict, List, Any, Optional
from datetime import date, timedelta

from ..services.base import BaseService
from ..models.travel_models import TravelRequest, Itinerary, ItineraryDay, Location
from ..exceptions import ItineraryGenerationError


class ItineraryService(BaseService):
    """Service for generating and managing travel itineraries."""
    
    def __init__(self):
        super().__init__("itinerary")
        self._generator = None
        self._initialize_generator()
    
    def _initialize_generator(self):
        """Initialize the itinerary generator."""
        try:
            from .core.itinerary import ItineraryGenerator
            self._generator = ItineraryGenerator()
            self.logger.info("Itinerary generator initialized")
        except ImportError as e:
            self.logger.error(f"Failed to initialize itinerary generator: {e}")
            self._generator = None
    
    def health_check(self) -> bool:
        """Check if the itinerary service is healthy."""
        return self._generator is not None
    
    async def generate_itinerary(
        self,
        travel_request: TravelRequest,
        context: Optional[Dict[str, Any]] = None
    ) -> Itinerary:
        """Generate a complete travel itinerary."""
        if not self._generator:
            raise ItineraryGenerationError("Itinerary generator not available")
        
        try:
            self._log_api_call(f"generate_itinerary({travel_request.duration_days} days)")
            
            # Check cache first
            cache_key = f"itinerary:{travel_request.origin}:{travel_request.destination}:{travel_request.start_date}"
            cached_result = self._cache_get("generate_itinerary", 
                                         origin=travel_request.origin,
                                         destination=travel_request.destination,
                                         start_date=travel_request.start_date.isoformat())
            if cached_result:
                self.logger.info(f"Retrieved itinerary from cache")
                return cached_result
            
            # Generate itinerary
            itinerary = await self._generator.generate_itinerary(travel_request, context)
            
            # Cache the result
            self._cache_set("generate_itinerary", itinerary,
                           origin=travel_request.origin,
                           destination=travel_request.destination,
                           start_date=travel_request.start_date.isoformat())
            
            return itinerary
            
        except Exception as e:
            self.logger.error(f"Error generating itinerary: {e}", exc_info=True)
            raise ItineraryGenerationError(f"Failed to generate itinerary: {e}")
    
    async def create_basic_itinerary(self, travel_request: TravelRequest) -> Itinerary:
        """Create a basic itinerary without AI generation."""
        try:
            self.logger.info(f"Creating basic itinerary for {travel_request.duration_days} days")
            
            # Create location objects
            origin = Location(name=travel_request.origin)
            destination = Location(name=travel_request.destination)
            
            # Create day-by-day structure
            days = []
            current_date = travel_request.start_date
            
            for i in range(travel_request.duration_days):
                day_date = current_date + timedelta(days=i)
                
                # Basic template activities
                if i == 0:  # Arrival day
                    activities = [
                        "Arrive at destination",
                        "Check into accommodation",
                        "Explore local area",
                        "Welcome dinner"
                    ]
                elif i == travel_request.duration_days - 1:  # Departure day
                    activities = [
                        "Final breakfast",
                        "Last-minute shopping",
                        "Depart for home"
                    ]
                else:  # Full days
                    activities = [
                        "Morning sightseeing",
                        "Lunch at local restaurant",
                        "Afternoon activity",
                        "Evening entertainment"
                    ]
                
                itinerary_day = ItineraryDay(
                    day=i + 1,
                    date=day_date,
                    activities=activities,
                    notes=f"Day {i + 1} in {travel_request.destination}"
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
            
        except Exception as e:
            self.logger.error(f"Error creating basic itinerary: {e}", exc_info=True)
            raise ItineraryGenerationError(f"Failed to create basic itinerary: {e}")
    
    async def update_itinerary_day(
        self,
        itinerary: Itinerary,
        day_number: int,
        activities: List[str],
        notes: Optional[str] = None
    ) -> Itinerary:
        """Update a specific day in an itinerary."""
        try:
            # Find the day to update
            day_to_update = None
            for day in itinerary.days:
                if day.day == day_number:
                    day_to_update = day
                    break
            
            if not day_to_update:
                raise ItineraryGenerationError(f"Day {day_number} not found in itinerary")
            
            # Update the day
            day_to_update.activities = activities
            if notes:
                day_to_update.notes = notes
            
            self.logger.info(f"Updated itinerary day {day_number}")
            return itinerary
            
        except Exception as e:
            self.logger.error(f"Error updating itinerary day: {e}", exc_info=True)
            raise ItineraryGenerationError(f"Failed to update itinerary day: {e}")
    
    async def add_accommodation_to_day(
        self,
        itinerary: Itinerary,
        day_number: int,
        accommodation: Any  # Hotel object
    ) -> Itinerary:
        """Add accommodation to a specific day."""
        try:
            # Find the day to update
            day_to_update = None
            for day in itinerary.days:
                if day.day == day_number:
                    day_to_update = day
                    break
            
            if not day_to_update:
                raise ItineraryGenerationError(f"Day {day_number} not found in itinerary")
            
            # Add accommodation
            day_to_update.accommodation = accommodation
            
            self.logger.info(f"Added accommodation to day {day_number}")
            return itinerary
            
        except Exception as e:
            self.logger.error(f"Error adding accommodation: {e}", exc_info=True)
            raise ItineraryGenerationError(f"Failed to add accommodation: {e}")
    
    async def add_meals_to_day(
        self,
        itinerary: Itinerary,
        day_number: int,
        meals: List[Any]  # Restaurant objects
    ) -> Itinerary:
        """Add meals to a specific day."""
        try:
            # Find the day to update
            day_to_update = None
            for day in itinerary.days:
                if day.day == day_number:
                    day_to_update = day
                    break
            
            if not day_to_update:
                raise ItineraryGenerationError(f"Day {day_number} not found in itinerary")
            
            # Add meals
            day_to_update.meals = meals
            
            self.logger.info(f"Added {len(meals)} meals to day {day_number}")
            return itinerary
            
        except Exception as e:
            self.logger.error(f"Error adding meals: {e}", exc_info=True)
            raise ItineraryGenerationError(f"Failed to add meals: {e}")
    
    def calculate_itinerary_summary(self, itinerary: Itinerary) -> Dict[str, Any]:
        """Calculate summary statistics for an itinerary."""
        try:
            total_activities = sum(len(day.activities) for day in itinerary.days)
            days_with_accommodation = sum(1 for day in itinerary.days if day.accommodation)
            total_meals = sum(len(day.meals) for day in itinerary.days)
            
            summary = {
                'total_days': len(itinerary.days),
                'total_activities': total_activities,
                'activities_per_day': total_activities / len(itinerary.days) if itinerary.days else 0,
                'days_with_accommodation': days_with_accommodation,
                'total_meals': total_meals,
                'sustainability_rating': itinerary.sustainability_rating,
                'total_emissions_kg_co2': itinerary.total_emissions_kg_co2
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error calculating itinerary summary: {e}", exc_info=True)
            return {}
    
    async def optimize_itinerary_for_sustainability(
        self,
        itinerary: Itinerary,
        preference: str = "moderate"
    ) -> Itinerary:
        """Optimize an itinerary for sustainability."""
        try:
            self.logger.info(f"Optimizing itinerary for sustainability ({preference})")
            
            # This is a placeholder for sustainability optimization
            # In a real implementation, this would:
            # 1. Analyze current activities for environmental impact
            # 2. Suggest more sustainable alternatives
            # 3. Optimize transportation between locations
            # 4. Recommend eco-friendly accommodations and dining
            
            # For now, just update the sustainability rating
            if preference == "high":
                itinerary.sustainability_rating = "Excellent"
            elif preference == "moderate":
                itinerary.sustainability_rating = "Good"
            else:
                itinerary.sustainability_rating = "Fair"
            
            self.logger.info(f"Optimized itinerary sustainability rating: {itinerary.sustainability_rating}")
            return itinerary
            
        except Exception as e:
            self.logger.error(f"Error optimizing itinerary: {e}", exc_info=True)
            raise ItineraryGenerationError(f"Failed to optimize itinerary: {e}")
    
    def export_itinerary_to_text(self, itinerary: Itinerary) -> str:
        """Export itinerary to formatted text."""
        try:
            lines = []
            lines.append(f"Travel Itinerary: {itinerary.origin} to {itinerary.destination}")
            lines.append(f"Dates: {itinerary.start_date} to {itinerary.end_date}")
            lines.append(f"Duration: {itinerary.duration_days} days")
            
            if itinerary.sustainability_rating:
                lines.append(f"Sustainability Rating: {itinerary.sustainability_rating}")
            
            if itinerary.total_emissions_kg_co2:
                lines.append(f"Total Emissions: {itinerary.total_emissions_kg_co2:.2f} kg CO2")
            
            lines.append("\n" + "="*50 + "\n")
            
            for day in itinerary.days:
                lines.append(f"Day {day.day} - {day.date}")
                lines.append("-" * 30)
                
                for activity in day.activities:
                    lines.append(f"  2022 {activity}")
                
                if day.accommodation:
                    lines.append(f"  2022 Hotel: {day.accommodation.name}")
                
                if day.meals:
                    lines.append("  2022 Meals:")
                    for meal in day.meals:
                        lines.append(f"    - {meal.name}")
                
                if day.estimated_emissions:
                    lines.append(f"  2022 Emissions: {day.estimated_emissions.co2_kg:.2f} kg CO2")
                
                if day.notes:
                    lines.append(f"  2022 Notes: {day.notes}")
                
                lines.append("")
            
            return "\n".join(lines)
            
        except Exception as e:
            self.logger.error(f"Error exporting itinerary: {e}", exc_info=True)
            raise ItineraryGenerationError(f"Failed to export itinerary: {e}")
    
    def validate_itinerary(self, itinerary: Itinerary) -> List[str]:
        """Validate an itinerary and return any issues."""
        issues = []
        
        try:
            # Check basic structure
            if not itinerary.days:
                issues.append("Itinerary has no days")
            
            if not itinerary.origin:
                issues.append("Itinerary has no origin")
            
            if not itinerary.destination:
                issues.append("Itinerary has no destination")
            
            # Check date consistency
            if itinerary.start_date and itinerary.end_date:
                if itinerary.start_date > itinerary.end_date:
                    issues.append("Start date is after end date")
                
                expected_days = (itinerary.end_date - itinerary.start_date).days + 1
                if len(itinerary.days) != expected_days:
                    issues.append(f"Number of days ({len(itinerary.days)}) doesn't match date range ({expected_days})")
            
            # Check day numbering
            for i, day in enumerate(itinerary.days):
                if day.day != i + 1:
                    issues.append(f"Day {i + 1} has incorrect number: {day.day}")
            
            # Check for empty days
            for day in itinerary.days:
                if not day.activities:
                    issues.append(f"Day {day.day} has no activities")
            
        except Exception as e:
            self.logger.error(f"Error validating itinerary: {e}", exc_info=True)
            issues.append(f"Validation error: {e}")
        
        return issues
