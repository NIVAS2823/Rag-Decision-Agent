"""
Configuration Management
========================
Loads and validates environment variables using Pydantic Settings.
Provides type-safe access to configuration throughout the application.

Enhanced features:
- Connection string builders
- API key validation
- Secret masking
- Configuration health checks
- Safe export for debugging
"""

from functools import lru_cache
from typing import List, Optional, Dict, Any
import json
import re

from pydantic import Field, field_validator, computed_field
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
    
    # Model configurations
    DEFAULT_LLM_MODEL: str = Field(default="gpt-4")
    DEFAULT_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")
    
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
    MONGODB_MAX_POOL_SIZE: int = Field(default=10)
    MONGODB_MIN_POOL_SIZE: int = Field(default=1)
    
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_PASSWORD: Optional[str] = Field(default=None)
    REDIS_ENABLE: bool = Field(default=False)
    REDIS_MAX_CONNECTIONS: int = Field(default=50)
    REDIS_DECODE_RESPONSES: bool = Field(default=True)
    
    # ========================================================================
    # CLOUD STORAGE
    # ========================================================================
    R2_ACCOUNT_ID: Optional[str] = Field(default=None)
    R2_ACCESS_KEY_ID: Optional[str] = Field(default=None)
    R2_SECRET_ACCESS_KEY: Optional[str] = Field(default=None)
    R2_BUCKET_NAME: str = Field(default="rag-documents")
    R2_ENDPOINT_URL: Optional[str] = Field(default=None)
    R2_PUBLIC_URL: Optional[str] = Field(default=None)
    
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
    TEMPERATURE: float = Field(default=0.7, ge=0.0, le=2.0)
    TOP_K_RETRIEVAL: int = Field(default=10, ge=1, le=100)
    CHUNK_SIZE: int = Field(default=1000, ge=100, le=10000)
    CHUNK_OVERLAP: int = Field(default=200, ge=0, le=1000)
    
    # Request limits
    MAX_UPLOAD_SIZE_MB: int = Field(default=10)
    RATE_LIMIT_PER_MINUTE: int = Field(default=60)
    
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
    def is_staging(self) -> bool:
        """Check if running in staging mode"""
        return self.ENVIRONMENT.lower() == "staging"
    
    @property
    def mongodb_database_url(self) -> str:
        """Get full MongoDB URL with database name"""
        return f"{self.MONGODB_URL}/{self.MONGODB_DB_NAME}"
    
    @computed_field
    @property
    def redis_connection_url(self) -> str:
        """
        Get Redis connection URL with password if configured
        
        Returns:
            str: Complete Redis connection URL
        """
        if self.REDIS_PASSWORD:
            # Extract host and port from URL
            # Format: redis://localhost:6379/0
            parts = self.REDIS_URL.replace("redis://", "").split("/")
            host_port = parts[0]
            db = parts[1] if len(parts) > 1 else "0"
            return f"redis://:{self.REDIS_PASSWORD}@{host_port}/{db}"
        return self.REDIS_URL
    
    @computed_field
    @property
    def r2_configured(self) -> bool:
        """Check if Cloudflare R2 is fully configured"""
        return all([
            self.R2_ACCOUNT_ID,
            self.R2_ACCESS_KEY_ID,
            self.R2_SECRET_ACCESS_KEY,
            self.R2_ENDPOINT_URL,
        ])
    
    @computed_field
    @property
    def openai_configured(self) -> bool:
        """Check if OpenAI is configured"""
        return bool(self.OPENAI_API_KEY)
    
    @computed_field
    @property
    def anthropic_configured(self) -> bool:
        """Check if Anthropic is configured"""
        return bool(self.GROQ_API_KEY)
    
    @computed_field
    @property
    def tavily_configured(self) -> bool:
        """Check if Tavily is configured"""
        return bool(self.TAVILY_API_KEY)
    
    @computed_field
    @property
    def langsmith_configured(self) -> bool:
        """Check if LangSmith is configured"""
        return self.LANGCHAIN_TRACING_V2 and bool(self.LANGCHAIN_API_KEY)
    
    # ========================================================================
    # VALIDATION METHODS
    # ========================================================================
    
    def validate_required_for_production(self) -> List[str]:
        """
        Validate that all required settings for production are configured
        
        Returns:
            List[str]: List of missing required settings
        """
        if not self.is_production:
            return []
        
        missing = []
        
        # Security
        if len(self.SECRET_KEY) < 32:
            missing.append("SECRET_KEY must be at least 32 characters")
        if len(self.JWT_SECRET_KEY) < 32:
            missing.append("JWT_SECRET_KEY must be at least 32 characters")
        
        # LLM Provider (at least one required)
        if not self.openai_configured and not self.anthropic_configured:
            missing.append("At least one LLM provider (OpenAI or Anthropic) must be configured")
        
        # Database
        if "localhost" in self.MONGODB_URL:
            missing.append("Production should not use localhost MongoDB")
        
        # Cloud storage
        if not self.r2_configured:
            missing.append("Cloudflare R2 must be fully configured for production")
        
        return missing
    
    def get_api_key_status(self) -> Dict[str, bool]:
        """
        Get status of all API keys
        
        Returns:
            Dict[str, bool]: API key configuration status
        """
        return {
            "openai": self.openai_configured,
            "anthropic": self.anthropic_configured,
            "tavily": self.tavily_configured,
            "langsmith": self.langsmith_configured,
        }
    
    def mask_secret(self, secret: Optional[str], show_chars: int = 4) -> str:
        """
        Mask a secret for safe logging
        
        Args:
            secret: The secret to mask
            show_chars: Number of characters to show at the start
            
        Returns:
            str: Masked secret
        """
        if not secret:
            return "NOT_SET"
        
        if len(secret) <= show_chars:
            return "*" * len(secret)
        
        return secret[:show_chars] + "*" * (len(secret) - show_chars)
    
    def to_safe_dict(self) -> Dict[str, Any]:
        """
        Export configuration as dictionary with secrets masked
        
        Returns:
            Dict[str, Any]: Safe configuration dictionary
        """
        config = self.model_dump()
        
        # Mask sensitive fields
        sensitive_fields = [
            "SECRET_KEY",
            "JWT_SECRET_KEY",
            "OPENAI_API_KEY",
            "GROQ_API_KEY",
            "TAVILY_API_KEY",
            "LANGCHAIN_API_KEY",
            "REDIS_PASSWORD",
            "R2_ACCESS_KEY_ID",
            "R2_SECRET_ACCESS_KEY",
        ]
        
        for field in sensitive_fields:
            if field in config:
                config[field] = self.mask_secret(config[field])
        
        return config
    
    def get_database_config(self) -> Dict[str, Any]:
        """
        Get database configuration
        
        Returns:
            Dict[str, Any]: Database configuration
        """
        return {
            "mongodb": {
                "url": self.MONGODB_URL.split("@")[-1] if "@" in self.MONGODB_URL else self.MONGODB_URL,
                "database": self.MONGODB_DB_NAME,
                "max_pool_size": self.MONGODB_MAX_POOL_SIZE,
                "min_pool_size": self.MONGODB_MIN_POOL_SIZE,
            },
            "redis": {
                "enabled": self.REDIS_ENABLE,
                "url": self.REDIS_URL.split("@")[-1] if "@" in self.REDIS_URL else self.REDIS_URL,
                "max_connections": self.REDIS_MAX_CONNECTIONS,
            }
        }
    
    def get_llm_config(self) -> Dict[str, Any]:
        """
        Get LLM configuration
        
        Returns:
            Dict[str, Any]: LLM configuration
        """
        return {
            "default_model": self.DEFAULT_LLM_MODEL,
            "embedding_model": self.DEFAULT_EMBEDDING_MODEL,
            "max_tokens": self.MAX_TOKENS,
            "temperature": self.TEMPERATURE,
            "providers": self.get_api_key_status(),
        }
    
    def get_rag_config(self) -> Dict[str, Any]:
        """
        Get RAG configuration
        
        Returns:
            Dict[str, Any]: RAG configuration
        """
        return {
            "embedding_model": self.EMBEDDING_MODEL,
            "embedding_dimension": self.EMBEDDING_DIMENSION,
            "chunk_size": self.CHUNK_SIZE,
            "chunk_overlap": self.CHUNK_OVERLAP,
            "top_k_retrieval": self.TOP_K_RETRIEVAL,
            "web_search_enabled": self.ENABLE_WEB_SEARCH,
            "verification_enabled": self.ENABLE_VERIFICATION,
        }


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


# ============================================================================
# CONFIGURATION VALIDATION ON IMPORT
# ============================================================================

def validate_configuration():
    """
    Validate configuration on module import
    
    Raises:
        ValueError: If production configuration is invalid
    """
    if settings.is_production:
        missing = settings.validate_required_for_production()
        if missing:
            error_msg = "Production configuration validation failed:\n" + "\n".join(f"  - {m}" for m in missing)
            raise ValueError(error_msg)


# Run validation on import (will only raise in production)
try:
    validate_configuration()
except ValueError as e:
    # In production, this should crash the application
    # In development, we just warn
    if settings.is_production:
        raise
    else:
        print(f"⚠️  Configuration warning: {e}")
