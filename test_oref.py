import requests
import json
import sys

# Ensure stdout can handle utf-8 characters properly
if sys.stdout.encoding.lower() != 'utf-8':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

def fetch_alerts():
    url = "https://www.oref.org.il/WarningMessages/alert/alerts.json"
    
    # Headers exactly as requested
    headers = {
        'Referer': 'https://www.oref.org.il/',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    print(f"Fetching alerts from {url}...")
    
    try:
        # We add timeout just in case it hangs
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        response.raise_for_status()
        
        # Oref API returns empty content if there are no active alerts
        content = response.content.decode('utf-8-sig', errors='ignore').strip()
        
        if not content:
            print("\nNo active alerts at the moment (Response is empty).")
            return
            
        # Try to parse as JSON
        try:
            data = json.loads(content)
            print("\nActive Alerts found:")
            print(json.dumps(data, indent=4, ensure_ascii=False))
        except json.JSONDecodeError:
            print("\nFailed to parse JSON. Raw content received:")
            print(content)
            
    except requests.exceptions.RequestException as e:
        print(f"\nError fetching data: {e}")

if __name__ == "__main__":
    fetch_alerts()
