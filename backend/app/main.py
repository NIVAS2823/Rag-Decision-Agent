"""
RAG Decision Intelligence Agent - Main Application
===================================================
FastAPI application entry point with lifecycle management.

This is the core of our backend application. It:
- Initializes the FastAPI app
- Configures application metadata
- Manages application lifecycle (startup/shutdown)
- Will later integrate all API routes, middleware, and services
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.config import settings


# ============================================================================
# APPLICATION LIFESPAN MANAGEMENT
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application Lifespan Manager
    
    Handles startup and shutdown events for the application.
    This is the modern way to handle lifecycle events in FastAPI.
    
    Startup tasks:
    - Load configuration
    - Initialize database connections (Phase 3)
    - Load AI models and indexes (Phase 5)
    - Initialize agent system (Phase 4)
    
    Shutdown tasks:
    - Close database connections
    - Save state if needed
    - Cleanup resources
    """
    # ========================================================================
    # STARTUP
    # ========================================================================
    print("=" * 70)
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print("=" * 70)
    
    # Log configuration
    print(f"📋 Environment: {settings.ENVIRONMENT}")
    print(f"🐛 Debug Mode: {settings.DEBUG}")
    print(f"🌐 API Host: {settings.API_HOST}:{settings.API_PORT}")
    print(f"👷 Workers: {settings.API_WORKERS}")
    
    # Log feature flags
    print("\n🚩 Feature Flags:")
    print(f"   Caching: {'✅' if settings.ENABLE_CACHING else '❌'}")
    print(f"   Web Search: {'✅' if settings.ENABLE_WEB_SEARCH else '❌'}")
    print(f"   Verification: {'✅' if settings.ENABLE_VERIFICATION else '❌'}")
    print(f"   Confidence Scoring: {'✅' if settings.ENABLE_CONFIDENCE_SCORING else '❌'}")
    
    # Future: Initialize database connections (Phase 3)
    # await init_mongodb()
    # await init_redis()
    
    # Future: Load RAG components (Phase 5)
    # await load_faiss_index()
    # await load_bm25_index()
    
    # Future: Initialize agent system (Phase 4)
    # await init_langgraph_agents()
    
    print("\n✅ Application startup complete")
    print("=" * 70)
    print()
    
    # Application is now running
    yield
    
    # ========================================================================
    # SHUTDOWN
    # ========================================================================
    print()
    print("=" * 70)
    print("🛑 Shutting down application...")
    print("=" * 70)
    
    # Future: Close database connections
    # await close_mongodb()
    # await close_redis()
    
    # Future: Save any pending state
    # await save_application_state()
    
    print("✅ Shutdown complete")
    print("=" * 70)


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

app = FastAPI(
    title=settings.APP_NAME,
    description="""
    ## Enterprise-Grade RAG + Decision Intelligence Agent
    
    A production-ready AI system that combines:
    - **Internal knowledge** (document ingestion & retrieval)
    - **External intelligence** (real-time web search)
    - **Multi-agent reasoning** (LangGraph orchestration)
    
    ### Key Features
    - 🔍 **Hybrid RAG**: Vector search (FAISS) + Keyword search (BM25) + Re-ranking
    - 🤖 **Multi-Agent System**: Specialized agents for planning, retrieval, decision-making
    - ✅ **Fact Verification**: External tool-based validation (Tavily)
    - 📊 **Confidence Scoring**: Quantified uncertainty for every decision
    - 🔐 **Enterprise Security**: JWT authentication, role-based access control
    - 📝 **Full Auditability**: Complete trace of every decision via LangSmith
    
    ### Architecture
    - **Backend**: Python + FastAPI + LangGraph
    - **AI**: LangChain + OpenAI/Anthropic
    - **RAG**: FAISS + BM25 + Cross-encoders
    - **Database**: MongoDB + Redis + FAISS
    - **Storage**: Cloudflare R2
    
    ### Use Cases
    - Strategic business decisions
    - Compliance & legal review
    - Investment analysis
    - Product development prioritization
    
    ---
    
    **API Documentation**: Available at `/docs` (Swagger UI) and `/redoc` (ReDoc)
    """,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    # Additional metadata
    contact={
        "name": "RAG Decision Agent Team",
        "email": "support@example.com",  # Update with actual contact
    },
    license_info={
        "name": "MIT",  # Update with actual license
    },
    # OpenAPI tags for grouping endpoints
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check and system status endpoints",
        },
        {
            "name": "auth",
            "description": "Authentication and authorization endpoints",
        },
        {
            "name": "decisions",
            "description": "Decision generation and retrieval endpoints",
        },
        {
            "name": "documents",
            "description": "Document upload and management endpoints",
        },
        {
            "name": "users",
            "description": "User management endpoints",
        },
    ],
)


# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get(
    "/",
    summary="Root endpoint",
    description="Returns basic API information",
    response_class=JSONResponse,
    tags=["health"],
)
async def root():
    """
    Root Endpoint
    
    Returns basic information about the API.
    Useful for quickly checking if the server is responding.
    """
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
# FUTURE ROUTE INCLUDES (Placeholder for upcoming steps)
# ============================================================================

# Phase 2 (Step 2.3): Health check endpoints
# from app.api.routes import health
# app.include_router(health.router, prefix="/api/v1", tags=["health"])

# Phase 5: Authentication endpoints
# from app.api.routes import auth
# app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])

# Phase 6: Decision endpoints
# from app.api.routes import decisions
# app.include_router(decisions.router, prefix="/api/v1/decisions", tags=["decisions"])

# Phase 6: Document endpoints
# from app.api.routes import documents
# app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])

# Phase 6: User endpoints
# from app.api.routes import users
# app.include_router(users.router, prefix="/api/v1/users", tags=["users"])


# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    """
    Development Server Entry Point
    
    This allows running the server directly with: python main.py
    For production, use: uvicorn main:app --host 0.0.0.0 --port 8000
    """
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,  # Auto-reload on code changes in development
        log_level="debug" if settings.DEBUG else "info",
        access_log=True,
    )