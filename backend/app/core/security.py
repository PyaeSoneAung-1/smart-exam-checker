"""Password hashing and JWT helpers."""
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

from app.config import settings
from app.core._compat import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# bcrypt only considers the first 72 bytes of a password and raises on longer
# input, so hash a stable prefix-safe value instead of erroring.
BCRYPT_MAX_BYTES = 72


def _clamp_password(password: str) -> str:
    """Trim a password to bcrypt's 72-byte limit without splitting a character."""
    encoded = password.encode("utf-8")
    if len(encoded) <= BCRYPT_MAX_BYTES:
        return password
    return encoded[:BCRYPT_MAX_BYTES].decode("utf-8", errors="ignore")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    try:
        return pwd_context.verify(_clamp_password(plain_password), hashed_password)
    except ValueError:
        return False


def get_password_hash(password: str) -> str:
    """Hash a plain password using bcrypt."""
    return pwd_context.hash(_clamp_password(password))


def _encode(payload: dict, expires_delta: timedelta) -> str:
    to_encode = payload.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + expires_delta
    to_encode["iat"] = datetime.now(timezone.utc)
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return _encode({**data, "type": "access"}, delta)


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT refresh token."""
    delta = expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return _encode({**data, "type": "refresh"}, delta)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token. Returns None when invalid/expired."""
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp"]},
        )
    except jwt.PyJWTError:
        return None
