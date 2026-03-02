import threading

class AlertState:
    def __init__(self):
        self.data = None
        self.is_online = True # Default to True until first poll fails
        self.lock = threading.Lock()

    def update(self, new_data):
        with self.lock:
            # Case 1: Real Connection Error or API Block
            if isinstance(new_data, dict) and "error" in new_data:
                self.is_online = False
                # We keep the current data (persistence during attack blips)
                return

            # Case 2: Success! (Either active alerts or empty state)
            self.is_online = True
            
            # Explicit check for "Empty" response (success but no active alerts)
            # This is when we FINALLY clear the map.
            if new_data is None or (isinstance(new_data, dict) and not new_data.get("data")):
                self.data = None
                return

            # Case 3: We have fresh active alerts to accumulate
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
