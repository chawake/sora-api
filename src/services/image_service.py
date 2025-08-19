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

# Global dictionary to store generation results
generation_results = {}

# Mapping of request task IDs to API keys used
task_to_api_key = {}

# Format processing status messages into a think code block
def format_think_block(message: str) -> str:
    """Wrap message in a ```think code block."""
    return f"```think\n{message}\n```"

async def process_image_task(
    request_id: str,
    sora_client: SoraClient,
    task_type: str,
    prompt: str,
    **kwargs
) -> None:
    """
    Unified image processing task handler
    
    Args:
        request_id: Request ID
        sora_client: Sora client instance
        task_type: Task type ("generation" or "remix")
        prompt: Prompt text
        **kwargs: Additional parameters depending on task type
    """
    try:
        # Save the API key used for this task to reuse consistently
        current_api_key = sora_client.auth_token
        task_to_api_key[request_id] = current_api_key
        
        # Update status to processing
        generation_results[request_id] = {
            "status": "processing",
            "message": format_think_block("Preparing the generation task, please wait..."),
            "timestamp": int(time.time()),
            "api_key": current_api_key  # record API key used
        }
        
        # Execute different operations based on task type
        if task_type == "generation":
            # Text-to-image generation
            num_images = kwargs.get("num_images", 1)
            width = kwargs.get("width", 720)
            height = kwargs.get("height", 480)
            
            # Update status
            generation_results[request_id] = {
                "status": "processing",
                "message": format_think_block("Generating images, please be patient..."),
                "timestamp": int(time.time()),
                "api_key": current_api_key
            }
            
            # Generate images
            logger.info(f"[{request_id}] Start generating images, prompt: {prompt}")
            image_urls = await sora_client.generate_image(
                prompt=prompt,
                num_images=num_images,
                width=width,
                height=height
            )
            
        elif task_type == "remix":
            # Image-to-image generation (Remix)
            image_data = kwargs.get("image_data")
            num_images = kwargs.get("num_images", 1)
            
            if not image_data:
                raise ValueError("Missing image data")
                
            # Update status
            generation_results[request_id] = {
                "status": "processing",
                "message": format_think_block("Processing the uploaded image..."),
                "timestamp": int(time.time()),
                "api_key": current_api_key
            }
            
            # Save base64 image to a temporary file
            temp_dir = tempfile.mkdtemp()
            temp_image_path = os.path.join(temp_dir, f"upload_{uuid.uuid4()}.png")
            
            try:
                # Decode and save image
                with open(temp_image_path, "wb") as f:
                    f.write(base64.b64decode(image_data))
                
                # Update status
                generation_results[request_id] = {
                    "status": "processing",
                    "message": format_think_block("Uploading image to Sora service..."),
                    "timestamp": int(time.time()),
                    "api_key": current_api_key
                }
                
                # Upload image - ensure the same API key as the initial request is used
                upload_result = await sora_client.upload_image(temp_image_path)
                media_id = upload_result['id']
                
                # Update status
                generation_results[request_id] = {
                    "status": "processing",
                    "message": format_think_block("Generating new images based on the uploaded image..."),
                    "timestamp": int(time.time()),
                    "api_key": current_api_key
                }
                
                # Execute remix generation
                logger.info(f"[{request_id}] Start generating Remix images, prompt: {prompt}")
                image_urls = await sora_client.generate_image_remix(
                    prompt=prompt,
                    media_id=media_id,
                    num_images=num_images
                )
                
            finally:
                # Clean up temporary files
                if os.path.exists(temp_image_path):
                    os.remove(temp_image_path)
                if os.path.exists(temp_dir):
                    os.rmdir(temp_dir)
        else:
            raise ValueError(f"Unknown task type: {task_type}")
        
        # Validate generation results
        if isinstance(image_urls, str):
            logger.warning(f"[{request_id}] Image generation failed or returned an error message: {image_urls}")
            generation_results[request_id] = {
                "status": "failed",
                "error": image_urls,
                "message": format_think_block(f"Image generation failed: {image_urls}"),
                "timestamp": int(time.time()),
                "api_key": current_api_key
            }
            return
            
        if not image_urls:
            logger.warning(f"[{request_id}] Image generation returned an empty list")
            generation_results[request_id] = {
                "status": "failed",
                "error": "Image generation returned empty result",
                "message": format_think_block("Image generation failed: server returned empty result"),
                "timestamp": int(time.time()),
                "api_key": current_api_key
            }
            return
            
        logger.info(f"[{request_id}] Successfully generated {len(image_urls)} image(s)")
        
        # Localize image URLs if enabled
        if Config.IMAGE_LOCALIZATION:
            logger.info(f"[{request_id}] Preparing to localize image URLs")
            try:
                localized_urls = await localize_image_urls(image_urls)
                logger.info(f"[{request_id}] Image URL localization completed")
                
                # Check localization results
                if not localized_urls:
                    logger.warning(f"[{request_id}] Localization returned an empty list, using original URLs")
                    localized_urls = image_urls
                
                # Check how many URLs were localized
                local_count = sum(1 for url in localized_urls if url.startswith("/static/") or "/static/" in url)
                logger.info(f"[{request_id}] Localization result: total {len(localized_urls)} images, successfully localized {local_count}")
                
                if local_count == 0:
                    logger.warning(f"[{request_id}] Warning: none of the URLs were localized, using original URLs")
                    localized_urls = image_urls
                
                image_urls = localized_urls
            except Exception as e:
                logger.error(f"[{request_id}] Error during image URL localization: {str(e)}", exc_info=True)
                logger.info(f"[{request_id}] Using original URLs due to error")
        else:
            logger.info(f"[{request_id}] Image localization feature is disabled, using original URLs")
        
        # Store results
        generation_results[request_id] = {
            "status": "completed",
            "image_urls": image_urls,
            "timestamp": int(time.time()),
            "api_key": current_api_key
        }
        
        # Auto-clean results after 30 minutes
        def cleanup_task():
            generation_results.pop(request_id, None)
            task_to_api_key.pop(request_id, None)
            
        threading.Timer(1800, cleanup_task).start()
        
    except Exception as e:
        error_message = f"Image generation failed: {str(e)}"
        generation_results[request_id] = {
            "status": "failed",
            "error": error_message,
            "message": format_think_block(error_message),
            "timestamp": int(time.time()),
            "api_key": sora_client.auth_token  # record current API key
        }
        logger.error(f"Image generation failed (ID: {request_id}): {str(e)}", exc_info=True)

def get_generation_result(request_id: str) -> Dict[str, Any]:
    """Get generation result by request ID"""
    if request_id not in generation_results:
        return {
            "status": "not_found",
            "error": f"Generation task not found: {request_id}",
            "timestamp": int(time.time())
        }
    
    return generation_results[request_id]

def get_task_api_key(request_id: str) -> Optional[str]:
    """Get the API key used by a specific request/task"""
    return task_to_api_key.get(request_id)