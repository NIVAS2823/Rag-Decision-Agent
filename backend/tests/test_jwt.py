"""
Tests for JWT token service
"""
import pytest_asyncio
import pytest
import time
from datetime import timedelta
from jose import jwt

from app.services.auth import jwt_service
from app.models.user import UserRole
from app.core.config import settings


def test_create_access_token():
    """Test creating an access token"""
    token = jwt_service.create_access_token(
        user_id="user123",
        email="test@example.com",
        role=UserRole.USER
    )
    
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 50  # JWT tokens are long
    
    # Decode to verify payload
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
    
    assert payload["sub"] == "user123"
    assert payload["email"] == "test@example.com"
    assert payload["role"] == "user"
    assert payload["type"] == "access"
    assert "exp" in payload
    assert "iat" in payload


def test_create_refresh_token():
    """Test creating a refresh token"""
    token = jwt_service.create_refresh_token(user_id="user123")
    
    assert token is not None
    assert isinstance(token, str)
    
    # Decode to verify payload
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
    
    assert payload["sub"] == "user123"
    assert payload["type"] == "refresh"
    assert "exp" in payload
    assert "iat" in payload
    # Refresh tokens don't include email/role
    assert "email" not in payload
    assert "role" not in payload


def test_create_token_pair():
    """Test creating both access and refresh tokens"""
    tokens = jwt_service.create_token_pair(
        user_id="user123",
        email="test@example.com",
        role=UserRole.ADMIN
    )
    
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert "token_type" in tokens
    assert tokens["token_type"] == "bearer"
    
    # Verify both tokens are valid
    access_payload = jwt.decode(
        tokens["access_token"],
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
    
    refresh_payload = jwt.decode(
        tokens["refresh_token"],
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
    
    assert access_payload["type"] == "access"
    assert refresh_payload["type"] == "refresh"
    assert access_payload["role"] == "admin"


def test_access_token_expiration():
    """Test that access token has correct expiration"""
    token = jwt_service.create_access_token(
        user_id="user123",
        email="test@example.com",
        role=UserRole.USER
    )
    
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
    
    # Check expiration is in the future
    exp_time = payload["exp"]
    current_time = time.time()
    
    assert exp_time > current_time
    
    # Check it expires in approximately the configured time
    time_diff = exp_time - current_time
    expected_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    # Allow 5 second variance
    assert abs(time_diff - expected_seconds) < 5


def test_custom_expiration():
    """Test creating token with custom expiration"""
    custom_delta = timedelta(minutes=60)
    
    token = jwt_service.create_access_token(
        user_id="user123",
        email="test@example.com",
        role=UserRole.USER,
        expires_delta=custom_delta
    )
    
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
    
    exp_time = payload["exp"]
    iat_time = payload["iat"]
    
    # Should expire in approximately 60 minutes
    time_diff = exp_time - iat_time
    assert abs(time_diff - 3600) < 5  # 60 minutes = 3600 seconds


def test_password_reset_token():
    """Test creating password reset token"""
    token = jwt_service.create_password_reset_token(
        user_id="user123",
        email="test@example.com"
    )
    
    assert token is not None
    
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
    
    assert payload["type"] == "password_reset"
    assert payload["email"] == "test@example.com"


def test_email_verification_token():
    """Test creating email verification token"""
    token = jwt_service.create_email_verification_token(
        user_id="user123",
        email="test@example.com"
    )
    
    assert token is not None
    
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
    
    assert payload["type"] == "email_verification"
    assert payload["email"] == "test@example.com"


def test_token_includes_issued_at():
    """Test that tokens include issued at timestamp"""
    token = jwt_service.create_access_token(
        user_id="user123",
        email="test@example.com",
        role=UserRole.USER
    )
    
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
    
    assert "iat" in payload
    
    # Issued at should be recent (within last few seconds)
    current_time = time.time()
    iat_time = payload["iat"]
    
    assert abs(current_time - iat_time) < 5


def test_different_roles():
    """Test creating tokens with different roles"""
    roles = [UserRole.USER, UserRole.ADMIN, UserRole.VIEWER]
    
    for role in roles:
        token = jwt_service.create_access_token(
            user_id="user123",
            email="test@example.com",
            role=role
        )
        
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        assert payload["role"] == role.value