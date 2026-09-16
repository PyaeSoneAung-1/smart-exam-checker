"""File upload service for exam attachments and question images."""
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.config import settings
from app.core.deps import get_current_teacher
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["File Upload"])

# Allowed MIME types
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
ALLOWED_DOC_TYPES = {"application/pdf", "text/plain", "application/msword",
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES | ALLOWED_DOC_TYPES

# File size limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_IMAGE_SIZE = 5 * 1024 * 1024   # 5 MB


def _get_upload_dir(subdir: str = "general") -> Path:
    """Get or create the upload directory."""
    upload_dir = Path(settings.UPLOAD_DIR) / subdir
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _generate_filename(original_filename: str) -> str:
    """Generate a unique filename preserving the extension."""
    ext = Path(original_filename).suffix.lower()
    return f"{uuid.uuid4().hex}{ext}"


# Magic-byte signatures: the client-supplied content type is never trusted.
_SIGNATURES = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/gif": [b"GIF87a", b"GIF89a"],
    "image/webp": [b"RIFF"],
    "application/pdf": [b"%PDF"],
    "application/msword": [b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [b"PK\x03\x04"],
}


def _content_matches_type(content: bytes, content_type: str) -> bool:
    """Return True when the bytes look like the declared content type."""
    signature = _SIGNATURES.get(content_type or "")
    if signature is None:
        # text/plain and unknown-but-allowed types: require decodable text.
        try:
            content.decode("utf-8")
            return True
        except UnicodeDecodeError:
            return False
    if content_type == "image/webp":
        return content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    return any(content.startswith(sig) for sig in signature)


async def _validate_file(
    file: UploadFile,
    allowed_types: set,
    max_size: int,
) -> bytes:
    """Validate file type (declared AND actual bytes) and size."""
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{file.content_type}' not allowed. Allowed: {', '.join(sorted(allowed_types))}",
        )
    content = await file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max size: {max_size // (1024*1024)} MB",
        )
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file upload.",
        )
    if not _content_matches_type(content, file.content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match its declared type.",
        )
    return content


@router.post("/exam-attachment", status_code=status.HTTP_201_CREATED)
async def upload_exam_attachment(
    file: UploadFile = File(..., description="Exam attachment (PDF, DOCX, TXT, or image)"),
    current_user: User = Depends(get_current_teacher),
):
    """Upload an exam attachment (teacher only).
    
    Returns the file path and metadata.
    """
    content = await _validate_file(file, ALLOWED_TYPES, MAX_FILE_SIZE)
    filename = _generate_filename(file.filename)
    upload_dir = _get_upload_dir("exam_attachments")
    filepath = upload_dir / filename
    filepath.write_bytes(content)

    relative_path = str(filepath.relative_to(Path(settings.UPLOAD_DIR)))
    logger.info(f"File uploaded by user {current_user.id}: {relative_path}")
    return {
        "filename": file.filename,
        "stored_filename": filename,
        "path": relative_path,
        "size": len(content),
        "content_type": file.content_type,
        "url": f"/api/files/{relative_path}",
        "uploaded_by": current_user.id,
    }


@router.post("/question-image", status_code=status.HTTP_201_CREATED)
async def upload_question_image(
    file: UploadFile = File(..., description="Question image (JPEG, PNG, GIF, WebP)"),
    current_user: User = Depends(get_current_teacher),
):
    """Upload an image for a question (teacher only).
    
    Returns the image path and metadata.
    """
    content = await _validate_file(file, ALLOWED_IMAGE_TYPES, MAX_IMAGE_SIZE)
    filename = _generate_filename(file.filename)
    upload_dir = _get_upload_dir("question_images")
    filepath = upload_dir / filename
    filepath.write_bytes(content)

    relative_path = str(filepath.relative_to(Path(settings.UPLOAD_DIR)))
    logger.info(f"Image uploaded by user {current_user.id}: {relative_path}")
    return {
        "filename": file.filename,
        "stored_filename": filename,
        "path": relative_path,
        "size": len(content),
        "content_type": file.content_type,
        "url": f"/api/files/{relative_path}",
        "uploaded_by": current_user.id,
    }
