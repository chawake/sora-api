from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field

# Chat completion request models
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

# API key creation model
class ApiKeyCreate(BaseModel):
    name: str = Field(..., description="Key name")
    key_value: str = Field(..., description="Key value")
    weight: int = Field(1, description="Weight")
    rate_limit: int = Field(60, description="Rate limit (requests per minute)")
    is_enabled: bool = Field(True, description="Enabled")
    notes: Optional[str] = Field(None, description="Notes")

# API key update model
class ApiKeyUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Key name")
    key_value: Optional[str] = Field(None, description="Key value")
    weight: Optional[int] = Field(None, description="Weight")
    rate_limit: Optional[int] = Field(None, description="Rate limit (requests per minute)")
    is_enabled: Optional[bool] = Field(None, description="Enabled")
    notes: Optional[str] = Field(None, description="Notes")

# Batch operation base model
class BatchOperation(BaseModel):
    action: str = Field(..., description="Operation type: import, enable, disable, delete")
    key_ids: Optional[List[str]] = Field(None, description="List of key IDs to operate on")

# Batch import key item model
class ImportKeyItem(BaseModel):
    name: str = Field(..., description="Key name")
    key: str = Field(..., description="Key value")
    weight: int = Field(1, description="Weight")
    rate_limit: int = Field(60, description="Rate limit (requests per minute)")
    enabled: bool = Field(True, description="Enabled")
    notes: Optional[str] = Field(None, description="Notes")

# Batch import operation model
class BatchImportOperation(BatchOperation):
    keys: List[ImportKeyItem] = Field(..., description="List of keys to import")
    key_ids: Optional[List[str]] = None

# System configuration update model
class ConfigUpdate(BaseModel):
    PROXY_HOST: Optional[str] = Field(None, description="Proxy server host")
    PROXY_PORT: Optional[str] = Field(None, description="Proxy server port")
    PROXY_USER: Optional[str] = Field(None, description="Proxy username")
    PROXY_PASS: Optional[str] = Field(None, description="Proxy password")
    BASE_URL: Optional[str] = Field(None, description="Base URL used for image access")
    IMAGE_LOCALIZATION: Optional[bool] = Field(None, description="Enable local image storage")
    IMAGE_SAVE_DIR: Optional[str] = Field(None, description="Image save directory")
    save_to_env: bool = Field(True, description="Save to environment variable file")

# Log level update model
class LogLevelUpdate(BaseModel):
    level: str = Field(..., description="Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL")
    save_to_env: bool = Field(True, description="Save to environment variable file")

# JWT authentication request model
class LoginRequest(BaseModel):
    admin_key: str = Field(..., description="Admin key")

# JWT token response model
class TokenResponse(BaseModel):
    token: str = Field(..., description="JWT token")
    expires_in: int = Field(..., description="Expiration (seconds)")
    token_type: str = Field("bearer", description="Token type")