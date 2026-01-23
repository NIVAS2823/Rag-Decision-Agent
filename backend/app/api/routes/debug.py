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


