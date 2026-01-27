"""
JWT Token Service
=================
JWT token generation and management.
"""

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


# Singleton instance
jwt_service = JWTService()