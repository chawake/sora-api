import time
import logging
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from ..api.dependencies import verify_api_key, get_sora_client_dep
from ..services.image_service import get_generation_result, get_task_api_key
from ..key_manager import key_manager

# Configure logging
logger = logging.getLogger("sora-api.generation")

# Create router
router = APIRouter()

@router.get("/generation/{request_id}")
async def check_generation_status(
    request_id: str,
    client_info = Depends(get_sora_client_dep()),
    api_key: str = Depends(verify_api_key)
):
    """
    Check the status of an image generation task.
    
    Args:
        request_id: The request ID to query.
        client_info: Sora client info (provided by dependency).
        api_key: API key (provided by dependency).
    
    Returns:
        A JSON response containing task status and result.
    """
    # Get the original API key used for this task
    task_api_key = get_task_api_key(request_id)
    
    # If found, use that key to get the client
    if task_api_key:
        # Get a client using the specific API key
        specific_client_dep = get_sora_client_dep(specific_key=task_api_key)
        client_info = await specific_client_dep(api_key)
    
    # Parse client info
    _, sora_auth_token = client_info
    
    # Record start time
    start_time = time.time()
    success = False
    
    try:
        # Get task result
        result = get_generation_result(request_id)
        
        if result.get("status") == "not_found":
            raise HTTPException(status_code=404, detail=f"Generation task not found: {request_id}")
        
        if result.get("status") == "completed":
            # Task completed; return result
            image_urls = result.get("image_urls", [])
            
            # Build an OpenAI-compatible response
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
            # Task failed
            message = result.get("message", f"```think\nGeneration failed: {result.get('error', 'unknown error')}\n```")
            
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
            
        else:  # processing
            # Task is still in progress
            message = result.get("message", "```think\nGenerating image, please wait...\n```")
            
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
            
        # Record request result
        response_time = time.time() - start_time
        key_manager.record_request_result(sora_auth_token, success, response_time)
        
        # Return response
        return JSONResponse(content=response)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle other exceptions
        success = False
        logger.error(f"Failed to check task status: {str(e)}", exc_info=True)
        
        # Record request result
        response_time = time.time() - start_time
        key_manager.record_request_result(sora_auth_token, success, response_time)
        
        raise HTTPException(status_code=500, detail=f"Failed to check task status: {str(e)}")