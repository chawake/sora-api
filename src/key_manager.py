import time
import random
import uuid
import json
import os
import logging
import threading
from typing import Dict, List, Optional, Any, Union, Tuple, Callable

# Initialize logger
logger = logging.getLogger("sora-api.key_manager")

class KeyManager: 
    def __init__(self, storage_file: str = "api_keys.json"):
        """
        Initialize the API key manager.
        
        Args:
            storage_file: Path to the key storage file
        """
        self.keys = []  # List of API keys
        self.storage_file = storage_file
        self.usage_stats = {}  # Usage statistics
        self._lock = threading.RLock()  # Reentrant lock to support concurrent access
        self._working_keys = {}  # Track keys currently in use {key_value: task_id}
        self._load_keys()
        
    def _load_keys(self) -> None:
        """Load API keys from environment variables or a file."""
        keys_loaded = False
        
        # Try environment variable first
        api_keys_str = os.getenv("API_KEYS", "")
        if api_keys_str:
            try:
                env_data = json.loads(api_keys_str)
                self._process_keys_data(env_data)
                if len(self.keys) > 0:
                    logger.info(f"Loaded {len(self.keys)} keys from environment variables")
                    keys_loaded = True
                else:
                    logger.warning("Environment variable API_KEYS exists but contains no valid keys")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse API_KEYS from environment: {str(e)}")
        
            # If env var is not set, parsing failed, or no keys loaded, load from file
        if not keys_loaded:
            try:
                if os.path.exists(self.storage_file):
                    logger.info(f"Attempting to load keys from file: {self.storage_file}")
                    with open(self.storage_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        keys_before = len(self.keys)
                        self._process_keys_data(data)
                        keys_loaded = len(self.keys) > keys_before
                        logger.info(f"Loaded {len(self.keys) - keys_before} keys from file")
                else:
                    logger.warning(f"Key storage file does not exist: {self.storage_file}")
            except Exception as e:
                logger.error(f"Failed to load keys: {str(e)}")
                
        if len(self.keys) == 0:
            logger.warning("No API keys were loaded from environment or file")

        
    def _process_keys_data(self, data):
        """Process API key data in different supported formats."""
        # Handle multiple data formats
        if isinstance(data, list):
            # Legacy format: a direct list of keys
            raw_keys = data
            self.keys = []
            self.usage_stats = {}
            
            # Create a complete record for each key
            for key_info in raw_keys:
                if isinstance(key_info, dict):
                    key_value = key_info.get("key")
                    if not key_value:
                        logger.warning(f"Ignoring invalid key config: {key_info}")
                        continue
                        
                    # Ensure an ID
                    key_id = key_info.get("id") or str(uuid.uuid4())
                    
                    # Build full key record
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
                    
                    # Initialize usage stats
                    self.usage_stats[key_id] = {
                        "total_requests": 0,
                        "successful_requests": 0,
                        "failed_requests": 0,
                        "daily_usage": {},
                        "average_response_time": 0
                    }
                elif isinstance(key_info, str):
                    # If it's a string, use directly as the key value
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
                    
                    # Initialize usage stats
                    self.usage_stats[key_id] = {
                        "total_requests": 0,
                        "successful_requests": 0,
                        "failed_requests": 0,
                        "daily_usage": {},
                        "average_response_time": 0
                    }
        else:
            # New format: dict with 'keys' and 'usage_stats'
            self.keys = data.get('keys', [])
            self.usage_stats = data.get('usage_stats', {})
    
    def _save_keys(self) -> None:
        """Persist keys and usage stats to file."""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'keys': self.keys,
                    'usage_stats': self.usage_stats
                }, f, ensure_ascii=False, indent=2)
                
            # Also update Config.API_KEYS
            try:
                from .config import Config
                Config.API_KEYS = self.keys
            except (ImportError, AttributeError):
                logger.debug("Unable to update API_KEYS in Config")
        except Exception as e:
            logger.error(f"Failed to save keys: {str(e)}")
            
    def add_key(self, key_value: str, name: str = "", weight: int = 1, 
                rate_limit: int = 60, is_enabled: bool = True, notes: str = None) -> Dict[str, Any]:
        """
        Add a new API key.
        
        Args:
            key_value: API key value
            name: Key name
            weight: Selection weight
            rate_limit: Requests per minute
            is_enabled: Whether the key is enabled
            notes: Notes
            
        Returns:
            The added key record
        """
        with self._lock:  # Protect add with lock
            # Check if key already exists
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
            
            # Initialize usage stats
            self.usage_stats[key_id] = {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "daily_usage": {},
                "average_response_time": 0
            }
            
            self._save_keys()
            logger.info(f"Added API key: {name or key_id}")
            return new_key
    
    def get_all_keys(self) -> List[Dict[str, Any]]:
        """Get all key records (masking the full key value)."""
        with self._lock:  # Protect read with lock
            result = []
            for key in self.keys:
                key_copy = key.copy()
                if "key" in key_copy:
                    # Show only first 6 and last 4 characters
                    full_key = key_copy["key"]
                    if len(full_key) > 10:
                        key_copy["key"] = full_key[:6] + "..." + full_key[-4:]
                
                # Enrich with temporary disable information if present
                if key_copy.get("temp_disabled_until"):
                    temp_disabled_until = key_copy["temp_disabled_until"]
                    # Ensure it's a timestamp
                    if isinstance(temp_disabled_until, (int, float)):
                        # Add a human-readable copy while keeping the raw timestamp
                        disabled_until_date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(temp_disabled_until))
                        key_copy["temp_disabled_until_formatted"] = disabled_until_date
                        key_copy["temp_disabled_remaining"] = int(temp_disabled_until - time.time())
                
                result.append(key_copy)
            return result
    
    def get_key_by_id(self, key_id: str) -> Optional[Dict[str, Any]]:
        """Get a key record by its ID."""
        with self._lock:  # Protect read with lock
            for key in self.keys:
                if key.get("id") == key_id:
                    return key
            return None
    
    def update_key(self, key_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Update a key record.
        
        Args:
            key_id: Key ID
            **kwargs: Fields to update
            
        Returns:
            Updated key record, or None if not found
        """
        with self._lock:  # Protect update with lock
            for key in self.keys:
                if key.get("id") == key_id:
                    # Apply provided fields
                    for field, value in kwargs.items():
                        if value is not None:
                            if field == "is_enabled":
                                key["available"] = value  # Keep 'available' in sync
                            key[field] = value
                    
                    self._save_keys()
                    logger.info(f"Updated API key: {key.get('name') or key_id}")
                    return key
            
            logger.warning(f"Key not found: {key_id}")
            return None
    
    def delete_key(self, key_id: str) -> bool:
        """
        Delete a key record.
        
        Args:
            key_id: Key ID
            
        Returns:
            True if deleted, False otherwise
        """
        with self._lock:  # Protect delete with lock
            original_length = len(self.keys)
            self.keys = [key for key in self.keys if key.get("id") != key_id]
            
            # Persist if deletion happened
            if len(self.keys) < original_length:
                self._save_keys()
                return True
                
            return False
    
    def batch_import_keys(self, keys_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Batch import API keys.
        
        Args:
            keys_data: List of dicts each containing key info
            
        Returns:
            A summary dict with counts imported and skipped
        """
        with self._lock:  # Protect import with lock
            imported_count = 0
            skipped_count = 0
            
            # Gather existing key values
            existing_keys = {key.get("key") for key in self.keys}
            
            for key_data in keys_data:
                key_value = key_data.get("key")
                if not key_value:
                    continue
                    
                # Skip if key already exists
                if key_value in existing_keys:
                    skipped_count += 1
                    continue
                    
                # Add new key
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
                existing_keys.add(key_value)  # Track in the existing set
                
                # Initialize usage stats
                self.usage_stats[key_id] = {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "failed_requests": 0,
                    "daily_usage": {},
                    "average_response_time": 0
                }
                
                imported_count += 1
                
            # Persist keys
            if imported_count > 0:
                self._save_keys()
                
            return {
                "imported": imported_count,
                "skipped": skipped_count
            }
    
    def get_key(self) -> Optional[str]:
        """Get the next available API key."""
        with self._lock:  # Protect entire selection with lock
            if not self.keys:
                logger.warning("No API keys available")
                return None
                
            # Reset counters if needed
            current_time = time.time()
            temporary_disabled_updated = False
            
            for key in self.keys:
                # Re-enable temporarily disabled keys whose time has passed
                if key.get("temp_disabled_until") and current_time > key.get("temp_disabled_until"):
                    key["is_enabled"] = True
                    key["available"] = True
                    key["temp_disabled_until"] = None
                    temporary_disabled_updated = True
                    logger.info(f"Temporary disable lifted for key {key.get('name') or key.get('id')}")
                    
                if current_time - key["last_reset"] >= 60:
                    key["requests"] = 0
                    key["last_reset"] = current_time
                    if not key.get("temp_disabled_until"):  # Only re-activate if not temp-disabled
                        key["available"] = key.get("is_enabled", True)
            
            # Persist if any temp-disabled keys were updated
            if temporary_disabled_updated:
                self._save_keys()
            
            # Filter available keys, excluding those currently working
            available_keys = []
            for k in self.keys:
                key_value = k.get("key", "")
                clean_key = key_value.replace("Bearer ", "") if key_value.startswith("Bearer ") else key_value
                
                # Check if this key is in working set
                is_working = clean_key in self._working_keys
                
                if k.get("available", False) and not is_working:
                    available_keys.append(k)
            
            if not available_keys:
                logger.warning("No available keys (all are rate-limited, disabled, or currently in use)")
                return None
                
            # Weighted random selection
            weights = [k.get("weight", 1) for k in available_keys]
            selected_idx = random.choices(range(len(available_keys)), weights=weights, k=1)[0]
            selected_key = available_keys[selected_idx]
            
            # Update usage counters
            selected_key["requests"] += 1
            selected_key["last_used"] = current_time
            
            # Check and mark rate limit
            if selected_key["requests"] >= selected_key.get("max_rpm", 60):
                selected_key["available"] = False
            
            # Persist every time to ensure accuracy in concurrent environments
            self._save_keys()
            
            # Ensure returned key has the "Bearer " prefix
            key_value = selected_key["key"]
            if not key_value.startswith("Bearer "):
                key_value = f"Bearer {key_value}"
            
            return key_value
    
    def record_request_result(self, key: str, success: bool, response_time: float = 0) -> None:
        """
        Record the result of a request.
        
        Args:
            key: API key value
            success: Whether the request succeeded
            response_time: Response time in seconds
        """
        if not key:
            logger.warning("Failed to record request result: key is empty")
            return
            
        with self._lock:  # Protect recording with lock
            # Strip optional Bearer prefix
            key_for_search = key.replace("Bearer ", "") if key.startswith("Bearer ") else key
            
            # Find the matching key ID
            key_id = None
            key_info = None
            for k in self.keys:
                stored_key = k.get("key", "").replace("Bearer ", "") if k.get("key", "").startswith("Bearer ") else k.get("key", "")
                if stored_key == key_for_search:
                    key_id = k.get("id")
                    key_info = k
                    break
            
            if not key_id:
                logger.warning(f"Failed to record request result: key not found {key_for_search[:6]}...")
                return
            
            # Initialize usage_stats if missing
            if key_id not in self.usage_stats:
                self.usage_stats[key_id] = {
                    "total_requests": 0,
                    "successful_requests": 0,
                    "failed_requests": 0,
                    "daily_usage": {},
                    "average_response_time": 0
                }
            
            # Update request counters
            stats = self.usage_stats[key_id]
            stats["total_requests"] += 1
            
            if success:
                stats["successful_requests"] += 1
            else:
                stats["failed_requests"] += 1
            
            # Update response time average
            if response_time > 0:
                if stats["average_response_time"] == 0:
                    stats["average_response_time"] = response_time
                else:
                    # Weighted average
                    old_avg = stats["average_response_time"]
                    total = stats["total_requests"]
                    # Guard against edge cases (total already incremented above)
                    if total > 0:
                        stats["average_response_time"] = ((old_avg * (total - 1)) + response_time) / total
                    else: # Should not happen
                        stats["average_response_time"] = response_time
            
            # Record daily usage
            today = time.strftime("%Y-%m-%d")
            if today not in stats["daily_usage"]:
                stats["daily_usage"][today] = {"successful": 0, "failed": 0} # Initialize
            
            # Update today's counters
            if success:
                stats["daily_usage"][today]["successful"] += 1
            else:
                stats["daily_usage"][today]["failed"] += 1
            
            # Keep the last 30 days
            if len(stats["daily_usage"]) > 30:
                # Remove the oldest date
                sorted_dates = sorted(stats["daily_usage"].keys())
                if sorted_dates: # Ensure not empty
                    oldest_date = sorted_dates[0]
                    del stats["daily_usage"][oldest_date]
            
            # Update key's last used timestamp
            if key_info and "last_used" in key_info:
                key_info["last_used"] = time.time()
            
            # Persist every time to ensure accuracy in concurrent environments
            self._save_keys()
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get aggregated usage statistics."""
        with self._lock:  # Protect read with lock
            total_keys = len(self.keys)
            active_keys = sum(1 for k in self.keys if k.get("is_enabled", False))
            available_keys = sum(1 for k in self.keys if k.get("available", False))
            
            total_requests = sum(stats.get("total_requests", 0) for stats in self.usage_stats.values())
            successful_requests = sum(stats.get("successful_requests", 0) for stats in self.usage_stats.values())
            
            # Success rate
            success_rate = (successful_requests / total_requests * 100) if total_requests > 0 else 0
            
            # Average response time across keys
            avg_response_times = [stats.get("average_response_time", 0) for stats in self.usage_stats.values() if stats.get("average_response_time", 0) > 0]
            overall_avg_response_time = sum(avg_response_times) / len(avg_response_times) if avg_response_times else 0
            
            # Aggregate usage over the past 7 days
            past_7_days = {}
            for key_id, stats in self.usage_stats.items():
                daily_usage = stats.get("daily_usage", {})
                for date, count_data in daily_usage.items():
                    if date not in past_7_days:
                        past_7_days[date] = {"successful": 0, "failed": 0}
                    # Sum counts from dict entries
                    past_7_days[date]["successful"] += count_data.get("successful", 0)
                    past_7_days[date]["failed"] += count_data.get("failed", 0)
                    
            # Keep last 7 days
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

    def mark_key_as_working(self, key: str, task_id: str) -> None:
        """
        Mark a key as currently in use for a task.
        
        Args:
            key: API key value (may include Bearer prefix)
            task_id: Associated task ID
        """
        with self._lock:
            clean_key = key.replace("Bearer ", "") if key.startswith("Bearer ") else key
            self._working_keys[clean_key] = task_id
            logger.debug(f"Key marked as working, task ID: {task_id}")
    
    def release_key(self, key: str) -> None:
        """
        Release a key from working state.
        
        Args:
            key: API key value (may include Bearer prefix)
        """
        with self._lock:
            clean_key = key.replace("Bearer ", "") if key.startswith("Bearer ") else key
            if clean_key in self._working_keys:
                del self._working_keys[clean_key]
                logger.debug(f"Key released")
    
    def is_key_working(self, key: str) -> bool:
        """
        Check if a key is currently marked as working.
        
        Args:
            key: API key value (may include Bearer prefix)
            
        Returns:
            bool: Whether the key is working
        """
        with self._lock:
            clean_key = key.replace("Bearer ", "") if key.startswith("Bearer ") else key
            return clean_key in self._working_keys

    def mark_key_invalid(self, key: str) -> Optional[str]:
        """
        Mark the given key as invalid (temporarily disabled) and return a new available key.
        
        Args:
            key: API key value (may include Bearer prefix)
            
        Returns:
            Optional[str]: A new available key, or None if none available
        """
        # Use temporary disable with a 24-hour window
        return self.mark_key_temp_disabled(key, hours=24.0)
        
    def mark_key_temp_disabled(self, key: str, hours: float = 12.0) -> Optional[str]:
        """
        Temporarily disable the given key for a specified number of hours, and return a new available key.
        
        Args:
            key: API key value (may include Bearer prefix)
            hours: Number of hours to disable
            
        Returns:
            Optional[str]: A new available key, or None if none available
        """
        with self._lock:  # Protect temp-disable with lock
            # Strip optional Bearer prefix
            key_for_search = key.replace("Bearer ", "") if key.startswith("Bearer ") else key
            
            # If the key is currently working, skip disabling
            if key_for_search in self._working_keys:
                logger.warning(f"Attempted to disable a key that is currently in use (task ID: {self._working_keys[key_for_search]}), skipping disable")
                # Return a new key without disabling the current one
                new_key = self.get_key()
                if new_key:
                    logger.info(f"Returned a new key but did not disable the working key")
                    return new_key
                else:
                    logger.warning("No backup keys available")
                    return None
            
            # Find the matching key record
            key_found = False
            disabled_key_id = None
            for key_info in self.keys:
                stored_key = key_info.get("key", "").replace("Bearer ", "") if key_info.get("key", "").startswith("Bearer ") else key_info.get("key", "")
                if stored_key == key_for_search:
                    # Mark as temporarily disabled
                    disabled_until = time.time() + (hours * 3600)  # Current time + hours
                    key_info["available"] = False
                    key_info["temp_disabled_until"] = disabled_until
                    key_info["notes"] = (key_info.get("notes") or "") + f"\n[Auto] Temporarily disabled for {hours} hours at {time.strftime('%Y-%m-%d %H:%M:%S')}"
                    key_found = True
                    disabled_key_id = key_info.get("id")
                    logger.warning(f"Key {key_info.get('name') or key_info.get('id')} temporarily disabled for {hours} hours")
                    break
            
            if key_found:
                # Persist changes
                self._save_keys()
                
                # Get a new key
                new_key = self.get_key()
                if new_key:
                    logger.info(f"Automatically switched to a new key")
                    return new_key
                else:
                    logger.warning("No backup keys available")
                    return None
            else:
                logger.warning(f"Key to temporarily disable not found")
                return None
            
    def retry_request(self, original_key: str, request_func: Callable, max_retries: int = 1, 
                     max_key_switches: int = 3) -> Tuple[bool, Any, str]:
        """
        Automatically retry a request and switch keys if needed upon errors.
        
        Args:
            original_key: Original API key (may include Bearer prefix)
            request_func: Callable taking a key and returning (success: bool, result: Any)
            max_retries: Max retries with the same key
            max_key_switches: Max number of key switches
            
        Returns:
            Tuple[bool, Any, str]: (success, result, used_key)
        """
        current_key = original_key
        current_key_switches = 0
        
        # Try with the original key first
        for attempt in range(max_retries + 1):  # +1 because the first attempt is not a retry
            try:
                success, result = request_func(current_key)
                # Successful requests should not disable the key
                if success:
                    # Record success, avoid unnecessary disabling
                    with self._lock:
                        self.record_request_result(current_key, True)
                    return True, result, current_key
                logger.warning(f"Request failed (attempt {attempt+1}/{max_retries+1}): {result}")
            except Exception as e:
                logger.error(f"Request exception (attempt {attempt+1}/{max_retries+1}): {str(e)}")
            
            # If not the last attempt, wait one second before retrying
            if attempt < max_retries:
                time.sleep(1)
                
        # After exhausting retries with the original key, attempt to switch keys
        tried_keys = set([current_key.replace("Bearer ", "") if current_key.startswith("Bearer ") else current_key])
        
        while current_key_switches < max_key_switches:
            # Obtain a new key
            with self._lock:
                new_key = self.get_key()
            if not new_key:
                logger.warning("No more available API keys")
                break
                
            # Ensure we don't reuse tried keys
            clean_new_key = new_key.replace("Bearer ", "") if new_key.startswith("Bearer ") else new_key
            if clean_new_key in tried_keys:
                continue
                
            tried_keys.add(clean_new_key)
            current_key = new_key
            current_key_switches += 1
            
            logger.info(f"Switched to a new key (switch {current_key_switches}/{max_key_switches})")
            
            # Try with the new key
            for attempt in range(max_retries + 1):
                try:
                    success, result = request_func(current_key)
                    if success:
                        # Record success
                        with self._lock:
                            self.record_request_result(current_key, True)
                        return True, result, current_key
                    logger.warning(f"Request failed with new key (attempt {attempt+1}/{max_retries+1}): {result}")
                except Exception as e:
                    logger.error(f"Request exception with new key (attempt {attempt+1}/{max_retries+1}): {str(e)}")
                
                # If not the last attempt, wait one second before retrying
                if attempt < max_retries:
                    time.sleep(1)
        
        # All attempts failed; consider temporarily disabling the original key.
        # In concurrent environments, failures may be due to network/service issues rather than the key itself.
        # Additional checks could be added here to reduce unnecessary key disables.
        should_disable = True
        
        # TODO: Add heuristics to determine if disable is warranted
        
        if should_disable:
            logger.error(f"All retries and key-switch attempts failed; temporarily disabling the original key")
            with self._lock:
                self.mark_key_temp_disabled(original_key, hours=6.0)  # Shorter window to avoid resource waste
        else:
            logger.warning(f"All retries and key-switch attempts failed, but likely a service issue; not disabling key")
        
        # Return result from the last attempt
        return False, result, current_key

# Create global key manager instance
storage_file = os.getenv("KEYS_STORAGE_FILE", "api_keys.json")
# Use absolute path if provided; otherwise resolve relative to base dir
if not os.path.isabs(storage_file):
    base_dir = os.getenv("BASE_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    storage_file = os.path.join(base_dir, storage_file)

key_manager = KeyManager(storage_file=storage_file)
logger.info(f"Initialized global KeyManager, storage file: {storage_file}")