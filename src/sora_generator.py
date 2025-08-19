import cloudscraper
import time
import json
import random
import string
import os
import mimetypes # To guess file mime type
import asyncio
from .utils import localize_image_urls
from .config import Config

class SoraImageGenerator:
    def __init__(self, proxy_host=None, proxy_port=None, proxy_user=None, proxy_pass=None, auth_token=None):
        # Use Config.VERBOSE_LOGGING instead of reading SORA_DEBUG directly from env
        self.DEBUG = Config.VERBOSE_LOGGING
        
        # Configure proxy
        if proxy_host and proxy_port:
            # If auth credentials are provided, include them in the proxy URL
            if proxy_user and proxy_pass:
                proxy_auth = f"{proxy_user}:{proxy_pass}@"
                self.proxies = {
                    "http": f"http://{proxy_auth}{proxy_host}:{proxy_port}",
                    "https": f"http://{proxy_auth}{proxy_host}:{proxy_port}"
                }
                if self.DEBUG:
                    print(f"Configured proxy with authentication: {proxy_user}:****@{proxy_host}:{proxy_port}")
            else:
                self.proxies = {
                    "http": f"http://{proxy_host}:{proxy_port}",
                    "https": f"http://{proxy_host}:{proxy_port}"
                }
                if self.DEBUG:
                    print(f"Configured proxy: {proxy_host}:{proxy_port}")
        else:
            self.proxies = None
            if self.DEBUG:
                print("Proxy not configured. Requests will be sent directly.")
        # Create cloudscraper instance
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'mobile': False
            }
        )
        # Set common headers - Content-Type and openai-sentinel-token are set dynamically per request
        self.base_headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "sec-ch-ua": "\"Chromium\";v=\"136\", \"Google Chrome\";v=\"136\", \"Not.A/Brand\";v=\"99\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            # Referer will be set according to the operation
        }
        # Set auth token (provided externally or hardcoded)
        self.auth_token = auth_token or "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjE5MzQ0ZTY1LWJiYzktNDRkMS1hOWQwLWY5NTdiMDc5YmQwZSIsInR5cCI6IkpXVCJ9.eyJhdWQiOlsiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS92MSJdLCJjbGllbnRfaWQiOiJhcHBfWDh6WTZ2VzJwUTl0UjNkRTduSzFqTDVnSCIsImV4cCI6MTc0Nzk3MDExMSwiaHR0cHM6Ly9hcGkub3BlbmFpLmNvbS9hdXRoIjp7InVzZXJfaWQiOiJ1c2VyLWdNeGM0QmVoVXhmTW1iTDdpeUtqengxYiJ9LCJodHRwczovL2FwaS5vcGVuYWkuY29tL3Byb2ZpbGUiOnsiZW1haWwiOiIzajVtOTFud3VtckBmcmVlLnViby5lZHUuZ24iLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZX0sImlhdCI6MTc0NzEwNjExMSwiaXNzIjoiaHR0cHM6Ly9hdXRoLm9wZW5haS5jb20iLCJqdGkiOiIzMGM4ZDJhOS0yNzkxLTRhNjQtODI2OS0yMzU3OGFhMmI0MTEiLCJuYmYiOjE3NDcxMDYxMTEsInB3ZF9hdXRoX3RpbWUiOjE3NDcxMDYxMDkxMDksInNjcCI6WyJvcGVuaWQiLCJlbWFpbCIsInByb2ZpbGUiLCJvZmZsaW5lX2FjY2VzcyIsIm1vZGVsLnJlcXVlc3QiLCJtb2RlbC5yZWFkIiwib3JnYW5pemF0aW9uLnJlYWQiLCJvcmdhbml6YXRpb24ud3JpdGUiXSwic2Vzc2lvbl9pZCI6ImF1dGhzZXNzX21yWFRwZlVENU51TDFsV05xNUhSOW9lYiIsInN1YiI6ImF1dGgwfDY4MjFkYWYyNjhiYjgxMzFkMDRkYTAwNCJ9.V4ZqYJuf_f7F_DrMMRrt-ymul5HUrqENVkiFyEwfYmzMFWthEGS6Ryia100QRlprw8jjGscHZXlUFaOcRNIarcBig8fBY6n_AB3J34MlcBv6peS-3_EJlIiH_N7j_mu-8lNpJbxk9lSlFaGpKU1IOO7kBuaAmLH-iErM-wqBfSlnnAq8h4iqBDxi4CMTcAhVm2-qG7u7f0Ho1TCGa7wrdchWtZxyfHIqNWkC88qBlUwTH5g2vRL419_zIKEWKyAtV2WNI68vpyBLrRVhtnpDh0jcrm2WqCj2X2LQqNFkFKoui3wCdG9Vskpl39l9sV54HuV7w6stQIausR1F4Y9NbjsBAyLIimZOllCwYAefTC2BOpIHfOA3_D58G3SEiRADVK7pK7ip6QsEI__GteoeCuRvZA9b5jLmhVS0SUlDYSOoNwlJ_ejfEpPJcmHUchFa7bUkS-XVrEUgr1yP5FxPwWUyn7UWrW_dZ3lVW1EU4Bp6Kp6JuwyOFf2Mj-V3_9tc8qJRClI8WHUf6In0hiO_pGbFCI2opkF3XusAQKmTB12nPBsmSlwewigTPhAj3nf-8Ze3O-etnBrV5pz_woIwQsQ54T-wgEdrLWDE6dSqNDulfpldF6Cok62212kW8w3SY3V7VSq5Tr1KRyWXJEH-haVb6qmAE2ldDjeHvJossWg" # Replace with your valid token or read from environment variable
        if not self.auth_token or not self.auth_token.startswith("Bearer "):
            raise ValueError("Invalid or missing auth token (should start with 'Bearer ')")
        self.gen_url = "https://sora.chatgpt.com/backend/video_gen"
        self.check_url = "https://sora.chatgpt.com/backend/video_gen"
        self.upload_url = "https://sora.chatgpt.com/backend/uploads"
        
        # Show whether image localization is enabled
        if Config.IMAGE_LOCALIZATION:
            if self.DEBUG:
                print(f"Image localization enabled, images will be saved to: {Config.IMAGE_SAVE_DIR}")
            os.makedirs(Config.IMAGE_SAVE_DIR, exist_ok=True)
    
    def _get_dynamic_headers(self, content_type="application/json", referer="https://sora.chatgpt.com/explore"):
        """Generate headers for each request with a dynamic sentinel token"""
        headers = self.base_headers.copy()
        headers["authorization"] = self.auth_token
        headers["openai-sentinel-token"] = self._generate_sentinel_token()
        headers["referer"] = referer
        if content_type: # For multipart/form-data, requests sets Content-Type automatically
            headers["content-type"] = content_type
        return headers
    
    def _generate_sentinel_token(self):
        """Generate a randomly modified sentinel-token"""
        base_token = {
            "p": "gAAAAABWzIxMjksIk1vbiBNYXkgMTIgMjAyNSAxODo1ODowOSBHTVQrMDgwMCAo5Lit5Zu95qCH5YeG5pe26Ze0KSIsMjI0ODE0Njk0NCw5LCJNb3ppbGxhLzUuMCAoV2luZG93cyBOVCAxMC4wOyBXaW42NDsgeDY0KSBBcHBsZVdlYktpdC81MzcuMzYgKEtIVE1MLCBsaWtlIEdlY2tvKSBDaHJvbWUvMTM2LjAuMC4wIFNhZmFyaS81MzcuMzYiLCJodHRwczovL3NvcmEtY2RuLm9haXN0YXRpYy5jb20vX25leHQvc3RhdGljL2NodW5rcy93ZWJwYWNrLWU1MDllMDk0N2RlZWM0Y2YuanMiLG51bGwsInpoLUNOIiwiemgtQ04semgiLDEwLCJwcm9kdWN0U3Vi4oiSMjAwMzAxMDciLCJfcmVhY3RMaXN0ZW5pbmd2cXAzdWtpNmh6IiwiX19zZW50aW5lbF9pbml0X3BlbmRpbmciLDEyMDczMzEuNSwiN2M4OTMxM2EtZTY0Mi00MjI4LTk5ZDQtNTRlZDRjYzQ3MGZiIiwiIiwxNl0=",
            "t": "SBYdBBoGFhQRdVtbdxEYEQEaHQAAFhQRYwN2T2IEUH5pRHJyYx51YnJybFBhWHZkYgRyUHgDclZzH2l5a1gXUWVlcRMRGBEBHR0HBBYUEXpnfVt9YFAJDB8WAAIAAgYRDgxpYltjSl55SWJEZV9mXx4KFh8WGAAaBxYUEXVydW9ydXJ1b3J1cnVvcnVydW9ydXJ1b3J1b3J1b3J1DgkMHxYBAgALAxEOHh0BBwIXCwwEBx8FAwADGwAAHxYcBxoFDQwJFnFDEw4WHxYXBxoCBwwJFmB2dGRxYgBqdHVLf2hUX3VySWpVcVNNa3ZiYW13dgtyb3J5cHxvam12YWB7YgN2THVcYnxsSwR7fH9mfHJlZ1F3VARtcVwLcGpiV2pwaEdmZFhgdGZLbWRxXAdQbHJ5dHNvanlwQ29Xd1QEZnFmXFJoWFBRbEZ2e3JTWVF8YnFvd2ZUd2xiR3Vzb1BxcWV3UXxLbmxrYV9Wf3FxfHNJclVydU1qdXJtaHJmUH9sYnF1fElcdXtMdH5sdnZmZAR+ZmpUcXZzVgN2cUN3UHZyZWhyXAd8bHJ5cnVGdW1lWGRScWIAamBlDgkMHxYKBgADDREODHZjcWx/AnIBZkJLV2FTRWZWZX5Pa2JHVWsDbmRie1xgYXFoUWxfbmlhBQJ4f3FmUGFJBnNkWEphZ3VET2VYcntpA25kYntDVWRYf2Z3ZXZ9Vl9hXXZ1RGZseENzZnJ3Z3YCdn1WX2FddnVEZmx4Q3NmcndkFh8WFwAaBAUMCRZrcnh7fF92T2Z1eXx2dW5pZ1YKXGIFRnFhX3ZAZmJLUXwAfmtgeGlxYQVoeFdYdU1iYgJjfFsBAVJ7YUxrB1ZDVUR+fGthcXN4ZkRrbH9lWmtsG0FiAkdIZHFXZnxffnRiVgZsa3JeUmVlQEhhQ31ybFsNZ2VCS2NmWEZFZlhMWWQEcWJ2ZWZdZx5XdWRYXnllcVxJanMKWnQARElXdgoDUHx4WlZ0UEBWB0tNTQBuQW4dAlNXWXRUV11cXWkHQwx0XW5BUW9QbWVyRnFhZWJIVwR1UHtfRGdSeGl1YQUfcmJ2V0h3Zgd4bFR9cWdCUHFmZU1qd199amVDeQx5X3JRYB51ZWRYXnlSZHJcdAVHdXtmcWlWaXFwV1hGXlB0Q2hlX1dQf2V+fWB7cndqcl5YUF92TXRxV3V3AkBXY0JpbWRfSlJ8AgVLZGFHdnwCRHBnHFdzZlheV2wCYmZmbAZjfF9iUWxoBmJrYkp/UAJiZmVleXB4ZWZhdR9HYmJ2Qn5iX3JKdGFbV3xfdmF1HnVmZWF0f2V1THlmdXlTd3t+VFJ2Q05RfEZbV3tiAVIHAlpLAXICVXZpRmpzbEVXa1wcUgZXBwxO",
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
        """Generate a random ID similar to a UUID format"""
        return f"{self._random_hex(8)}-{self._random_hex(4)}-{self._random_hex(4)}-{self._random_hex(4)}-{self._random_hex(12)}"
    
    def _random_hex(self, length):
        """Generate a random hexadecimal string of a specified length"""
        return ''.join(random.choice(string.hexdigits.lower()) for _ in range(length))
    
    def generate_image(self, prompt, num_images=1, width=720, height=480):
        """
        Generate one or more images and return a list of image URLs.
        Args:
        prompt (str): Prompt for image generation
        num_images (int): Number of images to generate (maps to n_variants)
        width (int): Image width
        height (int): Image height
        Returns:
        list[str] or str: A list of image URLs on success, or an error message string on failure
        """
        # Ensure prompt is valid UTF-8
        if isinstance(prompt, bytes):
            prompt = prompt.decode('utf-8')
        
        # Print prompt and handle possible encoding issues
        try:
            if self.DEBUG:
                print(f"Starting to generate {num_images} images, prompt: '{prompt}'")
        except UnicodeEncodeError:
            if self.DEBUG:
                print(f"Starting to generate {num_images} images, prompt: [encoding display issue, data is valid]")
        
        payload = {
            "type": "image_gen",
            "operation": "simple_compose",
            "prompt": prompt,
            "n_variants": num_images, # Use the provided number
            "width": width,
            "height": height,
            "n_frames": 1,
            "inpaint_items": []
        }
        try:
            task_id = self._submit_task(payload, referer="https://sora.chatgpt.com/explore")
            if not task_id:
                # Task submission failed, attempt switching API key and retry
                if self.DEBUG:
                    print(f"Task submission failed, attempting to switch API key and retry")
                
                try:
                    # Import here to avoid circular import
                    from .key_manager import key_manager
                    # Mark current key invalid and get a new one
                    new_key = key_manager.mark_key_invalid(self.auth_token)
                    if new_key:
                        self.auth_token = new_key
                        if self.DEBUG:
                            print(f"Switched to a new API key, retrying task")
                        # Retry task submission with the new key
                        task_id = self._submit_task(payload, referer="https://sora.chatgpt.com/explore")
                        if not task_id:
                            return "Task submission failed (tried switching keys)"
                    else:
                        return "Task submission failed (no alternate keys available)"
                except ImportError:
                    if self.DEBUG:
                        print(f"Failed to import key_manager, cannot switch keys automatically")
                    return "Task submission failed"
                except Exception as e:
                    if self.DEBUG:
                        print(f"Error switching API keys: {str(e)}")
                    return f"Task submission failed: {str(e)}"
            
            if self.DEBUG:
                print(f"Task submitted, ID: {task_id}")
            # Poll task status until completion
            image_urls = self._poll_task_status(task_id)
            
            # If polling returns an error message, try switching key and retry
            if isinstance(image_urls, str) and any(k in image_urls.lower() for k in ["fail", "failed", "error"]):
                if self.DEBUG:
                    print(f"Task failed, attempting to switch API key and retry")
                
                try:
                    from .key_manager import key_manager
                    new_key = key_manager.mark_key_invalid(self.auth_token)
                    if new_key:
                        self.auth_token = new_key
                        if self.DEBUG:
                            print(f"Switched to a new API key, retrying the entire generation process")
                        # Retry the entire generation process with the new key
                        return self.generate_image(prompt, num_images, width, height)
                except (ImportError, Exception) as e:
                    if self.DEBUG:
                        print(f"Failed to switch API keys or retry: {str(e)}")
            
            # Image localization
            if Config.IMAGE_LOCALIZATION and isinstance(image_urls, list) and image_urls:
                if self.DEBUG:
                    print(f"\n================================")
                    print(f"Starting image localization")
                    print(f"Image localization config: enabled={Config.IMAGE_LOCALIZATION}, save dir={Config.IMAGE_SAVE_DIR}")
                    print(f"Number of images to localize: {len(image_urls)}")
                    print(f"Original image URLs: {image_urls}")
                    print(f"================================\n")
                
                try:
                    # Create an event loop and run image localization
                    if self.DEBUG:
                        print(f"Creating async event loop for image downloads...")
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    if self.DEBUG:
                        print(f"Calling localize_image_urls()...")
                    localized_urls = loop.run_until_complete(localize_image_urls(image_urls))
                    loop.close()
                    
                    if self.DEBUG:
                        print(f"\n================================")
                        print(f"Image localization completed")
                        print(f"Original URLs: {image_urls}")
                        print(f"Localized URLs: {localized_urls}")
                        print(f"================================\n")
                    
                    # Validate result
                    if not localized_urls:
                        if self.DEBUG:
                            print(f"❌ Warning: Localized URL list is empty. Returning original URLs")
                        return image_urls
                        
                    # Check if all URLs were properly localized
                    local_count = sum(1 for url in localized_urls if url.startswith("/static/") or "/static/" in url)
                    if local_count == 0:
                        if self.DEBUG:
                            print(f"❌ Warning: No URLs were successfully localized. Returning original URLs")
                        return image_urls
                    elif local_count < len(localized_urls):
                        if self.DEBUG:
                            print(f"⚠️ Note: Some URLs were not successfully localized ({local_count}/{len(localized_urls)})")
                        
                    return localized_urls
                except Exception as e:
                    if self.DEBUG:
                        print(f"❌ Error occurred during image localization: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    if self.DEBUG:
                        print(f"Returning original URLs due to the error")
                    return image_urls
            elif not Config.IMAGE_LOCALIZATION:
                if self.DEBUG:
                    print(f"Image localization disabled, returning original URLs")
            elif not isinstance(image_urls, list):
                if self.DEBUG:
                    print(f"Image generation returned a non-list result: {image_urls}, cannot localize")
            elif not image_urls:
                if self.DEBUG:
                    print(f"Image generation returned an empty list, nothing to localize")
            
            return image_urls
        except Exception as e:
            if self.DEBUG:
                print(f"❌ Error generating images: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"Error generating images: {str(e)}"
    
    def upload_image(self, file_path):
        """
        Upload a local image file to the Sora backend.
        Args:
        file_path (str): Local image file path.
        Returns:
        dict or str: Dict with upload info on success, or an error message string on failure.
        """
        if not os.path.exists(file_path):
            return f"Error: File not found '{file_path}'"
        file_name = os.path.basename(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type or not mime_type.startswith('image/'):
            return f"Error: Unable to determine file type or file is not an image '{file_path}' (Mime: {mime_type})"
        if self.DEBUG:
            print(f"Starting image upload: {file_name} (Type: {mime_type})")
        # For multipart/form-data, Content-Type header is set automatically by requests
        headers = self._get_dynamic_headers(content_type=None, referer="https://sora.chatgpt.com/library") # Referer from example
        
        # Attempt upload
        return self._try_upload_with_retry(file_path, file_name, mime_type, headers)
    
    def _try_upload_with_retry(self, file_path, file_name, mime_type, headers, is_retry=False):
        """Attempt to upload an image, with optional API key switch and retry on failure"""
        # Save the current API key to ensure the entire upload uses the same key
        current_auth_token = self.auth_token
        
        files = {
            'file': (file_name, open(file_path, 'rb'), mime_type),
            'file_name': (None, file_name) # The second field is the file name
        }
        try:
            response = self.scraper.post(
                self.upload_url,
                headers=headers,
                files=files, # Use the 'files' parameter to upload
                proxies=self.proxies,
                timeout=60 # Upload may take longer
            )
            if response.status_code == 200:
                result = response.json()
                if self.DEBUG:
                    print(f"Image uploaded successfully! Media ID: {result.get('id')}")
                # Ensure the response includes the API key used for upload
                result['used_auth_token'] = current_auth_token
                # print(f"Upload response: {json.dumps(result, indent=2)}") # Optional: full response
                return result # Dict containing id, url, etc.
            else:
                error_msg = f"Failed to upload image, status code: {response.status_code}, response: {response.text}"
                if self.DEBUG:
                    print(error_msg)
                
                # If not already retrying and response suggests an API key issue, try switching keys
                if not is_retry and (response.status_code in [401, 403] or "auth" in response.text.lower() or "token" in response.text.lower()):
                    if self.DEBUG:
                        print(f"Upload failure may be related to API key, attempting to switch key and retry")
                    
                    try:
                        from .key_manager import key_manager
                        new_key = key_manager.mark_key_invalid(self.auth_token)
                        if new_key:
                            self.auth_token = new_key
                            if self.DEBUG:
                                print(f"Switched to new API key, retrying upload")
                            # Update headers and retry
                            new_headers = self._get_dynamic_headers(content_type=None, referer="https://sora.chatgpt.com/library")
                            return self._try_upload_with_retry(file_path, file_name, mime_type, new_headers, is_retry=True)
                    except (ImportError, Exception) as e:
                        if self.DEBUG:
                            print(f"Failed to switch API key: {str(e)}")
                
                return error_msg
        except Exception as e:
            error_msg = f"Error uploading image: {str(e)}"
            if self.DEBUG:
                print(error_msg)
            
            # If not already retrying, try switching key and retry
            if not is_retry:
                if self.DEBUG:
                    print(f"Exception during upload, attempting to switch API key and retry")
                
                try:
                    from .key_manager import key_manager
                    new_key = key_manager.mark_key_invalid(self.auth_token)
                    if new_key:
                        self.auth_token = new_key
                        if self.DEBUG:
                            print(f"Switched to new API key, retrying upload")
                        # Update headers and retry
                        new_headers = self._get_dynamic_headers(content_type=None, referer="https://sora.chatgpt.com/library")
                        return self._try_upload_with_retry(file_path, file_name, mime_type, new_headers, is_retry=True)
                except (ImportError, Exception) as err:
                    if self.DEBUG:
                        print(f"Failed to switch API key: {str(err)}")
            
            return error_msg
        finally:
            # Ensure file handles are closed
            if 'file' in files and files['file'][1]:
                files['file'][1].close()
    
    def generate_image_remix(self, prompt, uploaded_media_id, num_images=1, width=None, height=None):
        """
        Generate new images by remixing an uploaded image.
        Args:
        prompt (str): Image generation prompt
        uploaded_media_id (str): Media ID from upload_image (e.g., "media_...")
        num_images (int): Number of images to generate
        width (int, optional): Output image width. If None, may be decided by API.
        height (int, optional): Output image height. If None, may be decided by API.
        Returns:
        list[str] or str: List of image URLs on success, or an error message string on failure
        """
        if self.DEBUG:
            print(f"Starting Remix (ID: {uploaded_media_id}) with prompt: '{prompt}'")
        
        # If a specific API key was used during upload, ensure we use the same key for remix
        # The result from upload_image may contain used_auth_token
        if isinstance(uploaded_media_id, dict) and 'id' in uploaded_media_id:
            if 'used_auth_token' in uploaded_media_id and uploaded_media_id['used_auth_token'] != self.auth_token:
                if self.DEBUG:
                    print(f"Detected a different API key used for upload; switching to the matching key for Remix")
                self.auth_token = uploaded_media_id['used_auth_token']
            uploaded_media_id = uploaded_media_id['id']
        
        # In real use we might query details for media_id; simplified here
        payload = {
            "prompt": prompt,
            "n_variants": num_images,
            "inpaint_items": [
                {
                    "type": "image",
                    "frame_index": 0,
                    "preset_id": None,
                    "generation_id": None,
                    "upload_media_id": uploaded_media_id, # Reference the uploaded image
                    "source_start_frame": 0,
                    "source_end_frame": 0,
                    "crop_bounds": None
                }
            ],
            "operation": "remix", # Operation type
            "type": "image_gen",
            "n_frames": 1,
            "width": 720, # Optional
            "height": 480 # Optional
        }
        # Only add these if provided
        if width is not None:
            payload["width"] = width
        if height is not None:
            payload["height"] = height
        try:
            # Use 'library' as referer when submitting task (consistent with examples)
            task_id = self._submit_task(payload, referer="https://sora.chatgpt.com/library")
            if not task_id:
                # Task submission failed, try switching keys and retry
                if self.DEBUG:
                    print(f"Remix task submission failed, attempting to switch API key and retry")
                
                try:
                    # Import here to avoid circular import
                    from .key_manager import key_manager
                    # Mark current key invalid and get a new key
                    new_key = key_manager.mark_key_invalid(self.auth_token)
                    if new_key:
                        self.auth_token = new_key
                        if self.DEBUG:
                            print(f"Switched to new API key, retrying Remix task")
                        # Retry submitting the task with new key
                        task_id = self._submit_task(payload, referer="https://sora.chatgpt.com/library")
                        if not task_id:
                            return "Remix task submission failed (tried switching keys)"
                    else:
                        return "Remix task submission failed (no alternate keys available)"
                except ImportError:
                    if self.DEBUG:
                        print(f"Failed to import key_manager, cannot switch keys automatically")
                    return "Remix task submission failed"
                except Exception as e:
                    if self.DEBUG:
                        print(f"Error switching API keys: {str(e)}")
                    return f"Remix task submission failed: {str(e)}"
            
            if self.DEBUG:
                print(f"Remix task submitted, ID: {task_id}")
            # Poll task status
            image_urls = self._poll_task_status(task_id)
            
            # If polling returns an error message, try switching keys and retry
            if isinstance(image_urls, str) and any(k in image_urls.lower() for k in ["fail", "failed", "error"]):
                if self.DEBUG:
                    print(f"Remix task failed, attempting to switch API key and retry")
                
                try:
                    from .key_manager import key_manager
                    new_key = key_manager.mark_key_invalid(self.auth_token)
                    if new_key:
                        self.auth_token = new_key
                        if self.DEBUG:
                            print(f"Switched to new API key, retrying the entire Remix process")
                        # Retry the entire process with the new key
                        return self.generate_image_remix(prompt, uploaded_media_id, num_images, width, height)
                except (ImportError, Exception) as e:
                    if self.DEBUG:
                        print(f"Failed to switch API keys or retry: {str(e)}")
            
            # Image localization support
            if image_urls and isinstance(image_urls, list):
                if Config.IMAGE_LOCALIZATION:
                    if self.DEBUG:
                        print(f"Localizing {len(image_urls)} images generated by Remix...")
                    # Create event loop and run image localization
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    localized_urls = loop.run_until_complete(localize_image_urls(image_urls))
                    loop.close()
                    
                    if self.DEBUG:
                        print(f"Remix image localization completed")
                    return localized_urls
            
            return image_urls
        except Exception as e:
            # If an exception occurs, also try switching keys and retry
            if self.DEBUG:
                print(f"Exception during Remix generation: {str(e)}, attempting to switch API key")
            
            try:
                from .key_manager import key_manager
                new_key = key_manager.mark_key_invalid(self.auth_token)
                if new_key:
                    self.auth_token = new_key
                    if self.DEBUG:
                        print(f"Switched to new API key, retrying the entire Remix process")
                    # Retry the entire generation process with the new key
                    return self.generate_image_remix(prompt, uploaded_media_id, num_images, width, height)
            except (ImportError, Exception) as err:
                if self.DEBUG:
                    print(f"Failed to switch API key or retry: {str(err)}")
            
            return f"Error generating Remix images: {str(e)}"
    
    def _submit_task(self, payload, referer="https://sora.chatgpt.com/explore"):
        """Submit a generation task (generic, accepts payload dict)"""
        headers = self._get_dynamic_headers(content_type="application/json", referer=referer)
        
        # Save current auth_token in case we need to release it later
        current_auth_token = self.auth_token
        
        try:
            # Try importing key_manager and mark the key as working
            try:
                from .key_manager import key_manager
                # Generate a temporary task ID to mark key working status
                temp_task_id = f"pending_task_{self._generate_random_id()}"
                key_manager.mark_key_as_working(self.auth_token, temp_task_id)
            except ImportError:
                if self.DEBUG:
                    print(f"Failed to import key_manager, cannot mark key as working")
            except Exception as e:
                if self.DEBUG:
                    print(f"Error marking key as working: {str(e)}")
                
            response = self.scraper.post(
                self.gen_url,
                headers=headers,
                json=payload,
                proxies=self.proxies,
                timeout=20 # Slightly increased timeout
            )
            if response.status_code == 200:
                try:
                    result = response.json()
                    task_id = result.get("id")
                    if task_id:
                        # Update the task ID to the actual assigned ID
                        try:
                            from .key_manager import key_manager
                            # Update working status with the real task ID
                            key_manager.release_key(self.auth_token)  # Release temporary ID first
                            key_manager.mark_key_as_working(self.auth_token, task_id)  # Re-mark with the real ID
                            if self.DEBUG:
                                print(f"Marked key as in use, task ID: {task_id}")
                        except (ImportError, Exception) as e:
                            if self.DEBUG:
                                print(f"Error updating key status: {str(e)}")
                        
                        return task_id
                    else:
                        # Task submitted successfully but no ID returned, release the key
                        try:
                            from .key_manager import key_manager
                            key_manager.release_key(self.auth_token)
                            if self.DEBUG:
                                print(f"Task submitted without returning ID, key released")
                        except (ImportError, Exception) as e:
                            if self.DEBUG:
                                print(f"Error releasing key: {str(e)}")
                        
                        # Check if response content indicates a possible API key issue
                        response_text = response.text.lower()
                        is_auth_issue = False
                        auth_keywords = ["authorization", "auth", "token", "permission", "unauthorized", "credentials", "login"]
                        
                        for keyword in auth_keywords:
                            if keyword in response_text:
                                is_auth_issue = True
                                break
                        
                        if is_auth_issue:
                            if self.DEBUG:
                                print(f"API response indicates a possible authentication issue, attempting to switch keys")
                            
                            try:
                                from .key_manager import key_manager
                                new_key = key_manager.mark_key_invalid(self.auth_token)
                                if new_key:
                                    self.auth_token = new_key
                                    if self.DEBUG:
                                        print(f"Switched to new API key, retrying request")
                                    # Retry the request with the new key
                                    return self._submit_task(payload, referer)
                            except ImportError:
                                if self.DEBUG:
                                    print(f"Failed to import key_manager, cannot switch keys automatically")
                            except Exception as e:
                                if self.DEBUG:
                                    print(f"Error switching API keys: {str(e)}")
                        
                        if self.DEBUG:
                            print(f"Task submitted successfully, but task ID not found in response. Response: {response.text}")
                        return None
                except json.JSONDecodeError:
                    # Release the key
                    try:
                        from .key_manager import key_manager
                        key_manager.release_key(self.auth_token)
                        if self.DEBUG:
                            print(f"JSON decode failed, key released")
                    except (ImportError, Exception) as e:
                        if self.DEBUG:
                            print(f"Error releasing key: {str(e)}")
                        
                    if self.DEBUG:
                        print(f"Task submitted successfully, but unable to parse response JSON. Status: {response.status_code}, Response: {response.text}")
                    return None
            else:
                # Release the key
                try:
                    from .key_manager import key_manager
                    key_manager.release_key(self.auth_token)
                    if self.DEBUG:
                        print(f"Request failed, key released")
                except (ImportError, Exception) as e:
                    if self.DEBUG:
                        print(f"Error releasing key: {str(e)}")
                
                if self.DEBUG:
                    print(f"Task submission failed, status code: {response.status_code}")
                if self.DEBUG:
                    print(f"Request payload: {json.dumps(payload)}")
                if self.DEBUG:
                    print(f"Response content: {response.text}")
                
                # Special handling for 429 (too many concurrent tasks)
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
                            print(f"Detected concurrency limit error; current key is processing other tasks. Getting a new key without disabling the current one")
                        try:
                            from .key_manager import key_manager
                            # Get a new available key without marking current one invalid
                            new_key = key_manager.get_key()
                            if new_key:
                                self.auth_token = new_key
                                if self.DEBUG:
                                    print(f"Acquired a new API key, retrying request")
                                # Retry with the new key
                                return self._submit_task(payload, referer)
                            else:
                                if self.DEBUG:
                                    print(f"No alternate keys available")
                        except (ImportError, Exception) as e:
                            if self.DEBUG:
                                print(f"Error getting new key: {str(e)}")
                        return None
                
                # Check for authentication failure (401/403) or other API key issues
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
                    # Exclude errors caused by concurrency limits
                    "concurrent" in response_text or 
                    "too many" in response_text or 
                    "wait" in response_text or
                    "progress" in response_text
                )
                
                if is_auth_issue:
                    if self.DEBUG:
                        print(f"API key may have expired, attempting to switch keys")
                    
                    try:
                        # Import here to avoid circular import
                        from .key_manager import key_manager
                        # Mark current key invalid and get a new one
                        new_key = key_manager.mark_key_invalid(self.auth_token)
                        if new_key:
                            self.auth_token = new_key
                            if self.DEBUG:
                                print(f"Switched to new API key, retrying request")
                            # Retry the request with the new key
                            return self._submit_task(payload, referer)
                    except ImportError:
                        if self.DEBUG:
                            print(f"Failed to import key_manager, cannot switch keys automatically")
                    except Exception as e:
                        if self.DEBUG:
                            print(f"Error switching API keys: {str(e)}")
                            
                return None
        except Exception as e:
            # Ensure the key is released
            try:
                from .key_manager import key_manager
                key_manager.release_key(current_auth_token)
                if self.DEBUG:
                    print(f"Exception occurred, key released")
            except (ImportError, Exception) as release_err:
                if self.DEBUG:
                    print(f"Error releasing key: {str(release_err)}")
                
            if self.DEBUG:
                print(f"Error submitting task: {str(e)}")
            
            # Check if the exception indicates a possible authentication issue
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
                    print(f"Exception suggests a possible API key issue, attempting to switch keys")
                
                try:
                    from .key_manager import key_manager
                    new_key = key_manager.mark_key_invalid(self.auth_token)
                    if new_key:
                        self.auth_token = new_key
                        if self.DEBUG:
                            print(f"Switched to new API key, retrying request")
                        # Retry the request with the new key
                        return self._submit_task(payload, referer)
                except (ImportError, Exception) as err:
                    if self.DEBUG:
                        print(f"Failed to switch API key: {str(err)}")
            
            return None
            
    def _poll_task_status(self, task_id, max_attempts=40, interval=5):
        """
        Poll task status until completion and return all generated image URLs.
        """
        # Save the current key so we can release it correctly at the end
        current_auth_token = self.auth_token
        
        if self.DEBUG:
            print(f"Polling status for task {task_id}...")
        try:
            for attempt in range(max_attempts):
                try:
                    headers = self._get_dynamic_headers(referer="https://sora.chatgpt.com/library") # Polling often happens from library view
                    query_url = f"{self.check_url}?limit=10" # Fetch recent tasks to reduce payload
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
                            # Find the matching task
                            for task in task_responses:
                                if task.get("id") == task_id:
                                    status = task.get("status")
                                    if self.DEBUG:
                                        print(f"  Task {task_id} status: {status} (attempt {attempt+1}/{max_attempts})")
                                    if status == "succeeded":
                                        # Task succeeded; release the key
                                        try:
                                            from .key_manager import key_manager
                                            key_manager.release_key(current_auth_token)
                                            if self.DEBUG:
                                                print(f"Task succeeded, key released")
                                        except (ImportError, Exception) as e:
                                            if self.DEBUG:
                                                print(f"Error releasing key: {str(e)}")
                                                
                                        generations = task.get("generations", [])
                                        image_urls = []
                                        if generations:
                                            for gen in generations:
                                                url = gen.get("url")
                                                if url:
                                                    image_urls.append(url)
                                        if image_urls:
                                            if self.DEBUG:
                                                print(f"Task {task_id} completed successfully! Found {len(image_urls)} images.")
                                            return image_urls
                                        else:
                                            if self.DEBUG:
                                                print(f"Task {task_id} is 'succeeded' but no valid image URLs were found in the response.")
                                            if self.DEBUG:
                                                print(f"Task details: {json.dumps(task, indent=2)}")
                                            return "Task succeeded but no image URLs were found"
                                    elif status == "failed":
                                        # Task failed; release the key
                                        try:
                                            from .key_manager import key_manager
                                            key_manager.release_key(current_auth_token)
                                            if self.DEBUG:
                                                print(f"Task failed, key released")
                                        except (ImportError, Exception) as e:
                                            if self.DEBUG:
                                                print(f"Error releasing key: {str(e)}")
                                                
                                        failure_reason = task.get("failure_reason", "unknown reason")
                                        if self.DEBUG:
                                            print(f"Task {task_id} failed: {failure_reason}")
                                        # Check if the failure may be caused by API key issues
                                        failure_reason_lower = failure_reason.lower()
                                        auth_keywords = [
                                            "authorization", "auth", "token", "permission", 
                                            "unauthorized", "credentials", "login", "invalid"
                                        ]
                                        is_auth_issue = any(keyword in failure_reason_lower for keyword in auth_keywords)
                                        
                                        if is_auth_issue:
                                            if self.DEBUG:
                                                print(f"Detected possible API key issue; attempting to switch keys")
                                            try:
                                                # Import here to avoid circular import
                                                from .key_manager import key_manager
                                                # Mark current key invalid and get a new one
                                                new_key = key_manager.mark_key_invalid(self.auth_token)
                                                if new_key:
                                                    self.auth_token = new_key
                                                    if self.DEBUG:
                                                        print(f"Switched to a new API key")
                                            except ImportError:
                                                if self.DEBUG:
                                                    print(f"Failed to import key_manager, cannot switch keys automatically")
                                            except Exception as e:
                                                if self.DEBUG:
                                                    print(f"Error switching API keys: {str(e)}")
                                            return f"Task failed: {failure_reason}"
                                    elif status in ["rejected", "needs_user_review"]:
                                        # Task rejected; release the key
                                        try:
                                            from .key_manager import key_manager
                                            key_manager.release_key(current_auth_token)
                                            if self.DEBUG:
                                                print(f"Task was rejected, key released")
                                        except (ImportError, Exception) as e:
                                            if self.DEBUG:
                                                print(f"Error releasing key: {str(e)}")
                                                
                                        if self.DEBUG:
                                            print(f"Task {task_id} was rejected or needs review: {status}")
                                        return f"Task rejected or needs review: {status}"
                                    # else status is pending, processing, etc. - continue polling
                                    break # Found the task, no need to check others in this response
                            else:
                                # Task ID not found in the recent list; continue waiting
                                if self.DEBUG:
                                    print(f"  Task {task_id} not found in recent list, waiting... (attempt {attempt+1}/{max_attempts})")
                        except json.JSONDecodeError:
                            if self.DEBUG:
                                print(f"Unable to parse JSON while checking task status. Status: {response.status_code}, Response: {response.text}")
                    else:
                        if self.DEBUG:
                            print(f"Failed to check task status, status: {response.status_code}, response: {response.text}")
                        
                        # Check for authentication failure or other possible API key issues
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
                                print(f"API key may have expired, attempting to switch keys")
                            
                            try:
                                # Import here to avoid circular import
                                from .key_manager import key_manager
                                # Mark current key invalid and get a new one
                                new_key = key_manager.mark_key_invalid(self.auth_token)
                                if new_key:
                                    self.auth_token = new_key
                                    if self.DEBUG:
                                        print(f"Switched to new API key, retrying request")
                                    # Continue polling with the new key
                                    continue
                            except ImportError:
                                if self.DEBUG:
                                    print(f"Failed to import key_manager, cannot switch keys automatically")
                            except Exception as e:
                                if self.DEBUG:
                                    print(f"Error switching API keys: {str(e)}")
                                    
                    time.sleep(interval)  # Wait before checking again
                except Exception as e:
                    if self.DEBUG:
                        print(f"Error while checking task status: {str(e)}")
                    
                    # Check if the exception suggests an authentication issue
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
                            print(f"Exception suggests a possible API key issue, attempting to switch keys")
                        
                        try:
                            from .key_manager import key_manager
                            new_key = key_manager.mark_key_invalid(self.auth_token)
                            if new_key:
                                self.auth_token = new_key
                                if self.DEBUG:
                                    print(f"Switched to new API key, retrying request")
                                # Reset current attempt and continue polling
                                continue
                        except (ImportError, Exception) as err:
                            if self.DEBUG:
                                print(f"Failed to switch API key: {str(err)}")
                    
                    # Add a slightly longer delay on error to avoid hammering the server
                    time.sleep(interval * 1.5)
            
            # If we have reached the max number of attempts, release the key
            try:
                from .key_manager import key_manager
                key_manager.release_key(current_auth_token)
                if self.DEBUG:
                    print(f"Polling timed out, key released")
            except (ImportError, Exception) as e:
                if self.DEBUG:
                    print(f"Error releasing key: {str(e)}")
                
            return f"Task {task_id} timed out ({max_attempts * interval} seconds), final status not obtained"
        except Exception as e:
            # Ensure the key is released on exception as well
            try:
                from .key_manager import key_manager
                key_manager.release_key(current_auth_token)
                if self.DEBUG:
                    print(f"Exception during polling, key released")
            except (ImportError, Exception) as release_err:
                if self.DEBUG:
                    print(f"Error releasing key: {str(release_err)}")
                
            if self.DEBUG:
                print(f"Unhandled exception while polling task status: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"Error while polling task status: {str(e)}"
    
    def test_connection(self):
        """
        Test if the API connection is valid by sending a lightweight request.
        Returns:
        dict: A dict containing the connection status information.
        """
        start_time = time.time()  # Record start time to compute response time
        success = False  # Initialize request result flag
        
        try:
            # Use a simple GET request to validate connectivity and authentication
            headers = self._get_dynamic_headers(referer="https://sora.chatgpt.com/explore")
            response = self.scraper.get(
                "https://sora.chatgpt.com/backend/parameters",
                headers=headers,
                proxies=self.proxies,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                # Check for key fields in the response to confirm API is valid
                api_valid = result.get("can_create_images") is not None or "limits_for_images" in result
                
                if api_valid:
                    success = True  # Mark success
                    # Record the request result (success)
                    try:
                        from .key_manager import key_manager
                        response_time = time.time() - start_time
                        key_manager.record_request_result(self.auth_token, success, response_time)
                    except (ImportError, Exception) as e:
                        if self.DEBUG:
                            print(f"Failed to record request result: {str(e)}")
                    
                    return {
                        "status": "success",
                        "message": "API connection test succeeded",
                        "data": result
                    }
                else:
                    # API returned 200 but data was not as expected
                    success = False  # Mark failure
                    
                    # Record the request result (failure)
                    try:
                        from .key_manager import key_manager
                        response_time = time.time() - start_time
                        key_manager.record_request_result(self.auth_token, success, response_time)
                    except (ImportError, Exception) as e:
                        if self.DEBUG:
                            print(f"Failed to record request result: {str(e)}")
                    
                    return {
                        "status": "error",
                        "message": "API connection test failed: response data format not as expected",
                        "response": result
                    }
            else:
                # Check for authentication failure or other API key issue
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
                
                success = False  # Mark failure
                
                # Record the request result (failure)
                try:
                    from .key_manager import key_manager
                    response_time = time.time() - start_time
                    key_manager.record_request_result(self.auth_token, success, response_time)
                except (ImportError, Exception) as e:
                    if self.DEBUG:
                        print(f"Failed to record request result: {str(e)}")
                
                if is_auth_issue:
                    if self.DEBUG:
                        print(f"API key may have expired, attempting to switch keys")
                    
                    try:
                        # Import here to avoid circular import
                        from .key_manager import key_manager
                        # Mark current key invalid and get a new one
                        new_key = key_manager.mark_key_invalid(self.auth_token)
                        if new_key:
                            self.auth_token = new_key
                            if self.DEBUG:
                                print(f"Switched to new API key, retrying connection test")
                            # Retry with the new key
                            return self.test_connection()
                    except ImportError:
                        if self.DEBUG:
                            print(f"Failed to import key_manager, cannot switch keys automatically")
                    except Exception as e:
                        if self.DEBUG:
                            print(f"Error switching API keys: {str(e)}")
                
                return {
                    "status": "error",
                    "message": f"API connection test failed, status code: {response.status_code}",
                    "response": response.text
                }
        except Exception as e:
            success = False  # Mark failure
            
            # Record the request result (exception/failure)
            try:
                from .key_manager import key_manager
                response_time = time.time() - start_time
                key_manager.record_request_result(self.auth_token, success, response_time)
            except (ImportError, Exception) as err:
                if self.DEBUG:
                    print(f"Failed to record request result: {str(err)}")
            
            # Check if the exception suggests an authentication issue
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
                    print(f"Exception suggests a possible API key issue, attempting to switch keys")
                
                try:
                    from .key_manager import key_manager
                    new_key = key_manager.mark_key_invalid(self.auth_token)
                    if new_key:
                        self.auth_token = new_key
                        if self.DEBUG:
                            print(f"Switched to new API key, retrying connection test")
                        # Retry with the new key
                        return self.test_connection()
                except (ImportError, Exception) as err:
                    if self.DEBUG:
                        print(f"Failed to switch API key: {str(err)}")
            
            raise Exception(f"API connection test failed: {str(e)}")