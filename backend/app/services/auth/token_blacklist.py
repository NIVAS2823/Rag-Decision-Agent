"""
Token Blacklist Service
=======================
Manages blacklisted tokens (for logout functionality).
"""

from datetime import timedelta
from typing import Optional

from app.services.cache import redis_client
from app.core.logging_config import get_logger


logger = get_logger(__name__)


class TokenBlacklistService:
    """
    Token Blacklist Service
    
    Uses Redis to store blacklisted tokens (logged out sessions).
    """
    
    PREFIX = "blacklist:token:"
    
    @staticmethod
    async def add_token(token: str, expires_in: int) -> bool:
        """
        Add token to blacklist
        
        Args:
            token: JWT token to blacklist
            expires_in: Seconds until token expires naturally
            
        Returns:
            bool: True if added successfully
        """
        key = f"{TokenBlacklistService.PREFIX}{token}"
        
        # Store with TTL matching token expiration
        # After token expires naturally, it will be removed from Redis automatically
        result = await redis_client.set(key, "1", ttl=expires_in)
        
        if result:
            logger.info("Token added to blacklist")
        
        return result
    
    @staticmethod
    async def is_blacklisted(token: str) -> bool:
        """
        Check if token is blacklisted
        
        Args:
            token: JWT token to check
            
        Returns:
            bool: True if blacklisted, False otherwise
        """
        key = f"{TokenBlacklistService.PREFIX}{token}"
        
        exists = await redis_client.exists(key)
        
        if exists:
            logger.debug("Token is blacklisted")
        
        return exists
    
    @staticmethod
    async def remove_token(token: str) -> bool:
        """
        Remove token from blacklist
        
        Args:
            token: JWT token to remove
            
        Returns:
            bool: True if removed
        """
        key = f"{TokenBlacklistService.PREFIX}{token}"
        return await redis_client.delete(key)


# Singleton instance
token_blacklist = TokenBlacklistService()