import requests
import os
import json
import logging
import time

logger = logging.getLogger(__name__)

# Global session to persist cookies and connection
session = requests.Session()

def reset_session():
    """
    Creates a fresh requests Session to clear any stuck connections or corrupted states.
    Useful when a proxy dies and we want to ensure the next attempt is totally clean.
    """
    global session
    logger.info("♻️ Resetting Oref Client Session (Connection Pool Purge)...")
    session = requests.Session()

from app.core.config import get_config

# Common headers for Oref
OREF_HEADERS = {
    'Host': 'www.oref.org.il',
    'Accept': 'application/json, text/javascript, */*; q=0.01',
    'Accept-Language': 'he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Referer': 'https://www.oref.org.il/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
    'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    'Sec-Ch-Ua-Mobile': '?0',
    'Sec-Ch-Ua-Platform': '"Windows"',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin'
}

def fetch_active_alerts():
    """
    Fetches the active alerts from the Oref API.
    Environment-aware: Uses a proxy ONLY on Railway to bypass IP blocks.
    Uses Direct connection on localhost/others.
    """
    url = "https://www.oref.org.il/WarningMessages/alert/alerts.json"
    home_url = "https://www.oref.org.il/"
    headers = OREF_HEADERS
    
    # Dynamically load the latest configuration (Hot-swappable Proxies)
    current_config = get_config()
    proxy_config = current_config.get("proxy")
    
    # Check if running on Railway
    is_railway = os.getenv("RAILWAY_ENVIRONMENT") is not None
    
    def attempt_request(proxy_config=None):
        if proxy_config:
            p_url = proxy_config["url"]
            p_type = proxy_config["type"]
            logger.info(f"🎯 [PROXY FETCH] using {p_url} ({p_type})")
            
            if p_type == "socks5":
                proxy_str = f"socks5h://{p_url}"
            else:
                proxy_str = f"http://{p_url}"
                
            proxies = {"http": proxy_str, "https": proxy_str}
            timeout = 25
        else:
            logger.info("🎯 [DIRECT FETCH] no proxy used")
            proxies = None
            timeout = 10 
            
        try:
            session.cookies.clear()
            # Visit home page first to get cookies
            session.get(home_url, headers={'User-Agent': headers['User-Agent']}, timeout=timeout, proxies=proxies)
            time.sleep(1.2) # Small break
            
            response = session.get(url, headers=headers, timeout=timeout, proxies=proxies)
            return response
        except Exception as e:
            logger.warning(f"Fetch failed: {e}")
            # If we fail, we reset the session for the NEXT attempt to ensure no stuck sockets
            reset_session()
            return None

    if is_railway:
        logger.info("RAILWAY DETECTED: Routing via Proxy Only...")
        response = attempt_request(proxy_config)
        if response and response.status_code == 200:
            logger.info(f"SUCCESS: Fetched alerts via proxy: {proxy_config['url']}")
        return process_response(response)
    else:
        logger.info("LOCALHOST/DEV DETECTED: Routing via Direct Connection Only...")
        response = attempt_request()
        if response and response.status_code == 200:
            logger.info("SUCCESS: Direct connection successful.")
        return process_response(response)

def process_response(response):
    if not response:
        return {"error": "All connection attempts failed"}
    
    if response.status_code != 200:
        logger.error(f"Final response status from Oref: {response.status_code}")
        return {"error": f"Oref API error: {response.status_code}"}

    try:
        content = response.content.decode('utf-8-sig', errors='ignore').strip()
        if not content:
            return None
        return json.loads(content)
    except Exception as e:
        logger.error(f"Failed to process Oref response: {e}")
        return {"error": "Invalid data received from Oref"}
