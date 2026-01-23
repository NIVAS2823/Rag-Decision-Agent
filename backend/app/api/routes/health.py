"""
Health Check Endpoints
======================
Provides health status for monitoring and observability.

Endpoints:
- GET /health - Simple health check (for load balancers)
- GET /health/detailed - Comprehensive system status
"""

import time
from datetime import datetime
from typing import Dict, Any

import psutil
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.core.config import settings


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class HealthStatus(BaseModel):
    """Simple health status response"""
    status: str = Field(..., description="Overall system status")
    timestamp: str = Field(..., description="Current server timestamp")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Current environment")


class DependencyHealth(BaseModel):
    """Health status of a single dependency"""
    name: str = Field(..., description="Dependency name")
    status: str = Field(..., description="Status: healthy, degraded, unhealthy")
    response_time_ms: float = Field(None, description="Response time in milliseconds")
    message: str = Field(None, description="Additional information")
    details: Dict[str, Any] = Field(default_factory=dict, description="Extra details")


class SystemResources(BaseModel):
    """System resource utilization"""
    cpu_percent: float = Field(..., description="CPU usage percentage")
    memory_percent: float = Field(..., description="Memory usage percentage")
    memory_available_mb: float = Field(..., description="Available memory in MB")
    disk_percent: float = Field(..., description="Disk usage percentage")
    disk_available_gb: float = Field(..., description="Available disk space in GB")


class DetailedHealthStatus(BaseModel):
    """Detailed health status response"""
    status: str = Field(..., description="Overall system status")
    timestamp: str = Field(..., description="Current server timestamp")
    version: str = Field(..., description="API version")
    environment: str = Field(..., description="Current environment")
    uptime_seconds: float = Field(..., description="Server uptime in seconds")
    dependencies: list[DependencyHealth] = Field(default_factory=list, description="Dependency health checks")
    system_resources: SystemResources = Field(..., description="System resource usage")
    features: Dict[str, bool] = Field(default_factory=dict, description="Enabled features")


# ============================================================================
# GLOBAL STATE
# ============================================================================

# Track server start time for uptime calculation
SERVER_START_TIME = time.time()


# ============================================================================
# ROUTER SETUP
# ============================================================================

router = APIRouter()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def check_mongodb_health() -> DependencyHealth:
    """
    Check MongoDB connection health
    
    Returns:
        DependencyHealth: MongoDB health status
    """
    from app.services.database.mongodb import mongodb_manager
    
    if not mongodb_manager.client:
        return DependencyHealth(
            name="mongodb",
            status="not_connected",
            message="MongoDB client not initialized",
            details={"configured": bool(settings.MONGODB_URL)}
        )
    
    # Measure response time
    import time
    start_time = time.time()
    
    try:
        is_healthy = await mongodb_manager.health_check()
        response_time_ms = (time.time() - start_time) * 1000
        
        if is_healthy:
            return DependencyHealth(
                name="mongodb",
                status="healthy",
                response_time_ms=round(response_time_ms, 2),
                message="MongoDB connection is healthy",
                details={
                    "database": settings.MONGODB_DB_NAME,
                    "max_pool_size": settings.MONGODB_MAX_POOL_SIZE,
                }
            )
        else:
            return DependencyHealth(
                name="mongodb",
                status="unhealthy",
                response_time_ms=round(response_time_ms, 2),
                message="MongoDB ping failed",
                details={}
            )
    except Exception as e:
        response_time_ms = (time.time() - start_time) * 1000
        return DependencyHealth(
            name="mongodb",
            status="unhealthy",
            response_time_ms=round(response_time_ms, 2),
            message=f"MongoDB health check error: {str(e)}",
            details={}
        )


async def check_redis_health() -> DependencyHealth:
    """
    Check Redis connection health
    
    Returns:
        DependencyHealth: Redis health status
    """
    # Placeholder for Phase 3 when we implement Redis
    # For now, check if it's enabled
    
    if not settings.REDIS_ENABLE:
        return DependencyHealth(
            name="redis",
            status="disabled",
            message="Redis caching is disabled",
            details={"enabled": False}
        )
    
    return DependencyHealth(
        name="redis",
        status="pending",
        message="Redis connection not yet implemented (Phase 3)",
        details={
            "configured": bool(settings.REDIS_URL),
            "enabled": settings.REDIS_ENABLE,
        }
    )


async def check_llm_provider_health() -> list[DependencyHealth]:
    """
    Check LLM provider configurations
    
    Returns:
        list[DependencyHealth]: LLM provider health statuses
    """
    providers = []
    
    # Check OpenAI
    if settings.OPENAI_API_KEY:
        providers.append(DependencyHealth(
            name="openai",
            status="configured",
            message="OpenAI API key configured",
            details={
                "key_length": len(settings.OPENAI_API_KEY),
                "key_prefix": settings.OPENAI_API_KEY[:10] + "..." if len(settings.OPENAI_API_KEY) > 10 else "***",
            }
        ))
    else:
        providers.append(DependencyHealth(
            name="openai",
            status="not_configured",
            message="OpenAI API key not set",
            details={}
        ))
    
    # Check Anthropic
    if settings.GROQ_API_KEY:
        providers.append(DependencyHealth(
            name="groq",
            status="configured",
            message="GROQ API key configured",
            details={
                "key_length": len(settings.GROQ_API_KEY),
            }
        ))
    else:
        providers.append(DependencyHealth(
            name="Groq",
            status="not_configured",
            message="Groq API key not set (optional)",
            details={}
        ))
    
    return providers


