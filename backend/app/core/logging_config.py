"""
Logging Configuration
=====================
Centralized logging setup using loguru for structured logging.

Features:
- Structured JSON logging for production
- Human-readable logs for development
- Request ID tracking
- Log rotation and retention
- Different log levels per environment
"""

import sys
import logging
from pathlib import Path
from typing import Optional

from loguru import logger

from app.core.config import settings


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

class InterceptHandler(logging.Handler):
    """
    Intercept standard logging messages and redirect to loguru.
    
    This allows us to capture logs from third-party libraries
    (uvicorn, fastapi, etc.) and format them consistently.
    """
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record through loguru
        
        Args:
            record: Standard library log record
        """
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        
        # Find caller from where the logged message originated
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        
        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging() -> None:
    """
    Configure application-wide logging
    
    Sets up:
    - Console logging (stdout)
    - File logging with rotation
    - JSON formatting for production
    - Intercepts standard library logging
    """
    # Remove default loguru handler
    logger.remove()
    
    # ========================================================================
    # CONSOLE LOGGING (stdout)
    # ========================================================================
    
    if settings.is_development:
        # Development: Human-readable format
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        logger.add(
            sys.stdout,
            format=log_format,
            level="DEBUG" if settings.DEBUG else "INFO",
            colorize=True,
            backtrace=True,
            diagnose=True,
        )
    else:
        # Production: JSON format for log aggregation
        logger.add(
            sys.stdout,
            format="{message}",
            level="INFO",
            serialize=True,  # Output as JSON
            backtrace=False,
            diagnose=False,
        )
    
    # ========================================================================
    # FILE LOGGING (optional, for debugging)
    # ========================================================================
    
    if settings.is_development:
        # Create logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Add file handler with rotation
        logger.add(
            log_dir / "app_{time:YYYY-MM-DD}.log",
            rotation="00:00",  # Rotate at midnight
            retention="7 days",  # Keep logs for 7 days
            compression="zip",  # Compress old logs
            level="DEBUG",
            format=(
                "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
                "{level: <8} | "
                "{name}:{function}:{line} | "
                "{message}"
            ),
        )
    
    # ========================================================================
    # INTERCEPT STANDARD LIBRARY LOGGING
    # ========================================================================
    
    # Intercept uvicorn logs
    logging.getLogger("uvicorn").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.error").handlers = [InterceptHandler()]
    
    # Intercept FastAPI logs
    logging.getLogger("fastapi").handlers = [InterceptHandler()]
    
    # Set log levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    
    logger.info(f"Logging configured for {settings.ENVIRONMENT} environment")


def get_logger(name: Optional[str] = None) -> logger:
    """
    Get a logger instance
    
    Args:
        name: Optional logger name for context
        
    Returns:
        logger: Configured loguru logger
    """
    if name:
        return logger.bind(logger_name=name)
    return logger
