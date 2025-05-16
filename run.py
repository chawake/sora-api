#!/usr/bin/env python
import sys
import os
import logging

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("sora-api")

# 设置控制台输出编码为UTF-8
if sys.platform.startswith('win'):
    os.system("chcp 65001")
    sys.stdout.reconfigure(encoding='utf-8')
elif sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# 确保src目录在路径中
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 提前加载app和key_manager，确保API密钥在启动前已加载
from src.app import app, key_manager
from src.main import init_app
from src.config import Config
import uvicorn

if __name__ == "__main__":
    # 设置环境变量确保正确处理UTF-8
    os.environ["PYTHONIOENCODING"] = "utf-8"
    
    # 初始化应用
    init_app()
    
    # 启动服务
    logger.info(f"启动OpenAI兼容的Sora API服务: {Config.HOST}:{Config.PORT}")
    logger.info(f"已加载 {len(key_manager.keys)} 个API密钥")
    uvicorn.run(
        "src.app:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=False  # 生产环境关闭自动重载
    ) 