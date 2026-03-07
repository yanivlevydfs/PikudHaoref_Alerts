import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime

import os

logger = logging.getLogger("pikudhaoref_app.database")

# Support dynamic directory paths for persistent Volumes (Railway)
# Default to the directory of this file (app/db)
DEFAULT_DB_DIR = Path(__file__).parent.absolute()
db_dir = os.getenv("DB_DIR", str(DEFAULT_DB_DIR))
DB_PATH = Path(db_dir) / "alerts_history.db"

def get_db_connection():
    """Establish and return a threaded connection to the SQLite database with high-performance PRAGMAs."""
    # check_same_thread=False is required for FastAPI global dependencies or BackgroundSchedulers
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=20.0, isolation_level=None)
    conn.row_factory = sqlite3.Row
    
    # Enable Write-Ahead Logging (WAL) for high concurrency (readers don't block writers)
    conn.execute('PRAGMA journal_mode=WAL;')
    
    # Synchronous NORMAL is perfectly safe in WAL mode and much faster (less fsync calls)
    conn.execute('PRAGMA synchronous=NORMAL;')
    
    # Increase cache size for better performance (negative means KB: -64000 = ~64MB)
    conn.execute('PRAGMA cache_size=-64000;')
    
    # Keep temp tables and indices in memory rather than on disk
    conn.execute('PRAGMA temp_store=MEMORY;')
    
    # Map the database into memory up to 256MB for ultra-fast reads
    conn.execute('PRAGMA mmap_size=268435456;')
    
    # Busy timeout ensures locked threads wait natively rather than throwing errors immediately
    conn.execute('PRAGMA busy_timeout=5000;')
    
    return conn

def init_db():
    """Initialize the database schema with performance indexes."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Create the main alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_id TEXT UNIQUE NOT NULL,
                    title TEXT,
                    category TEXT,
                    description TEXT,
                    locations_json TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create the system_state table for cross-process synchronization
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            # Create the geolocations table for permanent coordinate storage
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS geolocations (
                    city_name TEXT PRIMARY KEY,
                    is_found BOOLEAN NOT NULL DEFAULT 0,
                    geo_data TEXT,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for high performance querying
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON alerts(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alert_id ON alerts(alert_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_geolocations_city ON geolocations(city_name)')
            
            conn.commit()
            logger.info("Database initialized successfully with indexes.")
            
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

def insert_alert_if_new(alert_data):
    """
    Inserts an alert payload if its ID doesn't already exist.
    Takes the Oref alert dictionary.
    Returns True if inserted, False if it was a duplicate.
    """
    if not alert_data or "id" not in alert_data:
        return False
        
    alert_id = alert_data["id"]
    title = alert_data.get("title", "")
    category = alert_data.get("cat", "")
    description = alert_data.get("desc", "")
    locations = alert_data.get("data", [])
    locations_json = json.dumps(locations, ensure_ascii=False)
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Use INSERT OR IGNORE leveraging the UNIQUE constraint on alert_id
            cursor.execute('''
                INSERT OR IGNORE INTO alerts 
                (alert_id, title, category, description, locations_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (alert_id, title, category, description, locations_json, datetime.now()))
            
            if cursor.rowcount > 0:
                conn.commit()
                logger.info(f"New alert '{alert_id}' inserted into database.")
                return True
            else:
                # Was a duplicate, ignored
                return False
                
    except Exception as e:
        logger.error(f"Error inserting alert '{alert_id}' into DB: {e}")
        return False

def get_recent_alerts(hours=24):
    """
    Fetch alerts from the database that occurred within the last 'hours'.
    Returns a list of dictionaries.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # The idx_timestamp index makes this query blazing fast
            cursor.execute('''
                SELECT alert_id, title, category, description, locations_json, timestamp
                FROM alerts
                WHERE timestamp >= datetime('now', ?)
                ORDER BY timestamp DESC
            ''', (f'-{hours} hours',))
            
            rows = cursor.fetchall()
            alerts = []
            for row in rows:
                alert_dict = dict(row)
                # Parse the JSON string back to a Python list
                alert_dict['locations'] = json.loads(alert_dict.pop('locations_json'))
                alerts.append(alert_dict)
                
            return alerts
            
    except Exception as e:
        logger.error(f"Error fetching recent alerts: {e}")
        return []

def get_alert_statistics(timeframe="24h"):
    """
    Fetches aggregated alert statistics per city.
    Uses SQLite's json_each to unpack the locations_json array efficiently.
    """
    timeframe_map = {
        "24h": "-1 day",
        "1w": "-7 days",
        "1m": "-1 month",
        "6m": "-6 months",
        "1y": "-1 year",
        "all": None
    }
    
    sql_modifier = timeframe_map.get(timeframe, "-1 day")
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if sql_modifier is None:
                # All time
                query = '''
                    SELECT j.value as city, COUNT(*) as count 
                    FROM alerts, json_each(alerts.locations_json) as j 
                    GROUP BY city 
                    ORDER BY count DESC
                '''
                cursor.execute(query)
            else:
                # Time filtered
                query = '''
                    SELECT j.value as city, COUNT(*) as count 
                    FROM alerts, json_each(alerts.locations_json) as j 
                    WHERE timestamp >= datetime('now', ?)
                    GROUP BY city 
                    ORDER BY count DESC
                '''
                cursor.execute(query, (sql_modifier,))
                
            rows = cursor.fetchall()
            stats = [{"city": row["city"], "count": row["count"]} for row in rows]
            return stats
            
    except Exception as e:
        logger.error(f"Error fetching alert statistics: {e}")
        return []

