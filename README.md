# OpenAI兼容的Sora API服务

这是一个为Sora提供OpenAI兼容接口的API服务。该服务使用cloudscraper绕过Cloudflare验证，支持多key轮询、并发处理和标准的OpenAI接口格式。

## 功能特点

- **OpenAI兼容接口**：完全兼容OpenAI的`/v1/chat/completions`接口
- **CF验证绕过**：使用cloudscraper库成功绕过Cloudflare验证
- **多key轮询**：支持多个Sora认证token，根据权重和速率限制智能选择
- **并发处理**：支持多个并发请求
- **流式响应**：支持SSE格式的流式响应
- **图像处理**：支持文本到图像生成和图像到图像生成（Remix）
- **异步处理**：支持异步生成图像，返回立即响应，防止请求超时
- **状态查询**：提供API端点查询异步任务的状态和结果
- **优化性能**：经过代码优化，提高请求处理速度和资源利用率
- **健康检查**：支持容器健康检查功能

## 环境要求

- Python 3.8+
- FastAPI 0.95.0+
- cloudscraper 1.2.71+
- 其他依赖见requirements.txt

## 快速部署指南

### 方法一：直接运行

1. 克隆仓库
   ```bash
   git clone https://github.com/1hei1/sora-api.git      
   cd sora-api
   ```

2. 安装依赖
   ```bash
   pip install -r requirements.txt
   ```

3. 配置API Keys（两种方式）
   - **方式1**: 创建api_keys.json文件
     ```json
     [
       {"key": "Bearer your-sora-token-1", "weight": 1, "max_rpm": 60},
       {"key": "Bearer your-sora-token-2", "weight": 2, "max_rpm": 60}
     ]
     ```
   - **方式2**: 设置环境变量
     ```bash
     # Linux/macOS
     export API_KEYS='[{"key": "Bearer your-sora-token-1", "weight": 1, "max_rpm": 60}, {"key": "Bearer your-sora-token-2", "weight": 2, "max_rpm": 60}]'
     
     # Windows (PowerShell)
     $env:API_KEYS='[{"key": "Bearer your-sora-token-1", "weight": 1, "max_rpm": 60}, {"key": "Bearer your-sora-token-2", "weight": 2, "max_rpm": 60}]'
     
     # Windows (CMD)
     set API_KEYS=[{"key": "Bearer your-sora-token-1", "weight": 1, "max_rpm": 60}, {"key": "Bearer your-sora-token-2", "weight": 2, "max_rpm": 60}]
     ```

4. 配置代理（可选，如果需要）
   ```bash
   # Linux/macOS - 基本代理
   export PROXY_HOST=127.0.0.1
   export PROXY_PORT=7890
   
   # Linux/macOS - 带认证的代理
   export PROXY_HOST=127.0.0.1
   export PROXY_PORT=7890
   export PROXY_USER=username
   export PROXY_PASS=password
   
   # Windows (PowerShell) - 基本代理
   $env:PROXY_HOST="127.0.0.1"
   $env:PROXY_PORT="7890"
   
   # Windows (PowerShell) - 带认证的代理
   $env:PROXY_HOST="127.0.0.1"
   $env:PROXY_PORT="7890"
   $env:PROXY_USER="username"
   $env:PROXY_PASS="password"
   
   # Windows (CMD) - 基本代理
   set PROXY_HOST=127.0.0.1
   set PROXY_PORT=7890
   
   # Windows (CMD) - 带认证的代理
   set PROXY_HOST=127.0.0.1
   set PROXY_PORT=7890
   set PROXY_USER=username
   set PROXY_PASS=password
   ```

5. 启动服务
   ```bash
   python run.py
   ```

6. 访问服务
   - API服务地址: http://localhost:8890
   - 健康检查: http://localhost:8890/health

### 方法二：Docker部署

1. 构建Docker镜像
   ```bash
   docker build -t sora-api .
   ```

