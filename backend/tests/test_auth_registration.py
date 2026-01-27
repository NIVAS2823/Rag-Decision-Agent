"""
Tests for user registration endpoint
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.database import mongodb_manager
from app.services.database.repositories import user_repository


@pytest.fixture
async def setup_auth():
    """Setup for auth tests"""
    await mongodb_manager.connect()
    
    yield
    
    # Cleanup test users
    await user_repository.collection.delete_many({"email": {"$regex": "^authtest.*@example.com$"}})
    await mongodb_manager.disconnect()


def test_register_new_user(setup_auth):
    """Test registering a new user"""
    with TestClient(app) as client:
    
        response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "authtest_new@example.com",
            "password": "SecurePass123",
            "full_name": "Auth Test User",
            "role": "user"
        }
    )
    
    assert response.status_code == 201
    
    data = response.json()
    
    # Check response structure
    assert "user" in data
    assert "tokens" in data
    assert "message" in data
    
    # Check user data
    user = data["user"]
    assert user["email"] == "authtest_new@example.com"
    assert user["full_name"] == "Auth Test User"
    assert user["role"] == "user"
    assert user["is_active"] is True
    assert user["is_verified"] is False
    
    # Check tokens
    tokens = data["tokens"]
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["token_type"] == "bearer"
    
    # Tokens should be long strings
    assert len(tokens["access_token"]) > 50
    assert len(tokens["refresh_token"]) > 50


def test_register_duplicate_email(setup_auth):
    """Test that duplicate email registration fails"""
    with TestClient(app) as client:
    
        user_data = {
        "email": "authtest_duplicate@example.com",
        "password": "SecurePass123",
        "full_name": "Duplicate Test"
    }
    
    # First registration - should succeed
    response1 = client.post("/api/v1/auth/register", json=user_data)
    assert response1.status_code == 201
    
    # Second registration - should fail
    response2 = client.post("/api/v1/auth/register", json=user_data)
    assert response2.status_code == 400
    
    data = response2.json()
    assert "already registered" in data["detail"].lower()


def test_register_invalid_email(setup_auth):
    """Test registration with invalid email"""
    with TestClient(app) as client:
    
        response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "SecurePass123",
            "full_name": "Test User"
        }
    )
    
    assert response.status_code == 422  # Validation error


def test_register_weak_password(setup_auth):
    """Test registration with weak password"""
    with TestClient(app) as client:
    
    # Too short
        response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "authtest_weak@example.com",
            "password": "short",
            "full_name": "Test User"
        }
    )
    
    assert response.status_code == 422
    data = response.json()
    assert "8 characters" in str(data)


def test_register_password_without_uppercase(setup_auth):
    """Test password validation - no uppercase"""
    with TestClient(app) as client:
    
        response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "authtest_noupper@example.com",
            "password": "nouppercase123",
            "full_name": "Test User"
        }
    )
    
    assert response.status_code == 422
    data = response.json()
    assert "uppercase" in str(data).lower()


def test_register_password_without_digit(setup_auth):
    """Test password validation - no digit"""
    with TestClient(app) as client: 
    
        response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "authtest_nodigit@example.com",
            "password": "NoDigitsHere",
            "full_name": "Test User"
        }
    )
    
    assert response.status_code == 422
    data = response.json()
    assert "digit" in str(data).lower()


def test_register_default_role(setup_auth):
    """Test that default role is 'user' if not specified"""
    with TestClient(app) as client:
    
        response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "authtest_defaultrole@example.com",
            "password": "SecurePass123",
            "full_name": "Default Role User"
            # Note: no role specified
        }
    )
    
    assert response.status_code == 201
    
    data = response.json()
    assert data["user"]["role"] == "user"


def test_register_admin_role(setup_auth):
    """Test registering with admin role"""
    with TestClient(app) as client:
    
        response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "authtest_admin@example.com",
            "password": "SecurePass123",
            "full_name": "Admin User",
            "role": "admin"
        }
    )
    
    assert response.status_code == 201
    
    data = response.json()
    assert data["user"]["role"] == "admin"


def test_register_password_not_in_response(setup_auth):
    """Test that password is not returned in response"""
    with TestClient(app) as client:
    
        response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "authtest_password@example.com",
            "password": "SecurePass123",
            "full_name": "Password Test"
        }
    )
    
    assert response.status_code == 201
    
    data = response.json()
    
    # Password should not be in user object
    user = data["user"]
    assert "password" not in user
    assert "hashed_password" not in user


def test_register_tokens_are_valid(setup_auth):
    """Test that returned tokens can be decoded"""
    with TestClient(app) as client:
    
        response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "authtest_tokens@example.com",
            "password": "SecurePass123",
            "full_name": "Token Test"
        }
    )
    
    assert response.status_code == 201
    
    data = response.json()
    access_token = data["tokens"]["access_token"]
    
    # Decode and verify token
    from app.services.auth import jwt_service
    
    payload = jwt_service.verify_access_token(access_token)
    
    assert payload["email"] == "authtest_tokens@example.com"
    assert payload["type"] == "access"