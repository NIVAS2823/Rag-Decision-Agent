from app.core.config import settings

print("=" * 60)
print("CONFIGURATION TEST")
print("=" * 60)
print()

# Application
print("📱 Application:")
print(f"  Name: {settings.APP_NAME}")
print(f"  Version: {settings.APP_VERSION}")
print(f"  Environment: {settings.ENVIRONMENT}")
print(f"  Debug: {settings.DEBUG}")
print()

# API Server
print("🌐 API Server:")
print(f"  Host: {settings.API_HOST}")
print(f"  Port: {settings.API_PORT}")
print(f"  Workers: {settings.API_WORKERS}")
print()

# Security
print("🔒 Security:")
print(f"  Secret Key: {'*' * 20} (length: {len(settings.SECRET_KEY)})")
print(f"  JWT Secret: {'*' * 20} (length: {len(settings.JWT_SECRET_KEY)})")
print(f"  JWT Algorithm: {settings.JWT_ALGORITHM}")
print(f"  Token Expiry: {settings.ACCESS_TOKEN_EXPIRE_MINUTES} minutes")
print()

# LLM Providers
print("🤖 LLM Providers:")
openai_status = "✅ Configured" if settings.OPENAI_API_KEY else "❌ Not configured"
groq_status = "✅ Configured" if settings.GROQ_API_KEY else "❌ Not configured"
print(f"  OpenAI: {openai_status}")
print(f"  Groq: {groq_status}")
print()

# RAG
print("📚 RAG Configuration:")
print(f"  Embedding Model: {settings.EMBEDDING_MODEL}")
print(f"  Embedding Dimension: {settings.EMBEDDING_DIMENSION}")
print(f"  Chunk Size: {settings.CHUNK_SIZE}")
print(f"  Chunk Overlap: {settings.CHUNK_OVERLAP}")
print(f"  Top-K Retrieval: {settings.TOP_K_RETRIEVAL}")
print()

# Databases
print("💾 Databases:")
print(f"  MongoDB URL: {settings.MONGODB_URL}")
print(f"  MongoDB Database: {settings.MONGODB_DB_NAME}")
print(f"  Redis: {'Enabled' if settings.REDIS_ENABLE else 'Disabled'}")
print()

# Feature Flags
print("🚩 Feature Flags:")
print(f"  Caching: {'✅' if settings.ENABLE_CACHING else '❌'}")
print(f"  Web Search: {'✅' if settings.ENABLE_WEB_SEARCH else '❌'}")
print(f"  Verification: {'✅' if settings.ENABLE_VERIFICATION else '❌'}")
print(f"  Confidence Scoring: {'✅' if settings.ENABLE_CONFIDENCE_SCORING else '❌'}")
print()

# Environment Checks
print("🔍 Environment Checks:")
print(f"  Is Development: {settings.is_development}")
print(f"  Is Production: {settings.is_production}")
print()

print("=" * 60)
print("✅ Configuration loaded successfully!")
print("=" * 60)