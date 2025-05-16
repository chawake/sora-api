import logging
from fastapi import APIRouter
from .admin import router as admin_router
from .generation import router as generation_router
from .chat import router as chat_router
from .health import router as health_router
# 添加auth路由
from .auth import router as auth_router

# 设置日志
logger = logging.getLogger("sora-api.api")

# 创建v1版本路由（兼容OpenAI API）
v1_router = APIRouter(prefix="/v1")

# 创建主路由
main_router = APIRouter()

# 向v1路由注册相关功能路由
v1_router.include_router(generation_router)
v1_router.include_router(chat_router)

# 注册所有路由
main_router.include_router(v1_router) # 保持与OpenAI API兼容的v1前缀路由
main_router.include_router(admin_router, tags=["admin"])
main_router.include_router(health_router, tags=["health"])
main_router.include_router(auth_router, tags=["auth"])

logger.info("API路由已初始化")
