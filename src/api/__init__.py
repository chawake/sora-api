import logging
from fastapi import APIRouter
from .admin import router as admin_router
from .generation import router as generation_router
from .chat import router as chat_router
from .health import router as health_router
# Add auth routes
from .auth import router as auth_router

# Configure logging
logger = logging.getLogger("sora-api.api")

# Create v1 router (OpenAI API compatible)
v1_router = APIRouter(prefix="/v1")

# Create main router
main_router = APIRouter()

# Register feature routes under v1
v1_router.include_router(generation_router)
v1_router.include_router(chat_router)

# Register all routers
main_router.include_router(v1_router) # Keep v1 prefix for OpenAI API compatibility
main_router.include_router(admin_router, tags=["admin"])
main_router.include_router(health_router, tags=["health"])
main_router.include_router(auth_router, tags=["auth"])

logger.info("API routes initialized")
