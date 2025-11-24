"""Sustainability Travel Planner Package.

Usage:
	from ai_travel_planner_agent import run_query, fetch_weather
	print(run_query("Weather in Berlin and emissions for 20 km car trip"))

Features:
  - Tool wrappers (weather, air quality, emissions, time).
  - Pure fetch functions for direct use or testing.
  - Graceful fallbacks if the advanced agent framework (google-adk) is missing.

Versioning: increment __version__ for any public API change.
"""

__version__ = "0.1.2"

try:  # Attempt to import agent components (absolute import since top-level module)
	from agent import (
		root_agent,
		main_agent,
		run_query,
		weather_tool,
		air_quality_tool,
		transport_emissions_tool,
		timer_tool,
		itinerary_tool,
		ItineraryAgent,
	)
	starter_agent = main_agent  # backward-compatible alias
except ImportError:
	# Relative import fallback only when running as installed package (__package__ truthy)
	if __package__:
		try:
			from .agent import (
				root_agent,
				main_agent,
				run_query,
				weather_tool,
				air_quality_tool,
				transport_emissions_tool,
				timer_tool,
				itinerary_tool,
				ItineraryAgent,
			)
			starter_agent = main_agent
		except Exception:
			pass
except Exception:  # Provide graceful fallbacks
	def _unavailable(*args, **kwargs):
		return "(agent framework unavailable)"

	root_agent = None  # type: ignore
	starter_agent = None  # type: ignore

	def run_query(prompt: str) -> str:
		return _unavailable(prompt)

	def weather_tool(city: str) -> str:
		return _unavailable(city)

	def air_quality_tool(city: str) -> str:
		return _unavailable(city)

	def transport_emissions_tool(mode: str, distance_km: float) -> str:
		return _unavailable(mode, distance_km)

	def timer_tool(city: str) -> str:
		return _unavailable(city)

try:
	from tools import (
		fetch_weather,
		fetch_air_quality,
		estimate_transport_emissions,
		fetch_city_time,
		geocode_city,
		fetch_air_quality_openmeteo,
	)
except Exception:
	# Minimal fallbacks if tools cannot be imported
	def fetch_weather(*args, **kwargs): return "(weather unavailable)"
	def fetch_air_quality(*args, **kwargs): return "(air quality unavailable)"
	def estimate_transport_emissions(*args, **kwargs): return "(emissions unavailable)"
	def fetch_city_time(*args, **kwargs): return "(time unavailable)"
	def geocode_city(*args, **kwargs): return None
	def fetch_air_quality_openmeteo(*args, **kwargs): return "(openmeteo unavailable)"

def get_version() -> str:
	"""Return the package version string."""
	return __version__

__all__ = [
	'root_agent',
	'starter_agent',
	'run_query',
	'weather_tool',
	'air_quality_tool',
	'transport_emissions_tool',
	'timer_tool',
	'itinerary_tool',
	'ItineraryAgent',
	'fetch_weather',
	'fetch_air_quality',
	'fetch_air_quality_openmeteo',
	'estimate_transport_emissions',
	'fetch_city_time',
	'geocode_city',
	'__version__',
	'get_version',
]
