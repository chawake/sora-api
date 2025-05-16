import os
import logging
import dotenv
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from ..models.schemas import ApiKeyCreate, ApiKeyUpdate, ConfigUpdate, LogLevelUpdate
from ..api.dependencies import verify_admin, verify_admin_jwt
from ..config import Config
from ..key_manager import key_manager
from ..sora_integration import SoraClient

# 设置日志
logger = logging.getLogger("sora-api.admin")

# 日志系统配置
class LogConfig:
    LEVEL = os.getenv("LOG_LEVEL", "WARNING").upper()
    FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

# 创建路由
router = APIRouter(prefix="/api")

# 密钥管理API
@router.get("/keys")
async def get_all_keys(admin_token = Depends(verify_admin_jwt)):
    """获取所有API密钥"""
    return key_manager.get_all_keys()

@router.get("/keys/{key_id}")
async def get_key(key_id: str, admin_token = Depends(verify_admin_jwt)):
    """获取单个API密钥详情"""
    key = key_manager.get_key_by_id(key_id)
    if not key:
        raise HTTPException(status_code=404, detail="密钥不存在")
    return key

@router.post("/keys")
async def create_key(key_data: ApiKeyCreate, admin_token = Depends(verify_admin_jwt)):
    """创建新API密钥"""
    try:
        # 确保密钥值包含 Bearer 前缀
        key_value = key_data.key_value
        if not key_value.startswith("Bearer "):
            key_value = f"Bearer {key_value}"
            
        new_key = key_manager.add_key(
            key_value,
            name=key_data.name,
            weight=key_data.weight,
            rate_limit=key_data.rate_limit,
            is_enabled=key_data.is_enabled,
            notes=key_data.notes
        )
        
        # 通过Config永久保存所有密钥
        Config.save_api_keys(key_manager.keys)
        
        return new_key
    except Exception as e:
        logger.error(f"创建密钥失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/keys/{key_id}")
async def update_key(key_id: str, key_data: ApiKeyUpdate, admin_token = Depends(verify_admin_jwt)):
    """更新API密钥信息"""
    try:
        # 如果提供了新的密钥值，确保包含Bearer前缀
        key_value = key_data.key_value
        if key_value and not key_value.startswith("Bearer "):
            key_value = f"Bearer {key_value}"
            key_data.key_value = key_value
            
        updated_key = key_manager.update_key(
            key_id,
            key_value=key_data.key_value,
            name=key_data.name,
            weight=key_data.weight,
            rate_limit=key_data.rate_limit,
            is_enabled=key_data.is_enabled,
            notes=key_data.notes
        )
        if not updated_key:
            raise HTTPException(status_code=404, detail="密钥不存在")
        
        # 通过Config永久保存所有密钥
        Config.save_api_keys(key_manager.keys)
        
        return updated_key
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新密钥失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/keys/{key_id}")
async def delete_key(key_id: str, admin_token = Depends(verify_admin_jwt)):
    """删除API密钥"""
    success = key_manager.delete_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="密钥不存在")
    
    # 通过Config永久保存所有密钥
    Config.save_api_keys(key_manager.keys)
    
    return {"status": "success", "message": "密钥已删除"}

@router.get("/stats")
async def get_usage_stats(admin_token = Depends(verify_admin_jwt)):
    """获取API使用统计"""
    stats = key_manager.get_usage_stats()
    
    # 处理daily_usage数据，确保前端能够正确显示
    daily_usage = {}
    keys_usage = {}
    
    # 从past_7_days数据转换为daily_usage格式
    for date, counts in stats.get("past_7_days", {}).items():
        daily_usage[date] = counts.get("successful", 0) + counts.get("failed", 0)
    
    # 获取每个密钥的使用情况
    for key in key_manager.keys:
        key_id = key.get("id")
        key_name = key.get("name") or f"密钥_{key_id[:6]}"
        
        # 获取该密钥的使用统计
        if key_id in key_manager.usage_stats:
            key_stats = key_manager.usage_stats[key_id]
            total_requests = key_stats.get("total_requests", 0)
            
            if total_requests > 0:
                keys_usage[key_name] = total_requests
    
    # 添加到返回数据中
    stats["daily_usage"] = daily_usage
    stats["keys_usage"] = keys_usage
    
    return stats

