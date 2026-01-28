"""
Authentication Dependencies
===========================
FastAPI dependencies for authentication and authorization.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from app.models.user import UserInDB, UserRole
from app.services.database.repositories import user_repository
from app.services.auth import jwt_service
from app.core.exceptions import (
    InvalidTokenException,
    TokenExpiredException,
    TokenRevokedException,
    UserNotFoundException,
    UserInactiveException,
)
from app.core.logging_config import get_logger


logger = get_logger(__name__)

# HTTP Bearer token security scheme
security = HTTPBearer()


# ============================================================================
# TOKEN EXTRACTION & VALIDATION
# ============================================================================

async def get_token_from_header(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Extract JWT token from Authorization header
    
    Args:
        credentials: HTTP Authorization credentials
        
    Returns:
        str: JWT token string
        
    Raises:
        HTTPException 401: If token is missing or invalid format
    """
    if not credentials or not credentials.credentials:
        logger.warning("Missing authorization token")
        raise InvalidTokenException()
    
    token = credentials.credentials
    
    # Basic token format validation (should start with 'eyJ')
    if not token.startswith('eyJ'):
        logger.warning("Invalid token format")
        raise InvalidTokenException()
    
    return token


async def verify_token(token: str = Depends(get_token_from_header)) -> dict:
    """
    Verify and decode JWT token
    
    This dependency:
    1. Validates token signature
    2. Checks expiration
    3. Verifies token is not blacklisted
    
    Args:
        token: JWT token from header
        
    Returns:
        dict: Decoded token payload
        
    Raises:
        HTTPException 401: If token is invalid, expired, or revoked
    """
    try:
        # Verify token and check blacklist
        payload = await jwt_service.verify_token_with_blacklist(token)
        
        if not payload:
            raise InvalidTokenException()
        
        # Verify it's an access token
        if payload.get("type") != jwt_service.TOKEN_TYPE_ACCESS:
            logger.warning("Invalid token type - expected access token")
            raise InvalidTokenException()
        
        return payload
        
    except ValueError as e:
        # Token is blacklisted
        if "revoked" in str(e).lower():
            logger.warning(f"Attempt to use revoked token")
            raise TokenRevokedException()
        raise InvalidTokenException()
        
    except JWTError as e:
        error_msg = str(e).lower()
        
        if "expired" in error_msg:
            logger.warning("Expired token used")
            raise TokenExpiredException()
        else:
            logger.warning(f"Token validation failed: {e}")
            raise InvalidTokenException()


# ============================================================================
# CURRENT USER RETRIEVAL
# ============================================================================

async def get_current_user(
    payload: dict = Depends(verify_token)
) -> UserInDB:
    """
    Get current authenticated user from token
    
    This is the PRIMARY dependency for protected endpoints.
    Use this to get the current user in any protected route.
    
    Args:
        payload: Decoded token payload
        
    Returns:
        UserInDB: Current authenticated user
        
    Raises:
        HTTPException 401: If user not found or inactive
        
    Example:
```python
        @router.get("/protected")
        async def protected_route(
            current_user: UserInDB = Depends(get_current_user)
        ):
            return {"user_id": str(current_user.id)}
```
    """
    user_id = payload.get("sub")
    
    if not user_id:
        logger.error("Token missing user ID (sub)")
        raise InvalidTokenException()
    
    # Retrieve user from database
    user = await user_repository.get_by_id(user_id)
    
    if not user:
        logger.warning(f"User not found for token: {user_id}")
        raise UserNotFoundException()
    
    # Check if user is active
    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {user.email}")
        raise UserInactiveException()
    
    logger.debug(
        f"Authenticated user: {user.email}",
        extra={"user_id": str(user.id)}
    )
    
    return user


async def get_current_user_cached(
    payload: dict = Depends(verify_token)
) -> UserInDB:
    """
    Get current authenticated user from token (with caching)
    
    Use this for high-traffic endpoints where user data doesn't change frequently.
    
    Args:
        payload: Decoded token payload
        
    Returns:
        UserInDB: Current authenticated user
        
    Raises:
        HTTPException 401: If user not found or inactive
    """
    user_id = payload.get("sub")
    
    if not user_id:
        raise InvalidTokenException()
    
    # Use cached repository method
    user = await user_repository.get_by_id_cached(user_id)
    
    if not user:
        raise UserNotFoundException()
    
    if not user.is_active:
        raise UserInactiveException()
    
    return user


async def get_current_active_user(
    current_user: UserInDB = Depends(get_current_user)
) -> UserInDB:
    """
    Get current active user (explicit active check)
    
    This is redundant since get_current_user already checks is_active,
    but provided for semantic clarity in some routes.
    
    Args:
        current_user: Current user from get_current_user
        
    Returns:
        UserInDB: Active user
        
    Raises:
        HTTPException 401: If user is inactive
    """
    if not current_user.is_active:
        raise UserInactiveException()
    
    return current_user


# ============================================================================
# OPTIONAL AUTHENTICATION
# ============================================================================

async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(
        HTTPBearer(auto_error=False)
    )
) -> Optional[UserInDB]:
    """
    Get current user if authenticated, None otherwise
    
    Use this for endpoints that have different behavior for authenticated
    vs. anonymous users, but don't require authentication.
    
    Args:
        credentials: Optional HTTP Authorization credentials
        
    Returns:
        Optional[UserInDB]: User if authenticated, None otherwise
        
    Example:
```python
        @router.get("/public-with-benefits")
        async def public_route(
            user: Optional[UserInDB] = Depends(get_current_user_optional)
        ):
            if user:
                return {"message": f"Hello {user.full_name}"}
            return {"message": "Hello guest"}
```
    """
    if not credentials or not credentials.credentials:
        return None
    
    try:
        token = credentials.credentials
        payload = await jwt_service.verify_token_with_blacklist(token)
        
        if not payload:
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        user = await user_repository.get_by_id(user_id)
        
        if not user or not user.is_active:
            return None
        
        return user
        
    except Exception:
        # Silently fail for optional authentication
        return None


# ============================================================================
# ROLE-BASED DEPENDENCIES (For Step 6 - RBAC)
# ============================================================================

class RoleChecker:
    """
    Dependency class for role-based access control
    
    Usage:
        require_admin = RoleChecker([UserRole.ADMIN])
        
        @router.get("/admin-only")
        async def admin_route(user: UserInDB = Depends(require_admin)):
            ...
    """
    
    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles
    
    async def __call__(
        self,
        current_user: UserInDB = Depends(get_current_user)
    ) -> UserInDB:
        """
        Check if user has required role
        
        Args:
            current_user: Current authenticated user
            
        Returns:
            UserInDB: User if authorized
            
        Raises:
            HTTPException 403: If user lacks required role
        """
        from app.core.exceptions import InsufficientPermissionsException
        
        if current_user.role not in self.allowed_roles:
            logger.warning(
                f"Insufficient permissions: {current_user.email} "
                f"(role: {current_user.role}) attempted to access "
                f"endpoint requiring: {self.allowed_roles}"
            )
            raise InsufficientPermissionsException()
        
        return current_user


# Predefined role checkers (ready for Step 6)
require_admin = RoleChecker([UserRole.ADMIN])
require_admin_or_user = RoleChecker([UserRole.ADMIN, UserRole.USER])
require_any_role = RoleChecker([UserRole.ADMIN, UserRole.USER, UserRole.VIEWER])