2. 运行Docker容器（不同配置选项）

   **基本运行方式**:
   ```bash
   docker run -d -p 8890:8890 --name sora-api sora-api
   ```

   **使用预打包镜像**:
   ```bash
   docker run -d -p 8890:8890 --name sora-api 1hei1/sora-api:v0.1
   ```

   **使用预打包镜像并配置API密钥**:
   ```bash
   docker run -d -p 8890:8890 \
     -e API_KEYS='[{"key": "Bearer your-sora-token-1", "weight": 1, "max_rpm": 60}, {"key": "Bearer your-sora-token-2", "weight": 2, "max_rpm": 60}]' \
     --name sora-api \
     1hei1/sora-api:v0.1
   ```

   **使用预打包镜像并配置代理**:
   ```bash
   docker run -d -p 8890:8890 \
     -e API_KEYS='[{"key": "Bearer your-sora-token-1", "weight": 1, "max_rpm": 60}]' \
     -e PROXY_HOST=host.docker.internal \
     -e PROXY_PORT=7890 \
     --name sora-api \
     1hei1/sora-api:v0.1
   ```

   **带API密钥配置**:
   ```bash
   docker run -d -p 8890:8890 \
     -e API_KEYS='[{"key": "Bearer your-sora-token-1", "weight": 1, "max_rpm": 60}, {"key": "Bearer your-sora-token-2", "weight": 2, "max_rpm": 60}]' \
     --name sora-api \
     sora-api
   ```

   **带基本代理配置**:
   ```bash
   docker run -d -p 8890:8890 \
     -e API_KEYS='[{"key": "Bearer your-sora-token-1", "weight": 1, "max_rpm": 60}]' \
     -e PROXY_HOST=host.docker.internal \
     -e PROXY_PORT=7890 \
     --name sora-api \
     sora-api
   ```

   **带认证代理配置**:
   ```bash
   docker run -d -p 8890:8890 \
     -e API_KEYS='[{"key": "Bearer your-sora-token-1", "weight": 1, "max_rpm": 60}]' \
     -e PROXY_HOST=host.docker.internal \
     -e PROXY_PORT=7890 \
     -e PROXY_USER=username \
     -e PROXY_PASS=password \
     --name sora-api \
     sora-api
   ```

   **使用外部配置文件**:
   ```bash
   # 首先确保api_keys.json文件已正确配置
   docker run -d -p 8890:8890 \
     -v $(pwd)/api_keys.json:/app/api_keys.json \
     -e PROXY_HOST=host.docker.internal \
     -e PROXY_PORT=7890 \
     --name sora-api \
     sora-api
   ```

   **启用详细日志**:
   ```bash
   docker run -d -p 8890:8890 \
     -e API_KEYS='[{"key": "Bearer your-sora-token-1", "weight": 1, "max_rpm": 60}]' \
     -e VERBOSE_LOGGING=true \
     --name sora-api \
     sora-api
   ```

   **注意**: 在Docker中使用宿主机代理时，请使用`host.docker.internal`而不是`127.0.0.1`作为代理主机地址。

3. 检查容器状态
   ```bash
   docker ps
   docker logs sora-api
   ```

4. 停止和移除容器
   ```bash
   docker stop sora-api
   docker rm sora-api
   ```

## 环境变量说明

| 环境变量 | 描述 | 默认值 | 示例 |
|---------|------|--------|------|
| `API_HOST` | API服务监听地址 | `0.0.0.0` | `127.0.0.1` |
| `API_PORT` | API服务端口 | `8890` | `9000` |
| `BASE_URL` | API基础URL | `http://0.0.0.0:8890` | `https://api.example.com` |
| `PROXY_HOST` | HTTP代理主机 | 空（不使用代理） | `127.0.0.1` |
| `PROXY_PORT` | HTTP代理端口 | 空（不使用代理） | `7890` |
| `PROXY_USER` | HTTP代理用户名 | 空（不使用认证） | `username` |
| `PROXY_PASS` | HTTP代理密码 | 空（不使用认证） | `password` |
| `STATIC_DIR` | 静态文件目录 | `src/static` | `/data/static` |
| `IMAGE_SAVE_DIR` | 图片保存目录 | `src/static/images` | `/data/images` |
| `IMAGE_LOCALIZATION` | 是否启用图片本地化 | `False` | `True` |
| `API_KEYS` | API密钥配置（JSON格式） | 空 | `[{"key":"Bearer token", "weight":1, "max_rpm":60}]` |
| `ADMIN_KEY` | 管理员API密钥 | `sk-123456` | `sk-youradminkey` |
| `KEYS_STORAGE_FILE` | API密钥存储文件 | `api_keys.json` | `keys/my_keys.json` |
| `API_AUTH_TOKEN` | API认证令牌 | 空 | `your-auth-token` |
| `VERBOSE_LOGGING` | 是否启用详细日志 | `False` | `True` |

## API密钥配置说明

API密钥配置采用JSON格式，每个密钥包含以下属性：

- `key`: Sora认证令牌（必须包含Bearer前缀）
- `weight`: 轮询权重，数字越大被选中概率越高
- `max_rpm`: 每分钟最大请求数（速率限制）

