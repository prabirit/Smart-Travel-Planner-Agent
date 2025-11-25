import csv
import os
from dataclasses import dataclass
from typing import Optional

import requests
from requests.exceptions import SSLError, RequestException
import certifi
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# Optional Gemini (Generative AI) import
try:
    import google.generativeai as genai  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    genai = None  # Fallback handled below

from datetime import datetime
import ssl
import socket

# Optional dependencies for Open-Meteo rich client
try:
    import openmeteo_requests  # type: ignore
    import pandas as pd  # type: ignore
    import requests_cache  # type: ignore
    from retry_requests import retry  # type: ignore
    _OPENMETEO_AVAILABLE = True
except Exception:  # pragma: no cover - treat any import failure as unavailable
    _OPENMETEO_AVAILABLE = False
    openmeteo_requests = None  # type: ignore
    pd = None  # type: ignore
    requests_cache = None  # type: ignore
    retry = None  # type: ignore


"""Simple sustainable travel planner agent.

Environment variables expected (export before running):
    GOOGLE_API_KEY        -> Gemini API key
    GOOGLE_MAPS_API_KEY   -> Google Maps Directions API key
    WEATHER_API_KEY       -> OpenWeatherMap API key

If macOS SSL errors occur (CERTIFICATE_VERIFY_FAILED), run the macOS Python
Install Certificates script or upgrade certifi:
    open /Applications/Python\\ 3.14/Install\\ Certificates.command
or:
    python -m pip install --upgrade certifi
"""

# Load API keys from environment
GENAI_KEY = os.getenv("GOOGLE_API_KEY")
MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

# Configure Gemini model only if key and library available
if GENAI_KEY and genai is not None:
    try:
        genai.configure(api_key=GENAI_KEY)
        model = genai.GenerativeModel("gemini-2.5-flash")
    except Exception:  # pragma: no cover - network/config errors
        model = None
else:
    model = None  # Graceful fallback – itinerary generation will degrade


def get_route(origin, destination, mode="driving"):
    
    if not MAPS_API_KEY:
        raise RuntimeError("Missing GOOGLE_MAPS_API_KEY environment variable.")
        #return None, None
    url = (
        "https://maps.googleapis.com/maps/api/directions/json?"
        f"origin={origin}&destination={destination}&mode={mode}&key={MAPS_API_KEY}"
    )
    try:
        print(f"[get_route] Fetching route from {origin} to {destination}...")
        resp = requests.get(url, timeout=15, verify=certifi.where())
        resp.raise_for_status()
        data = resp.json()
        #print(f"[get_route] Response data: {data}")
        if data.get("routes"):
            leg = data["routes"][0]["legs"][0]
            return leg["distance"]["text"], leg["duration"]["text"]
    except RequestException as e:
        print(f"[get_route] Request failed: {e}")
    except (KeyError, IndexError) as e:
        print(f"[get_route] Unexpected data format: {e}")
    return None, None

def get_weather(city):
    if not WEATHER_API_KEY:
        return "(weather unavailable: missing WEATHER_API_KEY)"
    url = (
        "https://api.openweathermap.org/data/2.5/weather?"
        f"q={city}&appid={WEATHER_API_KEY}&units=imperial"
    )
    try:
        print(f"[get_weather] Fetching weather for {city}...")
        resp = requests.get(url, timeout=10, verify=certifi.where())
        resp.raise_for_status()
        data = resp.json()
        if "weather" in data and "main" in data:
            return f"{data['weather'][0]['description']}, {data['main']['temp']}°F"
        return "(weather data incomplete)"
    except RequestException as e:
        print(f"[get_weather] Request failed: {e}")
    except (KeyError, IndexError) as e:
        print(f"[get_weather] Unexpected data format: {e}")
    return "(weather unavailable)"