def get_system_resources() -> SystemResources:
    """
    Get current system resource utilization
    
    Returns:
        SystemResources: Current system resource metrics
    """
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=0.1)
    
    # Memory usage
    memory = psutil.virtual_memory()
    memory_percent = memory.percent
    memory_available_mb = memory.available / (1024 * 1024)
    
    # Disk usage
    disk = psutil.disk_usage('/')
    disk_percent = disk.percent
    disk_available_gb = disk.free / (1024 * 1024 * 1024)
    
    return SystemResources(
        cpu_percent=round(cpu_percent, 2),
        memory_percent=round(memory_percent, 2),
        memory_available_mb=round(memory_available_mb, 2),
        disk_percent=round(disk_percent, 2),
        disk_available_gb=round(disk_available_gb, 2),
    )


def determine_overall_status(dependencies: list[DependencyHealth]) -> str:
    """
    Determine overall system status based on dependencies
    
    Args:
        dependencies: List of dependency health checks
        
    Returns:
        str: Overall status (healthy, degraded, unhealthy)
    """
    if not dependencies:
        return "healthy"
    
    statuses = [dep.status for dep in dependencies]
    
    # If any dependency is unhealthy, system is unhealthy
    if "unhealthy" in statuses:
        return "unhealthy"
    
    # If any dependency is degraded, system is degraded
    if "degraded" in statuses:
        return "degraded"
    
    # If all are healthy, configured, or disabled, system is healthy
    if all(s in ["healthy", "configured", "disabled", "pending"] for s in statuses):
        return "healthy"
    
    # If any not_configured (but none unhealthy/degraded)
    if "not_configured" in statuses:
        return "degraded"
    
    return "healthy"


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get(
    "/health",
    response_model=HealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Simple health check",
    description="Returns basic health status. Used by load balancers and monitoring tools.",
    tags=["health"],
)
async def health_check():
    """
    Simple Health Check
    
    Returns a basic health status response.
    This endpoint is designed to be fast and lightweight for frequent polling.
    
    Returns:
        HealthStatus: Basic health information
    """
    return HealthStatus(
        status="healthy",
        timestamp=datetime.utcnow().isoformat() + "Z",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )


@router.get(
    "/health/detailed",
    response_model=DetailedHealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Detailed health check",
    description="Returns comprehensive system status including dependencies and resources.",
    tags=["health"],
)
async def detailed_health_check():
    """
    Detailed Health Check
    
    Returns comprehensive health status including:
    - Dependency health (databases, caches, external APIs)
    - System resource utilization (CPU, memory, disk)
    - Enabled features
    - Uptime
    
    This endpoint is more expensive than /health and should be polled less frequently.
    
    Returns:
        DetailedHealthStatus: Comprehensive health information
    """
    # Calculate uptime
    uptime_seconds = time.time() - SERVER_START_TIME
    
    # Check all dependencies
    dependencies = []
    
    # Database health
    mongo_health = await check_mongodb_health()
    dependencies.append(mongo_health)
    
    # Cache health
    redis_health = await check_redis_health()
    dependencies.append(redis_health)
    
    # LLM provider health
    llm_providers = await check_llm_provider_health()
    dependencies.extend(llm_providers)
    
    # Get system resources
    system_resources = get_system_resources()
    
    # Feature flags
    features = {
        "caching": settings.ENABLE_CACHING,
        "web_search": settings.ENABLE_WEB_SEARCH,
        "verification": settings.ENABLE_VERIFICATION,
        "confidence_scoring": settings.ENABLE_CONFIDENCE_SCORING,
    }
    
    # Determine overall status
    overall_status = determine_overall_status(dependencies)
    
    return DetailedHealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat() + "Z",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        uptime_seconds=round(uptime_seconds, 2),
        dependencies=dependencies,
        system_resources=system_resources,
        features=features,
    )


@router.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description="Kubernetes liveness probe endpoint. Returns 200 if the server is running.",
    tags=["health"],
)
async def liveness_probe():
    """
    Liveness Probe
    
    Used by Kubernetes to determine if the container should be restarted.
    Returns 200 if the application is running, regardless of dependency health.
    
    Returns:
        dict: Simple alive status
    """
    return {"status": "alive"}


@router.get(
    "/health/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    description="Kubernetes readiness probe endpoint. Returns 200 if ready to serve traffic.",
    tags=["health"],
)
async def readiness_probe():
    """
    Readiness Probe
    
    Used by Kubernetes to determine if the container is ready to receive traffic.
    Returns 200 if all critical dependencies are healthy.
    
    Future: Will check database connections before returning healthy status.
    
    Returns:
        dict: Readiness status
    """
    # Future: Check critical dependencies
    # - MongoDB connection
    # - Redis connection (if enabled)
    # - FAISS index loaded
    
    # For now, return ready since no dependencies are critical yet
    return {"status": "ready"}