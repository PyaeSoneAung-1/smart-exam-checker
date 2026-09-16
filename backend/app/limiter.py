"""Shared slowapi rate limiter.

Importing this module never fails: when slowapi is not installed (it is an
optional dependency) `limiter` is `None` and the decorators become no-ops, so
the API keeps working.
"""
import logging

from app.config import settings

logger = logging.getLogger(__name__)

try:  # pragma: no cover - depends on optional dependency
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[settings.RATE_LIMIT_DEFAULT],
        enabled=settings.RATE_LIMIT_ENABLED,
    )
except ImportError:  # pragma: no cover
    limiter = None
    logger.info("slowapi is not installed — rate limiting disabled.")


def rate_limit(rule: str):
    """Decorator applying a rate limit when slowapi is available."""

    def decorator(func):
        if limiter is None:
            return func
        return limiter.limit(rule)(func)

    return decorator
