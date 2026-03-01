import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime

import os

logger = logging.getLogger("pikudhaoref_app.database")

# Support dynamic directory paths for persistent Volumes (Railway)
db_dir = os.getenv("DB_DIR", "")
DB_PATH = Path(db_dir) / "alerts_history.db"

def get_db_connection():
    """Establish and return a threaded connection to the SQLite database with WAL enabled."""
    # check_same_thread=False is required for FastAPI global dependencies or BackgroundSchedulers
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=15.0)
    conn.row_factory = sqlite3.Row
    
    # Enable Write-Ahead Logging (WAL) for high concurrency (readers don't block writers)
    conn.execute('PRAGMA journal_mode=WAL;')
    # Synchronous NORMAL is perfectly safe in WAL mode and much faster
    conn.execute('PRAGMA synchronous=NORMAL;')
    # Increase cache size for better performance
    conn.execute('PRAGMA cache_size=-64000;')
    
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
            
            # Create indexes for high performance querying
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON alerts(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_alert_id ON alerts(alert_id)')
            
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

# Initialize immediately when the module is imported
init_db()
