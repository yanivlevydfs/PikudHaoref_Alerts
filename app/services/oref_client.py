import requests
import json
import logging

logger = logging.getLogger(__name__)

def fetch_active_alerts():
    """
    Fetches the active alerts from the Oref API.
    Returns a dictionary with the alerts data, or None if there are no active alerts.
    """
    url = "https://www.oref.org.il/WarningMessages/alert/alerts.json"
    
    # Headers exactly as required by Oref, plus a browser-like User-Agent
    headers = {
        'Referer': 'https://www.oref.org.il/',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    
    try:
        # We add timeout just in case it hangs
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            logger.error(f"Oref API returned status code {response.status_code}")
            return {"error": f"Oref API error: {response.status_code}"}
            
        response.raise_for_status()
        
        # Oref API returns empty content if there are no active alerts
        content = response.content.decode('utf-8-sig', errors='ignore').strip()
        
        # If there are no real alerts, return None so the UI can show the "No Alerts" screen
        if not content:
            return None
            
        # Try to parse as JSON
        try:
            data = json.loads(content)
            return data
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON. Raw content received: {content}")
            return {"error": "Failed to parse alerts data from Oref"}
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from Oref: {e}")
        return {"error": str(e)}
