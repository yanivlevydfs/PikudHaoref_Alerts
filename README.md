# Pikud Haoref Alerts API

This repository contains a FastAPI wrapper around the official Israel Home Front Command (Pikud Haoref) alerts API. It provides a structured, modern API endpoint to fetch real-time active alerts, complete with built-in interactive Swagger UI documentation and standardized logging.

## Features

- **Real-time Dashboard**: Interactive Map (Leaflet) with live alert updates and visual status indicators.
- **Israel-First Geocoding**: Optimized location search using localized OSM data with aggressive caching.
- **Environment-Aware Proxy**: Automatically uses a high-performance proxy on Railway to bypass 403 blocks, while using efficient direct connections on localhost.
- **24-Hour Session Persistence**: Maintains persistent session state to minimize connection overhead and bypass rate limits.
- **Intelligent Alert Persistence**: State accumulation ensures city markers stay on the map throughout a "bulk" attack until the API explicitly returns an empty response.
- **System Reliability Notifications**: Real-time red warning banners and status indicators if the Oref API connection is interrupted.
- **Adaptive Polling**: Automatically scales polling frequency between Routine (gentle) and Emergency (rapid) modes based on threat level.
- **SQLite History & Stats**: Automatic 24h history recording and SQLite-backed statistics for all intercepted alerts.
- **Desktop Notifications & Audio**: Optional voice synthesis (Hebrew) and synthetic siren/bell alarms for immediate awareness.
- **PWA Ready**: Mobile-friendly manifest and service worker for "Add to Home Screen" support.

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

## Configuration

The application uses a `config.json` file in the root directory for core settings:

```json
{
    "scheduler": {
        "routine_interval_seconds": 120,
        "emergency_interval_seconds": 10
    }
}
```
- **routine_interval_seconds**: Polling frequency when no alerts are active.
- **emergency_interval_seconds**: High-speed polling frequency during a detected attack.

## Proxy Management

To bypass 403 blocks from the Oref servers when deployed in cloud environments (like Railway), the system uses a high-performance dedicated proxy configured in `config.json`.

**Example `config.json`:**
```json
{
    "proxy": {
        "url": "185.241.5.57:3128",
        "type": "http"
    }
}
```

- **Railway**: Automatically routes all Oref traffic through the proxy defined in the config.
- **Development/Local**: Uses direct connection for maximum speed.
- **Persistence**: Uses a shared `requests.Session` with automatic cookie management to ensure consistent bypass success.

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/alerts` | `GET` | Returns currently accumulated active alerts and system status. |
| `/api/alerts/history` | `GET` | Returns alert history for the last 24 hours from SQLite. |
| `/api/alerts/statistics` | `GET` | Returns aggregated count per city for a given timeframe. |
| `/rss` | `GET` | Real-time XML RSS feed of recent alerts. |
| `/health` | `GET` | Lightweight health check for deployment platforms. |

## Dashboard Access

Navigate to the root URL `/` to access the interactive dashboard.
- **Mock Mode**: Add `?mock=true` to the URL to simulate a massive attack for testing UI/Audio.

## Project Architecture

For a detailed technical breakdown of the accumulation logic, proxy rotator, and database schema, please refer to the [architecture.md](architecture.md) file.
