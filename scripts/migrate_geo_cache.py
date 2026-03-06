import json
import sqlite3
import os
import sys

# Ensure we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.database import save_geolocation

CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "app", "db", "geo_cache.json")

def migrate():
    print(f"Reading legacy cache from: {CACHE_FILE}")
    
    if not os.path.exists(CACHE_FILE):
        print("No geo_cache.json found. Nothing to migrate.")
        return

    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)
            
        print(f"Found {len(cache)} coordinates in legacy cache.")
        
        migrated = 0
        for city_name, data in cache.items():
            is_found = data != "NOT_FOUND"
            geo_data = data if is_found else None
            
            success = save_geolocation(city_name, is_found, geo_data)
            if success:
                migrated += 1
            else:
                print(f"Failed to migrate: {city_name}")
                
        print(f"✅ Successfully migrated {migrated} out of {len(cache)} records to the SQLite database.")
        
        # Optionally rename the old file so it isn't accidentally loaded or overwritten
        backup_file = CACHE_FILE + ".bak"
        os.rename(CACHE_FILE, backup_file)
        print(f"ℹ️ Renamed legacy cache to {backup_file} for safety.")
        
    except Exception as e:
        print(f"Migration error: {e}")

if __name__ == "__main__":
    migrate()
