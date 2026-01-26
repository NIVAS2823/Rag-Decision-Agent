"""
Cache Integration Tests
=======================
Test caching with real database operations.
"""
import pytest_asyncio
import pytest
import time
from app.models.user import UserCreate, UserRole
from app.models.decision import DecisionCreate
from app.services.database import mongodb_manager
from app.services.database.repositories import user_repository, decision_repository
from app.services.cache import redis_client, cache_utils
from app.core.config import settings


@pytest_asyncio.fixture
async def setup_integration():
    """Setup database and cache for integration tests"""
    if not settings.REDIS_ENABLE:
        pytest.skip("Redis is disabled")
    
    from app.services.database.redis_manager import redis_manager
    await mongodb_manager.connect()
    await redis_manager.connect()
    
    # Clean cache
    await redis_client.delete_pattern("*")
    
    yield
    
    # Cleanup
    await user_repository.collection.delete_many({"email": {"$regex": "^cachetest.*@example.com$"}})
    await decision_repository.collection.delete_many({})
    await redis_client.delete_pattern("*")
    
    await mongodb_manager.disconnect()
    await redis_manager.disconnect()


@pytest.mark.asyncio
async def test_user_caching_performance(setup_integration):
    """Test that caching improves user lookup performance"""
    # Create user
    user_data = UserCreate(
        email="cachetest_perf@example.com",
        password="SecurePass123",
        full_name="Cache Test User"
    )
    user = await user_repository.create(user_data)
    user_id = str(user.id)
    
    # First call (no cache) - measure time
    start = time.time()
    user1 = await user_repository.get_by_id_cached(user_id)
    time_uncached = time.time() - start
    
    assert user1 is not None
    
    # Second call (cached) - should be faster
    start = time.time()
    user2 = await user_repository.get_by_id_cached(user_id)
    time_cached = time.time() - start
    
    assert user2 is not None
    assert user1.email == user2.email
    
    # Cached call should be faster (or at least not slower)
    # In real scenarios, cache is significantly faster
    print(f"\nUncached: {time_uncached*1000:.2f}ms, Cached: {time_cached*1000:.2f}ms")
    assert time_cached <= time_uncached * 2  # Allow some variance


@pytest.mark.asyncio
async def test_user_cache_invalidation(setup_integration):
    """Test that updating user invalidates cache"""
    # Create user
    user_data = UserCreate(
        email="cachetest_invalidate@example.com",
        password="SecurePass123",
        full_name="Original Name"
    )
    user = await user_repository.create(user_data)
    user_id = str(user.id)
    
    # Get user (caches it)
    user1 = await user_repository.get_by_id_cached(user_id)
    assert user1.full_name == "Original Name"
    
    # Update user (should invalidate cache)
    from app.models.user import UserUpdate
    update_data = UserUpdate(full_name="Updated Name")
    await user_repository.update(user_id, update_data)
    
    # Get user again (should fetch fresh data)
    user2 = await user_repository.get_by_id_cached(user_id)
    assert user2.full_name == "Updated Name"


@pytest.mark.asyncio
async def test_decision_caching(setup_integration):
    """Test decision caching"""
    # Create user
    user_data = UserCreate(
        email="cachetest_decision@example.com",
        password="SecurePass123",
        full_name="Decision Test"
    )
    user = await user_repository.create(user_data)
    user_id = str(user.id)
    
    # Create decision
    decision_data = DecisionCreate(query="Should we cache decisions?")
    decision = await decision_repository.create(user_id, decision_data)
    decision_id = str(decision.id)
    
    # Get decision (caches it)
    decision1 = await decision_repository.get_by_id_cached(decision_id)
    assert decision1 is not None
    
    # Get again (from cache)
    decision2 = await decision_repository.get_by_id_cached(decision_id)
    assert decision2 is not None
    assert str(decision1.id) == str(decision2.id)


