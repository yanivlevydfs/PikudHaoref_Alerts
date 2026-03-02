import threading
import logging

logger = logging.getLogger(__name__)

from app.db.database import get_system_state, set_system_state

class AlertState:
    def __init__(self):
        # We no longer need in-memory storage or locks for cross-process sync
        pass

    @property
    def is_online(self):
        # Fetch directly from DB to ensure cross-worker consistency
        val = get_system_state("is_online", "True")
        return str(val).lower() == "true"

    @is_online.setter
    def is_online(self, value):
        set_system_state("is_online", str(value))

    @property
    def data(self):
        # Fetch active alert bulk from DB
        return get_system_state("active_alert_json")

    @data.setter
    def data(self, value):
        set_system_state("active_alert_json", value)

    def update(self, new_data):
        # Case 1: Real Connection Error or API Block
        if isinstance(new_data, dict) and "error" in new_data:
            if self.is_online:
                logger.warning(f"System status changed to OFFLINE: {new_data['error']}")
            self.is_online = False
            return

        # Case 2: Success! (Either active alerts or empty state)
        if not self.is_online:
            logger.info("✅ System status recovered to ONLINE (Synchronized via DB)")
        self.is_online = True
        
        # Normalize list responses to a single "bulk" object or None if empty
        normalized_alert = None
        if isinstance(new_data, list) and len(new_data) > 0:
            normalized_alert = new_data[0]
            all_cities = []
            for entry in new_data:
                all_cities.extend(entry.get("data", []))
            normalized_alert["data"] = list(set(all_cities))
        elif isinstance(new_data, dict) and new_data.get("data"):
            normalized_alert = new_data

        if not normalized_alert:
            self.data = None
            return

        # Case 3: We have fresh active alerts to accumulate
        new_cities = set(normalized_alert.get("data", []))
        
        current_data = self.data
        if not current_data:
            self.data = normalized_alert
        else:
            existing_cities = set(current_data.get("data", []))
            merged_cities = list(existing_cities.union(new_cities))
            
            current_data["data"] = merged_cities
            current_data["id"] = normalized_alert.get("id", current_data.get("id"))
            current_data["title"] = normalized_alert.get("title", current_data.get("title"))
            current_data["desc"] = normalized_alert.get("desc", current_data.get("desc"))
            self.data = current_data
            
    def get(self):
        return self.data

global_alert_state = AlertState()
