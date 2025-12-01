# Smart Travel Planner Agent - Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACE LAYER                                │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │  CLI Interface / Google ADK Web UI / Agent Query Interface           │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          AGENT ORCHESTRATION LAYER                           │
│                                                                              │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │                    Root Sustainability Agent                         │   │
│   │                  (Gemini 2.5 Flash Lite Model)                       │   │
│   │                                                                      │   │
│   │  • Route planning & coordination                                     │   │
│   │  • Tool selection & invocation                                       │   │
│   │  • Response synthesis                                                │   │
│   │  • Session management (InMemory/Database)                            │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                                      │                                       │
│                                      ▼                                       │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │                    Itinerary Planning Agent Tool                     │   │
│   │                    (Gemini 2.5 Flash Model)                          │   │
│   │                                                                      │   │
│   │  • Multi-day itinerary generation                                    │   │
│   │  • Sustainability recommendations                                    │   │
│   │  • Emissions reduction suggestions                                   │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            TOOL LAYER                                       │
│                                                                             │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                 │
│  │ weather_tool   │  │  timer_tool    │  │air_quality_tool│                 │
│  └────────────────┘  └────────────────┘  └────────────────┘                 │
│                                                                             │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                 │
│  │hotel_search    │  │flight_search   │  │restaurant_     │                 │ 
│  │_tool           │  │_tool           │  │search_tool     │                 │
│  └────────────────┘  └────────────────┘  └────────────────┘                 │
│                                                                             │
│  ┌────────────────┐  ┌────────────────────────────────────┐                 │
│  │transport_      │  │    itinerary_tool                  │                 │
│  │emissions_tool  │  │  (Wrapper for sub-agent)           │                 │
│  └────────────────┘  └────────────────────────────────────┘                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      EXTERNAL API INTEGRATION LAYER                         │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    Weather & Air Quality APIs                        │   │
│  │  • Open-Meteo API (primary - weather & air quality)                  │   │
│  │  • OpenWeatherMap API (fallback - requires key)                      │   │
│  │  • OpenAQ API (optional enhanced air quality)                        │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │ 
│  │                    Location & Mapping APIs                           │   │
│  │  • Nominatim/OpenStreetMap (free geocoding)                          │   │
│  │  • Google Maps Directions API (route planning - optional)            │   │
│  │  • Google Places API (restaurant search - requires key)              │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    Travel Booking APIs                               │   │
│  │  • Amadeus Self-Service API                                          │   │
│  │    - Hotel search by geocode (v1/reference-data/locations/hotels)    │   │
│  │    - Hotel pricing (v3/shopping/hotel-offers)                        │   │
│  │    - Airport/city lookup (v1/reference-data/locations)               │   │
│  │    - Flight search (v2/shopping/flight-offers)                       │   │
│  │  • OpenStreetMap Overpass API (fallback hotel search)                │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │                    LLM & AI Services                                 │   │
│  │  • Google Generative AI (Gemini)                                     │   │
│  │    - gemini-2.5-flash-lite (main agent)                              │   │
│  │    - gemini-2.5-flash (itinerary sub-agent)                          │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DATA & UTILITIES LAYER                             │
│                                                                             │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                 │
│  │emission_factors│  │Session Service │  │ Logging Plugin │                 │
│  │.csv (local DB) │  │(Memory/SQLite) │  │                │                 │
│  └────────────────┘  └────────────────┘  └────────────────┘                 │
│                                                                             │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                 │
│  │ Retry Logic    │  │ SSL/TLS Config │  │ Response Cache │                 │
│  │ (HTTP Adapter) │  │ (Certifi)      │  │ (requests)     │                 │
│  └────────────────┘  └────────────────┘  └────────────────┘                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Overview

### 1. Weather & Air Quality Query
```
User Request → Root Agent → weather_tool/air_quality_tool 
           → Open-Meteo API → Parse Response → Format Output → User
```

### 2. Hotel Search (Real-time Pricing)
```
User Request → Root Agent → hotel_search_tool → Amadeus Token Auth
           → Amadeus Hotel Geocode API → Get Hotel IDs
           → Amadeus Hotel Offers API → Sort by Price → User
           (Fallback: OSM Overpass API for heuristic search)
```

### 3. Flight Search
```
User Request → Root Agent → flight_search_tool → Amadeus Token Auth
           → Location API (IATA codes) → Flight Offers API
           → Sort by Price → Format Results → User
```

### 4. Restaurant Search
```
User Request → Root Agent → restaurant_search_tool 
           → Nominatim Geocoding → Google Places API
           → Filter by Cuisine/Price/Rating → User
```

### 5. Complete Itinerary Generation
```
User Request → Root Agent → itinerary_tool 
           → Itinerary Sub-Agent → Collect Context:
             ├─ Route Data (Google Maps)
             ├─ Weather (Open-Meteo)
             ├─ Air Quality (Open-Meteo)
             ├─ Emissions (CSV lookup)
             └─ Local Time (calculated)
           → Gemini LLM Generation → 3-5 Day Plan → User
```

## Component Details

### Agent Layer (agent.py)
- **Root Agent**: Primary orchestrator using Gemini 2.5 Flash Lite
  - Manages tool selection and invocation
  - Handles session persistence (InMemory or SQLite)
  - Configured with retry logic for API resilience
  
- **Itinerary Sub-Agent**: Specialized planning agent
  - Uses Gemini 2.5 Flash model
  - Generates sustainable travel plans
  - Composes data from multiple tool calls

### Tool Layer (tools.py)
Core functions wrapped as ADK tools:
- **fetch_weather()**: Temperature, wind, humidity from Open-Meteo
- **fetch_city_time()**: Calculates local time via longitude offset
- **fetch_air_quality_openmeteo()**: PM2.5, PM10 data with SSL error handling
- **estimate_transport_emissions()**: CO2 calculations from CSV factors
- **geocode_city()**: Free geocoding via Nominatim OSM
- **search_hotels()**: OSM Overpass heuristic search (fallback)
- **search_hotels_realtime()**: Amadeus API with date-based pricing
- **search_flights()**: Amadeus flight offers with IATA lookup
- **restaurant_search()**: Google Places API with filters

### API Authentication & Error Handling
- **Amadeus**: OAuth2 client credentials flow with token caching
- **Google APIs**: API key authentication
- **Retry Strategy**: 5 attempts with exponential backoff for 429/5xx errors
- **SSL/TLS**: Certifi certificate bundle with fallback options
- **Graceful Degradation**: Automatic fallback when premium APIs unavailable


## Key Design Principles

1. **Sustainability First**: Prioritizes low-carbon transport modes, emissions tracking
2. **Graceful Degradation**: Falls back to free/heuristic APIs when premium services unavailable
3. **Modular Architecture**: Clear separation between agents, tools, and API integrations
4. **Error Resilience**: Comprehensive retry logic, SSL handling, and fallback mechanisms
5. **Session Management**: Supports both ephemeral (InMemory) and persistent (SQLite) sessions
6. **Extensibility**: MCP server pattern for adding new capabilities (reference implementation included)
