# Smart Travel Planner Agent - write up

## Abstract
Smart Travel Planner Agent is a sustainability‑focused trip planning system that integrates real‑time flight and hotel pricing, weather and air quality data, emissions estimation, and restaurant recommendations. The agent orchestrates multiple data sources and tools, using Google Gemini (via `google-generativeai`) to produce a multi‑day itinerary optimized for low carbon impact. The project demonstrates modern agent architectures, pragmatic API integrations, and robust testing, delivering a practical assistant that balances user experience with environmental considerations.

## Problem Statement
Travel planning is fragmented across many services: flights, lodging, local conditions, and dining. Typical planners optimize for cost or convenience but rarely for sustainability. This project addresses:
- Consolidation of travel signals (route distance, weather, air quality).
- Real‑time pricing for hotels and flights (Amadeus APIs).
- Emissions estimation to inform greener choices.
- Dining recommendations to complement itineraries.
- Simple, reproducible tooling for users and developers.

## Objectives
- Provide real‑time flight and hotel search with pricing in sandbox mode.
- Estimate transport emissions for common modes (car gas/electric, train, bus).
- Fetch weather and air quality reliably with robust fallback behavior.
- Generate concise, low‑carbon itineraries using an LLM.
- Offer restaurant recommendations with filters for cuisine, price, and rating.
- Ensure maintainability with tests, clear documentation, and environment handling.

## System Architecture
- `agent.py`: Orchestrates tools; hosts `ItineraryAgent` and user‑facing wrappers.
- `tools.py`: Core integrations (Open‑Meteo, Amadeus, OSM/Nominatim, Google Directions).
- `restaurant_server.py`: Reference MCP server (optional); main implementation uses direct Places API to avoid event loop conflicts.
- `emission_factors.csv`: Emission factors used by estimation tool.
- `requirements.txt`: Dependency manifest.
- `README.md`: User documentation, setup, and usage.
- `test_tools.py`: Unit tests for weather, air quality, emissions, time, and restaurant features.
- Refer to architecture_diagram.md for more details

Data flows:
- Geocoding (Nominatim) → Weather/Air Quality → Emissions.
- Amadeus → Hotel IDs (by geocode) → Pricing (offers).
- Amadeus → Flight offers (IATA lookup → pricing).
- Google Places → Nearby Search for restaurants.
- Gemini → Multi‑day sustainable itinerary.

## Key Technologies
- Python 3.x (type hints, requests, certifi)
- Google Generative AI (`google-generativeai`) for itinerary generation
- Amadeus Self‑Service APIs (sandbox): hotels, flights
- Open‑Meteo for weather and air quality
- OpenStreetMap Overpass + Nominatim for hotel discovery and geocoding
- Google Maps Directions and Places APIs
- `python-dotenv` for environment management
- `pytest` for testing

## Implementation Highlights
- Real‑time hotel pricing: two‑step Amadeus flow (by‑geocode → `v3/shopping/hotel-offers`) with adjustable dates via `.env` (`AMADEUS_CHECKIN_OFFSET_DAYS`, `AMADEUS_STAY_NIGHTS`).
- Flight search: `v1/reference-data/locations` → `v2/shopping/flight-offers` with cheapest‑first result formatting.
- Emissions: CSV‑backed factors with mode selection heuristics and explicit distance parsing.
- Air quality: Open‑Meteo with graceful fallback when optional packages are not installed.
- Restaurants: Direct Google Places Nearby Search with cuisine/price/rating filters; Nominatim geocoding avoids key requirements.
- Robust SSL verification (`certifi.where()`), helpful error messages (e.g., Places API enabling guidance).
- Agent wrappers: `weather_tool`, `air_quality_tool`, `transport_emissions_tool`, `itinerary_tool`, `hotel_search_tool`, `flight_search_tool`, `restaurant_search_tool`.
- Impelmented Session management using SessionService (The storage layer) and Runner (The orchestration layer)

