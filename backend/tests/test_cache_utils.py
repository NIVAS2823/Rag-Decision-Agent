"""
Tests for cache utilities
"""
import pytest
from app.services.cache import cache_keys, cache_utils, cached, cache_invalidate
from app.services.database.redis_manager import redis_manager
from app.core.config import settings
import pytest_asyncio


@pytest_asyncio.fixture
async def setup_cache():
    """Setup cache for tests"""
    if not settings.REDIS_ENABLE:
        pytest.skip("Redis is disabled")
    
    await redis_manager.connect()
    
    # Clean up
    from app.services.cache import redis_client
    await redis_client.delete_pattern("*")
    
    yield
    
    await redis_client.delete_pattern("*")
    await redis_manager.disconnect()


def test_cache_key_generation():
    """Test cache key generation"""
    # User keys
    user_key = cache_keys.user_by_id("123")
    assert "user" in user_key
    assert "123" in user_key
    
    # Decision keys
    decision_key = cache_keys.decision_by_id("456")
    assert "decision" in decision_key
    assert "456" in decision_key
    
    # Session keys
    session_key = cache_keys.session("session_abc")
    assert "session" in session_key


@pytest.mark.asyncio
async def test_get_or_set(setup_cache):
    """Test cache-aside pattern"""
    call_count = 0
    
    async def fetch_data():
        nonlocal call_count
        call_count += 1
        return {"data": "value", "count": call_count}
    
    # First call - should fetch
    result1 = await cache_utils.get_or_set("test:key", fetch_data, ttl=60)
    assert result1["count"] == 1
    assert call_count == 1
    
    # Second call - should use cache
    result2 = await cache_utils.get_or_set("test:key", fetch_data, ttl=60)
    assert result2["count"] == 1  # Same data from cache
    assert call_count == 1  # Function not called again


@pytest.mark.asyncio
async def test_cache_decorator(setup_cache):
    """Test cache decorator"""
    call_count = 0
    
    @cached(ttl=60, key_prefix="test")
    async def expensive_function(value: str):
        nonlocal call_count
        call_count += 1
        return f"result_{value}_{call_count}"
    
    # First call
    result1 = await expensive_function("abc")
    assert "result_abc_1" == result1
    assert call_count == 1
    
    # Second call - should be cached
    result2 = await expensive_function("abc")
    assert result2 == result1
    assert call_count == 1  # Not called again
    
    # Different args - should call function
    result3 = await expensive_function("xyz")
    assert "xyz" in result3
    assert call_count == 2


@pytest.mark.asyncio
async def test_cache_invalidation(setup_cache):
    """Test cache invalidation"""
    from app.services.cache import redis_client
    
    # Set some cache
    await redis_client.set("v1:user:id:123", {"name": "John"})
    await redis_client.set("v1:user:id:124", {"name": "Jane"})
    await redis_client.set("v1:decision:id:456", {"query": "test"})
    
    # Invalidate user cache
    deleted = await cache_utils.invalidate_user_cache("123")
    assert deleted >= 1
    
    # Verify user 123 cache is gone
    value = await redis_client.get("v1:user:id:123")
    assert value is None
    
    # Other caches should still exist
    value = await redis_client.get("v1:decision:id:456")
    assert value is not None


@pytest.mark.asyncio
async def test_rate_limiting(setup_cache):
    """Test rate limiting"""
    # First request - should be allowed
    allowed, remaining = await cache_utils.check_rate_limit(
        user_id="user123",
        endpoint="/api/test",
        limit=5,
        window=60
    )
    assert allowed is True
    assert remaining == 4
    
    # Make more requests
    for i in range(4):
        allowed, remaining = await cache_utils.check_rate_limit(
            user_id="user123",
            endpoint="/api/test",
            limit=5,
            window=60
        )
    
    # Should have 0 remaining
    assert remaining == 0
    
    # Next request should be denied
    allowed, remaining = await cache_utils.check_rate_limit(
        user_id="user123",
        endpoint="/api/test",
        limit=5,
        window=60
    )
    assert allowed is False


@pytest.mark.asyncio
async def test_counter_increment(setup_cache):
    """Test counter increment"""
    # Increment counter
    value = await cache_utils.increment_counter("test:counter", amount=1, ttl=60)
    assert value == 1
    
    # Increment again
    value = await cache_utils.increment_counter("test:counter", amount=5)
    assert value == 6


@pytest.mark.asyncio
async def test_cache_stats(setup_cache):
    """Test cache statistics"""
    from app.services.cache import redis_client
    
    # Create some keys
    await redis_client.set("v1:user:id:1", "data1")
    await redis_client.set("v1:decision:id:2", "data2")
    await redis_client.set("v1:session:abc", "data3")
    
    # Get stats
    stats = await cache_utils.get_cache_stats()
    
    assert stats["total_keys"] >= 3
    assert stats["user_keys"] >= 1
    assert stats["decision_keys"] >= 1
    assert stats["session_keys"] >= 1