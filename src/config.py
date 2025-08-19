import os
import json
import uuid
from typing import List, Dict
import logging

logger = logging.getLogger("sora-api.config")

class Config:
    # API service configuration
    HOST = os.getenv("API_HOST", "0.0.0.0")
    PORT = int(os.getenv("API_PORT", "8890"))
    
    # Base URL configuration
    BASE_URL = os.getenv("BASE_URL", f"http://0.0.0.0:{PORT}")
    
    # Static file path prefix for handling app deployment in subpaths
    # Example: /sora-api means the app is deployed under /sora-api
    STATIC_PATH_PREFIX = os.getenv("STATIC_PATH_PREFIX", "")
    
    # Proxy configuration
    PROXY_HOST = os.getenv("PROXY_HOST", "")
    PROXY_PORT = os.getenv("PROXY_PORT", "")
    PROXY_USER = os.getenv("PROXY_USER", "")
    PROXY_PASS = os.getenv("PROXY_PASS", "")
    
    # Directory configuration
    ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    BASE_DIR = ROOT_DIR
    STATIC_DIR = os.getenv("STATIC_DIR", os.path.join(BASE_DIR, "src/static"))
    
    # Image save directory - users only need to set this
    IMAGE_SAVE_DIR = os.getenv("IMAGE_SAVE_DIR", os.path.join(STATIC_DIR, "images"))
    
    # Image localization configuration
    IMAGE_LOCALIZATION = os.getenv("IMAGE_LOCALIZATION", "False").lower() in ("true", "1", "yes")
    
    # When external access address is different from server address, use BASE_URL to override image access URL
    # Example: when server is in internal network but accessed via reverse proxy from external network
    
    # API Keys configuration
    API_KEYS = []
    
    # Administrator configuration
    ADMIN_KEY = os.getenv("ADMIN_KEY", "sk-123456")
    KEYS_STORAGE_FILE = os.getenv("KEYS_STORAGE_FILE", "api_keys.json")
    
    # API authentication token
    API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN", "")
    
    # Logging configuration
    VERBOSE_LOGGING = os.getenv("VERBOSE_LOGGING", "False").lower() in ("true", "1", "yes")
    
    @classmethod
    def print_config(cls):
        """Print current configuration information"""
        print("\n==== Sora API Configuration ====")
        print(f"Base directory: {cls.BASE_DIR}")
        print(f"API service address: {cls.HOST}:{cls.PORT}")
        print(f"Base URL: {cls.BASE_URL}")
        
        # API authentication information
        if cls.API_AUTH_TOKEN:
            print(f"API auth token: Set (length: {len(cls.API_AUTH_TOKEN)})")
        else:
            print(f"API auth token: Not set (will use admin panel key)")
        
        # Detailed logging
        if cls.VERBOSE_LOGGING:
            print(f"Static files directory: {cls.STATIC_DIR}")
            print(f"Image save directory: {cls.IMAGE_SAVE_DIR}")
            print(f"Image localization: {'Enabled' if cls.IMAGE_LOCALIZATION else 'Disabled'}")
            
            # Proxy configuration info
            if cls.PROXY_HOST:
                proxy_info = f"{cls.PROXY_HOST}:{cls.PROXY_PORT}"
                if cls.PROXY_USER:
                    proxy_info = f"{cls.PROXY_USER}:****@{proxy_info}"
                print(f"Proxy: {proxy_info}")
            else:
                print(f"Proxy: (Not configured)")
        
        # Ensure required directories exist
        cls._ensure_directories()
        
    @classmethod
    def _ensure_directories(cls):
        """Ensure required directories exist"""
        # Check static files directory
        if not os.path.exists(cls.STATIC_DIR):
            print(f" Warning: Static files directory does not exist: {cls.STATIC_DIR}")
        elif cls.VERBOSE_LOGGING:
            print(f" Static files directory exists")
            
        # Check and create image save directory
        if not os.path.exists(cls.IMAGE_SAVE_DIR):
            try:
                os.makedirs(cls.IMAGE_SAVE_DIR, exist_ok=True)
                if cls.VERBOSE_LOGGING:
                    print(f" Created image save directory: {cls.IMAGE_SAVE_DIR}")
            except Exception as e:
                print(f" Failed to create image save directory: {str(e)}")
        elif cls.VERBOSE_LOGGING:
            print(f" Image save directory exists")
            
            # Test write permissions
            try:
                test_file = os.path.join(cls.IMAGE_SAVE_DIR, '.test_write')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                print(f" Write permission granted for image save directory")
            except Exception as e:
                print(f" No write permission for image save directory: {str(e)}")
    
    @classmethod
    def load_api_keys(cls):
        """Load API keys"""
        # First try to load from environment variables
        api_keys_str = os.getenv("API_KEYS", "")
        if api_keys_str:
            try:
                cls.API_KEYS = json.loads(api_keys_str)
                if cls.VERBOSE_LOGGING:
                    logger.info(f"Loaded {len(cls.API_KEYS)} API keys from environment variables")
                return
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse API keys from environment variables: {e}")
                
        # Then try to load from file
        try:
            if os.path.exists(cls.KEYS_STORAGE_FILE):
                with open(cls.KEYS_STORAGE_FILE, "r", encoding="utf-8") as f:
                    keys_data = json.load(f)
                    if isinstance(keys_data, dict) and "keys" in keys_data:
                        cls.API_KEYS = [k for k in keys_data["keys"] if k.get("key")]
                    else:
                        cls.API_KEYS = keys_data
                    
                    if cls.VERBOSE_LOGGING:
                        logger.info(f"Loaded {len(cls.API_KEYS)} API keys from file")
        except Exception as e:
            logger.error(f"Failed to load API keys from file: {e}") 
    
    @classmethod
    def save_api_keys(cls, keys_data):
        """Save API keys to file"""
        try:
            keys_storage_file = os.path.join(cls.BASE_DIR, cls.KEYS_STORAGE_FILE)
            
            with open(keys_storage_file, "w", encoding="utf-8") as f:
                if isinstance(keys_data, list):
                    json.dump({"keys": keys_data}, f, ensure_ascii=False, indent=2)
                else:
                    json.dump(keys_data, f, ensure_ascii=False, indent=2)
            
            # Update in-memory keys
            if isinstance(keys_data, dict) and "keys" in keys_data:
                cls.API_KEYS = [k for k in keys_data["keys"] if k.get("key")]
            else:
                cls.API_KEYS = keys_data
                
            if cls.VERBOSE_LOGGING:
                logger.info(f"API keys saved to {keys_storage_file}")
        except Exception as e:
            logger.error(f"Failed to save API keys: {e}")
    
    @classmethod
    def save_admin_key(cls):
        """Save admin key to file"""
        try:
            admin_config_file = os.path.join(cls.BASE_DIR, "admin_config.json")
            with open(admin_config_file, "w", encoding="utf-8") as f:
                json.dump({"admin_key": cls.ADMIN_KEY}, f, indent=2)
            
            if cls.VERBOSE_LOGGING:
                logger.info(f"Admin key saved to {admin_config_file}")
        except Exception as e:
            logger.error(f"Failed to save admin key: {e}")