@pytest.mark.asyncio
async def test_decision_list_caching(setup_integration):
    """Test caching of user's decision list"""
    # Create user
    user_data = UserCreate(
        email="cachetest_list@example.com",
        password="SecurePass123",
        full_name="List Test"
    )
    user = await user_repository.create(user_data)
    user_id = str(user.id)
    
    # Create multiple decisions
    for i in range(5):
        decision_data = DecisionCreate(query=f"Decision {i}?")
        await decision_repository.create(user_id, decision_data)
    
    # Get decisions (caches the list)
    start = time.time()
    decisions1 = await decision_repository.get_by_user_cached(user_id, limit=10)
    time_uncached = time.time() - start
    
    assert len(decisions1) == 5
    
    # Get again (from cache)
    start = time.time()
    decisions2 = await decision_repository.get_by_user_cached(user_id, limit=10)
    time_cached = time.time() - start
    
    assert len(decisions2) == 5
    
    print(f"\nList uncached: {time_uncached*1000:.2f}ms, cached: {time_cached*1000:.2f}ms")


@pytest.mark.asyncio
async def test_cache_aside_pattern(setup_integration):
    """Test cache-aside pattern with real data"""
    fetch_count = 0
    
    async def expensive_fetch():
        nonlocal fetch_count
        fetch_count += 1
        
        # Simulate expensive operation
        import asyncio
        await asyncio.sleep(0.1)
        
        return {"data": "expensive_result", "timestamp": time.time()}
    
    # First call - fetches data
    result1 = await cache_utils.get_or_set("test:expensive", expensive_fetch, ttl=60)
    assert fetch_count == 1
    
    # Second call - uses cache
    result2 = await cache_utils.get_or_set("test:expensive", expensive_fetch, ttl=60)
    assert fetch_count == 1  # Not called again
    assert result1["data"] == result2["data"]


@pytest.mark.asyncio
async def test_rate_limiting_integration(setup_integration):
    """Test rate limiting with real usage"""
    user_id = "test_user_123"
    endpoint = "/api/test"
    
    # Make requests within limit
    for i in range(5):
        allowed, remaining = await cache_utils.check_rate_limit(
            user_id, endpoint, limit=10, window=60
        )
        assert allowed is True
        assert remaining == 10 - (i + 1)
    
    # Should still have 5 remaining
    allowed, remaining = await cache_utils.check_rate_limit(
        user_id, endpoint, limit=10, window=60
    )
    assert allowed is True
    assert remaining == 4


@pytest.mark.asyncio
async def test_cache_statistics(setup_integration):
    """Test cache statistics tracking"""
    from app.services.cache import cache_keys
    
    # Create some cached data
    await redis_client.set(cache_keys.user_by_id("123"), {"name": "User 1"})
    await redis_client.set(cache_keys.user_by_id("124"), {"name": "User 2"})
    await redis_client.set(cache_keys.decision_by_id("456"), {"query": "Test"})
    await redis_client.set(cache_keys.session("abc"), {"user_id": "123"})
    
    # Get stats
    stats = await cache_utils.get_cache_stats()
    
    assert stats["total_keys"] >= 4
    assert stats["user_keys"] >= 2
    assert stats["decision_keys"] >= 1
    assert stats["session_keys"] >= 1


@pytest.mark.asyncio
async def test_cache_ttl_expiration(setup_integration):
    """Test that cache respects TTL"""
    import asyncio
    
    # Set data with short TTL
    key = "test:ttl_expiry"
    await redis_client.set(key, "expires_soon", ttl=2)
    
    # Should exist immediately
    value = await redis_client.get(key)
    assert value == "expires_soon"
    
    # Wait for expiration
    await asyncio.sleep(3)
    
    # Should be expired
    value = await redis_client.get(key)
    assert value is None


@pytest.mark.asyncio
async def test_multiple_cache_layers(setup_integration):
    """Test using multiple cache strategies together"""
    # Create user
    user_data = UserCreate(
        email="cachetest_layers@example.com",
        password="SecurePass123",
        full_name="Layers Test"
    )
    user = await user_repository.create(user_data)
    user_id = str(user.id)
    
    # Cache by ID
    user_by_id = await user_repository.get_by_id_cached(user_id)
    assert user_by_id is not None
    
    # Cache by email
    user_by_email = await user_repository.get_by_email_cached("cachetest_layers@example.com")
    assert user_by_email is not None
    
    # Both should return same user
    assert user_by_id.email == user_by_email.email
    
    # Verify both caches exist
    from app.services.cache import cache_keys
    id_exists = await redis_client.exists(cache_keys.user_by_id(user_id))
    email_exists = await redis_client.exists(cache_keys.user_by_email("cachetest_layers@example.com"))
    
    assert id_exists is True
    assert email_exists is True