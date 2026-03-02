import requests
import json
import logging
import time
import random

import os

logger = logging.getLogger(__name__)

# Global session to persist cookies and connection
session = requests.Session()

def load_proxies():
    """Load proxies from the external configuration file."""
    try:
        # Resolve the path to app/resources/proxies.json
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        proxy_path = os.path.join(base_dir, "resources", "proxies.json")
        
        if os.path.exists(proxy_path):
            with open(proxy_path, "r") as f:
                return json.load(f)
        else:
            logger.warning(f"Proxy config file not found at {proxy_path}. Using empty list.")
            return []
    except Exception as e:
        logger.error(f"Failed to load proxies from config: {e}")
        return []

# Dynamic list of Israeli Proxies
ISRAELI_PROXIES = load_proxies()

# State for the currently working proxy
_working_proxy = None
_last_proxy_check = 0
PROXY_CACHE_TTL = 3600 # Cache working proxy for 1 hour

from concurrent.futures import ThreadPoolExecutor, as_completed

def test_proxy(proxy_config):
    """
    Tests if a proxy can reach Oref API with required headers.
    """
    url = "https://www.oref.org.il/WarningMessages/alert/alerts.json"
    p_url = proxy_config["url"]
    p_type = proxy_config["type"]
    
    if p_type == "socks5":
        proxy_str = f"socks5h://{p_url}"
    else:
        proxy_str = f"http://{p_url}"
    
    proxies = {"http": proxy_str, "https": proxy_str}
    
    headers = {
        'Referer': 'https://www.oref.org.il/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest'
    }

    try:
        # 7s timeout for the "is it alive" check - free proxies are slow
        response = requests.get(url, timeout=7, proxies=proxies, headers=headers)
        # 200 is success (even if empty list), 403 is blocked
        return response.status_code == 200
    except Exception:
        return False

def get_working_proxy(force_refresh=False):
    """
    Returns a working proxy from the list, testing them in parallel.
    """
    global _working_proxy, _last_proxy_check
    
    now = time.time()
    if not force_refresh and _working_proxy and (now - _last_proxy_check < PROXY_CACHE_TTL):
        return _working_proxy

    logger.info("Testing Israeli proxies in parallel to find a working one...")
    
    shuffled = ISRAELI_PROXIES.copy()
    random.shuffle(shuffled)
    
    # Test up to 20 proxies at a time in parallel
    batch_size = 20
    for i in range(0, len(shuffled), batch_size):
        batch = shuffled[i:i+batch_size]
        logger.info(f"Testing batch of {len(batch)} proxies...")
        
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            future_to_proxy = {executor.submit(test_proxy, p): p for p in batch}
            for future in as_completed(future_to_proxy):
                proxy = future_to_proxy[future]
                try:
                    if future.result():
                        logger.info(f"Found working proxy: {proxy['url']} ({proxy['type']})")
                        _working_proxy = proxy
                        _last_proxy_check = now
                        return _working_proxy
                except Exception:
                    continue
            
    logger.error("No working proxies found in the entire list!")
    _working_proxy = None
    return None

def fetch_active_alerts():
    """
    Fetches the active alerts from the Oref API.
    Uses extensive headers, persistent session, and Israeli proxies to bypass 403 blocks.
    """
    url = "https://www.oref.org.il/WarningMessages/alert/alerts.json"
    home_url = "https://www.oref.org.il/"
    
    headers = {
        'Host': 'www.oref.org.il',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'he-IL,he;q=0.9,en-US;q=0.8,en;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': home_url,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
        'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin'
    }

    def attempt_request(proxy_config=None):
        if proxy_config:
            p_url = proxy_config["url"]
            p_type = proxy_config["type"]
            if p_type == "socks5":
                proxy_str = f"socks5h://{p_url}"
            else:
                proxy_str = f"http://{p_url}"
            proxies = {"http": proxy_str, "https": proxy_str}
            timeout = 25 # Increased timeout for unreliable free proxies
        else:
            proxies = None
            timeout = 10 
            
        try:
            # Always clear cookies before a new attempt to avoid session state issues
            session.cookies.clear()
            
            # Visit home page first to get cookies/session state
            logger.info(f"Visiting Oref homepage via {proxy_config['url'] if proxy_config else 'Direct'}...")
            session.get(home_url, headers={'User-Agent': headers['User-Agent']}, timeout=timeout, proxies=proxies)
            time.sleep(1.5)
            
            response = session.get(url, headers=headers, timeout=timeout, proxies=proxies)
            return response
        except Exception as e:
            logger.warning(f"Request failed with {proxy_config['type'] if proxy_config else 'Direct'}: {e}")
            return None

    # Step 1: Try Direct first
    response = attempt_request()
    
    # Step 2: If direct fails or 403, try proxies
    import os
    is_railway = os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("PORT") is not None
    
    # On Local, we might still want to test proxies if direct fails, OR keep it restricted. 
    # User said "your solution is not working", so let's allow it if direct fails even on non-railway for testing.
    if not response or response.status_code == 403:
        logger.info("Direct request blocked or failed. Attempting to use a working proxy...")
        
        # Try up to 3 different "working" proxies in case one dies
        for attempt in range(3):
            proxy = get_working_proxy(force_refresh=(attempt > 0))
            if not proxy:
                break
                
            response = attempt_request(proxy)
            if response and response.status_code == 200:
                logger.info(f"Successfully fetched alerts via proxy: {proxy['url']}")
                return process_response(response)
            elif response:
                logger.warning(f"Proxy {proxy['url']} returned status {response.status_code}")
                # If it's a 403 via proxy, it might mean the proxy itself is blocked or bad headers
                # we'll let it loop and try another if refresh is forced
    
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
