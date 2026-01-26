"""
Cache Decorators
================
Decorators for automatic function result caching.
"""

import functools
from typing import Callable, Optional, Any
import inspect

from app.services.cache import redis_client
from app.services.cache.keys import cache_keys
from app.core.logging_config import get_logger


logger = get_logger(__name__)


def cached(
    ttl: int = 300,
    key_prefix: Optional[str] = None,
    key_builder: Optional[Callable] = None
):
    """
    Cache decorator for async functions
    
    Args:
        ttl: Time to live in seconds (default: 5 minutes)
        key_prefix: Prefix for cache key
        key_builder: Custom function to build cache key from args
        
    Example:
        @cached(ttl=60, key_prefix="user")
        async def get_user(user_id: str):
            return await fetch_from_db(user_id)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            elif key_prefix:
                # Use function args to build key
                arg_str = cache_keys._hash_data({"args": args, "kwargs": kwargs})
                cache_key = f"{key_prefix}:{func.__name__}:{arg_str}"
            else:
                # Default: use function name and args
                arg_str = cache_keys._hash_data({"args": args, "kwargs": kwargs})
                cache_key = f"cache:{func.__name__}:{arg_str}"
            
            # Try to get from cache
            cached_value = await redis_client.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value
            
            # Cache miss - call function
            logger.debug(f"Cache miss: {cache_key}")
            result = await func(*args, **kwargs)
            
            # Store in cache
            if result is not None:
                await redis_client.set(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


def cache_invalidate(key_pattern: str):
    """
    Decorator to invalidate cache after function execution
    
    Args:
        key_pattern: Pattern of keys to invalidate
        
    Example:
        @cache_invalidate("user:*")
        async def update_user(user_id: str, data: dict):
            return await db.update(user_id, data)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Execute function
            result = await func(*args, **kwargs)
            
            # Invalidate cache
            deleted = await redis_client.delete_pattern(key_pattern)
            if deleted > 0:
                logger.info(f"Invalidated {deleted} cache keys: {key_pattern}")
            
            return result
        
        return wrapper
    return decorator