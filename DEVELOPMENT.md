# Development Guide

This document provides comprehensive guidance for developers working on the Smart Travel Planner Agent.

## Getting Started

### Prerequisites

- Python 3.11+
- Git
- Docker (optional, for containerized development)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/smarttravelplanner/smart-travel-planner-agent.git
   cd smart-travel-planner-agent
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   # Install base dependencies
   pip install -r requirements.txt
   
   # Install development dependencies
   pip install -e ".[dev]"
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

5. **Run tests**
   ```bash
   pytest tests/
   ```

## Project Structure

```
smart-travel-planner-agent/
|-- src/
|   |-- smart_travel_planner/
|   |   |-- __init__.py
|   |   |-- config/           # Configuration management
|   |   |-- core/             # Core application logic
|   |   |-- models/            # Data models
|   |   |-- services/          # External service integrations
|   |   |-- utils/             # Utility functions
|   |   |-- exceptions/        # Custom exceptions
|   |   `-- main.py           # Application entry point
|-- tests/
|   |-- unit/                 # Unit tests
|   |-- integration/          # Integration tests
|   |-- fixtures/             # Test fixtures
|   `-- conftest.py          # Pytest configuration
|-- docs/                     # Documentation
|-- .github/workflows/         # CI/CD pipelines
|-- Dockerfile               # Container configuration
|-- docker-compose.yml       # Development containers
|-- pyproject.toml           # Project configuration
|-- requirements.txt         # Base dependencies
`-- README.md               # Project overview
```

## Development Workflow

### Code Quality

We use several tools to maintain code quality:

- **Black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting
- **mypy**: Type checking
- **bandit**: Security scanning

Run all quality checks:
```bash
pre-commit run --all-files
```

### Testing

Run the full test suite:
```bash
pytest tests/ -v --cov=src/smart_travel_planner
```

Run specific test categories:
```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Tests requiring API keys
pytest tests/ -m api -v
```

### Adding New Features

1. **Create a feature branch**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Implement the feature**
   - Follow the existing code structure
   - Add comprehensive tests
   - Update documentation

3. **Run quality checks**
   ```bash
   pre-commit run --all-files
   pytest tests/
   ```

4. **Submit pull request**
   - Include tests for new functionality
   - Update documentation
   - Ensure all CI checks pass

## Architecture Overview

### Core Components

- **Configuration**: Centralized settings management with environment variable support
- **Models**: Type-safe data structures using dataclasses
- **Services**: External API integrations with consistent error handling
- **Utils**: Shared utilities for HTTP, caching, validation, and security
- **Exceptions**: Hierarchical exception handling for better error management

### Design Principles

1. **Separation of Concerns**: Each module has a single responsibility
2. **Dependency Injection**: Services accept dependencies for better testability
3. **Error Handling**: Comprehensive exception hierarchy with meaningful error messages
4. **Configuration**: Environment-based configuration with validation
5. **Testing**: High test coverage with unit and integration tests
6. **Security**: Input validation, rate limiting, and secure defaults

### Service Layer

All external integrations follow the same pattern:

```python
class BaseService(ABC):
    def __init__(self, name: str):
        self.name = name
        self.settings = get_settings()
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.cache = get_cache()
        self.http_client: Optional[HTTPClient] = None
    
    @abstractmethod
    def health_check(self) -> bool:
        pass
```

## API Integration Guidelines

### Adding New Services

1. **Create service class** inheriting from `BaseService`
2. **Implement health check** method
3. **Use HTTPClient** for API calls with built-in retry logic
4. **Add caching** for expensive operations
5. **Handle errors** with appropriate custom exceptions
6. **Write comprehensive tests**

### Error Handling

- Use specific exception types from `src.smart_travel_planner.exceptions`
- Include meaningful error messages and context
- Log errors with appropriate severity levels
- Graceful degradation when external services are unavailable

### Rate Limiting

All HTTP clients include built-in rate limiting:
- Configurable request limits per time window
- Automatic retry with exponential backoff
- Respect API provider rate limits

## Testing Guidelines

### Unit Tests

- Test individual components in isolation
- Mock external dependencies
- Cover edge cases and error conditions
- Aim for high code coverage

### Integration Tests

- Test service interactions
- Use test containers or mocks for external APIs
- Verify end-to-end workflows
- Test with realistic data

### Test Data

Use fixtures for consistent test data:
```python
@pytest.fixture
def sample_flight_data():
    return {
        "airline": "Test Airlines",
        "flight_number": "TA123",
        # ... more fields
    }
```

## Security Guidelines

### Input Validation

- Validate all user inputs using utility functions
- Sanitize data to prevent injection attacks
- Use type hints for better validation
- Implement rate limiting for API endpoints

### API Keys

- Store API keys in environment variables
- Never commit secrets to version control
- Use different keys for development and production
- Rotate keys regularly

### Dependencies

- Regularly update dependencies
- Use `safety` to check for known vulnerabilities
- Pin versions in production
- Review security advisories

## Performance Considerations

### Caching

- Cache expensive API calls
- Use appropriate TTL values
- Implement cache invalidation
- Monitor cache hit rates

### Database Operations

- Use connection pooling
- Optimize queries
- Implement pagination
- Monitor query performance

### Memory Usage

- Profile memory usage
- Use generators for large datasets
- Implement proper cleanup
- Monitor for memory leaks

## Deployment

### Docker

Build production image:
```bash
docker build -t smart-travel-planner .
```

Run with docker-compose:
```bash
docker-compose up -d
```

### Environment Variables

Required environment variables:
- `GOOGLE_API_KEY`: Gemini API key
- `GOOGLE_MAPS_API_KEY`: Maps API key (optional)
- `GOOGLE_PLACES_API_KEY`: Places API key (optional)
- `AMADEUS_API_KEY`: Amadeus client ID (optional)
- `AMADEUS_API_SECRET`: Amadeus client secret (optional)

### Monitoring

Set up monitoring for:
- Application metrics
- Error rates
- Response times
- Resource usage

## Contributing

### Code Style

Follow the established code style:
- Use Black for formatting
- Follow PEP 8 guidelines
- Use descriptive variable names
- Add docstrings for public functions

### Documentation

- Update README.md for user-facing changes
- Add inline documentation for complex logic
- Update API documentation
- Include examples in docstrings

### Pull Requests

- Write clear commit messages
- Include tests for new features
- Update documentation
- Ensure CI checks pass
- Request code review from team members

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure virtual environment is activated
2. **API failures**: Check API keys and network connectivity
3. **Test failures**: Verify test configuration and mocks
4. **Docker issues**: Check Docker daemon and permissions

### Debugging

- Enable debug logging: `LOG_LEVEL=DEBUG`
- Use pdb for debugging: `import pdb; pdb.set_trace()`
- Check application logs
- Use monitoring tools for production issues

## Resources

- [Python Documentation](https://docs.python.org/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Black Code Formatter](https://black.readthedocs.io/)
- [Docker Documentation](https://docs.docker.com/)
- [GitHub Actions](https://docs.github.com/en/actions)
