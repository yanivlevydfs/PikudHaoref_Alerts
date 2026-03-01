# Pikud Haoref Alerts API

This repository contains a FastAPI wrapper around the official Israel Home Front Command (Pikud Haoref) alerts API. It provides a structured, modern API endpoint to fetch real-time active alerts, complete with built-in interactive Swagger UI documentation and standardized logging.

## Features

- **FastAPI Framework**: High performance and easy-to-read code structure.
- **Swagger Documentation**: Automatically generated interactive API documentation.
- **Robust Client**: Handles requests to the official Pikud Haoref endpoint with proper required headers, timeouts, and error handling.
- **Standardized Logging**: Tracks application flow and errors efficiently.

## Prerequisites

- Python 3.8+

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd PikudHaoref_Alerts
   ```

2. **Create a virtual environment (optional but recommended):**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

To start the development server, run:

```bash
uvicorn app.main:app --reload
```

The server will start at `http://localhost:8000`.

## Interactive API Docs (Swagger UI)

Once the application is running, you can explore and test the endpoints directly from your browser by navigating to:

**[http://localhost:8000/docs](http://localhost:8000/docs)**

## Project Architecture

For a detailed breakdown of the application's structure and data flow, please refer to the [architecture.md](architecture.md) file.
