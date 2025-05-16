import uuid
import time
import re
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse

from ..models.schemas import ChatCompletionRequest
from ..api.dependencies import verify_api_key, get_sora_client_dep
from ..services.image_service import process_image_task, format_think_block
from ..services.streaming import generate_streaming_response, generate_streaming_remix_response
from ..key_manager import key_manager

# 设置日志
logger = logging.getLogger("sora-api.chat")

# 创建路由
router = APIRouter()

@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    background_tasks: BackgroundTasks,
    client_info = Depends(get_sora_client_dep()),
    api_key: str = Depends(verify_api_key)
):
    """
    聊天完成端点 - 处理文本到图像和图像到图像的请求
    兼容OpenAI API格式
    """
    # 解析客户端信息
    sora_client, sora_auth_token = client_info
    
    # 记录开始时间
    start_time = time.time()
    success = False
    
    try:
        # 分析用户消息
        user_messages = [m for m in request.messages if m.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="至少需要一条用户消息")
        
        last_user_message = user_messages[-1]
        prompt = ""
        image_data = None
        
        # 提取提示词和图片数据
        if isinstance(last_user_message.content, str):
            # 简单的字符串内容
            prompt = last_user_message.content
            
            # 检查是否包含内嵌的base64图片
            pattern = r'data:image\/[^;]+;base64,([^"]+)'
            match = re.search(pattern, prompt)
            if match:
                image_data = match.group(1)
                # 从提示词中删除base64数据
                prompt = re.sub(pattern, "[已上传图片]", prompt)
        else:
            # 多模态内容，提取文本和图片
            content_items = last_user_message.content
            text_parts = []
            
            for item in content_items:
                if item.type == "text" and item.text:
                    text_parts.append(item.text)
                elif item.type == "image_url" and item.image_url:
                    # 如果有图片URL包含base64数据
                    url = item.image_url.get("url", "")
                    if url.startswith("data:image/"):
                        pattern = r'data:image\/[^;]+;base64,([^"]+)'
                        match = re.search(pattern, url)
                        if match:
                            image_data = match.group(1)
                            text_parts.append("[已上传图片]")
            
            prompt = " ".join(text_parts)
        
        # 检查是否为流式响应
        if request.stream:
            # 流式响应处理
            if image_data:
                response = StreamingResponse(
                    generate_streaming_remix_response(sora_client, prompt, image_data, request.n),
                    media_type="text/event-stream"
                )
            else:
                response = StreamingResponse(
                    generate_streaming_response(sora_client, prompt, request.n),
                    media_type="text/event-stream"
                )
            success = True
            
            # 记录请求结果
            response_time = time.time() - start_time
            key_manager.record_request_result(sora_auth_token, success, response_time)
            
            return response
        else:
            # 非流式响应 - 返回一个即时响应，表示任务已接收
            request_id = f"chatcmpl-{uuid.uuid4().hex}"
            
            # 创建后台任务
            if image_data:
                background_tasks.add_task(
                    process_image_task,
                    request_id,
                    sora_client,
                    "remix",
                    prompt,
                    image_data=image_data,
                    num_images=request.n
                )
            else:
                background_tasks.add_task(
                    process_image_task,
                    request_id,
                    sora_client,
                    "generation",
                    prompt,
                    num_images=request.n,
                    width=720,
                    height=480
                )
                
            # 返回正在处理的响应
            processing_message = "正在准备生成任务，请稍候..."
            response = {
                "id": request_id,
                "object": "chat.completion",
                "created": int(time.time()),
                "model": "sora-1.0",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": format_think_block(processing_message)
                        },
                        "finish_reason": "processing"
                    }
                ],
                "usage": {
                    "prompt_tokens": len(prompt) // 4,
                    "completion_tokens": 10,
                    "total_tokens": len(prompt) // 4 + 10
                }
            }
            
            success = True
            
            # 记录请求结果
            response_time = time.time() - start_time
            key_manager.record_request_result(sora_auth_token, success, response_time)
            
            return JSONResponse(content=response)
            
    except Exception as e:
        success = False
        logger.error(f"处理聊天完成请求失败: {str(e)}", exc_info=True)
        
        # 记录请求结果
        response_time = time.time() - start_time
        key_manager.record_request_result(sora_auth_token, success, response_time)
        
        raise HTTPException(status_code=500, detail=f"图像生成失败: {str(e)}") 