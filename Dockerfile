# Production-ready Dockerfile for Smart Travel Planner Agent
FROM python:3.12-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r travelplanner && useradd -r -g travelplanner travelplanner

# Copy requirements first for better caching
COPY requirements.txt pyproject.toml ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY data/ ./data/
COPY emission_factors.csv ./

# Create necessary directories
RUN mkdir -p logs cache && \
    chown -R travelplanner:travelplanner /app

# Switch to non-root user
USER travelplanner

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import src.smart_travel_planner; print('OK')" || exit 1

# Expose port (if running web service)
EXPOSE 8000

# Default command
CMD ["python", "-m", "src.smart_travel_planner.main"]
