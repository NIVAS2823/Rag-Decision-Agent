"""
Cache Key Management
====================
Utilities for generating and managing cache keys.
"""

from typing import Any, Optional
import hashlib
import json


class CacheKeys:
    """
    Cache key generator with consistent naming
    
    Pattern: {prefix}:{resource}:{identifier}:{version}
    """
    
    # Cache version (increment to invalidate all caches)
    VERSION = "v1"
    
    # Key prefixes
    PREFIX_USER = "user"
    PREFIX_DECISION = "decision"
    PREFIX_STATS = "stats"
    PREFIX_SESSION = "session"
    PREFIX_RATE_LIMIT = "ratelimit"
    PREFIX_TEMP = "temp"
    
    @classmethod
    def _make_key(cls, *parts: Any, version: Optional[str] = None) -> str:
        """
        Create cache key from parts
        
        Args:
            parts: Key components
            version: Cache version (defaults to VERSION)
            
        Returns:
            str: Cache key
        """
        version = version or cls.VERSION
        key_parts = [str(p) for p in parts if p is not None]
        return ":".join([version] + key_parts)
    
    @classmethod
    def _hash_data(cls, data: Any) -> str:
        """
        Create hash of data for cache key
        
        Args:
            data: Data to hash
            
        Returns:
            str: Hash string
        """
        if isinstance(data, (dict, list)):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)
        
        return hashlib.md5(data_str.encode()).hexdigest()[:8]
    
    # ========================================================================
    # USER CACHE KEYS
    # ========================================================================
    
    @classmethod
    def user_by_id(cls, user_id: str) -> str:
        """Cache key for user by ID"""
        return cls._make_key(cls.PREFIX_USER, "id", user_id)
    
    @classmethod
    def user_by_email(cls, email: str) -> str:
        """Cache key for user by email"""
        return cls._make_key(cls.PREFIX_USER, "email", cls._hash_data(email))
    
    @classmethod
    def user_decisions(cls, user_id: str, page: int = 1) -> str:
        """Cache key for user's decisions list"""
        return cls._make_key(cls.PREFIX_USER, user_id, "decisions", f"page{page}")
    
    @classmethod
    def user_stats(cls, user_id: str) -> str:
        """Cache key for user statistics"""
        return cls._make_key(cls.PREFIX_STATS, "user", user_id)
    
    # ========================================================================
    # DECISION CACHE KEYS
    # ========================================================================
    
    @classmethod
    def decision_by_id(cls, decision_id: str) -> str:
        """Cache key for decision by ID"""
        return cls._make_key(cls.PREFIX_DECISION, "id", decision_id)
    
    @classmethod
    def decision_query(cls, query: str, user_id: str) -> str:
        """Cache key for decision by query (for duplicate detection)"""
        query_hash = cls._hash_data(query)
        return cls._make_key(cls.PREFIX_DECISION, "query", user_id, query_hash)
    
    # ========================================================================
    # SESSION CACHE KEYS
    # ========================================================================
    
    @classmethod
    def session(cls, session_id: str) -> str:
        """Cache key for user session"""
        return cls._make_key(cls.PREFIX_SESSION, session_id)
    
    @classmethod
    def user_sessions(cls, user_id: str) -> str:
        """Cache key for all user sessions"""
        return cls._make_key(cls.PREFIX_SESSION, "user", user_id)
    
    # ========================================================================
    # RATE LIMITING KEYS
    # ========================================================================
    
    @classmethod
    def rate_limit(cls, user_id: str, endpoint: str) -> str:
        """Cache key for rate limiting"""
        return cls._make_key(cls.PREFIX_RATE_LIMIT, user_id, endpoint)
    
    # ========================================================================
    # TEMPORARY DATA KEYS
    # ========================================================================
    
    @classmethod
    def temp_data(cls, identifier: str) -> str:
        """Cache key for temporary data (OTP, reset tokens, etc.)"""
        return cls._make_key(cls.PREFIX_TEMP, identifier)
    
    @classmethod
    def password_reset_token(cls, token: str) -> str:
        """Cache key for password reset token"""
        return cls._make_key(cls.PREFIX_TEMP, "reset", cls._hash_data(token))
    
    @classmethod
    def email_verification_token(cls, token: str) -> str:
        """Cache key for email verification token"""
        return cls._make_key(cls.PREFIX_TEMP, "verify", cls._hash_data(token))


# Singleton instance
cache_keys = CacheKeys()