def get_quiet_time_stats(city=None):
    """
    Analyzes all historical data to find the distribution of alerts by hour of the day.
    Returns counts for all 24 hours (00-23).
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if city:
                # Per-city analysis
                query = '''
                    SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
                    FROM alerts, json_each(alerts.locations_json) as j
                    WHERE j.value = ?
                    GROUP BY hour
                    ORDER BY hour ASC
                '''
                cursor.execute(query, (city,))
            else:
                # Global analysis
                query = '''
                    SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
                    FROM alerts
                    GROUP BY hour
                    ORDER BY hour ASC
                '''
                cursor.execute(query)
            
            rows = cursor.fetchall()
            
            # Initialize all 24 hours with 0
            hour_map = {f"{h:02d}": 0 for h in range(24)}
            for row in rows:
                if row["hour"] in hour_map:
                    hour_map[row["hour"]] = row["count"]
            
            # Convert back to sorted list
            result = [{"hour": h, "count": count} for h, count in sorted(hour_map.items())]
            return result
            
    except Exception as e:
        logger.error(f"Error fetching quiet time stats: {e}")
        return []

def get_all_unique_cities():
    """
    Fetches a flat list of all unique cities/places ever intercepted and stored in the database.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # json_each unpacking gives us individual city strings flatly
            query = '''
                SELECT DISTINCT j.value as city
                FROM alerts, json_each(alerts.locations_json) as j
            '''
            cursor.execute(query)
            
            rows = cursor.fetchall()
            cities = [row["city"] for row in rows if row["city"]]
            return cities
            
    except Exception as e:
        logger.error(f"Error fetching all unique cities: {e}")
        return []

def get_missing_cities(known_cities=None):
    """
    Fetches a flat list of all unique cities/places ever intercepted and stored in the database,
    excluding those that already exist in the `geolocations` table natively.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Use SQLite natively to filter out places that are already geocoded/processed
            query = '''
                SELECT DISTINCT j.value as city
                FROM alerts, json_each(alerts.locations_json) as j
                LEFT JOIN geolocations g ON j.value = g.city_name
                WHERE g.city_name IS NULL
            '''
            cursor.execute(query)
            
            rows = cursor.fetchall()
            cities = [row["city"] for row in rows if row["city"]]
            
            logger.info(f"[DB GEO] Fetched {len(cities)} natively missing cities requiring geolocation.")
            return cities
            
    except Exception as e:
        logger.error(f"Error fetching missing cities natively: {e}")
        return []

def get_geolocation_by_city(city_name: str):
    """Retrieves a single parsed GeoJSON object from the database for a city, or None if missing."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT is_found, geo_data FROM geolocations WHERE city_name = ?', (city_name,))
            row = cursor.fetchone()
            if row:
                if row['is_found'] and row['geo_data']:
                    try:
                        return json.loads(row['geo_data'])
                    except:
                        pass
                return "NOT_FOUND"
            return None
    except Exception as e:
        logger.error(f"Error getting geolocation for {city_name}: {e}")
        return None

def get_all_geolocations():
    """Returns a dictionary of all cached geolocations from the SQLite table."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT city_name, is_found, geo_data FROM geolocations')
            rows = cursor.fetchall()
            
            results = {}
            for row in rows:
                city = row['city_name']
                if row['is_found'] and row['geo_data']:
                    try:
                        results[city] = json.loads(row['geo_data'])
                    except:
                        results[city] = "NOT_FOUND"
                else:
                    results[city] = "NOT_FOUND"
                    
            return results
    except Exception as e:
        logger.error(f"Error fetching all geolocations: {e}")
        return {}

def save_geolocation(city_name: str, is_found: bool, geo_data: dict = None):
    """Saves or updates a geolocation entry into the database natively."""
    try:
        geo_str = json.dumps(geo_data, ensure_ascii=False) if geo_data else None
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO geolocations (city_name, is_found, geo_data, updated_at) 
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(city_name) DO UPDATE SET 
                    is_found = excluded.is_found,
                    geo_data = excluded.geo_data,
                    updated_at = excluded.updated_at
            ''', (city_name, int(is_found), geo_str))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error saving geolocation for {city_name}: {e}")
        return False

def set_system_state(key, value):
    """
    Atomically updates or inserts a system state key-value pair.
    Used for cross-process synchronization of 'is_online' and 'active_alerts'.
    """
    try:
        # Convert non-string values to JSON strings
        if not isinstance(value, str):
            val_str = json.dumps(value, ensure_ascii=False)
        else:
            val_str = value
            
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO system_state (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
            ''', (key, val_str))
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Error setting system state '{key}': {e}")
        return False

def get_system_state(key, default=None):
    """
    Retrieves a system state value by key. Robustly parses JSON values.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT value FROM system_state WHERE key = ?', (key,))
            row = cursor.fetchone()
            if row:
                val = row['value']
                try:
                    # Robustly parse JSON (handles null, true, false, numbers, dicts, lists)
                    return json.loads(val)
                except (ValueError, TypeError, json.JSONDecodeError):
                    # Fallback to raw string if not valid JSON
                    return val
            return default
    except Exception as e:
        logger.error(f"Error getting system state '{key}': {e}")
        return default

# Initialize immediately when the module is imported
init_db()
