"""
Tests for Redis connection manager
"""
import pytest
from app.services.database.redis_manager import RedisManager
from app.core.config import settings


@pytest.mark.asyncio
async def test_redis_connect():
    """Test Redis connection"""
    if not settings.REDIS_ENABLE:
        pytest.skip("Redis is disabled")
    
    manager = RedisManager()
    
    try:
        await manager.connect()
        assert manager.client is not None
    finally:
        await manager.disconnect()


@pytest.mark.asyncio
async def test_redis_health_check():
    """Test Redis health check"""
    if not settings.REDIS_ENABLE:
        pytest.skip("Redis is disabled")
    
    manager = RedisManager()
    
    try:
        await manager.connect()
        is_healthy = await manager.health_check()
        assert is_healthy is True
    finally:
        await manager.disconnect()


@pytest.mark.asyncio
async def test_get_redis_client():
    """Test getting Redis client"""
    if not settings.REDIS_ENABLE:
        pytest.skip("Redis is disabled")
    
    manager = RedisManager()
    
    try:
        await manager.connect()
        client = manager.get_client()
        assert client is not None
        
        # Test basic operation
        await client.set("test_key", "test_value")
        value = await client.get("test_key")
        assert value == "test_value"
        
        # Cleanup
        await client.delete("test_key")
    finally:
        await manager.disconnect()


@pytest.mark.asyncio
async def test_redis_info():
    """Test getting Redis server info"""
    if not settings.REDIS_ENABLE:
        pytest.skip("Redis is disabled")
    
    manager = RedisManager()
    
    try:
        await manager.connect()
        info = await manager.get_info()
        
        assert "version" in info
        assert "connected_clients" in info
    finally:
        await manager.disconnect()


def test_redis_health_endpoint():
    """Test Redis health in health endpoint"""
    from fastapi.testclient import TestClient
    from app.main import app
    
    with TestClient(app) as client:
        response = client.get("/api/v1/health/detailed")
    
    assert response.status_code == 200
    data = response.json()
    
    # Find Redis dependency
    redis_dep = next(
        (d for d in data["dependencies"] if d["name"] == "redis"),
        None
    )
    
    assert redis_dep is not None
    if settings.REDIS_ENABLE:
        assert redis_dep["status"] in ["healthy", "unhealthy"]
    else:
        assert redis_dep["status"] == "disabled"