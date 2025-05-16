import time
import random
import uuid
import json
import os
import logging
from typing import Dict, List, Optional, Any, Union, Tuple, Callable

# 初始化日志
logger = logging.getLogger("sora-api.key_manager")

class KeyManager:
    def __init__(self, storage_file: str = "api_keys.json"):
        """
        初始化密钥管理器
        
        Args:
            storage_file: 密钥存储文件路径
        """
        self.keys = []  # 密钥列表
        self.storage_file = storage_file
        self.usage_stats = {}  # 使用统计
        self._load_keys()
        
    def _load_keys(self) -> None:
        """从环境变量或文件加载密钥"""
        keys_loaded = False
        
        # 先尝试从环境变量加载
        api_keys_str = os.getenv("API_KEYS", "")
        if api_keys_str:
            try:
                env_data = json.loads(api_keys_str)
                self._process_keys_data(env_data)
                if len(self.keys) > 0:
                    logger.info(f"已从环境变量加载 {len(self.keys)} 个密钥")
                    keys_loaded = True
                else:
                    logger.warning("环境变量API_KEYS存在但未包含有效密钥")
            except json.JSONDecodeError as e:
                logger.error(f"解析环境变量API keys失败: {str(e)}")
        
            # 如果环境变量未设置、解析失败或未加载到密钥，从文件加载
        if not keys_loaded:
            try:
                if os.path.exists(self.storage_file):
                    logger.info(f"尝试从文件加载密钥: {self.storage_file}")
                    with open(self.storage_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        keys_before = len(self.keys)
                        self._process_keys_data(data)
                        keys_loaded = len(self.keys) > keys_before
                        logger.info(f"已从文件加载 {len(self.keys) - keys_before} 个密钥")
                else:
                    logger.warning(f"密钥文件不存在: {self.storage_file}")
            except Exception as e:
                logger.error(f"加载密钥失败: {str(e)}")
                
        if len(self.keys) == 0:
            logger.warning("未能从环境变量或文件加载任何密钥")

        
    def _process_keys_data(self, data):
        """处理不同格式的密钥数据"""
        # 处理不同的数据格式
        if isinstance(data, list):
            # 旧版格式：直接是密钥列表
            raw_keys = data
            self.keys = []
            self.usage_stats = {}
            
            # 为每个密钥创建完整的记录
            for key_info in raw_keys:
                if isinstance(key_info, dict):
                    key_value = key_info.get("key")
                    if not key_value:
                        logger.warning(f"忽略无效密钥配置: {key_info}")
                        continue
                        
                    # 确保有ID
                    key_id = key_info.get("id") or str(uuid.uuid4())
                    
                    # 构建完整的密钥记录
                    key_record = {
                        "id": key_id,
                        "name": key_info.get("name", ""),
                        "key": key_value,
                        "weight": key_info.get("weight", 1),
                        "max_rpm": key_info.get("max_rpm", 60),
                        "requests": 0,
                        "last_reset": time.time(),
                        "available": key_info.get("is_enabled", True),
                        "is_enabled": key_info.get("is_enabled", True),
                        "created_at": key_info.get("created_at", time.time()),
                        "last_used": key_info.get("last_used"),
                        "notes": key_info.get("notes")
                    }
                    
                    self.keys.append(key_record)
                    
                    # 初始化使用统计
                    self.usage_stats[key_id] = {
                        "total_requests": 0,
                        "successful_requests": 0,
                        "failed_requests": 0,
                        "daily_usage": {},
                        "average_response_time": 0
                    }
                elif isinstance(key_info, str):
                    # 如果是字符串，直接作为密钥值
                    key_id = str(uuid.uuid4())
                    self.keys.append({
                        "id": key_id,
                        "name": "",
                        "key": key_info,
                        "weight": 1,
                        "max_rpm": 60,
                        "requests": 0,
                        "last_reset": time.time(),
                        "available": True,
                        "is_enabled": True,
                        "created_at": time.time(),
                        "last_used": None,
                        "notes": None
                    })
                    
                    # 初始化使用统计
                    self.usage_stats[key_id] = {
                        "total_requests": 0,
                        "successful_requests": 0,
                        "failed_requests": 0,
                        "daily_usage": {},
                        "average_response_time": 0
                    }
        else:
            # 新版格式：包含keys和usage_stats的字典
            self.keys = data.get('keys', [])
            self.usage_stats = data.get('usage_stats', {})
    
    def _save_keys(self) -> None:
        """保存密钥到文件"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'keys': self.keys,
                    'usage_stats': self.usage_stats
                }, f, ensure_ascii=False, indent=2)
                
            # 同时更新Config中的API_KEYS
            try:
                from .config import Config
                Config.API_KEYS = self.keys
            except (ImportError, AttributeError):
                logger.debug("无法更新Config中的API_KEYS")
        except Exception as e:
            logger.error(f"保存密钥失败: {str(e)}")
            
    def add_key(self, key_value: str, name: str = "", weight: int = 1, 
                rate_limit: int = 60, is_enabled: bool = True, notes: str = None) -> Dict[str, Any]:
        """
        添加密钥
        
        Args:
            key_value: 密钥值
            name: 密钥名称
            weight: 权重
            rate_limit: 速率限制(每分钟请求数)
            is_enabled: 是否启用
            notes: 备注
            
        Returns:
            添加的密钥信息
        """
        # 检查密钥是否已存在
        for key in self.keys:
            if key.get("key") == key_value:
                return key
            
        key_id = str(uuid.uuid4())
        new_key = {
            "id": key_id,
            "name": name,
            "key": key_value,
            "weight": weight,
            "max_rpm": rate_limit,
            "requests": 0,
            "last_reset": time.time(),
            "available": is_enabled,
            "is_enabled": is_enabled,
            "created_at": time.time(),
            "last_used": None,
            "notes": notes
        }
        self.keys.append(new_key)
        
        # 初始化使用统计
        self.usage_stats[key_id] = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "daily_usage": {},
            "average_response_time": 0
        }
        
        self._save_keys()
        logger.info(f"已添加密钥: {name or key_id}")
        return new_key
    
    def get_all_keys(self) -> List[Dict[str, Any]]:
        """获取所有密钥信息（已隐藏完整密钥值）"""
        result = []
        for key in self.keys:
            key_copy = key.copy()
            if "key" in key_copy:
                # 只显示密钥前6位和后4位
                full_key = key_copy["key"]
                if len(full_key) > 10:
                    key_copy["key"] = full_key[:6] + "..." + full_key[-4:]
            
            # 增加临时禁用信息的处理
            if key_copy.get("temp_disabled_until"):
                temp_disabled_until = key_copy["temp_disabled_until"]
                # 确保temp_disabled_until是时间戳格式
                if isinstance(temp_disabled_until, (int, float)):
                    # 转换为可读格式，但保留原始时间戳，让前端可以自行处理
                    disabled_until_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(temp_disabled_until))
                    key_copy["temp_disabled_until_formatted"] = disabled_until_date
                    key_copy["temp_disabled_remaining"] = int(temp_disabled_until - time.time())
            
            result.append(key_copy)
        return result
    
    def get_key_by_id(self, key_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取密钥信息"""
        for key in self.keys:
            if key.get("id") == key_id:
                return key
        return None
    
    def update_key(self, key_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        更新密钥信息
        
        Args:
            key_id: 密钥ID
            **kwargs: 要更新的字段
            
        Returns:
            更新后的密钥信息，未找到则返回None
        """
        for key in self.keys:
            if key.get("id") == key_id:
                # 更新提供的字段
                for field, value in kwargs.items():
                    if value is not None:
                        if field == "is_enabled":
                            key["available"] = value  # 同步更新available字段
                        key[field] = value
                
                self._save_keys()
                logger.info(f"已更新密钥: {key.get('name') or key_id}")
                return key
        
        logger.warning(f"未找到密钥: {key_id}")
        return None
    
    def delete_key(self, key_id: str) -> bool:
        """
        删除密钥
        
        Args:
            key_id: 密钥ID
            
        Returns:
            是否成功删除
        """
        original_length = len(self.keys)
        self.keys = [key for key in self.keys if key.get("id") != key_id]
        
        # 如果成功删除，保存密钥
        if len(self.keys) < original_length:
            self._save_keys()
            return True
            
        return False
    
    def batch_import_keys(self, keys_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        批量导入密钥
        
        Args:
            keys_data: 密钥数据列表，每个元素为包含密钥信息的字典
            
        Returns:
            导入结果统计
        """
        imported_count = 0
        skipped_count = 0
        
        # 获取现有密钥值
        existing_keys = {key.get("key") for key in self.keys}
        
        for key_data in keys_data:
            key_value = key_data.get("key")
            if not key_value:
                continue
                
            # 检查密钥是否已存在
            if key_value in existing_keys:
                skipped_count += 1
                continue
                
            # 添加新密钥
            key_id = str(uuid.uuid4())
            new_key = {
                "id": key_id,
                "name": key_data.get("name", ""),
                "key": key_value,
                "weight": key_data.get("weight", 1),
                "max_rpm": key_data.get("rate_limit", 60),
                "requests": 0,
                "last_reset": time.time(),
                "available": key_data.get("enabled", True),
                "is_enabled": key_data.get("enabled", True),
                "created_at": time.time(),
                "last_used": None,
                "notes": key_data.get("notes")
            }
            self.keys.append(new_key)
            existing_keys.add(key_value)  # 添加到已存在集合中
            
            # 初始化使用统计
            self.usage_stats[key_id] = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "daily_usage": {},
                "average_response_time": 0
            }
            
            imported_count += 1
            
        # 保存密钥
        if imported_count > 0:
            self._save_keys()
            
        return {
            "imported": imported_count,
            "skipped": skipped_count
        }
    
    def get_key(self) -> Optional[str]:
        """获取下一个可用的密钥"""
        if not self.keys:
            logger.warning("没有可用的密钥")
            return None
            
        # 重置计数器（如果需要）
        current_time = time.time()
        temporary_disabled_updated = False
        
        for key in self.keys:
            # 检查是否有被临时禁用的密钥需要重新启用
            if key.get("temp_disabled_until") and current_time > key.get("temp_disabled_until"):
                key["is_enabled"] = True
                key["available"] = True
                key["temp_disabled_until"] = None
                temporary_disabled_updated = True
                logger.info(f"密钥 {key.get('name') or key.get('id')} 的临时禁用已解除")
                
            if current_time - key["last_reset"] >= 60:
                key["requests"] = 0
                key["last_reset"] = current_time
                if not key.get("temp_disabled_until"):  # 只有未被临时禁用的密钥才会被重新激活
                    key["available"] = key.get("is_enabled", True)
        
        # 如果有任何临时禁用的密钥被更新，保存变更
        if temporary_disabled_updated:
            self._save_keys()
        
        # 筛选可用的密钥
        available_keys = [k for k in self.keys if k.get("available", False)]
        if not available_keys:
            logger.warning("没有可用的密钥（所有密钥都达到速率限制或被禁用）")
            return None
            
        # 根据权重选择密钥
        weights = [k.get("weight", 1) for k in available_keys]
        selected_idx = random.choices(range(len(available_keys)), weights=weights, k=1)[0]
        selected_key = available_keys[selected_idx]
        
        # 更新使用统计
        selected_key["requests"] += 1
        selected_key["last_used"] = current_time
        
        # 检查是否达到速率限制
        if selected_key["requests"] >= selected_key.get("max_rpm", 60):
            selected_key["available"] = False
        
        # 定期保存数据（10%的概率）
        if random.random() < 0.1:
            self._save_keys()
        
        # 确保返回的密钥包含"Bearer "前缀
        key_value = selected_key["key"]
        if not key_value.startswith("Bearer "):
            key_value = f"Bearer {key_value}"
        
        return key_value
    
    def record_request_result(self, key: str, success: bool, response_time: float = 0) -> None:
        """
        记录请求结果
        
        Args:
            key: 密钥值
            success: 请求是否成功
            response_time: 响应时间(秒)
        """
        if not key:
            logger.warning("记录请求结果失败：密钥为空")
            return
            
        # 去掉可能的Bearer前缀
        key_for_search = key.replace("Bearer ", "") if key.startswith("Bearer ") else key
        
        # 查找对应的密钥ID
        key_id = None
        key_info = None
        for k in self.keys:
            stored_key = k.get("key", "").replace("Bearer ", "") if k.get("key", "").startswith("Bearer ") else k.get("key", "")
            if stored_key == key_for_search:
                key_id = k.get("id")
                key_info = k
                break
                
        if not key_id:
            logger.warning(f"记录请求结果失败：未找到密钥 {key_for_search[:6]}...")
            return
            
        # 初始化usage_stats如果该密钥还没有统计数据
        if key_id not in self.usage_stats:
            self.usage_stats[key_id] = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "daily_usage": {},
                "average_response_time": 0
            }
            
        # 记录请求结果
        stats = self.usage_stats[key_id]
        stats["total_requests"] += 1
        
        if success:
            stats["successful_requests"] += 1
        else:
            stats["failed_requests"] += 1
            
        # 记录响应时间
        if response_time > 0:
            if stats["average_response_time"] == 0:
                stats["average_response_time"] = response_time
            else:
                # 使用加权平均
                old_avg = stats["average_response_time"]
                total = stats["total_requests"]
                # 避免 total 为0或1时产生问题，尽管前面 total_requests 已经增加了
                if total > 0:
                    stats["average_response_time"] = ((old_avg * (total - 1)) + response_time) / total
                else: # 理论上不应该发生，因为 total_requests 已经增加了
                    stats["average_response_time"] = response_time
                
        # 记录每日使用情况
        today = time.strftime("%Y-%m-%d")
        if today not in stats["daily_usage"]:
            stats["daily_usage"][today] = {"successful": 0, "failed": 0} # 初始化每日统计
        
        # 根据成功与否更新每日统计
        if success:
            stats["daily_usage"][today]["successful"] += 1
        else:
            stats["daily_usage"][today]["failed"] += 1
            
        # 保留最近30天的数据
        if len(stats["daily_usage"]) > 30:
            # 获取所有日期并排序，然后删除最早的
            sorted_dates = sorted(stats["daily_usage"].keys())
            if sorted_dates: # 确保列表不为空
                oldest_date = sorted_dates[0]
                del stats["daily_usage"][oldest_date]
                
        # 更新密钥的最后使用时间
        if key_info and "last_used" in key_info:
            key_info["last_used"] = time.time()
            
        # 保存统计数据，增加保存概率以确保统计更准确
        if random.random() < 0.25:  # 提高保存概率到25%
            self._save_keys()
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计信息"""
        total_keys = len(self.keys)
        active_keys = sum(1 for k in self.keys if k.get("is_enabled", False))
        available_keys = sum(1 for k in self.keys if k.get("available", False))
        
        total_requests = sum(stats.get("total_requests", 0) for stats in self.usage_stats.values())
        successful_requests = sum(stats.get("successful_requests", 0) for stats in self.usage_stats.values())
        
        # 计算成功率
        success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
        
        # 计算每个密钥的平均响应时间
        avg_response_times = [stats.get("average_response_time", 0) for stats in self.usage_stats.values() if stats.get("average_response_time", 0) > 0]
        overall_avg_response_time = sum(avg_response_times) / len(avg_response_times) if avg_response_times else 0
        
        # 获取过去7天的使用情况
        past_7_days = {}
        for key_id, stats in self.usage_stats.items():
            daily_usage = stats.get("daily_usage", {})
            for date, count_data in daily_usage.items():
                if date not in past_7_days:
                    past_7_days[date] = {"successful": 0, "failed": 0}
                # 正确处理字典类型的count_data
                past_7_days[date]["successful"] += count_data.get("successful", 0)
                past_7_days[date]["failed"] += count_data.get("failed", 0)
                
        # 只保留最近7天
        dates = sorted(past_7_days.keys(), reverse=True)[:7]
        past_7_days = {date: past_7_days[date] for date in dates}
        
        return {
            "total_keys": total_keys,
            "active_keys": active_keys,
            "available_keys": available_keys,
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "failed_requests": total_requests - successful_requests,
            "success_rate": success_rate,
            "average_response_time": overall_avg_response_time,
            "past_7_days": past_7_days
        } 

    def mark_key_invalid(self, key: str) -> Optional[str]:
        """
        将指定的密钥标记为无效（临时禁用而不是永久禁用），并返回一个新的可用密钥
        
        Args:
            key: API密钥值（可能包含Bearer前缀）
            
        Returns:
            Optional[str]: 新的可用密钥，如果没有可用密钥则返回None
        """
        # 调用临时禁用方法，设置24小时禁用时间
        return self.mark_key_temp_disabled(key, hours=24.0)
        
    def mark_key_temp_disabled(self, key: str, hours: float = 12.0) -> Optional[str]:
        """
        将指定的密钥临时禁用指定小时数，并返回一个新的可用密钥
        
        Args:
            key: API密钥值（可能包含Bearer前缀）
            hours: 禁用小时数
            
        Returns:
            Optional[str]: 新的可用密钥，如果没有可用密钥则返回None
        """
        # 去掉可能的Bearer前缀
        key_for_search = key.replace("Bearer ", "") if key.startswith("Bearer ") else key
        
        # 查找对应的密钥
        key_found = False
        disabled_key_id = None
        for key_info in self.keys:
            stored_key = key_info.get("key", "").replace("Bearer ", "") if key_info.get("key", "").startswith("Bearer ") else key_info.get("key", "")
            if stored_key == key_for_search:
                # 标记密钥为临时禁用
                disabled_until = time.time() + (hours * 3600)  # 当前时间加上禁用小时数
                key_info["available"] = False
                key_info["temp_disabled_until"] = disabled_until
                key_info["notes"] = (key_info.get("notes") or "") + f"\n[自动] 在 {time.strftime('%Y-%m-%d %H:%M:%S')} 被临时禁用{hours}小时"
                key_found = True
                disabled_key_id = key_info.get("id")
                logger.warning(f"密钥 {key_info.get('name') or key_info.get('id')} 被临时禁用{hours}小时")
                break
        
        if key_found:
            # 保存更改
            self._save_keys()
            
            # 获取新的密钥，排除已禁用的
            new_key = self.get_key()
            if new_key:
                logger.info(f"已自动切换到新的密钥")
                return new_key
            else:
                logger.warning("没有可用的备用密钥")
                # 如果没有其他可用密钥，重新启用这个密钥
                # if disabled_key_id:
                #     for key_info in self.keys:
                #         if key_info.get("id") == disabled_key_id:
                #             key_info["available"] = True
                #             key_info["temp_disabled_until"] = None
                #             key_info["notes"] = (key_info.get("notes") or "") + f"\n[自动] 在 {time.strftime('%Y-%m-%d %H:%M:%S')} 因无备用密钥而被重新启用"
                #             self._save_keys()
                #             logger.info(f"由于没有备用密钥，密钥 {key_info.get('name') or disabled_key_id} 被重新启用")
                #             key_value = key_info["key"]
                #             if not key_value.startswith("Bearer "):
                #                 key_value = f"Bearer {key_value}"
                #             return key_value
                return None
        else:
            logger.warning(f"未找到要临时禁用的密钥")
            return None
            
    def retry_request(self, original_key: str, request_func: Callable, max_retries: int = 1, 
                     max_key_switches: int = 3) -> Tuple[bool, Any, str]:
        """
        出错时自动重试请求，并在需要时切换密钥
        
        Args:
            original_key: 原始API密钥（可能包含Bearer前缀）
            request_func: 执行请求的函数，接受一个参数(密钥)并返回(成功标志, 结果)
            max_retries: 使用同一密钥的最大重试次数
            max_key_switches: 最大密钥切换次数
            
        Returns:
            Tuple[bool, Any, str]: (是否成功, 请求结果, 使用的密钥)
        """
        current_key = original_key
        current_key_switches = 0
        
        # 首先用原始密钥尝试
        for attempt in range(max_retries + 1):  # +1是因为第一次不算重试
            try:
                success, result = request_func(current_key)
                if success:
                    return True, result, current_key
                logger.warning(f"请求失败(尝试 {attempt+1}/{max_retries+1}): {result}")
            except Exception as e:
                logger.error(f"请求异常(尝试 {attempt+1}/{max_retries+1}): {str(e)}")
            
            # 如果这不是最后一次尝试，等待一秒后重试
            if attempt < max_retries:
                time.sleep(1)
                
        # 如果原始密钥的所有重试都失败，尝试切换密钥
        tried_keys = set([current_key.replace("Bearer ", "") if current_key.startswith("Bearer ") else current_key])
        
        while current_key_switches < max_key_switches:
            # 获取新的密钥
            new_key = self.get_key()
            if not new_key:
                logger.warning("没有更多可用的密钥")
                break
                
            # 确保不使用已经尝试过的密钥
            clean_new_key = new_key.replace("Bearer ", "") if new_key.startswith("Bearer ") else new_key
            if clean_new_key in tried_keys:
                continue
                
            tried_keys.add(clean_new_key)
            current_key = new_key
            current_key_switches += 1
            
            logger.info(f"切换到新密钥 (切换 {current_key_switches}/{max_key_switches})")
            
            # 用新密钥尝试
            for attempt in range(max_retries + 1):
                try:
                    success, result = request_func(current_key)
                    if success:
                        return True, result, current_key
                    logger.warning(f"使用新密钥请求失败(尝试 {attempt+1}/{max_retries+1}): {result}")
                except Exception as e:
                    logger.error(f"使用新密钥请求异常(尝试 {attempt+1}/{max_retries+1}): {str(e)}")
                
                # 如果这不是最后一次尝试，等待一秒后重试
                if attempt < max_retries:
                    time.sleep(1)
        
        # 所有尝试都失败，临时禁用原始密钥
        logger.error(f"所有重试和密钥切换尝试都失败，临时禁用原始密钥")
        self.mark_key_temp_disabled(original_key)
        
        # 返回最后一次尝试的结果
        return False, result, current_key

# 创建全局密钥管理器实例
storage_file = os.getenv("KEYS_STORAGE_FILE", "api_keys.json")
# 如果提供了绝对路径则直接使用，否则使用相对路径
if not os.path.isabs(storage_file):
    base_dir = os.getenv("BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    storage_file = os.path.join(base_dir, storage_file)

key_manager = KeyManager(storage_file=storage_file)
logger.info(f"初始化全局密钥管理器，存储文件: {storage_file}") 