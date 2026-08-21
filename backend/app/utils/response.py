from pydantic import BaseModel
from typing import Any, Optional


class APIResponse(BaseModel):
    success: bool = True
    message: str = "OK"
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    detail: Optional[str] = None


def success_response(message: str = "OK", data: Any = None) -> dict:
    return {"success": True, "message": message, "data": data}


def error_response(message: str, detail: Optional[str] = None) -> dict:
    return {"success": False, "message": message, "detail": detail}
