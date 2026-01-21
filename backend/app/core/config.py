from functools import lru_cache
from typing import List, Optional
import json

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application Settings
    
    All settings are loaded from environment variables or .env file.
    Pydantic validates types and required fields automatically.
    """
    
    # ========================================================================
    # APPLICATION
    # ========================================================================
    APP_NAME: str = "RAG Decision Agent"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    
    # ========================================================================
    # API SERVER
    # ========================================================================
    API_HOST: str = Field(default="0.0.0.0")
    API_PORT: int = Field(default=8000)
    API_WORKERS: int = Field(default=4)
    
    # ========================================================================
    # SECURITY
    # ========================================================================
    SECRET_KEY: str = Field(..., min_length=32)  # Required, min 32 chars
    JWT_SECRET_KEY: str = Field(..., min_length=32)  # Required
    JWT_ALGORITHM: str = Field(default="HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30)
    
    # ========================================================================
    # LLM PROVIDERS
    # ========================================================================
    OPENAI_API_KEY: Optional[str] = Field(default=None)
    GROQ_API_KEY: Optional[str] = Field(default=None)
    
    # ========================================================================
    # RAG & SEARCH
    # ========================================================================
    TAVILY_API_KEY: Optional[str] = Field(default=None)
    EMBEDDING_MODEL: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2"
    )
    EMBEDDING_DIMENSION: int = Field(default=384)
    
    # ========================================================================
    # DATABASES
    # ========================================================================
    MONGODB_URL: str = Field(default="mongodb://localhost:27017")
    MONGODB_DB_NAME: str = Field(default="rag_decision_agent")
    
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_PASSWORD: Optional[str] = Field(default=None)
    REDIS_ENABLE: bool = Field(default=False)
    
    # ========================================================================
    # CLOUD STORAGE
    # ========================================================================
    R2_ACCOUNT_ID: Optional[str] = Field(default=None)
    R2_ACCESS_KEY_ID: Optional[str] = Field(default=None)
    R2_SECRET_ACCESS_KEY: Optional[str] = Field(default=None)
    R2_BUCKET_NAME: str = Field(default="rag-documents")
    R2_ENDPOINT_URL: Optional[str] = Field(default=None)
    
    # ========================================================================
    # OBSERVABILITY
    # ========================================================================
    LANGCHAIN_TRACING_V2: bool = Field(default=False)
    LANGCHAIN_ENDPOINT: str = Field(
        default="https://api.smith.langchain.com"
    )
    LANGCHAIN_API_KEY: Optional[str] = Field(default=None)
    LANGCHAIN_PROJECT: str = Field(default="rag-decision-agent")
    
    # ========================================================================
    # CORS
    # ========================================================================
    CORS_ORIGINS: str = Field(
        default='["http://localhost:5173","http://localhost:3000"]'
    )
    
    @field_validator("CORS_ORIGINS")
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from JSON string to list"""
        if isinstance(v, str):
            return json.loads(v)
        return v
    
    # ========================================================================
    # FEATURE FLAGS
    # ========================================================================
    ENABLE_CACHING: bool = Field(default=False)
    ENABLE_WEB_SEARCH: bool = Field(default=False)
    ENABLE_VERIFICATION: bool = Field(default=False)
    ENABLE_CONFIDENCE_SCORING: bool = Field(default=True)
    
    # ========================================================================
    # PERFORMANCE
    # ========================================================================
    MAX_TOKENS: int = Field(default=4096)
    TEMPERATURE: float = Field(default=0.7)
    TOP_K_RETRIEVAL: int = Field(default=10)
    CHUNK_SIZE: int = Field(default=1000)
    CHUNK_OVERLAP: int = Field(default=200)
    
    # ========================================================================
    # PYDANTIC CONFIGURATION
    # ========================================================================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"  # Ignore extra fields in .env
    )
    
    # ========================================================================
    # COMPUTED PROPERTIES
    # ========================================================================
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.ENVIRONMENT.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def mongodb_database_url(self) -> str:
        """Get full MongoDB URL with database name"""
        return f"{self.MONGODB_URL}/{self.MONGODB_DB_NAME}"


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    
    Uses lru_cache to ensure settings are loaded only once.
    This is the recommended way to access settings throughout the app.
    
    Returns:
        Settings: Validated settings instance
    """
    return Settings()


# Convenience: Create a global settings instance
settings = get_settings()