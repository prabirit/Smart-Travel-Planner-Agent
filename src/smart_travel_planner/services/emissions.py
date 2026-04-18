"""Emissions calculation service for Smart Travel Planner."""

import csv
import logging
from pathlib import Path
from typing import Dict, Optional, Union

from ..services.base import BaseService
from ..models.travel_models import EmissionsData, TransportMode, TravelRequest
from ..utils.geo_utils import calculate_distance
from ..exceptions import EmissionsCalculationError
from ..config import get_settings


class EmissionsService(BaseService):
    """Service for calculating transport emissions."""
    
    def __init__(self):
        super().__init__("emissions")
        self.settings = get_settings()
        self._emission_factors = {}
        self._load_emission_factors()
    
    def _load_emission_factors(self):
        """Load emission factors from CSV file."""
        try:
            # Path to emission factors file
            factors_file = self.settings.data_dir / self.settings.emission_factors_file
            
            if not factors_file.exists():
                # Create default emission factors file
                self._create_default_emission_factors(factors_file)
            
            # Load emission factors
            with open(factors_file, 'r', newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    mode = row['mode'].strip().lower()
                    self._emission_factors[mode] = {
                        'co2_per_km': float(row['co2_per_km']),
                        'description': row.get('description', ''),
                        'source': row.get('source', 'Default')
                    }
            
            self.logger.info(f"Loaded {len(self._emission_factors)} emission factors")
            
        except Exception as e:
            self.logger.error(f"Error loading emission factors: {e}")
            # Use hardcoded defaults as fallback
            self._emission_factors = self._get_default_emission_factors()
    
    def _create_default_emission_factors(self, file_path: Path):
        """Create default emission factors CSV file."""
        default_factors = [
            {'mode': 'car_gasoline', 'co2_per_km': '0.205', 'description': 'Gasoline car', 'source': 'EPA'},
            {'mode': 'car_electric', 'co2_per_km': '0.050', 'description': 'Electric car', 'source': 'EPA'},
            {'mode': 'train', 'co2_per_km': '0.041', 'description': 'Train', 'source': 'EPA'},
            {'mode': 'bus', 'co2_per_km': '0.089', 'description': 'Bus', 'source': 'EPA'},
            {'mode': 'flight', 'co2_per_km': '0.115', 'description': 'Domestic flight', 'source': 'EPA'},
            {'mode': 'walking', 'co2_per_km': '0.000', 'description': 'Walking', 'source': 'EPA'},
            {'mode': 'cycling', 'co2_per_km': '0.000', 'description': 'Cycling', 'source': 'EPA'},
        ]
        
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', newline='') as csvfile:
            fieldnames = ['mode', 'co2_per_km', 'description', 'source']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(default_factors)
        
        self.logger.info(f"Created default emission factors file: {file_path}")
    
    def _get_default_emission_factors(self) -> Dict[str, Dict[str, Union[float, str]]]:
        """Get default emission factors as fallback."""
        return {
            'car_gasoline': {'co2_per_km': 0.205, 'description': 'Gasoline car', 'source': 'Default'},
            'car_electric': {'co2_per_km': 0.050, 'description': 'Electric car', 'source': 'Default'},
            'train': {'co2_per_km': 0.041, 'description': 'Train', 'source': 'Default'},
            'bus': {'co2_per_km': 0.089, 'description': 'Bus', 'source': 'Default'},
            'flight': {'co2_per_km': 0.115, 'description': 'Domestic flight', 'source': 'Default'},
            'walking': {'co2_per_km': 0.000, 'description': 'Walking', 'source': 'Default'},
            'cycling': {'co2_per_km': 0.000, 'description': 'Cycling', 'source': 'Default'},
        }
    
    def health_check(self) -> bool:
        """Check if the emissions service is healthy."""
        return len(self._emission_factors) > 0
    
    async def calculate_emissions(
        self,
        mode: Union[str, TransportMode],
        distance_km: float
    ) -> EmissionsData:
        """Calculate emissions for a specific transport mode and distance."""
        try:
            # Convert mode to enum if needed
            if isinstance(mode, str):
                mode = TransportMode(mode.lower())
            
            # Get emission factor
            if mode.value not in self._emission_factors:
                raise EmissionsCalculationError(f"No emission factor for mode: {mode.value}")
            
            factor_data = self._emission_factors[mode.value]
            co2_per_km = factor_data['co2_per_km']
            
            # Calculate total emissions
            total_co2 = distance_km * co2_per_km
            
            emissions_data = EmissionsData(
                mode=mode,
                distance_km=distance_km,
                co2_kg=total_co2,
                co2_per_km=co2_per_km
            )
            
            self.logger.info(f"Calculated emissions: {mode.value} - {total_co2:.2f} kg CO2")
            return emissions_data
            
        except Exception as e:
            self.logger.error(f"Error calculating emissions: {e}", exc_info=True)
            raise EmissionsCalculationError(f"Failed to calculate emissions: {e}")
    
    async def calculate_trip_emissions(self, travel_request: TravelRequest) -> EmissionsData:
        """Calculate emissions for the entire trip."""
        try:
            self._log_api_call(f"calculate_trip_emissions({travel_request.origin} -> {travel_request.destination})")
            
            # Check cache first
            cache_key = f"trip_emissions:{travel_request.origin}:{travel_request.destination}"
            cached_result = self._cache_get("calculate_trip_emissions", 
                                         origin=travel_request.origin, 
                                         destination=travel_request.destination)
            if cached_result:
                self.logger.info(f"Retrieved trip emissions from cache")
                return cached_result
            
            # Calculate distance between origin and destination
            # For simplicity, we'll use a straight-line distance
            # In production, this would use actual routing data
            try:
                from ..utils.geo_utils import geocode_location
                origin_lat, origin_lon = geocode_location(travel_request.origin)
                dest_lat, dest_lon = geocode_location(travel_request.destination)
                distance_km = calculate_distance(origin_lat, origin_lon, dest_lat, dest_lon)
            except Exception:
                # Fallback: estimate distance based on typical values
                distance_km = 1000  # Default 1000km
            
            # Choose transport mode based on distance and preferences
            mode = self._choose_transport_mode(distance_km, travel_request)
            
            # Calculate emissions
            emissions = await self.calculate_emissions(mode, distance_km)
            
            # Cache the result
            self._cache_set("calculate_trip_emissions", emissions,
                           origin=travel_request.origin, 
                           destination=travel_request.destination)
            
            return emissions
            
        except Exception as e:
            self.logger.error(f"Error calculating trip emissions: {e}", exc_info=True)
            raise EmissionsCalculationError(f"Failed to calculate trip emissions: {e}")
    
    def _choose_transport_mode(self, distance_km: float, travel_request: TravelRequest) -> TransportMode:
        """Choose the most appropriate transport mode based on distance and preferences."""
        # Simple logic based on distance
        if distance_km < 5:
            return TransportMode.WALKING
        elif distance_km < 50:
            return TransportMode.CYCLING
        elif distance_km < 500:
            return TransportMode.TRAIN
        elif distance_km < 1500:
            return TransportMode.FLIGHT
        else:
            return TransportMode.FLIGHT
    
    async def compare_transport_modes(
        self,
        distance_km: float,
        modes: Optional[list[TransportMode]] = None
    ) -> list[EmissionsData]:
        """Compare emissions across different transport modes."""
        if modes is None:
            modes = [
                TransportMode.CAR_GASOLINE,
                TransportMode.CAR_ELECTRIC,
                TransportMode.TRAIN,
                TransportMode.BUS,
                TransportMode.FLIGHT
            ]
        
        comparisons = []
        
        for mode in modes:
            try:
                emissions = await self.calculate_emissions(mode, distance_km)
                comparisons.append(emissions)
            except EmissionsCalculationError:
                # Skip modes that don't have emission factors
                continue
        
        # Sort by emissions (lowest first)
        comparisons.sort(key=lambda x: x.co2_kg)
        
        return comparisons
    
    def get_emission_factor_info(self, mode: Union[str, TransportMode]) -> Optional[Dict[str, Union[float, str]]]:
        """Get detailed information about an emission factor."""
        if isinstance(mode, str):
            mode = TransportMode(mode.lower())
        
        return self._emission_factors.get(mode.value)
    
    async def calculate_savings(
        self,
        current_mode: TransportMode,
        alternative_mode: TransportMode,
        distance_km: float
    ) -> Dict[str, float]:
        """Calculate emissions savings between two transport modes."""
        try:
            current_emissions = await self.calculate_emissions(current_mode, distance_km)
            alternative_emissions = await self.calculate_emissions(alternative_mode, distance_km)
            
            savings = current_emissions.co2_kg - alternative_emissions.co2_kg
            percentage_savings = (savings / current_emissions.co2_kg) * 100 if current_emissions.co2_kg > 0 else 0
            
            return {
                'current_emissions_kg': current_emissions.co2_kg,
                'alternative_emissions_kg': alternative_emissions.co2_kg,
                'savings_kg': savings,
                'percentage_savings': percentage_savings
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating savings: {e}", exc_info=True)
            raise EmissionsCalculationError(f"Failed to calculate savings: {e}")
    
    def get_transport_recommendations(
        self,
        distance_km: float,
        sustainability_preference: str = "moderate"
    ) -> list[TransportMode]:
        """Get transport mode recommendations based on distance and sustainability preference."""
        all_modes = [
            TransportMode.WALKING,
            TransportMode.CYCLING,
            TransportMode.BUS,
            TransportMode.TRAIN,
            TransportMode.CAR_ELECTRIC,
            TransportMode.CAR_GASOLINE,
            TransportMode.FLIGHT
        ]
        
        # Filter modes based on distance
        suitable_modes = []
        
        for mode in all_modes:
            if self._is_mode_suitable_for_distance(mode, distance_km):
                suitable_modes.append(mode)
        
        # Sort by emissions (lowest first)
        mode_emissions = []
        for mode in suitable_modes:
            if mode.value in self._emission_factors:
                co2_per_km = self._emission_factors[mode.value]['co2_per_km']
                mode_emissions.append((mode, co2_per_km))
        
        mode_emissions.sort(key=lambda x: x[1])
        
        # Adjust based on sustainability preference
        if sustainability_preference == "high":
            # Only return the top 3 most sustainable options
            return [mode for mode, _ in mode_emissions[:3]]
        elif sustainability_preference == "low":
            # Include more options, even if less sustainable
            return [mode for mode, _ in mode_emissions]
        else:  # moderate
            # Balance between sustainability and practicality
            return [mode for mode, _ in mode_emissions[:5]]
    
    def _is_mode_suitable_for_distance(self, mode: TransportMode, distance_km: float) -> bool:
        """Check if a transport mode is suitable for a given distance."""
        suitability_ranges = {
            TransportMode.WALKING: (0, 10),
            TransportMode.CYCLING: (0, 50),
            TransportMode.BUS: (1, 500),
            TransportMode.TRAIN: (10, 2000),
            TransportMode.CAR_ELECTRIC: (1, 1000),
            TransportMode.CAR_GASOLINE: (1, 1000),
            TransportMode.FLIGHT: (100, float('inf')),
        }
        
        min_dist, max_dist = suitability_ranges.get(mode, (0, float('inf')))
        return min_dist <= distance_km <= max_dist
