import asyncio
import base64
import os
import tempfile
import time
import uuid
import logging
import threading
from typing import List, Dict, Any, Optional, Union, Tuple

from ..sora_integration import SoraClient
from ..config import Config
from ..utils import localize_image_urls

logger = logging.getLogger("sora-api.image_service")

# 存储生成结果的全局字典
generation_results = {}

# 存储任务与API密钥的映射关系
task_to_api_key = {}

# 将处理中状态消息格式化为think代码块
def format_think_block(message: str) -> str:
    """将消息放入```think代码块中"""
    return f"```think\n{message}\n```"

async def process_image_task(
    request_id: str,
    sora_client: SoraClient,
    task_type: str,
    prompt: str,
    **kwargs
) -> None:
    """
    统一的图像处理任务函数
    
    Args:
        request_id: 请求ID
        sora_client: Sora客户端实例
        task_type: 任务类型 ("generation" 或 "remix")
        prompt: 提示词
        **kwargs: 其他参数，取决于任务类型
    """
    try:
        # 保存当前任务使用的API密钥，以便后续使用同一密钥进行操作
        current_api_key = sora_client.auth_token
        task_to_api_key[request_id] = current_api_key
        
        # 更新状态为处理中
        generation_results[request_id] = {
            "status": "processing",
            "message": format_think_block("正在准备生成任务，请稍候..."),
            "timestamp": int(time.time()),
            "api_key": current_api_key  # 记录使用的API密钥
        }
        
        # 根据任务类型执行不同操作
        if task_type == "generation":
            # 文本到图像生成
            num_images = kwargs.get("num_images", 1)
            width = kwargs.get("width", 720)
            height = kwargs.get("height", 480)
            
            # 更新状态
            generation_results[request_id] = {
                "status": "processing",
                "message": format_think_block("正在生成图像，请耐心等待..."),
                "timestamp": int(time.time()),
                "api_key": current_api_key
            }
            
            # 生成图像
            logger.info(f"[{request_id}] 开始生成图像, 提示词: {prompt}")
            image_urls = await sora_client.generate_image(
                prompt=prompt,
                num_images=num_images,
                width=width,
                height=height
            )
            
        elif task_type == "remix":
            # 图像到图像生成（Remix）
            image_data = kwargs.get("image_data")
            num_images = kwargs.get("num_images", 1)
            
            if not image_data:
                raise ValueError("缺少图像数据")
                
            # 更新状态
            generation_results[request_id] = {
                "status": "processing",
                "message": format_think_block("正在处理上传的图片..."),
                "timestamp": int(time.time()),
                "api_key": current_api_key
            }
            
            # 保存base64图片到临时文件
            temp_dir = tempfile.mkdtemp()
            temp_image_path = os.path.join(temp_dir, f"upload_{uuid.uuid4()}.png")
            
            try:
                # 解码并保存图片
                with open(temp_image_path, "wb") as f:
                    f.write(base64.b64decode(image_data))
                
                # 更新状态
                generation_results[request_id] = {
                    "status": "processing",
                    "message": format_think_block("正在上传图片到Sora服务..."),
                    "timestamp": int(time.time()),
                    "api_key": current_api_key
                }
                
                # 上传图片 - 确保使用与初始请求相同的API密钥
                upload_result = await sora_client.upload_image(temp_image_path)
                media_id = upload_result['id']
                
                # 更新状态
                generation_results[request_id] = {
                    "status": "processing",
                    "message": format_think_block("正在基于图片生成新图像..."),
                    "timestamp": int(time.time()),
                    "api_key": current_api_key
                }
                
                # 执行remix生成
                logger.info(f"[{request_id}] 开始生成Remix图像, 提示词: {prompt}")
                image_urls = await sora_client.generate_image_remix(
                    prompt=prompt,
                    media_id=media_id,
                    num_images=num_images
                )
                
            finally:
                # 清理临时文件
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
        else:
            raise ValueError(f"未知的任务类型: {task_type}")
        
        # 验证生成结果
        if isinstance(image_urls, str):
            logger.warning(f"[{request_id}] 图像生成失败或返回了错误信息: {image_urls}")
            generation_results[request_id] = {
                "status": "failed",
                "error": image_urls,
                "message": format_think_block(f"图像生成失败: {image_urls}"),
                "timestamp": int(time.time()),
                "api_key": current_api_key
            }
            return
            
        if not image_urls:
            logger.warning(f"[{request_id}] 图像生成返回了空列表")
            generation_results[request_id] = {
                "status": "failed",
                "error": "图像生成返回了空结果",
                "message": format_think_block("图像生成失败: 服务器返回了空结果"),
                "timestamp": int(time.time()),
                "api_key": current_api_key
            }
            return
            
        logger.info(f"[{request_id}] 成功生成 {len(image_urls)} 张图片")
        
        # 本地化图片URL
        if Config.IMAGE_LOCALIZATION:
            logger.info(f"[{request_id}] 准备进行图片本地化处理")
            try:
                localized_urls = await localize_image_urls(image_urls)
                logger.info(f"[{request_id}] 图片本地化处理完成")
                
                # 检查本地化结果
                if not localized_urls:
                    logger.warning(f"[{request_id}] 本地化处理返回了空列表，将使用原始URL")
                    localized_urls = image_urls
                
                # 检查是否所有URL都被正确本地化
                local_count = sum(1 for url in localized_urls if url.startswith("/static/") or "/static/" in url)
                logger.info(f"[{request_id}] 本地化结果: 总计 {len(localized_urls)} 张图片，成功本地化 {local_count} 张")
                
                if local_count == 0:
                    logger.warning(f"[{request_id}] 警告：没有一个URL被成功本地化，将使用原始URL")
                    localized_urls = image_urls
                
                image_urls = localized_urls
            except Exception as e:
                logger.error(f"[{request_id}] 图片本地化过程中发生错误: {str(e)}", exc_info=True)
                logger.info(f"[{request_id}] 由于错误，将使用原始URL")
        else:
            logger.info(f"[{request_id}] 图片本地化功能未启用，使用原始URL")
        
        # 存储结果
        generation_results[request_id] = {
            "status": "completed",
            "image_urls": image_urls,
            "timestamp": int(time.time()),
            "api_key": current_api_key
        }
        
        # 30分钟后自动清理结果
        def cleanup_task():
            generation_results.pop(request_id, None)
            task_to_api_key.pop(request_id, None)
            
        threading.Timer(1800, cleanup_task).start()
        
    except Exception as e:
        error_message = f"图像生成失败: {str(e)}"
        generation_results[request_id] = {
            "status": "failed",
            "error": error_message,
            "message": format_think_block(error_message),
            "timestamp": int(time.time()),
            "api_key": sora_client.auth_token  # 记录当前API密钥
        }
        logger.error(f"图像生成失败 (ID: {request_id}): {str(e)}", exc_info=True)

def get_generation_result(request_id: str) -> Dict[str, Any]:
    """获取生成结果"""
    if request_id not in generation_results:
        return {
            "status": "not_found",
            "error": f"找不到生成任务: {request_id}",
            "timestamp": int(time.time())
        }
    
    return generation_results[request_id]

def get_task_api_key(request_id: str) -> Optional[str]:
    """获取任务对应的API密钥"""
    return task_to_api_key.get(request_id) 