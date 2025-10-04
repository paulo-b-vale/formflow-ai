"""
Redis caching utilities for the AI Form Assistant.

This module provides a comprehensive caching layer using Redis for
improved performance and reduced database load.
"""

import json
import logging
import pickle
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from functools import wraps

import redis.asyncio as redis
from redis.exceptions import RedisError, ConnectionError

from app.config.settings import settings
from app.core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis-based caching manager with async support."""

    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.is_connected = False

    async def connect(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False,  # We'll handle encoding ourselves
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30,
            )

            # Test connection
            await self.redis_client.ping()
            self.is_connected = True
            logger.info("✅ Connected to Redis cache")

        except Exception as e:
            logger.error(f"❌ Failed to connect to Redis: {str(e)}")
            self.is_connected = False
            raise ExternalServiceError("Redis", f"Connection failed: {str(e)}")

    async def disconnect(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()
            self.is_connected = False
            logger.info("Disconnected from Redis cache")

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
        serialize: str = "json"
    ) -> bool:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default 1 hour)
            serialize: Serialization method ('json' or 'pickle')

        Returns:
            True if successful, False otherwise
        """
        if not self._check_connection():
            return False

        try:
            # Serialize the value
            if serialize == "json":
                serialized_value = json.dumps(value, default=str)
            elif serialize == "pickle":
                serialized_value = pickle.dumps(value)
            else:
                raise ValueError(f"Unsupported serialization method: {serialize}")

            # Set in Redis with TTL
            await self.redis_client.setex(key, ttl, serialized_value)
            logger.debug(f"Cached value for key: {key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Error setting cache key {key}: {str(e)}")
            return False

    async def get(self, key: str, serialize: str = "json") -> Optional[Any]:
        """
        Get a value from the cache.

        Args:
            key: Cache key
            serialize: Serialization method used ('json' or 'pickle')

        Returns:
            Cached value or None if not found
        """
        if not self._check_connection():
            return None

        try:
            serialized_value = await self.redis_client.get(key)
            if serialized_value is None:
                return None

            # Deserialize the value
            if serialize == "json":
                return json.loads(serialized_value)
            elif serialize == "pickle":
                return pickle.loads(serialized_value)
            else:
                raise ValueError(f"Unsupported serialization method: {serialize}")

        except Exception as e:
            logger.error(f"Error getting cache key {key}: {str(e)}")
            return None

    async def delete(self, key: str) -> bool:
        """
        Delete a key from the cache.

        Args:
            key: Cache key to delete

        Returns:
            True if successful, False otherwise
        """
        if not self._check_connection():
            return False

        try:
            result = await self.redis_client.delete(key)
            logger.debug(f"Deleted cache key: {key}")
            return bool(result)

        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {str(e)}")
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.

        Args:
            key: Cache key to check

        Returns:
            True if key exists, False otherwise
        """
        if not self._check_connection():
            return False

        try:
            return bool(await self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Error checking cache key {key}: {str(e)}")
            return False

    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration time for a key.

        Args:
            key: Cache key
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        if not self._check_connection():
            return False

        try:
            return bool(await self.redis_client.expire(key, ttl))
        except Exception as e:
            logger.error(f"Error setting expiration for key {key}: {str(e)}")
            return False

    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a numeric value in the cache.

        Args:
            key: Cache key
            amount: Amount to increment by

        Returns:
            New value after increment or None if error
        """
        if not self._check_connection():
            return None

        try:
            return await self.redis_client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Error incrementing cache key {key}: {str(e)}")
            return None

    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching a pattern.

        Args:
            pattern: Redis pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        if not self._check_connection():
            return 0

        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(f"Cleared {deleted} cache keys matching pattern: {pattern}")
                return deleted
            return 0

        except Exception as e:
            logger.error(f"Error clearing cache pattern {pattern}: {str(e)}")
            return 0

    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Get the time to live for a key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds, -1 if no expiration, -2 if key doesn't exist, None if error
        """
        if not self._check_connection():
            return None

        try:
            return await self.redis_client.ttl(key)
        except Exception as e:
            logger.error(f"Error getting TTL for key {key}: {str(e)}")
            return None

    def _check_connection(self) -> bool:
        """Check if Redis connection is active."""
        if not self.is_connected or not self.redis_client:
            logger.warning("Redis connection not available")
            return False
        return True


class CacheKeyBuilder:
    """Utility class for building consistent cache keys."""

    @staticmethod
    def user_key(user_id: str) -> str:
        """Build cache key for user data."""
        return f"user:{user_id}"

    @staticmethod
    def form_template_key(template_id: str) -> str:
        """Build cache key for form template."""
        return f"form_template:{template_id}"

    @staticmethod
    def context_key(context_id: str) -> str:
        """Build cache key for context data."""
        return f"context:{context_id}"

    @staticmethod
    def form_responses_key(user_id: str, page: int = 1, limit: int = 20) -> str:
        """Build cache key for paginated form responses."""
        return f"form_responses:{user_id}:page_{page}_limit_{limit}"

    @staticmethod
    def user_forms_key(user_id: str) -> str:
        """Build cache key for user's accessible forms."""
        return f"user_forms:{user_id}"

    @staticmethod
    def analytics_key(metric: str, period: str = "daily") -> str:
        """Build cache key for analytics data."""
        return f"analytics:{metric}:{period}"

    @staticmethod
    def rate_limit_key(user_id: str, endpoint: str) -> str:
        """Build cache key for rate limiting."""
        return f"rate_limit:{user_id}:{endpoint}"

    @staticmethod
    def session_key(session_id: str) -> str:
        """Build cache key for session data."""
        return f"session:{session_id}"


