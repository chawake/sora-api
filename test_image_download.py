import asyncio
import os
import sys

# 添加src目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils import download_and_save_image, localize_image_urls
from src.config import Config

# 设置为True启用本地化
Config.IMAGE_LOCALIZATION = True
# 确保目录存在
os.makedirs(Config.IMAGE_SAVE_DIR, exist_ok=True)

async def test_single_download():
    """测试单个图片下载"""
    # 使用一个可靠的图片URL进行测试
    test_url = "https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png"
    print(f"测试单个图片下载: {test_url}")
    
    local_url = await download_and_save_image(test_url)
    print(f"下载结果: {local_url}")
    
    # 检查文件是否真的下载了
    if local_url.startswith("/static/"):
        file_path = os.path.join(os.path.dirname(Config.STATIC_DIR), local_url[1:])
        if os.path.exists(file_path):
            print(f"文件存在: {file_path}, 大小: {os.path.getsize(file_path)} 字节")
        else:
            print(f"文件不存在: {file_path}")
    else:
        print("下载失败，返回了原始URL")

async def test_multiple_downloads():
    """测试多个图片下载"""
    test_urls = [
        "https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/121px-Python-logo-notext.svg.png"
    ]
    print(f"\n测试多个图片下载: {test_urls}")
    
    local_urls = await localize_image_urls(test_urls)
    
    print(f"本地化结果: {local_urls}")
    
    # 验证所有文件是否下载成功
    for i, url in enumerate(local_urls):
        if url.startswith("/static/"):
            file_path = os.path.join(os.path.dirname(Config.STATIC_DIR), url[1:])
            if os.path.exists(file_path):
                print(f"文件 {i+1} 存在: {file_path}, 大小: {os.path.getsize(file_path)} 字节")
            else:
                print(f"文件 {i+1} 不存在: {file_path}")
        else:
            print(f"文件 {i+1} 下载失败，返回了原始URL")

async def main():
    print(f"配置信息:")
    print(f"IMAGE_LOCALIZATION: {Config.IMAGE_LOCALIZATION}")
    print(f"STATIC_DIR: {Config.STATIC_DIR}")
    print(f"IMAGE_SAVE_DIR: {Config.IMAGE_SAVE_DIR}")
    
    await test_single_download()
    await test_multiple_downloads()

if __name__ == "__main__":
    asyncio.run(main()) 