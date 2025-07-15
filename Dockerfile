# Use Python 3.13 as base image
FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for USB printer support
RUN apt-get update && apt-get install -y \
    libusb-1.0-0 \
    libusb-1.0-0-dev \
    udev \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python dependencies
RUN uv sync --frozen

# Copy application code
COPY . .

# Create data directory for SQLite database
RUN mkdir -p /app/data

# Expose any ports if needed (none for this app)
# EXPOSE 8080

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser -m
RUN chown -R appuser:appuser /app
USER appuser

# Create cache directory with proper permissions
RUN mkdir -p /home/appuser/.cache/uv

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Set the default command
CMD ["uv", "run", "app.py"]