## Data Sources and APIs
- Amadeus: `v1/reference-data/locations/hotels/by-geocode`, `v3/shopping/hotel-offers`, `v1/reference-data/locations`, `v2/shopping/flight-offers`.
- Open‑Meteo: weather and air quality endpoints.
- OSM/Nominatim: geocoding (free, no key).
- Google Maps: Directions API.
- Google Places: Nearby Search + (optional) Geocoding API.

## Security and Configuration
- `.env` loads via `python-dotenv` in `tools.py` and `agent.py`.
- Sensitive keys: `GOOGLE_API_KEY`, `GOOGLE_MAPS_API_KEY`, `GOOGLE_PLACES_API_KEY`, `AMADEUS_API_KEY`, `AMADEUS_API_SECRET`.
- SSL verification enforced; debugging flags for Open‑Meteo only, not recommended for production.

## Testing Strategy and Results
- Unit tests (`test_tools.py`): 13 tests cover emissions, weather, time, geocoding, and restaurant search (success, filters, error paths).
- Current run: 13 passed, 0 failed (3 warnings).
- Restaurant tests validate filter logic, error messaging for missing API key and disabled Places API.

Run tests:
```bash
python3 -m pytest test_tools.py -v
```

## Results and Evaluation
- Real‑time flight/hotel data (sandbox) integrated and validated.
- Itinerary generation produces coherent, sustainability‑oriented plans.
- Emissions estimation provides immediate, interpretable feedback.
- Restaurant recommendations enrich user experience.
- Clear README and error messages improve developer and user onboarding.

## Limitations
- Amadeus sandbox pricing may not reflect production market rates.
- Places API may require legacy enablement; the "New" variant uses different endpoints.
- Air quality rich mode requires optional packages; falls back gracefully.
- Route estimation depends on Google Directions availability.

## Future Work
- Add caching layers to reduce quota usage for Amadeus and Places APIs.
- Expand transit support (city‑specific public transport APIs).
- Multi‑currency and budget optimization.
- More MCP servers: events, currency exchange, safety advisories.
- UI layer (web front‑end) for non‑technical users.
- Accessibility features and localization.

## Setup and Usage
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env  # or edit .env
# Fill GOOGLE_API_KEY, GOOGLE_MAPS_API_KEY, GOOGLE_PLACES_API_KEY, AMADEUS_API_KEY/SECRET

# Run itinerary generation
python agent.py "San Francisco" "Los Angeles" --itinerary

# Test flight search (Amadeus sandbox)
python -c "from tools import search_flights; print(search_flights('San Francisco','New York','2025-12-01'))"

# Test restaurant search
python -c "from agent import restaurant_search_tool; print(restaurant_search_tool('San Francisco', cuisine='italian', min_rating=4.0, limit=3))"

# Run tests
python3 -m pytest test_tools.py -v
```

## Ethical Considerations
- Sustainability data (emissions, air quality) should be communicated transparently; estimates are simplified.
- Respect API terms and rate limits; avoid scraping beyond allowed usage.
- Provide clear privacy expectations; this project does not store user data.
- Encourage greener choices without coercion; balance cost, accessibility, and user needs.

## References
- Amadeus for Developers: https://developers.amadeus.com
- Open‑Meteo API: https://open-meteo.com
- OpenStreetMap Nominatim: https://nominatim.openstreetmap.org
- Google Maps Platform (Directions, Places): https://developers.google.com/maps
- Google Generative AI: https://ai.google.dev

## agent prompts
What can you help me with?
Create a Full itinerary from San Francisco to London for January 5th 2026
I would like to explore options for flights this trip?
What about hotels for this trip?
Plan a trip from San Francisco to Las Vegas for December 10th 2025 with some hotel options
What about some restaurants?
whts the current time and weather in Las Vegas
What was my last trip?
And previous to this trip?