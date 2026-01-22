"""
Server Configuration
====================
Uvicorn server configuration for development and production.
"""

from typing import Dict, Any

from app.core.config import settings


def get_uvicorn_config() -> Dict[str, Any]:
    """
    Get Uvicorn server configuration based on environment
    
    Returns:
        Dict[str, Any]: Uvicorn configuration parameters
    """
    # Base configuration
    config = {
        "app": "main:app",
        "host": settings.API_HOST,
        "port": settings.API_PORT,
        "log_config": None,  # We use our custom logging
    }
    
    # Development-specific configuration
    if settings.is_development:
        config.update({
            "reload": True,  # Auto-reload on code changes
            "reload_dirs": ["app"],  # Watch these directories
            "log_level": "debug",
            "access_log": True,
            "use_colors": True,
        })
    
    # Production-specific configuration
    else:
        config.update({
            "reload": False,
            "workers": settings.API_WORKERS,  # Multiple worker processes
            "log_level": "info",
            "access_log": True,
            "use_colors": False,
            "proxy_headers": True,  # Trust X-Forwarded-* headers
            "forwarded_allow_ips": "*",  # Allow all IPs (behind load balancer)
            
            # Performance tuning
            "limit_concurrency": 1000,  # Max concurrent connections
            "backlog": 2048,  # Connection backlog queue
            "timeout_keep_alive": 5,  # Keep-alive timeout
            
            # SSL/TLS (if certificates are provided)
            # "ssl_keyfile": "/path/to/key.pem",
            # "ssl_certfile": "/path/to/cert.pem",
        })
    
    return config


def get_gunicorn_config() -> Dict[str, Any]:
    """
    Get Gunicorn configuration for production deployment
    
    Gunicorn is often used as a process manager for Uvicorn workers.
    
    Returns:
        Dict[str, Any]: Gunicorn configuration
    """
    return {
        "bind": f"{settings.API_HOST}:{settings.API_PORT}",
        "workers": settings.API_WORKERS,
        "worker_class": "uvicorn.workers.UvicornWorker",
        "keepalive": 5,
        "timeout": 120,  # Worker timeout
        "graceful_timeout": 30,  # Graceful shutdown timeout
        "max_requests": 1000,  # Restart worker after N requests (memory leak protection)
        "max_requests_jitter": 50,  # Add randomness to max_requests
        "preload_app": True,  # Load app before forking workers
        "accesslog": "-",  # Log to stdout
        "errorlog": "-",  # Log errors to stdout
        "loglevel": "info",
    }