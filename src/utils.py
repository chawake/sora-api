import os
import uuid
import aiohttp
import aiofiles
import logging
import ssl
from urllib.parse import urlparse
from .config import Config

# Initialize logging
logger = logging.getLogger("sora-api.utils")

# Image localization debug flag
IMAGE_DEBUG = os.getenv("IMAGE_DEBUG", "").lower() in ("true", "1", "yes")

# Fix HTTPS proxy handling for HTTPS requests in Python versions before 3.11
# Reference: https://docs.aiohttp.org/en/stable/client_advanced.html#proxy-support
try:
    import aiohttp.connector
    orig_create_connection = aiohttp.connector.TCPConnector._create_connection

    async def patched_create_connection(self, req, traces, timeout):
        if req.ssl and req.proxy and req.proxy.scheme == 'https':
            # Create SSL context for proxy connection
            proxy_ssl = ssl.create_default_context()
            req.proxy_ssl = proxy_ssl
            
            if IMAGE_DEBUG:
                logger.debug("Applied HTTPS proxy patch")
        
        return await orig_create_connection(self, req, traces, timeout)
    
    # Apply monkey patch
    aiohttp.connector.TCPConnector._create_connection = patched_create_connection
    
    if IMAGE_DEBUG:
        logger.debug("Enabled aiohttp HTTPS proxy support patch")
except Exception as e:
    logger.warning(f"Failed to apply HTTPS proxy patch: {e}")

async def download_and_save_image(image_url: str) -> str:
    """
    Download image and save to local storage
    
    Args:
        image_url: Image URL
        
    Returns:
        Localized image URL
    """
    # If localization is disabled or URL is already a local path, return as is
    if not Config.IMAGE_LOCALIZATION:
        if IMAGE_DEBUG:
            logger.debug(f"Image localization not enabled, returning original URL: {image_url}")
        return image_url
    
    # Check if URL is already local
    # Prepare information needed for URL detection
    parsed_base_url = urlparse(Config.BASE_URL)
    base_path = parsed_base_url.path.rstrip('/')
    
    # Directly check common image URL patterns
    local_url_patterns = [
        "/images/",
        "/static/images/",
        f"{base_path}/images/",
        f"{base_path}/static/images/"
    ]
    
    # Check for custom prefix
    if Config.STATIC_PATH_PREFIX:
        prefix = Config.STATIC_PATH_PREFIX
        if not prefix.startswith('/'):
            prefix = f"/{prefix}"
        local_url_patterns.append(f"{prefix}/images/")
        local_url_patterns.append(f"{base_path}{prefix}/images/")
    
    # Check if URL matches any local URL pattern
    is_local_url = any(pattern in image_url for pattern in local_url_patterns)
    
    if is_local_url:
        if IMAGE_DEBUG:
            logger.debug(f"URL is already a local image path: {image_url}")
        
        # If it's a relative path, make it a full URL
        if image_url.startswith("/"):
            return f"{parsed_base_url.scheme}://{parsed_base_url.netloc}{image_url}"
        return image_url
    
    try:
        # Generate filename and save path
        parsed_url = urlparse(image_url)
        file_extension = os.path.splitext(parsed_url.path)[1] or ".png"
        filename = f"{uuid.uuid4()}{file_extension}"
        save_path = os.path.join(Config.IMAGE_SAVE_DIR, filename)
        
        # Ensure save directory exists
        os.makedirs(Config.IMAGE_SAVE_DIR, exist_ok=True)
        
        if IMAGE_DEBUG:
            logger.debug(f"Downloading image: {image_url} -> {save_path}")
        
        # Configure proxy
        proxy = None
        if Config.PROXY_HOST and Config.PROXY_PORT:
            proxy_auth = None
            if Config.PROXY_USER and Config.PROXY_PASS:
                proxy_auth = aiohttp.BasicAuth(Config.PROXY_USER, Config.PROXY_PASS)
            
            proxy_url = f"http://{Config.PROXY_HOST}:{Config.PROXY_PORT}"
            if IMAGE_DEBUG:
                auth_info = f" (with auth)" if proxy_auth else ""
                logger.debug(f"Using proxy: {proxy_url}{auth_info}")
            proxy = proxy_url
        
        # Download image
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Create request parameters
            request_kwargs = {"timeout": 30}
            if proxy:
                request_kwargs["proxy"] = proxy
                if Config.PROXY_USER and Config.PROXY_PASS:
                    request_kwargs["proxy_auth"] = aiohttp.BasicAuth(Config.PROXY_USER, Config.PROXY_PASS)
            
            async with session.get(image_url, **request_kwargs) as response:
                if response.status != 200:
                    logger.warning(f"Download failed with status: {response.status}, URL: {image_url}")
                    return image_url
                
                content = await response.read()
                if not content:
                    logger.warning("Downloaded content is empty")
                    return image_url
                
                # Save image
                async with aiofiles.open(save_path, "wb") as f:
                    await f.write(content)
        
        # Verify file was saved successfully
        if not os.path.exists(save_path) or os.path.getsize(save_path) == 0:
            logger.warning(f"Failed to save image: {save_path}")
            if os.path.exists(save_path):
                os.remove(save_path)
            return image_url
        
        # Return local URL
        # Get filename
        filename = os.path.basename(save_path)
        
        # Parse base URL
        parsed_base_url = urlparse(Config.BASE_URL)
        base_path = parsed_base_url.path.rstrip('/')
        
        # Use fixed image URL format
        relative_url = f"/images/{filename}"
        
        # If STATIC_PATH_PREFIX is set, use it as prefix
        if Config.STATIC_PATH_PREFIX:
            prefix = Config.STATIC_PATH_PREFIX
            if not prefix.startswith('/'):
                prefix = f"/{prefix}"
            relative_url = f"{prefix}/images/{filename}"
        
        # If BASE_URL has subpath, prepend it to relative URL
        if base_path:
            relative_url = f"{base_path}{relative_url}"
        
        # Handle duplicate slashes
        while "//" in relative_url:
            relative_url = relative_url.replace("//", "/")
        
        # Generate full URL
        full_url = f"{parsed_base_url.scheme}://{parsed_base_url.netloc}{relative_url}"
        
        if IMAGE_DEBUG:
            logger.debug(f"Image saved successfully: {full_url}")
            logger.debug(f"Image save path: {save_path}")
        
        return full_url
    except Exception as e:
        logger.error(f"Failed to download image: {str(e)}", exc_info=IMAGE_DEBUG)
        return image_url

async def localize_image_urls(image_urls: list) -> list:
    """
    Localize multiple image URLs
    
    Args:
        image_urls: List of image URLs
        
    Returns:
        List of localized URLs
    """
    if not Config.IMAGE_LOCALIZATION or not image_urls:
        return image_urls
    
    if IMAGE_DEBUG:
        logger.debug(f"Localizing {len(image_urls)} URLs: {image_urls}")
    else:
        logger.info(f"Localizing {len(image_urls)} images")
    
    localized_urls = []
    for url in image_urls:
        localized_url = await download_and_save_image(url)
        localized_urls.append(localized_url)
    
    return localized_urls 