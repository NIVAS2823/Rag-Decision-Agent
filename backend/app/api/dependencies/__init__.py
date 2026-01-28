"""
API Dependencies
================
Centralized imports for API dependencies.
"""

from app.api.dependencies.auth import (
    get_current_user,
    get_current_user_cached,
    get_current_active_user,
    get_current_user_optional,
    get_token_from_header,
    verify_token,
    require_admin,
    require_admin_or_user,
    require_any_role,
    RoleChecker,
)
from app.api.dependencies.logging import RequestLoggingMiddleware

__all__ = [
    # User dependencies
    "get_current_user",
    "get_current_user_cached",
    "get_current_active_user",
    "get_current_user_optional",
    
    # Token dependencies
    "get_token_from_header",
    "verify_token",
    
    # Role-based dependencies
    "require_admin",
    "require_admin_or_user",
    "require_any_role",
    "RoleChecker",
    
    # Middleware
    "RequestLoggingMiddleware",
]