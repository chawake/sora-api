from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field

# 聊天完成请求模型
class ContentItem(BaseModel):
    type: str
    text: Optional[str] = None
    image_url: Optional[Dict[str, str]] = None

class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[ContentItem]]

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0
    frequency_penalty: Optional[float] = 0

# API密钥创建模型
class ApiKeyCreate(BaseModel):
    name: str = Field(..., description="密钥名称")
    key_value: str = Field(..., description="密钥值")
    weight: int = Field(1, description="权重")
    rate_limit: int = Field(60, description="速率限制(每分钟请求数)")
    is_enabled: bool = Field(True, description="是否启用")
    notes: Optional[str] = Field(None, description="备注")

# API密钥更新模型
class ApiKeyUpdate(BaseModel):
    name: Optional[str] = Field(None, description="密钥名称")
    key_value: Optional[str] = Field(None, description="密钥值")
    weight: Optional[int] = Field(None, description="权重")
    rate_limit: Optional[int] = Field(None, description="速率限制(每分钟请求数)")
    is_enabled: Optional[bool] = Field(None, description="是否启用")
    notes: Optional[str] = Field(None, description="备注")

# 系统配置更新模型
class ConfigUpdate(BaseModel):
    PROXY_HOST: Optional[str] = Field(None, description="代理服务器主机")
    PROXY_PORT: Optional[str] = Field(None, description="代理服务器端口")
    PROXY_USER: Optional[str] = Field(None, description="代理服务器用户名")
    PROXY_PASS: Optional[str] = Field(None, description="代理服务器密码")
    IMAGE_LOCALIZATION: Optional[bool] = Field(None, description="是否启用图片本地化存储")
    IMAGE_SAVE_DIR: Optional[str] = Field(None, description="图片保存目录")
    save_to_env: bool = Field(True, description="是否保存到环境变量文件")

# 日志级别更新模型
class LogLevelUpdate(BaseModel):
    level: str = Field(..., description="日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    save_to_env: bool = Field(True, description="是否保存到环境变量文件")

# JWT认证请求模型
class LoginRequest(BaseModel):
    admin_key: str = Field(..., description="管理员密钥")

# JWT令牌响应模型
class TokenResponse(BaseModel):
    token: str = Field(..., description="JWT令牌")
    expires_in: int = Field(..., description="有效期(秒)")
    token_type: str = Field("bearer", description="令牌类型") 