import json
import time
import asyncio
import logging
from typing import AsyncGenerator, List, Dict, Any

from ..sora_integration import SoraClient
from ..config import Config
from ..utils import localize_image_urls
from .image_service import format_think_block

logger = logging.getLogger("sora-api.streaming")

async def generate_streaming_response(
    sora_client: SoraClient,
    prompt: str,
    n_images: int = 1
) -> AsyncGenerator[str, None]:
    """
    文本到图像的流式响应生成器
    
    Args:
        sora_client: Sora客户端
        prompt: 提示词
        n_images: 生成图像数量
    
    Yields:
        SSE格式的响应数据
    """
    request_id = f"chatcmpl-stream-{time.time()}-{hash(prompt) % 10000}"
    
    # 发送开始事件
    yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]})}\n\n"
    
    # 发送处理中的消息（放在代码块中）
    start_msg = "```think\n正在生成图像，请稍候...\n"
    yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': start_msg}, 'finish_reason': None}]})}\n\n"
    
    # 创建一个后台任务来生成图像
    logger.info(f"[流式响应 {request_id}] 开始生成图像, 提示词: {prompt}")
    generation_task = asyncio.create_task(sora_client.generate_image(
        prompt=prompt,
        num_images=n_images,
        width=720,
        height=480
    ))
    
    # 每5秒发送一条"仍在生成中"的消息，防止连接超时
    progress_messages = [
        "正在处理您的请求...",
        "仍在生成图像中，请继续等待...",
        "Sora正在创作您的图像作品...",
        "图像生成需要一点时间，感谢您的耐心等待...",
        "我们正在努力为您创作高质量图像..."
    ]
    
    i = 0
    while not generation_task.done():
        # 每5秒发送一次进度消息
        await asyncio.sleep(5)
        progress_msg = progress_messages[i % len(progress_messages)]
        i += 1
        content = "\n" + progress_msg + "\n"
        yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': content}, 'finish_reason': None}]})}\n\n"
    
    try:
        # 获取生成结果
        image_urls = await generation_task
        logger.info(f"[流式响应 {request_id}] 图像生成完成，获取到 {len(image_urls) if isinstance(image_urls, list) else '非列表'} 个URL")
        
        # 本地化图片URL
        if Config.IMAGE_LOCALIZATION and isinstance(image_urls, list) and image_urls:
            logger.info(f"[流式响应 {request_id}] 准备进行图片本地化处理")
            try:
                localized_urls = await localize_image_urls(image_urls)
                image_urls = localized_urls
                logger.info(f"[流式响应 {request_id}] 图片本地化处理完成")
            except Exception as e:
                logger.error(f"[流式响应 {request_id}] 图片本地化过程中发生错误: {str(e)}", exc_info=True)
                logger.info(f"[流式响应 {request_id}] 由于错误，将使用原始URL")
        elif not Config.IMAGE_LOCALIZATION:
            logger.info(f"[流式响应 {request_id}] 图片本地化功能未启用")
        
        # 结束代码块
        content_str = "\n```\n\n"
        yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': content_str}, 'finish_reason': None}]})}\n\n"
        
        # 添加生成的图片URLs
        for i, url in enumerate(image_urls):
            if i > 0:
                content_str = "\n\n"
                yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': content_str}, 'finish_reason': None}]})}\n\n"
            
            image_markdown = f"![Generated Image]({url})"
            yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': image_markdown}, 'finish_reason': None}]})}\n\n"
        
        # 发送完成事件
        yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
        
        # 发送结束标志
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        error_msg = f"图像生成失败: {str(e)}"
        logger.error(f"[流式响应 {request_id}] 错误: {error_msg}", exc_info=True)
        error_content = f"\n{error_msg}\n```"
        yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': error_content}, 'finish_reason': 'error'}]})}\n\n"
        yield "data: [DONE]\n\n"