@router.post("/keys/test")
async def test_key(key_data: ApiKeyCreate, admin_token = Depends(verify_admin_jwt)):
    """测试API密钥是否有效"""
    try:
        # 获取密钥值
        key_value = key_data.key_value.strip()
        
        # 确保密钥格式正确
        if not key_value.startswith("Bearer "):
            key_value = f"Bearer {key_value}"
        
        # 获取代理配置
        proxy_host = Config.PROXY_HOST if Config.PROXY_HOST and Config.PROXY_HOST.strip() else None
        proxy_port = Config.PROXY_PORT if Config.PROXY_PORT and Config.PROXY_PORT.strip() else None
        proxy_user = Config.PROXY_USER if Config.PROXY_USER and Config.PROXY_USER.strip() else None
        proxy_pass = Config.PROXY_PASS if Config.PROXY_PASS and Config.PROXY_PASS.strip() else None
        
        test_client = SoraClient(
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            proxy_user=proxy_user,
            proxy_pass=proxy_pass,
            auth_token=key_value
        )
        
        # 执行简单API调用测试连接
        test_result = await test_client.test_connection()
        logger.info(f"API密钥测试结果: {test_result}")
        
        # 检查底层测试结果的状态
        if test_result.get("status") == "success":
            # API连接测试成功
            return {
                "status": "success", 
                "message": "API密钥测试成功", 
                "details": test_result,
                "success": True
            }
        else:
            # API连接测试失败
            return {
                "status": "error", 
                "message": f"API密钥测试失败: {test_result.get('message', '连接失败')}", 
                "details": test_result,
                "success": False
            }
    except Exception as e:
        logger.error(f"测试密钥失败: {str(e)}", exc_info=True)
        return {
            "status": "error", 
            "message": f"API密钥测试失败: {str(e)}",
            "success": False
        }

@router.post("/keys/batch")
async def batch_operation(operation: Dict[str, Any], admin_token = Depends(verify_admin_jwt)):
    """批量操作API密钥"""
    action = operation.get("action")
    key_ids = operation.get("key_ids", [])
    
    if not action or not key_ids:
        raise HTTPException(status_code=400, detail="无效的请求参数")
    
    # 确保key_ids是一个列表
    if isinstance(key_ids, str):
        key_ids = [key_ids]
    
    results = {}
    
    if action == "enable":
        for key_id in key_ids:
            success = key_manager.update_key(key_id, is_enabled=True)
            results[key_id] = "success" if success else "failed"
    elif action == "disable":
        for key_id in key_ids:
            success = key_manager.update_key(key_id, is_enabled=False)
            results[key_id] = "success" if success else "failed"
    elif action == "delete":
        for key_id in key_ids:
            success = key_manager.delete_key(key_id)
            results[key_id] = "success" if success else "failed"
    else:
        raise HTTPException(status_code=400, detail="不支持的操作类型")
    
    # 通过Config永久保存所有密钥
    Config.save_api_keys(key_manager.keys)
    
    return {"status": "success", "results": results}

# 配置管理API
@router.get("/config")
async def get_config(admin_token = Depends(verify_admin_jwt)):
    """获取当前系统配置"""
    return {
        "HOST": Config.HOST,
        "PORT": Config.PORT,
        "BASE_URL": Config.BASE_URL,
        "PROXY_HOST": Config.PROXY_HOST,
        "PROXY_PORT": Config.PROXY_PORT,
        "PROXY_USER": Config.PROXY_USER,
        "PROXY_PASS": "******" if Config.PROXY_PASS else "",
        "IMAGE_LOCALIZATION": Config.IMAGE_LOCALIZATION,
        "IMAGE_SAVE_DIR": Config.IMAGE_SAVE_DIR,
        "API_AUTH_TOKEN": bool(Config.API_AUTH_TOKEN)  # 只返回是否设置，不返回实际值
    }

