"""
Request Logging Middleware
===========================
Logs all incoming requests and outgoing responses with timing information.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging_config import get_logger


logger = get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all HTTP requests and responses
    
    Features:
    - Request ID generation and tracking
    - Request timing
    - Structured logging
    - Response status tracking
    """
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process request and log details
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain
            
        Returns:
            Response: HTTP response
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Store request ID in request state for access in routes
        request.state.request_id = request_id
        
        # Start timer
        start_time = time.time()
        
        # Extract request details
        method = request.method
        path = request.url.path
        client_host = request.client.host if request.client else "unknown"
        
        # Log incoming request
        logger.info(
            "Incoming request",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "client_host": client_host,
                "user_agent": request.headers.get("user-agent", "unknown"),
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log error
            process_time = time.time() - start_time
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "process_time": round(process_time, 4),
                }
            )
            raise
        
        # Calculate processing time
        process_time = time.time() - start_time
        
        # Add custom headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(round(process_time, 4))
        
        # Log response
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "process_time": round(process_time, 4),
            }
        )
        
        return response
