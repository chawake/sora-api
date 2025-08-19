#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import json
import time
import sys
import base64
import os

# Set UTF-8 encoding
if sys.platform.startswith('win'):
    os.system("chcp 65001")
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

API_URL = "http://127.0.0.1:8890/v1/chat/completions"
API_KEY = "sk-123456"  # Replace with your actual API key

def test_text_to_image(prompt="Generate a cute cat", stream=False):
    """Test text-to-image generation"""
    print(f"\n===== Test: Text-to-Image Generation =====")
    try:
        print(f"Prompt: '{prompt}'")
    except UnicodeEncodeError:
        print(f"Prompt: [contains non-ASCII characters]")
    print(f"Streaming: {stream}")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    payload = {
        "model": "sora-1.0",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "n": 1,
        "stream": stream
    }
    
    start_time = time.time()
    response = requests.post(
        API_URL,
        headers=headers,
        json=payload,
        stream=stream
    )
    
    if response.status_code != 200:
        print(f"Error: status code {response.status_code}")
        print(response.text)
        return
    
    if stream:
        # Handle streaming response
        print("Streaming response:")
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        print("[DONE]")
                    else:
                        try:
                            json_data = json.loads(data)
                            if 'choices' in json_data and json_data['choices'] and 'delta' in json_data['choices'][0]:
                                delta = json_data['choices'][0]['delta']
                                if 'content' in delta:
                                    print(f"Content: {delta['content']}")
                        except Exception as e:
                            print(f"Error parsing response: {e}")
    else:
        # Handle normal (non-streaming) response
        try:
            data = response.json()
            print(f"Response:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            if 'choices' in data and data['choices']:
                image_url = None
                content = data['choices'][0]['message']['content']
                if "![Generated Image](" in content:
                    image_url = content.split("![Generated Image](")[1].split(")")[0]
                    print(f"\nGenerated image URL: {image_url}")
        except Exception as e:
            print(f"Error parsing response: {e}")
    
    elapsed = time.time() - start_time
    print(f"Elapsed: {elapsed:.2f}s")

def test_image_to_image(image_path, prompt="Transform this image to anime style"):
    """Test image-to-image generation (Remix)"""
    print(f"\n===== Test: Image-to-Image Generation =====")
    print(f"Image path: '{image_path}'")
    print(f"Prompt: '{prompt}'")
    
    # Read and encode image to base64
    try:
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"Failed to read image: {e}")
        return
    
    # Build request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    payload = {
        "model": "sora-1.0",
        "messages": [
            {"role": "user", "content": f"data:image/jpeg;base64,{base64_image}\n{prompt}"}
        ],
        "n": 1,
        "stream": False
    }
    
    start_time = time.time()
    response = requests.post(
        API_URL,
        headers=headers,
        json=payload
    )
    
    if response.status_code != 200:
        print(f"Error: status code {response.status_code}")
        print(response.text)
        return
    
    # Handle response
    try:
        data = response.json()
        print(f"Response:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        if 'choices' in data and data['choices']:
            image_url = None
            content = data['choices'][0]['message']['content']
            if "![Generated Image](" in content:
                image_url = content.split("![Generated Image](")[1].split(")")[0]
                print(f"\nGenerated image URL: {image_url}")
    except Exception as e:
        print(f"Error parsing response: {e}")
    
    elapsed = time.time() - start_time
    print(f"Elapsed: {elapsed:.2f}s")

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python test_client.py <test_type> [args...]")
        print("Test types:")
        print("  text2img <prompt> [stream=true/false]")
        print("  img2img <image_path> <prompt>")
        return
    
    test_type = sys.argv[1].lower()
    
    if test_type == "text2img":
        prompt = sys.argv[2] if len(sys.argv) > 2 else "Generate a cute cat"
        stream = False
        if len(sys.argv) > 3 and sys.argv[3].lower() == "stream=true":
            stream = True
        test_text_to_image(prompt, stream)
    elif test_type == "img2img":
        if len(sys.argv) < 3:
            print("Error: image path required")
            return
        image_path = sys.argv[2]
        prompt = sys.argv[3] if len(sys.argv) > 3 else "Transform this image to anime style"
        test_image_to_image(image_path, prompt)
    else:
        print(f"Error: unknown test type '{test_type}'")

if __name__ == "__main__":
    main()