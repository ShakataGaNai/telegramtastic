# Use Python 3.13 as base image with multi-architecture support
FROM --platform=$BUILDPLATFORM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for USB printer support
# Handle architecture-specific dependencies
RUN apt-get update && apt-get install -y \
    libusb-1.0-0 \
    libusb-1.0-0-dev \
    udev \
    && rm -rf /var/lib/apt/lists/* \
    && pip install uv \
    && apt-get clean

# Create app directory
WORKDIR /app

# Copy application code
COPY . .

# Create data directory for SQLite database
RUN uv sync --frozen
RUN mkdir -p /app/data

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser -m
RUN chown -R appuser:appuser /app
USER appuser

# Create cache directory with proper permissions
RUN mkdir -p /home/appuser/.cache/uv

# Set the default command
CMD ["uv", "run", "app.py"]