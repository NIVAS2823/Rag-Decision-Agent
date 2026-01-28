"""
Authentication Routes
====================
User authentication endpoints (register, login, logout, etc.).
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer

from app.services.database.repositories import user_repository
from app.services.auth import jwt_service
from app.core.logging_config import get_logger
from app.core.exceptions import (
    InvalidCredentialsException,
    UserNotFoundException,
    UserInactiveException
)
from app.models.user import (
    UserCreate,
    UserLogin,
    User,
    Token,
    UserInDB,
    UserRole,
    PasswordChange,
    PasswordResetRequest,
    PasswordResetVerify,
    PasswordResetConfirm,
)
from app.api.dependencies.auth import (
    get_current_user,
    require_admin,
    require_admin_or_user,
    require_any_role,
    RoleChecker,
)
from app.services.auth.password import verify_password, hash_password
from app.services.auth.token_blacklist import token_blacklist
from app.api.dependencies.auth import get_token_from_header


logger = get_logger(__name__)
router = APIRouter()
security = HTTPBearer()


# ============================================================================
# REGISTRATION
# ============================================================================

@router.post(
    "/register",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user",
    description="Create a new user account and receive authentication tokens.",
    tags=["auth"],
)
async def register(user_data: UserCreate):
    """
    Register New User
    
    Creates a new user account with the provided information.
    Returns JWT tokens for immediate authentication.
    
    Args:
        user_data: User registration data
        
    Returns:
        dict: User info and authentication tokens
        
    Raises:
        HTTPException 400: If email already exists
        HTTPException 422: If validation fails
    """
    # Check if email already exists
    existing_user = await user_repository.get_by_email(user_data.email)
    if existing_user:
        logger.warning(f"Registration attempt with existing email: {user_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    try:
        user = await user_repository.create(user_data)
        
        logger.info(
            f"New user registered: {user.email}",
            extra={"user_id": str(user.id)}
        )
        
        # Generate tokens
        tokens = jwt_service.create_token_pair(
            user_id=str(user.id),
            email=user.email,
            role=user.role
        )
        
        # Convert user to response model
        user_response = User.from_db(user)
        
        return {
            "user": user_response.model_dump(),
            "tokens": tokens,
            "message": "User registered successfully"
        }
        
    except ValueError as e:
        # This catches duplicate email from repository level
        logger.error(f"User creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error during registration: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration"
        )

# ============================================================================
# LOGIN
# ============================================================================

@router.post(
    "/login",
    response_model=dict,
    status_code=status.HTTP_200_OK,
    summary="User login",
    description="Authenticate user with email and password. Returns JWT tokens.",
    tags=["auth"],
)
async def login(credentials: UserLogin):
    """
    User Login
    
    Authenticate a user with email and password.
    Returns JWT tokens for subsequent authenticated requests.
    
    Args:
        credentials: User login credentials (email and password)
        
    Returns:
        dict: User info and authentication tokens
        
    Raises:
        HTTPException 401: If credentials are invalid or account is inactive
        HTTPException 500: If an unexpected error occurs
    """
    try:
        # Get user by email
        user = await user_repository.get_by_email(credentials.email)
        
        # Check if user exists
        if not user:
            logger.warning(f"Login attempt with non-existent email: {credentials.email}")
            raise InvalidCredentialsException()
        
        # Check if account is active
        if not user.is_active:
            logger.warning(f"Login attempt for inactive account: {credentials.email}")
            raise UserInactiveException()
        
        # Verify password
        from app.services.auth.password import verify_password
        
        if not verify_password(credentials.password, user.hashed_password):
            logger.warning(f"Failed login attempt for user: {credentials.email}")
            raise InvalidCredentialsException()
        
        # Update last login timestamp
        await user_repository.update_last_login(str(user.id))
        
        # Generate token pair
        tokens = jwt_service.create_token_pair(
            user_id=str(user.id),
            email=user.email,
            role=user.role
        )
        
        logger.info(
            f"User logged in successfully: {user.email}",
            extra={"user_id": str(user.id)}
        )
        
        # Convert user to response model
        user_response = User.from_db(user)
        
        return {
            "user": user_response.model_dump(),
            "tokens": tokens,
            "message": "Login successful"
        }
        
    except (InvalidCredentialsException, UserInactiveException):
        # Re-raise authentication exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )
    

# ============================================================================
# CURRENT USER INFO (Step 5.5 Test Endpoint)
# ============================================================================

@router.get(
    "/me",
    response_model=User,
    summary="Get current user",
    description="Get information about the currently authenticated user.",
    tags=["auth"],
)
async def get_me(current_user: UserInDB = Depends(get_current_user)):
    """
    Get Current User
    
    Returns information about the currently authenticated user.
    This endpoint requires a valid JWT token.
    
    Args:
        current_user: Current authenticated user (injected by dependency)
        
    Returns:
        User: Current user information
    """
    logger.info(
        f"User profile accessed: {current_user.email}",
        extra={"user_id": str(current_user.id)}
    )
    
    return User.from_db(current_user)

# ============================================================================
# LOGOUT (Step 5.7)
# ============================================================================

@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="User logout",
    description="Logout user by blacklisting their access token",
    tags=["auth"],
)
async def logout(
    token: str = Depends(get_token_from_header),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    User Logout
    
    Blacklists the current access token to prevent further use.
    The token will remain blacklisted until its natural expiration.
    
    Args:
        token: JWT token from Authorization header
        current_user: Current authenticated user
        
    Returns:
        dict: Logout confirmation message
        
    Note:
        After logout, the client should:
        1. Delete the access_token from local storage
        2. Delete the refresh_token from local storage
        3. Redirect to login page
    """
    try:
        # Calculate remaining TTL for the token
        ttl = jwt_service.calculate_token_ttl(token)
        
        if ttl and ttl > 0:
            # Add token to blacklist
            await token_blacklist.add_token(token, ttl)
            
            logger.info(
                f"User logged out: {current_user.email}",
                extra={
                    "user_id": str(current_user.id),
                    "token_ttl": ttl
                }
            )
            
            return {
                "message": "Logout successful",
                "user_email": current_user.email
            }
        else:
            # Token already expired or invalid TTL
            logger.warning(f"Logout attempted with expired token: {current_user.email}")
            return {
                "message": "Logout successful (token already expired)",
                "user_email": current_user.email
            }
            
    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during logout"
        )


