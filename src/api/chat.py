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

# Configure logging
logger = logging.getLogger("sora-api.chat")

# Create router
router = APIRouter()

@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    background_tasks: BackgroundTasks,
    client_info = Depends(get_sora_client_dep()),
    api_key: str = Depends(verify_api_key)
):
    """
    Chat completions endpoint - handles text-to-image and image-to-image requests.
    Compatible with OpenAI API format.
    """
    # Parse client info
    sora_client, sora_auth_token = client_info
    
    # Record start time
    start_time = time.time()
    success = False
    
    try:
        # Analyze user messages
        user_messages = [m for m in request.messages if m.role == "user"]
        if not user_messages:
            raise HTTPException(status_code=400, detail="At least one user message is required")
        
        last_user_message = user_messages[-1]
        prompt = ""
        image_data = None
        
        # Extract prompt and image data
        if isinstance(last_user_message.content, str):
            # Simple string content
            prompt = last_user_message.content
            
            # Check for embedded base64 image
            pattern = r'data:image\/[^;]+;base64,([^"]+)'
            match = re.search(pattern, prompt)
            if match:
                image_data = match.group(1)
                # Remove base64 data from the prompt
                prompt = re.sub(pattern, "[uploaded image]", prompt)
        else:
            # Multimodal content: extract text and images
            content_items = last_user_message.content
            text_parts = []
            
            for item in content_items:
                if item.type == "text" and item.text:
                    text_parts.append(item.text)
                elif item.type == "image_url" and item.image_url:
                    # Handle image URL with base64 data
                    url = item.image_url.get("url", "")
                    if url.startswith("data:image/"):
                        pattern = r'data:image\/[^;]+;base64,([^"]+)'
                        match = re.search(pattern, url)
                        if match:
                            image_data = match.group(1)
                            text_parts.append("[uploaded image]")
            
            prompt = " ".join(text_parts)
        
        # Streaming vs non-streaming response
        if request.stream:
            # Streaming response handling
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
            
            # Record request result
            response_time = time.time() - start_time
            key_manager.record_request_result(sora_auth_token, success, response_time)
            
            return response
        else:
            # Non-streaming response - return immediate acknowledgement
            request_id = f"chatcmpl-{uuid.uuid4().hex}"
            
            # Create background task
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
                
            # Return processing response
            processing_message = "Preparing generation task, please wait..."
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
            
            # Record request result
            response_time = time.time() - start_time
            key_manager.record_request_result(sora_auth_token, success, response_time)
            
            return JSONResponse(content=response)
            
    except Exception as e:
        success = False
        logger.error(f"Failed to process chat completion request: {str(e)}", exc_info=True)
        
        # Record request result
        response_time = time.time() - start_time
        key_manager.record_request_result(sora_auth_token, success, response_time)
        
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")