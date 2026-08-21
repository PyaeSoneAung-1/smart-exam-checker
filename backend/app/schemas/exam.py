from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ExamCreate(BaseModel):
    subject_id: int
    title: str = Field(..., min_length=2, max_length=500)
    description: Optional[str] = None
    total_marks: float = Field(..., gt=0)
    time_limit_minutes: Optional[int] = Field(None, gt=0)
    is_active: bool = True


class ExamUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=500)
    description: Optional[str] = None
    total_marks: Optional[float] = Field(None, gt=0)
    time_limit_minutes: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None


class QuestionBrief(BaseModel):
    id: int
    question_text: str
    marks: float

    model_config = {"from_attributes": True}


class ExamResponse(BaseModel):
    id: int
    subject_id: int
    title: str
    description: Optional[str]
    total_marks: float
    time_limit_minutes: Optional[int]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ExamDetailResponse(ExamResponse):
    questions: List[QuestionBrief] = []
