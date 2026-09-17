import csv
import io
import secrets
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import get_current_admin, get_current_admin_or_teacher, get_current_user
from app.core.security import get_password_hash
from app.database import get_db
from app.file_upload import _content_matches_type
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.utils.pagination import PaginationParams, get_pagination_params, paginate_query

router = APIRouter(prefix="/users", tags=["Users"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "profile_photos"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)



@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Create a single user (admin only)."""
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


@router.post("/bulk-import", response_model=dict, status_code=status.HTTP_201_CREATED)
def bulk_import_users(
    file: UploadFile = File(..., description="CSV file with columns: name, email, role, password (optional)"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Bulk import users from a CSV file (admin only).

    CSV columns: name, email, role, password
    - password is optional: each row without one gets a random password which
      is returned once in this response (set BULK_IMPORT_PASSWORD to use a
      fixed shared password instead)
    - role is optional; defaults to 'student'
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file",
        )

    content = file.file.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(content))

    created_users = []
    skipped = []
    errors = []

    for i, row in enumerate(reader, start=1):
        name = row.get("name", "").strip()
        email = row.get("email", "").strip()
        role_str = row.get("role", "student").strip().lower()
        password = (row.get("password") or "").strip() or settings.BULK_IMPORT_PASSWORD
        generated = password is None
        if generated:
            password = secrets.token_urlsafe(9)

        if not name or not email:
            errors.append(f"Row {i}: missing name or email")
            continue

        # Validate role
        try:
            role = UserRole(role_str)
        except ValueError:
            role = UserRole.STUDENT

        # Check if user exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            skipped.append(email)
            continue

        user = User(
            name=name,
            email=email,
            hashed_password=get_password_hash(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        entry = {"name": name, "email": email, "role": role.value}
        if generated:
            entry["temporary_password"] = password
        created_users.append(entry)

    db.commit()

    return {
        "created": len(created_users),
        "skipped": len(skipped),
        "errors": errors,
        "users": created_users,
        "skipped_emails": skipped,
    }


@router.get("/", response_model=dict)
def list_users(
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    pagination: PaginationParams = Depends(get_pagination_params),
    current_user: User = Depends(get_current_admin_or_teacher),
    db: Session = Depends(get_db),
):
    """List users. Admin sees all; teacher sees only students."""
    query = db.query(User)

    # Teachers can only see students
    if current_user.role == UserRole.TEACHER:
        query = query.filter(User.role == UserRole.STUDENT)
        if role and role != UserRole.STUDENT:
            # Teachers can't see non-student users
            query = query.filter(User.id == -1)
    elif role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        query = query.filter(
            (User.name.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%"))
        )

    query = query.order_by(User.created_at.desc())
    result = paginate_query(query, db, pagination)
    # Serialize items
    result.items = [UserResponse.model_validate(u).model_dump() for u in result.items]
    return result.model_dump()


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get a specific user by ID (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Update a user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data = user_data.model_dump(exclude_unset=True)

    # Hash password separately before setattr
    if "password" in update_data:
        user.hashed_password = get_password_hash(update_data.pop("password"))

    for field, value in update_data.items():
        setattr(user, field, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Deactivate a user (admin only). Soft delete."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself",
        )

    user.is_active = False
    db.commit()


@router.put("/{user_id}/activate", response_model=UserResponse)
def activate_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Reactivate a deactivated user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


@router.post("/{user_id}/unlock", response_model=UserResponse)
def unlock_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Clear a login lockout so the user can sign in again (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}/profile-photo", response_model=UserResponse)
def upload_profile_photo(
    user_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a profile photo. Users can update their own; admin can update any."""
    if current_user.id != user_id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user's profile photo",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an image (JPEG, PNG, GIF, or WebP)",
        )

    ext = Path(file.filename or "").suffix.lower().lstrip(".") or "jpg"
    filename = f"{user_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}.{ext}"
    file_path = UPLOAD_DIR / filename

    content = file.file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file upload.")
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image too large. Max size: 5 MB")
    if not _content_matches_type(content, file.content_type or ""):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match its declared type.",
        )

    with open(file_path, "wb") as f:
        f.write(content)

    user.profile_photo = f"/api/files/profile_photos/{filename}"
    db.commit()
    db.refresh(user)
    return user