def cache_result(
    ttl: int = 3600,
    key_builder: Optional[callable] = None,
    serialize: str = "json"
):
    """
    Decorator for caching function results.

    Args:
        ttl: Time to live in seconds
        key_builder: Function to build cache key from function args
        serialize: Serialization method ('json' or 'pickle')
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get cache instance (assumes it's available in the app context)
            cache = getattr(func, '_cache', None)
            if not cache:
                # If no cache available, just call the function
                return await func(*args, **kwargs)

            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key building
                key_parts = [func.__name__]
                key_parts.extend(str(arg) for arg in args)
                key_parts.extend(f"{k}:{v}" for k, v in kwargs.items())
                cache_key = ":".join(key_parts)

            # Try to get from cache
            cached_result = await cache.get(cache_key, serialize=serialize)
            if cached_result is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_result

            # Call function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl=ttl, serialize=serialize)
            logger.debug(f"Cached result for key: {cache_key}")

            return result

        return wrapper
    return decorator


# Global cache instance
cache = RedisCache()


# Convenience functions for common cache operations
async def cache_user_data(user_id: str, user_data: Dict[str, Any], ttl: int = 1800):
    """Cache user data for 30 minutes."""
    key = CacheKeyBuilder.user_key(user_id)
    await cache.set(key, user_data, ttl=ttl)


async def get_cached_user_data(user_id: str) -> Optional[Dict[str, Any]]:
    """Get cached user data."""
    key = CacheKeyBuilder.user_key(user_id)
    return await cache.get(key)


async def cache_form_template(template_id: str, template_data: Dict[str, Any], ttl: int = 3600):
    """Cache form template for 1 hour."""
    key = CacheKeyBuilder.form_template_key(template_id)
    await cache.set(key, template_data, ttl=ttl)


async def get_cached_form_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Get cached form template."""
    key = CacheKeyBuilder.form_template_key(template_id)
    return await cache.get(key)


async def invalidate_user_cache(user_id: str):
    """Invalidate all cache entries related to a user."""
    pattern = f"*{user_id}*"
    await cache.clear_pattern(pattern)


async def invalidate_form_cache(template_id: str):
    """Invalidate cache entries related to a form template."""
    await cache.delete(CacheKeyBuilder.form_template_key(template_id))


async def cache_user_forms(user_id: str, forms_data: List[Dict[str, Any]], ttl: int = 1800):
    """Cache user's accessible forms for 30 minutes."""
    key = CacheKeyBuilder.user_forms_key(user_id)
    await cache.set(key, forms_data, ttl=ttl)


async def get_cached_user_forms(user_id: str) -> Optional[List[Dict[str, Any]]]:
    """Get cached user forms."""
    key = CacheKeyBuilder.user_forms_key(user_id)
    return await cache.get(key)


async def invalidate_user_forms_cache(user_id: str):
    """Invalidate cached user forms."""
    key = CacheKeyBuilder.user_forms_key(user_id)
    await cache.delete(key)


# Rate limiting utilities
async def check_rate_limit(
    user_id: str,
    endpoint: str,
    limit: int = 100,
    window: int = 3600
) -> tuple[bool, int]:
    """
    Check if user has exceeded rate limit.

    Args:
        user_id: User ID
        endpoint: API endpoint
        limit: Maximum requests per window
        window: Time window in seconds

    Returns:
        Tuple of (is_allowed, remaining_requests)
    """
    key = CacheKeyBuilder.rate_limit_key(user_id, endpoint)

    # Get current count
    current_count = await cache.get(key, serialize="json")
    if current_count is None:
        current_count = 0

    if current_count >= limit:
        return False, 0

    # Increment count
    new_count = await cache.increment(key)
    if new_count == 1:
        # Set expiration on first increment
        await cache.expire(key, window)

    remaining = max(0, limit - new_count)
    return True, remaining