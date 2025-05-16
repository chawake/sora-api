import uvicorn
import logging
from .app import app, key_manager
from .config import Config

# 获取日志记录器
logger = logging.getLogger("sora-api.main")

def init_app():
    """初始化应用程序"""
    try:
        # 密钥管理器已在app.py中初始化并加载完成
        # 检查是否有可用的密钥
        if not key_manager.keys:
            logger.warning("未配置API key，将使用测试密钥")
            key_manager.add_key(
                key_value="Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjE5MzQ0ZTY1LWJiYzktNDRkMS1hOWQwLWY5NTdiMDc5YmQwZSIsInR5cCI6IkpXVCJ9...",
                name="默认测试密钥"
            )
        
        logger.info(f"API服务初始化完成，已加载 {len(key_manager.keys)} 个API key")
    except Exception as e:
        logger.error(f"API服务初始化失败: {str(e)}")
        raise

def start():
    """启动API服务"""
    # 初始化应用
    init_app()
    
    # 打印配置信息
    Config.print_config()
    
    # 启动服务
    logger.info(f"启动服务: {Config.HOST}:{Config.PORT}")
    uvicorn.run(
        "src.app:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.VERBOSE_LOGGING  # 仅在调试模式下开启自动重载
    )

if __name__ == "__main__":
    start()