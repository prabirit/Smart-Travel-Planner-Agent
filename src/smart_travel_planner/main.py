"""Main entry point for Smart Travel Planner Agent."""

import argparse
import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .config import setup_logging, get_settings
from .core.agent import TravelPlannerAgent
from .models.travel_models import TravelRequest
from .exceptions import SmartTravelPlannerError, ConfigurationError
from .utils.validators import validate_location, validate_date_range


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Smart Travel Planner Agent - Sustainable travel planning assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "San Francisco" "Los Angeles" --itinerary
  %(prog)s "New York" "London" --flights --hotels
  %(prog)s "Paris" --weather --restaurants
        """
    )
    
    # Positional arguments
    parser.add_argument(
        "origin",
        help="Origin location (city, airport, or address)"
    )
    
    parser.add_argument(
        "destination",
        nargs="?",
        help="Destination location (city, airport, or address)"
    )
    
    # Date arguments
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date (YYYY-MM-DD format)"
    )
    
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date (YYYY-MM-DD format)"
    )
    
    # Feature flags
    parser.add_argument(
        "--itinerary",
        action="store_true",
        help="Generate complete travel itinerary"
    )
    
    parser.add_argument(
        "--flights",
        action="store_true",
        help="Search for flights"
    )
    
    parser.add_argument(
        "--hotels",
        action="store_true",
        help="Search for hotels"
    )
    
    parser.add_argument(
        "--restaurants",
        action="store_true",
        help="Search for restaurants"
    )
    
    parser.add_argument(
        "--weather",
        action="store_true",
        help="Get weather information"
    )
    
    parser.add_argument(
        "--emissions",
        action="store_true",
        help="Calculate transport emissions"
    )
    
    # Configuration options
    parser.add_argument(
        "--travelers",
        type=int,
        default=1,
        help="Number of travelers (default: 1)"
    )
    
    parser.add_argument(
        "--budget",
        type=float,
        help="Budget in USD"
    )
    
    parser.add_argument(
        "--sustainability",
        choices=["low", "moderate", "high"],
        default="moderate",
        help="Sustainability preference (default: moderate)"
    )
    
    parser.add_argument(
        "--cuisine",
        type=str,
        help="Preferred cuisine type for restaurants"
    )
    
    parser.add_argument(
        "--min-rating",
        type=float,
        help="Minimum rating for hotels and restaurants"
    )
    
    # Output options
    parser.add_argument(
        "--output",
        choices=["table", "json", "simple"],
        default="table",
        help="Output format (default: table)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    
    return parser


def validate_arguments(args) -> None:
    """Validate command line arguments."""
    # Validate locations
    validate_location(args.origin)
    
    if args.destination:
        validate_location(args.destination)
    
    # Validate dates
    if args.start_date or args.end_date:
        if not args.start_date or not args.end_date:
            raise ValueError("Both start-date and end-date must be provided")
        
        validate_date_range(args.start_date, args.end_date)
    
    # Validate travelers
    if args.travelers < 1:
        raise ValueError("Number of travelers must be at least 1")
    
    # Validate budget
    if args.budget and args.budget < 0:
        raise ValueError("Budget cannot be negative")
    
    # Validate rating
    if args.min_rating and (args.min_rating < 0 or args.min_rating > 5):
        raise ValueError("Rating must be between 0 and 5")


def create_travel_request(args) -> TravelRequest:
    """Create travel request from command line arguments."""
    # Set default dates if not provided
    if not args.start_date:
        start_date = date.today() + timedelta(days=7)
    else:
        start_date = date.fromisoformat(args.start_date)
    
    if not args.end_date:
        end_date = start_date + timedelta(days=3)
    else:
        end_date = date.fromisoformat(args.end_date)
    
    # Validate destination for certain features
    destination = args.destination or start_date.isoformat()
    
    return TravelRequest(
        origin=args.origin,
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        travelers=args.travelers,
        budget_usd=args.budget,
        sustainability_preference=args.sustainability,
        cuisine_preferences=[args.cuisine] if args.cuisine else []
    )


def display_results(results: dict, output_format: str = "table") -> None:
    """Display results in the specified format."""
    console = Console()
    
    if output_format == "json":
        import json
        console.print(json.dumps(results, indent=2, default=str))
        return
    
    if output_format == "simple":
        for key, value in results.items():
            console.print(f"{key}: {value}")
        return
    
    # Table format (default)
    if "itinerary" in results:
        display_itinerary(results["itinerary"], console)
    
    if "flights" in results and results["flights"]:
        display_flights(results["flights"], console)
    
    if "hotels" in results and results["hotels"]:
        display_hotels(results["hotels"], console)
    
    if "restaurants" in results and results["restaurants"]:
        display_restaurants(results["restaurants"], console)
    
    if "weather" in results:
        display_weather(results["weather"], console)
    
    if "emissions" in results:
        display_emissions(results["emissions"], console)


def display_itinerary(itinerary, console: Console) -> None:
    """Display travel itinerary."""
    console.print(Panel(f"Travel Itinerary: {itinerary.origin} to {itinerary.destination}", style="bold blue"))
    
    for day in itinerary.days:
        console.print(f"\n[bold]Day {day.day} - {day.date}[/bold]")
        
        if day.activities:
            for activity in day.activities:
                console.print(f"  2022 {activity}")
        
        if day.accommodation:
            console.print(f"  2022 Hotel: {day.accommodation.name}")
        
        if day.meals:
            for meal in day.meals:
                console.print(f"  2022 Dining: {meal.name}")
        
        if day.estimated_emissions:
            console.print(f"  2022 Emissions: {day.estimated_emissions.co2_kg:.2f} kg CO2")


def display_flights(flights, console: Console) -> None:
    """Display flight search results."""
    table = Table(title="Flight Options")
    table.add_column("Airline", style="cyan")
    table.add_column("Flight", style="magenta")
    table.add_column("Route", style="green")
    table.add_column("Departure", style="yellow")
    table.add_column("Duration", style="blue")
    table.add_column("Price", style="red")
    
    for flight in flights:
        table.add_row(
            flight.airline,
            flight.flight_number,
            f"{flight.departure_airport} -> {flight.arrival_airport}",
            flight.departure_time.strftime("%H:%M"),
            f"{flight.duration_hours:.1f}h",
            f"${flight.price:.2f}"
        )
    
    console.print(table)


def display_hotels(hotels, console: Console) -> None:
    """Display hotel search results."""
    table = Table(title="Hotel Options")
    table.add_column("Name", style="cyan")
    table.add_column("Rating", style="magenta")
    table.add_column("Stars", style="yellow")
    table.add_column("Price", style="green")
    table.add_column("Distance", style="blue")
    
    for hotel in hotels:
        table.add_row(
            hotel.name,
            f"{hotel.rating:.1f}" if hotel.rating else "N/A",
            f"{hotel.stars}" if hotel.stars else "N/A",
            hotel.price_range_display,
            f"{hotel.distance_km:.1f} km" if hotel.distance_km else "N/A"
        )
    
    console.print(table)


def display_restaurants(restaurants, console: Console) -> None:
    """Display restaurant search results."""
    table = Table(title="Restaurant Options")
    table.add_column("Name", style="cyan")
    table.add_column("Cuisine", style="magenta")
    table.add_column("Rating", style="yellow")
    table.add_column("Price", style="green")
    table.add_column("Distance", style="blue")
    
    for restaurant in restaurants:
        table.add_row(
            restaurant.name,
            restaurant.cuisine_type or "N/A",
            restaurant.rating_display,
            restaurant.price_display,
            f"{restaurant.distance_km:.1f} km" if restaurant.distance_km else "N/A"
        )
    
    console.print(table)


def display_weather(weather, console: Console) -> None:
    """Display weather information."""
    weather_text = Text()
    weather_text.append(f"Temperature: {weather.temperature_celsius:.1f}°C ({weather.temperature_fahrenheit:.1f}°F)\n", style="yellow")
    weather_text.append(f"Description: {weather.description}\n", style="cyan")
    weather_text.append(f"Humidity: {weather.humidity_percent}%\n", style="blue")
    weather_text.append(f"Wind Speed: {weather.wind_speed_kmh:.1f} km/h\n", style="green")
    weather_text.append(f"Pressure: {weather.pressure_hpa:.1f} hPa", style="magenta")
    
    console.print(Panel(weather_text, title="Weather Information", style="bold blue"))


def display_emissions(emissions, console: Console) -> None:
    """Display emissions information."""
    emissions_text = Text()
    emissions_text.append(f"Transport Mode: {emissions.mode.value.replace('_', ' ').title()}\n", style="cyan")
    emissions_text.append(f"Distance: {emissions.distance_km:.1f} km\n", style="yellow")
    emissions_text.append(f"CO2 Emissions: {emissions.co2_kg:.2f} kg ({emissions.co2_lb:.2f} lbs)\n", style="red")
    emissions_text.append(f"Sustainability: {emissions.sustainability_score}", style="green")
    
    console.print(Panel(emissions_text, title="Emissions Information", style="bold blue"))


async def main() -> int:
    """Main application entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Setup logging
    log_level = "DEBUG" if args.debug or args.verbose else "INFO"
    setup_logging(level=log_level)
    
    try:
        # Validate arguments
        validate_arguments(args)
        
        # Create travel request
        travel_request = create_travel_request(args)
        
        # Initialize agent
        agent = TravelPlannerAgent()
        
        # Determine which features to run
        features = []
        if args.itinerary:
            features.append("itinerary")
        if args.flights:
            features.append("flights")
        if args.hotels:
            features.append("hotels")
        if args.restaurants:
            features.append("restaurants")
        if args.weather:
            features.append("weather")
        if args.emissions:
            features.append("emissions")
        
        # Default to itinerary if no features specified
        if not features:
            features = ["itinerary"]
        
        # Process request
        results = await agent.process_request(travel_request, features)
        
        # Display results
        display_results(results, args.output)
        
        return 0
        
    except SmartTravelPlannerError as e:
        console = Console()
        console.print(f"[red]Error: {e.message}[/red]")
        if args.debug:
            console.print(f"[dim]Details: {e.details}[/dim]")
        return 1
    
    except Exception as e:
        console = Console()
        console.print(f"[red]Unexpected error: {str(e)}[/red]")
        if args.debug:
            import traceback
            console.print(traceback.format_exc())
        return 1


def cli_main() -> None:
    """CLI entry point."""
    sys.exit(asyncio.run(main()))


if __name__ == "__main__":
    cli_main()
