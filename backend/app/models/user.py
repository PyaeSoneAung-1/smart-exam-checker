import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String

from app.database import Base
from app.utils.time import utcnow


class UserRole(str, enum.Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    profile_photo = Column(String(500), nullable=True)
    # Bumped on logout/password change — invalidates every token issued before.
    token_version = Column(Integer, nullable=False, default=0, server_default="0")
    # Login lockout: consecutive failed passwords, and the moment the lock lifts.
    failed_login_attempts = Column(Integer, nullable=False, default=0, server_default="0")
    locked_until = Column(DateTime, nullable=True)

    @property
    def is_locked(self) -> bool:
        """True while a failed-login lockout is in effect."""
        return self.locked_until is not None and self.locked_until > utcnow()

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"
