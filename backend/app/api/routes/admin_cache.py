"""
Admin Cache Management
======================
Administrative endpoints for cache management (development/admin only).
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.services.cache import redis_client
from app.services.cache.invalidation import cache_invalidation
from app.services.cache.utils import cache_utils


router = APIRouter()


class InvalidateResponse(BaseModel):
    """Response for invalidation operations"""
    success: bool
    keys_deleted: int
    message: str


# ============================================================================
# CACHE STATISTICS
# ============================================================================

@router.get(
    "/stats",
    summary="Get cache statistics",
    description="Returns comprehensive cache statistics. Development only.",
    tags=["admin-cache"],
)
async def get_cache_stats():
    """Get cache statistics"""
    if not settings.is_development:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin cache endpoints only available in development"
        )
    
    stats = await cache_invalidation.get_invalidation_stats()
    general_stats = await cache_utils.get_cache_stats()
    
    return {
        "invalidation_stats": stats,
        "general_stats": general_stats
    }


# ============================================================================
# USER CACHE INVALIDATION
# ============================================================================

@router.delete(
    "/users/{user_id}",
    response_model=InvalidateResponse,
    summary="Invalidate user cache",
    description="Invalidate all cache for a specific user. Development only.",
    tags=["admin-cache"],
)
async def invalidate_user_cache(user_id: str):
    """Invalidate cache for a user"""
    if not settings.is_development:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin cache endpoints only available in development"
        )
    
    counts = await cache_invalidation.invalidate_user(user_id)
    total = sum(counts.values())
    
    return InvalidateResponse(
        success=True,
        keys_deleted=total,
        message=f"Invalidated {total} cache keys for user {user_id}"
    )


# ============================================================================
# DECISION CACHE INVALIDATION
# ============================================================================

@router.delete(
    "/decisions/{decision_id}",
    response_model=InvalidateResponse,
    summary="Invalidate decision cache",
    description="Invalidate cache for a specific decision. Development only.",
    tags=["admin-cache"],
)
async def invalidate_decision_cache(decision_id: str):
    """Invalidate cache for a decision"""
    if not settings.is_development:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin cache endpoints only available in development"
        )
    
    deleted = await cache_invalidation.invalidate_decision(decision_id)
    
    return InvalidateResponse(
        success=True,
        keys_deleted=deleted,
        message=f"Invalidated decision cache: {decision_id}"
    )


# ============================================================================
# BULK INVALIDATION
# ============================================================================

@router.delete(
    "/pattern/{pattern}",
    response_model=InvalidateResponse,
    summary="Invalidate by pattern",
    description="Invalidate all keys matching a pattern. Development only. USE WITH CAUTION!",
    tags=["admin-cache"],
)
async def invalidate_by_pattern(pattern: str):
    """Invalidate cache by pattern"""
    if not settings.is_development:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin cache endpoints only available in development"
        )
    
    deleted = await cache_invalidation.invalidate_by_pattern(pattern)
    
    return InvalidateResponse(
        success=True,
        keys_deleted=deleted,
        message=f"Invalidated {deleted} keys matching pattern: {pattern}"
    )


@router.delete(
    "/flush",
    response_model=InvalidateResponse,
    summary="Flush all cache",
    description="Delete ALL cache keys. Development only. DANGER!",
    tags=["admin-cache"],
)
async def flush_all_cache():
    """Flush all cache (DANGER!)"""
    if not settings.is_development:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin cache endpoints only available in development"
        )
    
    success = await redis_client.flush_all()
    
    if success:
        return InvalidateResponse(
            success=True,
            keys_deleted=-1,  # Unknown count
            message="All cache flushed successfully"
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to flush cache"
        )