import logging
import math
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_admin, get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.database import get_db
from app.limiter import rate_limit
from app.models.user import User
from app.schemas.user import ChangePassword, Token, TokenRefresh, UserCreate, UserLogin, UserResponse
from app.utils.time import utcnow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _token_claims(user: User) -> dict:
    """Claims shared by access and refresh tokens."""
    return {"sub": str(user.id), "role": user.role.value, "ver": int(user.token_version or 0)}


def _lock_minutes_left(locked_until) -> int:
    """Whole minutes (at least 1) until an account lock expires."""
    seconds = (locked_until - utcnow()).total_seconds()
    return max(1, math.ceil(seconds / 60))


def _lockout_error(minutes_left: int) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_423_LOCKED,
        detail=(
            f"Account locked after {settings.LOGIN_MAX_FAILED_ATTEMPTS} failed sign-in attempts. "
            f"Try again in {minutes_left} minute(s) or ask an administrator to unlock it."
        ),
    )


def _issue_tokens(user: User) -> Token:
    claims = _token_claims(user)
    return Token(
        access_token=create_access_token(claims),
        refresh_token=create_refresh_token(claims),
        token_type="bearer",
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    user_data: UserCreate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Register a new user account. Admin-only."""
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
@rate_limit(settings.RATE_LIMIT_LOGIN)
def login(request: Request, credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate a user and return access + refresh tokens."""
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = db.query(User).filter(User.email == credentials.email).first()

    # Per-account lockout, on top of the per-IP rate limit. A locked account is
    # refused before the password is even checked.
    if user and user.locked_until is not None:
        if user.locked_until > utcnow():
            logger.warning("Sign-in attempt on locked account %s", credentials.email)
            raise _lockout_error(_lock_minutes_left(user.locked_until))
        # The lock has expired — start the account with a clean slate.
        user.locked_until = None
        user.failed_login_attempts = 0
        db.commit()

    if not user or not verify_password(credentials.password, user.hashed_password):
        # The 401 body is identical whether or not the email exists, so failed
        # logins cannot be used to enumerate accounts.
        # Only active accounts are counted: a deactivated account answers like an
        # unknown email, so neither status nor lock history leaks.
        if user and user.is_active and settings.LOGIN_LOCKOUT_ENABLED:
            attempts = int(user.failed_login_attempts or 0) + 1
            remaining = settings.LOGIN_MAX_FAILED_ATTEMPTS - attempts
            if remaining <= 0:
                user.failed_login_attempts = 0
                user.locked_until = utcnow() + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
                db.commit()
                logger.warning(
                    "Account %s locked for %d minute(s) after %d failed attempts",
                    credentials.email,
                    settings.LOGIN_LOCKOUT_MINUTES,
                    settings.LOGIN_MAX_FAILED_ATTEMPTS,
                )
                raise _lockout_error(settings.LOGIN_LOCKOUT_MINUTES)
            user.failed_login_attempts = attempts
            db.commit()
            logger.info(
                "Failed login for %s (%d of %d attempts used)",
                credentials.email,
                attempts,
                settings.LOGIN_MAX_FAILED_ATTEMPTS,
            )
        else:
            logger.info("Failed login for %s", credentials.email)
        raise invalid_credentials

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # A successful sign-in clears the failed-attempt counter.
    if user.failed_login_attempts or user.locked_until is not None:
        user.failed_login_attempts = 0
        user.locked_until = None
        db.commit()

    return _issue_tokens(user)


@router.post("/refresh", response_model=Token)
@rate_limit(settings.RATE_LIMIT_LOGIN)
def refresh_token(request: Request, body: TokenRefresh, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access/refresh pair."""
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user = db.query(User).filter(User.id == int(payload.get("sub") or 0)).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    if int(payload.get("ver", 0)) != int(user.token_version or 0):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
        )

    return _issue_tokens(user)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return current_user


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Sign out everywhere: invalidates every token issued to this account."""
    current_user.token_version = int(current_user.token_version or 0) + 1
    db.commit()
    return {"message": "Logged out. All existing tokens are no longer valid."}


@router.put("/change-password")
def change_password(
    body: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change the current user's password and invalidate existing tokens."""
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.hashed_password = get_password_hash(body.new_password)
    current_user.token_version = int(current_user.token_version or 0) + 1
    db.commit()

    return {"message": "Password changed. Please sign in again."}
