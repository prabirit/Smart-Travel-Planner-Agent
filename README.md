# Smart Travel Planner Agent

A production-ready, sustainability-focused travel planning system that integrates real-time flight and hotel pricing, weather and air quality data, emissions estimation, and restaurant recommendations.

## Features

### 2022 Core Capabilities
- **Real-time Flight Search**: Amadeus API integration with pricing and availability
- **Hotel Search**: Dual approach (OSM heuristic + Amadeus real-time pricing)
- **Weather & Air Quality**: Open-Meteo with OpenWeatherMap fallback
- **Restaurant Recommendations**: Google Places API with advanced filtering
- **Emissions Calculation**: Transport mode comparison and sustainability scoring
- **AI-Powered Itineraries**: Google Gemini integration for intelligent trip planning

### 2022 Production Features
- **Comprehensive Configuration**: Environment-based settings management
- **Structured Logging**: Configurable logging with multiple levels and outputs
- **Error Handling**: Hierarchical exception system with detailed error context
- **Security**: Rate limiting, input validation, and data sanitization
- **Caching**: Intelligent caching with TTL and persistence options
- **Testing**: 95%+ test coverage with unit and integration tests
- **Docker Support**: Multi-stage builds with security best practices
- **CI/CD Pipeline**: Automated testing, security scanning, and deployment

## Quick Start

### Prerequisites
- Python 3.11+
- Docker (optional, for containerized deployment)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/smarttravelplanner/smart-travel-planner-agent.git
   cd smart-travel-planner-agent
   ```

2. **Set up environment**
   ```bash
   # Create virtual environment
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Install dependencies
   pip install -e ".[dev]"
   
   # Copy environment configuration
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Configure API Keys**
   
   Required for full functionality:
   ```bash
   # Google APIs
   GOOGLE_API_KEY=your_google_api_key_here              # Gemini for itineraries
   GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here    # Maps/Directions
   GOOGLE_PLACES_API_KEY=your_google_places_api_key_here  # Restaurants
   
   # Travel APIs (optional but recommended)
   AMADEUS_API_KEY=your_amadeus_client_id_here          # Flights/Hotels
   AMADEUS_API_SECRET=your_amadeus_client_secret_here
   WEATHER_API_KEY=your_openweathermap_api_key_here     # Weather fallback
   ```

4. **Run the application**
   ```bash
   # Generate a complete itinerary
   smart-travel-planner "San Francisco" "Los Angeles" --itinerary
   
   # Search for flights
   smart-travel-planner "New York" "London" --flights --start-date 2024-12-01
   
   # Find restaurants
   smart-travel-planner "Paris" --restaurants --cuisine french --min-rating 4.0
   ```

## Usage Examples

### Command Line Interface

```bash
# Complete trip planning
smart-travel-planner "San Francisco" "Los Angeles" \
  --start-date 2024-12-01 \
  --end-date 2024-12-03 \
  --itinerary \
  --flights \
  --hotels \
  --restaurants \
  --sustainability high

# Individual services
smart-travel-planner "Tokyo" --weather --emissions
smart-travel-planner "Rome" --hotels --min-rating 4.0
smart-travel-planner "Barcelona" --restaurants --cuisine spanish
```

### Python API

```python
from smart_travel_planner import TravelPlannerAgent
from smart_travel_planner.models import TravelRequest
from datetime import date

# Create agent
agent = TravelPlannerAgent()

# Create travel request
request = TravelRequest(
    origin="San Francisco",
    destination="Los Angeles",
    start_date=date(2024, 12, 1),
    end_date=date(2024, 12, 3),
    travelers=2,
    sustainability_preference="high"
)

# Process request
results = await agent.process_request(request, ["itinerary", "flights", "hotels"])
print(results["itinerary"])
```

## Architecture

### Project Structure
```
smart-travel-planner-agent/
|-- src/smart_travel_planner/
|   |-- config/           # Configuration management
|   |-- core/             # Main application logic
|   |-- models/           # Type-safe data models
|   |-- services/         # External API integrations
|   |-- utils/            # Shared utilities
|   |-- exceptions/       # Custom exceptions
|   `-- main.py          # Application entry point
|-- tests/                # Comprehensive test suite
|-- docs/                 # Documentation
|-- .github/workflows/    # CI/CD pipelines
|-- Dockerfile           # Container configuration
`-- pyproject.toml       # Project configuration
```

### Design Principles
- **Separation of Concerns**: Each module has a single responsibility
- **Type Safety**: Comprehensive use of dataclasses and type hints
- **Error Resilience**: Graceful degradation when services are unavailable
- **Security First**: Input validation, rate limiting, and secure defaults
- **Testability**: High test coverage with mocking and fixtures
- **Performance**: Intelligent caching and connection pooling

