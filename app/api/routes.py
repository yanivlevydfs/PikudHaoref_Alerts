from fastapi import APIRouter, HTTPException
from app.services.oref_client import fetch_active_alerts

router = APIRouter()

@router.get(
    "/api/alerts", 
    summary="Get Active Alerts", 
    description="Fetches the current active alerts from the Pikud Haoref (Home Front Command) API.",
    tags=["Alerts"]
)
async def get_alerts():
    """
    Retrieves active alerts. If there are no alerts, returns a specific message.
    """
    import logging
    logger = logging.getLogger("pikudhaoref_app.routes")
    
    logger.info("Received request to fetch active alerts.")
    alerts_data = fetch_active_alerts()
    
    if alerts_data is None:
        logger.info("No active alerts found from Oref.")
        return {"message": "No active alerts at the moment.", "data": None}
        
    if isinstance(alerts_data, dict) and "error" in alerts_data:
        logger.error(f"Error encountered during fetch: {alerts_data['error']}")
        raise HTTPException(status_code=500, detail=alerts_data["error"])
        
    logger.info("Active alerts retrieved successfully.")
    return {"message": "Active alerts found.", "data": alerts_data}
