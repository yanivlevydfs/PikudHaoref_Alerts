import threading

class AlertState:
    def __init__(self):
        self.data = None
        self.lock = threading.Lock()

    def update(self, new_data):
        with self.lock:
            self.data = new_data
            
    def get(self):
        with self.lock:
            return self.data

global_alert_state = AlertState()
