"""
Debug Endpoints
===============
Development-only endpoints for debugging and inspection.

⚠️  THESE ENDPOINTS ARE DISABLED IN PRODUCTION
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.core.config import settings


router = APIRouter()


@router.get(
    "/config",
    summary="View configuration (dev only)",
    description="Returns current configuration with secrets masked. Only available in development.",
    tags=["debug"],
)
async def get_configuration():
    """
    Get Current Configuration
    
    Returns the current application configuration with all secrets masked.
    This endpoint is only available in development mode.
    
    Returns:
        dict: Safe configuration dictionary
        
    Raises:
        HTTPException: If called in production
    """
    if not settings.is_development:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Configuration endpoint is only available in development mode"
        )
    
    return JSONResponse(content=settings.to_safe_dict())


@router.get(
    "/config/database",
    summary="View database configuration",
    description="Returns database configuration. Only available in development.",
    tags=["debug"],
)
async def get_database_config():
    """Get database configuration"""
    if not settings.is_development:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debug endpoints are only available in development mode"
        )
    
    return settings.get_database_config()


@router.get(
    "/config/llm",
    summary="View LLM configuration",
    description="Returns LLM configuration. Only available in development.",
    tags=["debug"],
)
async def get_llm_config():
    """Get LLM configuration"""
    if not settings.is_development:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debug endpoints are only available in development mode"
        )
    
    return settings.get_llm_config()


@router.get(
    "/config/rag",
    summary="View RAG configuration",
    description="Returns RAG configuration. Only available in development.",
    tags=["debug"],
)
async def get_rag_config():
    """Get RAG configuration"""
    if not settings.is_development:
        raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Debug endpoints are only available in development mode"
    )

    return settings.get_rag_config()


@router.get(
    "/database/stats",
    summary="View database statistics",
    description="Returns database statistics. Only available in development.",
    tags=["debug"],
)
async def get_database_statistics():
    """Get database statistics"""
    if not settings.is_development:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debug endpoints are only available in development mode"
        )
    
    from app.services.database import db_client
    
    return await db_client.get_database_stats()


@router.get(
    "/database/collections",
    summary="List database collections",
    description="Returns list of all collections. Only available in development.",
    tags=["debug"],
)
async def list_database_collections():
    """List all database collections"""
    if not settings.is_development:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debug endpoints are only available in development mode"
        )
    
    from app.services.database import db_client
    
    collections = await db_client.list_collections()
    return {"collections": collections}


@router.get(
    "/database/collections/{collection_name}",
    summary="View collection statistics",
    description="Returns statistics for a specific collection. Only available in development.",
    tags=["debug"],
)
async def get_collection_statistics(collection_name: str):
    """Get collection statistics"""
    if not settings.is_development:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debug endpoints are only available in development mode"
        )
    
    from app.services.database import db_client
    
    try:
        return await db_client.get_collection_stats(collection_name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Collection not found or error: {str(e)}"
        )

@router.get(
    "/database/indexes",
    summary="Verify database indexes",
    description="Returns all indexes for all collections. Only available in development.",
    tags=["debug"],
)
async def verify_database_indexes():
    """Verify all database indexes"""
    if not settings.is_development:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debug endpoints are only available in development mode"
        )
    
    from app.services.database import db_client
    
    indexes = await db_client.verify_indexes()
    
    # Count total indexes
    total = sum(len(idx_list) for idx_list in indexes.values())
    
    return {
        "total_indexes": total,
        "collections": len(indexes),
        "indexes": indexes
    }