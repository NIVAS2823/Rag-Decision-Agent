"""
Tests for user repository
"""

import pytest_asyncio
import pytest
from app.models.user import UserCreate, UserUpdate, UserRole
from app.services.database import mongodb_manager
from app.services.database.repositories import user_repository


@pytest_asyncio.fixture
async def setup_database():
    """Setup database for tests"""
    await mongodb_manager.connect()
    yield
    # Cleanup: delete test users
    collection = user_repository.collection
    await collection.delete_many({"email": {"$regex": "^test.*@example.com$"}})
    await mongodb_manager.disconnect()


@pytest.mark.asyncio
async def test_create_user(setup_database):
    """Test creating a user"""
    user_data = UserCreate(
        email="testuser1@example.com",
        password="SecurePass123",
        full_name="Test User",
        role=UserRole.USER
    )
    
    user = await user_repository.create(user_data)
    
    assert user is not None
    assert user.email == "testuser1@example.com"
    assert user.full_name == "Test User"
    assert user.role == UserRole.USER
    assert user.is_active is True
    assert user.is_verified is False
    assert user.hashed_password != "SecurePass123"  # Should be hashed


@pytest.mark.asyncio
async def test_create_duplicate_email(setup_database):
    """Test that duplicate email raises error"""
    user_data = UserCreate(
        email="testdup@example.com",
        password="SecurePass123",
        full_name="Test User"
    )
    
    # Create first user
    await user_repository.create(user_data)
    
    # Try to create duplicate
    with pytest.raises(ValueError, match="already exists"):
        await user_repository.create(user_data)


@pytest.mark.asyncio
async def test_get_user_by_id(setup_database):
    """Test getting user by ID"""
    # Create user
    user_data = UserCreate(
        email="testgetid@example.com",
        password="SecurePass123",
        full_name="Test User"
    )
    created_user = await user_repository.create(user_data)
    
    # Get by ID
    user = await user_repository.get_by_id(str(created_user.id))
    
    assert user is not None
    assert user.email == "testgetid@example.com"


@pytest.mark.asyncio
async def test_get_user_by_email(setup_database):
    """Test getting user by email"""
    # Create user
    user_data = UserCreate(
        email="testgetemail@example.com",
        password="SecurePass123",
        full_name="Test User"
    )
    await user_repository.create(user_data)
    
    # Get by email
    user = await user_repository.get_by_email("testgetemail@example.com")
    
    assert user is not None
    assert user.email == "testgetemail@example.com"


@pytest.mark.asyncio
async def test_update_user(setup_database):
    """Test updating user"""
    # Create user
    user_data = UserCreate(
        email="testupdate@example.com",
        password="SecurePass123",
        full_name="Original Name"
    )
    created_user = await user_repository.create(user_data)
    
    # Update user
    update_data = UserUpdate(full_name="Updated Name", role=UserRole.ADMIN)
    updated_user = await user_repository.update(str(created_user.id), update_data)
    
    assert updated_user is not None
    assert updated_user.full_name == "Updated Name"
    assert updated_user.role == UserRole.ADMIN


@pytest.mark.asyncio
async def test_soft_delete_user(setup_database):
    """Test soft deleting user"""
    # Create user
    user_data = UserCreate(
        email="testdelete@example.com",
        password="SecurePass123",
        full_name="Test User"
    )
    created_user = await user_repository.create(user_data)
    
    # Soft delete
    result = await user_repository.soft_delete(str(created_user.id))
    assert result is True
    
    # Verify user is inactive
    user = await user_repository.get_by_id(str(created_user.id))
    assert user.is_active is False


@pytest.mark.asyncio
async def test_get_all_users(setup_database):
    """Test getting all users with pagination"""
    # Create multiple users
    for i in range(5):
        user_data = UserCreate(
            email=f"testlist{i}@example.com",
            password="SecurePass123",
            full_name=f"Test User {i}"
        )
        await user_repository.create(user_data)
    
    # Get users
    users = await user_repository.get_all(skip=0, limit=10)
    
    assert len(users) >= 5


@pytest.mark.asyncio
async def test_count_users(setup_database):
    """Test counting users"""
    # Create users
    for i in range(3):
        user_data = UserCreate(
            email=f"testcount{i}@example.com",
            password="SecurePass123",
            full_name=f"Test User {i}"
        )
        await user_repository.create(user_data)
    
    # Count
    count = await user_repository.count()
    assert count >= 3


@pytest.mark.asyncio
async def test_exists_by_email(setup_database):
    """Test checking if user exists by email"""
    # Create user
    user_data = UserCreate(
        email="testexists@example.com",
        password="SecurePass123",
        full_name="Test User"
    )
    await user_repository.create(user_data)
    
    # Check exists
    exists = await user_repository.exists_by_email("testexists@example.com")
    assert exists is True
    
    # Check non-existent
    exists = await user_repository.exists_by_email("nonexistent@example.com")
    assert exists is False