def generate_itinerary(origin, destination, distance, duration, weather):
    """Generate itinerary using Gemini if available; otherwise return a fallback message."""
    distance_txt = distance or "Unknown"
    duration_txt = duration or "Unknown"
    prompt = (
        "Plan a sustainable trip from "
        f"{origin} to {destination}.\n"
        f"Distance: {distance_txt}, Duration: {duration_txt}, Weather at destination: {weather}.\n"
        "Suggest eco-friendly transport options (EV charging, public transit, carpool),"
        " low-impact lodging, and a concise day-by-day itinerary."
    )
    if model is None:
        return (
            "(LLM unavailable – install google-generativeai and set GOOGLE_API_KEY)\n"
            f"Basic trip summary: {origin} -> {destination} | Distance: {distance_txt} | Duration: {duration_txt} | Weather: {weather}"
        )
    try:
        response = model.generate_content(prompt)
        return getattr(response, "text", "(No response text)")
    except Exception as e:  # pragma: no cover - API/runtime errors
        return f"(LLM error: {e}) Fallback summary: {origin}->{destination}, {distance_txt}, {duration_txt}, {weather}"

# Example usage
def main():
    origin = "San Francisco"
    destination = "Las Vegas"
    distance, duration = get_route(origin, destination)
    print(f"Route from {origin} to {destination}: {distance}, {duration}")
    weather = get_weather(destination) 
    print (f"Weather in {destination}: {weather}")
    #itinerary = generate_itinerary(origin, destination, distance, duration, weather)
    #print(itinerary)

