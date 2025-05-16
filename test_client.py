#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
import json
import time
import sys
import base64
import os

# 设置UTF-8编码
if sys.platform.startswith('win'):
    os.system("chcp 65001")
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

API_URL = "http://127.0.0.1:8890/v1/chat/completions"
API_KEY = "sk-123456"  # 替换为实际的API key

def test_text_to_image(prompt="生成一只可爱的猫咪", stream=False):
    """测试文本到图像生成"""
    print(f"\n===== 测试文本到图像生成 =====")
    try:
        print(f"提示词: '{prompt}'")
    except UnicodeEncodeError:
        print(f"提示词: [包含非ASCII字符]")
    print(f"流式响应: {stream}")
    
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
        print(f"错误: 状态码 {response.status_code}")
        print(response.text)
        return
    
    if stream:
        # 处理流式响应
        print("流式响应内容:")
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        print("[完成]")
                    else:
                        try:
                            json_data = json.loads(data)
                            if 'choices' in json_data and json_data['choices'] and 'delta' in json_data['choices'][0]:
                                delta = json_data['choices'][0]['delta']
                                if 'content' in delta:
                                    print(f"接收内容: {delta['content']}")
                        except Exception as e:
                            print(f"解析响应时出错: {e}")
    else:
        # 处理普通响应
        try:
            data = response.json()
            print(f"响应内容:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            if 'choices' in data and data['choices']:
                image_url = None
                content = data['choices'][0]['message']['content']
                if "![Generated Image](" in content:
                    image_url = content.split("![Generated Image](")[1].split(")")[0]
                    print(f"\n生成的图片URL: {image_url}")
        except Exception as e:
            print(f"解析响应时出错: {e}")
    
    elapsed = time.time() - start_time
    print(f"请求耗时: {elapsed:.2f}秒")

def test_image_to_image(image_path, prompt="将这张图片变成动漫风格"):
    """测试图像到图像生成（Remix）"""
    print(f"\n===== 测试图像到图像生成 =====")
    print(f"图片路径: '{image_path}'")
    print(f"提示词: '{prompt}'")
    
    # 读取并转换图片为base64
    try:
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        print(f"读取图片失败: {e}")
        return
    
    # 构建请求
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
        print(f"错误: 状态码 {response.status_code}")
        print(response.text)
        return
    
    # 处理响应
    try:
        data = response.json()
        print(f"响应内容:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        if 'choices' in data and data['choices']:
            image_url = None
            content = data['choices'][0]['message']['content']
            if "![Generated Image](" in content:
                image_url = content.split("![Generated Image](")[1].split(")")[0]
                print(f"\n生成的图片URL: {image_url}")
    except Exception as e:
        print(f"解析响应时出错: {e}")
    
    elapsed = time.time() - start_time
    print(f"请求耗时: {elapsed:.2f}秒")

def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python test_client.py <测试类型> [参数...]")
        print("测试类型:")
        print("  text2img <提示词> [stream=true/false]")
        print("  img2img <图片路径> <提示词>")
        return
    
    test_type = sys.argv[1].lower()
    
    if test_type == "text2img":
        prompt = sys.argv[2] if len(sys.argv) > 2 else "生成一只可爱的猫咪"
        stream = False
        if len(sys.argv) > 3 and sys.argv[3].lower() == "stream=true":
            stream = True
        test_text_to_image(prompt, stream)
    elif test_type == "img2img":
        if len(sys.argv) < 3:
            print("错误: 需要图片路径")
            return
        image_path = sys.argv[2]
        prompt = sys.argv[3] if len(sys.argv) > 3 else "将这张图片变成动漫风格"
        test_image_to_image(image_path, prompt)
    else:
        print(f"错误: 未知的测试类型 '{test_type}'")

if __name__ == "__main__":
    main() 