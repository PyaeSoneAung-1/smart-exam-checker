"""Authenticated access to uploaded files.

Uploads are private by default: files live outside any static mount and are
served through this endpoint, which requires a valid access token — either in
the `Authorization` header or as a `?token=` query parameter (needed because
`<img src>` cannot send headers). Set `UPLOADS_PUBLIC=true` to also mount them
as static files.
"""
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.core.deps import resolve_token_user
from app.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["Files"])


def _token_from_request(request: Request, token: Optional[str]) -> Optional[str]:
    if token:
        return token
    header = request.headers.get("Authorization", "")
    scheme, _, credentials = header.partition(" ")
    if scheme.lower() == "bearer" and credentials:
        return credentials
    return None


@router.get("/{file_path:path}")
def get_uploaded_file(
    file_path: str,
    request: Request,
    token: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Serve an uploaded file to authenticated users only."""
    raw_token = _token_from_request(request, token)
    if not raw_token or resolve_token_user(raw_token, db) is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    root = Path(settings.UPLOAD_DIR).resolve()
    target = (root / file_path.lstrip("/")).resolve()
    if root != target and root not in target.parents:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    if not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    return FileResponse(target)
