"""
Authentication Routes
====================
User authentication endpoints (register, login, logout, etc.).
"""

from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPBearer

from app.models.user import UserCreate, User, Token
from app.services.database.repositories import user_repository
from app.services.auth import jwt_service
from app.core.logging_config import get_logger
from app.core.exceptions import (
    InvalidCredentialsException,
    UserNotFoundException,
)


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
# PLACEHOLDER FOR FUTURE ENDPOINTS
# ============================================================================

# Login endpoint - Step 5.4
# Logout endpoint - Step 5.7
# Refresh token endpoint - Step 5.4
# Password reset endpoints - Step 5.8