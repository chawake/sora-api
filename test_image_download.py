import asyncio
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add src directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils import download_and_save_image, localize_image_urls
from src.config import Config

# Set to True to enable localization
Config.IMAGE_LOCALIZATION = True
# Enable debug logging
os.environ["IMAGE_DEBUG"] = "true"
# Ensure directory exists
os.makedirs(Config.IMAGE_SAVE_DIR, exist_ok=True)

async def test_single_download():
    """Test single image download"""
    # Use a reliable image URL for testing
    test_url = "https://pic.baidu.com/feed/b90e7bec54e736d1f9ddbe94c2691f254d4ade13.jpeg"
    print(f"Testing single image download: {test_url}")
    
    local_url = await download_and_save_image(test_url)
    print(f"Download result: {local_url}")
    
    # Check if the file was actually downloaded
    if local_url.startswith("http"):
        # Handle full URL case
        url_path = local_url.split(Config.BASE_URL, 1)[-1]
        if url_path.startswith("/static/"):
            relative_path = url_path[len("/static/"):]
            file_path = os.path.join(Config.STATIC_DIR, relative_path)
            print(f"Full URL converted to file path: {file_path}")
            
            if os.path.exists(file_path):
                print(f"File exists: {file_path}, size: {os.path.getsize(file_path)} bytes")
            else:
                print(f"File does not exist: {file_path}")
                # Try to find possible files
                dir_path = os.path.dirname(file_path)
                if os.path.exists(dir_path):
                    print(f"Directory exists: {dir_path}")
                    print(f"Directory contents: {os.listdir(dir_path)}")
                else:
                    print(f"Directory does not exist: {dir_path}")
        else:
            print(f"URL format exception: {local_url}")
    elif local_url.startswith("/static/"):
        # Restore actual file path from URL
        relative_path = local_url[len("/static/"):]
        file_path = os.path.join(Config.STATIC_DIR, relative_path)
        print(f"Relative URL converted to file path: {file_path}")
        
        if os.path.exists(file_path):
            print(f"File exists: {file_path}, size: {os.path.getsize(file_path)} bytes")
        else:
            print(f"File does not exist: {file_path}")
    else:
        print("Download failed, returning original URL")

async def test_multiple_downloads():
    """Test multiple image downloads"""
    test_urls = [
        "https://pic.baidu.com/feed/b90e7bec54e736d1f9ddbe94c2691f254d4ade13.jpeg",
        "https://pic1.zhimg.com/v2-b78b719d8782ad5146851b87bbd3a9fb_r.jpg"
    ]
    print(f"\nTesting multiple image downloads: {test_urls}")
    
    local_urls = await localize_image_urls(test_urls)
    
    print(f"Localization results: {local_urls}")
    
    # Verify all files were downloaded successfully
    for i, url in enumerate(local_urls):
        print(f"\nChecking file {i+1}:")
        if url.startswith("http"):
            # Handle full URL case
            if url.startswith(Config.BASE_URL):
                url_path = url.split(Config.BASE_URL, 1)[-1]
                if url_path.startswith("/static/"):
                    relative_path = url_path[len("/static/"):]
                    file_path = os.path.join(Config.STATIC_DIR, relative_path)
                    print(f"Full URL converted to file path: {file_path}")
                    
                    if os.path.exists(file_path):
                        print(f"File {i+1} exists: {file_path}, size: {os.path.getsize(file_path)} bytes")
                    else:
                        print(f"File {i+1} does not exist: {file_path}")
                        # Try to find possible files
                        dir_path = os.path.dirname(file_path)
                        if os.path.exists(dir_path):
                            print(f"Directory exists: {dir_path}")
                            print(f"Directory contents: {os.listdir(dir_path)}")
                        else:
                            print(f"Directory does not exist: {dir_path}")
                else:
                    print(f"URL format exception: {url}")
            else:
                print(f"File {i+1} download failed, returning original URL: {url}")
        elif url.startswith("/static/"):
            # Restore actual file path from URL
            relative_path = url[len("/static/"):]
            file_path = os.path.join(Config.STATIC_DIR, relative_path)
            print(f"Relative URL converted to file path: {file_path}")
            
            if os.path.exists(file_path):
                print(f"File {i+1} exists: {file_path}, size: {os.path.getsize(file_path)} bytes")
            else:
                print(f"File {i+1} does not exist: {file_path}")
        else:
            print(f"File {i+1} download failed, returning original URL: {url}")

async def main():
    print(f"Configuration:")
    print(f"IMAGE_LOCALIZATION: {Config.IMAGE_LOCALIZATION}")
    print(f"STATIC_DIR: {Config.STATIC_DIR}")
    print(f"IMAGE_SAVE_DIR: {Config.IMAGE_SAVE_DIR}")
    
    await test_single_download()
    await test_multiple_downloads()

if __name__ == "__main__":
    asyncio.run(main()) 