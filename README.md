# Smart Travel Planner Agent

Sustainable travel planning assistant providing:
- Current weather (Open-Meteo / OpenWeatherMap fallback)
- Approximate local time calculations
- Air quality (Open-Meteo rich or JSON fallback)
- Transport emissions estimation from CSV factors
- Hotel search (OSM heuristic) with star-based price range estimates
- Real-time hotel pricing (Amadeus Self-Service API)
- Flight search with real-time pricing (Amadeus Self-Service API)
- Multi-day sustainable itinerary generation (Gemini)

## Features

### Hotel Search (Heuristic)
Uses OpenStreetMap Overpass API to list nearby hotels within 5 km, estimating a price range from `stars` tags. These ranges are heuristic only.

### Real-Time Hotel Pricing (Amadeus)
If `AMADEUS_API_KEY` and `AMADEUS_API_SECRET` are set, the agent uses a two-step workflow:
1. **List hotels by location**: Queries `v1/reference-data/locations/hotels/by-geocode` to obtain hotel IDs within 5 miles.
2. **Fetch pricing**: Calls `v3/shopping/hotel-offers` with collected hotel IDs, check-in/out dates, and returns cheapest offers sorted by price.

Check-in dates are computed as `AMADEUS_CHECKIN_OFFSET_DAYS` (default 7) days from today; stay duration is `AMADEUS_STAY_NIGHTS` (default 1). Falls back automatically to heuristic OSM list if:
- Credentials missing
- Token request fails
- No hotel IDs or offers returned

**Important**: Sandbox data may be synthetic, limited, or not reflect current market rates. Always verify rates before booking. For production-grade pricing or larger quotas, upgrade your Amadeus plan to Production environment.

### Flight Search (Amadeus)
If `AMADEUS_API_KEY` and `AMADEUS_API_SECRET` are set, the agent searches for flights using:
1. **Airport code lookup**: Converts city names to IATA codes via `v1/reference-data/locations`.
2. **Flight offers search**: Queries `v2/shopping/flight-offers` for available flights with pricing.

Results include carrier, flight number, departure/arrival times, duration, stops, and total price sorted by cheapest first. Departure date defaults to `AMADEUS_CHECKIN_OFFSET_DAYS` from today (configurable via environment variable).

### Itinerary Generation
Combines route distance (Google Directions if `GOOGLE_MAPS_API_KEY` available), weather, air quality, emissions, and preferred mode to generate a 3–5 day sustainable itinerary via Gemini (`GOOGLE_API_KEY`). Falls back to a static template if LLM unavailable.

## Environment Variables (`.env`)
```
GOOGLE_API_KEY=              # Gemini API key
GOOGLE_MAPS_API_KEY=         # Google Directions API key (optional for route data)
WEATHER_API_KEY=             # OpenWeatherMap API key (optional alternate weather)
OPENAQ_API_KEY=              # Optional for enhanced air quality sources
AMADEUS_API_KEY=             # Amadeus client id (for real-time hotel pricing)
AMADEUS_API_SECRET=          # Amadeus client secret
AMADEUS_CHECKIN_OFFSET_DAYS=7 # Days from today for hotel check-in (default 7)
AMADEUS_STAY_NIGHTS=1        # Number of nights for hotel stay (default 1)
REQUESTS_CA_BUNDLE=          # Optional custom CA bundle path
OPENMETEO_FORCE_JSON=0       # Force JSON air quality mode
OPENMETEO_AUTO_ACCEPT_UNVERIFIED=0
OPENMETEO_ALLOW_INSECURE=0
OPENMETEO_CAPTURE_CHAIN=0
OPENMETEO_CHAIN_FILE=openmeteo_cert.pem
```

## Quick Start
1. Clone repo
2. Create and fill `.env`
3. Install dependencies:
```bash
pip install -r requirements.txt
```
4. Run agent test script:
```bash
python agent.py "San Francisco" "Los Angeles" --itinerary
```
5. Hotel search (heuristic):
```bash
python tools.py
```
6. Flight search (requires Amadeus credentials):
```python
from tools import search_flights
print(search_flights("San Francisco", "New York", "2025-12-01"))
```

## Real-Time Pricing Integration Steps
1. Sign up at [Amadeus for Developers](https://developers.amadeus.com) and create an application in Test (Sandbox) mode.
2. Copy your **Client ID** (`AMADEUS_API_KEY`) and **Client Secret** (`AMADEUS_API_SECRET`) to `.env`.
3. (Optional) Adjust `AMADEUS_CHECKIN_OFFSET_DAYS` and `AMADEUS_STAY_NIGHTS` to customize date logic.
4. Re-run any hotel search through the agent; pricing will auto-switch to real-time Amadeus workflow.

**Note**: The agent workflow uses:
- `v1/reference-data/locations/hotels/by-geocode` (hotel discovery)
- `v3/shopping/hotel-offers` (hotel pricing with date parameters)
- `v1/reference-data/locations` (airport/city code lookup for flights)
- `v2/shopping/flight-offers` (flight search and pricing)

## Disclaimers
- Estimated emission factors are simplified and not lifecycle-complete.
- OSM-based price ranges are heuristic and may not match real rates.
- Amadeus Sandbox prices may differ from production/live vendor pricing.
- SSL bypass flags (`OPENMETEO_ALLOW_INSECURE`, etc.) are for debugging only—avoid in production.

## Roadmap Ideas
- Add caching for Amadeus responses to save quota.
- Integrate timezone database for accurate local times.
- Add unit tests for hotel pricing logic.
- Support multi-currency selection.

## License
See `LICENSE` file.
