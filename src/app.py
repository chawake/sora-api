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

# 配置日志
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

logger = logging.getLogger("sora-api")

# 创建FastAPI应用
app = FastAPI(
    title="OpenAI Compatible Sora API",
    description="为Sora提供OpenAI兼容接口的API服务",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置CORS中间件
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

# 异常处理
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证错误"""
    return JSONResponse(
        status_code=422,
        content={"detail": f"请求验证错误: {str(exc)}"}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    # 记录错误
    logger.error(f"全局异常: {str(exc)}", exc_info=True)
    
    # 如果是已知的HTTPException，保持原始状态码和详情
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    
    # 其他异常返回500状态码
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {str(exc)}"}
    )

# 应用启动和关闭事件
@app.on_event("startup")
async def startup_event():
    """应用启动时执行的操作"""
    global session_pool
    # 创建共享会话池
    session_pool = aiohttp.ClientSession()
    logger.info("应用已启动，创建了全局会话池")
    
    # 初始化时保存管理员密钥
    Config.save_admin_key()
    
    # 确保静态文件目录存在
    os.makedirs(os.path.join(Config.STATIC_DIR, "admin"), exist_ok=True)
    os.makedirs(os.path.join(Config.STATIC_DIR, "admin/js"), exist_ok=True)
    os.makedirs(os.path.join(Config.STATIC_DIR, "admin/css"), exist_ok=True)
    os.makedirs(Config.IMAGE_SAVE_DIR, exist_ok=True)
    
    # 输出图片保存目录的信息 
    logger.info(f"图片保存目录: {Config.IMAGE_SAVE_DIR}")
    
    # 图片访问URL
    base_url = Config.BASE_URL.rstrip('/')
    if Config.STATIC_PATH_PREFIX:
        logger.info(f"图片将通过 {base_url}{Config.STATIC_PATH_PREFIX}/images/<filename> 访问")
    else:
        logger.info(f"图片将通过 {base_url}/images/<filename> 访问")
    
    # 打印配置信息
    Config.print_config()

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行的操作"""
    # 关闭会话池
    if session_pool:
        await session_pool.close()
    logger.info("应用已关闭，清理了全局会话池")

# 添加根路径路由
@app.get("/")
async def root():
    """根路径，返回系统状态信息"""
    return {
        "status": "OK",
        "message": "系统运行正常",
        "version": app.version,
        "name": app.title
    }

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory=Config.STATIC_DIR), name="static")

# 通用图片访问路由 - 支持多种路径格式
@app.get("/images/{filename}")
@app.get("/static/images/{filename}")
async def get_image(filename: str):
    """处理图片请求 - 无论保存在哪里"""
    # 直接从IMAGE_SAVE_DIR获取图片
    file_path = os.path.join(Config.IMAGE_SAVE_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    else:
        logger.warning(f"请求的图片不存在: {file_path}")
        raise HTTPException(status_code=404, detail="图片不存在")

# 添加静态文件路径前缀的兼容路由
if Config.STATIC_PATH_PREFIX:
    prefix_path = Config.STATIC_PATH_PREFIX.lstrip("/")
    
    @app.get(f"/{prefix_path}/images/{{filename}}")
    async def get_prefixed_image(filename: str):
        """处理带前缀的图片请求"""
        return await get_image(filename)

# 管理界面路由
@app.get("/admin")
async def admin_panel():
    """返回管理面板HTML页面"""
    return FileResponse(os.path.join(Config.STATIC_DIR, "admin/index.html"))

# 现在使用JWT认证，不再需要直接暴露管理员密钥

# 注册所有API路由
app.include_router(main_router)

# 应用入口点（供uvicorn直接调用）
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.VERBOSE_LOGGING
    ) 