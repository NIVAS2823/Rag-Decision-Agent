"""
Tests for cache invalidation
"""
import pytest
from app.models.user import UserCreate
from app.models.decision import DecisionCreate
from app.services.database import mongodb_manager
from app.services.database.repositories import user_repository, decision_repository
from app.services.cache import redis_client, cache_keys, cache_invalidation
from app.core.config import settings
import pytest_asyncio

@pytest_asyncio.fixture
async def setup_invalidation():
    """Setup for invalidation tests"""
    if not settings.REDIS_ENABLE:
        pytest.skip("Redis is disabled")
    
    from app.services.database.redis_manager import redis_manager
    await mongodb_manager.connect()
    await redis_manager.connect()
    
    # Clean cache
    await redis_client.delete_pattern("*")
    
    yield
    
    # Cleanup
    await user_repository.collection.delete_many({"email": {"$regex": "^invalidtest.*@example.com$"}})
    await decision_repository.collection.delete_many({})
    await redis_client.delete_pattern("*")
    
    await mongodb_manager.disconnect()
    await redis_manager.disconnect()


@pytest.mark.asyncio
async def test_user_invalidation(setup_invalidation):
    """Test user cache invalidation"""
    # Create and cache user
    user_data = UserCreate(
        email="invalidtest@example.com",
        password="SecurePass123",
        full_name="Invalidation Test"
    )
    user = await user_repository.create(user_data)
    user_id = str(user.id)
    
    # Cache user
    cached_user = await user_repository.get_by_id_cached(user_id)
    assert cached_user is not None
    
    # Verify cache exists
    cache_exists = await redis_client.exists(cache_keys.user_by_id(user_id))
    assert cache_exists is True
    
    # Invalidate
    counts = await cache_invalidation.invalidate_user(user_id)
    total = sum(counts.values())
    assert total > 0
    
    # Verify cache is gone
    cache_exists = await redis_client.exists(cache_keys.user_by_id(user_id))
    assert cache_exists is False


@pytest.mark.asyncio
async def test_decision_invalidation(setup_invalidation):
    """Test decision cache invalidation"""
    # Create user and decision
    user_data = UserCreate(
        email="invalidtest_decision@example.com",
        password="SecurePass123",
        full_name="Decision Test"
    )
    user = await user_repository.create(user_data)
    user_id = str(user.id)
    
    decision_data = DecisionCreate(query="Test query?")
    decision = await decision_repository.create(user_id, decision_data)
    decision_id = str(decision.id)
    
    # Cache decision
    await decision_repository.get_by_id_cached(decision_id)
    
    # Verify cached
    cache_exists = await redis_client.exists(cache_keys.decision_by_id(decision_id))
    assert cache_exists is True
    
    # Invalidate
    deleted = await cache_invalidation.invalidate_decision(decision_id)
    assert deleted > 0
    
    # Verify gone
    cache_exists = await redis_client.exists(cache_keys.decision_by_id(decision_id))
    assert cache_exists is False


@pytest.mark.asyncio
async def test_user_decisions_list_invalidation(setup_invalidation):
    """Test invalidation of user's decision list cache"""
    # Create user
    user_data = UserCreate(
        email="invalidtest_list@example.com",
        password="SecurePass123",
        full_name="List Test"
    )
    user = await user_repository.create(user_data)
    user_id = str(user.id)
    
    # Create and cache decisions list
    decision_data = DecisionCreate(query="Test decision query?")
    await decision_repository.create(user_id, decision_data)
    await decision_repository.get_by_user_cached(user_id)
    
    # Verify cached
    cache_exists = await redis_client.exists(cache_keys.user_decisions(user_id, page=1))
    assert cache_exists is True
    
    # Invalidate
    deleted = await cache_invalidation.invalidate_user_decisions(user_id)
    assert deleted > 0
    
    # Verify gone
    cache_exists = await redis_client.exists(cache_keys.user_decisions(user_id, page=1))
    assert cache_exists is False


@pytest.mark.asyncio
async def test_pattern_invalidation(setup_invalidation):
    """Test pattern-based invalidation"""
    # Create multiple cache entries
    await redis_client.set("v1:test:pattern:1", "value1")
    await redis_client.set("v1:test:pattern:2", "value2")
    await redis_client.set("v1:test:other:3", "value3")
    
    # Invalidate pattern
    deleted = await cache_invalidation.invalidate_by_pattern("*:test:pattern:*")
    assert deleted == 2
    
    # Verify only pattern keys deleted
    assert await redis_client.exists("v1:test:pattern:1") is False
    assert await redis_client.exists("v1:test:pattern:2") is False
    assert await redis_client.exists("v1:test:other:3") is True


@pytest.mark.asyncio
async def test_invalidation_stats(setup_invalidation):
    """Test invalidation statistics"""
    # Create some cache entries
    await redis_client.set(cache_keys.user_by_id("123"), {"name": "User"})
    await redis_client.set(cache_keys.decision_by_id("456"), {"query": "Test"})
    
    # Get stats
    stats = await cache_invalidation.get_invalidation_stats()
    
    assert "total_keys" in stats
    assert "by_type" in stats
    assert "timestamp" in stats
    assert stats["total_keys"] >= 2


def test_admin_cache_endpoints():
    """Test admin cache management endpoints"""
    from fastapi.testclient import TestClient
    from app.main import app
    
    with TestClient(app) as client:
        response = client.get("/api/v1/admin/cache/stats")
    assert response.status_code == 200
    
    data = response.json()
    assert "invalidation_stats" in data
    assert "general_stats" in data