示例:
```json
[
  {
    "key": "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjE5MzQ0ZTY1LWJiYzktNDRkMS1hOWQwLWY5NTdiMDc5YmQwZSIsInR5cCI6IkpXVCJ9...",
    "weight": 1,
    "max_rpm": 60
  },
  {
    "key": "Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6IjE5MzQ0ZTY1LWJiYzktNDRkMS1hOWQwLWY5NTdiMDc5YmQwZSIsInR5cCI6IkpXVCJ9...",
    "weight": 2,
    "max_rpm": 60
  }
]
```

## 使用示例

### 使用curl发送请求

```bash
# 文本到图像请求（非流式）
curl -X POST http://localhost:8890/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "sora-1.0",
    "messages": [
      {"role": "user", "content": "生成一只在草地上奔跑的金毛犬"}
    ],
    "n": 1,
    "stream": false
  }'

# 文本到图像请求（流式）
curl -X POST http://localhost:8890/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "sora-1.0",
    "messages": [
      {"role": "user", "content": "生成一只在草地上奔跑的金毛犬"}
    ],
    "n": 1,
    "stream": true
  }'

# 查询异步任务状态
curl -X GET http://localhost:8890/v1/generation/chatcmpl-123456789abcdef \
  -H "Authorization: Bearer your-api-key"
```

### 使用Python客户端

```python
import openai
import base64
import time

# 配置API key和基础URL
openai.api_key = "your-api-key"
openai.api_base = "http://localhost:8890/v1"

# 文本到图像请求（异步方式）
response = openai.ChatCompletion.create(
    model="sora-1.0",
    messages=[
        {"role": "user", "content": "生成一只在草地上奔跑的金毛犬"}
    ],
    n=1,
    stream=False
)

# 从异步响应中获取任务ID
request_id = response["id"]
print(f"任务已提交，ID: {request_id}")
print(f"初始状态: {response.choices[0].message.content}")

# 轮询检查任务状态
while True:
    print("检查任务状态...")
    try:
        result = openai.ChatCompletion.retrieve(
            model="sora-1.0",
            id=request_id
        )
        
        # 判断任务是否完成
        if result.choices[0].finish_reason == "stop":
            print("任务已完成!")
            print(f"结果: {result.choices[0].message.content}")
            break
        elif result.choices[0].finish_reason == "error":
            print(f"任务失败: {result.choices[0].message.content}")
            break
        else:
            print(f"任务仍在处理中: {result.choices[0].message.content}")
            time.sleep(5)  # 等待5秒后再次检查
    except Exception as e:
        print(f"检查任务状态时出错: {str(e)}")
        time.sleep(5)

# 图像到图像请求（Remix）
with open("dog.jpg", "rb") as image_file:
    base64_image = base64.b64encode(image_file.read()).decode('utf-8')

response = openai.ChatCompletion.create(
    model="sora-1.0",
    messages=[
        {"role": "user", "content": f"data:image/jpeg;base64,{base64_image}\n将这张图片变成卡通风格"}
    ],
    n=1,
    stream=False
)

# 获取任务ID并轮询结果
request_id = response["id"]
print(f"Remix任务已提交，ID: {request_id}")
# ... 轮询代码同上 ...
```

## 常见问题排查

1. **连接超时或无法连接**
   - 检查代理配置是否正确
   - 如使用代理认证，确认用户名密码正确
   - 确认Sora服务器是否可用
   - 检查本地网络连接

2. **API密钥加载失败**
   - 确认api_keys.json格式正确
   - 检查环境变量API_KEYS是否正确设置
   - 查看日志中的错误信息

3. **图片生成失败**
   - 确认Sora令牌有效性
   - 查看日志中的错误信息
   - 检查是否超出账户额度限制

4. **Docker容器启动失败**
   - 检查端口是否被占用
   - 确认环境变量设置正确
   - 查看Docker日志中的错误信息

## 性能优化

最新版本包含以下性能优化：

1. **代码重构**：简化了代码结构，提高可读性和可维护性
2. **内存优化**：减少不必要的内存使用，优化大型图像处理
3. **异步处理**：全面使用异步处理提高并发性能
4. **错误处理**：改进了错误处理和日志记录
5. **密钥管理**：优化了密钥轮询算法，提高了可靠性
6. **容器优化**：增强了Docker容器配置，支持健康检查

## 贡献

欢迎提交问题报告和改进建议！

## 许可证

MIT 
