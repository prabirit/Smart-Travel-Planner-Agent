
from google.adk.agents.llm_agent import Agent
from typing import Callable

import os
import sys
import pathlib
import google.generativeai as genai
import requests
from datetime import datetime
import pytz
from requests.exceptions import RequestException
import certifi
import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv


from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool
from google.adk.models.google_llm import Gemini
from google.genai import types
from google.adk.sessions import InMemorySessionService
from google.adk.runners import InMemoryRunner
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService


from google.adk.plugins.logging_plugin import (
    LoggingPlugin,
) # Example plugin for logging

print("ADK components imported successfully.")

# Load environment variables
load_dotenv()

"""Agent module: provides root sustainability agent and itinerary planning.

Adds an itinerary agent that composes route, weather, air quality and emissions
data, then uses a generative model (Gemini) to produce a sustainable travel plan.
"""

# Ensure local directory is on sys.path for environments launching this file outside its folder (e.g. ADK web UI)
_HERE = pathlib.Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# Import tool functions (prefer relative if part of a package, fallback to absolute)
try:  # package context
    from .tools import (
        fetch_weather,
        fetch_city_time,
        estimate_transport_emissions,
        fetch_air_quality_openmeteo,
        geocode_city,
        search_hotels,
        search_hotels_realtime,
        search_flights,
        restaurant_search
    )
except Exception:  # script / non-package execution
    try:
        from tools import (
            fetch_weather,
            fetch_city_time,
            estimate_transport_emissions,
            fetch_air_quality_openmeteo,
            geocode_city,
            search_hotels,
            search_hotels_realtime,
            search_flights,
            restaurant_search
        )
    except Exception as import_err:
        raise RuntimeError(
            f"Failed to import local tools module. Checked relative and absolute paths. Base directory: {_HERE}. "
            f"Original error: {import_err}"
        )

# Optional: route & weather helpers (duplicated in tools but kept local to avoid circular import)
def _safe_get_route(origin: str, destination: str, mode: str = "driving"):
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not api_key:
        return None, None, "(route unavailable: missing GOOGLE_MAPS_API_KEY)"
    url = (
        "https://maps.googleapis.com/maps/api/directions/json?"
        f"origin={origin}&destination={destination}&mode={mode}&key={api_key}"
    )
    try:
        resp = requests.get(url, timeout=20, verify=certifi.where())
        resp.raise_for_status()
        data = resp.json()
        if data.get("routes"):
            leg = data["routes"][0]["legs"][0]
            return leg["distance"]["text"], leg["duration"]["text"], None
        return None, None, "(no routes found)"
    except Exception as e:
        return None, None, f"(route error: {e})"

def _format_distance_km(distance_text: str) -> float | None:
    if not distance_text:
        return None
    # Expect formats like "552 km" or "1,234 km"
    import re
    m = re.search(r"([0-9,.]+)\s*km", distance_text)
    if not m:
        return None
    return float(m.group(1).replace(",", ""))

