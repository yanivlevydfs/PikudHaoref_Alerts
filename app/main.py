from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.api.routes import router as api_router
from app.core.logging_config import setup_logging
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.config import APP_CONFIG
from app.services.oref_client import fetch_active_alerts
from app.services.alert_state import global_alert_state
from app.db.database import init_db, insert_alert_if_new
import os

# Initialize Logger
logger = setup_logging()

# We instantiate the scheduler globally so scheduled_job can reschedule itself
scheduler = BackgroundScheduler()

def scheduled_job():
    logger.info("Executing scheduled task: fetching active alerts from Oref...")
    alerts = fetch_active_alerts()
    
    # Update our global memory state for the FastAPI routes
    global_alert_state.update(alerts)
    status_str = "SUCCESS" if global_alert_state.is_online else "FAILED"
    logger.info(f"Global alert state updated. Status: {status_str}, IsAttack: {alerts and 'data' in alerts}")
    
    # Adaptive Polling & Database Logic
    if alerts and "error" in alerts:
        logger.error(f"Oref API check failed: {alerts['error']}")
        # Keep current interval for retry
    elif alerts and "data" in alerts:
        # Insert into SQLite Database
        was_inserted = insert_alert_if_new(alerts)
        if was_inserted:
            logger.info(f"Database recorded new alert with ID: {alerts.get('id')}")
            
        active_cities = alerts.get("data", [])
        city_count = len(active_cities)
        title = alerts.get("title", 'Unknown Alert')
        logger.info(f"SUCCESS: Oref returning alerts: '{title}' affecting {city_count} locations.")
        logger.info(f"ADAPTIVE POLLING: Emergency active. Scaling polling interval down to {APP_CONFIG['scheduler']['emergency_interval_seconds']} seconds.")
        # Under attack: Poll very frequently
        scheduler.reschedule_job('fetch_alerts_job', trigger='interval', seconds=APP_CONFIG['scheduler']['emergency_interval_seconds'])
    else:
        logger.info("Oref returned no active alerts (Status: Healthy).")
        logger.info(f"ADAPTIVE POLLING: Shigra (Routine). Relaxing polling interval to {APP_CONFIG['scheduler']['routine_interval_seconds']} seconds.")
        # Routine: Poll gently
        scheduler.reschedule_job('fetch_alerts_job', trigger='interval', seconds=APP_CONFIG['scheduler']['routine_interval_seconds'])

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure database is prepared
    init_db()
    
    # Initial startup interval will be the gentle routine one
    initial_interval = APP_CONFIG['scheduler']['routine_interval_seconds']
    
    scheduler.add_job(
        scheduled_job,
        'interval',
        seconds=initial_interval,
        id='fetch_alerts_job',
        replace_existing=True
    )
    
    # Start the scheduler
    scheduler.start()
    
    logger.info("Application startup complete. Ready to serve requests.")
    
    # Yield control back to FastAPI immediately (Startup complete)
    yield
    
    # Shutdown the scheduler when the app is tearing down
    logger.info("Shutting down Background Scheduler.")
    scheduler.shutdown()

app = FastAPI(
    title="Pikud Haoref Alerts API (Unofficial)",
    description="""
    A robust, modern FastAPI wrapper around the official Israel Home Front Command (Oref) real-time alerts.
    
    ### Key Capabilities:
    * **Real-time Monitoring**: High-frequency adaptive polling during attacks.
    * **State Persistence**: Smart accumulation of cities throughout a barrage.
    * **Proxy Resilience**: 24h sticky Israeli proxy rotation to bypass 403 blocks.
    * **Alert History**: SQLite-backed tracking of all intercepted events.
    * **RSS Support**: Standardized XML feed for downstream consumers.
    """,
    version="1.2.0",
    contact={
        "name": "Pikud Haoref API Support",
        "url": "https://github.com/YanivLevy/PikudHaoref_Alerts",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan
)

@app.get("/health", include_in_schema=False)
async def health_check():
    """
    Lightweight healthcheck for Railway/Automation.
    """
    return {"status": "ok"}

from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi.exceptions import HTTPException

# Set up templates directory
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

# Mount Static Files Directory
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Include API routes
app.include_router(api_router)

@app.get("/", include_in_schema=False)
async def root(request: Request):
    """
    Serves the main frontend dashboard using Jinja2 Templates.
    """
    return templates.TemplateResponse("index.html", {"request": request})

from fastapi.responses import FileResponse

@app.get("/robots.txt", include_in_schema=False)
async def serve_robots():
    """
    Serves the robots.txt directly from the root for SEO/Crawlers.
    """
    return FileResponse(os.path.join(static_dir, "robots.txt"))

@app.get("/sw.js", include_in_schema=False)
async def serve_sw():
    """
    Serves the Service Worker directly from the root.
    """
    return FileResponse(os.path.join(static_dir, "sw.js"))

@app.get("/favicon.ico", include_in_schema=False)
async def serve_favicon():
    """
    Serves the icon.png as favicon.ico for legacy support.
    """
    return FileResponse(os.path.join(static_dir, "icon.png"))

@app.get("/sitemap.xml", include_in_schema=False)
async def serve_sitemap_xml():
    """
    Generates and serves a proper XML sitemap for search engines.
    """
    from fastapi.responses import Response
    from datetime import datetime
    
    # In a real app, you'd define these dynamically
    base_url = "https://alerts.up.railway.app"
    pages = ["", "about", "contact", "terms", "accessibility", "privacy", "sitemap", "stats", "archive"]
    lastmod = datetime.now().strftime("%Y-%m-%d")
    
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    for page in pages:
        url = f"{base_url}/{page}" if page else f"{base_url}/"
        xml_content += f'  <url>\n    <loc>{url}</loc>\n    <lastmod>{lastmod}</lastmod>\n    <changefreq>daily</changefreq>\n    <priority>{"1.0" if not page else "0.8"}</priority>\n  </url>\n'
    
    xml_content += '</urlset>'
    return Response(content=xml_content, media_type="application/xml")

@app.get("/manifest.json", include_in_schema=False)
async def serve_manifest():
    """
    Serves the PWA manifest directly from the root.
    """
    return FileResponse(os.path.join(static_dir, "manifest.json"))

@app.get("/{page}", include_in_schema=False)
async def serve_page(request: Request, page: str):
    """
    Serves generic sub-pages (About, Contact, Terms, etc.) directly from Jinja templates.
    """
    valid_pages = ["about", "contact", "terms", "accessibility", "privacy", "sitemap", "stats", "archive"]
    if page in valid_pages:
        return templates.TemplateResponse(f"{page}.html", {"request": request})
    
    # Otherwise return 404
    raise HTTPException(status_code=404, detail="Page not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
