import requests
import json
import logging
import time

logger = logging.getLogger(__name__)

# Global session to persist cookies and connection
session = requests.Session()

def fetch_active_alerts():
    """
    Fetches the active alerts from the Oref API.
    Uses more extensive headers, persistent session, and delays to bypass 403 blocks.
    """
    url = "https://www.oref.org.il/WarningMessages/alert/alerts.json"
    home_url = "https://www.oref.org.il/"
    
    # Very specific headers to match a real browser's fingerprint
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
    
    try:
        # Pre-flight: Visit homepage if we don't have cookies yet
        if not session.cookies:
            logger.info("Performing pre-flight request to Oref homepage for cookies...")
            session.get(home_url, headers={'User-Agent': headers['User-Agent']}, timeout=10)
            time.sleep(1.5) # Wait a bit to simulate human reading/loading
        
        # Main request
        response = session.get(url, headers=headers, timeout=10)
        
        if response.status_code == 403:
            logger.error("Oref API returned 403 Forbidden. This likely indicates an IP block on the hosting provider.")
            return {"error": "Oref 403 Access Denied - Possible IP Block"}
            
        if response.status_code != 200:
            logger.error(f"Oref API returned status code {response.status_code}")
            return {"error": f"Oref API error: {response.status_code}"}
            
        response.raise_for_status()
        
        content = response.content.decode('utf-8-sig', errors='ignore').strip()
        
        if not content:
            return None
            
        try:
            data = json.loads(content)
            return data
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON. Raw content received: {content}")
            return {"error": "Failed to parse alerts data from Oref"}
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from Oref: {e}")
        return {"error": str(e)}
