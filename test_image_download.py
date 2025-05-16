import asyncio
import os
import sys
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 添加src目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils import download_and_save_image, localize_image_urls
from src.config import Config

# 设置为True启用本地化
Config.IMAGE_LOCALIZATION = True
# 打开调试日志
os.environ["IMAGE_DEBUG"] = "true"
# 确保目录存在
os.makedirs(Config.IMAGE_SAVE_DIR, exist_ok=True)

async def test_single_download():
    """测试单个图片下载"""
    # 使用一个可靠的图片URL进行测试
    test_url = "https://pic.baidu.com/feed/b90e7bec54e736d1f9ddbe94c2691f254d4ade13.jpeg"
    print(f"测试单个图片下载: {test_url}")
    
    local_url = await download_and_save_image(test_url)
    print(f"下载结果: {local_url}")
    
    # 检查文件是否真的下载了
    if local_url.startswith("http"):
        # 处理完整URL的情况
        url_path = local_url.split(Config.BASE_URL, 1)[-1]
        if url_path.startswith("/static/"):
            relative_path = url_path[len("/static/"):]
            file_path = os.path.join(Config.STATIC_DIR, relative_path)
            print(f"完整URL转换为文件路径: {file_path}")
            
            if os.path.exists(file_path):
                print(f"文件存在: {file_path}, 大小: {os.path.getsize(file_path)} 字节")
            else:
                print(f"文件不存在: {file_path}")
                # 尝试查找可能的文件
                dir_path = os.path.dirname(file_path)
                if os.path.exists(dir_path):
                    print(f"目录存在: {dir_path}")
                    print(f"目录内容: {os.listdir(dir_path)}")
                else:
                    print(f"目录不存在: {dir_path}")
        else:
            print(f"URL格式异常: {local_url}")
    elif local_url.startswith("/static/"):
        # 从URL恢复实际的文件路径
        relative_path = local_url[len("/static/"):]
        file_path = os.path.join(Config.STATIC_DIR, relative_path)
        print(f"相对URL转换为文件路径: {file_path}")
        
        if os.path.exists(file_path):
            print(f"文件存在: {file_path}, 大小: {os.path.getsize(file_path)} 字节")
        else:
            print(f"文件不存在: {file_path}")
    else:
        print("下载失败，返回了原始URL")

async def test_multiple_downloads():
    """测试多个图片下载"""
    test_urls = [
        "https://pic.baidu.com/feed/b90e7bec54e736d1f9ddbe94c2691f254d4ade13.jpeg",
        "https://pic1.zhimg.com/v2-b78b719d8782ad5146851b87bbd3a9fb_r.jpg"
    ]
    print(f"\n测试多个图片下载: {test_urls}")
    
    local_urls = await localize_image_urls(test_urls)
    
    print(f"本地化结果: {local_urls}")
    
    # 验证所有文件是否下载成功
    for i, url in enumerate(local_urls):
        print(f"\n检查文件 {i+1}:")
        if url.startswith("http"):
            # 处理完整URL的情况
            if url.startswith(Config.BASE_URL):
                url_path = url.split(Config.BASE_URL, 1)[-1]
                if url_path.startswith("/static/"):
                    relative_path = url_path[len("/static/"):]
                    file_path = os.path.join(Config.STATIC_DIR, relative_path)
                    print(f"完整URL转换为文件路径: {file_path}")
                    
                    if os.path.exists(file_path):
                        print(f"文件 {i+1} 存在: {file_path}, 大小: {os.path.getsize(file_path)} 字节")
                    else:
                        print(f"文件 {i+1} 不存在: {file_path}")
                        # 尝试查找可能的文件
                        dir_path = os.path.dirname(file_path)
                        if os.path.exists(dir_path):
                            print(f"目录存在: {dir_path}")
                            print(f"目录内容: {os.listdir(dir_path)}")
                        else:
                            print(f"目录不存在: {dir_path}")
                else:
                    print(f"URL格式异常: {url}")
            else:
                print(f"文件 {i+1} 下载失败，返回了原始URL: {url}")
        elif url.startswith("/static/"):
            # 从URL恢复实际的文件路径
            relative_path = url[len("/static/"):]
            file_path = os.path.join(Config.STATIC_DIR, relative_path)
            print(f"相对URL转换为文件路径: {file_path}")
            
            if os.path.exists(file_path):
                print(f"文件 {i+1} 存在: {file_path}, 大小: {os.path.getsize(file_path)} 字节")
            else:
                print(f"文件 {i+1} 不存在: {file_path}")
        else:
            print(f"文件 {i+1} 下载失败，返回了原始URL: {url}")

async def main():
    print(f"配置信息:")
    print(f"IMAGE_LOCALIZATION: {Config.IMAGE_LOCALIZATION}")
    print(f"STATIC_DIR: {Config.STATIC_DIR}")
    print(f"IMAGE_SAVE_DIR: {Config.IMAGE_SAVE_DIR}")
    
    await test_single_download()
    await test_multiple_downloads()

if __name__ == "__main__":
    asyncio.run(main()) 