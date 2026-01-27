"""
Tests for JWT token verification
"""
import pytest
import time
from datetime import timedelta
from jose import JWTError

from app.services.auth.jwt import jwt_service
from app.services.auth.token_blacklist import token_blacklist
from app.models.user import UserRole
from app.core.config import settings


def test_decode_valid_token():
    """Test decoding a valid token"""
    # Create token
    token = jwt_service.create_access_token(
        user_id="user123",
        email="test@example.com",
        role=UserRole.USER
    )
    
    # Decode it
    payload = jwt_service.decode_token(token)
    
    assert payload is not None
    assert payload["sub"] == "user123"
    assert payload["email"] == "test@example.com"


def test_decode_expired_token():
    """Test that expired tokens are rejected"""
    # Create token that expires immediately
    token = jwt_service.create_access_token(
        user_id="user123",
        email="test@example.com",
        role=UserRole.USER,
        expires_delta=timedelta(seconds=-1)  # Already expired
    )
    
    # Should raise error
    from jose import ExpiredSignatureError
    with pytest.raises(ExpiredSignatureError):
        jwt_service.decode_token(token)


def test_decode_invalid_signature():
    """Test that tokens with invalid signatures are rejected"""
    token = jwt_service.create_access_token(
        user_id="user123",
        email="test@example.com",
        role=UserRole.USER
    )
    
    # Tamper with token (change last character)
    parts = token.split(".")
    parts[2] = "x" * len(parts[2])
    tampered_token = ".".join(parts)
    
    # Should raise error
    with pytest.raises(JWTError):
        jwt_service.decode_token(tampered_token)


def test_verify_access_token():
    """Test verifying access token"""
    token = jwt_service.create_access_token(
        user_id="user123",
        email="test@example.com",
        role=UserRole.USER
    )
    
    payload = jwt_service.verify_access_token(token)
    
    assert payload is not None
    assert payload["type"] == "access"


def test_verify_refresh_token():
    """Test verifying refresh token"""
    token = jwt_service.create_refresh_token(user_id="user123")
    
    payload = jwt_service.verify_refresh_token(token)
    
    assert payload is not None
    assert payload["type"] == "refresh"


def test_verify_wrong_token_type():
    """Test that access token fails refresh verification"""
    access_token = jwt_service.create_access_token(
        user_id="user123",
        email="test@example.com",
        role=UserRole.USER
    )
    
    # Should raise error when verifying as refresh token
    with pytest.raises(ValueError, match="expected refresh token"):
        jwt_service.verify_refresh_token(access_token)


def test_extract_user_id():
    """Test extracting user ID from token"""
    token = jwt_service.create_access_token(
        user_id="user123",
        email="test@example.com",
        role=UserRole.USER
    )
    
    user_id = jwt_service.extract_user_id(token)
    
    assert user_id == "user123"


def test_get_token_expiration():
    """Test getting token expiration"""
    token = jwt_service.create_access_token(
        user_id="user123",
        email="test@example.com",
        role=UserRole.USER
    )
    
    exp = jwt_service.get_token_expiration(token)
    
    assert exp is not None
    assert exp > time.time()


def test_calculate_token_ttl():
    """Test calculating token TTL"""
    token = jwt_service.create_access_token(
        user_id="user123",
        email="test@example.com",
        role=UserRole.USER
    )
    
    ttl = jwt_service.calculate_token_ttl(token)
    
    assert ttl is not None
    assert ttl > 0
    
    # Should be approximately ACCESS_TOKEN_EXPIRE_MINUTES * 60
    expected_ttl = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert abs(ttl - expected_ttl) < 5  # Allow 5 second variance


@pytest.mark.asyncio
async def test_token_blacklist():
    """Test token blacklist functionality"""
    if not settings.REDIS_ENABLE:
        pytest.skip("Redis is disabled")
    
    from app.services.database.redis_manager import redis_manager
    await redis_manager.connect()
    
    try:
        token = "test_token_abc123"
        
        # Should not be blacklisted initially
        is_blacklisted = await token_blacklist.is_blacklisted(token)
        assert is_blacklisted is False
        
        # Add to blacklist
        result = await token_blacklist.add_token(token, expires_in=60)
        assert result is True
        
        # Should now be blacklisted
        is_blacklisted = await token_blacklist.is_blacklisted(token)
        assert is_blacklisted is True
        
        # Cleanup
        await token_blacklist.remove_token(token)
        
    finally:
        await redis_manager.disconnect()


@pytest.mark.asyncio
async def test_verify_token_with_blacklist():
    """Test verifying token with blacklist check"""
    if not settings.REDIS_ENABLE:
        pytest.skip("Redis is disabled")
    
    from app.services.database.redis_manager import redis_manager
    await redis_manager.connect()
    
    try:
        # Create token
        token = jwt_service.create_access_token(
            user_id="user123",
            email="test@example.com",
            role=UserRole.USER
        )
        
        # Should verify successfully
        payload = await jwt_service.verify_token_with_blacklist(token)
        assert payload is not None
        
        # Add to blacklist
        ttl = jwt_service.calculate_token_ttl(token)
        await token_blacklist.add_token(token, expires_in=ttl)
        
        # Should now fail verification
        with pytest.raises(ValueError, match="revoked"):
            await jwt_service.verify_token_with_blacklist(token)
        
        # Cleanup
        await token_blacklist.remove_token(token)
        
    finally:
        await redis_manager.disconnect()