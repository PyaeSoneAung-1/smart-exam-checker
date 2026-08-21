"""Security middleware: rate limiting, headers, logging, compression."""
import time
import logging
from typing import Callable
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Security Headers Middleware
# ──────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add standard security headers to every response."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'"
        return response


# ──────────────────────────────────────────────
# Request Logging Middleware
# ──────────────────────────────────────────────
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.time()
        method = request.method
        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000, 2)

        logger.info(
            f"{method} {path} - {response.status_code} - {duration_ms}ms - {client_ip}"
        )
        return response


# ──────────────────────────────────────────────
# Rate Limiting (slowapi)
# ──────────────────────────────────────────────
def setup_rate_limiting(app: FastAPI):
    """Configure slowapi rate limiting on the app."""
    try:
        from slowapi import Limiter, _rate_limit_exceeded_handler
        from slowapi.util import get_remote_address
        from slowapi.errors import RateLimitExceeded

        limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
        app.state.limiter = limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
        logger.info("Rate limiting configured: 60 requests/minute default.")
        return limiter
    except ImportError:
        logger.warning("slowapi not installed, rate limiting disabled.")
        return None


# ──────────────────────────────────────────────
# GZip Compression
# ──────────────────────────────────────────────
def setup_gzip(app: FastAPI, minimum_size: int = 500):
    """Enable GZip compression middleware."""
    from fastapi.middleware.gzip import GZipMiddleware
    app.add_middleware(GZipMiddleware, minimum_size=minimum_size)
    logger.info(f"GZip compression enabled (min size: {minimum_size} bytes).")


# ──────────────────────────────────────────────
# Setup all middleware
# ──────────────────────────────────────────────
def setup_middleware(app: FastAPI):
    """Register all middleware on the FastAPI app."""
    setup_gzip(app)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    limiter = setup_rate_limiting(app)
    return limiter
