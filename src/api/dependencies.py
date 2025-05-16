from typing import Optional, Tuple, Dict, Any
from fastapi import Request, HTTPException, Depends, Header
import aiohttp
import logging
from ..config import Config
from .auth import verify_jwt_token

logger = logging.getLogger("sora-api.dependencies")

# 全局会话池
session_pool: Optional[aiohttp.ClientSession] = None

# 获取Sora客户端
def get_sora_client(auth_token: str):
    from ..sora_integration import SoraClient
    
    # 使用字典缓存客户端实例
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

# 从请求头中获取并验证认证令牌
async def get_token_from_header(authorization: Optional[str] = Header(None)) -> str:
    """从请求头中获取认证令牌"""
    if not authorization:
        raise HTTPException(status_code=401, detail="缺少认证头")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="无效的认证头格式")
    
    return authorization.replace("Bearer ", "")

# 验证API key
async def verify_api_key(request: Request):
    """检查请求头中的API密钥"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少或无效的API key")
    
    api_key = auth_header.replace("Bearer ", "")
    
    # 验证API认证令牌
    if Config.API_AUTH_TOKEN:
        # 如果设置了API_AUTH_TOKEN环境变量，则进行验证
        if api_key != Config.API_AUTH_TOKEN:
            logger.warning(f"API认证失败: 提供的令牌不匹配")
            raise HTTPException(status_code=401, detail="API认证失败，令牌无效")
    else:
        # 如果未设置API_AUTH_TOKEN，则验证是否为管理面板的key
        from ..key_manager import key_manager
        valid_keys = [k.get("key") for k in key_manager.get_all_keys() if k.get("is_enabled", False)]
        if api_key not in valid_keys and api_key != Config.ADMIN_KEY:
            logger.warning(f"API认证失败: 提供的key不在有效列表中")
            raise HTTPException(status_code=401, detail="API认证失败，key无效")
    
    return api_key

# 获取Sora客户端依赖
def get_sora_client_dep(specific_key=None):
    """返回一个依赖函数，用于获取Sora客户端
    
    Args:
        specific_key: 指定使用的API密钥，如果不为None，则优先使用此密钥
    """
    async def _get_client(auth_token: str = Depends(verify_api_key)):
        from ..key_manager import key_manager
        
        # 如果提供了特定密钥，则使用该密钥
        if specific_key:
            sora_auth_token = specific_key
        else:
            # 使用密钥管理器获取可用的API密钥
            sora_auth_token = key_manager.get_key()
            if not sora_auth_token:
                raise HTTPException(status_code=429, detail="所有API key都已达到速率限制")
            
        # 获取Sora客户端
        return get_sora_client(sora_auth_token), sora_auth_token
    
    return _get_client

# 验证JWT令牌并验证管理员权限
async def verify_admin_jwt(token: str = Depends(get_token_from_header)) -> Dict[str, Any]:
    """验证JWT令牌并确认管理员权限"""
    # 验证JWT令牌
    payload = verify_jwt_token(token)
    
    # 验证是否为管理员角色
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="没有管理员权限")
    
    return payload

# 验证管理员权限（传统方法，保留向后兼容性）
async def verify_admin(request: Request):
    """验证管理员权限"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未授权")
    
    token = auth_header.replace("Bearer ", "")
    
    # 尝试JWT验证
    try:
        payload = verify_jwt_token(token)
        if payload.get("role") == "admin":
            return token
    except HTTPException:
        # JWT验证失败，尝试传统验证
        pass
    
    # 传统验证（直接验证管理员密钥）
    if token != Config.ADMIN_KEY:
        raise HTTPException(status_code=403, detail="没有管理员权限")
    
    return token 