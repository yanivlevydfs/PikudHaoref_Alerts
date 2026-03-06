import requests
import json
import logging
import time

logger = logging.getLogger(__name__)

# Global session to persist cookies and connection
session = requests.Session()

# The only working proxy for now per user request
WORKING_PROXY = {"url": "185.241.5.57:3128", "type": "http"}

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
    Uses extensive headers, persistent session, and a single working proxy to bypass 403 blocks.
    """
    url = "https://www.oref.org.il/WarningMessages/alert/alerts.json"
    home_url = "https://www.oref.org.il/"
    
    headers = OREF_HEADERS

    def attempt_request(proxy_config=None):
        if proxy_config:
            p_url = proxy_config["url"]
            p_type = proxy_config["type"]
            logger.info(f"++++++++++++++++++++++++++++++++++++++++")
            logger.info(f"🎯 [ACTIVE PROXY IN USE] -> {p_url} (Type: {p_type})")
            logger.info(f"++++++++++++++++++++++++++++++++++++++++")
            if p_type == "socks5":
                proxy_str = f"socks5h://{p_url}"
            elif p_type == "socks4":
                proxy_str = f"socks4://{p_url}"
            elif p_type == "https":
                proxy_str = f"https://{p_url}"
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
    logger.info("Attempting direct connection to Oref...")
    response = attempt_request()
    
    if response and response.status_code == 200:
        logger.info("SUCCESS: Direct connection to Oref established.")
        return process_response(response)
    
    if response:
        logger.warning(f"Direct connection returned status {response.status_code}. Might be blocked.")
    else:
        logger.warning("Direct connection failed completely (Timeout/Network Error).")

    # Step 2: Use the single working proxy
    logger.info("Direct request blocked or failed. Attempting to use the working proxy...")
    
    response = attempt_request(WORKING_PROXY)
    if response and response.status_code == 200:
        logger.info(f"SUCCESS: Fetched alerts via working proxy: {WORKING_PROXY['url']}")
        return process_response(response)
    elif response:
        logger.warning(f"Proxy {WORKING_PROXY['url']} returned status {response.status_code}")
    
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
