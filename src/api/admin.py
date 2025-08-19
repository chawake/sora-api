import os
import logging
import dotenv
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..models.schemas import ApiKeyCreate, ApiKeyUpdate, ConfigUpdate, LogLevelUpdate, BatchOperation, BatchImportOperation
from ..api.dependencies import verify_admin, verify_admin_jwt
from ..config import Config
from ..key_manager import key_manager
from ..sora_integration import SoraClient

# Configure logging
logger = logging.getLogger("sora-api.admin")

# Logging configuration
class LogConfig:
    LEVEL = os.getenv("LOG_LEVEL", "WARNING").upper()
    FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

# Create router
router = APIRouter(prefix="/api")

# Key management APIs
@router.get("/keys")
async def get_all_keys(admin_token = Depends(verify_admin_jwt)):
    """Get all API keys"""
    return key_manager.get_all_keys()

@router.get("/keys/{key_id}")
async def get_key(key_id: str, admin_token = Depends(verify_admin_jwt)):
    """Get details of a single API key"""
    key = key_manager.get_key_by_id(key_id)
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    return key

@router.post("/keys")
async def create_key(key_data: ApiKeyCreate, admin_token = Depends(verify_admin_jwt)):
    """Create a new API key"""
    try:
        # Ensure the key value includes the Bearer prefix
        key_value = key_data.key_value
        if not key_value.startswith("Bearer "):
            key_value = f"Bearer {key_value}"
            
        new_key = key_manager.add_key(
            key_value,
            name=key_data.name,
            weight=key_data.weight,
            rate_limit=key_data.rate_limit,
            is_enabled=key_data.is_enabled,
            notes=key_data.notes
        )
        
        # Persist all keys via Config
        Config.save_api_keys(key_manager.keys)
        
        return new_key
    except Exception as e:
        logger.error(f"Failed to create API key: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/keys/{key_id}")
async def update_key(key_id: str, key_data: ApiKeyUpdate, admin_token = Depends(verify_admin_jwt)):
    """Update API key information"""
    try:
        # If a new key value is provided, ensure it includes the Bearer prefix
        key_value = key_data.key_value
        if key_value and not key_value.startswith("Bearer "):
            key_value = f"Bearer {key_value}"
            key_data.key_value = key_value
            
        updated_key = key_manager.update_key(
            key_id,
            key_value=key_data.key_value,
            name=key_data.name,
            weight=key_data.weight,
            rate_limit=key_data.rate_limit,
            is_enabled=key_data.is_enabled,
            notes=key_data.notes
        )
        if not updated_key:
            raise HTTPException(status_code=404, detail="API key not found")
        
        # Persist all keys via Config
        Config.save_api_keys(key_manager.keys)
        
        return updated_key
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update API key: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/keys/{key_id}")
async def delete_key(key_id: str, admin_token = Depends(verify_admin_jwt)):
    """Delete an API key"""
    success = key_manager.delete_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # Persist all keys via Config
    Config.save_api_keys(key_manager.keys)
    
    return {"status": "success", "message": "API key deleted"}

@router.get("/stats")
async def get_usage_stats(admin_token = Depends(verify_admin_jwt)):
    """Get API usage statistics"""
    stats = key_manager.get_usage_stats()
    
    # Process daily_usage data for frontend display
    daily_usage = {}
    keys_usage = {}
    
    # Convert past_7_days data to daily_usage format
    for date, counts in stats.get("past_7_days", {}).items():
        daily_usage[date] = counts.get("successful", 0) + counts.get("failed", 0)
    
    # Build per-key usage
    for key in key_manager.keys:
        key_id = key.get("id")
        key_name = key.get("name") or f"Key_{key_id[:6]}"
        
        # Get usage stats for this key
        if key_id in key_manager.usage_stats:
            key_stats = key_manager.usage_stats[key_id]
            total_requests = key_stats.get("total_requests", 0)
            
            if total_requests > 0:
                keys_usage[key_name] = total_requests
    
    # Add to return payload
    stats["daily_usage"] = daily_usage
    stats["keys_usage"] = keys_usage
    
    return stats

@router.post("/keys/test")
async def test_key(key_data: ApiKeyCreate, admin_token = Depends(verify_admin_jwt)):
    """Test whether an API key is valid"""
    try:
        # Get key value
        key_value = key_data.key_value.strip()
        
        # Ensure key format is correct
        if not key_value.startswith("Bearer "):
            key_value = f"Bearer {key_value}"
        
        # Get proxy configuration
        proxy_host = Config.PROXY_HOST if Config.PROXY_HOST and Config.PROXY_HOST.strip() else None
        proxy_port = Config.PROXY_PORT if Config.PROXY_PORT and Config.PROXY_PORT.strip() else None
        proxy_user = Config.PROXY_USER if Config.PROXY_USER and Config.PROXY_USER.strip() else None
        proxy_pass = Config.PROXY_PASS if Config.PROXY_PASS and Config.PROXY_PASS.strip() else None
        
        test_client = SoraClient(
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            proxy_user=proxy_user,
            proxy_pass=proxy_pass,
            auth_token=key_value
        )
        
        # Perform a simple API call to test connectivity
        test_result = await test_client.test_connection()
        logger.info(f"API key test result: {test_result}")
        
        # Check the status in the underlying test result
        if test_result.get("status") == "success":
            # API connectivity test succeeded
            return {
                "status": "success", 
                "message": "API key test successful", 
                "details": test_result,
                "success": True
            }
        else:
            # API connectivity test failed
            return {
                "status": "error", 
                "message": f"API key test failed: {test_result.get('message', 'connection failed')}", 
                "details": test_result,
                "success": False
            }
    except Exception as e:
        logger.error(f"API key test error: {str(e)}", exc_info=True)
        return {
            "status": "error", 
            "message": f"API key test failed: {str(e)}",
            "success": False
        }

