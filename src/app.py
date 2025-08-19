import os
import aiohttp
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError

from .config import Config
from .key_manager import key_manager
from .api import main_router
from .api.dependencies import session_pool 

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("sora-api")

# Create FastAPI application
app = FastAPI(
    title="OpenAI Compatible Sora API",
    description="API service providing OpenAI-compatible interface for Sora",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS middleware
origins = [
    "http://localhost",
    "http://localhost:8890",
    f"http://{Config.HOST}:{Config.PORT}",
    Config.BASE_URL,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Exception handling
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    return JSONResponse(
        status_code=422,
        content={"detail": f"Request validation error: {str(exc)}"}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    # Log the error
    logger.error(f"Global exception: {str(exc)}", exc_info=True)
    
    # If it's a known HTTPException, keep the original status code and details
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    
    # Return 500 for other exceptions
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

# Application startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Operations to perform when the application starts"""
    global session_pool
    # Create shared session pool
    session_pool = aiohttp.ClientSession()
    logger.info("Application started, created global session pool")
    
    # Save admin key on initialization
    Config.save_admin_key()
    
    # Ensure static file directories exist
    os.makedirs(os.path.join(Config.STATIC_DIR, "admin"), exist_ok=True)
    os.makedirs(os.path.join(Config.STATIC_DIR, "admin/js"), exist_ok=True)
    os.makedirs(os.path.join(Config.STATIC_DIR, "admin/css"), exist_ok=True)
    os.makedirs(Config.IMAGE_SAVE_DIR, exist_ok=True)
    
    # Output image save directory information
    logger.info(f"Image save directory: {Config.IMAGE_SAVE_DIR}")
    
    # Image access URL
    base_url = Config.BASE_URL.rstrip('/')
    if Config.STATIC_PATH_PREFIX:
        logger.info(f"Images will be accessible at {base_url}{Config.STATIC_PATH_PREFIX}/images/<filename>")
    else:
        logger.info(f"Images will be accessible at {base_url}/images/<filename>")
    
    # Print configuration information
    Config.print_config()

@app.on_event("shutdown")
async def shutdown_event():
    """Operations to perform when the application shuts down"""
    # Close the session pool
    if session_pool:
        await session_pool.close()
    logger.info("Application shut down, cleaned up global session pool")

# Add root path route
@app.get("/")
async def root():
    """Root path, returns system status information"""
    return {
        "status": "OK",
        "message": "System is running normally",
        "version": app.version,
        "name": app.title
    }

# Mount static file directory
app.mount("/static", StaticFiles(directory=Config.STATIC_DIR), name="static")

# General image access route - supports multiple path formats
@app.get("/images/{filename}")
@app.get("/static/images/{filename}")
async def get_image(filename: str):
    """Handle image requests - no matter where they're stored"""
    # Get image directly from IMAGE_SAVE_DIR
    file_path = os.path.join(Config.IMAGE_SAVE_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        logger.warning(f"Requested image does not exist: {file_path}")
        raise HTTPException(status_code=404, detail="Image not found")

# Add compatible route for static file path prefix
if Config.STATIC_PATH_PREFIX:
    prefix_path = Config.STATIC_PATH_PREFIX.lstrip("/")
    
    @app.get(f"/{prefix_path}/images/{{filename}}")
    async def get_prefixed_image(filename: str):
        """Handle prefixed image requests"""
        return await get_image(filename)

# Admin panel route
@app.get("/admin")
async def admin_panel():
    """Return the admin panel HTML page"""
    return FileResponse(os.path.join(Config.STATIC_DIR, "admin/index.html"))

# Now using JWT authentication, no need to expose admin key directly

# Register all API routes
app.include_router(main_router)

# Application entry point (for uvicorn direct call)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.VERBOSE_LOGGING
    ) 