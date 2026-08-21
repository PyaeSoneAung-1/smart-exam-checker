from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class SubjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    teacher_id: Optional[int] = None


class SubjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None


class SubjectResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    teacher_id: int
    teacher_name: Optional[str] = None
    exam_count: int = 0
    total_students: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}
