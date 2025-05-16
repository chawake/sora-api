import asyncio
import concurrent.futures
from typing import List, Dict, Any, Optional, Union
import json
import os
import base64
import tempfile
import uuid

# 导入原有的SoraImageGenerator类
from .sora_generator import SoraImageGenerator

class SoraClient:
    def __init__(self, proxy_host=None, proxy_port=None, proxy_user=None, proxy_pass=None, auth_token=None):
        """初始化Sora客户端，使用cloudscraper绕过CF验证"""
        self.generator = SoraImageGenerator(
            proxy_host=proxy_host, 
            proxy_port=proxy_port,
            proxy_user=proxy_user,
            proxy_pass=proxy_pass,
            auth_token=auth_token
        )
        # 保存原始的auth_token，用于检测是否已更新
        self.auth_token = auth_token
        # 创建线程池执行器
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
        
    async def generate_image(self, prompt: str, num_images: int = 1, 
                           width: int = 720, height: int = 480) -> List[str]:
        """异步包装SoraImageGenerator.generate_image方法"""
        loop = asyncio.get_running_loop()
        # 使用线程池执行同步方法（因为cloudscraper不是异步的）
        result = await loop.run_in_executor(
            self.executor, 
            lambda: self.generator.generate_image(prompt, num_images, width, height)
        )
        
        # 检查generator中的auth_token是否已经被更新（由自动切换密钥机制）
        if self.generator.auth_token != self.auth_token:
            self.auth_token = self.generator.auth_token
        
        if isinstance(result, list):
            return result
        else:
            raise Exception(f"图像生成失败: {result}")
    
    async def upload_image(self, image_path: str) -> Dict:
        """异步包装上传图片方法"""
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            self.executor,
            lambda: self.generator.upload_image(image_path)
        )
        
        # 检查generator中的auth_token是否已经被更新
        if self.generator.auth_token != self.auth_token:
            self.auth_token = self.generator.auth_token
        
        if isinstance(result, dict) and 'id' in result:
            return result
        else:
            raise Exception(f"图片上传失败: {result}")
            
    async def generate_image_remix(self, prompt: str, media_id: str, 
                                 num_images: int = 1) -> List[str]:
        """异步包装remix方法"""
        loop = asyncio.get_running_loop()
        
        # 处理可能包含API密钥信息的media_id对象
        if isinstance(media_id, dict) and 'id' in media_id:
            # 如果上传时使用的密钥与当前不同，则先切换密钥
            if 'used_auth_token' in media_id and media_id['used_auth_token'] != self.auth_token:
                self.auth_token = media_id['used_auth_token']
                # 同步更新generator的auth_token
                self.generator.auth_token = self.auth_token
            # 提取实际的media_id
            media_id = media_id['id']
            
        result = await loop.run_in_executor(
            self.executor,
            lambda: self.generator.generate_image_remix(prompt, media_id, num_images)
        )
        
        # 检查generator中的auth_token是否已经被更新
        if self.generator.auth_token != self.auth_token:
            self.auth_token = self.generator.auth_token
        
        if isinstance(result, list):
            return result
        else:
            raise Exception(f"Remix生成失败: {result}")
            
    async def test_connection(self) -> Dict:
        """测试API连接是否有效"""
        try:
            # 简单测试上传功能，这个方法会调用API但不会真正上传文件
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                self.executor,
                lambda: self.generator.test_connection()
            )
            
            # 检查generator中的auth_token是否已经被更新
            if self.generator.auth_token != self.auth_token:
                self.auth_token = self.generator.auth_token
            
            # 直接返回generator.test_connection的结果，保留所有信息
            return result
        except Exception as e:
            return {"status": "error", "message": f"API连接测试失败: {str(e)}"}
            
    def close(self):
        """关闭线程池"""
        self.executor.shutdown(wait=False) 