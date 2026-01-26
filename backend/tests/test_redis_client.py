"""
Tests for Redis client wrapper
"""
import pytest
from app.services.cache import redis_client
from app.services.database.redis_manager import redis_manager
from app.core.config import settings
import pytest_asyncio


@pytest_asyncio.fixture
async def setup_redis():
    """Setup Redis for tests"""
    if not settings.REDIS_ENABLE:
        pytest.skip("Redis is disabled")
    
    await redis_manager.connect()
    
    # Clean up test keys before tests
    await redis_client.delete_pattern("test:*")
    
    yield
    
    # Clean up after tests
    await redis_client.delete_pattern("test:*")
    await redis_manager.disconnect()


@pytest.mark.asyncio
async def test_set_and_get(setup_redis):
    """Test basic set and get operations"""
    # Set string value
    result = await redis_client.set("test:string", "hello world")
    assert result is True
    
    # Get value
    value = await redis_client.get("test:string")
    assert value == "hello world"


@pytest.mark.asyncio
async def test_set_and_get_json(setup_redis):
    """Test JSON serialization"""
    # Set complex object
    data = {"name": "John", "age": 30, "active": True}
    result = await redis_client.set("test:json", data)
    assert result is True
    
    # Get and verify
    value = await redis_client.get("test:json")
    assert value == data
    assert value["name"] == "John"


@pytest.mark.asyncio
async def test_set_with_ttl(setup_redis):
    """Test TTL (time to live)"""
    import asyncio
    
    # Set with 2 second TTL
    await redis_client.set("test:ttl", "expires soon", ttl=2)
    
    # Should exist immediately
    exists = await redis_client.exists("test:ttl")
    assert exists is True
    
    # Check TTL
    ttl = await redis_client.ttl("test:ttl")
    assert ttl > 0 and ttl <= 2
    
    # Wait for expiry
    await asyncio.sleep(3)
    
    # Should be gone
    value = await redis_client.get("test:ttl")
    assert value is None


@pytest.mark.asyncio
async def test_delete(setup_redis):
    """Test delete operation"""
    # Set value
    await redis_client.set("test:delete", "to be deleted")
    
    # Delete
    result = await redis_client.delete("test:delete")
    assert result is True
    
    # Verify deleted
    value = await redis_client.get("test:delete")
    assert value is None


@pytest.mark.asyncio
async def test_exists(setup_redis):
    """Test exists operation"""
    # Set value
    await redis_client.set("test:exists", "I exist")
    
    # Should exist
    exists = await redis_client.exists("test:exists")
    assert exists is True
    
    # Non-existent key
    exists = await redis_client.exists("test:nonexistent")
    assert exists is False


@pytest.mark.asyncio
async def test_hash_operations(setup_redis):
    """Test hash operations"""
    # Set hash fields
    await redis_client.hset("test:hash", "field1", "value1")
    await redis_client.hset("test:hash", "field2", {"nested": "object"})
    
    # Get individual field
    value = await redis_client.hget("test:hash", "field1")
    assert value == "value1"
    
    # Get nested object
    value = await redis_client.hget("test:hash", "field2")
    assert value == {"nested": "object"}
    
    # Get all fields
    all_data = await redis_client.hgetall("test:hash")
    assert "field1" in all_data
    assert "field2" in all_data


@pytest.mark.asyncio
async def test_list_operations(setup_redis):
    """Test list operations"""
    # Push items
    await redis_client.lpush("test:list", "item1", "item2", "item3")
    
    # Get range
    items = await redis_client.lrange("test:list", 0, -1)
    assert len(items) == 3
    assert "item1" in items


@pytest.mark.asyncio
async def test_delete_pattern(setup_redis):
    """Test pattern-based deletion"""
    # Create multiple keys
    await redis_client.set("test:pattern:1", "value1")
    await redis_client.set("test:pattern:2", "value2")
    await redis_client.set("test:other", "value3")
    
    # Delete pattern
    deleted = await redis_client.delete_pattern("test:pattern:*")
    assert deleted == 2
    
    # Verify only pattern keys deleted
    assert await redis_client.exists("test:pattern:1") is False
    assert await redis_client.exists("test:pattern:2") is False
    assert await redis_client.exists("test:other") is True


@pytest.mark.asyncio
async def test_keys_pattern(setup_redis):
    """Test getting keys by pattern"""
    # Create keys
    await redis_client.set("test:keys:a", "1")
    await redis_client.set("test:keys:b", "2")
    await redis_client.set("test:other:c", "3")
    
    # Get matching keys
    keys = await redis_client.keys("test:keys:*")
    assert len(keys) == 2