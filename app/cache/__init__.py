"""
Caching utilities for the AI Form Assistant.
"""

from .redis_cache import (
    RedisCache,
    CacheKeyBuilder,
    cache,
    cache_result,
    cache_user_data,
    get_cached_user_data,
    cache_form_template,
    get_cached_form_template,
    invalidate_user_cache,
    invalidate_form_cache,
    check_rate_limit,
)

__all__ = [
    "RedisCache",
    "CacheKeyBuilder",
    "cache",
    "cache_result",
    "cache_user_data",
    "get_cached_user_data",
    "cache_form_template",
    "get_cached_form_template",
    "invalidate_user_cache",
    "invalidate_form_cache",
    "check_rate_limit",
]