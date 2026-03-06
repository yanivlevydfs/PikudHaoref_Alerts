import json
import logging
from pathlib import Path

logger = logging.getLogger("pikudhaoref_app.config")

# Path to the configuration file
CONFIG_FILE_PATH = Path("config.json")

import os

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
    Prioritizes Environment Variables for Proxy settings.
    """
    config = DEFAULT_CONFIG.copy()

    if CONFIG_FILE_PATH.exists():
        try:
            with open(CONFIG_FILE_PATH, "r") as f:
                loaded_config = json.load(f)
                # Deep merge or simple update
                if "scheduler" in loaded_config:
                    config["scheduler"].update(loaded_config["scheduler"])
                if "proxy" in loaded_config:
                    config["proxy"].update(loaded_config["proxy"])
                logger.info("Configuration loaded from file.")
        except Exception as e:
            logger.error(f"Failed to load configuration file: {e}. Using defaults.")
    else:
        logger.info(f"Configuration file not found. Creating default configuration at {CONFIG_FILE_PATH}")
        with open(CONFIG_FILE_PATH, "w") as f:
            json.dump(DEFAULT_CONFIG, f, indent=4)

    # Environment Variable Overrides (PROXIES ONLY)
    env_url = os.getenv("OREF_PROXY_URL")
    env_type = os.getenv("OREF_PROXY_TYPE")

    if env_url:
        logger.info(f"Using Environment Variable OVERRIDE for Proxy URL: {env_url}")
        config["proxy"]["url"] = env_url
    if env_type:
        config["proxy"]["type"] = env_type

    return config

def get_config():
    """
    Always returns the most up-to-date configuration.
    """
    return load_config()

# Global alias for backward compatibility, but get_config() is preferred for dynamic updates
APP_CONFIG = get_config()
