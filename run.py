#!/usr/bin/env python
import sys
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sora-api")

# Ensure console output encoding is UTF-8
if sys.platform.startswith('win'):
    os.system("chcp 65001")
    sys.stdout.reconfigure(encoding='utf-8')
elif sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
 
# Ensure src directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Preload app and key_manager to ensure API keys are loaded before startup
from src.app import app, key_manager
from src.main import init_app
from src.config import Config
import uvicorn

if __name__ == "__main__":
    # Set environment variable to ensure proper UTF-8 handling
    os.environ["PYTHONIOENCODING"] = "utf-8"
    
    # Initialize application
    init_app()
    
    # Start server
    logger.info(f"Starting OpenAI-compatible Sora API service: {Config.HOST}:{Config.PORT}")
    logger.info(f"Loaded {len(key_manager.keys)} API key(s)")
    uvicorn.run(
        "src.app:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=False  # Disable auto-reload in production
    )