@router.post(
    "/logout-all",
    status_code=status.HTTP_200_OK,
    summary="Logout from all devices",
    description="Invalidate all tokens for the current user",
    tags=["auth"],
)
async def logout_all(
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Logout From All Devices
    
    This is a placeholder for future implementation.
    To fully implement this, you would need to:
    1. Store a "token version" or "session ID" in the database
    2. Increment it on logout-all
    3. Check version/ID in token validation
    
    For now, this endpoint logs the action but doesn't invalidate all tokens.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        dict: Logout confirmation message
    """
    logger.warning(
        f"Logout-all requested (not fully implemented): {current_user.email}",
        extra={"user_id": str(current_user.id)}
    )
    
    # TODO: Implement actual logout-all logic
    # This would require adding a "token_version" field to User model
    # and incrementing it here, then checking it in verify_token
    
    return {
        "message": "Logout from all devices initiated",
        "user_email": current_user.email,
        "note": "Full implementation pending (requires token versioning)"
    }



# ============================================================================
# RBAC TEST ENDPOINTS (Step 5.6 Validation)
# ============================================================================

@router.get(
    "/admin-only",
    summary="Admin-only endpoint",
    description="Test endpoint that requires ADMIN role",
    tags=["rbac-tests"],
)
async def admin_only_endpoint(
    current_user: UserInDB = Depends(require_admin)
):
    """
    Admin Only Endpoint
    
    Only users with ADMIN role can access this endpoint.
    
    Returns:
        dict: Success message with user info
        
    Raises:
        HTTPException 403: If user does not have ADMIN role
    """
    logger.info(
        f"Admin endpoint accessed by: {current_user.email}",
        extra={"user_id": str(current_user.id), "role": current_user.role.value}
    )
    
    return {
        "message": "Admin access granted",
        "user_email": current_user.email,
        "user_role": current_user.role.value,
        "endpoint": "/admin-only"
    }


@router.get(
    "/user-or-admin",
    summary="User or Admin endpoint",
    description="Test endpoint that requires USER or ADMIN role",
    tags=["rbac-tests"],
)
async def user_or_admin_endpoint(
    current_user: UserInDB = Depends(require_admin_or_user)
):
    """
    User or Admin Endpoint
    
    Users with USER or ADMIN role can access this endpoint.
    VIEWER role will be denied.
    
    Returns:
        dict: Success message with user info
        
    Raises:
        HTTPException 403: If user does not have USER or ADMIN role
    """
    logger.info(
        f"User/Admin endpoint accessed by: {current_user.email}",
        extra={"user_id": str(current_user.id), "role": current_user.role.value}
    )
    
    return {
        "message": "User or Admin access granted",
        "user_email": current_user.email,
        "user_role": current_user.role.value,
        "allowed_roles": ["user", "admin"],
        "endpoint": "/user-or-admin"
    }


@router.get(
    "/any-authenticated",
    summary="Any authenticated user",
    description="Test endpoint that accepts any authenticated user",
    tags=["rbac-tests"],
)
async def any_authenticated_endpoint(
    current_user: UserInDB = Depends(require_any_role)
):
    """
    Any Authenticated User Endpoint
    
    Any authenticated user (ADMIN, USER, or VIEWER) can access this endpoint.
    
    Returns:
        dict: Success message with user info
    """
    logger.info(
        f"Any-role endpoint accessed by: {current_user.email}",
        extra={"user_id": str(current_user.id), "role": current_user.role.value}
    )
    
    return {
        "message": "Authenticated access granted",
        "user_email": current_user.email,
        "user_role": current_user.role.value,
        "allowed_roles": ["admin", "user", "viewer"],
        "endpoint": "/any-authenticated"
    }


@router.get(
    "/custom-role-check",
    summary="Custom role check example",
    description="Example of using RoleChecker with custom roles",
    tags=["rbac-tests"],
)
async def custom_role_check_endpoint(
    current_user: UserInDB = Depends(RoleChecker([UserRole.ADMIN, UserRole.VIEWER]))
):
    """
    Custom Role Check Endpoint
    
    Example showing how to create custom role requirements.
    This endpoint only allows ADMIN and VIEWER (but not USER).
    
    Returns:
        dict: Success message with user info
        
    Raises:
        HTTPException 403: If user does not have ADMIN or VIEWER role
    """
    logger.info(
        f"Custom-role endpoint accessed by: {current_user.email}",
        extra={"user_id": str(current_user.id), "role": current_user.role.value}
    )
    
    return {
        "message": "Custom role check passed",
        "user_email": current_user.email,
        "user_role": current_user.role.value,
        "allowed_roles": ["admin", "viewer"],
        "note": "USER role is NOT allowed on this endpoint",
        "endpoint": "/custom-role-check"
    }

# ============================================================================
# PASSWORD RESET (Step 5.8)
# ============================================================================

@router.post(
    "/password-reset/request",
    status_code=status.HTTP_200_OK,
    summary="Request password reset",
    description="Request a password reset link to be sent to email",
    tags=["password-reset"],
)
async def request_password_reset(request: PasswordResetRequest):
    """
    Request Password Reset
    
    Generates a password reset token and sends it to the user's email.
    For security, always returns success even if email doesn't exist.
    
    Args:
        request: Password reset request with email
        
    Returns:
        dict: Success message
        
    Note:
        In production, this would send an email with the reset link.
        For now, it logs the token for testing purposes.
    """
    try:
        # Get user by email
        user = await user_repository.get_by_email(request.email)
        
        if user:
            # Generate reset token
            reset_token = jwt_service.create_password_reset_token(
                user_id=str(user.id),
                email=user.email
            )
            
            # TODO: Send email with reset link
            # In production, you would:
            # 1. Create reset link: f"https://yourapp.com/reset-password?token={reset_token}"
            # 2. Send email via email service
            # For now, just log it (REMOVE IN PRODUCTION)
            logger.info(
                f"Password reset requested for: {user.email}",
                extra={
                    "user_id": str(user.id),
                    "reset_token": reset_token  # REMOVE IN PRODUCTION
                }
            )
            
            # In development, return the token for testing
            # REMOVE THIS IN PRODUCTION
            from app.core.config import settings
            if not settings.is_production:
                return {
                    "message": "Password reset instructions sent to email",
                    "reset_token": reset_token,  # DEV ONLY
                    "note": "In production, this would be sent via email"
                }
        else:
            # For security, don't reveal that email doesn't exist
            logger.warning(f"Password reset requested for non-existent email: {request.email}")
        
        # Always return success to prevent email enumeration
        return {
            "message": "If the email exists, password reset instructions have been sent"
        }
        
    except Exception as e:
        logger.error(f"Password reset request error: {e}")
        # Still return success for security
        return {
            "message": "If the email exists, password reset instructions have been sent"
        }


@router.post(
    "/password-reset/verify",
    status_code=status.HTTP_200_OK,
    summary="Verify password reset token",
    description="Verify if a password reset token is valid",
    tags=["password-reset"],
)
async def verify_password_reset_token(request: PasswordResetVerify):
    """
    Verify Password Reset Token
    
    Checks if a password reset token is valid and not expired.
    Useful for frontend validation before showing reset form.
    
    Args:
        request: Token verification request
        
    Returns:
        dict: Token validity status
        
    Raises:
        HTTPException 400: If token is invalid or expired
    """
    try:
        # Decode and verify token
        payload = jwt_service.decode_token(request.token)
        
        # Check token type
        if payload.get("type") != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type"
            )
        
        # Get user to verify they still exist and are active
        user_id = payload.get("sub")
        user = await user_repository.get_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive"
            )
        
        logger.info(f"Password reset token verified for: {user.email}")
        
        return {
            "valid": True,
            "email": user.email,
            "message": "Token is valid"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Invalid password reset token: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )


@router.post(
    "/password-reset/confirm",
    status_code=status.HTTP_200_OK,
    summary="Confirm password reset",
    description="Complete password reset with new password",
    tags=["password-reset"],
)
async def confirm_password_reset(request: PasswordResetConfirm):
    """
    Confirm Password Reset
    
    Completes the password reset by setting a new password.
    Invalidates the reset token after successful use.
    
    Args:
        request: Password reset confirmation with token and new password
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException 400: If token is invalid or expired
        HTTPException 500: If password update fails
    """
    try:
        # Decode and verify token
        payload = jwt_service.decode_token(request.token)
        
        # Check token type
        if payload.get("type") != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token type"
            )
        
        # Get user
        user_id = payload.get("sub")
        email = payload.get("email")
        
        user = await user_repository.get_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User not found"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User account is inactive"
            )
        
        # Verify email matches (extra security)
        if user.email != email:
            logger.error(f"Email mismatch in password reset token")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid reset token"
            )
        
        # Update password
        from app.models.user import UserUpdate
        update_data = UserUpdate(password=request.new_password)
        
        updated_user = await user_repository.update(str(user.id), update_data)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )
        
        logger.info(
            f"Password reset completed for: {user.email}",
            extra={"user_id": str(user.id)}
        )
        
        # TODO: Optionally blacklist the reset token to prevent reuse
        # (would require adding reset tokens to blacklist with 1-hour TTL)
        
        return {
            "message": "Password has been reset successfully",
            "email": user.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset confirmation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )


@router.post(
    "/password-change",
    status_code=status.HTTP_200_OK,
    summary="Change password",
    description="Change password for authenticated user",
    tags=["password-reset"],
)
async def change_password(
    request: PasswordChange,
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Change Password
    
    Allows authenticated users to change their password.
    Requires current password verification.
    
    Args:
        request: Password change request with current and new password
        current_user: Current authenticated user
        
    Returns:
        dict: Success message
        
    Raises:
        HTTPException 400: If current password is incorrect
        HTTPException 500: If password update fails
    """
    try:
        # Verify current password
        if not verify_password(request.current_password, current_user.hashed_password):
            logger.warning(f"Incorrect current password for: {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Check new password is different
        if verify_password(request.new_password, current_user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from current password"
            )
        
        # Update password
        from app.models.user import UserUpdate
        update_data = UserUpdate(password=request.new_password)
        
        updated_user = await user_repository.update(str(current_user.id), update_data)
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update password"
            )
        
        logger.info(
            f"Password changed for: {current_user.email}",
            extra={"user_id": str(current_user.id)}
        )
        
        return {
            "message": "Password changed successfully",
            "email": current_user.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while changing password"
        )