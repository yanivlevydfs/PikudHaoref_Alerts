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

# Create directory for SQLite database if it doesn't exist
RUN mkdir -p /app/data

# Default port if not provided by environment (e.g. for local runs)
ENV PORT=8000

# Expose the dynamic port
EXPOSE $PORT

# Command to run the application using shell form to expand the $PORT variable
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT
