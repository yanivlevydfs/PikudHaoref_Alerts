import requests
import json
import logging
import time
import random

logger = logging.getLogger(__name__)

# Global session to persist cookies and connection
session = requests.Session()

# List of free Israeli Proxies (HTTP and SOCKS5)
# Note: Free proxies are unreliable; these are gathered from public lists.
ISRAELI_PROXIES = [
    {"url": "129.159.159.78:3128", "type": "http"},
    {"url": "51.16.6.90:3128", "type": "http"},
    {"url": "185.241.5.57:3128", "type": "http"},
    {"url": "51.16.49.113:189", "type": "http"},
    {"url": "51.85.49.118:8823", "type": "http"},
    {"url": "144.24.161.2:3128", "type": "http"},
    {"url": "193.106.31.254:3128", "type": "http"},
    {"url": "149.88.66.150:7890", "type": "socks5"},
    {"url": "51.16.56.189:8001", "type": "socks5"},
    {"url": "185.241.5.57:8888", "type": "http"},
    {"url": "82.81.111.109:80", "type": "http"}
]

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
            timeout = 20 # Slower timeout for proxies
        else:
            proxies = None
            timeout = 10 # Faster timeout for direct
            
        try:
            if not session.cookies:
                logger.info(f"Visiting Oref homepage (Proxy: {proxy_config['url'] if proxy_config else 'Direct'})...")
                session.get(home_url, headers={'User-Agent': headers['User-Agent']}, timeout=timeout, proxies=proxies)
                time.sleep(1)
            
            response = session.get(url, headers=headers, timeout=timeout, proxies=proxies)
            return response
        except Exception as e:
            logger.warning(f"Request failed with {proxy_config['type'] if proxy_config else 'Direct'} proxy {proxy_config['url'] if proxy_config else ''}: {e}")
            return None

    # Step 1: Try Direct first
    response = attempt_request()
    
    # Step 2: If direct fails or 403, try proxies ONLY on Railway
    import os
    is_railway = os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("PORT") is not None
    
    if (not response or response.status_code == 403) and is_railway:
        logger.info("Direct request blocked (403) on Railway. Attempting Israeli proxies...")
        
        # Shuffle proxies to distribute load
        shuffled_proxies = ISRAELI_PROXIES.copy()
        random.shuffle(shuffled_proxies)
        
        for proxy in shuffled_proxies:
            session.cookies.clear() # Fresh session for each proxy
            logger.info(f"Trying Israeli {proxy['type']} proxy: {proxy['url']}")
            response = attempt_request(proxy)
            
            if response and response.status_code == 200:
                logger.info(f"Successfully fetched alerts via proxy: {proxy['url']}")
                break
            elif response:
                logger.warning(f"Proxy {proxy['url']} returned status {response.status_code}")
    elif response and response.status_code == 403 and not is_railway:
        logger.warning("Direct request blocked (403) on Localhost. Proxies are disabled for dev.")

    # Final check
    if not response:
        return {"error": "All connection attempts (Direct + Proxies) failed"}
    
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
