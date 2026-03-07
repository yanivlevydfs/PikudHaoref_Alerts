# Pikud Haoref Alerts API - Architecture

This document describes the architecture of the Pikud Haoref Alerts API project.

## Overview

The application is built using **FastAPI**, providing a modern, fast (high-performance) web framework for building APIs with Python based on standard Python type hints. It serves as a wrapper around the official Pikud Haoref (Home Front Command) alerts API, making it easier to consume and test via a built-in Swagger UI.

## Directory Structure

```text
PikudHaoref_Alerts/
│
├── app/
│   ├── api/
│   │   └── routes.py         # Defines the FastAPI endpoints (e.g., /api/alerts)
│   ├── core/
│   │   ├── config.py         # Application configuration management
│   │   └── logging_config.py # Configures standard output logging
│   ├── db/
│   │   ├── database.py       # SQLite database operations (History & Stats)
│   │   └── alerts_history.db # Local SQLite database (Auto-generated)
│   ├── services/
│   │   ├── alert_state.py    # Persistent state management with accumulation logic
│   │   └── oref_client.py    # core logic to interact with the external Oref API (Proxy on Railway)
│   ├── static/               # Frontend assets (JS, CSS, Icons)
│   ├── templates/            # HTML templates (Jinja2)
│   └── main.py               # The FastAPI application & background scheduler entry point
│
├── requirements.txt          # Python dependencies
├── architecture.md           # This file
├── README.md                 # Project description and run instructions
└── config.json               # System configuration (Intervals & Proxy)
```

## Components

### 1. The FastAPI Application & Scheduler (`app/main.py`)
The entry point of the app. It initializes FastAPI, sets up the **Lifespan** handler to start a **BackgroundScheduler**. The scheduler periodically (every 10s-120s) triggers the alert fetching job.

### 2. Alert State Management (`app/services/alert_state.py`)
A thread-safe singleton that holds the current "active" alerts. It implements **Accumulation Logic**: when new alerts arrive, they are merged with existing ones so that map markers persist throughout a barrage. It only clears when the API explicitly returns an empty response. It also tracks the `is_online` status of the system.

### 3. Environment-Aware Client (`app/services/oref_client.py`)
Handles the complex interaction with Oref's servers. It detects the environment (Railway vs. Local) and automatically decides whether to use a dedicated high-performance proxy (configured in `config.json`) or a direct connection (Local) to bypass 403 blocks.

### 4. Database Layer (`app/db/database.py`)
Manages a local **SQLite database** (`app/db/alerts_history.db`). It records unique alerts, prevents duplicates, and provides statistical aggregations for the `/stats` page.

### 5. Frontend Dashboard (`app/static/` & `app/templates/`)
A modern, dark-themed dashboard using **Leaflet.js** for mapping. It polls the `/api/alerts` endpoint every 10s and uses **Select2** for city searching. It includes visual warning banners for system errors.

### 6. Swagger API Services
The application exposes a fully documented OpenAPI (Swagger) interface at `/docs`. The architectural endpoints are categorized as follows:
- **Alerts Core**: 
  - `GET /api/alerts`: Real-time active alerts buffered in memory.
  - `GET /api/config`: Injected configuration state (e.g., map marker durations).
- **Data & History**: 
  - `GET /api/alerts/history`: 24-hour SQL-backed chronological history.
  - `GET /api/alerts/statistics`: Aggregated metrics over multiple timeframes (`24h` to `all`).
  - `GET /api/alerts/quiet_times`: Analytical engine resolving historically safe hours.
- **Geocoding Engine (OSM Fallback)**:
  - `POST /api/geocode`: High-performance bulk geocoding resolving shapes via SQLite caches.
  - `GET /api/geolocations_list`: Management endpoint listing cached vs. missing cities.
  - `POST /api/geolocations/sync`: Trigger endpoint to force the background `APScheduler` worker to resolve missing coordinates immediately.
- **Feeds & Health**: 
  - `GET /rss`: Real-time XML feed generation.
  - `GET /health`: Platform readiness probe.

## Technical Deep Dive

### 1. Alert Accumulation Logic
The `AlertState` class uses a `threading.Lock` to ensure thread-safety during background updates. 
- **Persistence**: When new alerts arrive, the system performs a `set.union()` of the incoming cities with the existing cities. 
- **Time-Based Expiration**: Map markers persist intelligently via the `map.marker_display_duration_minutes` configuration (default 10m). The frontend JavaScript asynchronously fetches this `/api/config` REST endpoint on load and manages graceful cleanup locally rather than relying on aggressive immediate wipes from the backend.
- **Resilience**: If the API returns an error or a timeout occurs, the last known-good alert state is preserved to keep markers on the map, while `is_online` is flipped to `False`.

### 2. Environment-Aware Connection
The `oref_client` automatically routes traffic based on the detected cloud environment:
- **Cloud Detection**: Checks for environment variables (e.g., `RAILWAY_ENVIRONMENT`).
- **Standardized Headers**: Uses comprehensive, identical headers in both modes to mimic a real browser session.
- **Session Persistence**: Maintains an active `requests.Session` for cookie reuse.

### 3. Adaptive Polling
The system dynamically adjusts its poll rate via `APScheduler`:
- **Routine Mode**: Polls every 120 seconds.
- **Emergency Mode**: If an alert is detected, the interval is instantly scaled down to 10 seconds.
- **Recovery**: Once the alerts clear, the scheduler relaxes the interval back to routine speed.

### 4. Database Schema (`alerts_history.db`)
The system tracks alerts in a flat SQLite table for high-performance retrieval of stats and history:

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Primary Key (Autoincrement) |
| `alert_id` | TEXT | Unique ID from Oref API |
| `title` | TEXT | Alert type (e.g., Rockets & Missiles) |
| `description` | TEXT | Instructions (e.g., enter shelter) |
| `locations` | TEXT | JSON string of affected cities |
| `timestamp` | DATETIME | ISO 8601 recording time |

## Data Flow (Updated)

1. **Service Startup**: `Lifespan` handler initializes `init_db()` and loads system settings from `config.json`.
2. **Scheduled Cycle**: `scheduled_job` calls `fetch_active_alerts()`.
3. **Connection Handling**:
    - **Railway**: Routes directly through the proxy defined in `config.json`.
    - **Local**: Routes directly through the local network.
    - **Retry Logic**: If the primary method fails, the system logs the error and maintains the last known healthy state.
4. **State Sync**: Backend updates `AlertState` (Accumulation/Online flag).
5. **UI Notification**: Client-side `script.js` polls every 10s. It initializes once via `/api/config` to understand visual rules. If `is_online` is `false`, it triggers the **Red System Warning Banner**. Organic JS timers ensure markers stay on screen according to config.
6. **Persistence**: Alert data is logged to SQLite and preserved in memory.
