import cloudscraper
import time
import json
import random
import string
import os
import mimetypes # To guess file mime type
import argparse # For better command-line arguments
import asyncio
from .utils import localize_image_urls
from .config import Config

class SoraImageGenerator:
    def __init__(self, proxy_host=None, proxy_port=None, proxy_user=None, proxy_pass=None, auth_token=None):
        # 使用Config.VERBOSE_LOGGING替代直接从环境变量读取SORA_DEBUG
        self.DEBUG = Config.VERBOSE_LOGGING
        
        # 设置代理
        if proxy_host and proxy_port:
            # 如果有认证信息，添加到代理URL中
            if proxy_user and proxy_pass:
                proxy_auth = f"{proxy_user}:{proxy_pass}@"
                self.proxies = {
                    "http": f"http://{proxy_auth}{proxy_host}:{proxy_port}",
                    "https": f"http://{proxy_auth}{proxy_host}:{proxy_port}"
                }
                if self.DEBUG:
                    print(f"已配置带认证的代理: {proxy_user}:****@{proxy_host}:{proxy_port}")
            else:
                self.proxies = {
                    "http": f"http://{proxy_host}:{proxy_port}",
                    "https": f"http://{proxy_host}:{proxy_port}"
                }
                if self.DEBUG:
                    print(f"已配置代理: {proxy_host}:{proxy_port}")
        else:
            self.proxies = None
            if self.DEBUG:
                print("代理未配置。请求将直接发送。")
        # 创建 cloudscraper 实例
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        # 设置通用请求头 - 移除 Content-Type 和 openai-sentinel-token (会动态添加)
        self.base_headers = {
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "sec-ch-ua": "\"Chromium\";v=\"136\", \"Google Chrome\";v=\"136\", \"Not.A/Brand\";v=\"99\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            # Referer 会根据操作不同设置
        }
        # 设置认证Token (从外部传入或硬编码)
        self.auth_token = auth_token or "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjE5MzQ0ZTY1LWJiYzktNDRkMS1hOWQwLWY5NTdiMDc5YmQwZSIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS92MSJdLCJjbGllbnRfaWQiOiJhcHBfWDh6WTZ2VzJwUTl0UjNkRTduSzFqTDVnSCIsImV4cCI6MTc0Nzk3MDExMSwiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS9hdXRoIjp7InVzZXJfaWQiOiJ1c2VyLWdNeGM0QmVoVXhmTW1iTDdpeUtqengxYiJ9LCJodHRwczovL2FwaS5vcGVuYWkuY29tL3Byb2ZpbGUiOnsiZW1haWwiOiIzajVtOTFud3VtckBmcmVlLnViby5lZHUuZ24iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZX0sImlhdCI6MTc0NzEwNjExMSwiaXNzIjoiaHR0cHM6Ly9hdXRoLm9wZW5haS5jb20iLCJqdGkiOiIzMGM4ZDJhOS0yNzkxLTRhNjQtODI2OS0yMzU3OGFhMmI0MTEiLCJuYmYiOjE3NDcxMDYxMTEsInB3ZF9hdXRoX3RpbWUiOjE3NDcxMDYxMDkxMDksInNjcCI6WyJvcGVuaWQiLCJlbWFpbCIsInByb2ZpbGUiLCJvZmZsaW5lX2FjY2VzcyIsIm1vZGVsLnJlcXVlc3QiLCJtb2RlbC5yZWFkIiwib3JnYW5pemF0aW9uLnJlYWQiLCJvcmdhbml6YXRpb24ud3JpdGUiXSwic2Vzc2lvbl9pZCI6ImF1dGhzZXNzX21yWFRwZlVENU51TDFsV05xNUhSOW9lYiIsInN1YiI6ImF1dGgwfDY4MjFkYWYyNjhiYjgxMzFkMDRkYTAwNCJ9.V4ZqYJuf_f7F_DrMMRrt-ymul5HUrqENVkiFyEwfYmzMFWthEGS6Ryia100QRlprw8jjGscHZXlUFaOcRNIarcBig8fBY6n_AB3J34MlcBv6peS-3_EJlIiH_N7j_mu-8lNpJbxk9lSlFaGpKU1IOO7kBuaAmLH-iErM-wqBfSlnnAq8h4iqBDxi4CMTcAhVm2-qG7u7f0Ho1TCGa7wrdchWtZxyfHIqNWkC88qBlUwTH5g2vRL419_zIKEWKyAtV2WNI68vpyBLrRVhtnpDh0jcrm2WqCj2X2LQqNFkFKoui3wCdG9Vskpl39l9sV54HuV7w6stQIausR1F4Y9NbjsBAyLIimZOllCwYAefTC2BOpIHfOA3_D58G3SEiRADVK7pK7ip6QsEI__GteoeCuRvZA9b5jLmhVS0SUlDYSOoNwlJ_ejfEpPJcmHUchFa7bUkS-XVrEUgr1yP5FxPwWUyn7UWrW_dZ3lVW1EU4Bp6Kp6JuwyOFf2Mj-V3_9tc8qJRClI8WHUf6In0hiO_pGbFCI2opkF3XusAQKmTB12nPBsmSlwewigTPhAj3nf-8Ze3O-etnBrV5pz_woIwQsQ54T-wgEdrLWDE6dSqNDulfpldF6Cok62212kW8w3SY3V7VSq5Tr1KRyWXJEH-haVb6qmAE2ldDjeHvJossWg" # 替换成你的有效Token或从环境变量读取
        if not self.auth_token or not self.auth_token.startswith("Bearer "):
            raise ValueError("无效或缺失的认证Token (应以 'Bearer ' 开头)")
        self.gen_url = "https://sora.chatgpt.com/backend/video_gen"
        self.check_url = "https://sora.chatgpt.com/backend/video_gen"
        self.upload_url = "https://sora.chatgpt.com/backend/uploads"
        
        # 显示是否启用了图片本地化功能
        if Config.IMAGE_LOCALIZATION:
            if self.DEBUG:
                print(f"图片本地化功能已启用，图片将保存到：{Config.IMAGE_SAVE_DIR}")
            os.makedirs(Config.IMAGE_SAVE_DIR, exist_ok=True)
    
    def _get_dynamic_headers(self, content_type="application/json", referer="https://sora.chatgpt.com/explore"):
        """为每个请求生成包含动态sentinel token的headers"""
        headers = self.base_headers.copy()
        headers["authorization"] = self.auth_token
        headers["openai-sentinel-token"] = self._generate_sentinel_token()
        headers["referer"] = referer
        if content_type: # multipart/form-data 时 Content-Type 由 requests 自动设置
            headers["content-type"] = content_type
        return headers
    
    def _generate_sentinel_token(self):
        """生成一个随机修改的sentinel-token"""
        base_token = {
            "p": "gAAAAABWzIxMjksIk1vbiBNYXkgMTIgMjAyNSAxODo1ODowOSBHTVQrMDgwMCAo5Lit5Zu95qCH5YeG5pe26Ze0KSIsMjI0ODE0Njk0NCw5LCJNb3ppbGxhLzUuMCAoV2luZG93cyBOVCAxMC4wOyBXaW42NDsgeDY0KSBBcHBsZVdlYktpdC81MzcuMzYgKEtIVE1MLCBsaWtlIEdlY2tvKSBDaHJvbWUvMTM2LjAuMC4wIFNhZmFyaS81MzcuMzYiLCJodHRwczovL3NvcmEtY2RuLm9haXN0YXRpYy5jb20vX25leHQvc3RhdGljL2NodW5rcy93ZWJwYWNrLWU1MDllMDk0N2RlZWM0Y2YuanMiLG51bGwsInpoLUNOIiwiemgtQ04semgiLDEwLCJwcm9kdWN0U3Vi4oiSMjAwMzAxMDciLCJfcmVhY3RMaXN0ZW5pbmd2cXAzdWtpNmh6IiwiX19zZW50aW5lbF9pbml0X3BlbmRpbmciLDEyMDczMzEuNSwiN2M4OTMxM2EtZTY0Mi00MjI4LTk5ZDQtNTRlZDRjYzQ3MGZiIiwiIiwxNl0=",
            "t": "SBYdBBoGFhQRdVtbdxEYEQEaHQAAFhQRYwN2T2IEUH5pRHJyYx51YnJybFBhWHZkYgRyUHgDclZzH2l5a1gXUWVlcRMRGBEBHR0HBBYUEXpnfVt9YFAJDB8WAAIAAgYRDgxpYltjSl55SWJEZV9mXx4KFh8WGAAaBxYUEXVydW9ydXJ1b3J1cnVvcnVydW9ydXJ1b3J1b3J1b3J1b3J1DgkMHxYBAgALAxEOHh0BBwIXCwwEBx8FAwADGwAAHxYcBxoFDQwJFnFDEw4WHxYXBxoCBwwJFmB2dGRxYgBqdHVLf2hUX3VySWpVcVNNa3ZiYW13dgtyb3J5cHxvam12YWB7YgN2THVcYnxsSwR7fH9mfHJlZ1F3VARtcVwLcGpiV2pwaEdmZFhgdGZLbWRxXAdQbHJ5dHNvanlwQ29Xd1QEZnFmXFJoWFBRbEZ2e3JTWVF8YnFvd2ZUd2xiR3Vzb1BxcWV3UXxLbmxrYV9Wf3FxfHNJclVydU1qdXJtaHJmUH9sYnF1fElcdXtMdH5sdnZmZAR+ZmpUcXZzVgN2cUN3UHZyZWhyXAd8bHJ5cnVGdW1lWGRScWIAamBlDgkMHxYKBgADDREODHZjcWx/AnIBZkJLV2FTRWZWZX5Pa2JHVWsDbmRie1xgYXFoUWxfbmlhBQJ4f3FmUGFJBnNkWEphZ3VET2VYcntpA25kYntDVWRYf2Z3ZXZ9Vl9hXXZ1RGZseENzZnJ3Z3YCdn1WX2FddnVEZmx4Q3NmcndkFh8WFwAaBAUMCRZrcnh7fF92T2Z1eXx2dW5pZ1YKXGIFRnFhX3ZAZmJLUXwAfmtgeGlxYQVoeFdYdU1iYgJjfFsBAVJ7YUxrB1ZDVUR+fGthcXN4ZkRrbH9lWmtsG0FiAkdIZHFXZnxffnRiVgZsa3JeUmVlQEhhQ31ybFsNZ2VCS2NmWEZFZlhMWWQEcWJ2ZWZdZx5XdWRYXnllcVxJanMKWnQARElXdgoDUHx4WlZ0UEBWB0tNTQBuQW4dAlNXWXRUV11cXWkHQwx0XW5BUW9QbWVyRnFhZWJIVwR1UHtfRGdSeGl1YQUfcmJ2V0h3Zgd4bFR9cWdCUHFmZU1qd199amVDeQx5X3JRYB51ZWRYXnlSZHJcdAVHdXtmcWlWaXFwV1hGXlB0Q2hlX1dQf2V+fWB7cndqcl5YUF92TXRxV3V3AkBXY0JpbWRfSlJ8AgVLZGFHdnwCRHBnHFdzZlheV2wCYmZmbAZjfF9iUWxoBmJrYkp/UAJiZmVleXB4ZWZhdR9HYmJ2Qn5iX3JKdGFbV3xfdmF1HnVmZWF0f2V1THlmdXlTd3t+VFJ2Q05RfEZbV3tiAVIHAlpLAXICVXZpRmpzbEVXa1wcUgZXBwxO",
            "c": "gAAAAABoIdRAZEk6qAnDRqdimKxPhXtA_xBkiDXhKF4LUmlNY6CZmfNxZiabjPHk_DCEUnnyq-y6JPj-D46YPk-6r7zR6qS64hEwGYt9Hh_8vUIod-7PLh9qPKqdYl4TBCVUgtrbhTWfse7s6NHCSy1T0Nzj2C6vAUPhzAx4LAMIrl2YbElkUVPgwELyYF_inh3zliwZL-zp4zR3LOABcrGqlrLoP7_kNrwcIZwlVD1RNlnHy9TEFsRzYOMQo_DbagZAK1h87arrMonZHBi9ukfiGuvCQP-y76j61b4qaQPMA19EoURLwnotVBWUIBpHEEoH9vmPb817sGwQ2R8XHoAVR4dwYs_7EoS8H8kAlUVZDjAKGq5x48nvZrarLBjYJXXsfJLuxhibNYXG1hKNbOdi1w-Xl1NgqSPAb-MuwnyDLPGE5MeLkwM2Dl3jD7G6B2Z2F993cvW7mOOs0OebZ6NMgIrZnTG4mMI7PirPY95JWmztDfeuFLJ_V_kyaSP--BZCIIAB4074RBVitIrJEwceWVW3zXOOHWJoDax7E0nfa5abvLGCjdEeJfNx4Fcp7iYFN_E8iR0f797DLlFh4uFLv1DPhipYtQFpPPUlbxKu9H9W4IDr7Hv_LgfvFo0VwLzV6ANZPGmdza67dAsKXrWtXlCrVNfqFoVO4wI4n-zrE3lcUPzI_ZJebF2HGlzerTvqgU5R0i4fzUGY4-UqpWlVurP-rCJY2ARcSMSyPXnPGetl5Z2m-f9k7K3n7txrfv2293jyyRTVAZLC9aLrBOFWHD4cf0aiwisgJ9IKnhhnoJ-WF8NuvFS7l1Z0d2zTnndjuryb0M36Og4b_Ku3aJKS0_Eqbns8_bUXdEPh5_15T_92_1yf5jy-amrgolgcO_7yJqX5aU9-PUUiaP3WzeyidMSH4Vtls63tQ5evUlDkEHfNKoyCYaSxpzA_FsNmPbMmcv3g1wNKg_W8V0Yh7ZrtW1L8229SpZFWc96Sg3CRPplk-dnVzV93lP7cN5o5ubGWZMkkz5UASjE5XLn8h5dx6neuOemKVHAj29QxOWmdGEehNvmeMec0k8uL9X-7yYBJSTnI066OR38JUUTFqTH3RSXI9M4ggals32P56bwUmawvZ-bu02qc3kCVI3oK9bnP8oTk0xTK5_bMrlevGYKG0qdPXamgdDfVg7hlNA2OTCnw6iRP6DJiPm_zKVdQa4z6SPJsdt_Q",
            "id": self._generate_random_id(),
            "flow": "sora_create_task" # This might need changing for uploads? Let's try keeping it.
        }
        # Simple randomization (can be improved if needed)
        p_chars = list(base_token["p"])
        for _ in range(random.randint(3, 7)):
            pos = random.randint(10, len(p_chars) - 10)
            p_chars[pos] = random.choice(string.ascii_letters + string.digits + "+/=")
        base_token["p"] = "".join(p_chars)
        c_chars = list(base_token["c"])
        for _ in range(random.randint(3, 7)):
            pos = random.randint(10, len(c_chars) - 10)
            c_chars[pos] = random.choice(string.ascii_letters + string.digits + "+/=_-")
        base_token["c"] = "".join(c_chars)
        return json.dumps(base_token)
    
    def _generate_random_id(self):
        """生成一个随机ID，格式类似于UUID"""
        return f"{self._random_hex(8)}-{self._random_hex(4)}-{self._random_hex(4)}-{self._random_hex(4)}-{self._random_hex(12)}"
    
    def _random_hex(self, length):
        """生成指定长度的随机十六进制字符串"""
        return ''.join(random.choice(string.hexdigits.lower()) for _ in range(length))
    
    def generate_image(self, prompt, num_images=1, width=720, height=480):
        """
        生成一张或多张图片并返回图片URL列表
        参数:
        prompt (str): 图片生成提示词
        num_images (int): 要生成的图片数量 (对应 n_variants)
        width (int): 图片宽度
        height (int): 图片高度
        返回:
        list[str] or str: 成功时返回包含图片URL的列表，失败时返回错误信息字符串
        """
        # 确保提示词是正确的UTF-8格式
        if isinstance(prompt, bytes):
            prompt = prompt.decode('utf-8')
        
        # 打印提示词，并处理可能的编码问题
        try:
            if self.DEBUG:
                print(f"开始生成 {num_images} 张图片，提示词: '{prompt}'")
        except UnicodeEncodeError:
            if self.DEBUG:
                print(f"开始生成 {num_images} 张图片，提示词: [编码显示问题，但数据正确]")
        
        payload = {
            "type": "image_gen",
            "operation": "simple_compose",
            "prompt": prompt,
            "n_variants": num_images, # 使用传入的数量
            "width": width,
            "height": height,
            "n_frames": 1,
            "inpaint_items": []
        }
        try:
            task_id = self._submit_task(payload, referer="https://sora.chatgpt.com/explore")
            if not task_id:
                # 任务提交失败，尝试切换密钥后重试
                if self.DEBUG:
                    print(f"任务提交失败，尝试切换API密钥后重试")
                
                try:
                    # 导入在这里进行以避免循环导入
                    from .key_manager import key_manager
                    # 标记当前密钥为无效并获取新密钥
                    new_key = key_manager.mark_key_invalid(self.auth_token)
                    if new_key:
                        self.auth_token = new_key
                        if self.DEBUG:
                            print(f"已切换到新的API密钥，重试任务")
                        # 使用新密钥重试提交任务
                        task_id = self._submit_task(payload, referer="https://sora.chatgpt.com/explore")
                        if not task_id:
                            return "任务提交失败（已尝试切换密钥）"
                    else:
                        return "任务提交失败（无可用的备用密钥）"
                except ImportError:
                    if self.DEBUG:
                        print(f"无法导入key_manager，无法自动切换密钥")
                    return "任务提交失败"
                except Exception as e:
                    if self.DEBUG:
                        print(f"切换API密钥时发生错误: {str(e)}")
                    return f"任务提交失败: {str(e)}"
            
            if self.DEBUG:
                print(f"任务已提交，ID: {task_id}")
            # 轮询检查任务状态，直到完成
            image_urls = self._poll_task_status(task_id)
            
            # 如果轮询返回错误信息，也尝试切换密钥重试
            if isinstance(image_urls, str) and ("失败" in image_urls or "错误" in image_urls or "error" in image_urls.lower()):
                if self.DEBUG:
                    print(f"任务执行失败，尝试切换API密钥后重试")
                
                try:
                    from .key_manager import key_manager
                    new_key = key_manager.mark_key_invalid(self.auth_token)
                    if new_key:
                        self.auth_token = new_key
                        if self.DEBUG:
                            print(f"已切换到新的API密钥，重试整个生成过程")
                        # 使用新密钥重试整个生成过程
                        return self.generate_image(prompt, num_images, width, height)
                except (ImportError, Exception) as e:
                    if self.DEBUG:
                        print(f"切换API密钥失败或重试失败: {str(e)}")
            
            # 图片本地化处理
            if Config.IMAGE_LOCALIZATION and isinstance(image_urls, list) and image_urls:
                if self.DEBUG:
                    print(f"\n================================")
                    print(f"开始图片本地化处理")
                    print(f"图片本地化配置: 启用={Config.IMAGE_LOCALIZATION}, 保存目录={Config.IMAGE_SAVE_DIR}")
                    print(f"需要本地化的图片数量: {len(image_urls)}")
                    print(f"原始图片URLs: {image_urls}")
                    print(f"================================\n")
                
                try:
                    # 创建事件循环并运行图片本地化
                    if self.DEBUG:
                        print(f"创建异步事件循环处理图片下载...")
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    if self.DEBUG:
                        print(f"调用localize_image_urls函数...")
                    localized_urls = loop.run_until_complete(localize_image_urls(image_urls))
                    loop.close()
                    if self.DEBUG:
                        print(f"异步事件循环已关闭")
                    
                    if self.DEBUG:
                        print(f"\n================================")
                        print(f"图片本地化完成")
                        print(f"原始URLs: {image_urls}")
                        print(f"本地化后的URLs: {localized_urls}")
                        print(f"================================\n")
                    
                    # 检查结果是否有效
                    if not localized_urls:
                        if self.DEBUG:
                            print(f"❌ 警告：本地化后的URL列表为空，将使用原始URL")
                        return image_urls
                        
                    # 检查是否所有URL都被正确本地化
                    local_count = sum(1 for url in localized_urls if url.startswith("/static/") or "/static/" in url)
                    if local_count == 0:
                        if self.DEBUG:
                            print(f"❌ 警告：没有一个URL被成功本地化，将使用原始URL")
                        return image_urls
                    elif local_count < len(localized_urls):
                        if self.DEBUG:
                            print(f"⚠️ 注意：部分URL未成功本地化 ({local_count}/{len(localized_urls)})")
                        
                    return localized_urls
                except Exception as e:
                    if self.DEBUG:
                        print(f"❌ 图片本地化过程中发生错误: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    if self.DEBUG:
                        print(f"由于错误，将返回原始URL")
                    return image_urls
            elif not Config.IMAGE_LOCALIZATION:
                if self.DEBUG:
                    print(f"图片本地化功能未启用，返回原始URLs")
            elif not isinstance(image_urls, list):
                if self.DEBUG:
                    print(f"图片生成返回了非列表结果: {image_urls}，无法进行本地化")
            elif not image_urls:
                if self.DEBUG:
                    print(f"图片生成返回了空列表，没有可本地化的内容")
            
            return image_urls
        except Exception as e:
            if self.DEBUG:
                print(f"❌ 生成图片时出错: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"生成图片时出错: {str(e)}"
    
    def upload_image(self, file_path):
        """
        上传本地图片文件到Sora后端
        参数:
        file_path (str): 本地图片文件的路径
        返回:
        dict or str: 成功时返回包含上传信息的字典，失败时返回错误信息字符串
        """
        if not os.path.exists(file_path):
            return f"错误：文件未找到 '{file_path}'"
        file_name = os.path.basename(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type or not mime_type.startswith('image/'):
            return f"错误：无法确定文件类型或文件不是图片 '{file_path}' (Mime: {mime_type})"
        if self.DEBUG:
            print(f"开始上传图片: {file_name} (Type: {mime_type})")
        # multipart/form-data 请求不需要手动设置 Content-Type header
        # requests 会根据 files 参数自动处理 boundary 和 Content-Type
        headers = self._get_dynamic_headers(content_type=None, referer="https://sora.chatgpt.com/library") # Referer from example
        
        # 尝试上传
        return self._try_upload_with_retry(file_path, file_name, mime_type, headers)
    
    def _try_upload_with_retry(self, file_path, file_name, mime_type, headers, is_retry=False):
        """尝试上传图片，失败时可能尝试切换密钥重试"""
        # 保存当前的API密钥，确保整个上传过程使用相同的密钥
        current_auth_token = self.auth_token
        
        files = {
            'file': (file_name, open(file_path, 'rb'), mime_type),
            'file_name': (None, file_name) # 第二个字段是文件名
        }
        try:
            response = self.scraper.post(
                self.upload_url,
                headers=headers,
                files=files, # 使用 files 参数上传文件
                proxies=self.proxies,
                timeout=60 # 上传可能需要更长时间
            )
            if response.status_code == 200:
                result = response.json()
                if self.DEBUG:
                    print(f"图片上传成功! Media ID: {result.get('id')}")
                # 确保返回的结果中包含上传时使用的API密钥信息
                result['used_auth_token'] = current_auth_token
                # print(f"上传响应: {json.dumps(result, indent=2)}") # 可选：打印完整响应
                return result # 返回包含id, url等信息的字典
            else:
                error_msg = f"上传图片失败，状态码: {response.status_code}, 响应: {response.text}"
                if self.DEBUG:
                    print(error_msg)
                
                # 如果不是已经在重试，且响应表明可能是API密钥问题，尝试切换密钥
                if not is_retry and (response.status_code in [401, 403] or "auth" in response.text.lower() or "token" in response.text.lower()):
                    if self.DEBUG:
                        print(f"上传失败可能与API密钥有关，尝试切换密钥后重试")
                    
                    try:
                        from .key_manager import key_manager
                        new_key = key_manager.mark_key_invalid(self.auth_token)
                        if new_key:
                            self.auth_token = new_key
                            if self.DEBUG:
                                print(f"已切换到新的API密钥，重试上传")
                            # 更新头部信息并重试
                            new_headers = self._get_dynamic_headers(content_type=None, referer="https://sora.chatgpt.com/library")
                            return self._try_upload_with_retry(file_path, file_name, mime_type, new_headers, is_retry=True)
                    except (ImportError, Exception) as e:
                        if self.DEBUG:
                            print(f"切换API密钥失败: {str(e)}")
                
                return error_msg
        except Exception as e:
            error_msg = f"上传图片时出错: {str(e)}"
            if self.DEBUG:
                print(error_msg)
            
            # 如果不是已经在重试，尝试切换密钥后重试
            if not is_retry:
                if self.DEBUG:
                    print(f"上传过程中发生异常，尝试切换API密钥后重试")
                
                try:
                    from .key_manager import key_manager
                    new_key = key_manager.mark_key_invalid(self.auth_token)
                    if new_key:
                        self.auth_token = new_key
                        if self.DEBUG:
                            print(f"已切换到新的API密钥，重试上传")
                        # 更新头部信息并重试
                        new_headers = self._get_dynamic_headers(content_type=None, referer="https://sora.chatgpt.com/library")
                        return self._try_upload_with_retry(file_path, file_name, mime_type, new_headers, is_retry=True)
                except (ImportError, Exception) as err:
                    if self.DEBUG:
                        print(f"切换API密钥失败: {str(err)}")
            
            return error_msg
        finally:
            # 确保文件句柄被关闭
            if 'file' in files and files['file'][1]:
                files['file'][1].close()
    
    def generate_image_remix(self, prompt, uploaded_media_id, num_images=1, width=None, height=None):
        """
        基于已上传的图片进行重混（Remix）生成新图片
        参数:
        prompt (str): 图片生成提示词
        uploaded_media_id (str): 通过 upload_image 获取的媒体ID (例如 "media_...")
        num_images (int): 要生成的图片数量
        width (int, optional): 输出图片宽度。如果为None，可能由API决定。
        height (int, optional): 输出图片高度。如果为None，可能由API决定。
        返回:
        list[str] or str: 成功时返回包含图片URL的列表，失败时返回错误信息字符串
        """
        if self.DEBUG:
            print(f"开始 Remix 图片 (ID: {uploaded_media_id})，提示词: '{prompt}'")
            
        # 如果上传图片时使用了特定API密钥，则确保使用同一个密钥进行remix
        # 在upload_image的返回结果中可能包含used_auth_token
        if isinstance(uploaded_media_id, dict) and 'id' in uploaded_media_id:
            if 'used_auth_token' in uploaded_media_id and uploaded_media_id['used_auth_token'] != self.auth_token:
                if self.DEBUG:
                    print(f"检测到上传图片时使用了不同的API密钥，切换到匹配的密钥进行Remix操作")
                self.auth_token = uploaded_media_id['used_auth_token']
            uploaded_media_id = uploaded_media_id['id']
        
        # 获取上传图片的信息，特别是原始尺寸，如果未指定输出尺寸则可能需要
        # (这里简化，假设API能处理尺寸或我们强制指定)
        # 实际应用中可能需要先查询 media_id 的详情
        payload = {
            "prompt": prompt,
            "n_variants": num_images,
            "inpaint_items": [
                {
                    "type": "image",
                    "frame_index": 0,
                    "preset_id": None,
                    "generation_id": None,
                    "upload_media_id": uploaded_media_id, # 关键：引用上传的图片
                    "source_start_frame": 0,
                    "source_end_frame": 0,
                    "crop_bounds": None
                }
            ],
            "operation": "remix", # 关键：操作类型
            "type": "image_gen",
            "n_frames": 1,
            "width": 720, # 可选，如果为None，API可能会基于输入调整
            "height": 480 # 可选
        }
        # 只有当width和height都提供了值时才添加到payload中
        if width is not None:
            payload["width"] = width
        if height is not None:
            payload["height"] = height
        try:
            # 提交任务时使用 library 作为 referer，与示例一致
            task_id = self._submit_task(payload, referer="https://sora.chatgpt.com/library")
            if not task_id:
                # 任务提交失败，尝试切换密钥后重试
                if self.DEBUG:
                    print(f"Remix任务提交失败，尝试切换API密钥后重试")
                
                try:
                    # 导入在这里进行以避免循环导入
                    from .key_manager import key_manager
                    # 标记当前密钥为无效并获取新密钥
                    new_key = key_manager.mark_key_invalid(self.auth_token)
                    if new_key:
                        self.auth_token = new_key
                        if self.DEBUG:
                            print(f"已切换到新的API密钥，重试Remix任务")
                        # 使用新密钥重试提交任务
                        task_id = self._submit_task(payload, referer="https://sora.chatgpt.com/library")
                        if not task_id:
                            return "Remix任务提交失败（已尝试切换密钥）"
                    else:
                        return "Remix任务提交失败（无可用的备用密钥）"
                except ImportError:
                    if self.DEBUG:
                        print(f"无法导入key_manager，无法自动切换密钥")
                    return "Remix任务提交失败"
                except Exception as e:
                    if self.DEBUG:
                        print(f"切换API密钥时发生错误: {str(e)}")
                    return f"Remix任务提交失败: {str(e)}"
            
            if self.DEBUG:
                print(f"Remix 任务已提交，ID: {task_id}")
            # 轮询检查任务状态
            image_urls = self._poll_task_status(task_id)
            
            # 如果轮询返回错误信息，也尝试切换密钥重试
            if isinstance(image_urls, str) and ("失败" in image_urls or "错误" in image_urls or "error" in image_urls.lower()):
                if self.DEBUG:
                    print(f"Remix任务执行失败，尝试切换API密钥后重试")
                
                try:
                    from .key_manager import key_manager
                    new_key = key_manager.mark_key_invalid(self.auth_token)
                    if new_key:
                        self.auth_token = new_key
                        if self.DEBUG:
                            print(f"已切换到新的API密钥，重试整个Remix过程")
                        # 使用新密钥重试整个生成过程
                        return self.generate_image_remix(prompt, uploaded_media_id, num_images, width, height)
                except (ImportError, Exception) as e:
                    if self.DEBUG:
                        print(f"切换API密钥失败或重试失败: {str(e)}")
            
            # 增加图片本地化支持
            if image_urls and isinstance(image_urls, list):
                if Config.IMAGE_LOCALIZATION:
                    if self.DEBUG:
                        print(f"正在本地化 Remix 生成的 {len(image_urls)} 张图片...")
                    # 创建事件循环并运行图片本地化
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    localized_urls = loop.run_until_complete(localize_image_urls(image_urls))
                    loop.close()
                    
                    if self.DEBUG:
                        print(f"Remix 图片本地化完成")
                    return localized_urls
            
            return image_urls
        except Exception as e:
            # 如果发生异常，也尝试切换密钥重试
            if self.DEBUG:
                print(f"Remix生成过程中发生异常: {str(e)}，尝试切换API密钥")
            
            try:
                from .key_manager import key_manager
                new_key = key_manager.mark_key_invalid(self.auth_token)
                if new_key:
                    self.auth_token = new_key
                    if self.DEBUG:
                        print(f"已切换到新的API密钥，重试整个Remix过程")
                    # 使用新密钥重试整个生成过程
                    return self.generate_image_remix(prompt, uploaded_media_id, num_images, width, height)
            except (ImportError, Exception) as err:
                if self.DEBUG:
                    print(f"切换API密钥失败或重试失败: {str(err)}")
            
            return f"Remix 生成图片时出错: {str(e)}"

    def _submit_task(self, payload, referer="https://sora.chatgpt.com/explore"):
        """提交生成任务 (通用，接受payload字典)"""
        headers = self._get_dynamic_headers(content_type="application/json", referer=referer)
        
        # 获取当前的auth_token用于最后可能的释放
        current_auth_token = self.auth_token
        
        try:
            # 检查是否可以导入key_manager并标记密钥为工作中
            try:
                from .key_manager import key_manager
                # 生成一个临时任务ID，用于标记密钥工作状态
                temp_task_id = f"pending_task_{self._generate_random_id()}"
                key_manager.mark_key_as_working(self.auth_token, temp_task_id)
            except ImportError:
                if self.DEBUG:
                    print(f"无法导入key_manager，无法标记密钥工作状态")
            except Exception as e:
                if self.DEBUG:
                    print(f"标记密钥工作状态时发生错误: {str(e)}")
                
            response = self.scraper.post(
                self.gen_url,
                headers=headers,
                json=payload,
                proxies=self.proxies,
                timeout=20 # 增加超时时间
            )
            if response.status_code == 200:
                try:
                    result = response.json()
                    task_id = result.get("id")
                    if task_id:
                        # 更新任务ID为实际分配的ID
                        try:
                            from .key_manager import key_manager
                            # 更新工作中状态的任务ID
                            key_manager.release_key(self.auth_token)  # 先释放临时ID
                            key_manager.mark_key_as_working(self.auth_token, task_id)  # 用真实ID重新标记
                            if self.DEBUG:
                                print(f"已将密钥标记为工作中，任务ID: {task_id}")
                        except (ImportError, Exception) as e:
                            if self.DEBUG:
                                print(f"更新密钥工作状态时发生错误: {str(e)}")
                        
                        return task_id
                    else:
                        # 任务提交成功但未返回ID，释放密钥
                        try:
                            from .key_manager import key_manager
                            key_manager.release_key(self.auth_token)
                            if self.DEBUG:
                                print(f"任务提交未返回ID，已释放密钥")
                        except (ImportError, Exception) as e:
                            if self.DEBUG:
                                print(f"释放密钥时发生错误: {str(e)}")
                        
                        # 检查响应中是否有可能表明API密钥问题的信息
                        response_text = response.text.lower()
                        is_auth_issue = False
                        auth_keywords = ["authorization", "auth", "token", "permission", "unauthorized", "credentials", "login"]
                        
                        for keyword in auth_keywords:
                            if keyword in response_text:
                                is_auth_issue = True
                                break
                        
                        if is_auth_issue:
                            if self.DEBUG:
                                print(f"API响应内容表明可能存在认证问题，尝试切换密钥")
                            
                            try:
                                from .key_manager import key_manager
                                new_key = key_manager.mark_key_invalid(self.auth_token)
                                if new_key:
                                    self.auth_token = new_key
                                    if self.DEBUG:
                                        print(f"已切换到新的API密钥，重试请求")
                                    # 使用新密钥重试请求
                                    return self._submit_task(payload, referer)
                            except ImportError:
                                if self.DEBUG:
                                    print(f"无法导入key_manager，无法自动切换密钥")
                            except Exception as e:
                                if self.DEBUG:
                                    print(f"切换API密钥时发生错误: {str(e)}")
                        
                        if self.DEBUG:
                            print(f"提交任务成功，但响应中未找到任务ID。响应: {response.text}")
                        return None
                except json.JSONDecodeError:
                    # 释放密钥
                    try:
                        from .key_manager import key_manager
                        key_manager.release_key(self.auth_token)
                        if self.DEBUG:
                            print(f"JSON解析失败，已释放密钥")
                    except (ImportError, Exception) as e:
                        if self.DEBUG:
                            print(f"释放密钥时发生错误: {str(e)}")
                            
                    if self.DEBUG:
                        print(f"提交任务成功，但无法解析响应JSON。状态码: {response.status_code}, 响应: {response.text}")
                    return None
            else:
                # 释放密钥
                try:
                    from .key_manager import key_manager
                    key_manager.release_key(self.auth_token)
                    if self.DEBUG:
                        print(f"请求失败，已释放密钥")
                except (ImportError, Exception) as e:
                    if self.DEBUG:
                        print(f"释放密钥时发生错误: {str(e)}")
                
                if self.DEBUG:
                    print(f"提交任务失败，状态码: {response.status_code}")
                if self.DEBUG:
                    print(f"请求Payload: {json.dumps(payload)}")
                if self.DEBUG:
                    print(f"响应内容: {response.text}")
                
                # 特殊处理429错误（太多并发任务）
                if response.status_code == 429:
                    response_text = response.text.lower()
                    is_concurrent_issue = (
                        "concurrent" in response_text or 
                        "too many" in response_text or 
                        "wait" in response_text or
                        "progress" in response_text
                    )
                    
                    if is_concurrent_issue:
                        if self.DEBUG:
                            print(f"检测到并发限制错误，当前密钥正在处理其他任务，获取新密钥但不禁用当前密钥")
                        try:
                            from .key_manager import key_manager
                            # 不标记为无效，但获取一个新的可用密钥
                            new_key = key_manager.get_key()
                            if new_key:
                                self.auth_token = new_key
                                if self.DEBUG:
                                    print(f"已获取新的API密钥，重试请求")
                                # 使用新密钥重试请求
                                return self._submit_task(payload, referer)
                            else:
                                if self.DEBUG:
                                    print(f"没有可用的备用密钥")
                        except (ImportError, Exception) as e:
                            if self.DEBUG:
                                print(f"获取新密钥时发生错误: {str(e)}")
                        return None
                
                # 检查是否是认证失败（401/403）或其他可能表明API密钥失效的情况
                response_text = response.text.lower()
                is_auth_issue = (
                    response.status_code in [401, 403] or
                    "authorization" in response_text or
                    "auth" in response_text or
                    "token" in response_text or
                    "permission" in response_text or
                    "unauthorized" in response_text or
                    "credentials" in response_text or
                    "login" in response_text or
                    "invalid" in response_text
                ) and not (
                    # 排除并发限制导致的错误
                    "concurrent" in response_text or 
                    "too many" in response_text or 
                    "wait" in response_text or
                    "progress" in response_text
                )
                
                if is_auth_issue:
                    if self.DEBUG:
                        print(f"API密钥可能已失效，尝试切换密钥")
                    
                    try:
                        # 导入在这里进行以避免循环导入
                        from .key_manager import key_manager
                        # 标记当前密钥为无效并获取新密钥
                        new_key = key_manager.mark_key_invalid(self.auth_token)
                        if new_key:
                            self.auth_token = new_key
                            if self.DEBUG:
                                print(f"已切换到新的API密钥，重试请求")
                            # 使用新密钥重试请求
                            return self._submit_task(payload, referer)
                    except ImportError:
                        if self.DEBUG:
                            print(f"无法导入key_manager，无法自动切换密钥")
                    except Exception as e:
                        if self.DEBUG:
                            print(f"切换API密钥时发生错误: {str(e)}")
                            
                return None
        except Exception as e:
            # 确保释放密钥
            try:
                from .key_manager import key_manager
                key_manager.release_key(current_auth_token)
                if self.DEBUG:
                    print(f"发生异常，已释放密钥")
            except (ImportError, Exception) as release_err:
                if self.DEBUG:
                    print(f"释放密钥时发生错误: {str(release_err)}")
                
            if self.DEBUG:
                print(f"提交任务时出错: {str(e)}")
            
            # 检查异常信息中是否包含可能的认证问题
            error_str = str(e).lower()
            is_auth_issue = (
                "authorization" in error_str or
                "auth" in error_str or
                "token" in error_str or
                "permission" in error_str or
                "unauthorized" in error_str or
                "credentials" in error_str or
                "login" in error_str
            )
            
            if is_auth_issue:
                if self.DEBUG:
                    print(f"异常信息表明可能存在API密钥问题，尝试切换密钥")
                
                try:
                    from .key_manager import key_manager
                    new_key = key_manager.mark_key_invalid(self.auth_token)
                    if new_key:
                        self.auth_token = new_key
                        if self.DEBUG:
                            print(f"已切换到新的API密钥，重试请求")
                        # 使用新密钥重试请求
                        return self._submit_task(payload, referer)
                except (ImportError, Exception) as err:
                    if self.DEBUG:
                        print(f"切换API密钥失败: {str(err)}")
            
            return None
            
    def _poll_task_status(self, task_id, max_attempts=40, interval=5):
        """
        轮询检查任务状态，直到完成，返回所有生成的图片URL列表
        """
        # 保存当前使用的密钥，确保最后可以正确释放
        current_auth_token = self.auth_token
        
        if self.DEBUG:
            print(f"开始轮询任务 {task_id} 的状态...")
        try:
            for attempt in range(max_attempts):
                try:
                    headers = self._get_dynamic_headers(referer="https://sora.chatgpt.com/library") # Polling often happens from library view
                    query_url = f"{self.check_url}?limit=10" # 获取最近的任务，减少数据量
                    response = self.scraper.get(
                        query_url,
                        headers=headers,
                        proxies=self.proxies,
                        timeout=15
                    )
                    if response.status_code == 200:
                        try:
                            result = response.json()
                            task_responses = result.get("task_responses", [])
                            # 查找对应的任务
                            for task in task_responses:
                                if task.get("id") == task_id:
                                    status = task.get("status")
                                    if self.DEBUG:
                                        print(f"  任务 {task_id} 状态: {status} (尝试 {attempt+1}/{max_attempts})")
                                    if status == "succeeded":
                                        # 任务成功完成，释放密钥
                                        try:
                                            from .key_manager import key_manager
                                            key_manager.release_key(current_auth_token)
                                            if self.DEBUG:
                                                print(f"任务成功完成，已释放密钥")
                                        except (ImportError, Exception) as e:
                                            if self.DEBUG:
                                                print(f"释放密钥时发生错误: {str(e)}")
                                                
                                        generations = task.get("generations", [])
                                        image_urls = []
                                        if generations:
                                            for gen in generations:
                                                url = gen.get("url")
                                                if url:
                                                    image_urls.append(url)
                                        if image_urls:
                                            if self.DEBUG:
                                                print(f"任务 {task_id} 成功完成！找到 {len(image_urls)} 张图片。")
                                            return image_urls
                                        else:
                                            if self.DEBUG:
                                                print(f"任务 {task_id} 状态为 succeeded，但在响应中未找到有效的图片URL。")
                                            if self.DEBUG:
                                                print(f"任务详情: {json.dumps(task, indent=2)}")
                                            return "任务成功但未找到图片URL"
                                    elif status == "failed":
                                        # 任务失败，释放密钥
                                        try:
                                            from .key_manager import key_manager
                                            key_manager.release_key(current_auth_token)
                                            if self.DEBUG:
                                                print(f"任务失败，已释放密钥")
                                        except (ImportError, Exception) as e:
                                            if self.DEBUG:
                                                print(f"释放密钥时发生错误: {str(e)}")
                                                
                                        failure_reason = task.get("failure_reason", "未知原因")
                                        if self.DEBUG:
                                            print(f"任务 {task_id} 失败: {failure_reason}")
                                        # 检查是否是因为API密钥问题导致的失败
                                        failure_reason_lower = failure_reason.lower()
                                        auth_keywords = [
                                            "authorization", "auth", "token", "permission", 
                                            "unauthorized", "credentials", "login", "invalid"
                                        ]
                                        is_auth_issue = any(keyword in failure_reason_lower for keyword in auth_keywords)
                                        
                                        if is_auth_issue:
                                            if self.DEBUG:
                                                print(f"检测到API密钥可能失效，尝试切换密钥")
                                            try:
                                                # 导入在这里进行以避免循环导入
                                                from .key_manager import key_manager
                                                # 标记当前密钥为无效并获取新密钥
                                                new_key = key_manager.mark_key_invalid(self.auth_token)
                                                if new_key:
                                                    self.auth_token = new_key
                                                    if self.DEBUG:
                                                        print(f"已切换到新的API密钥")
                                            except ImportError:
                                                if self.DEBUG:
                                                    print(f"无法导入key_manager，无法自动切换密钥")
                                            except Exception as e:
                                                if self.DEBUG:
                                                    print(f"切换API密钥时发生错误: {str(e)}")
                                            return f"任务失败: {failure_reason}"
                                    elif status in ["rejected", "needs_user_review"]:
                                        # 任务被拒绝，释放密钥
                                        try:
                                            from .key_manager import key_manager
                                            key_manager.release_key(current_auth_token)
                                            if self.DEBUG:
                                                print(f"任务被拒绝，已释放密钥")
                                        except (ImportError, Exception) as e:
                                            if self.DEBUG:
                                                print(f"释放密钥时发生错误: {str(e)}")
                                                
                                        if self.DEBUG:
                                            print(f"任务 {task_id} 被拒绝或需要审查: {status}")
                                        return f"任务被拒绝或需审查: {status}"
                                    # else status is pending, processing, etc. - continue polling
                                    break # Found the task, no need to check others in this response
                            else:
                                # Task ID not found in the recent list, maybe it's older or just submitted
                                if self.DEBUG:
                                    print(f"  未在最近任务列表中找到 {task_id}，继续等待... (尝试 {attempt+1}/{max_attempts})")
                        except json.JSONDecodeError:
                            if self.DEBUG:
                                print(f"检查任务状态时无法解析响应JSON。状态码: {response.status_code}, 响应: {response.text}")
                    else:
                        if self.DEBUG:
                            print(f"检查任务状态失败，状态码: {response.status_code}, 响应: {response.text}")
                        
                        # 检查是否是认证失败或其他可能表明API密钥失效的情况
                        response_text = response.text.lower()
                        is_auth_issue = (
                            response.status_code in [401, 403, 429] or
                            "authorization" in response_text or
                            "auth" in response_text or
                            "token" in response_text or
                            "permission" in response_text or
                            "unauthorized" in response_text or
                            "credentials" in response_text or
                            "login" in response_text or
                            "invalid" in response_text
                        )
                        
                        if is_auth_issue:
                            if self.DEBUG:
                                print(f"API密钥可能已失效，尝试切换密钥")
                            
                            try:
                                # 导入在这里进行以避免循环导入
                                from .key_manager import key_manager
                                # 标记当前密钥为无效并获取新密钥
                                new_key = key_manager.mark_key_invalid(self.auth_token)
                                if new_key:
                                    self.auth_token = new_key
                                    if self.DEBUG:
                                        print(f"已切换到新的API密钥，重试请求")
                                    # 使用新密钥继续轮询
                                    continue
                            except ImportError:
                                if self.DEBUG:
                                    print(f"无法导入key_manager，无法自动切换密钥")
                            except Exception as e:
                                if self.DEBUG:
                                    print(f"切换API密钥时发生错误: {str(e)}")
                                    
                    time.sleep(interval)  # 等待一段时间后再次检查
                except Exception as e:
                    if self.DEBUG:
                        print(f"检查任务状态时出错: {str(e)}")
                    
                    # 检查异常信息中是否包含可能的认证问题
                    error_str = str(e).lower()
                    is_auth_issue = (
                        "authorization" in error_str or
                        "auth" in error_str or
                        "token" in error_str or
                        "permission" in error_str or
                        "unauthorized" in error_str or
                        "credentials" in error_str or
                        "login" in error_str
                    )
                    
                    if is_auth_issue:
                        if self.DEBUG:
                            print(f"异常信息表明可能存在API密钥问题，尝试切换密钥")
                        
                        try:
                            from .key_manager import key_manager
                            new_key = key_manager.mark_key_invalid(self.auth_token)
                            if new_key:
                                self.auth_token = new_key
                                if self.DEBUG:
                                    print(f"已切换到新的API密钥，重试请求")
                                # 重置当前尝试次数，继续轮询
                                continue
                        except (ImportError, Exception) as err:
                            if self.DEBUG:
                                print(f"切换API密钥失败: {str(err)}")
                    
                    # Add a slightly longer delay on error to avoid hammering the server
                    time.sleep(interval * 1.5)
            
            # 如果达到最大尝试次数，释放密钥
            try:
                from .key_manager import key_manager
                key_manager.release_key(current_auth_token)
                if self.DEBUG:
                    print(f"轮询超时，已释放密钥")
            except (ImportError, Exception) as e:
                if self.DEBUG:
                    print(f"释放密钥时发生错误: {str(e)}")
                    
            return f"任务 {task_id} 超时 ({max_attempts * interval}秒)，未能获取最终状态"
        except Exception as e:
            # 确保在异常情况下也释放密钥
            try:
                from .key_manager import key_manager
                key_manager.release_key(current_auth_token)
                if self.DEBUG:
                    print(f"轮询过程发生异常，已释放密钥")
            except (ImportError, Exception) as release_err:
                if self.DEBUG:
                    print(f"释放密钥时发生错误: {str(release_err)}")
                
            if self.DEBUG:
                print(f"轮询任务状态时发生未处理的异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"轮询任务状态时出错: {str(e)}"

    def test_connection(self):
        """
        测试API连接是否有效，仅发送一个轻量级请求
        返回:
        dict: 包含连接状态信息的字典
        """
        start_time = time.time()  # 记录开始时间，用于计算响应时间
        success = False  # 初始化请求结果标识
        
        try:
            # 使用简单的GET请求来验证连接和认证
            headers = self._get_dynamic_headers(referer="https://sora.chatgpt.com/explore")
            response = self.scraper.get(
                "https://sora.chatgpt.com/backend/parameters",
                headers=headers,
                proxies=self.proxies,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                # 检查返回的数据中是否含有关键字段，确认API确实有效
                api_valid = result.get("can_create_images") is not None or "limits_for_images" in result
                
                if api_valid:
                    success = True  # 标记请求成功
                    # 记录请求结果（成功）
                    try:
                        from .key_manager import key_manager
                        response_time = time.time() - start_time
                        key_manager.record_request_result(self.auth_token, success, response_time)
                    except (ImportError, Exception) as e:
                        if self.DEBUG:
                            print(f"记录请求结果失败: {str(e)}")
                    
                    return {
                        "status": "success",
                        "message": "API连接测试成功",
                        "data": result
                    }
                else:
                    # API返回200但数据不符合预期
                    success = False  # 标记请求失败
                    
                    # 记录请求结果（失败）
                    try:
                        from .key_manager import key_manager
                        response_time = time.time() - start_time
                        key_manager.record_request_result(self.auth_token, success, response_time)
                    except (ImportError, Exception) as e:
                        if self.DEBUG:
                            print(f"记录请求结果失败: {str(e)}")
                    
                    return {
                        "status": "error",
                        "message": "API连接测试失败：返回数据格式不符合预期",
                        "response": result
                    }
            else:
                # 检查是否是认证失败或其他可能表明API密钥失效的情况
                response_text = response.text.lower()
                is_auth_issue = (
                    response.status_code in [401, 403, 429] or
                    "authorization" in response_text or
                    "auth" in response_text or
                    "token" in response_text or
                    "permission" in response_text or
                    "unauthorized" in response_text or
                    "credentials" in response_text or
                    "login" in response_text or
                    "invalid" in response_text
                )
                
                success = False  # 标记请求失败
                
                # 记录请求结果（失败）
                try:
                    from .key_manager import key_manager
                    response_time = time.time() - start_time
                    key_manager.record_request_result(self.auth_token, success, response_time)
                except (ImportError, Exception) as e:
                    if self.DEBUG:
                        print(f"记录请求结果失败: {str(e)}")
                
                if is_auth_issue:
                    if self.DEBUG:
                        print(f"API密钥可能已失效，尝试切换密钥")
                    
                    try:
                        # 导入在这里进行以避免循环导入
                        from .key_manager import key_manager
                        # 标记当前密钥为无效并获取新密钥
                        new_key = key_manager.mark_key_invalid(self.auth_token)
                        if new_key:
                            self.auth_token = new_key
                            if self.DEBUG:
                                print(f"已切换到新的API密钥，重试连接测试")
                            # 使用新密钥重试
                            return self.test_connection()
                    except ImportError:
                        if self.DEBUG:
                            print(f"无法导入key_manager，无法自动切换密钥")
                    except Exception as e:
                        if self.DEBUG:
                            print(f"切换API密钥时发生错误: {str(e)}")
                
                return {
                    "status": "error",
                    "message": f"API连接测试失败，状态码: {response.status_code}",
                    "response": response.text
                }
        except Exception as e:
            success = False  # 标记请求失败
            
            # 记录请求结果（异常失败）
            try:
                from .key_manager import key_manager
                response_time = time.time() - start_time
                key_manager.record_request_result(self.auth_token, success, response_time)
            except (ImportError, Exception) as err:
                if self.DEBUG:
                    print(f"记录请求结果失败: {str(err)}")
            
            # 检查异常信息中是否包含可能的认证问题
            error_str = str(e).lower()
            is_auth_issue = (
                "authorization" in error_str or
                "auth" in error_str or
                "token" in error_str or
                "permission" in error_str or
                "unauthorized" in error_str or
                "credentials" in error_str or
                "login" in error_str
            )
            
            if is_auth_issue:
                if self.DEBUG:
                    print(f"异常信息表明可能存在API密钥问题，尝试切换密钥")
                
                try:
                    from .key_manager import key_manager
                    new_key = key_manager.mark_key_invalid(self.auth_token)
                    if new_key:
                        self.auth_token = new_key
                        if self.DEBUG:
                            print(f"已切换到新的API密钥，重试连接测试")
                        # 使用新密钥重试
                        return self.test_connection()
                except (ImportError, Exception) as err:
                    if self.DEBUG:
                        print(f"切换API密钥失败: {str(err)}")
            
            raise Exception(f"API连接测试失败: {str(e)}") 