"""
Request logging middleware for structured observability.
Logs all incoming requests with timing, status codes, and request IDs.
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.logging_config import get_logger

logger = get_logger("middleware.logging")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that logs all HTTP requests with structured data.
    
    Features:
    - Generates unique request IDs for tracing
    - Measures request duration
    - Logs request/response metadata
    - Adds request ID to response headers
    """

    def __init__(self, app: ASGIApp, exclude_paths: list[str] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/ready", "/metrics", "/favicon.ico"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip logging for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Generate request ID
        request_id = str(uuid.uuid4())[:8]
        
        # Store in request state for use in handlers
        request.state.request_id = request_id
        
        # Record start time
        start_time = time.perf_counter()
        
        # Log incoming request
        logger.info(
            f"→ {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.query_params) if request.query_params else None,
                "client_ip": request.client.host if request.client else None,
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            # Log exception
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"✗ {request.method} {request.url.path} - Exception: {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration_ms, 2),
                    "status_code": 500,
                },
                exc_info=True
            )
            raise
        
        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        # Log response
        log_level = "info" if status_code < 400 else "warning" if status_code < 500 else "error"
        status_symbol = "✓" if status_code < 400 else "⚠" if status_code < 500 else "✗"
        
        getattr(logger, log_level)(
            f"{status_symbol} {request.method} {request.url.path} → {status_code} ({duration_ms:.0f}ms)",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": round(duration_ms, 2),
            }
        )
        
        return response


class RequestIDMiddleware:
    """
    Simple middleware that just adds request ID without full logging.
    Useful when you want request tracing but minimal logging overhead.
    """
    
    def __init__(self, app: ASGIApp):
        self.app = app
        
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request_id = str(uuid.uuid4())[:8]
            scope["state"] = scope.get("state", {})
            scope["state"]["request_id"] = request_id
            
        await self.app(scope, receive, send)
