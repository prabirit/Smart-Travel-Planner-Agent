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

### Restaurant Recommendations
The agent includes restaurant search using **Google Places API** with support for cuisine filters, price levels, and ratings:

**Implementation** (`agent.py`):
- Direct REST API calls to Google Places Nearby Search
- Uses Nominatim for geocoding (free, no API key required)
- Filters by cuisine type, price level (1-4), and minimum rating
- Returns top restaurants sorted by rating with:
  - Name, rating, and review count
  - Price level indicators (💰)
  - Open/closed status
  - Address and Place ID

**Usage**:
```python
# Ask the agent for restaurant recommendations
"Find me top italian restaurants in San Francisco with ratings above 4.0"
"Show me affordable vegetarian restaurants in New York"
"What are the best restaurants near Times Square?"
```

**Features**:
- **No Event Loop Conflicts**: Works in both standalone scripts and Google ADK web environment
- **Helpful Error Messages**: Clear instructions if APIs aren't enabled
- **Free Geocoding**: Uses OpenStreetMap Nominatim (no extra API key)
- **Flexible Filters**: Combine cuisine, price, and rating filters

### Itinerary Generation
Combines route distance (Google Directions if `GOOGLE_MAPS_API_KEY` available), weather, air quality, emissions, and preferred mode to generate a 3–5 day sustainable itinerary via Gemini (`GOOGLE_API_KEY`). Falls back to a static template if LLM unavailable.

## Environment Variables (`.env`)
```
GOOGLE_API_KEY=              # Gemini API key
GOOGLE_MAPS_API_KEY=         # Google Directions API key (optional for route data)
GOOGLE_PLACES_API_KEY=       # Google Places API key (for restaurant MCP server)
WEATHER_API_KEY=             # OpenWeatherMap API key (optional alternate weather)
OPENAQ_API_KEY=              # Optional for enhanced air quality sources
AMADEUS_API_KEY=             # Amadeus client id (for real-time hotel/flight pricing)
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
7. Restaurant search (requires Google Places API key):
```bash
# MCP server runs automatically when agent uses restaurant_search_tool
python agent.py  # Then ask: "Find italian restaurants in San Francisco"
```

## Setup Instructions

### 1. API Keys Setup
Get your API keys from:
- **Google AI Studio**: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) (for Gemini)
- **Google Cloud Console**: [https://console.cloud.google.com/apis/credentials](https://console.cloud.google.com/apis/credentials) (for Maps & Places)
  - **Required APIs to Enable** ([API Library](https://console.cloud.google.com/apis/library)):
    - **Maps Directions API** (for route planning)
    - **Places API** (for restaurant search) - **Must enable the LEGACY Places API, not "Places API (New)"**
    - **Geocoding API** (optional - fallback if Nominatim fails)
  - **Important**: 
    - The restaurant feature uses the **legacy Places API (Nearby Search)**
    - The "Places API (New)" uses different endpoints and won't work
    - After enabling, wait 2-5 minutes for API activation to propagate
- **Amadeus for Developers**: [https://developers.amadeus.com](https://developers.amadeus.com) (for hotel/flight pricing)

### 2. Testing Restaurant Search
The restaurant search uses direct API calls and works immediately after enabling the Places API:

```python
from agent import restaurant_search_tool

# Search for restaurants
result = restaurant_search_tool(
    location="San Francisco, CA",
    cuisine="italian",
    min_rating=4.0,
    price_level=2,  # 1=cheap, 2=moderate, 3=expensive, 4=very expensive
    limit=5
)
print(result)
```

**If you see an error about API not enabled:**
1. Go to [Google Cloud API Library](https://console.cloud.google.com/apis/library)
2. Search for "Places API" (legacy version, not "Places API (New)")
3. Click "Enable"
4. Wait 2-5 minutes for activation

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
- **Google Places API**: `place/nearbysearch/json` for restaurant recommendations

## Example Usage

### Complete Travel Planning
```python
from agent import root_agent

# Ask the agent to plan a complete trip
response = root_agent.query(
    "Plan a 3-day sustainable trip from San Francisco to Los Angeles. "
    "Include hotel recommendations, restaurant suggestions, and flight options."
)
print(response)
```

### Restaurant Search Examples
```python
# Via agent (recommended)
"Find top 5 italian restaurants in San Francisco with ratings above 4.0"
"Show me affordable vegetarian restaurants in New York (price level 1-2)"
"What are the best restaurants near Golden Gate Park?"

# Direct tool call
from agent import restaurant_search_tool
results = restaurant_search_tool(
    location="San Francisco, CA",
    cuisine="italian",
    min_rating=4.0,
    price_level=2,
    limit=5
)
print(results)
```

## Disclaimers
- Estimated emission factors are simplified and not lifecycle-complete.
- OSM-based price ranges are heuristic and may not match real rates.
- Amadeus Sandbox prices may differ from production/live vendor pricing.
- SSL bypass flags (`OPENMETEO_ALLOW_INSECURE`, etc.) are for debugging only—avoid in production.

## MCP Server Reference (Optional)

This repository includes a **reference MCP server implementation** (`restaurant_server.py`) that demonstrates the **Model Context Protocol** architecture. The main agent uses direct API calls for simplicity and compatibility, but you can adapt the MCP pattern for other features.

### Why MCP?
- **Separation of Concerns**: Search logic isolated in dedicated server
- **Reusability**: Same server can be used by multiple agents/applications
- **Independent Scaling**: Server can be optimized/updated without changing agent code
- **Language Agnostic**: MCP servers can be written in any language
- **Standardized Communication**: JSON-RPC protocol ensures compatibility

**Note**: The restaurant search currently uses direct API calls to avoid async event loop conflicts in Google ADK web environment. The MCP server (`restaurant_server.py`) is included as a reference for building other capabilities.

### Adding More MCP Servers
You can easily add more capabilities by creating additional MCP servers:

1. **Create server** (e.g., `events_server.py`) following the pattern in `restaurant_server.py`
2. **Add client integration** in `agent.py`:
   ```python
   async def _init_events_client():
       server_params = StdioServerParameters(
           command="python3",
           args=[str(_HERE / "events_server.py")]
       )
       ...
   ```
3. **Create tool wrapper** and add to `root_agent.tools`
4. **Update instructions** to include new capability

**Suggested MCP Servers:**
- 🎭 Local Events & Activities (Ticketmaster/Eventbrite API)
- 💱 Currency Exchange & Budget Tracking
- 🚇 Public Transit Directions (city-specific transit APIs)
- ⚠️ Travel Alerts & Safety Advisories
- 🎫 Ticket Booking Integration

## Roadmap Ideas
- Add caching for Amadeus responses to save quota.
- Integrate timezone database for accurate local times.
- Add unit tests for hotel pricing logic.
- Support multi-currency selection.
- Implement more MCP servers (events, currency, transit, safety)
- Add MCP server discovery and dynamic tool registration

## License
See `LICENSE` file.

---

## Capstone Report
For a comprehensive project write‑up covering problem statement, architecture, implementation details, testing results, limitations, and future work, see `CAPSTONE.md`.
