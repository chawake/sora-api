import time
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from ..api.dependencies import verify_api_key, get_sora_client_dep
from ..services.image_service import get_generation_result, get_task_api_key
from ..key_manager import key_manager

# 设置日志
logger = logging.getLogger("sora-api.generation")

# 创建路由
router = APIRouter()

@router.get("/generation/{request_id}")
async def check_generation_status(
    request_id: str,
    client_info = Depends(get_sora_client_dep()),
    api_key: str = Depends(verify_api_key)
):
    """
    检查图像生成任务的状态
    
    Args:
        request_id: 要查询的请求ID
        client_info: Sora客户端信息（由依赖提供）
        api_key: API密钥（由依赖提供）
    
    Returns:
        包含任务状态和结果的JSON响应
    """
    # 获取任务对应的原始API密钥
    task_api_key = get_task_api_key(request_id)
    
    # 如果找到任务对应的API密钥，则使用该密钥获取客户端
    if task_api_key:
        # 获取使用特定API密钥的客户端
        specific_client_dep = get_sora_client_dep(specific_key=task_api_key)
        client_info = await specific_client_dep(api_key)
    
    # 解析客户端信息
    _, sora_auth_token = client_info
    
    # 记录开始时间
    start_time = time.time()
    success = False
    
    try:
        # 获取任务结果
        result = get_generation_result(request_id)
        
        if result.get("status") == "not_found":
            raise HTTPException(status_code=404, detail=f"找不到生成任务: {request_id}")
        
        if result.get("status") == "completed":
            # 任务已完成，返回结果
            image_urls = result.get("image_urls", [])
            
            # 构建OpenAI兼容的响应
            response = {
                "id": request_id,
                "object": "chat.completion",
                "created": result.get("timestamp", int(time.time())),
                "model": "sora-1.0",
                "choices": [
                    {
                        "index": i,
                        "message": {
                            "role": "assistant",
                            "content": f"![Generated Image]({url})"
                        },
                        "finish_reason": "stop"
                    }
                    for i, url in enumerate(image_urls)
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 20,
                    "total_tokens": 20
                }
            }
            success = True
            
        elif result.get("status") == "failed":
            # 任务失败
            message = result.get("message", f"```think\n生成失败: {result.get('error', '未知错误')}\n```")
            
            response = {
                "id": request_id,
                "object": "chat.completion",
                "created": result.get("timestamp", int(time.time())),
                "model": "sora-1.0",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": message
                        },
                        "finish_reason": "error"
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 10,
                    "total_tokens": 10
                }
            }
            success = False
            
        else:  # 处理中
            # 任务仍在处理中
            message = result.get("message", "```think\n正在生成图像，请稍候...\n```")
            
            response = {
                "id": request_id,
                "object": "chat.completion",
                "created": result.get("timestamp", int(time.time())),
                "model": "sora-1.0",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": message
                        },
                        "finish_reason": "processing"
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 10,
                    "total_tokens": 10
                }
            }
            success = True
            
        # 记录请求结果
        response_time = time.time() - start_time
        key_manager.record_request_result(sora_auth_token, success, response_time)
        
        # 返回响应
        return JSONResponse(content=response)
        
    except HTTPException:
        # 直接重新抛出HTTP异常
        raise
    except Exception as e:
        # 处理其他异常
        success = False
        logger.error(f"检查任务状态失败: {str(e)}", exc_info=True)
        
        # 记录请求结果
        response_time = time.time() - start_time
        key_manager.record_request_result(sora_auth_token, success, response_time)
        
        raise HTTPException(status_code=500, detail=f"检查任务状态失败: {str(e)}") 