"""
Cache Utilities
===============
Helper functions for common caching patterns.
"""

from typing import Optional, Any, Callable
from datetime import timedelta
from bson import ObjectId
from datetime import datetime

from app.services.cache import redis_client
from app.services.cache.keys import cache_keys
from app.core.logging_config import get_logger


logger = get_logger(__name__)

def json_safe(value: Any) -> Any:
    """
    Convert objects into JSON-serializable form for Redis storage.
    """
    if isinstance(value, ObjectId):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, dict):
        return {k: json_safe(v) for k, v in value.items()}

    if isinstance(value, list):
        return [json_safe(v) for v in value]

    return value



class CacheUtils:
    """Cache utility functions"""
    
    # Default TTLs
    TTL_SHORT = 60  # 1 minute
    TTL_MEDIUM = 300  # 5 minutes
    TTL_LONG = 3600  # 1 hour
    TTL_DAY = 86400  # 24 hours
    
    @staticmethod
    async def get_or_set(
        key: str,
        fetch_func: Callable,
        ttl: int = TTL_MEDIUM
    ) -> Any:
        """
        Cache-aside pattern: Get from cache or fetch and cache
        
        Args:
            key: Cache key
            fetch_func: Async function to fetch data if not cached
            ttl: Time to live in seconds
            
        Returns:
            Any: Cached or fetched data
        """
        # Try cache first
        cached = await redis_client.get(key)
        if cached is not None:
            logger.debug(f"Cache hit: {key}")
            return cached
        
        # Cache miss - fetch data
        logger.debug(f"Cache miss: {key}")
        data = await fetch_func()
        
        # Store in cache
        if data is not None:
            await redis_client.set(key, json_safe(data), ttl=ttl)      
        return data
    
    @staticmethod
    async def invalidate_user_cache(user_id: str) -> int:
        """
        Invalidate all cache for a user
        
        Args:
            user_id: User ID
            
        Returns:
            int: Number of keys deleted
        """
        patterns = [
            f"*:user:id:{user_id}",
            f"*:user:{user_id}:*",
            f"*:stats:user:{user_id}",
        ]
        
        total_deleted = 0
        for pattern in patterns:
            deleted = await redis_client.delete_pattern(pattern)
            total_deleted += deleted
        
        if total_deleted > 0:
            logger.info(f"Invalidated user cache: {user_id} ({total_deleted} keys)")
        
        return total_deleted
    
    @staticmethod
    async def invalidate_decision_cache(decision_id: str) -> int:
        """
        Invalidate cache for a decision
        
        Args:
            decision_id: Decision ID
            
        Returns:
            int: Number of keys deleted
        """
        pattern = f"*:decision:id:{decision_id}"
        deleted = await redis_client.delete_pattern(pattern)
        
        if deleted > 0:
            logger.info(f"Invalidated decision cache: {decision_id}")
        
        return deleted
    
    @staticmethod
    async def warm_user_cache(user_id: str, user_data: dict) -> bool:
        """
        Pre-populate user cache (cache warming)
        
        Args:
            user_id: User ID
            user_data: User data to cache
            
        Returns:
            bool: True if successful
        """
        key = cache_keys.user_by_id(user_id)
        result = await redis_client.set(key, user_data, ttl=CacheUtils.TTL_LONG)
        
        if result:
            logger.debug(f"Warmed user cache: {user_id}")
        
        return result
    
    @staticmethod
    async def get_cache_stats() -> dict:
        """
        Get cache statistics
        
        Returns:
            dict: Cache statistics
        """
        # Get all keys (be careful in production)
        all_keys = await redis_client.keys("*")
        
        # Count by prefix
        stats = {
            "total_keys": len(all_keys),
            "user_keys": len([k for k in all_keys if ":user:" in k]),
            "decision_keys": len([k for k in all_keys if ":decision:" in k]),
            "session_keys": len([k for k in all_keys if ":session:" in k]),
            "temp_keys": len([k for k in all_keys if ":temp:" in k]),
        }
        
        return stats
    
    @staticmethod
    async def increment_counter(
        key: str,
        amount: int = 1,
        ttl: Optional[int] = None
    ) -> int:
        """
        Increment a counter (useful for rate limiting, analytics)
        
        Args:
            key: Counter key
            amount: Amount to increment
            ttl: Optional TTL for the counter
            
        Returns:
            int: New counter value
        """
        from app.services.database.redis_manager import redis_manager
        
        client = redis_manager.get_client()
        if not client:
            return 0
        
        # Increment
        value = await client.incrby(key, amount)
        
        # Set TTL if provided and this is a new key
        if ttl and value == amount:
            await client.expire(key, ttl)
        
        return value
    
    @staticmethod
    async def check_rate_limit(
        user_id: str,
        endpoint: str,
        limit: int = 60,
        window: int = 60
    ) -> tuple[bool, int]:
        """
        Check if request is within rate limit
        
        Args:
            user_id: User ID
            endpoint: API endpoint
            limit: Max requests per window
            window: Time window in seconds
            
        Returns:
            tuple[bool, int]: (is_allowed, remaining_requests)
        """
        key = cache_keys.rate_limit(user_id, endpoint)
        
        # Get current count
        current = await redis_client.get(key)
        count = int(current) if current else 0
        
        if count >= limit:
            return False, 0
        
        # Increment counter
        new_count = await CacheUtils.increment_counter(key, ttl=window)
        remaining = max(0, limit - new_count)
        
        return True, remaining


# Singleton instance
cache_utils = CacheUtils()