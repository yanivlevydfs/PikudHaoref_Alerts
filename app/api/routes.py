from fastapi import APIRouter, HTTPException
from app.services.oref_client import fetch_active_alerts
from cachetools import cached, TTLCache
import logging

router = APIRouter()
logger = logging.getLogger("pikudhaoref_app.routes")

# Define a cache: max 1 item in memory, expiring after 15 seconds
# We use 15s instead of 30s to ensure we never serve extremely stale data since the scheduler runs every 30s
alerts_cache = TTLCache(maxsize=1, ttl=15)

@cached(cache=alerts_cache)
def _get_cached_alerts():
    """Helper function to fetch and cache alerts using cachetools"""
    logger.debug("Cache miss/expired. Fetching fresh alerts from Oref client...")
    return fetch_active_alerts()

@router.get(
    "/api/alerts", 
    summary="Get Active Alerts", 
    description="Fetches the current active alerts from the Pikud Haoref (Home Front Command) API. Responses are cached.",
    tags=["Alerts"]
)
async def get_alerts():
    """
    Retrieves active alerts. If there are no alerts, returns a specific message.
    """
    alerts_data = _get_cached_alerts()
    
    if alerts_data is None:
        return {"message": "No active alerts at the moment.", "data": None}
        
    if isinstance(alerts_data, dict) and "error" in alerts_data:
        logger.error(f"Error encountered during fetch: {alerts_data['error']}")
        raise HTTPException(status_code=500, detail=alerts_data["error"])
        
    logger.info("Active alerts retrieved successfully.")
    return {"message": "Active alerts found.", "data": alerts_data}
