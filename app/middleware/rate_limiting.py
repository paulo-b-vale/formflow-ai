"""
Rate limiting middleware using Redis cache.

This module provides rate limiting functionality to protect against
abuse and ensure fair usage of the API.
"""

import logging
from typing import Dict, Any
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.cache import check_rate_limit

logger = logging.getLogger(__name__)


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limits per user and endpoint.
    """

    def __init__(self, app, default_limits: Dict[str, Dict[str, Any]] = None):
        super().__init__(app)
        self.default_limits = default_limits or {
            "auth": {"limit": 10, "window": 300},  # 10 requests per 5 minutes
            "forms": {"limit": 100, "window": 3600},  # 100 requests per hour
            "conversation": {"limit": 50, "window": 3600},  # 50 requests per hour
            "files": {"limit": 20, "window": 3600},  # 20 requests per hour
            "default": {"limit": 200, "window": 3600},  # 200 requests per hour
        }

    async def dispatch(self, request: Request, call_next):
        """
        Check rate limits before processing request.
        """
        # Skip rate limiting for certain paths
        if await self._should_skip_rate_limiting(request):
            return await call_next(request)

        # Get user ID from request (from authentication)
        user_id = await self._get_user_id(request)
        if not user_id:
            # Rate limit by IP for unauthenticated requests
            user_id = request.client.host if request.client else "unknown"

        # Determine rate limit category
        endpoint_category = self._get_endpoint_category(request.url.path)
        limits = self.default_limits.get(endpoint_category, self.default_limits["default"])

        # Check rate limit
        is_allowed, remaining = await check_rate_limit(
            user_id=user_id,
            endpoint=endpoint_category,
            limit=limits["limit"],
            window=limits["window"]
        )

        if not is_allowed:
            logger.warning(f"Rate limit exceeded for user {user_id} on endpoint {endpoint_category}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "type": "rate_limit_exceeded",
                        "message": f"Rate limit exceeded. Try again later.",
                        "retry_after": limits["window"]
                    }
                },
                headers={
                    "X-RateLimit-Limit": str(limits["limit"]),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(limits["window"]),
                    "Retry-After": str(limits["window"])
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limits["limit"])
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(limits["window"])

        return response

    async def _should_skip_rate_limiting(self, request: Request) -> bool:
        """
        Determine if rate limiting should be skipped for this request.
        """
        skip_paths = [
            "/health",
            "/",
            "/docs",
            "/redoc",
            "/openapi.json"
        ]

        path = request.url.path
        return any(path.startswith(skip_path) for skip_path in skip_paths)

    async def _get_user_id(self, request: Request) -> str:
        """
        Extract user ID from request authentication.
        """
        try:
            # Try to get user from request state (set by auth middleware)
            if hasattr(request.state, "user") and request.state.user:
                return str(request.state.user.get("id", "unknown"))

            # Try to get from Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # In a real implementation, you'd decode the JWT token here
                # For now, we'll use the token as an identifier
                token = auth_header[7:]
                return f"token:{hash(token) % 1000000}"  # Simple hash for demo

            return request.client.host if request.client else "unknown"

        except Exception as e:
            logger.error(f"Error extracting user ID: {str(e)}")
            return "unknown"

    def _get_endpoint_category(self, path: str) -> str:
        """
        Categorize endpoint for rate limiting.
        """
        if path.startswith("/auth"):
            return "auth"
        elif path.startswith("/forms") or path.startswith("/forms-management"):
            return "forms"
        elif path.startswith("/enhanced_conversation"):
            return "conversation"
        elif path.startswith("/files"):
            return "files"
        else:
            return "default"


def create_rate_limiting_middleware(custom_limits: Dict[str, Dict[str, Any]] = None):
    """
    Factory function to create rate limiting middleware with custom limits.

    Args:
        custom_limits: Custom rate limits per endpoint category

    Returns:
        Configured middleware class
    """
    class CustomRateLimitingMiddleware(RateLimitingMiddleware):
        def __init__(self, app):
            super().__init__(app, custom_limits)

    return CustomRateLimitingMiddleware