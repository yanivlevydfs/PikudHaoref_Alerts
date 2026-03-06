import json
import logging
from pathlib import Path

logger = logging.getLogger("pikudhaoref_app.config")

# Path to the configuration file
CONFIG_FILE_PATH = Path("config.json")

# Default configuration
DEFAULT_CONFIG = {
    "scheduler": {
        "routine_interval_seconds": 120,
        "emergency_interval_seconds": 10
    },
    "proxy": {
        "url": "185.241.5.57:3128",
        "type": "http"
    }
}

def load_config():
    """
    Loads the configuration from config.json.
    If the file does not exist, it creates one with default values.
    """
    if not CONFIG_FILE_PATH.exists():
        logger.info(f"Configuration file not found. Creating default configuration at {CONFIG_FILE_PATH}")
        with open(CONFIG_FILE_PATH, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)
        return DEFAULT_CONFIG

    try:
        with open(CONFIG_FILE_PATH, "r") as f:
            config = json.load(f)
            logger.info("Configuration loaded successfully.")
            return config
    except Exception as e:
        logger.error(f"Failed to load configuration file: {e}. Using default configuration.")
        return DEFAULT_CONFIG

# Load configuration on module import
APP_CONFIG = load_config()
