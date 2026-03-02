from fastapi import APIRouter, HTTPException, Query, Response
from datetime import datetime
from app.services.alert_state import global_alert_state
from app.db.database import get_recent_alerts, get_alert_statistics
import logging

router = APIRouter()
logger = logging.getLogger("pikudhaoref_app.routes")

@router.get(
    "/api/alerts", 
    summary="Get Active Alerts", 
    description="Fetches the current active alerts from the Rockets & Missles alerts API. Responses are cached.",
    tags=["Alerts"]
)
async def get_alerts(mock: bool = False):
    """
    Retrieves active alerts instantaneously from global memory state.
    If 'mock=true' is passed, simulates a massive attack for UI testing.
    """
    if mock:
        return {
            "message": "MOCK MODE ACTIVE",
            "data": {
                "id": "123456789",
                "cat": "1",
                "title": "ירי רקטות וטילים",
                "data": [
                    "תל אביב - יפו",
                    "רמת גן",
                    "גבעתיים",
                    "חיפה - כרמל",
                    "טירת כרמל",
                    "ירושלים - מרכז",
                    "שדרות",
                    "רחוב הרצל",
                    "שדרות רוטשילד"
                ],
                "desc": "היכנסו למרחב המוגן, שהו בו 10 דקות"
            }
        }

    alerts_data = global_alert_state.get()
    
    logger.info(f"API Request: /api/alerts (Online: {global_alert_state.is_online}, HasData: {alerts_data is not None})")
    
    return {
        "message": "Active alerts found." if alerts_data else "No active alerts at the moment.",
        "data": alerts_data,
        "is_online": global_alert_state.is_online
    }

@router.get(
    "/api/alerts/history", 
    summary="Get Alert History (Last 24 Hours)", 
    description="Fetches alerts that occurred in the last 24 hours from the local SQLite database.",
    tags=["Alerts"]
)
async def get_alert_history(hours: int = 24):
    """
    Retrieves historical alerts. 
    By default fetches the last 24 hours.
    """
    try:
        history_data = get_recent_alerts(hours=hours)
        return {"message": "History retrieved successfully", "data": history_data}
    except Exception as e:
        logger.error(f"Failed to fetch history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching history.")

@router.get(
    "/api/alerts/statistics",
    summary="Get Alert Statistics By City",
    description="Fetches aggregated statistics of alerts per city based on a given timeframe.",
    tags=["Statistics"]
)
async def get_statistics(timeframe: str = Query("24h", description="Options: 24h, 1w, 1m, 6m, 1y, all")):
    """
    Returns an aggregated list of cities and their alert counts.
    """
    try:
        stats_data = get_alert_statistics(timeframe=timeframe)
        return {"message": f"Statistics for {timeframe} retrieved successfully", "data": stats_data}
    except Exception as e:
        logger.error(f"Failed to fetch statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching statistics.")

@router.get(
    "/rss",
    summary="Get Alert RSS Feed",
    description="Returns an RSS XML feed of recent alerts.",
    tags=["RSS"]
)
async def get_rss_feed():
    try:
        # Get last 24h of alerts
        history_data = get_recent_alerts(hours=24)
        
        # Build XML
        current_time = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0200")
        
        xml_content = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>התראות ביטחוניות</title>
    <link>http://localhost:8000/</link>
    <description>התראות בזמן אמת</description>
    <lastBuildDate>{current_time}</lastBuildDate>
"""
        
        for alert in history_data:
            # Parse SQLite timestamp (which is ISO format) into RSS RFC 822 format
            try:
                alert_time = datetime.fromisoformat(alert['timestamp']).strftime("%a, %d %b %Y %H:%M:%S +0200")
            except:
                alert_time = current_time

            locations = ", ".join(alert['locations'])
            
            xml_content += f"""
    <item>
      <title>{alert['title']} - {locations}</title>
      <link>http://localhost:8000/archive</link>
      <description>{alert['description']} באזורים: {locations}</description>
      <pubDate>{alert_time}</pubDate>
      <guid>{alert['alert_id']}</guid>
    </item>"""
            
        xml_content += """
  </channel>
</rss>"""

        return Response(content=xml_content, media_type="application/xml")
    except Exception as e:
        logger.error(f"Failed to generate RSS: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while generating RSS feed.")