class ItineraryAgent:
    """Generates a sustainable travel itinerary from origin to destination.

    Steps:
      1. Fetch route distance & duration (Google Maps if key available).
      2. Fetch destination weather & air quality.
      3. Estimate emissions for a default mode (train preferred if distance < 800 km, else car_electric).
      4. Build structured context and invoke Gemini for an itinerary proposal.
      5. Provide fallback textual itinerary if model key missing.
    """

    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        self._llm_ready = False
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self._model = genai.GenerativeModel(model_name)
                self._llm_ready = True
            except Exception as e:
                self._model = None
                self._llm_ready = False
                self._init_error = f"LLM init failed: {e}"
        else:
            self._model = None
            self._init_error = "Missing GOOGLE_API_KEY"

    def create_itinerary(self, origin: str, destination: str, mode: str | None = None) -> str:
        distance_text, duration_text, route_err = _safe_get_route(origin, destination)
        distance_km = _format_distance_km(distance_text) if distance_text else None
        # Heuristic mode selection
        chosen_mode = mode or ("train" if (distance_km and distance_km < 800) else "car_electric")
        emissions = estimate_transport_emissions(chosen_mode, distance_km) if distance_km else "(emissions unavailable)"
        weather = fetch_weather(destination)
        air = fetch_air_quality_openmeteo(destination)
        time_info = fetch_city_time(destination)

        context = (
            f"Origin: {origin}\nDestination: {destination}\n"
            f"Distance: {distance_text or 'Unknown'} | Duration: {duration_text or 'Unknown'}\n"
            f"Weather: {weather}\nAirQuality: {air}\nLocalTime: {time_info}\nEmissions: {emissions}\n"
            f"PreferredMode: {chosen_mode}\n"
        )

        planning_prompt = (
            "Using the provided travel context, craft a 3-5 day sustainable itinerary. "
            "Prioritize low-carbon transport, local experiences, eco-friendly lodging, and concise daily plans. "
            "Include an overview, daily breakdown, sustainability tips, and an emissions reduction suggestion.\n\n" + context
        )

        if self._llm_ready and self._model:
            try:
                resp = self._model.generate_content(planning_prompt)
                llm_text = getattr(resp, "text", "(no model text)")
            except Exception as e:
                llm_text = f"(LLM generation failed: {e})"
        else:
            llm_text = (
                "(LLM unavailable) Draft itinerary:\n" \
                "Day 1: Arrival and orientation; walking tour to minimize transport emissions.\n" \
                "Day 2: Public transit to key sights; choose plant-based meals.\n" \
                "Day 3: Regional nature excursion via train or shared shuttle.\n" \
                "Day 4: Local cultural experiences; support small sustainable businesses.\n" \
                "Day 5: Departure; offset remaining emissions through a reputable program."
            )

        return (
            "=== Sustainable Travel Itinerary ===\n" +
            llm_text + "\n\n=== Raw Context ===\n" + context +
            (f"RouteStatus: {route_err}\n" if route_err else "")
        )


# Wrap tool functions so ADK can call them directly.

def weather_tool(city: str):
    return fetch_weather(city)

def timer_tool(city: str):
    return fetch_city_time(city)

def air_quality_tool(city: str):
    return fetch_air_quality_openmeteo(city)

def transport_emissions_tool(mode: str, distance_km: float):
    return estimate_transport_emissions(mode, distance_km)

def hotel_search_tool(city: str, limit: int = 5):
    # Prefer real-time pricing if Amadeus credentials available
    if os.getenv("AMADEUS_API_KEY") and os.getenv("AMADEUS_API_SECRET"):
        return search_hotels_realtime(city, limit)
    return search_hotels(city, limit)

def flight_search_tool(origin: str, destination: str, departure_date: str | None = None, limit: int = 5):
    return search_flights(origin, destination, departure_date, limit)



def restaurant_search_tool(destination: str, cuisine: str | None = None, price_level: int | None = None, 
    min_rating: float | None = None, limit: int = 5):
    return restaurant_search(destination, cuisine, price_level, min_rating, limit)

# New: itinerary tool wrapping ItineraryAgent
def itinerary_tool(origin: str, destination: str, mode: str = "auto"):
    ia = ItineraryAgent()
    forced_mode = None if mode == "auto" else mode
    return ia.create_itinerary(origin, destination, mode=forced_mode)

# Optional itinerary sub-agent (can be referenced by root agent)
itinerary_sub_agent = Agent(
    model="gemini-2.5-flash",
    name="itinerary_planner_agent",
    description="Generates sustainable multi-day travel itineraries between two cities.",
    instruction=(
        "When asked to plan a trip, call itinerary_tool(origin, destination, mode). "
        "Offer low-carbon transport, daily breakdown, sustainability tips, and emissions reduction suggestions."
    ),
    tools=[itinerary_tool],
    sub_agents=[],
)

#itinerary agent
itinerary_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="itinerary_planner_agent",
    description="Generates sustainable multi-day travel itineraries between two cities.",
    instruction=(
        "When asked to plan a trip, call itinerary_tool(origin, destination, mode). "
        "Offer low-carbon transport, daily breakdown, sustainability tips, and emissions reduction suggestions."
    ),
    tools=[itinerary_tool],
)

#Configure Retry Options
retry_config = types.HttpRetryOptions(
    attempts=5,  # Maximum retry attempts
    exp_base=7,  # Delay multiplier
    initial_delay=1,
    http_status_codes=[429, 500, 503, 504],  # Retry on these HTTP errors
)

# Create the root agent
root_agent = Agent(
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    name="starter_sustainability_agent",
    description="Answers sustainability questions: weather, air quality, transport emissions, current time, hotel search, flight search, restaurant recommendations, and itinerary planning.",
    instruction=(
        "You help with: 1) weather -> weather_tool(city); 2) air quality -> air_quality_tool(city); "
        "3) transport emissions -> transport_emissions_tool(mode, distance_km); 4) current time -> timer_tool(city); "
        "5) itinerary planning -> itinerary_tool(origin, destination, mode); 6) hotel search -> hotel_search_tool(city, limit); "
        "7) flight search -> flight_search_tool(origin, destination, departure_date, limit); "
        "8) restaurant search -> restaurant_search_tool(location, cuisine, price_level, min_rating, limit). "
        "If a user asks for hotels or lodging, use hotel_search_tool. If a user asks for flights, use flight_search_tool. "
        "If a user asks for restaurants or dining recommendations, use restaurant_search_tool. "
        "If a user asks for a trip plan, prefer itinerary_tool which combines multiple tools."
    ),
    tools=[weather_tool, air_quality_tool, transport_emissions_tool, timer_tool, itinerary_tool, hotel_search_tool, flight_search_tool, restaurant_search_tool,
           AgentTool(agent=itinerary_agent),],
    #sub_agents=[itinerary_sub_agent],
)

APP_NAME = "default"  # Application
USER_ID = "default"  # User
SESSION = "default"  # Session

# Set up Session Management
# InMemorySessionService stores conversations in RAM (temporary)
session_service = InMemorySessionService()

# SQLite database will be created automatically
#db_url = "sqlite:///my_smart_travel_agent_data.db"  # Local SQLite file
#session_service = DatabaseSessionService(db_url=db_url)

# Create the Runner
seaaionRunner = Runner(agent=itinerary_agent, app_name=APP_NAME, session_service=session_service)

# Alternatively, use InMemoryRunner with plugins
runner = InMemoryRunner(
    agent=root_agent,
    plugins=[
        LoggingPlugin()
    ],
)

print("Runner configured")

#print("Upgraded to persistent sessions!")
#print(f"   - Database: my_smart_travel_agent_data.db")
#print(f"   - Sessions will survive restarts!")

main_agent = root_agent

import re

def run_query(prompt: str) -> str:
    """Simple dispatcher that interprets the user prompt and calls tool functions directly.

    This replaces the previous attempt to use google-adk's internal streaming API,
    which requires a complex InvocationContext. For local testing we map the prompt
    to tool calls ourselves.
    """
    # Extract city (naive): look for 'in <city>'
    city_match = re.search(r'in ([A-Za-z ,]+)\?', prompt)
    city = city_match.group(1).strip() if city_match else 'San Francisco'

    # Extract distance (km)
    dist_match = re.search(r'(\d+(?:\.\d+)?)\s*km', prompt)
    distance_km = float(dist_match.group(1)) if dist_match else 50.0

    # Infer transport mode
    if 'electric' in prompt.lower():
        mode = 'car_electric'
    elif 'car' in prompt.lower():
        mode = 'car_gas'
    elif 'train' in prompt.lower():
        mode = 'train'
    else:
        mode = 'car_gas'

    weather = weather_tool(city)
    air = air_quality_tool(city)
    time_info = timer_tool(city)
    emissions = transport_emissions_tool(mode, distance_km)
    restaurants = restaurant_search_tool(city, cuisine=None, price_level=None, min_rating=None, limit=5)

    return (
        f"City: {city}\n"
        f"{weather}\n"
        f"{air}\n"
        f"{time_info}\n"
        f"{emissions}\n"
        f"{restaurants}\n"
        f"(Mode inferred: {mode})"
    )

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Sustainability & itinerary agent")
    parser.add_argument("origin", nargs="?", default="San Francisco")
    parser.add_argument("destination", nargs="?", default="Los Angeles")
    parser.add_argument("--itinerary", action="store_true", help="Generate sustainable itinerary")
    parser.add_argument("--mode", help="Force transport mode for emissions (train, car_electric, car_gas, bus)")
    args = parser.parse_args()

    if args.itinerary:
        ia = ItineraryAgent()
        print(ia.create_itinerary(args.origin, args.destination, mode=args.mode))
    else:
        test_prompt = (
            f"What's the weather and air quality in {args.destination}? "
            f"What's the estimated CO2 emissions for a 50 km car trip? "
            f"Also, what is the current time there?"
            f"Can you recommend some restaurants in {args.destination}?"
        )
        response_text = run_query(test_prompt)
        print("Agent response>>>:\n" + response_text)