####
def fetch_air_quality_openmeteo(city: str) -> str:
    """Alternate air quality fetch using Open-Meteo's air quality API.

    Behaves gracefully if optional dependencies are missing.
    """
    print(f"[fetch_air_quality_openmeteo] Fetching air quality for {city}...")
    if not _OPENMETEO_AVAILABLE:
        return (
            "Open-Meteo detailed client unavailable (missing optional packages: "
            "openmeteo_requests, pandas, requests_cache, retry_requests). Install them to enable this feature."
        )
    try:
        ca_bundle = os.getenv("REQUESTS_CA_BUNDLE") or certifi.where()
        loc = geocode_city(city)
        if not loc:
            return f"Could not geocode city '{city}'."
        lat, lon = loc

        force_json = os.getenv("OPENMETEO_FORCE_JSON") == "1"

        def _json_request() -> str:
            simple_params = {"latitude": lat, "longitude": lon, "hourly": "pm10,pm2_5", "format": "json"}
            try:
                resp = requests.get(
                    "https://air-quality-api.open-meteo.com/v1/air-quality",
                    params=simple_params,
                    timeout=20,
                    verify=ca_bundle,
                )
                resp.raise_for_status()
                j = resp.json() or {}
                hourly = j.get("hourly", {})
                pm10 = (hourly.get("pm10") or [None])[0]
                pm25 = (hourly.get("pm2_5") or [None])[0]
                return f"Open-Meteo JSON data for {city}: PM10={pm10}, PM2.5={pm25}"
            except Exception as json_err:
                # Automatic insecure retry if explicitly allowed by user
                if os.getenv("OPENMETEO_AUTO_ACCEPT_UNVERIFIED") == "1":
                    try:
                        insecure_resp = requests.get(
                            "https://air-quality-api.open-meteo.com/v1/air-quality",
                            params=simple_params,
                            timeout=20,
                            verify=False,
                        )
                        insecure_resp.raise_for_status()
                        j = insecure_resp.json() or {}
                        hourly = j.get("hourly", {})
                        pm10 = (hourly.get("pm10") or [None])[0]
                        pm25 = (hourly.get("pm2_5") or [None])[0]
                        return (
                            "(Insecure auto-accepted SSL) Open-Meteo JSON data for "
                            f"{city}: PM10={pm10}, PM2.5={pm25}. Disable by unsetting OPENMETEO_AUTO_ACCEPT_UNVERIFIED."
                        )
                    except Exception as insecure_auto_err:
                        return (
                            "Open-Meteo SSL error. Insecure auto attempt failed. Guidance: upgrade certifi, run macOS Install Certificates.command, "
                            "or set REQUESTS_CA_BUNDLE. JSON error: "
                            f"{json_err}; Insecure auto error: {insecure_auto_err}"
                        )
                if os.getenv("OPENMETEO_CAPTURE_CHAIN") == "1":
                    chain_file = os.getenv("OPENMETEO_CHAIN_FILE", "openmeteo_cert.pem")
                    try:
                        ctx = ssl.create_default_context()
                        with socket.create_connection(("air-quality-api.open-meteo.com", 443), timeout=10) as sock:
                            with ctx.wrap_socket(sock, server_hostname="air-quality-api.open-meteo.com") as ssock:
                                der = ssock.getpeercert(True)
                                pem = ssl.DER_cert_to_PEM_cert(der)
                                with open(chain_file, "w") as fh:
                                    fh.write(pem)
                        return (
                            "Open-Meteo SSL error. Wrote leaf certificate to '" + chain_file + "'. "
                            "Add its issuing CA to a bundle and set REQUESTS_CA_BUNDLE to trust securely. Error: " + str(json_err)
                        )
                    except Exception as capture_err:
                        return (
                            "Open-Meteo SSL error and certificate capture failed. Error: "
                            f"{json_err}; Capture error: {capture_err}. Try: openssl s_client -connect air-quality-api.open-meteo.com:443 -showcerts"
                        )
                if os.getenv("OPENMETEO_ALLOW_INSECURE") == "1":
                    try:
                        resp = requests.get(
                            "https://air-quality-api.open-meteo.com/v1/air-quality",
                            params=simple_params,
                            timeout=20,
                            verify=False,
                        )
                        resp.raise_for_status()
                        j = resp.json() or {}
                        hourly = j.get("hourly", {})
                        pm10 = (hourly.get("pm10") or [None])[0]
                        pm25 = (hourly.get("pm2_5") or [None])[0]
                        return (
                            "Insecure SSL bypass (NOT recommended) succeeded. Set OPENMETEO_ALLOW_INSECURE=0 to disable. "
                            f"PM10={pm10}, PM2.5={pm25}"
                        )
                    except Exception as insecure_err:
                        return (
                            "Open-Meteo SSL error; insecure bypass also failed. Guidance: upgrade certifi (pip install --upgrade certifi), "
                            "run macOS Install Certificates.command, or set REQUESTS_CA_BUNDLE=/path/to/corporate-ca.pem. "
                            f"JSON fallback error: {json_err}; Insecure error: {insecure_err}"
                        )
                return (
                    "Open-Meteo JSON request SSL error. Guidance: upgrade certifi, run macOS Install Certificates.command, or set REQUESTS_CA_BUNDLE=/path/to/ca.pem. "
                    "Export OPENMETEO_ALLOW_INSECURE=1 to bypass (NOT recommended). "
                    f"JSON error: {json_err}"
                )

        if force_json:
            return _json_request()

        # First attempt: rich client (flatbuffers) for efficiency unless forced JSON
        try:
            cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
            cache_session.verify = ca_bundle
            retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
            openmeteo = openmeteo_requests.Client(session=retry_session)
            responses = openmeteo.weather_api(
                "https://air-quality-api.open-meteo.com/v1/air-quality",
                params={"latitude": lat, "longitude": lon, "hourly": ["pm10", "pm2_5"]},
            )
            response = responses[0]
            hourly = response.Hourly()
            hourly_pm10 = hourly.Variables(0).ValuesAsNumpy()
            hourly_pm2_5 = hourly.Variables(1).ValuesAsNumpy()
            hourly_data = {
                "date": pd.date_range(
                    start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                    end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                    freq=pd.Timedelta(seconds=hourly.Interval()),
                    inclusive="left",
                ),
                "pm10": hourly_pm10,
                "pm2_5": hourly_pm2_5,
            }
            hourly_dataframe = pd.DataFrame(data=hourly_data)
            return f"Air quality data (Open-Meteo) for {city}: {hourly_dataframe.head()}"
        except Exception as rich_err:
            if "CERTIFICATE_VERIFY_FAILED" in str(rich_err) or isinstance(rich_err, SSLError):
                # Attempt JSON fallback
                json_result = _json_request()
                if json_result.startswith("Open-Meteo JSON data"):
                    return "Open-Meteo SSL issue with flatbuffers client. " + json_result
                return json_result
            return f"Air quality client error: {rich_err}"
    except Exception as outer:
        return f"Air quality API error (Open-Meteo): {outer}"



OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
# OpenAQ v3: use /latest endpoint for city-based query (free, no key required for basic usage)
OPENAQ_URL = "https://api.openaq.org/v3/latest"

OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY")

# Prepare a shared Session with certifi root CAs and basic retry strategy
_session = requests.Session()
_session.verify = certifi.where()
_retries = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
_session.mount("https://", HTTPAdapter(max_retries=_retries))
_DEFAULT_TIMEOUT = 15

# Data classes (restored after refactor)
@dataclass
class Weather:
    temperature_c: float
    wind_speed_ms: float
    humidity: Optional[float]
    description: str

@dataclass
class AirQuality:
    pm25: Optional[float]
    pm10: Optional[float]
    source: str

# Simple geocoding (Nominatim)

def geocode_city(city: str):
    """Very lightweight geocoding using Nominatim (no key)."""
    try:
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": city, "format": "json", "limit": 1},
            headers={"User-Agent": "sustainability-starter/1.0"},
            timeout=_DEFAULT_TIMEOUT,
            verify=certifi.where(),
        )
        resp.raise_for_status()
        data = resp.json() or []
        if not data:
            return None
        first = data[0]
        return float(first.get("lat")), float(first.get("lon"))
    except SSLError as e:
        print("[geocode_city] SSL error. Certificate verify failed. "
              "Try: pip install --upgrade certifi OR set REQUESTS_CA_BUNDLE to your CA pem.")
        print(f"[geocode_city] Raw SSL error: {e}")
        return None
    except Exception as e:
        print(f"[geocode_city] Error: {e}")
        return None


def fetch_weather(city: str) -> str:
    loc = geocode_city(city)
    if not loc:
        return f"Could not geocode city '{city}'."
    lat, lon = loc
    params = {
        "latitude": lat,
        "longitude": lon,
        "current_weather": True,
    }
    try:
        r = requests.get(OPEN_METEO_URL, params=params, timeout=_DEFAULT_TIMEOUT, verify=certifi.where())
        r.raise_for_status()
        data = r.json() or {}
        cw = data.get("current_weather", {})
        temp = cw.get("temperature")
        wind = cw.get("windspeed")
        weather = Weather(temperature_c=temp, wind_speed_ms=wind, humidity=None, description="Current conditions")
        return f"Weather in {city}: {weather.temperature_c}°C, wind {weather.wind_speed_ms} m/s."
    except SSLError as e:
        return ("Weather API SSL error: certificate verification failed. Suggestions: upgrade certifi (pip install --upgrade certifi), "
                "or set REQUESTS_CA_BUNDLE=/path/to/ca-bundle.pem if using a corporate proxy. Raw: " + str(e))
    except Exception as e:
        return f"Weather API error: {e}"


def estimate_transport_emissions(mode: str, distance_km: float) -> str:
    """Estimate CO2 emissions using a simple CSV table."""
    csv_path = os.path.join(os.path.dirname(__file__), "emission_factors.csv")
    factors = {}
    with open(csv_path) as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            factors[row["mode"]] = float(row["grams_co2_per_km"])
    if mode not in factors:
        return f"Mode '{mode}' not supported. Choose from: {', '.join(factors.keys())}";
    grams = factors[mode] * distance_km
    kg = grams / 1000.0
    return f"Estimated emissions for {distance_km:.1f} km by {mode}: {kg:.2f} kg CO2"


