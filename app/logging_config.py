"""
Logging utilities for the Inbound Voice Agent.
"""
import logging
import logging.handlers
import os
from app.config import settings


def setup_logging():
    """Configure logging for the application."""
    # Create logs directory
    log_dir = os.path.dirname(settings.log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(settings.log_level)

    # Create formatters
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # File handler with rotation
    if log_dir:
        file_handler = logging.handlers.RotatingFileHandler(
            settings.log_file,
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# Set up logging when module is imported
setup_logging()
