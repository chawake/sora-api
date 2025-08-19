import jwt
import time
import uuid
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..config import Config

# Configure logging
logger = logging.getLogger("sora-api.auth")

# Create router
router = APIRouter(prefix="/api/auth")

# JWT configuration
JWT_SECRET = Config.ADMIN_KEY  # Use admin key as JWT secret
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 3600  # Token valid for 1 hour

# Authentication request model
class LoginRequest(BaseModel):
    admin_key: str

# Token response model
class TokenResponse(BaseModel):
    token: str
    expires_in: int
    token_type: str = "bearer"

# Create JWT token
def create_jwt_token(data: Dict[str, Any], expires_delta: int = JWT_EXPIRATION) -> str:
    payload = data.copy()
    issued_at = int(time.time())
    expiration = issued_at + expires_delta
    payload.update({
        "iat": issued_at,
        "exp": expiration,
        "jti": str(uuid.uuid4())
    })
    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

# Verify JWT token
def verify_jwt_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        # Check if token has expired
        if payload.get("exp", 0) < time.time():
            raise HTTPException(status_code=401, detail="Token has expired")
        return payload
    except jwt.PyJWTError as e:
        logger.warning(f"JWT verification failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")

# Login API
@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Admin login, returns a JWT token"""
    # Validate admin key
    if request.admin_key != Config.ADMIN_KEY:
        logger.warning("Attempt to log in with an invalid admin key")
        # Fixed delay to mitigate timing attacks
        time.sleep(1)
        raise HTTPException(status_code=401, detail="Invalid admin key")
    
    # Create token
    token_data = {
        "sub": "admin",
        "role": "admin",
        "name": "Administrator"
    }
    
    token = create_jwt_token(token_data)
    logger.info("Admin login successful, issued new token")
    
    return TokenResponse(token=token, expires_in=JWT_EXPIRATION)

# Refresh token API
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(token: str = Depends(verify_jwt_token)):
    """Refresh JWT token"""
    # Create a new token keeping the same sub and role
    token_data = {
        "sub": token.get("sub"),
        "role": token.get("role", "admin"),
        "name": token.get("name", "Administrator"),
        "refresh_count": token.get("refresh_count", 0) + 1
    }
    
    new_token = create_jwt_token(token_data)
    logger.info("Token refresh successful, issued new token")
    
    return TokenResponse(token=new_token, expires_in=JWT_EXPIRATION)