def fetch_city_time(city: str) -> str:
    """Return an approximate local time for the given city.

    Steps:
      1. Geocode city to get longitude.
      2. Derive a crude UTC offset by rounding lon/15 (360° / 24h = 15° per hour).
      3. Apply offset to current UTC time.

    Notes:
      - This is an approximation; real timezones can differ from simple longitude slices.
      - For higher accuracy, integrate a timezone database (e.g. timezonefinder + pytz).
    """
    from datetime import datetime, timedelta
    loc = geocode_city(city)
    if not loc:
        return f"Could not determine time for '{city}'."
    lat, lon = loc
    print(f"[fetch_city_time] Geocoded {city} to lat={lat}, lon={lon}")
    offset_hours = int(round(lon / 15.0))
    offset = timedelta(hours=offset_hours)
    now_local = (datetime.utcnow().replace(microsecond=0) + offset).isoformat()
    tz_label = 'UTC' if offset_hours == 0 else f"UTC{'+' if offset_hours >= 0 else ''}{offset_hours}"
    return f"Approximate local time in {city}: {now_local} ({tz_label})"


def search_hotels(city: str, limit: int = 5) -> str:
    """Search for hotels in the given city using OpenStreetMap Overpass API.

    Returns a list of hotel names with addresses (if available).
    """
    loc = geocode_city(city)
    if not loc:
        return f"Could not geocode city '{city}' for hotel search."
    lat, lon = loc
    
    # Overpass API query for hotels (tourism=hotel) within ~5km radius
    radius = 5000  # meters
    overpass_url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json][timeout:25];
    (
      node["tourism"="hotel"](around:{radius},{lat},{lon});
      way["tourism"="hotel"](around:{radius},{lat},{lon});
    );
    out body {limit};
    """
    print(f"[search_hotels] Querying Overpass API for hotels in {city}..")
    #print("query parameters:", {"data": query})

    try:
        resp = requests.post(
            overpass_url,
            data={"data": query},
            timeout=30,
            verify=certifi.where(),
        )
        resp.raise_for_status()
        data = resp.json()
        elements = data.get("elements", [])

        if not elements:
            return f"No hotels found in {city} (within {radius/1000:.1f}km radius)."

        def _estimate_price(stars: int | None) -> tuple[float, str]:
            """Return (midpoint_price_usd, display_range). Heuristic mapping from star rating.
            If stars is None, use a generic mid-range fallback.
            """
            mapping = {
                5: (325, "$250-$400"),
                4: (240, "$180-$300"),
                3: (160, "$120-$200"),
                2: (100, "$80-$120"),
                1: (65, "$50-$80"),
            }
            return mapping.get(stars, (140, "$100-$180"))

        enriched = []
        for elem in elements:
            tags = elem.get("tags", {})
            name = tags.get("name", "(unnamed hotel)")
            addr_parts = []
            if "addr:street" in tags:
                street = tags.get("addr:street", "")
                number = tags.get("addr:housenumber", "")
                addr_parts.append(f"{number} {street}".strip())
            if "addr:city" in tags:
                addr_parts.append(tags["addr:city"])
            address = ", ".join(addr_parts) if addr_parts else "(address unavailable)"
            # Star rating if present (as string) -> int
            raw_stars = tags.get("stars")
            try:
                stars_int = int(raw_stars) if raw_stars is not None else None
            except ValueError:
                stars_int = None
            mid_price, price_range = _estimate_price(stars_int)
            enriched.append({
                "name": name,
                "address": address,
                "stars": stars_int,
                "mid_price": mid_price,
                "price_range": price_range,
            })

        # Sort by estimated midpoint price ascending (cheapest first)
        enriched.sort(key=lambda h: h["mid_price"])
        top = enriched[:limit]

        lines = []
        for h in top:
            stars_display = f"{h['stars']}★" if h['stars'] else "(unrated)"
            lines.append(
                f"- {h['name']} | {stars_display} | {h['address']} | Est. price: {h['price_range']}"
            )

        disclaimer = (
            "Price ranges are heuristic estimates derived from OSM star ratings; "
            "they are not real-time prices. For actual rates, consult a booking provider."
        )
        return f"Top {len(top)} hotels (cheapest first) in {city}:\n" + "\n".join(lines) + "\n" + disclaimer
    except SSLError as e:
        return (f"Hotel search SSL error for {city}. Suggestions: upgrade certifi, set REQUESTS_CA_BUNDLE. Raw: {e}")
    except Exception as e:
        return f"Hotel search error for {city}: {e}"


# ==== Real-time hotel pricing via Amadeus Self-Service API ====
# Requires AMADEUS_API_KEY (client id) and AMADEUS_API_SECRET (client secret) in env.
# Falls back to heuristic OSM hotel search if credentials missing or API errors.

AMADEUS_API_KEY = os.getenv("AMADEUS_API_KEY")
AMADEUS_API_SECRET = os.getenv("AMADEUS_API_SECRET")
_AMADEUS_TOKEN: str | None = None
_AMADEUS_TOKEN_EXP: float = 0.0

def _amadeus_get_token() -> str | None:
    import time
    global _AMADEUS_TOKEN, _AMADEUS_TOKEN_EXP

    #print("[amadeus] Fetching access token...")
    if not (AMADEUS_API_KEY and AMADEUS_API_SECRET):
        print("[amadeus] Missing API credentials.")
        return None
    # Reuse token if still valid (leave 60s safety margin)
    if _AMADEUS_TOKEN and time.time() < _AMADEUS_TOKEN_EXP - 60:
        return _AMADEUS_TOKEN
    try:
        resp = requests.post(
            "https://test.api.amadeus.com/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": AMADEUS_API_KEY,
                "client_secret": AMADEUS_API_SECRET,
            },
            timeout=20,
            verify=certifi.where(),
        )
        resp.raise_for_status()
        j = resp.json() or {}
        _AMADEUS_TOKEN = j.get("access_token")
        expires_in = j.get("expires_in", 1800)
        import time as _t
        _AMADEUS_TOKEN_EXP = _t.time() + expires_in
        return _AMADEUS_TOKEN
    except Exception as e:
        print(f"[amadeus] token error: {e}")
        return None

def search_hotels_realtime(city: str, limit: int = 5) -> str:
    """Search hotels with real-time pricing using Amadeus workflow:

    1. List hotels by geocode (v1/reference-data/locations/hotels/by-geocode) to obtain hotelIds.
    2. Fetch offers/prices for those hotelIds (v3/shopping/hotel-offers).
    3. Return cheapest 'limit' hotels with total price.

    Falls back to heuristic OSM search if any step fails or no offers found.
    Dates are derived from environment overrides: AMADEUS_CHECKIN_OFFSET_DAYS and AMADEUS_STAY_NIGHTS.
    """
    token = _amadeus_get_token()
    if not token:
        return "(Real-time pricing unavailable: missing or invalid Amadeus credentials)\n" + search_hotels(city, limit)

    loc = geocode_city(city)
    if not loc:
        return f"Could not geocode city '{city}'."
    lat, lon = loc

    # Determine check-in/check-out dates
    from datetime import date, timedelta
    try:
        offset_days = int(os.getenv("AMADEUS_CHECKIN_OFFSET_DAYS", "7"))
    except ValueError:
        offset_days = 7
    try:
        stay_nights = int(os.getenv("AMADEUS_STAY_NIGHTS", "1"))
    except ValueError:
        stay_nights = 1
    if stay_nights < 1:
        stay_nights = 1
    check_in = date.today() + timedelta(days=offset_days)
    check_out = check_in + timedelta(days=stay_nights)
    check_in_str = check_in.isoformat()
    check_out_str = check_out.isoformat()

    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: list hotels by geocode
    list_params = {
        "latitude": lat,
        "longitude": lon,
        "radius": 5,
        "radiusUnit": "MILE",
    }
    try:
        list_resp = requests.get(
            "https://test.api.amadeus.com/v1/reference-data/locations/hotels/by-geocode",
            params=list_params,
            headers=headers,
            timeout=20,
            verify=certifi.where(),
        )
        if not list_resp.ok:
            return f"(Amadeus hotel listing error {list_resp.status_code})\n" + search_hotels(city, limit)
        list_json = list_resp.json() or {}
        hotels_data = list_json.get("data", [])
        print(f"[amadeus] Found {len(hotels_data)} hotels in listing.")
        hotel_ids = [h.get("hotelId") for h in hotels_data if h.get("hotelId")]
        if not hotel_ids:
            return "(No hotel IDs from Amadeus geocode; fallback)\n" + search_hotels(city, limit)
        # Limit number of hotelIds to avoid very large requests
        hotel_ids = hotel_ids[:min(len(hotel_ids), 20)]
    except Exception as e:
        return f"(Amadeus listing exception: {e})\n" + search_hotels(city, limit)

    # Step 2: fetch offers for collected hotel IDs (batch request)
    offers_params = {
        "hotelIds": ",".join(hotel_ids),
        "adults": 1,
        "checkInDate": check_in_str,
        "checkOutDate": check_out_str,
        "roomQuantity": 1,
        "paymentPolicy": "NONE",
        "bestRateOnly": "true",
    }
    try:
        offers_resp = requests.get(
            "https://test.api.amadeus.com/v3/shopping/hotel-offers",
            params=offers_params,
            headers=headers,
            timeout=25,
            verify=certifi.where(),
        )
        print("offers_resp status:", offers_resp.status_code)
        print("offers_resp text:", offers_resp.text)
        if not offers_resp.ok:
            return f"(Offers request error {offers_resp.status_code})\n" + search_hotels(city, limit)
        offers_json = offers_resp.json() or {}
        data_arr = offers_json.get("data", [])
        priced_hotels: list[dict] = []
        for entry in data_arr:
            hotel_info = entry.get("hotel", {})
            name = hotel_info.get("name", "(unnamed)")
            addr_lines = hotel_info.get("address", {}).get("lines", [])
            address = ", ".join(addr_lines) if addr_lines else "(address unavailable)"
            offers = entry.get("offers", [])
            cheapest_price = None
            currency = "USD"
            for off in offers:
                price_obj = off.get("price", {})
                total = price_obj.get("total")
                currency = price_obj.get("currency", currency)
                try:
                    val = float(total) if total is not None else None
                except ValueError:
                    val = None
                if val is not None and (cheapest_price is None or val < cheapest_price):
                    cheapest_price = val
            if cheapest_price is not None:
                priced_hotels.append({
                    "name": name,
                    "address": address,
                    "price": cheapest_price,
                    "currency": currency,
                })
        if not priced_hotels:
            return "(No priced offers; fallback heuristic list)\n" + search_hotels(city, limit)
        priced_hotels.sort(key=lambda h: h["price"])  # cheapest first
        top = priced_hotels[:limit]
        lines = [f"- {h['name']} | {h['address']} | {h['price']:.2f} {h['currency']}" for h in top]
        disclaimer = (
            "Prices from Amadeus Sandbox for dates "
            f"{check_in_str} to {check_out_str}; may not reflect live market. Verify before booking."
        )
        return (
            f"Real-time hotel prices (Amadeus) in {city} (cheapest first):\n" +
            "\n".join(lines) + "\n" + disclaimer
        )
    except SSLError as e:
        return f"(SSL error contacting Amadeus offers: {e})\n" + search_hotels(city, limit)
    except Exception as e:
        return f"(Amadeus offers exception: {e})\n" + search_hotels(city, limit)


# Test function to run the agent
if __name__ == "__main__":
    #Test 1: Weather for the same city
    #print("\n\n=== Test 1: Get Weather for San Francisco ===")
    #result = fetch_city_time("San Francisco")
    #print(result)

    
    #print("\n\n=== Test 2: Get Air Quality for San Francisco (Open-Meteo) ===")
    #om_result = fetch_air_quality_openmeteo("San Francisco")
    #print(om_result)

    print("\n\n=== Test 3: Search Hotels in London ===")
    om_result = search_hotels_realtime("London", limit=5)
    print(om_result)

    #main()