## API Integrations

### Required APIs
- **Google Gemini**: AI-powered itinerary generation
- **Google Places**: Restaurant recommendations and geocoding
- **Google Maps**: Route planning and directions (optional)

### Optional APIs
- **Amadeus**: Real-time flight and hotel pricing
- **OpenWeatherMap**: Weather data fallback
- **Open-Meteo**: Primary weather and air quality data

### Setup Instructions

#### Google APIs
1. **Enable APIs** in [Google Cloud Console](https://console.cloud.google.com/apis/library):
   - Generative Language API (for Gemini)
   - Places API (legacy version)
   - Maps Directions API (optional)

2. **Create API Keys**:
   - [Google AI Studio](https://aistudio.google.com/app/apikey) for Gemini
   - [Google Cloud Console](https://console.cloud.google.com/apis/credentials) for Maps/Places

#### Amadeus APIs
1. **Sign up** at [Amadeus for Developers](https://developers.amadeus.com)
2. **Create application** in Test (Sandbox) mode
3. **Copy credentials** to `.env` file

## Development

### Setup Development Environment
```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v --cov=src/smart_travel_planner

# Code formatting
black src/ tests/
isort src/ tests/

# Type checking
mypy src/

# Security scanning
bandit -r src/
safety check
```

### Project Structure
- **`src/smart_travel_planner/config/`**: Configuration management and logging
- **`src/smart_travel_planner/core/`**: Main agent and itinerary generation
- **`src/smart_travel_planner/services/`**: External API integrations
- **`src/smart_travel_planner/utils/`**: HTTP client, validation, security, caching
- **`src/smart_travel_planner/models/`**: Type-safe data structures
- **`tests/`**: Unit and integration tests with comprehensive fixtures

### Adding New Features
1. Create service class inheriting from `BaseService`
2. Implement health check and error handling
3. Add comprehensive tests
4. Update documentation
5. Follow existing code style and patterns

## Deployment

### Docker
```bash
# Build image
docker build -t smart-travel-planner .

# Run with docker-compose
docker-compose up -d
```

### Environment Configuration
```bash
# Production
ENVIRONMENT=production
LOG_LEVEL=INFO
SSL_VERIFY=true

# Development
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
```

### Monitoring
- Application logs with structured formatting
- Health checks for all services
- Error tracking and alerting
- Performance metrics and caching statistics

## Testing

### Test Coverage
- **Unit Tests**: Individual component testing with mocks
- **Integration Tests**: Service interaction testing
- **API Tests**: External API integration testing
- **Security Tests**: Input validation and security scanning

### Running Tests
```bash
# All tests
pytest tests/ -v

# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# With coverage
pytest tests/ --cov=src/smart_travel_planner --cov-report=html
```

## Security

### Implemented Security Measures
- **Input Validation**: Comprehensive validation for all user inputs
- **Rate Limiting**: Configurable rate limits for API requests
- **Data Sanitization**: Prevention of injection attacks
- **SSL Verification**: Secure HTTPS connections with certificate validation
- **API Key Management**: Environment-based credential storage
- **Error Handling**: No sensitive information in error messages

### Security Scanning
```bash
# Run security scans
bandit -r src/
safety check
```

## Performance

### Optimization Features
- **Intelligent Caching**: Redis/file-based caching with TTL
- **Connection Pooling**: Efficient HTTP client with connection reuse
- **Rate Limiting**: Built-in rate limiting to prevent API abuse
- **Lazy Loading**: Optional dependencies loaded only when needed
- **Async Operations**: Non-blocking API calls where possible

### Monitoring Performance
- Cache hit rates and response times
- API quota usage and error rates
- Memory usage and resource consumption
- Database query performance (if applicable)

## Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Make changes with comprehensive tests
4. Run quality checks: `pre-commit run --all-files`
5. Submit pull request with detailed description

### Code Quality Standards
- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **pytest**: Testing
- **bandit**: Security scanning

## Documentation

- **[DEVELOPMENT.md](DEVELOPMENT.md)**: Comprehensive developer guide
- **[CHANGELOG.md](CHANGELOG.md)**: Version history and changes
- **[API Documentation](docs/api/)**: Detailed API reference
- **[Architecture Guide](docs/architecture/)**: System design and patterns

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/smarttravelplanner/smart-travel-planner-agent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/smarttravelplanner/smart-travel-planner-agent/discussions)
- **Documentation**: [Project Wiki](https://github.com/smarttravelplanner/smart-travel-planner-agent/wiki)

---

## Acknowledgments

- **Open-Meteo**: Weather and air quality data
- **Google**: Maps, Places, and Generative AI APIs
- **Amadeus**: Travel industry data and pricing
- **OpenStreetMap**: Geographic data and hotel information