@router.post("/keys/batch")
async def batch_operation(operation: Dict[str, Any], admin_token = Depends(verify_admin_jwt)):
    """Batch operations on API keys"""
    try:
        action = operation.get("action")
        logger.info(f"Received batch operation request: {action}")
        
        if not action:
            logger.warning("Batch operation is missing 'action' parameter")
            raise HTTPException(status_code=400, detail="Missing required parameter: action")
        
        logger.info(f"Batch operation type: {action}")
        
        if action == "import":
            # Batch import API keys
            keys_data = operation.get("keys", [])
            if not keys_data:
                logger.warning("Batch import is missing 'keys' data")
                raise HTTPException(status_code=400, detail="No key data provided")
            
            logger.info(f"Preparing to import {len(keys_data)} keys")
            
            # Ensure each key has the Bearer prefix
            for key_data in keys_data:
                if isinstance(key_data, dict):
                    key_value = key_data.get("key", "").strip()
                    if key_value and not key_value.startswith("Bearer "):
                        key_data["key"] = f"Bearer {key_value}"
            
            # Execute batch import
            try:
                result = key_manager.batch_import_keys(keys_data)
                logger.info(f"Import result: imported={result['imported']}, skipped={result['skipped']}")
                
                # Persist all keys via Config
                Config.save_api_keys(key_manager.keys)
                
                return {
                    "success": True,
                    "message": f"Imported {result['imported']} keys, skipped {result['skipped']} duplicate keys",
                    "imported": result["imported"],
                    "skipped": result["skipped"]
                }
            except Exception as e:
                logger.error(f"Batch import error: {str(e)}", exc_info=True)
                raise HTTPException(status_code=500, detail=f"Failed to import keys: {str(e)}")
                
        elif action not in ["enable", "disable", "delete"]:
            logger.warning(f"Unsupported batch operation: {action}")
            raise HTTPException(status_code=400, detail=f"Unsupported operation: {action}")
            
        # For non-import operations, key_ids must be provided
        key_ids = operation.get("key_ids", [])
        if not key_ids:
            logger.warning(f"{action} operation is missing 'key_ids' parameter")
            raise HTTPException(status_code=400, detail="Missing required parameter: key_ids")
            
        # Ensure key_ids is a list
        if isinstance(key_ids, str):
            key_ids = [key_ids]
            
        logger.info(f"Batch {action} operation on {len(key_ids)} keys")
            
        if action == "enable":
            # Batch enable
            success_count = 0
            for key_id in key_ids:
                updated = key_manager.update_key(key_id, is_enabled=True)
                if updated:
                    success_count += 1
            
            # Persist all keys via Config
            Config.save_api_keys(key_manager.keys)
            
            logger.info(f"Enabled {success_count} keys")
            return {
                "success": True,
                "message": f"Successfully enabled {success_count} key(s)",
                "affected": success_count
            }
        elif action == "disable":
            # Batch disable
            success_count = 0
            for key_id in key_ids:
                updated = key_manager.update_key(key_id, is_enabled=False)
                if updated:
                    success_count += 1
            
            # Persist all keys via Config
            Config.save_api_keys(key_manager.keys)
            
            logger.info(f"Disabled {success_count} keys")
            return {
                "success": True,
                "message": f"Successfully disabled {success_count} key(s)",
                "affected": success_count
            }
        elif action == "delete":
            # Batch delete
            success_count = 0
            for key_id in key_ids:
                if key_manager.delete_key(key_id):
                    success_count += 1
            
            # Persist all keys via Config
            Config.save_api_keys(key_manager.keys)
            
            logger.info(f"Deleted {success_count} keys")
            return {
                "success": True,
                "message": f"Successfully deleted {success_count} key(s)",
                "affected": success_count
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch operation failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# Configuration management APIs
@router.get("/config")
async def get_config(admin_token = Depends(verify_admin_jwt)):
    """Get current system configuration"""
    return {
        "HOST": Config.HOST,
        "PORT": Config.PORT,
        "BASE_URL": Config.BASE_URL,
        "PROXY_HOST": Config.PROXY_HOST,
        "PROXY_PORT": Config.PROXY_PORT,
        "PROXY_USER": Config.PROXY_USER,
        "PROXY_PASS": "******" if Config.PROXY_PASS else "",
        "IMAGE_LOCALIZATION": Config.IMAGE_LOCALIZATION,
        "IMAGE_SAVE_DIR": Config.IMAGE_SAVE_DIR,
        "API_AUTH_TOKEN": bool(Config.API_AUTH_TOKEN)  # return only whether set, not the actual value
    }

@router.post("/config")
async def update_config(config_data: ConfigUpdate, admin_token = Depends(verify_admin_jwt)):
    """Update system configuration"""
    try:
        changes = []
        
        # Update proxy settings
        if config_data.PROXY_HOST is not None:
            Config.PROXY_HOST = config_data.PROXY_HOST
            changes.append("PROXY_HOST")
            # Update environment variable
            os.environ["PROXY_HOST"] = config_data.PROXY_HOST
            
        if config_data.PROXY_PORT is not None:
            Config.PROXY_PORT = config_data.PROXY_PORT
            changes.append("PROXY_PORT")
            # Update environment variable
            os.environ["PROXY_PORT"] = config_data.PROXY_PORT
            
        # Update proxy authentication settings
        if config_data.PROXY_USER is not None:
            Config.PROXY_USER = config_data.PROXY_USER
            changes.append("PROXY_USER")
            # Update environment variable
            os.environ["PROXY_USER"] = config_data.PROXY_USER
            
        if config_data.PROXY_PASS is not None:
            Config.PROXY_PASS = config_data.PROXY_PASS
            changes.append("PROXY_PASS")
            # Update environment variable
            os.environ["PROXY_PASS"] = config_data.PROXY_PASS
            
        # Update base URL setting
        if config_data.BASE_URL is not None:
            Config.BASE_URL = config_data.BASE_URL
            changes.append("BASE_URL")
            # Update environment variable
            os.environ["BASE_URL"] = config_data.BASE_URL
            
        # Update image localization setting
        if config_data.IMAGE_LOCALIZATION is not None:
            Config.IMAGE_LOCALIZATION = config_data.IMAGE_LOCALIZATION
            changes.append("IMAGE_LOCALIZATION")
            # Update environment variable
            os.environ["IMAGE_LOCALIZATION"] = str(config_data.IMAGE_LOCALIZATION)
            
        if config_data.IMAGE_SAVE_DIR is not None:
            Config.IMAGE_SAVE_DIR = config_data.IMAGE_SAVE_DIR
            changes.append("IMAGE_SAVE_DIR")
            # Update environment variable
            os.environ["IMAGE_SAVE_DIR"] = config_data.IMAGE_SAVE_DIR
            # Ensure directory exists
            os.makedirs(Config.IMAGE_SAVE_DIR, exist_ok=True)
            
        # Persist to .env file if requested
        if config_data.save_to_env and changes:
            env_file = os.path.join(Config.BASE_DIR, '.env')
            env_data = {}
            
            # Read existing .env file if it exists
            if os.path.exists(env_file):
                env_data = dotenv.dotenv_values(env_file)
                
            # Update environment variables
            for field in changes:
                value = getattr(Config, field)
                env_data[field] = str(value)
                
            # Write to .env file
            with open(env_file, 'w') as f:
                for key, value in env_data.items():
                    f.write(f"{key}={value}\n")
                    
            logger.info(f"Configuration saved to .env: {changes}")
        
        return {
            "status": "success", 
            "message": f"Configuration updated: {', '.join(changes) if changes else 'no changes'}"
        }
    except Exception as e:
        logger.error(f"Failed to update configuration: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to update configuration: {str(e)}")

@router.post("/logs/level")
async def update_log_level(data: LogLevelUpdate, admin_token = Depends(verify_admin_jwt)):
    """Update logging level"""
    try:
        # Validate logging level
        level = data.level.upper()
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        if level not in valid_levels:
            raise HTTPException(status_code=400, detail=f"Invalid log level: {level}")
        
        # Update the root logger level
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, level))
        
        # Update the sora-api module logger as well
        sora_logger = logging.getLogger("sora-api")
        sora_logger.setLevel(getattr(logging, level))
        
        # Log the level change
        logger.info(f"Log level updated to: {level}")
        
        # Save to environment if requested
        if data.save_to_env:
            env_file = os.path.join(Config.BASE_DIR, '.env')
            env_data = {}
            
            # Read existing .env file if present
            if os.path.exists(env_file):
                env_data = dotenv.dotenv_values(env_file)
                
            # Update LOG_LEVEL environment variable
            env_data["LOG_LEVEL"] = level
                
            # Write to .env file
            with open(env_file, 'w') as f:
                for key, value in env_data.items():
                    f.write(f"{key}={value}\n")
            
            # Log persistence info
            logger.info(f"Saved log level to .env: LOG_LEVEL={level}")
        
        return {"status": "success", "message": f"Log level updated to: {level}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update log level: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to update log level: {str(e)}")

# Admin key APIs - moved to app.py