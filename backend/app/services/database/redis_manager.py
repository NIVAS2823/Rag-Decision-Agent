"""
Redis Connection Manager
========================
Handles Redis connection lifecycle using redis-py (async).
"""

from typing import Optional, Any
import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import ConnectionError, TimeoutError

from app.core.config import settings
from app.core.logging_config import get_logger


logger = get_logger(__name__)


class RedisManager:
    """
    Redis Connection Manager
    
    Manages the Redis connection lifecycle:
    - Connection initialization
    - Connection pooling
    - Health checks
    - Graceful shutdown
    """
    
    def __init__(self):
        """Initialize Redis manager"""
        self.client: Optional[Redis] = None
        self._pool: Optional[redis.ConnectionPool] = None
    
    async def connect(self) -> None:
        """
        Connect to Redis
        
        Raises:
            ConnectionError: If connection fails
        """
        if not settings.REDIS_ENABLE:
            logger.info("Redis is disabled in configuration")
            return
        
        try:
            logger.info(f"Connecting to Redis: {settings.REDIS_URL}")
            
            # Create connection pool
            self._pool = redis.ConnectionPool.from_url(
                settings.redis_connection_url,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                decode_responses=settings.REDIS_DECODE_RESPONSES,
            )
            
            # Create Redis client
            self.client = redis.Redis(connection_pool=self._pool)
            
            # Verify connection
            await self.client.ping()
            
            logger.info(
                "✅ Connected to Redis",
                extra={
                    "max_connections": settings.REDIS_MAX_CONNECTIONS,
                    "decode_responses": settings.REDIS_DECODE_RESPONSES,
                }
            )
            
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"❌ Failed to connect to Redis: {e}")
            if settings.is_production:
                raise
            else:
                logger.warning("Redis connection failed but continuing (development mode)")
    
    async def disconnect(self) -> None:
        """
        Disconnect from Redis
        """
        if self.client:
            logger.info("Closing Redis connection...")
            await self.client.close()
            if self._pool:
                await self._pool.disconnect()
            logger.info("✅ Redis connection closed")
    
    async def health_check(self) -> bool:
        """
        Check if Redis connection is healthy
        
        Returns:
            bool: True if healthy, False otherwise
        """
        if not settings.REDIS_ENABLE or not self.client:
            return False
        
        try:
            # Ping the Redis server
            result = await self.client.ping()
            return result is True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
    
    def get_client(self) -> Redis:
        """
        Get the Redis client instance
        
        Returns:
            Redis: Redis client
            
        Raises:
            RuntimeError: If not connected
        """
        if not self.client:
            raise RuntimeError("Redis not connected. Call connect() first or enable Redis in config.")
        return self.client
    
    async def get_info(self) -> dict:
        """
        Get Redis server information
        
        Returns:
            dict: Redis server info
        """
        if not self.client:
            return {}
        
        try:
            info = await self.client.info()
            return {
                "version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "total_connections_received": info.get("total_connections_received"),
                "total_commands_processed": info.get("total_commands_processed"),
            }
        except Exception as e:
            logger.error(f"Failed to get Redis info: {e}")
            return {}


# Global Redis manager instance
redis_manager = RedisManager()


async def get_redis() -> Redis:
    """
    Dependency to get Redis client instance
    
    Returns:
        Redis: Redis client
    """
    return redis_manager.get_client()