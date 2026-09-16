from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.database import get_db
from app.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def resolve_token_user(token: str, db: Session) -> Optional[User]:
    """Return the user for a valid *access* token, else None.

    Also enforces the per-user `token_version`, so incrementing it (logout or
    password change) immediately invalidates every previously issued token.
    """
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        return None

    subject = payload.get("sub")
    if subject is None:
        return None

    user = db.query(User).filter(User.id == int(subject)).first()
    if user is None or not user.is_active:
        return None

    if int(payload.get("ver", 0)) != int(user.token_version or 0):
        return None

    return user


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db),
) -> User:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user = resolve_token_user(token, db)
    if user is None:
        raise credentials_exception

    return user


async def get_current_admin_or_teacher(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Dependency that requires the current user to be an admin or teacher."""
    if current_user.role not in (UserRole.ADMIN, UserRole.TEACHER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or teacher access required",
        )
    return current_user


async def get_current_student(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Dependency that requires the current user to be a student."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student access required",
        )
    return current_user


async def get_current_teacher(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Dependency that requires the current user to be a teacher."""
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teacher access required",
        )
    return current_user


async def get_current_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Dependency that requires the current user to be an admin."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