@router.post("/config")
async def update_config(config_data: ConfigUpdate, admin_token = Depends(verify_admin_jwt)):
    """更新系统配置"""
    try:
        changes = []
        
        # 更新代理设置
        if config_data.PROXY_HOST is not None:
            Config.PROXY_HOST = config_data.PROXY_HOST
            changes.append("PROXY_HOST")
            # 更新环境变量
            os.environ["PROXY_HOST"] = config_data.PROXY_HOST
            
        if config_data.PROXY_PORT is not None:
            Config.PROXY_PORT = config_data.PROXY_PORT
            changes.append("PROXY_PORT")
            # 更新环境变量
            os.environ["PROXY_PORT"] = config_data.PROXY_PORT
            
        # 更新代理认证设置
        if config_data.PROXY_USER is not None:
            Config.PROXY_USER = config_data.PROXY_USER
            changes.append("PROXY_USER")
            # 更新环境变量
            os.environ["PROXY_USER"] = config_data.PROXY_USER
            
        if config_data.PROXY_PASS is not None:
            Config.PROXY_PASS = config_data.PROXY_PASS
            changes.append("PROXY_PASS")
            # 更新环境变量
            os.environ["PROXY_PASS"] = config_data.PROXY_PASS
            
        # 更新图片本地化设置
        if config_data.IMAGE_LOCALIZATION is not None:
            Config.IMAGE_LOCALIZATION = config_data.IMAGE_LOCALIZATION
            changes.append("IMAGE_LOCALIZATION")
            # 更新环境变量
            os.environ["IMAGE_LOCALIZATION"] = str(config_data.IMAGE_LOCALIZATION)
            
        if config_data.IMAGE_SAVE_DIR is not None:
            Config.IMAGE_SAVE_DIR = config_data.IMAGE_SAVE_DIR
            changes.append("IMAGE_SAVE_DIR")
            # 更新环境变量
            os.environ["IMAGE_SAVE_DIR"] = config_data.IMAGE_SAVE_DIR
            # 确保目录存在
            os.makedirs(Config.IMAGE_SAVE_DIR, exist_ok=True)
            
        # 保存到.env文件
        if config_data.save_to_env and changes:
            env_file = os.path.join(Config.BASE_DIR, '.env')
            env_data = {}
            
            # 先读取现有的.env文件
            if os.path.exists(env_file):
                env_data = dotenv.dotenv_values(env_file)
                
            # 更新环境变量
            for field in changes:
                value = getattr(Config, field)
                env_data[field] = str(value)
                
            # 写入.env文件
            with open(env_file, 'w') as f:
                for key, value in env_data.items():
                    f.write(f"{key}={value}\n")
                    
            logger.info(f"已将配置保存到.env文件: {changes}")
        
        return {
            "status": "success", 
            "message": f"配置已更新: {', '.join(changes) if changes else '无变更'}"
        }
    except Exception as e:
        logger.error(f"更新配置失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"更新配置失败: {str(e)}")

@router.post("/logs/level")
async def update_log_level(data: LogLevelUpdate, admin_token = Depends(verify_admin_jwt)):
    """更新日志级别"""
    try:
        # 验证日志级别
        level = data.level.upper()
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        if level not in valid_levels:
            raise HTTPException(status_code=400, detail=f"无效的日志级别: {level}")
        
        # 更新根日志记录器的级别
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, level))
        
        # 同时更新sora-api模块的日志级别
        sora_logger = logging.getLogger("sora-api")
        sora_logger.setLevel(getattr(logging, level))
        
        # 记录日志级别变更
        logger.info(f"日志级别已更新为: {level}")
        
        # 如果需要，保存到环境变量
        if data.save_to_env:
            env_file = os.path.join(Config.BASE_DIR, '.env')
            env_data = {}
            
            # 先读取现有的.env文件
            if os.path.exists(env_file):
                env_data = dotenv.dotenv_values(env_file)
                
            # 更新LOG_LEVEL环境变量
            env_data["LOG_LEVEL"] = level
                
            # 写入.env文件
            with open(env_file, 'w') as f:
                for key, value in env_data.items():
                    f.write(f"{key}={value}\n")
            
            # 记录配置保存
            logger.info(f"已将日志级别保存到.env文件: LOG_LEVEL={level}")
        
        return {"status": "success", "message": f"日志级别已更新为: {level}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新日志级别失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"更新日志级别失败: {str(e)}")

# 管理员密钥API - 已移至app.py中