#!/usr/bin/env python3
"""
Development server launcher for Inbound Voice Agent.
"""
import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """Start the development server."""
    logger.info("Inbound Voice Agent - Development Server")
    logger.info("=" * 60)

    # Check if .env exists
    if not os.path.exists(".env"):
        logger.error("ERROR: .env file not found!")
        logger.info("Please run: python startup.py")
        sys.exit(1)

    # Check if virtual environment is active
    if sys.prefix == sys.base_prefix:
        logger.warning("WARNING: Virtual environment not activated!")
        logger.info("Please activate with: source venv/bin/activate")

    # Start the server
    logger.info("Starting Uvicorn server...")
    logger.info("API available at http://localhost:8000")
    logger.info("Docs available at http://localhost:8000/docs")
    logger.info("")
    logger.info("Press Ctrl+C to stop the server")
    logger.info("=" * 60)

    try:
        subprocess.run(
            [
                "uvicorn",
                "app.main:app",
                "--reload",
                "--host", "0.0.0.0",
                "--port", "8000"
            ]
        )
    except KeyboardInterrupt:
        logger.info("\nServer stopped.")
        sys.exit(0)


if __name__ == "__main__":
    main()
