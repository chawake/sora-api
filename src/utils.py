import os
import uuid
import aiohttp
import aiofiles
import logging
import ssl
from urllib.parse import urlparse
from .config import Config

# 初始化日志
logger = logging.getLogger("sora-api.utils")

# 图片本地化调试开关
IMAGE_DEBUG = os.getenv("IMAGE_DEBUG", "").lower() in ("true", "1", "yes")

# 修复Python 3.11之前版本中HTTPS代理处理HTTPS请求的问题
# 参考: https://docs.aiohttp.org/en/stable/client_advanced.html#proxy-support
try:
    import aiohttp.connector
    orig_create_connection = aiohttp.connector.TCPConnector._create_connection

    async def patched_create_connection(self, req, traces, timeout):
        if req.ssl and req.proxy and req.proxy.scheme == 'https':
            # 为代理连接创建SSL上下文
            proxy_ssl = ssl.create_default_context()
            req.proxy_ssl = proxy_ssl
            
            if IMAGE_DEBUG:
                logger.debug("已应用HTTPS代理补丁")
        
        return await orig_create_connection(self, req, traces, timeout)
    
    # 应用猴子补丁
    aiohttp.connector.TCPConnector._create_connection = patched_create_connection
    
    if IMAGE_DEBUG:
        logger.debug("已启用aiohttp HTTPS代理支持补丁")
except Exception as e:
    logger.warning(f"应用HTTPS代理补丁失败: {e}")

async def download_and_save_image(image_url: str) -> str:
    """
    下载图片并保存到本地
    
    Args:
        image_url: 图片URL
        
    Returns:
        本地化后的图片URL
    """
    # 如果未启用本地化或URL已经是本地路径，直接返回
    if not Config.IMAGE_LOCALIZATION:
        if IMAGE_DEBUG:
            logger.debug(f"图片本地化未启用，返回原始URL: {image_url}")
        return image_url
    
    # 检查是否已经是本地URL
    # 准备URL检测所需的信息
    parsed_base_url = urlparse(Config.BASE_URL)
    base_path = parsed_base_url.path.rstrip('/')
    
    # 直接检查常见的图片URL模式
    local_url_patterns = [
        "/images/",
        "/static/images/",
        f"{base_path}/images/",
        f"{base_path}/static/images/"
    ]
    
    # 检查是否有自定义前缀
    if Config.STATIC_PATH_PREFIX:
        prefix = Config.STATIC_PATH_PREFIX
        if not prefix.startswith('/'):
            prefix = f"/{prefix}"
        local_url_patterns.append(f"{prefix}/images/")
        local_url_patterns.append(f"{base_path}{prefix}/images/")
    
    # 检查是否符合任何本地URL模式
    is_local_url = any(pattern in image_url for pattern in local_url_patterns)
    
    if is_local_url:
        if IMAGE_DEBUG:
            logger.debug(f"URL已是本地图片路径: {image_url}")
        
        # 如果是相对路径，补充完整的URL
        if image_url.startswith("/"):
            return f"{parsed_base_url.scheme}://{parsed_base_url.netloc}{image_url}"
        return image_url
    
    try:
        # 生成文件名和保存路径
        parsed_url = urlparse(image_url)
        file_extension = os.path.splitext(parsed_url.path)[1] or ".png"
        filename = f"{uuid.uuid4()}{file_extension}"
        save_path = os.path.join(Config.IMAGE_SAVE_DIR, filename)
        
        # 确保保存目录存在
        os.makedirs(Config.IMAGE_SAVE_DIR, exist_ok=True)
        
        if IMAGE_DEBUG:
            logger.debug(f"下载图片: {image_url} -> {save_path}")
        
        # 配置代理
        proxy = None
        if Config.PROXY_HOST and Config.PROXY_PORT:
            proxy_auth = None
            if Config.PROXY_USER and Config.PROXY_PASS:
                proxy_auth = aiohttp.BasicAuth(Config.PROXY_USER, Config.PROXY_PASS)
            
            proxy_url = f"http://{Config.PROXY_HOST}:{Config.PROXY_PORT}"
            if IMAGE_DEBUG:
                auth_info = f" (使用认证)" if proxy_auth else ""
                logger.debug(f"使用代理: {proxy_url}{auth_info}")
            proxy = proxy_url
        
        # 下载图片
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # 创建请求参数
            request_kwargs = {"timeout": 30}
            if proxy:
                request_kwargs["proxy"] = proxy
                if Config.PROXY_USER and Config.PROXY_PASS:
                    request_kwargs["proxy_auth"] = aiohttp.BasicAuth(Config.PROXY_USER, Config.PROXY_PASS)
            
            async with session.get(image_url, **request_kwargs) as response:
                if response.status != 200:
                    logger.warning(f"下载失败，状态码: {response.status}, URL: {image_url}")
                    return image_url
                
                content = await response.read()
                if not content:
                    logger.warning("下载内容为空")
                    return image_url
                
                # 保存图片
                async with aiofiles.open(save_path, "wb") as f:
                    await f.write(content)
        
        # 检查文件是否成功保存
        if not os.path.exists(save_path) or os.path.getsize(save_path) == 0:
            logger.warning(f"图片保存失败: {save_path}")
            if os.path.exists(save_path):
                os.remove(save_path)
            return image_url
        
        # 返回本地URL
        # 获取文件名
        filename = os.path.basename(save_path)
        
        # 解析基础URL
        parsed_base_url = urlparse(Config.BASE_URL)
        base_path = parsed_base_url.path.rstrip('/')
        
        # 使用固定的图片URL格式
        relative_url = f"/images/{filename}"
        
        # 如果设置了STATIC_PATH_PREFIX，优先使用该前缀
        if Config.STATIC_PATH_PREFIX:
            prefix = Config.STATIC_PATH_PREFIX
            if not prefix.startswith('/'):
                prefix = f"/{prefix}"
            relative_url = f"{prefix}/images/{filename}"
        
        # 如果BASE_URL有子路径，添加到相对路径前
        if base_path:
            relative_url = f"{base_path}{relative_url}"
        
        # 处理重复斜杠
        while "//" in relative_url:
            relative_url = relative_url.replace("//", "/")
        
        # 生成完整URL
        full_url = f"{parsed_base_url.scheme}://{parsed_base_url.netloc}{relative_url}"
        
        if IMAGE_DEBUG:
            logger.debug(f"图片保存成功: {full_url}")
            logger.debug(f"图片保存路径: {save_path}")
        
        return full_url
    except Exception as e:
        logger.error(f"图片下载失败: {str(e)}", exc_info=IMAGE_DEBUG)
        return image_url

async def localize_image_urls(image_urls: list) -> list:
    """
    批量将图片URL本地化
    
    Args:
        image_urls: 图片URL列表
        
    Returns:
        本地化后的URL列表
    """
    if not Config.IMAGE_LOCALIZATION or not image_urls:
        return image_urls
    
    if IMAGE_DEBUG:
        logger.debug(f"本地化 {len(image_urls)} 个URL: {image_urls}")
    else:
        logger.info(f"本地化 {len(image_urls)} 个图片")
    
    localized_urls = []
    for url in image_urls:
        localized_url = await download_and_save_image(url)
        localized_urls.append(localized_url)
    
    return localized_urls 