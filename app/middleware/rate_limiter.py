"""
Redis-based rate limiting middleware for API protection.
Implements sliding window rate limiting with configurable limits per endpoint.
"""
import time
from typing import Callable, Optional
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import redis.asyncio as redis

from app.core.logging_config import get_logger

logger = get_logger("middleware.rate_limiter")


class RateLimitExceeded(HTTPException):
    """Exception raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": "Too many requests. Please try again later.",
                "retry_after": retry_after
            },
            headers={"Retry-After": str(retry_after)}
        )


class RateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm.
    
    Features:
    - Configurable rate limits per endpoint pattern
    - Sliding window for accurate rate limiting
    - Graceful degradation when Redis is unavailable
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_limit: int = 100,
        default_window: int = 60,
    ):
        """
        Initialize the rate limiter.
        
        Args:
            redis_url: Redis connection URL
            default_limit: Default number of requests allowed per window
            default_window: Default time window in seconds
        """
        self.redis_url = redis_url
        self.default_limit = default_limit
        self.default_window = default_window
        self._redis: Optional[redis.Redis] = None
        
        # Endpoint-specific limits
        self.endpoint_limits = {
            "/auth/login": (10, 60),      # 10 requests per minute
            "/auth/register": (5, 60),    # 5 requests per minute
            "/api/v1/chat": (30, 60),     # 30 requests per minute
        }
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            await self._redis.ping()
            logger.info("Rate limiter connected to Redis")
        except Exception as e:
            logger.warning(f"Rate limiter Redis connection failed: {e}. Rate limiting disabled.")
            self._redis = None
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None
    
    def get_limit_for_path(self, path: str) -> tuple[int, int]:
        """Get the rate limit configuration for a given path."""
        for pattern, limits in self.endpoint_limits.items():
            if path.startswith(pattern):
                return limits
        return self.default_limit, self.default_window
    
    async def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, int, int]:
        """
        Check if a request is allowed under the rate limit.
        
        Args:
            key: Unique identifier for the rate limit (e.g., IP or user ID)
            limit: Maximum number of requests allowed
            window: Time window in seconds
            
        Returns:
            Tuple of (is_allowed, remaining_requests, retry_after_seconds)
        """
        if not self._redis:
            # Graceful degradation: allow all requests if Redis is down
            return True, limit, 0
        
        try:
            now = time.time()
            window_start = now - window
            
            # Use pipeline for atomic operations
            pipe = self._redis.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(now): now})
            
            # Set expiry on the key
            pipe.expire(key, window + 1)
            
            results = await pipe.execute()
            current_count = results[1]
            
            if current_count >= limit:
                # Calculate retry-after
                oldest = await self._redis.zrange(key, 0, 0, withscores=True)
                if oldest:
                    retry_after = int(window - (now - oldest[0][1])) + 1
                else:
                    retry_after = window
                    
                return False, 0, retry_after
            
            remaining = limit - current_count - 1
            return True, remaining, 0
            
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            # Graceful degradation
            return True, limit, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    
    Applies rate limits based on client IP and optionally user ID.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        redis_url: str = "redis://localhost:6379",
        exclude_paths: list[str] = None,
    ):
        super().__init__(app)
        self.limiter = RateLimiter(redis_url=redis_url)
        self.exclude_paths = exclude_paths or ["/health", "/ready", "/metrics", "/docs", "/openapi.json"]
        self._connected = False
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        # Lazy connect to Redis
        if not self._connected:
            await self.limiter.connect()
            self._connected = True
        
        # Get client identifier (IP address, or user ID if authenticated)
        client_id = request.client.host if request.client else "unknown"
        
        # Check for authenticated user
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            # Use a hash of the token as part of the key for authenticated users
            token_hash = hash(auth_header[7:20])  # First 20 chars of token
            client_id = f"user:{token_hash}"
        
        # Get limit for this endpoint
        limit, window = self.limiter.get_limit_for_path(request.url.path)
        
        # Create rate limit key
        key = f"ratelimit:{client_id}:{request.url.path}"
        
        # Check rate limit
        allowed, remaining, retry_after = await self.limiter.is_allowed(key, limit, window)
        
        if not allowed:
            logger.warning(
                f"Rate limit exceeded: {client_id} on {request.url.path}",
                extra={"client_id": client_id, "path": request.url.path}
            )
            raise RateLimitExceeded(retry_after=retry_after)
        
        # Process request
        response = await call_next(request)
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + window)
        
        return response
