import sys
import os
import json
import uuid
import sqlite3
from datetime import datetime

# Adjust path to find the 'app' module
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Import our database logic
try:
    from app.db.database import DB_PATH, get_db_connection
    print(f"Using database at: {DB_PATH}")
except ImportError:
    print("Error: Could not import app.db.database. Make sure you are running from the project root.")
    sys.exit(1)

def trigger_alert(cities):
    if not cities:
        cities = ["תל אביב - מרכז העיר", "חיפה - מערב", "ירושלים - מרכז"]
    
    alert_id = str(uuid.uuid4())
    alert_data = {
        "id": alert_id,
        "cat": "1",
        "title": "התרעת בדיקה ידנית",
        "data": cities,
        "desc": "זוהי התרעה שהופעלה באמצעות כלי הבדיקה החיצוני.",
    }

    # 1. Insert into history (Alerts table)
    # This ensures it shows up in the 'History' widget and stays on map after refresh
    locations_json = json.dumps(cities, ensure_ascii=False)
    
    try:
        with get_db_connection() as conn:
            # Insert Alert
            conn.execute('''
                INSERT INTO alerts (alert_id, title, category, description, locations_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (alert_id, alert_data["title"], alert_data["cat"], alert_data["desc"], locations_json, datetime.now()))
            
            # Update active state (System State table)
            # This makes it 'Active' for real-time polling
            conn.execute('''
                INSERT INTO system_state (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            ''', ("active_alert_json", json.dumps(alert_data, ensure_ascii=False)))
            
            conn.execute('''
                INSERT INTO system_state (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            ''', ("is_online", "True"))
            
            conn.commit()
            
        print(f"Successfully triggered alert for: {', '.join(cities)}")
        print("The website should reflect this immediately upon the next poll (usually < 10s).")
        print("Because it was inserted into history, it will persist on the map for 10 minutes.")

    except Exception as e:
        print(f"Error triggering alert: {e}")

if __name__ == "__main__":
    cities_to_trigger = sys.argv[1:]
    trigger_alert(cities_to_trigger)
