import os
import json
import uuid
from typing import List, Dict
import logging

logger = logging.getLogger("sora-api.config")

class Config:
    # API服务配置
    HOST = os.getenv("API_HOST", "0.0.0.0")
    PORT = int(os.getenv("API_PORT", "8890"))
    
    # 基础URL配置
    BASE_URL = os.getenv("BASE_URL", f"http://0.0.0.0:{PORT}")
    
    # 静态文件路径前缀，用于处理应用部署在子路径的情况
    # 例如: /sora-api 表示应用部署在 /sora-api 下
    STATIC_PATH_PREFIX = os.getenv("STATIC_PATH_PREFIX", "")
    
    # 代理配置
    PROXY_HOST = os.getenv("PROXY_HOST", "")
    PROXY_PORT = os.getenv("PROXY_PORT", "")
    PROXY_USER = os.getenv("PROXY_USER", "")
    PROXY_PASS = os.getenv("PROXY_PASS", "")
    
    # 目录配置
    ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    BASE_DIR = ROOT_DIR
    STATIC_DIR = os.getenv("STATIC_DIR", os.path.join(BASE_DIR, "src/static"))
    
    # 图片保存目录 - 用户只需设置这一项
    IMAGE_SAVE_DIR = os.getenv("IMAGE_SAVE_DIR", os.path.join(STATIC_DIR, "images"))
    
    # 图片本地化配置
    IMAGE_LOCALIZATION = os.getenv("IMAGE_LOCALIZATION", "False").lower() in ("true", "1", "yes")
    
    # API Keys配置
    API_KEYS = []
    
    # 管理员配置
    ADMIN_KEY = os.getenv("ADMIN_KEY", "sk-123456")
    KEYS_STORAGE_FILE = os.getenv("KEYS_STORAGE_FILE", "api_keys.json")
    
    # API认证令牌
    API_AUTH_TOKEN = os.getenv("API_AUTH_TOKEN", "")
    
    # 日志配置
    VERBOSE_LOGGING = os.getenv("VERBOSE_LOGGING", "False").lower() in ("true", "1", "yes")
    
    @classmethod
    def print_config(cls):
        """打印当前配置信息"""
        print("\n==== Sora API 配置信息 ====")
        print(f"基础目录: {cls.BASE_DIR}")
        print(f"API服务地址: {cls.HOST}:{cls.PORT}")
        print(f"基础URL: {cls.BASE_URL}")
        
        # API认证信息
        if cls.API_AUTH_TOKEN:
            print(f"API认证令牌: 已设置 (长度: {len(cls.API_AUTH_TOKEN)})")
        else:
            print(f"API认证令牌: 未设置 (将使用管理面板的key)")
        
        # 详细日志
        if cls.VERBOSE_LOGGING:
            print(f"静态文件目录: {cls.STATIC_DIR}")
            print(f"图片保存目录: {cls.IMAGE_SAVE_DIR}")
            print(f"图片本地化: {'启用' if cls.IMAGE_LOCALIZATION else '禁用'}")
            
            # 代理配置信息
            if cls.PROXY_HOST:
                proxy_info = f"{cls.PROXY_HOST}:{cls.PROXY_PORT}"
                if cls.PROXY_USER:
                    proxy_info = f"{cls.PROXY_USER}:****@{proxy_info}"
                print(f"代理配置: {proxy_info}")
            else:
                print(f"代理配置: (未配置)")
        
        # 确保必要目录存在
        cls._ensure_directories()
        
    @classmethod
    def _ensure_directories(cls):
        """确保必要的目录存在"""
        # 检查静态文件目录
        if not os.path.exists(cls.STATIC_DIR):
            print(f"⚠️ 警告: 静态文件目录不存在: {cls.STATIC_DIR}")
        elif cls.VERBOSE_LOGGING:
            print(f"✅ 静态文件目录存在")
            
        # 检查并创建图片保存目录
        if not os.path.exists(cls.IMAGE_SAVE_DIR):
            try:
                os.makedirs(cls.IMAGE_SAVE_DIR, exist_ok=True)
                if cls.VERBOSE_LOGGING:
                    print(f"✅ 已创建图片保存目录: {cls.IMAGE_SAVE_DIR}")
            except Exception as e:
                print(f"❌ 创建图片保存目录失败: {str(e)}")
        elif cls.VERBOSE_LOGGING:
            print(f"✅ 图片保存目录存在")
            
            # 测试写入权限
            try:
                test_file = os.path.join(cls.IMAGE_SAVE_DIR, '.test_write')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                print(f"✅ 图片保存目录有写入权限")
            except Exception as e:
                print(f"❌ 图片保存目录没有写入权限: {str(e)}")
    
    @classmethod
    def load_api_keys(cls):
        """加载API密钥"""
        # 先从环境变量加载
        api_keys_str = os.getenv("API_KEYS", "")
        if api_keys_str:
            try:
                cls.API_KEYS = json.loads(api_keys_str)
                if cls.VERBOSE_LOGGING:
                    logger.info(f"已从环境变量加载 {len(cls.API_KEYS)} 个API keys")
                return
            except json.JSONDecodeError as e:
                logger.error(f"解析环境变量API keys失败: {e}")
                
        # 再从文件加载
        try:
            if os.path.exists(cls.KEYS_STORAGE_FILE):
                with open(cls.KEYS_STORAGE_FILE, "r", encoding="utf-8") as f:
                    keys_data = json.load(f)
                    if isinstance(keys_data, dict) and "keys" in keys_data:
                        cls.API_KEYS = [k for k in keys_data["keys"] if k.get("key")]
                    else:
                        cls.API_KEYS = keys_data
                    
                    if cls.VERBOSE_LOGGING:
                        logger.info(f"已从文件加载 {len(cls.API_KEYS)} 个API keys")
        except Exception as e:
            logger.error(f"从文件加载API keys失败: {e}") 
    
    @classmethod
    def save_api_keys(cls, keys_data):
        """保存API密钥到文件"""
        try:
            keys_storage_file = os.path.join(cls.BASE_DIR, cls.KEYS_STORAGE_FILE)
            
            with open(keys_storage_file, "w", encoding="utf-8") as f:
                if isinstance(keys_data, list):
                    json.dump({"keys": keys_data}, f, ensure_ascii=False, indent=2)
                else:
                    json.dump(keys_data, f, ensure_ascii=False, indent=2)
            
            # 更新内存中的keys
            if isinstance(keys_data, dict) and "keys" in keys_data:
                cls.API_KEYS = [k for k in keys_data["keys"] if k.get("key")]
            else:
                cls.API_KEYS = keys_data
                
            if cls.VERBOSE_LOGGING:
                logger.info(f"API keys已保存至 {keys_storage_file}")
        except Exception as e:
            logger.error(f"保存API keys失败: {e}")
    
    @classmethod
    def save_admin_key(cls):
        """保存管理员密钥到文件"""
        try:
            admin_config_file = os.path.join(cls.BASE_DIR, "admin_config.json")
            with open(admin_config_file, "w", encoding="utf-8") as f:
                json.dump({"admin_key": cls.ADMIN_KEY}, f, indent=2)
            
            if cls.VERBOSE_LOGGING:
                logger.info(f"管理员密钥已保存至 {admin_config_file}")
        except Exception as e:
            logger.error(f"保存管理员密钥失败: {e}") 