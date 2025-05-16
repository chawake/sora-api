import jwt
import time
import uuid
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..config import Config

# 设置日志
logger = logging.getLogger("sora-api.auth")

# 创建路由
router = APIRouter(prefix="/api/auth")

# JWT配置
JWT_SECRET = Config.ADMIN_KEY  # 使用管理员密钥作为JWT秘钥
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = 3600  # 令牌有效期1小时

# 认证请求模型
class LoginRequest(BaseModel):
    admin_key: str

# 令牌响应模型
class TokenResponse(BaseModel):
    token: str
    expires_in: int
    token_type: str = "bearer"

# 创建JWT令牌
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

# 验证JWT令牌
def verify_jwt_token(token: str) -> Dict[str, Any]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        # 检查token是否已过期
        if payload.get("exp", 0) < time.time():
            raise HTTPException(status_code=401, detail="令牌已过期")
        return payload
    except jwt.PyJWTError as e:
        logger.warning(f"JWT验证失败: {str(e)}")
        raise HTTPException(status_code=401, detail="无效的令牌")

# 登录API
@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """管理员登录，返回JWT令牌"""
    # 验证管理员密钥
    if request.admin_key != Config.ADMIN_KEY:
        logger.warning(f"尝试使用无效的管理员密钥登录")
        # 使用固定延迟以防止计时攻击
        time.sleep(1)
        raise HTTPException(status_code=401, detail="管理员密钥错误")
    
    # 创建令牌
    token_data = {
        "sub": "admin",
        "role": "admin",
        "name": "管理员"
    }
    
    token = create_jwt_token(token_data)
    logger.info(f"管理员登录成功，生成新令牌")
    
    return TokenResponse(token=token, expires_in=JWT_EXPIRATION)

# 刷新令牌API
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(token: str = Depends(verify_jwt_token)):
    """刷新JWT令牌"""
    # 创建新令牌，保持相同的sub和role
    token_data = {
        "sub": token.get("sub"),
        "role": token.get("role", "admin"),
        "name": token.get("name", "管理员"),
        "refresh_count": token.get("refresh_count", 0) + 1
    }
    
    new_token = create_jwt_token(token_data)
    logger.info(f"令牌刷新成功，生成新令牌")
    
    return TokenResponse(token=new_token, expires_in=JWT_EXPIRATION) 