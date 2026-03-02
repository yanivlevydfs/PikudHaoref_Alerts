# Production Dockerfile for Pikud Haoref Alerts API
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for SQLite database and ensure it's writable
RUN mkdir -p /app/data && chmod 777 /app/data
ENV DB_DIR=/app/data

# Default port if not provided by environment
ENV PORT=8000
EXPOSE $PORT

# Start application using the package module runner
CMD ["python", "-m", "app.main"]
