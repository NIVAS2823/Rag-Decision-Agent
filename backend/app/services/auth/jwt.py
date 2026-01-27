"""
JWT Token Service
=================
JWT token generation and management.
"""
import time

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import jwt

from app.core.config import settings
from app.models.user import UserRole
from app.core.logging_config import get_logger


logger = get_logger(__name__)


class JWTService:
    """
    JWT Token Service
    
    Handles creation and management of JWT tokens for authentication.
    """
    
    # Token types
    TOKEN_TYPE_ACCESS = "access"
    TOKEN_TYPE_REFRESH = "refresh"
    
    @staticmethod
    def create_access_token(
        user_id: str,
        email: str,
        role: UserRole,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create access token
        
        Access tokens are short-lived and used for API authentication.
        
        Args:
            user_id: User ID
            email: User email
            role: User role
            expires_delta: Custom expiration time (optional)
            
        Returns:
            str: Encoded JWT token
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )
        
        # Token payload
        payload = {
            "sub": user_id,  # Subject (user ID)
            "email": email,
            "role": role.value,
            "type": JWTService.TOKEN_TYPE_ACCESS,
            "exp": expire,  # Expiration time
            "iat": datetime.utcnow(),  # Issued at
        }
        
        # Encode token
        encoded_jwt = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        logger.debug(
            f"Created access token for user: {email}",
            extra={
                "user_id": user_id,
                "expires_at": expire.isoformat()
            }
        )
        
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(
        user_id: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create refresh token
        
        Refresh tokens are long-lived and used to obtain new access tokens.
        
        Args:
            user_id: User ID
            expires_delta: Custom expiration time (optional)
            
        Returns:
            str: Encoded JWT token
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            # Default: 7 days
            expire = datetime.utcnow() + timedelta(days=7)
        
        # Token payload (minimal for refresh tokens)
        payload = {
            "sub": user_id,
            "type": JWTService.TOKEN_TYPE_REFRESH,
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        
        # Encode token
        encoded_jwt = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        logger.debug(
            f"Created refresh token for user: {user_id}",
            extra={"expires_at": expire.isoformat()}
        )
        
        return encoded_jwt
    
    @staticmethod
    def create_token_pair(
        user_id: str,
        email: str,
        role: UserRole
    ) -> Dict[str, str]:
        """
        Create both access and refresh tokens
        
        Args:
            user_id: User ID
            email: User email
            role: User role
            
        Returns:
            Dict[str, str]: Dictionary with access_token and refresh_token
        """
        access_token = JWTService.create_access_token(user_id, email, role)
        refresh_token = JWTService.create_refresh_token(user_id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer"
        }
    
    @staticmethod
    def get_token_expiration_time(
        token_type: str = TOKEN_TYPE_ACCESS
    ) -> timedelta:
        """
        Get expiration time for a token type
        
        Args:
            token_type: Type of token
            
        Returns:
            timedelta: Expiration time delta
        """
        if token_type == JWTService.TOKEN_TYPE_ACCESS:
            return timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        elif token_type == JWTService.TOKEN_TYPE_REFRESH:
            return timedelta(days=7)
        else:
            raise ValueError(f"Unknown token type: {token_type}")
    
    @staticmethod
    def create_password_reset_token(user_id: str, email: str) -> str:
        """
        Create password reset token
        
        These are short-lived tokens for password reset flows.
        
        Args:
            user_id: User ID
            email: User email
            
        Returns:
            str: Encoded token
        """
        expire = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
        
        payload = {
            "sub": user_id,
            "email": email,
            "type": "password_reset",
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        
        encoded_jwt = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        logger.info(f"Created password reset token for user: {email}")
        
        return encoded_jwt
    
    @staticmethod
    def create_email_verification_token(user_id: str, email: str) -> str:
        """
        Create email verification token
        
        Args:
            user_id: User ID
            email: User email
            
        Returns:
            str: Encoded token
        """
        expire = datetime.utcnow() + timedelta(days=1)  # 24 hour expiry
        
        payload = {
            "sub": user_id,
            "email": email,
            "type": "email_verification",
            "exp": expire,
            "iat": datetime.utcnow(),
        }
        
        encoded_jwt = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        logger.info(f"Created email verification token for user: {email}")
        
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and verify JWT token
        
        Args:
            token: JWT token to decode
            
        Returns:
            Optional[Dict[str, Any]]: Token payload if valid, None otherwise
            
        Raises:
            JWTError: If token is invalid
        """
        from jose import JWTError, ExpiredSignatureError
        
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
            
        except ExpiredSignatureError:
            logger.warning("Token has expired")
            raise
        except JWTError as e:
            logger.warning(f"Token validation failed: {e}")
            raise
    
    @staticmethod
    def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode access token
        
        Args:
            token: Access token
            
        Returns:
            Optional[Dict[str, Any]]: Token payload if valid
            
        Raises:
            ValueError: If token type is not 'access'
            JWTError: If token is invalid or expired
        """
        payload = JWTService.decode_token(token)
        
        if payload.get("type") != JWTService.TOKEN_TYPE_ACCESS:
            raise ValueError("Invalid token type - expected access token")
        
        return payload
    
    @staticmethod
    def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode refresh token
        
        Args:
            token: Refresh token
            
        Returns:
            Optional[Dict[str, Any]]: Token payload if valid
            
        Raises:
            ValueError: If token type is not 'refresh'
            JWTError: If token is invalid or expired
        """
        payload = JWTService.decode_token(token)
        
        if payload.get("type") != JWTService.TOKEN_TYPE_REFRESH:
            raise ValueError("Invalid token type - expected refresh token")
        
        return payload
    
    @staticmethod
    async def verify_token_with_blacklist(token: str) -> Optional[Dict[str, Any]]:
        """
        Verify token and check if it's blacklisted
        
        Args:
            token: JWT token
            
        Returns:
            Optional[Dict[str, Any]]: Token payload if valid and not blacklisted
            
        Raises:
            ValueError: If token is blacklisted
            JWTError: If token is invalid or expired
        """
        from app.services.auth.token_blacklist import token_blacklist
        
        # Check blacklist first (faster than decoding)
        is_blacklisted = await token_blacklist.is_blacklisted(token)
        if is_blacklisted:
            raise ValueError("Token has been revoked")
        
        # Decode and verify
        payload = JWTService.decode_token(token)
        
        return payload
    
    @staticmethod
    def extract_user_id(token: str) -> Optional[str]:
        """
        Extract user ID from token without full verification
        
        Useful for logging/debugging purposes.
        
        Args:
            token: JWT token
            
        Returns:
            Optional[str]: User ID if present
        """
        try:
            # Decode without verification (just to read payload)
            payload = jwt.decode(
                                token,
                                key="",
                                algorithms=[settings.JWT_ALGORITHM],
                                options={"verify_signature": False}
                                )

            return payload.get("sub")
        except Exception:
            return None
    
    @staticmethod
    def get_token_expiration(token: str) -> Optional[int]:
        """
        Get token expiration timestamp
        
        Args:
            token: JWT token
            
        Returns:
            Optional[int]: Expiration timestamp
        """
        try:
            payload = jwt.decode(
                            token,
                            key="",
                            algorithms=[settings.JWT_ALGORITHM],
                            options={"verify_signature": False}
                                )
            return payload.get("exp")
        except Exception:
            return None
    
    @staticmethod
    def calculate_token_ttl(token: str) -> Optional[int]:
        """
        Calculate remaining TTL for token (for blacklist)
        
        Args:
            token: JWT token
            
        Returns:
            Optional[int]: TTL in seconds, or None if expired/invalid
        """
        exp = JWTService.get_token_expiration(token)
        if not exp:
            return None
        
        current_time = time.time()
        ttl = int(exp - current_time)
        
        return ttl if ttl > 0 else 0


# Singleton instance
jwt_service = JWTService()