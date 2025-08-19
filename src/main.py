import uvicorn
import logging
from .app import app, key_manager
from .config import Config

# Get the logger
logger = logging.getLogger("sora-api.main")

def init_app():
    """Initialize the application."""
    try:
        # The key manager has been initialized and loaded in app.py
        # Check if there are any available keys
        if not key_manager.keys:
            logger.warning("No API key configured, using a test key.")
            key_manager.add_key(
                key_value="Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjE5MzQ0ZTY1LWJiYzktNDRkMS1hOWQwLWY5NTdiMDc5YmQwZSIsInR5cCI6IkpXVCJ9...",
                name="Default Test Key"
            )

        logger.info(f"API service initialization complete. Loaded {len(key_manager.keys)} API keys.")
    except Exception as e:
        logger.error(f"API service initialization failed: {str(e)}")
        raise

def start():
    """Start the API service."""
    # Initialize the app
    init_app()

    # Print configuration information
    Config.print_config()

    # Start the service
    logger.info(f"Starting service: {Config.HOST}:{Config.PORT}")
    uvicorn.run(
        "src.app:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.VERBOSE_LOGGING  # Enable auto-reload only in debug mode
    )

if __name__ == "__main__":
    start()
