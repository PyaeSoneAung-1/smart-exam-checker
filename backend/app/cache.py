"""Redis caching layer with graceful fallback."""
import json
import functools
import logging
from typing import Optional, Any, Callable

logger = logging.getLogger(__name__)

_redis_client = None
_redis_available = False


def _get_redis():
    """Get Redis client, initializing on first call."""
    global _redis_client, _redis_available
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        from app.config import settings
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        _redis_client.ping()
        _redis_available = True
        logger.info("Redis connected successfully.")
        return _redis_client
    except Exception as e:
        _redis_available = False
        logger.warning(f"Redis unavailable, falling back to no-cache: {e}")
        return None


def get_cache(key: str) -> Optional[Any]:
    """Get a value from cache. Returns None if missing or Redis unavailable."""
    client = _get_redis()
    if client is None:
        return None
    try:
        value = client.get(key)
        if value is not None:
            return json.loads(value)
        return None
    except Exception as e:
        logger.error(f"Cache get error for key '{key}': {e}")
        return None


def set_cache(key: str, value: Any, ttl: int = 300) -> bool:
    """Set a value in cache with TTL in seconds. Returns success."""
    client = _get_redis()
    if client is None:
        return False
    try:
        serialized = json.dumps(value, default=str)
        client.setex(key, ttl, serialized)
        return True
    except Exception as e:
        logger.error(f"Cache set error for key '{key}': {e}")
        return False


def delete_cache(key: str) -> bool:
    """Delete a specific cache key."""
    client = _get_redis()
    if client is None:
        return False
    try:
        client.delete(key)
        return True
    except Exception as e:
        logger.error(f"Cache delete error for key '{key}': {e}")
        return False


def clear_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern. Returns count of deleted keys."""
    client = _get_redis()
    if client is None:
        return 0
    try:
        keys = client.keys(pattern)
        if keys:
            return client.delete(*keys)
        return 0
    except Exception as e:
        logger.error(f"Cache clear_pattern error for '{pattern}': {e}")
        return 0


def cached(prefix: str = "cache", ttl: int = 300, key_builder: Optional[Callable] = None):
    """Decorator for caching API endpoint responses.

    Usage:
        @router.get("/items")
        @cached(prefix="items", ttl=600)
        def list_items(...):
            ...
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = f"{prefix}:{key_builder(*args, **kwargs)}"
            else:
                key_parts = [prefix, func.__name__]
                for a in args[1:]:
                    key_parts.append(str(a))
                for k, v in sorted(kwargs.items()):
                    if k not in ("db", "current_user"):
                        key_parts.append(f"{k}={v}")
                cache_key = ":".join(key_parts)

            # Try cache
            cached_val = get_cache(cache_key)
            if cached_val is not None:
                return cached_val

            # Execute and cache
            result = func(*args, **kwargs)
            if isinstance(result, (dict, list)):
                set_cache(cache_key, result, ttl)
            return result
        return wrapper
    return decorator


def is_redis_available() -> bool:
    """Check if Redis is currently available."""
    _get_redis()
    return _redis_available
