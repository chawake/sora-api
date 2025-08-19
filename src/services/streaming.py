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
    Streaming response generator for text-to-image
    
    Args:
        sora_client: Sora client
        prompt: Prompt text
        n_images: Number of images to generate
    
    Yields:
        SSE-formatted response data
    """
    request_id = f"chatcmpl-stream-{time.time()}-{hash(prompt) % 10000}"
    
    # Send start event
    yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]})}\n\n"
    
    # Send processing message (inside a code block)
    start_msg = "```think\nGenerating images, please wait...\n"
    yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': start_msg}, 'finish_reason': None}]})}\n\n"
    
    # Create a background task to generate images
    logger.info(f"[Streaming {request_id}] Start generating images, prompt: {prompt}")
    generation_task = asyncio.create_task(sora_client.generate_image(
        prompt=prompt,
        num_images=n_images,
        width=720,
        height=480
    ))
    
    # Send a "still generating" message every 5 seconds to prevent connection timeout
    progress_messages = [
        "Processing your request...",
        "Still generating images, please keep waiting...",
        "Sora is creating your images...",
        "Image generation takes a bit of time, thanks for your patience...",
        "We are working to create high-quality images for you..."
    ]
    
    i = 0
    while not generation_task.done():
        # Send progress message every 5 seconds
        await asyncio.sleep(5)
        progress_msg = progress_messages[i % len(progress_messages)]
        i += 1
        content = "\n" + progress_msg + "\n"
        yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': content}, 'finish_reason': None}]})}\n\n"
    
    try:
        # Get generation results
        image_urls = await generation_task
        logger.info(f"[Streaming {request_id}] Image generation completed, obtained {len(image_urls) if isinstance(image_urls, list) else 'non-list'} URLs")
        
        # Localize image URLs if enabled
        if Config.IMAGE_LOCALIZATION and isinstance(image_urls, list) and image_urls:
            logger.info(f"[Streaming {request_id}] Preparing to localize image URLs")
            try:
                localized_urls = await localize_image_urls(image_urls)
                image_urls = localized_urls
                logger.info(f"[Streaming {request_id}] Image URL localization completed")
            except Exception as e:
                logger.error(f"[Streaming {request_id}] Error during image URL localization: {str(e)}", exc_info=True)
                logger.info(f"[Streaming {request_id}] Using original URLs due to error")
        elif not Config.IMAGE_LOCALIZATION:
            logger.info(f"[Streaming {request_id}] Image localization feature is disabled")
        
        # End the code block
        content_str = "\n```\n\n"
        yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': content_str}, 'finish_reason': None}]})}\n\n"
        
        # Append generated image URLs
        for i, url in enumerate(image_urls):
            if i > 0:
                content_str = "\n\n"
                yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': content_str}, 'finish_reason': None}]})}\n\n"
            
            image_markdown = f"![Generated Image]({url})"
            yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': image_markdown}, 'finish_reason': None}]})}\n\n"
        
        # Send completion event
        yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
        
        # Send end marker
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        error_msg = f"Image generation failed: {str(e)}"
        logger.error(f"[Streaming {request_id}] Error: {error_msg}", exc_info=True)
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
    Streaming response generator for image-to-image (Remix)
    
    Args:
        sora_client: Sora client
        prompt: Prompt text
        image_data: Base64-encoded image data
        n_images: Number of images to generate
    
    Yields:
        SSE-formatted response data
    """
    import os
    import tempfile
    import uuid
    import base64
    
    request_id = f"chatcmpl-stream-remix-{time.time()}-{hash(prompt) % 10000}"
    
    # Send start event
    yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]})}\n\n"
    
    try:
        # Save base64 image to a temporary file
        temp_dir = tempfile.mkdtemp()
        temp_image_path = os.path.join(temp_dir, f"upload_{uuid.uuid4()}.png")
        
        try:
            # Decode and save image
            with open(temp_image_path, "wb") as f:
                f.write(base64.b64decode(image_data))
            
            # Upload image
            upload_msg = "```think\nUploading image...\n"
            yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': upload_msg}, 'finish_reason': None}]})}\n\n"
            
            logger.info(f"[Streaming Remix {request_id}] Uploading image")
            upload_result = await sora_client.upload_image(temp_image_path)
            media_id = upload_result['id']
            
            # Send generating message
            generate_msg = "\nGenerating new images based on the uploaded image...\n"
            yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': generate_msg}, 'finish_reason': None}]})}\n\n"
            
            # Create a background task to generate images
            logger.info(f"[Streaming Remix {request_id}] Start generating images, prompt: {prompt}")
            generation_task = asyncio.create_task(sora_client.generate_image_remix(
                prompt=prompt,
                media_id=media_id,
                num_images=n_images
            ))
            
            # Send a "still generating" message every 5 seconds
            progress_messages = [
                "Processing your request...",
                "Still generating images, please keep waiting...",
                "Sora is creating new images based on your picture...",
                "Image generation takes a bit of time, thanks for your patience...",
                "Blending your style and prompt to craft tailored images..."
            ]
            
            i = 0
            while not generation_task.done():
                await asyncio.sleep(5)
                progress_msg = progress_messages[i % len(progress_messages)]
                i += 1
                content = "\n" + progress_msg + "\n"
                yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': content}, 'finish_reason': None}]})}\n\n"
            
            # Get generation results
            image_urls = await generation_task
            logger.info(f"[Streaming Remix {request_id}] Image generation completed")
            
            # Localize image URLs if enabled
            if Config.IMAGE_LOCALIZATION:
                logger.info(f"[Streaming Remix {request_id}] Performing image URL localization")
                localized_urls = await localize_image_urls(image_urls)
                image_urls = localized_urls
                logger.info(f"[Streaming Remix {request_id}] Image URL localization completed")
            else:
                logger.info(f"[Streaming Remix {request_id}] Image localization feature is disabled")
            
            # End the code block
            content_str = "\n```\n\n"
            yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': content_str}, 'finish_reason': None}]})}\n\n"
            
            # Send image URLs as Markdown
            for i, url in enumerate(image_urls):
                if i > 0:
                    newline_str = "\n\n"
                    yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': newline_str}, 'finish_reason': None}]})}\n\n"
                
                image_markdown = f"![Generated Image]({url})"
                yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': image_markdown}, 'finish_reason': None}]})}\n\n"
            
            # Send completion event
            yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}]})}\n\n"
            
            # Send end marker
            yield "data: [DONE]\n\n"
            
        finally:
            # Clean up temporary files
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
                
    except Exception as e:
        error_msg = f"Image remix failed: {str(e)}"
        logger.error(f"[Streaming Remix {request_id}] Error: {error_msg}", exc_info=True)
        error_content = f"\n{error_msg}\n```"
        yield f"data: {json.dumps({'id': request_id, 'object': 'chat.completion.chunk', 'created': int(time.time()), 'model': 'sora-1.0', 'choices': [{'index': 0, 'delta': {'content': error_content}, 'finish_reason': 'error'}]})}\n\n"
    
    # End of stream
    yield "data: [DONE]\n\n"