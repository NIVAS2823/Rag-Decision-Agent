"""
RAG Decision Intelligence Agent - Main Application
===================================================
FastAPI application entry point with lifecycle management.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from datetime import datetime, timezone
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.routes import health, debug,admin_cache
from app.core.logging_config import setup_logging,get_logger
from app.api.dependencies.logging import RequestLoggingMiddleware
# from app.services.database.mongodb import mongodb_manager
from app.services.database import initialize_database,close_database
from app.services.database.redis_manager import redis_manager

# Initialize logger
logger = get_logger(__name__)

# ============================================================================
# APPLICATION LIFESPAN MANAGEMENT
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application Lifespan Manager
    Handles startup and shutdown events for the application.
    """

    # ========================================================================
    # STARTUP
    # ========================================================================

    setup_logging()

    logger.info("=" * 70)
    logger.info("🚀 Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("=" * 70)

    logger.info("📋 Environment: %s", settings.ENVIRONMENT)
    logger.info("🐛 Debug Mode: %s", settings.DEBUG)
    logger.info("🌐 API Host: %s:%s", settings.API_HOST, settings.API_PORT)
    logger.info("👷 Workers: %s", settings.API_WORKERS)

    logger.info("🔐 CORS Allowed Origins: %s", settings.CORS_ORIGINS)

    logger.info("🚩 Feature Flags:")
    logger.info("   Caching: %s", "ENABLED" if settings.ENABLE_CACHING else "DISABLED")
    logger.info("   Web Search: %s", "ENABLED" if settings.ENABLE_WEB_SEARCH else "DISABLED")
    logger.info("   Verification: %s", "ENABLED" if settings.ENABLE_VERIFICATION else "DISABLED")
    logger.info("   Confidence Scoring: %s", "ENABLED" if settings.ENABLE_CONFIDENCE_SCORING else "DISABLED")

    # Initialize MongoDB
    try:
        await initialize_database()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        if settings.is_production:
            raise
    if settings.REDIS_ENABLE:
        try:
            await redis_manager.connect()
            logger.info("✅ Redis connected successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis: {e}")
            if settings.is_production:
                raise
    else:
        logger.info("ℹ️ Redis is disabled")

    logger.info("✅ Application startup complete")
    logger.info("=" * 70)

    yield

    # ========================================================================
    # SHUTDOWN
    # ========================================================================

    logger.info("=" * 70)
    logger.info("🛑 Shutting down application...")
    logger.info("=" * 70)

    try:
        await close_database()
        logger.info("✅ Database connection closed")
    except Exception:
        logger.exception("⚠️ Error while closing database connection")

    if settings.REDIS_ENABLE:
        try:
            await redis_manager.disconnect()
            logger.info("✅ Redis connection closed")
        except Exception:
            logger.exception("⚠️ Error while closing Redis connection")

    logger.info("✅ Shutdown complete")
    logger.info("=" * 70)


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    description="## Enterprise-Grade RAG + Decision Intelligence Agent",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "RAG Decision Agent Team",
        "email": "support@example.com",
    },
    license_info={"name": "MIT"},
    openapi_tags=[
        {"name": "health", "description": "Health check and system status endpoints"},
        {"name": "auth", "description": "Authentication and authorization endpoints"},
        {"name": "decisions", "description": "Decision generation and retrieval endpoints"},
        {"name": "documents", "description": "Document upload and management endpoints"},
        {"name": "users", "description": "User management endpoints"},
    ],
)

# ============================================================================
# CORS CONFIGURATION
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "X-Request-ID",
        "X-Process-Time",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    ],
    max_age=600,
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(health.router, prefix="/api/v1", tags=["health"])

if settings.is_development:
    app.include_router(debug.router, prefix="/api/v1/debug", tags=["debug"])
    app.include_router(admin_cache.router, prefix="/api/v1/admin/cache", tags=["admin-cache"])


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/", summary="Root endpoint", tags=["health"])
async def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc",
        "message": "Welcome to the RAG Decision Intelligence Agent API",
    }


# ============================================================================
# CORS TEST ENDPOINT
# ============================================================================

@app.get("/cors-test", summary="CORS test endpoint", tags=["health"])
async def cors_test():
    return {
        "message": "CORS is configured correctly",
        "allowed_origins": settings.CORS_ORIGINS,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
        access_log=True,
    )
