"""
Cache Invalidation Service
===========================
Strategies and utilities for cache invalidation.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from app.services.cache import redis_client, cache_keys
from app.core.logging_config import get_logger


logger = get_logger(__name__)


class CacheInvalidationService:
    """
    Cache Invalidation Service
    
    Provides various strategies for invalidating cache entries
    to ensure data consistency.
    """
    
    # ========================================================================
    # USER INVALIDATION
    # ========================================================================
    
    @staticmethod
    async def invalidate_user(user_id: str) -> Dict[str, int]:
        """
        Invalidate all cache entries for a user
        
        Args:
            user_id: User ID
            
        Returns:
            Dict[str, int]: Counts of invalidated keys by type
        """
        patterns = [
            f"*:user:id:{user_id}",
            f"*:user:{user_id}:*",
            f"*:stats:user:{user_id}",
        ]
        
        counts = {}
        for pattern in patterns:
            deleted = await redis_client.delete_pattern(pattern)
            counts[pattern] = deleted
        
        total = sum(counts.values())
        
        logger.info(
            f"Invalidated user cache: {user_id}",
            extra={"total_keys": total, "breakdown": counts}
        )
        
        return counts
    
    @staticmethod
    async def invalidate_user_by_email(email: str) -> int:
        """
        Invalidate cache for user by email
        
        Args:
            email: User email
            
        Returns:
            int: Number of keys deleted
        """
        key = cache_keys.user_by_email(email)
        result = await redis_client.delete(key)
        
        if result:
            logger.info(f"Invalidated user email cache: {email}")
        
        return 1 if result else 0
    
    # ========================================================================
    # DECISION INVALIDATION
    # ========================================================================
    
    @staticmethod
    async def invalidate_decision(decision_id: str) -> int:
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
    async def invalidate_user_decisions(user_id: str) -> int:
        """
        Invalidate all decision lists for a user
        
        This should be called when a new decision is created
        or when a decision is deleted.
        
        Args:
            user_id: User ID
            
        Returns:
            int: Number of keys deleted
        """
        pattern = f"*:user:{user_id}:decisions:*"
        deleted = await redis_client.delete_pattern(pattern)
        
        if deleted > 0:
            logger.info(f"Invalidated user decisions cache: {user_id}")
        
        return deleted
    
    # ========================================================================
    # SESSION INVALIDATION
    # ========================================================================
    
    @staticmethod
    async def invalidate_session(session_id: str) -> bool:
        """
        Invalidate a specific session
        
        Args:
            session_id: Session ID
            
        Returns:
            bool: True if invalidated
        """
        key = cache_keys.session(session_id)
        result = await redis_client.delete(key)
        
        if result:
            logger.info(f"Invalidated session: {session_id}")
        
        return result
    
    @staticmethod
    async def invalidate_all_user_sessions(user_id: str) -> int:
        """
        Invalidate all sessions for a user
        
        Useful for logout from all devices.
        
        Args:
            user_id: User ID
            
        Returns:
            int: Number of sessions invalidated
        """
        pattern = f"*:session:user:{user_id}:*"
        deleted = await redis_client.delete_pattern(pattern)
        
        if deleted > 0:
            logger.info(f"Invalidated all sessions for user: {user_id}")
        
        return deleted
    
    # ========================================================================
    # BULK INVALIDATION
    # ========================================================================
    
    @staticmethod
    async def invalidate_by_pattern(pattern: str) -> int:
        """
        Invalidate all keys matching a pattern
        
        Args:
            pattern: Redis key pattern
            
        Returns:
            int: Number of keys deleted
        """
        deleted = await redis_client.delete_pattern(pattern)
        
        logger.warning(
            f"Bulk invalidation by pattern: {pattern}",
            extra={"keys_deleted": deleted}
        )
        
        return deleted
    
    @staticmethod
    async def invalidate_all_users() -> int:
        """
        Invalidate cache for all users
        
        Use with caution!
        
        Returns:
            int: Number of keys deleted
        """
        deleted = await redis_client.delete_pattern("*:user:*")
        
        logger.warning(f"Invalidated ALL user caches: {deleted} keys")
        
        return deleted
    
    @staticmethod
    async def invalidate_all_decisions() -> int:
        """
        Invalidate cache for all decisions
        
        Returns:
            int: Number of keys deleted
        """
        deleted = await redis_client.delete_pattern("*:decision:*")
        
        logger.warning(f"Invalidated ALL decision caches: {deleted} keys")
        
        return deleted
    
    # ========================================================================
    # VERSION-BASED INVALIDATION
    # ========================================================================
    
    @staticmethod
    async def invalidate_version(old_version: str) -> int:
        """
        Invalidate all cache keys from an old version
        
        This is useful when you increment cache version in code
        and want to clear old version caches.
        
        Args:
            old_version: Old cache version (e.g., "v1")
            
        Returns:
            int: Number of keys deleted
        """
        pattern = f"{old_version}:*"
        deleted = await redis_client.delete_pattern(pattern)
        
        logger.warning(f"Invalidated cache version {old_version}: {deleted} keys")
        
        return deleted
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    @staticmethod
    async def get_invalidation_stats() -> Dict[str, Any]:
        """
        Get statistics about cached data
        
        Returns:
            Dict[str, Any]: Cache statistics
        """
        all_keys = await redis_client.keys("*")
        
        # Count by type
        user_keys = len([k for k in all_keys if ":user:" in k])
        decision_keys = len([k for k in all_keys if ":decision:" in k])
        session_keys = len([k for k in all_keys if ":session:" in k])
        stats_keys = len([k for k in all_keys if ":stats:" in k])
        temp_keys = len([k for k in all_keys if ":temp:" in k])
        
        return {
            "total_keys": len(all_keys),
            "by_type": {
                "users": user_keys,
                "decisions": decision_keys,
                "sessions": session_keys,
                "stats": stats_keys,
                "temporary": temp_keys,
            },
            "timestamp": datetime.utcnow().isoformat()
        }


# Singleton instance
cache_invalidation = CacheInvalidationService()