async def generate_streaming_remix_response(
    sora_client: SoraClient,
    prompt: str,
    image_data: str,
    n_images: int = 1
) -> AsyncGenerator[str, None]:
    """
    图像到图像的流式响应生成器
    
    Args:
        sora_client: Sora客户端
        prompt: 提示词
        image_data: Base64编码的图像数据
        n_images: 生成图像数量
    
    Yields:
        SSE格式的响应数据
    """
    import os
    import tempfile
    import uuid
    import base64
    
    request_id = f"chatcmpl-stream-remix-{time.time()}-{hash(prompt) % 10000}"
    
    # 发送开始事件
    yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]})}\n\n"
    
    try:
        # 保存base64图片到临时文件
        temp_dir = tempfile.mkdtemp()
        temp_image_path = os.path.join(temp_dir, f"upload_{uuid.uuid4()}.png")
        
        try:
            # 解码并保存图片
            with open(temp_image_path, "wb") as f:
                f.write(base64.b64decode(image_data))
            
            # 上传图片
            upload_msg = "```think\n上传图片中...\n"
            yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': upload_msg}, 'finish_reason': None}]})}\n\n"
            
            logger.info(f"[流式响应Remix {request_id}] 上传图片中")
            upload_result = await sora_client.upload_image(temp_image_path)
            media_id = upload_result['id']
            
            # 发送生成中消息
            generate_msg = "\n基于图片生成新图像中...\n"
            yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': generate_msg}, 'finish_reason': None}]})}\n\n"
            
            # 创建后台任务生成图像
            logger.info(f"[流式响应Remix {request_id}] 开始生成图像，提示词: {prompt}")
            generation_task = asyncio.create_task(sora_client.generate_image_remix(
                prompt=prompt,
                media_id=media_id,
                num_images=n_images
            ))
            
            # 每5秒发送一条"仍在生成中"的消息
            progress_messages = [
                "正在处理您的请求...",
                "仍在生成图像中，请继续等待...",
                "Sora正在基于您的图片创作新作品...",
                "图像生成需要一点时间，感谢您的耐心等待...",
                "正在融合您的风格和提示词，打造专属图像..."
            ]
            
            i = 0
            while not generation_task.done():
                await asyncio.sleep(5)
                progress_msg = progress_messages[i % len(progress_messages)]
                i += 1
                content = "\n" + progress_msg + "\n"
                yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': content}, 'finish_reason': None}]})}\n\n"
            
            # 获取生成结果
            image_urls = await generation_task
            logger.info(f"[流式响应Remix {request_id}] 图像生成完成")
            
            # 本地化图片URL
            if Config.IMAGE_LOCALIZATION:
                logger.info(f"[流式响应Remix {request_id}] 进行图片本地化处理")
                localized_urls = await localize_image_urls(image_urls)
                image_urls = localized_urls
                logger.info(f"[流式响应Remix {request_id}] 图片本地化处理完成")
            else:
                logger.info(f"[流式响应Remix {request_id}] 图片本地化功能未启用")
            
            # 结束代码块
            content_str = "\n```\n\n"
            yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': content_str}, 'finish_reason': None}]})}\n\n"
            
            # 发送图片URL作为Markdown
            for i, url in enumerate(image_urls):
                if i > 0:
                    newline_str = "\n\n"
                    yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': newline_str}, 'finish_reason': None}]})}\n\n"
                
                image_markdown = f"![Generated Image]({url})"
                yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': image_markdown}, 'finish_reason': None}]})}\n\n"
            
            # 发送完成事件
            yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
            
            # 发送结束标志
            yield "data: [DONE]\n\n"
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
                
    except Exception as e:
        error_msg = f"图像Remix失败: {str(e)}"
        logger.error(f"[流式响应Remix {request_id}] 错误: {error_msg}", exc_info=True)
        error_content = f"\n{error_msg}\n```"
        yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': error_content}, 'finish_reason': 'error'}]})}\n\n"
    
    # 结束流
    yield "data: [DONE]\n\n" 