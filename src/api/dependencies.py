from typing import Optional, Tuple, Dict, Any
from fastapi import Request, HTTPException, Depends, Header
import aiohttp
import logging
from ..config import Config
from .auth import verify_jwt_token

logger = logging.getLogger("sora-api.dependencies")

# Global session pool
session_pool: Optional[aiohttp.ClientSession] = None

# Get Sora client
def get_sora_client(auth_token: str):
    from ..sora_integration import SoraClient
    
    # Cache client instances in a dict
    if not hasattr(get_sora_client, "clients"):
        get_sora_client.clients = {}
        
    if auth_token not in get_sora_client.clients:
        proxy_host = Config.PROXY_HOST if Config.PROXY_HOST and Config.PROXY_HOST.strip() else None
        proxy_port = Config.PROXY_PORT if Config.PROXY_PORT and Config.PROXY_PORT.strip() else None
        proxy_user = Config.PROXY_USER if Config.PROXY_USER and Config.PROXY_USER.strip() else None
        proxy_pass = Config.PROXY_PASS if Config.PROXY_PASS and Config.PROXY_PASS.strip() else None
        
        get_sora_client.clients[auth_token] = SoraClient(
            proxy_host=proxy_host, 
            proxy_port=proxy_port,
            proxy_user=proxy_user,
            proxy_pass=proxy_pass,
            auth_token=auth_token
        )
    
    return get_sora_client.clients[auth_token]

# Extract and validate auth token from request header
async def get_token_from_header(authorization: Optional[str] = Header(None)) -> str:
    """Get auth token from the Authorization header"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")
    
    return authorization.replace("Bearer ", "")

# Verify API key
async def verify_api_key(request: Request):
    """Validate API key from the Authorization header"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid API key")
    
    api_key = auth_header.replace("Bearer ", "")
    
    # Validate API auth token
    if Config.API_AUTH_TOKEN:
        # If API_AUTH_TOKEN env var is set, validate against it
        if api_key != Config.API_AUTH_TOKEN:
            logger.warning("API authentication failed: provided token does not match")
            raise HTTPException(status_code=401, detail="API authentication failed: invalid token")
    else:
        # If API_AUTH_TOKEN not set, validate against enabled admin panel keys
        from ..key_manager import key_manager
        valid_keys = [k.get("key") for k in key_manager.get_all_keys() if k.get("is_enabled", False)]
        if api_key not in valid_keys and api_key != Config.ADMIN_KEY:
            logger.warning("API authentication failed: key not in the valid list")
            raise HTTPException(status_code=401, detail="API authentication failed: invalid key")
    
    return api_key

# Dependency to get Sora client
def get_sora_client_dep(specific_key=None):
    """Return a dependency function to obtain a Sora client.
    
    Args:
        specific_key: If provided, use this specific API key instead of selecting automatically.
    """
    async def _get_client(auth_token: str = Depends(verify_api_key)):
        from ..key_manager import key_manager
        
        # Use the specific key if provided
        if specific_key:
            sora_auth_token = specific_key
        else:
            # Use key manager to obtain an available API key
            sora_auth_token = key_manager.get_key()
            if not sora_auth_token:
                raise HTTPException(status_code=429, detail="All API keys have reached the rate limit")
            
        # Get Sora client
        return get_sora_client(sora_auth_token), sora_auth_token
    
    return _get_client

# Verify JWT token and admin privileges
async def verify_admin_jwt(token: str = Depends(get_token_from_header)) -> Dict[str, Any]:
    """Validate JWT token and confirm admin privileges"""
    # Verify JWT token
    payload = verify_jwt_token(token)
    
    # Check admin role
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    return payload

# Verify admin privileges (legacy method for backward compatibility)
async def verify_admin(request: Request):
    """Verify admin privileges"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    token = auth_header.replace("Bearer ", "")
    
    # Try JWT verification first
    try:
        payload = verify_jwt_token(token)
        if payload.get("role") == "admin":
            return token
    except HTTPException:
        # If JWT verification fails, fall back to legacy validation
        pass
    
    # Legacy validation (directly compare with admin key)
    if token != Config.ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Admin privileges required")
    
    return token