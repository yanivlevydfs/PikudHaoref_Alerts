import logging
import sys

def setup_logging():
    """
    Sets up the application's logging configuration.
    Logs are written to standard output with timestamp, log level, and message.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    logger = logging.getLogger("pikudhaoref_app")
    return logger
