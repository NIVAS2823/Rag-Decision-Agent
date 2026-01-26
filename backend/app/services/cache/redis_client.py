"""
Redis Client Wrapper
====================
High-level wrapper for Redis operations with automatic serialization.
"""

import json
from typing import Any, Optional, List, Dict
from datetime import timedelta

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.services.database.redis_manager import RedisManager,redis_manager
from app.core.config import settings
from app.core.logging_config import get_logger


logger = get_logger(__name__)


class RedisClient:
    """
    Redis Client Wrapper
    
    Provides high-level methods for Redis operations with:
    - Automatic JSON serialization/deserialization
    - Error handling
    - Logging
    - Type safety
    """
    
    def __init__(self, manager: RedisManager):
        self._enabled = settings.REDIS_ENABLE
        self._manager = manager
    
    def _get_client(self) -> Optional[Redis]:
        if not self._enabled:
            return None
        try:
            return self._manager.get_client()
        except RuntimeError:
            logger.warning("Redis client not available")
            return None
    
    # ========================================================================
    # STRING OPERATIONS
    # ========================================================================
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value by key
        
        Automatically deserializes JSON values.
        
        Args:
            key: Cache key
            
        Returns:
            Optional[Any]: Value if found, None otherwise
        """
        client = self._get_client()
        if not client:
            return None
        
        try:
            value = await client.get(key)
            
            if value is None:
                logger.debug(f"Cache miss: {key}")
                return None
            
            # Try to deserialize JSON
            try:
                result = json.loads(value)
                logger.debug(f"Cache hit: {key}")
                return result
            except (json.JSONDecodeError, TypeError):
                # Return as-is if not JSON
                logger.debug(f"Cache hit (raw): {key}")
                return value
                
        except RedisError as e:
            logger.error(f"Redis get error for key '{key}': {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value by key
        
        Automatically serializes to JSON if needed.
        
        Args:
            key: Cache key
            ttl: Time to live in seconds (optional)
            value: Value to cache
            
        Returns:
            bool: True if successful, False otherwise
        """
        client = self._get_client()
        if not client:
            return False
        
        try:
            # Serialize to JSON if not a string
            if not isinstance(value, str):
                value = json.dumps(value)
            
            # Set with TTL if provided
            if ttl:
                await client.setex(key, ttl, value)
            else:
                await client.set(key, value)
            
            logger.debug(f"Cache set: {key} (ttl: {ttl}s)" if ttl else f"Cache set: {key}")
            return True
            
        except RedisError as e:
            logger.error(f"Redis set error for key '{key}': {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key
        
        Args:
            key: Cache key to delete
            
        Returns:
            bool: True if deleted, False if key didn't exist or error
        """
        client = self._get_client()
        if not client:
            return False
        
        try:
            result = await client.delete(key)
            if result > 0:
                logger.debug(f"Cache delete: {key}")
                return True
            return False
            
        except RedisError as e:
            logger.error(f"Redis delete error for key '{key}': {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists
        
        Args:
            key: Cache key
            
        Returns:
            bool: True if exists, False otherwise
        """
        client = self._get_client()
        if not client:
            return False
        
        try:
            result = await client.exists(key)
            return result > 0
            
        except RedisError as e:
            logger.error(f"Redis exists error for key '{key}': {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set TTL on existing key
        
        Args:
            key: Cache key
            ttl: Time to live in seconds
            
        Returns:
            bool: True if TTL was set, False otherwise
        """
        client = self._get_client()
        if not client:
            return False
        
        try:
            result = await client.expire(key, ttl)
            if result:
                logger.debug(f"Set TTL on {key}: {ttl}s")
            return result
            
        except RedisError as e:
            logger.error(f"Redis expire error for key '{key}': {e}")
            return False
    
    async def ttl(self, key: str) -> Optional[int]:
        """
        Get remaining TTL for key
        
        Args:
            key: Cache key
            
        Returns:
            Optional[int]: TTL in seconds, -1 if no expiry, -2 if key doesn't exist
        """
        client = self._get_client()
        if not client:
            return None
        
        try:
            return await client.ttl(key)
        except RedisError as e:
            logger.error(f"Redis TTL error for key '{key}': {e}")
            return None
    
    # ========================================================================
    # HASH OPERATIONS
    # ========================================================================
    
    async def hset(self, key: str, field: str, value: Any) -> bool:
        """
        Set hash field
        
        Args:
            key: Hash key
            field: Field name
            value: Field value
            
        Returns:
            bool: True if successful
        """
        client = self._get_client()
        if not client:
            return False
        
        try:
            if not isinstance(value, str):
                value = json.dumps(value)
            
            await client.hset(key, field, value)
            logger.debug(f"Hash set: {key}[{field}]")
            return True
            
        except RedisError as e:
            logger.error(f"Redis hset error: {e}")
            return False
    
    async def hget(self, key: str, field: str) -> Optional[Any]:
        """
        Get hash field
        
        Args:
            key: Hash key
            field: Field name
            
        Returns:
            Optional[Any]: Field value if found
        """
        client = self._get_client()
        if not client:
            return None
        
        try:
            value = await client.hget(key, field)
            
            if value is None:
                return None
            
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
                
        except RedisError as e:
            logger.error(f"Redis hget error: {e}")
            return None
    
    async def hgetall(self, key: str) -> Dict[str, Any]:
        """
        Get all hash fields
        
        Args:
            key: Hash key
            
        Returns:
            Dict[str, Any]: All fields and values
        """
        client = self._get_client()
        if not client:
            return {}
        
        try:
            data = await client.hgetall(key)
            
            # Deserialize JSON values
            result = {}
            for field, value in data.items():
                try:
                    result[field] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    result[field] = value
            
            return result
            
        except RedisError as e:
            logger.error(f"Redis hgetall error: {e}")
            return {}
    
    async def hdel(self, key: str, *fields: str) -> bool:
        """
        Delete hash fields
        
        Args:
            key: Hash key
            fields: Field names to delete
            
        Returns:
            bool: True if at least one field was deleted
        """
        client = self._get_client()
        if not client:
            return False
        
        try:
            result = await client.hdel(key, *fields)
            return result > 0
            
        except RedisError as e:
            logger.error(f"Redis hdel error: {e}")
            return False
    
    # ========================================================================
    # LIST OPERATIONS
    # ========================================================================
    
    async def lpush(self, key: str, *values: Any) -> bool:
        """
        Push values to left of list
        
        Args:
            key: List key
            values: Values to push
            
        Returns:
            bool: True if successful
        """
        client = self._get_client()
        if not client:
            return False
        
        try:
            # Serialize values
            serialized = [
                json.dumps(v) if not isinstance(v, str) else v
                for v in values
            ]
            
            await client.lpush(key, *serialized)
            logger.debug(f"List push: {key} ({len(values)} items)")
            return True
            
        except RedisError as e:
            logger.error(f"Redis lpush error: {e}")
            return False
    
    async def lrange(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """
        Get range of list elements
        
        Args:
            key: List key
            start: Start index
            end: End index (-1 for all)
            
        Returns:
            List[Any]: List elements
        """
        client = self._get_client()
        if not client:
            return []
        
        try:
            values = await client.lrange(key, start, end)
            
            # Deserialize values
            result = []
            for value in values:
                try:
                    result.append(json.loads(value))
                except (json.JSONDecodeError, TypeError):
                    result.append(value)
            
            return result
            
        except RedisError as e:
            logger.error(f"Redis lrange error: {e}")
            return []
    
    # ========================================================================
    # PATTERN OPERATIONS
    # ========================================================================
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern
        
        Args:
            pattern: Key pattern (e.g., "user:*")
            
        Returns:
            int: Number of keys deleted
        """
        client = self._get_client()
        if not client:
            return 0
        
        try:
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            
            if keys:
                deleted = await client.delete(*keys)
                logger.info(f"Deleted {deleted} keys matching pattern: {pattern}")
                return deleted
            
            return 0
            
        except RedisError as e:
            logger.error(f"Redis delete_pattern error: {e}")
            return 0
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """
        Get all keys matching pattern
        
        WARNING: Use with caution in production (can be slow)
        
        Args:
            pattern: Key pattern
            
        Returns:
            List[str]: Matching keys
        """
        client = self._get_client()
        if not client:
            return []
        
        try:
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            
            return keys
            
        except RedisError as e:
            logger.error(f"Redis keys error: {e}")
            return []
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    async def flush_all(self) -> bool:
        """
        Flush all keys (WARNING: deletes everything)
        
        Only works in development mode.
        
        Returns:
            bool: True if successful
        """
        if settings.is_production:
            logger.error("Cannot flush Redis in production!")
            return False
        
        client = self._get_client()
        if not client:
            return False
        
        try:
            await client.flushall()
            logger.warning("Redis flushed (all keys deleted)")
            return True
            
        except RedisError as e:
            logger.error(f"Redis flush error: {e}")
            return False


# Global Redis client instance
redis_client = RedisClient(redis_manager)