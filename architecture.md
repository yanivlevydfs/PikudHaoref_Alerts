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
│   │   └── logging_config.py # Configures standard output logging
│   ├── services/
│   │   └── oref_client.py    # Contains the core logic to interact with the external Oref API
│   └── main.py               # The FastAPI application entry point
│
├── requirements.txt          # Python dependencies
├── architecture.md           # This file
├── README.md                 # Project description and run instructions
└── test_oref.py              # Legacy script (for reference)
```

## Components

### 1. The FastAPI Application (`app/main.py`)
This is the root of the application. It initializes the `FastAPI` instance, sets up the metadata for the Swagger UI documentation, configures the logger, and includes the routing modularized in `routes.py`.

### 2. API Routes (`app/api/routes.py`)
This module uses FastAPI's `APIRouter` to define endpoints cleanly. Currently, it exposes `GET /api/alerts`. It handles the HTTP request flow, calls the service layer, logs activity, and transforms any raw errors into proper HTTP responses.

### 3. Service Layer (`app/services/oref_client.py`)
This file is dedicated solely to external business logic. It handles the actual HTTP request to the `https://www.oref.org.il/WarningMessages/alert/alerts.json` endpoint. It ensures the specific headers (`Referer` and `X-Requested-With`) are sent correctly and handles potential JSON decoding issues or connection timeouts. 

### 4. Logging (`app/core/logging_config.py`)
Provides centralized logging. Logs are directed to `sys.stdout` so that they can be easily captured by container orchestration systems (like Docker/Kubernetes) or local development terminals.

## Data Flow

1. **Client Request**: A client (e.g., via browser or Swagger UI) makes a `GET` request to `/api/alerts`.
2. **Route Handler**: The request is intercepted by `app/api/routes.py`. It logs the incoming request and calls the service layer.
3. **External Fetch**: The `fetch_active_alerts()` function in `app/services/oref_client.py` makes an HTTP request to the Pikud Haoref servers.
4. **Data Parsing**: The external response is validated and parsed as JSON. If empty (meaning no alerts), it returns `None`.
5. **Response Delivery**: The route handler formats the data into a standard JSON response (`{ "message": "...", "data": [...] }`) and returns it to the client. If an error occurred during fetching, a 500 Internal Server Error is raised instead.
