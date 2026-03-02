import threading

class AlertState:
    def __init__(self):
        self.data = None
        self.is_online = True # Default to True until first poll fails
        self.lock = threading.Lock()

    def update(self, new_data):
        with self.lock:
            # If API returns None or an error, we keep the current state but mark as offline
            if new_data is None or (isinstance(new_data, dict) and "error" in new_data):
                self.is_online = False
                return

            self.is_online = True
            
            # Explicit check for "Empty" response (success but no alerts)
            # Oref API returns empty list or empty string when no alerts are active.
            if not new_data or ("data" in new_data and not new_data["data"]):
                self.data = None
                return

            # If we have new data, accumulate it
            new_cities = set(new_data.get("data", []))
            
            if not self.data:
                # Fresh start for a new bulk
                self.data = new_data
            else:
                # Merge cities into existing data to keep the map "Full" of the bulk
                existing_cities = set(self.data.get("data", []))
                merged_cities = list(existing_cities.union(new_cities))
                
                self.data["data"] = merged_cities
                # Always update with the latest metadata
                self.data["id"] = new_data.get("id", self.data.get("id"))
                self.data["title"] = new_data.get("title", self.data.get("title"))
                self.data["desc"] = new_data.get("desc", self.data.get("desc"))
            
    def get(self):
        with self.lock:
            return self.data

global_alert_state = AlertState()
