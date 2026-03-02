# Pikud Haoref Alerts API

This repository contains a FastAPI wrapper around the official Israel Home Front Command (Pikud Haoref) alerts API. It provides a structured, modern API endpoint to fetch real-time active alerts, complete with built-in interactive Swagger UI documentation and standardized logging.

## Features

- **Real-time Dashboard**: Interactive Map (Leaflet) with live alert updates and visual status indicators.
- **Israel-First Geocoding**: Optimized location search using localized OSM data with aggressive caching.
- **Robust Proxy Management**: Integrated with a dynamic, external Israeli proxy list (`proxies.json`) to bypass 403 blocks.
- **24-Hour Proxy Stickiness**: Implements long-term session persistence to "keep working" with a validated proxy, reducing re-validation overhead.
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

To bypass 403 blocks from the Oref servers, the system uses a rotator located in `app/resources/proxies.json`. 

**Structure:**
```json
[
  { "url": "host:port", "type": "http" },
  { "url": "user:pass@host:port", "type": "socks5" }
]
```
The system will automatically find a working Israeli proxy and "stick" to it for 24 hours to ensure consistent performance.

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

## Deployment

The application is containerized and ready for deployment on modern cloud platforms.

### 1. Docker & Docker Compose
To run the application locally using Docker:
```bash
# Build and start the container
docker-compose up --build
```
The app will be available at `http://localhost:8000`.

### 2. Render.com / Northflank
1. Connect your GitHub repository.
2. The `render.yaml` blueprint will automatically configure the service.
3. Ensure the `PORT` environment variable is set (Render does this automatically).

### 3. Fly.io
1. Install the [flyctl](https://fly.io/docs/hands-on/install-cli/) CLI.
2. Run `fly launch` to initialize the project (uses `fly.toml`).
3. Deploy using `fly deploy`.

### 4. DigitalOcean App Platform
1. Select "Apps" -> "Create".
2. Link your GitHub repository.
3. Choose "Docker" as the resource type. DigitalOcean will automatically pick up the `Dockerfile`.

### 5. Coolify (Self-Hosted)
1. Point Coolify to your GitHub repository.
2. Select "Docker Compose" as the build pack.
3. Coolify will use `docker-compose.yml` to orchestrate the deployment.

---
## Project Architecture
