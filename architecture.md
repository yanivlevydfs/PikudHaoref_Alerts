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
│   │   └── database.py       # SQLite database operations (History & Stats)
│   ├── resources/
│   │   └── proxies.json      # External list of Israeli proxies
│   ├── services/
│   │   ├── alert_state.py    # Persistent state management with accumulation logic
│   │   └── oref_client.py    # core logic to interact with the external Oref API via proxies
│   ├── static/               # Frontend assets (JS, CSS, Icons)
│   ├── templates/            # HTML templates (Jinja2)
│   └── main.py               # The FastAPI application & background scheduler entry point
│
├── requirements.txt          # Python dependencies
├── architecture.md           # This file
├── README.md                 # Project description and run instructions
└── alerts_history.db         # Local SQLite database (Auto-generated)
```

## Components

### 1. The FastAPI Application & Scheduler (`app/main.py`)
The entry point of the app. It initializes FastAPI, sets up the **Lifespan** handler to start a **BackgroundScheduler**. The scheduler periodically (every 10s-120s) triggers the alert fetching job.

### 2. Alert State Management (`app/services/alert_state.py`)
A thread-safe singleton that holds the current "active" alerts. It implements **Accumulation Logic**: when new alerts arrive, they are merged with existing ones so that map markers persist throughout a barrage. It only clears when the API explicitly returns an empty response. It also tracks the `is_online` status of the system.

### 3. Proxy-Aware Client (`app/services/oref_client.py`)
Handles the complex interaction with Oref's servers. It rotates through a list of Israeli proxies from `proxies.json` to bypass 403 blocks. It implements **Proxy Stickiness**, caching a working proxy for 24 hours to ensure stable performance.

### 4. Database Layer (`app/db/database.py`)
Manages a local **SQLite database** (`alerts_history.db`). It records unique alerts, prevents duplicates, and provides statistical aggregations for the `/stats` page.

### 5. Frontend Dashboard (`app/static/` & `app/templates/`)
A modern, dark-themed dashboard using **Leaflet.js** for mapping. It polls the `/api/alerts` endpoint every 10s and uses **Select2** for city searching. It includes visual warning banners for system errors.

## Technical Deep Dive

### 1. Alert Accumulation Logic
The `AlertState` class uses a `threading.Lock` to ensure thread-safety during background updates. 
- **Persistence**: When new alerts arrive, the system performs a `set.union()` of the incoming cities with the existing cities. 
- **Implicit Clearing**: Cities are only removed when the API returns a success status with an empty data payload.
- **Resilience**: If the API returns an error or a timeout occurs, the last known-good alert state is preserved to keep markers on the map, while `is_online` is flipped to `False`.

### 2. Parallel Proxy Rotator
The `oref_client` uses a `ThreadPoolExecutor` to test up to 20 Israeli proxies simultaneously. 
- **Validation**: A proxy is considered "Working" if it successfully fetches the Oref alerts JSON with a 200 OK.
- **Stickiness**: To avoid frequent stall times during testing, a working proxy is cached for **24 hours**. Every 24 hours (or if the current proxy fails), a fresh validation cycle is triggered.

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

1. **Service Startup**: `Lifespan` handler initializes `init_db()` and starts the `BackgroundScheduler`.
2. **Scheduled Cycle**: `scheduled_job` calls `fetch_active_alerts()`.
3. **Connection Handling**:
    - **Step A**: Attempt direct fetch.
    - **Step B**: If blocked (403), use the "sticky" working proxy.
    - **Step C**: If proxy fails, trigger parallel re-validation.
4. **State Sync**: Backend updates `AlertState` (Accumulation/Online flag).
5. **UI Notification**: Client-side `script.js` polls every 10s. If `is_online` is `false`, it triggers the **Red System Warning Banner**.
6. **Persistence**: Alert data is logged to SQLite and preserved in memory until an explicit clear signal.
