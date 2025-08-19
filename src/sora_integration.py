import asyncio
import concurrent.futures
from typing import List, Dict, Any, Optional, Union
import json
import os
import base64
import tempfile
import uuid
 
# Import the original SoraImageGenerator class
from .sora_generator import SoraImageGenerator

class SoraClient:
    def __init__(self, proxy_host=None, proxy_port=None, proxy_user=None, proxy_pass=None, auth_token=None):
        """Initialize Sora client, using cloudscraper to bypass CF verification"""
        self.generator = SoraImageGenerator(
            proxy_host=proxy_host, 
            proxy_port=proxy_port,
            proxy_user=proxy_user,
            proxy_pass=proxy_pass,
            auth_token=auth_token
        )
        # Save the original auth_token to detect if it has been updated
        self.auth_token = auth_token
        # Create a thread pool executor
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
        
    async def generate_image(self, prompt: str, num_images: int = 1, 
                           width: int = 720, height: int = 480) -> List[str]:
        """Asynchronous wrapper for SoraImageGenerator.generate_image method"""
        loop = asyncio.get_running_loop()
        # Use thread pool to execute synchronous methods (since cloudscraper is not async)
        result = await loop.run_in_executor(
            self.executor, 
            lambda: self.generator.generate_image(prompt, num_images, width, height)
        )
        
        # Check if the auth_token in the generator has been updated (by the automatic key switching mechanism)
        if self.generator.auth_token != self.auth_token:
            self.auth_token = self.generator.auth_token
        
        if isinstance(result, list):
            return result
        else:
            raise Exception(f"Image generation failed: {result}")
    
    async def upload_image(self, image_path: str) -> Dict:
        """Asynchronous wrapper for upload image method"""
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            self.executor,
            lambda: self.generator.upload_image(image_path)
        )
        
        # Check if the auth_token in the generator has been updated
        if self.generator.auth_token != self.auth_token:
            self.auth_token = self.generator.auth_token
        
        if isinstance(result, dict) and 'id' in result:
            return result
        else:
            raise Exception(f"Image upload failed: {result}")
            
    async def generate_image_remix(self, prompt: str, media_id: str, 
                                 num_images: int = 1) -> List[str]:
        """Asynchronous wrapper for remix method"""
        loop = asyncio.get_running_loop()
        
        # Handle media_id object that might contain API key information
        if isinstance(media_id, dict) and 'id' in media_id:
            # If the key used for upload is different from the current one, switch keys first
            if 'used_auth_token' in media_id and media_id['used_auth_token'] != self.auth_token:
                self.auth_token = media_id['used_auth_token']
                # Synchronize the generator's auth_token
                self.generator.auth_token = self.auth_token
            # Extract the actual media_id
            media_id = media_id['id']
            
        result = await loop.run_in_executor(
            self.executor,
            lambda: self.generator.generate_image_remix(prompt, media_id, num_images)
        )
        
        # Check if the auth_token in the generator has been updated
        if self.generator.auth_token != self.auth_token:
            self.auth_token = self.generator.auth_token
        
        if isinstance(result, list):
            return result
        else:
            raise Exception(f"Remix generation failed: {result}")
            
    async def test_connection(self) -> Dict:
        """Test if the API connection is valid"""
        try:
            # Simple test of upload functionality, this method will call the API but won't actually upload files
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.generator.test_connection()
            )
            
            # Check if the auth_token in the generator has been updated
            if self.generator.auth_token != self.auth_token:
                self.auth_token = self.generator.auth_token
            
            # Return the result of generator.test_connection directly, preserving all information
            return result
        except Exception as e:
            return {"status": "error", "message": f"API connection test failed: {str(e)}"}
            
    def close(self):
        """Shut down the thread pool"""
        self.executor.shutdown(wait=False) 