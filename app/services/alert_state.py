import threading
import logging

logger = logging.getLogger(__name__)

class AlertState:
    def __init__(self):
        self.data = None
        self.is_online = True # Default to True until first poll fails
        self.lock = threading.Lock()

    def update(self, new_data):
        with self.lock:
            # Case 1: Real Connection Error or API Block
            if isinstance(new_data, dict) and "error" in new_data:
                if self.is_online:
                    logger.warning(f"System status changed to OFFLINE: {new_data['error']}")
                self.is_online = False
                return

            # Case 2: Success! (Either active alerts or empty state)
            # CRITICAL: We explicitly flip this back to True BEFORE processing data
            if not self.is_online:
                logger.info("System status recovered to ONLINE.")
            self.is_online = True
            
            # Normalize list responses to a single "bulk" object or None if empty
            normalized_alert = None
            if isinstance(new_data, list) and len(new_data) > 0:
                # If multiple alerts, merge them into one "Current Bulk"
                normalized_alert = new_data[0] # Base metadata from the first/latest
                all_cities = []
                for entry in new_data:
                    all_cities.extend(entry.get("data", []))
                normalized_alert["data"] = list(set(all_cities))
            elif isinstance(new_data, dict) and new_data.get("data"):
                normalized_alert = new_data

            # Case 2a: Explicit check for "Empty" response (success but no active alerts)
            if not normalized_alert:
                self.data = None
                return

            # Case 3: We have fresh active alerts to accumulate
            new_cities = set(normalized_alert.get("data", []))
            
            if not self.data:
                # Fresh start for a new bulk
                self.data = normalized_alert
            else:
                # Merge cities into existing data to keep the map "Full" of the bulk
                existing_cities = set(self.data.get("data", []))
                merged_cities = list(existing_cities.union(new_cities))
                
                self.data["data"] = merged_cities
                # Always update with the latest metadata
                self.data["id"] = normalized_alert.get("id", self.data.get("id"))
                self.data["title"] = normalized_alert.get("title", self.data.get("title"))
                self.data["desc"] = normalized_alert.get("desc", self.data.get("desc"))
            
    def get(self):
        with self.lock:
            return self.data

global_alert_state = AlertState()
