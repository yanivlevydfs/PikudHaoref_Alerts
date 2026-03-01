from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.routes import router as api_router
from app.core.logging_config import setup_logging
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.config import APP_CONFIG
from app.services.oref_client import fetch_active_alerts
import os

# Initialize Logger
logger = setup_logging()

def scheduled_job():
    logger.info("Executing scheduled task: fetching active alerts...")
    alerts = fetch_active_alerts()
    if alerts:
        logger.info(f"Scheduled fetch found valid response: {alerts}")
    else:
        logger.info("Scheduled fetch found no active alerts.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup the background scheduler
    scheduler = BackgroundScheduler()
    interval = APP_CONFIG.get("scheduler", {}).get("interval_seconds", 30)
    
    scheduler.add_job(
        scheduled_job,
        'interval',
        seconds=interval,
        id='fetch_alerts_job',
        replace_existing=True
    )
    
    logger.info(f"Starting Background Scheduler with an interval of {interval} seconds.")
    scheduler.start()
    
    # Yield control back to FastAPI
    yield
    
    # Shutdown the scheduler when the app is tearing down
    logger.info("Shutting down Background Scheduler.")
    scheduler.shutdown()

app = FastAPI(
    title="Pikud Haoref Alerts API",
    description="A FastAPI wrapper around the official Pikud Haoref (Home Front Command) alerts API. Provides an easy-to-use endpoint "
                "with Swagger UI documentation for fetching real-time alerts in Israel.",
    version="1.0.0",
    contact={
        "name": "Yaniv Levy",
    },
    lifespan=lifespan
)

# Mount Static Files Directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include API routes
app.include_router(api_router)

@app.get("/", include_in_schema=False)
async def root():
    """
    Serves the main frontend dashboard.
    """
    return FileResponse(os.path.join(static_dir, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
